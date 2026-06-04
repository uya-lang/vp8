#!/usr/bin/env python3
"""Contract checks for libvpx encoder comparison metrics."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bench" / "libvpx_encode_compare.py"

REQUIRED_FIELDS = {
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
}


def load_module():
    spec = importlib.util.spec_from_file_location("libvpx_encode_compare", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contract(contract: dict[str, object]) -> None:
    fields = set(contract["required_result_fields"])
    missing = REQUIRED_FIELDS - fields
    if missing:
        raise AssertionError(f"missing required metric fields: {sorted(missing)}")

    thresholds = contract["thresholds"]
    assert thresholds["max_bitrate_ratio"] == 1.10
    assert thresholds["min_psnr_all_delta_db"] == -0.50
    assert thresholds["min_fps_ratio"] == 0.80
    assert contract["libvpx_preset"] == "vpxenc --best"


def main() -> int:
    module = load_module()
    assert_contract(module.metric_contract())

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--print-metric-contract"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout)
    assert_contract(json.loads(completed.stdout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
