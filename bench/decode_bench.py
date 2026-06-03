#!/usr/bin/env python3
"""Benchmark vp8uya decode paths on built-in IVF samples."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"
sys.path.insert(0, str(TESTS_DIR))

from tiny_ivf_md5 import EXPECTED_MD5  # noqa: E402
from tiny_ivf_md5 import GROUPS_BY_NAME  # noqa: E402
from tiny_ivf_md5 import SAMPLES  # noqa: E402
from tiny_ivf_md5 import Sample  # noqa: E402
from tiny_ivf_md5 import make_ivf  # noqa: E402


BENCH_1080P_SAMPLE = Sample("gray-1920x1080", 1920, 1080, "gray", ("bench-1080p", "key"), 1, 1)

MODES = {
    "scalar": "--force-scalar",
    "simd": "--force-simd",
}


def expected_yuv_size(sample: Sample) -> int:
    luma = sample.width * sample.height
    chroma = math.ceil(sample.width / 2) * math.ceil(sample.height / 2) * 2
    return (luma + chroma) * sample.output_frames


def expected_md5_for_sample(sample: Sample, expected_size: int) -> str:
    if sample.name in EXPECTED_MD5:
        return EXPECTED_MD5[sample.name]
    if sample.variant == "gray":
        return hashlib.md5(bytes([128]) * expected_size).hexdigest()
    raise RuntimeError(f"{sample.name}: no benchmark MD5 rule for variant {sample.variant}")


def read_stats(stats_path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in stats_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_decode(bin_path: Path, mode: str, threads: int, ivf_path: Path, yuv_path: Path, stats_path: Path) -> tuple[int, bytes, list[dict[str, object]]]:
    start_ns = time.perf_counter_ns()
    completed = subprocess.run(
        [
            str(bin_path),
            MODES[mode],
            "--threads",
            str(threads),
            "decode",
            str(ivf_path),
            "--yuv",
            str(yuv_path),
            "--stats",
            str(stats_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    elapsed_ns = time.perf_counter_ns() - start_ns
    if completed.returncode != 0:
        raise RuntimeError(
            f"{mode} decode failed for {ivf_path.name} with exit {completed.returncode}: "
            f"{completed.stdout.strip()}"
        )
    return elapsed_ns, yuv_path.read_bytes(), read_stats(stats_path)


def percentile(values: list[int], rank: float) -> int:
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * rank))
    return sorted_values[index]


def benchmark_sample(
    bin_path: Path,
    out_dir: Path,
    sample: Sample,
    mode: str,
    repeats: int,
    warmups: int,
    threads: int,
    cycles_per_second: float,
) -> dict[str, object]:
    ivf_path = out_dir / "fixtures" / f"{sample.name}.ivf"
    yuv_path = out_dir / "runs" / f"{sample.name}.{mode}.yuv"
    stats_path = out_dir / "runs" / f"{sample.name}.{mode}.stats.jsonl"
    ivf_path.parent.mkdir(parents=True, exist_ok=True)
    yuv_path.parent.mkdir(parents=True, exist_ok=True)
    if not ivf_path.exists():
        ivf_path.write_bytes(make_ivf(sample))

    for _ in range(warmups):
        run_decode(bin_path, mode, threads, ivf_path, yuv_path, stats_path)

    timings = []
    yuv = b""
    frame_stats: list[dict[str, object]] = []
    for _ in range(repeats):
        elapsed_ns, yuv, frame_stats = run_decode(bin_path, mode, threads, ivf_path, yuv_path, stats_path)
        timings.append(elapsed_ns)

    expected_size = expected_yuv_size(sample)
    if len(yuv) != expected_size:
        raise RuntimeError(f"{sample.name}/{mode}: expected {expected_size} YUV bytes, got {len(yuv)}")

    digest = hashlib.md5(yuv).hexdigest()
    expected_md5 = expected_md5_for_sample(sample, expected_size)
    if digest != expected_md5:
        raise RuntimeError(f"{sample.name}/{mode}: expected MD5 {expected_md5}, got {digest}")

    median_ns = int(statistics.median(timings))
    decoded_frames = len(frame_stats)
    if decoded_frames == 0:
        raise RuntimeError(f"{sample.name}/{mode}: decode stats file was empty")
    decoded_pixels = sample.width * sample.height * decoded_frames
    fps_median = (decoded_frames * 1_000_000_000.0) / median_ns if median_ns > 0 else 0.0
    cycles_per_pixel = ((median_ns / 1_000_000_000.0) * cycles_per_second) / decoded_pixels if decoded_pixels > 0 else 0.0
    bytes_copied_total = sum(int(item["bytes_copied_for_ref_refresh"]) for item in frame_stats)
    allocation_count = sum(int(item["hot_loop_heap_allocation_count"]) for item in frame_stats)
    reported_thread_count = max(int(item["thread_count"]) for item in frame_stats)
    return {
        "sample": sample.name,
        "variant": sample.variant,
        "mode": mode,
        "thread_count": reported_thread_count,
        "width": sample.width,
        "height": sample.height,
        "frames": sample.output_frames,
        "decoded_frames": decoded_frames,
        "yuv_bytes": expected_size,
        "repeats": repeats,
        "warmups": warmups,
        "min_ns": min(timings),
        "median_ns": median_ns,
        "p90_ns": percentile(timings, 0.90),
        "max_ns": max(timings),
        "fps": fps_median,
        "cycles_per_second": cycles_per_second,
        "cycles_per_pixel": cycles_per_pixel,
        "bytes_per_second_median": int((expected_size * 1_000_000_000) / median_ns) if median_ns > 0 else 0,
        "bytes_copied_per_frame": bytes_copied_total / decoded_frames,
        "allocation_count": allocation_count,
        "frame_stats": frame_stats,
        "md5": digest,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark vp8uya decode on built-in samples")
    parser.add_argument("--group", default=None, help="fixture manifest group to benchmark")
    parser.add_argument("--include-1080p", action="store_true", help="include a generated 1920x1080 benchmark sample")
    parser.add_argument("--repeats", type=int, default=5, help="measured decode runs per sample and mode")
    parser.add_argument("--warmups", type=int, default=1, help="warmup decode runs per sample and mode")
    parser.add_argument("--threads", type=int, default=1, help="decoder worker scratch count to pass through --threads")
    parser.add_argument("--cycles-per-second", type=float, default=1_000_000_000.0, help="cycle rate used to derive cycles/pixel from wall time")
    parser.add_argument("bin_path", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv[1:])
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.threads <= 0:
        parser.error("--threads must be positive")
    if args.cycles_per_second <= 0:
        parser.error("--cycles-per-second must be positive")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    bin_path = args.bin_path
    out_dir = args.out_dir
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    available_samples = list(SAMPLES)
    if args.include_1080p:
        available_samples.append(BENCH_1080P_SAMPLE)

    selected_samples = [
        sample for sample in available_samples
        if args.group is None or args.group in GROUPS_BY_NAME.get(sample.name, sample.groups)
    ]
    if not selected_samples:
        print(f"error: no samples matched group {args.group}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    results = []
    for sample in selected_samples:
        for mode in ("scalar", "simd"):
            result = benchmark_sample(
                bin_path,
                out_dir,
                sample,
                mode,
                args.repeats,
                args.warmups,
                args.threads,
                args.cycles_per_second,
            )
            results.append(result)
            print(
                f"bench sample={result['sample']} mode={result['mode']} "
                f"fps={result['fps']:.3f} cycles_per_pixel={result['cycles_per_pixel']:.3f} "
                f"threads={result['thread_count']} bytes_copied_per_frame={result['bytes_copied_per_frame']:.3f} "
                f"allocation_count={result['allocation_count']} median_ns={result['median_ns']} "
                f"bytes={result['yuv_bytes']} bps={result['bytes_per_second_median']} md5={result['md5']}"
            )

    ndjson_path = out_dir / "results.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, sort_keys=True) + "\n")

    summary = {
        "samples": len(selected_samples),
        "modes": sorted(MODES.keys()),
        "repeats": args.repeats,
        "threads": args.threads,
        "warmups": args.warmups,
        "cycles_per_second": args.cycles_per_second,
        "results": str(ndjson_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
