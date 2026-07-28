from __future__ import annotations

from clutchiq.demo_analysis import AnalysisEngine
from clutchiq.demo_ingest import BinaryDemoSource, Cs2DemoParser, DemoIngestService


def test_existing_demo_ingest_and_analysis_public_apis_still_import() -> None:
    assert DemoIngestService is not None
    assert Cs2DemoParser is not None
    assert AnalysisEngine is not None
    assert BinaryDemoSource is not None
