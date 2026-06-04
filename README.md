# AZ-305 Study Agent

Personal study tutor for the **AZ-305: Designing Microsoft Azure Infrastructure
Solutions** exam, powered by a terminal AI agent that quizzes you on the course
material under [course/](course/).

The agent's behavior is defined in [AGENTS.md](AGENTS.md) and is compatible with
GitHub Copilot CLI.

## Repo layout

```text
az-305/
├── AGENTS.md          ← agent instructions for the study agent
├── data/              ← external dataset drop zone (e.g. Savill videos)
├── course/            ← all study modules (Spanish)
└── README.md          ← you are here
```

## Prerequisites

- GitHub Copilot CLI **1.0.11+** (recommended: latest)
- Windows with `winget` available
- A terminal (Git Bash, PowerShell, WSL — all fine)

Why 1.0.11+: release 1.0.11 added directory-level discovery for custom
instructions, skills, MCP servers, and agents from the working directory up to
the git root, which makes `AGENTS.md` behavior reliable in nested repo layouts.

## Option 1 — GitHub Copilot CLI (recommended to start)

Uses your existing GitHub Copilot subscription. No extra API keys, no per-token
cost.

Interactive mode is the recommended default workflow for this repo.

### Install

Minimum recommended version for this repo: **1.0.11+**.

```bash
winget install --id GitHub.Copilot --exact
copilot --version
```

To update later:

```bash
winget upgrade --id GitHub.Copilot --exact
```

### Run

```bash
cd /c/Users/anafranco/Workspace/learning/az-305
copilot
```

First launch opens a browser to authenticate with your GitHub account. After
that, `copilot` in this folder will read [AGENTS.md](AGENTS.md) and behave as
the AZ-305 tutor.

Useful slash commands inside the session:

- `/model` — switch between GPT-5, Claude, etc.
- `/help` — full command list
- `/exit` — quit

## Daily plan workflow

For guidance on creating an effective plan from scratch (starting with a
50-question mixed mock), see
[data/study-plans/README.md](data/study-plans/README.md).

### Run today's study block

Use the `follow-plan` skill to execute today's block from your active study
plan. The skill automatically:

- Checks today's date against the plan.
- Runs warm-up, remediation, mixed quiz, and review in order.
- Updates `data/progress.md` with results.
- Adapts tomorrow's block and logs the session.

#### Interactive mode

Start `copilot`, then run:

```text
/follow-plan data/study-plans/study-plan-2026-05-27-to-2026-06-15.md
```

Optional: specify duration (default 120 min):

```text
/follow-plan data/study-plans/study-plan-2026-05-27-to-2026-06-15.md --duration 90
```

Or simply say: "Run today's plan" or "Run today's plan for 60 minutes", and the
skill will find the active plan.

## Study modes

All five operating modes are available. Pick based on your goal.

### 1. Quiz (default)

One exam-style question per turn. The agent grades your answer and updates your
progress.

**Interactive:**

```text
copilot
> Quiz me on Azure VMs
> Random quiz on AKS
```

### 2. Tutor

Deep conceptual explanation with a logic-first decision framework (goal →
decision tree → trade-offs → distractors → rule of thumb) + mental map + one
transfer question.

**Interactive:**

```text
copilot
> Explain Cosmos DB consistency levels (tutor mode)
> Teach me when to use App Service vs Container Apps
```

### 3. Mock exam

10 questions with domain-weighted selection, deferred grading, and per-domain
summary. Automatically updates progress.

**Interactive:**

```text
copilot
> Run a mock exam
> 10-question mock on weak topics
```

### 4. Sprint

Build a dated study plan from your exam date, weak topics, and available time.
Default 90–150 min per day with 70% weak / 20% adjacent / 10% retention mix.

**Interactive:**

```text
copilot
> Build a sprint plan
> Create a plan for exam on June 15 with 2 hours/day
```

### 5. Follow plan

Execute today's study block from your active plan (warm-up → remediation → mixed
quiz → review). Automatically adapts tomorrow's block and logs the session.
**Recommended for daily study.**

**Interactive:**

```text
copilot
> /follow-plan data/study-plans/study-plan-2026-05-27-to-2026-06-15.md
> Run today's plan
> Run today's plan for 60 minutes
```

For more details on all modes, see [AGENTS.md](AGENTS.md).

## Adding external study material

Drop transcripts, PDFs, or other reference material into [data/](data/) — see
[data/README.md](data/README.md) for details. The agent is already configured to
cite from `data/savill/` when present.

## Updating the agent's behavior

Edit [AGENTS.md](AGENTS.md) directly. Copilot CLI re-reads it on session start,
so changes take effect the next time you launch `copilot`.
