#!/usr/bin/env python3
"""Generate malformed VP8 payload cases in valid IVF containers."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST = REPO_ROOT / "fixtures" / "malformed_vp8" / "manifest.json"
DECODE_ERROR = "error: failed to decode VP8 frame"


def frame_tag(*, frame_type: int = 0, show_frame: int = 1, first_partition_size: int = 0) -> bytes:
    tag = frame_type | (show_frame << 4) | (first_partition_size << 5)
    return struct.pack("<I", tag)[:3]


def key_payload(*, first_partition_size: int, start_code: bytes = b"\x9d\x01\x2a", width: int = 16, height: int = 16) -> bytes:
    payload = bytearray(frame_tag(frame_type=0, show_frame=1, first_partition_size=first_partition_size))
    payload.extend(start_code)
    payload.extend(struct.pack("<H", width))
    payload.extend(struct.pack("<H", height))
    return bytes(payload)


def make_payload(kind: str) -> bytes:
    if kind == "short-frame-tag":
        return b"\x10\x00"
    if kind == "inter-partition-overrun":
        return frame_tag(frame_type=1, show_frame=1, first_partition_size=4)
    if kind == "bad-key-start-code":
        return key_payload(first_partition_size=7, start_code=b"\x9d\x01\x2b")
    if kind == "key-partition-too-small":
        return key_payload(first_partition_size=6)
    if kind == "key-size-mismatch":
        return key_payload(first_partition_size=7, width=32, height=16)
    if kind == "empty-inter-partition":
        return frame_tag(frame_type=1, show_frame=1, first_partition_size=0)
    raise RuntimeError(f"unknown malformed VP8 payload kind: {kind}")


def wrap_ivf(payload: bytes) -> bytes:
    out = bytearray()
    out.extend(b"DKIF")
    out.extend(struct.pack("<H", 0))
    out.extend(struct.pack("<H", 32))
    out.extend(b"VP80")
    out.extend(struct.pack("<H", 16))
    out.extend(struct.pack("<H", 16))
    out.extend(struct.pack("<I", 30))
    out.extend(struct.pack("<I", 1))
    out.extend(struct.pack("<I", 1))
    out.extend(struct.pack("<I", 0))
    out.extend(struct.pack("<I", len(payload)))
    out.extend(struct.pack("<Q", 0))
    out.extend(payload)
    return bytes(out)


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


def check_case(bin_path: Path, out_dir: Path, case: dict[str, object]) -> list[dict[str, object]]:
    name = str(case["name"])
    ivf_path = out_dir / "corpus" / f"{name}.ivf"
    ivf_path.write_bytes(wrap_ivf(make_payload(str(case["kind"]))))

    actions = [
        ("info", [str(bin_path), "info", str(ivf_path)], 0, "ivf.payloads=1"),
        ("decode", [str(bin_path), "decode", str(ivf_path), "--yuv", str(out_dir / f"{name}.yuv")], 2, DECODE_ERROR),
        ("decode-frame", [str(bin_path), "decode-frame", str(ivf_path), "--index", "0", "--yuv", str(out_dir / f"{name}-frame.yuv")], 2, DECODE_ERROR),
    ]
    results = []
    for action, command, expected_exit, expected_output in actions:
        returncode, output = run_command(command)
        ok = returncode == expected_exit and expected_output in output
        results.append({
            "name": name,
            "action": action,
            "path": str(ivf_path),
            "returncode": returncode,
            "expected_exit": expected_exit,
            "expected_output": expected_output,
            "output": output.strip(),
            "ok": ok,
        })
    return results


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: malformed_vp8.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "corpus").mkdir(parents=True)

    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))
    results = []
    for case in manifest["cases"]:
        results.extend(check_case(bin_path, out_dir, case))

    (out_dir / "report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failures = [result for result in results if not result["ok"]]
    if failures:
        for failure in failures:
            print(
                f"{failure['name']} {failure['action']}: "
                f"exit {failure['returncode']} output {failure['output']!r}",
                file=sys.stderr,
            )
        return 1

    for result in results:
        print(f"{result['name']} {result['action']} exit={result['returncode']} {result['expected_output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
