---
name: update-progress
description: Apply a safe, surgical update to exams/<active-exam>/assets/progress.md after grading an answer or finishing a session.
---

# Update progress

Use this skill to mutate `exams/<active-exam>/assets/progress.md` consistently across quiz, tutor,
planner, and mock-exam flows.

## Inputs

- Topic (short, canonical name; reuse existing labels when present).
- Status: ✅ correct / ⚠️ partial / ❌ incorrect.
- Optional: short note (what was missed, distractor pattern, source).
- Mode (quiz / tutor / mock / planner).

## Procedure

1. Read `exams/<active-exam>/assets/progress.md`. If it does not exist, create it with sections:
   `## Weak topics`, `## Strong topics`, `## Mistake log`, `## Session log`.
2. Apply the rules from
   `.github/instructions/progress-tracking.instructions.md`:
   - ❌ → mistake log entry + weak topic bump.
   - ⚠️ → mistake log entry + weak topic add/bump (`misses: 1` minimum).
   - ✅ → decrement weak `misses`; promote to strong after 2 consecutive
     correct; bump `correct streak` and `last seen` for already strong.
3. Keep entries one or two lines. Do not rewrite unrelated sections.
4. On session close (user says goodbye, switches off mock mode, or finishes
   a mock exam), append one line to the session log and trim to last 10.
5. If a topic now has 3+ consecutive misses, add a short flag at the end of
   its weak-topic entry: `→ recommend tutor deep dive`.

## Output

- Write the file in place.
- Reply with a one-line confirmation listing the topic and new state
  (for example: `progress updated: AKS node pools — weak (misses: 3) → tutor
  deep dive recommended`).

## Guardrails

- Never delete history outside the session-log trim rule.
- Never reorder unrelated sections.
- Preserve existing labels; do not rename topics arbitrarily.
