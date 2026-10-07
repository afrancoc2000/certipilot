# AZ-104 — Microsoft Azure Administrator

Exam config for the AZ-104 study agent. Read this first when AZ-104 is the
active exam (see `.github/instructions/active-exam.instructions.md`).

> ⚠️ AZ-104 course notes are not added yet. Author original questions from
> the official skills outline and Microsoft Learn (flag answers as "no
> workspace citation" where needed). Do not borrow AZ-305 content.

## Domains (official skills outline)

1. **Manage Azure identities and governance** (D1) — ~20–25%
2. **Implement and manage storage** (D2) — ~15–20%
3. **Deploy and manage Azure compute resources** (D3) — ~20–25%
4. **Implement and manage virtual networking** (D4) — ~15–20%
5. **Monitor and maintain Azure resources** (D5) — ~10–15%

These domain weights match the detailed Microsoft Learn outline effective
April 17, 2026, checked on October 4, 2026. The certification page currently
offers exam scheduling; re-check it before booking.

## Blueprint catalog

Use [blueprint.json](./blueprint.json) for the complete, source-mapped objective
and subskill inventory when building or following an approved study plan.
It covers all 82 detailed official bullets, not question-bank content.
Check `revision`, `verified`, `verification_note`, and source dates before use.
`derived: true` identifies teaching decomposition beyond explicitly named
components, not additional official exam bullets. Keep existing objective and
subskill IDs stable when revising wording; do not recycle removed IDs.
Weights come from the detailed guide, not local question frequencies.
Verification covers published English scope, not every possible exam topic or
the timing of localized exam updates.

## Microsoft Learn (source of truth)

- Exam page: https://learn.microsoft.com/en-us/credentials/certifications/exams/az-104/
- Study guide: https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104

## Source hierarchy (lookup order)

1. `exams/az-104/material/course/` — study notes per domain (to be added).
2. `exams/az-104/material/test-exams/<exam-id>/results.md` — your own local
   practice results (never committed).
3. Microsoft Learn (authoritative — wins on conflict; flag discrepancies).

## Question style

No third-party question bank is used. Author original scenario questions from
the official skills outline and Microsoft Learn, following the style rules in
`.github/instructions/sources-and-citations.instructions.md`. The free
[Microsoft Learn practice assessment](https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator/practice/assessment?assessment-type=practice&assessmentId=21)
is a supporting self-check; do not copy its items into the repo.
