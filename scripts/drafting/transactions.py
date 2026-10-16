"""Idempotent file transitions with snapshots and drift checks, never recursive deletion."""
import os
from contextlib import contextmanager
from pathlib import Path
from .preparation import load
from .storage import atomic, digest, disjoint, git_state, inventory, loads, read_json, require, safe_root, save, target, tree, tree_digest, write_tree
import json
from .validation import verify_files
from .layout import check_empty_directories


@contextmanager
def lock(work):
    path = safe_root(work) / "transaction.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Transaction lock exists; confirm no writer is running before removing the lock in the work directory")
    try:
        os.write(descriptor, str(os.getpid()).encode()); os.close(descriptor)
        yield
    finally:
        path.unlink()


def transition(root, before, after, journal_path, stop_after=None):
    root = safe_root(root)
    root.mkdir(parents=True, exist_ok=True)
    current = tree(root)
    paths = set(before) | set(after)
    for name in after:
        destination = target(root, name)
        require(not destination.is_dir(), "File/directory transition requires a separate reviewed revision: " + name)
        require(not any(parent.is_file() for parent in destination.parents if parent.is_relative_to(root)), "Directory/file transition requires a separate reviewed revision: " + name)
    known_directories = {str(parent).replace("\\", "/") for name in set(before) | set(after) for parent in Path(name).parents if str(parent) != "."}
    require(not set(current) - (set(before) | set(after)), "Unrecorded target files")
    for path in set(before) | set(after):
        require(current.get(path) in (before.get(path), after.get(path)), "Intervening edits: " + path)
    event_path = safe_root(journal_path.with_suffix(".jsonl"))
    outcomes = []
    completed = set()
    if event_path.exists():
        journal_bytes = event_path.read_bytes()
        require(not journal_bytes or journal_bytes.endswith(b"\n"), "Incomplete journal record; preserve and inspect before resuming")
        for line in journal_bytes.decode("utf-8").splitlines():
            outcome = loads(line)
            path = outcome["path"]
            require(path in paths, "Unknown journal path")
            require(path not in completed, "Duplicate journal outcome")
            expected = after.get(path)
            require(outcome["sha256"] == (digest(expected) if expected is not None else None), "Journal outcome changed")
            require(current.get(path) == expected, "Completed outcome drift: " + path)
            completed.add(path)
            outcomes.append(outcome)
    save(journal_path, {"state": "running", "journal": event_path.name, "completed_count": len(outcomes)})
    for path in sorted(set(before) | set(after)):
        if path in completed:
            continue
        destination = target(root, path)
        expected = after.get(path)
        observed = destination.read_bytes() if destination.is_file() else None
        require(observed == current.get(path), "Concurrent target edit: " + path)
        if current.get(path) != expected:
            if expected is None:
                destination.unlink()
            else:
                require(not destination.is_dir(), "File/directory collision: " + path)
                atomic(destination, expected)
        outcome = {"path": path, "sha256": digest(expected) if expected is not None else None}
        with event_path.open("ab") as handle:
            handle.write((json.dumps(outcome, ensure_ascii=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        outcomes.append(outcome)
        if stop_after and len(outcomes) == stop_after:
            raise RuntimeError("Injected interruption after recorded file outcome")
    # Only empty directories within the verified root are removed.
    for folder, dirs, _ in os.walk(root, topdown=False):
        for directory in dirs:
            path = safe_root(Path(folder) / directory)
            if ".git" in path.relative_to(root).parts:
                continue
            require(path.is_relative_to(root) and path != root, "Directory containment")
            if path.relative_to(root).as_posix() in known_directories and not any(path.iterdir()):
                path.rmdir()
    require(inventory(tree(root)) == inventory(after), "Emitted tree differs")
    save(journal_path, {"completed": outcomes, "state": "complete"})


def apply(work, stop_after=None):
    work = safe_root(work)
    with lock(work):
        manifest = load(work)
        require(inventory(tree(manifest["input_root"])) == manifest["before"], "Live input drift")
        after = tree(work / "proposed")
        preflight = verify_files(after, manifest["name"], manifest["roots"], manifest["dispositions"])
        require(preflight["passed"], "Prepared proposal violates current verification: " + str(preflight["errors"][:12]))
        candidate = work / "candidate" / manifest["name"]
        require(not candidate.exists() or not check_empty_directories(candidate, manifest["roots"]), "Unexpected candidate directories")
        if (work / "apply.json").exists() and read_json(work / "apply.json")["state"] == "complete":
            require(inventory(tree(candidate)) == manifest["after"], "Completed candidate drift")
        transition(candidate, {}, after, work / "apply.json", stop_after)
        report = verify_files(tree(candidate), manifest["name"], manifest["roots"], manifest["dispositions"])
        require(report["passed"], "Candidate verification failed")
        save(work / "candidate_verification.json", report)
        save(work / "checkpoint.json", {"state": "awaiting_owner_review", "next": "Review candidate, tasks, source map and diffs; deployment requires exact digest authorization.", "candidate": str(candidate), "digest": report["digest"]})
        return report


def deploy(work, destination, approved_digest, authorization, stop_after=None):
    work, destination = safe_root(work), safe_root(destination)
    disjoint(work, destination)
    with lock(work):
        manifest = load(work)
        require(destination == safe_root(manifest["input_root"]), "Deployment destination must be the captured input root")
        after = tree(work / "candidate" / manifest["name"])
        require(not check_empty_directories(work / "candidate" / manifest["name"], manifest["roots"]), "Unexpected candidate directories")
        require(inventory(after) == manifest["after"], "Candidate drift")
        report = verify_files(after, manifest["name"], manifest["roots"], manifest["dispositions"])
        require(report["passed"] and approved_digest == tree_digest(after), "Approval does not match verified bytes")
        require(bool(authorization.strip()), "Caller authorization statement required")
        record_path = work / "deployment.json"
        before = tree(work / "input")
        if record_path.exists():
            record = read_json(record_path)
            require(record["destination"] == str(destination) and record["approved_digest"] == approved_digest, "Different deployment transaction")
            require(record["state"] != "rolled_back", "Use a new preparation after rollback")
            require(record["state"] != "rolling_back", "Rollback is in progress")
            if record["state"] == "deployed_verified":
                require(inventory(tree(destination)) == manifest["after"], "Completed deployment drift")
            require(inventory(tree(work / "rollback")) == manifest["before"], "Rollback snapshot drift")
            require(git_state(destination) == record["git"], "Git metadata changed during transaction")
        else:
            require(inventory(tree(destination)) == manifest["before"], "Live input drift")
            if (work / "rollback").exists():
                require(inventory(tree(work / "rollback")) == manifest["before"], "Incomplete rollback snapshot; inspect before resuming")
            else:
                write_tree(work / "rollback", before)
            record = {"state": "running", "destination": str(destination), "approved_digest": approved_digest, "authorization": authorization, "git": git_state(destination)}
            save(record_path, record)
        transition(destination, before, after, work / "deploy_outcomes.json", stop_after)
        require(git_state(destination) == record["git"], "Git metadata changed")
        record["state"] = "deployed_verified"
        save(record_path, record)
        save(work / "checkpoint.json", {"state": record["state"], "next": "Preserve deployment receipt and rollback snapshot."})
        return record


def rollback(work, authorization, stop_after=None):
    work = safe_root(work)
    with lock(work):
        manifest = load(work)
        record = read_json(work / "deployment.json")
        require(bool(authorization.strip()), "Rollback authorization required")
        require(record["state"] in {"deployed_verified", "rolling_back"}, "Deployment must finish before rollback")
        destination = safe_root(record["destination"])
        require(destination == safe_root(manifest["input_root"]), "Rollback destination drift")
        disjoint(work, destination)
        before, after = tree(work / "rollback"), tree(work / "proposed")
        require(inventory(before) == manifest["before"], "Rollback snapshot drift")
        require(git_state(destination) == record["git"], "Git metadata changed")
        if record["state"] == "deployed_verified":
            require(inventory(tree(destination)) == manifest["after"], "Post-deployment edits; rollback refused")
        record.update(state="rolling_back", rollback_authorization=authorization)
        save(work / "deployment.json", record)
        transition(destination, after, before, work / "rollback_outcomes.json", stop_after)
        record["state"] = "rolled_back"
        save(work / "deployment.json", record)
        save(work / "checkpoint.json", {"state": "rolled_back", "next": "Prepare a new revision before further changes."})
        return record
