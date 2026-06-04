#!/usr/bin/env python3
"""Contract checks for libvpx encoder comparison metrics."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bench" / "libvpx_encode_compare.py"

REQUIRED_FIELDS = {
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
}


def load_module():
    spec = importlib.util.spec_from_file_location("libvpx_encode_compare", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contract(contract: dict[str, object]) -> None:
    fields = set(contract["required_result_fields"])
    missing = REQUIRED_FIELDS - fields
    if missing:
        raise AssertionError(f"missing required metric fields: {sorted(missing)}")

    thresholds = contract["thresholds"]
    assert thresholds["max_bitrate_ratio"] == 1.10
    assert thresholds["min_psnr_all_delta_db"] == -0.50
    assert thresholds["min_fps_ratio"] == 0.80
    assert contract["libvpx_preset"] == "vpxenc --best"


def make_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "sample": "unit",
        "width": 16,
        "height": 16,
        "frames": 1,
        "fps": "30/1",
        "vp8uya_bits_per_pixel": 1.0,
        "libvpx_bits_per_pixel": 1.0,
        "vp8uya_psnr_all_db": 40.0,
        "libvpx_psnr_all_db": 40.0,
        "vp8uya_ssim_all": 0.99,
        "libvpx_ssim_all": 0.99,
        "vp8uya_fps": 100.0,
        "libvpx_fps": 100.0,
    }
    result.update(overrides)
    return result


def assert_bitrate_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.10, libvpx_bits_per_pixel=1.0)
    )
    assert passing["passed"] is True
    assert passing["bitrate_ratio"] == 1.10
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.11, libvpx_bits_per_pixel=1.0)
    )
    assert failing["passed"] is False
    assert failing["bitrate_ratio"] == 1.11
    assert any("bitrate_ratio" in reason for reason in failing["failure_reasons"])


def assert_psnr_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.50, libvpx_psnr_all_db=40.0)
    )
    assert passing["passed"] is True
    assert passing["psnr_all_delta_db"] == -0.50
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.49, libvpx_psnr_all_db=40.0)
    )
    assert failing["passed"] is False
    assert failing["psnr_all_delta_db"] == -0.51
    assert any("psnr_all_delta_db" in reason for reason in failing["failure_reasons"])


def assert_fps_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_fps=80.0, libvpx_fps=100.0)
    )
    assert passing["passed"] is True
    assert passing["fps_ratio"] == 0.80
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_fps=79.0, libvpx_fps=100.0)
    )
    assert failing["passed"] is False
    assert failing["fps_ratio"] == 0.79
    assert any("fps_ratio" in reason for reason in failing["failure_reasons"])


def assert_ssim_is_record_only(module: object) -> None:
    contract = module.metric_contract()
    fields = set(contract["required_result_fields"])
    hard_threshold_fields = set(contract["hard_threshold_fields"])
    assert "vp8uya_ssim_all" in fields
    assert "libvpx_ssim_all" in fields
    assert "vp8uya_ssim_all" not in hard_threshold_fields
    assert "libvpx_ssim_all" not in hard_threshold_fields

    evaluated = module.evaluate_thresholds(
        make_result(vp8uya_ssim_all=0.10, libvpx_ssim_all=0.99)
    )
    assert evaluated["passed"] is True
    assert not any("ssim" in reason.lower() for reason in evaluated["failure_reasons"])


def write_fake_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def write_fake_help_version_tool(path: Path, version_line: str) -> None:
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo unsupported >&2\n"
        "  exit 1\n"
        "fi\n"
        "if [ \"$1\" = \"--help\" ]; then\n"
        f"  echo '{version_line}'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def assert_vpxenc_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxenc"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXENC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxenc")
        missing = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXENC"
        assert "VPXENC" in missing["error"]
        assert missing_path in missing["error"]


def assert_vpxdec_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxdec"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXDEC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxdec")
        missing = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXDEC"
        assert "VPXDEC" in missing["error"]
        assert missing_path in missing["error"]


def assert_probe_tools_path_lookup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_executable(tmp_path / "vpxenc")
        write_fake_executable(tmp_path / "vpxdec")
        env = dict(os.environ)
        env["PATH"] = str(tmp_path)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--probe-tools"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        report = json.loads(completed.stdout)
        assert report["vpxenc"]["source"] == "PATH"
        assert report["vpxenc"]["path"] == str(tmp_path / "vpxenc")
        assert report["vpxenc"]["version_returncode"] == 0
        assert report["vpxenc"]["probe_returncode"] == 0
        assert report["vpxdec"]["source"] == "PATH"
        assert report["vpxdec"]["path"] == str(tmp_path / "vpxdec")
        assert report["vpxdec"]["version_returncode"] == 0
        assert report["vpxdec"]["probe_returncode"] == 0


def assert_probe_tools_help_version_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_help_version_tool(tmp_path / "vpxenc", "vp8 - WebM Project VP8 Encoder v9.8.7")
        write_fake_help_version_tool(tmp_path / "vpxdec", "vp8 - WebM Project VP8 Decoder v9.8.7")
        env = dict(os.environ)
        env["PATH"] = str(tmp_path)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--probe-tools"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        report = json.loads(completed.stdout)
        assert report["vpxenc_version"] == "vp8 - WebM Project VP8 Encoder v9.8.7"
        assert report["vpxenc"]["version_source"] == "help"
        assert report["vpxdec_version"] == "vp8 - WebM Project VP8 Decoder v9.8.7"
        assert report["vpxdec"]["version_source"] == "help"


def assert_extracted_dir_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_executable(tmp_path / "vpxenc")
        write_fake_executable(tmp_path / "vpxdec")

        vpxenc = module.find_vpx_tool("vpxenc", "VPXENC", env={}, path="", extracted_dir=tmp_path)
        assert vpxenc["path"] == str(tmp_path / "vpxenc")
        assert vpxenc["source"] == "extracted"
        assert vpxenc["error"] is None

        vpxdec = module.find_vpx_tool("vpxdec", "VPXDEC", env={}, path="", extracted_dir=tmp_path)
        assert vpxdec["path"] == str(tmp_path / "vpxdec")
        assert vpxdec["source"] == "extracted"
        assert vpxdec["error"] is None


def assert_missing_tool_error(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = module.find_vpx_tool("vpxenc", "VPXENC", env={}, path="", extracted_dir=Path(tmp))
        assert missing["path"] is None
        assert "vpxenc" in missing["error"]
        assert "VPXENC" in missing["error"]
        assert "PATH" in missing["error"]
        assert "vpx-tools" in missing["error"]
        assert "--fetch-vpx-tools" in missing["error"]
        assert "--extract-vpx-tools" in missing["error"]


def assert_fetch_vpx_tools_download(module: object) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if "sudo" in command:
            return subprocess.CompletedProcess(command, 1, "", "sudo must not be used")
        (cwd / "vpx-tools_1.0_test_amd64.deb").write_bytes(b"fake deb")
        return subprocess.CompletedProcess(command, 0, "downloaded\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        report = module.fetch_vpx_tools(download_dir=Path(tmp), runner=fake_runner)
        assert report["ok"] is True
        assert calls == [(["apt-get", "download", "vpx-tools"], Path(tmp))]
        assert report["command"] == ["apt-get", "download", "vpx-tools"]
        assert report["deb_files"] == [str(Path(tmp) / "vpx-tools_1.0_test_amd64.deb")]


def assert_extract_vpx_tools(module: object) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if "sudo" in command:
            return subprocess.CompletedProcess(command, 1, "", "sudo must not be used")
        root = Path(command[3])
        bin_dir = root / "usr" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        write_fake_executable(bin_dir / "vpxenc")
        write_fake_executable(bin_dir / "vpxdec")
        return subprocess.CompletedProcess(command, 0, "extracted\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        deb = tmp_path / "vpx-tools_1.0_test_amd64.deb"
        deb.write_bytes(b"fake deb")
        root = tmp_path / "vpx-tools-root"
        report = module.extract_vpx_tools(deps_dir=tmp_path, extract_root=root, runner=fake_runner)
        assert report["ok"] is True
        assert calls == [(["dpkg-deb", "-x", str(deb), str(root)], tmp_path)]
        assert report["command"] == ["dpkg-deb", "-x", str(deb), str(root)]
        assert report["vpxenc"] == str(root / "usr" / "bin" / "vpxenc")
        assert report["vpxdec"] == str(root / "usr" / "bin" / "vpxdec")


def assert_prepare_sample_dirs(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        y4m_dir = root / "real-y4m"
        i420_dir = root / "fixtures"
        report = module.prepare_sample_dirs(y4m_dir=y4m_dir, i420_dir=i420_dir)
        assert report["ok"] is True
        assert report["y4m_cache_dir"] == str(y4m_dir)
        assert report["i420_cache_dir"] == str(i420_dir)
        assert y4m_dir.is_dir()
        assert i420_dir.is_dir()

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--prepare-sample-dirs",
                "--y4m-cache-dir",
                str(root / "cli-real-y4m"),
                "--i420-cache-dir",
                str(root / "cli-fixtures"),
            ],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        cli_report = json.loads(completed.stdout)
        assert cli_report["ok"] is True
        assert (root / "cli-real-y4m").is_dir()
        assert (root / "cli-fixtures").is_dir()


def main() -> int:
    module = load_module()
    assert_contract(module.metric_contract())
    assert_bitrate_threshold(module)
    assert_psnr_threshold(module)
    assert_fps_threshold(module)
    assert_ssim_is_record_only(module)
    assert_vpxenc_env_lookup(module)
    assert_vpxdec_env_lookup(module)
    assert_probe_tools_path_lookup()
    assert_probe_tools_help_version_fallback()
    assert_extracted_dir_lookup(module)
    assert_missing_tool_error(module)
    assert_fetch_vpx_tools_download(module)
    assert_extract_vpx_tools(module)
    assert_prepare_sample_dirs(module)

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--print-metric-contract"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout)
    assert_contract(json.loads(completed.stdout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
