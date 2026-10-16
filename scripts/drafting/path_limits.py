"""Portable owner-profile bounds, measured from the whole package root."""
from pathlib import PurePosixPath
from .storage import relative

# Owner-selected values; these are not Agent Skills interchange requirements.
# Names include extensions. Paths use one "/" separator and Unicode code points.
LIMITS = {
    "filename": {"target": 48, "hard": 64},
    "directory_name": {"target": 48, "hard": 64},
    "relative_path": {"target": 100, "hard": 160},
    "directory_depth": {"target": 4, "hard": 4},
}


def check_paths(files=(), directories=(), *, collection=False):
    """Check binary/text paths and implicit or explicit directories without I/O."""
    errors, warnings = [], []
    folders = set()
    limits = {**LIMITS, "directory_depth": {"target": 4, "hard": 6 if collection else 4}}

    def measure(path, kind, value):
        bounds = limits[kind]
        finding = {"path": path, "code": kind + "_limit", "measured": value,
                   "target": bounds["target"], "hard": bounds["hard"]}
        if value > bounds["hard"]:
            errors.append(finding)
        elif value > bounds["target"]:
            warnings.append(finding)

    def ancestors(parts):
        for depth in range(1, len(parts) + 1):
            folders.add("/".join(parts[:depth]))

    for name in files:
        parts = PurePosixPath(relative(name)).parts
        measure(name, "filename", len(parts[-1]))
        measure(name, "relative_path", len(name))
        measure(name, "directory_depth", len(parts) - 1)
        ancestors(parts[:-1])
    for name in directories:
        parts = PurePosixPath(relative(name)).parts
        ancestors(parts)
        measure(name, "directory_depth", len(parts))
    for name in sorted(folders):
        measure(name, "directory_name", len(PurePosixPath(name).name))
    return {"errors": errors, "warnings": warnings, "limits": limits}
