# Portable private pause/resume checkpoint

The standard-library [session helper](../scripts/session.py) stores one current
checkpoint in `exams/<exam>/assets/session.json`. It imports the adjacent
[coverage helper](../scripts/coverage.py) by file location, avoiding collisions
with an installed Python `coverage` package. No host SQL database is required.
Host session storage can mirror this state, but cannot replace its evidence,
immutability, or recovery rules.

The checkpoint is private learner data, like `assets/coverage.json`. Never add
it or its input payload to Git. Private keys and rationales are intentionally in
the local checkpoint, not a public/shared customization file. This is output
separation, not encryption or secrecy from the file's owner.

## CLI

Run from the repository, or provide `--root` explicitly:

```powershell
python .github\skills\coverage-audit\scripts\session.py checkpoint --exam az-104 --input C:\private\checkpoint-input.json --expected-sha256 missing
python .github\skills\coverage-audit\scripts\session.py resume --exam az-104 --json
python .github\skills\coverage-audit\scripts\session.py checkpoint --exam az-104 --input C:\private\checkpoint-input.json --expected-sha256 <checkpoint_sha256>
```

All three commands (`checkpoint`, `resume`, `mock-quotas`) accept
`--root <repository>` and `--as-of YYYY-MM-DD`. The default
root is the script's `parents[4]`, independent of the shell's current directory.
Default `--as-of` is today's UTC date; an explicit date fixes the reporting date
for reproducible fixture checks. It cannot precede recorded evidence or
verification dates and never bypasses genuine-turn checks.
All three reject `--as-of` later than today's UTC date before reading or
writing exam data. Response and termination timestamps cannot exceed the real
clock; selecting a reporting date never licenses future learner evidence.

`mock-quotas --exam <exam> --json` is a separate read-only preparation command.
It validates only the blueprint and returns `exam`, `question_count`, and
`domain_quotas` (domain ID to count). Default length is 10; `--question-count`
can request a longer mock, but must allow at least one question per domain.
It uses normalized weight-range midpoints, floor-with-minimum-one allocation,
and exact-fraction deficit/excess adjustment with catalog-order ties, matching
the mock skill. Invalid/unreconciled weight data fails explicitly; reconcile
the outline before calculating. No checkpoint or learner ledger is created.

- `checkpoint` requires an existing, valid exam ledger and blueprint. The
  `--expected-sha256` token compares the destination checkpoint, **not** the
  ledger. Use literal `missing` only for the first save. For later saves, use
  the hash returned by `resume` or the last successful save.
- The payload's `ledger_sha256` separately identifies the ledger snapshot.
  Obtain it from the `sha256` of the current coverage audit or successful
  `record --json` report. Stale ledger inputs cannot be saved.
- A mock checkpoint must reference a ledger unit with `mode: mock`; nonmock
  checkpoints cannot reference mock units. Matching only the allocation kind
  is insufficient. This is checked on both save and resume; mocks never consume
  normal allocation slots. Reconcile legacy mismatches explicitly, not by
  silently relabeling a normal unit.
- `resume` is read-only: it validates the state and ledger, reports the next
  action, and never writes evidence, grades, advances an index, or unpauses.
  Both ordinary and `--json` output exclude private keys, grading criteria, rationales, actual
  answer content, and correctness. Only an unanswered current question is
  returned, with its exact stem and locked option order.
- Saving prints a safe status, never a question. This matters when saving
  because the learner stopped.
- Success is exit code 0; validation, missing-state, lock, concurrency, and
  persistence failures are explicit stderr errors with exit code 2. Never
  claim durable resume when saving fails. An interrupted replace preserves the
  previous checkpoint. An abandoned writer lock must be inspected before any
  deliberate recovery; never automatically delete another writer's lock.

To grade a confirmed answer, the agent reads the **private file directly**.
There is deliberately no `--include-solutions` switch. Do not paste that file
into user-facing summaries or use its private key to manufacture user answers.

## Private question metadata

