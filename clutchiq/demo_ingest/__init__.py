"""Demo ingestion domain package for ClutchIQ."""

from clutchiq.demo_ingest.cs2_parser import Cs2DemoParser
from clutchiq.demo_ingest.errors import (
    DemoIngestError,
    DemoParseError,
    DemoReadError,
)
from clutchiq.demo_ingest.models import (
    BinaryDemoSource,
    Cs2Demo,
    DemoEvent,
    DemoHeader,
    DemoKill,
    DemoPlayer,
    DemoRound,
)
from clutchiq.demo_ingest.parser import DemoParser
from clutchiq.demo_ingest.ports import DemoIngestSource
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.demo_ingest.summary import MatchSummary, build_match_summary, format_match_summary

__all__ = [
    "BinaryDemoSource",
    "Cs2Demo",
    "Cs2DemoParser",
    "DemoEvent",
    "DemoHeader",
    "DemoIngestError",
    "DemoIngestService",
    "DemoIngestSource",
    "DemoKill",
    "DemoParser",
    "DemoParseError",
    "DemoPlayer",
    "DemoReadError",
    "DemoRound",
    "MatchSummary",
    "build_match_summary",
    "format_match_summary",
]
