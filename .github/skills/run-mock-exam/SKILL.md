---
name: run-mock-exam
description: Run a 10-question certification mock exam with deferred grading, domain-weighted selection, and a per-domain summary at the end.
---

# Run mock exam

Use this skill to simulate exam pacing and calibration. Unlike a quiz, the
mock defers grading until all questions are answered.
Load the [canonical contract](../../instructions/progress-tracking.instructions.md),
its shared evidence/session specifications, the
[source contract](../../instructions/sources-and-citations.instructions.md), and
the [quiz presentation/deck contract](../../agents/quiz-agent.agent.md#correct-answer-position-generation).

## Inputs

- Optional: target time (default 20 minutes for 10 questions).
- Question banks and style references declared in
  `exams/<active-exam>/exam.md`. When no bank exists, author original questions
  from the listed authoritative first-party sources.
- `exams/<active-exam>/assets/progress.md` weak/strong topics.
- Active exam catalog and read-only audit, with subskill IDs, revision,
  uncovered scope, and pending checks. Load the
  [canonical evidence contract](../../instructions/progress-tracking.instructions.md).
- Any existing `exams/<active-exam>/material/test-exams/*/results.md`
  failed-question indices (avoid verbatim repeats per
  `.github/instructions/sources-and-citations.instructions.md`).

## Domain weighting

Mock exams calibrate against the official exam outline, **not** today's
sprint-plan focus. Use plan topics only as a tiebreaker when picking
specific questions inside a domain.

Read the domains and weight ranges from the active exam's `blueprint.json`,
reconciled with `exam.md` and the official outline. Report an unverified or
conflicting source rather than claiming verified coverage. Compute quotas once
before selecting items, using this deterministic rule:

Use `python .github\skills\coverage-audit\scripts\session.py mock-quotas --exam <active-exam> --json`
to compute the quotas from the validated catalog; do not reimplement the
calculation by intuition. This command is read-only and requires no learner
ledger. Its output is private preparation bookkeeping, not a learner dashboard.

1. Use each domain's midpoint: `weight = (weight_min + weight_max) / 2`.
   Normalize across all domains: `quota = 10 * weight / sum(weights)`;
   midpoints need not sum to 100. If the official outline omits a usable weight
   for any domain, stop mock preparation and report the blocking source gap.
   There is no equal-weight fallback. Obtain source-supported numeric ranges
   for every domain and reconcile the catalog before retrying; never invent
   official weights. Invalid or conflicting catalog data also requires
   reconciliation, not silent fallback.
2. Start each domain at `count = max(1, floor(quota))`.
3. If the total is below 10, repeatedly add one question to the domain with
   the largest `quota - count`, recalculating after each addition.
4. If the total is above 10 because of the one-question minimum, repeatedly
   remove one question from the domain with the largest `count - quota` among
   domains with `count > 1`, recalculating after each removal.
5. Break every tie by earlier position in the catalog's `domains` array, not
   plan focus, weakness, alphabetical order, or random choice. Compare exact
   fractions rather than rounded percentages. Confirm the counts sum to 10
   and every domain has at least one question. With more than 10 domains,
   stop and ask to increase the mock length; never silently omit a domain.

Examples in catalog order: ranges `25-30, 20-25, 15-20, 30-35` produce
counts `3, 2, 2, 3`. Ranges `20-25, 15-20, 20-25, 15-20, 10-15` produce
`3, 2, 2, 2, 1` after normalization and the catalog-order tiebreak.
Six equally weighted domains produce `2, 2, 2, 2, 1, 1`.
The minimum-one rule is a breadth constraint, not a claim that a 10-item mock
can reproduce official percentages exactly.

Within each domain, prefer scenario-based questions. Aim for at least 2
weak-topic items across the mock when supported and compatible with quotas;
do not force two into every domain or displace official weights. If an active sprint
plan covers today, prefer plan topics when breaking ties between candidate
questions in the same domain.

Use `mode: mock` for actual units and `context: mock` for attempts. Mocks do
not advance the normal allocation cycle or repay its debt. Coverage breadth
and independent evidence are reported separately from the weighted score.

## Procedure

1. Resume an unambiguous matching checkpoint before preparing a new mock.
   For a new run, announce 10 questions, target time, and deferred grading.
2. Before authoring questions, decide the 10-item manifest's formats, then
   generate and save the private `answer_position_deck` with `kind: planned`,
   one shuffled position per four-option single-answer item (10 when all are
   single-answer), `cursor: 0`, and empty `items`, following the
   [deck schema](../coverage-audit/references/session.md#private-answer-position-deck).
   Before asking question 1, precompute the complete mock. Select and verify
   every item, apply the locked answer-position deck, and persist the ordered
   `items` array in the private exam-local checkpoint using the
   [checkpoint schema](../coverage-audit/references/session.md#private-question-metadata).
   Set the cursor to the deck length when saving this manifest; the helper allows an empty preparation checkpoint to acquire its
   complete mock once, then locks the manifest. This single item array supplies
   both views; do not invent separate top-level manifest fields.
   - Public view: question number derived from its one-based array position,
     stem and neutral options. Resume exposes only the safe question fields.
   - Private view: the owning mock activity's `unit_id`, `private_key`,
     `private_rationale`, and `private_metadata`
     (source/bank item ID, domain, topic, subskill IDs, verification snapshot).
     Catalog revision is the checkpoint's `blueprint_revision`; genuine answers
     use the existing `response` and `attempt_id` fields. Include metadata for
     every newly prepared item. Older metadata-free checkpoints remain readable,
     but missing verification must be recovered before definitive grading.
     The one mock activity must declare every subskill targeted by the manifest;
     bind every item to that same unit before saving, not to a later response's
     session or an unrelated activity.
   Validate question count and numbering, domain quotas, answer-position
   sequence, four options per item, and absence of answer leakage from the
   public manifest. Apply the
   [item-quality gate](../select-next-question/SKILL.md#item-quality-gate) to every
   item. Do not start until validation and durable checkpointing succeed; report
   unavailable storage rather than claim a resumable mock.
3. Use [select-next-question](../select-next-question/SKILL.md) while building
   the manifests, not between user answers. During the live mock, read the next
   item directly from the cached public manifest so question transitions are
   immediate.
4. Ask one question per turn. Accept the answer. Do **not** grade, hint,
   reveal, restate, or comment on the correct option while the mock is in
   progress.
5. Check genuine-turn provenance and timestamp before accepting an answer;
   clarify ambiguity, never fabricate. Persist each genuine response/reference,
   timestamp, index, grading state, and `flagged_for_review` flag through the
   [canonical checkpoint](../coverage-audit/references/session.md) before advancing. Host session SQL is optional. A trailing `*`,
   "flag this," or "explain at the end" requests expanded review.
   Capture actual unit starts/lifecycle separately from answer times.
   Prepared questions/deck remain immutable during ordinary flow; do not
   reselect or reverify unchanged claims between answers.
6. After question 10, grade genuine answers and produce the summary (see Output).
   Keep assistance and reasoning separate from scores; a correct letter alone
   does not establish reasoning or delayed transfer.
7. Bulk-invoke [update-progress](../update-progress/SKILL.md):
   - Record validated attempts/actual mock units and qualifying pending checks
     before deriving progress. Leave unanswered/voided scope unassessed where
     no qualifying response exists; never infer a whole objective was covered.
   - One mistake-log entry per effective nonvoid incorrect/partial answer.
   - One session-log line with mode, effective score/denominator, and domains;
     exclude invalid/disowned responses and show unanswered/void counts separately.
8. Record audit breadth gaps and the next protected normal-study objective
   internally; explain relevant remaining topics as practical next steps.
   Post-mock instructional review may reuse genuine reasoning for the closing
   diagnostic. Do not alter the completed exam by adding required exit questions;
   incomplete dimensions and cold/delayed checks stay pending for later work.

## Presentation and continuity gates

- Apply [Question-last delivery](../../../AGENTS.md#question-last-delivery):
  finish required saves and internal handoffs before the final question, then
  yield. Use interactive mode; automated continuations are not learner input.
- Plain neutral options; one question, then stop for genuine input. Never cue
  the correct answer or demand reasoning during a deferred mock.
- Apply the quiz agent's mechanically randomized balanced locked deck. Record
  correct-position counts and learner selections separately in private records;
  disclose these diagnostics only on request after the mock ends.
- On pause/stop, checkpoint without another question or mandatory exit ticket.
  Pause preserves deferred grading; explicit ending/aborting permits partial
  review, not scoring unanswered items.
- Resume the exact unanswered item, original unit ID, and locked position.
  If an answer is already genuinely recorded, continue its next appropriate
  step without accepting/regrading it twice. Reconcile applied ledger IDs first.
  Missing/conflicting state requires clarification, not reconstruction or restart.

## Output (summary)

Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
During the mock, show question position and the question, not mock states or
save confirmations. At review, keep the useful score and full teaching review;
leave audit classifications, hashes, IDs, and allocation counts internal.

```
Mock exam result: X/N valid answered items (10 planned; target: NN min)
Unanswered / voided: <counts and reasons>

Per-domain breakdown:
- <each domain from the active exam catalog>: a/b

Learning recap (separate from score):
- <what the genuine answers showed and topics worth revisiting>
- <a useful next topic; relevant limitations in plain language, without an audit dashboard>

Missed questions:
1. QN — <topic>
   Question: <complete stem and all answer options>
   Your answer: <letter and option text>
   Correct answer: <letter and option text>
   Explanation: <why the correct answer wins and why the selected answer fails>
   Cite: <workspace-relative path or first-party URL>
2. ...

Flagged questions:
1. QN — <topic>
   Question: <complete stem and all answer options>
   Your answer: <letter and option text>
   Correct answer: <letter and option text>
   Explanation: <expanded mechanism-first explanation requested by the user>
   Cite: <workspace-relative path or first-party URL>

Recommended next steps:
- Tutor deep dive on: <topic with 2+ misses>
- Re-quiz: <other weak topics>
```

- For **every incorrect or partial answer**, reproduce the complete question,
  including all options, followed by the user's selected letter and option
  text, the correct letter and option text, and the explanation. Never reduce a
  miss to only a topic label or one-line rationale.
- Do the same for **every flagged question**, even when the user's answer was
  correct. A flagged item is any item whose live-journal entry requests an
  expanded explanation.
- If an item is both missed and flagged, present it once under Missed questions
  and label it `flagged for expanded explanation`; do not duplicate it.
- For an invalid item, reproduce the full stem/options and genuine answer if
  present, give the precise defect and first-party evidence, and state no
  learner penalty or mastery. Do not manufacture a unique correct answer.
  A disowned response is not an ambiguous item: label its provenance correction
  separately, retain history, and do not attribute that response to the learner.
- Keep only the primary score and per-domain summary under ~25 lines. The
  required missed, flagged, and voided question reviews may extend beyond that
  limit and must never be omitted for brevity.
- Cite per `.github/instructions/sources-and-citations.instructions.md`.

## Guardrails

- Never grade or react between questions; this preserves calibration value.
- Never re-ask a verbatim question from the mistake log within the past 7
  days.
- If the user ends/aborts mid-mock, bulk-update genuine answered evidence and
  log the partial run. A pause alone does not trigger grading.
- Apply canonical corrections via `update-progress`: disowned responses re-ask
  the cached item unchanged unless stopped; invalid items are replaced only
  with continued permission, after verification, at the same locked position.
  Retain the original item/void history and quotas. Never force agreement with
  an unsupported key, penalize the learner, or leak a live mock solution.