Each newly prepared question must include `private_metadata` beside its
existing `private_key` and `private_rationale`. It is optional only for backward
compatibility: old checkpoints remain readable without fabricated verification.
Missing metadata is not evidence that an item was verified. Recover verification
before definitive grading; do not silently modify a locked legacy question.
Prepared metadata is never included in the safe save/resume output.
Appending a question without metadata is rejected, even when the existing
checkpoint is legacy. This does not require rewriting metadata-free historical
items or adding fabricated evidence to their immutable history.
Newly prepared items must store their current activity's `unit_id` and target
only that unit's subskills, not merely IDs that exist elsewhere in the catalog.
Item ownership is durable: completed and queued items retain their own unit
when the session changes activities or temporarily returns to an older item.
The current pending item and any new response must belong to `current_unit_id`;
linked ledger attempts must match the item's owner and claim only subskills the
item targets. A voided attempt's claims no longer count, so voiding an
over-claiming attempt lets its replacement be asked. Historical correction
snapshots are not attributed to a new unit, and source-proved history retains
the original activity. Out-of-scope preparation is rejected before presentation.

Legacy items may omit `unit_id`. Resolve ownership from a linked ledger attempt
or correction history; unfinished legacy work retains its recorded current
activity. A caller may explicitly confirm a missing tag only from that known
ownership. Never change/remove an existing tag or invent ownership for completed,
unlinked legacy evidence. Such completed items remain readable without being
credited to the current activity.

```json
{
  "source_id": "original:storage-access-01",
  "domain_id": "d2",
  "topic": "Storage access",
  "subskill_ids": ["<actual catalog subskill ID>"],
  "verification": {
    "claim": "<claim checked against the source>",
    "constraints": "<decisive conditions in the question>",
    "url": "https://learn.microsoft.com/azure/storage/common/storage-sas-overview",
    "checked_at": "2026-10-05",
    "rationale": "<source-supported explanation>"
  }
}
```

When metadata is present, every displayed field is required and extra fields
are rejected. `source_id` is a nonempty bank/item locator or explicit original
item ID, not necessarily a catalog source ID. Domain and subskill IDs must exist
in the active catalog; all targets must belong to that domain. A verification
snapshot requires nonempty claim, constraints and rationale, an HTTPS URL on
`learn.microsoft.com` or `docs.github.com`, and a valid check date no later than
the audit date. For AI-500 only, its declared official framework documentation
is also accepted on these exact hosts: `docs.langchain.com`,
`python.langchain.com`, `js.langchain.com`, `langchain-ai.github.io`,
`huggingface.co`, and `modelcontextprotocol.io`. This allowance does not apply
to other exams or arbitrary subdomains. On `huggingface.co`, only
`/docs/transformers` and its descendants qualify, not user model cards,
Spaces, other framework docs, or paths that escape that subtree after decoding
and normalization. URLs containing credentials are
rejected for every authority. The helper checks structure and the exam-scoped
authority allowlist, not the truth of source claims.
Use `private_rationale` for the full per-option teaching explanation.

Question number is derived from the item's one-based position in `items`; catalog revision comes
from the checkpoint's `blueprint_revision`. Do not duplicate them or add separate
public/private manifest fields. No answer or verification metadata goes in the
public question view. Source locators and topic labels are also private in safe
CLI output, because they can cue a solution.

Ordinary save/resume cannot add, remove, or change metadata on an existing item.
A disowned-answer replacement preserves it exactly along with the unchanged
question. An invalid-item replacement may update verification/source/scope as
needed for its corrected question, but cannot drop existing metadata. Its
history entry preserves the complete original metadata; legacy history entries
without metadata remain valid. Validate corrected metadata against the active
catalog, never rewrite the earlier history.

Previously saved AI-500 Hugging Face snapshots outside the Transformers subtree
remain readable for recovery, not trusted verification. Resume reports
`replace_unverified_item` and `source_recovery_question_indices`/`source_recovery_item_ids`,
without exposing the source or a pending question. Such items cannot acquire
answers, grading, or review, and the checkpoint cannot advance while they remain.
Pause and unchanged reconciliation remain available. A validated replacement
may move `question_index` and activity to that legacy item's original item index even while
other legacy sources remain; ordinary advancement is still blocked.
Use the existing
source-backed invalid-item replacement protocol: preserve the exact original
snapshot in history, document the verification defect, and prepare a corrected
question with current official verification. Journal-only invalidation applies
only to uncommitted items; ledger-backed answers require the normal attributable
void and score reconciliation. Never rewrite historical scores or metadata
merely to satisfy the new source rule. New items and replacements still require
Transformers documentation; immutable history may retain the previously accepted
URL without using it for new grading.

