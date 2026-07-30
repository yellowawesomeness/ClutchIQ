"""ValveResourceFormat Source2Viewer acquisition and controlled invocation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import urllib.request
import zipfile


class Source2ViewerError(RuntimeError):
    pass


# This is deliberately a tag, not a ``latest`` URL.  The resolved asset URL and
# SHA-256 are recorded beside the managed executable after the first install.
UPSTREAM_REPOSITORY = "ValveResourceFormat/ValveResourceFormat"
RELEASE_TAG = "19.2"
RELEASE_API_URL = f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}/releases/tags/{RELEASE_TAG}"


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    url: str
    sha256: str | None


def managed_tool_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "ClutchIQ" / "source2viewer"
    return root / ("Source2Viewer.exe" if platform.system() == "Windows" else "Source2Viewer")


def _lock_path(tool: Path) -> Path:
    return tool.with_suffix(tool.suffix + ".json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _published_sha256(asset: dict[str, object]) -> str | None:
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        value = digest.split(":", 1)[1].lower()
        if len(value) == 64 and all(character in "0123456789abcdef" for character in value):
            return value
    return None


def discover_windows_x64_asset() -> ReleaseAsset:
    """Resolve the immutable Windows x64 CLI asset for the pinned upstream tag."""
    try:
        with urllib.request.urlopen(RELEASE_API_URL, timeout=30) as response:
            payload = json.load(response)
    except (OSError, ValueError) as error:
        raise Source2ViewerError(f"Could not query the ValveResourceFormat {RELEASE_TAG} release API. Use --source2viewer <path>.") from error
    if not isinstance(payload, dict) or payload.get("tag_name") != RELEASE_TAG:
        raise Source2ViewerError(f"ValveResourceFormat release API did not return the pinned tag {RELEASE_TAG}.")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise Source2ViewerError("ValveResourceFormat release has no assets.")
    candidates: list[ReleaseAsset] = []
    for raw in assets:
        if not isinstance(raw, dict):
            continue
        name, url = raw.get("name"), raw.get("browser_download_url")
        normalized = name.lower() if isinstance(name, str) else ""
        if (isinstance(url, str) and "source2viewer" in normalized and "win" in normalized
                and ("x64" in normalized or "win64" in normalized) and normalized.endswith((".zip", ".exe"))):
            candidates.append(ReleaseAsset(name, url, _published_sha256(raw)))
    if len(candidates) != 1:
        raise Source2ViewerError("Could not identify exactly one Windows x64 Source2Viewer asset in ValveResourceFormat release 19.2. Use --source2viewer <path>.")
    return candidates[0]


def _read_lock(tool: Path) -> dict[str, str] | None:
    try:
        value = json.loads(_lock_path(tool).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and all(isinstance(item, str) for item in value.values()) else None


def _write_lock(tool: Path, asset: ReleaseAsset, digest: str) -> None:
    payload = {"repository": UPSTREAM_REPOSITORY, "tag": RELEASE_TAG, "asset": asset.name, "url": asset.url, "sha256": digest}
    temporary = _lock_path(tool).with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(_lock_path(tool))


def resolve_source2viewer(explicit: Path | None = None) -> Path:
    if explicit is not None:
        path = Path(explicit)
        if path.is_file():
            return path
        raise Source2ViewerError(f"--source2viewer does not exist: {path}")
    managed = managed_tool_path()
    lock = _read_lock(managed)
    if managed.is_file() and lock is not None and lock.get("tag") == RELEASE_TAG and lock.get("sha256") == _sha256(managed):
        return managed
    return download_source2viewer(managed)


def _install_download(download: Path, destination: Path) -> None:
    if download.suffix.lower() == ".zip":
        with zipfile.ZipFile(download) as archive:
            names = [name for name in archive.namelist() if Path(name).name.lower() == "source2viewer.exe"]
            if len(names) != 1:
                raise Source2ViewerError("Pinned Source2Viewer archive does not contain exactly one Source2Viewer.exe.")
            with archive.open(names[0]) as source, destination.open("wb") as target:
                target.write(source.read())
    else:
        download.replace(destination)


def download_source2viewer(destination: Path) -> Path:
    if platform.system() != "Windows":
        raise Source2ViewerError("Managed ValveResourceFormat Source2Viewer 19.2 is configured for Windows x64 only. Provide --source2viewer <path>.")
    asset = discover_windows_x64_asset()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clutchiq-source2viewer-", dir=destination.parent) as directory:
        download = Path(directory) / asset.name
        candidate = Path(directory) / destination.name
        try:
            urllib.request.urlretrieve(asset.url, download)
            downloaded_digest = _sha256(download)
            if asset.sha256 is not None and downloaded_digest != asset.sha256:
                raise Source2ViewerError("Downloaded Source2Viewer failed the ValveResourceFormat published SHA-256 verification.")
            _install_download(download, candidate)
        except (OSError, zipfile.BadZipFile) as error:
            raise Source2ViewerError("Source2Viewer could not be downloaded or unpacked. Use --source2viewer <path>.") from error
        if not candidate.is_file() or not candidate.stat().st_size:
            raise Source2ViewerError("Pinned Source2Viewer installation produced no executable.")
        candidate.replace(destination)
    _write_lock(destination, asset, downloaded_digest)
    return destination


def extract(tool: Path, vpk: Path, destination: Path) -> None:
    """Extract a VPK using Source2Viewer's documented export interface."""
    destination.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run([str(tool), "-i", str(vpk), "-o", str(destination)], capture_output=True, text=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Source2ViewerError(f"Source2Viewer extraction failed for {vpk}: {error}") from error
    if result.returncode:
        raise Source2ViewerError(f"Source2Viewer extraction failed for {vpk}: {result.stderr.strip() or result.stdout.strip()}")
