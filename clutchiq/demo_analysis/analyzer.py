"""Deterministic analysis engine for Cs2Demo domain objects."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from clutchiq.demo_ingest.models import Cs2Demo, DemoKill, DemoPlayer, DemoRound

from clutchiq.demo_analysis.models import (
    AnalysisResult,
    FinalScore,
    MatchMetrics,
    MultiKillRecord,
    OpeningKill,
    PlayerMetrics,
    RoundMetrics,
    WinningSide,
)


@dataclass(frozen=True, slots=True)
class AnalysisEngine:
    """Analyze a parsed CS2 demo into immutable match metrics."""

    def analyze(self, demo: Cs2Demo) -> AnalysisResult:
        round_kills = self._group_kills_by_round(demo.kills)
        kill_index = {id(kill): index for index, kill in enumerate(demo.kills)}

        match = self._build_match_metrics(demo.rounds)
        player_metrics = self._build_player_metrics(demo.players, demo.kills, demo.rounds)
        round_metrics = tuple(
            self._build_round_metrics(round_, round_kills.get(round_.round_number, ()), kill_index)
            for round_ in demo.rounds
        )
        return AnalysisResult(match=match, players=player_metrics, rounds=round_metrics)

    def _build_match_metrics(self, rounds: tuple[DemoRound, ...]) -> MatchMetrics:
        ct_rounds = 0
        t_rounds = 0
        known_winners = 0
        for round_ in rounds:
            winner = self._normalize_winner(round_.winner_team)
            if winner == WinningSide.CT:
                ct_rounds += 1
                known_winners += 1
            elif winner == WinningSide.T:
                t_rounds += 1
                known_winners += 1
        final_score = FinalScore(ct_rounds=ct_rounds, t_rounds=t_rounds)
        if ct_rounds > t_rounds:
            winning_side = WinningSide.CT
        elif t_rounds > ct_rounds:
            winning_side = WinningSide.T
        else:
            winning_side = WinningSide.TIE
        return MatchMetrics(
            total_rounds=len(rounds),
            final_score=final_score,
            winning_side=winning_side,
            rounds_with_known_winner=known_winners,
        )

    def _build_player_metrics(
        self,
        players: tuple[DemoPlayer, ...],
        kills: tuple[DemoKill, ...],
        rounds: tuple[DemoRound, ...],
    ) -> tuple[PlayerMetrics, ...]:
        known_players: dict[int, DemoPlayer] = {player.player_id: player for player in players}
        event_player_ids = self._event_player_ids(kills)
        all_player_ids = list(dict.fromkeys([player.player_id for player in players] + sorted(event_player_ids - set(known_players))))

        kills_by_player = Counter[int]()
        deaths_by_player = Counter[int]()
        assists_by_player = Counter[int]()
        headshot_kills_by_player = Counter[int]()
        entry_kills_by_player = Counter[int]()
        entry_deaths_by_player = Counter[int]()
        survived_rounds_by_player = Counter[int]()

        round_number_to_kills = self._group_kills_by_round(kills)
        total_rounds = len(rounds)

        for kill in kills:
            if kill.attacker_player_id is not None:
                kills_by_player[kill.attacker_player_id] += 1
                if kill.headshot is True:
                    headshot_kills_by_player[kill.attacker_player_id] += 1
            if kill.victim_player_id is not None:
                deaths_by_player[kill.victim_player_id] += 1
            if kill.assister_player_id is not None:
                assists_by_player[kill.assister_player_id] += 1

        for round_ in rounds:
            kills_in_round = round_number_to_kills.get(round_.round_number, ())
            if not kills_in_round:
                for player_id in all_player_ids:
                    survived_rounds_by_player[player_id] += 1
                continue

            first_kill = self._opening_kill(kills_in_round)
            if first_kill is not None:
                if first_kill.attacker_player_id is not None:
                    entry_kills_by_player[first_kill.attacker_player_id] += 1
                if first_kill.victim_player_id is not None:
                    entry_deaths_by_player[first_kill.victim_player_id] += 1

            victims_this_round = {kill.victim_player_id for kill in kills_in_round if kill.victim_player_id is not None}
            for player_id in all_player_ids:
                if player_id not in victims_this_round:
                    survived_rounds_by_player[player_id] += 1

        results: list[PlayerMetrics] = []
        for player_id in all_player_ids:
            player = known_players.get(player_id)
            kills_count = kills_by_player[player_id]
            deaths_count = deaths_by_player[player_id]
            assists_count = assists_by_player[player_id]
            k_d = float(kills_count) if deaths_count == 0 else kills_count / deaths_count
            headshot_percentage = (headshot_kills_by_player[player_id] / kills_count * 100.0) if kills_count > 0 else 0.0
            survival_rate = (survived_rounds_by_player[player_id] / total_rounds) if total_rounds > 0 else 0.0
            results.append(
                PlayerMetrics(
                    player_id=player_id,
                    name=player.name if player else None,
                    steam_id=player.steam_id if player else None,
                    team=player.team if player else None,
                    side=player.side if player else None,
                    kills=kills_count,
                    deaths=deaths_count,
                    assists=assists_count,
                    k_d=k_d,
                    headshot_percentage=headshot_percentage,
                    entry_kills=entry_kills_by_player[player_id],
                    entry_deaths=entry_deaths_by_player[player_id],
                    survival_rate=survival_rate,
                )
            )
        return tuple(results)

    def _build_round_metrics(
        self,
        round_: DemoRound,
        kills_in_round: tuple[DemoKill, ...],
        kill_index: dict[int, int],
    ) -> RoundMetrics:
        winner = self._normalize_winner(round_.winner_team)
        opening = self._opening_kill(kills_in_round, kill_index, round_.round_number)
        multi_kills = self._multi_kills(kills_in_round)
        return RoundMetrics(
            round_number=round_.round_number,
            winner=winner,
            opening_kill=opening,
            multi_kills=multi_kills,
        )

    def _group_kills_by_round(self, kills: tuple[DemoKill, ...]) -> dict[int, tuple[DemoKill, ...]]:
        grouped: dict[int, list[DemoKill]] = defaultdict(list)
        for kill in kills:
            if kill.round_number is None:
                continue
            grouped[kill.round_number].append(kill)
        return {round_number: tuple(items) for round_number, items in grouped.items()}

    def _opening_kill(
        self,
        kills_in_round: tuple[DemoKill, ...],
        kill_index: dict[int, int] | None = None,
        round_number: int | None = None,
    ) -> OpeningKill | None:
        if not kills_in_round:
            return None
        if kill_index is None:
            kill_index = {id(kill): index for index, kill in enumerate(kills_in_round)}
        earliest = min(kills_in_round, key=lambda kill: (kill.tick, kill_index[id(kill)]))
        return OpeningKill(
            round_number=round_number,
            tick=earliest.tick,
            attacker_player_id=earliest.attacker_player_id,
            victim_player_id=earliest.victim_player_id,
            headshot=earliest.headshot,
            weapon=earliest.weapon,
        )

    def _multi_kills(self, kills_in_round: tuple[DemoKill, ...]) -> tuple[MultiKillRecord, ...]:
        counts: Counter[int] = Counter()
        for kill in kills_in_round:
            if kill.attacker_player_id is not None:
                counts[kill.attacker_player_id] += 1
        multi = [MultiKillRecord(player_id=player_id, kill_count=kill_count) for player_id, kill_count in counts.items() if kill_count >= 2]
        multi.sort(key=lambda record: (-record.kill_count, record.player_id))
        return tuple(multi)

    def _normalize_winner(self, winner: str | None) -> WinningSide:
        if winner is None:
            return WinningSide.TIE
        normalized = winner.strip().lower()
        if normalized in {"ct", "counter-terrorist", "counter-terrorists"}:
            return WinningSide.CT
        if normalized in {"t", "terrorist", "terrorists"}:
            return WinningSide.T
        return WinningSide.TIE

    def _event_player_ids(self, kills: tuple[DemoKill, ...]) -> set[int]:
        ids: set[int] = set()
        for kill in kills:
            if kill.attacker_player_id is not None:
                ids.add(kill.attacker_player_id)
            if kill.victim_player_id is not None:
                ids.add(kill.victim_player_id)
            if kill.assister_player_id is not None:
                ids.add(kill.assister_player_id)
        return ids
