"""Synthetic CLI journeys; never use learner records or live answers as fixtures."""

import contextlib
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_coverage import attempt, catalog
from test_session import answer, metadata, positioned_question, session


coverage = session.coverage
AS_OF = "2026-10-04"


class WorkflowFixture(unittest.TestCase):
    EXAM = "test-100"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "exams" / self.EXAM
        self.base.mkdir(parents=True)
        self.ledger_path = self.base / "assets" / "coverage.json"
        self.checkpoint_path = self.base / "assets" / "session.json"
        self.input_path = self.root / "input.json"
        self.catalog = catalog()
        self.catalog["exam"] = self.EXAM
        template = self.catalog["domains"][0]
        self.catalog["domains"] = []
        for index, (low, high) in enumerate(((25, 30), (20, 25), (15, 20), (30, 35)), 1):
            domain = deepcopy(template)
            domain.update(id=f"d{index}", weight_min=low, weight_max=high)
            domain["objectives"][0].update(
                id=f"o{index}", subskills=[{"id": f"s{index}", "title": "Fixture skill", "derived": True}],
            )
            self.catalog["domains"].append(domain)
        self.write(self.base / "blueprint.json", self.catalog)
        self.invoke(coverage, "init")

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def invoke(self, helper, command, *args, error=None):
        destination = self.ledger_path if helper is coverage else self.checkpoint_path
        before = destination.read_bytes() if destination.exists() else None
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = helper.main([
                command, "--root", str(self.root), "--exam", self.EXAM,
                "--as-of", AS_OF, "--json", *args,
            ])
        if error is not None:
            self.assertEqual(code, 2, out.getvalue())
            self.assertIn(error, err.getvalue())
            self.assertEqual(destination.read_bytes() if destination.exists() else None, before)
            return None
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(err.getvalue(), "")
        result = json.loads(out.getvalue())
        if helper is session:
            for private in ("private_key", "private_rationale", "private_metadata",
                            "private_grading_criteria", "answer_position_deck", "FIXTURE PRIVATE"):
                self.assertNotIn(private, out.getvalue())
        return result

    def record(self, batch, **kwargs):
        self.write(self.input_path, batch)
        return self.invoke(
            coverage, "record", "--input", str(self.input_path),
            "--expected-sha256", coverage.digest(self.ledger_path), **kwargs,
        )

    def save(self, **kwargs):
        self.write(self.input_path, self.state)
        return self.invoke(
            session, "checkpoint", "--input", str(self.input_path),
            "--expected-sha256", coverage.digest(self.checkpoint_path) or "missing", **kwargs,
        )

    def resume(self, fresh_process=False):
        before = self.checkpoint_path.read_bytes()
        if fresh_process:
            run = subprocess.run(
                [sys.executable, "-B", session.__file__, "resume", "--root", str(self.root),
                 "--exam", self.EXAM, "--as-of", AS_OF, "--json"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertNotIn("FIXTURE PRIVATE", run.stdout)
            self.assertNotIn("answer_position_deck", run.stdout)
            result = json.loads(run.stdout)
        else:
            result = self.invoke(session, "resume")
        self.assertEqual(self.checkpoint_path.read_bytes(), before)
        return result

    def start(self, mock=False, subskill_ids=None):
        self.unit = {
            "id": "u1", "session_id": "session1", "timestamp": "2026-10-01T10:00:00Z",
            "subskill_ids": subskill_ids if subskill_ids is not None else ["s1", "s2", "s3", "s4"],
            "kind": "coverage",
            "mode": "mock" if mock else "normal", "lifecycle": "started",
        }
        if mock:
            self.unit["reason"] = "Synthetic full mock"
        self.record({"study_units": [self.unit]})
        self.state = {
            "schema_version": 1, "exam": self.EXAM, "blueprint_revision": "v1",
            "session_id": "session1", "mode": "mock" if mock else "quiz",
            "phase": "mixed_quiz", "paused": False, "current_unit_id": "u1",
            "allocation_category": "coverage", "question_index": 0, "items": [],
            "answer_position_deck": {
                "kind": "planned" if mock else "open_ended",
                "positions": list("BACDBACDBA" if mock else "BACD" * 3), "cursor": 0,
            },
            "ledger_sha256": coverage.digest(self.ledger_path), "applied_attempt_ids": [],
            "applied_void_ids": [], "pending_check_ids": [], "next_action": "resume_phase",
        }
        self.save()

    def prepare(self, index, domain, position=None):
        position = index if position is None else position
        item = positioned_question(
            index, self.state["answer_position_deck"]["positions"][position], self.state["mode"] == "mock",
        )
        item["private_metadata"] = metadata()
        item["private_metadata"].update(
            source_id=f"original:workflow-{index}", domain_id=f"d{domain}",
            topic=f"Fixture domain {domain}", subskill_ids=[f"s{domain}"],
        )
        item["private_rationale"] = "FIXTURE PRIVATE verified per-option rationale"
        item["unit_id"] = self.state["current_unit_id"]
        return item

    def respond(self, index, aid=None, timestamp=None):
        item = self.state["items"][index]
        item["attempt_id"] = aid or f"a{index + 1}"
        item["response"] = {
            "response_ref": f"synthetic-turn:{item['attempt_id']}",
            "timestamp": timestamp or f"2026-10-01T12:{index:02d}:00Z",
            "genuine_confirmed": True, "text": "FIXTURE PRIVATE scripted response",
            "flags": ["flagged_for_review"] if index == 3 else [],
        }
        self.state["next_action"] = (
            "grade_deferred" if index == len(self.state["items"]) - 1 else "continue_mock"
        ) if self.state["mode"] == "mock" else "grade_recorded"
        self.save()
        return attempt(
            item["attempt_id"], item["private_metadata"]["subskill_ids"][0],
            session_id=self.state["session_id"], unit_id=self.state["current_unit_id"],
            timestamp=item["response"]["timestamp"],
            response_ref=item["response"]["response_ref"],
            context="mock" if self.state["mode"] == "mock" else "cold",
            result="incorrect" if index == 3 else "correct",
        )

    def reconcile(self, rows):
        for item in self.state["items"]:
            if item["attempt_id"] in {row["id"] for row in rows}:
                item["grading"] = "applied"
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.state["applied_attempt_ids"] += [row["id"] for row in rows]
        self.state["next_action"] = "review_recorded"
        self.save()


class AI500SourceWorkflowTests(WorkflowFixture):
    EXAM = "ai-500"

    def legacy_source_checkpoint(self, answered=False, committed=False):
        self.start(subskill_ids=["s1"])
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        row = self.respond(0) if answered else None
        if committed:
            self.record({"attempts": [row]})
            self.reconcile([row])
        self.state["items"][0]["private_metadata"]["verification"]["url"] = (
            "https://huggingface.co/docs/datasets/"
        )
        # Emulate an archived checkpoint accepted by the previous host-only rule.
        session.validate(
            self.state, self.catalog, coverage.read_json(self.ledger_path),
            coverage.audit_date(AS_OF), allow_legacy_sources=True,
        )
        self.write(self.checkpoint_path, self.state)
        return row

    def test_legacy_source_resume_is_read_only_and_blocks_new_answer_or_progress(self):
        self.legacy_source_checkpoint()
        original = deepcopy(self.state)
        resumed = self.resume(fresh_process=True)
        self.assertEqual(resumed["next_action"], "replace_unverified_item")
        self.assertEqual(resumed["source_recovery_question_indices"], [0])
        self.assertEqual(resumed["source_recovery_item_ids"], ["q1"])
        self.assertNotIn("pending_question", resumed)
        self.state["paused"] = True
        self.save()
        self.assertEqual(self.resume()["next_action"], "replace_unverified_item")
        self.state["paused"] = False
        self.save()
        self.state["items"][0].update(
            response={"response_ref": "synthetic:blocked", "timestamp": "2026-10-02T12:00:00Z",
                      "genuine_confirmed": True, "text": "Synthetic response", "flags": []},
            attempt_id="blocked",
        )
        self.state["next_action"] = "grade_recorded"
        self.save(error="official Transformers documentation")
        self.state = deepcopy(original)
        self.state["phase"] = "review"
        self.save(error="Replace legacy source verification")
        self.state = deepcopy(original)
        self.state["items"][0]["private_metadata"]["verification"]["url"] = (
            "https://huggingface.co/docs/transformers/"
        )
        self.save(error="Locked question private metadata")

    def test_legacy_source_journal_replacement_preserves_history_and_resumes_grading(self):
        for answered in (False, True):
            with self.subTest(answered=answered):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.legacy_source_checkpoint(answered=answered)
                original = deepcopy(self.state["items"][0])
                replacement = deepcopy(original)
                replacement.update(
                    id="q1-verified", stem="Corrected synthetic verified constraint?",
                    response=None, attempt_id=None, grading="pending", review="pending",
                    history=[{"item": original, "invalidation": {
                        "id": "source-defect", "reason_kind": "invalid_item",
                        "reason": "Prior verification did not use approved framework documentation",
                        "source_ref": "https://huggingface.co/docs/transformers/",
                        "timestamp": "2026-10-02T10:00:00Z",
                    }}],
                )
                self.state.update(items=[replacement], next_action="reask_pending")
                self.save(error="official Transformers documentation")
                replacement["private_metadata"]["verification"]["url"] = (
                    "https://huggingface.co/docs/transformers/"
                )
                self.save()
                resumed = self.resume(fresh_process=True)
                self.assertEqual(resumed["next_action"], "reask_pending")
                self.assertEqual(resumed["pending_question"]["id"], "q1-verified")
                self.assertEqual(
                    coverage.read_json(self.checkpoint_path)["items"][0]["history"][0]["item"],
                    original,
                )
                row = self.respond(0, aid="verified", timestamp="2026-10-03T12:00:00Z")
                self.record({"attempts": [row]})
                self.reconcile([row])
                self.assertEqual(self.resume()["next_action"], "review_recorded")

    def test_legacy_source_ledger_replacement_requires_void_and_keeps_original_score(self):
        row = self.legacy_source_checkpoint(answered=True, committed=True)
        original = deepcopy(self.state["items"][0])
        replacement = deepcopy(original)
        replacement.update(
            id="q1-verified", stem="Corrected synthetic verified constraint?",
            response=None, attempt_id=None, grading="pending", review="pending",
            history=[{"void_id": "source-defect", "item": original}],
        )
        replacement["private_metadata"]["verification"]["url"] = (
            "https://huggingface.co/docs/transformers/"
        )
        self.record({"voided_attempts": [{
            "id": "source-defect", "attempt_id": row["id"], "reason_kind": "invalid_item",
            "reason": "Prior verification did not use approved framework documentation",
            "source_ref": "https://huggingface.co/docs/transformers/",
            "response_ref": row["response_ref"], "genuine_confirmed": True,
            "timestamp": "2026-10-02T10:00:00Z",
        }]})
        self.state.update(
            items=[replacement], next_action="reask_pending", applied_void_ids=["source-defect"],
            ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "reask_pending")
        self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [row])

    def test_multiple_legacy_mock_sources_can_be_recovered_one_at_a_time(self):
        self.start(mock=True)
        self.state["items"] = [
            self.prepare(index, domain)
            for index, domain in enumerate([1, 4, 3, 1, 2, 4, 3, 2, 1, 4])
        ]
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        self.save()
        for item in self.state["items"][:3]:
            item["private_metadata"]["verification"]["url"] = (
                "https://huggingface.co/docs/datasets/"
            )
        self.write(self.checkpoint_path, self.state)
        for index in range(3):
            original = deepcopy(self.state["items"][index])
            replacement = deepcopy(original)
            replacement.update(
                id=f"verified-{index}", stem="Corrected synthetic verified constraint?",
                history=[{"item": original, "invalidation": {
                    "id": f"source-defect-{index}", "reason_kind": "invalid_item",
                    "reason": "Prior source did not qualify as approved verification",
                    "source_ref": "https://huggingface.co/docs/transformers/",
                    "timestamp": f"2026-10-02T1{index}:00:00Z",
                }}],
            )
            replacement["private_metadata"]["verification"]["url"] = (
                "https://huggingface.co/docs/transformers/"
            )
            self.state["items"][index] = replacement
            self.state.update(question_index=index, next_action="reask_pending")
            self.save()
            resumed = self.resume(fresh_process=True)
            if index < 2:
                self.assertEqual(resumed["source_recovery_question_indices"], list(range(index + 1, 3)))
            else:
                self.assertEqual(resumed["next_action"], "reask_pending")
                self.assertNotIn("source_recovery_question_indices", resumed)
            self.respond(index, timestamp=f"2026-10-03T1{index}:00:00Z")
            if index < 2:
                self.state.update(question_index=index + 1, next_action="reask_pending")
                self.save(error="Replace legacy source verification")
                self.state.update(question_index=index, next_action="continue_mock")
        self.assertEqual(self.resume()["next_action"], "continue_mock")
        stored = coverage.read_json(self.checkpoint_path)
        self.assertEqual([row["id"] for row in stored["items"][:3]],
                         ["verified-0", "verified-1", "verified-2"])
        self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [])

    def test_framework_authorities_survive_checkpoint_restart_and_complete_journey(self):
        for url in (
            "https://docs.langchain.com/oss/python/langchain/overview",
            "https://python.langchain.com/docs/",
            "https://js.langchain.com/docs/",
            "https://langchain-ai.github.io/langgraph/",
            "https://huggingface.co/docs/transformers/",
            "https://huggingface.co/docs/transformers",
            "https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/bert?language=python",
            "https://modelcontextprotocol.io/specification/",
        ):
            with self.subTest(url=url):
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.start(subskill_ids=["s1"])
                self.state["items"] = [self.prepare(0, 1)]
                self.state["items"][0]["private_metadata"]["verification"]["url"] = url
                self.state["answer_position_deck"]["cursor"] = 1
                self.state["next_action"] = "reask_pending"
                self.save()
                self.state["paused"] = True
                self.save()
                resumed = self.resume(fresh_process=True)
                self.assertEqual(resumed["next_action"], "reask_pending")
                self.assertNotIn(url, json.dumps(resumed))
                self.assertEqual(
                    coverage.read_json(self.checkpoint_path)["items"][0]["private_metadata"]
                    ["verification"]["url"], url,
                )
                self.state["paused"] = False
                self.save()
                row = self.respond(0)
                self.record({"attempts": [row]})
                self.reconcile([row])
                self.assertEqual(self.resume(fresh_process=True)["next_action"], "review_recorded")
                self.state["items"][0]["review"] = "complete"
                self.state["next_action"] = "advance_after_review"
                self.save()
                self.record({"unit_events": [{
                    "id": "done", "unit_id": "u1", "status": "completed",
                    "timestamp": "2026-10-01T13:00:00Z", "reason": "Synthetic source journey",
                }]})
                self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                self.state.update(phase="complete", next_action="session_complete")
                self.save()
                self.assertEqual(self.resume(fresh_process=True)["next_action"], "session_complete")

    def test_framework_authorities_keep_https_exact_host_and_no_credentials_rules(self):
        self.start(subskill_ids=["s1"])
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        for url in (
            "http://modelcontextprotocol.io/specification/",
            "https://modelcontextprotocol.io.evil.test/specification/",
            "https://evilmodelcontextprotocol.io/specification/",
            "https://user@modelcontextprotocol.io/specification/",
            "https://user:password@docs.langchain.com/",
            "https://docs.langchain.com@evil.test/",
            "https://community.langchain.com/",
            "https://example.com/",
        ):
            with self.subTest(url=url):
                self.state["items"][0]["private_metadata"]["verification"]["url"] = url
                self.save(error="Verification URL must be first-party HTTPS documentation")
        self.state["items"][0]["private_metadata"]["verification"]["url"] = (
            "https://modelcontextprotocol.io/specification/"
        )
        self.save()
        stored = coverage.read_json(self.checkpoint_path)
        stored["items"][0]["private_metadata"]["verification"]["url"] = "https://example.com/"
        self.write(self.checkpoint_path, stored)
        self.invoke(session, "resume", error="Verification URL must be first-party HTTPS documentation")

    def test_hugging_face_user_content_is_not_transformers_documentation(self):
        self.start(subskill_ids=["s1"])
        checkpoint_before = self.checkpoint_path.read_bytes()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        for path in (
            "/community/model-card", "/spaces/community/demo", "/datasets/community/data",
            "/", "/docs/datasets/", "/docs/transformers-community/",
            "/docs/transformers/../../spaces/community/demo",
            "/docs/transformers/%2e%2e/%2e%2e/spaces/community/demo",
            "/docs/transformers/%2e%2e%5c%2e%2e%5cspaces/community/demo",
        ):
            with self.subTest(path=path):
                self.checkpoint_path.write_bytes(checkpoint_before)
                self.state["items"][0]["private_metadata"]["verification"]["url"] = (
                    "https://huggingface.co" + path
                )
                self.save(error="Hugging Face verification must use official Transformers documentation")


