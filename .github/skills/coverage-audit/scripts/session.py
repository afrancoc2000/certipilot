"""Save private study checkpoints and produce solution-free, read-only resume instructions."""

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import importlib.util
import itertools
import json
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit


SPEC = importlib.util.spec_from_file_location(
    "study_coverage_checkpoint", Path(__file__).with_name("coverage.py"),
)
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)
ROOT = Path(__file__).resolve().parents[4]
LOCKED = ("id", "stem", "options", "answer_order_locked", "private_key", "private_rationale")
MODES = {"quiz", "tutor", "follow_plan", "mock", "planner"}
ACTIONS = {
    "reask_pending", "grade_recorded", "continue_mock", "grade_deferred",
    "review_recorded", "advance_after_review", "resume_phase", "session_complete",
    "finish_aborted_review",
}
RESPONSE_FIELDS = {"response_ref", "timestamp", "genuine_confirmed"}
ITEM_FIELDS = set(LOCKED) | {"response", "attempt_id", "grading", "review"}
OPTIONAL_ITEM_FIELDS = {"private_metadata", "kind", "private_grading_criteria", "unit_id"}


def question_kind(item):
    return item.get("kind", "choice")


def locked_question(item):
    return dict(
        {key: item[key] for key in LOCKED},
        kind=question_kind(item), private_grading_criteria=item.get("private_grading_criteria"),
    )


def question_unit(item, attempts, fallback):
    if "unit_id" in item:
        return item["unit_id"]
    actual = attempts.get(item["attempt_id"])
    if actual is not None and actual.get("unit_id") is not None:
        return actual["unit_id"]
    if item.get("history"):
        return question_unit(item["history"][-1]["item"], attempts, fallback)
    return fallback


