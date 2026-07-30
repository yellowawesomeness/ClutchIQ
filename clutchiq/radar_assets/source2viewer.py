"""ValveResourceFormat Source2Viewer acquisition and controlled invocation."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import ctypes, hashlib, json, os, platform, shutil, subprocess, tempfile, urllib.request, zipfile
class Source2ViewerError(RuntimeError): pass
UPSTREAM_REPOSITORY="ValveResourceFormat/ValveResourceFormat"; RELEASE_TAG="19.2"; RELEASE_API_URL=f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}/releases/tags/{RELEASE_TAG}"; WINDOWS_X64_ASSET_NAME="cli-windows-x64.zip"; SOURCE2VIEWER_CLI_EXECUTABLE="Source2Viewer-CLI.exe"
OVERVIEW_VPK_PATH="resource/overviews/"; OVERVIEW_VPK_EXTENSIONS="txt"; OVERHEADMAP_VPK_PATH="panorama/images/overheadmaps/"; OVERHEADMAP_VPK_EXTENSIONS="vtex_c"; TARGETED_EXTRACTION_TARGETS=((OVERVIEW_VPK_PATH,OVERVIEW_VPK_EXTENSIONS),(OVERHEADMAP_VPK_PATH,OVERHEADMAP_VPK_EXTENSIONS)); Report=Callable[[str],None]
@dataclass(frozen=True,slots=True)
class ReleaseAsset: name:str; url:str; sha256:str|None
def managed_bundle_path()->Path: return Path(os.environ.get("LOCALAPPDATA",Path.home()/".cache"))/"ClutchIQ"/"source2viewer"/RELEASE_TAG
def managed_tool_path()->Path: return managed_bundle_path()/SOURCE2VIEWER_CLI_EXECUTABLE
def _lock_path(tool:Path)->Path: return tool.parent/"installation.json"
def _sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def _published_sha256(a:dict[str,object])->str|None:
 d=a.get("digest")
 return d.split(":",1)[1].lower() if isinstance(d,str) and d.startswith("sha256:") and len(d)==71 else None
def discover_windows_x64_asset()->ReleaseAsset:
 try:
  with urllib.request.urlopen(RELEASE_API_URL,timeout=30) as r: p=json.load(r)
 except (OSError,ValueError) as e: raise Source2ViewerError(f"Could not query the ValveResourceFormat {RELEASE_TAG} release API. Use --source2viewer <path>.") from e
 assets=p.get("assets") if isinstance(p,dict) and p.get("tag_name")==RELEASE_TAG else None
 c=[ReleaseAsset(x["name"],x["browser_download_url"],_published_sha256(x)) for x in assets or [] if isinstance(x,dict) and x.get("name")==WINDOWS_X64_ASSET_NAME and isinstance(x.get("browser_download_url"),str)]
 if len(c)!=1: raise Source2ViewerError(f"Could not identify exactly one Windows x64 Source2Viewer asset named {WINDOWS_X64_ASSET_NAME!r}. Use --source2viewer <path>.")
 return c[0]
def _files(tool:Path)->dict[str,str]: return {p.relative_to(tool.parent).as_posix():_sha256(p) for p in tool.parent.rglob("*") if p.is_file() and p.name!="installation.json"}
def _lock(tool:Path,a:ReleaseAsset,d:str)->None: _lock_path(tool).write_text(json.dumps({"tag":RELEASE_TAG,"asset":a.name,"archive_sha256":d,"files":_files(tool)},sort_keys=True),encoding="utf-8")
def _valid(tool:Path)->bool:
 try: p=json.loads(_lock_path(tool).read_text(encoding="utf-8"))
 except (OSError,ValueError): return False
 return tool.is_file() and p.get("tag")==RELEASE_TAG and p.get("files")==_files(tool)
def _runtime(tool:Path)->Path:
 root=tool.parent; managed=[p for p in root.rglob("SkiaSharp.dll") if p.is_file()]; native=[p for p in root.rglob("libSkiaSharp.dll") if p.is_file() and "runtimes" in {x.lower() for x in p.relative_to(root).parts}]
 if len(managed)!=1 or len(native)!=1: raise Source2ViewerError(f"Source2Viewer runtime is incomplete beneath {root}: SkiaSharp.dll and runtimes/.../libSkiaSharp.dll are required.")
 return native[0]
def _run(command:list[str],*,timeout:int,reporter:Report|None=None)->subprocess.CompletedProcess[str]:
 if reporter: reporter(f"Source2Viewer command: {subprocess.list2cmdline(command)}")
 try: return subprocess.run(command,capture_output=True,text=True,timeout=timeout,check=False)
 except (OSError,subprocess.TimeoutExpired) as e: raise Source2ViewerError(f"Source2Viewer command failed: {e}") from e
def verify_source2viewer_runtime(tool:Path)->None:
 if not tool.is_file(): raise Source2ViewerError(f"Source2Viewer executable does not exist: {tool}")
 native=_runtime(tool)
 if platform.system()=="Windows":
  try:
   with os.add_dll_directory(str(native.parent)): ctypes.WinDLL(str(native))
  except OSError as e: raise Source2ViewerError(f"Source2Viewer Skia native runtime cannot load ({native.relative_to(tool.parent)}): {e}") from e
 r=_run([str(tool),"--help"],timeout=15)
 if r.returncode: raise Source2ViewerError(f"Source2Viewer startup self-check failed (exit {r.returncode}): {(r.stderr or r.stdout).strip()[:2000]}")
def resolve_source2viewer(explicit:Path|None=None)->Path:
 if explicit is not None: verify_source2viewer_runtime(Path(explicit)); return Path(explicit)
 tool=managed_tool_path()
 if _valid(tool): verify_source2viewer_runtime(tool); return tool
 return download_source2viewer(tool)
def _member(m:zipfile.ZipInfo)->PurePosixPath:
 p=PurePosixPath(m.filename.replace("\\","/"))
 if p.is_absolute() or not p.parts or any(x in (".","..") for x in p.parts) or ":" in p.parts[0]: raise Source2ViewerError(f"Pinned Source2Viewer archive contains unsafe member: {m.filename!r}")
 return p
def _install_download(download:Path,destination:Path)->Path:
 with zipfile.ZipFile(download) as z:
  entries=[(m,_member(m)) for m in z.infolist() if not m.is_dir()]
  if len({p.as_posix().lower() for _,p in entries})!=len(entries): raise Source2ViewerError("Pinned Source2Viewer archive contains case-colliding members.")
  cli=[p for _,p in entries if p.name.lower()==SOURCE2VIEWER_CLI_EXECUTABLE.lower()]
  if len(cli)!=1: raise Source2ViewerError(f"Pinned Source2Viewer archive does not contain exactly one {SOURCE2VIEWER_CLI_EXECUTABLE}.")
  for m,p in entries:
   out=destination.joinpath(*p.parts); out.parent.mkdir(parents=True,exist_ok=True)
   with z.open(m) as src,out.open("wb") as dst: shutil.copyfileobj(src,dst)
 return destination.joinpath(*cli[0].parts)
def download_source2viewer(destination:Path)->Path:
 if platform.system()!="Windows": raise Source2ViewerError("Managed ValveResourceFormat Source2Viewer 19.2 is configured for Windows x64 only. Provide --source2viewer <path>.")
 a=discover_windows_x64_asset(); destination.parent.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="clutchiq-source2viewer-",dir=destination.parent.parent) as d:
  archive=Path(d)/a.name; bundle=Path(d)/"bundle"; urllib.request.urlretrieve(a.url,archive); digest=_sha256(archive)
  if a.sha256 and digest!=a.sha256: raise Source2ViewerError("Downloaded Source2Viewer failed the ValveResourceFormat published SHA-256 verification.")
  candidate=_install_download(archive,bundle); _runtime(candidate); _lock(candidate,a,digest)
  if destination.parent.exists(): shutil.rmtree(destination.parent)
  shutil.move(str(bundle),str(destination.parent)); installed=destination.parent/candidate.relative_to(bundle)
 verify_source2viewer_runtime(installed); return installed
def build_targeted_list_command(tool:Path,vpk:Path,vpk_path:str=OVERVIEW_VPK_PATH,extensions:str=OVERVIEW_VPK_EXTENSIONS)->list[str]: return [str(tool),"-i",str(vpk),"--vpk_list","--vpk_filepath",vpk_path,"--vpk_extensions",extensions]
def build_targeted_extract_command(tool:Path,vpk:Path,destination:Path,vpk_path:str=OVERVIEW_VPK_PATH,extensions:str=OVERVIEW_VPK_EXTENSIONS)->list[str]: return [str(tool),"-i",str(vpk),"-o",str(destination),"--vpk_decompile","--vpk_filepath",vpk_path,"--vpk_extensions",extensions,"--threads","1"]
def parse_targeted_vpk_list(
    output: str,
    *,
    vpk_path: str = OVERVIEW_VPK_PATH,
    extensions: str = OVERVIEW_VPK_EXTENSIONS,
) -> tuple[str, ...]:
    expected_path = vpk_path.replace("\\", "/").lower()
    expected_extensions = {
        extension.strip().lower().lstrip(".")
        for extension in extensions.split(",")
        if extension.strip()
    }
    assets: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith('"'):
            asset, separator, _ = stripped[1:].partition('"')
            if not separator:
                continue
        else:
            asset = stripped.split(maxsplit=1)[0]

        asset = asset.replace("\\", "/")
        if (
            asset.lower().startswith(expected_path)
            and Path(asset).suffix.lower().lstrip(".") in expected_extensions
        ):
            assets.append(asset)

    return tuple(assets)
def extract_targeted(
    tool: Path,
    vpk: Path,
    destination: Path,
    *,
    timeout: int = 180,
    reporter: Report | None = None,
) -> None:
    if timeout <= 0:
        raise ValueError("Extraction timeout must be positive.")

    destination.mkdir(parents=True, exist_ok=True)

    for vpk_path, extensions in TARGETED_EXTRACTION_TARGETS:
        result = _run(
            build_targeted_list_command(tool, vpk, vpk_path, extensions),
            timeout=timeout,
            reporter=reporter,
        )

        if result.returncode != 0:
            raise Source2ViewerError(
                f"Source2Viewer targeted listing failed for {vpk}: "
                f"{(result.stderr or result.stdout).strip()}"
            )

        if not parse_targeted_vpk_list(
            result.stdout,
            vpk_path=vpk_path,
            extensions=extensions,
        ):
            raise Source2ViewerError(
                f"Source2Viewer targeted listing found no {extensions} assets in "
                f"{vpk_path} for {vpk}; refusing decompilation."
            )

    for vpk_path, extensions in TARGETED_EXTRACTION_TARGETS:
        result = _run(
            build_targeted_extract_command(
                tool,
                vpk,
                destination,
                vpk_path,
                extensions,
            ),
            timeout=timeout,
            reporter=reporter,
        )

        if result.returncode != 0:
            raise Source2ViewerError(
                f"Source2Viewer targeted extraction failed for {vpk}: "
                f"{(result.stderr or result.stdout).strip()}"
            )


def extract(
    tool: Path,
    vpk: Path,
    destination: Path,
    *,
    timeout: int = 180,
) -> None:
    if timeout <= 0:
        raise ValueError("Extraction timeout must be positive.")

    destination.mkdir(parents=True, exist_ok=True)

    result = _run(
        [str(tool), "-i", str(vpk), "-o", str(destination)],
        timeout=timeout,
    )

    if result.returncode != 0:
        raise Source2ViewerError(
            f"Source2Viewer extraction failed for {vpk}: "
            f"{(result.stderr or result.stdout).strip()}"
        )