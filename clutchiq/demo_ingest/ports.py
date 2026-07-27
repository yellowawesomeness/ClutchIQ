"""Typed ports for demo ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class DemoIngestSource(Protocol):
    """Readable binary demo source boundary."""

    @property
    def path(self) -> Path:
        """Return the demo file path."""
        ...

    @property
    def size_bytes(self) -> int:
        """Return the current file size in bytes."""
        ...

    def read_bytes(self) -> bytes:
        """Eagerly load and return the complete demo file."""
        ...