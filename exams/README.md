# Adding a Certification

1. Create `exams/<exam-id>/exam.md` with the official title, skills outline,
   domain weights, authoritative sources, local source order, and available
   question banks.
2. Create `material/README.md` and add only legally shareable notes, links,
   transcripts, and question banks.
3. Create `assets/progress.md` using the starter format below. It remains local.
4. Create `assets/study-plans/README.md`; dated plans in that folder remain local.
5. Name the exam explicitly in chat to activate it.

Minimum progress headings:

```markdown
# <Exam> Progress

## Status
## Weak topics
## Strong topics
## Mistake log
## Session log
```

Do not reuse another exam's sources. When no local bank exists, generate
original questions from the authoritative sources declared in `exam.md`.