def mock_quotas(catalog, count):
    domains = catalog["domains"]
    coverage.require(type(count) is int and count >= len(domains),
                     "Mock length must allow at least one question per domain")
    weights = [Fraction(str(d["weight_min"])) + Fraction(str(d["weight_max"])) for d in domains]
    quotas = [count * weight / sum(weights) for weight in weights]
    counts = [max(1, quota.numerator // quota.denominator) for quota in quotas]
    while sum(counts) < count:
        index = max(range(len(domains)), key=lambda i: (quotas[i] - counts[i], -i))
        counts[index] += 1
    while sum(counts) > count:
        index = max((i for i in range(len(domains)) if counts[i] > 1),
                    key=lambda i: (counts[i] - quotas[i], -i))
        counts[index] -= 1
    return {domain["id"]: quota for domain, quota in zip(domains, counts)}


def validate_metadata(metadata, catalog, as_of, allow_legacy_sources=False):
    coverage.mapping(metadata, "private metadata")
    coverage.require(set(metadata) == {"source_id", "domain_id", "topic", "subskill_ids", "verification"},
                     "Private metadata has missing or unknown fields")
    coverage.text(metadata["source_id"], "source/bank item ID")
    coverage.text(metadata["topic"], "question topic")
    skills = {
        skill["id"]: domain["id"] for domain in catalog["domains"]
        for objective in domain["objectives"] for skill in objective["subskills"]
    }
    domain = coverage.choice(metadata["domain_id"], {d["id"] for d in catalog["domains"]},
                             "question domain")
    coverage.skill_refs(metadata, skills)
    coverage.require(all(skills[sid] == domain for sid in metadata["subskill_ids"]),
                     "Question subskills do not belong to its domain")
    verification = metadata["verification"]
    coverage.mapping(verification, "verification snapshot")
    coverage.require(set(verification) == {"claim", "constraints", "url", "checked_at", "rationale"},
                     "Verification snapshot has missing or unknown fields")
    for field in ("claim", "constraints", "rationale"):
        coverage.text(verification[field], f"verification {field}")
    try:
        url = urlsplit(coverage.text(verification["url"], "verification URL"))
    except ValueError as exc:
        raise coverage.CoverageError("Invalid verification URL") from exc
    authorities = {"learn.microsoft.com", "docs.github.com"}
    if catalog["exam"] == "ai-500":
        authorities.update({
            "docs.langchain.com", "python.langchain.com", "js.langchain.com",
            "langchain-ai.github.io", "huggingface.co", "modelcontextprotocol.io",
        })
    coverage.require(url.scheme == "https" and url.hostname in authorities
                     and url.username is None and url.password is None,
                     "Verification URL must be first-party HTTPS documentation")
    current_source = True
    if url.hostname == "huggingface.co":
        path = posixpath.normpath(unquote(url.path).replace("\\", "/"))
        current_source = path == "/docs/transformers" or path.startswith("/docs/transformers/")
        coverage.require(current_source or allow_legacy_sources,
                         "Hugging Face verification must use official Transformers documentation")
    checked = coverage.calendar_date(verification["checked_at"], "verification checked_at")
    coverage.require(checked <= as_of, "Verification date is after the as-of date")
    return current_source


def validate_position_deck(state):
    deck = coverage.mapping(state["answer_position_deck"], "answer-position deck")
    coverage.require(set(deck) == {"kind", "positions", "cursor"},
                     "Answer-position deck has missing or unknown fields")
    kind = coverage.choice(deck["kind"], {"planned", "open_ended"}, "answer-position deck kind")
    positions = coverage.array(deck["positions"], "answer positions")
    coverage.require(bool(positions), "Answer-position deck cannot be empty")
    for position in positions:
        coverage.choice(position, {"A", "B", "C", "D"}, "answer position")
    coverage.require(type(deck["cursor"]) is int, "Deck cursor must be an integer")
    coverage.require(not any(a == b == c for a, b, c in zip(positions, positions[1:], positions[2:])),
                     "Answer-position deck cannot contain three consecutive identical positions")
    if kind == "open_ended":
        coverage.require(len(positions) % 12 == 0, "Open-ended decks require complete 12-position batches")
    size = 12 if kind == "open_ended" else len(positions)
    for start in range(0, len(positions), size):
        counts = [positions[start:start + size].count(letter) for letter in "ABCD"]
        coverage.require(max(counts) - min(counts) <= 1, "Answer-position deck must be balanced")
    if state["mode"] == "mock":
        coverage.require(kind == "planned", "Mock requires a planned answer-position deck")


def takes_position(item):
    """Only four-option single-answer A/B/C/D items consume an answer position."""
    return ({option["key"] for option in item["options"]} == set("ABCD")
            and len(item["private_key"]) == 1)


def validate_position_cursor(state, versions):
    deck = state["answer_position_deck"]
    positions = deck["positions"]
    ordinals = list(itertools.accumulate((takes_position(item) for item in state["items"]), initial=0))
    coverage.require(deck["cursor"] == ordinals[-1] <= len(positions),
                     "Deck cursor must equal the number of prepared four-option single-answer "
                     "items and remain within the deck")
    for index, item, _ in versions:
        if takes_position(item):
            coverage.require(ordinals[index] < len(positions)
                             and item["private_key"] == [positions[ordinals[index]]],
                             "Question key differs from its locked answer position")
    if state["mode"] == "mock":
        coverage.require(not state["items"] or deck["cursor"] == len(positions),
                         "Save the complete mock manifest with one deck position per four-option single-answer item")


def validate_position_deck_update(old, new):
    before, after = old.get("answer_position_deck"), new.get("answer_position_deck")
    if before is None:
        coverage.require(after is None or not old["items"],
                         "Cannot reconstruct an answer-position deck for existing legacy questions")
        if not old["items"]:
            require_deck_only_preparation(new)
        if after is not None and after["kind"] == "open_ended":
            coverage.require(len(after["positions"]) == 12, "Start with one 12-position batch")
    else:
        coverage.require(after is not None, "Cannot discard the answer-position deck")
        coverage.require(before["kind"] == after["kind"], "Cannot change answer-position deck kind")
        previous, upcoming = before["positions"], after["positions"]
        coverage.require(upcoming[:len(previous)] == previous, "Locked answer positions cannot change")
        if upcoming != previous:
            coverage.require(before["kind"] == "open_ended"
                             and before["cursor"] == len(previous)
                             and len(upcoming) == len(previous) + 12,
                             "Append one 12-position batch only after exhausting the saved deck")
    if new["paused"]:
        coverage.require(before == after, "Pause cannot generate or consume answer positions")


def ids(value, label):
    rows = coverage.array(value, label)
    for row in rows:
        coverage.text(row, label)
    coverage.require(len(rows) == len(set(rows)), f"Repeated {label}")
    return set(rows)


def sha256(value, label):
    coverage.require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
                     f"{label}: expected SHA-256")
    return value


def unit_lifecycle(ledger, uid):
    if uid is None:
        return None
    return coverage.unit_lifecycles(ledger)[uid]


def neutral_option(text):
    markup = (
        r"`", r"\*\*(?=\S).+?(?<=\S)\*\*", r"(?<!\w)__(?=\S).+?(?<=\S)__(?!\w)",
        r"(?<!\*)\*(?!\*)(?=\S).+?(?<=\S)(?<!\*)\*(?!\*)",
        r"(?<!\w)_(?=\S).+?(?<=\S)_(?!\w)", r"~~(?=\S).+?(?<=\S)~~",
        r"!?\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])",
        r"^\s*(?:#{1,6}\s|>|[-+*]\s|\d+[.)]\s)",
        r'^\s*(?:"[^"]+"|\u201c[^\u201d]+\u201d|\u2018[^\u2019]+\u2019)\s*$',
        r"(?<!\w)<[A-Za-z][^<>]*>", r"</[A-Za-z][^<>]*>", r"<!--",
        r"(?i:<(?:area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)\b[^<>]*>)",
    )
    return not any(c in text for c in "\r\n") and not any(re.search(p, text) for p in markup)


def recorded_response(response, as_of, label):
    coverage.mapping(response, label)
    coverage.require(set(response) in (RESPONSE_FIELDS, RESPONSE_FIELDS | {"text", "flags"}),
                     f"{label}: expected provenance plus private text and flags")
    coverage.text(response["response_ref"], f"{label} reference")
    coverage.require(response["genuine_confirmed"] is True,
                     "Recorded answer requires genuine user confirmation")
    moment = coverage.timestamp(response["timestamp"])
    coverage.not_future(moment, as_of, label)
    if "text" in response:
        coverage.text(response["text"], f"{label} text")
        flags = ids(response["flags"], f"{label} flags")
        coverage.require(flags <= {"flagged_for_review", "uncertain", "time_expired"},
                         f"{label}: unknown response flag")
    return moment


def require_portable_response(item):
    if item["response"] is not None:
        coverage.require("text" in item["response"] and "flags" in item["response"],
                         "New recorded answers require genuine private text and flags")


def require_unanswered_preparation(item):
    coverage.require(item["response"] is None,
                     "New questions must be checkpointed unanswered before receiving a response")


def require_deck_only_preparation(state):
    coverage.require(not state["items"],
                     "Save the answer-position deck before preparing questions")


def history_correction(entry, voids, attempts, applied_voids, as_of):
    coverage.require(set(entry) in ({"void_id", "item"}, {"invalidation", "item"}),
                     "Invalid history entry")
    if "void_id" in entry:
        coverage.choice(entry["void_id"], voids, "history void ID")
        coverage.require(entry["void_id"] in applied_voids, "History void must be reconciled")
        return voids[entry["void_id"]]
    correction = coverage.mapping(entry["invalidation"], "journal invalidation")
    coverage.require(set(correction) == {"id", "reason_kind", "reason", "source_ref", "timestamp"},
                     "Journal invalidation has missing or unknown fields")
    coverage.text(correction["id"], "journal invalidation ID")
    coverage.require(correction["id"] not in voids, "Journal invalidation ID conflicts with ledger void")
    coverage.require(correction["reason_kind"] == "invalid_item",
                     "Journal invalidation requires invalid_item defect evidence")
    coverage.text(correction["reason"], "journal invalidation reason")
    coverage.text(correction["source_ref"], "journal invalidation source evidence")
    moment = coverage.timestamp(correction["timestamp"])
    coverage.not_future(moment, as_of, "Journal invalidation")
    original = coverage.mapping(entry["item"], "historical question")
    coverage.require(original.get("attempt_id") not in attempts and original.get("grading") != "applied",
                     "Journal-only invalidation cannot replace a ledger attempt")
    if original.get("response") is not None:
        coverage.require(moment >= recorded_response(original["response"], as_of, "Historical response"),
                         "Journal invalidation predates original response")
    return dict(correction, attempt_id=original.get("attempt_id"))


def validate_replacement(before, after, void):
    coverage.require(before["attempt_id"] == void["attempt_id"],
                     "Question history does not match its ledger void")
    coverage.require(before["id"] != after["id"], "Recovery requires a new question ID/version")
    coverage.require(question_kind(before) == question_kind(after),
                     "Replacement must retain its question kind")
    coverage.require(before["private_key"] == after["private_key"]
                     and [row["key"] for row in before["options"]]
                     == [row["key"] for row in after["options"]],
                     "Replacement must retain the original locked answer positions")
    if void.get("reason_kind", "disowned_answer") == "disowned_answer":
        coverage.require(
            {key: value for key, value in locked_question(before).items() if key != "id"}
            == {key: value for key, value in locked_question(after).items() if key != "id"},
                         "Disowned answer must reask the exact unchanged question and options")
        coverage.require(before.get("private_metadata") == after.get("private_metadata"),
                         "Disowned answer must preserve private metadata")
    else:
        coverage.require("private_metadata" not in before or "private_metadata" in after,
                         "Invalid-item replacement cannot discard private metadata")
        coverage.require(before["stem"] != after["stem"] or before["options"] != after["options"]
                         or (question_kind(before) == "free_response"
                             and before["private_grading_criteria"] != after["private_grading_criteria"]),
                         "Invalid item needs a corrected replacement, not an unchanged reask")


def intended_action(state):
    if state["phase"] == "complete":
        return "session_complete"
    if state["phase"] == "aborted_review":
        answered = [row for row in state["items"] if row["response"] is not None]
        if any(row["grading"] != "applied" for row in answered):
            return "grade_deferred"
        if any(row["review"] == "pending" for row in answered):
            return "review_recorded"
        return "finish_aborted_review"
    if not state["items"]:
        return "resume_phase"
    item = state["items"][state["question_index"]]
    if item["response"] is None:
        return "reask_pending"
    if state["mode"] == "mock" and any(row["response"] is None for row in state["items"]):
        return "continue_mock"
    if state["mode"] == "mock":
        if any(row["grading"] != "applied" for row in state["items"]):
            return "grade_deferred"
        if any(row["review"] == "pending" for row in state["items"]):
            return "review_recorded"
    if item["grading"] != "applied":
        return "grade_deferred" if state["mode"] == "mock" else "grade_recorded"
    if item["review"] == "pending":
        return "review_recorded"
    return "advance_after_review"


def validate(state, catalog, ledger, as_of, allow_legacy_sources=False):
    coverage.mapping(state, "checkpoint")
    required = {
        "schema_version", "exam", "blueprint_revision", "session_id", "mode", "phase",
        "paused", "ledger_sha256", "applied_attempt_ids", "applied_void_ids",
        "pending_check_ids", "current_unit_id", "allocation_category",
        "items", "question_index", "next_action",
    }
    coverage.require(required <= set(state) <= required
                     | {"termination", "answer_position_deck", "private_planning"},
                     "Checkpoint has missing or unknown fields")
    coverage.require(type(state.get("schema_version")) is int and state["schema_version"] == 1,
                     "Unsupported checkpoint schema")
    coverage.require(state.get("exam") == catalog["exam"], "Checkpoint belongs to another exam")
    coverage.require(state.get("blueprint_revision") == catalog["revision"],
                     "Checkpoint blueprint revision changed; reconcile explicitly")
    session_id = coverage.text(state.get("session_id"), "session_id")
    coverage.choice(state.get("mode"), MODES, "session mode")
    coverage.text(state.get("phase"), "phase")
    coverage.boolean(state.get("paused"), "paused")
    if state["mode"] == "planner":
        proposal = coverage.mapping(state.get("private_planning"), "private planning proposal")
        coverage.require(set(proposal) == {"plan_filename", "proposal"},
                         "Planning proposal has missing or unknown fields")
        filename = coverage.text(proposal["plan_filename"], "plan filename")
        coverage.require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\.md", filename) is not None,
                         "Plan filename must be a local Markdown filename")
        coverage.text(proposal["proposal"], "planning proposal")
        coverage.require(state["phase"] in {"planning", "complete"}
                         and not state["items"] and state["current_unit_id"] is None
                         and state["allocation_category"] is None
                         and not state["applied_attempt_ids"] and not state["applied_void_ids"]
                         and "answer_position_deck" not in state,
                         "Planner checkpoints cannot contain quiz items or fabricated learning activity")
    else:
        coverage.require("private_planning" not in state,
                         "Private planning proposal requires planner mode")
    termination = state.get("termination")
    termination_time = None
    if termination is not None:
        coverage.mapping(termination, "termination")
        coverage.require(set(termination) == RESPONSE_FIELDS | {"text", "flags", "intent"}
                         and termination["intent"] == "end_and_review",
                         "Partial review requires explicit end_and_review intent")
        termination_time = recorded_response(
            {key: value for key, value in termination.items() if key != "intent"},
            as_of, "Termination",
        )
        coverage.require(state["mode"] == "mock" and state["phase"] in {"aborted_review", "complete"}
                         and not state["paused"],
                         "Termination intent belongs only to an explicitly ended mock")
    if state["phase"] == "aborted_review":
        coverage.require(termination is not None, "Aborted review requires genuine termination intent")
    sha256(state.get("ledger_sha256"), "ledger_sha256")
    applied = ids(state.get("applied_attempt_ids"), "applied attempt IDs")
    applied_voids = ids(state.get("applied_void_ids"), "applied void IDs")
    checks = ids(state.get("pending_check_ids"), "pending check IDs")
    attempts = {row["id"]: row for row in ledger["attempts"]}
    voids = {row["id"]: row for row in ledger.get("voided_attempts", [])}
    coverage.require(applied <= attempts.keys(), "Applied attempt is missing from ledger")
    coverage.require(applied_voids <= voids.keys(), "Applied void is missing from ledger")
    coverage.require(checks <= {row["id"] for row in ledger["pending_checks"]},
                     "Unknown pending check ID")
    coverage.require(all(attempts[aid]["session_id"] == session_id for aid in applied),
                     "Applied attempt belongs to another session")
    coverage.require(all(attempts[voids[vid]["attempt_id"]]["session_id"] == session_id
                         for vid in applied_voids), "Applied void belongs to another session")

    units = {row["id"]: row for row in ledger["study_units"]}
    uid = state.get("current_unit_id")
    if uid is None:
        coverage.require(state.get("allocation_category") is None,
                         "Allocation category needs a current unit")
    else:
        coverage.choice(uid, units, "current unit ID")
        coverage.require(units[uid]["session_id"] == session_id, "Unit belongs to another session")
        coverage.require(state.get("allocation_category") == units[uid]["kind"],
                         "Checkpoint allocation differs from its ledger unit")
        coverage.require((state["mode"] == "mock") == (units[uid]["mode"] == "mock"),
                         "Checkpoint mock mode differs from its ledger unit")
        coverage.require(unit_lifecycle(ledger, uid) != "unknown",
                         "Checkpoint unit needs explicit started lifecycle or reconciled ledger unit events")

    items = coverage.unique_rows(state.get("items"), "question")
    if "answer_position_deck" in state:
        validate_position_deck(state)
    index = state.get("question_index")
    coverage.require(type(index) is int and 0 <= index < max(1, len(items)),
                     "Invalid zero-based question_index")
    coverage.require(not items or uid is not None, "Questions need a current ledger unit")
    seen_attempts, seen_refs = set(), set()
    voided = {row["attempt_id"] for row in voids.values()}
    previous = None
    versions = []
    journal_ids = set()
    recovery = any(item.get("history") for item in items.values())
    for position, item in enumerate(items.values()):
        history = coverage.array(item.get("history", []), "question history")
        for offset, entry in enumerate(history):
            coverage.mapping(entry, "history entry")
            correction = history_correction(entry, voids, attempts, applied_voids, as_of)
            if "invalidation" in entry:
                coverage.require(correction["id"] not in journal_ids,
                                 "Journal invalidation ID reused")
                journal_ids.add(correction["id"])
            coverage.mapping(entry["item"], "historical question")
            coverage.require(ITEM_FIELDS <= set(entry["item"]) <= ITEM_FIELDS | OPTIONAL_ITEM_FIELDS,
                             "Invalid historical question fields")
            versions.append((position, entry["item"], True))
        versions.append((position, item, False))
    seen_questions = set()
    legacy_sources = []
    for position, item, historical in versions:
        coverage.require(ITEM_FIELDS <= set(item) <= ITEM_FIELDS | OPTIONAL_ITEM_FIELDS
                         | (set() if historical else {"history"}),
                         "Question has missing or unknown fields")
        if "private_metadata" in item:
            current_source = validate_metadata(
                item["private_metadata"], catalog, as_of,
                allow_legacy_sources=historical or allow_legacy_sources,
            )
            if not historical and not current_source:
                legacy_sources.append(position)
        coverage.text(item["id"], "question ID")
        coverage.require(item["id"] not in seen_questions, "Question ID reused in immutable history")
        seen_questions.add(item["id"])
        coverage.text(item.get("stem"), "question stem")
        kind = coverage.choice(question_kind(item), {"choice", "free_response"}, "question kind")
        coverage.require(item.get("answer_order_locked") is True, "Answer order must be locked")
        options = coverage.array(item.get("options"), "options")
        if state["mode"] == "mock":
            coverage.require(kind == "choice", "Mocks require choice items")
        if kind == "free_response":
            coverage.require(not options and item["private_key"] == [],
                             "Free-response items cannot contain choices or a private key")
            coverage.require(bool(ids(item.get("private_grading_criteria"), "private grading criteria")),
                             "Free-response items require private grading criteria")
        else:
            coverage.require("private_grading_criteria" not in item,
                             "Choice items cannot contain private grading criteria")
            coverage.require(len(options) >= 2, "Question needs at least two neutral options")
        keys = set()
        for option in options:
            coverage.mapping(option, "option")
            coverage.require(set(option) == {"key", "text"}, "Options contain only key and text")
            key = coverage.text(option["key"], "option key")
            coverage.require(re.fullmatch(r"[A-Z]", key), "Option key must be one uppercase letter")
            coverage.require(key not in keys, "Duplicate option key")
            keys.add(key)
            text = coverage.text(option["text"], "option text")
            coverage.require(neutral_option(text),
                             "Option text must be plain neutral text, not presentation markup")
        answer = ids(item.get("private_key"), "private key")
        if state["mode"] == "mock":
            coverage.require(len(options) == 4 and keys == set("ABCD"),
                             "Mock questions require exactly four A/B/C/D options")
        if kind == "choice":
            coverage.require(bool(answer) and answer <= keys, "Private key references unknown options")
        coverage.text(item.get("private_rationale"), "private rationale")
        grading = coverage.choice(item.get("grading"), {"pending", "deferred", "applied"}, "grading")
        coverage.choice(item.get("review"), {"pending", "complete"}, "review")
        if "unit_id" in item:
            coverage.choice(item["unit_id"], units, "question unit ID")
            coverage.require(units[item["unit_id"]]["session_id"] == session_id,
                             "Question unit belongs to another session")
        response = item.get("response")
        aid = item.get("attempt_id")
        if response is None:
            coverage.require(aid is None and grading != "applied" and item["review"] == "pending",
                             "Unanswered question cannot have an attempt, grade, or review")
        else:
            moment = recorded_response(response, as_of, "Response")
            ref = response["response_ref"]
            coverage.require(recovery or previous is None or moment >= previous,
                             "Responses are out of order")
            coverage.require(termination_time is None or moment <= termination_time,
                             "Answer postdates mock termination")
            previous = moment
            coverage.require(ref not in seen_refs, "Response reference reused for another question")
            seen_refs.add(ref)
            coverage.text(aid, "reserved attempt_id")
            coverage.require(aid not in seen_attempts, "Attempt ID reused for another question")
            seen_attempts.add(aid)
            if aid in attempts:
                actual = attempts[aid]
                coverage.require(actual["session_id"] == session_id
                                 and actual["response_ref"] == ref
                                 and coverage.timestamp(actual["timestamp"]) == moment
                                 and actual["genuine_confirmed"] is True,
                                 "Checkpoint answer conflicts with the ledger attempt")
                coverage.require(actual.get("unit_id") is None
                                 or actual["unit_id"] == question_unit(item, attempts, uid),
                                 "Checkpoint answer belongs to another activity")
                # A voided attempt's claims no longer count, so it cannot block its own recovery.
                coverage.require(aid in voided or "private_metadata" not in item
                                 or set(actual["subskill_ids"]) <= set(item["private_metadata"]["subskill_ids"]),
                                 "Ledger attempt claims subskills its question does not target")
            if grading == "applied":
                coverage.require(aid in applied, "Applied grading lacks an applied ledger marker")
            coverage.require(item["review"] != "complete" or grading == "applied",
                             "Review cannot complete before ledger grading")
        if not historical:
            owner_id = question_unit(item, attempts, None if item["review"] == "complete" else uid)
            if owner_id is not None and "private_metadata" in item:
                coverage.require(
                    set(item["private_metadata"]["subskill_ids"]) <= set(units[owner_id]["subskill_ids"]),
                    "Question targets subskills outside its activity",
                )
            if position == index and item["review"] != "complete":
                coverage.require(owner_id == uid, "Pending question belongs to another activity")
        if state["mode"] == "mock":
            coverage.require(grading in {"deferred", "applied"}, "Mock grading must remain deferred")
        else:
            coverage.require(grading != "deferred", "Deferred grading requires mock mode")
        if historical:
            continue
        if position < index:
            coverage.require(response is not None, "Cannot advance past an unanswered question")
            if state["mode"] != "mock":
                coverage.require(grading == "applied" and item["review"] == "complete",
                                 "Cannot advance before grading and review")
        if position > index and not recovery:
            coverage.require(response is None, "Future question already has an answer")
    for item in items.values():
        history = item.get("history", [])
        for offset, entry in enumerate(history):
            after = history[offset + 1]["item"] if offset + 1 < len(history) else item
            correction = history_correction(entry, voids, attempts, applied_voids, as_of)
            validate_replacement(entry["item"], after, correction)
            coverage.require(question_unit(entry["item"], attempts, uid)
                             == question_unit(after, attempts, uid),
                             "Replacement must retain its original activity")
            if after["response"] is not None:
                coverage.require(coverage.timestamp(after["response"]["timestamp"])
                                 >= coverage.timestamp(correction["timestamp"]),
                                 "Replacement answer predates confirmed void")
    if "answer_position_deck" in state:
        validate_position_cursor(state, versions)
    unanswered = [row for row in items.values() if row["response"] is None]
    # Only a ledger void of an already graded answer may leave a replacement unanswered while
    # other mock grades stand; journal-only invalidations keep the mock ungraded.
    recovery_only_gaps = unanswered and all(
        any("void_id" in entry for entry in row.get("history", [])) for row in unanswered
    )
    if state["mode"] == "mock" and unanswered and termination is None and not recovery_only_gaps:
        voided_ids = {row["attempt_id"] for row in voids.values()}
        coverage.require(not any(
            (row["grading"] == "applied" or row["attempt_id"] in attempts)
            and row["attempt_id"] not in voided_ids for row in items.values()
        ),
                         "Cannot grade an incomplete mock")
    if state["phase"] == "complete":
        coverage.require(all(row["review"] == "complete" or (
            termination is not None and row["response"] is None
        ) for row in items.values()),
                         "Session cannot complete with outstanding question review")
    coverage.choice(state.get("next_action"), ACTIONS, "next_action")
    coverage.require(state["next_action"] == intended_action(state),
                     "next_action conflicts with recorded question state")
    return legacy_sources


