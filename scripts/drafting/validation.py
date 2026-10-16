"""Structural evidence; semantic correctness still requires a recorded review."""
import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from . import markdown
from .format import check_entry, frontmatter
from .path_limits import check_paths
from .classification import classify
from .catalogs import inspect as inspect_catalog
from .storage import Refusal, digest, loads, relative, require, tree, tree_digest


def resolve(source, url, files):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None, None
    raw = unquote(parsed.path)
    if "\\" in raw or raw.startswith("/"):
        raise Refusal("Absolute or backslash local link")
    path = posixpath.normpath(posixpath.join(posixpath.dirname(source), raw)) if raw else source
    relative(path)
    if path not in files:
        raise Refusal("Missing local target: " + path)
    return path, unquote(parsed.fragment)


def verify_files(files, name, roots=(".",), dispositions=()):
    kind = classify(files)
    bounds = check_paths(files, collection=kind["collection"])
    errors, parsed, graph = kind["errors"] + bounds["errors"], {}, {}
    def issue(path, code, detail=None):
        errors.append({"path": path, "code": code, **({"detail": detail} if detail else {})})
    if "." not in roots or len(set(roots)) != len(roots):
        issue("SKILL.md", "explicit_roots")
    root_prefixes = ["" if r == "." else relative(r) + "/" for r in roots]
    for prefix in root_prefixes:
        for folder in ("references", "assets", "scripts", "evals"):
            if not any(p.startswith(prefix + folder + "/") for p in files):
                issue(prefix + folder, "missing_root_folder")
        if prefix + "SKILL.md" not in files:
            issue(prefix, "missing_entrypoint")
    folded = {}
    file_names = {p.casefold() for p in files}
    directory_spellings = {}
    maximum, references = 0, 0
    for path, data in files.items():
        relative(path)
        parts = PurePosixPath(path).parts
        owner_prefix = max((p for p in root_prefixes if path.startswith(p)), key=len, default="")
        owned = path[len(owner_prefix):].split("/")
        product_branches = {p[len(owner_prefix):].split("/")[0] for p in root_prefixes if p.startswith(owner_prefix) and p != owner_prefix}
        if len(owned) > 1 and owned[0] not in {"references", "assets", "scripts", "evals"} | product_branches:
            issue(path, "unrecognized_root_folder")
        if path.casefold() in folded:
            issue(path, "case_collision")
        folded[path.casefold()] = path
        for depth in range(1, len(parts)):
            directory = "/".join(parts[:depth])
            key = directory.casefold()
            if key in directory_spellings and directory_spellings[key] != directory:
                issue(path, "directory_case_collision")
            directory_spellings[key] = directory
            if key in file_names:
                issue(path, "file_directory_collision")
        directories = [p.casefold() for p in parts[:-1]]
        if len(set(directories)) != len(directories):
            issue(path, "repeated_ancestor")
        if re.search(r"-(?:[a-f0-9]{8,}|part-?\d+|\d+)\.md$", path):
            issue(path, "suspect_ordinal_or_hash_name")
        if len(parts) > 1 and parts[-1] == ".gitkeep" and parts[-2] in {"assets", "scripts", "evals"}:
            prefix = "/".join(parts[:-2])
            if (prefix + "/" if prefix else "") not in root_prefixes:
                issue(path, "misplaced_empty_template")
        is_reference = "references" in parts[:-1]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            if is_reference and path.endswith((".md", ".json")):
                issue(path, "invalid_utf8")
            continue
        if "\r" in text or text.startswith("\ufeff"):
            issue(path, "lf_utf8_required")
        if is_reference:
            references += 1
            count = len(text.splitlines())
            maximum = max(maximum, count)
            if count > 100:
                issue(path, "reference_line_limit", str(count))
        if path.endswith(".md") and (is_reference or PurePosixPath(path).name.casefold() == "readme.md" or path in {p + "SKILL.md" for p in root_prefixes}):
            body = text
            if PurePosixPath(path).name == "SKILL.md":
                language = "languages.md" if is_reference else "references/languages.md"
                expected_name = name if path == "SKILL.md" else PurePosixPath(path).parent.name
                errors.extend(check_entry(path, text, expected_name, language, None))
                try:
                    _, body = frontmatter(text)
                except ValueError:
                    pass
            parsed[path] = markdown.inspect(body)
            if any(h["title"].casefold() == "gotchas" for h in parsed[path]["headings"]):
                issue(path, "gotchas_section")
            for finding in parsed[path]["issues"]:
                issue(path, finding["code"], str(finding))
            if is_reference and not any(line.strip() and not line.startswith("#") for line in body.splitlines()):
                issue(path, "heading_only_fragment")
    for path, document in parsed.items():
        graph[path] = []
        for url in document["links"]:
            try:
                destination, fragment = resolve(path, url, files)
                if destination:
                    graph[path].append(destination)
                    if fragment and destination in parsed and fragment not in parsed[destination]["anchors"]:
                        issue(path, "missing_fragment", url)
            except (ValueError, TypeError) as exc:
                issue(path, "local_link", str(exc))
        if path.endswith("SKILL.md"):
            _, body = frontmatter(files[path].decode("utf-8")) if not any(e["path"] == path and e["code"] == "frontmatter_or_layout" for e in errors) else ({}, "")
            router = body.split("# Language Translations", 1)[0]
            for url in markdown.inspect(router)["links"]:
                if path in {p + "SKILL.md" for p in root_prefixes} and not url.startswith("references/"):
                    issue(path, "router_outside_references", url)
        if PurePosixPath(path).name.casefold() == "index.md":
            local = [u for u in document["links"] if not urlsplit(u).scheme]
            language = []
            for i, url in enumerate(local):
                try:
                    target, _ = resolve(path, url, files)
                    if target and files[target].decode("utf-8").lstrip().lower().startswith("# reference language"):
                        language.append(i)
                except (ValueError, UnicodeError):
                    pass  # Link errors are reported by the navigation check above.
            if language and language != [len(local) - 1]:
                issue(path, "index_language_order")
    for path in files:
        if path.endswith(".json") and "references" in PurePosixPath(path).parts:
            try:
                destinations = inspect_catalog(path, files)
                if destinations is not None:
                    graph[path] = destinations
            except (ValueError, UnicodeError, KeyError, TypeError, IndexError) as exc:
                issue(path, "catalog", str(exc))
    reachable, pending = set(), ["SKILL.md"]
    while pending:
        path = pending.pop()
        if path not in reachable:
            reachable.add(path)
            pending.extend(graph.get(path, []))
    for path in parsed:
        if "references" in PurePosixPath(path).parts and path not in reachable:
            issue(path, "unreachable_reference")
    accepted = []
    for item in dispositions:
        require(item["code"] in {"suspect_ordinal_or_hash_name", "unrendered_component_or_literal"}, "Hard requirement cannot be waived")
        require(item["path"] in files and digest(files[item["path"]]) == item["sha256"] and item.get("reason", "").strip(), "Stale or unsupported contextual disposition")
        matches = [e for e in errors if e["path"] == item["path"] and e["code"] == item["code"]]
        require(bool(matches), "Disposition does not match a current finding")
        errors = [e for e in errors if e not in matches]
        accepted.append(item)
    return {"passed": not errors, "errors": errors, "warnings": bounds["warnings"], "path_limits": bounds["limits"],
            "skill_type": "collection" if kind["collection"] else "single", "nested_skills": kind["nested_skills"],
            "contextual_dispositions": accepted, "files": len(files), "reference_files": references,
            "line_limit": 100, "longest_reference": maximum, "digest": tree_digest(files),
            "not_proven": ["semantic organization", "source fidelity without mappings", "runtime behavior", "activation quality"]}


def verify(root, roots=(".",)):
    from .layout import check_empty_directories
    report = verify_files(tree(root), root.name, roots)
    report["errors"].extend(check_empty_directories(root, roots, report["warnings"]))
    report["passed"] = not report["errors"]
    return report
