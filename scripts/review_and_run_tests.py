#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.print_test_expectations import main as print_expectations_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    print("=== Zalecane odpowiedzi / zakresy z testow ===")
    print_expectations_main()
    sys.stdout.flush()
    print("\n=== Start pytest ===")
    sys.stdout.flush()

    cmd = [sys.executable, "-m", "pytest", *args]
    completed = subprocess.run(cmd, cwd=ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
