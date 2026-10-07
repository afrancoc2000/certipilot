---
name: close-session
description: Close study sessions with reusable diagnostic evidence, coverage debt, and a confirmed proposal for tomorrow's plan.
---

# Close session

Use this skill at session close, including early stops and Follow Plan.
Apply the [canonical contract](../../instructions/progress-tracking.instructions.md).
Load its shared evidence/session specifications and the
[source contract](../../instructions/sources-and-citations.instructions.md).
Where a dated plan exists, propose tomorrow's block; `build-sprint-plan` owns
whole-plan creation. No automatic dated-plan edits.

## Inputs

- Today's date.
- Active exam/catalog and audit (actual allocation, breadth gaps, pending checks).
- The plan path retained by active-exam or Follow Plan resolution, if available;
  otherwise date-matching plans under `exams/<active-exam>/assets/study-plans/`.
  A filename or modification timestamp alone does not establish an active plan.
- Today's genuine evidence, supported diagnoses/actions, and actual activities
  completed vs. skipped; progress is the derived summary, not sole evidence.

## Procedure

1. Resolve the exam, read config/catalog, and obtain a current validated report
   (reuse a retained audit or `record --json` report under the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns);
   otherwise run a read-only audit).
   - Reuse the retained plan path for this session, checking its exam and dates;
     do not silently switch away from an explicitly selected plan.
   - If no path was retained, read candidate plans' actual date ranges and
     filter to plans covering today's date for the active exam. Exclude newer
     expired or future plans before considering any active marker or recency.
   - Use the sole date-matching plan. If multiple matches remain, ask which
     plan to adapt before proposing or writing a patch; do not guess by recency.
     On pause/stop, retain the unresolved choice without asking a new question
     or editing a plan.
   - Locate tomorrow's block only in the selected plan. If no match/block exists,
     or the retained plan is missing/out of range, still review and log; report
     no dated block to adapt. Any alternate plan needs the user's selection.
2. Apply the canonical closing diagnostic: reuse genuine mechanism,
   new-scenario application, and distractor-failure evidence by ID. If the user
   is continuing, ask only missing dimensions, one untimed question at a time,
   using the [item-quality gate](../select-next-question/SKILL.md#item-quality-gate).
   On pause/stop, skip all new prompts and checkpoint immediately; leave missing
   checks pending. Do not turn a stop into an exit-ticket requirement.
   Prepare missing mechanism/transfer prompts as `kind: free_response` with
   private grading criteria using the shared session schema; save them
   unanswered before asking. They take no answer position under the
   [deck schema](../coverage-audit/references/session.md#private-answer-position-deck). Do not invent options to satisfy persistence.
3. Produce an internal instructional brief with taught subskill IDs, demonstrated
   reasoning, supported diagnosis/action, and next protected breadth objective.
   Use `uncertain` when evidence does not identify the gap. Correct guesses
   retain their scores but do not establish mastery; immediate/assisted success
   is not delayed independent transfer.
4. Record genuine evidence and lifecycle events through `update-progress`, then
   checkpoint using its successful `record --json` report and `sha256`; re-audit
   only on a hash/date/revision change, conflict, failure or lost result. Complete units only with linked nonvoid evidence;
   otherwise mark interruption or explicit deferment, not completion. Preserve
   started/completed/assessed distinctions and deferred debt. Reused ticket
   evidence is not a new attempt. Pending delayed checks obey later-local-day
   and source-event requirements.
5. If a tomorrow block exists, prepare a proposal:
   - Preserve projected canonical allocation, catalog IDs, time budget, and
     next coverage from `coverage_queue`. Resume unfinished units with the same
     ID/category before new allocation, or explicitly defer them with visible
     debt. New carryover uses an eligible slot, marked `(carryover from <today>)`;
     do not double-count resumed work or append unlimited work.
   - Use fresh supported diagnoses to change teaching actions in eligible
     remediation slots. Repeated misses may warrant a tutor intervention but
     cannot replace breadth or restart an endless repair loop.
   - Schedule cold and later novel transfer checks within eligible work and
     keep outstanding checks visible if capacity is insufficient.
   - Preserve mock/dress-rehearsal milestones and all days other than tomorrow.
6. When the user continues, preview the proposed topic/time changes in plain
   language and ask for confirmation before writing. Keep the exact patch
   internally; show a unified diff only if requested.
   Reconcile concurrent plan edits before applying the confirmed change.
   On stop, retain the proposal for later; do not require a new decision now.
7. Log the session once via `update-progress`, whether adaptation is accepted,
   declined, or unavailable. Include ticket completeness, next action, pending
   checks, and actual allocation/debt. No fabricated planner score.

## Output

- Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
- Internal: instructional brief, synchronized evidence/summary, pending work,
  and checkpoint/repair status.
- Learner-facing: a short recap of what clicked, what needs another example,
  and the next topic. No routine audit dashboard or save receipt.
- Updated plan file only if one day's proposed patch was confirmed.
- Report whether tomorrow's block was adapted, proposed, or unchanged;
  describe carryover as named topics, not allocation debt or state identifiers.
  On stop, give a brief acknowledgment; disclose a failed save if applicable
  without requiring another question or decision.

## Guardrails

- Never edit days before tomorrow.
- Never touch milestones or the dress-rehearsal day.
- Preserve the plan's existing format (table or per-day headings).
- Never invent diagnoses or unsupported evidence.
- If no instructional change is supported, log without changing the plan;
  a clean score does not remove unassessed scope or pending transfer checks.
