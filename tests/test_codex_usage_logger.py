import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_usage_logger as logger
import codex_usage_reader as reader


class CodexUsageLoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def usage(self, five=80, weekly=60, five_reset="2026-09-25T00:00:00Z",
              weekly_reset="2026-10-01T00:00:00Z", captured_at="2026-09-24T12:00:00Z"):
        return {
            "five_hour_remaining_percent": five,
            "five_hour_reset_at": five_reset,
            "weekly_remaining_percent": weekly,
            "weekly_reset_at": weekly_reset,
            "captured_at": captured_at,
            "source": reader.SOURCE,
            "parser_version": reader.PARSER_VERSION,
            "codex_version": None,
            "model": None,
            "configuration": None,
        }

    def capture(self, value):
        return lambda: value

    def path(self, task="TASK 31"):
        return self.root / ".project-intelligence" / "codex-usage" / f"{task}.json"

    def create(self, task="TASK 31", *, phase="START", five=80, weekly=60,
               captured_at="2026-09-24T12:00:00Z", five_reset="2026-09-25T00:00:00Z",
               weekly_reset="2026-10-01T00:00:00Z", snapshot_id=None):
        data = self.usage(five, weekly, five_reset, weekly_reset, captured_at)
        if phase == "START":
            return logger.start(task, root=self.root, usage_reader=self.capture(data),
                                captured_at=captured_at, snapshot_id=snapshot_id)
        if phase in {"PLAN", "EXECUTED"}:
            return logger.add_snapshot(task, phase, root=self.root,
                                       usage_reader=self.capture(data), captured_at=captured_at,
                                       snapshot_id=snapshot_id)
        return logger.close(task, phase, root=self.root, usage_reader=self.capture(data),
                            captured_at=captured_at, snapshot_id=snapshot_id)

    def test_normal_task_records_all_phases_and_valid_transitions(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=90, weekly=80)
        self.create(phase="PLAN", captured_at="2026-09-24T12:10:00Z", five=85, weekly=77)
        self.create(phase="EXECUTED", captured_at="2026-09-24T12:40:00Z", five=72, weekly=70)
        record = self.create(phase="DONE", captured_at="2026-09-24T13:00:00Z", five=65, weekly=68)
        self.assertEqual([s["phase"] for s in record["snapshots"]], ["START", "PLAN", "EXECUTED", "DONE"])
        self.assertEqual(record["status"], "done")
        self.assertEqual(record["derived"]["transitions"]["START_TO_PLAN"]["five_hour"]["consumed_percentage_points"], 5)
        self.assertEqual(record["derived"]["transitions"]["PLAN_TO_EXECUTED"]["weekly"]["consumed_percentage_points"], 7)
        self.assertEqual(record["derived"]["transitions"]["EXECUTED_TO_DONE"]["five_hour"]["consumed_percentage_points"], 7)
        self.assertEqual(record["derived"]["transitions"]["START_TO_DONE"]["weekly"]["consumed_percentage_points"], 12)
        self.assertEqual(record["derived"]["duration_minutes"], 60)
        self.assertEqual(record["derived"]["reset_during_task_by_window"], {"five_hour": False, "weekly": False})
        self.assertFalse(record["derived"]["reset_during_task"])

    def test_missing_plan_and_executed_transitions_remain_unknown(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=90)
        self.create(phase="EXECUTED", captured_at="2026-09-24T12:20:00Z", five=80)
        record = self.create(phase="DONE", captured_at="2026-09-24T12:30:00Z", five=75)
        transitions = record["derived"]["transitions"]
        self.assertIsNone(transitions["START_TO_PLAN"]["five_hour"]["consumed_percentage_points"])
        self.assertIsNone(transitions["PLAN_TO_EXECUTED"]["five_hour"]["consumed_percentage_points"])
        self.assertEqual(transitions["START_TO_DONE"]["five_hour"]["consumed_percentage_points"], 15)

    def test_unavailable_source_is_recorded_as_null_without_blocking(self):
        logger.start("unavailable", root=self.root,
                     usage_reader=lambda: (_ for _ in ()).throw(reader.UsageReaderError("private raw details")),
                     captured_at="2026-09-24T12:00:00-06:00")
        record = logger.inspect("unavailable", root=self.root)
        snap = record["snapshots"][0]
        self.assertEqual(snap["measurement_status"], "unavailable")
        self.assertEqual(snap["captured_at"], "2026-09-24T18:00:00Z")
        self.assertIsNone(snap["five_hour_remaining_percent"])
        self.assertEqual(snap["error_code"], "usage_unavailable")
        serialized = self.path("unavailable").read_text(encoding="utf-8")
        self.assertNotIn("private raw details", serialized)

    def test_five_hour_reset_is_detected_without_negative_consumption(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=8, weekly=50,
                    five_reset="2026-09-24T13:00:00Z")
        self.create(phase="PLAN", captured_at="2026-09-24T12:10:00Z", five=6, weekly=48,
                    five_reset="2026-09-24T13:00:00Z")
        self.create(phase="EXECUTED", captured_at="2026-09-24T12:20:00Z", five=4, weekly=45,
                    five_reset="2026-09-24T13:00:00Z")
        record = self.create(phase="DONE", captured_at="2026-09-24T14:00:00Z", five=97, weekly=40,
                             five_reset="2026-09-24T18:00:00Z")
        derived = record["derived"]
        self.assertTrue(derived["reset_during_task_by_window"]["five_hour"])
        self.assertIsNone(derived["transitions"]["EXECUTED_TO_DONE"]["five_hour"]["consumed_percentage_points"])
        self.assertEqual(derived["transitions"]["START_TO_DONE"]["five_hour"]["start_remaining_percent"], 8)
        self.assertEqual(derived["transitions"]["START_TO_DONE"]["five_hour"]["end_remaining_percent"], 97)
        self.assertIsNone(derived["transitions"]["START_TO_DONE"]["five_hour"]["consumed_percentage_points"])
        self.assertEqual(derived["transitions"]["EXECUTED_TO_DONE"]["five_hour"]["reset_at_end"], "2026-09-24T18:00:00Z")
        self.assertEqual(derived["transitions"]["EXECUTED_TO_DONE"]["weekly"]["consumed_percentage_points"], 5)

    def test_weekly_reset_is_independent_from_five_hour(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=70, weekly=8,
                    weekly_reset="2026-09-25T00:00:00Z")
        record = self.create(phase="DONE", captured_at="2026-09-24T13:00:00Z", five=60, weekly=97,
                             weekly_reset="2026-10-01T00:00:00Z")
        derived = record["derived"]
        self.assertFalse(derived["reset_during_task_by_window"]["five_hour"])
        self.assertTrue(derived["reset_during_task_by_window"]["weekly"])
        self.assertEqual(derived["transitions"]["START_TO_DONE"]["five_hour"]["consumed_percentage_points"], 10)
        self.assertIsNone(derived["transitions"]["START_TO_DONE"]["weekly"]["consumed_percentage_points"])

    def test_both_resets_are_recorded_separately(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=10, weekly=9)
        record = self.create(phase="DONE", captured_at="2026-09-24T13:00:00Z", five=98, weekly=99,
                             five_reset="2026-09-24T18:00:00Z", weekly_reset="2026-10-01T00:00:00Z")
        self.assertEqual(record["derived"]["reset_during_task_by_window"], {"five_hour": True, "weekly": True})
        self.assertTrue(record["derived"]["reset_during_task"])

    def test_endpoint_reset_change_is_detected_across_unavailable_phase(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=80, weekly=70,
                    five_reset="2026-09-24T13:00:00Z", weekly_reset="2026-09-25T00:00:00Z")
        logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                            usage_reader=lambda: (_ for _ in ()).throw(reader.UsageReaderError("unavailable")),
                            captured_at="2026-09-24T12:10:00Z")
        record = self.create(phase="DONE", captured_at="2026-09-24T14:00:00Z", five=60, weekly=50,
                             five_reset="2026-09-24T18:00:00Z", weekly_reset="2026-09-25T00:00:00Z")
        transition = record["derived"]["transitions"]["START_TO_DONE"]
        self.assertTrue(transition["five_hour"]["reset_detected"])
        self.assertIsNone(transition["five_hour"]["consumed_percentage_points"])
        self.assertFalse(transition["weekly"]["reset_detected"])
        self.assertEqual(transition["weekly"]["consumed_percentage_points"], 20)
        self.assertEqual(record["derived"]["reset_during_task_by_window"], {"five_hour": True, "weekly": False})
        self.assertTrue(record["derived"]["reset_during_task"])

    def test_weekly_endpoint_reset_is_detected_across_unavailable_phase(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=80, weekly=70,
                    five_reset="2026-09-24T13:00:00Z", weekly_reset="2026-09-25T00:00:00Z")
        logger.add_snapshot("TASK 31", "EXECUTED", root=self.root,
                            usage_reader=lambda: (_ for _ in ()).throw(reader.UsageReaderError("unavailable")),
                            captured_at="2026-09-24T12:10:00Z")
        record = self.create(phase="DONE", captured_at="2026-09-24T14:00:00Z", five=60, weekly=50,
                             five_reset="2026-09-24T13:00:00Z", weekly_reset="2026-10-01T00:00:00Z")
        transition = record["derived"]["transitions"]["START_TO_DONE"]
        self.assertFalse(transition["five_hour"]["reset_detected"])
        self.assertEqual(transition["five_hour"]["consumed_percentage_points"], 20)
        self.assertTrue(transition["weekly"]["reset_detected"])
        self.assertIsNone(transition["weekly"]["consumed_percentage_points"])
        self.assertEqual(record["derived"]["reset_during_task_by_window"], {"five_hour": False, "weekly": True})
        self.assertTrue(record["derived"]["reset_during_task"])

    def test_duplicate_snapshot_is_idempotent_but_distinct_capture_is_preserved(self):
        record = self.create(captured_at="2026-09-24T12:00:00Z", snapshot_id="start-1")
        before = self.path().read_bytes()
        same = logger.start("TASK 31", root=self.root, usage_reader=self.capture(self.usage(captured_at="2026-09-24T12:00:00Z")),
                            captured_at="2026-09-24T12:00:00Z", snapshot_id="start-1")
        self.assertEqual(len(same["snapshots"]), 1)
        self.assertEqual(self.path().read_bytes(), before)
        # A new timestamp is an auditable recapture, not a duplicate.
        recaptured = logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                                         usage_reader=self.capture(self.usage(captured_at="2026-09-24T12:01:00Z")),
                                         captured_at="2026-09-24T12:01:00Z", snapshot_id="plan-1")
        self.assertEqual(len(recaptured["snapshots"]), 2)
        with self.assertRaisesRegex(logger.UsageLogError, "different data"):
            logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                                usage_reader=self.capture(self.usage(five=79, captured_at="2026-09-24T12:01:00Z")),
                                captured_at="2026-09-24T12:01:00Z", snapshot_id="plan-1")

    def test_resume_after_interruption_and_inspect_are_read_only(self):
        self.create(captured_at="2026-09-24T12:00:00Z")
        resumed = logger.start("TASK 31", root=self.root,
                              usage_reader=lambda: self.fail("start should reuse existing START"))
        self.assertEqual(len(resumed["snapshots"]), 1)
        self.create(phase="PLAN", captured_at="2026-09-24T12:02:00Z")
        before = self.path().read_bytes()
        with patch.object(logger.codex_usage_reader, "read_codex_usage", side_effect=AssertionError("reader called")):
            inspected = logger.inspect("TASK 31", root=self.root)
        self.assertEqual(self.path().read_bytes(), before)
        self.assertEqual(inspected["task_id"], "TASK 31")

    def test_atomic_replace_failure_preserves_previous_record(self):
        self.create(captured_at="2026-09-24T12:00:00Z")
        path = self.path()
        before = path.read_bytes()
        with patch.object(logger.os, "replace", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                                    usage_reader=self.capture(self.usage(captured_at="2026-09-24T12:01:00Z")),
                                    captured_at="2026-09-24T12:01:00Z")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(list(path.parent.glob("*.tmp"))), 0)

    def test_windows_safe_paths_and_traversal_are_rejected(self):
        self.create(task="task.with-hyphen_31", captured_at="2026-09-24T12:00:00Z")
        self.assertTrue((self.root / ".project-intelligence" / "codex-usage" / "task.with-hyphen_31.json").exists())
        for task in ("../escape", "..", "CON", "NUL.txt", "bad/child", "trailing."):
            with self.subTest(task=task), self.assertRaises(logger.UsageLogError):
                logger.inspect(task, root=self.root)

    def test_zero_and_one_hundred_percent_are_valid(self):
        record = self.create(captured_at="2026-09-24T12:00:00Z", five=0, weekly=100)
        self.assertEqual(record["snapshots"][0]["five_hour_remaining_percent"], 0)
        self.assertEqual(record["snapshots"][0]["weekly_remaining_percent"], 100)

    def test_out_of_range_measurement_is_rejected_without_mutation(self):
        self.create(captured_at="2026-09-24T12:00:00Z")
        before = self.path().read_bytes()
        with self.assertRaisesRegex(logger.UsageLogError, "between 0 and 100"):
            logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                                usage_reader=self.capture(self.usage(five=101, captured_at="2026-09-24T12:01:00Z")),
                                captured_at="2026-09-24T12:01:00Z")
        self.assertEqual(self.path().read_bytes(), before)

    def test_naive_or_invalid_timestamp_is_rejected(self):
        self.create(captured_at="2026-09-24T12:00:00Z")
        before = self.path().read_bytes()
        for stamp in ("2026-09-24T12:01:00", "not-a-date"):
            with self.subTest(stamp=stamp), self.assertRaisesRegex(logger.UsageLogError, "timezone"):
                logger.add_snapshot("TASK 31", "PLAN", root=self.root,
                                    usage_reader=self.capture(self.usage(captured_at=stamp)), captured_at=stamp)
        self.assertEqual(self.path().read_bytes(), before)

    def test_source_failure_is_sanitized_and_not_blocking(self):
        def failure():
            raise reader.UsageReaderError("secret=token-123 prompt text")
        record = logger.start("source-failure", root=self.root, usage_reader=failure)
        serialized = self.path("source-failure").read_text(encoding="utf-8")
        self.assertEqual(record["status"], "active")
        self.assertNotIn("token-123", serialized)
        self.assertNotIn("prompt text", serialized)
        self.assertEqual(record["snapshots"][0]["error_code"], "usage_unavailable")

    def test_blocked_and_done_close_idempotently(self):
        self.create(task="blocked", captured_at="2026-09-24T12:00:00Z")
        blocked = self.create(task="blocked", phase="BLOCKED", captured_at="2026-09-24T12:05:00Z")
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["finished_at"], "2026-09-24T12:05:00Z")
        same = logger.close("blocked", "BLOCKED", root=self.root,
                            usage_reader=lambda: self.fail("closed task must be idempotent"))
        self.assertEqual(same["snapshots"], blocked["snapshots"])
        self.create(task="done", captured_at="2026-09-24T12:00:00Z")
        done = self.create(task="done", phase="DONE", captured_at="2026-09-24T12:01:00Z")
        self.assertEqual(done["status"], "done")

    def test_phase_recaptures_keep_history_but_latest_values_drive_derivation(self):
        self.create(captured_at="2026-09-24T12:00:00Z", five=90)
        self.create(phase="PLAN", captured_at="2026-09-24T12:05:00Z", five=80)
        record = self.create(phase="PLAN", captured_at="2026-09-24T12:06:00Z", five=75)
        self.assertEqual(len(record["snapshots"]), 3)
        self.assertEqual(record["derived"]["transitions"]["START_TO_PLAN"]["five_hour"]["end_remaining_percent"], 75)

    def test_cli_inspect_does_not_modify_record(self):
        self.create(captured_at="2026-09-24T12:00:00Z")
        before = self.path().read_bytes()
        with patch.object(logger.codex_usage_reader, "read_codex_usage", side_effect=AssertionError("reader called")):
            with patch("sys.stdout", new_callable=__import__("io").StringIO) as output:
                result = logger.main(["--root", str(self.root), "inspect", "--task-id", "TASK 31"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["task_id"], "TASK 31")
        self.assertEqual(self.path().read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
