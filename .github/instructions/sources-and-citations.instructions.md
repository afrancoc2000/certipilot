---
applyTo: "**"
description: Source hierarchy, citation, language, and MS Learn priority for AZ-305 study agents
---

# Sources, citations, and language

## Source-of-truth rule

Microsoft Learn is the authoritative source for Azure capabilities, limits,
SKUs, default behaviors, and current best practices. Other workspace sources
are study material that may be outdated. When they conflict with Microsoft
Learn, Microsoft Learn wins. Flag the discrepancy explicitly when you see it
(for example: "⚠️ the course notes say X, but Microsoft Learn now documents Y
— follow Y").

## Lookup order

1. `course/` — Spanish-language study notes per exam domain (`README.md`,
   `q&a.md`, `usecase/`).
2. `data/savill/` — John Savill transcripts.
3. `data/pluralsight/<Course>/transcript.txt` — Pluralsight transcripts.
4. `data/oreilly/certification-guide/chapter-0X.md` — O'Reilly guide.
5. `data/test-exams/<source>/<exam-id>/...` — graded practice/exam captures.
6. **Microsoft Learn (source of truth).** Use Microsoft Learn MCP first when
   available; otherwise cite the official URLs:
   - https://learn.microsoft.com/en-us/credentials/certifications/exams/az-305/
   - https://learn.microsoft.com/en-us/training/paths/design-identity-governance-monitor-solutions/
   - https://learn.microsoft.com/en-us/training/paths/design-data-storage-solutions/
   - https://learn.microsoft.com/en-us/training/paths/design-business-continuity-solutions/
   - https://learn.microsoft.com/en-us/training/paths/design-infrastructure-solutions/

## Test-exam evidence rules

- Microsoft certification score reports are primary evidence for prioritization.
- Microsoft Learn practice sets are supporting evidence.
- Verify Pluralsight stated answers against Microsoft Learn before trusting
  them; flag discrepancies.
- Never re-ask a verbatim question from `results.md`; rephrase or use a sibling
  subtopic.

## Citation rules

- Always cite as workspace-relative paths (for example `course/02 compute/README.md`
  or `data/test-exams/pluralsight/exam-2026-05-25/results.md#qN`).
- Never fabricate citations.
- If a topic is not covered in workspace sources, say so explicitly and tag
  the answer with "⚠️ no workspace citation, sourced from Microsoft Learn"
  with the URL.
- Do not cite random blogs or aggregator pages.
- `data/pluralsight/` and `data/oreilly/` are personal-use copies — never
  commit or share their content.

## Language

- Quiz questions: English by default. Switch only on explicit user request.
- Explanations and feedback: follow the user's requested language (default
  Spanish if the user writes in Spanish).
- When introducing an abbreviation, write the full term first then the
  abbreviation in parentheses (for example: Azure Virtual Network (VNet)).

## Output style

- Clean Markdown only; never raw HTML/CSS.
- Concise, exam-focused: emphasize when to choose X over Y, cost/SLA
  trade-offs, and the design decision framework Microsoft expects on AZ-305.

## File-edit guardrails

- Do not modify files under `course/` unless the user explicitly asks.
- Agent-side files (`AGENTS.md`, `.github/`, `data/progress.md`,
  `data/study-plans/`) are fair game when configuring the agent or tracking
  progress.
