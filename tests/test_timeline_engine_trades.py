from __future__ import annotations

import pytest

from clutchiq.timeline_engine import InMemoryTimelineRepository, TimelineEngine, TimelineEvent, TimelineImport, TimelineMetadata, TradeDetectionConfig, TradeQuery


def _membership(event_id: str, player: object, team: object, round_number: object = 1) -> TimelineEvent:
    return TimelineEvent(event_id, 0, 0, "player.round_team", round_number if isinstance(round_number, int) else None, raw={"player_id": player, "team_num": team, "round_number": round_number})


def _kill(event_id: str, tick: object, sequence: object, attacker: object, victim: object, round_number: object = 1) -> TimelineEvent:
    return TimelineEvent(event_id, tick, sequence, "kill.recorded", round_number if isinstance(round_number, int) else None, raw={"attacker_player_id": attacker, "victim_player_id": victim, "round_number": round_number})


def _result(events: tuple[TimelineEvent, ...], window: int = 128):
    engine = TimelineEngine(InMemoryTimelineRepository())
    timeline_id = engine.import_timeline(TimelineImport(TimelineMetadata(), events=events))
    return engine.detect_trades(TradeQuery(timeline_id, TradeDetectionConfig(window)))


def _teams() -> tuple[TimelineEvent, ...]:
    return (_membership("m1", 1, 2), _membership("m2", 2, 3), _membership("m3", 3, 2), _membership("m4", 4, 3))


def test_detects_normal_trade_and_inclusive_boundaries() -> None:
    result = _result(_teams() + (_kill("death", 10, 0, 1, 2), _kill("trade", 20, 0, 2, 1)), 10)
    assert [(trade.death_event_id, trade.retaliation_event_id) for trade in result.trades] == [("death", "trade")]
    assert not result.skipped_malformed


def test_rejects_trade_outside_window() -> None:
    assert not _result(_teams() + (_kill("death", 10, 0, 1, 2), _kill("trade", 21, 0, 2, 1)), 10).trades


def test_equal_tick_order_uses_sequence_not_input_order() -> None:
    events = _teams() + (_kill("trade", 10, 1, 2, 1), _kill("death", 10, 0, 1, 2))
    assert [trade.retaliation_event_id for trade in _result(events, 0).trades] == ["trade"]


def test_rejects_cross_round_and_same_team_kills() -> None:
    events = _teams() + (_membership("m5", 2, 3, 2), _membership("m6", 1, 2, 2), _kill("death", 10, 0, 1, 2), _kill("cross", 20, 0, 2, 1, 2), _kill("friendly", 30, 0, 1, 3))
    result = _result(events)
    assert not result.trades
    assert result.skipped_unknown == 1


def test_skips_unknown_conflicting_duplicate_and_malformed_records() -> None:
    events = _teams() + (_membership("duplicate", 1, 2), _membership("conflict", 2, 2), _membership("bad", "x", 3), _kill("bad-kill", 9, 0, "x", 2), _kill("unknown", 10, 0, 3, 4), _kill("death", 11, 0, 1, 2), _kill("death-copy", 11, 1, 1, 2), _kill("trade", 12, 0, 2, 1))
    result = _result(events)
    assert not result.trades
    assert result.skipped_duplicate >= 2
    assert result.skipped_conflicting >= 1
    assert result.skipped_malformed >= 2


def test_uses_newest_unmatched_death_and_consumes_events_one_to_one() -> None:
    events = _teams() + (_kill("old", 1, 0, 1, 2), _kill("new", 2, 0, 1, 2), _kill("trade", 3, 0, 2, 1), _kill("second", 4, 0, 2, 1))
    result = _result(events, 2)
    assert [(trade.death_event_id, trade.retaliation_event_id) for trade in result.trades] == [("new", "trade")]


def test_config_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        TradeDetectionConfig(-1)
