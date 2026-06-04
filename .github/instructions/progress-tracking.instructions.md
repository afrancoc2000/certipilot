---
applyTo: "data/progress.md"
description: How to read and update data/progress.md across all AZ-305 agents
---

# Progress tracking rules

`data/progress.md` is the agent's persistent notebook across sessions. Treat
it as a study log, not a database. Keep edits surgical and the file readable.

## At session start

1. Read `data/progress.md` first.
2. Greet with a one-line summary of weak topics and last session result
   (for example: "Última sesión: 7/10 en mock. Pendiente reforzar: AKS,
   ExpressRoute, Cosmos consistency.").
3. Bias question selection by weak topics (see selection mix below).

## Question selection mix

- ~60% weak topics
- ~25% retention checks on strong or adjacent topics
- ~15% unseen or stale objective rotation (not seen in the last 7-10 days)

Hard coverage rules:
- Include at least one unseen/stale objective in every session.
- Ensure rolling 3 sessions touch all four AZ-305 domains at least once.

Never quiz exclusively on weak topics. Avoid re-asking a mistake-log question
verbatim within the same week — rephrase or pick a sibling subtopic.

## After every graded answer

- ❌ incorrect: append a full entry to the mistake log; bump or add the topic
  to weak topics (increment `misses`, update `last seen`, refresh note).
- ⚠️ partial: append to the mistake log with what was missing; add to weak
  topics with `misses: 1` if not already there.
- ✅ correct: if the topic was in weak topics, decrement `misses` (or move to
  strong topics after 2 consecutive correct); if already strong, bump
  `correct streak` and `last seen`.

## After every mock exam

- Log each missed question in the mistake log and bump weak topics.
- Append a session log entry with the score.

## At session end

- Append one line to the session log (mode, topics, outcome, next priority).
- Trim session log to the last 10 entries.

## Escalation rule

If a topic shows 3+ misses in a row, suggest a tutor-mode deep dive on it
before continuing to quiz.
