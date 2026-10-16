"""Regression checks for optional parser coordinates and malformed inputs."""
import unittest
from unittest.mock import patch
from markdown_it.token import Token
from support import spec
from drafting.catalogs import check
from drafting.format import frontmatter
from drafting.markdown import inspect
from drafting.render import render
from drafting.storage import Refusal


class ParserGuards(unittest.TestCase):
    def test_missing_frontmatter_is_a_typed_refusal(self):
        with self.assertRaisesRegex(Refusal, "Missing frontmatter delimiters"):
            frontmatter("# Missing YAML\n")

    def test_catalog_topics_must_be_a_nonempty_list(self):
        files, _ = render(spec())
        for value in [None, [], {}, "text", 42]:
            with self.subTest(value=value), self.assertRaisesRegex(Refusal, "nonempty array"):
                check("references/topics.json", {"schema_version": 1, "topics": value}, files)

    def test_missing_or_invalid_token_coordinates_are_findings(self):
        for kind, tag in [("heading_open", "h1"), ("fence", "code")]:
            for location in [None, [-1, 1], [0, 100], [1, 1]]:
                token = Token(kind, tag, 1 if kind == "heading_open" else 0)
                token.map = location
                token.markup = "```"
                with self.subTest(kind=kind, location=location):
                    with patch("drafting.markdown.PARSER.parse", return_value=[token]):
                        result = inspect("content\n")
                    self.assertEqual(result["issues"], [{"code": "invalid_source_position", "kind": kind}])
