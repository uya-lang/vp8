#!/usr/bin/env python3
"""Compare vp8uya encoder output against libvpx.

The first landed surface is the machine-readable metric contract used by the
future benchmark and threshold gate. Real sample execution is added later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPS_DIR = REPO_ROOT / "build" / "deps"
DEFAULT_VPX_TOOLS_ROOT = DEFAULT_DEPS_DIR / "vpx-tools-root"
DEFAULT_VPX_TOOLS_DIR = DEFAULT_VPX_TOOLS_ROOT / "usr" / "bin"
DEFAULT_Y4M_CACHE_DIR = REPO_ROOT / "build" / "real-y4m"
DEFAULT_I420_CACHE_DIR = REPO_ROOT / "build" / "libvpx-encode-compare" / "fixtures"
DEFAULT_VP8UYA_BIN = REPO_ROOT / "build" / "vp8uya"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "fixtures" / "encoder_libvpx_real_samples.json"
LIBVPX_PRESET = "vpxenc --best"

REQUIRED_RESULT_FIELDS = (
    "sample",
    "width",
    "height",
    "frames",
    "fps",
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "bitrate_ratio",
    "vp8uya_psnr_y_db",
    "vp8uya_psnr_u_db",
    "vp8uya_psnr_v_db",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_y_db",
    "libvpx_psnr_u_db",
    "libvpx_psnr_v_db",
    "libvpx_psnr_all_db",
    "psnr_all_delta_db",
    "vp8uya_ssim_all",
    "libvpx_ssim_all",
    "vp8uya_fps",
    "libvpx_fps",
    "fps_ratio",
    "passed",
    "failure_reasons",
)

REQUIRED_SUMMARY_FIELDS = (
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
    "vpxenc_version",
    "vpxdec_version",
)

HARD_THRESHOLD_FIELDS = (
    "bitrate_ratio",
    "psnr_all_delta_db",
    "fps_ratio",
)

THRESHOLDS = {
    "max_bitrate_ratio": 1.10,
    "min_psnr_all_delta_db": -0.50,
    "min_fps_ratio": 0.80,
}


def tool_lookup_result(path: str | None, source: str | None, error: str | None, attempted: list[str]) -> dict[str, Any]:
    return {
        "path": path,
        "source": source,
        "error": error,
        "attempted": attempted,
    }


def is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def validate_vp8uya_binary(path: Path) -> dict[str, Any]:
    if is_executable_file(path):
        return {
            "ok": True,
            "path": str(path),
            "error": None,
        }
    return {
        "ok": False,
        "path": str(path),
        "error": f"vp8uya binary not found or not executable: {path}",
    }


def positive_int_arg(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def extract_help_version(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if "WebM Project VP8" in stripped and ("Encoder" in stripped or "Decoder" in stripped):
            return stripped
    return ""


def attach_tool_metadata(lookup: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(lookup)
    path = enriched.get("path")
    if path is None:
        enriched["version_returncode"] = None
        enriched["version_stdout"] = ""
        enriched["version_stderr"] = ""
        enriched["version"] = None
        enriched["probe_command"] = []
        enriched["probe_returncode"] = None
        enriched["probe_stdout"] = ""
        enriched["probe_stderr"] = ""
        return enriched

    version_completed = run_command([str(path), "--version"], REPO_ROOT)
    stdout = version_completed.stdout.strip()
    stderr = version_completed.stderr.strip()
    version_line = first_nonempty_line(stdout)
    if not version_line:
        version_line = first_nonempty_line(stderr)
    enriched["version_returncode"] = version_completed.returncode
    enriched["version_stdout"] = stdout
    enriched["version_stderr"] = stderr
    enriched["version"] = version_line
    enriched["version_source"] = "version" if version_completed.returncode == 0 else "version-error"

    if version_completed.returncode == 0:
        enriched["probe_command"] = [str(path), "--version"]
        enriched["probe_returncode"] = 0
        enriched["probe_stdout"] = stdout
        enriched["probe_stderr"] = stderr
        return enriched

    help_completed = run_command([str(path), "--help"], REPO_ROOT)
    help_stdout = help_completed.stdout.strip()
    help_stderr = help_completed.stderr.strip()
    enriched["probe_command"] = [str(path), "--help"]
    enriched["probe_returncode"] = help_completed.returncode
    enriched["probe_stdout"] = help_stdout
    enriched["probe_stderr"] = help_stderr
    help_version = extract_help_version(help_stdout)
    if not help_version:
        help_version = extract_help_version(help_stderr)
    if help_version:
        enriched["version"] = help_version
        enriched["version_source"] = "help"
    if help_completed.returncode != 0:
        enriched["error"] = f"{path} --help failed with exit {help_completed.returncode}"
    return enriched


def find_vpx_tool(
    name: str,
    env_var: str,
    *,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
    extracted_dir: Path | None = None,
) -> dict[str, Any]:
    env_map = os.environ if env is None else env
    search_path = env_map.get("PATH", os.environ.get("PATH", "")) if path is None else path
    tool_dir = DEFAULT_VPX_TOOLS_DIR if extracted_dir is None else extracted_dir
    attempted: list[str] = []

    env_value = env_map.get(env_var)
    if env_value:
        attempted.append(env_value)
        env_path = Path(env_value)
        if is_executable_file(env_path):
            return tool_lookup_result(str(env_path), env_var, None, attempted)
        return tool_lookup_result(
            None,
            env_var,
            f"{env_var} points to a missing or non-executable {name}: {env_value}",
            attempted,
        )

    path_value = shutil.which(name, path=search_path)
    if path_value is not None:
        attempted.append(path_value)
        return tool_lookup_result(path_value, "PATH", None, attempted)

    extracted_path = tool_dir / name
    attempted.append(str(extracted_path))
    if is_executable_file(extracted_path):
        return tool_lookup_result(str(extracted_path), "extracted", None, attempted)

    return tool_lookup_result(
        None,
        None,
        f"{name} not found; set {env_var}, add {name} to PATH, or run "
        "python3 bench/libvpx_encode_compare.py --fetch-vpx-tools followed by "
        "python3 bench/libvpx_encode_compare.py --extract-vpx-tools to fetch vpx-tools",
        attempted,
    )


def fetch_vpx_tools(
    *,
    download_dir: Path = DEFAULT_DEPS_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    download_dir.mkdir(parents=True, exist_ok=True)
    command = ["apt-get", "download", "vpx-tools"]
    try:
        completed = runner(command, download_dir)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "download_dir": str(download_dir),
            "deb_files": [],
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    deb_files = sorted(download_dir.glob("vpx-tools_*.deb"))
    return {
        "ok": completed.returncode == 0 and len(deb_files) > 0,
        "command": command,
        "download_dir": str(download_dir),
        "deb_files": [str(path) for path in deb_files],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def latest_vpx_tools_deb(deps_dir: Path) -> Path | None:
    debs = sorted(deps_dir.glob("vpx-tools_*.deb"))
    if not debs:
        return None
    return debs[-1]


def extract_vpx_tools(
    *,
    deps_dir: Path = DEFAULT_DEPS_DIR,
    extract_root: Path = DEFAULT_VPX_TOOLS_ROOT,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    deb = latest_vpx_tools_deb(deps_dir)
    if deb is None:
        return {
            "ok": False,
            "command": [],
            "deps_dir": str(deps_dir),
            "extract_root": str(extract_root),
            "vpxenc": str(extract_root / "usr" / "bin" / "vpxenc"),
            "vpxdec": str(extract_root / "usr" / "bin" / "vpxdec"),
            "returncode": None,
            "stdout": "",
            "stderr": "no vpx-tools .deb found",
        }

    deps_dir.mkdir(parents=True, exist_ok=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    command = ["dpkg-deb", "-x", str(deb), str(extract_root)]
    try:
        completed = runner(command, deps_dir)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "deps_dir": str(deps_dir),
            "extract_root": str(extract_root),
            "vpxenc": str(extract_root / "usr" / "bin" / "vpxenc"),
            "vpxdec": str(extract_root / "usr" / "bin" / "vpxdec"),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    vpxenc = extract_root / "usr" / "bin" / "vpxenc"
    vpxdec = extract_root / "usr" / "bin" / "vpxdec"
    return {
        "ok": completed.returncode == 0 and is_executable_file(vpxenc) and is_executable_file(vpxdec),
        "command": command,
        "deps_dir": str(deps_dir),
        "extract_root": str(extract_root),
        "vpxenc": str(vpxenc),
        "vpxdec": str(vpxdec),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def prepare_sample_dirs(
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
) -> dict[str, Any]:
    y4m_dir.mkdir(parents=True, exist_ok=True)
    i420_dir.mkdir(parents=True, exist_ok=True)
    return {
        "ok": y4m_dir.is_dir() and i420_dir.is_dir(),
        "y4m_cache_dir": str(y4m_dir),
        "i420_cache_dir": str(i420_dir),
    }


def load_sample_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"failed to read sample manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse sample manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"sample manifest {path} must contain an object")
    samples = data.get("samples")
    if not isinstance(samples, list):
        raise ValueError(f"sample manifest {path} must contain a samples array")
    return data


def manifest_samples(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_samples = manifest.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("sample manifest must contain a samples array")

    samples: list[dict[str, Any]] = []
    for index, raw_sample in enumerate(raw_samples):
        if not isinstance(raw_sample, dict):
            raise ValueError(f"sample manifest entry {index} must be an object")
        name = raw_sample.get("name")
        groups = raw_sample.get("groups")
        if not isinstance(name, str) or not name:
            raise ValueError(f"sample manifest entry {index} must have a non-empty name")
        if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
            raise ValueError(f"sample manifest entry {name} must have string groups")
        samples.append(dict(raw_sample))
    return samples


def filter_samples_by_group(samples: list[dict[str, Any]], group: str | None) -> list[dict[str, Any]]:
    if group is None:
        return list(samples)
    return [sample for sample in samples if group in sample["groups"]]


def dry_run_samples(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
) -> dict[str, Any]:
    try:
        manifest = load_sample_manifest(manifest_path)
        selected = filter_samples_by_group(manifest_samples(manifest), group)
    except ValueError as exc:
        return {
            "ok": False,
            "manifest_path": str(manifest_path),
            "group": group,
            "samples": [],
            "error": str(exc),
        }

    planned_samples: list[dict[str, Any]] = []
    for sample in selected:
        planned = dict(sample)
        if frames_override is not None:
            planned["manifest_frames"] = planned.get("frames")
            planned["frames"] = frames_override
        planned_samples.append(planned)

    return {
        "ok": True,
        "manifest_path": str(manifest_path),
        "group": group,
        "frames_override": frames_override,
        "samples": planned_samples,
        "sample_count": len(planned_samples),
    }


def http_download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        with dest.open("wb") as out:
            shutil.copyfileobj(response, out)


def sample_y4m_path(sample: Mapping[str, Any], y4m_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return y4m_dir / f"{name}.y4m"


def download_y4m_sample(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    downloader: Callable[[str, Path], None] = http_download,
) -> dict[str, Any]:
    y4m_dir.mkdir(parents=True, exist_ok=True)
    try:
        url = sample["url"]
        if not isinstance(url, str) or not url:
            raise ValueError("sample url must be a non-empty string")
        final_path = sample_y4m_path(sample, y4m_dir)
    except (KeyError, ValueError) as exc:
        return {
            "ok": False,
            "cached": False,
            "path": "",
            "partial_path": "",
            "url": "",
            "error": str(exc),
        }

    partial_path = final_path.with_name(final_path.name + ".part")
    if final_path.exists():
        return {
            "ok": True,
            "cached": True,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": None,
        }

    if partial_path.exists():
        partial_path.unlink()

    try:
        downloader(url, partial_path)
        if not partial_path.exists() or partial_path.stat().st_size <= 0:
            raise RuntimeError("download produced an empty file")
        partial_path.replace(final_path)
        return {
            "ok": True,
            "cached": False,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": None,
        }
    except Exception as exc:
        if partial_path.exists():
            partial_path.unlink()
        return {
            "ok": False,
            "cached": False,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": str(exc),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_y4m_sample_sha256(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
) -> dict[str, Any]:
    try:
        expected = sample["sha256"]
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("sample sha256 must be a 64-character hex string")
        path = sample_y4m_path(sample, y4m_dir)
    except (KeyError, ValueError) as exc:
        return {
            "ok": False,
            "path": "",
            "expected_sha256": "",
            "actual_sha256": "",
            "error": str(exc),
        }

    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "expected_sha256": expected,
            "actual_sha256": "",
            "error": f"missing downloaded sample: {path}",
        }

    actual = sha256_file(path)
    if actual == expected.lower():
        return {
            "ok": True,
            "path": str(path),
            "expected_sha256": expected.lower(),
            "actual_sha256": actual,
            "error": None,
        }

    bad_path = path.with_name(path.name + ".bad-sha256")
    if bad_path.exists():
        bad_path.unlink()
    path.replace(bad_path)
    return {
        "ok": False,
        "path": str(path),
        "bad_path": str(bad_path),
        "expected_sha256": expected.lower(),
        "actual_sha256": actual,
        "error": f"sha256 mismatch for {path}: expected {expected.lower()} got {actual}",
    }


def ensure_y4m_sample(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    downloader: Callable[[str, Path], None] = http_download,
) -> dict[str, Any]:
    try:
        path = sample_y4m_path(sample, y4m_dir)
    except ValueError as exc:
        return {
            "ok": False,
            "download": None,
            "sha256": None,
            "error": str(exc),
        }

    if path.exists():
        sha_report = verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
        if sha_report["ok"]:
            return {
                "ok": True,
                "download": {
                    "ok": True,
                    "cached": True,
                    "path": str(path),
                    "partial_path": str(path.with_name(path.name + ".part")),
                    "url": sample.get("url", ""),
                    "error": None,
                },
                "sha256": sha_report,
                "error": None,
            }
        return {
            "ok": False,
            "download": None,
            "sha256": sha_report,
            "error": sha_report["error"],
        }

    download_report = download_y4m_sample(sample, y4m_dir=y4m_dir, downloader=downloader)
    if not download_report["ok"]:
        return {
            "ok": False,
            "download": download_report,
            "sha256": None,
            "error": download_report["error"],
        }
    sha_report = verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
    return {
        "ok": sha_report["ok"],
        "download": download_report,
        "sha256": sha_report,
        "error": None if sha_report["ok"] else sha_report["error"],
    }


def sample_i420_path(sample: Mapping[str, Any], i420_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return i420_dir / f"{name}.i420"


def sample_frames(sample: Mapping[str, Any]) -> int:
    frames = sample.get("frames", 60)
    if not isinstance(frames, int) or frames <= 0:
        raise ValueError("sample frames must be a positive integer")
    return frames


def sample_dimension(sample: Mapping[str, Any], field: str) -> int:
    value = sample.get(field)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"sample {field} must be a positive integer")
    return value


def i420_frame_size(width: int, height: int) -> int:
    if width <= 0 or height <= 0:
        raise ValueError("I420 width and height must be positive")
    chroma_width = (width + 1) // 2
    chroma_height = (height + 1) // 2
    return (width * height) + (2 * chroma_width * chroma_height)


def validate_i420_sample_size(
    sample: Mapping[str, Any],
    *,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
) -> dict[str, Any]:
    try:
        output_path = sample_i420_path(sample, i420_dir)
        width = sample_dimension(sample, "width")
        height = sample_dimension(sample, "height")
        frames = sample_frames(sample)
        expected = i420_frame_size(width, height) * frames
    except ValueError as exc:
        return {
            "ok": False,
            "path": "",
            "expected_bytes": 0,
            "actual_bytes": 0,
            "error": str(exc),
        }

    if not output_path.exists():
        return {
            "ok": False,
            "path": str(output_path),
            "expected_bytes": expected,
            "actual_bytes": 0,
            "error": f"missing I420 output: {output_path}",
        }

    actual = output_path.stat().st_size
    if actual != expected:
        return {
            "ok": False,
            "path": str(output_path),
            "expected_bytes": expected,
            "actual_bytes": actual,
            "error": f"I420 size mismatch for {output_path}: expected {expected} got {actual}",
        }

    return {
        "ok": True,
        "path": str(output_path),
        "expected_bytes": expected,
        "actual_bytes": actual,
        "error": None,
    }


def convert_y4m_to_i420(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    try:
        input_path = sample_y4m_path(sample, y4m_dir)
        output_path = sample_i420_path(sample, i420_dir)
        frames = sample_frames(sample)
    except ValueError as exc:
        return {
            "ok": False,
            "command": [],
            "input_path": "",
            "output_path": "",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    if not input_path.exists():
        return {
            "ok": False,
            "command": [],
            "input_path": str(input_path),
            "output_path": str(output_path),
            "returncode": None,
            "stdout": "",
            "stderr": f"missing Y4M input: {input_path}",
        }

    i420_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-frames:v",
        str(frames),
        "-pix_fmt",
        "yuv420p",
        "-f",
        "rawvideo",
        str(output_path),
    ]
    try:
        completed = runner(command, REPO_ROOT)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    return {
        "ok": completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0,
        "command": command,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def require_number(result: dict[str, Any], field: str) -> float:
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def metric_contract() -> dict[str, Any]:
    return {
        "libvpx_preset": LIBVPX_PRESET,
        "required_result_fields": list(REQUIRED_RESULT_FIELDS),
        "required_summary_fields": list(REQUIRED_SUMMARY_FIELDS),
        "hard_threshold_fields": list(HARD_THRESHOLD_FIELDS),
        "thresholds": dict(THRESHOLDS),
    }


def probe_tools(*, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    vpxenc = attach_tool_metadata(find_vpx_tool("vpxenc", "VPXENC", env=env))
    vpxdec = attach_tool_metadata(find_vpx_tool("vpxdec", "VPXDEC", env=env))
    return {
        "ok": (
            vpxenc["path"] is not None
            and vpxdec["path"] is not None
            and vpxenc["probe_returncode"] == 0
            and vpxdec["probe_returncode"] == 0
        ),
        "vpxenc": vpxenc,
        "vpxenc_probe_returncode": vpxenc["probe_returncode"],
        "vpxdec": vpxdec,
        "vpxdec_probe_returncode": vpxdec["probe_returncode"],
        "vpxenc_version": vpxenc["version"],
        "vpxdec_version": vpxdec["version"],
    }


def evaluate_thresholds(result: dict[str, Any]) -> dict[str, Any]:
    evaluated = dict(result)
    failure_reasons: list[str] = []

    try:
        vp8uya_bpp = require_number(evaluated, "vp8uya_bits_per_pixel")
        libvpx_bpp = require_number(evaluated, "libvpx_bits_per_pixel")
        if libvpx_bpp <= 0.0:
            evaluated["bitrate_ratio"] = float("inf")
            failure_reasons.append("libvpx_bits_per_pixel must be positive")
        else:
            bitrate_ratio = vp8uya_bpp / libvpx_bpp
            evaluated["bitrate_ratio"] = bitrate_ratio
            if bitrate_ratio > THRESHOLDS["max_bitrate_ratio"]:
                failure_reasons.append(
                    "bitrate_ratio "
                    f"{bitrate_ratio:.6f} exceeds max {THRESHOLDS['max_bitrate_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_psnr = require_number(evaluated, "vp8uya_psnr_all_db")
        libvpx_psnr = require_number(evaluated, "libvpx_psnr_all_db")
        psnr_delta = round(vp8uya_psnr - libvpx_psnr, 6)
        evaluated["psnr_all_delta_db"] = psnr_delta
        if psnr_delta < THRESHOLDS["min_psnr_all_delta_db"]:
            failure_reasons.append(
                "psnr_all_delta_db "
                f"{psnr_delta:.6f} below min {THRESHOLDS['min_psnr_all_delta_db']:.6f}"
            )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_fps = require_number(evaluated, "vp8uya_fps")
        libvpx_fps = require_number(evaluated, "libvpx_fps")
        if libvpx_fps <= 0.0:
            evaluated["fps_ratio"] = 0.0
            failure_reasons.append("libvpx_fps must be positive")
        else:
            fps_ratio = round(vp8uya_fps / libvpx_fps, 6)
            evaluated["fps_ratio"] = fps_ratio
            if fps_ratio < THRESHOLDS["min_fps_ratio"]:
                failure_reasons.append(
                    "fps_ratio "
                    f"{fps_ratio:.6f} below min {THRESHOLDS['min_fps_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    evaluated["failure_reasons"] = failure_reasons
    evaluated["passed"] = len(failure_reasons) == 0
    return evaluated


def evaluate_result_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {
            "passed": False,
            "failure_reasons": [f"failed to read result JSON {path}: {exc}"],
        }
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "failure_reasons": [f"failed to parse result JSON {path}: {exc}"],
        }

    if not isinstance(data, dict):
        return {
            "passed": False,
            "failure_reasons": [f"result JSON {path} must contain an object"],
        }
    return evaluate_thresholds(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare vp8uya encoder output against libvpx")
    parser.add_argument(
        "--print-metric-contract",
        action="store_true",
        help="print the required benchmark metric names and hard thresholds as JSON",
    )
    parser.add_argument(
        "--probe-tools",
        action="store_true",
        help="locate vpxenc/vpxdec and print the lookup result as JSON",
    )
    parser.add_argument(
        "--fetch-vpx-tools",
        action="store_true",
        help="download vpx-tools .deb into build/deps without sudo",
    )
    parser.add_argument(
        "--extract-vpx-tools",
        action="store_true",
        help="extract the downloaded vpx-tools .deb into build/deps/vpx-tools-root",
    )
    parser.add_argument(
        "--prepare-sample-dirs",
        action="store_true",
        help="create real Y4M and converted I420 cache directories",
    )
    parser.add_argument(
        "--evaluate-result-json",
        type=Path,
        help="read one benchmark result JSON object, apply hard thresholds, and return non-zero on failure",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected sample plan without downloading, encoding, or decoding",
    )
    parser.add_argument(
        "--group",
        help="only select samples whose manifest groups include this value",
    )
    parser.add_argument(
        "--frames",
        type=positive_int_arg,
        help="override each selected sample frame count",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"path to the real-sample manifest, defaulting to {DEFAULT_MANIFEST_PATH}",
    )
    parser.add_argument(
        "--vp8uya-bin",
        type=Path,
        default=None,
        help=f"path to the vp8uya binary, defaulting to {DEFAULT_VP8UYA_BIN}",
    )
    parser.add_argument(
        "--y4m-cache-dir",
        type=Path,
        default=DEFAULT_Y4M_CACHE_DIR,
        help="directory for downloaded Y4M samples",
    )
    parser.add_argument(
        "--i420-cache-dir",
        type=Path,
        default=DEFAULT_I420_CACHE_DIR,
        help="directory for converted raw I420 samples",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.vp8uya_bin is not None:
        report = validate_vp8uya_binary(args.vp8uya_bin)
        if not report["ok"]:
            print(report["error"], file=sys.stderr)
            return 2
    if args.print_metric_contract:
        print(json.dumps(metric_contract(), indent=2, sort_keys=True))
        return 0
    if args.probe_tools:
        report = probe_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        if not report["ok"]:
            for tool_name in ("vpxenc", "vpxdec"):
                error = report[tool_name].get("error")
                if error:
                    print(error, file=sys.stderr)
        return 0 if report["ok"] else 2
    if args.fetch_vpx_tools:
        report = fetch_vpx_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.extract_vpx_tools:
        report = extract_vpx_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.dry_run:
        report = dry_run_samples(
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.prepare_sample_dirs:
        report = prepare_sample_dirs(y4m_dir=args.y4m_cache_dir, i420_dir=args.i420_cache_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.evaluate_result_json is not None:
        report = evaluate_result_json(args.evaluate_result_json)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2

    print("error: no action requested; use --print-metric-contract, --probe-tools, --fetch-vpx-tools, --extract-vpx-tools, --dry-run, --prepare-sample-dirs, or --evaluate-result-json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
