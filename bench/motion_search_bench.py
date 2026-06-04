#!/usr/bin/env python3
"""Benchmark VP8 integer-pel motion-search scalar vs forced-SIMD SAD paths."""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODES = ("scalar", "simd")


def parse_report(output: str) -> dict[str, object]:
    report: dict[str, object] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("motion_search.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "motion_search.mode":
            report[key] = value
        else:
            report[key] = int(value)
    return report


def run_bench(bin_path: Path, mode: str, iterations: int) -> tuple[int, dict[str, object]]:
    start_ns = time.perf_counter_ns()
    completed = subprocess.run(
        [str(bin_path), mode, str(iterations)],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    elapsed_ns = time.perf_counter_ns() - start_ns
    if completed.returncode != 0:
        raise RuntimeError(
            f"{mode} motion-search benchmark failed with exit {completed.returncode}: "
            f"{completed.stdout.strip()}"
        )
    report = parse_report(completed.stdout)
    if report.get("motion_search.mode") != mode:
        raise RuntimeError(f"{mode}: missing or mismatched benchmark mode report")
    for key in (
        "motion_search.iterations",
        "motion_search.macroblocks_per_iteration",
        "motion_search.search_radius",
        "motion_search.candidates",
        "motion_search.checksum",
    ):
        if key not in report:
            raise RuntimeError(f"{mode}: missing {key} in benchmark report")
    return elapsed_ns, report


def percentile(values: list[int], rank: float) -> int:
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * rank))
    return sorted_values[index]


def benchmark_mode(
    bin_path: Path,
    mode: str,
    repeats: int,
    warmups: int,
    iterations: int,
    cycles_per_second: float,
) -> dict[str, object]:
    for _ in range(warmups):
        run_bench(bin_path, mode, iterations)

    timings: list[int] = []
    report: dict[str, object] = {}
    for _ in range(repeats):
        elapsed_ns, report = run_bench(bin_path, mode, iterations)
        timings.append(elapsed_ns)

    median_ns = int(statistics.median(timings))
    candidates = int(report["motion_search.candidates"])
    return {
        "mode": mode,
        "repeats": repeats,
        "warmups": warmups,
        "iterations": iterations,
        "macroblocks_per_iteration": int(report["motion_search.macroblocks_per_iteration"]),
        "search_radius": int(report["motion_search.search_radius"]),
        "candidates": candidates,
        "checksum": int(report["motion_search.checksum"]),
        "min_ns": min(timings),
        "median_ns": median_ns,
        "p90_ns": percentile(timings, 0.90),
        "max_ns": max(timings),
        "candidates_per_second": (candidates * 1_000_000_000.0 / median_ns) if median_ns > 0 else 0.0,
        "ns_per_candidate": (median_ns / candidates) if candidates > 0 else 0.0,
        "cycles_per_second": cycles_per_second,
        "cycles_per_candidate": ((median_ns / 1_000_000_000.0) * cycles_per_second / candidates) if candidates > 0 else 0.0,
        "report": report,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark VP8 motion-search scalar and forced-SIMD SAD paths")
    parser.add_argument("--repeats", type=int, default=7, help="measured runs per mode")
    parser.add_argument("--warmups", type=int, default=1, help="warmup runs per mode")
    parser.add_argument("--iterations", type=int, default=8, help="motion-search batches per benchmark process")
    parser.add_argument("--cycles-per-second", type=float, default=1_000_000_000.0, help="cycle rate used to derive cycles/candidate from wall time")
    parser.add_argument("--min-speedup", type=float, default=1.05, help="required scalar_median_ns / simd_median_ns")
    parser.add_argument("bin_path", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv[1:])
    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.cycles_per_second <= 0:
        parser.error("--cycles-per-second must be positive")
    if args.min_speedup <= 0:
        parser.error("--min-speedup must be positive")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    bin_path = args.bin_path
    out_dir = args.out_dir
    if not bin_path.exists():
        print(f"error: benchmark binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    results = [
        benchmark_mode(bin_path, mode, args.repeats, args.warmups, args.iterations, args.cycles_per_second)
        for mode in MODES
    ]
    by_mode = {result["mode"]: result for result in results}
    scalar = by_mode["scalar"]
    simd = by_mode["simd"]
    same_work = (
        scalar["candidates"] == simd["candidates"]
        and scalar["checksum"] == simd["checksum"]
        and scalar["iterations"] == simd["iterations"]
    )
    speedup = (scalar["median_ns"] / simd["median_ns"]) if simd["median_ns"] else 0.0

    for result in results:
        print(
            f"bench-motion-search mode={result['mode']} candidates={result['candidates']} "
            f"median_ns={result['median_ns']} ns_per_candidate={result['ns_per_candidate']:.3f} "
            f"cycles_per_candidate={result['cycles_per_candidate']:.3f} checksum={result['checksum']}"
        )
    print(
        f"bench-motion-search-compare same_work={int(same_work)} "
        f"speedup={speedup:.3f} min_speedup={args.min_speedup:.3f}"
    )

    if not same_work:
        raise RuntimeError("scalar and SIMD motion-search benchmark results differ")
    if speedup < args.min_speedup:
        raise RuntimeError(f"motion-search speedup {speedup:.3f} below required {args.min_speedup:.3f}")

    ndjson_path = out_dir / "results.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, sort_keys=True) + "\n")
    summary = {
        "modes": sorted(MODES),
        "repeats": args.repeats,
        "warmups": args.warmups,
        "iterations": args.iterations,
        "cycles_per_second": args.cycles_per_second,
        "min_speedup": args.min_speedup,
        "speedup": speedup,
        "same_work": same_work,
        "results": str(ndjson_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
