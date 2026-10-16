"""Regression controls for catalogs whose filenames do not contain topics."""
import copy
import unittest
from support import spec
from drafting.render import render
from drafting.storage import encoded, loads, Refusal
from drafting.validation import verify_files
from drafting.catalogs import resolve


class CatalogRoutes(unittest.TestCase):
    def setUp(self):
        self.files, _ = render(spec())
        self.catalog = loads(self.files["references/topics.json"].decode())
        self.files["references/context-setup.json"] = encoded(self.catalog)
        self.files["references/service-setup.md"] += b"\n[Setup catalog](context-setup.json).\n"

    def errors(self):
        return verify_files(self.files, "example-skill")["errors"]

    def test_arbitrary_catalog_name_valid(self):
        self.assertEqual(self.errors(), [])

    def test_arbitrary_catalog_missing_target(self):
        self.catalog["topics"][0]["file"] = "references/absent.md"
        self.files["references/context-setup.json"] = encoded(self.catalog)
        self.assertTrue(any(e["code"] == "catalog" for e in self.errors()))

    def test_renamed_destination_stale_route(self):
        self.files["references/renamed.md"] = self.files.pop("references/service-setup.md")
        self.assertTrue(any(e["code"] == "catalog" for e in self.errors()))

    def test_catalog_only_reference_reachable(self):
        self.files["references/catalog-only.md"] = b"# Catalog only\n\nUseful service details.\n"
        self.catalog["topics"].insert(0, {"topic":"Service details", "file":"references/catalog-only.md",
            "summary":"Open when configuring service details.", "keywords":[]})
        self.files["references/context-setup.json"] = encoded(self.catalog)
        self.assertEqual(self.errors(), [])

    def test_ordinary_json_not_a_catalog(self):
        self.files["references/example.json"] = b'{"enabled":true}'
        self.assertEqual(self.errors(), [])

    def test_ambiguous_owner_resolution(self):
        files = {"SKILL.md":b"", "references/a.md":b"", "references/area/a.md":b""}
        with self.assertRaises(Refusal):
            resolve("references/area/catalog.json", "a.md", files)
        self.assertEqual(resolve("references/area/catalog.json", "a.md", files, "references/area"),
                         "references/area/a.md")

    def test_nested_owner_cannot_escape(self):
        files = {"SKILL.md":b"", "product/SKILL.md":b"", "references/a.md":b""}
        with self.assertRaises(Refusal):
            resolve("product/references/catalog.json", "../../references/a.md", files)

    def test_api_languages_property_is_not_selector(self):
        self.files["references/languages.md"] = b"# languages\n\nAvailable spelling dictionaries.\n"
        self.assertTrue(any(e["code"] == "catalog" for e in self.errors()))

    def test_duplicate_and_malformed_catalog_rejected(self):
        for raw in (b'{"topics":[],"topics":[]}', b'{"topics": broken}'):
            self.files["references/context-setup.json"] = raw
            self.assertTrue(any(e["code"] == "catalog" for e in self.errors()))

    def test_api_languages_in_index_is_not_a_selector(self):
        self.files["references/api/languages.md"] = b"# languages\n\nAvailable spelling dictionaries.\n"
        self.files["references/INDEX.md"] = b"# Service contexts\n\n[API language property](api/languages.md).\n[Setup](service-setup.md).\n[Reference Language Selection](languages.md).\n"
        self.files["references/service-setup.md"] += b"\n[Context index](INDEX.md).\n"
        self.assertEqual(self.errors(), [])

    def test_real_language_selector_still_must_be_last(self):
        self.files["references/INDEX.md"] = b"# Service contexts\n\n[Reference Language Selection](languages.md).\n[Setup](service-setup.md).\n"
        self.files["references/service-setup.md"] += b"\n[Context index](INDEX.md).\n"
        self.assertTrue(any(e["code"] == "index_language_order" for e in self.errors()))
