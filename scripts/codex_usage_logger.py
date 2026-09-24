"""Local, versioned Codex usage snapshots by task; never stores raw provider data."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import uuid
from typing import Any, Callable, Mapping

import codex_usage_reader

SCHEMA_VERSION = 1
PHASES = ("START", "PLAN", "EXECUTED", "DONE", "BLOCKED", "ABORTED")
WINDOWS = {
    "five_hour": ("five_hour_remaining_percent", "five_hour_reset_at"),
    "weekly": ("weekly_remaining_percent", "weekly_reset_at"),
}
TASK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}\Z")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class UsageLogError(ValueError):
    """Raised when a local usage record is invalid or cannot be updated safely."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(value: Any, field: str) -> tuple[str, dt.datetime]:
    if not isinstance(value, str) or not value.strip():
        raise UsageLogError(f"{field} must be a timezone-aware ISO-8601 timestamp.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UsageLogError(f"{field} must be a timezone-aware ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise UsageLogError(f"{field} must include a timezone.")
    parsed = parsed.astimezone(dt.timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z"), parsed


def _task_id(value: str) -> str:
    if not isinstance(value, str) or not TASK_ID_RE.fullmatch(value) or value in {".", ".."}:
        raise UsageLogError("Invalid task_id; use 1-80 letters, digits, dots, underscores or hyphens.")
    if value.rstrip(". ") != value or value.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        raise UsageLogError("Invalid task_id for a Windows filename.")
    return value


def _directory(root: str | Path | None) -> Path:
    project_root = Path(root) if root is not None else Path(__file__).resolve().parent.parent
    base = project_root / ".project-intelligence" / "codex-usage"
    resolved = base.resolve()
    expected = (project_root / ".project-intelligence").resolve()
    if expected not in resolved.parents:
        raise UsageLogError("Usage log directory escaped the project state directory.")
    return resolved


def _path(task_id: str, root: str | Path | None = None) -> Path:
    safe_id = _task_id(task_id)
    directory = _directory(root)
    path = (directory / f"{safe_id}.json").resolve()
    if path.parent != directory:
        raise UsageLogError("task_id resolved outside the usage log directory.")
    return path


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _validate_percent(value: Any, field: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise UsageLogError(f"{field} must be a finite percentage or null.")
    if not 0 <= float(value) <= 100:
        raise UsageLogError(f"{field} must be between 0 and 100.")
    value = round(float(value), 4)
    return int(value) if value.is_integer() else value


def _validate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise UsageLogError("snapshot must be an object.")
    phase = snapshot.get("phase")
    if phase not in PHASES:
        raise UsageLogError("snapshot phase is invalid.")
    captured_at, _ = _timestamp(snapshot.get("captured_at"), "captured_at")
    status = snapshot.get("measurement_status")
    if status not in {"ok", "unavailable"}:
        raise UsageLogError("measurement_status must be ok or unavailable.")
    result = {
        "phase": phase,
        "captured_at": captured_at,
        "measurement_status": status,
    }
    for name, (percent_key, reset_key) in WINDOWS.items():
        percent = _validate_percent(snapshot.get(percent_key), percent_key)
        reset = snapshot.get(reset_key)
        if reset is not None:
            reset, _ = _timestamp(reset, reset_key)
        if status == "unavailable" and (percent is not None or reset is not None):
            raise UsageLogError("Unavailable measurements must have null quota fields.")
        result[percent_key] = percent
        result[reset_key] = reset
    source = snapshot.get("source")
    if source is not None and (not isinstance(source, str) or len(source) > 160):
        raise UsageLogError("source must be a short string or null.")
    parser_version = snapshot.get("parser_version")
    if parser_version is not None and (not isinstance(parser_version, str) or len(parser_version) > 40):
        raise UsageLogError("parser_version must be a short string or null.")
    codex_version = snapshot.get("codex_version")
    if codex_version is not None and (not isinstance(codex_version, str) or len(codex_version) > 120):
        raise UsageLogError("codex_version must be a short string or null.")
    snapshot_id = snapshot.get("snapshot_id")
    if snapshot_id is not None and (not isinstance(snapshot_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", snapshot_id)):
        raise UsageLogError("snapshot_id is invalid.")
    error_code = snapshot.get("error_code")
    if error_code not in {None, "usage_unavailable"}:
        raise UsageLogError("error_code is invalid.")
    if status == "ok" and error_code is not None:
        raise UsageLogError("Successful measurements cannot have an error_code.")
    if status == "unavailable" and error_code != "usage_unavailable":
        raise UsageLogError("Unavailable measurements require the generic usage_unavailable code.")
    result.update({
        "source": source,
        "parser_version": parser_version,
        "codex_version": codex_version,
        "error_code": error_code,
    })
    if snapshot_id is not None:
        result["snapshot_id"] = snapshot_id
    return result


def _load(path: Path, expected_task_id: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageLogError("The local usage record is missing or invalid; it was not changed.") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise UsageLogError("Unsupported or invalid usage record schema; it was not changed.")
    if data.get("task_id") != expected_task_id:
        raise UsageLogError("The local usage record task_id does not match the requested task.")
    if data.get("status") not in {"active", "done", "blocked", "aborted"}:
        raise UsageLogError("The local usage record has an invalid status.")
    if not isinstance(data.get("snapshots"), list):
        raise UsageLogError("The local usage record snapshots are invalid.")
    for snapshot in data["snapshots"]:
        _validate_snapshot(snapshot)
    if data.get("started_at") is not None:
        _timestamp(data["started_at"], "started_at")
    if data.get("finished_at") is not None:
        _timestamp(data["finished_at"], "finished_at")
    return data


def _snapshot_identity(snapshot: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(snapshot.get(key) for key in (
        "phase", "captured_at", "measurement_status",
        "five_hour_remaining_percent", "five_hour_reset_at",
        "weekly_remaining_percent", "weekly_reset_at", "source", "parser_version",
        "codex_version", "error_code", "snapshot_id",
    ))


def _ordered_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(snapshot: dict[str, Any]) -> tuple[dt.datetime, str, str]:
        _, parsed = _timestamp(snapshot["captured_at"], "captured_at")
        return parsed, snapshot["phase"], snapshot.get("snapshot_id", "")
    return sorted(snapshots, key=key)


def _reset_events(snapshots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    ordered = _ordered_snapshots(snapshots)
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in WINDOWS}
    for previous, current in zip(ordered, ordered[1:]):
        if previous["measurement_status"] != "ok" or current["measurement_status"] != "ok":
            continue
        for name, (percent_key, reset_key) in WINDOWS.items():
            before = previous.get(percent_key)
            after = current.get(percent_key)
            if before is None or after is None:
                continue
            reset_before, reset_after = previous.get(reset_key), current.get(reset_key)
            reset_changed = reset_before is not None and reset_after is not None and reset_before != reset_after
            increased = after > before
            if reset_changed or increased:
                events[name].append({
                    "from_captured_at": previous["captured_at"],
                    "from_phase": previous["phase"],
                    "to_captured_at": current["captured_at"],
                    "to_phase": current["phase"],
                    "reset_timestamp_changed": reset_changed,
                    "remaining_increased": increased,
                    "reset_at_before": reset_before,
                    "reset_at_after": reset_after,
                })
    return events


def _transition(start: dict[str, Any] | None, end: dict[str, Any] | None,
                events: list[dict[str, Any]], window: str) -> dict[str, Any]:
    percent_key, reset_key = WINDOWS[window]
    before = start.get(percent_key) if start else None
    after = end.get(percent_key) if end else None
    reset_before = start.get(reset_key) if start else None
    reset_after = end.get(reset_key) if end else None
    reset_detected = False
    if start and end:
        start_time = _timestamp(start["captured_at"], "captured_at")[1]
        end_time = _timestamp(end["captured_at"], "captured_at")[1]
        intermediate_reset = any(
            start_time <= _timestamp(event["to_captured_at"], "captured_at")[1] <= end_time
            for event in events
        )
        endpoint_reset_changed = (
            reset_before is not None and reset_after is not None and reset_before != reset_after
        )
        endpoint_remaining_increased = (
            before is not None and after is not None and after > before
        )
        # Endpoint comparisons are necessary when an unavailable/missing snapshot
        # interrupts adjacency-based reset detection but the endpoints still show
        # that a reset occurred somewhere in the transition.
        reset_detected = intermediate_reset or endpoint_reset_changed or endpoint_remaining_increased
    valid = (start is not None and end is not None
             and start.get("measurement_status") == "ok"
             and end.get("measurement_status") == "ok"
             and before is not None and after is not None and not reset_detected)
    consumed = max(0, before - after) if valid else None
    return {
        "start_remaining_percent": before,
        "end_remaining_percent": after,
        "consumed_percentage_points": consumed,
        "reset_detected": reset_detected,
        "reset_at_start": reset_before,
        "reset_at_end": reset_after,
        "mathematically_valid": bool(valid),
    }


def derive(record: Mapping[str, Any]) -> dict[str, Any]:
    snapshots = record.get("snapshots", [])
    latest: dict[str, dict[str, Any]] = {}
    for snapshot in _ordered_snapshots(snapshots):
        latest[snapshot["phase"]] = snapshot
    events = _reset_events(snapshots)
    pairs = {
        "START_TO_PLAN": (latest.get("START"), latest.get("PLAN")),
        "PLAN_TO_EXECUTED": (latest.get("PLAN"), latest.get("EXECUTED")),
        "EXECUTED_TO_DONE": (latest.get("EXECUTED"), latest.get("DONE")),
        "START_TO_DONE": (latest.get("START"), latest.get("DONE")),
    }
    transitions: dict[str, Any] = {}
    for pair_name, (start, end) in pairs.items():
        transitions[pair_name] = {
            window: _transition(start, end, events[window], window)
            for window in WINDOWS
        }
    started = record.get("started_at")
    finished = record.get("finished_at")
    duration_minutes = None
    if started is not None and finished is not None:
        start_dt = _timestamp(started, "started_at")[1]
        finish_dt = _timestamp(finished, "finished_at")[1]
        delta = (finish_dt - start_dt).total_seconds() / 60
        if delta >= 0:
            duration_minutes = round(delta, 4)
    total = transitions["START_TO_DONE"]
    points_per_minute = {
        window: (round(result["consumed_percentage_points"] / duration_minutes, 6)
                 if duration_minutes is not None and duration_minutes > 0 and result["mathematically_valid"]
                 else None)
        for window, result in total.items()
    }
    reset_flags = {
        window: bool(events[window]) or any(
            transition[window]["reset_detected"] for transition in transitions.values()
        )
        for window in WINDOWS
    }
    return {
        "transitions": transitions,
        "reset_events": events,
        "reset_during_task_by_window": reset_flags,
        "reset_during_task": any(reset_flags.values()),
        "duration_minutes": duration_minutes,
        "percentage_points_per_minute": points_per_minute,
    }


def _persist(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    record["derived"] = derive(record)
    _atomic_json(path, record)
    return record


def _capture(phase: str, *, usage_reader: Callable[[], Mapping[str, Any]] | None = None,
             captured_at: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    if phase not in PHASES:
        raise UsageLogError("phase is invalid.")
    try:
        usage = (usage_reader or codex_usage_reader.read_codex_usage)()
    except codex_usage_reader.UsageReaderError:
        stamp, _ = _timestamp(captured_at or _utc_now(), "captured_at")
        snapshot = {
            "phase": phase, "captured_at": stamp, "measurement_status": "unavailable",
            **{key: None for pair in WINDOWS.values() for key in pair},
            "source": codex_usage_reader.SOURCE, "parser_version": codex_usage_reader.PARSER_VERSION,
            "codex_version": None, "error_code": "usage_unavailable",
        }
    else:
        if not isinstance(usage, Mapping):
            raise UsageLogError("The accepted usage reader returned an invalid object.")
        stamp, _ = _timestamp(captured_at or usage.get("captured_at"), "captured_at")
        snapshot = {
            "phase": phase,
            "captured_at": stamp,
            "measurement_status": "ok",
            **{key: usage.get(key) for pair in WINDOWS.values() for key in pair},
            "source": usage.get("source"),
            "parser_version": usage.get("parser_version"),
            "codex_version": usage.get("codex_version"),
            "error_code": None,
        }
    if snapshot_id is not None:
        snapshot["snapshot_id"] = snapshot_id
    return _validate_snapshot(snapshot)


def _append_snapshot(record: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    identity = _snapshot_identity(snapshot)
    for existing in record["snapshots"]:
        if snapshot.get("snapshot_id") is not None and existing.get("snapshot_id") == snapshot["snapshot_id"]:
            if _snapshot_identity(existing) != identity:
                raise UsageLogError("snapshot_id already exists with different data; history was preserved.")
            return False
        if _snapshot_identity(existing) == identity:
            return False
    record["snapshots"].append(snapshot)
    return True


def start(task_id: str, *, root: str | Path | None = None,
          usage_reader: Callable[[], Mapping[str, Any]] | None = None,
          captured_at: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    task_id = _task_id(task_id)
    path = _path(task_id, root)
    if path.exists():
        record = _load(path, task_id)
        if record["status"] != "active":
            raise UsageLogError("This task log is already closed and cannot be resumed as active.")
        if any(item["phase"] == "START" for item in record["snapshots"]):
            return record
    else:
        record = {
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
            "status": "active",
            "started_at": None,
            "finished_at": None,
            "model": None,
            "configuration": None,
            "snapshots": [],
            "derived": {},
        }
    snapshot = _capture("START", usage_reader=usage_reader, captured_at=captured_at, snapshot_id=snapshot_id)
    if record["started_at"] is None:
        record["started_at"] = snapshot["captured_at"]
    _append_snapshot(record, snapshot)
    return _persist(path, record)


def add_snapshot(task_id: str, phase: str, *, root: str | Path | None = None,
                 usage_reader: Callable[[], Mapping[str, Any]] | None = None,
                 captured_at: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    task_id = _task_id(task_id)
    if phase not in {"PLAN", "EXECUTED"}:
        raise UsageLogError("snapshot phase must be PLAN or EXECUTED; use close for terminal phases.")
    path = _path(task_id, root)
    record = _load(path, task_id)
    if record["status"] != "active":
        raise UsageLogError("Cannot add a snapshot to a closed task log.")
    snapshot = _capture(phase, usage_reader=usage_reader, captured_at=captured_at, snapshot_id=snapshot_id)
    if not _append_snapshot(record, snapshot):
        return record
    return _persist(path, record)


def close(task_id: str, status: str = "DONE", *, root: str | Path | None = None,
          usage_reader: Callable[[], Mapping[str, Any]] | None = None,
          captured_at: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    task_id = _task_id(task_id)
    status = status.upper()
    if status not in {"DONE", "BLOCKED", "ABORTED"}:
        raise UsageLogError("close status must be DONE, BLOCKED or ABORTED.")
    path = _path(task_id, root)
    record = _load(path, task_id)
    if record["status"] != "active":
        if record["status"] == status.lower():
            return record
        raise UsageLogError("Task log is already closed with a different status.")
    snapshot = _capture(status, usage_reader=usage_reader, captured_at=captured_at, snapshot_id=snapshot_id)
    stamp = snapshot["captured_at"]
    _append_snapshot(record, snapshot)
    record["status"] = status.lower()
    record["finished_at"] = stamp
    return _persist(path, record)


def inspect(task_id: str, *, root: str | Path | None = None) -> dict[str, Any]:
    task_id = _task_id(task_id)
    record = _load(_path(task_id, root), task_id)
    # Recompute for the view only; inspection never persists or calls the usage reader.
    result = dict(record)
    result["derived"] = derive(record)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="Project root (defaults to this repository).")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("start", "snapshot", "close", "inspect"):
        child = sub.add_parser(command)
        child.add_argument("--task-id", required=True)
        child.add_argument("--snapshot-id", default=None, help="Stable retry key for idempotent capture.")
        if command == "snapshot":
            child.add_argument("--phase", choices=("PLAN", "EXECUTED"), required=True)
        if command == "close":
            child.add_argument("--status", choices=("DONE", "BLOCKED", "ABORTED"), default="DONE")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "start":
            result = start(args.task_id, root=args.root, snapshot_id=args.snapshot_id)
        elif args.command == "snapshot":
            result = add_snapshot(args.task_id, args.phase, root=args.root, snapshot_id=args.snapshot_id)
        elif args.command == "close":
            result = close(args.task_id, args.status, root=args.root, snapshot_id=args.snapshot_id)
        else:
            result = inspect(args.task_id, root=args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except UsageLogError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
