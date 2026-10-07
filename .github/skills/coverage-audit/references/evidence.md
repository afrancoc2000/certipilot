# Coverage evidence schema

All JSON uses `schema_version: 1`. Shared catalogs live beside `exam.md`;
personal ledgers and input batches stay in ignored exam assets or session storage.
Audit, init, and record output must pair metrics with the hash of the same
ledger snapshot. Writes capture their committed digest under the writer lock;
a change detected before output fails explicitly. A record can have committed
even when this final consistency check fails: re-audit and retry identical IDs,
not new evidence or an overwrite of the concurrent writer's work.

## Catalog

`blueprint.json` contains `exam`, `revision`, `verified`, `verification_note`,
`sources`, and `domains`. Sources carry `id`, HTTPS `url`, ISO `checked_at`, and
`published_revision` (explicitly "not stated" if unavailable).

Each domain has `id`, `title`, `weight_min`, `weight_max`, and `objectives`.
Each lowest-level official objective has `id`, a paraphrased `title`,
`source_id`, a traceable `source_locator`, and required `subskills`. Each subskill
has a unique `id`, `title`, and boolean `derived` distinguishing local
decomposition from the published objective. Broader objectives need all their
named operations/technologies represented, not one representative question.

IDs must be stable within the exam. A domain visit never marks all objectives
covered. Source verification is a human/agent reconciliation step; the local
checker does not fetch or reinterpret source websites.

## Personal ledger and record batch

The ledger has `exam`, `blueprint_revision`, `attempts`, `study_units`,
`pending_checks`, optional `voided_attempts` and `unit_events`, and optional
`study_timezone`. A record batch includes any
nonempty selection of those arrays, without the ledger metadata.
Example only; substitute actual evidence,
catalog IDs, dates, and provenance rather than copying the fictional values:

```json
{
  "attempts": [{
    "id": "session-example-q1",
    "session_id": "session-example",
    "timestamp": "2026-10-04T12:00:00-05:00",
    "blueprint_revision": "example-revision",
    "subskill_ids": ["d1-o01-s01"],
    "result": "partial",
    "assistance": "unaided",
    "context": "cold",
    "response_ref": "local-session:<actual-session-id>#turn-<actual-turn>",
    "genuine_confirmed": true,
    "reasoning_demonstrated": false,
    "novel": true,
    "diagnosis": "application",
    "action": "Contrast the two scope constraints before another novel scenario."
  }],
  "study_units": [{
    "id": "session-example-unit1",
    "session_id": "session-example",
    "timestamp": "2026-10-04T11:59:00-05:00",
    "kind": "coverage",
    "mode": "normal",
    "lifecycle": "started",
    "subskill_ids": ["d1-o01-s01"]
  }],
  "pending_checks": [{
    "id": "session-example-q1-cold",
    "subskill_id": "d1-o01-s01",
    "after_attempt_id": "session-example-q1",
    "kind": "cold",
    "status": "pending",
    "evidence_attempt_id": null
  }]
}
```

Attempt enums:

- `result`: correct, partial, incorrect, unscored.
- `assistance`: unaided, assisted, unknown.
- `context`: cold, post_teaching, delayed_transfer, mock, teaching, historical.
- `diagnosis`: none, mechanism, application, prerequisite, reading, uncertain.

Teaching uses `unscored`. An uncertain diagnosis does not invent a weakness.
`response_ref` and confirmed provenance are mandatory for scored answers.
Each scored `response_ref` belongs to exactly one attempt ID across the ledger,
including voided attempts. Put genuinely evidenced multiple subskills in that
one attempt's `subskill_ids`; do not duplicate a response to increase coverage.
Replaying the identical attempt ID and content is still idempotent. Unscored
teaching records may share a source reference and do not create scored credit.
When one genuine turn contains several separately numbered answers, reference
the actual turn and each verified item (for example `#turn-13&item=3`).
That identifies distinct answer content, unlike adding attempt IDs to make a
shared answer appear unique. Historical summary references should likewise
locate the existing supporting item or exact excerpt without claiming raw-turn
provenance that was not recovered.
When `unit_id` is present, the attempt must share that activity's `session_id`
and target only its declared subskills. Unlinked historical attempts remain
supported; do not attach them to a different session's unit to manufacture
activity completion. Invalid existing links require explicit source-backed
repair, not a silent session-ID rewrite.
After voiding, a replacement scored attempt needs a new genuine response
reference; never reuse the disowned/invalid answer as a fresh learner turn.
Legacy imports that cite only a shared session summary may fail this check.
That signals ambiguous attribution, not proof of duplicated learner answers.
Preserve the original records and reconcile against actual source turns/items
before recording more evidence; never invent reference suffixes merely to
make the validator pass or silently delete/regrade historical answers.
Historical records with uncertain hint use remain `assistance: unknown`;
historical selected-option correctness alone does not show reasoning.
Never rewrite old grades to fit the new framework.

