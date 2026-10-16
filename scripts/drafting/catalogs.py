"""Discover catalogs by structure and resolve routes inside their owning skill."""
import posixpath
from pathlib import PurePosixPath
from .storage import Refusal, require, loads, relative

LANGUAGE = "Reference Language Selection"


def owner(source, files):
    return next((str(p) for p in PurePosixPath(source).parents
                 if str(p / "SKILL.md") in files), ".")


def resolve(source, name, files, declared=None):
    require(isinstance(name, str) and bool(name), "Catalog file must be a nonempty string")
    require("\\" not in name and not name.startswith("/") and ":" not in name,
            "Catalog file must be a portable local path")
    boundary = owner(source, files)
    parents = []
    for p in PurePosixPath(source).parents:
        parents.append(str(p))
        if str(p) == boundary:
            break
    if declared is not None:
        require(isinstance(declared, str) and declared in parents,
                "Catalog owner must be its containing area or an owning ancestor")
        candidates = [posixpath.normpath(posixpath.join(declared, name))]
    else:
        candidates = [name] if boundary == "." or name.startswith(boundary + "/") else []
        candidates += [posixpath.normpath(posixpath.join(p, name)) for p in parents]
    candidates = list(dict.fromkeys(p for p in candidates if p in files and
                      not p.startswith("../") and
                      (boundary == "." or p.startswith(boundary + "/"))))
    require(len(candidates) == 1,
            f"Catalog target must resolve once inside its owner: {name}; matches={candidates}")
    relative(candidates[0])
    return candidates[0]


def check(path, value, files):
    require(isinstance(value, dict) and value.get("schema_version") == 1,
            "Catalog schema_version must be 1")
    topics = value.get("topics")
    if not isinstance(topics, list) or not topics:
        raise Refusal("Catalog topics must be a nonempty array")
    destinations = []
    for item in topics:
        require(isinstance(item, dict), "Catalog topic must be an object")
        require(all(isinstance(item.get(k), str) and item[k].strip()
                    for k in ("topic", "summary", "file")), "Catalog topic, summary and file must be strings")
        require(item["summary"].startswith("Open when "), "Catalog summary must be a trigger")
        require(isinstance(item.get("keywords"), list) and
                all(isinstance(k, str) and k.strip() for k in item["keywords"]),
                "Catalog keywords must be strings")
        destinations.append(resolve(path, item["file"], files, value.get("owner")))
    language = [i for i, item in enumerate(topics) if item["topic"] == LANGUAGE]
    require(language == [len(topics)-1], "Generic language selection must appear once, last")
    target = destinations[-1]
    require(PurePosixPath(target).name == "languages.md", "Last target must be a language selector")
    require(files[target].decode("utf-8").lstrip().lower().startswith("# reference language"),
            "Language selector must be reference-language guidance, not an API Languages property")
    return destinations


def inspect(path, files):
    value = loads(files[path].decode("utf-8"))
    if isinstance(value, dict) and "topics" in value:
        return check(path, value, files)
    require(PurePosixPath(path).name != "topics.json", "Named topics catalog has no topics")
    return None
