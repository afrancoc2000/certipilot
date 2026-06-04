---
name: grade-answer
description: Grade an AZ-305 quiz answer and produce a concise, cited rationale. Invoke after the user responds to a quiz question.
---

# Grade answer

Use this skill to grade a single AZ-305 answer with consistent format and
citations.

## Inputs

- The original question and options.
- The user's answer.
- The reference answer (from a workspace source or Microsoft Learn).

## Procedure

1. Classify the answer:
   - ✅ correct — fully matches the reference answer.
   - ⚠️ partial — partially correct; one or more required selections missing
     or one minor error.
   - ❌ incorrect — wrong primary choice.
2. Verify the reference answer against Microsoft Learn when the source is
   Pluralsight, O'Reilly, or older course notes. Flag any discrepancy.
3. Produce the rationale in this exact shape:

   ```
   Result: <✅|⚠️|❌>

   Why: <1-3 sentences explaining the correct choice using AZ-305 decision
   framing (when to choose X over Y, cost/SLA tradeoff, common distractor).>

   Cite: <workspace-relative path or MS Learn URL>
   ```

4. Keep total grading output under ~8 lines unless the question is a case
   study, in which case under ~14 lines.
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