class WorkflowTests(WorkflowFixture):
    def test_invalid_item_void_requires_exact_original_response_and_preserves_failed_writes(self):
        self.start(subskill_ids=["s1", "s2"])
        original = attempt("original", "s1", unit_id="u1")
        other = attempt("other", "s2", unit_id="u1", timestamp="2026-10-01T12:30:00Z")
        self.record({"attempts": [original, other]})
        void = {
            "id": "invalid-original", "attempt_id": "original", "reason_kind": "invalid_item",
            "reason": "Synthetic verified defect", "source_ref": "https://learn.microsoft.com/fixture",
            "response_ref": original["response_ref"], "genuine_confirmed": True,
            "timestamp": "2026-10-02T12:00:00Z",
        }
        baseline = self.ledger_path.read_bytes()
        for reference in ("synthetic:unrelated", other["response_ref"],
                          original["response_ref"].upper(), original["response_ref"] + " "):
            with self.subTest(reference=reference):
                self.ledger_path.write_bytes(baseline)
                self.record({"voided_attempts": [dict(void, response_ref=reference)]},
                            error="Invalid item must reference its original answer")
                self.assertEqual(self.invoke(coverage, "audit")["subskills"]["demonstrated"], 2)
        self.ledger_path.write_bytes(baseline)
        self.record({"voided_attempts": [void]})
        self.record({"voided_attempts": [void]})
        persisted = coverage.read_json(self.ledger_path)
        self.assertEqual(persisted["attempts"], [original, other])
        self.assertEqual(persisted["voided_attempts"], [void])
        self.assertEqual(self.invoke(coverage, "audit")["subskills"]["demonstrated"], 1)
        persisted["voided_attempts"][0]["response_ref"] = other["response_ref"]
        self.write(self.ledger_path, persisted)
        self.invoke(coverage, "audit", error="Invalid item must reference its original answer")
        self.invoke(session, "resume", error="Invalid item must reference its original answer")

    def test_disowned_answer_keeps_distinct_correction_turn_with_explicit_or_default_kind(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start(subskill_ids=["s1"])
                original = attempt("original", "s1", unit_id="u1")
                self.record({"attempts": [original]})
                void = {
                    "id": "disowned", "attempt_id": "original", "reason": "Synthetic disowning turn",
                    "response_ref": "synthetic:genuine-disowning-turn", "genuine_confirmed": True,
                    "timestamp": "2026-10-02T12:00:00Z",
                }
                if explicit:
                    void["reason_kind"] = "disowned_answer"
                self.record({"voided_attempts": [void]})
                self.assertNotEqual(void["response_ref"], original["response_ref"])
                self.assertEqual(self.invoke(coverage, "audit")["subskills"]["demonstrated"], 0)

    def test_cross_session_unit_links_reject_recording_without_changing_ledger(self):
        self.start(subskill_ids=["s1"])
        row = attempt("cross-session", "s1", unit_id="u1", session_id="different-session")
        self.record({"attempts": [row]}, error="Attempt belongs to another activity session")
        row["session_id"] = "session1"
        self.record({"attempts": [row]})
        self.record({"attempts": [row]})
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 1)
        legacy = attempt("unlinked-history", "s1", session_id="historic-session",
                         timestamp="2026-10-02T12:00:00Z", context="historical")
        self.record({"attempts": [legacy]})
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 2)

    def test_prepared_choice_and_free_response_scope_must_belong_to_current_activity(self):
        for free_response in (False, True):
            with self.subTest(free_response=free_response):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start(subskill_ids=["s1"])
                item = self.prepare_free_response() if free_response else self.prepare(0, 1)
                original = deepcopy(item["private_metadata"])
                item["private_metadata"].update(domain_id="d2", subskill_ids=["s2"])
                self.state.update(items=[item], next_action="reask_pending")
                self.state["answer_position_deck"]["cursor"] = 0 if free_response else 1
                self.save(error="Question targets subskills outside its activity")
                item["private_metadata"] = original
                self.save()
                self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q1")
                row = self.respond(0)
                self.record({"attempts": [row]})
                self.reconcile([row])

    def advance_to_second_activity(self):
        self.start(subskill_ids=["s1"])
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        row = self.respond(0)
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.state["items"][0]["review"] = "complete"
        self.state["next_action"] = "advance_after_review"
        self.save()
        original = deepcopy(self.state["items"][0])
        self.record({
            "unit_events": [{
                "id": "complete-u1", "unit_id": "u1", "status": "completed",
                "timestamp": "2026-10-01T13:00:00Z", "reason": "Synthetic evidence delivered",
            }],
            "study_units": [{
                "id": "u2", "session_id": "session1", "timestamp": "2026-10-01T14:00:00Z",
                "subskill_ids": ["s2"], "kind": "coverage", "mode": "override", "lifecycle": "started",
                "reason": "Synthetic explicit activity scope",
            }],
        })
        self.state["items"].append(self.prepare(1, 2))
        self.state["items"][-1]["unit_id"] = "u2"
        self.state["answer_position_deck"]["cursor"] = 2
        self.state.update(
            current_unit_id="u2", allocation_category="coverage", question_index=1,
            next_action="reask_pending", ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.save()
        return original

    def test_completed_item_keeps_its_own_activity_scope_after_advancing_to_new_unit(self):
        original = self.advance_to_second_activity()
        self.assertEqual(self.state["items"][0], original)
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q2")
        row = self.respond(1, timestamp="2026-10-01T15:00:00Z")
        row["unit_id"] = "u2"
        self.record({"attempts": [row]})
        self.reconcile([row])

    def test_earlier_activity_corrections_resume_original_unit_without_rebinding_later_items(self):
        for reason in ("disowned_answer", "invalid_item"):
            for later_stage in ("unanswered", "reviewed"):
                with self.subTest(reason=reason, later_stage=later_stage):
                    if self.checkpoint_path.exists():
                        self.checkpoint_path.unlink()
                    self.ledger_path.unlink()
                    self.invoke(coverage, "init")
                    original = self.advance_to_second_activity()
                    if later_stage == "reviewed":
                        row = self.respond(1, timestamp="2026-10-01T15:00:00Z")
                        self.record({"attempts": [row]})
                        self.reconcile([row])
                        self.state["items"][1]["review"] = "complete"
                        self.state["next_action"] = "advance_after_review"
                        self.save()
                    later = deepcopy(self.state["items"][1])
                    self.record({"voided_attempts": [{
                        "id": "void-original", "attempt_id": "a1", "reason_kind": reason,
                        "reason": "Synthetic historical correction",
                        "response_ref": original["response"]["response_ref"]
                        if reason == "invalid_item" else "synthetic:void",
                        "genuine_confirmed": True, "source_ref": "https://learn.microsoft.com/fixture",
                        "timestamp": "2026-10-01T16:00:00Z",
                    }]})
                    self.assertEqual(self.resume()["recovery_question_index"], 0)
                    replacement = deepcopy(original)
                    replacement.update(
                        id="q1-corrected", response=None, attempt_id=None, grading="pending",
                        review="pending", history=[{"void_id": "void-original", "item": original}],
                    )
                    if reason == "invalid_item":
                        replacement["stem"] = "Corrected source-backed mechanism constraint?"
                    self.state["items"][0] = replacement
                    self.state.update(
                        question_index=0, next_action="reask_pending",
                        applied_void_ids=["void-original"], ledger_sha256=coverage.digest(self.ledger_path),
                    )
                    self.save(error="Pending question belongs to another activity")
                    self.state["current_unit_id"] = "u1"
                    self.save()
                    self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q1-corrected")
                    self.assertEqual(self.state["items"][1], later)
                    replacement["response"] = {
                        "response_ref": "synthetic:confirmed", "genuine_confirmed": True,
                        "timestamp": "2026-10-01T17:00:00Z", "text": "Synthetic answer", "flags": [],
                    }
                    replacement["attempt_id"] = "confirmed"
                    self.state["next_action"] = "grade_recorded"
                    self.save(error="Record answers only during an active activity")
                    replacement.update(response=None, attempt_id=None)
                    self.state["next_action"] = "reask_pending"
                    self.record({"unit_events": [{
                        "id": "restart-u1", "unit_id": "u1", "status": "started",
                        "timestamp": "2026-10-01T16:30:00Z", "reason": "Resume original activity",
                    }]})
                    self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                    row = self.respond(0, aid="confirmed", timestamp="2026-10-01T17:00:00Z")
                    self.record({"attempts": [row]})
                    self.reconcile([row])
                    self.state["items"][0]["review"] = "complete"
                    self.state["next_action"] = "advance_after_review"
                    self.save()
                    self.state.update(
                        current_unit_id="u2", question_index=1,
                        next_action="reask_pending" if later_stage == "unanswered" else "advance_after_review",
                    )
                    self.save()
                    if later_stage == "unanswered":
                        row = self.respond(1, aid="remaining", timestamp="2026-10-01T18:00:00Z")
                        self.record({"attempts": [row]})
                        self.reconcile([row])
                    self.assertEqual(self.state["answer_position_deck"]["cursor"], 2)
                    self.assertEqual(coverage.read_json(self.ledger_path)["study_units"][0]["id"], "u1")

    def test_new_activity_bindings_are_required_locked_and_session_scoped(self):
        self.start(subskill_ids=["s1"])
        item = self.prepare(0, 1)
        item.pop("unit_id")
        self.state.update(items=[item], next_action="reask_pending")
        self.state["answer_position_deck"]["cursor"] = 1
        self.save(error="New questions require their current activity unit ID")
        item["unit_id"] = "u1"
        self.save()
        self.record({"study_units": [{
            "id": "alternate", "session_id": "session1", "timestamp": "2026-10-01T11:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "override", "lifecycle": "started",
            "reason": "Synthetic alternative scope",
        }, {
            "id": "foreign", "session_id": "different-session", "timestamp": "2026-10-01T11:30:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "override", "lifecycle": "started",
            "reason": "Synthetic other session",
        }]})
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        for owner, error in (
            ("missing", "Invalid question unit ID"), ("foreign", "Question unit belongs to another session"),
            ("alternate", "Locked question activity cannot change"),
        ):
            with self.subTest(owner=owner):
                item["unit_id"] = owner
                if owner == "alternate":
                    self.state["current_unit_id"] = owner
                self.save(error=error)
        item["unit_id"] = "u1"
        self.state["current_unit_id"] = "u1"
        self.save()

    def test_legacy_activity_tags_can_be_confirmed_only_from_existing_ownership(self):
        self.advance_to_second_activity()
        for item in self.state["items"]:
            item.pop("unit_id")
        self.write(self.checkpoint_path, self.state)  # Existing checkpoint from before item-unit tags.
        self.state["items"][0]["unit_id"] = "u1"  # Recorded attempt proves this owner.
        self.state["items"][1]["unit_id"] = "u2"  # Unfinished checkpoint proves its current owner.
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q2")
        self.assertEqual([item["unit_id"] for item in coverage.read_json(self.checkpoint_path)["items"]],
                         ["u1", "u2"])

    def test_unreviewed_checkpoint_cannot_reconcile_an_attempt_linked_to_another_unit(self):
        self.start(subskill_ids=["s1"])
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        self.record({"study_units": [{
            "id": "other-unit", "session_id": "session1", "timestamp": "2026-10-01T11:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "override", "lifecycle": "started",
            "reason": "Synthetic explicit alternate activity",
        }]})
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        row = self.respond(0)
        row["unit_id"] = "other-unit"
        self.record({"attempts": [row]})
        self.state["items"][0]["grading"] = "applied"
        self.state.update(
            applied_attempt_ids=["a1"], next_action="review_recorded",
            ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.save(error="Checkpoint answer belongs to another activity")

    def reconcile_attempt_claiming(self, claimed):
        self.start(subskill_ids=["s1", "s2"])
        self.state["items"] = [self.prepare(0, 1)]  # Verified for s1 only.
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        row = self.respond(0)
        row["subskill_ids"] = claimed  # Same activity, but claims coverage the item never tested.
        self.record({"attempts": [row]})
        self.state["items"][0]["grading"] = "applied"
        self.state.update(
            applied_attempt_ids=["a1"], next_action="review_recorded",
            ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.save(error="Ledger attempt claims subskills its question does not target")
        return row

    def test_voiding_an_overclaiming_attempt_allows_reasking_its_question(self):
        row = self.reconcile_attempt_claiming(["s2"])
        self.record({"voided_attempts": [{
            "id": "overclaim", "attempt_id": row["id"], "reason_kind": "disowned_answer",
            "reason": "Attempt claimed a subskill its question did not test",
            "timestamp": "2026-10-01T13:00:00Z", "genuine_confirmed": True,
            "response_ref": "synthetic:overclaim",
        }]})
        self.state = coverage.read_json(self.checkpoint_path)  # The rejected grading never persisted.
        before = deepcopy(self.state["items"][0])
        replacement = deepcopy(before)
        replacement.update(id="q1-reask", response=None, attempt_id=None, grading="pending",
                           review="pending", history=[{"void_id": "overclaim", "item": before}])
        self.state.update(items=[replacement], applied_attempt_ids=[row["id"]],
                          applied_void_ids=["overclaim"],
                          next_action="reask_pending", ledger_sha256=coverage.digest(self.ledger_path))
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q1-reask")

    def test_checkpoint_rejects_attempt_for_a_different_subskill_in_the_same_activity(self):
        self.reconcile_attempt_claiming(["s2"])

    def test_checkpoint_rejects_attempt_claiming_extra_subskills_beyond_its_question(self):
        self.reconcile_attempt_claiming(["s1", "s2"])

    def test_completed_unlinked_legacy_item_does_not_invent_current_activity_ownership(self):
        self.start(subskill_ids=["s1"])
        row = attempt("historical", "s2", session_id="session1", context="historical")
        self.record({"attempts": [row]})
        item = self.prepare(0, 2)
        item.pop("unit_id")
        answer(item, aid="historical", timestamp=row["timestamp"])
        item["response"]["response_ref"] = row["response_ref"]
        item.update(grading="applied", review="complete")
        self.state.update(
            items=[item], applied_attempt_ids=["historical"], next_action="advance_after_review",
            ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.state["answer_position_deck"]["cursor"] = 1
        # Preexisting completed legacy item: no recorded unit link to reconstruct.
        self.write(self.checkpoint_path, self.state)
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "advance_after_review")
        self.assertNotIn("unit_id", coverage.read_json(self.ledger_path)["attempts"][0])
        self.assertEqual(self.resume()["unit_lifecycle"], "started")

    def test_metadata_free_legacy_pending_item_cannot_adopt_another_activitys_attempt(self):
        self.start(subskill_ids=["s1"])
        item = self.prepare(0, 1)
        item.pop("private_metadata")
        item.pop("unit_id")
        self.state.update(items=[item], next_action="reask_pending")
        self.state["answer_position_deck"]["cursor"] = 1
        self.write(self.checkpoint_path, self.state)  # Supported pre-binding, metadata-free legacy item.
        self.record({"study_units": [{
            "id": "other-unit", "session_id": "session1", "timestamp": "2026-10-01T11:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "override", "lifecycle": "started",
            "reason": "Synthetic other activity",
        }]})
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        answer(item)
        self.state["next_action"] = "grade_recorded"
        self.save()
        row = attempt("a1", "s1", session_id="session1", unit_id="other-unit",
                      timestamp=item["response"]["timestamp"], response_ref=item["response"]["response_ref"])
        self.record({"attempts": [row]})
        item["grading"] = "applied"
        self.state.update(applied_attempt_ids=["a1"], ledger_sha256=coverage.digest(self.ledger_path),
                          next_action="review_recorded")
        self.save(error="Pending question belongs to another activity")
        self.invoke(session, "resume", error="Pending question belongs to another activity")

    def prepare_free_response(self, index=0):
        item = self.prepare(index, 1)
        item.update(
            kind="free_response", stem="What changes, and why does the mechanism force it?",
            options=[], private_key=[], private_grading_criteria=[
                "FIXTURE PRIVATE identify the changed constraint",
                "FIXTURE PRIVATE derive the decision from the mechanism",
            ],
        )
        return item

    def test_free_response_journey_prepares_pauses_resumes_grades_and_completes(self):
        self.start(subskill_ids=["s1"])
        self.state["mode"] = "tutor"
        self.checkpoint_path.unlink()
        self.save()
        self.state["items"] = [self.prepare_free_response()]  # Takes no answer position.
        self.state["next_action"] = "reask_pending"
        self.save()
        self.state["paused"] = True
        self.save()
        pending = self.resume(fresh_process=True)["pending_question"]
        self.assertEqual(pending, {
            "id": "q1", "kind": "free_response",
            "stem": "What changes, and why does the mechanism force it?",
        })
        before = self.checkpoint_path.read_bytes()
        plain = subprocess.run(
            [sys.executable, "-B", session.__file__, "resume", "--root", str(self.root),
             "--exam", "test-100", "--as-of", AS_OF],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn(pending["stem"], plain.stdout)
        self.assertNotIn("FIXTURE PRIVATE", plain.stdout)
        self.assertNotIn("\nA. ", plain.stdout)
        self.assertEqual(self.checkpoint_path.read_bytes(), before)
        self.state["paused"] = False
        self.save()
        row = self.respond(0)
        row.update(context="post_teaching", assistance="assisted")
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.state["items"][0]["review"] = "complete"
        self.state.update(phase="complete", next_action="session_complete")
        self.record({"unit_events": [{
            "id": "done", "unit_id": "u1", "status": "completed",
            "timestamp": "2026-10-01T12:30:00Z", "reason": "Synthetic transfer check delivered",
        }]})
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.save()
        resumed = self.resume(fresh_process=True)
        self.assertEqual(resumed["next_action"], "session_complete")
        self.assertEqual(resumed["unit_lifecycle"], "completed")
        report = self.invoke(coverage, "audit")
        self.assertEqual(report["completed_normal_units"], 1)
        self.assertEqual(report["subskills"]["assessed"], 0)

    def test_free_response_schema_rejects_choice_payloads_missing_criteria_and_mocks(self):
        self.start()
        item = self.prepare_free_response()
        self.state.update(items=[item], next_action="reask_pending")
        self.state["answer_position_deck"]["cursor"] = 1
        for changes, error in (
            ({"private_grading_criteria": None}, "private grading criteria"),
            ({"private_grading_criteria": []}, "private grading criteria"),
            ({"private_grading_criteria": [""]}, "private grading criteria"),
            ({"private_grading_criteria": ["same", "same"]}, "private grading criteria"),
            ({"options": [{"key": "A", "text": "Choice"}]}, "Free-response items cannot contain choices"),
            ({"private_key": ["A"]}, "Free-response items cannot contain choices"),
            ({"kind": "essay"}, "question kind"),
            ({"kind": "choice"}, "Choice items cannot contain private grading criteria"),
        ):
            with self.subTest(changes=changes):
                self.state["items"] = [dict(item, **changes)]
                self.save(error=error)
        self.state["items"] = [deepcopy(item)]
        del self.state["items"][0]["private_grading_criteria"]
        self.save(error="private grading criteria")
        self.checkpoint_path.unlink()
        self.ledger_path.unlink()
        self.invoke(coverage, "init")
        self.start(mock=True)
        self.state["items"] = [self.prepare_free_response(i) for i in range(10)]
        for prepared in self.state["items"]:
            prepared["grading"] = "deferred"
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        self.save(error="Mocks require choice items")

    def test_free_response_cannot_skip_unanswered_preparation_or_consume_a_position_on_pause(self):
        self.start()
        prepared = self.prepare_free_response()
        self.state.update(items=[deepcopy(prepared)], next_action="grade_recorded")
        answer(self.state["items"][0])
        self.save(error="New questions must be checkpointed unanswered")
        self.state.update(items=[prepared], next_action="reask_pending")
        self.save()
        self.state["paused"] = True
        self.save()
        self.state["items"].append(self.prepare(1, 1, position=0))
        self.state["answer_position_deck"]["cursor"] = 1
        self.save(error="Pause cannot generate or consume answer positions")

    def test_free_response_takes_no_answer_position_so_the_next_choice_uses_the_first_one(self):
        self.start()
        self.state["items"] = [self.prepare_free_response()]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save(error="Deck cursor must equal the number of prepared four-option single-answer items")
        self.state["answer_position_deck"]["cursor"] = 0
        self.save()
        row = self.respond(0)
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.state["items"][0]["review"] = "complete"
        self.state["next_action"] = "advance_after_review"
        self.save()
        self.state["items"].append(self.prepare(1, 1))  # Keyed to the second position.
        self.state["answer_position_deck"]["cursor"] = 1
        self.state.update(question_index=1, next_action="reask_pending")
        self.save(error="Question key differs from its locked answer position")
        self.state["items"][1] = self.prepare(1, 1, position=0)
        self.save()
        self.assertEqual(coverage.read_json(self.checkpoint_path)["answer_position_deck"]["cursor"], 1)

    def test_free_response_criteria_and_kind_are_locked_and_disowned_reask_is_exact(self):
        self.start()
        self.state["items"] = [self.prepare_free_response()]  # Takes no answer position.
        self.state["next_action"] = "reask_pending"
        self.save()
        original = deepcopy(self.state["items"][0])
        self.state["items"][0]["private_grading_criteria"] = ["Different private criteria"]
        self.save(error="Locked question stem/options/key/order cannot change")
        self.state["items"][0] = deepcopy(original)
        self.state["items"][0] = self.prepare(0, 1)
        self.state["answer_position_deck"]["cursor"] = 1
        self.save(error="Locked question stem/options/key/order cannot change")
        self.state["items"][0] = deepcopy(original)
        self.state["answer_position_deck"]["cursor"] = 0
        row = self.respond(0)
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.record({"voided_attempts": [{
            "id": "disowned", "attempt_id": "a1", "reason_kind": "disowned_answer",
            "reason": "Synthetic answer was not mine", "timestamp": "2026-10-01T13:00:00Z",
            "genuine_confirmed": True, "response_ref": "synthetic:disowned",
        }]})
        summary = self.resume(fresh_process=True)
        self.assertEqual(summary["next_action"], "reask_disowned")
        self.assertEqual(summary["pending_question"]["kind"], "free_response")
        before = deepcopy(self.state["items"][0])
        replacement = deepcopy(original)
        replacement.update(id="q1-reask", history=[{"void_id": "disowned", "item": before}])
        self.state["items"] = [replacement]
        self.state["applied_void_ids"] = ["disowned"]
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.state["next_action"] = "reask_pending"
        self.save()
        self.state["items"][0] = deepcopy(replacement)
        self.state["items"][0]["private_grading_criteria"] = ["Different private criteria"]
        self.save(error="Disowned answer must reask the exact unchanged question and options")
        self.state["items"][0] = deepcopy(replacement)
        row = self.respond(0, aid="confirmed", timestamp="2026-10-01T14:00:00Z")
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.assertEqual(coverage.read_json(self.checkpoint_path)["answer_position_deck"]["cursor"], 0)

    def test_invalid_free_response_criteria_can_be_corrected_at_each_persistence_stage(self):
        for stage in ("prepared", "journaled", "ledger"):
            with self.subTest(stage=stage):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start()
                self.state["items"] = [self.prepare_free_response()]
                self.state["next_action"] = "reask_pending"
                self.save()
                if stage != "prepared":
                    row = self.respond(0)
                    if stage == "ledger":
                        self.record({"attempts": [row]})
                        self.reconcile([row])
                original = deepcopy(self.state["items"][0])
                correction = {
                    "id": "invalid", "reason_kind": "invalid_item", "reason": "Invalid criterion",
                    "source_ref": "https://learn.microsoft.com/example",
                    "timestamp": "2026-10-01T13:00:00Z",
                }
                if stage == "ledger":
                    self.record({"voided_attempts": [
                        dict(correction, attempt_id="a1", genuine_confirmed=True,
                             response_ref=original["response"]["response_ref"]),
                    ]})
                    entry = {"void_id": "invalid", "item": original}
                    self.state["applied_void_ids"] = ["invalid"]
                    self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                else:
                    entry = {"invalidation": correction, "item": original}
                replacement = self.prepare_free_response()
                replacement.update(
                    id="corrected", private_grading_criteria=["FIXTURE PRIVATE corrected criterion"],
                    history=[entry],
                )
                self.state.update(items=[replacement], next_action="reask_pending")
                corrected = replacement["private_grading_criteria"]
                replacement["private_grading_criteria"] = deepcopy(original["private_grading_criteria"])
                self.save(error="Invalid item needs a corrected replacement, not an unchanged reask")
                replacement["private_grading_criteria"] = corrected
                self.save()
                persisted = coverage.read_json(self.checkpoint_path)
                self.assertEqual(persisted["items"][0]["history"][0]["item"], original)
                self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "corrected")
                replacement["kind"] = "choice"
                replacement.pop("private_grading_criteria")
                replacement.update(options=self.prepare(0, 1)["options"], private_key=["B"])
                self.state["answer_position_deck"]["cursor"] = 1
                self.save(error="Replacement must retain its question kind")

    def test_plain_bracketed_technical_options_save_and_resume_without_allowing_links(self):
        self.start()
        item = self.prepare(0, 1)
        for option, text in zip(item["options"], ("[1, 2, 3]", "[Authorize]", "Service C", "Service D")):
            option["text"] = text
        self.state.update(items=[item], next_action="reask_pending")
        self.state["answer_position_deck"]["cursor"] = 1
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["options"], item["options"])
        for text in ("[link](https://example.test)", "[link][reference]", "![image](url)"):
            with self.subTest(text=text):
                self.assertFalse(session.neutral_option(text))

    def test_new_manifest_requires_metadata_in_quiz_and_mock(self):
        for mock in (False, True):
            with self.subTest(mock=mock):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start(mock)
                count = 10 if mock else 1
                self.state["items"] = [self.prepare(i, i % 4 + 1) for i in range(count)]
                self.state["answer_position_deck"]["cursor"] = count
                self.state["next_action"] = "reask_pending"
                missing = self.state["items"][-1].pop("private_metadata")
                self.save(error="New questions require private verification metadata")
                self.state["items"][-1]["private_metadata"] = missing
                self.save()
                self.assertEqual(self.resume(fresh_process=True)["next_action"], "reask_pending")

    def test_new_responses_obey_activity_timeline_and_preserve_historical_reconciliation(self):
        for status in ("interrupted", "deferred", "completed"):
            with self.subTest(status=status):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start()
                self.state["items"] = [self.prepare(0, 1)]
                self.state["answer_position_deck"]["cursor"] = 1
                self.state["next_action"] = "reask_pending"
                self.save()
                if status == "completed":
                    self.record({"attempts": [
                        attempt(f"prior{i}", f"s{i}", session_id="session1", unit_id="u1",
                                timestamp="2026-10-01T10:30:00Z", response_ref=f"prior:{i}")
                        for i in range(1, 5)
                    ]})
                self.record({"unit_events": [{
                    "id": "inactive", "unit_id": "u1", "status": status,
                    "timestamp": "2026-10-01T11:00:00Z", "reason": "Synthetic lifecycle transition",
                }]})
                self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                item = self.state["items"][0]
                item.update(attempt_id="new-answer", response={
                    "response_ref": "synthetic:new-answer", "timestamp": "2026-10-01T12:00:00Z",
                    "genuine_confirmed": True, "text": "Synthetic B", "flags": [],
                })
                self.state["next_action"] = "grade_recorded"
                self.save(error="Record answers only during an active activity")
                item["response"]["timestamp"] = "2026-10-01T09:00:00Z"
                self.save(error="Answer precedes its activity")
                item["response"]["timestamp"] = "2026-10-01T10:45:00Z"
                self.save()  # Historical answer was received while the activity was started.
                row = attempt(
                    "new-answer", "s1", session_id="session1", unit_id="u1",
                    timestamp=item["response"]["timestamp"], response_ref=item["response"]["response_ref"],
                )
                self.record({"attempts": [row]})
                self.reconcile([row])
                self.assertEqual(self.resume(fresh_process=True)["next_action"], "review_recorded")
                if status != "completed":
                    self.state["items"][0]["review"] = "complete"
                    self.state["next_action"] = "advance_after_review"
                    self.save()
                    self.record({"unit_events": [{
                        "id": "restart", "unit_id": "u1", "status": "started",
                        "timestamp": "2026-10-01T11:30:00Z", "reason": "Synthetic resume",
                    }]})
                    self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                    self.state["items"].append(self.prepare(1, 2))
                    self.state["answer_position_deck"]["cursor"] = 2
                    self.state.update(question_index=1, next_action="reask_pending")
                    self.save()
                    row = self.respond(1, aid="after-resume")
                    self.record({"attempts": [row]})
                    self.reconcile([row])

    def test_response_exactly_at_supported_completion_timestamp_is_recordable(self):
        self.start()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        self.record({
            "attempts": [
                attempt(f"prior{i}", f"s{i}", session_id="session1", unit_id="u1",
                        timestamp="2026-10-01T10:30:00Z", response_ref=f"prior:{i}")
                for i in range(1, 5)
            ],
            "unit_events": [{
                "id": "done", "unit_id": "u1", "status": "completed",
                "timestamp": "2026-10-01T11:00:00Z", "reason": "Synthetic completed evidence",
            }],
        })
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        row = self.respond(0, timestamp="2026-10-01T11:00:00Z")
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "review_recorded")

    def test_new_questions_cannot_bypass_deck_preparation_by_omitting_the_field(self):
        for mode in ("quiz", "mock", "tutor", "follow_plan"):
            with self.subTest(mode=mode):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start(mock=mode == "mock")
                self.checkpoint_path.unlink()
                self.state["mode"] = mode
                self.state["items"] = [self.prepare(0, 1)]
                self.state.pop("answer_position_deck")
                self.state["next_action"] = "reask_pending"
                self.save(error="Save the answer-position deck before preparing questions")

    def test_empty_deckless_checkpoint_cannot_append_questions_before_locking_positions(self):
        self.start()
        self.state.pop("answer_position_deck")
        self.write(self.checkpoint_path, self.state)
        self.state["items"] = [positioned_question(0, "B")]
        self.state["next_action"] = "reask_pending"
        self.save(error="Save the answer-position deck before preparing questions")
        self.state.update(items=[], next_action="resume_phase")
        self.state["answer_position_deck"] = {
            "kind": "open_ended", "positions": list("BACD" * 3), "cursor": 0,
        }
        self.save()
        self.state["items"] = [positioned_question(0, "B")]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()

    def test_populated_legacy_checkpoint_can_resume_answer_and_append_without_inventing_deck(self):
        self.start()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["items"][0].pop("private_metadata")
        self.state.pop("answer_position_deck")
        self.state["next_action"] = "reask_pending"
        self.write(self.checkpoint_path, self.state)  # Existing pre-deck checkpoint fixture.
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "reask_pending")
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.save()
        response = self.state["items"][0]["response"]
        row = attempt("a1", "s1", session_id="session1", unit_id="u1",
                      timestamp=response["timestamp"], response_ref=response["response_ref"])
        self.record({"attempts": [row]})
        self.reconcile([row])
        self.state["items"][0]["review"] = "complete"
        self.state["next_action"] = "advance_after_review"
        self.save()
        self.state["items"].append(positioned_question(1, "C"))
        self.state.update(question_index=1, next_action="reask_pending")
        verification = self.state["items"][-1].pop("private_metadata")
        self.save(error="New questions require private verification metadata")
        self.state["items"][-1]["private_metadata"] = verification
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q2")
        self.assertNotIn("answer_position_deck", coverage.read_json(self.checkpoint_path))

    def test_rollover_cannot_carry_legacy_deck_exemption_into_new_session(self):
        self.state = self.planner_state()
        self.state.update(phase="complete", next_action="session_complete")
        self.save()
        self.record({"study_units": [{
            "id": "u2", "session_id": "session2", "timestamp": "2026-10-02T10:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "normal", "lifecycle": "started",
        }]})
        self.state.pop("private_planning")
        self.state.update(
            mode="quiz", session_id="session2", phase="warm_up", current_unit_id="u2",
            allocation_category="coverage", ledger_sha256=coverage.digest(self.ledger_path),
            items=[positioned_question(0, "B")], next_action="reask_pending",
        )
        self.state["items"][0]["unit_id"] = "u2"
        self.save(error="Save the answer-position deck before preparing questions")

    def test_deck_backed_first_save_must_precede_item_preparation(self):
        for mock in (False, True):
            with self.subTest(mock=mock):
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                self.start(mock)
                self.checkpoint_path.unlink()
                count = 10 if mock else 1
                self.state["items"] = [self.prepare(i, i % 4 + 1) for i in range(count)]
                self.state["answer_position_deck"]["cursor"] = count
                self.state["next_action"] = "reask_pending"
                self.save(error="Save the answer-position deck before preparing questions")

    def test_session_rollover_cannot_combine_new_deck_and_questions(self):
        self.state = self.planner_state()
        self.state.update(phase="complete", next_action="session_complete")
        self.save()
        self.record({"study_units": [{
            "id": "u2", "session_id": "session2", "timestamp": "2026-10-02T10:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "normal", "lifecycle": "started",
        }]})
        self.state.pop("private_planning")
        self.state.update(
            mode="quiz", session_id="session2", phase="warm_up", current_unit_id="u2",
            allocation_category="coverage", ledger_sha256=coverage.digest(self.ledger_path),
            answer_position_deck={"kind": "open_ended", "positions": list("BACD" * 3), "cursor": 1},
            next_action="reask_pending",
        )
        self.state["items"] = [self.prepare(0, 1)]
        self.save(error="Save the answer-position deck before preparing questions")
        item = self.state["items"].pop()
        self.state["answer_position_deck"]["cursor"] = 0
        self.state["next_action"] = "resume_phase"
        self.save()
        self.state["items"] = [item]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()

    def test_empty_legacy_checkpoint_must_lock_new_deck_before_preparing_questions(self):
        self.start()
        self.state.pop("answer_position_deck")
        self.write(self.checkpoint_path, self.state)
        self.state["answer_position_deck"] = {
            "kind": "open_ended", "positions": list("BACD" * 3), "cursor": 1,
        }
        self.state["items"] = [self.prepare(0, 1)]
        self.state["next_action"] = "reask_pending"
        self.save(error="Save the answer-position deck before preparing questions")

    def planner_state(self):
        return {
            "schema_version": 1, "exam": "test-100", "blueprint_revision": "v1",
            "session_id": "planner1", "mode": "planner", "phase": "planning",
            "paused": False, "current_unit_id": None, "allocation_category": None,
            "question_index": 0, "items": [], "ledger_sha256": coverage.digest(self.ledger_path),
            "applied_attempt_ids": [], "applied_void_ids": [], "pending_check_ids": [],
            "next_action": "resume_phase", "private_planning": {
                "plan_filename": "2026-10-20-sprint.md",
                "proposal": "FIXTURE PRIVATE draft dated plan and proposed changes",
            },
        }

    def test_planner_proposal_pause_restart_and_completion_do_not_write_plan_or_learning(self):
        self.state = self.planner_state()
        self.save()
        self.state["paused"] = True
        self.save()
        ledger = self.ledger_path.read_bytes()
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "resume_phase")
        self.assertEqual(coverage.read_json(self.checkpoint_path)["private_planning"],
                         self.state["private_planning"])
        self.assertFalse((self.base / "assets" / "study-plans").exists())
        self.assertEqual(self.ledger_path.read_bytes(), ledger)
        self.state["paused"] = False
        self.save()
        self.state["private_planning"]["proposal"] = "FIXTURE PRIVATE revised proposal"
        self.save()
        self.state.update(phase="complete", next_action="session_complete")
        self.save()
        self.assertEqual(self.resume()["next_action"], "session_complete")
        self.assertEqual(self.ledger_path.read_bytes(), ledger)
        self.assertFalse((self.base / "assets" / "study-plans").exists())

    def test_planner_rejects_bad_proposal_or_fabricated_activity(self):
        valid = self.planner_state()
        for field, value in (
            ("private_planning", None), ("private_planning", {}),
            ("private_planning", {"plan_filename": "../escape.md", "proposal": "Draft"}),
            ("private_planning", {"plan_filename": "draft.md", "proposal": ""}),
            ("private_planning", {"plan_filename": "draft.md", "proposal": "Draft", "approved": True}),
            ("items", [positioned_question(0, "A")]), ("phase", "grade_deferred"),
            ("answer_position_deck", {"kind": "planned", "positions": ["A"], "cursor": 0}),
        ):
            with self.subTest(field=field):
                self.state = deepcopy(valid)
                self.state[field] = value
                self.save(error="")
        self.state = valid
        self.save()
        self.state["paused"] = True
        self.save()
        self.state["private_planning"]["proposal"] = "Edited while paused"
        self.save(error="Paused planning proposal cannot change")

    def test_planner_proposals_are_private_and_cannot_attach_to_quiz_mode(self):
        self.state = self.planner_state()
        self.state["mode"] = "quiz"
        self.save(error="requires planner mode")
        self.state["mode"] = "planner"
        self.save()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = session.main([
                "resume", "--root", str(self.root), "--exam", "test-100", "--as-of", AS_OF,
            ])
        self.assertEqual(code, 0, err.getvalue())
        self.assertNotIn("FIXTURE PRIVATE", out.getvalue())
        self.assertNotIn("2026-10-20-sprint.md", out.getvalue())
        self.assertNotIn("private_planning", self.resume())
        self.assertEqual(coverage.read_json(self.ledger_path)["study_units"], [])

    def test_mock_validation_also_rejects_legacy_bad_manifest_on_read_only_resume(self):
        self.start(mock=True)
        self.state["items"] = [self.prepare(index, index % 4 + 1) for index in range(10)]
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        self.save()
        self.state["items"][0]["options"] = self.state["items"][0]["options"][:2]
        self.write(self.checkpoint_path, self.state)
        self.invoke(session, "resume", error="exactly four A/B/C/D options")

    def test_mock_rejects_non_abcd_manifest_options_even_when_deck_check_would_be_skipped(self):
        self.start(mock=True)
        self.state["items"] = [self.prepare(index, index % 4 + 1) for index in range(10)]
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        good = deepcopy(self.state)
        for keys in ("AB", "ABC", "ABCE", "ABCDE"):
            with self.subTest(keys=keys):
                self.state = deepcopy(good)
                self.state["items"][0]["options"] = [
                    {"key": key, "text": f"Service {key}"} for key in keys
                ]
                self.save(error="Mock questions require exactly four A/B/C/D options")
        self.state = deepcopy(good)
        self.state["items"][0]["private_key"] = ["A"]
        self.save(error="locked answer position")
        self.state = good
        self.save()

    def journal_replacement(self, answered=False, mock=False):
        self.start(mock=mock)
        count = 10 if mock else 1
        self.state["items"] = [self.prepare(index, index % 4 + 1) for index in range(count)]
        self.state["answer_position_deck"]["cursor"] = count
        self.state["next_action"] = "reask_pending"
        self.save()
        if answered:
            self.respond(0)
        original = deepcopy(self.state["items"][0])
        replacement = deepcopy(original)
        replacement.update(
            id="q1-v2", stem="Corrected synthetic constraint", response=None, attempt_id=None,
            grading="deferred" if mock else "pending", review="pending",
            history=[{
                "invalidation": {
                    "id": "journal-invalid-1", "reason_kind": "invalid_item",
                    "reason": "FIXTURE PRIVATE ambiguous constraint",
                    "source_ref": "https://learn.microsoft.com/fixture-defect",
                    "timestamp": "2026-10-02T10:00:00Z",
                },
                "item": original,
            }],
        )
        self.state["items"][0] = replacement
        self.state["next_action"] = "reask_pending"
        return original

    def test_journal_only_invalid_items_resume_without_fabricated_ledger_events(self):
        for mock in (False, True):
            for answered in (False, True):
                with self.subTest(mock=mock, answered=answered):
                    if self.checkpoint_path.exists():
                        self.checkpoint_path.unlink()
                    self.ledger_path.unlink()
                    self.invoke(coverage, "init")
                    original = self.journal_replacement(answered, mock)
                    ledger_before = self.ledger_path.read_bytes()
                    self.save()
                    self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q1-v2")
                    self.assertEqual(self.ledger_path.read_bytes(), ledger_before)
                    stored = coverage.read_json(self.checkpoint_path)
                    self.assertEqual(stored["items"][0]["history"][0]["item"], original)
                    self.assertEqual(stored["answer_position_deck"]["cursor"], 10 if mock else 1)
                    self.assertEqual(stored["applied_attempt_ids"], [])
                    self.assertEqual(stored["applied_void_ids"], [])
                    row = self.respond(0, aid="replacement-answer", timestamp="2026-10-03T12:00:00Z")
                    self.assertEqual(self.resume()["next_action"], "continue_mock" if mock else "grade_recorded")
                    if not mock:
                        self.record({"attempts": [row]})
                        self.reconcile([row])
                        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 1)
                        self.assertEqual(coverage.read_json(self.ledger_path)["voided_attempts"], [])

    def test_journal_reserved_original_attempt_cannot_later_gain_ledger_credit(self):
        self.journal_replacement(answered=True)
        self.save()
        before = self.checkpoint_path.read_bytes()
        self.record({"attempts": [attempt(
            "a1", timestamp="2026-10-01T12:00:00Z", unit_id="u1",
            response_ref="synthetic-turn:a1",
        )]})
        self.invoke(session, "resume", error="Journal-only invalidation cannot replace a ledger attempt")
        self.assertEqual(self.checkpoint_path.read_bytes(), before)

    def test_journal_correction_keeps_original_positions_and_requires_defect_change(self):
        self.journal_replacement()
        valid = deepcopy(self.state)
        for change, error in (
            ("key", "locked answer positions"), ("unchanged", "corrected replacement"),
            ("missing_metadata", "cannot discard private metadata"),
            ("changed_original", "preserve the exact original"),
        ):
            with self.subTest(change=change):
                self.state = deepcopy(valid)
                item = self.state["items"][0]
                if change == "key":
                    item["private_key"] = ["A", "B"]
                elif change == "unchanged":
                    item["stem"] = item["history"][0]["item"]["stem"]
                elif change == "missing_metadata":
                    del item["private_metadata"]
                else:
                    item["history"][0]["item"]["stem"] = "Fabricated original"
                self.save(error=error)

    def test_repeated_journal_corrections_append_history_and_cannot_reuse_ids(self):
        self.journal_replacement(answered=True)
        self.save()
        first = deepcopy(self.state["items"][0])
        revised = deepcopy(first)
        revised.update(id="q1-v3", stem="Second corrected constraint")
        revised["history"].append({
            "invalidation": {
                "id": "journal-invalid-2", "reason_kind": "invalid_item",
                "reason": "Further synthetic defect", "source_ref": "https://learn.microsoft.com/fixture",
                "timestamp": "2026-10-03T12:00:00Z",
            },
            "item": {key: value for key, value in first.items() if key != "history"},
        })
        self.state["items"][0] = revised
        valid = deepcopy(self.state)
        revised["history"][-1]["invalidation"]["id"] = "journal-invalid-1"
        self.save(error="Journal invalidation ID reused")
        self.state = valid
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q1-v3")
        self.assertEqual(len(coverage.read_json(self.checkpoint_path)["items"][0]["history"]), 2)
        self.assertEqual(coverage.read_json(self.checkpoint_path)["answer_position_deck"]["cursor"], 1)


    def test_journal_only_correction_rejects_invalid_provenance_and_ledger_bypass(self):
        self.journal_replacement(answered=True)
        valid = deepcopy(self.state)
        for field, value in (
            ("reason", ""), ("source_ref", ""), ("reason_kind", "disowned_answer"),
            ("timestamp", "2099-01-01T00:00:00Z"),
            ("timestamp", "2026-10-01T10:00:00Z"), ("extra", "unknown"),
        ):
            with self.subTest(field=field):
                self.state = deepcopy(valid)
                self.state["items"][0]["history"][0]["invalidation"][field] = value
                self.save(error="")  # All rejected writes must preserve saved bytes.
        self.state = valid
        self.record({"attempts": [attempt(
            "a1", timestamp="2026-10-01T12:00:00Z", unit_id="u1",
            response_ref="synthetic-turn:a1",
        )]})
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.save(error="Journal-only invalidation cannot replace a ledger attempt")

    def test_journal_history_is_immutable_and_replacement_must_be_unanswered(self):
        original = self.journal_replacement(answered=True)
        good = deepcopy(self.state)
        self.state["items"][0]["response"] = {
            "response_ref": "synthetic-turn:a2", "timestamp": "2026-10-03T12:00:00Z",
            "genuine_confirmed": True, "text": "Fixture response", "flags": [],
        }
        self.state["items"][0]["attempt_id"] = "a2"
        self.state["next_action"] = "grade_recorded"
        self.save(error="Persist replacement before")
        self.state = good
        self.save()
        self.state["items"][0]["history"][0]["invalidation"]["reason"] = "Changed reason"
        self.save(error="Cannot rewrite immutable question history")
        self.state = deepcopy(good)
        self.state["items"][0]["history"][0]["item"]["stem"] = "Changed original"
        self.save(error="Cannot rewrite immutable question history")
        self.state = good
        self.state["items"][0].update(attempt_id="a2", response={
            "response_ref": "synthetic-turn:a2", "timestamp": "2026-10-01T13:00:00Z",
            "genuine_confirmed": True, "text": "Fixture response", "flags": [],
        })
        self.state["next_action"] = "grade_recorded"
        self.save(error="Replacement answer predates confirmed void")

    def test_initial_checkpoint_must_prepare_question_before_accepting_its_response(self):
        self.start()
        self.checkpoint_path.unlink()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        item = self.state["items"][0]
        item.update(attempt_id="a1", response={
            "response_ref": "synthetic-turn:a1", "timestamp": "2026-10-01T12:00:00Z",
            "genuine_confirmed": True, "text": "FIXTURE PRIVATE premature response", "flags": [],
        })
        self.state["next_action"] = "grade_recorded"
        self.state.pop("answer_position_deck")
        self.save(error="New questions must be checkpointed unanswered")

    def test_appended_question_must_be_saved_before_its_response(self):
        self.start()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        item = self.state["items"][0]
        item.update(attempt_id="a1", response={
            "response_ref": "synthetic-turn:a1", "timestamp": "2026-10-01T12:00:00Z",
            "genuine_confirmed": True, "text": "FIXTURE PRIVATE premature response", "flags": [],
        })
        self.state["next_action"] = "grade_recorded"
        self.save(error="New questions must be checkpointed unanswered")

    def test_new_session_must_not_import_an_answer_with_its_first_question(self):
        self.start()
        self.state.update(phase="complete", next_action="session_complete")
        self.save()
        self.record({"study_units": [{
            "id": "u2", "session_id": "session2", "timestamp": "2026-10-02T10:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "override",
            "lifecycle": "started", "reason": "Synthetic fresh session",
        }]})
        self.state.update(
            session_id="session2", phase="warm_up", current_unit_id="u2",
            ledger_sha256=coverage.digest(self.ledger_path),
        )
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["items"][0].update(attempt_id="a1", response={
            "response_ref": "synthetic-turn:a1", "timestamp": "2026-10-02T12:00:00Z",
            "genuine_confirmed": True, "text": "FIXTURE PRIVATE premature response", "flags": [],
        })
        self.state["next_action"] = "grade_recorded"
        self.state.pop("answer_position_deck")
        self.save(error="New questions must be checkpointed unanswered")

    def test_ten_question_mock_prepare_pause_restart_grade_review_and_complete(self):
        self.start(mock=True)
        quotas = self.invoke(session, "mock-quotas")["domain_quotas"]
        self.assertEqual(quotas, {"d1": 3, "d2": 2, "d3": 2, "d4": 3})
        domains = [1, 4, 3, 1, 2, 4, 3, 2, 1, 4]
        self.state["items"] = [self.prepare(index, domain) for index, domain in enumerate(domains)]
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        self.save()
        prepared = deepcopy(self.state["items"])
        self.assertEqual(Counter(domains), {1: 3, 2: 2, 3: 2, 4: 3})
        self.assertEqual(Counter(item["private_metadata"]["domain_id"] for item in self.state["items"]),
                         quotas)
        rows = []
        for index in range(10):
            self.state["question_index"] = index
            self.state["next_action"] = "reask_pending"
            self.save()
            shown = self.resume()["pending_question"]
            self.assertEqual(shown["stem"], prepared[index]["stem"])
            self.assertEqual(shown["options"], prepared[index]["options"])
            self.assertEqual(len(shown["options"]), 4)
            rows.append(self.respond(index))
            expected = "grade_deferred" if index == 9 else "continue_mock"
            self.assertEqual(self.resume()["next_action"], expected)
            self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [])
            if index == 3:
                self.state["paused"] = True
                self.save()
                self.assertEqual(self.resume(fresh_process=True)["next_action"], "continue_mock")
                self.state = coverage.read_json(self.checkpoint_path)
                self.state["paused"] = False
                self.save()
        checkpoint_before = self.checkpoint_path.read_bytes()
        batch = {"attempts": rows}
        self.record(batch)
        self.assertEqual(self.checkpoint_path.read_bytes(), checkpoint_before)
        self.assertEqual(self.resume()["next_action"], "reconcile_ledger")
        ledger_before = self.ledger_path.read_bytes()
        self.record(batch)
        self.assertEqual(self.ledger_path.read_bytes(), ledger_before)
        self.reconcile(rows)
        self.assertEqual(self.resume()["next_action"], "review_recorded")
        for item in self.state["items"]:
            item["review"] = "complete"
        self.state["next_action"] = "advance_after_review"
        self.save()
        self.assertEqual(self.resume()["next_action"], "advance_after_review")
        self.record({"unit_events": [{
            "id": "done", "unit_id": "u1", "status": "completed",
            "timestamp": "2026-10-01T13:00:00Z", "reason": "All fixture targets reviewed",
        }]})
        self.state.update(phase="complete", next_action="session_complete",
                          ledger_sha256=coverage.digest(self.ledger_path))
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "session_complete")
        stored = coverage.read_json(self.ledger_path)
        self.assertEqual(len(stored["attempts"]), 10)
        self.assertEqual(sum(row["result"] == "correct" for row in stored["attempts"]), 9)
        audit = self.invoke(coverage, "audit")
        self.assertEqual(audit["normal_units"], 0)
        self.assertEqual(audit["subskills"]["assessed"], 4)
        for before, after in zip(prepared, coverage.read_json(self.checkpoint_path)["items"]):
            for field in (*session.LOCKED, "private_metadata"):
                self.assertEqual(before[field], after[field])

    def test_normal_quiz_advances_only_after_recording_and_review(self):
        self.start()
        for index in range(4):
            self.state["items"].append(self.prepare(index, index + 1))
            self.state["answer_position_deck"]["cursor"] = index + 1
            self.state["question_index"] = index
            self.state["next_action"] = "reask_pending"
            self.save()
            row = self.respond(index)
            self.assertEqual(self.resume()["next_action"], "grade_recorded")
            if index == 0:
                good = deepcopy(self.state)
                self.state["items"].append(self.prepare(1, 2))
                self.state["answer_position_deck"]["cursor"] = 2
                self.state.update(question_index=1, next_action="reask_pending")
                self.save(error="before grading and review")
                self.state = good
            self.record({"attempts": [row]})
            self.reconcile([row])
            self.assertEqual(self.resume()["next_action"], "review_recorded")
            if index == 0:
                good = deepcopy(self.state)
                self.state["items"].append(self.prepare(1, 2))
                self.state["answer_position_deck"]["cursor"] = 2
                self.state.update(question_index=1, next_action="reask_pending")
                self.save(error="before grading and review")
                self.state = good
            self.state["items"][index]["review"] = "complete"
            self.state["next_action"] = "advance_after_review"
            self.save()
        self.state["paused"] = True
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "advance_after_review")
        self.assertEqual(coverage.read_json(self.checkpoint_path)["answer_position_deck"]["cursor"], 4)
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 4)

    def test_invalid_item_correction_preserves_history_then_records_replacement_once(self):
        self.start()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        row = self.respond(0)
        self.record({"attempts": [row]})
        self.reconcile([row])
        original = deepcopy(self.state["items"][0])
        void = {
            "id": "void-a1", "attempt_id": "a1", "reason_kind": "invalid_item",
            "reason": "Synthetic ambiguous constraint", "genuine_confirmed": True,
            "response_ref": original["response"]["response_ref"], "timestamp": "2026-10-02T10:00:00Z",
            "source_ref": "https://learn.microsoft.com/fixture-defect",
        }
        self.record({"voided_attempts": [void]})
        self.assertEqual(self.resume()["next_action"], "replace_invalid_item")
        replacement = deepcopy(original)
        replacement.update(
            id="q1-v2", stem="Corrected synthetic constraint", response=None, attempt_id=None,
            grading="pending", review="pending", history=[{"void_id": "void-a1", "item": original}],
        )
        replacement["private_metadata"]["verification"]["claim"] = "Corrected fixture claim"
        self.state.update(items=[replacement], applied_void_ids=["void-a1"],
                          ledger_sha256=coverage.digest(self.ledger_path), next_action="reask_pending")
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["stem"], replacement["stem"])
        new_row = self.respond(0, aid="a2", timestamp="2026-10-03T12:00:00Z")
        self.record({"attempts": [new_row]})
        self.reconcile([new_row])
        stored = coverage.read_json(self.checkpoint_path)
        self.assertEqual(stored["items"][0]["history"][0]["item"], original)
        self.assertEqual(stored["answer_position_deck"]["cursor"], 1)
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 2)
        self.assertEqual(self.invoke(coverage, "audit")["voided_attempts"], 1)

    def test_checkpoint_failure_after_ledger_commit_recovers_without_duplicate_evidence(self):
        self.start()
        self.state["items"] = [self.prepare(0, 1)]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.save()
        row = self.respond(0)
        self.record({"attempts": [row]})
        before = self.checkpoint_path.read_bytes()
        self.state["items"][0]["grading"] = "applied"
        self.state.update(applied_attempt_ids=["a1"], ledger_sha256=coverage.digest(self.ledger_path),
                          next_action="review_recorded")
        with patch.object(coverage.os, "replace", side_effect=OSError("fixture write interruption")):
            self.save(error="fixture write interruption")
        self.assertEqual(self.checkpoint_path.read_bytes(), before)
        self.assertEqual(self.resume(fresh_process=True)["next_action"], "reconcile_ledger")
        self.save()
        self.assertEqual(self.resume()["next_action"], "review_recorded")
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 1)
        self.assertFalse(self.checkpoint_path.with_suffix(".json.lock").exists())
        self.assertEqual(list(self.checkpoint_path.parent.glob("*.tmp")), [])


