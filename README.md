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

One-shot mode (no interactive session):

```bash
copilot -p "Quiz me on Cosmos DB consistency levels"
```

## Daily plan workflow (copy/paste)

For guidance on creating an effective plan from scratch (starting with a
50-question mixed mock), see
[data/study-plans/README.md](data/study-plans/README.md).

Use the sprint plan in
[data/study-plans/study-plan-2026-05-27-to-2026-06-15.md](data/study-plans/study-plan-2026-05-27-to-2026-06-15.md)
as the source for each session and always persist results to
[data/progress.md](data/progress.md).

### Copilot CLI (interactive)

Start `copilot`, then paste:

```text
Use data/study-plans/study-plan-2026-05-27-to-2026-06-15.md as the active study plan.
Today is YYYY-MM-DD.
Run a 2-hour sprint session with:
1) retrieval warm-up,
2) focused remediation for today's topic,
3) mixed interleaved quiz,
4) concise review + next-day priority.
After grading, update data/progress.md.
```

### Copilot CLI (one-shot)

```bash
copilot -p "Use data/study-plans/study-plan-2026-05-27-to-2026-06-15.md as the active plan. Today is YYYY-MM-DD. Run a 2-hour sprint session (retrieval, focused remediation, mixed quiz, review) and update data/progress.md."
```

### Optional quick variants

- **60-minute day:** replace "75-minute" with "60-minute" in the prompt.
- **120-minute day:** replace "75-minute" with "120-minute" and request 10 extra
  mixed questions at the end.
- **Domain focus day:** append "Focus only on <domain> from today's plan, then
  add 3 retention questions from other domains."

## Adding external study material

Drop transcripts, PDFs, or other reference material into [data/](data/) — see
[data/README.md](data/README.md) for details. The agent is already configured to
cite from `data/savill/` when present.

## Updating the agent's behavior

Edit [AGENTS.md](AGENTS.md) directly. Copilot CLI re-reads it on session start, so
changes take effect the next time you launch `copilot`.
