"""Experimental, read-only Codex account usage reader via documented app-server JSONL."""
from __future__ import annotations

import datetime as dt
import json
import math
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping
from typing import Any

PARSER_VERSION = "1"
RATE_LIMITS_METHOD = "account/rateLimits/read"
SOURCE = "codex app-server account/rateLimits/read"
FIVE_HOUR_MINUTES = 5 * 60
WEEKLY_MINUTES = 7 * 24 * 60


class UsageReaderError(RuntimeError):
    """Raised when Codex usage cannot be read or safely normalized."""


def _utc_iso(epoch: Any) -> str | None:
    if isinstance(epoch, bool) or not isinstance(epoch, (int, float)):
        return None
    if not math.isfinite(float(epoch)):
        return None
    try:
        return dt.datetime.fromtimestamp(float(epoch), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _remaining_percent(window: Mapping[str, Any]) -> int | float | None:
    used = window.get("usedPercent")
    if isinstance(used, bool) or not isinstance(used, (int, float)) or not math.isfinite(float(used)):
        return None
    if not 0 <= float(used) <= 100:
        raise UsageReaderError("Codex returned an out-of-range usage percentage.")
    remaining = round(100 - float(used), 4)
    return int(remaining) if remaining.is_integer() else remaining


def _codex_bucket(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    buckets = result.get("rateLimitsByLimitId")
    if isinstance(buckets, Mapping):
        bucket = buckets.get("codex")
        if isinstance(bucket, Mapping) and bucket.get("limitId", "codex") == "codex":
            return bucket
    legacy = result.get("rateLimits")
    if isinstance(legacy, Mapping) and legacy.get("limitId") == "codex":
        return legacy
    return None


def _find_window(bucket: Mapping[str, Any], duration: int) -> Mapping[str, Any] | None:
    matches = [
        bucket[key]
        for key in ("primary", "secondary")
        if isinstance(bucket.get(key), Mapping)
        and bucket[key].get("windowDurationMins") == duration
    ]
    if len(matches) > 1:
        raise UsageReaderError("Codex returned ambiguous rate-limit windows.")
    return matches[0] if matches else None


def normalize_rate_limits(
    response: Mapping[str, Any], *, captured_at: str | None = None, codex_version: str | None = None
) -> dict[str, Any]:
    """Keep only documented Codex quota fields; unknown fields are discarded."""
    if not isinstance(response, Mapping):
        raise UsageReaderError("Codex returned an unsupported rate-limit response.")
    result = response.get("result", response)
    if not isinstance(result, Mapping):
        raise UsageReaderError("Codex returned an unsupported rate-limit response.")
    bucket = _codex_bucket(result)
    if bucket is None:
        raise UsageReaderError("Codex did not return a recognizable account rate-limit bucket.")
    five_hour = _find_window(bucket, FIVE_HOUR_MINUTES)
    weekly = _find_window(bucket, WEEKLY_MINUTES)

    return {
        "five_hour_remaining_percent": _remaining_percent(five_hour) if five_hour else None,
        "five_hour_reset_at": _utc_iso(five_hour.get("resetsAt")) if five_hour else None,
        "weekly_remaining_percent": _remaining_percent(weekly) if weekly else None,
        "weekly_reset_at": _utc_iso(weekly.get("resetsAt")) if weekly else None,
        "session_context_remaining_percent": None,
        "model": None,
        "configuration": None,
        "captured_at": captured_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": SOURCE,
        "parser_version": PARSER_VERSION,
        "codex_version": codex_version,
    }


class _JsonLineReader:
    def __init__(self, stream: Any):
        self.messages: queue.Queue[Any] = queue.Queue()

        def pump() -> None:
            try:
                for line in stream:
                    try:
                        self.messages.put(json.loads(line))
                    except (TypeError, json.JSONDecodeError):
                        continue
            finally:
                self.messages.put(None)

        threading.Thread(target=pump, daemon=True).start()

    def response(self, request_id: int, timeout: float) -> Mapping[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise UsageReaderError("Timed out waiting for the Codex app-server response.")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise UsageReaderError("Timed out waiting for the Codex app-server response.") from exc
            if message is None:
                raise UsageReaderError("Codex app-server closed before returning usage.")
            if isinstance(message, Mapping) and message.get("id") == request_id:
                if "error" in message:
                    raise UsageReaderError("Codex app-server could not provide rate limits.")
                return message


def _codex_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=3, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # Keep only the first short version line; never surface arbitrary command output.
    if completed.returncode != 0:
        return None
    line = completed.stdout.splitlines()[0].strip() if completed.stdout else ""
    return line[:120] or None


def read_codex_usage(*, executable: str | None = None, timeout: float = 12.0) -> dict[str, Any]:
    """Read only the Codex quota windows through its local app-server process."""
    codex = executable or shutil.which("codex")
    if not codex:
        raise UsageReaderError("Codex CLI was not found on PATH.")
    try:
        process = subprocess.Popen(
            [codex, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
    except OSError as exc:
        raise UsageReaderError("Could not start the Codex app-server.") from exc

    try:
        if process.stdin is None or process.stdout is None:
            raise UsageReaderError("Codex app-server did not expose its JSONL transport.")
        reader = _JsonLineReader(process.stdout)

        def send(message: Mapping[str, Any]) -> None:
            process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
            process.stdin.flush()

        send({
            "method": "initialize",
            "id": 0,
            "params": {
                "clientInfo": {"name": "codex_usage_reader", "title": "Codex usage reader", "version": PARSER_VERSION},
                "capabilities": {"optOutNotificationMethods": ["account/updated", "account/rateLimits/updated"]},
            },
        })
        reader.response(0, timeout)
        send({"method": "initialized", "params": {}})
        send({"method": RATE_LIMITS_METHOD, "id": 1, "params": {}})
        response = reader.response(1, timeout)
        usage = normalize_rate_limits(response, codex_version=_codex_version(codex))
        return usage
    except UsageReaderError:
        raise
    except (OSError, ValueError, TypeError, BrokenPipeError) as exc:
        raise UsageReaderError("Could not safely parse Codex account usage.") from exc
    finally:
        if process.stdin:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)


def main() -> int:
    try:
        print(json.dumps(read_codex_usage(), ensure_ascii=False, separators=(",", ":")))
        return 0
    except UsageReaderError as exc:
        # Errors are fixed/sanitized strings; never print raw app-server output.
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
