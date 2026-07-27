"""Domain models for demo ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from clutchiq.demo_ingest.errors import DemoReadError


@dataclass(frozen=True, slots=True)
class BinaryDemoSource:
    """File-backed binary demo source."""

    _path: Path

    @property
    def path(self) -> Path:
        """Return the demo file path."""
        return self._path

    @property
    def size_bytes(self) -> int:
        """Return the current file size in bytes."""
        try:
            return self._path.stat().st_size
        except OSError as exc:
            raise DemoReadError(
                f"Could not read file metadata for: {self._path}"
            ) from exc

    def read_bytes(self) -> bytes:
        """Eagerly load and return the complete demo file."""
        try:
            return self._path.read_bytes()
        except OSError as exc:
            raise DemoReadError(
                f"Could not read demo file: {self._path}"
            ) from exc