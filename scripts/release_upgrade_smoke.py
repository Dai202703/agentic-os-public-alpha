#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from agentic_os.cli import main as cli_main

    return cli_main(["release-upgrade-smoke", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
