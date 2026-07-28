"""Service logic for demo ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from clutchiq.demo_ingest.errors import DemoParseError, DemoReadError
from clutchiq.demo_ingest.models import BinaryDemoSource
from clutchiq.demo_ingest.parser import DemoParser
from clutchiq.demo_ingest.ports import DemoIngestSource

ParsedT = TypeVar("ParsedT")


@dataclass(frozen=True, slots=True)
class DemoIngestService(Generic[ParsedT]):
    """Read a demo source and parse it into a domain object."""

    parser: DemoParser[ParsedT]

    def ingest(self, source: DemoIngestSource) -> ParsedT:
        """Read bytes from the source and parse them."""
        try:
            data = source.read_bytes()
        except DemoReadError:
            raise
        except OSError as exc:
            raise DemoReadError(f"Could not read demo file: {source.path}") from exc

        try:
            return self.parser.parse(data)
        except DemoParseError:
            raise

    def ingest_path(self, path: str | Path) -> ParsedT:
        """Convenience wrapper for ingesting from a filesystem path."""
        return self.ingest(BinaryDemoSource(Path(path)))
