import copy
import json
import os
import subprocess
import sys
import unittest
from support import PACKAGE, decisions, spec, workspace
from drafting.render import render
from drafting.storage import encoded, save, tree, write_tree


class CLI(unittest.TestCase):
    def invoke(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(PACKAGE / "scripts/skill_builder.py"), *map(str, args)], capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def workflow(self, specification, before=None, extra_files=None):
        root = workspace()
        save(root / "spec.json", specification)
        self.invoke("render", "--spec", root / "spec.json", "--output", root / "example-skill")
        proposal = tree(root / "example-skill")
        if extra_files:
            for path, data in extra_files.items():
                destination = root / "example-skill" / path
                destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(data)
            proposal = tree(root / "example-skill")
        write_tree(root / "live", before or {})
        (root / "requirements.md").write_bytes(b"Fixture owner profile; stage before approval.\n")
        record = decisions(before or {}, proposal)
        record["roots"] = [m["root"] for m in specification["skills"]]
        save(root / "decisions.json", record)
        self.invoke("inspect", "--input", root / "example-skill")
        self.invoke("verify", "--input", root / "example-skill", "--roots", *record["roots"])
        self.invoke("prepare", "--input", root / "live", "--proposal", root / "example-skill", "--work", root / "work", "--requirements", root / "requirements.md", "--decisions", root / "decisions.json")
        self.invoke("status", "--work", root / "work")
        report = self.invoke("apply", "--work", root / "work")
        self.assertEqual(tree(root / "live"), before or {})
        self.invoke("deploy", "--work", root / "work", "--destination", root / "live", "--approved-digest", report["digest"], "--authorization", "Disposable fixture approval")
        self.assertEqual(tree(root / "live"), proposal)
        self.invoke("rollback", "--work", root / "work", "--authorization", "Disposable fixture rollback")
        self.assertEqual(tree(root / "live"), before or {})

    def test_fresh_skill(self):
        self.workflow(spec())

    def test_repair_skill(self):
        before, _ = render(spec(content="Prior prose to improve."))
        self.workflow(spec(content="Reviewed replacement prose."), before)

    def test_multi_product_skill(self):
        value = spec()
        value["skills"][0]["frontmatter"]["metadata"]["skill-type"] = "collection"
        product = copy.deepcopy(spec("product-one")["skills"][0]); product["root"] = "product-one"
        value["skills"].append(product)
        value["skills"][0]["products"] = [{"root": "product-one", "label": "Product one", "summary": "Open when using product one."}]
        self.workflow(value)

    def test_large_corpus_workflow(self):
        # Synthetic coherent areas stress routing/application; real inventory bytes are also carried unchanged.
        extra = {}
        area_links = []
        for area in ("calls", "events", "settings", "types", "methods", "fields", "responses", "requests", "errors", "examples"):
            entries = []
            for ordinal in range(90):
                # Alphabetic fixture identifiers are intentional data, not an authoring naming algorithm.
                identifier = chr(97 + ordinal // 26) + chr(97 + ordinal % 26)
                path = f"references/{area}/contract-{identifier}.md"
                extra[path] = f"# {area} contract {identifier}\n\nComplete synthetic fixture contract.\n".encode()
                entries.append(f"[{identifier}](contract-{identifier}.md)")
            extra[f"references/{area}/index.md"] = ("# Contract index\n\n" + "\n".join(entries) + "\n").encode()
            area_links.append(f"- [{area}]({area}/index.md)")
        extra["references/service-setup.md"] = ("# Service setup\n\n" + "\n".join(area_links) + "\n").encode()
        extra["assets/recorded-inventory.json.gz"] = (PACKAGE / "scripts/tests/fixtures/adobe-inventory.json.gz").read_bytes()
        self.workflow(spec(), extra_files=extra)

    def test_invalid_json_exit(self):
        root = workspace(); (root / "bad.json").write_bytes(b"invalid json")
        result = self.invoke("render", "--spec", root / "bad.json", "--output", root / "out", expected=2)
        self.assertFalse(result["passed"])
        self.assertFalse((root / "out").exists())
