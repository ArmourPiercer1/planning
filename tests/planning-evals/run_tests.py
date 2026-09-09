"""Zero-dependency test runner for the planning-evals test suite.

Usage:
    $env:UV_CACHE_DIR = "<workspace>/.cache/uv"   # sandbox-friendly uv cache
    uv run --no-project python tests/planning-evals/run_tests.py

Each test_*.py module in this directory must expose run() -> int (failure
count). Exit code is 1 if any module reports failures.
"""

import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    modules = sorted(HERE.glob("test_*.py"))
    if not modules:
        print("FAIL: no test_*.py modules found in", HERE)
        return 1
    total_failures = 0
    for m in modules:
        print(f"--- {m.name} " + "-" * max(0, 60 - len(m.name)))
        try:
            spec = importlib.util.spec_from_file_location(m.stem, m)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            failures = mod.run()
        except Exception:
            traceback.print_exc()
            failures = 1
            print(f"FAIL: {m.name} raised (see traceback)")
        total_failures += failures
    print("=" * 64)
    if total_failures:
        print(f"RESULT: {total_failures} failure(s) across {len(modules)} modules")
        return 1
    print(f"RESULT: all {len(modules)} test modules green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
