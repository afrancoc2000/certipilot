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

1. `exams/<active-exam>/material/course/` — the learner's own study notes per exam domain, if they
   have added any (optional; not shipped with the repo).
2. `exams/<active-exam>/material/cheat-sheets/` — original one-page summaries.
3. `exams/<active-exam>/material/test-exams/<exam-id>/results.md` — the learner's own
   local practice results (never committed).

This local lookup order does not delay or replace first-party verification.

## Original questions and style references

When the user studies in quiz, drill, case-study, or mock-exam mode, read the
skills outline, authoritative sources, and question-style guidance in the
active exam's `exam.md` first.

- In every mode, write original questions from the exam's skills outline and
  its declared authoritative first-party sources, including Microsoft Learn
  and GitHub Docs as appropriate. Do not reproduce third-party question banks,
  exam dumps, or paid practice-test content.
- Format: a concrete scenario with explicit constraints, four plausible
  options (A-D) for single-answer items (multi-select follows its own format),
  and a **per-option rationale** (why the right one wins and why each
  distractor fails) on grading.
- Do not reuse a stem the user already saw verbatim within the past 7 days —
  rephrase or pick a sibling variant.

## Test-exam evidence rules

- Official certification score reports are primary evidence for prioritization.
- Microsoft Learn practice sets are supporting evidence.
- Verify any practice-set stated answer under the same preparation contract
  and flag discrepancies.
- Never re-ask a verbatim question from `results.md`; rephrase or use a sibling
  subtopic.

## Citation rules

- Always cite as workspace-relative paths (for example `exams/<active-exam>/material/cheat-sheets/<file>`
  or `exams/<active-exam>/material/test-exams/<exam-id>/results.md#qN`).
- Never fabricate citations.
- If a topic is not covered in workspace sources, say so explicitly and tag
  the answer with "⚠️ no workspace citation, sourced from Microsoft Learn"
  with the URL.
- Do not cite random blogs or aggregator pages.

## Sharing / commit policy

The repo is shared with a small, trusted team so they can study from the same
material. `.gitignore` protects personal state, designated third-party
directories, and common ebook/transcript formats; it cannot determine
authorship or licensing from a filename:

- **Commit and share — original study material** under `exams/<exam>/material/`:
  the author's own notes and cheat sheets.
- **Never commit — third-party content**: books, course or video transcripts,
  slide captures, practice-test or exam-dump questions and answer keys. Link
  to the official source instead.
  Any legally obtained local reference files belong under
  `exams/<exam>/material/third-party/` (ignored at every depth), not alongside
  original notes. The `books/`, `transcripts/`, `slide-captures/`,
  `question-banks/`, and `exam-dumps/` directories under material are also
  ignored, as are the legacy `savill/`, `pluralsight/`, and `oreilly/`
  reference directories. Original notes and cheat-sheet PDFs remain shareable; review their
  provenance before staging. Ignore rules do not protect already tracked files
  or prevent a forced add.
- **Never commit — personal-use files** (keep local): everything under
  `exams/<exam>/assets/` (`progress.md`, `study-plans/`), the cross-exam
  `assets/` master plan (except the shared `README.md` templates that
  `.gitignore` re-includes), and everything under `material/test-exams/`
  (graded `results.md`, any `score-report.*`, and the real `certification/**`
  score reports).
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