class WorkflowTransitionTests(WorkflowFixture):
    def test_documented_record_command_returns_complete_reusable_json(self):
        self.start(subskill_ids=["s1"])
        row = attempt("documented-record", "s1", unit_id="u1")
        self.write(self.input_path, {"attempts": [row]})
        skill = (Path(session.__file__).resolve().parents[2]
                 / "update-progress" / "SKILL.md").read_text(encoding="utf-8")
        line = next(line for line in skill.splitlines() if "coverage.py record --exam" in line)
        command = line.split("`")[1].split()
        replacements = {
            "python": sys.executable, command[1]: coverage.__file__,
            "<exam>": self.EXAM, "<batch.json>": str(self.input_path),
            "<hash-from-audit>": coverage.digest(self.ledger_path),
        }
        run = subprocess.run(
            [replacements.get(token, token) for token in command]
            + ["--root", str(self.root), "--as-of", AS_OF],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), self.invoke(coverage, "audit"))

    def test_successful_record_report_matches_a_fresh_audit_for_turn_reuse(self):
        self.start(subskill_ids=["s1"])
        row = attempt("record-report", "s1", unit_id="u1")
        result = self.record({"attempts": [row]})
        self.assertEqual(result, self.invoke(coverage, "audit"))
        self.assertEqual(result["sha256"], coverage.digest(self.ledger_path))
        self.assertEqual(result["subskills"]["assessed"], 1)
        completed = self.record({"unit_events": [{
            "id": "complete", "unit_id": "u1", "status": "completed",
            "timestamp": "2026-10-02T12:00:00Z", "reason": "Synthetic completed activity",
        }]})
        self.assertEqual(completed, self.invoke(coverage, "audit"))
        self.assertEqual(completed["completed_normal_units"], 1)
        self.assertNotEqual(completed["sha256"], result["sha256"])

    def test_mock_answers_must_be_saved_one_at_a_time_at_the_old_cursor(self):
        self.start(mock=True)
        self.state["items"] = [
            self.prepare(index, domain)
            for index, domain in enumerate([1, 4, 3, 1, 2, 4, 3, 2, 1, 4])
        ]
        self.state["answer_position_deck"]["cursor"] = 10
        self.state["next_action"] = "reask_pending"
        self.save()
        prepared = deepcopy(self.state)
        checkpoint_before = self.checkpoint_path.read_bytes()
        for positions in ((0, 1), tuple(range(10))):
            with self.subTest(positions=positions):
                self.checkpoint_path.write_bytes(checkpoint_before)
                self.state = deepcopy(prepared)
                for index in positions:
                    answer(self.state["items"][index], f"batch-{index}",
                           timestamp=f"2026-10-01T12:{index:02d}:00Z")
                self.state["question_index"] = positions[-1]
                self.state["next_action"] = "grade_deferred" if len(positions) == 10 else "continue_mock"
                self.save(error="Journal only one new answer at the previously saved question")
                self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [])
        self.checkpoint_path.write_bytes(checkpoint_before)
        self.state = deepcopy(prepared)
        answer(self.state["items"][0], "first", timestamp="2026-10-01T12:00:00Z")
        self.state.update(question_index=1, next_action="reask_pending")
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["pending_question"]["id"], "q2")
        answer(self.state["items"][1], "second", timestamp="2026-10-01T12:01:00Z")
        self.state["next_action"] = "continue_mock"
        self.save()
        self.assertEqual(self.resume(fresh_process=True)["answered_count"], 2)
        two_answers = deepcopy(self.state)
        answer(self.state["items"][2], "third", timestamp="2026-10-01T12:02:00Z")
        self.state["question_index"] = 2
        self.save(error="Journal only one new answer at the previously saved question")
        self.state = two_answers
        self.state.update(question_index=2, next_action="reask_pending")
        self.save()
        self.respond(2)
        self.assertEqual(self.resume(fresh_process=True)["answered_count"], 3)

    def test_record_rejects_a_report_hash_race_and_preserves_both_writers(self):
        original_report = coverage.report
        interleaved = False
        first = attempt("first-writer", "s1", timestamp="2026-10-01T12:00:00Z")
        second = attempt("second-writer", "s2", timestamp="2026-10-01T12:01:00Z")

        def concurrent_report(catalog, ledger, as_of, stale_days=10):
            nonlocal interleaved
            result = original_report(catalog, ledger, as_of, stale_days)
            current = coverage.read_json(self.ledger_path)
            if not interleaved and first in current["attempts"]:
                interleaved = True
                current["attempts"].append(second)
                _, _, skills = coverage.validate_catalog(catalog, "test-100", as_of)
                coverage.validate_ledger(current, catalog, skills, as_of)
                coverage.atomic_write(self.ledger_path, current, coverage.digest(self.ledger_path))
            return result

        self.write(self.input_path, {"attempts": [first]})
        out, err = io.StringIO(), io.StringIO()
        with patch.object(coverage, "report", side_effect=concurrent_report):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = coverage.main([
                    "record", "--root", str(self.root), "--exam", self.EXAM,
                    "--as-of", AS_OF, "--json", "--input", str(self.input_path),
                    "--expected-sha256", coverage.digest(self.ledger_path),
                ])
        self.assertTrue(interleaved)
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Ledger changed during record", err.getvalue())
        self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [first, second])
        self.assertEqual(self.invoke(coverage, "audit")["subskills"]["assessed"], 2)
        before = self.ledger_path.read_bytes()
        replay = self.record({"attempts": [first]})
        self.assertEqual(replay["sha256"], coverage.digest(self.ledger_path))
        self.assertEqual(self.ledger_path.read_bytes(), before)

    def test_init_rejects_concurrent_report_snapshot_without_losing_evidence(self):
        self.ledger_path.unlink()
        original_report = coverage.report
        interleaved = False
        other = attempt("other-writer", "s1", timestamp="2026-10-01T12:00:00Z")

        def concurrent_report(catalog, ledger, as_of, stale_days=10):
            nonlocal interleaved
            result = original_report(catalog, ledger, as_of, stale_days)
            if not interleaved and self.ledger_path.exists():
                interleaved = True
                current = coverage.read_json(self.ledger_path)
                current["attempts"].append(other)
                _, _, skills = coverage.validate_catalog(catalog, self.EXAM, as_of)
                coverage.validate_ledger(current, catalog, skills, as_of)
                coverage.atomic_write(self.ledger_path, current, coverage.digest(self.ledger_path))
            return result

        out, err = io.StringIO(), io.StringIO()
        with patch.object(coverage, "report", side_effect=concurrent_report):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = coverage.main([
                    "init", "--root", str(self.root), "--exam", self.EXAM,
                    "--as-of", AS_OF, "--json",
                ])
        self.assertTrue(interleaved)
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Ledger changed during init", err.getvalue())
        self.assertEqual(coverage.read_json(self.ledger_path)["attempts"], [other])
        self.assertEqual(self.invoke(coverage, "audit")["subskills"]["assessed"], 1)

    def test_mock_quota_cli_blocks_unusable_weights_without_fallback_or_mutation(self):
        ledger_before = self.ledger_path.read_bytes()
        for label, values in (
            ("omitted", {}), ("null", {"weight_min": None, "weight_max": None}),
            ("zero", {"weight_min": 0, "weight_max": 0}),
            ("text", {"weight_min": "25", "weight_max": "30"}),
            ("reversed", {"weight_min": 30, "weight_max": 25}),
        ):
            with self.subTest(weights=label):
                fixture = deepcopy(self.catalog)
                domain = fixture["domains"][0]
                domain.pop("weight_min")
                domain.pop("weight_max")
                domain.update(values)
                self.write(self.base / "blueprint.json", fixture)
                catalog_before = (self.base / "blueprint.json").read_bytes()
                self.invoke(session, "mock-quotas", error="Invalid domain weights: d1")
                self.assertEqual((self.base / "blueprint.json").read_bytes(), catalog_before)
                self.assertEqual(self.ledger_path.read_bytes(), ledger_before)
                self.assertFalse(self.checkpoint_path.exists())

    def test_mock_quota_cli_matches_exact_examples_and_minimum_one_boundaries(self):
        cases = [
            ([(25, 30), (20, 25), (15, 20), (30, 35)], [3, 2, 2, 3]),
            ([(20, 25), (15, 20), (20, 25), (15, 20), (10, 15)], [3, 2, 2, 2, 1]),
            ([(15, 20)] * 6, [2, 2, 2, 2, 1, 1]),
            ([(98, 98), (1, 1), (1, 1)], [8, 1, 1]),
            ([(10, 10)] * 10, [1] * 10),
            ([(100, 100)], [10]),
        ]
        for ranges, expected in cases:
            with self.subTest(ranges=ranges):
                fixture = catalog()
                template = deepcopy(fixture["domains"][0])
                fixture["domains"] = []
                for index, (low, high) in enumerate(ranges, 1):
                    domain = deepcopy(template)
                    domain.update(id=f"d{index}", weight_min=low, weight_max=high)
                    domain["objectives"][0].update(
                        id=f"o{index}", subskills=[{"id": f"s{index}", "title": "Skill", "derived": True}],
                    )
                    fixture["domains"].append(domain)
                self.write(self.base / "blueprint.json", fixture)
                result = self.invoke(session, "mock-quotas")
                self.assertEqual(list(result["domain_quotas"].values()), expected)
                self.assertEqual(result["question_count"], 10)
                self.assertFalse(self.checkpoint_path.exists())

    def test_mock_quota_cli_rejects_short_length_or_unverified_catalog_without_mutation(self):
        self.invoke(session, "mock-quotas", "--question-count", "3",
                    error="at least one question per domain")
        self.invoke(session, "mock-quotas", "--question-count", "-1",
                    error="at least one question per domain")
        self.catalog["verified"] = False
        self.write(self.base / "blueprint.json", self.catalog)
        self.invoke(session, "mock-quotas", error="unverified blueprint")
        self.assertFalse(self.checkpoint_path.exists())

    def test_mock_quota_command_needs_no_learner_state_and_supports_explicit_length(self):
        self.ledger_path.unlink()
        result = self.invoke(session, "mock-quotas", "--question-count", "20")
        self.assertEqual(result["domain_quotas"], {"d1": 6, "d2": 5, "d3": 3, "d4": 6})
        self.assertEqual(result["question_count"], 20)
        self.assertFalse(self.ledger_path.exists())
        self.assertFalse(self.checkpoint_path.exists())

    def pending(self, kind="cold"):
        check = {
            "id": "check1", "subskill_id": "s1", "after_attempt_id": "a1",
            "kind": kind, "status": "pending", "evidence_attempt_id": None,
        }
        self.record({"study_timezone": "UTC-05:00", "attempts": [attempt()], "pending_checks": [check]})
        return check

    def test_cold_check_cli_completion_rejects_assistance_then_replays_idempotently(self):
        check = self.pending()
        evidence = attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z")
        completed = dict(check, status="completed", evidence_attempt_id="a2")
        self.record({"attempts": [dict(evidence, assistance="assisted")],
                     "pending_checks": [completed]}, error="later, novel, independent")
        batch = {"attempts": [evidence], "pending_checks": [completed]}
        self.assertEqual(self.record(batch)["pending_checks"], [])
        before = self.ledger_path.read_bytes()
        self.record(batch)
        self.assertEqual(self.ledger_path.read_bytes(), before)
        self.record({"pending_checks": [dict(completed, subskill_id="s2")]},
                    error="Conflicting existing pending_checks")

    def test_delayed_check_cli_completion_requires_its_actual_source(self):
        check = self.pending("delayed_transfer")
        self.record({"attempts": [attempt("a2", timestamp="2026-10-01T13:00:00Z")]})
        evidence = attempt(
            "a3", session_id="session2", timestamp="2026-10-02T12:00:00Z",
            context="delayed_transfer", retention_source_id="a2",
        )
        complete = dict(check, status="completed", evidence_attempt_id="a3")
        self.record({"attempts": [evidence], "pending_checks": [complete]},
                    error="Delayed check completion requires its source")
        evidence["retention_source_id"] = "a1"
        self.assertEqual(self.record({"attempts": [evidence], "pending_checks": [complete]})
                         ["pending_checks"], [])

    def test_check_completion_rejects_voided_source_or_completion_answer(self):
        for voided_id, message in (
            ("a1", "voided learning source"), ("a2", "voided answer"),
        ):
            with self.subTest(voided_id=voided_id):
                # Each branch starts from an isolated empty ledger, not a learner file.
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                check = self.pending()
                evidence = attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z")
                self.record({"attempts": [evidence], "voided_attempts": [{
                    "id": "v1", "attempt_id": voided_id, "reason": "Synthetic disowned answer",
                    "response_ref": "synthetic-void:1", "genuine_confirmed": True,
                    "timestamp": "2026-10-03T12:00:00Z",
                }]})
                self.record({"pending_checks": [dict(check, status="completed", evidence_attempt_id="a2")]},
                            error=message)
                if voided_id == "a1":
                    self.assertEqual(self.invoke(coverage, "audit")["pending_checks"], [])

    def test_new_pending_check_rejects_an_already_voided_source(self):
        self.record({"study_timezone": "UTC-05:00", "attempts": [attempt()], "voided_attempts": [{
            "id": "v1", "attempt_id": "a1", "reason": "Synthetic disowned answer",
            "response_ref": "synthetic-void:1", "genuine_confirmed": True,
            "timestamp": "2026-10-03T12:00:00Z",
        }]})
        self.record({"pending_checks": [{
            "id": "check1", "subskill_id": "s1", "after_attempt_id": "a1",
            "kind": "cold", "status": "pending", "evidence_attempt_id": None,
        }]}, error="voided learning source")

    def test_legacy_ledger_without_void_list_rejects_recompletion_cleanly(self):
        check = self.pending()
        self.record({
            "attempts": [attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z")],
            "pending_checks": [dict(check, status="completed", evidence_attempt_id="a2")],
        })
        legacy = coverage.read_json(self.ledger_path)
        legacy.pop("voided_attempts")
        self.write(self.ledger_path, legacy)
        self.record({
            "attempts": [attempt("a3", session_id="session3", timestamp="2026-10-03T12:00:00Z")],
            "pending_checks": [dict(check, status="completed", evidence_attempt_id="a3")],
        }, error="Conflicting existing pending_checks")

    def test_delayed_check_void_reopens_and_new_answer_recompletes_through_cli(self):
        check = self.pending("delayed_transfer")
        completed = dict(check, status="completed", evidence_attempt_id="a2")
        self.record({
            "attempts": [attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z",
                                 context="delayed_transfer", retention_source_id="a1")],
            "pending_checks": [completed],
        })
        self.record({"voided_attempts": [{
            "id": "v1", "attempt_id": "a2", "reason": "Synthetic correction",
            "response_ref": "synthetic-void:1", "genuine_confirmed": True,
            "timestamp": "2026-10-03T12:00:00Z",
        }]})
        reopened = self.invoke(coverage, "audit")["pending_checks"][0]
        self.assertTrue(reopened["reopened_by_void"])
        result = self.record({
            "attempts": [attempt("a3", session_id="session3", timestamp="2026-10-04T12:00:00Z",
                                 context="delayed_transfer", retention_source_id="a1")],
            "pending_checks": [dict(completed, evidence_attempt_id="a3")],
        })
        self.assertEqual(result["pending_checks"], [])
        self.assertEqual(len(coverage.read_json(self.ledger_path)["attempts"]), 3)

    def test_void_and_check_recompletion_in_one_batch_is_independent_of_key_order(self):
        check = self.pending()
        old = dict(check, status="completed", evidence_attempt_id="a2")
        self.record({
            "attempts": [attempt("a2", session_id="session2", timestamp="2026-10-02T12:00:00Z")],
            "pending_checks": [old],
        })
        before = self.ledger_path.read_bytes()
        batch = {
            "pending_checks": [dict(old, evidence_attempt_id="a3")],
            "attempts": [attempt("a3", session_id="session3", timestamp="2026-10-04T12:00:00Z")],
            "voided_attempts": [{
                "id": "v1", "attempt_id": "a2", "reason": "Synthetic correction",
                "response_ref": "synthetic-void:1", "genuine_confirmed": True,
                "timestamp": "2026-10-03T12:00:00Z",
            }],
        }
        results = []
        for ordered in (batch, dict(reversed(list(batch.items())))):
            self.ledger_path.write_bytes(before)
            self.assertEqual(self.record(ordered)["pending_checks"], [])
            results.append(coverage.read_json(self.ledger_path))
        self.assertEqual(results[0], results[1])

    def test_legacy_ineligible_delayed_completion_reopens_and_can_be_repaired(self):
        for reason in ("wrong_source", "same_day", "unknown_timezone"):
            with self.subTest(reason=reason):
                legacy = coverage.empty_ledger(self.catalog)
                if reason != "unknown_timezone":
                    legacy["study_timezone"] = "UTC-05:00"
                legacy["attempts"] = [
                    attempt(), attempt("a2", timestamp="2026-10-01T13:00:00Z"),
                    attempt("a3", session_id="session2",
                            timestamp="2026-10-01T15:00:00Z" if reason == "same_day"
                            else "2026-10-02T12:00:00Z",
                            context="delayed_transfer",
                            retention_source_id="a2" if reason == "wrong_source" else "a1"),
                ]
                old_check = {
                    "id": "check1", "subskill_id": "s1", "after_attempt_id": "a1",
                    "kind": "delayed_transfer", "status": "completed", "evidence_attempt_id": "a3",
                }
                legacy["pending_checks"] = [old_check]
                self.write(self.ledger_path, legacy)
                self.assertTrue(self.invoke(coverage, "audit")["pending_checks"][0]["ineligible_retention"])
                fixed = self.record({
                    "study_timezone": "UTC-05:00",
                    "attempts": [attempt("a4", session_id="session3", timestamp="2026-10-04T12:00:00Z",
                                         context="delayed_transfer", retention_source_id="a1")],
                    "pending_checks": [dict(old_check, evidence_attempt_id="a4")],
                })
                self.assertEqual(fixed["pending_checks"], [])
                self.assertEqual(coverage.read_json(self.ledger_path)["attempts"][:3], legacy["attempts"])

    def test_no_remediation_substitution_accepts_only_resolved_prior_evidence(self):
        for latest_result, assistance, allowed in (
            ("correct", "unaided", True), ("incorrect", "unaided", False),
            ("partial", "unaided", False), ("correct", "assisted", False),
        ):
            with self.subTest(latest_result=latest_result, assistance=assistance):
                self.ledger_path.unlink()
                self.invoke(coverage, "init")
                units, events = [], []
                for index in (1, 2):
                    units.append({
                        "id": f"u{index}", "session_id": "session1",
                        "timestamp": f"2026-10-01T0{index}:00:00Z", "subskill_ids": [f"s{index}"],
                        "kind": "coverage", "mode": "normal", "lifecycle": "started",
                    })
                    events.append({
                        "id": f"defer{index}", "unit_id": f"u{index}", "status": "deferred",
                        "timestamp": f"2026-10-01T0{index}:30:00Z", "reason": "Synthetic deferral",
                    })
                self.record({
                    "study_units": units, "unit_events": events,
                    "attempts": [
                        attempt("a1", timestamp="2026-10-01T03:00:00Z", result="incorrect"),
                        attempt("a2", timestamp="2026-10-01T04:00:00Z",
                                result=latest_result, assistance=assistance),
                        attempt("teaching", timestamp="2026-10-01T04:30:00Z",
                                result="unscored", context="teaching"),
                    ],
                })
                substitute = {
                    "id": "u3", "session_id": "session1", "timestamp": "2026-10-01T05:00:00Z",
                    "subskill_ids": ["s3"], "kind": "coverage", "mode": "normal",
                    "lifecycle": "started", "reason": "no-remediation-needed",
                }
                self.record({"study_units": [dict(substitute, reason="unspecified")]},
                            error="Remediation substitution must be explicit")
                if allowed:
                    self.assertEqual(self.record({"study_units": [substitute]})["normal_units"], 3)
                else:
                    self.record({"study_units": [substitute]}, error="Unresolved remediation")

    def test_malformed_timestamp_fails_explicitly_without_modifying_evidence(self):
        self.record({"attempts": [attempt(timestamp="not-a-timestamp")]}, error="Invalid timestamp")
