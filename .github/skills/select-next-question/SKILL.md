---
name: select-next-question
description: Choose the next certification quiz topic and question style based on exams/<active-exam>/assets/progress.md and test-exam evidence.
---

# Select next question

Use this skill at the start of every quiz turn (single question or case
study) to pick a topic and style consistent with the user's weak areas
without losing breadth.

## Inputs

- `exams/<active-exam>/assets/progress.md` (weak topics, strong topics, mistake log).
- **ExamTopics question bank:** `exams/<active-exam>/material/test-exams/examtopics/questions.md` (count
  in the active exam's `exam.md`) + `exams/<active-exam>/material/test-exams/examtopics/answer-key.md`, prioritized via
  `exams/<active-exam>/material/test-exams/examtopics/coverage-analysis.md` (NEW/PARTIAL clusters,
  duplicate map).
- Optional: failed-question indices under `exams/<active-exam>/material/test-exams/*/results.md`.
- Optional: active sprint plan under `exams/<active-exam>/assets/study-plans/` (most recent file
  whose date range covers today).
- Optional: user-requested domain or topic.

## Procedure

1. Read `exams/<active-exam>/assets/progress.md` and the most recent `results.md` failed-question
   index.
2. Look for an active sprint plan in `exams/<active-exam>/assets/study-plans/`. If one exists and
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
5. Map the chosen topic to a concrete stem in the ExamTopics bank:
   - Prefer questions tagged NEW or PARTIAL in `coverage-analysis.md` for the
     target topic; collapse near-duplicate variants to a single representative.
   - If no ExamTopics stem fits the topic, author an original scenario in the
     same style (see style references in
     `.github/instructions/sources-and-citations.instructions.md`).
6. Avoid:
   - Verbatim repeats of any question in the mistake log within the past 7
     days (rephrase the ExamTopics stem or pick a sibling variant).
   - Re-asking the same weak topic two turns in a row unless the user opted
     into focused practice.
7. Pick the question style:
   - Default: scenario-based single-answer (A/B/C/D).
   - Use multi-select when the topic naturally has multiple correct
     components (for example, identity protection signals).
   - Use matching when comparing services on shared dimensions.
   - Use a 2–4 question case study when the user asks for one or when the
     topic benefits from compound reasoning (BCDR, hybrid identity, hub-spoke
     design).
8. Verify the technical premise — and the ExamTopics community answer — against
   Microsoft Learn before asking, per
   `.github/instructions/sources-and-citations.instructions.md`. ExamTopics keys
   are disputed often; Microsoft Learn wins on conflict.
9. When you author the options, use the next position from the session's locked
   answer-position deck:
   - If no deck exists, mechanically generate one with an actual random-number
     tool (for example, PowerShell `Get-Random`), not language-model intuition.
     For an open-ended quiz, use a shuffled 12-position deck with three each of
     A/B/C/D; reject any shuffle containing three identical positions in a row.
   - Persist the deck before writing the question, consume one position per item,
     and never change it in response to the user's selections.
   - Place the correct option in that position and fill the remaining slots with
     distractors. Keep all options in plain text and of similar length/detail so
     neither formatting, position, nor verbosity signals the answer.
   - At session end, report correct-position counts separately from the user's
     answer-selection counts.

## Output

- Return the picked topic, style, and a one-line rationale (for example:
  `topic: ExpressRoute SKUs · style: scenario A/B/C/D · reason: weak (misses: 2)`).
- Then proceed to ask the question.
