# Study Plan Playbook (AZ-305)

This folder stores dated sprint plans and the method used to build them.

## Core principle

Build the plan from evidence, not intuition. Start with a mixed **50-question
mock exam** that covers all AZ-305 domains, then prioritize from misses.

## Recommended workflow

1. Run a baseline 50-question mock (timed).
2. Classify misses by domain and subtopic.
3. Cross-check weak areas against:
   - `data/progress.md`
   - prior practice results under `data/test-exams/`
   - official score reports (if available locally)
4. Create a dated plan with daily blocks (60 to 120 minutes).
5. Use weighted coverage:
   - ~70% weak topics
   - ~20% adjacent transfer topics
   - ~10% retention checks on stronger areas
6. Schedule at least:
   - 2 full timed mocks before exam day
   - 1 light dress rehearsal day in the final 48 hours
7. After each session, update `data/progress.md` with:
   - mistakes
   - decision rules
   - next-day priority

## Daily block template (60 to 120 min)

- 10 min: retrieval warm-up (no notes)
- 35 to 55 min: focused remediation for primary weak topic
- 15 to 25 min: interleaved mixed questions
- 10 to 20 min: review + decision rules + next-day target

## Prompt to generate an effective plan

Use this prompt with your agent:

```text
Create an AZ-305 sprint study plan from today until EXAM_DATE.
First run a 50-question mock exam covering all domains.
Then build the plan from misses and confidence gaps.

Requirements:
- Daily budget: X to Y minutes
- Coverage weighting: 70% weak, 20% adjacent, 10% retention
- Include 2 timed full mocks and 1 light dress rehearsal day
- No verbatim reuse of prior missed questions
- Add a daily retrieval block and daily decision-rule output
- Update data/progress.md after each graded session

Return:
1) Priority map
2) Dated day-by-day plan
3) Weekly checkpoints
4) Anti-failure guardrails
```

## Naming convention for plans

Use:

- `study-plan-YYYY-MM-DD-to-YYYY-MM-DD.md`

Example:

- `study-plan-2026-05-27-to-2026-06-15.md`
