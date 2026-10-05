---
name: follow-plan
description: Execute today's block from an active certification study plan, update progress, and adapt tomorrow's block.
---

# Follow Plan

## Purpose

Execute today's block from the active exam's study plan, orchestrating warm-up, remediation, mixed quiz, and review. Then update progress and close the session with plan adaptation.

## Usage

Invoke when the user runs a Follow plan session:
- `/follow-plan` or `/follow-plan [plan-file]`
- Optional: `--duration <minutes>` (default 120 min). Example: `/follow-plan exams/<active-exam>/assets/study-plans/plan.md --duration 90`
- Or when user says: "Run today's plan", "Execute today's block", "Follow plan session", or "Run today's plan for 60 minutes"

## Coverage ledger contract (`exams/<active-exam>/assets/progress.md`)

The coverage ledger must live under the heading:

`## Coverage ledger (breadth guardrail)`

Required sub-sections and formats:

1. `### Domain last-seen snapshot`
   - `- Identity/Governance/Monitoring (D1): last seen YYYY-MM-DD`
   - `- Data storage (D2): last seen YYYY-MM-DD`
   - `- Business continuity (D3): last seen YYYY-MM-DD`
   - `- Infrastructure/Compute/Networking/Migrations (D4): last seen YYYY-MM-DD`

2. `### Unseen or stale objective backlog`
   - `- <domain> / <objective> — status: unseen|stale|done, target: YYYY-MM-DD|next session, last seen: YYYY-MM-DD|never`

Bootstrap rule:
- If `## Coverage ledger (breadth guardrail)` is missing, create this section before selecting coverage objectives.
- If sub-sections exist but entries are malformed, normalize only the affected lines (do not rewrite unrelated parts of `exams/<active-exam>/assets/progress.md`).

## Workflow

1. **Locate the plan**
   - If plan-file is provided, use it.
   - Otherwise, scan `exams/<active-exam>/assets/study-plans/` for the active plan (most recently modified or explicitly marked active).
   - If no plan exists, ask the user to provide an exam date, weak topics, and available time; create a baseline plan first.

2. **Check today's date**
   - Extract today's date from the system.
   - Look up today's block in the plan file.
   - If today is not in the plan, offer to fold it into tomorrow or compress the remaining schedule.

3. **Read today's block**
   - Extract the listed topics, timeboxes, and activity sequence for today.
   - Example structure: "Topics: AKS, Cosmos consistency. Time: 120 min. Activities: 1) 15-min warm-up (VMs, Storage), 2) 45-min remediation (AKS design patterns), 3) 45-min mixed quiz (AKS + Cosmos + networking), 4) 10-min review."
   - If `--duration` parameter is provided, scale all phase timeboxes proportionally to fit the new total (e.g., 120→60 min scales all phases to 50%).

4. **Enforce breadth guardrails before execution**
   - Reserve a coverage slot (10-15 min, or ~15% of session) for one unseen or stale objective (not seen in the last 7-10 days).
   - Select coverage objective from `exams/<active-exam>/assets/progress.md` coverage ledger first.
   - If ledger does not exist yet, bootstrap it using the contract above, then select objective.
   - If backlog is empty, infer one objective from low-frequency domains and append it to backlog with `status: unseen`.
   - Prioritize objectives that prevent domain starvation (for example migrations, hybrid identity/AD Connect, monitoring).
   - Enforce session mix target: ~60% weak remediation, ~25% retention/adjacent, ~15% unseen/stale.
   - Ensure rolling 3 sessions touch all of the active exam's domains at least once.

5. **Execute the block in order**
   - Use `quiz-agent` for warm-up and mixed quiz phases.
   - Use the coverage slot for one unseen/stale objective (mini-quiz or tutor micro-drill).
   - Use `tutor-agent` for remediation (if user requests deep dive on a topic).
   - Keep the user in-session; do not close between phases.

6. **Update progress**
   - After the final quiz/review, call `update-progress` skill to log answers and bump weak/strong topics.
   - Update only under `## Coverage ledger (breadth guardrail)` in `exams/<active-exam>/assets/progress.md` (do not create alternative coverage section names).
   - In that section, update: domain last-seen dates, objective `last seen` date, and objective status transitions (`unseen/stale -> done` when completed).

7. **Close the session**
   - Call `close-session` skill to:
     - Adapt tomorrow's block based on today's performance.
     - Append a one-line session log entry with date, duration, score, and next-day priority.

## Error handling

- If the plan file is malformed or missing, report the error and ask the user to provide a corrected file or restart plan creation.
- If today's date is in the past, ask the user to confirm or correct the system date.
- If fewer than 3 days remain before the exam date in the plan, flag as high-risk and produce a triage-only block.

## Outputs

- Session transcript with all quiz responses, explanations, and grades.
- Updated `exams/<active-exam>/assets/progress.md` with today's performance.
- Updated coverage ledger in `exams/<active-exam>/assets/progress.md` (domain/objective last-seen and unseen backlog status).
- Updated `exams/<active-exam>/assets/study-plans/[plan-file]` with tomorrow's block adapted to today's results.
- One-line session log entry appended to `exams/<active-exam>/assets/progress.md`.