## Private answer-position deck

New question-bearing sessions (quizzes, mocks, and sessions with free-response
checks) must save the top-level `answer_position_deck` before authoring their
first item; only legacy checkpoints may lack it. Generate the sequence with an actual random-number
tool, not intuition. A structural check cannot prove randomness.

The object has exactly three fields:

- `kind`: `planned` for mocks and fixed-length quizzes, or `open_ended` for
  sessions that replenish 12-position batches. Planned decks cannot grow, so a
  planned length counts every four-option single-answer item the session will
  prepare; a session that may prepare only free-response items uses
  `open_ended`. Mocks are choice-only: closing prompts after a mock start a new
  nonmock session once the mock is complete.
- `positions`: a nonempty array of A/B/C/D strings. Planned decks have the full
  intended length, balanced so counts differ by at most one. Open-ended decks
  start with exactly 12 positions, three of each letter; each appended batch
  has the same balance. No three consecutive positions may match, including
  across batch boundaries.
- `cursor`: an integer equal to the number of prepared items that take a
  position (see below), between zero and the position-array length. It points
  to the next position to assign, not the question to display.
  `question_index` still selects the current question.

First save the deck with empty `items`, `cursor: 0`, `question_index: 0`, and
`next_action: resume_phase`. This is enforced on first save, session rollover,
and when an empty legacy checkpoint first acquires a deck. Combining a new deck
and prepared items in the same write is rejected; the question manifest must
arrive in a subsequent save. Omitting the deck does not grant an exemption:
all new question-bearing sessions must establish it before saving questions.
An empty deckless checkpoint may still save a teaching/planning phase, but
cannot append questions until it saves its deck-only preparation checkpoint.
Before displaying a newly authored item, append
it and, when it takes a position, advance the cursor in the same checkpoint
write. A planned mock saves its complete item array in one update after the
empty preparation checkpoint, with the cursor at the end of the deck; the
manifest is then immutable. Planned nonmock quizzes may author gradually.

Only four-option single-answer items (option keys exactly A/B/C/D and one
private key) take a position: the Nth such item, counted in `items` order, must
have its private key at `positions[N]`. Free-response prompts and multi-select
or other-option-count questions take no position and retain their independently
verified key. Replacement versions/history share the original item's position.
Answering, reviewing, pausing, resuming, or replacing an item never consumes an
extra position. No item may be assigned beyond the saved sequence.

Ordinary updates cannot change or remove the kind or any saved position.
Each update may journal only one new response, for the question at the
previously saved `question_index`. Save the response between genuine turns;
do not populate multiple prepared items or answer an unsaved future cursor.
The same write may advance the question index after that response is saved.
Updates without a new response (preparation, review, reconciliation, pause,
or recovery) remain valid; existing populated legacy checkpoints remain readable.
An open-ended deck may append exactly one 12-position batch only after the
previously saved cursor reached the sequence end; never generate several
batches ahead of time or replace the consumed prefix. Validate balance and
boundary triples before saving. A paused update cannot generate a batch.
Planned decks cannot grow.

Read the private file directly to recover the deck. Save/resume CLI output
never exposes this object, future positions, or the assignment cursor.
Legacy checkpoints without it remain readable and keep their existing item
locks. Only an already existing, populated checkpoint in the same session may
continue deckless response/review updates and append legacy items; that
compatibility does not extend to first saves, empty checkpoints, or rollover.
They cannot gain a retrospectively reconstructed deck once they contain
questions. Missing future positions are a continuity limitation, not permission
to silently regenerate them. Finish the legacy run before starting a new
deck-backed session. An empty legacy preparation checkpoint can acquire a deck.

