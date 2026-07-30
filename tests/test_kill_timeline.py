from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from clutchiq.demo_ingest.models import Cs2Demo, DemoHeader, DemoKill, DemoRound
from clutchiq.replay_state.models import ReplayViewModel
from clutchiq.timeline_engine.adapters import cs2demo_to_timeline_import
from clutchiq.widgets.pages.replay import ReplayPage


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_kill_events_preserve_normalized_payload_and_synchronize_missing_round() -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=4, start_tick=100, end_tick=200),),
        kills=(DemoKill(tick=150, attacker_player_id=1, victim_player_id=2, assister_player_id=3, weapon="ak47", headshot=True),),
    ))

    kill = next(event for event in timeline.events if event.kind == "kill.recorded")
    assert kill.round_number == 4
    assert kill.participant_id == 1
    assert kill.raw == {"attacker_player_id": 1, "victim_player_id": 2, "assister_player_id": 3, "weapon": "ak47", "headshot": True, "round_number": 4}


def test_replay_timeline_filters_to_active_round_and_tracks_current_tick(qapp: QApplication) -> None:
    page = ReplayPage()
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=12, start_tick=101, end_tick=202), DemoRound(round_number=13, start_tick=203, end_tick=300)),
        kills=(DemoKill(tick=150, round_number=12), DemoKill(tick=220, round_number=13)),
    ))
    view_model = ReplayViewModel(record=SimpleNamespace(source_name="match.dem"), round=DemoRound(round_number=12, start_tick=101, end_tick=202))

    page.set_view_model(view_model, lambda: None, timeline.events)
    assert len(page._kill_events) == 1
    assert "Kills: 0 / 1" in [label.text() for label in page.findChildren(QLabel)]

    page._set_tick(150)
    assert "Kills: 1 / 1" in [label.text() for label in page.findChildren(QLabel)]
