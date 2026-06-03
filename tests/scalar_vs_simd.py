#!/usr/bin/env python3
"""Compare forced scalar and forced SIMD decoder outputs on built-in samples."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from tiny_ivf_md5 import EXPECTED_MD5
from tiny_ivf_md5 import GROUPS_BY_NAME
from tiny_ivf_md5 import REPO_ROOT
from tiny_ivf_md5 import SAMPLES
from tiny_ivf_md5 import Sample
from tiny_ivf_md5 import make_ivf


def expected_yuv_size(sample: Sample) -> int:
    luma = sample.width * sample.height
    chroma = math.ceil(sample.width / 2) * math.ceil(sample.height / 2) * 2
    return (luma + chroma) * sample.output_frames


def run_decode(bin_path: Path, flag: str, ivf_path: Path, yuv_path: Path) -> bytes:
    completed = subprocess.run(
        [str(bin_path), flag, "decode", str(ivf_path), "--yuv", str(yuv_path)],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{flag} decode failed for {ivf_path.name} with exit {completed.returncode}: "
            f"{completed.stdout.strip()}"
        )
    return yuv_path.read_bytes()


def run_sample(bin_path: Path, out_dir: Path, sample: Sample) -> dict[str, object]:
    ivf_path = out_dir / f"{sample.name}.ivf"
    scalar_yuv_path = out_dir / f"{sample.name}.scalar.yuv"
    simd_yuv_path = out_dir / f"{sample.name}.simd.yuv"
    ivf_path.write_bytes(make_ivf(sample))

    scalar_yuv = run_decode(bin_path, "--force-scalar", ivf_path, scalar_yuv_path)
    simd_yuv = run_decode(bin_path, "--force-simd", ivf_path, simd_yuv_path)

    expected_size = expected_yuv_size(sample)
    if len(scalar_yuv) != expected_size:
        raise RuntimeError(f"{sample.name}: scalar output expected {expected_size} bytes, got {len(scalar_yuv)}")
    if len(simd_yuv) != expected_size:
        raise RuntimeError(f"{sample.name}: SIMD output expected {expected_size} bytes, got {len(simd_yuv)}")

    scalar_md5 = hashlib.md5(scalar_yuv).hexdigest()
    simd_md5 = hashlib.md5(simd_yuv).hexdigest()
    expected_md5 = EXPECTED_MD5[sample.name]

    return {
        "name": sample.name,
        "width": sample.width,
        "height": sample.height,
        "variant": sample.variant,
        "ivf": str(ivf_path),
        "scalar_yuv": str(scalar_yuv_path),
        "simd_yuv": str(simd_yuv_path),
        "yuv_bytes": expected_size,
        "scalar_md5": scalar_md5,
        "simd_md5": simd_md5,
        "expected_md5": expected_md5,
    }


def parse_args(argv: list[str]) -> tuple[str | None, Path, Path] | None:
    args = argv[1:]
    group = None
    if len(args) >= 2 and args[0] == "--group":
        group = args[1]
        args = args[2:]
    if len(args) != 2:
        return None
    return group, Path(args[0]), Path(args[1])


def main(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if parsed is None:
        print("usage: scalar_vs_simd.py [--group NAME] <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    group, bin_path, out_dir = parsed
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    selected_samples = [
        sample for sample in SAMPLES
        if group is None or group in GROUPS_BY_NAME.get(sample.name, ())
    ]
    if not selected_samples:
        print(f"error: no samples matched group {group}", file=sys.stderr)
        return 2

    results = [run_sample(bin_path, out_dir, sample) for sample in selected_samples]
    (out_dir / "manifest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    failures = []
    for result in results:
        if result["scalar_md5"] != result["expected_md5"] or result["simd_md5"] != result["scalar_md5"]:
            failures.append(result)

    if failures:
        for failure in failures:
            print(
                f"{failure['name']}: expected={failure['expected_md5']} "
                f"scalar={failure['scalar_md5']} simd={failure['simd_md5']}",
                file=sys.stderr,
            )
        return 1

    for result in results:
        print(
            f"{result['name']} scalar={result['scalar_md5']} "
            f"simd={result['simd_md5']} {result['yuv_bytes']} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
