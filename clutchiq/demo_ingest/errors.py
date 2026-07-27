"""Error types for demo ingestion."""

from __future__ import annotations


class DemoIngestError(Exception):
    """Base class for demo ingestion errors."""


class DemoReadError(DemoIngestError):
    """Raised when a demo file cannot be read."""


class DemoParseError(DemoIngestError):
    """Raised when a demo file cannot be parsed."""