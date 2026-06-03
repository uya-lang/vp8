#!/usr/bin/env python3
"""Generate malformed IVF cases and assert controlled CLI errors."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST = REPO_ROOT / "fixtures" / "malformed_ivf" / "manifest.json"


def ivf_header(
    *,
    signature: bytes = b"DKIF",
    header_size: int = 32,
    fourcc: bytes = b"VP80",
    width: int = 16,
    height: int = 16,
    frame_count: int = 1,
) -> bytes:
    out = bytearray()
    out.extend(signature)
    out.extend(struct.pack("<H", 0))
    out.extend(struct.pack("<H", header_size))
    out.extend(fourcc)
    out.extend(struct.pack("<H", width))
    out.extend(struct.pack("<H", height))
    out.extend(struct.pack("<I", 30))
    out.extend(struct.pack("<I", 1))
    out.extend(struct.pack("<I", frame_count))
    out.extend(struct.pack("<I", 0))
    return bytes(out)


def make_case(kind: str) -> bytes:
    if kind == "short-header":
        return b"DKI"
    if kind == "bad-signature":
        return ivf_header(signature=b"BAD!")
    if kind == "small-header-size":
        return ivf_header(header_size=16)
    if kind == "bad-fourcc":
        return ivf_header(fourcc=b"AV10")
    if kind == "large-header-size":
        return ivf_header(header_size=64, frame_count=0)
    if kind == "truncated-frame-header":
        return ivf_header(frame_count=1) + b"\x03\x00\x00"
    if kind == "truncated-payload":
        frame = bytearray(ivf_header(frame_count=1))
        frame.extend(struct.pack("<I", 9))
        frame.extend(struct.pack("<Q", 0))
        frame.extend(b"\xaa\xbb\xcc")
        return bytes(frame)
    raise RuntimeError(f"unknown malformed IVF case kind: {kind}")


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
    expected_output = str(case["expected_output"])
    ivf_path = out_dir / "corpus" / f"{name}.ivf"
    ivf_path.write_bytes(make_case(str(case["kind"])))

    actions = [
        ("info", [str(bin_path), "info", str(ivf_path)]),
        ("decode", [str(bin_path), "decode", str(ivf_path), "--yuv", str(out_dir / f"{name}.yuv")]),
    ]
    results = []
    for action, command in actions:
        returncode, output = run_command(command)
        ok = returncode == 2 and expected_output in output
        results.append({
            "name": name,
            "action": action,
            "path": str(ivf_path),
            "returncode": returncode,
            "expected_output": expected_output,
            "output": output.strip(),
            "ok": ok,
        })
    return results


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: malformed_ivf.py <vp8uya-bin> <out-dir>", file=sys.stderr)
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
