---
applyTo: "**"
description: How every study agent resolves the active exam and its exam-relative paths
---

# Active exam resolution

This repo now serves multiple certification exams (each a folder under
`exams/`, e.g. `exams/az-305/`, `exams/az-104/`). Before reading any
exam-specific file (progress, study plans, material), the agent
MUST determine the **active exam**. Everything the agent reads or writes for a
study session is scoped to that one exam.

## Resolution order

1. **Explicit user intent wins.** If the user names an exam ("study AZ-104",
   "quiz me on 104"), that is the active exam for the session.
2. **Active study plan by date.** Otherwise, scan for a study plan whose date
   range covers today:
   - each exam's plans in `exams/*/assets/study-plans/`, and
   - the cross-exam master plan in the top-level `assets/`.
   Retain the matching plan paths with each exam candidate. If exactly one
   exam has a plan covering today, that is the active exam; pass its matching
   plan paths to follow-plan rather than rediscovering a plan by recency.
3. **Multiple exams active today.** If plans for more than one distinct exam
   cover today, list all candidate exams and ask the user which exam to run
   first. Use the master plan's order (`assets/`) when available; append any
   candidates it does not order alphabetically by exam ID. If no master-plan
   order exists, list all candidates alphabetically. Multiple plans for the
   same exam count as one candidate, but retain every matching plan path.
   After the user chooses an exam, pass its matching paths to follow-plan.
   Do not select an exam or read its
   progress/material until the user chooses.
4. **No active plan.** If nothing covers today, ask which exam the user wants to
   study, and offer to build a sprint plan for it.

Plan choice within one exam is owned by
[follow-plan](../skills/follow-plan/SKILL.md) (date match first, then an
explicit active marker, then recency only among date matches). Skills that
*write* a plan (for example close-session) adapt only the plan retained for
this session or one the user selects; other skills reuse the retained path.

State the resolved exam in one short line at the start of the session (for
example: "Active exam: AZ-104 (per today's plan).").

## Exam-relative path convention

Once resolved, `<active-exam>` is the folder name under `exams/` (for example
`az-305` or `az-104`). All exam-scoped resources resolve under it:

| Resource | Path |
| --- | --- |
| Exam config (domains, sources, URLs, banks) | `exams/<active-exam>/exam.md` |
| Progress / agent memory | `exams/<active-exam>/assets/progress.md` |
| Canonical evidence / private checkpoint | `exams/<active-exam>/assets/coverage.json`, `exams/<active-exam>/assets/session.json` |
| Study plans | `exams/<active-exam>/assets/study-plans/` |
| Study material | `exams/<active-exam>/material/` (course, cheat-sheets) |
| Local practice results (never committed) | `exams/<active-exam>/material/test-exams/` |
| Cross-exam master / mixed plan | `assets/` (top level) |

Wherever a skill or instruction writes `exams/<active-exam>/…`, substitute the
resolved exam folder. **Read `exams/<active-exam>/exam.md` first** to load that
exam's domains, source hierarchy, MS Learn URLs, and which local references exist
— those differ per exam and are the authority for the session.

## Guardrails

- For explicit resume, a single unambiguous checkpoint can identify the exam;
  validate it under the [session policy](progress-tracking.instructions.md#pause-and-resume).
  Ask only if state is ambiguous, stale, conflicting, or differs from explicit
  exam intent. Never switch exams silently.

- Never mix material across exams in one session: while AZ-104 is active, do not
  quiz from AZ-305 banks or cite AZ-305 material, and vice versa.
- If the active exam's `exam.md` is missing or a referenced bank does not exist
  yet, say so and fall back to Microsoft Learn (flagged) rather than borrowing
  another exam's content.
