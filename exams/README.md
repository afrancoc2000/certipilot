# Adding a Certification

1. Create `exams/<exam-id>/exam.md` with the official title, skills outline,
   domain weights, authoritative sources, local source order, and original
   question-style guidance.
2. Create `exams/<exam-id>/blueprint.json` and link it from `exam.md`. Reconcile
   every published objective against the current official study guide, record
   source URLs and revision/check dates, and decompose broad objectives into
   assessable subskills with stable IDs. Mark the catalog verified only after
   that reconciliation; unknown scope is not complete. Follow the
   [catalog schema](../.github/skills/coverage-audit/references/evidence.md#catalog).
3. Create `material/README.md` for original notes, cheat sheets, and links to
   official resources. Do not commit third-party books, course or video
   transcripts, slide captures, practice-test or exam-dump questions, or answer
   keys. Mark `material/test-exams/` as local-only for personal practice results
   and score reports; never commit its contents. Follow the
   [source contract](../.github/instructions/sources-and-citations.instructions.md#sharing--commit-policy).
4. Create `assets/progress.md` using the starter format below. It remains local.
5. Create `assets/study-plans/README.md`; dated plans in that folder remain local.
6. From the repository root, validate the catalog and initialize private
   evidence with the commands below. `init` creates `assets/coverage.json`
   with unknown learning evidence and refuses to overwrite an existing ledger.
   Do not copy another exam's mastery records or assume a catalog proves learning.
7. Activate the exam by naming it explicitly in chat, or let a dated study plan
   covering today select it when no exam is named. Explicit intent takes
   precedence; if multiple exams have active plans, choose which to study.
   Follow the [active-exam resolver](../.github/instructions/active-exam.instructions.md)
   for the complete selection and resume rules.

Replace `<exam-id>` with the new exam's folder name:

```powershell
python .github\skills\coverage-audit\scripts\coverage.py audit --exam <exam-id>
python .github\skills\coverage-audit\scripts\coverage.py init --exam <exam-id>
python .github\skills\coverage-audit\scripts\coverage.py audit --exam <exam-id>
python -B -m unittest discover -s .github\skills\coverage-audit\tests -p test_repository.py
```

Resolve any nonzero exit status before using the exam. Audit success validates
catalog structure and evidence consistency, not the semantic accuracy of the
official-source mapping; that reconciliation is required separately.

Minimum progress headings:

```markdown
# <Exam> Progress

## Status
## Coverage summary
## Weak topics
## Strong topics
## Mistake log
## Session log
```

Do not reuse another exam's sources. Always generate original questions from
the authoritative first-party sources declared in `exam.md`, regardless of
whether local practice results exist.
