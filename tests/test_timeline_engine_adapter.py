from __future__ import annotations

import pytest

from clutchiq.demo_ingest.models import Cs2Demo, DemoEvent, DemoHeader, DemoKill, DemoPlayer, DemoRound
from clutchiq.timeline_engine.adapters import cs2demo_to_timeline_import


def test_cs2demo_to_timeline_import_preserves_supported_fields() -> None:
    demo = Cs2Demo(
        header=DemoHeader(map_name="de_dust2", tick_rate=128, raw={"header": True}),
        players=(DemoPlayer(player_id=7, name="alice", steam_id=42, team="CT", side="CT", raw={"player": True}),),
        rounds=(DemoRound(round_number=1, winner_team="CT", start_tick=1, end_tick=10, raw={"round": True}),),
        kills=(DemoKill(tick=2, attacker_player_id=7, victim_player_id=8, round_number=1, raw={"kill": True}),),
        events=(DemoEvent(tick=3, event_type="player_death", round_number=1, raw={"event": True}),),
        raw={"demo": True},
    )

    timeline = cs2demo_to_timeline_import(demo)

    assert timeline.metadata.map_name == "de_dust2"
    assert timeline.metadata.tick_rate == 128
    assert timeline.participants[0].participant_id == 7
    assert [event.kind for event in timeline.events] == ["round.recorded", "kill.recorded", "event.recorded", "round.outcome"]
    assert [event.sequence for event in timeline.events] == [0, 0, 0, 0]
    outcome = timeline.events[-1]
    assert outcome.tick == 10
    assert outcome.round_number == 1
    assert outcome.participant_id is None
    assert outcome.raw == {"round": True, "round_number": 1, "winner_team_num": 3}
    assert timeline.raw == {"header": {"header": True}}


@pytest.mark.parametrize(("winner_team", "winner_team_num"), [("T", 2), ("CT", 3)])
def test_adapter_emits_round_outcome_with_mapped_winner_team(winner_team: str, winner_team_num: int) -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, winner_team=winner_team, start_tick=1, end_tick=10),),
    ))

    assert len(timeline.events) == 2
    outcome = timeline.events[1]
    assert outcome.kind == "round.outcome"
    assert outcome.tick == 10
    assert outcome.sequence == 0
    assert outcome.raw == {"round_number": 1, "winner_team_num": winner_team_num}


@pytest.mark.parametrize("winner_team", [None, "Counter-Terrorist", "terrorist", ""])
def test_adapter_skips_invalid_round_outcomes(winner_team: str | None) -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, winner_team=winner_team, start_tick=1, end_tick=10),),
    ))

    assert [event.kind for event in timeline.events] == ["round.recorded"]


@pytest.mark.parametrize("end_tick", [None, True])
def test_adapter_skips_round_outcome_without_integer_end_tick(end_tick: int | None) -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, winner_team="CT", start_tick=1, end_tick=end_tick),),
    ))

    assert [event.kind for event in timeline.events] == ["round.recorded"]


def test_adapter_uses_round_end_tick_when_start_tick_is_unusable() -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, start_tick=None, end_tick=50),),
    ))

    assert [(event.kind, event.tick) for event in timeline.events] == [("round.recorded", 50)]


def test_adapter_skips_round_recorded_without_usable_tick() -> None:
    timeline = cs2demo_to_timeline_import(Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, start_tick=None, end_tick=None),),
    ))

    assert timeline.events == ()


def test_adapter_keeps_generic_tick_errors_visible() -> None:
    demo = Cs2Demo(header=DemoHeader(), events=(DemoEvent(tick=None, event_type="malformed"),))

    with pytest.raises(AttributeError, match="does not expose a tick field"):
        cs2demo_to_timeline_import(demo)


def test_adapter_orders_round_outcome_before_later_source_at_same_tick() -> None:
    demo = Cs2Demo(
        header=DemoHeader(),
        rounds=(DemoRound(round_number=1, winner_team="CT", start_tick=1, end_tick=10),),
        kills=(DemoKill(tick=10, attacker_player_id=7, victim_player_id=8, round_number=1),),
    )

    timeline = cs2demo_to_timeline_import(demo)

    assert [(event.kind, event.sequence) for event in timeline.events] == [
        ("round.recorded", 0),
        ("round.outcome", 0),
        ("kill.recorded", 1),
    ]


def test_adapter_event_ids_are_deterministic() -> None:
    demo = Cs2Demo(
        header=DemoHeader(raw={}),
        rounds=(DemoRound(round_number=1, winner_team="CT", start_tick=5, end_tick=10, raw={"round": True}),),
    )

    first = cs2demo_to_timeline_import(demo)
    second = cs2demo_to_timeline_import(demo)

    assert [event.event_id for event in first.events] == [event.event_id for event in second.events]
