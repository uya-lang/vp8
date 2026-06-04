#!/usr/bin/env python3
"""Generate a minimal WebM VP8 subset sample and verify CLI decode output."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from tiny_ivf_md5 import EXPECTED_MD5, Sample, make_ivf


REPO_ROOT = Path(__file__).resolve().parents[1]


def ebml_size(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative EBML size")
    if value < 0x7F:
        return bytes([0x80 | value])
    if value < 0x3FFF:
        return bytes([0x40 | ((value >> 8) & 0x3F), value & 0xFF])
    if value < 0x1FFFFF:
        return bytes([0x20 | ((value >> 16) & 0x1F), (value >> 8) & 0xFF, value & 0xFF])
    raise ValueError(f"EBML size too large for test sample: {value}")


def element(element_id: bytes, payload: bytes) -> bytes:
    return element_id + ebml_size(len(payload)) + payload


def first_ivf_payload(ivf: bytes) -> bytes:
    if len(ivf) < 44:
        raise ValueError("IVF sample is too short")
    frame_size = struct.unpack_from("<I", ivf, 32)[0]
    payload_offset = 44
    payload_end = payload_offset + frame_size
    if payload_end > len(ivf):
        raise ValueError("IVF frame payload is truncated")
    return ivf[payload_offset:payload_end]


def make_webm_subset(payload: bytes, width: int, height: int) -> bytes:
    ebml_header = element(
        bytes.fromhex("1a45dfa3"),
        element(bytes.fromhex("4282"), b"webm"),
    )
    video = element(bytes.fromhex("b0"), width.to_bytes(2, "big"))
    video += element(bytes.fromhex("ba"), height.to_bytes(2, "big"))
    track_entry = b"".join(
        [
            element(bytes.fromhex("d7"), b"\x01"),
            element(bytes.fromhex("83"), b"\x01"),
            element(bytes.fromhex("86"), b"V_VP8"),
            element(bytes.fromhex("e0"), video),
        ]
    )
    tracks = element(bytes.fromhex("1654ae6b"), element(bytes.fromhex("ae"), track_entry))
    simple_block_payload = b"\x81\x00\x00\x80" + payload
    cluster = element(
        bytes.fromhex("1f43b675"),
        element(bytes.fromhex("e7"), b"\x00") + element(bytes.fromhex("a3"), simple_block_payload),
    )
    return ebml_header + element(bytes.fromhex("18538067"), tracks + cluster)


def run(bin_path: Path, out_dir: Path) -> dict[str, object]:
    sample = Sample("gray-16x16", 16, 16, "gray", ("webm",), 1, 1)
    ivf = make_ivf(sample)
    webm = make_webm_subset(first_ivf_payload(ivf), sample.width, sample.height)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    webm_path = out_dir / "gray-16x16.webm"
    yuv_path = out_dir / "gray-16x16.yuv"
    webm_path.write_bytes(webm)
    subprocess.run(
        [str(bin_path), "decode", str(webm_path), "--yuv", str(yuv_path)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    yuv = yuv_path.read_bytes()
    digest = hashlib.md5(yuv).hexdigest()
    expected_md5 = EXPECTED_MD5[sample.name]
    if len(yuv) != 384:
        raise RuntimeError(f"expected 384 YUV bytes, got {len(yuv)}")
    if digest != expected_md5:
        raise RuntimeError(f"expected MD5 {expected_md5}, got {digest}")

    result = {
        "name": sample.name,
        "container": "webm-subset",
        "webm": str(webm_path),
        "yuv": str(yuv_path),
        "yuv_bytes": len(yuv),
        "md5": digest,
        "expected_md5": expected_md5,
    }
    (out_dir / "manifest.json").write_text(json.dumps([result], indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: webm_subset_decode.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    result = run(bin_path, Path(argv[2]))
    print(f"{result['name']} {result['md5']} {result['yuv_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
