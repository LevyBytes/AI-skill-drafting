"""Collection declarations must match actual valid nested skills."""
import copy
import unittest
import yaml
from support import spec, workspace
from drafting.classification import classify
from drafting.format import frontmatter
from drafting.render import render, render_to
from drafting.storage import write_tree
from drafting.validation import verify, verify_files


def collection_spec():
    value = spec()
    value["skills"][0]["frontmatter"]["metadata"]["skill-type"] = "collection"
    product = copy.deepcopy(spec("product-one")["skills"][0])
    product["root"] = "product-one"
    value["skills"].append(product)
    value["skills"][0]["products"] = [
        {"root": "product-one", "label": "Product", "summary": "Open when using the product."}]
    return value


def set_marker(files, value):
    header, body = frontmatter(files["SKILL.md"].decode())
    if value is None:
        header["metadata"].pop("skill-type", None)
    else:
        header["metadata"]["skill-type"] = value
    files["SKILL.md"] = ("---\n" + yaml.safe_dump(header, sort_keys=False) + "---\n" + body).encode()


class Classification(unittest.TestCase):
    def test_single_four_level_boundary(self):
        for depth in (3, 4, 5):
            files, _ = render(spec())
            path = "/".join(["assets"] + ["area" + chr(97 + i) for i in range(depth - 1)])
            files[path + "/payload.bin"] = b"\xff"
            result = verify_files(files, "example-skill")
            self.assertEqual(result["passed"], depth <= 4)
            self.assertEqual(result["skill_type"], "single")
            self.assertEqual(result["path_limits"]["directory_depth"]["hard"], 4)

    def test_collection_six_level_boundary(self):
        for depth in (5, 6, 7):
            files, roots = render(collection_spec())
            path = "/".join(["product-one", "assets"] + ["area" + chr(97 + i) for i in range(depth - 2)])
            files[path + "/payload.bin"] = b"\xff"
            result = verify_files(files, "example-skill", roots)
            self.assertEqual(result["passed"], depth <= 6)
            self.assertEqual(result["skill_type"], "collection")
            self.assertEqual(result["nested_skills"], ["product-one/SKILL.md"])

    def test_missing_marker_is_not_inferred(self):
        files, roots = render(collection_spec())
        set_marker(files, None)
        result = verify_files(files, "example-skill", roots)
        self.assertIn("collection_declaration_missing", {e["code"] for e in result["errors"]})
        self.assertEqual(result["skill_type"], "single")

    def test_marker_without_members_does_not_grant_depth(self):
        files, _ = render(spec())
        set_marker(files, "collection")
        files["assets/one/two/three/four/payload.bin"] = b"\xff"
        result = verify_files(files, "example-skill")
        self.assertTrue({"collection_members_missing", "directory_depth_limit"} <= {e["code"] for e in result["errors"]})

    def test_bad_marker_values(self):
        for marker in (True, False, "Collection", "single", "", ["collection"]):
            files, _ = render(spec())
            set_marker(files, marker)
            result = verify_files(files, "example-skill")
            self.assertIn("skill_type_metadata", {e["code"] for e in result["errors"]})
            self.assertFalse(result["passed"])

    def test_malformed_nested_entry_does_not_grant_depth(self):
        files, roots = render(collection_spec())
        files["product-one/SKILL.md"] = b"---\nname: [\n---\n"
        result = verify_files(files, "example-skill", roots)
        self.assertTrue({"invalid_nested_skill", "collection_members_missing"} <= {e["code"] for e in result["errors"]})
        self.assertEqual(result["path_limits"]["directory_depth"]["hard"], 4)

    def test_any_invalid_member_prevents_depth_allowance(self):
        files, roots = render(collection_spec())
        files["references/broken/SKILL.md"] = b"# Missing frontmatter\n"
        self.assertFalse(classify(files)["collection"])
        self.assertIn("invalid_nested_skill", {e["code"] for e in classify(files)["errors"]})

    def test_nested_name_must_match_directory(self):
        files, roots = render(collection_spec())
        files["product-one/SKILL.md"] = files["product-one/SKILL.md"].replace(b"name: product-one", b"name: different-product")
        self.assertFalse(classify(files)["collection"])

    def test_reference_area_members_are_recognized(self):
        files, _ = render(collection_spec())
        child = files.pop("product-one/SKILL.md")
        files["references/product-one/SKILL.md"] = child.replace(b"(references/languages.md)", b"(languages.md)")
        self.assertTrue(classify(files)["collection"])

    def test_roots_option_cannot_grant_depth(self):
        files, _ = render(spec())
        files["assets/one/two/three/four/payload.bin"] = b"\xff"
        result = verify_files(files, "example-skill", (".", "undeclared"))
        self.assertIn("directory_depth_limit", {e["code"] for e in result["errors"]})

    def test_empty_directory_depth_uses_validated_kind(self):
        for collection, allowed, rejected in ((False, 4, 5), (True, 6, 7)):
            files, roots = render(collection_spec() if collection else spec())
            root = workspace() / "example-skill"
            write_tree(root, files)
            path = root / "assets"
            for i in range(allowed - 1):
                path /= "area" + chr(97 + i)
            path.mkdir(parents=True)
            self.assertTrue(verify(root, roots)["passed"])
            (path / "extra").mkdir()
            result = verify(root, roots)
            self.assertIn("directory_depth_limit", {e["code"] for e in result["errors"]})

    def test_render_requires_collection_metadata_before_output(self):
        value = collection_spec()
        value["skills"][0]["frontmatter"]["metadata"].pop("skill-type")
        output = workspace() / "proposal"
        with self.assertRaisesRegex(ValueError, "collection_declaration_missing"):
            render_to(value, output)
        self.assertFalse(output.exists())