def validate_legacy_source_update(old, new, indexes, old_indexes):
    for index in indexes:
        coverage.require(old is not None and index < len(old["items"])
                         and old["session_id"] == new["session_id"]
                         and old["items"][index] == new["items"][index],
                         "Hugging Face verification must use official Transformers documentation")
    if indexes:
        replacements = [i for i in old_indexes if old["items"][i]["id"] != new["items"][i]["id"]]
        recovery_move = len(replacements) == 1 and new["question_index"] == replacements[0]
        coverage.require(old["phase"] == new["phase"] and (
            recovery_move or all(old[field] == new[field]
                                 for field in ("question_index", "current_unit_id"))
        ),
                         "Replace legacy source verification before advancing or grading")


def validate_update(old, new, ledger):
    if old["session_id"] != new["session_id"]:
        coverage.require(old["phase"] == "complete", "Conflicting active session; do not overwrite")
        return
    for field in ("exam", "blueprint_revision", "mode"):
        coverage.require(old[field] == new[field], f"Cannot change checkpoint {field}")
    if old["mode"] == "planner" and old["paused"] and new["paused"]:
        coverage.require(old["private_planning"] == new["private_planning"],
                         "Paused planning proposal cannot change; explicitly resume first")
    validate_position_deck_update(old, new)
    coverage.require(len(new["items"]) >= len(old["items"]), "Cannot discard locked questions")
    if old["mode"] == "mock" and old["items"]:
        coverage.require(len(new["items"]) == len(old["items"]), "Mock manifest is immutable")
    if old.get("termination") is not None:
        coverage.require(old["termination"] == new.get("termination"),
                         "Confirmed mock termination is immutable")
    voids = {row["id"]: row for row in ledger.get("voided_attempts", [])}
    attempts = {row["id"]: row for row in ledger["attempts"]}
    old_responses = [
        row["response"] for item in old["items"]
        for row in [entry["item"] for entry in item.get("history", [])] + [item]
        if row["response"] is not None
    ]
    last_response = max((coverage.timestamp(row["timestamp"]) for row in old_responses), default=None)
    new_answers = [
        position for position, (before, after) in enumerate(zip(old["items"], new["items"]))
        if before["id"] == after["id"] and before["response"] is None and after["response"] is not None
    ]
    coverage.require(not new_answers or new_answers == [old["question_index"]],
                     "Journal only one new answer at the previously saved question")
    replacements = []
    for position, (before, after) in enumerate(zip(old["items"], new["items"])):
        old_history, new_history = before.get("history", []), after.get("history", [])
        if before["id"] != after["id"]:
            coverage.require(new_history[:-1] == old_history and len(new_history) == len(old_history) + 1,
                             "Replacement must append immutable original question history")
            entry = new_history[-1]
            coverage.require(entry["item"] == {key: value for key, value in before.items()
                                               if key != "history"},
                             "Historical question/answer must preserve the exact original")
            if "void_id" in entry:
                coverage.require(before["attempt_id"] in new["applied_attempt_ids"],
                                 "Replacement must acknowledge the original ledger attempt")
                correction = voids[entry["void_id"]]
            else:
                correction = dict(entry["invalidation"], attempt_id=before["attempt_id"])
            validate_replacement(before, after, correction)
            coverage.require(question_unit(before, attempts, old["current_unit_id"])
                             == question_unit(after, attempts, new["current_unit_id"]),
                             "Replacement must retain its original activity")
            coverage.require(after["response"] is None and after["attempt_id"] is None,
                             "Persist replacement before receiving a new genuine answer")
            replacements.append(position)
            continue
        coverage.require(old_history == new_history, "Cannot rewrite immutable question history")
        coverage.require(locked_question(before) == locked_question(after),
                         "Locked question stem/options/key/order cannot change")
        coverage.require(before.get("private_metadata") == after.get("private_metadata"),
                         "Locked question private metadata cannot change")
        known_owner = question_unit(
            before, attempts, None if before["review"] == "complete" else old["current_unit_id"],
        )
        coverage.require(before.get("unit_id") == after.get("unit_id")
                         or ("unit_id" not in before and after.get("unit_id") == known_owner),
                         "Locked question activity cannot change")
        if before["response"] is not None:
            original = before["response"]
            enriched = (
                "text" not in original and after["response"] is not None
                and all(after["response"].get(key) == value for key, value in original.items())
            )
            coverage.require((original == after["response"] or enriched)
                             and before["attempt_id"] == after["attempt_id"],
                             "Conflicting recorded answer; use confirmed ledger correction, not replacement")
        elif after["response"] is not None:
            coverage.require(old.get("termination") is None, "Ended mock cannot receive new answers")
            coverage.require(position <= new["question_index"], "Cannot answer beyond the saved question index")
            coverage.require(after["attempt_id"] not in attempts,
                             "Journal the genuine answer before writing its ledger attempt")
            require_portable_response(after)
            uid = new["current_unit_id"]
            coverage.require(question_unit(after, attempts, uid) == uid,
                             "New answer belongs to another activity")
            coverage.require_active_unit_answer(
                next(unit for unit in ledger["study_units"] if unit["id"] == uid),
                coverage.unit_histories(ledger)[uid],
                {row["id"]: row for row in ledger["attempts"]},
                {row["attempt_id"]: coverage.timestamp(row["timestamp"]) for row in voids.values()},
                coverage.timestamp(after["response"]["timestamp"]),
            )
            coverage.require(last_response is None
                             or coverage.timestamp(after["response"]["timestamp"]) >= last_response,
                             "New answer predates the last confirmed genuine response")
        coverage.require(before["grading"] != "applied" or after["grading"] == "applied",
                         "Cannot discard applied grading")
        coverage.require(before["review"] != "complete" or after["review"] == "complete",
                         "Cannot discard completed review")
    for after in new["items"][len(old["items"]):]:
        coverage.require(not after.get("history"), "New question cannot invent recovery history")
        require_unanswered_preparation(after)
        coverage.require("private_metadata" in after,
                         "New questions require private verification metadata")
        coverage.require(after.get("unit_id") == new["current_unit_id"],
                         "New questions require their current activity unit ID")
    if replacements:
        coverage.require(len(replacements) == 1 and new["question_index"] == replacements[0],
                         "Recover one voided question at its original item index")
        coverage.require(not new["paused"], "Pause cannot generate a replacement question")
    else:
        coverage.require(new["question_index"] >= old["question_index"], "Cannot rewind question index")
    for field in ("applied_attempt_ids", "applied_void_ids"):
        coverage.require(set(old[field]) <= set(new[field]), f"Cannot discard {field}")
    pending = old["items"] and old["items"][old["question_index"]]["review"] != "complete"
    if pending or replacements:
        expected_unit = (
            question_unit(old["items"][replacements[0]], attempts, old["current_unit_id"])
            if replacements else old["current_unit_id"]
        )
        units = {row["id"]: row for row in ledger["study_units"]}
        coverage.require(expected_unit == new["current_unit_id"]
                         and units[expected_unit]["kind"] == new["allocation_category"],
                         "Pending work must retain its original unit and allocation")
    if new["paused"]:
        for field in ("phase", "current_unit_id", "allocation_category", "question_index"):
            coverage.require(old[field] == new[field], "Pause must not advance the phase or question")
        coverage.require(len(new["items"]) == len(old["items"]),
                         "Pause must not create another question")
        if old["paused"]:
            coverage.require(all(before["response"] == after["response"]
                                 for before, after in zip(old["items"], new["items"])),
                             "Paused session cannot acquire a new answer; explicitly resume first")


