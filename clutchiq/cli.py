"""Command-line entry points for ClutchIQ."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from clutchiq.demo_ingest import Cs2DemoParser, DemoIngestService, DemoParseError, DemoReadError
from clutchiq.demo_ingest.summary import build_match_summary, format_match_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clutchiq")
    parser.add_argument("demo_path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = DemoIngestService(parser=Cs2DemoParser())
    try:
        demo = service.ingest_path(args.demo_path)
        print(format_match_summary(build_match_summary(demo)))
        return 0
    except (DemoReadError, DemoParseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