`study_units` record actual begun primary activities at their start timestamp,
not hypothetical future plans or every follow-up question. Preserve chronological
order. A normal unit must match the next cycle slot. Only coverage may substitute
for unavailable retention or remediation, using reason `no-retention-evidence`
or `no-remediation-needed`; the checker verifies the available preceding evidence.
Overrides and mocks require an explicit scope `reason`. Follow-ups remain part
of the original activity and must not be relabeled as new breadth.
The checker rejects repeating visited coverage while unvisited, unassessed
subskills remain. Use the audit's `coverage_queue` instead of guessing the next
objective from the weak-topic list. Every target must be unassessed while
unassessed scope remains, and every target must also be unvisited while
unvisited-unassessed scope remains. Multi-subskill units are allowed only when
all targets qualify; one new target cannot license repeated familiar targets.
Visits come from attributable attempts on the exact evidenced subskills,
including unscored teaching and attempts without a linked unit. Planned targets,
unanswered scope, and evidence-less starts are not visits. Partial or aborted
mocks visit only the subskills actually delivered. The current queue counts only
surviving attempts; first-pass validation at each activity start uses preceding
attempts that were not yet voided at that boundary. A later void does not
retroactively invalidate a historically eligible selection. Allocation remains
based on begun normal units, separately from delivered visits and completion.

### Rolling session breadth

The audit's `session_breadth` reports the latest three distinct `session_id`
values across all modes (normal work, mocks, explicit overrides, and recorded
historical learning). Order sessions by their latest attempt, original
activity-start, or `unit_events` entry with `status: started` timestamp, oldest
first within the window; ties use session ID alphabetically. A resume event maps
its `unit_id` to the original unit's `session_id`; resuming updates that session's
position, not its count. Completed, interrupted, and deferred events are not
starts and do not update this window.
Timestamp ordering and least-recently assessed queue tiebreaks compare parsed
instants, not ISO text spelling. Mixed offsets are supported; equal instants
retain the documented session-ID/catalog-order tiebreaks. Preserve the original
timestamp strings in evidence and reports.

Starts and original attempts establish session membership, including sessions
whose attempts are later voided. Voids do not create new study sessions or
backfill older sessions into the window. A start without evidence still counts
as a session but earns no domain credit. An event-only resume likewise earns no
domain credit and consumes no additional allocation. Unrecorded chats cannot be
inferred.

Only surviving nonvoid attempts earn domain credit. Teaching counts as exposure;
correctness, independence, and mastery remain separate metrics. Voiding the only
evidence for a domain reopens its breadth gap. Ledger attempts may be unlinked
to a unit; their explicit session and subskill IDs still establish attribution.

Output includes `window_size: 3`, `window_complete`, ordered `session_ids`,
per-session `sessions` (`session_id`, `last_activity`, `domain_ids`),
`touched_domain_ids`, and `missing_domain_ids`. Domain lists follow catalog
order. With fewer than three recorded sessions, `window_complete` is false;
report the partial window and its gaps rather than claiming three-session
coverage. The text report also lists the window and missing domains. This
read-only report never changes allocation order or counts exposure as mastery.

### Activity lifecycle and interrupted coverage

New units must explicitly contain `lifecycle: started`. Legacy units without it
remain completion-unknown. Append `unit_events`, each containing `id`, `unit_id`,
`status`, timezone-bearing `timestamp`, and a factual `reason`:

- Started activities may become `completed`, `interrupted`, or `deferred`.
- Resume interrupted/deferred activities with a `started` event for the SAME
  unit ID; do not append another unit or consume another allocation slot.
- An interrupted activity can be explicitly deferred to keep its debt visible.
- Legacy completion-unknown units may be explicitly resumed, deferred, or
  completed with attributable evidence; do not invent past completion.

Attempts belonging to an activity include its `unit_id`. Completion requires
linked, nonvoid learning evidence for every targeted subskill, preceding the
completion event. Unscored teaching can establish delivered instruction, but
cannot establish independent assessment or understanding.

If a later void removes the evidence needed for any targeted subskill, the
completed activity becomes effectively `interrupted` and returns to unfinished
debt. Its original completion event remains unchanged. Other surviving linked
evidence can preserve completion, including unscored teaching. Resume with a
`started` event for the same unit ID, or explicitly defer it; after new evidence,
append a new completion event. Do not create another allocation unit to repair
the old one. Audits and checkpoint lifecycle use this same effective state.
Work begun before the void remains historically valid; new work after the void
must first reconcile the reopened activity.

