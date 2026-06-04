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


def assert_qcif_sample(
    manifest: dict[str, object],
    *,
    name: str,
    sha256: str,
    group: str,
) -> None:
    sample = sample_by_name(manifest, name)
    assert sample["url"] == f"https://media.xiph.org/video/derf/y4m/{name}.y4m"
    assert sample["width"] == 176
    assert sample["height"] == 144
    assert sample["frames"] == 60
    assert sample["fps"] == "30000/1001"
    assert sample["sha256"] == sha256
    assert SHA256_RE.match(sample["sha256"])
    assert {"real", "qcif", group}.issubset(set(sample["groups"]))


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["source"] == "Xiph Derf"
    assert isinstance(manifest["samples"], list)

    assert_qcif_sample(
        manifest,
        name="akiyo_qcif",
        sha256="df88d83cbf6d99f3ec41f2c1fd2e67665d2a71ff8caa08f8b6bc46bf4567ea2e",
        group="low-motion",
    )
    assert_qcif_sample(
        manifest,
        name="foreman_qcif",
        sha256="9b37e95ae2d06b3b173d6130965f450009216084bae12b2025248814baf057af",
        group="motion",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
