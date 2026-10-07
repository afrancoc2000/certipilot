"""Audit exam coverage without conflating exposure, scores, and mastery."""

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[4]
CYCLE = (
    "coverage", "coverage", "remediation", "coverage", "retention",
    "coverage", "remediation", "coverage", "coverage", "remediation",
    "coverage", "retention", "coverage", "remediation", "coverage",
    "coverage", "remediation", "coverage", "retention", "coverage",
)
RESULTS = {"correct", "partial", "incorrect", "unscored"}
CONTEXTS = {
    "cold", "post_teaching", "delayed_transfer", "mock", "teaching", "historical",
}


class CoverageError(ValueError):
    """An explicit input, evidence, or persistence error."""


def require(condition, message):
    if not condition:
        raise CoverageError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: expected text")
    return value


def boolean(value, label):
    require(type(value) is bool, f"{label}: expected boolean")
    return value


def array(value, label):
    require(isinstance(value, list), f"{label}: expected list")
    return value


def mapping(value, label):
    require(isinstance(value, dict), f"{label}: expected object")
    return value


def choice(value, allowed, label):
    require(isinstance(value, str) and value in allowed, f"Invalid {label}")
    return value


def timestamp(value):
    text(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CoverageError(f"Invalid timestamp: {value}") from exc
    require(parsed.tzinfo is not None, "timestamp must include a timezone")
    return parsed


def not_future(moment, as_of, label):
    require(moment.astimezone(timezone.utc).date() <= as_of, f"{label} is after the as-of date, which cannot precede recorded evidence")
    now = datetime.now(timezone.utc)
    require(moment <= now, f"{label} is later than the real clock")


def calendar_date(value, label):
    text(value, label)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CoverageError(f"{label}: invalid ISO date") from exc


def audit_date(value):
    as_of = calendar_date(value, "as-of")
    require(as_of <= datetime.now(timezone.utc).date(), "as-of cannot be later than today's UTC date")
    return as_of


def study_timezone(value):
    if value is None:
        return None
    text(value, "study_timezone")
    require(
        len(value) == 9 and value[:3] == "UTC" and value[3] in "+-"
        and value[6] == ":" and value[4:6].isdigit() and value[7:9].isdigit(),
        "study_timezone must be a fixed UTC offset such as UTC-05:00",
    )
    hours, minutes = int(value[4:6]), int(value[7:9])
    require(hours <= 14 and minutes < 60 and (hours < 14 or minutes == 0),
            "Invalid study timezone offset")
    offset = timedelta(hours=hours, minutes=minutes)
    return timezone(-offset if value[3] == "-" else offset)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CoverageError(f"Cannot read {path}: {exc}") from exc


def validate_catalog(catalog, exam, as_of):
    mapping(catalog, "catalog")
    require(type(catalog.get("schema_version")) is int and catalog["schema_version"] == 1,
            "Unsupported catalog schema")
    require(catalog.get("exam") == exam, "Catalog belongs to another exam")
    text(catalog.get("revision"), "catalog revision")
    boolean(catalog.get("verified"), "catalog verified")
    text(catalog.get("verification_note"), "verification note")
    sources = {}
    for source in array(catalog.get("sources"), "sources"):
        mapping(source, "source")
        sid = text(source.get("id"), "source id")
        require(sid not in sources, f"Duplicate source ID: {sid}")
        url = text(source.get("url"), "source URL")
        require(url.startswith("https://"), "Source URL must use HTTPS")
        checked = calendar_date(source.get("checked_at"), "source checked_at")
        require(checked <= as_of, "Source check date is after the as-of date")
        text(source.get("published_revision"), "published revision")
        sources[sid] = source
    require(sources, "Catalog needs official source metadata")
    domains, objectives, skills = {}, {}, {}
    for domain in array(catalog.get("domains"), "domains"):
        mapping(domain, "domain")
        did = text(domain.get("id"), "domain id")
        require(did not in domains, f"Duplicate domain ID: {did}")
        text(domain.get("title"), "domain title")
        low, high = domain.get("weight_min"), domain.get("weight_max")
        require(
            type(low) in (int, float) and type(high) in (int, float)
            and 0 < low <= high <= 100,
            f"Invalid domain weights: {did}",
        )
        domains[did] = domain
        rows = array(domain.get("objectives"), "objectives")
        require(rows, f"Domain has no objectives: {did}")
        for objective in rows:
            mapping(objective, "objective")
            oid = text(objective.get("id"), "objective id")
            require(oid not in objectives, f"Duplicate objective ID: {oid}")
            text(objective.get("title"), "objective title")
            choice(objective.get("source_id"), sources, f"source for {oid}")
            text(objective.get("source_locator"), "source locator")
            objectives[oid] = (did, objective)
            subskills = array(objective.get("subskills"), "subskills")
            require(subskills, f"Objective has no assessable subskills: {oid}")
            for skill in subskills:
                mapping(skill, "subskill")
                kid = text(skill.get("id"), "subskill id")
                require(kid not in skills, f"Duplicate subskill ID: {kid}")
                text(skill.get("title"), "subskill title")
                boolean(skill.get("derived"), "subskill derived")
                skills[kid] = (did, oid, skill)
    require(domains, "Catalog has no domains")
    require(
        sum(d["weight_min"] for d in domains.values()) <= 100
        <= sum(d["weight_max"] for d in domains.values()),
        "Domain weight ranges cannot sum to 100",
    )
    return domains, objectives, skills


def empty_ledger(catalog):
    return {
        "schema_version": 1, "exam": catalog["exam"],
        "blueprint_revision": catalog["revision"],
        "attempts": [], "study_units": [], "pending_checks": [], "voided_attempts": [],
        "unit_events": [],
    }


def unique_rows(rows, label):
    found = {}
    for row in array(rows, label):
        mapping(row, label)
        rid = text(row.get("id"), f"{label} id")
        require(rid not in found, f"Duplicate {label} ID: {rid}")
        found[rid] = row
    return found


def skill_refs(row, skills):
    refs = array(row.get("subskill_ids"), "subskill_ids")
    require(refs, "At least one subskill must be identified")
    require(all(isinstance(ref, str) for ref in refs), "Subskill IDs must be text")
    require(len(refs) == len(set(refs)), "Repeated subskill in one record")
    require(set(refs) <= skills.keys(), f"Unknown subskill IDs: {set(refs) - skills.keys()}")


def independent(attempt):
    return (
        attempt["result"] != "unscored"
        and attempt["assistance"] == "unaided"
        and attempt["genuine_confirmed"]
        and attempt["context"] != "teaching"
    )


def demonstrated(attempt):
    return (
        independent(attempt) and attempt["result"] == "correct"
        and attempt["reasoning_demonstrated"] and attempt["novel"]
        and attempt["context"] != "post_teaching"
    )


def delayed_eligible(attempt, attempts, local_zone):
    if attempt["context"] != "delayed_transfer" or local_zone is None:
        return False
    source = next((a for a in attempts if a["id"] == attempt.get("retention_source_id")), None)
    if source is None:
        return False
    start, end = timestamp(source["timestamp"]), timestamp(attempt["timestamp"])
    return (
        set(attempt["subskill_ids"]) <= set(source["subskill_ids"])
        and end > start
        and end.astimezone(local_zone).date() > start.astimezone(local_zone).date()
        and independent(attempt) and attempt["novel"]
    )


def skill_state(attempts, sid, local_zone=None):
    relevant = [a for a in attempts if sid in a["subskill_ids"]]
    assessed = [a for a in relevant if independent(a)]
    latest = assessed[-1] if assessed else None
    mastery_evidence = [
        a for a in assessed
        if demonstrated(a) or a["result"] in {"incorrect", "partial"}
    ]
    latest_mastery = mastery_evidence[-1] if mastery_evidence else None
    has_demonstration = bool(latest_mastery and demonstrated(latest_mastery))
    return {
        "introduced": bool(relevant),
        "assessed": bool(assessed),
        "demonstrated": has_demonstration,
        "delayed_transfer": bool(
            has_demonstration and any(
                demonstrated(a) and delayed_eligible(a, attempts, local_zone)
                for a in assessed
                if not any(
                    b["result"] in {"incorrect", "partial"}
                    for b in assessed if timestamp(b["timestamp"]) > timestamp(a["timestamp"])
                )
            )
        ),
        "last_independent": latest["timestamp"] if latest else None,
    }


def coverage_queue(domains, skills, states, units, attempts):
    """Make every subskill reachable, weighting sequence rather than omission."""
    visits = Counter(sid for attempt in attempts for sid in attempt["subskill_ids"])
    served = Counter()
    for unit in units:
        if unit["mode"] == "normal" and unit["kind"] == "coverage":
            for sid in unit["subskill_ids"]:
                served[skills[sid][0]] += 1 / len(unit["subskill_ids"])
    remaining = set(skills)
    queue = []
    while remaining:
        def phase(sid):
            state = states[sid]
            if not state["assessed"]:
                return 0 if visits[sid] == 0 else 1
            return 2 if not state["demonstrated"] else 3

        current_phase = min(phase(sid) for sid in remaining)
        candidates = [sid for sid in skills if sid in remaining and phase(sid) == current_phase]
        available_domains = {skills[sid][0] for sid in candidates}
        did = min(
            (did for did in domains if did in available_domains),
            key=lambda did: (served[did] + 1)
            / ((domains[did]["weight_min"] + domains[did]["weight_max"]) / 2),
        )
        sid = min(
            (sid for sid in candidates if skills[sid][0] == did),
            key=lambda sid: (
                visits[sid],
                timestamp(states[sid]["last_independent"]) if states[sid]["last_independent"]
                else datetime.min.replace(tzinfo=timezone.utc),
            ),
        )
        queue.append(sid)
        remaining.remove(sid)
        served[did] += 1
    return queue


def supported_subskills(uid, attempts, voided, evidence_by, effective_at):
    return {
        sid for aid, attempt in attempts.items()
        if attempt.get("unit_id") == uid and timestamp(attempt["timestamp"]) <= evidence_by
        and (aid not in voided or (effective_at is not None and voided[aid] > effective_at))
        for sid in attempt["subskill_ids"]
    }


def unit_state_at(unit, history, attempts, voided, at=None):
    state_time, status = [
        (moment, state) for moment, state in history if at is None or moment <= at
    ][-1]
    if status == "completed":
        required = set(unit["subskill_ids"])
        invalidations = sorted({
            moment for aid, moment in voided.items()
            if attempts[aid].get("unit_id") == unit["id"] and moment >= state_time
            and (at is None or moment <= at)
        })
        for moment in invalidations:
            if not required <= supported_subskills(
                unit["id"], attempts, voided, state_time, moment,
            ):
                return moment, "interrupted"
    return state_time, status


def unit_histories(ledger):
    histories = {
        u["id"]: [(timestamp(u["timestamp"]), u.get("lifecycle", "unknown"))]
        for u in ledger["study_units"]
    }
    for event in ledger.get("unit_events", []):
        histories[event["unit_id"]].append((timestamp(event["timestamp"]), event["status"]))
    return histories


def require_active_unit_answer(unit, history, attempts, voided, answer_time):
    require(answer_time >= timestamp(unit["timestamp"]), "Answer precedes its activity")
    state_time, state_at_answer = unit_state_at(unit, history, attempts, voided, answer_time)
    require(
        state_at_answer in {"started", "unknown"}
        or (state_at_answer == "completed" and state_time == answer_time),
        "Record answers only during an active activity, not after pause or completion",
    )


def unit_lifecycles(ledger):
    """Derive current lifecycle without rewriting historical completion events."""
    attempts = {a["id"]: a for a in ledger["attempts"]}
    voided = {v["attempt_id"]: timestamp(v["timestamp"]) for v in ledger.get("voided_attempts", [])}
    histories = unit_histories(ledger)
    return {
        u["id"]: unit_state_at(u, histories[u["id"]], attempts, voided)[1]
        for u in ledger["study_units"]
    }


def validate_ledger(ledger, catalog, skills, as_of):
    mapping(ledger, "ledger")
    require(type(ledger.get("schema_version")) is int and ledger["schema_version"] == 1,
            "Unsupported ledger schema")
    require(ledger.get("exam") == catalog["exam"], "Ledger belongs to another exam")
    require(
        ledger.get("blueprint_revision") == catalog["revision"],
        "Blueprint revision changed: reconcile evidence explicitly before auditing",
    )
    study_timezone(ledger.get("study_timezone"))
    attempts = unique_rows(ledger.get("attempts"), "attempt")
    scored_responses = set()
    previous = None
    for attempt in attempts.values():
        text(attempt.get("session_id"), "session_id")
        moment = timestamp(attempt.get("timestamp"))
        not_future(moment, as_of, "Attempt")
        require(previous is None or moment >= previous, "Attempts are out of chronological order")
        previous = moment
        require(attempt.get("blueprint_revision") == catalog["revision"], "Stale attempt revision")
        skill_refs(attempt, skills)
        choice(attempt.get("result"), RESULTS, "attempt result")
        choice(attempt.get("context"), CONTEXTS, "attempt context")
        choice(attempt.get("assistance"), {"unaided", "assisted", "unknown"}, "assistance")
        for key in ("genuine_confirmed", "reasoning_demonstrated", "novel"):
            boolean(attempt.get(key), key)
        choice(
            attempt.get("diagnosis"), {
                "none", "mechanism", "application", "prerequisite", "reading", "uncertain",
            }, "diagnosis",
        )
        require(isinstance(attempt.get("action"), str), "action must be text")
        require(isinstance(attempt.get("response_ref"), str), "response_ref must be text")
        if attempt["result"] != "unscored":
            require(attempt["genuine_confirmed"], "Scored attempt lacks confirmed genuine answer")
            text(attempt["response_ref"], "genuine response reference")
            require(attempt["response_ref"] not in scored_responses,
                    "Scored response reference reused by multiple attempts")
            scored_responses.add(attempt["response_ref"])
        if attempt["context"] == "teaching":
            require(attempt["result"] == "unscored", "Teaching alone cannot be scored")
        if attempt["diagnosis"] not in {"none", "uncertain"}:
            text(attempt["action"], "A diagnosed gap needs an instructional action")
        if attempt["context"] == "delayed_transfer":
            source_id = attempt.get("retention_source_id")
            if source_id is not None:
                choice(source_id, attempts, "retention source reference")
                source = attempts[source_id]
                require(set(attempt["subskill_ids"]) <= set(source["subskill_ids"]),
                        "Retention source does not cover the assessed subskills")
                require(timestamp(source["timestamp"]) < moment,
                        "Retention source must precede the attempt")

    voids = unique_rows(ledger.get("voided_attempts", []), "void")
    voided = {}
    disowning_refs = set()
    for void in voids.values():
        aid = choice(void.get("attempt_id"), attempts, "void attempt reference")
        require(aid not in voided, "Attempt already has a void record")
        text(void.get("reason"), "void reason")
        text(void.get("response_ref"), "void confirmation reference")
        require(void.get("genuine_confirmed") is True,
                "Voiding requires genuine user provenance for the answer or correction")
        choice(void.get("reason_kind", "disowned_answer"),
               {"disowned_answer", "invalid_item"}, "void reason kind")
        if void.get("reason_kind") == "invalid_item":
            text(void.get("source_ref"), "Invalid item requires defect evidence")
            require(void["response_ref"] == attempts[aid]["response_ref"],
                    "Invalid item must reference its original answer")
        else:
            require(void["response_ref"] not in scored_responses,
                    "Disowning confirmation must be a separate genuine turn, not a scored answer")
            require(void["response_ref"] not in disowning_refs,
                    "Disowning confirmation reference reused by multiple voids")
            disowning_refs.add(void["response_ref"])
        moment = timestamp(void.get("timestamp"))
        not_future(moment, as_of, "Void confirmation")
        require(moment >= timestamp(attempts[aid]["timestamp"]), "Void confirmation predates answer")
        voided[aid] = moment

    units = unique_rows(ledger.get("study_units"), "study unit")
    events = unique_rows(ledger.get("unit_events", []), "unit event")
    histories = {}
    for uid, unit in units.items():
        text(unit.get("session_id"), "study unit session")
        skill_refs(unit, skills)
        initial = unit.get("lifecycle", "unknown")
        choice(initial, {"unknown", "started"}, "initial unit lifecycle")
        histories[uid] = [(timestamp(unit.get("timestamp")), initial)]
    for attempt in attempts.values():
        if attempt.get("unit_id") is not None:
            uid = choice(attempt["unit_id"], units, "attempt unit reference")
            require(attempt["session_id"] == units[uid]["session_id"],
                    "Attempt belongs to another activity session")
            require(set(attempt["subskill_ids"]) <= set(units[uid]["subskill_ids"]),
                    "Attempt targets subskills outside its activity")
            require(timestamp(attempt["timestamp"]) >= histories[uid][0][0],
                    "Attempt precedes its activity")
    previous_event = None
    for event in events.values():
        uid = choice(event.get("unit_id"), units, "event unit reference")
        status = choice(event.get("status"), {"started", "completed", "interrupted", "deferred"},
                        "unit event status")
        moment = timestamp(event.get("timestamp"))
        not_future(moment, as_of, "Unit event")
        require(previous_event is None or moment >= previous_event,
                "Unit events are out of chronological order")
        previous_event = moment
        require(moment >= histories[uid][-1][0], "Unit event precedes its activity state")
        previous_time, previous_status = unit_state_at(
            units[uid], histories[uid], attempts, voided, moment,
        )
        require(moment >= previous_time, "Unit event precedes its activity state")
        transitions = {
            "unknown": {"started", "deferred", "completed"},
            "started": {"completed", "interrupted", "deferred"},
            "interrupted": {"started", "deferred"},
            "deferred": {"started"},
            "completed": set(),
        }
        require(status in transitions[previous_status], "Invalid unit lifecycle transition")
        text(event.get("reason"), "Unit event requires an explicit reason")
        if status == "completed":
            supported = supported_subskills(uid, attempts, voided, moment, moment)
            require(set(units[uid]["subskill_ids"]) <= supported,
                    "Completed activity needs linked learning evidence for each target subskill")
        histories[uid].append((moment, status))
    for attempt in attempts.values():
        if attempt.get("unit_id") is not None:
            history = histories[attempt["unit_id"]]
            answer_time = timestamp(attempt["timestamp"])
            require_active_unit_answer(
                units[attempt["unit_id"]], history, attempts, voided, answer_time,
            )
    previous, normal_count = None, 0
    order = {uid: index for index, uid in enumerate(units)}
    for unit in units.values():
        moment = timestamp(unit.get("timestamp"))
        not_future(moment, as_of, "Study unit")
        require(previous is None or moment >= previous, "Study units are out of chronological order")
        previous = moment
        choice(unit.get("kind"), set(CYCLE), "study unit kind")
        choice(unit.get("mode"), {"normal", "override", "mock"}, "study unit mode")
        if unit["mode"] != "normal":
            text(unit.get("reason"), "An override/mock unit needs a scope reason")
            continue
        for prior_uid, history in histories.items():
            if prior_uid == unit["id"] or units[prior_uid].get("mode") != "normal":
                continue
            if order[prior_uid] >= order[unit["id"]]:
                continue
            _, state_at_start = unit_state_at(
                units[prior_uid], history, attempts, voided, moment,
            )
            require(state_at_start not in {"started", "interrupted"},
                    f"Unfinished activity {prior_uid} must resume or be explicitly deferred")
        expected = CYCLE[normal_count % len(CYCLE)]
        normal_count += 1
        prior = [
            a for aid, a in attempts.items() if timestamp(a["timestamp"]) < moment
            and (aid not in voided or voided[aid] > moment)
        ]
        if unit["kind"] != expected:
            reason = unit.get("reason")
            require(unit["kind"] == "coverage", "Protected coverage/retention cannot become remediation")
            if expected == "retention":
                require(reason == "no-retention-evidence", "Retention substitution must be explicit")
                require(
                    not any(skill_state(prior, sid)["demonstrated"] for sid in skills),
                    "Retention evidence exists; its protected slot cannot be replaced",
                )
            else:
                require(
                    expected == "remediation" and reason == "no-remediation-needed",
                    "Remediation substitution must be explicit",
                )
                latest = {}
                for attempt in prior:
                    if attempt["result"] != "unscored":
                        for sid in attempt["subskill_ids"]:
                            latest[sid] = attempt
                require(not any(
                    a["result"] in {"incorrect", "partial"} or a["assistance"] == "assisted"
                    for a in latest.values()
                ), "Unresolved remediation evidence exists")
        if unit["kind"] == "coverage":
            unassessed = {sid for sid in skills if not skill_state(prior, sid)["assessed"]}
            require(
                not unassessed or set(unit["subskill_ids"]) <= unassessed,
                "Coverage slot repeats assessed material while unassessed subskills remain",
            )
            visited = {sid for attempt in prior for sid in attempt["subskill_ids"]}
            unvisited = unassessed - visited
            require(
                not unvisited or set(unit["subskill_ids"]) <= unvisited,
                "Coverage slot revisits a subskill before the unassessed first pass is complete",
            )

    checks = unique_rows(ledger.get("pending_checks"), "check")
    for check in checks.values():
        choice(check.get("subskill_id"), skills, "check subskill reference")
        choice(check.get("after_attempt_id"), attempts, "check source attempt reference")
        base = attempts[check["after_attempt_id"]]
        require(check["subskill_id"] in base["subskill_ids"], "Check/source subskills differ")
        choice(check.get("kind"), {"cold", "delayed_transfer"}, "check kind")
        choice(check.get("status"), {"pending", "completed"}, "check status")
        if check["status"] == "pending":
            require(check.get("evidence_attempt_id") is None, "Pending check already has completion evidence")
            continue
        choice(check.get("evidence_attempt_id"), attempts, "check completion reference")
        evidence = attempts[check["evidence_attempt_id"]]
        require(
            check["subskill_id"] in evidence["subskill_ids"]
            and independent(evidence) and evidence["novel"]
            and evidence["context"] == check["kind"]
            and (check["kind"] == "delayed_transfer"
                 or evidence["session_id"] != base["session_id"])
            and timestamp(evidence["timestamp"]) > timestamp(base["timestamp"]),
            "Check completion requires a later, novel, independent attempt",
        )
    return [a for aid, a in attempts.items() if aid not in voided], list(units.values())


def session_breadth(domains, skills, ledger, attempts):
    latest = {}
    units = {u["id"]: u for u in ledger["study_units"]}
    resumed = [
        {"session_id": units[event["unit_id"]]["session_id"], "timestamp": event["timestamp"]}
        for event in ledger.get("unit_events", []) if event["status"] == "started"
    ]
    for row in [*ledger["study_units"], *ledger["attempts"], *resumed]:
        sid, moment = row["session_id"], timestamp(row["timestamp"])
        if sid not in latest or moment > latest[sid]:
            latest[sid] = moment
    session_ids = sorted(latest, key=lambda sid: (latest[sid], sid))[-3:]
    touched = {sid: set() for sid in session_ids}
    for attempt in attempts:
        if attempt["session_id"] in touched:
            touched[attempt["session_id"]].update(skills[sid][0] for sid in attempt["subskill_ids"])
    covered = set().union(*touched.values())
    return {
        "window_size": 3,
        "window_complete": len(session_ids) == 3,
        "session_ids": session_ids,
        "sessions": [
            {"session_id": sid, "last_activity": latest[sid].isoformat(),
             "domain_ids": [did for did in domains if did in touched[sid]]}
            for sid in session_ids
        ],
        "touched_domain_ids": [did for did in domains if did in covered],
        "missing_domain_ids": [did for did in domains if did not in covered],
    }


def report(catalog, ledger, as_of, stale_days=10):
    mapping(catalog, "catalog")
    text(catalog.get("exam"), "catalog exam")
    domains, objectives, skills = validate_catalog(catalog, catalog["exam"], as_of)
    attempts, units = validate_ledger(ledger, catalog, skills, as_of)
    local_zone = study_timezone(ledger.get("study_timezone"))
    states = {sid: skill_state(attempts, sid, local_zone) for sid in skills}
    for state in states.values():
        state["stale"] = bool(
            state["last_independent"]
            and (as_of - timestamp(state["last_independent"]).astimezone(
                local_zone or timezone.utc).date()).days >= stale_days
        )
    metrics = ("introduced", "assessed", "demonstrated", "delayed_transfer", "stale")
    domain_reports, objective_reports = [], []
    for oid, (did, objective) in objectives.items():
        ids = [skill["id"] for skill in objective["subskills"]]
        objective_reports.append({
            "id": oid, "domain_id": did, "title": objective["title"],
            "total": len(ids),
            **{metric: sum(states[sid][metric] for sid in ids) for metric in metrics},
            "unassessed": [sid for sid in ids if not states[sid]["assessed"]],
            "unresolved": [sid for sid in ids if not states[sid]["demonstrated"]],
        })
    for did, domain in domains.items():
        ids = [sid for sid, (domain_id, _, _) in skills.items() if domain_id == did]
        domain_reports.append({
            "id": did, "title": domain["title"], "total": len(ids),
            "weight_min": domain["weight_min"], "weight_max": domain["weight_max"],
            **{metric: sum(states[sid][metric] for sid in ids) for metric in metrics},
        })
    midpoint_total = sum((d["weight_min"] + d["weight_max"]) / 2 for d in domain_reports)
    weighted = sum(
        ((d["weight_min"] + d["weight_max"]) / 2) * d["assessed"] / d["total"]
        for d in domain_reports
    ) / midpoint_total
    normal = [unit for unit in units if unit["mode"] == "normal"]
    counts = Counter(unit["kind"] for unit in normal)
    voided = {v["attempt_id"] for v in ledger.get("voided_attempts", [])}
    pending = []
    for check in ledger["pending_checks"]:
        if check["after_attempt_id"] in voided:
            continue
        if check["status"] == "pending":
            pending.append(check)
        elif check["evidence_attempt_id"] in voided:
            pending.append(dict(check, status="pending", evidence_attempt_id=None, reopened_by_void=True))
        elif check["kind"] == "delayed_transfer":
            evidence = next(a for a in attempts if a["id"] == check["evidence_attempt_id"])
            if (
                evidence.get("retention_source_id") != check["after_attempt_id"]
                or not delayed_eligible(evidence, attempts, local_zone)
            ):
                pending.append(dict(check, status="pending", evidence_attempt_id=None,
                                    ineligible_retention=True))
    lifecycle = unit_lifecycles(ledger)
    completed = Counter(u["kind"] for u in normal if lifecycle[u["id"]] == "completed")
    debt = [
        {"unit_id": u["id"], "kind": u["kind"], "status": lifecycle[u["id"]],
         "subskill_ids": u["subskill_ids"]}
        for u in normal if lifecycle[u["id"]] in {"started", "interrupted", "deferred"}
    ]
    active = [d for d in debt if d["status"] != "deferred"]
    return {
        "exam": catalog["exam"], "revision": catalog["revision"],
        "catalog_verified": catalog["verified"],
        "verification_note": catalog["verification_note"],
        "as_of": as_of.isoformat(), "total_subskills": len(skills),
        "total_objectives": len(objectives),
        "subskills": {metric: sum(s[metric] for s in states.values()) for metric in metrics},
        "objectives_fully_assessed": sum(o["assessed"] == o["total"] for o in objective_reports),
        "objectives_fully_demonstrated": sum(o["demonstrated"] == o["total"] for o in objective_reports),
        "weighted_assessed_percent": round(weighted * 100, 2),
        "weighted_method": "Normalized domain-weight midpoints; not an exam score or completeness claim",
        "next_allocation": CYCLE[len(normal) % len(CYCLE)],
        "next_action": "resume_unfinished" if active else "allocate",
        "unfinished_units": debt,
        "completion_unknown_units": [u["id"] for u in units if lifecycle[u["id"]] == "unknown"],
        "completed_allocation": dict(completed),
        "completed_normal_units": sum(completed.values()),
        "study_timezone": ledger.get("study_timezone"),
        "retention_ineligible_attempts": [
            a["id"] for a in attempts
            if a["context"] == "delayed_transfer" and not delayed_eligible(a, attempts, local_zone)
        ],
        "normal_units": len(normal), "actual_allocation": dict(counts),
        "cycle_remaining": dict(Counter(CYCLE[len(normal) % len(CYCLE):])),
        "override_units": sum(u["mode"] == "override" for u in units),
        "domains": domain_reports, "objectives": objective_reports,
        "session_breadth": session_breadth(domains, skills, ledger, attempts),
        "states": states,
        "coverage_queue": coverage_queue(domains, skills, states, units, attempts),
        "pending_checks": pending,
        "voided_attempts": len(voided),
        "invalidated_checks": [
            c["id"] for c in ledger["pending_checks"] if c["after_attempt_id"] in voided
        ],
        "unassessed": [sid for sid, state in states.items() if not state["assessed"]],
        "blocked": [] if catalog["verified"] else ["Official source reconciliation is unverified"],
    }


def render(data):
    lines = [
        f"# {data['exam'].upper()} coverage",
        f"Catalog verified: {data['catalog_verified']} ({data['revision']})",
        f"Evidence SHA-256: {data['sha256'] or 'missing ledger; run init'}",
        f"Independently assessed objectives: {data['objectives_fully_assessed']}/{data['total_objectives']}",
        f"Independently demonstrated objectives: {data['objectives_fully_demonstrated']}/{data['total_objectives']}",
    ]
    for metric, count in data["subskills"].items():
        lines.append(f"- {metric}: {count}/{data['total_subskills']} subskills")
    lines.extend([
        f"- Weighted assessment coverage: {data['weighted_assessed_percent']}% (not an exam score)",
        f"- Next normal allocation: {data['next_allocation']}",
        f"- Next action: {data['next_action']}; unfinished units: {len(data['unfinished_units'])}",
        f"- Started allocation: {data['actual_allocation']}; completed: {data['completed_allocation']}",
        f"- Legacy completion unknown: {len(data['completion_unknown_units'])}",
        f"- Study timezone: {data['study_timezone'] or 'unknown; delayed retention not established'}",
        f"- Remaining in allocation cycle: {data['cycle_remaining']}",
        f"- Pending cold/transfer checks: {len(data['pending_checks'])}",
        f"- Next breadth candidates: {', '.join(data['coverage_queue'][:5])}",
        f"- Domain breadth window: {len(data['session_breadth']['session_ids'])}/3 sessions (all modes)",
        f"- Window sessions (oldest first): {', '.join(data['session_breadth']['session_ids']) or 'none'}",
        f"- Domain breadth gaps: {', '.join(data['session_breadth']['missing_domain_ids']) or 'none'}",
        "",
        "| Domain | Assessed | Demonstrated | Delayed transfer |",
        "| --- | --- | --- | --- |",
    ])
    for domain in data["domains"]:
        lines.append(
            f"| {domain['title']} | {domain['assessed']}/{domain['total']} "
            f"| {domain['demonstrated']}/{domain['total']} "
            f"| {domain['delayed_transfer']}/{domain['total']} |"
        )
    gaps = [obj for obj in data["objectives"] if obj["unresolved"] or obj["unassessed"]]
    lines.append(f"\n## Unassessed or unresolved objectives ({len(gaps)} total)")
    for obj in gaps[:10]:
        lines.append(
            f"- {obj['id']} {obj['title']}: unassessed "
            f"{', '.join(obj['unassessed']) or 'none'}; not demonstrated "
            f"{', '.join(obj['unresolved']) or 'none'}"
        )
    if len(gaps) > 10:
        lines.append(f"- {len(gaps) - 10} additional objectives; use --json for the complete inventory.")
    for blocked in data["blocked"]:
        lines.append(f"BLOCKED: {blocked}")
    lines.append("\nCoverage describes published scope, not guaranteed mastery or exam success.")
    return "\n".join(lines)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def completion_reopened(check, ledger):
    voided = {v["attempt_id"] for v in ledger.get("voided_attempts", [])}
    if check.get("evidence_attempt_id") in voided:
        return True
    if check.get("kind") != "delayed_transfer":
        return False
    effective = [a for a in ledger["attempts"] if a["id"] not in voided]
    evidence = next((a for a in effective if a["id"] == check.get("evidence_attempt_id")), None)
    return (
        evidence is None
        or evidence.get("retention_source_id") != check.get("after_attempt_id")
        or not delayed_eligible(evidence, effective, study_timezone(ledger.get("study_timezone")))
    )


def merge_batch(ledger, batch):
    mapping(batch, "batch")
    require(set(batch) <= {"attempts", "study_units", "pending_checks", "voided_attempts",
                          "unit_events", "study_timezone"},
            "Unknown batch fields")
    require(batch, "Empty batch")
    merged = json.loads(json.dumps(ledger))
    merged.setdefault("voided_attempts", [])
    merged.setdefault("unit_events", [])
    # Check repairs depend on proposed voids, but must also retain prior reopening eligibility.
    for key, additions in sorted(batch.items(), key=lambda item: item[0] == "pending_checks"):
        if key == "study_timezone":
            require(additions is not None, "Cannot clear the study timezone")
            study_timezone(additions)
            require(merged.get(key) in (None, additions),
                    "Study timezone is fixed; changes require explicit evidence migration")
            merged[key] = additions
            continue
        rows = unique_rows(additions, key)
        existing = {row["id"]: row for row in merged[key]}
        for rid, row in rows.items():
            if rid not in existing:
                if key == "study_units":
                    require(row.get("lifecycle") == "started",
                            "New activities must explicitly start; legacy completion is unknown")
                if key == "attempts" and row.get("context") == "delayed_transfer":
                    require(merged.get("study_timezone") or batch.get("study_timezone"),
                            "Delayed retention requires a recorded study timezone")
                    text(row.get("retention_source_id"), "Delayed retention source")
                merged[key].append(row)
            elif row != existing[rid]:
                old = existing[rid]
                reopened = (
                    key == "pending_checks" and old.get("status") == "completed"
                    and (completion_reopened(old, ledger) or completion_reopened(old, merged))
                )
                allowed = (
                    key == "pending_checks" and (old["status"] == "pending" or reopened)
                    and row.get("status") == "completed"
                    and {k: v for k, v in old.items() if k not in {"status", "evidence_attempt_id"}}
                    == {k: v for k, v in row.items() if k not in {"status", "evidence_attempt_id"}}
                )
                require(allowed, f"Conflicting existing {key} ID: {rid}")
                merged[key][merged[key].index(old)] = row
    return merged


def atomic_write(path, data, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".json.lock")
    temp_path = None
    try:
        try:
            lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise CoverageError(f"Coverage writer lock exists: {lock}; inspect before retrying") from exc
        try:
            os.close(lock_fd)
            require(digest(path) == expected, "Ledger changed since audit; reload and merge")
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix="coverage.", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(data, stream, indent=2, ensure_ascii=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            require(digest(path) == expected, "Concurrent ledger change detected; refusing overwrite")
            os.replace(temp_path, path)
            temp_path = None
            return digest(path)
        finally:
            lock.unlink()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "init", "record"))
    parser.add_argument("--exam", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--stale-days", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    try:
        require(
            args.exam and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.exam),
            "Invalid exam folder name",
        )
        require(args.stale_days > 0, "stale-days must be positive")
        as_of = audit_date(args.as_of)
        exam_path = args.root / "exams" / args.exam
        catalog = read_json(exam_path / "blueprint.json")
        validate_catalog(catalog, args.exam, as_of)
        path = exam_path / "assets" / "coverage.json"
        before = digest(path)
        snapshot_hash = before
        ledger = read_json(path) if before is not None else empty_ledger(catalog)
        if args.command == "init":
            require(before is None, "Ledger already exists; init never overwrites evidence")
            report(catalog, ledger, as_of, args.stale_days)
            snapshot_hash = atomic_write(path, ledger, None)
        elif args.command == "record":
            require(before is not None, "Missing ledger; run init first")
            require(args.expected_sha256 == before, "Expected SHA-256 missing or stale; run audit")
            require(args.input is not None, "record requires --input")
            report(catalog, ledger, as_of, args.stale_days)
            old_ids = {a["id"] for a in ledger["attempts"]}
            old_checks = {c["id"]: c for c in ledger["pending_checks"]}
            ledger = merge_batch(ledger, read_json(args.input))
            report(catalog, ledger, as_of, args.stale_days)
            effective, _ = validate_ledger(
                ledger, catalog, validate_catalog(catalog, args.exam, as_of)[2], as_of,
            )
            for attempt in effective:
                if attempt["id"] not in old_ids and attempt["context"] == "delayed_transfer":
                    require(
                        delayed_eligible(attempt, effective, study_timezone(ledger.get("study_timezone"))),
                        "New delayed transfer needs a fresh unaided scenario on a later local day",
                    )
            effective_by_id = {a["id"]: a for a in effective}
            for check in ledger["pending_checks"]:
                if check == old_checks.get(check["id"]):
                    continue
                require(check["after_attempt_id"] in effective_by_id,
                        "A new check or completion cannot use a voided learning source")
                if check["status"] != "completed":
                    continue
                evidence = effective_by_id.get(check["evidence_attempt_id"])
                require(evidence is not None, "A new check completion cannot use a voided answer")
                if check["kind"] == "delayed_transfer":
                    require(
                        evidence.get("retention_source_id") == check["after_attempt_id"]
                        and delayed_eligible(
                            evidence, effective, study_timezone(ledger.get("study_timezone")),
                        ),
                        "Delayed check completion requires its source and a later local day",
                    )
            snapshot_hash = atomic_write(path, ledger, before)
        result = report(catalog, ledger, as_of, args.stale_days)
        final_hash = digest(path)
        require(final_hash == snapshot_hash,
                f"Ledger changed during {args.command}; retry for a consistent snapshot")
        result["sha256"] = final_hash
        result["ledger_exists"] = path.exists()
        print(json.dumps(result, indent=2) if args.json else render(result))
        return 0
    except (CoverageError, OSError) as exc:
        print(f"Coverage error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