The audit reports `normal_units`/`actual_allocation` as STARTED work and
`completed_normal_units`/`completed_allocation` separately. Never claim the
started 12/5/3 cycle proves delivery of 12/5/3 completed activities.
`unfinished_units` preserves debt and `completion_unknown_units` preserves
legacy uncertainty. If `next_action` is `resume_unfinished`, resume or explicitly
defer that work before starting another normal activity. A deferred item remains
debt; it is not completion. Resume data is described in [session](session.md).

### Later-day retention

Set `study_timezone` once through a record batch, using the learner's actual
fixed UTC offset, for example `{"study_timezone": "UTC-05:00"}`. This format
deliberately does not infer daylight-saving rules or use an optional timezone
database. Record the study convention explicitly; changes require deliberate
migration rather than silently reinterpreting historical local days.

A new `delayed_transfer` attempt must include `retention_source_id` referencing
the earlier learning attempt, target its subskills, use a novel unaided scenario,
and occur on a later calendar day in that recorded timezone. A chat restart
does not qualify; the same chat on a later day can. Both chronology and local
day are checked. For same-day independent follow-up use `cold` as appropriate,
or `post_teaching` after instruction; do not relabel it delayed.

Legacy delayed attempts lacking timezone/source data are preserved but appear
in `retention_ineligible_attempts` and do not establish delayed retention.
Voided source evidence cannot establish retention. Do not manufacture missing
source IDs or assistance metadata to improve a coverage percentage.

Checks become completed by sending the same check ID with `status: completed`
and a real `evidence_attempt_id`. All other fields remain unchanged. Completion
requires a novel, independent attempt of the specified context: a subsequent
session for a cold check, a later local day for delayed transfer. Ineligible
legacy delayed completions reopen in the report. Failed attempts can complete
the check but cannot demonstrate mastery;
schedule a new follow-up with a new ID when needed.

Assessed means an unaided scored attempt, regardless of correctness.
Demonstrated means qualified correct, novel, independent reasoning exists
without a subsequent contradictory independent incorrect/partial attempt.
Correct letter-only repeats and correct post-teaching checks neither create
nor erase a prior demonstration. Unknown or assisted evidence does not overwrite
qualified independent evidence. Delayed transfer additionally requires a
later-local-day transfer demonstration without a subsequent independent failure.
Staleness is a separate reporting flag. None guarantees a passing score.

## Revision migration and recovery

For a flawed or ambiguous item, use the same append-only void path with
`reason_kind: invalid_item`, a factual `reason`, and `source_ref` to the defect
evidence. `response_ref` identifies the genuine original answer, and
`genuine_confirmed` confirms that provenance; do not invent a user correction.
The validator requires an exact match with the referenced attempt's
`response_ref`, including for already stored invalid-item voids. A separate
correction-turn reference belongs to `disowned_answer`, not `invalid_item`.
Mismatches fail audit/record/resume rather than silently rewriting provenance.
This removes its effect on learner weakness and mastery without changing the
historical result. Do not ask the learner to accept an incorrect key. If the
item was never scored, no attempt needs to be invented merely to void it.
For prepared-unanswered or response-journaled items with no ledger attempt, use
the checkpoint's [journal-only invalidation](session.md#journal-only-invalid-item-replacement)
instead. Preserve the original question/response and defect evidence privately;
do not create a ledger void or learning event for it.
Replace an invalid item only when continuing, preserve the prepared item index and
answer-position contract, and never re-ask the flawed item unchanged as if it were valid.

If the user disowns an answer, append a `voided_attempts` record through the
same validated `record` command: `id`, `attempt_id`, `reason`, `response_ref`
pointing to the genuine correction, `genuine_confirmed: true`, and its actual
timezone-bearing `timestamp`. The original event is retained for audit, not
rewritten or scored again. Coverage calculations exclude it. Checks based on
the voided answer are invalidated; a check whose completion was voided reopens
in the audit. Reconcile the displayed session/mock score and progress summary,
then re-ask the original question unchanged. Historical activity allocation is
preserved; a void is not a new unit or a license to reset the breadth queue.

Keep a private backup before a deliberate migration. Reconcile old/new source
scope and map unchanged IDs explicitly. Changed/split scope remains unassessed
unless its exact subskills have attributable compatible evidence. Archive
retired-objective evidence rather than deleting it. Record migration provenance
and re-audit before resuming; do not use `init` to reset historical records.

For ordinary updates, use `record` with the current ledger hash (`sha256` from
the last audit or successful `record --json`). It validates the merged
state before an atomic replacement; duplicate identical events do not double
count. Batch object property order is not significant: check recompletion can
use a void in the same batch, and a check already reopened in the original
ledger remains eligible for repair when the batch also records its missing
timezone. The replacement completion must still pass all source/evidence
validation against the merged ledger. A stale hash, conflicting event, invalid file, or existing writer lock
is an explicit error. Preserve and inspect evidence rather than silently
starting over. Only remove a stale lock after establishing no writer is active.