def summary(state, ledger, ledger_hash, checkpoint_hash, legacy_sources=()):
    attempts = {row["id"]: row for row in ledger["attempts"]}
    all_items = [
        row for item in state["items"]
        for row in [entry["item"] for entry in item.get("history", [])] + [item]
    ]
    item_ids = {row["attempt_id"] for row in all_items if row["attempt_id"] is not None}
    committed = sorted(item_ids & attempts.keys())
    voids = sorted(row["id"] for row in ledger.get("voided_attempts", [])
                   if row["attempt_id"] in item_ids)
    unreconciled_voids = set(voids) - set(state["applied_void_ids"])
    unreconciled_attempts = any(
        row["attempt_id"] in attempts and (
            row["attempt_id"] not in state["applied_attempt_ids"] or row["grading"] != "applied"
        ) for row in state["items"]
    )
    stale = (ledger_hash != state["ledger_sha256"]
             or bool(unreconciled_voids) or unreconciled_attempts)
    item = state["items"][state["question_index"]] if state["items"] else None
    voided = {row["attempt_id"]: row for row in ledger.get("voided_attempts", [])}
    recovery = next(((index, row, voided[row["attempt_id"]])
                     for index, row in enumerate(state["items"]) if row["attempt_id"] in voided), None)
    missing_text = any(row["response"] is not None and "text" not in row["response"]
                       and row["grading"] != "applied" for row in state["items"])
    action = "reconcile_ledger" if stale else state["next_action"]
    if recovery is not None:
        action = ("replace_invalid_item" if recovery[2].get("reason_kind") == "invalid_item"
                  else "reask_disowned")
        if state.get("termination") is not None:
            action = "resolve_voided_partial_review"
    elif not stale and missing_text and action in {"grade_recorded", "grade_deferred"}:
        action = "recover_response_text"
    if legacy_sources:
        action = "replace_unverified_item"
    uid = state["current_unit_id"]
    result = {
        "exam": state["exam"], "session_id": state["session_id"], "mode": state["mode"],
        "phase": state["phase"], "paused": state["paused"],
        "current_unit_id": uid, "allocation_category": state["allocation_category"],
        "unit_lifecycle": unit_lifecycle(ledger, uid), "question_index": state["question_index"],
        "item_id": item["id"] if item else None,
        "next_action": action,
        "reconciliation_needed": stale, "committed_attempt_ids": committed,
        "committed_void_ids": voids, "pending_check_ids": state["pending_check_ids"],
        "checkpoint_sha256": checkpoint_hash, "ledger_sha256": ledger_hash,
        "read_only": True, "termination_recorded": state.get("termination") is not None,
        "answered_count": sum(row["response"] is not None for row in state["items"]),
        "unanswered_count": sum(row["response"] is None for row in state["items"]),
    }
    if recovery is not None:
        result["recovery_question_index"] = recovery[0]
        result["recovery_item_id"] = recovery[1]["id"]
        result["recovery_void_id"] = recovery[2]["id"]
    if legacy_sources:
        result["source_recovery_question_indices"] = legacy_sources
        result["source_recovery_item_ids"] = [state["items"][i]["id"] for i in legacy_sources]
    if action == "reask_disowned":
        item = recovery[1]
    if action == "reask_disowned" or (not stale and action == "reask_pending"):
        pending = {"id": item["id"], "stem": item["stem"]}
        if question_kind(item) == "free_response":
            pending["kind"] = "free_response"
        else:
            pending["options"] = item["options"]
        result["pending_question"] = pending
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("checkpoint", "resume", "mock-quotas"))
    parser.add_argument("--exam", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--input", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--question-count", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        coverage.require(re.fullmatch(r"[a-z0-9-]+", args.exam), "Invalid exam folder name")
        as_of = coverage.audit_date(args.as_of)
        base = args.root / "exams" / args.exam
        catalog = coverage.read_json(base / "blueprint.json")
        _, _, skills = coverage.validate_catalog(catalog, args.exam, as_of)
        if args.command == "mock-quotas":
            coverage.require(catalog["verified"], "Reconcile the unverified blueprint before mock quotas")
            quotas = mock_quotas(catalog, args.question_count)
            print(json.dumps({"exam": args.exam, "question_count": args.question_count,
                              "domain_quotas": quotas}, indent=2) if args.json else
                  "\n".join(f"{domain}: {count}" for domain, count in quotas.items()))
            return 0
        ledger_path = base / "assets" / "coverage.json"
        ledger_hash = coverage.digest(ledger_path)
        coverage.require(ledger_hash is not None, "Missing ledger; initialize coverage before checkpointing")
        ledger = coverage.read_json(ledger_path)
        coverage.validate_ledger(ledger, catalog, skills, as_of)
        path = base / "assets" / "session.json"
        before = coverage.digest(path)
        if args.command == "checkpoint":
            coverage.require(args.input is not None, "checkpoint requires --input")
            expected = None if args.expected_sha256 == "missing" else args.expected_sha256
            if expected is not None:
                sha256(expected, "expected-sha256")
            coverage.require(args.expected_sha256 is not None and expected == before,
                             "Checkpoint SHA-256 missing or stale; resume before updating")
            state = coverage.read_json(args.input)
            legacy_sources = validate(state, catalog, ledger, as_of, allow_legacy_sources=True)
            coverage.require(state["ledger_sha256"] == ledger_hash,
                             "Ledger changed; reconcile attempt/void IDs before checkpointing")
            new_session = before is None
            old = None
            old_legacy_sources = []
            if before is not None:
                old = coverage.read_json(path)
                old_legacy_sources = validate(
                    old, catalog, ledger, as_of, allow_legacy_sources=True,
                )
                validate_update(old, state, ledger)
                new_session = old["session_id"] != state["session_id"]
            validate_legacy_source_update(old, state, legacy_sources, old_legacy_sources)
            if new_session:
                if state.get("answer_position_deck", {}).get("kind") == "open_ended":
                    coverage.require(len(state["answer_position_deck"]["positions"]) == 12,
                                     "Start with one 12-position batch")
                for item in state["items"]:
                    coverage.require(not item.get("history"),
                                     "Initial checkpoint cannot invent recovery history")
                    require_unanswered_preparation(item)
                require_deck_only_preparation(state)
            coverage.require(coverage.digest(ledger_path) == ledger_hash,
                             "Ledger changed during checkpoint validation; retry")
            coverage.atomic_write(path, state, before)
            checkpoint_hash = coverage.digest(path)
            coverage.require(coverage.read_json(path) == state
                             and coverage.digest(path) == checkpoint_hash,
                             "Checkpoint changed after saving; resume before continuing")
        else:
            coverage.require(before is not None,
                             "Missing checkpoint; durable resume unavailable. Do not reconstruct answers.")
            state = coverage.read_json(path)
            legacy_sources = validate(state, catalog, ledger, as_of, allow_legacy_sources=True)
            coverage.require(coverage.digest(path) == before, "Checkpoint changed during resume; retry")
            checkpoint_hash = before
        coverage.require(coverage.digest(ledger_path) == ledger_hash,
                         "Ledger changed during operation; resume and reconcile before continuing")
        result = summary(state, ledger, ledger_hash, checkpoint_hash, legacy_sources)
        if args.command == "checkpoint":
            result.pop("pending_question", None)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"{args.command}: {result['exam']} / {result['session_id']}")
            print(f"Next action: {result['next_action']} (no action executed)")
            print(f"Checkpoint SHA-256: {result['checkpoint_sha256']}")
            if result["reconciliation_needed"]:
                print("Reconcile ledger markers; do not duplicate or regrade existing attempts.")
            if "pending_question" in result:
                question = result["pending_question"]
                print(question["stem"])
                for option in question.get("options", []):
                    print(f"{option['key']}. {option['text']}")
        return 0
    except (coverage.CoverageError, OSError) as exc:
        print(f"Session error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
