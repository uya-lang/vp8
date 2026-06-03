#!/usr/bin/env python3
"""Compare single-worker and multi-worker decoder outputs on built-in samples."""

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


def run_decode(bin_path: Path, threads: int, ivf_path: Path, yuv_path: Path) -> bytes:
    completed = subprocess.run(
        [str(bin_path), "--threads", str(threads), "decode", str(ivf_path), "--yuv", str(yuv_path)],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"--threads {threads} decode failed for {ivf_path.name} with exit "
            f"{completed.returncode}: {completed.stdout.strip()}"
        )
    return yuv_path.read_bytes()


def run_sample(bin_path: Path, out_dir: Path, sample: Sample) -> dict[str, object]:
    ivf_path = out_dir / f"{sample.name}.ivf"
    single_yuv_path = out_dir / f"{sample.name}.threads1.yuv"
    multi_yuv_path = out_dir / f"{sample.name}.threads4.yuv"
    ivf_path.write_bytes(make_ivf(sample))

    single_yuv = run_decode(bin_path, 1, ivf_path, single_yuv_path)
    multi_yuv = run_decode(bin_path, 4, ivf_path, multi_yuv_path)

    expected_size = expected_yuv_size(sample)
    if len(single_yuv) != expected_size:
        raise RuntimeError(f"{sample.name}: threads=1 output expected {expected_size} bytes, got {len(single_yuv)}")
    if len(multi_yuv) != expected_size:
        raise RuntimeError(f"{sample.name}: threads=4 output expected {expected_size} bytes, got {len(multi_yuv)}")

    single_md5 = hashlib.md5(single_yuv).hexdigest()
    multi_md5 = hashlib.md5(multi_yuv).hexdigest()
    expected_md5 = EXPECTED_MD5[sample.name]

    return {
        "name": sample.name,
        "width": sample.width,
        "height": sample.height,
        "variant": sample.variant,
        "ivf": str(ivf_path),
        "single_yuv": str(single_yuv_path),
        "multi_yuv": str(multi_yuv_path),
        "yuv_bytes": expected_size,
        "single_thread_md5": single_md5,
        "multi_thread_md5": multi_md5,
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
        print("usage: single_vs_multithread.py [--group NAME] <vp8uya-bin> <out-dir>", file=sys.stderr)
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
        if result["single_thread_md5"] != result["expected_md5"] or result["multi_thread_md5"] != result["single_thread_md5"]:
            failures.append(result)

    if failures:
        for failure in failures:
            print(
                f"{failure['name']}: expected={failure['expected_md5']} "
                f"threads1={failure['single_thread_md5']} threads4={failure['multi_thread_md5']}",
                file=sys.stderr,
            )
        return 1

    for result in results:
        print(
            f"{result['name']} threads1={result['single_thread_md5']} "
            f"threads4={result['multi_thread_md5']} {result['yuv_bytes']} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
