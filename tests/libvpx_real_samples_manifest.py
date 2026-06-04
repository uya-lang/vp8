#!/usr/bin/env python3
"""Validate the libvpx encoder real-sample manifest shape."""

from __future__ import annotations

import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "fixtures" / "encoder_libvpx_real_samples.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sample_by_name(manifest: dict[str, object], name: str) -> dict[str, object]:
    samples = manifest["samples"]
    assert isinstance(samples, list)
    for sample in samples:
        assert isinstance(sample, dict)
        if sample.get("name") == name:
            return sample
    raise AssertionError(f"missing sample: {name}")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["source"] == "Xiph Derf"
    assert isinstance(manifest["samples"], list)

    akiyo = sample_by_name(manifest, "akiyo_qcif")
    assert akiyo["url"] == "https://media.xiph.org/video/derf/y4m/akiyo_qcif.y4m"
    assert akiyo["width"] == 176
    assert akiyo["height"] == 144
    assert akiyo["frames"] == 60
    assert akiyo["fps"] == "30000/1001"
    assert SHA256_RE.match(akiyo["sha256"])
    assert {"real", "qcif", "low-motion"}.issubset(set(akiyo["groups"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
