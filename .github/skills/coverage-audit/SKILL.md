---
name: coverage-audit
description: "Use when starting or closing a certification session, selecting objectives, checking full exam coverage, or recording independent learning evidence. Audits the official blueprint separately from remediation and scores."
---

# Coverage audit

Use the active exam's `exam.md`, `blueprint.json`, and ignored
`assets/coverage.json`. Resolve the exam before reading its personal files.
Do not use another exam's evidence. The canonical allocation and teaching
contract is [progress tracking](../../instructions/progress-tracking.instructions.md).

## Presentation

Follow [Teacher-first conversation](../../../AGENTS.md#teacher-first-conversation).
Audit output is an internal planning input, not the default chat response.
Retain all required metrics in tools/private records; use them to choose a
helpful next explanation or topic. Do not narrate successful audits, hashes,
IDs, allocation counters, or checkpoint states. Show relevant metrics when the
learner requests progress or diagnostics, and disclose errors or limitations
briefly in plain language without claiming success.

## Commands

From the repository root (Python standard library only):

```powershell
python .github\skills\coverage-audit\scripts\coverage.py audit --exam az-104
python .github\skills\coverage-audit\scripts\coverage.py init --exam az-104
python .github\skills\coverage-audit\scripts\coverage.py audit --exam az-104 --json
python .github\skills\coverage-audit\scripts\coverage.py record --exam az-104 --input <private-batch.json> --expected-sha256 <audit-hash>
python -m unittest discover -s .github\skills\coverage-audit\tests
```

`audit` is read-only; a missing ledger reports all gaps. `init` creates only an
empty ledger and refuses to overwrite. `record` validates before replacing the
ledger, requires the current ledger hash (`sha256` from the last audit or
successful `record --json`), and uses an exclusive writer lock.
Identical IDs are idempotent; conflicting evidence is an error, not an overwrite.
Use `--as-of YYYY-MM-DD` to fix the reporting date for staleness, so the same
ledger and catalog give the same report. It is not a historical snapshot: it
must fall between the latest recorded evidence or source check and today's UTC
date, because the catalog keeps no history to rewind. Use `--stale-days N` to select
the reporting threshold (default 10). Staleness is not deletion of evidence.
Nonzero exit status means stop and resolve the error, not invent a fallback.
All commands reject a future `--as-of` before reading or writing exam data;
timestamps must also not exceed the real clock, even on today's date.

## Start and selection

1. Verify the catalog's official source/revision metadata. An unverified catalog
   cannot justify a completeness claim. The checker checks internal consistency,
   not the semantic completeness of the website-to-catalog mapping.
2. Run `audit`. If absent, initialize personal evidence as unknown; do not infer
   mastery from a broad topic label or a past overall score.
3. Use the next normal allocation from the report. Twenty primary units follow
   `C,C,M,C,R,C,M,C,C,M,C,R,C,M,C,C,M,C,R,C`: coverage, remediation, retention.
   Carry the position across sessions. One unit is a planned concept/diagnostic
   activity, not each hint, retry, or nested teaching turn.
   First honor `next_action: resume_unfinished`: resume the existing unit or
   explicitly defer it, preserving visible debt. Started allocation is not
   completed instruction; report `completed_allocation` separately.
4. For coverage, rotate the unassessed subskills across exam-weighted domains,
   giving every objective a finite turn. After assessment coverage is complete,
   rotate unresolved and least-recently assessed objectives. Never let low-weight
   domains disappear. Use `coverage_queue` in `audit --json`: unvisited gaps
   precede gaps already visited, with weighted domain sequencing. A normal
   coverage unit cannot revisit a subskill while unvisited gaps remain.
5. Explicit narrow-topic requests use `mode: override` with a reason. Mocks use
   `mode: mock`; neither silently consumes the normal allocation cycle.

## Evidence and persistence

Use the schema/examples in [evidence](references/evidence.md). Only genuine,
attributable user answers can be scored. If time/provenance is ambiguous, request
confirmation before recording. Never record a future or fabricated answer.

If an answer is disowned, use the documented append-only `voided_attempts`
batch, backed by the genuine correction reference. Use the post-record report
(re-audit only if it is stale or missing), correct the
session score/progress summary, and re-ask unchanged. Preserve the original
event as voided evidence rather than deleting or regrading it.

Every scored attempt identifies the exact subskills actually evidenced.
Unaided correctness without a novel scenario and demonstrated reasoning does
not establish independent understanding. Post-teaching success is not retention.
Exposure from teaching may be recorded as unscored, never as a learner answer.
Correct letter-only repeats do not erase prior qualified reasoning. New delayed
checks require a recorded fixed study timezone and `retention_source_id` on a
later local calendar day; a session rename does not qualify. Legacy metadata
remains unknown rather than silently establishing retention.

New activities explicitly start; append lifecycle events to interrupt, resume,
defer, and complete them. Link attempts using `unit_id`. Keep the same unit ID
across pauses. Completion needs actual linked learning evidence, but is not the
same as independent assessment. See the shared evidence schema for transitions.

Use the [private checkpoint protocol](references/session.md) for pause/resume.
Checkpoint state preserves pending questions and locked options but is not a
substitute for recording learning evidence.

Persist the ledger first; then update the concise `progress.md` summary with the
last applied attempt ID. If the summary update fails, report it and regenerate
from the ledger rather than re-recording/regrading the attempt. Keep the complete
ledger when trimming the progress session log. Keep batches local; remove only
named temporary batches you created after successful recording.

Do not edit the JSON behind a writer's back. A stale hash requires re-auditing
and merging; a lock requires investigating the active writer. A source revision
mismatch requires explicit migration with a preserved private backup, objective
mapping, and re-assessment for changed scope. Never relabel old evidence with a
new revision merely to make validation pass.

## Atlas-inspired closing brief

Use short checks aligned with what was taught: explain the mechanism, apply it
to a fresh scenario, explain a distractor's failure. Ask one at a time. Reuse
equivalent checks already completed; record an interrupted ticket as incomplete.

Summarize demonstrated reasoning, uncertainty, the specific teaching adjustment,
pending independent checks, and the next protected coverage objective. A
misconception changes instruction, not permission to drop breadth.

Atlas's reported NYC practice connects curriculum-aligned assessment with
teacher action. The blueprint allocation and delayed-transfer rules here are
our extensions, not outcomes established by that pilot. See
[Atlas](https://www.kiddom.co/atlas) and the
[foundation's account](https://usprogram.gatesfoundation.org/news-and-insights/articles/what-it-looks-like-to-design-technology-for-teachers-and-the-difference-it-makes-in-the-classroom).
