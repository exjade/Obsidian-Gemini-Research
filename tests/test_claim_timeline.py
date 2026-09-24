import unittest

from scripts.claim_timeline import (build_claim_timeline, project_claim_research_history,
                                    case_activity_event, project_case_activity,
                                    project_claim_timeline)


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

    def test_multiple_scientific_resolutions_keep_dates_provenance_and_evidence_separate_from_verdict(self):
        claim = {**self.claim, "status": "UNSUPPORTED", "provenance": [], "scientific_resolution_history": [
            {"resolution_id": "res-1", "resolution": "supported", "created_at": "2026-09-22T10:00:00Z",
             "dimensions": {"population": {"state": "supported", "evidence": [
                 {"source_id": "source-a", "evidence_id": "passage-a"}]}},
             "limitations": ["Adult sample"]},
            {"resolution_id": "res-2", "resolution": "indeterminate", "created_at": "2026-09-23T10:00:00Z",
             "dimensions": {"horizon": {"state": "unresolved", "passage_ids": ["passage-b"]}},
             "limitations": ["No delayed measure"]},
        ]}
        operations = [
            {"operation_id": "op-1", "kind": "claim_research", "claim_id": "claim-1",
             "claim_version": 2, "input_fingerprint": "fp-1", "input_data": {"claim_version": 2},
             "result": {"scientific_resolution": {"resolution_id": "res-1"}}},
            {"operation_id": "op-2", "kind": "claim_research", "claim_id": "claim-1",
             "claim_version": 3, "input_fingerprint": "fp-2", "input_data": {"claim_version": 3},
             "result": {"scientific_resolution": {"resolution_id": "res-2"}}},
        ]

        rows = build_claim_timeline(claim, operations=operations)
        resolutions = [row for row in rows if row["category"] == "scientific_resolution"]
        investigations = [row for row in rows if row["category"] == "automatic_investigation"]
        verdicts = [row for row in rows if row["category"] == "verdict_change"]
        by_id = {row["details"]["resolution_id"]: row for row in resolutions}

        self.assertEqual(set(by_id), {"res-1", "res-2"})
        self.assertEqual(by_id["res-1"]["occurred_at"], "2026-09-22T10:00:00Z")
        self.assertEqual(by_id["res-2"]["occurred_at"], "2026-09-23T10:00:00Z")
        self.assertEqual(by_id["res-1"]["operation_id"], "op-1")
        self.assertEqual(by_id["res-2"]["operation_id"], "op-2")
        self.assertEqual(by_id["res-1"]["details"]["claim_version"], 2)
        self.assertEqual(by_id["res-1"]["details"]["input_fingerprint"], "fp-1")
        self.assertEqual(by_id["res-2"]["details"]["claim_version"], 3)
        self.assertEqual(by_id["res-2"]["details"]["input_fingerprint"], "fp-2")
        self.assertEqual(by_id["res-1"]["details"]["evidence_links"],
                         [{"source_id": "source-a", "evidence_id": "passage-a"}])
        self.assertEqual(by_id["res-2"]["details"]["evidence_ids"], ["passage-b"])
        self.assertEqual(by_id["res-1"]["details"]["limitations"], ["Adult sample"])
        self.assertEqual(by_id["res-2"]["details"]["limitations"], ["No delayed measure"])
        self.assertEqual(len(investigations), 2)
        self.assertEqual(verdicts, [])

    def test_resolution_without_persisted_operation_link_does_not_invent_provenance(self):
        rows = build_claim_timeline({**self.claim, "scientific_resolution_history": [
            {"resolution_id": "legacy-res", "resolution": "unresolved", "created_at": "2026-09-20T00:00:00Z"}
        ]}, operations=[
            {"operation_id": "unrelated", "kind": "claim_research", "claim_id": "claim-1",
             "result": {"scientific_resolution": {"resolution_id": "different-resolution"}}}
        ])
        resolution = next(row for row in rows if row["category"] == "scientific_resolution")
        self.assertIsNone(resolution["operation_id"])
        self.assertEqual(resolution["details"]["resolution"], "unresolved")

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
                            "reviewed_at": "2026-09-23T16:00:00Z", "claim_version": 3,
                            "claim_fingerprint": "review-fp", "automatic_status_at_review": "UNSUPPORTED",
                            "notes": "Compared the passage", "limits": "One study",
                            "examined_evidence": [{"index": 0, "evidence": {"type": "document",
                                "document_id": "doc-1", "evidence_id": "passage-1",
                                "path": "study.pdf", "physical_page": 4}}]}],
            reformulations=[
                {"id": "proposal-1", "parent_claim_id": "claim-1", "revised_claim": "Narrower wording",
                 "status": "proposed", "created_at": "2026-09-23T16:30:00Z", "actor": "Ana",
                 "reason": "Narrow the scope", "retained_dimensions": ["population"],
                 "revised_claim_id": "child-1"},
                {"id": "proposal-1", "parent_claim_id": "claim-1", "revised_claim": "Narrower wording",
                 "status": "approved", "created_at": "2026-09-23T16:30:00Z",
                 "approved_at": "2026-09-23T17:00:00Z", "approved_by": "Ana",
                 "reason": "Narrow the scope", "retained_dimensions": ["population"],
                 "revised_claim_id": "child-1"}],
        )
        review = next(row for row in rows if row["category"] == "human_review")
        reforms = [row for row in rows if row["category"] == "claim_reformulation"]
        reform = next(row for row in reforms if row["event"] == "approved")
        self.assertFalse(review["details"]["automatic_verdict_changed"])
        self.assertEqual(review["details"]["automatic_status_at_review"], "UNSUPPORTED")
        self.assertEqual(review["details"]["claim_version"], 3)
        self.assertEqual(review["details"]["claim_fingerprint"], "review-fp")
        self.assertEqual(review["details"]["examined_evidence_refs"], [{"index": 0, "type": "document",
            "document_id": "doc-1", "evidence_id": "passage-1", "path": "study.pdf", "physical_page": 4}])
        self.assertFalse(any(row["category"] == "verdict_change" for row in rows))
        self.assertEqual([row["event"] for row in reforms], ["proposed", "approved"])
        proposal = reforms[0]
        self.assertEqual(proposal["occurred_at"], "2026-09-23T16:30:00Z")
        self.assertEqual(proposal["details"]["reason"], "Narrow the scope")
        self.assertEqual(proposal["details"]["retained_dimensions"], ["population"])
        self.assertFalse(reform["details"]["evidence_inherited"])
        self.assertFalse(reform["details"]["verdict_inherited"])
        self.assertEqual(reform["details"]["parent_claim_id"], "claim-1")
        self.assertEqual(reform["details"]["child_claim_id"], "child-1")
        self.assertEqual(reform["details"]["actor"], "Ana")

    def test_rejected_reformulation_is_a_distinct_parent_event_without_child_creation(self):
        record = {"id": "proposal-rejected", "parent_claim_id": "claim-1", "revised_claim_id": "child-2",
                  "revised_claim": "Narrower wording", "status": "rejected", "created_at": "2026-09-23T16:00:00Z",
                  "rejected_at": "2026-09-23T18:00:00Z", "rejected_by": "Ana", "reason": "Evidence too narrow",
                  "retained_dimensions": ["population"], "evidence_inherited": False, "verdict_inherited": False}
        before = {"claim": dict(self.claim), "reformulations": [dict(record)]}
        parent = project_claim_timeline(self.claim, reformulations=[record])
        child = project_claim_timeline({**self.claim, "id": "child-2"}, reformulations=[record])
        rejected = next(row for row in parent if row["event_type"] == "reformulation.rejected")
        self.assertEqual(rejected["timestamp"], "2026-09-23T18:00:00Z")
        self.assertEqual(rejected["details"]["actor"], "Ana")
        self.assertEqual(rejected["details"]["parent_claim_id"], "claim-1")
        self.assertEqual(rejected["details"]["child_claim_id"], "child-2")
        self.assertFalse(any(row["event_type"].startswith("reformulation.")
                             or row["event_type"] == "claim.child_created" for row in child))
        self.assertEqual(self.claim, before["claim"])
        self.assertEqual(record, before["reformulations"][0])

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
        child_canonical = [row for row in project_claim_timeline({**self.claim, "id": "child-1"},
            reformulations=history) if row["event_type"] == "claim.child_created"]
        self.assertEqual(len(child_canonical), 1)
        self.assertEqual(child_canonical[0]["source_record_id"], "proposal-1:child:approved")

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

    def test_canonical_timeline_reconstructs_interleaved_persisted_events(self):
        claim = {**self.claim, "created_at": "2026-09-17T00:00:00Z", "provenance": [
            {"id": "verdict-1", "previous_status": "PENDING", "status": "UNSUPPORTED",
             "reviewed_at": "2026-09-18T12:00:00Z"},
        ]}
        operations = [
            {"operation_id": "research-a", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-22T08:00:00Z", "started_at": "2026-09-22T08:05:00Z",
             "finished_at": "2026-09-22T09:00:00Z", "status": "done",
             "result": {"outcome": "supported"}},
            {"operation_id": "research-b", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T09:30:00Z", "started_at": "2026-09-23T09:35:00Z",
             "finished_at": "2026-09-23T10:00:00Z", "status": "failed",
             "stage": "skeptic", "error": {"type": "ValueError", "message": "auditor unavailable"}},
            {"operation_id": "technical-1", "kind": "technical_check",
             "input_data": {"claim_ids": ["claim-1"]}, "requested_at": "2026-09-23T10:50:00Z",
             "finished_at": "2026-09-23T11:00:00Z", "status": "done",
             "result": {"source_receipts": [{"claim_id": "claim-1", "source_check_id": "receipt-1",
                 "checked_at": "2026-09-23T11:00:00Z", "availability": "AVAILABLE", "excerpt_match": True}]}},
            {"operation_id": "research-c", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T13:00:00Z", "started_at": "2026-09-23T13:05:00Z",
             "finished_at": "2026-09-23T14:00:00Z", "status": "completed_with_limits",
             "result": {"outcome": "indeterminate"}},
        ]
        reviews = [{"id": "review-1", "claim_id": "claim-1", "actor": "Ana",
                    "decision": "needs_follow_up", "reviewed_at": "2026-09-23T16:00:00Z"}]

        rows = project_claim_timeline(claim, operations=operations, human_reviews=reviews)
        reverse_rows = project_claim_timeline(claim, operations=list(reversed(operations)),
                                              human_reviews=list(reversed(reviews)))
        self.assertEqual(rows, reverse_rows)
        self.assertTrue(rows)
        for row in rows:
            for field in ("timestamp", "event_type", "source_record_type", "source_record_id",
                          "operation_id", "text", "sequence"):
                self.assertIn(field, row)
        self.assertEqual(next(row for row in rows if row["event_type"] == "claim.created")["timestamp"],
                         "2026-09-17T00:00:00Z")

        chronology = [(row["event_type"], row["timestamp"], row["operation_id"])
                      for row in rows if row["event_type"] in {
                          "evaluation.changed", "investigation.requested", "investigation.started",
                          "investigation.completed", "investigation.failed", "technical_check.completed",
                          "human_review.recorded"}]
        self.assertEqual(chronology, [
            ("evaluation.changed", "2026-09-18T12:00:00Z", None),
            ("investigation.requested", "2026-09-22T08:00:00Z", "research-a"),
            ("investigation.started", "2026-09-22T08:05:00Z", "research-a"),
            ("investigation.completed", "2026-09-22T09:00:00Z", "research-a"),
            ("investigation.requested", "2026-09-23T09:30:00Z", "research-b"),
            ("investigation.started", "2026-09-23T09:35:00Z", "research-b"),
            ("investigation.failed", "2026-09-23T10:00:00Z", "research-b"),
            ("technical_check.completed", "2026-09-23T11:00:00Z", "technical-1"),
            ("investigation.requested", "2026-09-23T13:00:00Z", "research-c"),
            ("investigation.started", "2026-09-23T13:05:00Z", "research-c"),
            ("investigation.completed", "2026-09-23T14:00:00Z", "research-c"),
            ("human_review.recorded", "2026-09-23T16:00:00Z", None),
        ])
        failed = next(row for row in rows if row["event_type"] == "investigation.failed")
        self.assertEqual(failed["source_record_id"], "research-b")
        self.assertIn("auditor unavailable", failed["text"])
        self.assertEqual(next(row for row in rows if row["event_type"] == "technical_check.completed")[
            "source_record_type"], "technical_check.operation")

    def test_canonical_timeline_keeps_unknown_dates_and_legacy_aliases(self):
        rows = project_claim_timeline(self.claim, operations=[
            {"operation_id": "legacy-op", "kind": "claim_research", "claim_id": "claim-1", "status": "failed"}
        ])
        events = [row for row in rows if row["source_record_id"] == "legacy-op"]
        self.assertTrue(events)
        self.assertTrue(all(row["timestamp"] is None and row["occurred_at"] is None for row in events))
        self.assertEqual({row["event_type"] for row in events},
                         {"investigation.requested", "investigation.failed"})
        self.assertTrue(all("title" in row and "summary" in row and row["legacy"] for row in events))

    def test_canonical_timeline_does_not_present_naive_timestamp_as_a_valid_date(self):
        rows = project_claim_timeline({**self.claim, "provenance": [{"id": "naive-verdict",
            "previous_status": "PENDING", "status": "UNSUPPORTED",
            "reviewed_at": "2026-09-18T10:00:00"}]})
        event = next(row for row in rows if row["event_type"] == "evaluation.changed")
        self.assertIsNone(event["timestamp"])
        self.assertEqual(event["occurred_at"], "2026-09-18T10:00:00")

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
                     "input_data": {"document_ids": ["doc-1"], "claim_version": 3},
                     "input_fingerprint": "fp-1", "stage": "audit",
                     "progress": {"queries": 2, "pages": 4},
                     "budget_plan": {"target_cap": 6},
                     "result": {"outcome": "supported", "budget_receipts": [{"round": 1}]}}
        projected = project_claim_research_history([operation], "claim-1")
        row = projected["operations"][0]
        self.assertEqual(row["operation_id"], "op-1")
        self.assertEqual(row["evidence_mode"], "documents_only")
        self.assertEqual(row["document_ids"], ["doc-1"])
        self.assertEqual(row["claim_version"], 3)
        self.assertEqual(row["input_fingerprint"], "fp-1")
        self.assertEqual(row["stage"], "audit")
        self.assertEqual(row["progress"], {"queries": 2, "pages": 4})
        self.assertEqual(row["budget_plan"], {"target_cap": 6})
        self.assertEqual(row["budget_receipts"], [{"round": 1}])
        self.assertTrue(row["is_current_result"])
        self.assertIs(projected["latest_operation"], row)
        self.assertIs(projected["current_completed"], row)
        self.assertNotIn("is_current_result", operation)

    def test_claim_research_projection_normalizes_modes_and_legacy_input_fields(self):
        rows = [
            {"operation_id": "question", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T12:00:00Z", "status": "failed",
             "input_data": {"evidence_mode": "question_search", "document_ids": [],
                            "claim_version": 1, "input_fingerprint": "q-fp"},
             "error": {"type": "ValueError", "message": "keep scoped"}},
            {"id": "docs", "kind": "claim_research", "claim_id": "claim-1",
             "created_at": "2026-09-22T12:00:00Z", "status": "done",
             "result": {"resolution": "indeterminate"},
             "input_data": {"evidence_mode": "documents_only", "document_ids": ["doc-a"]}},
            {"operation_id": "mixed", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-21T12:00:00Z", "status": "done",
             "result": {"resolution": "supported"}, "evidence_mode": "documents_plus_search",
             "document_ids": ["doc-b"], "claim_version": 2, "input_fingerprint": "m-fp"},
            {"operation_id": "other-claim", "kind": "claim_research", "claim_id": "claim-2",
             "requested_at": "2026-09-24T12:00:00Z", "status": "done", "result": {}},
        ]
        projected = project_claim_research_history(rows, "claim-1")
        by_id = {row["operation_id"]: row for row in projected["operations"]}
        self.assertEqual(set(by_id), {"question", "docs", "mixed"})
        self.assertEqual(by_id["question"]["evidence_mode"], "question_search")
        self.assertEqual(by_id["question"]["document_ids"], [])
        self.assertEqual(by_id["docs"]["evidence_mode"], "documents_only")
        self.assertEqual(by_id["docs"]["document_ids"], ["doc-a"])
        self.assertEqual(by_id["mixed"]["evidence_mode"], "documents_plus_search")
        self.assertEqual(by_id["mixed"]["document_ids"], ["doc-b"])
        self.assertIsNone(by_id["docs"]["requested_at"])
        self.assertEqual(by_id["docs"]["created_at"], "2026-09-22T12:00:00Z")
        self.assertFalse(by_id["question"]["is_current_result"])
        self.assertFalse(by_id["mixed"]["is_current_result"])
        self.assertEqual(by_id["question"]["error"], {"type": "ValueError", "message": "keep scoped"})
        self.assertEqual(by_id["question"]["input_fingerprint"], "q-fp")
        self.assertEqual(by_id["question"]["budget_receipts"], [])
        self.assertEqual(projected["current_completed"]["operation_id"], "docs")

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

    def test_explicit_new_run_does_not_replace_current_result_until_success(self):
        completed = {"operation_id": "op-done", "kind": "claim_research", "claim_id": "claim-1",
                     "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-22T10:00:00Z",
                     "status": "done", "result": {"resolution": "indeterminate"}}
        running = {"operation_id": "op-new-running", "kind": "claim_research", "claim_id": "claim-1",
                   "requested_at": "2026-09-23T09:00:00Z", "status": "running", "result": None}
        during = project_claim_research_history([completed, running], "claim-1")
        self.assertEqual(during["latest_operation"]["operation_id"], "op-new-running")
        self.assertEqual(during["current_completed"]["operation_id"], "op-done")
        self.assertTrue(next(row for row in during["operations"]
                             if row["operation_id"] == "op-done")["is_current_result"])
        self.assertFalse(next(row for row in during["operations"]
                              if row["operation_id"] == "op-new-running")["is_current_result"])

        failed = {**running, "status": "failed", "finished_at": "2026-09-23T09:30:00Z",
                  "error": {"type": "ValueError", "message": "new run failed"}}
        after_failure = project_claim_research_history([failed, completed], "claim-1")
        self.assertEqual(after_failure["latest_operation"]["operation_id"], "op-new-running")
        self.assertEqual(after_failure["latest_operation"]["error"]["message"], "new run failed")
        self.assertEqual(after_failure["current_completed"]["operation_id"], "op-done")
        self.assertTrue(next(row for row in after_failure["operations"]
                             if row["operation_id"] == "op-done")["is_current_result"])

        successful = {**running, "status": "completed_with_limits",
                      "finished_at": "2026-09-23T14:00:00Z", "result": {"resolution": "supported"}}
        after_success = project_claim_research_history([completed, successful], "claim-1")
        self.assertEqual(after_success["current_completed"]["operation_id"], "op-new-running")
        self.assertFalse(next(row for row in after_success["operations"]
                              if row["operation_id"] == "op-done")["is_current_result"])

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
        self.assertIsNone(first["operations"][-1]["requested_at"])
        self.assertTrue(first["has_active"])

    def test_claim_research_projection_uses_created_only_as_ordering_fallback(self):
        rows = [
            {"operation_id": "created-later", "kind": "claim_research", "claim_id": "claim-1",
             "created_at": "2026-09-23T12:00:00Z", "updated_at": "2026-09-24T12:00:00Z", "status": "failed"},
            {"operation_id": "requested-earlier", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T11:00:00Z", "status": "failed"},
            {"operation_id": "unknown", "kind": "claim_research", "claim_id": "claim-1",
             "updated_at": "2026-09-25T12:00:00Z", "status": "failed"},
        ]
        projected = project_claim_research_history(rows, "claim-1")
        self.assertEqual([row["operation_id"] for row in projected["operations"]],
                         ["created-later", "requested-earlier", "unknown"])
        created_row = next(row for row in projected["operations"] if row["operation_id"] == "created-later")
        self.assertIsNone(created_row["requested_at"])
        self.assertEqual(created_row["created_at"], "2026-09-23T12:00:00Z")
        unknown_row = next(row for row in projected["operations"] if row["operation_id"] == "unknown")
        self.assertIsNone(unknown_row["requested_at"])
        self.assertIsNone(unknown_row["created_at"])

    def test_claim_research_projection_ignores_invalid_preferred_time_and_uses_next_valid_for_order(self):
        rows = [
            {"operation_id": "fallback", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "not-a-time", "created_at": "2026-09-23T12:00:00+00:00", "status": "failed"},
            {"operation_id": "later", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-23T13:00:00Z", "status": "failed"},
        ]
        projected = project_claim_research_history(rows, "claim-1")
        self.assertEqual([row["operation_id"] for row in projected["operations"]], ["later", "fallback"])
        self.assertEqual(projected["operations"][1]["requested_at"], "not-a-time")
        self.assertEqual(projected["operations"][1]["created_at"], "2026-09-23T12:00:00+00:00")

    def test_equal_completion_timestamps_use_stable_operation_id_tiebreak(self):
        rows = [
            {"operation_id": "z-op", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-22T09:00:00Z", "finished_at": "2026-09-23T12:00:00Z",
             "status": "done", "result": {"resolution": "indeterminate"}},
            {"operation_id": "a-op", "kind": "claim_research", "claim_id": "claim-1",
             "requested_at": "2026-09-22T10:00:00Z", "finished_at": "2026-09-23T12:00:00+00:00",
             "status": "done", "result": {"resolution": "indeterminate"}},
        ]
        projected = project_claim_research_history(rows, "claim-1")
        self.assertEqual(projected["current_completed"]["operation_id"], "a-op")

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

    def test_case_activity_merges_canonical_claim_events_deterministically(self):
        first = project_claim_timeline({"id": "claim-a", "claim": "A", "created_at": "2026-09-18T10:00:00Z"})
        second = project_claim_timeline({"id": "claim-b", "claim": "B", "created_at": "2026-09-18T09:00:00Z"})
        case_event = case_activity_event("case-1", record_type="case.json", record_id="case-1",
            event_type="case.created", timestamp="2026-09-17T10:00:00Z", title="Expediente creado",
            target_view="question")
        before = [list(first), list(second)]
        actual = project_case_activity([first, second], [case_event, case_event])
        reversed_actual = project_case_activity([second, first], [case_event])
        self.assertEqual([row["event_id"] for row in actual], [row["event_id"] for row in reversed_actual])
        self.assertEqual(len(actual), len({row["event_id"] for row in actual}))
        self.assertEqual(actual[0]["event_type"], "case.created")
        self.assertEqual(actual[0]["target_view"], "question")
        claim_rows = [row for row in actual if row.get("claim_id")]
        self.assertTrue(claim_rows)
        self.assertTrue(all(row["target_view"] == "claims" for row in claim_rows))
        original_by_id = {row["event_id"]: row for row in (*first, *second)}
        for row in claim_rows:
            original = original_by_id[row["event_id"]]
            self.assertEqual(row["timestamp"], original["timestamp"])
            self.assertEqual(row["event_type"], original["event_type"])
            self.assertEqual(row["source_record_id"], original["source_record_id"])
        self.assertEqual([list(first), list(second)], before)

    def test_case_activity_preserves_unknown_dates_and_uses_stable_ties(self):
        known_a = case_activity_event("case-1", record_type="case", record_id="z",
            event_type="case.beta", timestamp="2026-09-24T10:00:00Z", title="B")
        known_b = case_activity_event("case-1", record_type="case", record_id="a",
            event_type="case.alpha", timestamp="2026-09-24T10:00:00Z", title="A")
        unknown = case_activity_event("case-1", record_type="legacy", record_id="legacy-1",
            event_type="legacy.unknown", timestamp="2026-09-24T10:00:00", title="Legacy")
        rows = project_case_activity([], [unknown, known_a, known_b])
        self.assertEqual([row["event_type"] for row in rows], ["case.alpha", "case.beta", "legacy.unknown"])
        self.assertIsNone(rows[-1]["timestamp"])
        self.assertTrue(rows[-1]["legacy"])

    def test_execution_receipts_are_claim_timeline_events(self):
        rows = project_claim_timeline({"id": "claim-1", "execution_receipts": [
            {"run_id": "run-1", "stage": "pass2", "status": "provider_completed",
             "finished_at": "2026-09-23T09:00:00Z", "elapsed_seconds": 12, "reused": True},
            {"run_id": "run-2", "stage": "pass3", "status": "failed", "finished_at": None},
        ]})
        receipts = [row for row in rows if row["event_type"] == "investigation.tool_receipt"]
        self.assertEqual(len(receipts), 2)
        self.assertEqual(receipts[0]["source_record_id"], "run-1:pass2")
        self.assertIn("12 segundos", receipts[0]["summary"])
        self.assertIn("reutilizada", receipts[0]["summary"])
        self.assertIsNone(receipts[1]["timestamp"])
        self.assertEqual(receipts[1]["source_record_id"], "run-2:pass3")


if __name__ == "__main__":
    unittest.main()
