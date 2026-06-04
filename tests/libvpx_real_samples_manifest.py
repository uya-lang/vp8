#!/usr/bin/env python3
"""Validate the libvpx encoder real-sample manifest shape."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "fixtures" / "encoder_libvpx_real_samples.json"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["source"] == "Xiph Derf"
    assert isinstance(manifest["samples"], list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
