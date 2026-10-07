import contextlib
from copy import deepcopy
from datetime import date, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "coverage_audit", Path(__file__).resolve().parents[1] / "scripts" / "coverage.py",
)
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)
AS_OF = date(2026, 10, 4)


def catalog():
    return {
        "schema_version": 1, "exam": "test-100", "revision": "v1",
        "verified": True, "verification_note": "Fixture source reconciled",
        "sources": [{
            "id": "guide", "url": "https://learn.microsoft.com/example",
            "checked_at": "2026-10-04", "published_revision": "fixture",
        }],
        "domains": [{
            "id": "d1", "title": "Domain", "weight_min": 100, "weight_max": 100,
            "objectives": [{
                "id": "o1", "title": "Broad objective", "source_id": "guide",
                "source_locator": "Domain > objective",
                "subskills": [
                    {"id": "s1", "title": "Operation one", "derived": True},
                    {"id": "s2", "title": "Operation two", "derived": True},
                ],
            }],
        }],
    }


def attempt(aid="a1", sid="s1", **changes):
    row = {
        "id": aid, "session_id": "session1", "timestamp": "2026-10-01T12:00:00Z",
        "blueprint_revision": "v1", "subskill_ids": [sid],
        "result": "correct", "assistance": "unaided", "context": "cold",
        "response_ref": f"local-session:session1#{aid}", "genuine_confirmed": True,
        "reasoning_demonstrated": True, "novel": True, "diagnosis": "none", "action": "",
    }
    row.update(changes)
    return row


def unit(uid="u1", kind="coverage", **changes):
    row = {
        "id": uid, "session_id": "session1", "timestamp": "2026-10-01T11:00:00Z",
        "kind": kind, "mode": "normal", "subskill_ids": ["s1"],
    }
    row.update(changes)
    return row


