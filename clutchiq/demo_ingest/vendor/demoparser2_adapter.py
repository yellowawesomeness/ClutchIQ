"""Adapter for demoparser2 outputs."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clutchiq.demo_ingest.errors import DemoParseError
from clutchiq.demo_ingest.models import (
    Cs2Demo,
    DemoEvent,
    DemoHeader,
    DemoKill,
    DemoPlayer,
    DemoPlayerRoundTeam,
    DemoRound,
)


@dataclass(frozen=True, slots=True)
class Demoparser2Adapter:
    """Normalize demoparser2 query outputs into ClutchIQ domain models."""

    def parse_bytes(self, data: bytes) -> Cs2Demo:
        try:
            import demoparser2  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover
            raise DemoParseError("demoparser2 is required to parse CS2 demo files") from exc
        with tempfile.NamedTemporaryFile(suffix=".dem", delete=False) as tmp:
            path = Path(tmp.name)
            tmp.write(data)
            tmp.flush()
        try:
            return self.parse_path(path, demoparser2)
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def parse_path(self, path: Path, demoparser2: Any) -> Cs2Demo:
        parser = self._build_parser(path, demoparser2)
        header = self._parse_header(parser)
        players = self._parse_players(parser)
        rounds = self._parse_rounds(parser)
        kills = self._parse_kills(parser)
        player_round_teams = self._parse_player_round_teams(kills)
        events = self._parse_events(parser)
        raw = {
            "header": header.raw,
            "players": [player.raw for player in players],
            "rounds": [round_.raw for round_ in rounds],
            "player_round_teams": [membership.raw for membership in player_round_teams],
            "kills": [kill.raw for kill in kills],
            "events": [event.raw for event in events],
        }
        return Cs2Demo(
            header=header,
            rounds=tuple(rounds),
            players=tuple(players),
            player_round_teams=tuple(player_round_teams),
            kills=tuple(kills),
            events=tuple(events),
            raw=raw,
        )

    def _build_parser(self, path: Path, demoparser2: Any) -> Any:
        if hasattr(demoparser2, "DemoParser"):
            return demoparser2.DemoParser(str(path))
        raise DemoParseError("Unsupported demoparser2 API: DemoParser not available")

    def _parse_header(self, parser: Any) -> DemoHeader:
        item = self._as_mapping(self._call_query(parser, "parse_header"))
        return DemoHeader(map_name=item.get("map_name"), server_name=item.get("server_name"), client_name=item.get("client_name"), raw=item)

    def _parse_players(self, parser: Any) -> list[DemoPlayer]:
        if not hasattr(parser, "parse_player_info"):
            return []
        return [self._to_player(item) for item in self._as_items(self._call_query(parser, "parse_player_info"))]

    def _parse_rounds(self, parser: Any) -> list[DemoRound]:
        events: list[dict[str, Any]] = []
        if hasattr(parser, "parse_events"):
            events.extend(self._as_named_event_rows(self._call_query(parser, "parse_events", ["round_start", "round_end", "round_freeze_end"])))
        rounds: dict[int, DemoRound] = {}
        for item in events:
            event_type = str(item.get("event_type") or item.get("type") or item.get("event") or "unknown")
            if event_type not in {"round_start", "round_end", "round_freeze_end"}:
                continue
            round_number = self._as_int(self._first_value(item, "round_number", "round")) or 0
            current = rounds.get(round_number)
            start_tick = current.start_tick if current else None
            end_tick = current.end_tick if current else None
            if event_type == "round_start":
                start_tick = self._as_int(self._first_value(item, "start_tick", "tick"))
            elif event_type == "round_end":
                end_tick = self._as_int(self._first_value(item, "end_tick", "tick"))
            rounds[round_number] = DemoRound(
                round_number=round_number,
                winner_team=item.get("winner_team") or item.get("winner") or (current.winner_team if current else None),
                start_tick=start_tick,
                end_tick=end_tick,
                score_ct=self._as_int(item.get("score_ct") or (current.score_ct if current else None)),
                score_t=self._as_int(item.get("score_t") or (current.score_t if current else None)),
                raw=item,
            )
        return [rounds[key] for key in sorted(rounds)]

    def _parse_kills(self, parser: Any) -> list[DemoKill]:
        rows: Any = []
        if hasattr(parser, "parse_event"):
            rows = self._call_query(parser, "parse_event", "player_death", player=["team_num"], other=["total_rounds_played"])
        kills: list[DemoKill] = []
        for item in self._as_items(rows):
            event_type = str(item.get("event_type") or item.get("type") or item.get("event") or "")
            if event_type and event_type != "player_death":
                continue
            kills.append(DemoKill(
                tick=self._as_int(item.get("tick")) or 0,
                attacker_player_id=self._as_int(self._first_value(item, "attacker_player_id", "attacker_steamid", "attacker")),
                victim_player_id=self._as_int(self._first_value(item, "victim_player_id", "user_steamid", "victim", "user")),
                assister_player_id=self._as_int(self._first_value(item, "assister_player_id", "assister_steamid", "assister")),
                weapon=item.get("weapon"),
                headshot=self._as_bool(item.get("headshot") if "headshot" in item else item.get("is_headshot")),
                round_number=self._as_int(self._first_value(item, "round_number", "round", "total_rounds_played")),
                raw=item,
            ))
        return kills

    def _parse_player_round_teams(self, kills: list[DemoKill]) -> list[DemoPlayerRoundTeam]:
        """Build round membership exclusively from player_death event columns."""
        memberships: dict[tuple[int, int], DemoPlayerRoundTeam] = {}
        for kill in kills:
            if kill.round_number is None:
                continue
            for player_id, column_names in (
                (kill.attacker_player_id, ("attacker_team_num",)),
                (kill.victim_player_id, ("user_team_num", "victim_team_num")),
            ):
                team_num = self._as_int(self._first_value(kill.raw, *column_names))
                if player_id is None or team_num is None:
                    continue
                key = (kill.round_number, player_id)
                membership = DemoPlayerRoundTeam(player_id=player_id, round_number=kill.round_number, team_num=team_num, raw=dict(kill.raw))
                existing = memberships.get(key)
                if existing is None:
                    memberships[key] = membership
                elif existing.team_num != team_num:
                    raise DemoParseError(f"Conflicting team_num for player {player_id} in round {kill.round_number}")
        return [memberships[key] for key in sorted(memberships)]

    def _parse_events(self, parser: Any) -> list[DemoEvent]:
        rows: Any = []
        if hasattr(parser, "parse_events"):
            rows = self._call_query(parser, "parse_events", ["round_start", "round_end", "round_freeze_end", "player_death"])
        return [DemoEvent(tick=self._as_int(item.get("tick")) or 0, event_type=str(item.get("event_type") or item.get("type") or item.get("event") or "unknown"), round_number=self._as_int(self._first_value(item, "round_number", "round")), raw=item) for item in self._as_named_event_rows(rows)]

    def _to_player(self, item: Any) -> DemoPlayer:
        item = self._as_mapping(item)
        return DemoPlayer(player_id=self._as_int(self._first_value(item, "player_id", "id", "index")) or 0, name=item.get("name"), steam_id=self._as_int(self._first_value(item, "steam_id", "steamid")), team=item.get("team") or item.get("team_name"), side=item.get("side"), raw=item)

    def _call_query(self, parser: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
        method = getattr(parser, method_name, None)
        if not callable(method):
            raise DemoParseError(f"Unsupported demoparser2 API: {method_name} not available")
        return method(*args, **kwargs)

    def _as_items(self, items: Any) -> list[dict[str, Any]]:
        if items is None:
            return []
        if hasattr(items, "to_dicts"):
            return self._as_items(items.to_dicts())
        if hasattr(items, "to_dict"):
            try:
                return self._as_items(items.to_dict("records"))
            except TypeError:
                return self._as_items(items.to_dict())
        if hasattr(items, "to_json"):
            import json
            return self._as_items(json.loads(items.to_json()))
        if hasattr(items, "to_records"):
            return self._as_items(items.to_records())
        if isinstance(items, dict):
            return [dict(items)]
        if isinstance(items, (list, tuple)):
            return [self._as_mapping(item) for item in items]
        return []

    def _as_named_event_rows(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            return self._as_items(payload)
        rows: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, tuple) and len(item) == 2:
                event_name, frame = item
                for row in self._as_items(frame):
                    normalized = dict(row)
                    normalized["event_type"] = event_name
                    rows.append(normalized)
            else:
                rows.extend(self._as_items(item))
        return rows

    def _as_mapping(self, item: Any) -> dict[str, Any]:
        if item is None:
            return {}
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "to_dict"):
            return self._as_mapping(item.to_dict())
        if hasattr(item, "__dict__"):
            return {key: value for key, value in vars(item).items() if not key.startswith("_")}
        return {"value": item}

    @staticmethod
    def _first_value(item: dict[str, Any], *names: str) -> Any:
        for name in names:
            if name in item and item[name] is not None:
                return item[name]
        return None

    def _as_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _as_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _as_bool(self, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                return True
            if lowered in {"false", "0", "no", "n"}:
                return False
        return bool(value)
