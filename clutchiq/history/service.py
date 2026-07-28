"""Atomic JSON persistence and dashboard aggregation for demo imports."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from clutchiq.history.models import (
    AnalysisSummary,
    DashboardSummary,
    DemoImportResult,
    ImportResult,
    ImportStage,
    PersistedImportRecord,
    RecentDemoEntry,
)


class DemoHistoryError(RuntimeError):
    """Raised when history cannot be loaded or written."""


def default_history_path() -> Path:
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "ClutchIQ" / "demo_history.json"
    return Path.home() / ".clutchiq" / "demo_history.json"


class DemoHistoryService:
    def __init__(self, history_path: Path | None = None) -> None:
        self._path = history_path or default_history_path()

    @property
    def path(self) -> Path:
        return self._path

    def record_import(self, result: DemoImportResult) -> None:
        payload = self._read_payload()
        record = self._encode_result(result)
        if not payload:
            payload = {
                "schema_version": 1,
                "created_at": self._utc_now(),
                "updated_at": self._utc_now(),
                "records": [record],
            }
        else:
            payload["updated_at"] = self._utc_now()
            payload.setdefault("records", []).append(record)
        try:
            self._atomic_write(payload)
        except OSError as exc:
            raise DemoHistoryError("Unable to write history file.") from exc

    def load_summary(self) -> DashboardSummary:
        try:
            payload = self._read_payload()
        except DemoHistoryError:
            return DashboardSummary(
                is_available=False,
                is_empty=True,
                import_status="Import history unavailable",
                total_demos_imported=0,
                total_matches=0,
                last_import_time="Unavailable",
                recent_demos=(),
                records=(),
            )

        records = tuple(self._decode_record(record) for record in payload.get("records", []))
        total_demos_imported = sum(1 for record in records if record.result == ImportResult.SUCCESS)
        total_matches = total_demos_imported
        recent_demos = tuple(
            RecentDemoEntry(
                id=record.id,
                source_name=record.source_name,
                imported_at_utc=record.imported_at_utc,
                result=record.result,
                parse_stage=record.parse_stage,
                winning_side=record.analysis_summary.winning_side if record.analysis_summary is not None else None,
            )
            for record in records[-5:]
        )
        latest = records[-1] if records else None
        import_status = "No imports yet"
        if latest is not None:
            if latest.result == ImportResult.SUCCESS:
                import_status = f"Last import succeeded: {latest.source_name}"
            else:
                import_status = f"Last import failed: {latest.source_name}"

        return DashboardSummary(
            is_available=True,
            is_empty=not records,
            import_status=import_status,
            total_demos_imported=total_demos_imported,
            total_matches=total_matches,
            last_import_time=latest.imported_at_utc if latest is not None else "No imports yet",
            recent_demos=recent_demos,
            records=records,
        )

    def _read_payload(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DemoHistoryError("Unable to read history file.") from exc
        if not isinstance(payload, dict):
            raise DemoHistoryError("Invalid history format.")
        if int(payload.get("schema_version", 0)) != 1:
            raise DemoHistoryError("Unsupported history schema.")
        if "created_at" not in payload or "updated_at" not in payload:
            raise DemoHistoryError("Missing history metadata.")
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise DemoHistoryError("Invalid history records.")
        return payload

    def _decode_record(self, raw: object) -> PersistedImportRecord:
        if not isinstance(raw, dict):
            raise DemoHistoryError("Invalid record.")
        analysis_raw = raw.get("analysis_summary")
        analysis = None
        if isinstance(analysis_raw, dict):
            analysis = AnalysisSummary(
                total_rounds=int(analysis_raw["total_rounds"]),
                ct_rounds=int(analysis_raw["ct_rounds"]),
                t_rounds=int(analysis_raw["t_rounds"]),
                winning_side=str(analysis_raw["winning_side"]),
                rounds_with_known_winner=int(analysis_raw["rounds_with_known_winner"]),
            )
        return PersistedImportRecord(
            id=str(raw["id"]),
            imported_at_utc=str(raw["imported_at_utc"]),
            source_path=str(raw["source_path"]) if raw.get("source_path") is not None else None,
            source_name=str(raw["source_name"]),
            result=ImportResult(str(raw["result"])),
            parse_stage=ImportStage(str(raw["parse_stage"])),
            analysis_summary=analysis,
            error_type=str(raw["error_type"]) if raw.get("error_type") is not None else None,
            error_message=str(raw["error_message"]) if raw.get("error_message") is not None else None,
        )

    def _encode_result(self, result: DemoImportResult) -> dict:
        return {
            "id": result.id,
            "imported_at_utc": result.imported_at_utc.isoformat(),
            "source_path": str(result.source_path) if result.source_path is not None else None,
            "source_name": result.source_name,
            "result": result.result.value,
            "parse_stage": result.parse_stage.value,
            "analysis_summary": asdict(result.analysis_summary) if result.analysis_summary is not None else None,
            "error_type": result.error_type,
            "error_message": result.error_message,
        }

    def _atomic_write(self, payload: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f"{self._path.stem}.", suffix=".tmp", dir=str(self._path.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            temp_path.replace(self._path)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
