# Certification Study Agent

One workspace for studying multiple Microsoft and GitHub certifications with
GitHub Copilot. Each exam is isolated under `exams/<exam-id>/`; shared agent
instructions resolve the active exam before reading material or tracking
progress.

## Exams

| Exam | Status |
| --- | --- |
| [GH-300: GitHub Copilot](exams/gh-300/exam.md) | Passed; closed |
| [AZ-104: Microsoft Azure Administrator](exams/az-104/exam.md) | Passed; closed |
| [AZ-305: Azure Infrastructure Solutions](exams/az-305/exam.md) | Existing study material |
| [GH-600: Developing in Agentic AI Systems](exams/gh-600/exam.md) | Scaffolded; official syllabus, no material yet |
| [AI-103: Developing AI Apps and Agents on Azure](exams/ai-103/exam.md) | Scaffolded; verified blueprint, no material yet (prerequisite for AI-500) |
| [AI-500: Designing and Implementing Multi-Agent AI Solutions](exams/ai-500/exam.md) | Scaffolded; official syllabus, no material yet (requires AI-103) |

## Start studying

Open Copilot Chat in this workspace and name the exam:

```text
Study GH-300 now
Quiz me on GH-300 prompt engineering
Run today's GH-300 plan
Build an AZ-104 sprint plan for October 10 with 90 minutes per day
```

The agent reads `exams/<active-exam>/exam.md` first, then uses that exam's
material, progress, and study plan. It falls back to authoritative first-party
documentation when local material is missing.

## Runtime models and responsive turns

Skills define workflows, not model selection. Copilot's built-in
`execution-subagent` is configured separately from the quiz, tutor and planner
agents. In Copilot's user-level `settings.json`, a per-helper pin uses:

```json
{
  "subagents": {
    "agents": {
      "execution-subagent": {
        "model": "gpt-6-luna"
      }
    }
  }
}
```

Merge this into existing settings; do not replace the file. The pin applies
across repositories and does not change the main or study-agent models. Verify
`subagents.agents.execution-subagent.model` with `/settings` (alias `/config`;
`copilot config` outside a session); an already running client may need to reload
or restart/resume before using updated settings. This is Copilot configuration,
not [opencode.json](opencode.json), which controls the separate OpenCode client.

