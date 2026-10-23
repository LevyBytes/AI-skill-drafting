import json
import unittest
from support import PACKAGE
from drafting.storage import relative


class SessionRegressions(unittest.TestCase):
    def test_large_inventory_paths(self):
        # A generated tree at the scale of a large product collection: 30 products of 3,050 files each.
        paths = [f"product-{p:02d}/references/topic-{t:03d}/page-{n:02d}.md"
                 for p in range(30) for t in range(122) for n in range(25)]
        self.assertGreater(len(paths), 90000)
        self.assertEqual(len({p.casefold() for p in paths}), len(paths))
        for path in paths:
            self.assertEqual(relative(path), path)

    def test_activation_case_contract(self):
        cases = json.loads((PACKAGE / "evals/activation-cases.json").read_text("utf-8"))
        self.assertTrue(any(not c["should_activate"] for c in cases))
        self.assertTrue(any(c["should_activate"] for c in cases))
        for case in cases:
            if case["reference"]:
                self.assertTrue((PACKAGE / case["reference"]).is_file())
