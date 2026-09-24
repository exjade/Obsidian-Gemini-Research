import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_usage_reader as reader


class CodexUsageReaderTests(unittest.TestCase):
    def response(self):
        return {
            "id": 1,
            "result": {
                "rateLimitsByLimitId": {
                    "codex": {
                        "limitId": "codex",
                        "primary": {"usedPercent": 19, "windowDurationMins": 300, "resetsAt": 1790255913},
                        "secondary": {"usedPercent": 42, "windowDurationMins": 10080, "resetsAt": 1790713086},
                        "accessToken": "MUST_NOT_ESCAPE_FIXTURE",
                    },
                    "other": {"limitId": "other", "primary": {"usedPercent": 99, "windowDurationMins": 30}},
                },
                "rateLimitResetCredits": {"credits": [{"id": "not usage output"}]},
            },
        }

    def test_maps_five_hour_and_weekly_windows_to_remaining_and_utc_resets(self):
        result = reader.normalize_rate_limits(
            self.response(), captured_at="2026-09-24T12:00:00Z", codex_version="codex-cli test"
        )
        self.assertEqual(result["five_hour_remaining_percent"], 81)
        self.assertEqual(result["weekly_remaining_percent"], 58)
        self.assertTrue(result["five_hour_reset_at"].endswith("Z"))
        self.assertTrue(result["weekly_reset_at"].endswith("Z"))
        self.assertEqual(result["source"], "codex app-server account/rateLimits/read")
        self.assertEqual(result["parser_version"], "1")
        self.assertEqual(result["session_context_remaining_percent"], None)
        self.assertEqual(result["model"], None)
        self.assertEqual(result["configuration"], None)

    def test_missing_weekly_window_and_reset_remain_unknown(self):
        payload = {"result": {"rateLimits": {
            "limitId": "codex",
            "primary": {"usedPercent": 25, "windowDurationMins": 300},
        }}}
        result = reader.normalize_rate_limits(payload, captured_at="2026-09-24T12:00:00Z")
        self.assertEqual(result["five_hour_remaining_percent"], 75)
        self.assertIsNone(result["five_hour_reset_at"])
        self.assertIsNone(result["weekly_remaining_percent"])
        self.assertIsNone(result["weekly_reset_at"])

    def test_output_discards_unrelated_fields_and_secrets(self):
        output = json.dumps(reader.normalize_rate_limits(self.response()))
        self.assertNotIn("MUST_NOT_ESCAPE_FIXTURE", output)
        self.assertNotIn("accessToken", output)
        self.assertNotIn("rateLimitResetCredits", output)
        self.assertNotIn("other", output)

    def test_unsupported_response_fails_closed(self):
        for payload in (None, "text", {}, {"result": None}):
            with self.subTest(payload=payload), self.assertRaises(reader.UsageReaderError):
                reader.normalize_rate_limits(payload)

    def test_invalid_percent_and_ambiguous_window_fail_closed(self):
        invalid = self.response()
        invalid["result"]["rateLimitsByLimitId"]["codex"]["primary"]["usedPercent"] = 101
        with self.assertRaises(reader.UsageReaderError):
            reader.normalize_rate_limits(invalid)
        ambiguous = self.response()
        ambiguous["result"]["rateLimitsByLimitId"]["codex"]["secondary"]["windowDurationMins"] = 300
        with self.assertRaises(reader.UsageReaderError):
            reader.normalize_rate_limits(ambiguous)

    def test_reader_uses_only_documented_app_server_requests_and_filters_output(self):
        lines = [
            json.dumps({"id": 0, "result": {"protocolVersion": "test"}}),
            json.dumps({"method": "account/updated", "params": {"authMode": "chatgpt"}}),
            json.dumps(self.response()),
        ]

        class FakeProcess:
            def __init__(self):
                import io
                class RetainedStringIO(io.StringIO):
                    def close(self):
                        self.retained_value = self.getvalue()
                        super().close()

                self.stdin = RetainedStringIO()
                self.stdin.retained_value = ""
                self.stdout = io.StringIO("\n".join(lines) + "\n")
                self.args = None
                self.waited = False

            def wait(self, timeout=None):
                self.waited = True
                return 0

            def poll(self):
                return 0 if self.waited else None

        process = FakeProcess()
        with patch.object(reader.shutil, "which", return_value="codex"), \
             patch.object(reader.subprocess, "Popen", return_value=process) as spawn, \
             patch.object(reader, "_codex_version", return_value="codex-cli fixture"):
            result = reader.read_codex_usage()
        self.assertEqual(result["weekly_remaining_percent"], 58)
        self.assertEqual(spawn.call_args.args[0], ["codex", "app-server"])
        sent = process.stdin.retained_value
        self.assertIn('"method":"initialize"', sent)
        self.assertIn('"method":"account/rateLimits/read"', sent)
        self.assertNotIn("token", sent.lower())
        self.assertNotIn("MUST_NOT_ESCAPE_FIXTURE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
