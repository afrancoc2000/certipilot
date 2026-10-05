# AZ-104 — Microsoft Azure Administrator

Exam config for the AZ-104 study agent. Read this first when AZ-104 is the
active exam (see `.github/instructions/active-exam.instructions.md`).

> ⚠️ AZ-104 material is partially populated: the O'Reilly certification guide
> (chapters 1-6) and the ExamTopics question bank (574 questions, no answer key)
> are available. Course notes and other transcripts are not added yet, and the
> ExamTopics answers must be resolved against Microsoft Learn (flagged as "no
> workspace citation" where needed). Do not borrow AZ-305 content.

## Domains (official skills outline)

1. **Manage Azure identities and governance** (D1) — ~20–25%
2. **Implement and manage storage** (D2) — ~15–20%
3. **Deploy and manage Azure compute resources** (D3) — ~20–25%
4. **Implement and manage virtual networking** (D4) — ~15–20%
5. **Monitor and maintain Azure resources** (D5) — ~10–15%

⚠️ Verify the exact domains and weightings against the current Microsoft Learn
AZ-104 exam page before relying on them — Microsoft updates outlines over time.

## Microsoft Learn (source of truth)

- Exam page: https://learn.microsoft.com/en-us/credentials/certifications/exams/az-104/
- Study guide: https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104

## Source hierarchy (lookup order)

1. `exams/az-104/material/course/` — study notes per domain (to be added).
2. `exams/az-104/material/oreilly/certification-guide/chapter-0X.md` — O'Reilly
   AZ-104 certification guide, chapters 1-6 (extracted from PDF via Azure
   Document Intelligence, cleaned).
3. `exams/az-104/material/<source>/...` — other transcripts / guides (to be added).
4. `exams/az-104/material/test-exams/<source>/<exam-id>/...` — practice captures.
5. Microsoft Learn (authoritative — wins on conflict; flag discrepancies).

## Question banks

- **ExamTopics** — `exams/az-104/material/test-exams/examtopics/`:
  - Stems: `questions.md` (574 questions, global Q1-Q574; ExamTopics restarts
    numbering per topic set). Types: 357 multiple-choice, 175 hotspot,
    21 drag-drop, 21 case-study.
  - Answer key: `answer-key.md` — ⚠️ the ExamTopics export contains NO answers
    (no "Correct Answer", no community vote data). Every entry is a placeholder;
    resolve each answer against Microsoft Learn before grading. Do not treat the
    key as authoritative.
  - Raw capture: `AZ-104 Exam.md` (Document Intelligence prebuilt-layout output).
  - HOTSPOT / DRAG DROP items list their answer-area options but not the correct
    selection.
- **Microsoft Learn Practice Assessment** —
  `exams/az-104/material/test-exams/microsoft/learn-practice/`:
  - User-provided assessment captures organized by date.
  - Treat the assessment's displayed result and explanation as the candidate
    answer, then verify service behavior against current Microsoft Learn before
    reusing an item for quizzes.
