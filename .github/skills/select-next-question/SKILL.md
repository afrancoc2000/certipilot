---
name: select-next-question
description: Choose the next AZ-305 quiz topic and question style based on data/progress.md and test-exam evidence.
---

# Select next question

Use this skill at the start of every quiz turn (single question or case
study) to pick a topic and style consistent with the user's weak areas
without losing breadth.

## Inputs

- `data/progress.md` (weak topics, strong topics, mistake log).
- Optional: failed-question indices under `data/test-exams/*/results.md`.
- Optional: active sprint plan under `data/study-plans/` (most recent file
  whose date range covers today).
- Optional: user-requested domain or topic.

## Procedure

1. Read `data/progress.md` and the most recent `results.md` failed-question
   index.
2. Look for an active sprint plan in `data/study-plans/`. If one exists and
   today's date falls within its range, extract today's planned topics.
3. If the user explicitly requested a topic or domain, honor it (overrides
   the plan).
4. Otherwise apply the selection mix:
   - **Active plan available:** ≥50% from today's planned topics, then fill
     the rest with the standard mix below biased toward weak topics.
   - **No active plan:** apply the default mix from
     `.github/instructions/progress-tracking.instructions.md`:
     - ~60% weak topics
     - ~30% unseen / rotation
     - ~10% retention on strong topics
5. Avoid:
   - Verbatim repeats of any question in the mistake log within the past 7
     days.
   - Re-asking the same weak topic two turns in a row unless the user opted
     into focused practice.
6. Pick the question style:
   - Default: scenario-based single-answer (A/B/C/D).
   - Use multi-select when the topic naturally has multiple correct
     components (for example, identity protection signals).
   - Use matching when comparing services on shared dimensions.
   - Use a 2–4 question case study when the user asks for one or when the
     topic benefits from compound reasoning (BCDR, hybrid identity, hub-spoke
     design).
7. Verify the technical premise against Microsoft Learn before asking, per
   `.github/instructions/sources-and-citations.instructions.md`.

## Output

- Return the picked topic, style, and a one-line rationale (for example:
  `topic: ExpressRoute SKUs · style: scenario A/B/C/D · reason: weak (misses: 2)`).
- Then proceed to ask the question.
