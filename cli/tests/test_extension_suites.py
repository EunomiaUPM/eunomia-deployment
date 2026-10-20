"""Run the unit tests of every built-in extension (extensions/*/tests/) with the core ones."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli"))


def load_tests(loader, standard_tests, pattern):
    for tests in sorted((ROOT / "extensions").glob("*/tests")):
        standard_tests.addTests(loader.discover(str(tests), pattern="test_*.py", top_level_dir=str(tests)))
    return standard_tests
