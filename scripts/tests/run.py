"""Run portable tests into an explicit new work directory, never the installed skill."""
import argparse
import json
import platform
from importlib.metadata import version
import os
import sys
import unittest
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    root = args.work.resolve()
    package = Path(__file__).resolve().parents[2]
    if root.is_relative_to(package) or package.is_relative_to(root) or root.exists():
        parser.error("Use a new test directory disjoint from the package")
    root.mkdir(parents=True)
    os.environ["SKILL_DRAFTING_TEST_ROOT"] = str(root)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"passed": result.wasSuccessful(), "tests_run": result.testsRun,
              "failures": [str(test) for test, _ in result.failures],
              "errors": [str(test) for test, _ in result.errors],
              "skipped": [(str(test), reason) for test, reason in result.skipped],
              "python": platform.python_version(),
              "dependencies": {name: version(name) for name in ("PyYAML", "markdown-it-py", "jsonschema")},
              "scope": "Portable CLI and regression fixtures; native target applications and external-model activation not run."}
    (root / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
