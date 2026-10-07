---
name: select-next-question
description: Choose the next certification objective/subskill and question style from the coverage audit, protected allocation, and attributable evidence.
---

# Select next question

Use this skill at the start of every quiz turn (single question or case
study) to pick a catalog subskill and style under the
[canonical coverage contract](../../instructions/progress-tracking.instructions.md).
Explicitly load its shared evidence/session specifications and the
[source contract](../../instructions/sources-and-citations.instructions.md).
Follow the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns).
Selection is for a new item, not for grading the pending answer. Reuse a current
validated audit/record report and retained exam/plan context; search only the
selected scope, and reload or re-audit when the contract's freshness checks fail.

## Inputs

- Active exam config, `blueprint.json`, and the `coverage-audit` report
  (`coverage_queue`, next allocation, breadth gaps, pending checks).
- `exams/<active-exam>/assets/progress.md` (derived summary and mistake log).
- **ExamTopics question bank, only if declared in this exam's config:** `exams/<active-exam>/material/test-exams/examtopics/questions.md` (count
  in the active exam's `exam.md`) + `exams/<active-exam>/material/test-exams/examtopics/answer-key.md`, prioritized via
  `exams/<active-exam>/material/test-exams/examtopics/coverage-analysis.md` (NEW/PARTIAL clusters,
  duplicate map).
- Optional: failed-question indices under `exams/<active-exam>/material/test-exams/*/results.md`.
- Optional: today's plan, resolved by
  [active-exam](../../instructions/active-exam.instructions.md) (date range covers
  today; never chosen by recency alone).
- Optional: user-requested domain or topic.

## Procedure

1. Resolve one exam, load its `exam.md` and catalog, and obtain a current
   validated report (a retained audit/successful record report under the
   efficient-turn contract, otherwise a read-only audit).
   Read its progress and available failed-question evidence without borrowing
   another exam's IDs or sources. Follow the canonical missing-ledger/error
   handling; absent evidence is unknown. Check the session checkpoint first:
   resume an unambiguous pending item instead of selecting a new one. Reconcile
   unfinished normal units by resuming the same ID or explicitly deferring them.
2. Reuse the plan path resolved for this session under
   [active-exam](../../instructions/active-exam.instructions.md); if one covers
   today's date, extract today's planned topics. Multiple date matches are the
   user's choice, not a recency guess.
3. Honor an explicit topic/domain as an `override`, recording scope/reason and
   coverage debt; do not advance the normal cycle.
4. Otherwise use the audit's next normal allocation slot:
   - Coverage: consume `audit --json`'s `coverage_queue` under the canonical
     allocation policy; after recording begun work, use the successful
     `record --json` report (re-audit only when its freshness checks fail under
     the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns)). Resuming an existing
     unit is not a new queue selection or slot.
   - Remediation/retention: select qualified evidence or pending checks. Use only
     the canonical, explicitly recorded coverage substitutions when unavailable.
   - Today's plan is a tiebreaker within eligible scope, not a competing quota.
     Carry unfinished allocation across sessions and surface breadth gaps.
   - For mock preloading, instead use the official domain quotas supplied by
     `run-mock-exam`; normal allocation and topic overrides do not apply.
5. Map chosen required subskill IDs to a concrete stem in a declared bank:
   - Prefer questions tagged NEW or PARTIAL in `coverage-analysis.md` for the
     target topic; collapse near-duplicate variants to a single representative.
   - Bank NEW/PARTIAL tags guide stem choice, not official scope completion.
   - If no declared stem fits the subskill, author an original scenario in the
     same style (see style references in
     `.github/instructions/sources-and-citations.instructions.md`).
6. Avoid:
   - Verbatim repeats of any question in the mistake log within the past 7
     days (rephrase the ExamTopics stem or pick a sibling variant).
   - Re-asking the same weak topic two turns in a row unless the user opted
     into focused practice.
7. Pick the question style:
   - Default: scenario-based single-answer (A/B/C/D).
   - Use multi-select when the topic naturally has multiple correct
     components (for example, identity protection signals).
   - For an open-text mechanism or transfer diagnostic outside mocks, use
     `kind: free_response` and private verified grading criteria, not invented
     options. Apply the shared session preparation/response contract.
   - Use matching when comparing services on shared dimensions.
   - Use a 2–4 question case study when the user asks for one or when the
     topic benefits from compound reasoning. Still present only one question
     per turn and wait for genuine input.
8. Apply the item-quality gate below and source verification contract before
   asking. If unsupported or ambiguous, revise or reject the item, not the learner.
9. Apply the [quiz agent's locked deck and presentation contract](../../agents/quiz-agent.agent.md#correct-answer-position-generation).
   Persist the exact prepared item and private verification in the checkpoint
   before asking, binding its `unit_id` to the allocated current activity and
   verifying all item targets are in that unit. No solution metadata appears
   in the public question.

## Item-quality gate

Apply the shared [item-quality rubric](../coverage-audit/references/evaluation.md#item-quality-rubric)
before presenting a quiz, mock, or transfer item. Compact execution gate:

- Exact subskill/decision, decisive constraints, one defensible best answer or
  declared multi-select count, and verified causal rationale for each option.
- For free-response diagnostics, replace option/key requirements with verified
  private criteria describing the reasoning sought. Preserve the exact prompt,
  source snapshot and rubric across resume; criteria are not learner-facing cues.
- Neutral, similarly specific options without lead-in cues; preserve locked order.
- Transfer changes a decision-relevant condition. Ask "What changes in the
  decision, and why?" only when reasoning is needed, not on every score item.
  Credit multiple subskills only for reasoning that actually assesses each.

Reuse qualifying transfer responses in closing review. A failed gate blocks
presentation; a discovered live defect uses the canonical invalid-item flow
without penalty, with replacement only after continued permission.

## Output

- Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
- Return internally to the orchestrator objective/subskill IDs, primary unit kind/mode, style, and one-line
  selection rationale; include a substitution/override reason when applicable.
- The learner sees only a natural transition when useful and the question,
  never selection bookkeeping or private handoff fields.
- Keep expected answers and scoring evidence private until grading. Track the
  first attempt independently; teaching follow-ups are not fresh coverage units.
- Capture the primary unit's actual start timestamp when its activity begins,
  separately from the eventual answer timestamp; new units carry
  `lifecycle: started`. Pass the same unit ID into linked attempts.
- Ask one question with neutral options for choices or only the stem for
  free-response, then stop for genuine input. On a stop
  request, checkpoint without asking.
