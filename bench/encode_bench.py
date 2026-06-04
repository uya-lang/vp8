#!/usr/bin/env python3
"""Benchmark vp8uya encode paths on deterministic I420 samples."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

MODES = {
    "scalar": "--force-scalar",
    "simd": "--force-simd",
}


@dataclass(frozen=True)
class EncodeSample:
    name: str
    width: int
    height: int
    variant: str
    groups: tuple[str, ...]
    quantizer: int = 40
    speed: str = "best"


SAMPLES = (
    EncodeSample("gradient-32x16", 32, 16, "gradient", ("smoke", "encoder")),
    EncodeSample("mode-search-64x64", 64, 64, "mode-search", ("encoder",)),
)


def i420_size(width: int, height: int) -> int:
    luma = width * height
    chroma_width = (width + 1) // 2
    chroma_height = (height + 1) // 2
    return luma + (2 * chroma_width * chroma_height)


def make_i420(sample: EncodeSample) -> bytes:
    y_size = sample.width * sample.height
    uv_width = (sample.width + 1) // 2
    uv_height = (sample.height + 1) // 2
    uv_size = uv_width * uv_height
    out = bytearray(y_size + (uv_size * 2))

    for y in range(sample.height):
        for x in range(sample.width):
            index = (y * sample.width) + x
            if sample.variant == "mode-search":
                block_bias = ((x // 4) * 23) + ((y // 4) * 29)
                out[index] = 18 + ((x * 17 + y * 31 + block_bias + ((x * y) // 3)) % 214)
            else:
                out[index] = 22 + ((x * 19 + y * 37 + ((y // 4) * ((x % 5) + 1) * 11)) % 208)

    u_base = y_size
    v_base = y_size + uv_size
    for y in range(uv_height):
        for x in range(uv_width):
            index = (y * uv_width) + x
            out[u_base + index] = 80 + ((x * 11 + y * 17 + sample.width) % 72)
            out[v_base + index] = 92 + ((x * 13 + y * 19 + sample.height) % 64)

    return bytes(out)


def parse_encode_report(output: str) -> dict[str, object]:
    report: dict[str, object] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("encode.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value == "inf":
            report[key] = value
        elif key == "encode.speed.mode_search_work_units":
            report[key] = int(value)
        elif key.startswith("encode.bitrate."):
            report[key] = int(value)
        elif "." in value:
            report[key] = float(value)
        else:
            report[key] = value
    return report


def run_encode(bin_path: Path, mode: str, sample: EncodeSample, input_path: Path, output_path: Path) -> tuple[int, bytes, dict[str, object]]:
    start_ns = time.perf_counter_ns()
    completed = subprocess.run(
        [
            str(bin_path),
            MODES[mode],
            "encode",
            str(input_path),
            "--width",
            str(sample.width),
            "--height",
            str(sample.height),
            "--quantizer",
            str(sample.quantizer),
            "--speed",
            sample.speed,
            "--out",
            str(output_path),
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
            f"{mode} encode failed for {sample.name} with exit {completed.returncode}: "
            f"{completed.stdout.strip()}"
        )
    return elapsed_ns, output_path.read_bytes(), parse_encode_report(completed.stdout)


def percentile(values: list[int], rank: float) -> int:
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * rank))
    return sorted_values[index]


def benchmark_sample_mode(
    bin_path: Path,
    out_dir: Path,
    sample: EncodeSample,
    mode: str,
    repeats: int,
    warmups: int,
    cycles_per_second: float,
) -> dict[str, object]:
    input_path = out_dir / "fixtures" / f"{sample.name}.yuv"
    output_path = out_dir / "runs" / f"{sample.name}.{mode}.ivf"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    input_bytes = make_i420(sample)
    input_path.write_bytes(input_bytes)

    for _ in range(warmups):
        run_encode(bin_path, mode, sample, input_path, output_path)

    timings: list[int] = []
    ivf = b""
    report: dict[str, object] = {}
    for _ in range(repeats):
        elapsed_ns, ivf, report = run_encode(bin_path, mode, sample, input_path, output_path)
        timings.append(elapsed_ns)

    expected_input_size = i420_size(sample.width, sample.height)
    if len(input_bytes) != expected_input_size:
        raise RuntimeError(f"{sample.name}: expected {expected_input_size} input bytes, got {len(input_bytes)}")
    if not ivf:
        raise RuntimeError(f"{sample.name}/{mode}: encoder produced an empty IVF")
    if "encode.speed.mode_search_work_units" not in report:
        raise RuntimeError(f"{sample.name}/{mode}: encode report did not include mode search work units")

    median_ns = int(statistics.median(timings))
    pixels = sample.width * sample.height
    return {
        "sample": sample.name,
        "variant": sample.variant,
        "mode": mode,
        "width": sample.width,
        "height": sample.height,
        "pixels": pixels,
        "input_bytes": len(input_bytes),
        "ivf_bytes": len(ivf),
        "ivf_md5": hashlib.md5(ivf).hexdigest(),
        "repeats": repeats,
        "warmups": warmups,
        "min_ns": min(timings),
        "median_ns": median_ns,
        "p90_ns": percentile(timings, 0.90),
        "max_ns": max(timings),
        "fps": (1_000_000_000.0 / median_ns) if median_ns > 0 else 0.0,
        "cycles_per_second": cycles_per_second,
        "cycles_per_pixel": ((median_ns / 1_000_000_000.0) * cycles_per_second) / pixels if pixels > 0 else 0.0,
        "speed": sample.speed,
        "quantizer": sample.quantizer,
        "mode_search_work_units": int(report["encode.speed.mode_search_work_units"]),
        "psnr_all": report.get("encode.psnr.all"),
        "ssim_all": report.get("encode.ssim.all"),
        "report": report,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark vp8uya encode scalar and forced-SIMD paths")
    parser.add_argument("--group", default=None, help="sample group to benchmark")
    parser.add_argument("--repeats", type=int, default=5, help="measured encode runs per sample and mode")
    parser.add_argument("--warmups", type=int, default=1, help="warmup encode runs per sample and mode")
    parser.add_argument("--cycles-per-second", type=float, default=1_000_000_000.0, help="cycle rate used to derive cycles/pixel from wall time")
    parser.add_argument("--min-speedup", type=float, default=0.0, help="optional scalar_median_ns / simd_median_ns floor")
    parser.add_argument("bin_path", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv[1:])
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.cycles_per_second <= 0:
        parser.error("--cycles-per-second must be positive")
    if args.min_speedup < 0:
        parser.error("--min-speedup must be non-negative")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    bin_path = args.bin_path
    out_dir = args.out_dir
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    selected_samples = [
        sample for sample in SAMPLES
        if args.group is None or args.group in sample.groups
    ]
    if not selected_samples:
        print(f"error: no samples matched group {args.group}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    results: list[dict[str, object]] = []
    comparisons: list[dict[str, object]] = []
    for sample in selected_samples:
        by_mode: dict[str, dict[str, object]] = {}
        for mode in ("scalar", "simd"):
            result = benchmark_sample_mode(
                bin_path,
                out_dir,
                sample,
                mode,
                args.repeats,
                args.warmups,
                args.cycles_per_second,
            )
            results.append(result)
            by_mode[mode] = result
            print(
                f"bench-encode sample={result['sample']} mode={result['mode']} "
                f"fps={result['fps']:.3f} cycles_per_pixel={result['cycles_per_pixel']:.3f} "
                f"median_ns={result['median_ns']} work_units={result['mode_search_work_units']} "
                f"ivf_bytes={result['ivf_bytes']} md5={result['ivf_md5']}"
            )

        scalar = by_mode["scalar"]
        simd = by_mode["simd"]
        bitstream_equal = scalar["ivf_md5"] == simd["ivf_md5"] and scalar["ivf_bytes"] == simd["ivf_bytes"]
        speedup = (scalar["median_ns"] / simd["median_ns"]) if simd["median_ns"] else 0.0
        comparison = {
            "sample": sample.name,
            "bitstream_equal": bitstream_equal,
            "scalar_md5": scalar["ivf_md5"],
            "simd_md5": simd["ivf_md5"],
            "scalar_median_ns": scalar["median_ns"],
            "simd_median_ns": simd["median_ns"],
            "speedup": speedup,
            "mode_search_work_units_equal": scalar["mode_search_work_units"] == simd["mode_search_work_units"],
        }
        comparisons.append(comparison)
        print(
            f"bench-encode-compare sample={sample.name} bitstream_equal={int(bitstream_equal)} "
            f"speedup={speedup:.3f} work_units_equal={int(comparison['mode_search_work_units_equal'])}"
        )
        if not bitstream_equal:
            raise RuntimeError(f"{sample.name}: scalar and SIMD encoder bitstreams differ")
        if not comparison["mode_search_work_units_equal"]:
            raise RuntimeError(f"{sample.name}: scalar and SIMD encoder work units differ")
        if args.min_speedup > 0 and speedup < args.min_speedup:
            raise RuntimeError(f"{sample.name}: speedup {speedup:.3f} below required {args.min_speedup:.3f}")

    ndjson_path = out_dir / "results.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, sort_keys=True) + "\n")

    summary = {
        "samples": len(selected_samples),
        "modes": sorted(MODES.keys()),
        "repeats": args.repeats,
        "warmups": args.warmups,
        "cycles_per_second": args.cycles_per_second,
        "comparisons": comparisons,
        "results": str(ndjson_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
