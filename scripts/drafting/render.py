"""Render explicit author decisions through one set of actual asset templates."""
import posixpath
import json
import re
from pathlib import Path
from string import Template
import yaml
from .contracts import validate
from .storage import encoded, relative, require, write_tree
from .validation import verify_files

ASSETS = Path(__file__).resolve().parents[2] / "assets"


def template(name, **values):
    return Template((ASSETS / name).read_text(encoding="utf-8")).substitute(values)


def front_matter(front):
    """Owner front matter: name and token licenses stay plain; every other text value is one double-quoted line."""
    def scalar(key, value):
        plain = key == "name" or (key == "license" and re.fullmatch(r"[A-Za-z0-9.+-]+", value))
        return value if plain else json.dumps(value, ensure_ascii=False)
    lines = []
    for key, value in front.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {k}: {scalar(k, v)}" for k, v in value.items())
        else:
            lines.append(f"{key}: {scalar(key, value)}")
    text = "\n".join(lines)
    require(yaml.safe_load(text) == front, "Front matter does not round-trip")
    return text


def render(spec):
    validate("render", spec)
    require(spec.get("schema_version") == 1, "Unknown render schema")
    files, roots = {}, []
    def put(path, content):
        relative(path)
        require(path.casefold() not in {p.casefold() for p in files}, "Output collision: " + path)
        files[path] = content if isinstance(content, bytes) else content.encode("utf-8")
    for member in spec["skills"]:
        root = member["root"]
        prefix = "" if root == "." else relative(root) + "/"
        roots.append(root)
        front = member["frontmatter"]
        routes, entries, language_rows = [], [], []
        for item in member["topics"]:
            path = relative(item["file"])
            require(path.startswith("references/") and path.endswith(".md"), "Topic must be reference Markdown")
            require(item["summary"].startswith("Open when "), "Expected topic trigger")
            body = template("reference.md.template", title=item["topic"], content=item["content"].rstrip())
            put(prefix + path, body)
            routes.append(f'- {item["summary"]} [{item["topic"]}]({path}).')
            entries.append({k: item[k] for k in ("topic", "file", "summary", "keywords")})
        for row in member.get("translations", []):
            source, translated = relative(row["source"]), relative(row["file"])
            require(prefix + source in files and translated.startswith("references/"), "Translation source or path")
            put(prefix + translated, row["content"])
            language_rows.append(f'- {row["language"]}: [{row["label"]}]({posixpath.relpath(translated, "references")}) for `{source}`.')
        for product in member.get("products", []):
            path = relative(product["root"]) + "/SKILL.md"
            require(path.startswith(prefix) and not path.startswith(prefix + "references/"), "Product root location")
            routes.append(f'- {product["summary"]} [{product["label"]}](references/products.md).')
        if member.get("products"):
            links = [f'- {p["summary"]} [{p["label"]}]({posixpath.relpath(p["root"] + "/SKILL.md", prefix + "references")}).' for p in member["products"]]
            put(prefix + "references/products.md", "# Product selection\n\n" + "\n".join(links) + "\n")
            entries.append({"topic": "Product selection", "file": "references/products.md", "summary": "Open when selecting a bundled product skill.", "keywords": ["product selection"]})
        put(prefix + "references/languages.md", template("languages.md.template", translations="\n".join(language_rows) or "No translated references are bundled. Use the linked English topics and disclose that fallback.", english="\n".join(f'- [{e["topic"]}]({posixpath.relpath(e["file"], "references")})' for e in entries)))
        entries.append({"topic": "Reference Language Selection", "file": "references/languages.md", "summary": "Open when you need a language version of references other than English.", "keywords": ["reference language", "translated references"]})
        put(prefix + "references/topics.json", template("catalog.json.template", owner=json.dumps(root), topics=json.dumps(entries, ensure_ascii=False, indent=2)))
        put(prefix + "SKILL.md", template("entrypoint.md.template", frontmatter=front_matter(front), routes="\n".join(routes), source=member["official_source"]))
        for folder in ("assets", "scripts", "evals"):
            put(prefix + folder + "/.gitkeep", b"")
    for path, content in spec.get("files", {}).items():
        put(path, content)
    require(roots.count(".") == 1, "One main root required")
    name = next(m["frontmatter"]["name"] for m in spec["skills"] if m["root"] == ".")
    report = verify_files(files, name, roots)
    require(report["passed"], "Rendered proposal rejected: " + str(report["errors"][:12]))
    return files, roots


def render_to(spec, output):
    files, roots = render(spec)
    write_tree(output, files)
    return {"output": str(output), "files": len(files), "roots": roots}
