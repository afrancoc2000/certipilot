# Local workflow evaluation

Run the deterministic suite from the repository root:

```powershell
python -B -m unittest discover -s .github\skills\coverage-audit\tests
```

The fixtures are synthetic test data, not learner answers. Tests must never
write into real exam assets or count toward personal progress.

## What automated tests establish

- Catalog structure, complete queue membership, and exam isolation.
- Allocation and lifecycle transitions, including interruption and idempotent
  resume without double counting.
- Genuine-answer metadata requirements, assisted/independent distinctions,
  later-local-day eligibility, and effect of voided evidence.
- Atomic writes, stale-hash rejection, and checkpoint identity/order invariants.
- Privacy patterns and canonical-policy references.

These checks do not prove that an AI correctly diagnosed a misconception,
understood a source, generated an unambiguous item, or followed every instruction.
Keyword/link checks are wiring tests, not pedagogical evaluations.

## Study permission profile

Run `pwsh -NoProfile -File .github\tests\test-study-permissions.ps1` on Windows.
The synthetic launcher/helper checks cover command and root restrictions,
fixed payload routing, missing inputs, failed helper execution, targeted cleanup,
interactive launch arguments, and rejection of broad configured permissions.
They do not launch a model or prove the installed CLI will approve a live call.
Verify a real study turn separately: the directly invoked helper and fixed
progress/payload writes should not prompt; unrelated commands should still
request permission. Do not test by inventing learner answers.

## Executable workflow contracts

[test_workflows.py](../tests/test_workflows.py) uses temporary synthetic catalogs,
ledgers, and checkpoints, with actual `init`, `record`, `checkpoint`, `resume`,
and `mock-quotas` CLI entry points. It exercises a complete 10-item/four-domain
mock with metadata, locked positions, neutral four-option projection, a flagged
response, pause/fresh-process resume, deferred grading, record/checkpoint
interruption, identical replay, review and completion. Normal quiz advancement
and invalid-item replacement have separate complete journeys.
Free-response journeys cover private rubric validation/locking, pause and
fresh-process resume, genuine response recording, grading/review/completion,
and disowned or invalid-item corrections at all three persistence stages.

Expected quota counts, actions, scores, and surviving history are independently
asserted. Transition tests cover allowed/forbidden completion and repair, voided
sources/evidence, same-batch property ordering, missing historical timezones,
and no-remediation substitution. Failed writes preserve prior bytes; fixtures
never load real learner assets. Initial saves and session rollovers of
question-bearing sessions are deck-only (empty `items`); new questions are then
appended unanswered before responses are accepted.

Follow the [script-development instructions](../../../instructions/script-development.instructions.md)
when changing these contracts. The conversational scenarios below remain
separate: executing a script journey does not prove an AI delivered good teaching
or correctly interpreted a first-party source.

## Manual multi-turn scenarios

Exercise these with synthetic content in isolated session storage. Do not
simulate the real learner's answers or record a synthetic result in their ledger.
Use the learner's actual turns for any real study-session evaluation.

| Scenario | Required observation |
| --- | --- |
| Pause while an item is unanswered | No new question, grading, or exit ticket. Resume presents the same stem/options; the original activity ID is retained internally, not recited. |
| Pause after a genuine answer | Record at most once; resume the next required action, not a duplicate grade. |
| Pause after ledger write but before checkpoint write | Disclose the save limitation in plain language; reconcile using existing IDs internally. Never invent a missing answer or repeat an event. |
| Interrupted deferred mock | Resume preserves locked option order and deferred grading. The checkpoint summary reveals no key or rationale. |
| Correct letter-only response after prior reasoning | Quiz score remains valid; no new reasoning credit and no erasure of prior qualified evidence. |
| Correct response accompanied by uncertainty | Ask one targeted mechanism/constraint probe if needed; do not demand a long explanation for every item. |
| Same-day fresh scenario in a renamed chat | Useful independent follow-up, not delayed retention. |
| Independent wrong reasoning on a new scenario | Reopen the specific evidenced subskill, teach the causal gap, and preserve breadth. |
| Two defensible answers or unsupported key | Acknowledge the flawed item, remove its effect on learner weakness/mastery, and replace only when continuing. |
| User disowns an answer | Genuine correction provenance, append-only void when recorded, reconcile, and re-ask unchanged. |
| Already completed equivalent closing checks | Reuse the evidence rather than asking redundant exit questions. |
| Local notes conflict with authoritative behavior | Verify the specific claim, flag the discrepancy, and do not grade from the local/community key. |
| Source unavailable or context lost | Explicitly disclose the limitation; no authoritative-looking fallback or fictional resume state. |
| Close with a newer future/expired plan beside today's plan | Reuse the retained applicable plan, or select by actual date range; the newer nonmatching plan is not adapted. |
| Close with multiple date-matching plans | Ask which plan to adapt while continuing; on stop, retain the unresolved choice without a question or patch. |
| Paused free-response transfer check | Resume the exact prompt without invented options, private criteria, source hints, or fabricated input. |

