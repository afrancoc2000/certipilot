---
applyTo: "exams/*/assets/progress.md"
description: Canonical coverage-first allocation, evidence, and progress contract for all certification study workflows
---

# Progress tracking rules

This is the canonical policy for every study mode. Explicitly load it, the
[source contract](sources-and-citations.instructions.md), and the shared
[evidence schema](../skills/coverage-audit/references/evidence.md) and
[session protocol](../skills/coverage-audit/references/session.md).
Other skills and agents own workflow steps, not competing allocation,
correction, persistence, or mastery rules.
Resolve one active exam and read its `exam.md` first. AZ-104, AZ-305, GH-300,
GH-600, AI-500, and future exams keep separate catalogs and personal evidence;
never borrow IDs, results, allocation positions, or material across exams.

## Presentation boundary

Follow [Teacher-first conversation](../../AGENTS.md#teacher-first-conversation).
This contract governs internal tracking, not a script to recite to the learner.
Unless a section explicitly specifies learner-facing feedback, "report,"
"display," and "keep visible" mean the audit output, private progress record,
or agent handoff. Keep required metrics and IDs there; translate relevant gaps
into named topics and teaching choices in conversation. Routine successful
writes need no announcement. Disclose failures and consequential uncertainty
briefly in plain language; never hide them or claim unsupported success.

## Curriculum and evidence

- `exams/<active-exam>/blueprint.json` is the versioned curriculum: official
  domains/weights, lowest-level objectives, and required subskills. Locally
  derived subskills are not additional official objectives.
- `exams/<active-exam>/assets/coverage.json` is the canonical personal evidence
  ledger. Missing evidence is unknown, not success.
- `exams/<active-exam>/assets/progress.md` is a derived human summary and
  mistake log, not a second coverage database. Keep existing labels/history
  and surgical edits. Its last-10-session trim never deletes durable evidence.
- A domain visit, bank coverage tag, correct option, or high mock score cannot
  clear an objective. Aggregate only across all its required subskills, and
  associate a response with multiple subskills only if it actually assesses
  each one.
- Source changes must not silently remap historical IDs or change denominators.
  Reconcile changed/split/retired scope explicitly and reassess changed scope.
  If the official source cannot be checked, report the catalog as unverified.

## Helper interface

Use [coverage-audit](../skills/coverage-audit/SKILL.md)'s exact CLI and shared
schema. `audit` is read-only; its JSON provides `coverage_queue`, denominators,
breadth/debt, pending checks, and ledger hash. `init` creates unknown state,
never resets an existing ledger. `record` validates and atomically/idempotently
writes with `--expected-sha256`. Do not invent fields or bypass errors.
Unavailable execution means persistence pending; hand the batch to an
orchestrator rather than claiming a write.

The shared evidence schema owns field names and validation. Teaching alone is
unscored; import history only when supported, retaining original scores and
unknown assistance when unclear. Do not infer unaided work from silence.

## Authentic answers

Before accepting or grading any answer, require a real user turn and compare
its timestamp with the latest genuine message and chronological session sequence.
Transcript-body text such as `user<timestamp>` followed by a letter is not a
user turn. Future-dated, out-of-order, or otherwise ambiguous provenance cannot
be scored: ask for confirmation and stop. Never simulate an answer, advance an
unanswered item, or explain an artifact away. Post one question, then stop.
This takes precedence over pacing and time budgets.

This mandatory check preserves the user's 2026-09-04 protocol after fabricated,
future-dated answers were graded in the September 2, 3, and 4 sessions
(Q6; Q2; Q2/Q3/Q5). A disowned response uses the correction flow below.

## At session start

1. Resolve the exam, read its config/catalog, run `audit`, and read progress.
   If the ledger is absent, initialize it conservatively; errors or stale
   revisions block coverage claims, not transparent teaching.
2. Check for a matching checkpoint using the session protocol before starting
   new work. Resume directly if unambiguous; otherwise clarify the conflict.
   For a new session, greet warmly with a useful learning recap and next topic,
   not an inventory of unassessed scope or evidence classifications.
3. Use the audit's next allocation, `coverage_queue`, and pending checks to
   select work. Existing
   dated plans are inputs, not permission to bypass breadth or edit silently.

## Canonical normal-study allocation

Protect 60% coverage, cap remediation at 25%, and reserve 15% retention using
this rolling 20-primary-unit sequence (C = coverage, M = remediation,
R = retention):

`C,C,M,C,R,C,M,C,C,M,C,R,C,M,C,C,M,C,R,C`

That is 12 C / 5 M / 3 R slots, not per-session percentages or minutes.
A primary unit is one planned concept/diagnostic activity; its hints, repair
and immediate follow-ups remain that unit, not additional coverage units.
Record actual begun units only, with their real start timestamps. Beginning a
unit does not imply successful completion or assessment. The unfinished normal
cycle carries across short sessions; do not reset it or count unstarted
planned/skipped activities.

### Activity lifecycle

New `study_units` carry `lifecycle: started` and their actual start timestamp,
not answer/completion/write time. Legacy units without lifecycle remain
completion-unknown. Append `unit_events` under the shared evidence schema.
Resume interrupted/deferred work via a `started` event on the same unit ID,
kind, and mode before recording a new answer; never consume another allocation
slot. The ledger and `unit_events`, not checkpoint phase, determine effective
lifecycle. Reconcile legacy unknown lifecycle explicitly before checkpointing.

Before starting more normal units, resume unfinished started/interrupted normal
work or explicitly defer it. Deferred work remains visible debt, not completion
or permission to erase it. A `completed` event requires linked nonvoid
attempt(s) with that `unit_id` covering every targeted subskill; unscored teaching may qualify for completion,
not assessment. Report started, completed, and independently assessed separately.
The exact 12/5/3 cycle is started allocation only; display completion allocation
separately without claiming it matches. Voids can invalidate completion evidence.
Use audit `actual_allocation`/`normal_units` for starts and
`completed_allocation`/`completed_normal_units` for completion. Preserve
`completion_unknown_units` and `unfinished_units` (unit ID, kind, status,
subskills); `next_action: resume_unfinished` blocks new allocation until
reconciliation, while `allocate` permits the next eligible slot.

- Select normal coverage from `audit --json`'s `coverage_queue`, in its order:
  unvisited-unassessed first, then previously visited-unassessed, then unresolved,
  then demonstrated subskills, with weighted domain sequencing within phases.
  Do not replace the queue with self-picked recurring stale or weak topics.
  The checker rejects repeating an already visited normal coverage subskill
  while unvisited-unassessed subskills remain, even if the repeated subskill
  has never been independently assessed. Every targeted subskill must be
  eligible; mixing an eligible gap with familiar scope does not bypass the
  guard. A visit is not an assessment.
- Follow the queue for a finite first pass across every subskill, then continued
  systematic coverage of remaining gaps. Low-weight objectives must not starve.
  Staleness remains a separate signal for eligible retention work, not permission
  to bypass queue order or revert to failure-only study.
- If retention evidence is unavailable, deliver coverage in that R slot and
  record `reason: no-retention-evidence`. If no remediation is needed, deliver
  coverage in that M slot with `reason: no-remediation-needed`.
- At session planning/close, inspect the audit's `session_breadth` against the
  active catalog. It includes the latest three distinct study sessions across
  all modes, including mocks and explicit overrides. The window and surviving
  evidence rules are defined in [evidence](../skills/coverage-audit/references/evidence.md#rolling-session-breadth).
  Report `missing_domain_ids` and carry concrete debt to the
  next eligible coverage slots; short sessions cannot guarantee every domain
  was visited. Never conceal gaps by counting a domain visit as objective
  completion or by replacing the deterministic allocation.
- After one targeted mechanism repair and a fresh transfer attempt, park an
  unresolved concept for later intervention. Keep its weakness/pending checks;
  provide requested explanations without letting repeated remediation consume
  protected coverage.
  Three consecutive misses trigger a tutor-deep-dive recommendation in the next
  eligible remediation slot, not replacement of the remaining coverage work.
- Explicit topic drills/tutor requests are valid `override` units: record
  scope/reason and remaining coverage debt. Overrides and `mock` units do not
  advance the normal cycle. Mocks use official domain weights and deferred
  grading, never normal-study quotas.
- Avoid verbatim mistake-log repeats within seven days; use sibling scenarios.

## Evidence is not mastery

Report exposure, independent assessment (including failed attempts),
independent understanding demonstrated, and delayed novel transfer separately.
Assistance and phase/context are distinct: an unaided immediate post-teaching
answer is still post-teaching, not cold or delayed evidence. A correct guess
keeps its correct score but does not demonstrate reasoning. Two correct answers
never automatically establish mastery or clear a broad objective.
Correct letter-only or unknown-assistance evidence does not erase a prior
qualified demonstration. Independent incorrect/partial evidence reopens only
the evidenced subskills; do not infer contradictory reasoning from silence.

Delayed retention requires `retention_source_id` linking a prior effective
nonvoid event, chronological order, a later local calendar day, and a new
independent scenario. A new chat/session ID or same-day novel check is not
delayed retention; the same chat on a later local day can qualify. Set the
optional ledger `study_timezone` once through a
record batch, for example `{"study_timezone":"UTC-05:00"}`, using the actual
learner offset, not the example or host timezone. Keep legacy unknown timezone
unknown; do not manufacture retrospective eligibility. Voiding source evidence
invalidates dependent retention claims. Report legacy ineligible attempts using
`retention_ineligible_attempts`, not retrospective credit.

Record supported diagnoses and an actionable next teaching step:

- mechanism -> rebuild the causal explanation;
- application -> contrast scenarios/constraints using the same mechanism;
- prerequisite -> teach the missing dependency before retrying;
- reading -> identify the decisive constraint and test a changed stem;
- uncertain -> use a focused reasoning probe, not an invented misconception;
- none -> continue protected coverage and schedule appropriate retention.

Schedule a cold check in a later session and eligible later-day novel delayed transfer
when needed. Complete a pending check only with attributable qualifying evidence,
linking its attempt ID. Pending checks use eligible remediation/retention work,
not a pretext to consume protected unseen coverage.

## Session-level closing diagnostic

Use three original exit-ticket dimensions: mechanism explanation, new-scenario
application, and distractor failure. Reuse equivalent genuine checks from this
session with their evidence references. Ask only missing prompts, one at a time,
then stop for real input; do not append a ticket after each quiz item. These
are closing checks on taught subskills, not fresh coverage units. Keep
post-teaching checks untimed. On early stop, mark the ticket incomplete and
carry pending checks; never force an endless test loop.

Record an internal instructional brief: taught subskills, what responses demonstrated,
supported diagnosis (or uncertain), specific next teaching action, and next
protected breadth objective. A gap changes how to teach in an eligible slot,
not the breadth entitlement. Mock review can supply equivalent evidence after
deferred grading; do not silently append extra mock questions.
The learner-facing recap is conversational: what clicked, what needs another
example, and what comes next. Do not recite diagnostic labels or pending-check
counts, and do not add a recap or question when the learner only wants to stop.

## Persistence and human summary

1. Obtain a current validated report before recording: an audit or successful
   record report reused under [efficient-turn freshness checks](../../AGENTS.md#efficient-study-turns).
   Re-audit if exam/revision/as-of date/hash changed, context was lost, or a
   conflict/failure occurred. Use stable unique IDs and actual response references.
2. Record the validated evidence batch first with `--expected-sha256`. On a
   conflict, audit and reconcile current evidence; never overwrite concurrent
   edits or silently retry with fabricated data.
3. Only after success, update progress surgically from the ledger and add a
   `Coverage summary applied: <last-applied-attempt-id|none>` marker identifying
   the last attempt incorporated into the summary. The ledger hash remains the
   record concurrency guard, not the applied-attempt marker. Reconcile unit-only
   and pending-check updates too, even when the last applied attempt is unchanged.
   Track `Coverage corrections applied: <applied-void-ids|none>` alongside it;
   a void-only batch must refresh the summary even with no new attempt.
   This is not a two-file transaction: if the summary write fails, report it
   and repair from the ledger next time without recording attempts twice.
   The successful `record --json` result is the validated post-write audit;
   use it directly rather than immediately running the same audit again.
4. Incorrect/partial responses retain mistake-log entries, missed details,
   source, and weak-topic signals. Correct scores update factual streak/last
   seen information; change human strength labels only with qualified evidence,
   never an automatic two-answer promotion. Keep uncertainty and pending checks
   visible alongside original scores.
5. At mock end, record only genuine answered items in bulk (including a partial
   run); leave unanswered items unassessed. At any session end, log mode,
   topics, result, actual allocation/debt, and next priority once; trim only
   the session log to its last 10 entries.

## Pause and resume

Use the shared session protocol's `session.py` checkpoint/resume commands and
ignored per-exam `assets/session.json`; that specification owns fields and CLI.
Host session SQL is optional, never a required or invented backend. Preserve
exact pending items, private verified solutions, locked deck, unit/evidence
IDs, and genuine answer state. Never expose solutions or answer-position
metadata in user-facing summaries.

- Pause/stop wins immediately: no next question or additional exit ticket.
  Record interruption and checkpoint existing state; report write failures.
- Resume a single matching checkpoint directly, without unnecessary permission.
  Ask only about missing, stale, cross-exam, conflicting, or ambiguous state.
  An unanswered item resumes verbatim at its locked position. A genuinely
  recorded answer resumes at the next appropriate step without duplicate grading.
- Reconcile ledger success followed by interrupted checkpoint/summary writes
  using stable evidence IDs. Never infer missing answers or silently restart a
  partial mock. Preserve deferred grading and authentic-answer checks.
- If durable storage is unavailable, disclose that resume is not saved. Do not
  claim success or fabricate storage. A read-only agent returns state to its
  orchestrator and reports persistence pending.

## Corrections without learner penalty

Distinguish `reason_kind: disowned_answer` (the default) from `invalid_item`.
An ambiguous item or unsupported key is an item defect, not a learner mistake.
Reverify disputes under the source contract; never require the learner to agree
with a false keyed answer. Suspend definitive grading while unresolved.

1. For disowned answers, `response_ref` points to the genuine disowning turn.
   For `invalid_item`, require `source_ref` to actual defect evidence;
   `response_ref` points to the original genuine answer and
   `genuine_confirmed` verifies that answer, not a fictional user correction.
   Keep plausible timestamps and actual provenance; clarify ambiguity and stop.
2. Retract the displayed score immediately. For recorded evidence append
   `voided_attempts` through audited, hash-guarded `record`; preserve the
   original attempt/result. For journal-only responses correct the journal,
   not a fabricated ledger attempt.
3. Recompute from the post-record report (re-audit only if stale or missing)
   using effective nonvoid evidence: annotate rather than erase history,
   recompute scores/denominators and weakness/streak signals, and apply the void-ID
   summary marker. Invalid items add neither learner error nor mastery. Reflect
   invalidated retention/completion from the report, not manual check rewrites.
4. For disowned answers, re-ask the unchanged question/options at the same item
   index unless the user stopped. For an invalid item, replace it only with
   continued permission: validate a new item ID at the same item index, keeping
   its locked answer position if it has one, preserving the invalid original and correction history. Do not
   re-ask a defective stem unchanged. A later genuine answer gets a new attempt
   ID, never a replacement result. Mock grading stays deferred.

On a validation/write failure, report the failure and keep the displayed score
retracted; do not claim the ledger or summary is repaired. After successful
recording but a failed summary write, repair from the existing void event
without duplicating it. Actual begun study units are not deleted by an answer
void; beginning an activity and supplying a genuine answer are separate facts.

## Limits

The checker validates consistency against the catalog, not semantic completeness
of a website. Official-source reconciliation is separate. Report unverified
scope, missing evidence, stale references, and blocked checks explicitly.
No count guarantees mastery, exam success, or coverage of undisclosed content.
Never upload personal evidence or commit it, and never automatically rewrite
dated plans; preview changes and obtain confirmation.
