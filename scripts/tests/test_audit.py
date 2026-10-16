"""Regressions for findings reproduced during the owner-requested audit."""
import json
import unittest
from pathlib import Path
from support import PACKAGE, decisions, prepared, spec, workspace
from drafting.decisions import check
from drafting.markdown import inspect
from drafting.render import render
from drafting.storage import encoded, tree, write_tree
from drafting.transactions import apply, transition
from drafting.validation import verify_files


class Audit(unittest.TestCase):
    def setUp(self):
        self.files, _ = render(spec())

    def codes(self):
        return {e["code"] for e in verify_files(self.files, "example-skill")["errors"]}

    def test_malformed_yaml_reports_finding(self):
        self.files["SKILL.md"] = b"---\nname: [\n---\n# Context Router\n"
        self.assertIn("frontmatter_or_layout", self.codes())

    def test_malformed_catalog_types_report_findings(self):
        for value in (None, [], "text", {"schema_version": 1, "owner": ".", "topics": [None]}):
            self.files["references/topics.json"] = encoded(value)
            self.assertIn("catalog", self.codes())
        self.files, _ = render(spec())
        value = json.loads(self.files["references/topics.json"])
        for field in ("summary", "topic", "file"):
            damaged = json.loads(json.dumps(value))
            damaged["topics"][0][field] = []
            self.files["references/topics.json"] = encoded(damaged)
            self.assertIn("catalog", self.codes())

    def test_single_opening_fence(self):
        for marker in ("```", "~~~"):
            self.assertEqual(inspect(marker + "\n")["issues"][0]["code"], "unclosed_fence")
            self.assertEqual(inspect(marker + "\n" + marker + "\n")["issues"], [])

    def test_root_placeholder_does_not_crash(self):
        self.files[".gitkeep"] = b""
        self.assertEqual(self.codes(), set())

    def test_readme_links_and_fragments(self):
        self.files["README.md"] = b"# Guide\n\n[Missing](missing.md)\n"
        self.assertIn("local_link", self.codes())
        self.files["README.md"] = b"# Guide\n\n[Missing](references/service-setup.md#absent)\n"
        self.assertIn("missing_fragment", self.codes())
        self.files["README.md"] = b"# Guide\n\n[Setup](references/service-setup.md#service-setup)\n"
        self.assertEqual(self.codes(), set())

    def test_uppercase_index_language_order(self):
        self.files["references/INDEX.md"] = b"# Index\n\n[Languages](languages.md)\n[Setup](service-setup.md)\n"
        self.assertIn("index_language_order", self.codes())

    def test_license_and_notice_preservation(self):
        for path in ("LICENSE", "NOTICE.txt", "product/COPYING"):
            before = {path: b"Original notice\n"}
            record = decisions({}, {})
            record["sources"] = {path: {"action": "exclude", "outputs": [], "reason": "Omit"}}
            with self.assertRaisesRegex(ValueError, "license/notice"):
                check(before, {}, record, {})
            check(before, before, decisions(before, before), {})

    def test_missing_journal_newline_refuses_before_write(self):
        root = prepared()
        with self.assertRaises(RuntimeError):
            apply(root / "work", stop_after=1)
        event = root / "work/apply.jsonl"
        event.write_bytes(event.read_bytes().rstrip(b"\n"))
        before = tree(root / "work/candidate/example-skill")
        with self.assertRaisesRegex(ValueError, "Incomplete journal"):
            apply(root / "work")
        self.assertEqual(before, tree(root / "work/candidate/example-skill"))

    def test_file_directory_conflict_refuses_before_other_edits(self):
        root = workspace()
        before = {"a.txt": b"old", "topic/guide.md": b"guide"}
        after = {"a.txt": b"new", "topic": b"file"}
        write_tree(root / "live", before)
        with self.assertRaisesRegex(ValueError, "separate reviewed revision"):
            transition(root / "live", before, after, root / "outcomes.json")
        self.assertEqual(tree(root / "live"), before)
        self.assertFalse((root / "outcomes.json").exists())

    def test_agent_evaluation_cases_are_complete(self):
        document = json.loads((PACKAGE / "evals/evals.json").read_text("utf-8"))
        self.assertEqual(document["skill_name"], "skill-drafting")
        self.assertEqual(len(document["evals"]), 3)
        self.assertEqual(len({c["id"] for c in document["evals"]}), 3)
        for case in document["evals"]:
            self.assertTrue(case["prompt"].strip() and case["expected_output"].strip())
            self.assertGreaterEqual(len(case["assertions"]), 5)
            for name in case["files"]:
                path = (PACKAGE / name).resolve()
                self.assertTrue(path.is_relative_to(PACKAGE) and path.is_file())
                json.loads(path.read_text("utf-8"))
        self.assertFalse(list((PACKAGE / "evals").rglob("*.py")))
        self.assertFalse((PACKAGE / "evals/fixtures").exists())

    def test_empty_template_directories_without_gitkeep(self):
        from drafting.validation import verify
        root = workspace() / "example-skill"
        write_tree(root, self.files)
        (root / "references/api/assets").mkdir(parents=True)
        (root / "references/api/references").mkdir()
        codes = {e["code"] for e in verify(root)["errors"]}
        self.assertTrue({"misplaced_empty_template", "repeated_ancestor"} <= codes)

    def test_catalog_owner_optional_and_keywords_not_fixed(self):
        value = json.loads(self.files["references/topics.json"])
        value.pop("owner")
        value["topics"][-1]["keywords"] = ["reference translations", "language preference"]
        self.files["references/topics.json"] = encoded(value)
        self.assertEqual(self.codes(), set())
