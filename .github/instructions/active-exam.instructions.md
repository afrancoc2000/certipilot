---
applyTo: "**"
description: How every study agent resolves the active exam and its exam-relative paths
---

# Active exam resolution

This repo now serves multiple certification exams (each a folder under
`exams/`, e.g. `exams/az-305/`, `exams/az-104/`). Before reading any
exam-specific file (progress, study plans, question banks, material), the agent
MUST determine the **active exam**. Everything the agent reads or writes for a
study session is scoped to that one exam.

## Resolution order

1. **Explicit user intent wins.** If the user names an exam ("study AZ-104",
   "quiz me on 104"), that is the active exam for the session.
2. **Active study plan by date.** Otherwise, scan for a study plan whose date
   range covers today:
   - each exam's plans in `exams/*/assets/study-plans/`, and
   - the cross-exam master plan in the top-level `assets/`.
   If exactly one exam has a plan covering today, that is the active exam.
3. **Two exams active today.** If plans for two different exams both cover
   today, show the order from the master plan (`assets/`) and ask the user which
   exam to run first.
4. **No active plan.** If nothing covers today, ask which exam the user wants to
   study, and offer to build a sprint plan for it.

State the resolved exam in one short line at the start of the session (for
example: "Active exam: AZ-104 (per today's plan).").

## Exam-relative path convention

Once resolved, `<active-exam>` is the folder name under `exams/` (for example
`az-305` or `az-104`). All exam-scoped resources resolve under it:

| Resource | Path |
| --- | --- |
| Exam config (domains, sources, URLs, banks) | `exams/<active-exam>/exam.md` |
| Progress / agent memory | `exams/<active-exam>/assets/progress.md` |
| Study plans | `exams/<active-exam>/assets/study-plans/` |
| Study material | `exams/<active-exam>/material/` (course, savill, pluralsight, oreilly, cheat-sheets) |
| Question banks & graded runs | `exams/<active-exam>/material/test-exams/` |
| Cross-exam master / mixed plan | `assets/` (top level) |

Wherever a skill or instruction writes `exams/<active-exam>/…`, substitute the
resolved exam folder. **Read `exams/<active-exam>/exam.md` first** to load that
exam's domains, source hierarchy, MS Learn URLs, and which question banks exist
— those differ per exam and are the authority for the session.

## Guardrails

- Never mix material across exams in one session: while AZ-104 is active, do not
  quiz from AZ-305 banks or cite AZ-305 material, and vice versa.
- If the active exam's `exam.md` is missing or a referenced bank does not exist
  yet, say so and fall back to Microsoft Learn (flagged) rather than borrowing
  another exam's content.
