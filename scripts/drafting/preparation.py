"""Freeze reviewable output and atomic tasks before any candidate application."""
import difflib
from pathlib import Path
from . import decisions
from .storage import atomic, digest, disjoint, encoded, inventory, read_json, require, safe_root, save, tree, write_tree
from .validation import verify_files
from .layout import check_empty_directories


def prepare(input_root, proposal, work, requirements, decision_file, evidence_root=None):
    input_root, proposal, work = map(safe_root, (input_root, proposal, work))
    disjoint(input_root, proposal, work)
    require(not work.exists(), "Work directory must be new")
    before, after = tree(input_root), tree(proposal)
    evidence = tree(evidence_root) if evidence_root else {}
    decision_data = read_json(decision_file)
    roots = decision_data.get("roots", ["."])
    name = decision_data["name"]
    coverage = decisions.check(before, after, decision_data, evidence)
    report = verify_files(after, name, roots, decision_data.get("dispositions", []))
    report["errors"].extend(check_empty_directories(proposal, roots, report["warnings"]))
    report["passed"] = not report["errors"]
    require(report["passed"], "Proposal verification failed: " + str(report["errors"][:12]))
    requirements_data = Path(requirements).read_bytes()
    require(bool(requirements_data.strip()), "Requirements cannot be empty")
    tasks, diffs = [], {}
    for path in sorted(set(before) | set(after)):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        task = {"id": digest(path.encode())[:16], "path": path, "before": digest(old) if old is not None else None, "after": digest(new) if new is not None else None,
                "action": "remove" if new is None else "create" if old is None else "replace"}
        tasks.append(task)
        try:
            diff = "".join(difflib.unified_diff((old or b"").decode("utf-8").splitlines(True), (new or b"").decode("utf-8").splitlines(True), "input/" + path, "candidate/" + path))
        except UnicodeDecodeError:
            diff = f"Binary bytes: {task['before']} -> {task['after']}\n"
        diffs[task["id"] + ".diff"] = diff.encode("utf-8")
    manifest = {"schema_version": 1, "name": name, "roots": roots, "dispositions": decision_data.get("dispositions", []), "input_root": str(input_root), "proposal_root": str(proposal), "before": inventory(before), "after": inventory(after),
                "requirements": digest(requirements_data), "decisions": digest(encoded(decision_data)), "evidence": inventory(evidence), "diffs": inventory(diffs), "tasks": tasks}
    work.mkdir(parents=True)
    write_tree(work / "input", before); write_tree(work / "proposed", after)
    write_tree(work / "evidence", evidence); write_tree(work / "diffs", diffs)
    atomic(work / "REQUIREMENTS.md", requirements_data)
    save(work / "decisions.json", decision_data)
    save(work / "manifest.json", manifest)
    atomic(work / "manifest.sha256", (digest(encoded(manifest)) + "\n").encode())
    save(work / "verification.json", report)
    save(work / "coverage.json", coverage)
    save(work / "checkpoint.json", {"state": "prepared", "next": "Reread REQUIREMENTS.md and manifest; apply staged candidate.", "completed": []})
    return {"state": "prepared", "work": str(work), "tasks": len(tasks), "candidate_digest": report["digest"]}


def load(work):
    work = safe_root(work)
    manifest = read_json(work / "manifest.json")
    require(digest(encoded(manifest)) == (work / "manifest.sha256").read_text().strip(), "Manifest changed")
    require(digest((work / "REQUIREMENTS.md").read_bytes()) == manifest["requirements"], "Requirements changed")
    require(digest(encoded(read_json(work / "decisions.json"))) == manifest["decisions"], "Decisions changed")
    for folder, key in (("input", "before"), ("proposed", "after"), ("evidence", "evidence"), ("diffs", "diffs")):
        require(inventory(tree(work / folder)) == manifest[key], "Frozen artifact changed: " + folder)
    return manifest
