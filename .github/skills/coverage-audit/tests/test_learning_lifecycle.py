from copy import deepcopy
from datetime import datetime, timedelta, timezone
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from test_coverage import AS_OF, attempt, catalog, coverage, unit


def event(eid, status, time, uid="u1"):
    return {
        "id": eid, "unit_id": uid, "status": status, "timestamp": time,
        "reason": "Actual activity lifecycle fixture",
    }


class LearningLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog()
        self.ledger = coverage.empty_ledger(self.catalog)

    def report(self):
        return coverage.report(self.catalog, self.ledger, AS_OF)

    def test_correct_letter_only_repeat_preserves_prior_demonstration(self):
        self.ledger["attempts"] = [
            attempt(), attempt("a2", reasoning_demonstrated=False, novel=False,
                               timestamp="2026-10-02T12:00:00Z"),
        ]
        self.assertEqual(self.report()["subskills"]["demonstrated"], 1)
        self.ledger["attempts"].append(
            attempt("a3", result="partial", timestamp="2026-10-03T12:00:00Z"),
        )
        self.assertEqual(self.report()["subskills"]["demonstrated"], 0)

    def test_session_rename_does_not_establish_delayed_retention(self):
        self.ledger["study_timezone"] = "UTC-05:00"
        self.ledger["attempts"] = [
            attempt(), attempt("a2", session_id="reopened", retention_source_id="a1",
                               context="delayed_transfer", timestamp="2026-10-01T12:00:01Z"),
        ]
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 0)
        self.ledger["attempts"][1]["timestamp"] = "2026-10-02T12:00:00Z"
        self.ledger["attempts"][1]["session_id"] = "session1"
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 1)

    def test_calendar_boundaries_use_recorded_offset_not_timestamp_spelling(self):
        self.ledger["study_timezone"] = "UTC-05:00"
        self.ledger["attempts"] = [
            attempt(timestamp="2026-10-01T23:30:00-05:00"),
            attempt("a2", context="delayed_transfer", retention_source_id="a1",
                    timestamp="2026-10-02T04:45:00Z"),
        ]
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 0)
        self.ledger["attempts"][1]["timestamp"] = "2026-10-02T00:15:00-05:00"
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 1)

    def test_voided_source_invalidates_retention_but_not_real_transfer_answer(self):
        self.ledger["study_timezone"] = "UTC-05:00"
        self.ledger["attempts"] = [
            attempt(), attempt("a2", context="delayed_transfer", retention_source_id="a1",
                               timestamp="2026-10-02T12:00:00Z"),
        ]
        self.ledger["voided_attempts"] = [{
            "id": "v1", "attempt_id": "a1", "reason": "Source response was not genuine",
            "genuine_confirmed": True, "response_ref": "session:correction#turn1",
            "timestamp": "2026-10-03T12:00:00Z",
        }]
        result = self.report()
        self.assertEqual(result["subskills"]["delayed_transfer"], 0)
        self.assertEqual(result["subskills"]["demonstrated"], 1)

    def test_timezone_is_stable_and_unknown_history_does_not_gain_credit(self):
        self.ledger = coverage.merge_batch(self.ledger, {"study_timezone": "UTC-05:00"})
        with self.assertRaisesRegex(coverage.CoverageError, "fixed"):
            coverage.merge_batch(self.ledger, {"study_timezone": "UTC+01:00"})
        for value in ("America/Bogota", "UTC+15:00", "UTC-05:99", "UTC+14:01"):
            with self.subTest(value=value):
                with self.assertRaises(coverage.CoverageError):
                    coverage.study_timezone(value)
        self.ledger["attempts"] = [
            attempt(), attempt("a2", context="delayed_transfer",
                               timestamp="2026-10-03T12:00:00Z"),
        ]
        self.assertEqual(self.report()["subskills"]["delayed_transfer"], 0)

    def test_started_interrupted_resumed_and_completed_are_not_double_counted(self):
        self.ledger["study_units"] = [unit(lifecycle="started")]
        self.assertEqual(self.report()["next_action"], "resume_unfinished")
        self.assertEqual(self.report()["completed_normal_units"], 0)
        self.ledger["unit_events"] = [
            event("e1", "interrupted", "2026-10-01T11:30:00Z"),
            event("e2", "started", "2026-10-02T11:00:00Z"),
        ]
        self.ledger["attempts"] = [
            attempt(unit_id="u1", timestamp="2026-10-02T11:05:00Z"),
        ]
        self.ledger["unit_events"].append(event("e3", "completed", "2026-10-02T11:06:00Z"))
        result = self.report()
        self.assertEqual(result["normal_units"], 1)
        self.assertEqual(result["completed_normal_units"], 1)
        self.assertEqual(result["unfinished_units"], [])
        self.assertEqual(result["next_action"], "allocate")
        self.assertEqual(result["next_allocation"], "coverage")

    def test_unfinished_normal_activity_requires_resume_or_explicit_deferral(self):
        self.ledger["study_units"] = [
            unit(lifecycle="started"),
            unit("u2", lifecycle="started", subskill_ids=["s2"],
                 timestamp="2026-10-02T11:00:00Z"),
        ]
        with self.assertRaisesRegex(coverage.CoverageError, "Unfinished activity"):
            self.report()
        self.ledger["unit_events"] = [event("e1", "deferred", "2026-10-01T11:30:00Z")]
        self.assertEqual(len(self.report()["unfinished_units"]), 2)

    def test_simultaneous_timestamps_do_not_bypass_unfinished_work(self):
        self.ledger["study_units"] = [
            unit(lifecycle="started"),
            unit("u2", lifecycle="started", subskill_ids=["s2"]),
        ]
        with self.assertRaisesRegex(coverage.CoverageError, "Unfinished activity"):
            self.report()

    def test_completed_cycle_preserves_exact_allocation_across_sessions(self):
        start = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)
        for index, kind in enumerate(coverage.CYCLE):
            uid = f"unit-{index}"
            sid = "s2" if index == 1 else "s1"
            moment = start + timedelta(minutes=index * 5)
            self.ledger["study_units"].append(unit(
                uid, kind, lifecycle="started", subskill_ids=[sid],
                session_id=f"session-{index // 4}", timestamp=moment.isoformat(),
            ))
            self.ledger["attempts"].append(attempt(
                f"teaching-{index}", sid, unit_id=uid, result="unscored",
                session_id=f"session-{index // 4}",
                context="teaching", assistance="unknown", genuine_confirmed=False,
                reasoning_demonstrated=False, novel=False,
                timestamp=(moment + timedelta(minutes=1)).isoformat(),
            ))
            self.ledger["unit_events"].append(event(
                f"completed-{index}", "completed",
                (moment + timedelta(minutes=2)).isoformat(), uid,
            ))
        result = self.report()
        self.assertEqual(result["actual_allocation"], {"coverage": 12, "remediation": 5, "retention": 3})
        self.assertEqual(result["completed_allocation"], result["actual_allocation"])
        self.assertEqual(result["subskills"]["assessed"], 0)
        self.assertEqual(result["next_action"], "allocate")

    def test_legacy_completion_is_unknown_and_not_retroactively_invented(self):
        self.ledger["study_units"] = [unit()]
        result = self.report()
        self.assertEqual(result["completion_unknown_units"], ["u1"])
        self.assertEqual(result["completed_normal_units"], 0)
        with self.assertRaisesRegex(coverage.CoverageError, "explicitly start"):
            coverage.merge_batch(coverage.empty_ledger(self.catalog), {"study_units": [unit()]})

    def test_completion_needs_evidence_for_all_targeted_subskills(self):
        self.ledger["study_units"] = [unit(lifecycle="started", subskill_ids=["s1", "s2"])]
        self.ledger["attempts"] = [attempt(unit_id="u1")]
        self.ledger["unit_events"] = [event("e1", "completed", "2026-10-01T12:05:00Z")]
        with self.assertRaisesRegex(coverage.CoverageError, "each target subskill"):
            self.report()
        self.ledger["attempts"].append(attempt(
            "teaching-s2", "s2", unit_id="u1", result="unscored", context="teaching",
            reasoning_demonstrated=False, genuine_confirmed=False, assistance="unknown",
        ))
        result = self.report()
        self.assertEqual(result["completed_normal_units"], 1)
        self.assertEqual(result["objectives_fully_assessed"], 0)

    def test_duplicate_lifecycle_event_is_idempotent(self):
        self.ledger["study_units"] = [unit(lifecycle="started")]
        batch = {"unit_events": [event("e1", "interrupted", "2026-10-01T12:00:00Z")]}
        first = coverage.merge_batch(self.ledger, batch)
        self.assertEqual(coverage.merge_batch(first, batch), first)
        modified = deepcopy(batch)
        modified["unit_events"][0]["status"] = "deferred"
        with self.assertRaisesRegex(coverage.CoverageError, "Conflicting"):
            coverage.merge_batch(first, modified)

    def test_completed_activity_cannot_absorb_later_answers(self):
        self.ledger["study_units"] = [unit(lifecycle="started")]
        self.ledger["attempts"] = [attempt(unit_id="u1")]
        self.ledger["unit_events"] = [event("e1", "completed", "2026-10-01T12:05:00Z")]
        self.ledger["attempts"].append(
            attempt("a2", unit_id="u1", timestamp="2026-10-02T12:00:00Z"),
        )
        with self.assertRaisesRegex(coverage.CoverageError, "active activity"):
            self.report()

    def completed_activity(self, subskills=None):
        self.ledger["study_units"] = [unit(lifecycle="started", subskill_ids=subskills or ["s1"])]
        self.ledger["attempts"] = [attempt(unit_id="u1")]
        self.ledger["unit_events"] = [event("done", "completed", "2026-10-01T12:05:00Z")]

    def void_completion_answer(self, kind="disowned_answer", aid="a1", vid="v1"):
        reference = (
            next(row["response_ref"] for row in self.ledger["attempts"] if row["id"] == aid)
            if kind == "invalid_item" else f"fixture:correction-{vid}"
        )
        self.ledger["voided_attempts"].append({
            "id": vid, "attempt_id": aid, "reason_kind": kind, "reason": "Fixture correction",
            "genuine_confirmed": True, "response_ref": reference,
            "source_ref": "https://learn.microsoft.com/fixture",
            "timestamp": "2026-10-02T12:00:00Z",
        })

    def test_voided_completion_reopens_debt_without_rewriting_history(self):
        for kind in ("disowned_answer", "invalid_item"):
            with self.subTest(kind=kind):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.completed_activity()
                self.void_completion_answer(kind)
                before = deepcopy(self.ledger)
                result = self.report()
                self.assertEqual(self.ledger, before)
                self.assertEqual(result["completed_normal_units"], 0)
                self.assertEqual(result["completed_allocation"], {})
                self.assertEqual(result["normal_units"], 1)
                self.assertEqual(result["next_action"], "resume_unfinished")
                self.assertEqual(result["unfinished_units"][0]["status"], "interrupted")

    def test_other_surviving_evidence_preserves_completed_activity(self):
        for result, context in (("correct", "cold"), ("unscored", "teaching")):
            with self.subTest(context=context):
                self.ledger = coverage.empty_ledger(self.catalog)
                self.completed_activity()
                self.ledger["attempts"].append(attempt(
                    "survivor", unit_id="u1", result=result, context=context,
                    timestamp="2026-10-01T12:01:00Z",
                ))
                self.void_completion_answer()
                self.assertEqual(self.report()["completed_normal_units"], 1)
                self.assertEqual(self.report()["unfinished_units"], [])
                with self.assertRaisesRegex(coverage.CoverageError, "lifecycle transition"):
                    updated = coverage.merge_batch(self.ledger, {"unit_events": [
                        event("unneeded-resume", "started", "2026-10-03T12:00:00Z"),
                    ]})
                    coverage.report(self.catalog, updated, AS_OF)

    def test_losing_one_of_multiple_required_subskills_reopens_completion(self):
        self.completed_activity(["s1", "s2"])
        self.ledger["attempts"].append(attempt(
            "a2", "s2", unit_id="u1", timestamp="2026-10-01T12:01:00Z",
        ))
        self.void_completion_answer(aid="a2")
        self.assertEqual(self.report()["completed_normal_units"], 0)
        self.assertEqual(self.report()["subskills"]["assessed"], 1)

    def test_reopened_activity_resumes_and_recompletes_without_extra_slot(self):
        self.completed_activity()
        self.void_completion_answer()
        batch = {
            "unit_events": [
                event("resume", "started", "2026-10-03T11:00:00Z"),
                event("done-again", "completed", "2026-10-03T12:05:00Z"),
            ],
            "attempts": [attempt("a2", unit_id="u1", timestamp="2026-10-03T12:00:00Z")],
        }
        self.ledger = coverage.merge_batch(self.ledger, batch)
        self.assertEqual(coverage.merge_batch(self.ledger, batch), self.ledger)
        result = self.report()
        self.assertEqual(result["normal_units"], 1)
        self.assertEqual(result["completed_normal_units"], 1)
        self.assertEqual(result["unfinished_units"], [])
        self.assertEqual(len(self.ledger["unit_events"]), 3)

    def test_reopened_activity_requires_resume_before_new_answer(self):
        self.completed_activity()
        self.void_completion_answer()
        self.ledger["attempts"].append(attempt(
            "a2", unit_id="u1", timestamp="2026-10-03T12:00:00Z",
        ))
        with self.assertRaisesRegex(coverage.CoverageError, "active activity"):
            self.report()

    def test_record_persists_void_then_resume_and_recompletion_atomically(self):
        self.completed_activity()
        before_void = deepcopy(self.ledger)
        self.void_completion_answer()
        void = self.ledger["voided_attempts"][0]
        with tempfile.TemporaryDirectory() as tmp:
            exam = Path(tmp) / "exams" / "test-100"
            exam.mkdir(parents=True)
            (exam / "blueprint.json").write_text(json.dumps(self.catalog), encoding="utf-8")
            path = exam / "assets" / "coverage.json"
            coverage.atomic_write(path, before_void, None)
            batch_path = Path(tmp) / "batch.json"
            batches = [
                {"voided_attempts": [void]},
                {
                    "unit_events": [
                        event("resume", "started", "2026-10-03T11:00:00Z"),
                        event("done-again", "completed", "2026-10-03T12:05:00Z"),
                    ],
                    "attempts": [attempt("a2", unit_id="u1", timestamp="2026-10-03T12:00:00Z")],
                },
            ]
            for index, batch in enumerate(batches):
                batch_path.write_text(json.dumps(batch), encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = coverage.main([
                        "record", "--root", tmp, "--exam", "test-100", "--as-of", "2026-10-04",
                        "--input", str(batch_path), "--expected-sha256", coverage.digest(path), "--json",
                    ])
                self.assertEqual(code, 0, err.getvalue())
                self.assertEqual(json.loads(out.getvalue())["completed_normal_units"], index)
            stored = coverage.read_json(path)
            self.assertEqual(len(stored["study_units"]), 1)
            self.assertEqual(stored["attempts"][0], before_void["attempts"][0])
            self.assertEqual(stored["unit_events"][0], before_void["unit_events"][0])

    def test_void_does_not_retroactively_block_old_units_but_blocks_new_ones(self):
        self.completed_activity()
        self.ledger["study_units"].append(unit(
            "u2", subskill_ids=["s2"], lifecycle="started", timestamp="2026-10-01T13:00:00Z",
        ))
        self.ledger["unit_events"].append(event(
            "defer-u2", "deferred", "2026-10-01T13:10:00Z", uid="u2",
        ))
        self.void_completion_answer()
        self.report()
        self.ledger["study_units"].append(unit(
            "u3", kind="remediation", lifecycle="started", timestamp="2026-10-03T12:00:00Z",
        ))
        with self.assertRaisesRegex(coverage.CoverageError, "Unfinished activity u1"):
            self.report()
        self.ledger["unit_events"].append(event("defer-u1", "deferred", "2026-10-02T13:00:00Z"))
        result = self.report()
        self.assertEqual(result["completed_normal_units"], 0)
        self.assertEqual(coverage.unit_lifecycles(self.ledger)["u1"], "deferred")

    def test_ambiguous_item_is_invalidated_without_learner_penalty(self):
        self.ledger["attempts"] = [attempt(result="incorrect")]
        self.ledger["voided_attempts"] = [{
            "id": "v1", "attempt_id": "a1", "reason_kind": "invalid_item",
            "reason": "Two options meet the stated constraints",
            "genuine_confirmed": True, "response_ref": self.ledger["attempts"][0]["response_ref"],
            "source_ref": "https://learn.microsoft.com/verified-behavior",
            "timestamp": "2026-10-03T12:00:00Z",
        }]
        self.assertEqual(self.report()["subskills"]["assessed"], 0)
        del self.ledger["voided_attempts"][0]["source_ref"]
        with self.assertRaisesRegex(coverage.CoverageError, "defect evidence"):
            self.report()

    def test_record_rejects_same_day_retention_before_persisting(self):
        with tempfile.TemporaryDirectory() as tmp:
            exam = Path(tmp) / "exams" / "test-100"
            exam.mkdir(parents=True)
            (exam / "blueprint.json").write_text(json.dumps(self.catalog), encoding="utf-8")
            self.ledger["study_timezone"] = "UTC-05:00"
            self.ledger["attempts"] = [attempt()]
            path = exam / "assets" / "coverage.json"
            coverage.atomic_write(path, self.ledger, None)
            batch = Path(tmp) / "batch.json"
            batch.write_text(json.dumps({"attempts": [attempt(
                "a2", context="delayed_transfer", retention_source_id="a1",
                timestamp="2026-10-01T12:00:01Z",
            )]}), encoding="utf-8")
            before = path.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                code = coverage.main([
                    "record", "--root", tmp, "--exam", "test-100", "--as-of", "2026-10-04",
                    "--input", str(batch), "--expected-sha256", coverage.digest(path),
                ])
            self.assertEqual(code, 2)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
