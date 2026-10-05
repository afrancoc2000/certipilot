---
name: run-mock-exam
description: Run a 10-question certification mock exam with deferred grading, domain-weighted selection, and a per-domain summary at the end.
---

# Run mock exam

Use this skill to simulate exam pacing and calibration. Unlike a quiz, the
mock defers grading until all questions are answered.

## Inputs

- Optional: target time (default 20 minutes for 10 questions).
- Question banks and style references declared in
  `exams/<active-exam>/exam.md`. When no bank exists, author original questions
  from the listed authoritative first-party sources.
- `exams/<active-exam>/assets/progress.md` weak/strong topics.
- Any existing `exams/<active-exam>/material/test-exams/*/results.md`
  failed-question indices (avoid verbatim repeats per
  `.github/instructions/sources-and-citations.instructions.md`).

## Domain weighting

Mock exams calibrate against the official exam outline, **not** today's
sprint-plan focus. Use plan topics only as a tiebreaker when picking
specific questions inside a domain.

Read the domains and percentages from `exams/<active-exam>/exam.md`. Allocate
the 10 questions proportionally, giving each domain at least one question and
assigning rounding remainders to the highest-weighted domains. If the official
outline omits a usable percentage, distribute evenly and state that fallback.

Within each domain, prefer scenario-based questions and include at least 2
items from the user's weak topics for diagnostic value. If an active sprint
plan covers today, prefer plan topics when breaking ties between candidate
questions in the same domain.

## Procedure

1. Announce: number of questions (10), target time, and that grading is
   deferred until the end.
2. Before asking question 1, precompute the complete mock. Select and verify
   every item, apply the locked answer-position deck, and persist two
   session-only manifests:
   - A public manifest containing question number, source/bank ID, domain,
     topic, stem, and neutral answer options, with no answer metadata.
   - A private manifest containing the correct answer, citation, verification
     note, and user-answer field for every item.
   Validate question count and numbering, domain quotas, answer-position
   sequence, four options per item, and absence of answer leakage from the
   public manifest. Do not start the mock until validation passes.
3. Use [select-next-question](../select-next-question/SKILL.md) while building
   the manifests, not between user answers. During the live mock, read the next
   item directly from the cached public manifest so question transitions are
   immediate.
4. Ask one question per turn. Accept the answer. Do **not** grade, hint,
   reveal, restate, or comment on the correct option while the mock is in
   progress.
5. After each genuine user answer, persist it in the session database before
   presenting the next cached question. Do not rewrite the private manifest on
   every turn: repeated filesystem writes add latency and may trigger repeated
   approval prompts. Store at least question number, user answer, timestamp, and
   whether the user requested an expanded explanation. Treat a trailing `*`,
   "flag this," "explain at the end," and equivalent wording as an expanded-
   explanation request. Bulk-merge these rows into the private manifest only
   when the mock ends, is aborted, or reaches a deliberate checkpoint.
6. After question 10, produce the summary (see Output).
7. Bulk-invoke [update-progress](../update-progress/SKILL.md):
   - One mistake-log entry per ❌/⚠️.
   - One session-log line with `mode: mock · score: X/10 · domains: ...`.

## Answer formatting

- Present every question and all answer choices in plain neutral text.
- Never bold, italicize, underline, color, emoji-mark, code-span, or otherwise
  visually distinguish any option. Every option must share identical
  formatting so nothing marks the correct one.
- Never add phrasing that points to, previews, or “helps” identify the correct
  answer.

## Correct-answer position generation

- Before authoring question 1, use an actual random-number tool (for example,
  PowerShell `Get-Random`) to shuffle a balanced A/B/C/D position deck. Never
  manufacture a sequence by language-model intuition.
- For N questions, each letter's count must differ from every other letter's by
  at most one. Thus a 20-question mock uses exactly five of each; a 10-question
  mock uses counts 3/3/2/2, with the two extra letters selected randomly.
- Reject and reshuffle any deck with three identical consecutive positions.
- Persist the entire deck in session state before asking question 1. Consume one
  position per question and never change the deck based on the user's answers.
- Apply the complete deck while precomputing the mock manifests. Never defer
  answer verification or option placement until after the mock has started.
- Treat the public/private manifests as immutable during normal question flow.
  Use the session database as the live answer journal and reconcile it with the
  private manifest in one bulk operation at session end.
- Place the correct answer in the locked position and use plausible distractors
  of similar length/detail for all other positions.
- In the final summary, audit correct-position counts and user-selection counts
  separately. Do not reveal either distribution while the mock is in progress.

## Output (summary)

```
Mock exam result: X/10  (target time: NN min)

Per-domain breakdown:
- Identity/Governance/Monitoring: a/b
- Data storage: a/b
- Business continuity: a/b
- Infrastructure: a/b

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
- For a voided item, use the same full format, set `Correct answer` to
  `Void — multiple defensible answers` (or the precise void reason), and explain
  why the stem could not support a unique score.
- Keep only the primary score and per-domain summary under ~25 lines. The
  required missed, flagged, and voided question reviews may extend beyond that
  limit and must never be omitted for brevity.
- Cite per `.github/instructions/sources-and-citations.instructions.md`.

## Guardrails

- Never grade or react between questions; this preserves calibration value.
- Never re-ask a verbatim question from the mistake log within the past 7
  days.
- If the user aborts mid-mock, still bulk-update progress for answered
  questions and log the partial run in the session log.
