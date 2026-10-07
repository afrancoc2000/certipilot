import contextlib
from copy import deepcopy
from datetime import date, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "study_session", Path(__file__).resolve().parents[1] / "scripts" / "session.py",
)
session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(session)
coverage = session.coverage
AS_OF = date(2026, 10, 4)


def catalog():
    return {
        "schema_version": 1, "exam": "test-100", "revision": "v1",
        "verified": True, "verification_note": "Fixture only",
        "sources": [{"id": "guide", "url": "https://learn.microsoft.com/example",
                     "checked_at": "2026-10-01", "published_revision": "fixture"}],
        "domains": [{
            "id": "d1", "title": "Domain", "weight_min": 100, "weight_max": 100,
            "objectives": [{
                "id": "o1", "title": "Objective", "source_id": "guide",
                "source_locator": "Domain > Objective",
                "subskills": [{"id": "s1", "title": "Skill", "derived": True}],
            }],
        }],
    }


def question(qid="q1", mock=False):
    return {
        "id": qid, "stem": "Which service satisfies these constraints?",
        "options": ([{"key": key, "text": f"Service {key}"} for key in "ABCD"] if mock else
                    [{"key": "A", "text": "First service"}, {"key": "B", "text": "Second service"}]),
        "answer_order_locked": True, "private_key": ["B"],
        "private_rationale": "PRIVATE SOLUTION SENTINEL",
        "response": None, "attempt_id": None,
        "grading": "deferred" if mock else "pending", "review": "pending",
    }


def answer(item, aid="a1", timestamp="2026-10-02T12:00:00Z"):
    item["response"] = {
        "response_ref": f"genuine-user-turn:{aid}", "timestamp": timestamp,
        "genuine_confirmed": True, "text": "GENUINE PRIVATE ANSWER SENTINEL",
        "flags": ["flagged_for_review"],
    }
    item["attempt_id"] = aid


def metadata():
    return {
        "source_id": "original:PRIVATE SOURCE SENTINEL",
        "domain_id": "d1", "topic": "PRIVATE TOPIC SENTINEL", "subskill_ids": ["s1"],
        "verification": {
            "claim": "PRIVATE VERIFIED CLAIM", "constraints": "PRIVATE CONSTRAINTS",
            "url": "https://learn.microsoft.com/azure/PRIVATE-URL",
            "checked_at": "2026-10-01", "rationale": "PRIVATE VERIFICATION RATIONALE",
        },
    }


def position_deck(count=0, kind="open_ended", positions=None):
    return {"kind": kind, "positions": positions or list("BACD" * 3), "cursor": count}


