import unittest

from scripts.claim_timeline import build_claim_timeline, project_claim_research_history


class ClaimTimelineTests(unittest.TestCase):
    def setUp(self):
        self.claim = {"id": "claim-1", "investigation_id": "case-1", "claim": "Claim text"}

    def test_investigations_verdicts_and_resolutions_are_separate(self):
        rows = build_claim_timeline(self.claim,
            operations=[{"operation_id": "op-1", "kind": "claim_research", "claim_id": "claim-1",
                         "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-22T10:00:00Z",
                         "status": "completed_with_limits", "result": {"scientific_resolution": {
                             "resolution_id": "res-1", "resolution": "indeterminate", "created_at": "2026-09-22T10:00:00Z"}}},
                        {"operation_id": "op-2", "kind": "claim_research", "claim_id": "claim-1",
                         "requested_at": "2026-09-23T09:00:00Z", "finished_at": "2026-09-23T10:00:00Z",
                         "status": "failed", "error": {"type": "ValueError", "message": "scoped failure"}},
                        {"operation_id": "unscoped", "kind": "claim_research", "status": "failed",
                         "finished_at": "2026-09-23T10:01:00Z", "error": "must not be attributed"}],
            )
        investigations = [row for row in rows if row["category"] == "automatic_investigation"]
        resolutions = [row for row in rows if row["category"] == "scientific_resolution"]
        self.assertEqual({row["operation_id"] for row in investigations}, {"op-1", "op-2"})
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["operation_id"], "op-1")
        self.assertEqual(resolutions[0]["summary"], "indeterminate")
        self.assertEqual([row["summary"] for row in investigations if row["event"] == "failed"], ["scoped failure"])

    def test_only_actual_verdict_transition_is_projected(self):
        rows = build_claim_timeline({**self.claim, "status": "UNSUPPORTED", "provenance": [
            {"id": "same", "previous_status": "UNSUPPORTED", "status": "UNSUPPORTED", "reviewed_at": "2026-09-20T00:00:00Z"},
            {"id": "changed", "previous_status": "UNVERIFIED", "status": "UNSUPPORTED", "reviewed_at": "2026-09-21T00:00:00Z"},
        ]})
        verdicts = [row for row in rows if row["category"] == "verdict_change"]
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["source_record_id"], "changed")

    def test_technical_check_is_included_only_with_explicit_claim_association(self):
        rows = build_claim_timeline(self.claim, operations=[
            {"operation_id": "not-this-claim", "kind": "technical_check", "claim_id": "claim-2", "status": "done"},
            {"operation_id": "check-1", "kind": "technical_check", "input_data": {"claim_ids": ["claim-1"]},
             "requested_at": "2026-09-23T11:00:00Z", "finished_at": "2026-09-23T11:01:00Z", "status": "done",
             "result": {"source_receipts": [{"claim_id": "claim-1", "source_check_id": "receipt-1",
                 "checked_at": "2026-09-23T11:00:30Z", "availability": "AVAILABLE", "excerpt_match": True}]}}],
        )
        events = [row for row in rows if row["category"] == "technical_source_check"]
        self.assertEqual({row["operation_id"] for row in events}, {"check-1"})
        self.assertTrue(any(row["source_record_id"] == "receipt-1" for row in events))

    def test_undated_legacy_records_are_not_assigned_dates(self):
        rows = build_claim_timeline(self.claim, operations=[
            {"operation_id": "legacy-op", "kind": "claim_research", "claim_id": "claim-1", "status": "failed"},
        ])
        operation_events = [row for row in rows if row["source_record_id"] == "legacy-op"]
        self.assertTrue(operation_events)
        self.assertTrue(all(row["occurred_at"] is None for row in operation_events))
        self.assertTrue(all(row["legacy"] for row in operation_events))

    def test_retry_keeps_prior_failure_visible_without_duplicating_current_terminal_event(self):
        operation = {"operation_id": "retry-op", "kind": "claim_research", "claim_id": "claim-1",
            "requested_at": "2026-09-20T08:00:00Z", "started_at": "2026-09-20T08:01:00Z",
            "status": "running", "stage": "retriever", "finished_at": None,
            "attempt_history": [
                {"number": 1, "started_at": "2026-09-20T08:01:00Z", "finished_at": "2026-09-20T08:03:00Z",
                 "status": "failed", "error": {"type": "ValueError", "message": "bad matrix"}},
                {"number": 2, "started_at": "2026-09-20T08:05:00Z", "status": "running"},
            ]}
        rows = build_claim_timeline(self.claim, operations=[operation])
        failure = next(row for row in rows if row["event"] == "attempt_failed")
        retry = next(row for row in rows if row["event"] == "retry")
        self.assertEqual(failure["occurred_at"], "2026-09-20T08:03:00Z")
        self.assertEqual(failure["summary"], "bad matrix")
        self.assertEqual(retry["occurred_at"], "2026-09-20T08:05:00Z")

        completed = {**operation, "status": "done", "finished_at": "2026-09-20T08:07:00Z",
                     "attempt_history": [operation["attempt_history"][0],
                         {"number": 2, "started_at": "2026-09-20T08:05:00Z", "finished_at": "2026-09-20T08:07:00Z", "status": "done"}]}
        finished_rows = build_claim_timeline(self.claim, operations=[completed])
        current_terminal = [row for row in finished_rows if row["event"] == "done"]
        self.assertEqual(len(current_terminal), 1)
        self.assertTrue(any(row["event"] == "attempt_failed" for row in finished_rows))

    def test_missing_and_naive_timestamps_sort_after_utc_events_deterministically(self):
        claim = {**self.claim, "provenance": [
            {"id": "undated", "previous_status": "UNVERIFIED", "status": "UNSUPPORTED"},
            {"id": "naive", "previous_status": "UNSUPPORTED", "status": "PARTIAL", "reviewed_at": "2026-09-22T10:00:00"},
            {"id": "aware", "previous_status": "PARTIAL", "status": "VERIFIED", "reviewed_at": "2026-09-22T10:00:00+00:00"},
        ]}
        first = build_claim_timeline(claim)
        second = build_claim_timeline(claim)
        self.assertEqual(first, second)
        verdicts = [row for row in first if row["category"] == "verdict_change"]
        self.assertEqual(verdicts[0]["source_record_id"], "aware")
        self.assertIsNone(verdicts[-1]["occurred_at"])

    def test_human_review_and_reformulation_are_explicit_and_do_not_inherit_verdict(self):
        rows = build_claim_timeline(self.claim,
            human_reviews=[{"id": "review-1", "claim_id": "claim-1", "actor": "Ana", "decision": "revise",
                            "reviewed_at": "2026-09-23T16:00:00Z"}],
            reformulations=[{"id": "proposal-1", "parent_claim_id": "claim-1", "revised_claim": "Narrower wording",
                             "status": "approved", "approved_at": "2026-09-23T17:00:00Z", "revised_claim_id": "child-1"}],
        )
        review = next(row for row in rows if row["category"] == "human_review")
        reform = next(row for row in rows if row["category"] == "claim_reformulation")
        self.assertFalse(review["details"]["automatic_verdict_changed"])
        self.assertFalse(reform["details"]["evidence_inherited"])
        self.assertFalse(reform["details"]["verdict_inherited"])
        self.assertEqual(reform["details"]["parent_claim_id"], "claim-1")
        self.assertEqual(reform["details"]["child_claim_id"], "child-1")

    def test_reformulation_child_timeline_starts_only_when_approved(self):
        history = [
            {"id": "proposal-1", "parent_claim_id": "claim-1", "revised_claim_id": "child-1",
             "revised_claim": "Narrower wording", "status": "proposed", "created_at": "2026-09-23T16:00:00Z",
             "reason": "Narrow the horizon", "retained_dimensions": ["population"]},
            {"id": "proposal-1", "parent_claim_id": "claim-1", "revised_claim_id": "child-1",
             "revised_claim": "Narrower wording", "status": "approved", "created_at": "2026-09-23T16:00:00Z",
             "approved_at": "2026-09-23T17:00:00Z", "reason": "Narrow the horizon",
             "retained_dimensions": ["population"]},
        ]
        parent = [row for row in build_claim_timeline(self.claim, reformulations=history)
                  if row["category"] == "claim_reformulation"]
        child = [row for row in build_claim_timeline({**self.claim, "id": "child-1"},
                                                       reformulations=history)
                 if row["category"] == "claim_reformulation"]

        self.assertEqual([row["event"] for row in parent], ["proposed", "approved"])
        self.assertEqual([row["event"] for row in child], ["approved"])
        self.assertEqual(child[0]["occurred_at"], "2026-09-23T17:00:00Z")
        self.assertEqual(child[0]["details"]["parent_claim_id"], "claim-1")
        self.assertEqual(child[0]["source_record_id"], "proposal-1:child:approved")
        self.assertFalse(child[0]["details"]["evidence_inherited"])
        self.assertFalse(child[0]["details"]["verdict_inherited"])

    def test_scope_admission_and_legacy_source_check_need_persisted_links(self):
        rows = build_claim_timeline(self.claim,
            scope_history=[{"id": "scope-1", "status": "approved", "approved_at": "2026-09-20T00:00:00Z",
                            "selected_ids": ["claim-1"]}],
            legacy_source_checks=[{"source_check_id": "check-receipt", "checked_at": "2026-09-21T00:00:00Z",
                                   "availability": "NOT_FOUND"}],
        )
        self.assertTrue(any(row["event"] == "admitted_to_scope" for row in rows))
        self.assertTrue(any(row["source_record_id"] == "check-receipt" for row in rows))
        unlinked = build_claim_timeline(self.claim,
            legacy_source_checks=[{"id": "unlinked", "checked_at": "2026-09-21T00:00:00Z"}])
        self.assertFalse(any(row["category"] == "technical_source_check" for row in unlinked))

    def test_document_association_is_shown_without_inventing_an_association_date(self):
        rows = build_claim_timeline({**self.claim, "evidence": [
            {"type": "document", "document_id": "doc-1", "evidence_id": "passage-1", "filename": "study.pdf"},
        ]})
        event = next(row for row in rows if row["category"] == "document")
        self.assertIsNone(event["occurred_at"])
        self.assertTrue(event["legacy"])
        self.assertEqual(event["summary"], "study.pdf")
        self.assertEqual(event["details"]["document_id"], "doc-1")

    def test_equal_timestamps_have_stable_order_and_ids(self):
        operations = [
            {"operation_id": "op-b", "kind": "claim_research", "claim_id": "claim-1", "requested_at": "2026-09-22T10:00:00Z", "status": "queued"},
            {"operation_id": "op-a", "kind": "claim_research", "claim_id": "claim-1", "requested_at": "2026-09-22T10:00:00Z", "status": "queued"},
        ]
        first = build_claim_timeline(self.claim, operations=operations)
        second = build_claim_timeline(self.claim, operations=list(reversed(operations)))
        self.assertEqual(first, second)
        self.assertEqual(len({row["event_id"] for row in first}), len(first))

    def test_claim_research_projection_handles_empty_and_single_completed_operation(self):
        empty = project_claim_research_history([], "claim-1")
        self.assertEqual(empty["operations"], [])
        self.assertIsNone(empty["latest_operation"])
        self.assertIsNone(empty["current_completed"])
        self.assertFalse(empty["has_active"])

        operation = {"operation_id": "op-1", "kind": "claim_research", "claim_id": "claim-1",
                     "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-22T10:00:00Z",
                     "status": "done", "result": {"outcome": "supported"}, "error": None,
                     "evidence_mode": "documents_only", "document_ids": ["doc-1"],
                     "input_data": {"document_ids": ["doc-1"]}}
        projected = project_claim_research_history([operation], "claim-1")
        self.assertEqual(projected["operations"], [operation])
        self.assertEqual(projected["latest_operation"], operation)
        self.assertEqual(projected["current_completed"], operation)
        self.assertEqual(projected["operations"][0]["evidence_mode"], "documents_only")
        self.assertEqual(projected["operations"][0]["document_ids"], ["doc-1"])

    def test_claim_research_projection_keeps_latest_failure_and_prior_completed_result(self):
        completed = {"operation_id": "op-done", "kind": "claim_research", "claim_id": "claim-1",
                     "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-22T10:00:00Z",
                     "status": "completed_with_limits", "result": {"resolution": "indeterminate"}}
        failed = {"operation_id": "op-failed", "kind": "claim_research", "claim_id": "claim-1",
                  "requested_at": "2026-09-23T09:00:00Z", "finished_at": "2026-09-23T09:01:00Z",
                  "status": "failed", "error": {"type": "ValueError", "message": "source identity missing"}}
        projected = project_claim_research_history([failed, completed], "claim-1")
        self.assertEqual([row["operation_id"] for row in projected["operations"]], ["op-failed", "op-done"])
        self.assertEqual(projected["latest_operation"]["operation_id"], "op-failed")
        self.assertEqual(projected["latest_operation"]["error"]["message"], "source identity missing")
        self.assertEqual(projected["current_completed"]["operation_id"], "op-done")
        self.assertEqual(projected["current_completed"]["result"]["resolution"], "indeterminate")

    def test_claim_research_projection_uses_finish_time_for_current_completed(self):
        earlier_requested_later_finished = {"id": "a", "kind": "claim_research", "claim_id": "claim-1",
            "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-23T10:00:00Z",
            "status": "done", "result": {"v": 1}}
        later_requested_earlier_finished = {"id": "b", "kind": "claim_research", "claim_id": "claim-1",
            "requested_at": "2026-09-23T09:00:00Z", "finished_at": "2026-09-23T09:30:00Z",
            "status": "resolved", "result": {"v": 2}}
        projected = project_claim_research_history([later_requested_earlier_finished, earlier_requested_later_finished], "claim-1")
        self.assertEqual(projected["latest_operation"]["id"], "b")
        self.assertEqual(projected["current_completed"]["id"], "a")

    def test_claim_research_projection_is_stable_across_offsets_ties_and_legacy_missing_dates(self):
        rows = [
            {"operation_id": "offset", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T12:00:00+02:00", "status": "queued"},
            {"operation_id": "z-tie", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T11:00:00Z", "status": "queued"},
            {"operation_id": "a-tie", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T11:00:00Z", "status": "queued"},
            {"operation_id": "legacy-b", "kind": "claim_research", "claim_id": "claim-1",
             "updated_at": "2026-09-24T12:00:00Z", "status": "failed"},
            {"operation_id": "legacy-a", "kind": "claim_research", "claim_id": "claim-1", "status": "failed"},
        ]
        first = project_claim_research_history(rows, "claim-1")
        second = project_claim_research_history(list(reversed(rows)), "claim-1")
        self.assertEqual(first, second)
        self.assertEqual([row["operation_id"] for row in first["operations"]],
                         ["a-tie", "z-tie", "offset", "legacy-a", "legacy-b"])
        self.assertNotIn("requested_at", first["operations"][-1])
        self.assertTrue(first["has_active"])

    def test_claim_research_projection_filters_claims_and_reports_active_status(self):
        rows = [
            {"id": "active", "kind": "claim_research", "claim_id": "claim-1", "status": "running"},
            {"id": "other", "kind": "claim_research", "claim_id": "claim-2", "status": "failed",
             "error": {"message": "must stay scoped"}},
            {"id": "technical", "kind": "technical_check", "claim_id": "claim-1", "status": "done"},
        ]
        projected = project_claim_research_history(rows, "claim-1")
        self.assertEqual([row["id"] for row in projected["operations"]], ["active"])
        self.assertEqual(projected["latest_operation"]["status"], "running")
        self.assertTrue(projected["has_active"])


if __name__ == "__main__":
    unittest.main()
