"""Disposable test roots are supplied explicitly; no system temp or workspace discovery."""
import os
import sys
import uuid
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACKAGE / "scripts"))
from drafting.render import render
from drafting.storage import save, write_tree
from drafting.preparation import prepare


def workspace():
    root = Path(os.environ["SKILL_DRAFTING_TEST_ROOT"]).resolve() / uuid.uuid4().hex
    root.mkdir(parents=True)
    return root


def spec(name="example-skill", content="Read the documented setup before using the API."):
    return {"schema_version": 1, "skills": [{"root": ".", "frontmatter": {"name": name, "description": "Use when configuring the example service and its API.", "metadata": {"last-updated": "2026-10-15"}}, "official_source": "https://example.org/docs", "topics": [{"topic": "Service setup", "file": "references/service-setup.md", "summary": "Open when configuring the example service.", "keywords": ["service setup"], "content": content}]}]}


def decisions(before, after):
    sources = {}
    for path, data in before.items():
        if path in after and data == after[path]:
            sources[path] = {"action": "preserve", "outputs": [path], "reason": "Same reviewed bytes."}
        else:
            sources[path] = {"action": "rewrite", "outputs": [path], "reason": "Reviewed fixture prose repair.", "reviewed_ranges": [[1, len(data.decode().splitlines())]], "code": "preserve"}
    covered = {p for record in sources.values() for p in record["outputs"]}
    return {"schema_version": 1, "name": "example-skill", "roots": ["."], "sources": sources, "created": {p: "Explicit test package output." for p in after if p not in covered}, "reviews": {"organization": "One coherent setup topic.", "source_fidelity": "Fixture bytes inspected.", "behavior": "Text fixture; no external application execution."}}


def prepared(before=None, after=None):
    root = workspace()
    if after is None:
        after, _ = render(spec())
    before = {} if before is None else before
    write_tree(root / "live", before)
    write_tree(root / "proposal", after)
    (root / "requirements.md").write_text("Frozen fixture requirements.\n", encoding="utf-8")
    save(root / "decisions.json", decisions(before, after))
    prepare(root / "live", root / "proposal", root / "work", root / "requirements.md", root / "decisions.json")
    return root
