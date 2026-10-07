---
name: grade-answer
description: Grade a certification quiz answer and produce a concise, cited rationale. Invoke after the user responds to a quiz question.
---

# Grade answer

Use this skill to grade a single answer for the active exam with consistent format and
citations.
Load the [canonical contract](../../instructions/progress-tracking.instructions.md),
its shared evidence/session specifications, and the
[source contract](../../instructions/sources-and-citations.instructions.md).
Follow the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns):
retain the pending item's verified context and use direct tools for journaling
and persistence, without a second agent solely to rerun known commands.

## Inputs

- The original choice question/options, or free-response stem and its privately
  prepared grading criteria.
- The user's answer.
- Active exam/catalog revision, required subskill IDs, session/attempt IDs,
  actual response reference and timestamp, assistance, and context. Follow the
  [canonical evidence contract](../../instructions/progress-tracking.instructions.md).
- The reference answer. For ExamTopics-sourced questions this is
  `exams/<active-exam>/material/test-exams/examtopics/answer-key.md` — but it is community-sourced and
  often disputed, so treat it as a candidate, not ground truth. Use the prepared
  first-party verification snapshot under the source contract.

## Procedure

1. Before scoring, confirm the answer is a genuine user turn and check its
   timestamp against the latest genuine message and real session sequence.
   Never grade transcript artifacts or fill an unanswered item. If provenance
   is ambiguous, ask for confirmation and stop. Journal the genuine response in
   the session checkpoint before grading or writing its ledger attempt (the
   helper rejects a ledger attempt for an unjournaled answer). During a mock,
   defer this grading workflow until the mock ends/aborts.
2. Reuse unchanged prepared verification; reverify changed claims/constraints,
   disputes, or stale metadata under the source contract. If unresolved, do not
   issue a definitive grade. A resume action of `replace_unverified_item`
   requires the legacy-source recovery in the shared session specification;
   do not reuse that snapshot or score the item before correction.
   A defective/ambiguous item uses canonical
   `invalid_item` correction under the canonical provenance contract: no learner error,
   no mastery, and no demand that the learner accept a false key. Replace only
   with continued permission, retaining its item index and any locked answer position.
3. Classify the answer:
   - ✅ correct — fully matches the reference answer.
   - ⚠️ partial — partially correct; one or more required selections missing
     or one minor error.
   - ❌ incorrect — wrong primary choice.
   For `free_response`, evaluate the genuine explanation against the verified
   private criteria, not wording equality or an invented option key. Correct
   means the required reasoning is supported; partial means some criteria are
   met with missing or flawed reasoning; incorrect means the central mechanism
   or decision is wrong. Explain the causal gap and cite the source. Use
   criterion-based feedback instead of a per-option rationale when no choices
   exist; do not manufacture distractors or publish the private rubric.
4. Produce learner-facing feedback under
   [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
   Use the following content guide, not a mandatory administrative form:

   ```
   Result: <✅|⚠️|❌>

   Why: <1-3 sentences explaining the correct choice using the active exam's
   framing (when to choose X over Y, cost/SLA tradeoff, common distractor).>

   Per-option: <one short line per option — why the right one wins and why each
   distractor fails. Match the style of the graded references under
   exams/<active-exam>/material/test-exams/measureup/, exams/<active-exam>/material/test-exams/pluralsight/, and
   exams/<active-exam>/material/oreilly/certification-guide/.>

   Cite: <workspace-relative path or MS Learn URL>

   When useful: <a natural teaching bridge or specific next step, not a
   diagnostic label or evidence classification>
   ```

   Record assistance, context, reasoning evidence, diagnosis, and teaching
   action in the private evidence/handoff, not appended fields in the reply.
   A correct letter-only answer stays correct; do not routinely qualify it
   with "mastery not established." Use a reasoning probe only when it helps
   learning, never merely to satisfy a metric.

5. Separate answer score from evidence of understanding. Correct but unexplained
   or uncertain selections remain correct without automatic mastery. Attribute
   only demonstrated subskills; do not clear a broad objective from one narrow
   question. Preserve earlier qualified reasoning on a correct letter-only or
   unknown-evidence repeat; independent incorrect/partial evidence reopens
   evidenced scope. Apply canonical later-local-day/source-link eligibility for
   delayed transfer. Use `uncertain` rather than inventing a diagnosis.
   If necessary, ask one targeted reasoning probe within the same activity
   (for example, which constraint rules out the closest alternative). Do not
   require a long explanation for every correct answer or during a deferred mock.
6. Keep single-item feedback concise (about 12 lines; 18 for compound items).
   Mock review's complete missed/flagged/voided-item requirements take precedence.
7. Invoke `update-progress` with the canonical attempt fields and actual primary
   unit, not just topic/status. Include a supported mechanism, application,
   prerequisite, or reading diagnosis and teaching action; queue independent
   follow-up when appropriate. Do not count hints/retries as new coverage.
8. When continuing, offer a next topic, a focused explanation, or a mode switch
   conversationally; map that choice to the allocation policy internally.
   After a bounded repair and fresh attempt, park unresolved work rather than
   looping indefinitely. Do not add an exit ticket after this item: closing
   checks are session-level and reuse this evidence when sufficient.
   On pause/stop, checkpoint with no next question; on resume reconcile evidence
   IDs before grading so a recorded answer is not graded twice.

## Citation rules

Follow the source contract; never fabricate citations.

## Common pitfalls to flag in rationales

- Confusing service tiers (for example, Standard vs Premium SKUs) when SLA
  or feature differences drive the answer.
- Picking a regional service when the constraint requires global scope.
- Choosing managed identity vs service principal without the correct
  ownership boundary.
- Ignoring cost when the question explicitly mentions budget.
