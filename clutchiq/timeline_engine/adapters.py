"""Adapters from demo ingestion models into timeline import payloads."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from clutchiq.demo_ingest.models import Cs2Demo
from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata


def cs2demo_to_timeline_import(demo: Cs2Demo) -> TimelineImport:
    metadata = TimelineMetadata(
        schema_version=1,
        source_name="cs2-demo",
        map_name=demo.header.map_name,
        tick_rate=demo.header.tick_rate,
        raw=_copy_raw(demo.header.raw),
    )

    participants = tuple(
        Participant(
            participant_id=player.player_id,
            name=player.name,
            steam_id=player.steam_id,
            team=player.team,
            side=player.side,
            raw=_copy_raw(player.raw),
        )
        for player in demo.players
    )

    emitted: list[tuple[int, TimelineEvent]] = []
    per_tick_order: dict[int, int] = {}

    for kind, items in (
        ("round.recorded", demo.rounds),
        ("kill.recorded", demo.kills),
        ("event.recorded", demo.events),
    ):
        for item in items:
            tick = _source_tick(item)
            sequence = per_tick_order.get(tick, 0)
            per_tick_order[tick] = sequence + 1
            event = TimelineEvent(
                event_id=_event_id(kind, tick, sequence, item.raw),
                tick=tick,
                sequence=sequence,
                kind=kind,
                round_number=getattr(item, "round_number", None),
                participant_id=getattr(item, "attacker_player_id", None) or getattr(item, "player_id", None),
                raw=_copy_raw(item.raw),
            )
            emitted.append((tick, event))

    events = tuple(event for _, event in sorted(emitted, key=lambda item: (item[0], item[1].sequence, item[1].event_id)))
    return TimelineImport(metadata=metadata, participants=participants, events=events, raw={"header": _copy_raw(demo.header.raw)})


def _copy_raw(value: dict[str, object]) -> dict[str, object]:
    return dict(value)


def _source_tick(item: object) -> int:
    tick = getattr(item, "start_tick", None)
    if tick is not None:
        return tick
    tick = getattr(item, "tick", None)
    if tick is not None:
        return tick
    raise AttributeError("timeline source object does not expose a tick field")


def _event_id(kind: str, tick: int, sequence: int, raw: dict[str, object]) -> str:
    payload = f"{kind}|{tick}|{sequence}|{sorted(raw.items())!r}"
    return uuid5(NAMESPACE_URL, payload).hex
