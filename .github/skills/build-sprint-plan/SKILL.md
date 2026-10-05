---
name: build-sprint-plan
description: Produce a dated certification sprint plan from exam date, daily time, and current weak topics.
---

# Build sprint plan

Use this skill when the user provides an exam date and limited daily study
time and wants a calendar-based plan.

## Inputs

- Exam date (required).
- Daily available minutes (default: 90–150).
- `exams/<active-exam>/assets/progress.md` weak/strong topics.
- `exams/<active-exam>/material/test-exams/*/results.md` failed-question indices.

## Procedure

1. Validate exam date:
   - If in the past, ask the user to confirm or correct.
   - If fewer than 3 days remain, switch to triage-only plan covering the
     2–3 highest-weighted weak topics.
2. Offer a baseline mock exam to calibrate the plan:
   - Ask: "Want to start with a 10-question mock exam to measure your
     current level? (recommended if `exams/<active-exam>/assets/progress.md` is empty or stale)."
   - If yes, invoke `run-mock-exam`, then use its per-domain summary as the
     primary signal for ranking weak topics in step 3.
   - If no, or if `progress.md` already has recent evidence (last 7 days),
     skip the baseline and proceed.
   - Reserve Day 1 of the plan for the baseline mock + review when used.
3. Read progress + test-exam evidence (including the baseline result if
   available) to rank weak topics.
4. Build the daily block (default 90–150 min). Each day must include:
   1. Retrieval warm-up (5–10 min)
   2. Focused remediation on 1–2 weak topics (30–50 min)
   3. Concept-map deep dive (15–25 min)
   4. Mixed interleaved quiz (20–30 min)
   5. Short review + next-day priority (5 min)
5. Topic weighting per day:
   - 70–80% current weak topics
   - 20–30% retention on strong topics
6. Mandatory milestones:
   - At least 2 full timed mock exams before exam day.
   - Light dress-rehearsal day in the final 48 hours (no heavy new content).
7. If a weak topic was missed twice in the same week, schedule a tutor deep
   dive before returning to standard quiz flow.

## Output

- A dated plan from tomorrow through exam day, with explicit timeboxes,
  measurable completion criteria, and risk flags / fallbacks for missed days.
- Save the plan under `exams/<active-exam>/assets/study-plans/<exam-date>-sprint.md` when the user
  asks to persist it.
- Append a one-line entry to the session log via `update-progress`.

## Style

- Markdown table or per-day headings — pick whichever the user prefers; ask
  once if unspecified.
- Keep each day skimmable in under 12 lines.
