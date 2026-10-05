---
name: grade-answer
description: Grade a certification quiz answer and produce a concise, cited rationale. Invoke after the user responds to a quiz question.
---

# Grade answer

Use this skill to grade a single answer for the active exam with consistent format and
citations.

## Inputs

- The original question and options.
- The user's answer.
- The reference answer. For ExamTopics-sourced questions this is
  `exams/<active-exam>/material/test-exams/examtopics/answer-key.md` — but it is community-sourced and
  often disputed, so treat it as a candidate, not ground truth. Verify against
  Microsoft Learn before grading.

## Procedure

1. Classify the answer:
   - ✅ correct — fully matches the reference answer.
   - ⚠️ partial — partially correct; one or more required selections missing
     or one minor error.
   - ❌ incorrect — wrong primary choice.
2. Verify the reference answer against Microsoft Learn when the source is
   ExamTopics, Pluralsight, O'Reilly, or older course notes. Flag any
   discrepancy explicitly (for example: "⚠️ ExamTopics marks B, but MS Learn
   supports C — grading against C").
3. Produce the rationale in this exact shape:

   ```
   Result: <✅|⚠️|❌>

   Why: <1-3 sentences explaining the correct choice using the active exam's
   framing (when to choose X over Y, cost/SLA tradeoff, common distractor).>

   Per-option: <one short line per option — why the right one wins and why each
   distractor fails. Match the style of the graded references under
   exams/<active-exam>/material/test-exams/measureup/, exams/<active-exam>/material/test-exams/pluralsight/, and
   exams/<active-exam>/material/oreilly/certification-guide/.>

   Cite: <workspace-relative path or MS Learn URL>
   ```

4. Keep total grading output under ~10 lines for single-answer items and
   under ~16 lines for case studies or multi-select.
5. After grading, invoke `update-progress` with topic, status, and a short
   note on what was missed.
6. Offer the next step: same topic / different topic / switch mode.

## Citation rules

Follow `.github/instructions/sources-and-citations.instructions.md`. Never
fabricate paths. Always prefer Microsoft Learn for service-behavior facts.

## Common pitfalls to flag in rationales

- Confusing service tiers (for example, Standard vs Premium SKUs) when SLA
  or feature differences drive the answer.
- Picking a regional service when the constraint requires global scope.
- Choosing managed identity vs service principal without the correct
  ownership boundary.
- Ignoring cost when the question explicitly mentions budget.
