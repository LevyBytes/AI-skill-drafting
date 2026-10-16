"""Real Adobe failures and inclusive owner-profile boundary regressions."""
import json
from pathlib import Path
import unittest
from support import spec, workspace
from drafting.layout import check_empty_directories
from drafting.path_limits import check_paths
from drafting.render import render, render_to
from drafting.storage import digest, write_tree
from drafting.validation import verify, verify_files


class PathLimits(unittest.TestCase):
    def test_filename_includes_extension(self):
        for length in (47, 48, 49, 63, 64, 65):
            with self.subTest(length=length):
                path = "references/" + "x" * (length - 3) + ".md"
                result = check_paths([path])
                self.assertEqual(bool(result["errors"]), length > 64)
                self.assertEqual(bool(result["warnings"]), 48 < length <= 64)

    def test_directory_names_and_empty_folders(self):
        for length in (63, 64, 65):
            folder = "x" * length
            result = check_paths(directories=["references/" + folder])
            self.assertEqual(bool(result["errors"]), length > 64)
        root = workspace() / "example-skill"
        files, _ = render(spec())
        write_tree(root, files)
        (root / "references" / ("x" * 65)).mkdir()
        self.assertIn("directory_name_limit", {
            e["code"] for e in check_empty_directories(root, (".",))})
        self.assertFalse(verify(root)["passed"])

    def test_relative_path_includes_separators(self):
        for length in (99, 100, 101, 159, 160, 161):
            prefix = "references/" + "a" * 45 + "/" + "b" * 45 + "/"
            if length < len(prefix) + 4:
                prefix = "references/" + "a" * 40 + "/"
            path = prefix + "x" * (length - len(prefix) - 3) + ".md"
            self.assertEqual(len(path), length)
            result = check_paths([path])
            codes = {e["code"] for e in result["errors"]}
            warnings = {e["code"] for e in result["warnings"]}
            self.assertEqual("relative_path_limit" in codes, length > 160)
            self.assertEqual("relative_path_limit" in warnings, 100 < length <= 160)

    def test_depth_and_product_prefix(self):
        for depth in (3, 4, 5, 6, 7):
            path = "/".join("area" + chr(97 + i) for i in range(depth)) + "/read.md"
            result = check_paths([path], collection=True)
            self.assertEqual(bool(result["errors"]), depth > 6)
            self.assertEqual(bool(result["warnings"]), 4 < depth <= 6)
            single = check_paths([path])
            self.assertEqual(bool(single["errors"]), depth > 4)
        path = "references/" + "a" * 45 + "/" + "b" * 45 + "/" + "x" * 54 + ".md"
        self.assertEqual(len(path), 160)
        files, _ = render(spec())
        files["product/" + path] = b"# Topic\n\nContent.\n"
        result = verify_files(files, "example-skill", roots=(".", "product"))
        self.assertIn("relative_path_limit", {e["code"] for e in result["errors"]})

    def test_unicode_is_counted_as_code_points(self):
        path = "assets/" + "\U0001f680" * 60 + ".bin"
        self.assertFalse(check_paths([path])["errors"])
        self.assertGreater(len(Path(path).name.encode("utf-8")), 64)
        self.assertTrue(check_paths(["assets/" + "\U0001f680" * 61 + ".bin"])["errors"])

    def test_binary_file_and_unwaivable_failure(self):
        files, _ = render(spec())
        path = "assets/" + "x" * 61 + ".bin"
        files[path] = b"\xff\x00"
        report = verify_files(files, "example-skill")
        self.assertFalse(report["passed"])
        disposition = {"path": path, "sha256": digest(files[path]),
                       "code": "filename_limit", "reason": "Attempted waiver"}
        with self.assertRaisesRegex(ValueError, "cannot be waived"):
            verify_files(files, "example-skill", dispositions=[disposition])

    def test_targets_do_not_fail_a_valid_package(self):
        value = spec()
        value["skills"][0]["topics"][0]["file"] = "references/" + "x" * 46 + ".md"
        files, _ = render(value)
        report = verify_files(files, "example-skill")
        self.assertTrue(report["passed"])
        self.assertTrue(report["warnings"])

    def test_render_refuses_before_writing(self):
        value = spec()
        value["skills"][0]["topics"][0]["file"] = "references/" + "x" * 62 + ".md"
        target = workspace() / "proposal"
        with self.assertRaisesRegex(ValueError, "filename_limit"):
            render_to(value, target)
        self.assertFalse(target.exists())

    def test_prepare_refuses_before_snapshotting(self):
        from drafting.preparation import prepare
        from drafting.storage import save
        from support import decisions
        root = workspace()
        before, _ = render(spec())
        after = dict(before)
        after["assets/" + "x" * 61 + ".bin"] = b"\xff"
        write_tree(root / "live", before)
        write_tree(root / "proposal", after)
        save(root / "decisions.json", decisions(before, after))
        (root / "requirements.md").write_text("Owner bounds.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "filename_limit"):
            prepare(root / "live", root / "proposal", root / "work",
                    root / "requirements.md", root / "decisions.json")
        self.assertFalse((root / "work").exists())

    def test_captured_adobe_paths(self):
        fixture = Path(__file__).parent / "fixtures/path-repairs.json"
        cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 13)
        for case in cases:
            with self.subTest(path=case["before"]):
                self.assertTrue(check_paths([case["before"]], collection=True)["errors"])
                self.assertEqual(check_paths([case["after"]], collection=True)["errors"], [])

    def test_staging_prefix_does_not_spend_package_budget(self):
        files, _ = render(spec())
        root = workspace() / ("temporary-location-" * 5) / "example-skill"
        write_tree(root, files)
        self.assertTrue(verify(root)["passed"])
