#!/usr/bin/env python3
"""Generate tiny VP8 IVF samples and verify CLI YUV MD5 goldens."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HEADER_SOURCE = REPO_ROOT / "src" / "vp8" / "bitstream" / "header.uya"
FIXTURE_MANIFEST = REPO_ROOT / "fixtures" / "manifest.json"
MASK32 = 0xFFFFFFFF
COEFF_BANDS = [0, 1, 2, 3, 6, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6, 7]


@dataclass(frozen=True)
class Sample:
    name: str
    width: int
    height: int
    variant: str
    frame_count: int = 1
    output_frames: int = 1


def load_manifest() -> tuple[list[Sample], dict[str, str]]:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    samples = []
    expected_md5 = {}
    for item in manifest["samples"]:
        sample = Sample(
            name=item["name"],
            width=int(item["width"]),
            height=int(item["height"]),
            variant=item["variant"],
            frame_count=int(item["frame_count"]),
            output_frames=int(item.get("output_frames", item["frame_count"])),
        )
        samples.append(sample)
        expected_md5[sample.name] = item["yuv_md5"]
    return samples, expected_md5


SAMPLES, EXPECTED_MD5 = load_manifest()


class BoolWriter:
    def __init__(self, capacity: int) -> None:
        self.out = bytearray(capacity)
        self.byte_pos = 0
        self.range = 255
        self.low_value = 0
        self.count = -24
        self.bit_count = 0

    def _norm(self, value: int) -> int:
        shift = 0
        while value < 128:
            value <<= 1
            shift += 1
        return shift

    def _put_byte(self, offset: int) -> None:
        if self.byte_pos >= len(self.out):
            raise RuntimeError("BoolWriter output exhausted")

        if ((self.low_value << (offset - 1)) & 0x80000000) != 0:
            carry_index = self.byte_pos - 1
            while carry_index >= 0 and self.out[carry_index] == 0xFF:
                self.out[carry_index] = 0
                carry_index -= 1
            if carry_index >= 0:
                self.out[carry_index] = (self.out[carry_index] + 1) & 0xFF

        self.out[self.byte_pos] = (self.low_value >> (24 - offset)) & 0xFF
        self.byte_pos += 1

    def write(self, bit: int, probability: int) -> None:
        if self.byte_pos >= len(self.out):
            raise RuntimeError("BoolWriter output exhausted")

        split = 1 + (((self.range - 1) * probability) >> 8)
        if bit:
            self.low_value = (self.low_value + split) & MASK32
            self.range -= split
        else:
            self.range = split

        shift = self._norm(self.range)
        self.range = (self.range << shift) & MASK32
        self.count += shift

        if self.count >= 0:
            offset = shift - self.count
            self._put_byte(offset)
            self.low_value = (self.low_value << offset) & MASK32
            shift = self.count
            self.low_value &= 0x00FFFFFF
            self.count -= 8

        self.low_value = (self.low_value << shift) & MASK32
        self.bit_count += 1

    def flush(self) -> None:
        for _ in range(32):
            self.write(0, 128)

    def bytes(self) -> bytes:
        return bytes(self.out[: self.byte_pos])


def parse_uya_byte_array(name: str) -> list[int]:
    text = HEADER_SOURCE.read_text(encoding="utf-8")
    match = re.search(rf"var {name}: \[byte: \d+\] = \[(.*?)\];", text, re.S)
    if match is None:
        raise RuntimeError(f"could not find {name} in {HEADER_SOURCE}")
    return [int(value) for value in re.findall(r"\b\d+\b", match.group(1))]


DEFAULT_COEFF_PROBS = parse_uya_byte_array("VP8_DEFAULT_COEFF_PROBS")
COEFF_UPDATE_PROBS = parse_uya_byte_array("VP8_COEFF_UPDATE_PROBS")
MV_UPDATE_PROBS = parse_uya_byte_array("VP8_MV_UPDATE_PROBS")
Y_MODE_PROBS = [112, 86, 140, 37]
UV_MODE_PROBS = [162, 101, 204]


def write_literal(writer: BoolWriter, value: int, bit_count: int) -> None:
    for bit_index in range(bit_count - 1, -1, -1):
        writer.write((value >> bit_index) & 1, 128)


def coeff_prob_offset(block_type: int, position: int, context: int) -> int:
    band = COEFF_BANDS[position]
    return (((block_type * 8) + band) * 3 + context) * 11


def write_eob(writer: BoolWriter, block_type: int, position: int, context: int) -> None:
    writer.write(0, DEFAULT_COEFF_PROBS[coeff_prob_offset(block_type, position, context)])


def write_one_then_eob(writer: BoolWriter, block_type: int, position: int, context: int) -> None:
    offset = coeff_prob_offset(block_type, position, context)
    writer.write(1, DEFAULT_COEFF_PROBS[offset])
    writer.write(1, DEFAULT_COEFF_PROBS[offset + 1])
    writer.write(0, DEFAULT_COEFF_PROBS[offset + 2])
    writer.write(0, 128)
    write_eob(writer, block_type, position + 1, 1)


def write_uncompressed_key_partition(sample: Sample, mb_count: int) -> bytes:
    writer = BoolWriter(256)
    writer.write(0, 128)
    write_literal(writer, 0, 1)
    write_literal(writer, 0, 6)
    write_literal(writer, 0, 3)
    write_literal(writer, 0, 7)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    write_literal(writer, 0, 2)

    for probability in COEFF_UPDATE_PROBS:
        writer.write(0, probability)
    for probability in MV_UPDATE_PROBS:
        writer.write(0, probability)

    for _ in range(mb_count):
        writer.write(0, Y_MODE_PROBS[0])
        writer.write(0, UV_MODE_PROBS[0])

    writer.flush()
    encoded = writer.bytes()
    if len(encoded) > 256:
        raise RuntimeError(f"first partition too large for {sample.name}: {len(encoded)}")
    return encoded + bytes(256 - len(encoded))


def write_uncompressed_inter_partition(sample: Sample, mb_count: int) -> bytes:
    writer = BoolWriter(256)
    writer.write(0, 128)
    write_literal(writer, 0, 1)
    write_literal(writer, 0, 6)
    write_literal(writer, 0, 3)
    write_literal(writer, 0, 7)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    writer.write(0, 128)
    write_literal(writer, 0, 2)

    for probability in COEFF_UPDATE_PROBS:
        writer.write(0, probability)
    for probability in MV_UPDATE_PROBS:
        writer.write(0, probability)

    for _ in range(mb_count):
        writer.write(1, 145)
        writer.write(0, 156)
        writer.write(0, 2)

    writer.flush()
    encoded = writer.bytes()
    if len(encoded) > 256:
        raise RuntimeError(f"first partition too large for {sample.name}: {len(encoded)}")
    return encoded + bytes(256 - len(encoded))


def write_gray_mb_tokens(writer: BoolWriter) -> None:
    write_eob(writer, 1, 0, 0)
    for _ in range(16):
        write_eob(writer, 0, 1, 0)
    for _ in range(4):
        write_eob(writer, 2, 0, 0)
    for _ in range(4):
        write_eob(writer, 2, 0, 0)


def write_u_dc_mb_tokens(writer: BoolWriter) -> None:
    write_eob(writer, 1, 0, 0)
    for _ in range(16):
        write_eob(writer, 0, 1, 0)

    write_one_then_eob(writer, 2, 0, 0)
    write_eob(writer, 2, 0, 1)
    write_eob(writer, 2, 0, 1)
    write_eob(writer, 2, 0, 0)

    for _ in range(4):
        write_eob(writer, 2, 0, 0)


def write_v_dc_mb_tokens(writer: BoolWriter) -> None:
    write_eob(writer, 1, 0, 0)
    for _ in range(16):
        write_eob(writer, 0, 1, 0)
    for _ in range(4):
        write_eob(writer, 2, 0, 0)

    write_one_then_eob(writer, 2, 0, 0)
    write_eob(writer, 2, 0, 1)
    write_eob(writer, 2, 0, 1)
    write_eob(writer, 2, 0, 0)


def write_token_partition(sample: Sample, mb_count: int) -> bytes:
    writer = BoolWriter(4096)
    for mb_index in range(mb_count):
        if mb_index == 0 and sample.variant == "u-dc":
            write_u_dc_mb_tokens(writer)
        elif mb_index == 0 and sample.variant == "v-dc":
            write_v_dc_mb_tokens(writer)
        else:
            write_gray_mb_tokens(writer)
    writer.flush()
    return writer.bytes()


def write_inter_token_partition(mb_count: int) -> bytes:
    writer = BoolWriter(4096)
    for _ in range(mb_count):
        for _ in range(16):
            write_eob(writer, 0, 0, 0)
        for _ in range(8):
            write_eob(writer, 2, 0, 0)
    writer.flush()
    return writer.bytes()


def make_vp8_key_frame(sample: Sample) -> bytes:
    mb_cols = math.ceil(sample.width / 16)
    mb_rows = math.ceil(sample.height / 16)
    mb_count = mb_cols * mb_rows
    first_partition = write_uncompressed_key_partition(sample, mb_count)
    token_partition = write_token_partition(sample, mb_count)
    first_partition_size = 7 + len(first_partition)
    tag = (1 << 4) | (first_partition_size << 5)
    frame = bytearray()
    frame.extend(struct.pack("<I", tag)[:3])
    frame.extend(b"\x9d\x01\x2a")
    frame.extend(struct.pack("<H", sample.width))
    frame.extend(struct.pack("<H", sample.height))
    frame.extend(first_partition)
    frame.extend(token_partition)
    return bytes(frame)


def make_vp8_inter_frame(sample: Sample) -> bytes:
    mb_cols = math.ceil(sample.width / 16)
    mb_rows = math.ceil(sample.height / 16)
    mb_count = mb_cols * mb_rows
    first_partition = write_uncompressed_inter_partition(sample, mb_count)
    token_partition = write_inter_token_partition(mb_count)
    first_partition_size = len(first_partition)
    tag = 1 | (1 << 4) | (first_partition_size << 5)
    frame = bytearray()
    frame.extend(struct.pack("<I", tag)[:3])
    frame.extend(first_partition)
    frame.extend(token_partition)
    return bytes(frame)


def make_ivf(sample: Sample) -> bytes:
    if sample.variant == "inter-copy":
        key_sample = Sample(f"{sample.name}-key", sample.width, sample.height, "u-dc")
        frames = [make_vp8_key_frame(key_sample), make_vp8_inter_frame(sample)]
    else:
        frames = [make_vp8_key_frame(sample)]
    if len(frames) != sample.frame_count:
        raise RuntimeError(f"{sample.name}: expected {sample.frame_count} frames, generated {len(frames)}")

    header = bytearray()
    header.extend(b"DKIF")
    header.extend(struct.pack("<H", 0))
    header.extend(struct.pack("<H", 32))
    header.extend(b"VP80")
    header.extend(struct.pack("<H", sample.width))
    header.extend(struct.pack("<H", sample.height))
    header.extend(struct.pack("<I", 30))
    header.extend(struct.pack("<I", 1))
    header.extend(struct.pack("<I", len(frames)))
    header.extend(struct.pack("<I", 0))
    for index, frame in enumerate(frames):
        header.extend(struct.pack("<I", len(frame)))
        header.extend(struct.pack("<Q", index))
        header.extend(frame)
    return bytes(header)


def run_sample(bin_path: Path, out_dir: Path, sample: Sample) -> dict[str, object]:
    ivf_path = out_dir / f"{sample.name}.ivf"
    yuv_path = out_dir / f"{sample.name}.yuv"
    ivf_path.write_bytes(make_ivf(sample))
    subprocess.run(
        [str(bin_path), "decode", str(ivf_path), "--yuv", str(yuv_path)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    yuv = yuv_path.read_bytes()
    digest = hashlib.md5(yuv).hexdigest()
    expected_frame_size = sample.width * sample.height
    expected_frame_size += math.ceil(sample.width / 2) * math.ceil(sample.height / 2) * 2
    expected_size = expected_frame_size * sample.output_frames
    if len(yuv) != expected_size:
        raise RuntimeError(f"{sample.name}: expected {expected_size} YUV bytes, got {len(yuv)}")
    return {
        "name": sample.name,
        "width": sample.width,
        "height": sample.height,
        "variant": sample.variant,
        "ivf": str(ivf_path),
        "yuv": str(yuv_path),
        "yuv_bytes": len(yuv),
        "md5": digest,
        "expected_md5": EXPECTED_MD5[sample.name],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: tiny_ivf_md5.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    results = [run_sample(bin_path, out_dir, sample) for sample in SAMPLES]
    (out_dir / "manifest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    failures = []
    for result in results:
        if result["md5"] != result["expected_md5"]:
            failures.append(result)

    if failures:
        for failure in failures:
            print(
                f"{failure['name']}: expected {failure['expected_md5']} got {failure['md5']}",
                file=sys.stderr,
            )
        return 1

    for result in results:
        print(f"{result['name']} {result['md5']} {result['yuv_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
