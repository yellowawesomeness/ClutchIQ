"""Validation helpers for replay state."""

from __future__ import annotations

from clutchiq.timeline_engine.models import Tick


def validate_replay_tick(tick: Tick) -> None:
    if tick < 0:
        raise ValueError("tick must be non-negative")
