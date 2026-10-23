import copy
import unittest
from pathlib import PurePosixPath, PureWindowsPath
from support import spec
from drafting import markdown
from drafting.decisions import check
from drafting.render import render
from drafting.storage import Refusal, digest, encoded, loads, relative
from drafting.validation import verify_files


class Verification(unittest.TestCase):
    def setUp(self):
        self.files, _ = render(spec())

    def codes(self, files=None, dispositions=()):
        return {e["code"] for e in verify_files(files or self.files, "example-skill", dispositions=dispositions)["errors"]}

    def test_valid(self):
        self.assertEqual(self.codes(), set())

    def test_physical_boundaries(self):
        for count in (99, 100, 101):
            with self.subTest(count=count):
                self.files["references/service-setup.md"] = ("# Setup\n" + "A line.\n" * (count - 1)).encode()
                self.assertEqual("reference_line_limit" in self.codes(), count > 100)

    def test_structure_mutations(self):
        mutations = {
            "unsupported_frontmatter": ("description:", "covers: bad\ndescription:"),
            "quoted_utc_date": ('"2026-10-15"', "2026-10-15"),
            "entrypoint_sections": ("# Context Router", "## Task routes"),
            "language_section": ("[Reference Language Selection]", "Extra instruction. [Reference Language Selection]"),
            "source_disclaimer": ("skill's references", "skill's document prose"),
            "trigger_description": ("Use when configuring", "Keywords for configuring"),
        }
        for code, (old, new) in mutations.items():
            with self.subTest(code=code):
                files = dict(self.files)
                self.assertIn(old.encode(), files["SKILL.md"])
                files["SKILL.md"] = files["SKILL.md"].replace(old.encode(), new.encode())
                self.assertIn(code, self.codes(files))

    def test_real_heading_not_fenced_heading(self):
        result = markdown.inspect("# Real\n\n````md\n# Fake\n```py\nx=1\n```\n````\n")
        self.assertEqual([h["title"] for h in result["headings"]], ["Real"])
        self.assertEqual(result["issues"], [])

    def test_fence_and_table_coordinates(self):
        result = markdown.inspect("Preamble.\n\n| API | Type |\n| --- | --- |\n| f | int |\n\n```py\nx = 1\n")
        self.assertIn("table_open", [u["kind"] for u in result["units"]])
        self.assertEqual(result["issues"][0]["code"], "unclosed_fence")
        self.assertEqual(result["units"][0]["start"], 1)

    def test_html_images_fragments_and_literals(self):
        for text, code in [('<img src="absent.png">', "local_link"), ('[jump](service-setup.md#absent)', "missing_fragment"), ('<parameter>hidden</parameter>', "unrendered_component_or_literal")]:
            self.files["references/service-setup.md"] = ("# Setup\n\n" + text + "\n").encode()
            self.assertIn(code, self.codes())
        self.files["references/service-setup.md"] = b'# Setup\n\n`<parameter>`\n\n<a id="target"></a>\n\n[Jump](#target)\n'
        self.assertEqual(self.codes(), set())

    def test_catalog_error_not_silenced(self):
        self.files["references/topics.json"] = b'{"topics": broken}'
        self.assertIn("catalog", self.codes())

    def test_language_last(self):
        value = loads(self.files["references/topics.json"].decode())
        value["topics"].reverse()
        self.files["references/topics.json"] = encoded(value)
        self.assertIn("catalog", self.codes())

    def test_paths_and_empty_templates(self):
        self.files["references/messages/messages/read.md"] = b"# Read\n\nContent.\n"
        self.files["references/api/assets/.gitkeep"] = b""
        self.files["references/read-3efac31f7f.md"] = b"# Read\n\nContent.\n"
        self.assertTrue({"repeated_ancestor", "misplaced_empty_template", "suspect_ordinal_or_hash_name", "unreachable_reference"} <= self.codes())

    def test_context_outside_root_references(self):
        self.files["scripting-api/references/commands.md"] = b"# Commands\n\nContent.\n"
        self.assertIn("unrecognized_root_folder", self.codes())

    def test_unsafe_paths(self):
        # Construct synthetic absolute inputs; no local machine path is embedded.
        posix = PurePosixPath("/") / "rejected-fixture"
        windows = PureWindowsPath("Z:", "/") / "rejected-fixture"
        self.assertTrue(posix.is_absolute() and windows.is_absolute())
        for path in ("../escape", posix.as_posix(), windows.as_posix(), "a\\b", "a/../b", "NUL", ".GIT/config", "."):
            with self.subTest(path=path), self.assertRaises(ValueError):
                relative(path)

    def test_directory_case_and_file_collisions(self):
        self.files["references/API/one.md"] = b"# One\n\nContent.\n"
        self.files["references/api/two.md"] = b"# Two\n\nContent.\n"
        self.files["references/api"] = b"collision"
        self.assertTrue({"directory_case_collision", "file_directory_collision"} <= self.codes())

    def test_description_limit(self):
        import yaml
        from drafting.format import frontmatter
        original = self.files["SKILL.md"].decode()
        data, body = frontmatter(original)
        for length in (1023, 1024):
            data["description"] = "Use " + "x" * (length - 4)
            self.files["SKILL.md"] = ("---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body).encode()
            self.assertEqual("trigger_description" in self.codes(), length == 1024)

    def test_schema_rejects_unknown_inputs(self):
        value = spec(); value["magical_autosplit"] = True
        with self.assertRaisesRegex(ValueError, "Invalid render input"):
            render(value)

    def test_duplicate_keys(self):
        with self.assertRaises(ValueError):
            loads('{"a":1,"a":2}')

    def test_contextual_disposition_is_hash_bound(self):
        path = "references/service-setup.md"
        self.files[path] = b"# Setup\n\n<widget>Subject example.</widget>\n"
        entry = {"path": path, "code": "unrendered_component_or_literal", "sha256": digest(self.files[path]), "reason": "Intended custom HTML fixture, renderer requirement reviewed."}
        self.assertEqual(self.codes(dispositions=[entry]), set())
        entry["sha256"] = "bad"
        with self.assertRaises(ValueError):
            self.codes(dispositions=[entry])

    def test_code_preservation_and_ranges(self):
        old = {"references/example.md": b"Prerequisite.\n\n```python\nimport os\nprint(os.name)\n```\n"}
        new = {"references/example.md": old["references/example.md"].replace(b"import os\n", b"")}
        from support import decisions
        record = decisions(old, new)
        with self.assertRaisesRegex(ValueError, "Protected"):
            check(old, new, record, {})
        record["sources"]["references/example.md"]["reviewed_ranges"] = [[3, 6]]
        with self.assertRaisesRegex(ValueError, "coverage"):
            check(old, new, record, {})

    def test_repair_requires_evidence(self):
        from support import decisions
        old = {"api.md": b"```py\nobj.wrong()\n```\n"}
        new = {"api.md": b"```py\nobj.correct()\n```\n"}
        record = decisions(old, new)
        record["sources"]["api.md"].update(code="repair", evidence=["source.txt"], behavior_check="Mock checks exact method; native application not run.")
        with self.assertRaisesRegex(ValueError, "captured evidence"):
            check(old, new, record, {})
        check(old, new, record, {"source.txt": b"Exact API contract evidence."})

    def test_multilingual_and_multi_product(self):
        value = spec()
        value["skills"][0]["translations"] = [{"source": "references/service-setup.md", "file": "references/es/service-setup.md", "language": "Spanish", "label": "Service setup", "content": "# Configuracion\n\nConfigure el servicio.\n"}]
        product = copy.deepcopy(spec("product-one")["skills"][0])
        value["skills"][0]["frontmatter"]["metadata"]["skill-type"] = "collection"
        product["root"] = "product-one"
        value["skills"].append(product)
        value["skills"][0]["products"] = [{"root": "product-one", "label": "Product one", "summary": "Open when using product one."}]
        files, roots = render(value)
        self.assertTrue(verify_files(files, "example-skill", roots)["passed"])

    def test_oversized_unit_refused(self):
        with self.assertRaisesRegex(ValueError, "reference_line_limit"):
            render(spec(content="```text\n" + "complete example line\n" * 140 + "```"))
