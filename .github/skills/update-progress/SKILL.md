---
name: update-progress
description: Record validated canonical coverage evidence first, then safely derive the progress summary after grading or session close.
---

# Update progress

Use this skill across quiz, tutor, planner, and mock flows. Load the
[canonical contract](../../instructions/progress-tracking.instructions.md).
Also load its shared evidence/session specifications and the
[source contract](../../instructions/sources-and-citations.instructions.md).
The personal coverage ledger is authoritative; progress is a repairable human
summary, not a parallel database.
Use the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns):
one owner runs the validated save sequence directly, without repeated agent
handoffs or a redundant audit after a successful record.

## Inputs

- Topic (short, canonical name; reuse existing labels when present).
- Canonical attempts, actual study units/lifecycle events, pending checks, and optional
  `voided_attempts` in the
  [coverage-audit batch format](../coverage-audit/SKILL.md), with stable IDs,
  catalog revision, actual response references, and genuine-turn confirmation.
- Status when graded: ✅ correct / ⚠️ partial / ❌ incorrect; exposure is
  unscored. Planner-only activity has no fabricated answer or delivered unit.
- Optional: short note (what was missed, distractor pattern, source).
- Mode, using the checkpoint's `mode` values in the
  [session schema](../coverage-audit/references/session.md).

## Procedure

1. Resolve one active exam and load its config/catalog and progress. Obtain a
   current validated audit/record report under the efficient-turn freshness
   checks; when absent, changed or stale, audit:
   `python .github\skills\coverage-audit\scripts\coverage.py audit --exam <exam> --json`.
   If the ledger is absent, use `init --exam <exam>`; never overwrite an existing
   ledger. Catalog/source errors and unavailable execution must be reported.
2. Build a local batch from genuine evidence under the shared schema, with actual
   unit starts, `lifecycle: started`, linked `unit_id` attempts, and append-only
   `unit_events`. Resume the original unit ID; require nonvoid linked evidence
   before completion, including unscored teaching where appropriate. Keep
   legacy completion unknown and deferred debt visible. Apply canonical
   timezone/source-linked retention eligibility; never backdate or fabricate
   evidence, future starts, or completion.
3. Record before touching the human summary:
   `python .github\skills\coverage-audit\scripts\coverage.py record --exam <exam> --input <batch.json> --expected-sha256 <hash-from-audit> --json`.
   Follow the helper's validated batch schema, not manual ledger edits. On
   conflict, audit and reconcile without replacing concurrent changes. Retries
   reuse IDs and identical evidence; never duplicate attempts to repair a summary.
   Planner-only logging need not submit an empty evidence batch.
4. After successful recording, derive progress from the complete successful
   JSON report and committed hash. Abbreviated human-readable output cannot
   substitute for that report. Do not run another audit unless its freshness
   checks fail or the record result is unavailable. A failed record's output is
   not a report to reuse; audit/reconcile actual committed evidence first.
   Create missing summary sections only when needed:
   `## Coverage summary`, `## Weak topics`, `## Strong topics`,
   `## Mistake log`, `## Session log`.
   Preserve legacy coverage notes as historical, not proof of completion.
   Report objective/subskill denominators, independent assessment,
   demonstration/transfer, unresolved scope, allocation debt, and pending checks.
   Separate started allocation from completed allocation and assessment.
   Write `Coverage summary applied: <last-applied-attempt-id|none>` for the last
   attempt incorporated into the summary. Keep the audit hash for concurrency
   control, not as a substitute for the applied-ID marker.
   Also write `Coverage corrections applied: <applied-void-ids|none>` for void
   events incorporated into the summary; a correction need not add an attempt.
5. Preserve original scores. Effective nonvoid incorrect/partial answers receive concise
   mistake-log entries and weak-topic updates including supported diagnosis and
   action. Correct answers update factual streaks/last seen, not automatic
   promotion after two answers. Human strength summaries must reflect qualified
   evidence and remaining scope/uncertainty.
6. Keep edits surgical. If the summary write fails, explicitly report
   `evidence recorded; summary pending` and repair from the ledger on the next
   invocation. Unapplied attempt IDs trigger reconciliation, not re-recording.
   Unapplied void IDs likewise trigger repair from the ledger, not another void
   or a replacement answer. Also refresh unit-only/pending-check changes when
   the applied attempt ID is unchanged.
7. On close, append one session entry with actual work, result, closing diagnostic
   completeness, pending checks, next protected objective, and allocation debt;
   trim only the session log to 10. Log a mock once after deferred grading,
   including partial runs, and never score unanswered items.
8. Repeated misses suggest a targeted tutor intervention within eligible
   remediation work. Preserve breadth and the canonical bounded repair limit.

## Corrections and checkpoints

Apply [canonical corrections](../../instructions/progress-tracking.instructions.md#corrections-without-learner-penalty):
retain originals and genuine provenance, record append-only `voided_attempts`,
and reconcile effective scores, completion/retention, and applied void markers.
Distinguish disowned answers from `invalid_item`; neither creates a learner
mistake. Journal-only corrections do not manufacture ledger attempts.

After evidence writes, synchronize the private checkpoint through the shared
session protocol. Stable IDs repair interrupted summary/checkpoint writes,
not duplicate attempts or units. A pause stops questions immediately; disclose
storage failures. Host session SQL is optional.

## Output

- Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
- Return evidence persistence and summary synchronization status separately to
  the internal caller; retain unresolved evidence and pending checks in private
  records. Do not append routine save receipts, IDs, or counters to quiz feedback.
- If a write fails, explain its practical consequence and next step briefly
  to the learner; keep technical repair details in the internal handoff.
- Do not claim success if either recording or summary repair failed.

## Guardrails

- Never delete history outside the session-log trim rule.
- Never reorder unrelated sections.
- Preserve existing labels; do not rename topics arbitrarily.
- On a failed correction write, keep the displayed score retracted and report
  persistence as pending; never call a summary-only change a ledger repair.
- Keep batches/evidence local. Never edit source banks or dated plans here.
