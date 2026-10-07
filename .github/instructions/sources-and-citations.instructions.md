---
applyTo: "**"
description: Source hierarchy, citations, and language for certification study agents
---

# Sources, citations, and language

## Source-of-truth rule

Use the authoritative first-party sources listed in the active exam's
`exam.md`. Microsoft Learn is authoritative for the official skills outline
and Azure behavior; GitHub Docs is authoritative for GitHub product behavior.
Workspace sources may be outdated. When they conflict with current first-party
documentation, the first-party source wins and the discrepancy must be flagged.

## Preparation and verification

Prepare and verify an answer before presenting the question. Use Microsoft
Learn MCP when available for Microsoft claims, then the official URLs in the
active exam's `exam.md`; GitHub Docs governs GitHub behavior. Local notes and
community keys provide candidates, explanations, and style, not authority.

Keep the claim, decisive constraints, first-party URL, verification date, and
supporting rationale in the private prepared-session state. Reuse that verified
snapshot during the same prepared session when the claim and constraints are
unchanged, including grading; a fresh fetch for each answer is unnecessary.
Reverify new claims, changed constraints, disputes, and stale source metadata.
No unchecked cross-session cache. Missing or ambiguous verification blocks a
definitive grade, not permission to trust a community key. Apply the canonical
[invalid-item correction](progress-tracking.instructions.md#corrections-without-learner-penalty)
without learner penalty when a defect is established.

## Local explanation and style lookup

1. `exams/<active-exam>/material/course/` — Spanish-language study notes per exam domain (`README.md`,
   `q&a.md`, `usecase/`).
2. `exams/<active-exam>/material/savill/` — John Savill transcripts.
3. `exams/<active-exam>/material/pluralsight/<Course>/transcript.txt` — Pluralsight transcripts.
4. `exams/<active-exam>/material/oreilly/certification-guide/chapter-0X.md` — O'Reilly guide.
5. `exams/<active-exam>/material/test-exams/<source>/<exam-id>/...` — graded practice/exam captures.

This local lookup order does not delay or replace first-party verification.

## Question bank and style references

When the user studies in quiz, drill, or mock-exam mode, read the question-bank
and style-reference inventory in the active exam's `exam.md` first.

- **When ExamTopics is declared for the active exam:**
  `exams/<active-exam>/material/test-exams/examtopics/questions.md` (count in the active exam's `exam.md`) with the
  matching key in `exams/<active-exam>/material/test-exams/examtopics/answer-key.md`. Use
  `exams/<active-exam>/material/test-exams/examtopics/coverage-analysis.md` to prioritize NEW/PARTIAL
  clusters and to skip near-duplicate variants (the dump has many repeats).
- **When these style references exist:** the graded runs under
  `exams/<active-exam>/material/test-exams/measureup/`, `exams/<active-exam>/material/test-exams/pluralsight/`, and the O'Reilly
  certification guide `exams/<active-exam>/material/oreilly/certification-guide/chapter-0X.md`. Mirror
  their format: a concrete scenario with explicit constraints, four plausible
  options (A-D) for single-answer items (multi-select follows its own format), and a **per-option rationale** (why the right one wins and why each
  distractor fails) on grading.
- **ExamTopics answers are community-sourced and frequently disputed.** Never
  treat `answer-key.md` as authoritative on its own. Apply the preparation and
  verification contract above; if they conflict, follow Microsoft Learn and
  flag the discrepancy (for example: "⚠️ ExamTopics marks B, but MS Learn
  supports C — follow C").
- Present ExamTopics stems faithfully (light wording normalization is fine), but
  do not reuse a stem the user already saw verbatim within the past 7 days —
  rephrase or pick a sibling variant. Hotspot/drag-drop items whose answer area
  is image-only may be converted to a text table or skipped.

## Test-exam evidence rules

- Official certification score reports are primary evidence for prioritization.
- Microsoft Learn practice sets are supporting evidence.
- Verify Pluralsight stated answers under the same preparation contract and
  flag discrepancies; source brands do not change verification scope.
- Never re-ask a verbatim question from `results.md`; rephrase or use a sibling
  subtopic.

## Citation rules

- Always cite as workspace-relative paths (for example `exams/<active-exam>/material/course/02 compute/README.md`
  or `exams/<active-exam>/material/test-exams/pluralsight/exam-2026-05-25/results.md#qN`).
- Never fabricate citations.
- If a topic is not covered in workspace sources, say so explicitly and tag
  the answer with "⚠️ no workspace citation, sourced from Microsoft Learn"
  with the URL.
- Do not cite random blogs or aggregator pages.

## Sharing / commit policy

The repo is shared with a small, trusted team so they can study from the same
material. The split is enforced in `.gitignore`:

- **Commit and share — study material** under `exams/<exam>/material/`: course
  notes, Savill/Pluralsight transcripts, O'Reilly excerpts (text and PDFs), and
  the ExamTopics/practice question banks (questions, answer keys, coverage).
- **Never commit — personal-use files** (keep local): everything under
  `exams/<exam>/assets/` (`progress.md`, `study-plans/`), the cross-exam
  `assets/` master plan (except the shared `README.md` templates that
  `.gitignore` re-includes), and under `material/test-exams/` the graded
  `results.md`, any `score-report.*`, and the real `certification/**` score
  reports.
- If the user asks to commit something that matches a personal-use pattern,
  pause and confirm before overriding `.gitignore`.

## Language

- Quiz questions: English by default. Switch only on explicit user request.
- Explanations and feedback: follow the user's requested language (default
  Spanish if the user writes in Spanish).
- When introducing an abbreviation, write the full term first then the
  abbreviation in parentheses (for example: Azure Virtual Network (VNet)).

## Output style

- Clean Markdown only; never raw HTML/CSS.
- Concise, exam-focused: emphasize distinctions, trade-offs, and the decision
  framework expected by the active exam.

## File-edit guardrails

- Do not modify study material under `exams/<exam>/material/` unless the user
  explicitly asks.
- Agent-side files (`AGENTS.md`, `.github/`, `exams/<exam>/assets/progress.md`,
  `exams/<exam>/assets/study-plans/`) are fair game when configuring the agent
  or tracking progress.
- Never commit personal-use files — follow the sharing/commit policy above and
  the patterns in `.gitignore`.