## Teacher-first conversation checks

Evaluate under [Teacher-first conversation](../../../../AGENTS.md#teacher-first-conversation).
Static tests only verify policy wiring and removed output templates. These
scenarios require observing real agent behavior; do not claim tone is proven
by a passing keyword test.

| Scenario | Required observation |
| --- | --- |
| Start or resume a normal lesson | Warm, concise transition using topic names. No audit counts, hashes, activity IDs, or state-machine narration. Missing history does not become invented praise. |
| Correct letter-only quiz answer | Accurate result and useful causal explanation; no obligatory "reasoning not established" warning or save receipt. A probe is used only when instructionally useful. |
| Wrong answer or repeated difficulty | Explain the mechanism patiently and change the example when helpful. No compliance language, shaming, exaggerated praise, or claim the learner failed an evidence requirement. Breadth remains protected internally. |
| Direct topic question during a plan | Answer conversationally and record the focused choice internally; do not require the learner to request an "override." |
| Routine successful audit or checkpoint | Persist required fields and return operational handoffs internally. The learner sees teaching or the next question, not bookkeeping. |
| Publish a prepared question after tools or delegation | Required saves and handoffs finish first. The parent presents the neutral question as its final response, ending with the answer instruction, without a save receipt or subsequent waiting message. |
| Autopilot enabled or automated continuation while awaiting an answer | Before question delivery, request interactive mode once. Empty continuations and tool/review notifications never become answers, reminders, new questions, or dummy tool work; the pending item is unchanged. Client-generated notifications may still appear and are not claimed to be hidden by instructions. |
| Failed progress save | Briefly explain what was not saved and the practical next step. No success claim or raw diagnostic dump; safe concept teaching can continue without fabricating a resumable mock. |
| Mock in progress and final review | During the mock, only question position, neutral question/options, and necessary clarification. At review, genuine score, domain breakdown, complete missed/flagged reviews, and useful next topics; no audit dashboard or answer-position statistics by default. |
| Session close or stop | Short learning recap when appropriate; a stop gets acknowledgment without another question. Pending work stays recorded without reciting state IDs. |
| Requested metrics or audit explanation | Explain the relevant numbers and limitations accurately. The internal-output boundary is not a refusal to answer a diagnostics request or permission to leak a live mock key. |

## Item-quality rubric

Before presenting an original item, verify:

1. Its exact target subskill and decision are identifiable.
2. Stated constraints make the keyed answer defensible and best; multi-select
   cardinality is declared. Free-response checks instead have verified private
   criteria that specify the required causal reasoning.
3. Choice distractors fail for concrete causal reasons, not irrelevant trick wording.
4. Choice options are neutral and similarly specific; lead-ins do not reveal the
   key or free-response criteria.
5. The rationale is supported by a verified first-party source.
6. A transfer variant changes a decision-relevant constraint or application,
   not merely names.
7. The evidence sought matches the claim: selected option for score, actual
   reasoning for understanding, later-day unaided reasoning for retention.

Mark unsupported or ambiguous judgments as unresolved. Revise the item before
use or invalidate it without a learner penalty if the problem is discovered
after answering. No aggregate rubric score overrides a failed correctness gate.

## Evidence to retain from an evaluation

Keep only the scenario ID, observed state transition, violated expectation if
any, and the relevant source or local test reference. Keep synthetic artifacts
in test/session storage. Do not add external telemetry or upload learner content.

## CI and local code coverage

[CI Python](../../../workflows/ci-python.yml) runs the full unittest discovery
suite on Ubuntu and Windows with the same Python 3.13 version for pull requests and pushes
to `main`, plus manual runs. It adapts the shared container workflow's main-branch
triggers, explicit checkout/setup, and test reporting, without its containers,
deployment, scans, or secrets. Permissions are read-only; superseded runs cancel.
The Windows job runs on GitHub's hosted Windows runner, not the learner's PC;
both operating systems use Python 3.13. Runner-dependent paths are initialized
in a step through `GITHUB_ENV`, not unsupported job-level `runner` expressions.
Only explicitly named synthetic test logs and coverage reports are uploaded,
including on failure, with seven-day retention. Exam assets are never artifacts.

The runtime remains standard-library-only.
[requirements-dev.txt](../../../../requirements-dev.txt) pins the coverage test
dependency. [.coveragerc](../../../../.coveragerc) instruments branches and limits
measurement to the production scripts under `.github`, excluding only the
coverage-audit tests. This includes the executable coverage gate itself.
[check_coverage.py](../../../check_coverage.py) checks each file separately:
`coverage.py`, `session.py`, and `check_coverage.py` each require
99% lines / 98% branches, and any other measured script gets the same
`DEFAULT_FLOOR`, so a new script cannot escape the gate. Missing
reports, files, branch instrumentation, or valid counts
fail closed. The check uses exact counts, not rounded/combined percentages.
Ratchet `FLOORS` in the gate after validating improvements across the matrix;
never lower them to hide a regression.

When changing workflow expressions, run `actionlint -shellcheck= -pyflakes=
.github/workflows/ci-python.yml` (one command line) in addition to parsing YAML.
Valid YAML alone does not establish that GitHub permits an expression's context
at that location. Only an actual hosted run establishes that the jobs start.

Run from the repository root. Use a dedicated temporary virtual environment,
not the system Python or an existing project environment. Reports and coverage
data stay in that temporary directory, outside exam assets and the worktree.
The scoped `PYTHONPATH` allows discovery helpers to import each other under
coverage; do not point it at the production directory named `coverage.py`.

PowerShell:

```powershell
$env:CI_REPORT_DIR = Join-Path ([IO.Path]::GetTempPath()) ("study-ci-" + [guid]::NewGuid())
$env:COVERAGE_FILE = Join-Path $env:CI_REPORT_DIR ".coverage"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = Join-Path $PWD ".github\skills\coverage-audit\tests"
python -B -m venv "$env:CI_REPORT_DIR\venv"
$python = "$env:CI_REPORT_DIR\venv\Scripts\python.exe"
& $python -B -m pip install -r requirements-dev.txt
& $python -B -m coverage run -m unittest discover -s .github\skills\coverage-audit\tests
# Check $LASTEXITCODE after each command; a failed test run remains a failure.
& $python -B -m coverage json
& $python -B -m coverage xml
& $python -B -m coverage report
& $python -B .github\check_coverage.py "$env:CI_REPORT_DIR\coverage.json"
```

Bash (Linux/macOS):

```bash
export CI_REPORT_DIR="$(mktemp -d)"
export COVERAGE_FILE="$CI_REPORT_DIR/.coverage"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/.github/skills/coverage-audit/tests"
python3 -B -m venv "$CI_REPORT_DIR/venv"
python="$CI_REPORT_DIR/venv/bin/python"
"$python" -B -m pip install -r requirements-dev.txt
"$python" -B -m coverage run -m unittest discover -s .github/skills/coverage-audit/tests
# Check $? after each command; a failed test run remains a failure.
"$python" -B -m coverage json
"$python" -B -m coverage xml
"$python" -B -m coverage report
"$python" -B .github/check_coverage.py "$CI_REPORT_DIR/coverage.json"
```

Keep each run's temporary directory only while inspecting its reports. The
existing package-free `python -B -m unittest discover` command remains supported.
To run only the gate's synthetic threshold/failure tests, add
`-p test_ci_coverage_gate.py` to unittest discovery.
