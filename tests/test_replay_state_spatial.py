from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from clutchiq.replay_state.service import ReplayStateService
from clutchiq.replay_state.spatial import SPATIAL_COLUMNS, SpatialReplayData


REAL_DEMO = Path('demos/MATCH20260725-1.dem')


def _demo_parser_available() -> bool:
    if not REAL_DEMO.exists():
        return False
    if importlib.util.find_spec('demoparser2') is None:
        return False
    try:
        from demoparser2 import DemoParser  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.integration
def test_real_demo_spatial_frame_properties() -> None:
    if not _demo_parser_available():
        pytest.skip('demoparser2 demo parser unavailable')

    from demoparser2 import DemoParser

    frame = DemoParser(str(REAL_DEMO)).parse_ticks(list(SPATIAL_COLUMNS))
    spatial = SpatialReplayData.from_parse_ticks(frame)

    assert list(spatial.frame.columns) == list(SPATIAL_COLUMNS)
    assert str(spatial.frame['tick'].dtype) == 'uint32'
    assert str(spatial.frame['X'].dtype) == 'float32'
    assert str(spatial.frame['is_alive'].dtype) == 'bool'
    assert spatial.frame['tick'].is_monotonic_increasing
    assert spatial.frame['tick'].nunique() == len(spatial.frame.groupby('tick'))
    assert not spatial.frame.empty

    sample_ticks = spatial.frame['tick'].drop_duplicates().sample(n=min(5, spatial.frame['tick'].nunique()), random_state=1)
    for tick in sample_ticks.tolist():
        filtered = spatial.frame.loc[spatial.frame['tick'] == tick]
        assert spatial.rows_at_tick(int(tick)).reset_index(drop=True).equals(filtered.reset_index(drop=True))


@dataclass(frozen=True, slots=True)
class _Reader:
    frame: pd.DataFrame

    @property
    def metadata(self):
        return object()

    def participants(self):
        return ()

    def parse_ticks(self):
        return self.frame


@dataclass(frozen=True, slots=True)
class _Source:
    reader: _Reader

    def open(self, timeline_id):
        return self.reader


@pytest.mark.integration
def test_replay_state_service_tick_query_matches_canonical_filter() -> None:
    if not _demo_parser_available():
        pytest.skip('demoparser2 demo parser unavailable')

    from demoparser2 import DemoParser

    frame = DemoParser(str(REAL_DEMO)).parse_ticks(list(SPATIAL_COLUMNS))
    service = ReplayStateService(source=_Source(_Reader(frame)))
    session = service.open('timeline-1')
    spatial = SpatialReplayData.from_parse_ticks(frame)

    sample_ticks = spatial.frame['tick'].drop_duplicates().sample(n=min(7, spatial.frame['tick'].nunique()), random_state=2)
    for tick in sample_ticks.tolist():
        state = session.state_at(int(tick))
        expected = spatial.frame.loc[spatial.frame['tick'] == tick].reset_index(drop=True)
        actual = state.spatial_frame.reset_index(drop=True)
        pd.testing.assert_frame_equal(actual, expected, check_dtype=True)
