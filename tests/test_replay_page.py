from __future__ import annotations

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from clutchiq.demo_ingest.models import DemoRound
from clutchiq.history.models import AnalysisSummary, ImportResult, ImportStage, PersistedImportRecord
from clutchiq.replay_radar import RadarMapRegistry, RadarMapSpec
from clutchiq.replay_state.models import ReplayViewModel
from clutchiq.replay_state.spatial import SpatialReplayData
from clutchiq.widgets.pages.replay import RadarView, ReplayPage

@pytest.fixture(scope="session")
def qapp(): return QApplication.instance() or QApplication([])

def _model(map_name: str | None = "de_dust2"):
    record=PersistedImportRecord("match", "2026-01-01T00:00:00+00:00", "x.dem", "x.dem", ImportResult.SUCCESS, ImportStage.ANALYZE, AnalysisSummary(1,1,0,"CT",1,map_name), None, None)
    return ReplayViewModel(record, DemoRound(1,"CT",10,20,1,0))

def test_registry_normalizes_and_rejects_invalid_positions():
    spec=RadarMapSpec("map", "unused", 0, 100, 0, 100)
    registry=RadarMapRegistry({"map": spec})
    assert registry.resolve(" MAP ") is spec
    assert registry.resolve("unknown") is None
    assert spec.normalized(50, 50) == (0.5, 0.5)
    assert spec.normalized(101, 50) is None

def test_replay_uses_configured_map_and_unknown_map_fallback(qapp):
    page=ReplayPage(); page.set_view_model(_model(), lambda: None)
    assert page._radar_view._map_spec is not None
    page.set_view_model(_model("unknown"), lambda: None)
    assert page._radar_view._map_spec is None

def test_radar_ignores_off_map_spatial_positions(qapp):
    view=RadarView(RadarMapRegistry({"map": RadarMapSpec("map", "", 0, 1, 0, 1, asset_svg="<svg xmlns='http://www.w3.org/2000/svg'/>")}))
    model=_model("map")
    spatial=SpatialReplayData.from_parse_ticks(pd.DataFrame([{"tick":10,"steamid":"1","name":"x","team_name":"CT","X":2.0,"Y":2.0,"Z":0.0,"yaw":0.0,"pitch":0.0,"is_alive":True}]))
    view.set_replay(model, spatial, 10)
    assert view._map_spec is not None
