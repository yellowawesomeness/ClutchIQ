from pathlib import Path
import zipfile
import pytest
from clutchiq.radar_assets.source2viewer import Source2ViewerError, _install_download, _runtime


def test_full_bundle_is_extracted(tmp_path: Path) -> None:
 archive = tmp_path / "cli-windows-x64.zip"
 with zipfile.ZipFile(archive, "w") as file:
  file.writestr("cli-windows-x64/Source2Viewer-CLI.exe", b"cli")
  file.writestr("cli-windows-x64/SkiaSharp.dll", b"managed")
  file.writestr("cli-windows-x64/runtimes/win-x64/native/libSkiaSharp.dll", b"native")
  file.writestr("cli-windows-x64/sidecar.dll", b"sidecar")
 tool = _install_download(archive, tmp_path / "bundle")
 assert tool.read_bytes() == b"cli"
 assert (tool.parent / "SkiaSharp.dll").read_bytes() == b"managed"
 assert (tool.parent / "runtimes/win-x64/native/libSkiaSharp.dll").read_bytes() == b"native"
 assert (tool.parent / "sidecar.dll").read_bytes() == b"sidecar"
 assert _runtime(tool).name == "libSkiaSharp.dll"


def test_archive_without_cli_is_rejected(tmp_path: Path) -> None:
 archive = tmp_path / "cli-windows-x64.zip"
 with zipfile.ZipFile(archive, "w") as file: file.writestr("tools/Other.exe", b"x")
 with pytest.raises(Source2ViewerError, match="exactly one"):
  _install_download(archive, tmp_path / "bundle")


def test_unsafe_archive_member_is_rejected(tmp_path: Path) -> None:
 archive = tmp_path / "cli-windows-x64.zip"
 with zipfile.ZipFile(archive, "w") as file:
  file.writestr("../Source2Viewer-CLI.exe", b"x")
 with pytest.raises(Source2ViewerError, match="unsafe"):
  _install_download(archive, tmp_path / "bundle")


def test_missing_skia_runtime_fails_fast(tmp_path: Path) -> None:
 tool = tmp_path / "Source2Viewer-CLI.exe"; tool.write_bytes(b"cli")
 with pytest.raises(Source2ViewerError, match="SkiaSharp"):
  _runtime(tool)
