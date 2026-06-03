#!/usr/bin/env python3
"""Check malformed inputs through the multi-worker decoder path with timeouts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import malformed_ivf
import malformed_vp8


REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS = 4
TIMEOUT_SECONDS = 5.0


def command_output_from_timeout(exc: subprocess.TimeoutExpired) -> str:
    output = exc.stdout or ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def run_checked(
    name: str,
    action: str,
    command: list[str],
    expected_exit: int,
    expected_output: str,
) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=TIMEOUT_SECONDS,
        )
        output = completed.stdout
        timed_out = False
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = command_output_from_timeout(exc)
        timed_out = True
        returncode = -1

    ok = not timed_out and returncode == expected_exit and expected_output in output
    return {
        "name": name,
        "action": action,
        "threads": THREADS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "command": command,
        "returncode": returncode,
        "expected_exit": expected_exit,
        "expected_output": expected_output,
        "timed_out": timed_out,
        "output": output.strip(),
        "ok": ok,
    }


def check_ivf_case(bin_path: Path, out_dir: Path, case: dict[str, object]) -> list[dict[str, object]]:
    name = str(case["name"])
    expected_output = str(case["expected_output"])
    ivf_path = out_dir / "corpus" / "ivf" / f"{name}.ivf"
    ivf_path.write_bytes(malformed_ivf.make_case(str(case["kind"])))

    return [
        run_checked(
            name,
            "ivf-info",
            [str(bin_path), "--threads", str(THREADS), "info", str(ivf_path)],
            2,
            expected_output,
        ),
        run_checked(
            name,
            "ivf-decode",
            [str(bin_path), "--threads", str(THREADS), "decode", str(ivf_path), "--yuv", str(out_dir / f"{name}.yuv")],
            2,
            expected_output,
        ),
    ]


def check_vp8_case(bin_path: Path, out_dir: Path, case: dict[str, object]) -> list[dict[str, object]]:
    name = str(case["name"])
    ivf_path = out_dir / "corpus" / "vp8" / f"{name}.ivf"
    ivf_path.write_bytes(malformed_vp8.wrap_ivf(malformed_vp8.make_payload(str(case["kind"]))))

    return [
        run_checked(
            name,
            "vp8-info",
            [str(bin_path), "--threads", str(THREADS), "info", str(ivf_path)],
            0,
            "ivf.payloads=1",
        ),
        run_checked(
            name,
            "vp8-decode",
            [str(bin_path), "--threads", str(THREADS), "decode", str(ivf_path), "--yuv", str(out_dir / f"{name}.yuv")],
            2,
            malformed_vp8.DECODE_ERROR,
        ),
        run_checked(
            name,
            "vp8-decode-frame",
            [
                str(bin_path),
                "--threads",
                str(THREADS),
                "decode-frame",
                str(ivf_path),
                "--index",
                "0",
                "--yuv",
                str(out_dir / f"{name}-frame.yuv"),
            ],
            2,
            malformed_vp8.DECODE_ERROR,
        ),
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: multithread_malformed.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "corpus" / "ivf").mkdir(parents=True)
    (out_dir / "corpus" / "vp8").mkdir(parents=True)

    results = []
    ivf_manifest = json.loads(malformed_ivf.CORPUS_MANIFEST.read_text(encoding="utf-8"))
    for case in ivf_manifest["cases"]:
        results.extend(check_ivf_case(bin_path, out_dir, case))

    vp8_manifest = json.loads(malformed_vp8.CORPUS_MANIFEST.read_text(encoding="utf-8"))
    for case in vp8_manifest["cases"]:
        results.extend(check_vp8_case(bin_path, out_dir, case))

    (out_dir / "report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failures = [result for result in results if not result["ok"]]
    if failures:
        for failure in failures:
            if failure["timed_out"]:
                print(
                    f"{failure['name']} {failure['action']}: timed out after "
                    f"{failure['timeout_seconds']}s output {failure['output']!r}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"{failure['name']} {failure['action']}: exit "
                    f"{failure['returncode']} output {failure['output']!r}",
                    file=sys.stderr,
                )
        return 1

    for result in results:
        print(
            f"{result['name']} {result['action']} threads={result['threads']} "
            f"exit={result['returncode']} no-timeout"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
