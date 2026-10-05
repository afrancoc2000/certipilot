# GH-300 — Exam-Day Cheat Sheet

<!-- markdownlint-disable MD013 -->

**Exam:** 2026-08-28 · **Pass mark:** 700/1000 · **Scope:** skills measured as of
2026-08-07 · **Read time:** ~8 minutes

Read this once, slowly, before you walk in. Nothing else. No new material.

---

## 1. The five rules that decide most questions

1. **Human accountability never transfers.** Copilot output is a draft: review,
   test, validate. A filter reduces risk; it never certifies correctness,
   security, or license compliance.
2. **Who is the customer?** Individual → Free / Pro / Pro+.
   Organization → Business / Enterprise.
3. **Governance starts at Business** — org policies, content exclusions, audit
   logs, seat management, no-training commitment, conditional IP indemnity.
   **Enterprise** = Business + GitHub Enterprise Cloud + github.com-native
   grounding (knowledge bases).
4. **Where does the work run?** Editor + synchronous → completions / ask /
   Edits / agent mode. GitHub + asynchronous → Copilot coding agent.
5. **Copilot advises, humans gate.** Copilot code review never counts as an
   approval; branch protection and rulesets enforce human review.

> If two options both look right, pick the one that matches the exact wording of
> the stem.

---

## 2. Which mode? (discriminator words)

| Stem phrase | Answer |
| --- | --- |
| "as I type", ghost text, no prompt | Code completions |
| "explain it, I'll apply it myself" | Ask mode |
| "I know which files, change them together" | Copilot Edits |
| "multi-step, it picks files, runs commands, I watch, locally" | Agent mode |
| "assign an issue", "@copilot", background, opens a draft PR | Coding agent |

**Lock:** "locally" + "I'll watch" = agent mode. "Assign an issue" + async +
draft PR = coding agent. The coding agent cannot approve its own PR.

---

## 3. Which context surface?

| Need | Answer |
| --- | --- |
| Always-on project rules for everyone in a repo | Repository custom instructions (`.github/copilot-instructions.md`) |
| Reusable, on-demand task | Prompt file |
| Live external data or tools | MCP server / extension |
| Reusable bundle of repos, files, and notes | Copilot Space |
| Curated internal docs grounding on github.com (Enterprise) | Knowledge base |
| One-off targeted context | `#file`, `#selection`, `#codebase` |

**Lock:** `@` routes expertise (`@github`, `@azure`, `@terminal`, `@vscode`) ·
`#` attaches context · `/` shortcuts a task (`/explain`, `/fix`, `/tests`,
`/doc`, `/new`).

---

## 4. Suggestion lifecycle (be able to draw this)

```text
IDE gathers context (current file, cursor, neighboring tabs, custom
instructions, exclusion policy)
  -> prompt assembled client-side, sent over HTTPS (model does not run locally)
  -> proxy: content exclusion enforced + INPUT filtering (prompt injection,
     toxic language)
  -> hosted model generates
  -> OUTPUT filters: public-code matching (~150 chars), harmful content,
     insecure-pattern suppression, empty/repetitive discard
  -> suggestion shown -> developer accepts or rejects -> telemetry
```

**Retention lock:**

- Business/Enterprise code and prompts: **never used to train models**.
- Code completions: discarded after the suggestion is returned.
- **Copilot Chat: retained** to keep conversation context.
- Individual plans (Free/Pro): may be used for improvement **unless opted out**.
- "Not used for training" ≠ "no telemetry".

---

## 5. Prompt engineering

**Anatomy:** goal + context + expectations + source of truth.

- Zero-shot = no example · One-shot = one example · **Few-shot = several
  examples** (use for internal patterns that exist nowhere in public code).
- Bad answer? Diagnose in this order: **under-specified → over-scoped →
  missing context**.
- Generic output → add few-shot examples or custom instructions.
- Wrong file → attach it explicitly.
- Drifted after many turns → start a new thread and restate constraints.

---

## 6. Productivity plays

```text
Legacy code, no tests   -> explain -> characterization tests FIRST -> refactor small
Need tests              -> happy path -> ask for edge cases, boundaries, errors
Need docs               -> generate from code -> verify against real behavior
Security finding        -> ask for fix + explanation -> validate (CodeQL autofix is separate)
Performance issue       -> measure -> targeted optimization -> re-measure
Deprecated API suggested-> re-prompt with the target version -> verify in docs
```

---

## 7. Privacy and safeguards

**Content exclusion does 4 things:** no inline suggestions in the file · the
file does not inform suggestions elsewhere · it does not inform Chat · it is not
reviewed by Copilot code review.

**The 5 leak paths (memorize):**

1. **Edit mode and Agent mode** of Copilot Chat in VS Code and other editors.
2. **Semantic info supplied by the IDE** — types, hover definitions, build config.
3. **Symlinks.**
4. **Repositories on remote filesystems.**
5. **Not retroactive, not a security boundary** — identical content elsewhere
   can still surface.

**Who configures:** repository administrators, organization owners, enterprise
owners. **Plans:** Business and Enterprise only. github.com and Mobile support
is public preview. Xcode/Eclipse: inline only, no Chat. Azure Data Studio: not
supported. The client sends the repository URL to fetch the policy; those URLs
are not logged.

**IP indemnity is CONDITIONAL** on the duplication-detection / public-code
filter being enabled. Disable it and you forfeit coverage.

**Public code is not free code:** licenses may impose copyleft obligations; no
license = all rights reserved.

**Policy hierarchy:** enterprise owners can enforce enterprise-wide settings
that organization owners **cannot** override.

---

## 8. Numbers worth memorizing

| Item | Value |
| --- | --- |
| Code referencing / public-code match window | ~150 characters |
| Activity report / `last_activity_at` retention | 90 days rolling |
| Copilot audit log retention | 180 days |
| Copilot Memory unused facts | 28 days |
| Content-exclusion propagation to loaded IDEs | up to 30 minutes |

**Domain weights:** D1 responsible use 15-20% · D2 features 25-30% ·
D3 data/architecture 10-15% · D4 prompting 10-15% · D5 productivity 10-15% ·
D6 privacy/safeguards 10-15%.

---

## 9. Your personal trap list (things you actually missed)

- Content exclusion limits — recall the 5 leak paths, not generic controls.
- **Business** is the lowest tier with org policies, exclusions, and audit logs.
  Pro+ is still an individual plan.
- Agent mode vs coding agent — decide by "locally/synchronous" vs
  "assigned issue/async".
- Indemnity requires the public-code filter to be **on**.

---

## Sources

Microsoft Learn study guide:
`https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/gh-300`
GitHub Docs: `https://docs.github.com/en/copilot` (plans, code suggestions, code
referencing, prompt engineering, content exclusion, policies, audit logs,
coding agent, code review).
