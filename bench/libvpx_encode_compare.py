#!/usr/bin/env python3
"""Compare vp8uya encoder output against libvpx.

The first landed surface is the machine-readable metric contract used by the
future benchmark and threshold gate. Real sample execution is added later.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Mapping
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VPX_TOOLS_DIR = REPO_ROOT / "build" / "deps" / "vpx-tools-root" / "usr" / "bin"
LIBVPX_PRESET = "vpxenc --best"

REQUIRED_RESULT_FIELDS = (
    "sample",
    "width",
    "height",
    "frames",
    "fps",
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "bitrate_ratio",
    "vp8uya_psnr_y_db",
    "vp8uya_psnr_u_db",
    "vp8uya_psnr_v_db",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_y_db",
    "libvpx_psnr_u_db",
    "libvpx_psnr_v_db",
    "libvpx_psnr_all_db",
    "psnr_all_delta_db",
    "vp8uya_ssim_all",
    "libvpx_ssim_all",
    "vp8uya_fps",
    "libvpx_fps",
    "fps_ratio",
    "passed",
    "failure_reasons",
)

HARD_THRESHOLD_FIELDS = (
    "bitrate_ratio",
    "psnr_all_delta_db",
    "fps_ratio",
)

THRESHOLDS = {
    "max_bitrate_ratio": 1.10,
    "min_psnr_all_delta_db": -0.50,
    "min_fps_ratio": 0.80,
}


def tool_lookup_result(path: str | None, source: str | None, error: str | None, attempted: list[str]) -> dict[str, Any]:
    return {
        "path": path,
        "source": source,
        "error": error,
        "attempted": attempted,
    }


def is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_vpx_tool(
    name: str,
    env_var: str,
    *,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
    extracted_dir: Path | None = None,
) -> dict[str, Any]:
    env_map = os.environ if env is None else env
    search_path = env_map.get("PATH", os.environ.get("PATH", "")) if path is None else path
    tool_dir = DEFAULT_VPX_TOOLS_DIR if extracted_dir is None else extracted_dir
    attempted: list[str] = []

    env_value = env_map.get(env_var)
    if env_value:
        attempted.append(env_value)
        env_path = Path(env_value)
        if is_executable_file(env_path):
            return tool_lookup_result(str(env_path), env_var, None, attempted)
        return tool_lookup_result(
            None,
            env_var,
            f"{env_var} points to a missing or non-executable {name}: {env_value}",
            attempted,
        )

    path_value = shutil.which(name, path=search_path)
    if path_value is not None:
        attempted.append(path_value)
        return tool_lookup_result(path_value, "PATH", None, attempted)

    extracted_path = tool_dir / name
    attempted.append(str(extracted_path))
    if is_executable_file(extracted_path):
        return tool_lookup_result(str(extracted_path), "extracted", None, attempted)

    return tool_lookup_result(None, None, f"{name} not found", attempted)


def require_number(result: dict[str, Any], field: str) -> float:
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def metric_contract() -> dict[str, Any]:
    return {
        "libvpx_preset": LIBVPX_PRESET,
        "required_result_fields": list(REQUIRED_RESULT_FIELDS),
        "hard_threshold_fields": list(HARD_THRESHOLD_FIELDS),
        "thresholds": dict(THRESHOLDS),
    }


def evaluate_thresholds(result: dict[str, Any]) -> dict[str, Any]:
    evaluated = dict(result)
    failure_reasons: list[str] = []

    try:
        vp8uya_bpp = require_number(evaluated, "vp8uya_bits_per_pixel")
        libvpx_bpp = require_number(evaluated, "libvpx_bits_per_pixel")
        if libvpx_bpp <= 0.0:
            evaluated["bitrate_ratio"] = float("inf")
            failure_reasons.append("libvpx_bits_per_pixel must be positive")
        else:
            bitrate_ratio = vp8uya_bpp / libvpx_bpp
            evaluated["bitrate_ratio"] = bitrate_ratio
            if bitrate_ratio > THRESHOLDS["max_bitrate_ratio"]:
                failure_reasons.append(
                    "bitrate_ratio "
                    f"{bitrate_ratio:.6f} exceeds max {THRESHOLDS['max_bitrate_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_psnr = require_number(evaluated, "vp8uya_psnr_all_db")
        libvpx_psnr = require_number(evaluated, "libvpx_psnr_all_db")
        psnr_delta = round(vp8uya_psnr - libvpx_psnr, 6)
        evaluated["psnr_all_delta_db"] = psnr_delta
        if psnr_delta < THRESHOLDS["min_psnr_all_delta_db"]:
            failure_reasons.append(
                "psnr_all_delta_db "
                f"{psnr_delta:.6f} below min {THRESHOLDS['min_psnr_all_delta_db']:.6f}"
            )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_fps = require_number(evaluated, "vp8uya_fps")
        libvpx_fps = require_number(evaluated, "libvpx_fps")
        if libvpx_fps <= 0.0:
            evaluated["fps_ratio"] = 0.0
            failure_reasons.append("libvpx_fps must be positive")
        else:
            fps_ratio = round(vp8uya_fps / libvpx_fps, 6)
            evaluated["fps_ratio"] = fps_ratio
            if fps_ratio < THRESHOLDS["min_fps_ratio"]:
                failure_reasons.append(
                    "fps_ratio "
                    f"{fps_ratio:.6f} below min {THRESHOLDS['min_fps_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    evaluated["failure_reasons"] = failure_reasons
    evaluated["passed"] = len(failure_reasons) == 0
    return evaluated


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare vp8uya encoder output against libvpx")
    parser.add_argument(
        "--print-metric-contract",
        action="store_true",
        help="print the required benchmark metric names and hard thresholds as JSON",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.print_metric_contract:
        print(json.dumps(metric_contract(), indent=2, sort_keys=True))
        return 0

    print("error: no action requested; use --print-metric-contract", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
