---
name: follow-plan
description: Execute today's study block with protected blueprint coverage, record evidence, and propose confirmed plan adaptation.
---

# Follow Plan

## Purpose

Execute today's block with protected coverage, bounded remediation, retention,
and session-level review. Apply the
[canonical contract](../../instructions/progress-tracking.instructions.md),
record evidence first, and propose plan adaptation without automatic edits.
Explicitly load its shared evidence/session specifications and the
[source contract](../../instructions/sources-and-citations.instructions.md).
Apply the [efficient-turn contract](../../../AGENTS.md#efficient-study-turns):
retain today's resolved plan and context, use direct tools for deterministic
writes, and avoid redundant delegation/audits. Dispatch specialists for learning
work, not merely to reread files or invoke a known persistence command.

## Usage

Invoke when the user runs a Follow plan session:
- `/follow-plan` or `/follow-plan [plan-file]`
- Optional: `--duration <minutes>` (default 120 min). Example: `/follow-plan exams/<active-exam>/assets/study-plans/plan.md --duration 90`
- Or when user says: "Run today's plan", "Execute today's block", "Follow plan session", or "Run today's plan for 60 minutes"

## Coverage inputs

Resolve the active exam, read its `exam.md`, and use its catalog and
[coverage audit](../coverage-audit/SKILL.md) under the canonical contract.
Check for an unambiguous checkpoint before beginning a new block; resume its
unit/phase and exact pending item, reconciling ledger IDs without regrading.

## Workflow

1. **Locate the plan**
   - If plan-file is provided explicitly by the user, use it; still perform
     the date check below and do not silently replace it.
   - Otherwise, reuse the matching plan paths retained by active-exam
     resolution. If none were supplied, scan
     `exams/<active-exam>/assets/study-plans/` and the cross-exam master plan.
   - Filter candidates to plans covering today's date for the resolved exam
     before applying any tiebreaker. Prefer an explicitly marked active match,
     then the most recently modified matching plan. If still ambiguous, ask
     the user. Never let a newer expired or future-dated plan displace a match.
   - If plans exist but none cover today, explain the date gap and ask which
     plan to adapt; do not silently select by recency.
   - If no plan exists, ask for an exam date and available time; build a
     catalog-driven baseline plan with the user's confirmation.

2. **Check today's date**
   - Extract today's date from the system.
   - Look up today's block in the plan file.
   - If today is not in the plan, offer breadth-preserving carryover/compression.
     Preview and confirm any dated-plan change before writing.

3. **Read today's block**
   - Extract the listed topics, timeboxes, and activity sequence for today.
   - Map activities to catalog objective/subskill IDs, unit kinds, and evidence
     goals. If `--duration` is provided, fit fewer primary units/timeboxes to
     the budget, preserving allocation order and carrying unfinished work.
   - If an old plan conflicts with the canonical policy, explain the conflict
     and propose compliant execution or an explicit user override. Do not
     silently rewrite the plan or claim its old allocation is coverage-first.

4. **Enforce breadth guardrails before execution**
   - Apply canonical audit allocation and `coverage_queue`, breadth, and pending
     checks. Before more normal units, resume started/interrupted work using
     its original ID/category or explicitly defer it, retaining visible debt.
   - Project new starts only after reconciliation; never report a started
     allocation cycle as completed delivery.

5. **Execute the block in order**
   - Use `quiz-agent` for warm-up and mixed quiz phases.
   - Use quiz or tutor activities for each protected coverage unit, recording
     exposure separately from independent assessment.
   - Use `tutor-agent` for a supported diagnosis and specific teaching action
     within eligible remediation units, bounded to a repair and fresh check.
   - Pass exam/revision, subskill IDs, kind/mode, evidence context/assistance,
     and pending checks to each agent. The orchestrator owns recording if the
     delegated agent cannot execute the helper.
   - Record actual starts with `lifecycle: started`; link attempts to `unit_id`
     and append lifecycle events under the shared schema.
   - Present one question, then stop for a genuine user turn. Hints change
     assistance; immediate checks remain post-teaching and untimed.
   - Keep the user in-session; do not close between phases.
   - Checkpoint prepared items and genuine answers before advancing. Stop/pause
     immediately checkpoints interruption without another question or review
     prompt. Resume directly when matching state is unambiguous.

6. **Update progress**
   - Use `update-progress` after genuine graded answers: record evidence first,
     then the derived summary/applied marker. Carry actual units only.
   - At review, apply `close-session`'s reusable diagnostic; do not add another
     local exit-ticket procedure or ask missing prompts after a stop.
   - Report demonstrated reasoning separately from correct scores, assisted
     work, immediate success, and delayed transfer.

7. **Close the session**
   - Call `close-session` skill to:
     - Produce the instructional brief and next protected breadth objective.
     - Propose tomorrow's adjustment and obtain confirmation before any write.
     - Log once with date, duration, result, pending checks, and coverage debt.

## Error handling

- If the plan file is malformed or missing, report the error and ask the user to provide a corrected file or restart plan creation.
- If today's date is in the past, ask the user to confirm or correct the system date.
- If fewer than 3 days remain, flag coverage risk and offer explicit triage as
  an override; never silently abandon breadth.

## Outputs

Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
The persisted artifacts and operational statuses below are internal outputs,
not a checklist to recite. Teach conversationally throughout; close with a
brief learning recap and a plain-language plan proposal when appropriate.
Surface failed saves or material limitations, not routine successful bookkeeping.

- Session transcript with all quiz responses, explanations, and grades.
- Updated `exams/<active-exam>/assets/progress.md` with today's performance.
- Validated canonical evidence plus a synchronized summary, or explicit write
  failure/repair status.
- Proposed tomorrow block; update the dated plan only after confirmation.
- One-line session log entry appended to `exams/<active-exam>/assets/progress.md`.
- Private checkpoint status, with no solutions or locked answer-deck disclosure.
