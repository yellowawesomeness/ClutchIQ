from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from clutchiq.demo_ingest import Cs2DemoParser, DemoIngestService, build_match_summary
from clutchiq.demo_ingest.vendor import Demoparser2Adapter


REAL_DEMO = Path("demos/MATCH20260725-1.dem")


def _require_real_demo_and_vendor() -> None:
    if not REAL_DEMO.exists():
        pytest.skip("real demo file not present")
    if importlib.util.find_spec("demoparser2") is None:
        pytest.skip("demoparser2 not installed")


@pytest.mark.integration
def test_real_demo_ingests_end_to_end() -> None:
    _require_real_demo_and_vendor()

    demo = Demoparser2Adapter().parse_bytes(REAL_DEMO.read_bytes())

    assert demo.header.map_name
    assert demo.players
    assert demo.rounds
    assert demo.events

    summary = build_match_summary(demo)
    assert summary.rounds == len(demo.rounds)
    assert summary.players == len(demo.players)


@pytest.mark.integration
def test_real_demo_service_path(tmp_path: Path) -> None:
    _require_real_demo_and_vendor()

    demo_bytes = REAL_DEMO.read_bytes()
    copy = tmp_path / REAL_DEMO.name
    copy.write_bytes(demo_bytes)

    service = DemoIngestService(parser=Cs2DemoParser())
    demo = service.ingest_path(copy)

    assert demo.header.map_name
    assert demo.players
    assert demo.rounds
