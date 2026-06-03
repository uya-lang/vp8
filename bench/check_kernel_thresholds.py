#!/usr/bin/env python3
"""Validate kernel benchmark threshold configuration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path("bench/kernel_thresholds.json")
REQUIRED_CHECKS = {"bit_exact", "codegen", "benchmark"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SIMD kernel default-enable thresholds")
    parser.add_argument("config", nargs="?", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv[1:])


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be a number")
    return float(value)


def require_int(value: Any, field: str, minimum: int) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def validate_class(name: str, spec: Any) -> None:
    require(isinstance(spec, dict), f"kernel_classes.{name} must be an object")
    min_speedup = require_number(spec.get("min_speedup_to_default_enable"), f"kernel_classes.{name}.min_speedup_to_default_enable")
    max_regression = require_number(spec.get("max_regression_percent"), f"kernel_classes.{name}.max_regression_percent")
    require(min_speedup > 0.0, f"kernel_classes.{name}.min_speedup_to_default_enable must be > 0")
    require(max_regression >= 0.0, f"kernel_classes.{name}.max_regression_percent must be >= 0")
    require_int(spec.get("min_repeats"), f"kernel_classes.{name}.min_repeats", 1)
    require_int(spec.get("min_warmups"), f"kernel_classes.{name}.min_warmups", 0)

    checks = spec.get("required_checks")
    require(isinstance(checks, list) and checks, f"kernel_classes.{name}.required_checks must be a non-empty list")
    check_set = set(checks)
    require(check_set == REQUIRED_CHECKS, f"kernel_classes.{name}.required_checks must be {sorted(REQUIRED_CHECKS)}")


def validate_kernel(index: int, kernel: Any, class_names: set[str], names: set[str]) -> None:
    require(isinstance(kernel, dict), f"kernels[{index}] must be an object")
    name = kernel.get("name")
    require(isinstance(name, str) and name, f"kernels[{index}].name must be a non-empty string")
    require(name not in names, f"duplicate kernel name: {name}")
    names.add(name)

    class_name = kernel.get("class")
    require(isinstance(class_name, str) and class_name in class_names, f"kernels[{index}].class must reference a kernel class")
    require(isinstance(kernel.get("phase"), str) and kernel["phase"], f"kernels[{index}].phase must be a non-empty string")
    require(
        kernel.get("default_policy") == "disabled_until_threshold_passes",
        f"kernels[{index}].default_policy must be disabled_until_threshold_passes",
    )


def validate_config(config: Any) -> tuple[int, int]:
    require(isinstance(config, dict), "config must be an object")
    require(config.get("schema_version") == 1, "schema_version must be 1")
    require(
        config.get("speedup_metric") == "scalar_median_ns / simd_median_ns",
        "speedup_metric must be scalar_median_ns / simd_median_ns",
    )

    classes = config.get("kernel_classes")
    require(isinstance(classes, dict) and classes, "kernel_classes must be a non-empty object")
    require({"memory", "compute", "end_to_end_decoder"}.issubset(classes.keys()), "missing required kernel classes")
    for name, spec in classes.items():
        validate_class(name, spec)

    kernels = config.get("kernels")
    require(isinstance(kernels, list) and kernels, "kernels must be a non-empty list")
    names: set[str] = set()
    class_names = set(classes.keys())
    for index, kernel in enumerate(kernels):
        validate_kernel(index, kernel, class_names, names)
    return len(classes), len(kernels)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config_path = args.config
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            config = json.load(fh)
        class_count, kernel_count = validate_config(config)
        print(f"kernel-thresholds config={config_path.relative_to(REPO_ROOT)} classes={class_count} kernels={kernel_count}")
        print("kernel-thresholds result=ok")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
