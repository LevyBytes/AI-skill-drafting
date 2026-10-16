import gzip
import json
import re
import unittest
from pathlib import Path, PurePosixPath
from support import PACKAGE
from drafting.storage import relative

FIXTURES = PACKAGE / "scripts/tests/fixtures"


class SessionRegressions(unittest.TestCase):
    def test_tauri_flattened_comments(self):
        fixture = json.loads((FIXTURES / "tauri-comment-repair.json").read_text("utf-8"))
        def executable_lines(code):
            return "\n".join(line for line in code.splitlines() if not line.lstrip().startswith("//"))
        self.assertNotIn("import { invoke }", executable_lines(fixture["before"]))
        self.assertIn("import { invoke }", executable_lines(fixture["after"]))
        self.assertIn("invoke('my_custom_command')", executable_lines(fixture["after"]))

    def test_fsl_wrong_property_rejected(self):
        fixture = json.loads((FIXTURES / "fsl-sweep.json").read_text("utf-8"))
        log = []
        class Marker:
            def to_peak(self): log.append("peak")
            def zoom(self, span): log.append(span)
        class Instrument:
            __slots__ = ("continuous_sweep_enabled", "freq_span", "res_bandwidth", "video_bandwidth", "sweep_time")
            def create_marker(self): return Marker()
            def single_sweep(self): log.append("sweep")
            def read_trace(self): return [1, 2], [3, 4]
        self.assertEqual(fixture["property"], "continuous_sweep_enabled")
        self.assertEqual((fixture["query"], fixture["set"]), ("INIT:CONT?", "INIT:CONT %s"))
        scope = {"fsl": Instrument()}
        exec(compile(fixture["code"], "reviewed-fsl-example", "exec"), scope)
        self.assertEqual(log, ["sweep", "peak", "20 MHz", "sweep"])
        self.assertEqual((scope["x"], scope["y"]), ([1, 2], [3, 4]))
        self.assertIs(scope["fsl"].continuous_sweep_enabled, False)
        with self.assertRaises(AttributeError):
            exec(compile(fixture["code"].replace("continuous_sweep_enabled", "continuous_sweep"), "negative-fsl-example", "exec"), {"fsl": Instrument()})

    def test_fsl_valid_delta_default_preserved(self):
        # Execute reviewed captured methods; only transport activation is stubbed.
        import importlib.util
        spec = importlib.util.spec_from_file_location("fsl_fixture", FIXTURES / "fsl_marker.py")
        if spec is None or spec.loader is None:
            self.fail("The FSL Python fixture must have a file-backed module loader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        instrument = module.FSSeries()
        self.assertEqual(instrument.create_marker(is_delta_marker=True).name, "DELT2")
        self.assertEqual(instrument.create_marker().name, "MARK")
        self.assertEqual(instrument.create_marker(4, True).name, "DELT4")
        self.assertEqual(instrument.activations, ["DELT2", "MARK", "DELT4"])

    def test_recorded_large_inventory(self):
        value = json.loads(gzip.decompress((FIXTURES / "adobe-inventory.json.gz").read_bytes()))
        provenance = json.loads((FIXTURES / "inventory-provenance.json").read_text("utf-8"))
        self.assertEqual(len(value), provenance["files"])
        self.assertGreater(len(value), 90000)
        self.assertEqual(len({p.casefold() for p in value}), len(value))
        for path, sha in value.items():
            relative(path)
            self.assertRegex(sha, r"^[0-9a-f]{64}$")
            parts = [p.casefold() for p in PurePosixPath(path).parts[:-1]]
            self.assertEqual(len(parts), len(set(parts)), path)

    def test_activation_case_contract(self):
        cases = json.loads((PACKAGE / "evals/activation-cases.json").read_text("utf-8"))
        self.assertTrue(any(not c["should_activate"] for c in cases))
        self.assertTrue(any(c["should_activate"] for c in cases))
        for case in cases:
            if case["reference"]:
                self.assertTrue((PACKAGE / case["reference"]).is_file())
