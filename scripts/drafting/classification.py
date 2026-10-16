"""Validate the owner's collection declaration against bundled skill entrypoints."""
from pathlib import PurePosixPath
from .format import check_entry, frontmatter


def declaration(data):
    try:
        header, _ = frontmatter(data.decode("utf-8"))
    except (ValueError, UnicodeError):
        return None
    metadata = header.get("metadata", {})
    return metadata.get("skill-type") if isinstance(metadata, dict) else None


def classify(files):
    declared = declaration(files.get("SKILL.md", b""))
    errors, valid = [], []
    nested = [p for p in files if p != "SKILL.md" and PurePosixPath(p).name == "SKILL.md"]
    if declared is not None and declared != "collection":
        errors.append({"path": "SKILL.md", "code": "skill_type_metadata",
                       "detail": "Use string metadata.skill-type: collection, or omit it for a single skill."})
    for path in nested:
        language = "languages.md" if "references" in PurePosixPath(path).parts[:-1] else "references/languages.md"
        try:
            findings = check_entry(path, files[path].decode("utf-8"),
                                   PurePosixPath(path).parent.name, language, None)
        except UnicodeError:
            findings = [{"code": "invalid_utf8"}]
        if findings:
            errors.append({"path": path, "code": "invalid_nested_skill", "detail": findings})
        else:
            valid.append(path)
    if nested and declared is None:
        errors.append({"path": "SKILL.md", "code": "collection_declaration_missing"})
    if declared == "collection" and not valid:
        errors.append({"path": "SKILL.md", "code": "collection_members_missing"})
    collection = declared == "collection" and bool(valid) and len(valid) == len(nested)
    return {"collection": collection, "nested_skills": valid, "errors": errors}
