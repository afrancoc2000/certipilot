# AZ-305 — Designing Microsoft Azure Infrastructure Solutions

Exam config for the AZ-305 study agent. Read this first when AZ-305 is the
active exam (see `.github/instructions/active-exam.instructions.md`).

## Domains (official skills outline)

1. **Design identity, governance, and monitoring solutions** (D1)
2. **Design data storage solutions** (D2)
3. **Design business continuity solutions** (D3)
4. **Design infrastructure solutions** (D4)

Mock exams weight questions against this outline. Coverage guardrails require
the rolling 3 sessions to touch all four domains at least once.

## Microsoft Learn (source of truth)

- Exam page: https://learn.microsoft.com/en-us/credentials/certifications/exams/az-305/
- https://learn.microsoft.com/en-us/training/paths/design-identity-governance-monitor-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-data-storage-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-business-continuity-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-infrastructure-solutions/

## Source hierarchy (lookup order)

1. `exams/az-305/material/course/` — Spanish-language study notes per domain.
2. `exams/az-305/material/savill/` — John Savill transcripts.
3. `exams/az-305/material/pluralsight/<Course>/transcript.txt` — Pluralsight transcripts.
4. `exams/az-305/material/oreilly/certification-guide/chapter-0X.md` — O'Reilly guide.
5. `exams/az-305/material/test-exams/<source>/<exam-id>/...` — graded practice/exam captures.
6. Microsoft Learn (authoritative — wins on conflict; flag discrepancies).

## Question banks

- **Primary (source of stems):** ExamTopics —
  `exams/az-305/material/test-exams/examtopics/questions.md` (286 stems) +
  `answer-key.md`, prioritized via `coverage-analysis.md`. Community-sourced
  keys: verify against Microsoft Learn before grading.
- **Secondary drill banks (definitional / graded-run derived):**
  - MeasureUp — `exams/az-305/material/test-exams/measureup/exam-2026-02-26/questions.md`
    (152 AKB questions) + `answer-key.md`.
  - Pluralsight — `exams/az-305/material/test-exams/pluralsight/exam-2026-05-25/questions.md`
    (60 questions) + `answer-key.md`.
- **Style references:** the graded runs under `measureup/` and `pluralsight/`
  and the O'Reilly certification guide.

Personal graded runs (`results.md`, `score-report.*`, `certification/**`) stay
local and are not a shareable question source.
