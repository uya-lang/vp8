#!/usr/bin/env python3
"""Compare vp8uya encoder output against libvpx.

The first landed surface is the machine-readable metric contract used by the
future benchmark and threshold gate. Real sample execution is added later.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


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
