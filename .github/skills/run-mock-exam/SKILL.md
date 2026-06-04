---
name: run-mock-exam
description: Run a 10-question AZ-305 mock exam with deferred grading, domain-weighted selection, and a per-domain summary at the end.
---

# Run mock exam

Use this skill to simulate exam pacing and calibration. Unlike a quiz, the
mock defers grading until all questions are answered.

## Inputs

- Optional: target time (default 20 minutes for 10 questions).
- `data/progress.md` weak/strong topics.
- `data/test-exams/*/results.md` failed-question indices (avoid verbatim
  repeats per `.github/instructions/sources-and-citations.instructions.md`).

## Domain weighting

Mock exams calibrate against the official exam outline, **not** today's
sprint-plan focus. Use plan topics only as a tiebreaker when picking
specific questions inside a domain.

Mirror the official AZ-305 skills outline rather than the quiz weak-topic
mix. Target distribution across the 10 questions:

- Design identity, governance, and monitoring solutions — 2–3
- Design data storage solutions — 2–3
- Design business continuity solutions — 1–2
- Design infrastructure solutions — 3–4

Within each domain, prefer scenario-based questions and include at least 2
items from the user's weak topics for diagnostic value. If an active sprint
plan covers today, prefer plan topics when breaking ties between candidate
questions in the same domain.

## Procedure

1. Announce: number of questions (10), target time, and that grading is
   deferred until the end.
2. For each of the 10 questions, call
   [select-next-question](../select-next-question/SKILL.md) with the
   domain target above.
3. Ask one question per turn. Accept the answer. Do **not** grade or hint.
4. Track question, user answer, correct answer, and domain in memory.
5. After question 10, produce the summary (see Output).
6. Bulk-invoke [update-progress](../update-progress/SKILL.md):
   - One mistake-log entry per ❌/⚠️.
   - One session-log line with `mode: mock · score: X/10 · domains: ...`.

## Output (summary)

```
Mock exam result: X/10  (target time: NN min)

Per-domain breakdown:
- Identity/Governance/Monitoring: a/b
- Data storage: a/b
- Business continuity: a/b
- Infrastructure: a/b

Missed questions:
1. <one-line topic + why> → cite
2. ...

Recommended next steps:
- Tutor deep dive on: <topic with 2+ misses>
- Re-quiz: <other weak topics>
```

Keep the summary under ~25 lines. Cite per
`.github/instructions/sources-and-citations.instructions.md`.

## Guardrails

- Never grade or react between questions; this preserves calibration value.
- Never re-ask a verbatim question from the mistake log within the past 7
  days.
- If the user aborts mid-mock, still bulk-update progress for answered
  questions and log the partial run in the session log.
