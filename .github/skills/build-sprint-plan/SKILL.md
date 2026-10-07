---
name: build-sprint-plan
description: Produce a dated coverage-first certification sprint plan from the blueprint audit, exam date, available time, and evidence.
---

# Build sprint plan

Use this skill when the user provides an exam date and limited daily study
time and wants a calendar-based plan.
Load the [canonical contract](../../instructions/progress-tracking.instructions.md),
its shared evidence/session specifications, and the
[source contract](../../instructions/sources-and-citations.instructions.md).

## Inputs

- Exam date (required).
- Daily available minutes (default: 90–150).
- Active exam `exam.md`, `blueprint.json`, and read-only coverage audit.
- `exams/<active-exam>/assets/progress.md` weak/strong topics.
- `exams/<active-exam>/material/test-exams/*/results.md` failed-question indices.

## Procedure

1. Validate exam date:
   - If in the past, ask the user to confirm or correct.
   - If fewer than 3 days remain, flag uncovered scope and feasibility risk.
     Offer explicit triage as a user-confirmed override with coverage debt;
     never silently replace breadth with the highest-weighted weaknesses.
2. Offer a baseline mock exam to calibrate the plan:
   - Ask: "Want to start with a 10-question mock exam to measure your
     current level? (recommended if `exams/<active-exam>/assets/progress.md` is empty or stale)."
   - If yes, invoke `run-mock-exam`, then use its per-domain summary as the
     diagnostic signal within eligible remediation slots in step 3. A mock
     score is not proof of blueprint coverage.
   - If no, or if `progress.md` already has recent evidence (last 7 days),
     skip the baseline and proceed.
   - Reserve Day 1 of the plan for the baseline mock + review when used.
3. Resolve the active exam and audit its catalog/ledger. Read progress and
   test-exam evidence (including a baseline if available). Rank unassessed
   required subskills for protected coverage and diagnose supported weaknesses
   for bounded remediation; keep pending cold/delayed checks visible.
4. Build daily blocks (default 90–150 min) with timeboxes suited to the available
   time: retrieval warm-up, catalog coverage, bounded mechanism repair/deep dive,
   interleaved practice, and session-level closing review. Assign each primary
   activity explicit objective/subskill IDs, unit kind/mode, and evidence goal.
   Hints and repair follow-ups belong to their original unit.
5. Project the canonical allocation and audit `coverage_queue` from the carried
   position. Reconcile unfinished normal activities before new starts: resume
   the same ID or explicitly defer, retaining debt. Report started, completed,
   and assessed separately; a plan is none of them. Reserve eligible slots for
   checks using recorded local-day/source-event retention eligibility. Disclose
   infeasible scope rather than dropping breadth or inventing future starts.
6. Mandatory milestones:
   - Target at least 2 full timed mock exams before exam day; flag infeasibility
     rather than promising impossible scheduling. Mocks retain official weights.
   - Light dress-rehearsal day in the final 48 hours (no heavy new content);
     report remaining coverage debt honestly. Preserve existing milestones.
7. If a weak topic was missed twice in the same week, schedule a tutor deep
   dive in the next eligible remediation slot, with a specific teaching action.
   Bound repair/retest loops per the canonical policy.

## Output

- Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
  Present the learner's schedule using topic names, timeboxes, and practical
  goals. Explain feasibility honestly without diagnostic labels or ID lists.
- The saved plan/internal handoff retains the dated plan from tomorrow through exam day, with explicit timeboxes,
  catalog IDs, evidence goals, projected allocation, unassessed scope,
  pending checks, and breadth-preserving fallbacks for missed days.
- Save the plan under `exams/<active-exam>/assets/study-plans/<exam-date>-sprint.md` when the user
  asks to persist it.
- Preview changes and obtain confirmation before updating an existing dated
  plan. Never automatically rewrite plans after a quiz or audit.
- Append a one-line entry to the session log via `update-progress`.
- On pause, preserve planning phase and proposed changes in the canonical
  checkpoint with `mode: planner`, `phase: planning`, empty `items`,
  `current_unit_id: null`, and `allocation_category: null`. Store the target
  filename and complete proposed schedule/changes in `private_planning` under
  the [planner checkpoint schema](../coverage-audit/references/session.md#planner-proposals).
  Preserve the proposal privately on pause/resume; a proposal or saved
  checkpoint is not permission to edit a dated plan on resume. Ask for
  confirmation separately before applying changes.

## Style

- Markdown table or per-day headings — pick whichever the user prefers; ask
  once if unspecified.
- Keep each day skimmable in under 12 lines.
