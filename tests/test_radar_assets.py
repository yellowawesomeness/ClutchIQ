from __future__ import annotations

import io, json
from pathlib import Path
import pytest
from clutchiq.radar_assets import source2viewer
from clutchiq.radar_assets.images import install_png
from clutchiq.radar_assets.manifest import RadarLevel, RadarManifestEntry, write_manifest
from clutchiq.radar_assets.overview import parse_overview
from clutchiq.radar_assets.source2viewer import Source2ViewerError, discover_windows_x64_asset, resolve_source2viewer
from clutchiq.radar_assets.steam import find_cs2, steam_libraries
from clutchiq.replay_radar import RadarLevelSpec, RadarMapSpec

def _png(path: Path) -> None: path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00 ")
def test_parse_overview_and_manifest(tmp_path: Path) -> None:
 overview=tmp_path/"de_nuke.txt"; overview.write_text('"pos_x" "-100"\n"pos_y" "200"\n"scale" "4"\n"rotate" "1"\n',encoding="utf-8")
 parsed=parse_overview(overview.read_text(encoding="utf-8")); assert (parsed.pos_x,parsed.pos_y,parsed.scale,parsed.rotate)==(-100.0,200.0,4.0,True)
 image=tmp_path/"input.png"; _png(image); assert install_png(image,tmp_path/"de_nuke_upper.png")==(64,32)
 entry=RadarManifestEntry("de_nuke_upper.png",-100,28,136,200,levels=(RadarLevel("upper","de_nuke_upper.png",-100),RadarLevel("lower","de_nuke_lower.png",None,-100)))
 write_manifest({"de_nuke":entry},tmp_path/"maps.json"); assert '"levels"' in (tmp_path/"maps.json").read_text()
def test_manual_source2viewer_path_is_checked(tmp_path: Path) -> None:
 tool=tmp_path/"Source2Viewer"; tool.write_text("tool")
 with pytest.raises(Source2ViewerError,match="SkiaSharp"): resolve_source2viewer(tool)
 with pytest.raises(Source2ViewerError): resolve_source2viewer(tmp_path/"missing")
def _response(payload:dict[str,object]):
 class Response(io.StringIO):
  def __enter__(self): return self
  def __exit__(self,*_): self.close()
 return Response(json.dumps(payload))
def test_release_api_selects_only_windows_x64_source2viewer(monkeypatch:pytest.MonkeyPatch)->None:
 monkeypatch.setattr(source2viewer.urllib.request,"urlopen",lambda *_a,**_k:_response({"tag_name":"19.2","assets":[{"name":"cli-windows-x64.zip","browser_download_url":"https://example.invalid/viewer.zip","digest":"sha256:"+"a"*64},{"name":"Source2Viewer-linux-x64.zip","browser_download_url":"https://example.invalid/linux.zip"}]}))
 asset=discover_windows_x64_asset(); assert asset.name=="cli-windows-x64.zip"; assert asset.sha256=="a"*64
def test_release_api_failure_lists_returned_asset_names(monkeypatch:pytest.MonkeyPatch)->None:
 monkeypatch.setattr(source2viewer.urllib.request,"urlopen",lambda *_a,**_k:_response({"tag_name":"19.2","assets":[{"name":"cli-linux-x64.zip","browser_download_url":"x"},{"name":"Source2Viewer-windows-x64.zip","browser_download_url":"x"}]}))
 with pytest.raises(Source2ViewerError,match="cli-windows-x64.zip"): discover_windows_x64_asset()
def test_release_api_rejects_wrong_tag(monkeypatch:pytest.MonkeyPatch)->None:
 monkeypatch.setattr(source2viewer.urllib.request,"urlopen",lambda *_a,**_k:_response({"tag_name":"19.1","assets":[]}))
 with pytest.raises(Source2ViewerError): discover_windows_x64_asset()
def test_verified_managed_tool_is_reused(monkeypatch:pytest.MonkeyPatch,tmp_path:Path)->None:
 tool=tmp_path/"Source2Viewer.exe"; tool.write_bytes(b"managed")
 (tmp_path/"installation.json").write_text(json.dumps({"tag":"19.2","files":{"Source2Viewer.exe":source2viewer._sha256(tool)}}),encoding="utf-8")
 monkeypatch.setattr(source2viewer,"managed_tool_path",lambda:tool); monkeypatch.setattr(source2viewer,"verify_source2viewer_runtime",lambda _:None)
 assert resolve_source2viewer()==tool
