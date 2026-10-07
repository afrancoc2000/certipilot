---
description: "Use when creating or changing scripts, checkpoint schemas, CLI contracts, workflow tests, or their CI. Requires executable workflow and transition tests, not only line coverage."
applyTo: "**/*.py,.github/workflows/*.yml,.github/workflows/*.yaml"
---

# Script development and regression prevention

Study scripts implement the contracts in the agents and skills. Passing unit
tests or high coverage alone does not establish that those contracts work.

## Before changing behavior

- Read the caller's skill/instructions and the relevant schema reference. List
  required inputs, persisted fields, public outputs, valid transitions, and
  failure/recovery behavior before implementing a new script or schema field.
- Trace each required field through initial creation, validation, save, fresh
  process resume, ordinary update, correction history, and safe output. Keep
  private fields out of public projections. Define backward compatibility
  explicitly; never invent missing historical evidence.
- Reuse existing validators, persistence helpers, and test fixtures. Keep
  runtime dependencies minimal. Update directly related contracts with code.

## Required tests

- For each new workflow, add an executable contract journey using the same
  payload shape and cardinality the skill requires. Exercise the actual CLI
  entry points, not only internal helpers or a parallel test implementation.
  Include at least one fresh-process restart at a meaningful boundary.
- Cover the complete successful journey and relevant interrupted journeys:
  preparation, genuine synthetic response journal, ledger recording, grading,
  review, completion, pause/resume, and correction. For mocks use the full
  planned count, real metadata structure, locked deck, and deferred grading.
- Assert outcomes independently of the implementation. Do not derive expected
  actions, quotas, or scores by calling the same function being tested.
- For each changed state transition, test allowed and forbidden transitions,
  including corrections at each persistence stage: prepared-only,
  response-journaled but not ledger-recorded, and ledger-recorded. Also cover
  boundary values, immutable history, duplicate retries, stale hashes, and
  failure after one durable write but before the next. Assert failed writes
  preserve the previous bytes and retries do not duplicate evidence.
- Test batch ordering when operations depend on one another. JSON object
  property order must not determine whether a valid batch succeeds.
- Add explicit tests for both acceptance and rejection of each critical
  validation rule, including omitted optional-looking fields that a workflow
  actually requires and the boundaries of legacy-only exemptions.
  Line/branch coverage does not prove all compound predicates
  or exception paths were exercised.
- For a reported bug, first demonstrate a failing regression test, then fix
  it. If requested to evaluate tests independently of review findings, create
  and run that test set before reading those findings; disclose which findings
  it missed rather than claiming retrospective tests caught them independently.
- Keyword/link tests establish instruction wiring only. They cannot replace
  executable schema examples, allocation calculations, or workflow tests.

## Validation and reporting

- Run targeted tests while iterating, then the full relevant suite and the
  same coverage gates used by CI. Review missing branches by risk, not merely
  percentage. Do not lower baselines or exclude production code to make a
  change pass; explain unreachable paths and platform-specific limits.
- Run the CI matrix (Windows and Linux on each Python version listed in
  [ci-python.yml](../workflows/ci-python.yml)). Local Windows validation is
  not evidence that remote Linux jobs ran.
- Fixtures and failure injection must use temporary synthetic data. Never
  write tests into real exam assets, count synthetic answers as learning, or
  upload learner records. CI artifacts contain only test/coverage output.
- Follow the [evaluation guide](../skills/coverage-audit/references/evaluation.md)
  for commands and separate conversational scenarios. Report tests actually
  run, observed failures, coverage, and remaining limitations accurately.

## Different from conversational evaluation

These rules govern implementation correctness. The small conversational
evaluation set checks whether the agent teaches warmly, explains mechanisms,
honors stops, and avoids answer leakage in real interaction. Keep those checks
separate; neither Python coverage nor static wording checks prove teaching
quality, source truth, or authentic learner-answer provenance.
