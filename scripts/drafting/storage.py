"""Explicit paths, exact inventories and atomic work records."""
import hashlib
import json
import os
import time
from pathlib import Path, PurePosixPath, PureWindowsPath


class Refusal(ValueError):
    """A precondition failed; no dependent mutation is allowed."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=pairs)


def read_json(path):
    return loads(safe_root(path).read_text(encoding="utf-8"))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic(path, data):
    path = safe_root(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    require(not temporary.exists(), f"Unresolved interrupted write: {temporary}")
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(7):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if attempt == 6:
                raise
            time.sleep(0.01 * 2 ** attempt)


def save(path, value):
    atomic(path, encoded(value))


def relative(value):
    require(isinstance(value, str) and bool(value), "Expected a nonempty relative path")
    path = PurePosixPath(value)
    require(str(path) == value and value != "." and not path.is_absolute(), f"Noncanonical path: {value}")
    require("\\" not in value and not any(p.casefold() in {"..", ".git"} for p in path.parts), f"Unsafe path: {value}")
    for part in path.parts:
        require(not any(ord(c) < 32 for c in part), f"Control character in path: {value!r}")
        require(not PureWindowsPath(part).is_reserved() and not any(c in part for c in '<>:"|?*'), f"Nonportable path: {value}")
        require(not part.endswith((" ", ".")), f"Nonportable path: {value}")
    return value


def safe_root(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        require(not parent.is_symlink() and not parent.is_junction(), f"Filesystem link: {parent}")
    return path.resolve()


def target(root, name):
    relative(name)
    root = safe_root(root)
    path = safe_root(root / name)
    require(path.is_relative_to(root) and path != root, f"Outside target root: {name}")
    return path


def disjoint(*paths):
    roots = [safe_root(p) for p in paths if p is not None]
    for i, left in enumerate(roots):
        for right in roots[i + 1:]:
            require(not left.is_relative_to(right) and not right.is_relative_to(left), f"Overlapping roots: {left}, {right}")


def tree(root):
    root = safe_root(root)
    require(root.is_dir(), f"Missing directory: {root}")
    result = {}
    for folder, directories, files in os.walk(root):
        directories[:] = sorted(d for d in directories if d != ".git")
        for name in directories + files:
            safe_root(Path(folder) / name)
        for name in sorted(files):
            if name == ".git":
                continue
            path = Path(folder) / name
            require(path.is_file(), f"Not a regular file: {path}")
            rel = path.relative_to(root).as_posix()
            relative(rel)
            result[rel] = path.read_bytes()
    require(len({p.casefold() for p in result}) == len(result), "Case-insensitive path collision")
    return result


def inventory(files):
    return {p: digest(b) for p, b in sorted(files.items())}


def tree_digest(files):
    return digest(encoded(inventory(files)))


def write_tree(root, files):
    root = safe_root(root)
    require(not root.exists(), f"Output already exists: {root}")
    root.mkdir(parents=True)
    for name, data in sorted(files.items()):
        atomic(target(root, name), data)


def git_state(root):
    root = safe_root(root) / ".git"
    if not root.exists():
        return None
    safe_root(root)
    if root.is_file():
        return digest(root.read_bytes())
    return inventory(tree(root))
