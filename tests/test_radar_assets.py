from pathlib import Path
import hashlib
import io
import json
import struct

import pytest

from clutchiq.radar_assets.images import install_png
from clutchiq.radar_assets.manifest import RadarLevel, RadarManifestEntry, write_manifest
from clutchiq.radar_assets.overview import parse_overview
from clutchiq.radar_assets.steam import find_cs2, steam_libraries
from clutchiq.radar_assets import source2viewer
from clutchiq.radar_assets.source2viewer import Source2ViewerError, discover_windows_x64_asset, resolve_source2viewer
from clutchiq.replay_radar import RadarLevelSpec, RadarMapSpec


def _png(path: Path) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 64, 32))


def test_discovers_cs2_from_libraryfolders(tmp_path: Path) -> None:
    steam = tmp_path / "Steam"
    library = tmp_path / "Library"
    (steam / "steamapps").mkdir(parents=True)
    (steam / "steamapps" / "libraryfolders.vdf").write_text('"path" "' + str(library).replace("\\", "\\\\") + '"')
    (library / "steamapps/common/Counter-Strike Global Offensive/game/csgo").mkdir(parents=True)
    assert library in steam_libraries(steam)
    assert find_cs2(steam_root=steam).name == "Counter-Strike Global Offensive"


def test_overview_bounds_and_multilevel_manifest(tmp_path: Path) -> None:
    overview = parse_overview('"pos_x" "-100"\n"pos_y" "200"\n"scale" "2"')
    assert overview.bounds(64, 32) == (-100.0, 28.0, 136.0, 200.0)
    image = tmp_path / "input.png"
    _png(image)
    assert install_png(image, tmp_path / "de_nuke_upper.png") == (64, 32)
    entry = RadarManifestEntry("de_nuke_upper.png", -100, 28, 136, 200, levels=(RadarLevel("upper", "de_nuke_upper.png", -100), RadarLevel("lower", "de_nuke_lower.png", None, -100)))
    write_manifest({"de_nuke": entry}, tmp_path / "maps.json")
    assert '"levels"' in (tmp_path / "maps.json").read_text()


def test_manual_source2viewer_path_and_missing_path(tmp_path: Path) -> None:
    tool = tmp_path / "Source2Viewer"
    tool.write_text("tool")
    assert resolve_source2viewer(tool) == tool
    with pytest.raises(Source2ViewerError):
        resolve_source2viewer(tmp_path / "missing")


def test_release_api_selects_only_windows_x64_source2viewer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"tag_name": "19.2", "assets": [
        {"name": "Source2Viewer-win-x64.zip", "browser_download_url": "https://example.invalid/viewer.zip", "digest": "sha256:" + "a" * 64},
        {"name": "Source2Viewer-linux-x64.zip", "browser_download_url": "https://example.invalid/linux.zip"},
    ]}

    class Response(io.StringIO):
        def __enter__(self): return self
        def __exit__(self, *_): self.close()

    monkeypatch.setattr(source2viewer.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(json.dumps(payload)))
    asset = discover_windows_x64_asset()
    assert asset.name == "Source2Viewer-win-x64.zip"
    assert asset.sha256 == "a" * 64


def test_release_api_rejects_ambiguous_or_wrong_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response(io.StringIO):
        def __enter__(self): return self
        def __exit__(self, *_): self.close()

    monkeypatch.setattr(source2viewer.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(json.dumps({"tag_name": "19.1", "assets": []})))
    with pytest.raises(Source2ViewerError, match="pinned tag"):
        discover_windows_x64_asset()


def test_verified_managed_tool_is_reused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = tmp_path / "Source2Viewer.exe"
    tool.write_bytes(b"managed")
    digest = hashlib.sha256(b"managed").hexdigest()
    tool.with_suffix(".exe.json").write_text(json.dumps({"tag": "19.2", "sha256": digest}))
    monkeypatch.setattr(source2viewer, "managed_tool_path", lambda: tool)
    assert resolve_source2viewer() == tool


def test_registry_level_selection_is_additive() -> None:
    spec = RadarMapSpec("de_nuke", "nuke.png", 0, 100, 0, 100, levels=(RadarLevelSpec("lower", "lower.png", max_z=0), RadarLevelSpec("upper", "upper.png", min_z=0)))
    assert spec.normalized(50, 50) == (0.5, 0.5)
    assert spec.level_for_z(-1).name == "lower"
    assert spec.level_for_z(0).name == "upper"
