from __future__ import annotations

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
    assert [event.kind for event in timeline.events] == ["round.recorded", "kill.recorded", "event.recorded"]
    assert [event.sequence for event in timeline.events] == [0, 0, 0]
    assert timeline.raw == {"header": {"header": True}}


def test_adapter_event_ids_are_deterministic() -> None:
    demo = Cs2Demo(
        header=DemoHeader(raw={}),
        rounds=(DemoRound(round_number=1, start_tick=5, raw={"round": True}),),
    )

    first = cs2demo_to_timeline_import(demo)
    second = cs2demo_to_timeline_import(demo)

    assert [event.event_id for event in first.events] == [event.event_id for event in second.events]
