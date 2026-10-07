# AZ-305 — Designing Microsoft Azure Infrastructure Solutions

Exam config for the AZ-305 study agent. Read this first when AZ-305 is the
active exam (see `.github/instructions/active-exam.instructions.md`).

## Domains (official skills outline)

1. **Design identity, governance, and monitoring solutions** (D1) — 25–30%
2. **Design data storage solutions** (D2) — 20–25%
3. **Design business continuity solutions** (D3) — 15–20%
4. **Design infrastructure solutions** (D4) — 30–35%

Mock exams weight questions against this outline. Coverage guardrails require
the rolling 3 sessions to touch all four domains at least once.

## Blueprint catalog

Use [blueprint.json](./blueprint.json) for the complete, source-mapped objective
and subskill inventory when building or following an approved study plan.
All 49 detailed official bullets and the weights above were reconciled with
the English outline effective April 17, 2026, checked October 4, 2026.
The exam page offers scheduling and lists retirement date "none".
Check `revision`, `verified`, `verification_note`, and source dates before use.
`derived: true` marks teaching decomposition of broad recommendations, not
extra official bullets or a guarantee that a particular service is tested.
Keep existing objective and subskill IDs stable when revising wording; do not
recycle removed IDs. Use guide weights rather than question-bank frequencies.
Verification covers published English scope; localized updates can differ.

## Microsoft Learn (source of truth)

- Exam page: https://learn.microsoft.com/en-us/credentials/certifications/exams/az-305/
- Study guide: https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-305
- https://learn.microsoft.com/en-us/training/paths/design-identity-governance-monitor-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-data-storage-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-business-continuity-solutions/
- https://learn.microsoft.com/en-us/training/paths/design-infrastructure-solutions/

## Source hierarchy (lookup order)

1. `exams/az-305/material/course/` — Spanish-language study notes per domain.
2. `exams/az-305/material/cheat-sheets/` — original decision-tree one-pagers.
3. `exams/az-305/material/test-exams/<exam-id>/results.md` — your own local
   practice results (never committed).
4. Microsoft Learn (authoritative — wins on conflict; flag discrepancies).

## Question style

No third-party question bank is used. Author original scenario questions from
the official skills outline and Microsoft Learn, following the style rules in
`.github/instructions/sources-and-citations.instructions.md`. Personal graded
runs (`results.md`, `score-report.*`, `certification/**`) stay local and are
not a shareable question source.
