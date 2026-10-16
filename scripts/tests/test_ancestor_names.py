"""Reject real singular/plural nesting while preserving distinct contextual names."""
import unittest
from support import decisions, spec, workspace
from drafting.ancestor_names import equivalent
from drafting.path_limits import check_paths
from drafting.preparation import prepare
from drafting.render import render, render_to
from drafting.storage import digest, save, write_tree
from drafting.validation import verify, verify_files


class AncestorNames(unittest.TestCase):
    def findings(self, path, *, directory=False):
        result = check_paths(directories=[path]) if directory else check_paths([path])
        return [e for e in result["errors"] if e["code"] == "repeated_ancestor"]

    def test_reported_python_path_and_qualified_repair(self):
        self.assertEqual(len(self.findings("references/reference/guide.md")), 1)
        self.assertEqual(self.findings("references/language/guide.md"), [])

    def test_reported_discord_and_pymeasure_directories(self):
        paths = ["references/components/reference", "references/guilds/guild",
                 "references/adapters/adapter", "references/display/inputs/input",
                 "references/experiment/listeners/listener", "references/experiment/parameters/parameter",
                 "references/experiment/workers/worker", "references/instruments/instrument"]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(len(self.findings(path, directory=True)), 1)

    def test_both_orders_case_and_separated_ancestors(self):
        for path in ("references/reference/read.md", "reference/references/read.md",
                     "References/api/REFERENCE/read.md", "references/group/grouPs/read.md"):
            with self.subTest(path=path):
                self.assertEqual(len(self.findings(path)), 1)

    def test_existing_exact_repeats_remain_failures(self):
        for path in ("references/messages/messages/read.md", "references/area/references/read.md"):
            self.assertEqual(self.findings(path)[0]["detail"]["relationship"], "exact")

    def test_regular_irregular_and_compound_inflections(self):
        for pair in (("class", "classes"), ("property", "properties"), ("box", "boxes"),
                     ("status", "statuses"), ("analysis", "analyses"), ("index", "indices"),
                     ("index", "indexes"), ("child", "children"), ("matrix", "matrices"),
                     ("vertex", "vertices"), ("datum", "data"), ("id", "ids"),
                     ("file-type", "files-types"), ("render_pass", "render_passes")):
            with self.subTest(pair=pair):
                self.assertTrue(equivalent(*pair))
                self.assertTrue(equivalent(*reversed(pair)))

    def test_no_arbitrary_suffix_stripping_or_prefix_matching(self):
        for pair in (("statu", "status"), ("analysi", "analysis"), ("clas", "class"),
                     ("new", "news"), ("serie", "series"), ("specie", "species"),
                     ("canva", "canvas"), ("io", "ios"), ("cs", "css"),
                     ("material", "materialize"), ("data", "database"),
                     ("language-reference", "references"), ("api-v1", "api-v2"),
                     ("reference", "references-es"), ("input", "integer-input")):
            with self.subTest(pair=pair):
                self.assertFalse(equivalent(*pair))
                self.assertFalse(equivalent(*reversed(pair)))

    def test_unique_directory_outcome_for_many_payload_files(self):
        result = check_paths(["references/reference/read.md", "references/reference/data.json"])
        errors = [e for e in result["errors"] if e["code"] == "repeated_ancestor"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["path"], "references/reference")
        self.assertEqual(errors[0]["detail"]["ancestor"], "references")

    def test_filenames_and_siblings_are_not_ancestor_repetition(self):
        for path in ("references/reference.md", "references/language/reference.md"):
            self.assertEqual(self.findings(path), [])
        self.assertFalse(check_paths(["assets/input/example.bin", "assets/inputs/sample.bin"])["errors"])

    def test_all_payload_types_and_collection_prefixes(self):
        for path in ("assets/asset/payload.bin", "evals/eval/case.json", "scripts/script/tool.py",
                     "product/references/components/reference/example.md"):
            files, _ = render(spec())
            files[path] = b"\xff"
            self.assertIn("repeated_ancestor", {e["code"] for e in verify_files(files, "example-skill")["errors"]})
        self.assertIn("repeated_ancestor", {e["code"] for e in check_paths(
            ["product/references/reference/read.md"], collection=True)["errors"]})

    def test_empty_and_interior_directories(self):
        root = workspace() / "example-skill"
        files, _ = render(spec())
        write_tree(root, files)
        (root / "references" / "reference" / "language").mkdir(parents=True)
        result = verify(root)
        errors = [e for e in result["errors"] if e["code"] == "repeated_ancestor"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["path"], "references/reference")

    def test_repetition_is_unwaivable(self):
        files, _ = render(spec())
        path = "references/reference/example.md"
        files[path] = b"# Example\n\nSubject.\n"
        disposition = {"path": path, "code": "repeated_ancestor", "sha256": digest(files[path]),
                       "reason": "Attempt to preserve redundant nesting."}
        with self.assertRaisesRegex(ValueError, "cannot be waived"):
            verify_files(files, "example-skill", dispositions=[disposition])

    def test_render_refuses_before_output(self):
        value = spec()
        value["skills"][0]["topics"][0]["file"] = "references/reference/example.md"
        output = workspace() / "proposal"
        with self.assertRaisesRegex(ValueError, "repeated_ancestor"):
            render_to(value, output)
        self.assertFalse(output.exists())

    def test_prepare_refuses_before_snapshot(self):
        root = workspace()
        before, _ = render(spec())
        after = dict(before, **{"assets/asset/example.bin": b"\xff"})
        write_tree(root / "live", before)
        write_tree(root / "proposal", after)
        save(root / "decisions.json", decisions(before, after))
        (root / "requirements.md").write_text("No redundant nesting.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "repeated_ancestor"):
            prepare(root / "live", root / "proposal", root / "work", root / "requirements.md", root / "decisions.json")
        self.assertFalse((root / "work").exists())
