# AZ-305 Study Agent

Personal study tutor for the **AZ-305: Designing Microsoft Azure Infrastructure
Solutions** exam, powered by a terminal AI agent that quizzes you on the course
material under [course/](course/).

The agent's behavior is defined in [AGENTS.md](AGENTS.md) and is compatible with
two CLIs — pick whichever you prefer (or use both).

## Repo layout

```text
az-305/
├── AGENTS.md          ← agent instructions (read by both CLIs)
├── opencode.json      ← OpenCode provider config (DeepSeek + OpenAI)
├── data/              ← external dataset drop zone (e.g. Savill videos)
├── course/            ← all study modules (Spanish)
└── README.md          ← you are here
```

## Prerequisites

- Node.js 20+ and npm
- A terminal (Git Bash, PowerShell, WSL — all fine)

## Option 1 — GitHub Copilot CLI (recommended to start)

Uses your existing GitHub Copilot subscription. No extra API keys, no per-token
cost.

### Install

```bash
npm install -g @github/copilot
copilot --version
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

## Option 2 — OpenCode

Open-source CLI that lets you bring your own provider keys — useful if you want
to use **DeepSeek V4 Pro** (much cheaper than GPT-5) or run a model Copilot
doesn't expose.

### Install

```bash
npm install -g opencode-ai
opencode --version
```

### Configure API keys

Set the keys for whichever providers you want to use:

```bash
# DeepSeek (cheap, default in opencode.json)
echo 'export DEEPSEEK_API_KEY="sk-..."' >> ~/.bashrc

# OpenAI (optional, for GPT-5.5)
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc

source ~/.bashrc
```

Get a DeepSeek key at [platform.deepseek.com](https://platform.deepseek.com).

### Run

```bash
cd /c/Users/anafranco/Workspace/learning/az-305
opencode
```

OpenCode reads [AGENTS.md](AGENTS.md) (same file as Copilot CLI) plus
[opencode.json](opencode.json) for the model wiring.

Useful slash commands:

- `/model` — switch between `deepseek/deepseek-chat` and `openai/gpt-5.5`
- `/help` — full command list

## Which one should I use?

| Need                                             | Pick                       |
| ------------------------------------------------ | -------------------------- |
| Already paying for Copilot, want zero setup      | **Copilot CLI**            |
| Want to grind hundreds of questions cheaply      | **OpenCode** with DeepSeek |
| Want to A/B different models for the same prompt | Install both               |

Both tools read the same `AGENTS.md`, so the tutor behaves consistently across
them.

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

### OpenCode (interactive)

Start `opencode`, then paste the same prompt used for Copilot interactive mode.

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

Edit [AGENTS.md](AGENTS.md) directly. Both CLIs re-read it on session start, so
changes take effect the next time you launch `copilot` or `opencode`.
