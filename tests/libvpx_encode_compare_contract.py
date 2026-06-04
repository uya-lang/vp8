#!/usr/bin/env python3
"""Contract checks for libvpx encoder comparison metrics."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
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


def make_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "sample": "unit",
        "width": 16,
        "height": 16,
        "frames": 1,
        "fps": "30/1",
        "vp8uya_bits_per_pixel": 1.0,
        "libvpx_bits_per_pixel": 1.0,
        "vp8uya_psnr_all_db": 40.0,
        "libvpx_psnr_all_db": 40.0,
        "vp8uya_ssim_all": 0.99,
        "libvpx_ssim_all": 0.99,
        "vp8uya_fps": 100.0,
        "libvpx_fps": 100.0,
    }
    result.update(overrides)
    return result


def assert_bitrate_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.10, libvpx_bits_per_pixel=1.0)
    )
    assert passing["passed"] is True
    assert passing["bitrate_ratio"] == 1.10
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.11, libvpx_bits_per_pixel=1.0)
    )
    assert failing["passed"] is False
    assert failing["bitrate_ratio"] == 1.11
    assert any("bitrate_ratio" in reason for reason in failing["failure_reasons"])


def assert_psnr_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.50, libvpx_psnr_all_db=40.0)
    )
    assert passing["passed"] is True
    assert passing["psnr_all_delta_db"] == -0.50
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.49, libvpx_psnr_all_db=40.0)
    )
    assert failing["passed"] is False
    assert failing["psnr_all_delta_db"] == -0.51
    assert any("psnr_all_delta_db" in reason for reason in failing["failure_reasons"])


def assert_fps_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_fps=80.0, libvpx_fps=100.0)
    )
    assert passing["passed"] is True
    assert passing["fps_ratio"] == 0.80
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_fps=79.0, libvpx_fps=100.0)
    )
    assert failing["passed"] is False
    assert failing["fps_ratio"] == 0.79
    assert any("fps_ratio" in reason for reason in failing["failure_reasons"])


def assert_ssim_is_record_only(module: object) -> None:
    contract = module.metric_contract()
    fields = set(contract["required_result_fields"])
    hard_threshold_fields = set(contract["hard_threshold_fields"])
    assert "vp8uya_ssim_all" in fields
    assert "libvpx_ssim_all" in fields
    assert "vp8uya_ssim_all" not in hard_threshold_fields
    assert "libvpx_ssim_all" not in hard_threshold_fields

    evaluated = module.evaluate_thresholds(
        make_result(vp8uya_ssim_all=0.10, libvpx_ssim_all=0.99)
    )
    assert evaluated["passed"] is True
    assert not any("ssim" in reason.lower() for reason in evaluated["failure_reasons"])


def write_fake_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def assert_vpxenc_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxenc"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXENC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxenc")
        missing = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXENC"
        assert "VPXENC" in missing["error"]
        assert missing_path in missing["error"]


def assert_vpxdec_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxdec"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXDEC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxdec")
        missing = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXDEC"
        assert "VPXDEC" in missing["error"]
        assert missing_path in missing["error"]


def main() -> int:
    module = load_module()
    assert_contract(module.metric_contract())
    assert_bitrate_threshold(module)
    assert_psnr_threshold(module)
    assert_fps_threshold(module)
    assert_ssim_is_record_only(module)
    assert_vpxenc_env_lookup(module)
    assert_vpxdec_env_lookup(module)

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
