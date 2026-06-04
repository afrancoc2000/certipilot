---
name: close-session
description: Close a Follow-plan session by adapting tomorrow's block in the active study plan based on today's results, then logging the session.
---

# Close session

Use this skill at the end of a Follow-plan session to roll today's
performance into tomorrow's block in `data/study-plans/`. It is the
counterpart to `build-sprint-plan`: that skill builds the whole plan;
this one patches one day.

## Inputs

- Today's date.
- Active plan file under `data/study-plans/` (most recent
  `study-plan-*-sprint.md` or `*-to-*.md`).
- Today's results — newly added ❌/⚠️ entries in `data/progress.md` plus
  the list of activities completed vs. skipped.

## Procedure

1. Locate the active plan. If none exists, stop and tell the user there
   is nothing to adapt.
2. Find tomorrow's block by date. If tomorrow falls outside the plan
   range (exam day reached or passed), stop and report it.
3. Compute session signals:
   - **New weak topics**: topics that got ❌ or ⚠️ today and were not
     already in the weak-topics section of `data/progress.md`.
   - **Twice-missed-this-week**: topics with 2+ misses in the last 7
     days of the mistake log → flag for tutor deep dive (per
     `build-sprint-plan` step 7).
   - **Carryover**: activities listed for today that the user did not
     complete.
4. Patch tomorrow's block in place:
   - Replace the 70–80% weak-topic slots with today's freshest weak
     topics, keeping the existing time boxes and structure.
   - Append carryover items to the appropriate slot, marked
     `(carryover from <today>)`.
   - If a tutor deep dive flag fired, replace the concept-map slot with
     a tutor deep dive on the flagged topic.
   - Do not touch milestones (mock exams, dress rehearsal) or any day
     other than tomorrow.
5. Show a unified diff of the change and ask the user to confirm before
   writing.
6. On confirmation, write the patched plan in place.
7. Call `update-progress` with mode `planner` to append a one-line
   session-log entry summarizing what rolled over.

## Output

- Updated plan file (one day patched).
- One-line confirmation: `tomorrow's block adapted: <topics swapped in>;
  carryover: <items>; tutor deep dive: <topic or none>`.

## Guardrails

- Never edit days before tomorrow.
- Never touch milestones or the dress-rehearsal day.
- Preserve the plan's existing format (table or per-day headings).
- Never invent weak topics not present in `data/progress.md`.
- If today's signals are empty (clean session), still log a session-log
  line but make no plan changes.