## Schema version 1

Option text must remain neutral. The validator rejects presentation markup
(emphasis, code spans, links, HTML tags, and block markers), not every technical
punctuation character. Plain identifiers such as `Standard_D2s_v5`, glob patterns
such as `*.json`, comparisons such as `x < 5`, and generic types such as
`List<string>` are valid and round-trip unchanged. Agents must still present
all choices neutrally; this check is not a full Markdown renderer.

All fields below are required. The backward-compatible optional additions are
top-level `termination` and `answer_position_deck`, and per-item `history`,
`private_metadata`, `kind`, `private_grading_criteria` and `unit_id`, plus `private_planning`
required only in planner mode,
described in this reference. Unknown fields
fail validation. Replace IDs, hash, and content with the actual prepared session.

```json
{
  "schema_version": 1,
  "exam": "az-104",
  "blueprint_revision": "<exact catalog revision>",
  "session_id": "<stable session ID>",
  "mode": "quiz",
  "phase": "warm_up",
  "paused": true,
  "current_unit_id": "<existing ledger unit ID>",
  "allocation_category": "coverage",
  "question_index": 0,
  "items": [
    {
      "id": "<immutable question ID>",
      "unit_id": "<owning study unit ID>",
      "stem": "<exact presented stem>",
      "options": [
        {"key": "A", "text": "First neutral option"},
        {"key": "B", "text": "Second neutral option"}
      ],
      "answer_order_locked": true,
      "private_key": ["B"],
      "private_rationale": "<verified rationale and source references>",
      "response": null,
      "attempt_id": null,
      "grading": "pending",
      "review": "pending"
    }
  ],
  "ledger_sha256": "<64 lowercase hex characters>",
  "applied_attempt_ids": [],
  "applied_void_ids": [],
  "pending_check_ids": [],
  "next_action": "reask_pending"
}
```

- `mode`: `quiz`, `tutor`, `follow_plan`, `mock`, or `planner`.
- `phase`: a nonempty workflow phase, such as `warm_up`, `coverage`,
  `remediation`, `mixed_quiz`, `teaching`, or `review`. `aborted_review` requires
  genuine end-and-review intent, not a pause. `complete` requires no outstanding
  answered-question review; unanswered items remain unassessed after explicit
  termination. It is **not** proof of ledger activity completion or mastery.
- `paused`: a genuine stop/pause freezes phase, unit, question index, and
  manifest. Recording the already received genuine answer before the initial
  pause is allowed; generating an additional question is not. To continue,
  explicitly resume (`paused: false`) after the learner requests it.
- `current_unit_id` and `allocation_category`: refer to an existing unit of
  this session with matching `kind` and a known audited lifecycle. New units
  begin with `lifecycle: "started"`; effective status comes from subsequent
  ledger `unit_events`, never the checkpoint's phase. Both fields can be
  `null` for a pre-activity phase with no questions. Legacy unknown-lifecycle
  units need explicit ledger-event reconciliation, not a fabricated start or completion.
  New responses must occur during an active unit at their recorded timestamp,
  using the same lifecycle rule as ledger recording. Answers after interruption,
  deferral, or completion are rejected until a valid restart where supported.
  A historical answer received before interruption may still be journaled and
  reconciled afterwards; an answer exactly at a supported completion timestamp
  remains valid. This check does not invalidate already saved response history.
- `question_index`: zero-based current item, or `0` when `items` is empty.
  Empty items support pausing tutor/planning phases without inventing a quiz.
- `items`: the ordered, uniquely identified, pre-generated question list;
  `question_index` selects the current item. Existing item IDs, stems, options, private
  keys, rationales, optional private metadata, and item order are immutable on ordinary updates. Nonmock
  sessions can append prepared items when advancing; the initial mock manifest
  is locked. First saves and new-session rollovers of question-bearing sessions
  are deck-only (see the deck section); appended items must be unanswered:
  persist the prepared question before presenting it, then save
  its actual response in a subsequent update. Existing answered legacy
  checkpoints remain readable; never use first-save import as a substitute for
  preparation. Never regenerate or randomize it on resume. Confirmed ledger voids
  or journal-only invalidations permit only history-preserving, same-index
  recovery as documented below. Mock grading
  remains deferred until every item is answered, except explicit end-and-review
  of genuine answered items. Recovery preserves already recorded grades without
  grading an unanswered replacement.