def positioned_question(index, letter, mock=False):
    item = question(f"q{index + 1}", mock)
    item["options"] = [{"key": key, "text": f"Service {key}"} for key in "ABCD"]
    item["private_key"] = [letter]
    item["private_metadata"] = metadata()
    item["unit_id"] = "u1"
    return item


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "exams" / "test-100"
        self.assets = self.base / "assets"
        self.assets.mkdir(parents=True)
        self.catalog = catalog()
        self.write(self.base / "blueprint.json", self.catalog)
        self.ledger = coverage.empty_ledger(self.catalog)
        self.ledger["study_units"] = [{
            "id": "u1", "session_id": "session1", "timestamp": "2026-10-01T12:00:00Z",
            "subskill_ids": ["s1"], "kind": "coverage", "mode": "normal",
            "lifecycle": "started",
        }]
        self.ledger_path = self.assets / "coverage.json"
        self.path = self.assets / "session.json"
        self.input = self.root / "private-input.json"
        self.write(self.ledger_path, self.ledger)
        self.state = {
            "schema_version": 1, "exam": "test-100", "blueprint_revision": "v1",
            "session_id": "session1", "mode": "quiz", "phase": "warm_up", "paused": False,
            "current_unit_id": "u1", "allocation_category": "coverage", "question_index": 0,
            "items": [question()], "ledger_sha256": coverage.digest(self.ledger_path),
            "applied_attempt_ids": [], "applied_void_ids": [], "pending_check_ids": [],
            "next_action": "reask_pending",
        }

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def call(self, command, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = session.main([
                command, "--exam", "test-100", "--root", str(self.root),
                "--as-of", AS_OF.isoformat(), *args,
            ])
        return code, out.getvalue(), err.getvalue()

    def save(self, state=None, expected=None):
        self.write(self.input, state or self.state)
        return self.call(
            "checkpoint", "--input", str(self.input), "--expected-sha256",
            expected or coverage.digest(self.path) or "missing", "--json",
        )

    def prepare_checkpoint(self):
        if "answer_position_deck" in self.state and not self.path.exists():
            self.lock_position_checkpoint()
        prepared = deepcopy(self.state)
        prepared.update(question_index=0, paused=False)
        prepared["next_action"] = session.intended_action(prepared)
        self.assertTrue(all(item["response"] is None for item in prepared["items"]))
        if "answer_position_deck" not in prepared:
            self.seed_legacy_checkpoint(prepared)
        code, _, err = self.save(prepared)
        self.assertEqual(code, 0, err)

    def seed_legacy_checkpoint(self, state=None):
        """Represent an existing pre-deck file, not permission to create a new deckless run."""
        self.assertFalse(self.path.exists())
        legacy = deepcopy(state if state is not None else self.state)
        self.assertNotIn("answer_position_deck", legacy)
        session.validate(legacy, self.catalog, self.ledger, AS_OF)
        self.write(self.path, legacy)

    def lock_position_checkpoint(self):
        prepared = deepcopy(self.state)
        prepared.update(items=[], question_index=0, paused=False, next_action="resume_phase")
        prepared["answer_position_deck"]["cursor"] = 0
        code, _, err = self.save(prepared)
        self.assertEqual(code, 0, err)

    def resume(self):
        code, out, err = self.call("resume", "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def mock_unit(self):
        self.ledger["study_units"][0].update(mode="mock", reason="Explicit mock exam")
        self.write(self.ledger_path, self.ledger)
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)

    def prepare_positions(self, count=0, kind="open_ended", positions=None):
        deck = position_deck(count, kind, positions)
        self.state["answer_position_deck"] = deck
        self.state["items"] = [
            positioned_question(index, letter, self.state["mode"] == "mock")
            for index, letter in enumerate(deck["positions"][:count])
        ]
        self.state["next_action"] = "reask_pending" if count else "resume_phase"

    def test_position_deck_persists_before_authoring_and_survives_read_only_resume(self):
        self.prepare_positions()
        code, saved, err = self.save()
        self.assertEqual(code, 0, err)
        before = self.path.read_bytes()
        for flags in ([], ["--json"]):
            code, output, err = self.call("resume", *flags)
            self.assertEqual(code, 0, err)
            self.assertNotIn("answer_position_deck", output + saved)
            self.assertNotIn("positions", output + saved)
            self.assertEqual(self.path.read_bytes(), before)
        persisted = coverage.read_json(self.path)["answer_position_deck"]
        self.assertEqual(persisted, position_deck())
        self.state["items"] = [positioned_question(0, persisted["positions"][0])]
        self.state["answer_position_deck"]["cursor"] = 1
        self.state["next_action"] = "reask_pending"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(coverage.read_json(self.path)["answer_position_deck"]["positions"],
                         persisted["positions"])
        self.state["paused"] = True
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["pending_question"]["id"], "q1")
        self.assertEqual(coverage.read_json(self.path)["answer_position_deck"]["cursor"], 1)
        restarted = subprocess.run(
            [sys.executable, "-B", session.__file__, "resume", "--exam", "test-100",
             "--root", str(self.root), "--as-of", AS_OF.isoformat(), "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        self.assertEqual(json.loads(restarted.stdout)["pending_question"]["id"], "q1")
        self.assertNotIn("answer_position_deck", restarted.stdout)
        self.assertEqual(coverage.read_json(self.path)["answer_position_deck"], position_deck(1))

    def test_position_deck_rejects_bad_shape_balance_runs_and_cursors(self):
        self.prepare_positions()
        invalid = [
            None, {}, dict(position_deck(), extra=True),
            dict(position_deck(), kind="random"), dict(position_deck(), positions=[]),
            dict(position_deck(), positions="BACD" * 3),
            dict(position_deck(), positions=["X"] * 12),
            dict(position_deck(), positions=[None] * 12),
            dict(position_deck(), positions=list("BACD" * 2)),
            dict(position_deck(), positions=list("AB" * 6)),
            dict(position_deck(), positions=list("AAABBBCCCDDD")),
            dict(position_deck(), cursor=-1), dict(position_deck(), cursor=1),
            dict(position_deck(), cursor=True), dict(position_deck(), cursor=0.0),
        ]
        for deck in invalid:
            with self.subTest(deck=deck):
                self.state["answer_position_deck"] = deck
                self.assertEqual(self.save()[0], 2)
                self.assertFalse(self.path.exists())

    def test_position_deck_locks_future_positions_kind_and_presence(self):
        self.prepare_positions(1)
        self.lock_position_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        original = deepcopy(self.state)
        for change in ("positions", "kind", "removal"):
            with self.subTest(change=change):
                self.state = deepcopy(original)
                if change == "positions":
                    self.state["answer_position_deck"]["positions"][1:3] = ["C", "A"]
                elif change == "kind":
                    self.state["answer_position_deck"]["kind"] = "planned"
                else:
                    del self.state["answer_position_deck"]
                self.assertEqual(self.save()[0], 2)
                self.assertEqual(self.path.read_bytes(), before)

    def test_position_deck_rejects_mismatched_question_key_and_skipped_cursor(self):
        self.prepare_positions(1)
        self.state["items"][0]["private_key"] = ["A"]
        self.assertIn("locked answer position", self.save()[2])
        self.state["items"][0]["private_key"] = ["B"]
        self.state["answer_position_deck"]["cursor"] = 2
        self.assertIn("Deck cursor", self.save()[2])
        self.assertFalse(self.path.exists())

    def test_position_deck_replenishes_only_after_saved_batch_is_consumed(self):
        self.prepare_positions(1)
        self.lock_position_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        self.state["answer_position_deck"]["positions"] += list("BACD" * 3)
        self.assertIn("exhausting", self.save()[2])
        self.assertEqual(self.path.read_bytes(), before)
        self.prepare_positions(12)
        self.assertEqual(self.save()[0], 0)
        self.state["answer_position_deck"]["positions"] += list("CDAB" * 3)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(len(coverage.read_json(self.path)["answer_position_deck"]["positions"]), 24)
        self.state["items"].append(positioned_question(12, "C"))
        self.state["answer_position_deck"]["cursor"] = 13
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(coverage.read_json(self.path)["answer_position_deck"]["cursor"], 13)
        self.state["answer_position_deck"]["positions"] += list("BACD" * 3)
        self.assertIn("exhausting", self.save()[2])

    def test_position_deck_rejects_multiple_batches_and_boundary_triples(self):
        self.prepare_positions()
        self.state["answer_position_deck"]["positions"] *= 2
        self.assertIn("one 12-position batch", self.save()[2])
        self.prepare_positions(12, positions=list("ABCDABCDABDC"))
        self.lock_position_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        self.state["answer_position_deck"]["positions"] += list("CCABDBADABDC")
        self.assertIn("three consecutive", self.save()[2])
        self.assertEqual(self.path.read_bytes(), before)
        self.state["answer_position_deck"]["positions"] = list("ABCDABCDABDC") + list("BACD" * 6)
        self.assertIn("one 12-position batch", self.save()[2])

    def test_position_deck_pause_cannot_replenish_and_planned_deck_cannot_extend(self):
        self.prepare_positions(12)
        self.lock_position_checkpoint()
        self.assertEqual(self.save()[0], 0)
        self.state["answer_position_deck"]["positions"] += list("BACD" * 3)
        self.state["paused"] = True
        self.assertIn("Pause cannot", self.save()[2])
        self.path.unlink()
        self.state["paused"] = False
        self.prepare_positions(12, kind="planned")
        self.lock_position_checkpoint()
        self.assertEqual(self.save()[0], 0)
        self.state["answer_position_deck"]["positions"] += list("BACD" * 3)
        self.assertIn("Append one", self.save()[2])

    def test_position_deck_mock_can_lock_positions_before_full_manifest(self):
        self.mock_unit()
        self.state["mode"] = "mock"
        positions = list("BACDBACDBA")
        self.prepare_positions(kind="planned", positions=positions)
        self.assertEqual(self.save()[0], 0)
        self.prepare_positions(1, kind="planned", positions=positions)
        self.assertIn("complete mock manifest", self.save()[2])
        self.prepare_positions(10, kind="planned", positions=positions)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(len(coverage.read_json(self.path)["items"]), 10)
        self.state["answer_position_deck"]["positions"] += ["C", "D"]
        self.prepare_positions(12, kind="planned")
        self.assertEqual(self.save()[0], 2)

    def test_position_deck_legacy_checkpoint_is_not_silently_reconstructed(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "reask_pending")
        before = self.path.read_bytes()
        self.state["answer_position_deck"] = position_deck()  # The two-option legacy item takes no position.
        self.assertIn("legacy questions", self.save()[2])
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        self.state.pop("answer_position_deck")
        self.state.update(items=[], next_action="resume_phase")
        self.assertEqual(self.save()[0], 0)
        self.state["answer_position_deck"] = position_deck()
        self.assertEqual(self.save()[0], 0)

    def test_position_deck_corrections_reuse_original_item_index_without_consuming_positions(self):
        self.prepare_positions(1)
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer()
        self.replacement()
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(coverage.read_json(self.path)["answer_position_deck"], position_deck(1))
        self.assertEqual(len(coverage.read_json(self.path)["items"][0]["history"]), 1)
        self.state["answer_position_deck"]["cursor"] = 2
        self.assertIn("Deck cursor", self.save()[2])

    def test_new_session_cannot_bypass_initial_position_batch_limit(self):
        self.state.update(items=[], phase="complete", next_action="session_complete")
        self.assertEqual(self.save()[0], 0)
        self.state.update(session_id="session2", phase="warm_up",
                          current_unit_id=None, allocation_category=None)
        self.prepare_positions()
        self.state["answer_position_deck"]["positions"] *= 2
        self.assertIn("one 12-position batch", self.save()[2])
        self.prepare_positions()
        self.assertEqual(self.save()[0], 0)

    def test_position_deck_multiselect_keeps_verified_key_without_consuming_a_position(self):
        self.prepare_positions(1)
        self.lock_position_checkpoint()
        self.state["items"][0]["private_key"] = ["A", "C"]
        self.assertIn("Deck cursor", self.save()[2])
        self.state["answer_position_deck"]["cursor"] = 0
        self.assertEqual(self.save()[0], 0)
        persisted = coverage.read_json(self.path)
        self.assertEqual(persisted["items"][0]["private_key"], ["A", "C"])
        self.assertEqual(persisted["answer_position_deck"]["cursor"], 0)

    def commit_answer(self, item=None):
        item = item or self.state["items"][0]
        row = {
            "id": item["attempt_id"], "session_id": "session1",
            "timestamp": item["response"]["timestamp"], "blueprint_revision": "v1",
            "subskill_ids": ["s1"], "result": "correct", "assistance": "unaided",
            "context": "mock" if self.state["mode"] == "mock" else "cold",
            "response_ref": item["response"]["response_ref"], "genuine_confirmed": True,
            "reasoning_demonstrated": True, "novel": True, "diagnosis": "none", "action": "",
        }
        self.ledger["attempts"].append(row)
        self.write(self.ledger_path, self.ledger)

    def void_answer(self, aid="a1", reason_kind="disowned_answer"):
        reference = (
            next(row["response_ref"] for row in self.ledger["attempts"] if row["id"] == aid)
            if reason_kind == "invalid_item" else f"genuine-user-turn:void-{aid}"
        )
        self.ledger["voided_attempts"].append({
            "id": f"void-{aid}", "attempt_id": aid, "reason_kind": reason_kind,
            "reason": "Confirmed correction", "response_ref": reference,
            "timestamp": "2026-10-03T12:00:00Z", "genuine_confirmed": True,
            "source_ref": "https://learn.microsoft.com/fixture-defect",
        })
        self.write(self.ledger_path, self.ledger)

    def test_checkpoint_reflects_voided_completion_and_same_unit_resume(self):
        item = self.state["items"][0]
        self.prepare_checkpoint()
        answer(item)
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.ledger["attempts"][0]["unit_id"] = "u1"
        self.ledger["unit_events"] = [{
            "id": "done", "unit_id": "u1", "status": "completed",
            "timestamp": "2026-10-02T12:05:00Z", "reason": "Completed with genuine answer",
        }]
        self.write(self.ledger_path, self.ledger)
        self.state.update(
            ledger_sha256=coverage.digest(self.ledger_path),
            applied_attempt_ids=["a1"], next_action="review_recorded",
        )
        item["grading"] = "applied"
        code, _, err = self.save()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.resume()["unit_lifecycle"], "completed")
        self.void_answer()
        result = self.resume()
        self.assertEqual(result["unit_lifecycle"], "interrupted")
        self.assertEqual(result["next_action"], "reask_disowned")
        self.ledger["unit_events"].append({
            "id": "resume", "unit_id": "u1", "status": "started",
            "timestamp": "2026-10-03T13:00:00Z", "reason": "Resume after genuine correction",
        })
        self.write(self.ledger_path, self.ledger)
        self.assertEqual(self.resume()["unit_lifecycle"], "started")
        self.assertEqual(len(self.ledger["study_units"]), 1)

    def replacement(self, position=0, invalid=False):
        original = deepcopy(self.state["items"][position])
        replacement = deepcopy(original)
        replacement.update(
            id=original["id"] + "-v2", response=None, attempt_id=None,
            grading="deferred" if self.state["mode"] == "mock" else "pending", review="pending",
            history=original.get("history", []) + [{
                "void_id": f"void-{original['attempt_id']}",
                "item": {key: value for key, value in original.items() if key != "history"},
            }],
        )
        if invalid:
            replacement["stem"] = "Which service satisfies these corrected constraints?"
            replacement["options"][0]["text"] = "Revised first service"
            replacement["private_rationale"] = "PRIVATE REVISED RATIONALE"
        self.state["items"][position] = replacement
        self.state.update(
            question_index=position, paused=False, next_action="reask_pending",
            ledger_sha256=coverage.digest(self.ledger_path),
            applied_attempt_ids=[row["id"] for row in self.ledger["attempts"]],
            applied_void_ids=[row["id"] for row in self.ledger["voided_attempts"]],
        )
        return original

    def test_unanswered_pause_reasks_exact_locked_item_and_never_mutates(self):
        self.state["paused"] = True
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = {p: p.read_bytes() for p in (self.path, self.ledger_path)}
        result = self.resume()
        self.assertEqual(result["next_action"], "reask_pending")
        self.assertEqual(result["current_unit_id"], "u1")
        self.assertEqual(result["unit_lifecycle"], "started")
        self.assertEqual(result["pending_question"]["stem"], self.state["items"][0]["stem"])
        self.assertEqual(result["pending_question"]["options"], self.state["items"][0]["options"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        for flag in ([], ["--json"]):
            code, out, err = self.call("resume", *flag)
            self.assertEqual(code, 0, err)
            self.assertNotIn("PRIVATE SOLUTION SENTINEL", out)
            self.assertNotIn("private_key", out)
            self.assertNotIn("private_rationale", out)
            self.assertNotIn('"correct"', out)

    def test_answered_pause_resumes_grading_not_question(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state.update(paused=True, next_action="grade_recorded")
        self.assertEqual(self.save()[0], 0)
        result = self.resume()
        self.assertEqual(result["next_action"], "grade_recorded")
        self.assertNotIn("pending_question", result)
        self.assertNotIn("GENUINE PRIVATE ANSWER SENTINEL", self.call("resume", "--json")[1])
        self.assertEqual(self.ledger["attempts"], [])

    def test_save_on_stop_never_prints_an_exit_question(self):
        self.state["paused"] = True
        self.seed_legacy_checkpoint()
        code, out, err = self.save()
        self.assertEqual(code, 0, err)
        self.assertNotIn(self.state["items"][0]["stem"], out)
        self.assertNotIn("pending_question", out)

    def test_deferred_mock_pause_has_no_premature_grading_or_solution(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)])
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state.update(paused=True, next_action="continue_mock")
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "continue_mock")
        self.assertNotIn("PRIVATE SOLUTION SENTINEL", self.call("resume", "--json")[1])
        self.commit_answer()
        code, _, err = self.call("resume")
        self.assertEqual(code, 2)
        self.assertIn("incomplete mock", err)

    def test_completed_mock_resumes_deferred_grading_without_regrading(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)])
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "continue_mock"
        self.assertEqual(self.save()[0], 0)
        self.state.update(question_index=1, next_action="reask_pending")
        self.assertEqual(self.save()[0], 0)
        answer(self.state["items"][1], "a2", "2026-10-02T12:01:00Z")
        self.state.update(question_index=1, next_action="grade_deferred")
        self.assertEqual(self.save()[0], 0)
        self.state["paused"] = True
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "grade_deferred")
        self.commit_answer(self.state["items"][0])
        result = self.resume()
        self.assertEqual(result["next_action"], "reconcile_ledger")
        self.assertEqual(result["committed_attempt_ids"], ["a1"])

    def test_wrong_exam_revision_and_missing_fields_fail_explicitly(self):
        for field, value, message in [
            ("exam", "other", "another exam"),
            ("blueprint_revision", "old", "revision changed"),
            ("question_index", True, "question_index"),
        ]:
            with self.subTest(field=field):
                invalid = deepcopy(self.state)
                invalid[field] = value
                code, _, err = self.save(invalid)
                self.assertEqual(code, 2)
                self.assertIn(message, err)
        invalid = deepcopy(self.state)
        del invalid["current_unit_id"]
        self.assertIn("missing or unknown fields", self.save(invalid)[2])

    def test_mock_metadata_round_trips_without_public_leakage(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)])
        for item in self.state["items"]:
            item["private_metadata"] = metadata()
        self.seed_legacy_checkpoint()
        code, saved, err = self.save()
        self.assertEqual(code, 0, err)
        self.assertEqual(coverage.read_json(self.path)["items"], self.state["items"])
        for flags in ([], ["--json"]):
            code, out, err = self.call("resume", *flags)
            self.assertEqual(code, 0, err)
            for secret in ("PRIVATE", "private_metadata", "verification", "source_id", "subskill_ids"):
                self.assertNotIn(secret, out + saved)
        self.assertEqual(set(self.resume()["pending_question"]), {"id", "stem", "options"})
        answer(self.state["items"][0])
        self.state.update(paused=True, next_action="continue_mock")
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(coverage.read_json(self.path)["items"][0]["private_metadata"], metadata())
        self.assertEqual(self.resume()["next_action"], "continue_mock")

    def test_private_metadata_rejects_incomplete_unknown_and_inconsistent_fields(self):
        invalid_metadata = [None, {}, dict(metadata(), extra="bad")]
        for field in metadata():
            row = metadata()
            del row[field]
            invalid_metadata.append(row)
        for changes in (
            {"source_id": ""}, {"topic": " "}, {"domain_id": "other"},
            {"subskill_ids": []}, {"subskill_ids": ["missing"]}, {"subskill_ids": ["s1", "s1"]},
        ):
            invalid_metadata.append(dict(metadata(), **changes))
        for row in invalid_metadata:
            with self.subTest(metadata=row):
                state = deepcopy(self.state)
                state["items"][0]["private_metadata"] = row
                self.assertEqual(self.save(state)[0], 2)
                self.assertFalse(self.path.exists())

    def test_verification_snapshot_rejects_bad_dates_urls_and_empty_claims(self):
        invalid = [None, {}, dict(metadata()["verification"], extra="bad")]
        for field, value in (
            ("claim", ""), ("constraints", " "), ("rationale", ""),
            ("checked_at", "bad-date"), ("checked_at", "2099-01-01"),
            ("url", "http://learn.microsoft.com/page"), ("url", "https://example.com/page"),
            ("url", "https://learn.microsoft.com.evil.test/page"),
            ("url", "https://user@learn.microsoft.com/page"), ("url", "https://[broken"),
        ):
            invalid.append(dict(metadata()["verification"], **{field: value}))
        for snapshot in invalid:
            with self.subTest(snapshot=snapshot):
                state = deepcopy(self.state)
                state["items"][0]["private_metadata"] = dict(metadata(), verification=snapshot)
                self.assertEqual(self.save(state)[0], 2)
                self.assertFalse(self.path.exists())
        state = deepcopy(self.state)
        state["items"][0]["private_metadata"] = metadata()
        state["items"][0]["private_metadata"]["verification"]["url"] = "https://docs.github.com/en/copilot"
        self.seed_legacy_checkpoint(state)
        self.assertEqual(self.save(state)[0], 0)

    def test_framework_authorities_are_not_enabled_for_other_exams(self):
        for exam in ("az-104", "az-305", "gh-300", "test-100"):
            fixture = deepcopy(self.catalog)
            fixture["exam"] = exam
            for url in (
                "https://docs.langchain.com/", "https://python.langchain.com/",
                "https://js.langchain.com/", "https://langchain-ai.github.io/langgraph/",
                "https://huggingface.co/docs/transformers/", "https://modelcontextprotocol.io/",
            ):
                with self.subTest(exam=exam, url=url):
                    row = metadata()
                    row["verification"]["url"] = url
                    with self.assertRaisesRegex(
                        coverage.CoverageError, "first-party HTTPS documentation",
                    ):
                        session.validate_metadata(row, fixture, AS_OF)

    def test_metadata_subskills_must_match_declared_domain(self):
        second = deepcopy(self.catalog["domains"][0])
        self.catalog["domains"][0].update(weight_min=50, weight_max=50)
        second.update(id="d2", weight_min=50, weight_max=50)
        second["objectives"][0].update(
            id="o2", subskills=[{"id": "s2", "title": "Second skill", "derived": True}],
        )
        self.catalog["domains"].append(second)
        self.write(self.base / "blueprint.json", self.catalog)
        self.state["items"][0]["private_metadata"] = metadata()
        self.state["items"][0]["private_metadata"]["subskill_ids"] = ["s2"]
        self.assertIn("do not belong", self.save()[2])

    def test_locked_metadata_cannot_be_edited_removed_or_added_to_legacy_item(self):
        self.state["items"][0]["private_metadata"] = metadata()
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        for field, value in (
            ("source_id", "different-source"), ("topic", "Different topic"),
            ("verification", dict(metadata()["verification"], rationale="Changed rationale")),
        ):
            state = deepcopy(self.state)
            state["items"][0]["private_metadata"][field] = value
            self.assertIn("private metadata cannot change", self.save(state)[2])
            self.assertEqual(self.path.read_bytes(), before)
        state = deepcopy(self.state)
        del state["items"][0]["private_metadata"]
        self.assertIn("private metadata cannot change", self.save(state)[2])
        self.path.unlink()
        self.seed_legacy_checkpoint(state)
        self.assertEqual(self.save(state)[0], 0)
        self.assertIn("private metadata cannot change", self.save()[2])

    def test_metadata_survives_disowned_and_invalid_item_history(self):
        self.state["items"][0]["private_metadata"] = metadata()
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer()
        original = self.replacement()
        changed = deepcopy(self.state)
        changed["items"][0]["private_metadata"]["topic"] = "Changed topic"
        self.assertIn("preserve private metadata", self.save(changed)[2])
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(coverage.read_json(self.path)["items"][0]["history"][0]["item"], original)
        answer(self.state["items"][0], "a2", "2026-10-04T10:00:00Z")
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.ledger["voided_attempts"].append({
            "id": "void-a2", "attempt_id": "a2", "reason_kind": "invalid_item",
            "reason": "Corrected constraint",
            "response_ref": next(row["response_ref"] for row in self.ledger["attempts"] if row["id"] == "a2"),
            "timestamp": "2026-10-04T11:00:00Z", "genuine_confirmed": True,
            "source_ref": "https://learn.microsoft.com/fixture-defect",
        })
        self.write(self.ledger_path, self.ledger)
        self.replacement(invalid=True)
        missing = deepcopy(self.state)
        del missing["items"][0]["private_metadata"]
        self.assertIn("cannot discard private metadata", self.save(missing)[2])
        self.state["items"][0]["private_metadata"]["verification"]["claim"] = "PRIVATE CORRECTED CLAIM"
        self.assertEqual(self.save()[0], 0)
        stored = coverage.read_json(self.path)["items"][0]
        self.assertEqual(len(stored["history"]), 2)
        self.assertEqual(stored["history"][0]["item"]["private_metadata"], metadata())
        self.assertEqual(stored["history"][1]["item"]["private_metadata"], metadata())
        self.assertNotIn("PRIVATE", self.call("resume", "--json")[1])
        tampered = deepcopy(self.state)
        tampered["items"][0]["history"][0]["item"]["private_metadata"]["topic"] = "Changed history"
        self.assertEqual(self.save(tampered)[0], 2)

    def test_invalid_legacy_item_can_gain_metadata_without_rewriting_old_history(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer(reason_kind="invalid_item")
        original = self.replacement(invalid=True)
        self.state["items"][0]["private_metadata"] = metadata()
        self.assertEqual(self.save()[0], 0)
        item = coverage.read_json(self.path)["items"][0]
        self.assertEqual(item["history"][0]["item"], original)
        self.assertNotIn("private_metadata", item["history"][0]["item"])
        self.assertEqual(item["private_metadata"], metadata())
        self.assertEqual(self.resume()["next_action"], "reask_pending")

    def test_immutable_stem_options_key_order_and_manifest(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        changes = [
            {"stem": "Changed question"}, {"options": list(reversed(self.state["items"][0]["options"]))},
            {"private_key": ["A"]}, {"private_rationale": "Changed rationale"},
        ]
        for change in changes:
            with self.subTest(change=change):
                invalid = deepcopy(self.state)
                invalid["items"][0].update(change)
                code, _, err = self.save(invalid)
                self.assertEqual(code, 2)
                self.assertIn("Locked question", err)

    def test_lost_or_corrupt_state_is_not_reconstructed(self):
        code, out, err = self.call("resume")
        self.assertEqual(code, 2)
        self.assertIn("Missing checkpoint", err)
        self.assertEqual(out, "")
        self.path.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.call("resume")[0], 2)
        self.assertEqual(self.save()[0], 2)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{broken")

    def test_stale_checkpoint_hash_and_ledger_hash_reject_overwrite(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        original = self.path.read_bytes()
        self.assertEqual(self.save(expected="missing")[0], 2)
        self.assertEqual(self.save(expected="f" * 64)[0], 2)
        self.state["ledger_sha256"] = "f" * 64
        self.assertIn("Ledger changed", self.save()[2])
        self.assertEqual(self.path.read_bytes(), original)

    def test_failed_atomic_replace_preserves_checkpoint_and_cleans_temp(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        original = self.path.read_bytes()
        self.state["paused"] = True
        with patch.object(coverage.os, "replace", side_effect=OSError("disk unavailable")):
            code, out, err = self.save()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("disk unavailable", err)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.assets.glob("*.tmp")), [])
        self.assertFalse(self.path.with_suffix(".json.lock").exists())
        self.assertEqual(self.save()[0], 0)

    def test_ledger_write_then_interruption_reconciles_without_duplicate(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        ledger_before = self.ledger_path.read_bytes()
        result = self.resume()
        self.assertEqual(result["next_action"], "reconcile_ledger")
        self.assertEqual(result["committed_attempt_ids"], ["a1"])
        self.assertEqual(self.ledger_path.read_bytes(), ledger_before)
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.state["applied_attempt_ids"] = ["a1"]
        self.state["items"][0]["grading"] = "applied"
        self.state["next_action"] = "review_recorded"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "review_recorded")
        self.assertEqual(self.ledger_path.read_bytes(), ledger_before)

    def test_matching_hash_does_not_hide_unacknowledged_ledger_attempt(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "reconcile_ledger")

    def test_ledger_conflict_cannot_supply_or_replace_a_genuine_response(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.ledger["attempts"][0]["response_ref"] = "some-other-answer"
        self.write(self.ledger_path, self.ledger)
        code, out, err = self.call("resume")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("conflicts with the ledger", err)

    def test_void_after_interrupted_write_requires_resolution_not_regrade(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.ledger["voided_attempts"] = [{
            "id": "v1", "attempt_id": "a1", "reason": "User disowned answer",
            "response_ref": "genuine-user-turn:void1", "genuine_confirmed": True,
            "timestamp": "2026-10-03T12:00:00Z",
        }]
        self.write(self.ledger_path, self.ledger)
        result = self.resume()
        self.assertEqual(result["next_action"], "reask_disowned")
        self.assertEqual(result["committed_void_ids"], ["v1"])
        self.assertTrue(result["reconciliation_needed"])
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1"], applied_void_ids=["v1"])
        self.state["items"][0]["grading"] = "applied"
        self.state["next_action"] = "review_recorded"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "reask_disowned")
        self.state["items"][0]["response"]["response_ref"] = "invented-replacement"
        self.assertEqual(self.save()[0], 2)

    def test_unconfirmed_future_duplicate_and_conflicting_answers_rejected(self):
        for response in [
            {"response_ref": "", "timestamp": "2026-10-02T12:00:00Z", "genuine_confirmed": True},
            {"response_ref": "ref", "timestamp": "2026-10-02T12:00:00Z", "genuine_confirmed": False},
            {"response_ref": "ref", "timestamp": "2099-10-02T12:00:00Z", "genuine_confirmed": True},
        ]:
            with self.subTest(response=response):
                invalid = deepcopy(self.state)
                invalid["items"][0].update(response=response, attempt_id="a1")
                invalid["next_action"] = "grade_recorded"
                self.assertEqual(self.save(invalid)[0], 2)
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.state["items"][0]["response"]["response_ref"] = "different-user-turn"
        self.assertIn("Conflicting recorded answer", self.save()[2])

    def test_future_as_of_rejected_for_checkpoint_and_resume_without_mutation(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        ledger_before = self.ledger_path.read_bytes()
        for command in ("checkpoint", "resume"):
            with self.subTest(command=command):
                code, out, err = self.call(
                    command, "--as-of", "9999-12-31", "--input", str(self.input),
                    "--expected-sha256", coverage.digest(self.path),
                )
                self.assertEqual(code, 2)
                self.assertIn("as-of cannot be later", err)
                self.assertEqual(out, "")
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.ledger_path.read_bytes(), ledger_before)
                self.assertEqual(set(self.assets.iterdir()), {self.path, self.ledger_path})
        self.path.unlink()
        code, _, err = self.call("checkpoint", "--as-of", "9999-12-31")
        self.assertEqual(code, 2)
        self.assertIn("as-of cannot be later", err)
        self.assertFalse(self.path.exists())

    def test_future_response_and_termination_cannot_be_saved_with_future_as_of(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True)])
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        ledger_before = self.ledger_path.read_bytes()
        answer(self.state["items"][0], timestamp="2099-01-01T12:00:00Z")
        self.state["next_action"] = "grade_deferred"
        for terminated in (False, True):
            with self.subTest(terminated=terminated):
                if terminated:
                    self.state.update(phase="aborted_review", termination={
                        "intent": "end_and_review", "response_ref": "fixture:end",
                        "timestamp": "2099-01-02T12:00:00Z", "genuine_confirmed": True,
                        "text": "End and review.", "flags": [],
                    })
                self.write(self.input, self.state)
                code, out, err = self.call(
                    "checkpoint", "--as-of", "2099-01-03", "--input", str(self.input),
                    "--expected-sha256", coverage.digest(self.path),
                )
                self.assertEqual(code, 2)
                self.assertIn("as-of cannot be later", err)
                self.assertEqual(out, "")
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.ledger_path.read_bytes(), ledger_before)

    def test_today_checkpoint_rejects_response_or_termination_ahead_of_real_clock(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True)])
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        before = self.path.read_bytes()
        now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
        for terminated in (False, True):
            with self.subTest(terminated=terminated):
                answer(self.state["items"][0], timestamp=(
                    "2026-10-05T11:00:00Z" if terminated else "2026-10-05T13:00:00Z"
                ))
                self.state["next_action"] = "grade_deferred"
                if terminated:
                    self.state.update(phase="aborted_review", termination={
                        "intent": "end_and_review", "response_ref": "fixture:end",
                        "timestamp": "2026-10-05T13:00:00Z", "genuine_confirmed": True,
                        "text": "End and review.", "flags": [],
                    })
                self.write(self.input, self.state)
                with patch.object(coverage, "datetime", wraps=datetime) as clock:
                    clock.now.return_value = now
                    code, out, err = self.call(
                        "checkpoint", "--as-of", "2026-10-05", "--input", str(self.input),
                        "--expected-sha256", coverage.digest(self.path),
                    )
                self.assertEqual(code, 2)
                self.assertIn("real clock", err)
                self.assertEqual(out, "")
                self.assertEqual(self.path.read_bytes(), before)

    def test_pause_does_not_advance_or_create_a_question(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        self.state.update(paused=True, phase="remediation")
        self.assertIn("Pause must not advance", self.save()[2])
        self.state["phase"] = "warm_up"
        self.state["items"].append(question("q2"))
        self.state["items"][-1]["private_metadata"] = metadata()
        self.state["items"][-1]["unit_id"] = "u1"
        self.assertIn("Pause must not create", self.save()[2])

    def test_non_question_phase_can_pause_without_claiming_completion(self):
        self.state.update(mode="tutor", phase="teaching", paused=True, items=[],
                          next_action="resume_phase")
        self.assertEqual(self.save()[0], 0)
        result = self.resume()
        self.assertEqual(result["next_action"], "resume_phase")
        self.assertEqual(result["unit_lifecycle"], "started")
        self.assertEqual(self.ledger["attempts"], [])

    def test_interrupted_unit_status_comes_from_ledger_events_not_checkpoint_phase(self):
        self.state.update(mode="tutor", phase="teaching", paused=True, items=[],
                          next_action="resume_phase")
        self.ledger["unit_events"] = [{
            "id": "e1", "unit_id": "u1", "status": "interrupted",
            "timestamp": "2026-10-02T12:00:00Z", "reason": "Learner paused",
        }]
        self.write(self.ledger_path, self.ledger)
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["unit_lifecycle"], "interrupted")
        self.assertEqual(coverage.report(self.catalog, self.ledger, AS_OF)["next_action"],
                         "resume_unfinished")
        self.assertEqual(len(self.ledger["study_units"]), 1)

    def test_completed_unit_requires_ledger_evidence_not_session_phase(self):
        self.state.update(mode="tutor", phase="complete", items=[], next_action="session_complete")
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["unit_lifecycle"], "started")
        item = question()
        answer(item)
        self.commit_answer(item)
        self.ledger["attempts"][0]["unit_id"] = "u1"
        self.ledger["unit_events"] = [{
            "id": "e1", "unit_id": "u1", "status": "completed",
            "timestamp": "2026-10-03T12:00:00Z", "reason": "Learning evidence delivered",
        }]
        self.write(self.ledger_path, self.ledger)
        result = self.resume()
        self.assertEqual(result["next_action"], "reconcile_ledger")
        self.assertEqual(result["unit_lifecycle"], "completed")
        self.assertEqual(coverage.report(self.catalog, self.ledger, AS_OF)["completed_normal_units"], 1)

    def test_legacy_unit_can_resume_after_explicit_started_event(self):
        del self.ledger["study_units"][0]["lifecycle"]
        self.ledger["unit_events"] = [{
            "id": "e1", "unit_id": "u1", "status": "started",
            "timestamp": "2026-10-02T12:00:00Z", "reason": "Explicit legacy activity reconciliation",
        }]
        self.write(self.ledger_path, self.ledger)
        self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["unit_lifecycle"], "started")

    def test_paused_session_cannot_acquire_unconfirmed_continuation(self):
        self.state["paused"] = True
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertIn("explicitly resume", self.save()[2])
        self.state["paused"] = False
        self.assertEqual(self.save()[0], 0)

    def test_duplicate_or_out_of_order_mock_response_references_rejected(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)],
                          question_index=1, next_action="grade_deferred")
        answer(self.state["items"][0])
        answer(self.state["items"][1], "a2", "2026-10-02T11:00:00Z")
        self.assertIn("out of order", self.save()[2])
        self.state["items"][1]["response"] = deepcopy(self.state["items"][0]["response"])
        self.assertIn("reference reused", self.save()[2])

    def test_option_presentation_metadata_and_markup_rejected(self):
        for option in [
            {"key": "A", "text": "**Highlighted service**"},
            {"key": "A", "text": "Service", "correct": True},
        ]:
            invalid = deepcopy(self.state)
            invalid["items"][0]["options"][0] = option
            self.assertEqual(self.save(invalid)[0], 2)

    def test_mock_checkpoint_requires_mock_unit_and_does_not_consume_cycle(self):
        self.state.update(mode="mock", items=[question("q1", True)])
        for mode in ("normal", "override"):
            with self.subTest(mode=mode):
                self.ledger["study_units"][0].update(mode=mode, reason="Explicit test scope")
                self.write(self.ledger_path, self.ledger)
                self.state["ledger_sha256"] = coverage.digest(self.ledger_path)
                self.assertIn("mock mode differs", self.save()[2])
                self.assertFalse(self.path.exists())
        self.mock_unit()
        self.seed_legacy_checkpoint()
        code, _, err = self.save()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.resume()["mode"], "mock")
        report = coverage.report(self.catalog, coverage.read_json(self.ledger_path), AS_OF)
        self.assertEqual(report["normal_units"], 0)
        self.assertEqual(report["actual_allocation"], {})
        self.assertEqual(report["completed_normal_units"], 0)
        self.assertEqual(report["next_allocation"], "coverage")
        self.ledger["study_units"][0]["mode"] = "normal"
        self.write(self.ledger_path, self.ledger)
        self.assertIn("mock mode differs", self.call("resume")[2])

    def test_nonmock_checkpoint_cannot_reference_mock_unit(self):
        self.mock_unit()
        self.assertIn("mock mode differs", self.save()[2])

    def test_neutral_technical_options_round_trip_unchanged(self):
        options = [
            "Standard_D2s_v5", "*.json", "**/*.json", "x < 5", "x > 5",
            "List<string>", "Dictionary<string, List<int>>", "foo_bar_baz",
            "SELECT * FROM resources", "2 * 3", "user@example.com",
        ]
        self.state["items"][0]["options"] = [
            {"key": chr(ord("A") + i), "text": text} for i, text in enumerate(options)
        ]
        self.seed_legacy_checkpoint()
        code, _, err = self.save()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.resume()["pending_question"]["options"],
                         self.state["items"][0]["options"])

    def test_actual_presentation_markup_remains_rejected(self):
        for text in (
            "**Service**", "__Service__", "*Service*", "_Service_", "~~Service~~",
            "`Service`", "[Service](https://example.com)", "[Service][ref]",
            "![Service](image.png)", "![](image.png)", "<strong>Service</strong>", "<br>",
            "Service<BR>hint", 'Service<img src="highlight.png">',
            "text<em>Service</em>", "<!-- hidden -->", "# Service", "> Service",
            "- Service", "1. Service", '"Service"', "Service\nhighlight",
        ):
            with self.subTest(text=text):
                invalid = deepcopy(self.state)
                invalid["items"][0]["options"][0]["text"] = text
                self.assertIn("plain neutral text", self.save(invalid)[2])
                self.assertFalse(self.path.exists())

    def test_conflicting_session_and_legacy_unknown_unit_rejected(self):
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        other = deepcopy(self.state)
        other.update(session_id="different-session", current_unit_id=None,
                     allocation_category=None, items=[], next_action="resume_phase")
        self.assertIn("Conflicting active session", self.save(other)[2])
        del self.ledger["study_units"][0]["lifecycle"]
        self.write(self.ledger_path, self.ledger)
        self.assertIn("explicit started lifecycle", self.call("resume")[2])

    def test_legacy_reference_only_blocks_grading_until_actual_text_is_recovered(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        del self.state["items"][0]["response"]["text"]
        del self.state["items"][0]["response"]["flags"]
        self.assertIn("require genuine private text", self.save()[2])
        self.write(self.path, self.state)
        self.assertEqual(self.resume()["next_action"], "recover_response_text")
        self.assertEqual(self.ledger["attempts"], [])
        self.state["items"][0]["response"].update(text="Recovered exact user wording", flags=[])
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "grade_recorded")

    def test_genuine_text_and_flags_are_private_and_immutable(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        for args in ([], ["--json"]):
            code, out, err = self.call("resume", *args)
            self.assertEqual(code, 0, err)
            self.assertNotIn("GENUINE PRIVATE ANSWER SENTINEL", out)
            self.assertNotIn("flagged_for_review", out)
        self.state["items"][0]["response"]["flags"] = []
        self.assertIn("Conflicting recorded answer", self.save()[2])

    def test_disowned_answer_reasks_exact_then_preserves_history_when_reanswered(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer()
        result = self.resume()
        self.assertEqual(result["next_action"], "reask_disowned")
        self.assertEqual(result["pending_question"]["stem"], self.state["items"][0]["stem"])
        self.assertEqual(result["pending_question"]["options"], self.state["items"][0]["options"])
        original = self.replacement()
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "reask_pending")
        self.assertEqual(self.state["items"][0]["history"][0]["item"], original)
        answer(self.state["items"][0], "a2", "2026-10-04T12:00:00Z")
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.assertEqual(self.resume()["next_action"], "reconcile_ledger")
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1", "a2"], next_action="review_recorded")
        self.state["items"][0]["grading"] = "applied"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "review_recorded")
        self.assertEqual([row["id"] for row in self.ledger["attempts"]], ["a1", "a2"])
        self.assertEqual(self.state["items"][0]["private_key"], original["private_key"])

    def test_invalid_item_requires_replacement_not_an_unchanged_reask(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer(reason_kind="invalid_item")
        result = self.resume()
        self.assertEqual(result["next_action"], "replace_invalid_item")
        self.assertNotIn("pending_question", result)
        original = self.replacement(invalid=True)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["pending_question"]["stem"], self.state["items"][0]["stem"])
        self.assertEqual(self.state["items"][0]["history"][0]["item"], original)
        self.assertNotIn("PRIVATE REVISED RATIONALE", self.call("resume", "--json")[1])
        answer(self.state["items"][0], "a2", "2026-10-04T12:00:00Z")
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)

    def test_invalid_item_cannot_be_reissued_unchanged_under_a_new_id(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer(reason_kind="invalid_item")
        self.replacement()
        self.assertIn("corrected replacement", self.save()[2])

    def test_replacement_cannot_change_locked_answer_position_or_fabricate_an_answer(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer(reason_kind="invalid_item")
        self.replacement(invalid=True)
        valid = deepcopy(self.state)
        self.state["items"][0]["private_key"] = ["A"]
        self.assertIn("locked answer positions", self.save()[2])
        self.state = deepcopy(valid)
        answer(self.state["items"][0], "a2", "2026-10-04T12:00:00Z")
        self.state["next_action"] = "grade_recorded"
        self.assertIn("Persist replacement before", self.save()[2])
        self.state = deepcopy(valid)
        self.state["items"][0]["history"][0]["item"]["response"]["text"] = "Invented original"
        self.assertIn("preserve the exact original", self.save()[2])

    def test_disowned_question_cannot_be_changed_and_new_answer_must_follow_void(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "grade_recorded"
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer()
        self.replacement()
        correct_stem = self.state["items"][0]["stem"]
        self.state["items"][0]["stem"] = "An unrelated substitute"
        self.assertIn("exact unchanged question", self.save()[2])
        self.state["items"][0]["stem"] = correct_stem
        self.assertEqual(self.save()[0], 0)
        answer(self.state["items"][0], "a2", "2026-10-02T12:01:00Z")
        self.state["next_action"] = "grade_recorded"
        self.assertIn("predates confirmed void", self.save()[2])

    def test_mock_correction_keeps_original_item_index_and_other_genuine_answers(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)],
                          question_index=0, next_action="reask_pending")
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.state["next_action"] = "continue_mock"
        self.assertEqual(self.save()[0], 0)
        self.state.update(question_index=1, next_action="reask_pending")
        self.assertEqual(self.save()[0], 0)
        answer(self.state["items"][1], "a2", "2026-10-02T12:01:00Z")
        self.state["next_action"] = "grade_deferred"
        self.assertEqual(self.save()[0], 0)
        for item in self.state["items"]:
            self.commit_answer(item)
            item["grading"] = "applied"
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1", "a2"], next_action="review_recorded")
        self.assertEqual(self.save()[0], 0)
        original_second = deepcopy(self.state["items"][1])
        self.void_answer(reason_kind="invalid_item")
        self.assertEqual(self.resume()["recovery_question_index"], 0)
        self.replacement(invalid=True)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.state["items"][1], original_second)
        self.assertEqual(len(self.state["items"]), 2)
        self.assertEqual(self.resume()["next_action"], "reask_pending")
        answer(self.state["items"][0], "a3", "2026-10-04T12:00:00Z")
        self.state["next_action"] = "grade_deferred"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "grade_deferred")

    def test_in_progress_mock_can_recover_voided_unscored_invalid_item(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)],
                          next_action="continue_mock")
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.ledger["attempts"][0].update(result="unscored", reasoning_demonstrated=False)
        self.void_answer(reason_kind="invalid_item")
        self.assertEqual(self.resume()["next_action"], "replace_invalid_item")
        self.replacement(invalid=True)
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "reask_pending")
        skipped = deepcopy(self.state)
        skipped.update(question_index=1)
        self.assertIn("advance past an unanswered", self.save(skipped)[2])

    def invalidate_unanswered_mock_item(self):
        self.mock_unit()
        self.state.update(mode="mock", phase="mock")
        self.prepare_positions(0, "planned", list("BACD"))
        self.lock_position_checkpoint()
        self.prepare_positions(4, "planned", list("BACD"))
        self.state.update(question_index=0, next_action="reask_pending")
        self.assertEqual(self.save()[0], 0)
        for index in range(3):
            answer(self.state["items"][index], f"a{index + 1}", f"2026-10-02T12:0{index}:00Z")
            self.state["next_action"] = "continue_mock"
            self.assertEqual(self.save()[0], 0)
            self.state.update(question_index=index + 1, next_action="reask_pending")
            self.assertEqual(self.save()[0], 0)
        original = deepcopy(self.state["items"][3])
        revised = deepcopy(original)
        revised.update(id="q4-v2", stem="Which service satisfies these corrected constraints?")
        revised["history"] = [{
            "invalidation": {
                "id": "inv1", "reason_kind": "invalid_item", "reason": "Defective stem",
                "source_ref": "https://learn.microsoft.com/fixture-defect",
                "timestamp": "2026-10-02T12:10:00Z",
            },
            "item": {key: value for key, value in original.items() if key != "history"},
        }]
        self.state["items"][3] = revised
        self.assertEqual(self.save()[0], 0)
        for item in self.state["items"][:3]:
            self.commit_answer(item)
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1", "a2", "a3"])

    def test_journal_invalidation_does_not_unlock_grading_of_incomplete_mock(self):
        self.invalidate_unanswered_mock_item()
        for item in self.state["items"][:3]:
            item["grading"] = "applied"
        self.state["next_action"] = session.intended_action(self.state)
        code, _, err = self.save()
        self.assertEqual(code, 2)
        self.assertIn("Cannot grade an incomplete mock", err)

    def test_ledger_attempt_cannot_precede_its_journaled_answer(self):
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.commit_answer()
        self.state["items"][0]["grading"] = "applied"
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1"])
        self.state["next_action"] = session.intended_action(self.state)
        code, _, err = self.save()
        self.assertEqual(code, 2)
        self.assertIn("Journal the genuine answer before writing its ledger attempt", err)

    def test_explicit_mock_end_reviews_only_answered_items_without_new_questions(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)],
                          next_action="continue_mock")
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.assertEqual(self.save()[0], 0)
        self.state["paused"] = True
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "continue_mock")
        self.state.update(
            paused=False, phase="aborted_review", next_action="grade_deferred",
            termination={
                "intent": "end_and_review", "response_ref": "genuine-user-turn:end",
                "timestamp": "2026-10-02T12:05:00Z", "genuine_confirmed": True,
                "text": "End this mock now and review my answered items.", "flags": [],
            },
        )
        self.assertEqual(self.save()[0], 0)
        result = self.resume()
        self.assertEqual(result["next_action"], "grade_deferred")
        self.assertEqual(result["answered_count"], 1)
        self.assertEqual(result["unanswered_count"], 1)
        self.assertNotIn("pending_question", result)
        self.commit_answer()
        self.state.update(ledger_sha256=coverage.digest(self.ledger_path),
                          applied_attempt_ids=["a1"], next_action="review_recorded")
        self.state["items"][0]["grading"] = "applied"
        self.assertEqual(self.save()[0], 0)
        self.state["items"][0]["review"] = "complete"
        self.state["next_action"] = "finish_aborted_review"
        self.assertEqual(self.save()[0], 0)
        self.state.update(phase="complete", next_action="session_complete")
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(len(self.ledger["attempts"]), 1)
        self.assertIsNone(self.state["items"][1]["response"])
        self.assertEqual(self.state["items"][1]["grading"], "deferred")

    def test_aborted_review_without_explicit_genuine_end_intent_is_rejected(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True)], phase="aborted_review",
                          next_action="finish_aborted_review")
        self.assertIn("genuine termination intent", self.save()[2])
        self.state["termination"] = {
            "intent": "pause", "response_ref": "genuine-user-turn:stop",
            "timestamp": "2026-10-02T12:05:00Z", "genuine_confirmed": True,
            "text": "Stop for now.", "flags": [],
        }
        self.assertIn("end_and_review intent", self.save()[2])
        self.state["termination"]["intent"] = "end_and_review"
        self.state["termination"]["genuine_confirmed"] = False
        self.assertIn("genuine user confirmation", self.save()[2])

    def test_empty_ended_mock_finishes_without_assessment_and_cannot_accept_later_answers(self):
        self.mock_unit()
        self.state.update(
            mode="mock", phase="aborted_review", items=[question("q1", True)],
            next_action="finish_aborted_review",
            termination={
                "intent": "end_and_review", "response_ref": "genuine-user-turn:end",
                "timestamp": "2026-10-02T12:05:00Z", "genuine_confirmed": True,
                "text": "End and review what I answered.", "flags": [],
            },
        )
        self.seed_legacy_checkpoint()
        self.assertEqual(self.save()[0], 0)
        result = self.resume()
        self.assertEqual(result["answered_count"], 0)
        self.assertEqual(result["next_action"], "finish_aborted_review")
        self.assertNotIn("pending_question", result)
        answer(self.state["items"][0], timestamp="2026-10-02T12:04:00Z")
        self.state["next_action"] = "grade_deferred"
        self.assertIn("Ended mock cannot receive", self.save()[2])
        self.assertEqual(self.ledger["attempts"], [])

    def test_voided_answer_in_ended_mock_never_prompts_another_question(self):
        self.mock_unit()
        self.state.update(mode="mock", items=[question("q1", True), question("q2", True)],
                          next_action="continue_mock")
        self.prepare_checkpoint()
        answer(self.state["items"][0])
        self.assertEqual(self.save()[0], 0)
        self.state.update(
            phase="aborted_review", next_action="grade_deferred",
            termination={
                "intent": "end_and_review", "response_ref": "genuine-user-turn:end",
                "timestamp": "2026-10-02T12:05:00Z", "genuine_confirmed": True,
                "text": "End now and review.", "flags": [],
            },
        )
        self.assertEqual(self.save()[0], 0)
        self.commit_answer()
        self.void_answer()
        result = self.resume()
        self.assertEqual(result["next_action"], "resolve_voided_partial_review")
        self.assertNotIn("pending_question", result)
        self.replacement()
        self.state["next_action"] = "finish_aborted_review"
        self.assertEqual(self.save()[0], 0)
        self.assertEqual(self.resume()["next_action"], "finish_aborted_review")

    def test_default_root_is_repository_not_tests_or_skills(self):
        self.assertEqual(session.ROOT, Path(__file__).resolve().parents[4])


if __name__ == "__main__":
    unittest.main()
