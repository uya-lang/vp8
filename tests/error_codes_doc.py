#!/usr/bin/env python3
"""Verify docs/error_codes.md mentions every UYA error declaration."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ERROR_DECL_RE = re.compile(r"^error\s+(Err[A-Za-z0-9_]+);", re.MULTILINE)


def collect_error_codes(src_root: Path) -> list[str]:
    codes: set[str] = set()
    for path in sorted(src_root.rglob("*.uya")):
        text = path.read_text(encoding="utf-8")
        codes.update(ERROR_DECL_RE.findall(text))
    return sorted(codes)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: error_codes_doc.py <docs/error_codes.md> <src-dir>", file=sys.stderr)
        return 2

    doc_path = Path(argv[1])
    src_root = Path(argv[2])
    doc = doc_path.read_text(encoding="utf-8")
    codes = collect_error_codes(src_root)
    missing = [code for code in codes if code not in doc]
    if missing:
        for code in missing:
            print(f"missing error code in {doc_path}: {code}", file=sys.stderr)
        return 1

    print(f"error-codes-doc result=ok codes={len(codes)} doc={doc_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