- Per-item `unit_id`: the owning activity in this same session. Required when
  appending a new prepared item; it must equal the checkpoint's current unit at
  preparation. It remains locked through grading, review, and correction.
  Legacy tag confirmation needs existing ownership evidence, not a guess.
  To recover an older item, explicitly return to its original unit/category;
  restart an interrupted unit in the ledger before accepting a new answer.
  Later prepared items keep their own tags and item indexes while recovery is pending.
- `options`: objects containing only an uppercase single-letter `key` and a
  nonempty plain `text` string. At least two options; keys are unique.
  These choice requirements do not apply to free-response items below.
  Mock items require exactly four options with the A/B/C/D key set, including
  historical versions. Four-option single-answer items with a position deck
  must match their assigned position (see the private answer-position deck);
  multi-select keeps its verified multi-key answer.
  Invalid legacy mock manifests now fail validation explicitly: do not silently
  pad options or regenerate a live question; reconcile defects through the
  correction protocol before continuing.
  The helper rejects common presentation markup and extra correctness fields.
  Plain technical text beginning with square brackets (for example a JSON
  array or a C# attribute) is allowed; Markdown links and images remain rejected.
  The author must still ensure semantic neutrality, no visual correctness
  cues, plausible distractors, and the required question format. Mechanical
  validation is not a model-level guarantee of question quality.
- `private_key`: a nonempty unique array of option keys (supports multi-select).
  `private_rationale`: verified grading explanation/source references.
  Changed or disputed items must be handled as invalid items, not silently
  rewritten under the original question ID.
- `response`: `null`, or exactly
  `{"response_ref": "<genuine turn reference>", "timestamp": "<ISO timestamp with timezone>", "genuine_confirmed": true, "text": "<exact actual user answer>", "flags": []}`.
  New answered records require actual answer text and flags in the private
  checkpoint as well as provenance, so inaccessible host session references do
  not destroy portable recovery. Allowed flags are `flagged_for_review`,
  `uncertain`, and `time_expired`; record only supported flags, without repeats.
  The agent must verify real-turn provenance and timestamp order first. Neither
  answer text nor flags are shown in CLI summaries. The helper rejects missing,
  future, reused, or out-of-order references, but cannot independently prove
  that a real human authored a turn.
  Legacy references-only responses remain readable and may be carried forward
  unchanged; pending grading reports `recover_response_text` until actual text
  is recovered from the genuine source. Enrichment can add text/flags without
  changing provenance. If the source is unavailable, disclose the safe-grading
  block; never infer an answer from the key, score, or surrounding history.
- `attempt_id`: `null` until a genuine response is recorded; then reserve a
  unique stable ledger attempt ID **before** attempting the ledger write.
  That is how a successful ledger write can be found after an interruption.
- `grading`: `pending` for ordinary ungraded items, `deferred` for ungraded
  mock items, or `applied` once an exact matching ledger attempt exists and is
  listed in `applied_attempt_ids`. Unanswered items cannot be applied.
- `review`: `pending` or `complete`; complete requires applied grading.
- Applied attempt/void IDs refer to existing records in this same session.
  Markers are append-only. `pending_check_ids` references ledger diagnostic
  checks; the checkpoint cannot create or complete them.

Existing responses, including text and flags, and reserved attempt IDs cannot
be overwritten, including after correction. New responses following a void use
new question/attempt IDs and retain the immutable original in history. A
different session ID cannot replace active unfinished state; normal rollover
is allowed only after the old session is explicitly complete. Missing/corrupt
state requires user-assisted recovery; there is no silent reset flag.

## Free-response items

Tutor transfer checks and closing mechanism diagnostics may use
`kind: "free_response"` outside mocks. Missing `kind` means the legacy `choice`
format; explicit `kind: "choice"` is equivalent. Mocks remain choice-only.

Keep the common item envelope and genuine response journal unchanged:

```json
{
  "kind": "free_response",
  "options": [],
  "private_key": [],
  "answer_order_locked": true,
  "private_grading_criteria": [
    "<verified required causal explanation>",
    "<verified application to the changed constraint>"
  ]
}
```

This is a fragment: the item still requires its exact ID/stem, private rationale,
verification metadata, and response/attempt/grading/review fields. Criteria are
a nonempty list of unique nonempty strings. Choices/keys on free-response items,
criteria on choice items, and unknown kinds are rejected. The validator checks
structure, not the truth or fulfillment of criteria; grading remains the agent's
source-grounded evaluation of genuine input.

First save the empty position deck, then the unanswered prepared prompt. A
free-response item takes no answer position, so it leaves the deck cursor
unchanged; neither do its history or reasks. Normal pause,
response timestamps, ledger reconciliation, review and completion rules apply.
Safe resume returns only `id`, `kind: free_response`, and the exact `stem` for a
pending prompt; plain resume prints no invented options. It never exposes the
criteria, rationale, source snapshot or response text.

Kind and criteria are immutable on ordinary updates. A disowned answer reasks
the exact stem and original criteria with append-only history. A source-backed
invalid-item correction may change the stem or grading criteria under a new ID,
preserving the original kind, empty options/key, item index, and exact historical item.
This supports prepared-only, journal-only and ledger-backed corrections without
fabricating a score or rewriting evidence.

## Planner proposals

Standalone sprint planning uses `mode: planner` with `phase: planning` (or
`complete` on close), `items: []`, `question_index: 0`, and both current unit
and allocation category `null`. Applied attempt/void lists remain empty.
No answer-position deck or question can be added to a planner checkpoint.
The existing catalog, ledger hash, concurrency and session-identity checks
still apply, but planning alone records no learning evidence or delivered unit.

Planner mode requires this top-level private object, rejected in other modes:

```json
{
  "private_planning": {
    "plan_filename": "2026-10-20-sprint.md",
    "proposal": "<complete dated draft and proposed changes, including pending choices>"
  }
}
```

The filename is a local `.md` basename (letters/digits, underscores, dots and
hyphens, beginning with a letter/digit), not a filesystem path. It refers to
the active exam's `assets/study-plans/` only; the helper never writes that file.
`proposal` must be nonempty text. Additional fields such as inferred approval
are rejected. Resume returns `resume_phase`; read the private file directly
to recover proposed changes. Neither ordinary nor JSON CLI output exposes
the filename/proposal. Proposal edits require an active or explicitly resumed
session; an already paused checkpoint cannot acquire changed proposals while
remaining paused. Completion uses `next_action: session_complete`.

Persisting, resuming or completing planning does not grant permission to apply
the draft. Follow the sprint skill's confirmation rules separately; never
interpret checkpoint state as learner approval.

## Next actions and pause behavior

### Journal-only invalid-item replacement

If the defective item's reserved attempt ID is absent from the ledger (or it
has no response/attempt ID yet), do not manufacture an attempt or ledger void.
Use an alternative history entry with exactly `item` and `invalidation`:

```json
{
  "invalidation": {
    "id": "<unique private correction ID>",
    "reason_kind": "invalid_item",
    "reason": "<factual defect>",
    "source_ref": "<defect evidence reference>",
    "timestamp": "<actual timezone-bearing correction time>"
  },
  "item": "<complete original question object, excluding its history>"
}
```

The `item` value above stands for the actual original JSON object, including
its response, reserved attempt ID, metadata and private key if present.
Append this entry to prior immutable history, version the question ID, and
correct its stem/options. Preserve the original option keys, correct positions,
existing metadata and deck cursor. Save the replacement unanswered before
receiving another genuine answer, at the original index and unit, while
continuing (not in a paused update). A new answer gets a new attempt ID.

The invalidation requires factual nonempty reason/source evidence, actual
nonfuture time no earlier than the original response, and `invalid_item`
reason kind. This is an agent-discovered defect, not a fabricated learner
correction. Journal IDs are unique across checkpoint history and cannot collide
with ledger void IDs. No applied attempt/void markers are added for this
transition. Once a real ledger attempt exists, use the ledger void path instead.
An invalidated original reserved attempt cannot subsequently be scored:
resume fails explicitly if it appears in the ledger, requiring reconciliation.

Journal-only history survives save/resume and subsequent replacement versions,
but is excluded from safe CLI output, like private answers. It does not credit
or penalize learning or fabricate activity completion. Existing ledger-backed
history entries retain their original `void_id` schema and validation.