class CoverageTests(unittest.TestCase):
    def test_queue_orders_mixed_offsets_by_instant_and_keeps_equal_instant_ties_stable(self):
        self.ledger["attempts"] = [
            attempt("earlier", "s2", timestamp="2026-10-02T01:00:00+02:00"),
            attempt("later", "s1", timestamp="2026-10-01T23:00:00-05:00"),
        ]
        self.assertEqual(self.report()["coverage_queue"], ["s2", "s1"])
        self.ledger["attempts"] = [
            attempt("same-s1", "s1", timestamp="2026-10-02T04:00:00+00:00"),
            attempt("same-s2", "s2", timestamp="2026-10-01T23:00:00-05:00"),
        ]
        self.assertEqual(self.report()["coverage_queue"], ["s1", "s2"])

    def test_breadth_orders_mixed_offsets_by_instant_not_date_spelling(self):
        self.ledger["attempts"] = [
            attempt("earliest", session_id="one", timestamp="2026-10-01T22:00:00+00:00"),
            attempt("earlier", session_id="two", timestamp="2026-10-02T01:00:00+02:00"),
            attempt("latest", session_id="three", timestamp="2026-10-01T23:00:00-05:00"),
        ]
        self.assertEqual(self.report()["session_breadth"]["session_ids"], ["one", "two", "three"])

    def test_mixed_offsets_preserve_ledger_chronology_and_pending_check_order(self):
        self.ledger["attempts"] = [
            attempt("source", timestamp="2026-10-02T01:00:00+02:00"),
            attempt("later", session_id="session2", timestamp="2026-10-01T23:00:00-05:00"),
        ]
        self.ledger["pending_checks"] = [{
            "id": "check", "subskill_id": "s1", "after_attempt_id": "source",
            "kind": "cold", "status": "completed", "evidence_attempt_id": "later",
        }]
        self.assertEqual(self.report()["pending_checks"], [])
        self.ledger["attempts"].reverse()
        with self.assertRaisesRegex(coverage.CoverageError, "chronological order"):
            self.report()

    def setUp(self):
        self.catalog = catalog()
        self.ledger = coverage.empty_ledger(self.catalog)

    def report(self):
        return coverage.report(self.catalog, self.ledger, AS_OF)

    def test_missing_evidence_is_all_gaps(self):
        result = self.report()
        self.assertEqual(result["unassessed"], ["s1", "s2"])
        self.assertEqual(result["objectives_fully_assessed"], 0)
        self.assertEqual(result["weighted_assessed_percent"], 0)

    def test_one_narrow_success_does_not_clear_broad_objective(self):
        self.ledger["attempts"] = [attempt()]
        result = self.report()
        self.assertEqual(result["subskills"]["demonstrated"], 1)
        self.assertEqual(result["objectives_fully_assessed"], 0)
        self.assertEqual(result["weighted_assessed_percent"], 50)

    def test_assistance_reasoning_and_post_teaching_are_distinct(self):
        for changes in [
            {"assistance": "assisted"}, {"assistance": "unknown"},
            {"reasoning_demonstrated": False}, {"novel": False},
            {"context": "post_teaching"},
        ]:
            with self.subTest(changes=changes):
                self.ledger["attempts"] = [attempt(**changes)]
                result = self.report()
                self.assertEqual(result["subskills"]["demonstrated"], 0)
                self.assertEqual(result["subskills"]["delayed_transfer"], 0)

    def test_failed_independent_attempt_counts_as_assessed_not_mastered(self):
        self.ledger["attempts"] = [attempt(result="incorrect")]
        result = self.report()
        self.assertEqual(result["subskills"]["assessed"], 1)
        self.assertEqual(result["subskills"]["demonstrated"], 0)

    def test_post_teaching_success_neither_promotes_nor_erases_prior_evidence(self):
        check = attempt("a2", timestamp="2026-10-02T12:00:00Z", context="post_teaching")
        self.ledger["attempts"] = [attempt(), check]
        self.assertEqual(self.report()["subskills"]["demonstrated"], 1)
        self.ledger["attempts"][0]["result"] = "incorrect"
        self.assertEqual(self.report()["subskills"]["demonstrated"], 0)
        self.ledger["attempts"][0]["result"] = "correct"
        self.ledger["attempts"][1]["result"] = "partial"
        self.assertEqual(self.report()["subskills"]["demonstrated"], 0)

    def test_delayed_transfer_requires_source_and_later_local_day(self):
        self.ledger["attempts"] = [attempt(context="delayed_transfer")]
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 0)
        self.assertEqual(self.report()["retention_ineligible_attempts"], ["a1"])
        self.ledger["study_timezone"] = "UTC-05:00"
        self.ledger["attempts"] = [
            attempt(), attempt("a2", session_id="session2",
                               timestamp="2026-10-03T12:00:00Z", context="delayed_transfer",
                               retention_source_id="a1"),
        ]
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 1)
        self.ledger["attempts"].append(
            attempt("a3", timestamp="2026-10-04T12:00:00Z", result="partial"),
        )
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 0)

    def test_unverified_outline_blocks_completeness(self):
        self.catalog["verified"] = False
        self.assertTrue(self.report()["blocked"])

    def test_catalog_errors_are_explicit(self):
        invalid = []
        duplicate = catalog()
        duplicate["domains"][0]["objectives"][0]["subskills"][1]["id"] = "s1"
        invalid.append(duplicate)
        missing = catalog()
        missing["domains"][0]["objectives"][0]["subskills"] = []
        invalid.append(missing)
        wrong_exam = catalog()
        wrong_exam["exam"] = "other"
        invalid.append(wrong_exam)
        future = catalog()
        future["sources"][0]["checked_at"] = "2099-01-01"
        invalid.append(future)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(coverage.CoverageError):
                    coverage.validate_catalog(value, "test-100", AS_OF)

    def test_bad_provenance_and_references_fail(self):
        for change in [
            {"genuine_confirmed": False}, {"response_ref": ""},
            {"blueprint_revision": "v0"}, {"subskill_ids": ["foreign"]},
            {"timestamp": "2027-01-01T12:00:00Z"},
            {"timestamp": "2026-10-01T12:00:00"},
        ]:
            with self.subTest(change=change):
                self.ledger["attempts"] = [attempt(**change)]
                with self.assertRaises(coverage.CoverageError):
                    self.report()

    def test_revision_or_exam_change_requires_reconciliation(self):
        for key, value in [("exam", "other"), ("blueprint_revision", "v2")]:
            original = self.ledger[key]
            self.ledger[key] = value
            with self.assertRaises(coverage.CoverageError):
                self.report()
            self.ledger[key] = original

    def test_invalid_field_types_fail_explicitly(self):
        for key in ("result", "assistance", "context", "diagnosis"):
            with self.subTest(key=key):
                self.ledger["attempts"] = [attempt(**{key: ["invalid"]})]
                with self.assertRaises(coverage.CoverageError):
                    self.report()
        self.ledger["attempts"] = []
        self.catalog["schema_version"] = True
        with self.assertRaises(coverage.CoverageError):
            self.report()

    def test_exact_twenty_unit_cycle_and_short_session_carryover(self):
        self.ledger["study_units"] = [
            unit(f"u{i}", kind, session_id=f"session{i // 3}",
                 subskill_ids=["s2" if i == 1 else "s1"])
            for i, kind in enumerate(coverage.CYCLE)
        ]
        result = self.report()
        self.assertEqual(result["actual_allocation"],
                         {"coverage": 12, "remediation": 5, "retention": 3})
        self.assertEqual(result["next_allocation"], "coverage")
        self.ledger["study_units"] = self.ledger["study_units"][:2]
        self.assertEqual(self.report()["next_allocation"], "remediation")

    def test_remediation_cannot_steal_first_coverage_slot(self):
        self.ledger["study_units"] = [unit(kind="remediation")]
        with self.assertRaisesRegex(coverage.CoverageError, "Protected"):
            self.report()

    def test_override_and_mock_do_not_consume_cycle(self):
        self.ledger["study_units"] = [
            unit(mode="override", reason="User asked for a narrow drill"),
            unit("u2", mode="mock", reason="Weighted deferred mock"),
        ]
        result = self.report()
        self.assertEqual(result["normal_units"], 0)
        self.assertEqual(result["override_units"], 1)
        self.assertEqual(result["next_allocation"], "coverage")

    def test_empty_retention_substitution_is_explicit(self):
        self.ledger["study_units"] = [
            unit(f"u{i}", kind, subskill_ids=["s2" if i == 1 else "s1"])
            for i, kind in enumerate(coverage.CYCLE[:5])
        ]
        self.ledger["study_units"][-1]["kind"] = "coverage"
        with self.assertRaises(coverage.CoverageError):
            self.report()
        self.ledger["study_units"][-1]["reason"] = "no-retention-evidence"
        self.report()
        self.ledger["attempts"] = [attempt(timestamp="2026-09-30T12:00:00Z", sid="s2")]
        self.ledger["study_units"][1]["subskill_ids"] = ["s1"]
        with self.assertRaisesRegex(coverage.CoverageError, "Retention evidence exists"):
            self.report()

    def test_unassessed_first_pass_cannot_loop_on_one_skill(self):
        self.ledger["attempts"] = [
            attempt(context="teaching", result="unscored", assistance="assisted"),
        ]
        self.ledger["study_units"] = [
            unit(), unit("u2", timestamp="2026-10-02T11:00:00Z"),
        ]
        with self.assertRaisesRegex(coverage.CoverageError, "first pass"):
            self.report()
        self.ledger["study_units"] = [unit()]
        self.assertEqual(self.report()["coverage_queue"], ["s2", "s1"])

    def test_queue_weights_order_but_never_omits_low_weight_domain(self):
        self.catalog["domains"][0]["weight_min"] = 80
        self.catalog["domains"][0]["weight_max"] = 80
        second = deepcopy(self.catalog["domains"][0])
        second.update(id="d2", title="Small domain", weight_min=20, weight_max=20)
        second["objectives"][0]["id"] = "o2"
        second["objectives"][0]["subskills"] = [
            {"id": "s3", "title": "Small but required", "derived": True},
        ]
        self.catalog["domains"].append(second)
        self.assertEqual(self.report()["coverage_queue"], ["s1", "s2", "s3"])

    def test_coverage_rejects_mixing_visited_with_unvisited_subskills(self):
        self.ledger["attempts"] = [
            attempt(context="teaching", result="unscored", assistance="assisted"),
        ]
        self.ledger["study_units"] = [
            unit(), unit("u2", subskill_ids=["s1", "s2"],
                         timestamp="2026-10-02T11:00:00Z"),
        ]
        with self.assertRaisesRegex(coverage.CoverageError, "first pass"):
            self.report()
        self.ledger["study_units"][1]["subskill_ids"] = ["s2"]
        self.report()

    def test_unanswered_scope_does_not_visit_or_block_eligible_coverage(self):
        for mode in ("normal", "override", "mock"):
            with self.subTest(mode=mode):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.ledger["study_units"] = [
                    unit(mode=mode, lifecycle="started", reason="Explicit scope"),
                ]
                self.assertEqual(self.report()["coverage_queue"], ["s1", "s2"])
                self.ledger["unit_events"] = [{
                    "id": "defer", "unit_id": "u1", "status": "deferred",
                    "timestamp": "2026-10-01T13:00:00Z", "reason": "No evidence yet",
                }]
                self.ledger["study_units"].append(
                    unit("u2", timestamp="2026-10-02T11:00:00Z", lifecycle="started"),
                )
                result = self.report()
                self.assertEqual(result["normal_units"], 2 if mode == "normal" else 1)
                self.assertEqual(result["next_allocation"],
                                 "remediation" if mode == "normal" else "coverage")
                self.assertEqual(result["completed_normal_units"], 0)
                self.assertEqual(result["unfinished_units"][-1]["unit_id"], "u2")

    def test_partial_aborted_mock_only_visits_delivered_subskills(self):
        for result, context, assistance in (
            ("unscored", "teaching", "assisted"),
            ("incorrect", "mock", "unaided"),
        ):
            with self.subTest(context=context):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.ledger["study_units"] = [
                    unit(mode="mock", reason="Two planned targets", lifecycle="started",
                         subskill_ids=["s1", "s2"]),
                ]
                self.ledger["attempts"] = [
                    attempt(sid="s2", unit_id="u1", result=result,
                            context=context, assistance=assistance),
                ]
                self.ledger["unit_events"] = [{
                    "id": "pause", "unit_id": "u1", "status": "interrupted",
                    "timestamp": "2026-10-01T13:00:00Z", "reason": "Aborted mock",
                }]
                self.assertEqual(self.report()["coverage_queue"], ["s1", "s2"])
                self.ledger["study_units"].append(
                    unit("u2", timestamp="2026-10-02T11:00:00Z", lifecycle="started"),
                )
                self.assertEqual(self.report()["normal_units"], 1)
                self.ledger["study_units"][-1]["subskill_ids"] = ["s1", "s2"]
                with self.assertRaisesRegex(coverage.CoverageError,
                                            "first pass|repeats assessed"):
                    self.report()

    def test_unlinked_teaching_visits_without_allocation_or_assessment(self):
        for context, assistance in (("teaching", "assisted"), ("historical", "unknown")):
            with self.subTest(context=context):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.ledger["attempts"] = [
                    attempt(context=context, result="unscored", assistance=assistance),
                ]
                self.assertNotIn("unit_id", self.ledger["attempts"][0])
                result = self.report()
                self.assertEqual(result["coverage_queue"], ["s2", "s1"])
                self.assertEqual(result["normal_units"], 0)
                self.assertEqual(result["subskills"]["assessed"], 0)
                self.ledger["study_units"] = [unit(timestamp="2026-10-02T11:00:00Z")]
                with self.assertRaisesRegex(coverage.CoverageError, "first pass"):
                    self.report()
                self.ledger["study_units"][0]["subskill_ids"] = ["s2"]
                self.report()

    def test_first_pass_uses_evidence_time_not_planned_scope(self):
        self.ledger["study_units"] = [
            unit(mode="mock", reason="Later delivery"),
            unit("u2", timestamp="2026-10-02T11:00:00Z"),
        ]
        self.ledger["attempts"] = [
            attempt(unit_id="u1", timestamp="2026-10-03T12:00:00Z",
                    context="teaching", result="unscored", assistance="assisted"),
        ]
        self.assertEqual(self.report()["coverage_queue"], ["s2", "s1"])

    def test_void_timing_preserves_historical_visit_but_not_current_queue(self):
        self.ledger["attempts"] = [
            attempt(context="teaching", result="unscored", assistance="assisted"),
            attempt("a2", "s2", context="teaching", result="unscored",
                    assistance="assisted", timestamp="2026-10-01T12:01:00Z"),
        ]
        self.ledger["study_units"] = [unit(timestamp="2026-10-02T11:00:00Z")]
        self.ledger["voided_attempts"] = [{
            "id": "void", "attempt_id": "a1", "reason": "Invalid evidence",
            "timestamp": "2026-10-03T12:00:00Z", "response_ref": "local:correction",
            "genuine_confirmed": True,
        }]
        self.assertEqual(self.report()["coverage_queue"], ["s1", "s2"])
        # At or before the next start the void makes s1 eligible again.
        for moment in ("2026-10-02T11:00:00Z", "2026-10-01T13:00:00Z"):
            with self.subTest(moment=moment):
                self.ledger["voided_attempts"][0]["timestamp"] = moment
                self.report()
                self.ledger["study_units"][0]["subskill_ids"] = ["s2"]
                with self.assertRaisesRegex(coverage.CoverageError, "first pass"):
                    self.report()
                self.ledger["study_units"][0]["subskill_ids"] = ["s1"]

    def test_later_void_does_not_retroactively_reject_eligible_selection(self):
        self.ledger["attempts"] = [
            attempt(context="teaching", result="unscored", assistance="assisted"),
        ]
        self.ledger["study_units"] = [
            unit(timestamp="2026-10-02T11:00:00Z", subskill_ids=["s2"]),
        ]
        self.ledger["voided_attempts"] = [{
            "id": "void", "attempt_id": "a1", "reason": "Invalid evidence",
            "timestamp": "2026-10-03T12:00:00Z", "response_ref": "local:correction",
            "genuine_confirmed": True,
        }]
        self.report()
        self.ledger["voided_attempts"][0]["timestamp"] = "2026-10-01T13:00:00Z"
        self.ledger["study_units"][0]["subskill_ids"] = ["s1"]
        self.report()

    def test_queue_counts_delivered_visits_not_allocated_target_counts(self):
        self.ledger["attempts"] = [
            attempt("a1", context="teaching", result="unscored"),
            attempt("a2", timestamp="2026-10-01T12:01:00Z",
                    context="teaching", result="unscored"),
            attempt("a3", "s2", timestamp="2026-10-01T12:02:00Z",
                    context="teaching", result="unscored"),
        ]
        self.assertEqual(self.report()["coverage_queue"], ["s2", "s1"])

    def test_coverage_rejects_mixing_assessed_with_unassessed_subskills(self):
        self.ledger["attempts"] = [attempt(timestamp="2026-09-30T12:00:00Z")]
        self.ledger["study_units"] = [unit(subskill_ids=["s1", "s2"])]
        with self.assertRaisesRegex(coverage.CoverageError, "repeats assessed"):
            self.report()
        self.ledger["study_units"][0]["subskill_ids"] = ["s2"]
        self.report()

    def test_coverage_allows_multiple_eligible_subskills_and_full_pass_revisits(self):
        self.ledger["study_units"] = [unit(subskill_ids=["s1", "s2"])]
        self.report()
        self.ledger["attempts"] = [
            attempt(subskill_ids=["s1", "s2"], unit_id="u1", context="teaching",
                    result="unscored", assistance="assisted"),
        ]
        self.ledger["study_units"].append(
            unit("u2", subskill_ids=["s1", "s2"], timestamp="2026-10-02T11:00:00Z"),
        )
        self.report()
        self.ledger["attempts"] = [
            attempt(timestamp="2026-09-30T12:00:00Z"),
            attempt("a2", "s2", timestamp="2026-09-30T12:01:00Z"),
        ]
        self.report()

    def breadth_fixture(self):
        self.catalog["domains"][0].update(weight_min=50, weight_max=50)
        second = deepcopy(self.catalog["domains"][0])
        second.update(id="d2", title="Second domain")
        second["objectives"][0].update(
            id="o2", subskills=[{"id": "s3", "title": "Second domain skill", "derived": True}],
        )
        self.catalog["domains"].append(second)
        self.ledger["study_units"] = [
            unit("normal", session_id="normal", lifecycle="started"),
            unit("mock", session_id="mock", mode="mock", reason="Explicit mock",
                 timestamp="2026-10-02T11:00:00Z", lifecycle="started"),
            unit("override", session_id="override", mode="override", reason="Explicit tutoring",
                 timestamp="2026-10-03T11:00:00Z", lifecycle="started"),
        ]
        self.ledger["attempts"] = [
            attempt("old", "s3", session_id="old", timestamp="2026-09-30T12:00:00Z",
                    context="historical"),
            attempt("normal", session_id="normal"),
            attempt("mock", session_id="mock", timestamp="2026-10-02T12:00:00Z",
                    context="mock"),
            attempt("override", session_id="override", timestamp="2026-10-03T12:00:00Z",
                    context="teaching", result="unscored", assistance="assisted"),
        ]

    def test_breadth_reports_empty_and_partial_windows_without_completeness_claim(self):
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth, {
            "window_size": 3, "window_complete": False, "session_ids": [], "sessions": [],
            "touched_domain_ids": [], "missing_domain_ids": ["d1"],
        })
        self.ledger["attempts"] = [attempt()]
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["session1"])
        self.assertFalse(breadth["window_complete"])
        self.assertEqual(breadth["missing_domain_ids"], [])

    def test_breadth_uses_last_three_distinct_sessions_across_all_modes(self):
        self.breadth_fixture()
        before = deepcopy(self.ledger)
        result = self.report()
        breadth = result["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["normal", "mock", "override"])
        self.assertTrue(breadth["window_complete"])
        self.assertEqual(breadth["touched_domain_ids"], ["d1"])
        self.assertEqual(breadth["missing_domain_ids"], ["d2"])
        self.assertEqual(result["domains"][1]["assessed"], 1)
        self.assertEqual(result["normal_units"], 1)
        self.assertEqual(self.ledger, before)
        result["sha256"] = None
        self.assertIn("Domain breadth gaps: d2", coverage.render(result))
        self.assertEqual(len(breadth["sessions"]), 3)

    def test_breadth_counts_teaching_as_exposure_not_mastery(self):
        self.breadth_fixture()
        self.ledger["attempts"].pop(0)
        self.ledger["attempts"][-1]["subskill_ids"] = ["s3"]
        result = self.report()
        self.assertEqual(result["session_breadth"]["missing_domain_ids"], [])
        self.assertEqual(result["session_breadth"]["sessions"][-1]["domain_ids"], ["d2"])
        self.assertEqual(result["domains"][1]["assessed"], 0)
        self.assertEqual(result["domains"][1]["demonstrated"], 0)

    def test_breadth_event_only_resume_returns_old_session_without_domain_credit(self):
        self.breadth_fixture()
        self.ledger["attempts"].pop(0)
        self.ledger["study_units"].insert(0, unit(
            "old-unit", session_id="old", mode="override", reason="Old scope",
            timestamp="2026-09-30T11:00:00Z", lifecycle="started", subskill_ids=["s3"],
        ))
        self.ledger["unit_events"] = [
            {"id": "pause", "unit_id": "old-unit", "status": "interrupted",
             "timestamp": "2026-09-30T13:00:00Z", "reason": "Paused"},
            {"id": "resume", "unit_id": "old-unit", "status": "started",
             "timestamp": "2026-10-04T12:00:00Z", "reason": "Resumed without answer"},
        ]
        before = deepcopy(self.ledger)
        result = self.report()
        breadth = result["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["mock", "override", "old"])
        self.assertEqual(breadth["sessions"][-1], {
            "session_id": "old", "last_activity": "2026-10-04T12:00:00+00:00",
            "domain_ids": [],
        })
        self.assertEqual(breadth["missing_domain_ids"], ["d2"])
        self.assertEqual(result["normal_units"], 1)
        self.assertEqual(self.ledger, before)
        self.ledger["study_units"] = [self.ledger["study_units"][0]]
        self.ledger["attempts"] = []
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["old"])
        self.assertFalse(breadth["window_complete"])
        self.assertEqual(breadth["missing_domain_ids"], ["d1", "d2"])

    def test_breadth_started_events_deduplicate_sessions_and_break_ties_by_id(self):
        self.breadth_fixture()
        self.ledger["unit_events"] = [
            {"id": "pause", "unit_id": "normal", "status": "interrupted",
             "timestamp": "2026-10-01T13:00:00Z", "reason": "Paused"},
            {"id": "resume", "unit_id": "normal", "status": "started",
             "timestamp": "2026-10-02T11:30:00Z", "reason": "Earlier resume"},
            {"id": "pause2", "unit_id": "normal", "status": "interrupted",
             "timestamp": "2026-10-02T13:00:00Z", "reason": "Paused again"},
            {"id": "pause3", "unit_id": "override", "status": "deferred",
             "timestamp": "2026-10-03T13:00:00Z", "reason": "Deferred"},
            {"id": "resume2", "unit_id": "normal", "status": "started",
             "timestamp": "2026-10-04T12:00:00Z", "reason": "Resumed again"},
            {"id": "resume3", "unit_id": "override", "status": "started",
             "timestamp": "2026-10-04T12:00:00Z", "reason": "Resumed override"},
        ]
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["mock", "normal", "override"])
        self.assertEqual(len(breadth["sessions"]), 3)
        self.assertEqual([s["last_activity"] for s in breadth["sessions"]], [
            "2026-10-02T12:00:00+00:00", "2026-10-04T12:00:00+00:00",
            "2026-10-04T12:00:00+00:00",
        ])

    def test_breadth_nonstarted_events_do_not_update_latest_activity(self):
        for status in ("completed", "interrupted", "deferred"):
            with self.subTest(status=status):
                self.catalog = catalog()
                self.ledger = coverage.empty_ledger(self.catalog)
                self.breadth_fixture()
                self.ledger["attempts"][2]["unit_id"] = "mock"
                self.ledger["unit_events"] = [{
                    "id": "event", "unit_id": "mock", "status": status,
                    "timestamp": "2026-10-04T12:00:00Z", "reason": "Not a start",
                }]
                breadth = self.report()["session_breadth"]
                self.assertEqual(breadth["session_ids"], ["normal", "mock", "override"])
                self.assertEqual(breadth["sessions"][1]["last_activity"],
                                 "2026-10-02T12:00:00+00:00")

    def test_breadth_void_reopens_gap_without_backfilling_an_older_session(self):
        self.breadth_fixture()
        self.ledger["attempts"][-1]["subskill_ids"] = ["s3"]
        self.assertEqual(self.report()["session_breadth"]["missing_domain_ids"], [])
        self.ledger["voided_attempts"] = [{
            "id": "void", "attempt_id": "override", "reason": "Invalid teaching evidence",
            "response_ref": "local-session:correction", "genuine_confirmed": True,
            "timestamp": "2026-10-04T12:00:00Z",
        }]
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["normal", "mock", "override"])
        self.assertEqual(breadth["missing_domain_ids"], ["d2"])
        self.assertEqual(breadth["sessions"][-1]["domain_ids"], [])

    def test_breadth_started_only_session_counts_but_earns_no_domain_credit(self):
        self.breadth_fixture()
        self.ledger["study_units"].append(unit(
            "empty", session_id="empty", mode="override", reason="Interrupted before teaching",
            lifecycle="started", subskill_ids=["s3"], timestamp="2026-10-04T11:00:00Z",
        ))
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["mock", "override", "empty"])
        self.assertEqual(breadth["sessions"][-1]["domain_ids"], [])
        self.assertEqual(breadth["missing_domain_ids"], ["d2"])

    def test_breadth_resumed_sessions_are_deduplicated_and_ties_are_stable(self):
        self.breadth_fixture()
        self.ledger["attempts"].extend([
            attempt("resume", session_id="normal", timestamp="2026-10-04T12:00:00Z"),
            attempt("tied", session_id="z-last", timestamp="2026-10-04T12:00:00Z"),
        ])
        breadth = self.report()["session_breadth"]
        self.assertEqual(breadth["session_ids"], ["override", "normal", "z-last"])
        self.assertEqual(breadth["sessions"][1]["last_activity"], "2026-10-04T12:00:00+00:00")

    def test_unseen_gap_cannot_be_replaced_with_familiar_question(self):
        self.ledger["attempts"] = [attempt(timestamp="2026-09-30T12:00:00Z")]
        self.ledger["study_units"] = [unit()]
        with self.assertRaisesRegex(coverage.CoverageError, "repeats assessed"):
            self.report()
        self.ledger["study_units"][0]["subskill_ids"] = ["s2"]
        self.report()

    def test_completed_initial_pass_allows_systematic_revisit(self):
        self.ledger["attempts"] = [
            attempt(timestamp="2026-09-30T12:00:00Z"),
            attempt("a2", "s2", timestamp="2026-09-30T12:01:00Z"),
        ]
        self.ledger["study_units"] = [unit()]
        self.assertEqual(self.report()["objectives_fully_assessed"], 1)

    def test_diagnosis_requires_instructional_action(self):
        self.ledger["attempts"] = [attempt(diagnosis="mechanism")]
        with self.assertRaisesRegex(coverage.CoverageError, "instructional action"):
            self.report()
        self.ledger["attempts"][0]["action"] = "Teach the protocol constraint"
        self.report()

    def test_pending_check_completion_does_not_mean_success(self):
        self.ledger["attempts"] = [
            attempt(), attempt("a2", session_id="session2", result="incorrect",
                               timestamp="2026-10-03T12:00:00Z"),
        ]
        check = {
            "id": "c1", "subskill_id": "s1", "after_attempt_id": "a1",
            "kind": "cold", "status": "pending", "evidence_attempt_id": None,
        }
        self.ledger["pending_checks"] = [check]
        self.assertEqual(len(self.report()["pending_checks"]), 1)
        updated = dict(check, status="completed", evidence_attempt_id="a2")
        self.ledger = coverage.merge_batch(self.ledger, {"pending_checks": [updated]})
        self.assertEqual(len(self.report()["pending_checks"]), 0)
        self.assertEqual(self.report()["subskills"]["demonstrated"], 0)

    def test_idempotent_replay_and_conflict(self):
        batch = {"attempts": [attempt()]}
        first = coverage.merge_batch(self.ledger, batch)
        second = coverage.merge_batch(first, batch)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(coverage.CoverageError, "Conflicting"):
            coverage.merge_batch(first, {"attempts": [attempt(result="incorrect")]})

    def test_disowned_answer_is_voided_not_deleted(self):
        self.ledger["attempts"] = [attempt()]
        void = {
            "id": "v1", "attempt_id": "a1", "reason": "User disowned the answer",
            "response_ref": "local-session:session2#turn1", "genuine_confirmed": True,
            "timestamp": "2026-10-02T12:00:00Z",
        }
        self.ledger = coverage.merge_batch(self.ledger, {"voided_attempts": [void]})
        self.assertEqual(len(self.ledger["attempts"]), 1)
        self.assertEqual(self.report()["subskills"]["assessed"], 0)
        self.assertEqual(self.report()["voided_attempts"], 1)
        self.ledger["study_units"] = [unit(timestamp="2026-10-03T12:00:00Z")]
        self.report()
        self.ledger["voided_attempts"][0]["genuine_confirmed"] = False
        with self.assertRaisesRegex(coverage.CoverageError, "genuine user"):
            self.report()

    def test_voided_completion_reopens_pending_check(self):
        self.ledger["attempts"] = [
            attempt(), attempt("a2", session_id="session2",
                               timestamp="2026-10-02T12:00:00Z"),
        ]
        self.ledger["pending_checks"] = [{
            "id": "c1", "subskill_id": "s1", "after_attempt_id": "a1",
            "kind": "cold", "status": "completed", "evidence_attempt_id": "a2",
        }]
        self.ledger["voided_attempts"] = [{
            "id": "v1", "attempt_id": "a2", "reason": "Disowned",
            "response_ref": "local-session:session3#turn1", "genuine_confirmed": True,
            "timestamp": "2026-10-03T12:00:00Z",
        }]
        self.assertTrue(self.report()["pending_checks"][0]["reopened_by_void"])
        original = deepcopy(self.ledger["pending_checks"][0])
        self.ledger = coverage.merge_batch(self.ledger, {
            "attempts": [attempt("a3", session_id="session3", timestamp="2026-10-04T12:00:00Z")],
            "pending_checks": [dict(original, evidence_attempt_id="a3")],
        })
        self.assertEqual(self.report()["pending_checks"], [])

    def test_malformed_unit_is_rejected_before_attempt_or_event_cross_references(self):
        event = {"id": "e1", "unit_id": "u1", "status": "completed",
                 "timestamp": "2026-10-01T11:30:00Z", "reason": "Closed"}
        for field, value in (("session_id", None), ("subskill_ids", None), ("subskill_ids", 5)):
            for linked in ("attempt", "event"):
                with self.subTest(field=field, value=value, linked=linked):
                    broken = unit(lifecycle="started")
                    if value is None:
                        del broken[field]
                    else:
                        broken[field] = value
                    self.ledger = coverage.empty_ledger(self.catalog)
                    self.ledger["study_units"] = [broken]
                    if linked == "attempt":
                        self.ledger["attempts"] = [attempt(unit_id="u1")]
                    else:
                        self.ledger["unit_events"] = [event]
                    with self.assertRaises(coverage.CoverageError):
                        self.report()

    def test_disowning_confirmation_is_a_separate_unshared_turn(self):
        def void(vid, aid, ref):
            return {"id": vid, "attempt_id": aid, "reason": "Disowned", "response_ref": ref,
                    "genuine_confirmed": True, "timestamp": "2026-10-03T12:00:00Z"}

        self.ledger["attempts"] = [
            attempt(), attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z"),
        ]
        for refs, message in (
            ((attempt()["response_ref"],), "separate genuine turn"),
            ((attempt("a2")["response_ref"],), "separate genuine turn"),
            (("local-session:session3#turn1", "local-session:session3#turn1"), "reused by multiple voids"),
        ):
            with self.subTest(refs=refs):
                self.ledger["voided_attempts"] = [
                    void(f"v{index}", aid, ref)
                    for index, (aid, ref) in enumerate(zip(("a1", "a2"), refs))
                ]
                with self.assertRaisesRegex(coverage.CoverageError, message):
                    self.report()
        self.ledger["voided_attempts"] = [void("v1", "a1", "local-session:session3#turn1")]
        self.ledger["attempts"].append(attempt(
            "a3", session_id="session3", timestamp="2026-10-03T12:05:00Z",
            response_ref="local-session:session3#turn1",
        ))
        with self.assertRaisesRegex(coverage.CoverageError, "separate genuine turn"):
            self.report()

    def test_staleness_counts_days_in_the_study_timezone(self):
        self.ledger["attempts"] = [attempt(timestamp="2026-09-25T02:00:00Z")]
        # 02:00 UTC on 25 Sep is still 24 Sep in UTC-05:00, which crosses the 10-day threshold.
        self.assertEqual(self.report()["subskills"]["stale"], 0)
        self.ledger["study_timezone"] = "UTC-05:00"
        self.assertEqual(self.report()["subskills"]["stale"], 1)

    def test_atomic_write_stale_hash_lock_and_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.json"
            coverage.atomic_write(path, self.ledger, None)
            old_bytes, old_hash = path.read_bytes(), coverage.digest(path)
            with self.assertRaisesRegex(coverage.CoverageError, "changed"):
                coverage.atomic_write(path, {}, "wrong")
            self.assertEqual(path.read_bytes(), old_bytes)
            lock = path.with_suffix(".json.lock")
            lock.write_text("active", encoding="utf-8")
            with self.assertRaisesRegex(coverage.CoverageError, "lock exists"):
                coverage.atomic_write(path, {}, old_hash)
            self.assertTrue(lock.exists())
            lock.unlink()
            with patch.object(coverage.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    coverage.atomic_write(path, {}, old_hash)
            self.assertEqual(path.read_bytes(), old_bytes)
            self.assertFalse(lock.exists())
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_atomic_write_returns_the_committed_hash_before_releasing_its_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.json"
            original_digest = coverage.digest
            observed = []

            def checked_digest(candidate):
                self.assertTrue(path.with_suffix(".json.lock").exists())
                value = original_digest(candidate)
                observed.append(value)
                return value

            with patch.object(coverage, "digest", side_effect=checked_digest):
                committed = coverage.atomic_write(path, self.ledger, None)
            self.assertEqual(committed, original_digest(path))
            self.assertEqual(observed[-1], committed)
            self.assertFalse(path.with_suffix(".json.lock").exists())

    def test_cli_init_record_audit_and_reject_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            exam = Path(tmp) / "exams" / "test-100"
            exam.mkdir(parents=True)
            (exam / "blueprint.json").write_text(json.dumps(self.catalog), encoding="utf-8")
            common = ["--root", tmp, "--exam", "test-100", "--as-of", "2026-10-04"]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(coverage.main(["audit", *common, "--json"]), 0)
            self.assertFalse(json.loads(out.getvalue())["ledger_exists"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(coverage.main(["init", *common]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(coverage.main(["init", *common]), 2)
            ledger_path = exam / "assets" / "coverage.json"
            batch_path = Path(tmp) / "batch.json"
            batch_path.write_text(json.dumps({"attempts": [attempt()]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(coverage.main([
                    "record", *common, "--input", str(batch_path),
                    "--expected-sha256", coverage.digest(ledger_path),
                ]), 0)
            self.assertEqual(len(coverage.read_json(ledger_path)["attempts"]), 1)

    def test_duplicate_scored_response_rejected_across_skills_sessions_and_voids(self):
        original = attempt()
        for sid, session_id, voided in (
            ("s1", "session1", False), ("s2", "session2", False), ("s2", "session2", True),
        ):
            with self.subTest(sid=sid, session=session_id, voided=voided):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.ledger["attempts"] = [
                    original, attempt("a2", sid, session_id=session_id,
                                      response_ref=original["response_ref"],
                                      timestamp="2026-10-03T12:00:00Z"),
                ]
                if voided:
                    self.ledger["voided_attempts"] = [{
                        "id": "v1", "attempt_id": "a1", "reason": "Genuine correction",
                        "response_ref": "fixture:correction", "genuine_confirmed": True,
                        "timestamp": "2026-10-02T12:00:00Z",
                    }]
                with self.assertRaisesRegex(coverage.CoverageError, "Scored response reference reused"):
                    self.report()

    def test_single_response_multi_skill_and_identical_retry_remain_valid(self):
        batch = {"attempts": [attempt(subskill_ids=["s1", "s2"])]}
        self.ledger = coverage.merge_batch(self.ledger, batch)
        self.assertEqual(coverage.merge_batch(self.ledger, batch), self.ledger)
        result = self.report()
        self.assertEqual(result["subskills"]["assessed"], 2)
        self.assertEqual(len(self.ledger["attempts"]), 1)

    def test_unscored_teaching_may_share_a_reference(self):
        self.ledger["attempts"] = [
            attempt("a1", context="teaching", result="unscored", response_ref="fixture:lesson"),
            attempt("a2", "s2", context="teaching", result="unscored", response_ref="fixture:lesson"),
        ]
        result = self.report()
        self.assertEqual(result["subskills"]["introduced"], 2)
        self.assertEqual(result["subskills"]["assessed"], 0)

    def test_reporting_date_uses_utc_and_preserves_historical_dates(self):
        now = datetime(2026, 10, 5, 0, 30, tzinfo=timezone.utc)
        with patch.object(coverage, "datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            self.assertEqual(coverage.audit_date("2026-10-04"), date(2026, 10, 4))
            self.assertEqual(coverage.audit_date("2026-10-05"), date(2026, 10, 5))
            with self.assertRaisesRegex(coverage.CoverageError, "today's UTC date"):
                coverage.audit_date("2026-10-06")
            with self.assertRaisesRegex(coverage.CoverageError, "invalid ISO date"):
                coverage.audit_date("not-a-date")
            coverage.not_future(coverage.timestamp("2026-10-04T19:00:00-05:00"),
                                date(2026, 10, 5), "Answer")
            for reporting_date in (date(2026, 10, 5), date(2099, 1, 1)):
                with self.subTest(reporting_date=reporting_date):
                    with self.assertRaisesRegex(coverage.CoverageError, "real clock"):
                        coverage.not_future(coverage.timestamp("2026-10-04T20:00:00-05:00"),
                                            reporting_date, "Answer")

    def test_cli_future_date_rejected_before_reading_or_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            for command in ("audit", "init", "record"):
                with self.subTest(command=command):
                    out, err = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        code = coverage.main([
                            command, "--root", tmp, "--exam", "test-100", "--as-of", "9999-12-31",
                        ])
                    self.assertEqual(code, 2)
                    self.assertIn("as-of cannot be later", err.getvalue())
                    self.assertEqual(out.getvalue(), "")
                    self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_cli_rejects_duplicate_and_future_records_without_modifying_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            exam = Path(tmp) / "exams" / "test-100"
            (exam / "assets").mkdir(parents=True)
            (exam / "blueprint.json").write_text(json.dumps(self.catalog), encoding="utf-8")
            path = exam / "assets" / "coverage.json"
            self.ledger["attempts"] = [attempt()]
            path.write_text(json.dumps(self.ledger), encoding="utf-8")
            before = path.read_bytes()
            batch_path = Path(tmp) / "batch.json"
            future = {
                "study_units": [unit(lifecycle="started", timestamp="2099-01-01T10:00:00Z")],
                "attempts": [attempt("future", unit_id="u1", timestamp="2099-01-01T11:00:00Z")],
                "unit_events": [{
                    "id": "done", "unit_id": "u1", "status": "completed",
                    "timestamp": "2099-01-01T12:00:00Z", "reason": "Fixture",
                }],
                "voided_attempts": [{
                    "id": "void", "attempt_id": "future", "reason": "Fixture",
                    "response_ref": "fixture:correction", "genuine_confirmed": True,
                    "timestamp": "2099-01-02T12:00:00Z",
                }],
            }
            for batch, as_of, error in (
                ({"attempts": [attempt("a2", "s2", response_ref=attempt()["response_ref"])]},
                 "2026-10-04", "Scored response reference reused"),
                (future, "2099-01-03", "as-of cannot be later"),
                (future, "2026-10-04", "cannot precede recorded evidence"),
            ):
                with self.subTest(as_of=as_of, error=error):
                    batch_path.write_text(json.dumps(batch), encoding="utf-8")
                    out, err = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        code = coverage.main([
                            "record", "--root", tmp, "--exam", "test-100", "--as-of", as_of,
                            "--input", str(batch_path), "--expected-sha256", coverage.digest(path),
                        ])
                    self.assertEqual(code, 2)
                    self.assertIn(error, err.getvalue())
                    self.assertEqual(out.getvalue(), "")
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(list(path.parent.iterdir()), [path])
            batch_path.write_text(json.dumps({"attempts": [attempt()]}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(coverage.main([
                    "record", "--root", tmp, "--exam", "test-100", "--as-of", "2026-10-04",
                    "--input", str(batch_path), "--expected-sha256", coverage.digest(path),
                ]), 0)
            self.assertEqual(coverage.read_json(path), self.ledger)


if __name__ == "__main__":
    unittest.main()
