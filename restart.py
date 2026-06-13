#!/usr/bin/env python3
"""Restart the web scraper Docker stack."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd):
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main():
    if "--all" in sys.argv[1:]:
        cmd = ["docker", "compose", "restart"]
    else:
        cmd = ["docker", "compose", "restart", "scraper"]

    code = run(cmd)
    if code != 0:
        print("Restart failed.", file=sys.stderr)
        return code

    run(["docker", "compose", "ps"])
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
