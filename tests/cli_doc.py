#!/usr/bin/env python3
"""Verify docs/cli.md covers the current CLI help usage lines."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: cli_doc.py <docs/cli.md> <vp8uya-bin>", file=sys.stderr)
        return 2

    doc_path = Path(argv[1])
    bin_path = Path(argv[2])
    doc = doc_path.read_text(encoding="utf-8")
    completed = subprocess.run(
        [str(bin_path), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )

    missing = []
    for line in completed.stdout.splitlines():
        if line.startswith("  vp8uya ") and line.strip() not in doc:
            missing.append(line.strip())

    if missing:
        for line in missing:
            print(f"missing CLI usage line in {doc_path}: {line}", file=sys.stderr)
        return 1

    print(f"cli-doc result=ok usage_lines={len(completed.stdout.splitlines())} doc={doc_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