The helper validates `next_action` against question state:

| Action | Meaning |
| --- | --- |
| `reask_pending` | After an explicit resume request, present the exact unanswered stem (and options for a choice item), then stop. Never expose private grading criteria. |
| `grade_recorded` | Verify the referenced genuine answer, then grade once and record its reserved attempt ID. Do not re-ask it. |
| `continue_mock` | An answer is saved but other mock items are unanswered. On continuation, advance to the next already locked item without grading or revealing solutions. |
| `grade_deferred` | Grade genuine answered items only: the full answered mock, or its answered subset after explicit end-and-review. Verify provenance and existing attempt IDs first. |
| `review_recorded` | The grade is already in the ledger. Resume review without regrading or appending another attempt. |
| `advance_after_review` | Review is done; continue the workflow only when the learner resumes. |
| `resume_phase` | Continue the saved non-question activity phase; do not invent an exit ticket. |
| `finish_aborted_review` | The explicitly ended mock's answered subset has been reviewed; unanswered items remain unassessed. |
| `session_complete` | No outstanding question review; consult the ledger for actual activity completion. |

These are instructions for a subsequent agent action, not operations executed
by `resume`. A paused checkpoint stays paused on disk. Never ask an exit ticket
or advance phases when the learner says stop.

## Explicitly ending a mock for partial review

Pause/stop alone freezes state and never enables grading. If the learner's intent
is ambiguous, clarify pause versus end-and-review instead of treating "stop" as
permission to grade.

For a genuine explicit end-and-review request, retain the whole deck, cursor,
responses, and locked order. Set `phase: "aborted_review"`, `paused: false`,
and add:

```json
{
  "termination": {
    "intent": "end_and_review",
    "response_ref": "<actual user termination turn>",
    "timestamp": "<ISO timestamp with timezone>",
    "genuine_confirmed": true,
    "text": "<actual user request to end and review>",
    "flags": []
  }
}
```

Termination is immutable and cannot predate any saved genuine answer. No new
answers are accepted afterward. Only genuine answered items can be assessed;
their next actions are `grade_deferred`, then `review_recorded`, then
`finish_aborted_review`. Zero answered items means zero assessments and direct
`finish_aborted_review`. Unanswered items retain null response/attempt ID,
deferred grading, and pending review even when the session becomes `complete`.

Safe summaries include `answered_count`, `unanswered_count`, and
`termination_recorded`, never termination wording or response text. Reconcile
already committed answered attempts before grading the remaining answered
subset. Never count unanswered items as learner mistakes or call a partial
review a completed mock score.

## Ledger reconciliation and corrections

Safe output can override the stored next action:

1. `reconcile_ledger`: the ledger hash changed, an answered reserved attempt
   was committed without its applied marker, or a relevant void is not yet
   acknowledged. Output includes only `committed_attempt_ids` and
   `committed_void_ids`, never their correctness. An attempt matches only if
   session, genuine response reference, and timestamp match exactly; a
   conflicting ID is an error, not permission to merge someone else's answer.
2. Inspect the actual ledger and private checkpoint. Preserve confirmed
   responses and keys. Carry forward the existing attempt/void IDs; never
   replay scoring or append duplicate evidence. Update the ledger hash,
   applied markers, and item grading flags in a new hash-guarded checkpoint.
   Re-audit pending checks and activity lifecycle before continuing.
3. `replace_invalid_item`: a genuine ledger void has
   `reason_kind: "invalid_item"`. Do not re-ask the defective item unchanged.
   Prepare a corrected replacement under a new question ID/version, with changed
   stem or options, at the same item index, retaining the same private answer key
   and ordered option letters. Reverify its rationale and preserve the original
   question/answer in immutable history.
