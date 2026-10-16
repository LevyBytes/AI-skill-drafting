"""Check empty directories that a file inventory cannot describe."""
import os
from pathlib import Path
from .storage import relative, safe_root
from .path_limits import check_paths
from .classification import classify


def check_empty_directories(root, roots, warnings=None):
    root = safe_root(root)
    entries = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name != ".git"]
        if "SKILL.md" in files:
            entry = safe_root(Path(folder) / "SKILL.md")
            entries[entry.relative_to(root).as_posix()] = entry.read_bytes()
    collection = classify(entries)["collection"]
    owners = {root if name == "." else root / relative(name) for name in roots}
    errors = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name != ".git"]
        path = safe_root(folder)
        if path == root or dirs or files:
            continue
        parts = path.relative_to(root).parts
        bounds = check_paths(directories=[path.relative_to(root).as_posix()], collection=collection)
        for finding in bounds["errors"]:
            if finding not in errors:
                errors.append(finding)
        if warnings is not None:
            warnings.extend(finding for finding in bounds["warnings"] if finding not in warnings)
        if path.name in {"assets", "scripts", "evals"} and path.parent not in owners:
            errors.append({"path": path.relative_to(root).as_posix(), "code": "misplaced_empty_template"})
        folded = [p.casefold() for p in parts]
        if len(set(folded)) != len(folded):
            errors.append({"path": path.relative_to(root).as_posix(), "code": "repeated_ancestor"})
    return errors