The [efficient-turn contract](AGENTS.md#efficient-study-turns) reduces routine
execution-agent calls, full-file rereads and duplicate audits, while retaining
genuine-answer checks, first-party verification and every required durable save.
Actual model availability, price and turn latency depend on the runtime;
instruction tests do not establish a speed improvement.

## Coverage-first study

The official published blueprint, not the failure log or question bank, defines
the curriculum. Each exam has a shared `blueprint.json` with traceable objectives
and required subskills, plus a separate local `assets/coverage.json` evidence
ledger. [Progress tracking](.github/instructions/progress-tracking.instructions.md)
is the canonical policy; [coverage-audit](.github/skills/coverage-audit/SKILL.md)
documents the helper and batch format.

- Normal study protects coverage first, with bounded remediation and retention
  in a rolling primary-unit cycle. Short sessions carry the unfinished cycle
  and breadth debt; planned or skipped work is not counted as delivered.
- Coverage targets unassessed subskills before stale familiar topics. A domain
  visit, bank coverage tag, or one narrow answer cannot clear a broad objective.
  The audit's ordered `coverage_queue` protects an unvisited-first pass before
  systematic revisits; see the canonical policy for allocation and substitutions.
- Topic-specific drills/tutor requests are explicit overrides. Mocks keep
  official domain weights and deferred grading, not the normal-study quotas;
  neither overrides nor mocks advance the normal allocation cycle.
- Scores, demonstrated reasoning, assistance, and context are separate.
  A correct guess keeps its score, but two correct choices do not imply mastery.
  Letter-only correctness preserves earlier demonstrated reasoning but adds
  none. Independent mistakes reopen evidenced scope. Delayed transfer needs a
  nonvoid source event, a later day in the learner's recorded fixed-offset
  timezone, and a fresh independent scenario, not just a new chat ID.
- Session review reuses genuine checks for mechanism, new-scenario application,
  and distractor failure. Only missing exit-ticket dimensions need prompts,
  one at a time; early stops remain incomplete, not an endless extra test.
- Evidence is recorded first; progress is a derived human summary with an
  applied-attempt-ID marker so interrupted summary writes can be repaired
  without duplicating attempts. The ledger hash separately guards concurrent
  writes. Started, completed, and assessed are separate: resume the same unit
  or explicitly defer it before more normal work; deferred debt stays visible.
  Completion needs linked nonvoid evidence, including unscored teaching where
  appropriate. The 60/25/15 started allocation is not a promise that completed
  allocation matches. Legacy completion stays unknown. Dated plans change only
  after confirmation.
- A genuinely disowned answer retracts its displayed score. Recorded responses
  use an append-only `voided_attempts` batch through the same validated `record`
  command; original results remain in history but no longer count as effective
  evidence. Progress tracks applied void IDs as well as attempts for repair.
  Disowned answers re-ask unchanged. Invalid/ambiguous items use a distinct
  genuine-provenance correction with no learner penalty or mastery; replace
  only when continuing, preserving the locked answer position.

### Local audit commands

Run from the repository root (substitute one exam folder ID):

```powershell
python .github\skills\coverage-audit\scripts\coverage.py audit --exam gh-300
python .github\skills\coverage-audit\scripts\coverage.py audit --exam gh-300 --as-of 2026-10-04 --json
python .github\skills\coverage-audit\scripts\coverage.py init --exam gh-300
python .github\skills\coverage-audit\scripts\coverage.py record --exam gh-300 --input <batch.json> --expected-sha256 <hash-from-audit>
```

`audit` is read-only; `init` creates an unknown ledger and fails if one exists.
Use `record` only with a validated evidence batch and the current ledger hash
(`sha256` from the last audit or successful `record --json`);
it writes atomically/idempotently and rejects conflicting changes. All commands
accept `--root <repo>`; otherwise the helper resolves root from its own location.
Never reset a ledger or bypass an error to make a report look complete.

The audit exposes objective/subskill denominators, uncovered scope, next
allocation, `coverage_queue`, domain breadth gaps, pending checks, and the ledger hash. It checks
consistency against the catalog, not semantic completeness of a live website.
Official-source reconciliation remains separate; unavailable sources must stay
unverified, and changed revisions cannot silently remap old IDs. These reports
do not guarantee mastery, exam success, or coverage of undisclosed exam content.
The six exams' evidence, IDs, and normal allocation positions remain isolated.

### Atlas-inspired teaching, with limits

[Kiddom Atlas](https://www.kiddom.co/atlas),
[its reported impact](https://www.kiddom.co/impact/atlas-impact), and the
[Gates Foundation account](https://usprogram.gatesfoundation.org/news-and-insights/articles/what-it-looks-like-to-design-technology-for-teachers-and-the-difference-it-makes-in-the-classroom)
describe curriculum-aligned exit tickets, examining student reasoning, and
actionable instructional adjustments. This workflow adapts that feedback loop:
what was taught, what genuine responses demonstrated, a supported diagnosis
(or uncertainty), a specific next teaching action, and the next protected
breadth objective.

Protected allocation, full-blueprint catalogs, assistance-aware evidence, and
delayed transfer checks are our extensions, not policies established by the
pilot. Reported classroom outcomes involved curriculum, assessment, teacher
support, and implementation together; they do not establish adult certification
outcomes or a causal effect from AI alone.

### Quiz and mock safeguards

Questions remain one at a time, with genuine-turn/timestamp checks and neutral
answer formatting. Correct-answer positions use a mechanically randomized,
balanced locked deck, not model intuition. Mocks preload validated public/private
manifests, journal genuine answers without grading between items, and retain
complete missed/flagged/voided-item reviews at the end. See
[quiz-agent](.github/agents/quiz-agent.agent.md) and
[run-mock-exam](.github/skills/run-mock-exam/SKILL.md).

The [source contract](.github/instructions/sources-and-citations.instructions.md)
requires verification before presentation; unchanged prepared-session claims
reuse that snapshot, while changed constraints, disputes, and stale metadata
require reverification. The compact
[item-quality gate](.github/skills/select-next-question/SKILL.md#item-quality-gate)
checks decisive constraints, defensible answers, causal distractors, and genuine
transfer. The [evaluation guide](.github/skills/coverage-audit/references/evaluation.md)
separates deterministic contract tests from manual multi-turn scenarios and the
item-quality rubric. Passing tests or link checks is not a model evaluation.

### Pause and resume

Say "pause" or "stop" to checkpoint without another question. A single matching
checkpoint resumes directly, preserving the exact unanswered item, answer deck,
unit, and genuine answer journal. Ambiguous or conflicting state needs
clarification; missing answers are never reconstructed.

The [shared session protocol](.github/skills/coverage-audit/references/session.md)
uses the local `session.py` helper and ignored per-exam `assets/session.json`,
with atomic/hash-guarded writes. Host session SQL is optional. Private solutions
remain out of user-facing summaries; this is presentation separation, not a
claim that the local file is secret from its owner. Ledger/checkpoint/summary
writes reconcile by stable evidence IDs rather than duplicate scoring. Failed
or unavailable storage is reported explicitly, never called a saved session.

## Add another certification

Follow [exams/README.md](exams/README.md). The minimum exam package is:

```text
exams/<exam-id>/
├── exam.md
├── blueprint.json
├── assets/
│   ├── coverage.json
│   ├── progress.md
│   └── study-plans/README.md
└── material/README.md
```

Exam `assets/` folders and the top-level `assets/` folder are private by default
through `.gitignore`, including coverage backups, mock-session state, evidence
batches, and dated plans, regardless of filename or extension. Keep new personal
study files there; no separate state folder is needed. Only their root
`README.md` files and each exam's `assets/study-plans/README.md` are shared
templates. Graded results under study material also remain ignored. Ignore rules
do not untrack files already in Git; check the index before sharing.
Shared catalogs,
study material, and exam configuration can be shared. Verify a new exam's
official outline before declaring its catalog complete, and initialize its
ledger as unknown rather than borrowing another exam's evidence.
