#!/usr/bin/env python3
import struct
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"ivf-timestamps error: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        return fail("usage: ivf_timestamps.py <file.ivf> <timestamp>...")

    path = Path(argv[1])
    try:
        expected = [int(value, 0) for value in argv[2:]]
    except ValueError as exc:
        return fail(f"invalid expected timestamp: {exc}")

    data = path.read_bytes()
    if len(data) < 32:
        return fail("file is too short for an IVF header")
    if data[:4] != b"DKIF":
        return fail("invalid IVF signature")
    if data[8:12] != b"VP80":
        return fail("unsupported IVF fourcc")

    header_size = struct.unpack_from("<H", data, 6)[0]
    frame_count = struct.unpack_from("<I", data, 24)[0]
    if header_size < 32:
        return fail(f"invalid header size {header_size}")
    if frame_count != len(expected):
        return fail(f"frame_count={frame_count} expected={len(expected)}")

    offset = header_size
    observed: list[int] = []
    for frame_index in range(len(expected)):
        if offset + 12 > len(data):
            return fail(f"frame {frame_index} header is truncated")
        payload_size = struct.unpack_from("<I", data, offset)[0]
        timestamp = struct.unpack_from("<Q", data, offset + 4)[0]
        observed.append(timestamp)
        offset += 12 + payload_size
        if offset > len(data):
            return fail(f"frame {frame_index} payload is truncated")

    if offset != len(data):
        return fail(f"extra data after expected frames: {len(data) - offset} bytes")
    if observed != expected:
        return fail(f"timestamps={observed} expected={expected}")

    print("ivf-timestamps result=ok timestamps=" + ",".join(str(value) for value in observed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
