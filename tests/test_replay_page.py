from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSlider, QWidget

from clutchiq.demo_ingest.models import DemoRound
from clutchiq.history.models import AnalysisSummary, ImportResult, ImportStage, PersistedImportRecord
from clutchiq.replay_state.models import ReplayViewModel
from clutchiq.widgets.pages.replay import ReplayPage


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class BackTracker:
    def __init__(self) -> None:
        self.called = False

    def __call__(self) -> None:
        self.called = True


def _labels(page: QWidget) -> list[str]:
    return [widget.text() for widget in page.findChildren(QLabel)]


def _buttons(page: QWidget) -> list[QPushButton]:
    return page.findChildren(QPushButton)


def _slider(page: QWidget) -> QSlider:
    return page.findChild(QSlider)


def _view_model() -> ReplayViewModel:
    record = PersistedImportRecord(
        id="match-1",
        imported_at_utc="2026-07-25T12:00:00+00:00",
        source_path="C:/demos/match.dem",
        source_name="match.dem",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(
            total_rounds=1,
            ct_rounds=1,
            t_rounds=0,
            winning_side="CT",
            rounds_with_known_winner=1,
        ),
        error_type=None,
        error_message=None,
    )
    round_ = DemoRound(
        round_number=12,
        winner_team="CT",
        start_tick=101,
        end_tick=202,
        score_ct=7,
        score_t=5,
    )
    return ReplayViewModel(record=record, round=round_)


def test_replay_page_renders_empty_state(qapp: QApplication) -> None:
    page = ReplayPage(back_callback=lambda: None)

    assert "No replay loaded." in _labels(page)
    assert "Back to Match Details" in [button.text() for button in _buttons(page)]


def test_replay_page_renders_round_metadata_and_back_action(qapp: QApplication) -> None:
    tracker = BackTracker()
    page = ReplayPage(back_callback=lambda: None)

    page.set_view_model(_view_model(), tracker)
    next(button for button in _buttons(page) if button.text() == "Back to Match Details").click()

    assert "Match: match.dem" in _labels(page)
    assert "Round: 12" in _labels(page)
    assert "Start tick: 101" in _labels(page)
    assert "End tick: 202" in _labels(page)
    assert "CT score: 7" in _labels(page)
    assert "T score: 5" in _labels(page)
    assert "Winner: CT" in _labels(page)
    assert tracker.called is True


def test_replay_page_time_controls_are_read_only_and_step_within_range(qapp: QApplication) -> None:
    page = ReplayPage(back_callback=lambda: None)
    page.set_view_model(_view_model(), lambda: None)

    slider = _slider(page)
    assert slider.minimum() == 101
    assert slider.maximum() == 202
    assert slider.value() == 101

    buttons = _buttons(page)
    play_button = next(button for button in buttons if button.text() == "Play")
    step_forward_button = next(button for button in buttons if button.text() == "Step Forward")
    step_back_button = next(button for button in buttons if button.text() == "Step Back")

    step_forward_button.click()
    assert "Tick: 102" in _labels(page)

    step_back_button.click()
    assert "Tick: 101" in _labels(page)

    play_button.click()
    assert play_button.text() == "Pause"
    play_button.click()
    assert play_button.text() == "Play"


def test_replay_page_clamps_and_stops_at_end_tick(qapp: QApplication) -> None:
    page = ReplayPage(back_callback=lambda: None)
    page.set_view_model(_view_model(), lambda: None)

    page._current_tick = 201
    page._is_playing = True
    page._step_forward()

    assert "Tick: 202" in _labels(page)
    assert page._is_playing is False
    assert page._timer.isActive() is False