4. `reask_disowned`: a genuine ledger void has
   `reason_kind: "disowned_answer"` (also the legacy void default). Resume the
   exact original stem, options, answer order, and private key. The safe summary
   supplies that question and its recovery item index. Preserve the original response
   in immutable history; the later genuine answer gets a new question/attempt ID.
5. `recover_response_text`: pending grading needs a legacy answer's actual text.
   Recover only from an accessible genuine source, never the solution.
6. `resolve_voided_partial_review`: the mock already has explicit end-and-review
   intent. Preserve and reconcile the voided answer through the same immutable
   history mechanism, but never ask another question or accept another answer.
   The replacement stays unanswered/unassessed; review only the remaining
   genuine nonvoid answers.

Known genuine ledger voids directly identify actions 3 or 4 even when hash and
markers need reconciliation. An unambiguous genuine void needs no redundant
confirmation. Safe output includes `reconciliation_needed`,
`recovery_question_index`, `recovery_item_id`, and `recovery_void_id`; the actual
recovery write remains hash-guarded. Its `question_index` can return to the
affected item, never move the other questions or lose their genuine answers.

For either correction, append to the active item's optional `history` array:
an object with `void_id` (the reconciled ledger void ID) and `item` (an exact
snapshot of the previously persisted item, excluding only its own `history`).
That snapshot retains all original ID, stem/options/order, private key/rationale,
response text/flags/provenance, attempt ID, grading, and review fields.
Further corrections append snapshots, never rewrite history. Question IDs,
response references, and attempt IDs remain unique across all versions.

Then replace the active item with the new ID/version at that same item index. Preserve
the option-letter sequence and locked answer key/position(s). For disowned
answers preserve all question content; for invalid items correct the content.
Include the original attempt and void in applied markers and use the latest
ledger hash. Persist the new version unanswered first: null response/attempt ID,
pending grading (deferred for mocks), and pending review. Never create a
replacement and its supposed answer together. Only a later actual genuine
response after the confirmed void and last genuine response can populate it.
Its new reserved attempt ID prevents replay; old voided evidence remains voided.

The checkpoint is never the evidence ledger and cannot establish completion.
New units must be recorded with `lifecycle: "started"`; lifecycle changes use
append-only `unit_events` in the [evidence contract](evidence.md), not rewritten
study units. Pause may record an `interrupted` lifecycle event through the
coverage helper. Resume retains the original unit ID and allocation category;
it does not consume another coverage slot. A saved question or started
activity proves neither assessment nor delivered learning.

The coverage audit's `next_action: "resume_unfinished"` and `unfinished_units`
take precedence over allocating a new normal unit. Inspect the checkpoint's
ledger-derived `unit_lifecycle`: for an interrupted/deferred unit, append the
appropriate `started` event through the coverage helper before recording new
answers, then reconcile the checkpoint hash. A completed checkpoint phase does
not turn a started unit into a completed unit; only the validated ledger
evidence and lifecycle events can do that. Study timezone and delayed-check
eligibility remain solely in the evidence contract, not duplicated checkpoint
fields.

Ledger and checkpoint writes are separate atomic writes, not a multi-file
transaction. If a ledger write succeeds and checkpoint replacement fails,
read-only resume detects the changed ledger and reserved attempt IDs. If the
ledger changes during a save/read, an explicit error requires a fresh resume.
Unrelated ledger changes also require reconciliation; no optimistic guessing.

## Verification boundary

[Checkpoint tests](../tests/test_session.py) exercise unanswered/answered pauses,
deferred and explicitly ended partial mocks, phase freezes, exact locked options,
stale hashes, wrong exams/revisions, missing/corrupt state, private genuine
answer text/flags, legacy recovery blocking, interrupted atomic replacement,
invalid-item/disowned-answer history, same-index mock correction, and ledger-write
reconciliation. They do not establish
that an agent truly checked a user turn, authored an unambiguous question, or
respected a stop request outside this helper.
