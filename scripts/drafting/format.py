"""Validate public frontmatter and the owner's explicitly selected package layout."""
import datetime
import re
import yaml
from .storage import Refusal, require

SECTIONS = ["Context Router", "Language Translations", "Context For Open Source"]
DISCLAIMER = "Skill reference documentation is interpreted content for use in open source projects. Check against [official documentation sources]({url}) when dealing with defects or issues that may come up from interpreting this skill's references."


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    pairs = loader.construct_pairs(node, deep=deep)
    out = {}
    for key, value in pairs:
        require(isinstance(key, str), "YAML mapping keys must be strings")
        require(key not in out, f"Duplicate YAML key: {key}")
        out[key] = value
    return out


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    if match is None:
        raise Refusal("Missing frontmatter delimiters")
    try:
        data = yaml.load(match[1], Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise Refusal("Invalid YAML frontmatter: " + str(exc)) from exc
    require(isinstance(data, dict), "Frontmatter must be a mapping")
    return data, text[match.end():]


def check_entry(path, text, name, language_path, parsed):
    errors = []
    def check(ok, code):
        if not ok:
            errors.append({"path": path, "code": code})
    try:
        data, body = frontmatter(text)
        check(not set(data) - {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}, "unsupported_frontmatter")
        actual = data.get("name", "")
        check(isinstance(actual, str) and bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", actual)) and len(actual) <= 64 and actual == name, "skill_name")
        description = data.get("description", "")
        check(isinstance(description, str) and 0 < len(description) < 1024 and description.startswith("Use "), "trigger_description")
        for key in {"license", "compatibility", "allowed-tools"} & set(data):
            check(isinstance(data[key], str) and bool(data[key].strip()), "frontmatter_string:" + key)
        if "compatibility" in data and isinstance(data["compatibility"], str):
            check(len(data["compatibility"]) <= 500, "compatibility_length")
        metadata = data.get("metadata", {})
        check(isinstance(metadata, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()), "metadata_strings")
        check(isinstance(metadata, dict) and "covers" not in metadata, "retired_metadata")
        date = metadata.get("last-updated") if isinstance(metadata, dict) else None
        check(isinstance(date, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)), "quoted_utc_date")
        if isinstance(date, str):
            datetime.date.fromisoformat(date)
        from .markdown import inspect
        headings = inspect(body)["headings"]
        check(body.lstrip().startswith("# Context Router\n"), "entrypoint_first_section")
        check([(h["level"], h["title"]) for h in headings] == [(1, s) for s in SECTIONS], "entrypoint_sections")
        if all("# " + section + "\n" in body for section in SECTIONS):
            router, rest = body.split("# Language Translations\n", 1)
            language, footer = rest.split("# Context For Open Source\n", 1)
            check(language.strip() == f"[Reference Language Selection]({language_path})", "language_section")
            check(not re.search(r"languages\.md|non-English|Language Translations", router), "duplicate_language_route")
            pattern = re.escape(DISCLAIMER).replace(re.escape("{url}"), r"https?://[^)\s]+")
            check(bool(re.fullmatch(pattern, footer.strip())), "source_disclaimer")
    except (ValueError, TypeError, yaml.YAMLError) as exc:
        errors.append({"path": path, "code": "frontmatter_or_layout", "detail": str(exc)})
    return errors
