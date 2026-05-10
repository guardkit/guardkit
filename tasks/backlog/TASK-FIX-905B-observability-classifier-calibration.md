---
id: TASK-FIX-905B
title: Calibrate observability run-success classifier against TASK-REV-ABST §3.1 baseline
status: backlog
created: 2026-05-10T19:30:00Z
updated: 2026-05-10T19:30:00Z
priority: high
tags: [observability, classifier-calibration, ac-010, baseline-mismatch]
parent_task: TASK-OBS-ABST
parent_review: TASK-REV-ABST
complexity: 3
estimated_effort_hours: 2
---

# Task: Calibrate `classify_filename()` against the §3.1 baseline

> **Why this exists**: TASK-OBS-ABST AC-010's Definition of Done explicitly
> requires *"first invocation reproduces the §3.1 baseline within ±10%"*.
> The first invocation on 2026-05-10 missed that target on two of three
> named repos. The implementation is otherwise complete (62/62 tests pass,
> ACs 1-9 satisfied), but it's not safe to merge a calibrated-wrong
> metric to main during the freeze when TASK-REV-ABST.1 depends on it
> being right on 2026-05-17.

## Symptom

Running `guardkit observability run-success` from
`.guardkit/worktrees/TASK-OBS-ABST` on 2026-05-10 produces:

| Repo | TASK-REV-ABST §3.1 expected | Actual output | Verdict |
|---|---|---|---|
| jarvis | 5 features, 0 confirmed passes | 5 features (W17:2 + W18:3), 0 first-pass, 0 multi-retry-pass | ✅ matches (within tolerance) |
| forge | ~12 features, ~3 eventual passes, ~1 first-pass | 42 features total (W16:30 + W17:4 + W18:6 + W19:2), W16 alone reports 30 first-pass | ❌ ~3.5× over-count on features; first-pass bucket dominated by W16 anomaly |
| fleet-gateway | 1 feature (FG-001), 0 passes, last 2026-05-10 | 1 feature, 1 multi-retry-pass | ❌ over-counts pass (should be stuck/no-pass) |

The forge W16 row is the loudest signal: 30 features, all 30 marked
first-pass-pass. That's almost certainly the classifier mis-treating
forge's `autobuild-FEAT-*-success-history.md` filenames — each historical
"success" snapshot becomes a unique FEAT-ID first-pass-pass row, instead
of being deduplicated against the parent FEAT-ID's actual run sequence.

## Reproducer

```bash
WT=.guardkit/worktrees/TASK-OBS-ABST
cd "$WT"
python3 -m guardkit.cli.main observability run-success --since=2026-04-01 --format=md

# Cross-check against the per-repo §3.1 baseline in
# .claude/reviews/TASK-REV-ABST-review-report.md
```

For the forge anomaly, list the W16 source artefacts:

```bash
ls -1 ~/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-*.md \
  | head -40
# Look for *-success-history.md, *-run-N-success.md, *-first-attempt-success.md
# patterns and verify each maps to a *distinct* FEAT-ID before counting.
```

## Acceptance criteria

### AC-001 — Reproduces §3.1 within ±10%
**WHEN** the operator runs `guardkit observability run-success
--since=2026-04-01` from the GuardKit repo root, **THE SYSTEM SHALL**
produce per-repo metrics that match TASK-REV-ABST §3.1 (the baseline
table) within ±10% on `features_attempted`, `first_pass_pass`, and
`multi_retry_pass` for each of jarvis, forge, study-tutor,
specialist-agent, and fleet-gateway.

### AC-002 — Distinct FEAT-ID counting
**WHEN** scanning a repo, **THE SYSTEM SHALL** count each
`features_attempted` once per *distinct* FEAT-ID, regardless of how
many `autobuild-FEAT-*` artefact files reference that FEAT-ID. The
bucket assignment for that FEAT-ID uses the *most recent* artefact's
classification (per the existing AC-005 dual-signal rule), not a sum
across all artefacts.

### AC-003 — `-success-history` semantics
**WHEN** a filename matches `autobuild-FEAT-*-success-history.md`,
**THE SYSTEM SHALL** treat it as a *retrospective* record of a prior
success, not as a fresh first-pass-pass. Specifically:

- If the FEAT-ID has *only* `-success-history` artefacts and no
  `-run-N-` or other run-numbered artefacts → classify as
  `first_pass_pass` (the historical record IS the success).
- If the FEAT-ID has both `-success-history` and `-run-N-fail` /
  `-run-N-success` artefacts → use the run-numbered sequence; the
  history file is a retrospective summary and must not be double-counted.

### AC-004 — Fleet-gateway FG-001 reproduces
**WHEN** scanning fleet-gateway, **THE SYSTEM SHALL** classify FEAT-FG-001
as *not yet passed* (neither `first_pass_pass` nor `multi_retry_pass`)
based on the existing artefacts. The presence of
`autobuild-FEAT-FG-001-review.md` (a *review* artefact, not a *run*
artefact) must not push the FEAT into a pass bucket.

### AC-005 — Add baseline regression test
**THE SYSTEM SHALL** ship a new test
`tests/observability/test_baseline_reproduction.py` that:

1. Loads a frozen fixture under `tests/observability/fixtures/baseline_3_1/`
   replicating the on-disk shape of jarvis, forge, study-tutor,
   specialist-agent, and fleet-gateway as of 2026-05-10 (only the
   filenames, sizes, and minimal content needed for classification —
   not the full repo contents);
2. Runs the scanner against that fixture set;
3. Asserts each per-repo metric is within ±10% of the §3.1 expected
   values (hard-coded in the test as the regression target).

This test serves both as the AC-001 oracle and as a guardrail against
future regressions in the classifier.

### AC-006 — No regression on existing 62-test suite
**THE SYSTEM SHALL** keep all existing
`tests/observability/test_{run_success,sources,output}.py` tests
passing after the calibration fix.

## Implementation notes

- The classifier lives in `guardkit/observability/sources.py`. Suspected
  loci:
  - The filename → outcome regex table (`-success-history` likely missing
    a dedicated case, falling through to the generic `-success` rule).
  - The FEAT-ID extraction + dedup step (probably keying on the full
    filename rather than the parsed FEAT-ID).
  - The "review artefact vs run artefact" distinction in fleet-gateway —
    `autobuild-FEAT-FG-001-review.md` is review content, not a run
    record, and should be filtered out of `features_attempted` counting
    or treated as a `signal: filename-only` no-pass.

- The scanner already handles the divergent-signal rule (AC-005 of the
  parent task). Verify whether `-success-history` artefacts are coming
  in via the filename path with no JSON counterpart — that would explain
  why forge W16 lights up as first-pass: every history file is read as
  a fresh distinct success.

- For the regression fixture: copy the shape (filenames + 1-line bodies)
  from `~/Projects/appmilla_github/{forge,fleet-gateway}/docs/history/`
  on 2026-05-10. No need to replicate the full content — the classifier
  only reads filenames and (for incident detection) the first 200 lines.
  Synthesise a minimal corpus that reproduces the §3.1 baseline.

- The §3.1 baseline values to encode in the test are stated in the
  parent TASK-OBS-ABST body: forge ~12/~3/~1, jarvis 5/0, fleet-gateway
  1/0. Resolve the missing study-tutor and specialist-agent values by
  reading TASK-REV-ABST §3.1 directly.

## Out of scope

- Adding **new** signals (e.g. graphiti queries, autobuild stream-state
  reads) — those would change the metric definition, not calibrate the
  existing one.
- Changing the markdown/JSON output schema. The existing schema is
  consumed by TASK-REV-ABST.1 on 2026-05-17 and must remain stable.

## Files likely modified

- `guardkit/observability/sources.py` (classifier + dedup logic) —
  **out of scope of the gate-stack freeze**, safe to land any time
- `tests/observability/test_baseline_reproduction.py` (new)
- `tests/observability/fixtures/baseline_3_1/` (new fixture directory)

## Validation gate

This task is **blocking** for merging TASK-OBS-ABST to main. The
observability worktree at `.guardkit/worktrees/TASK-OBS-ABST` is
preserved on branch `autobuild/TASK-OBS-ABST` (merge-base
`b17275f6`, 16 commits behind current main). The merge sequence
post-fix is:

1. Land this calibration fix on the worktree branch (or as a small
   patch on top).
2. Confirm `pytest tests/observability/` green and the new baseline
   regression passes.
3. Rebase `autobuild/TASK-OBS-ABST` onto current main.
4. Merge to main; mark TASK-OBS-ABST `completed`.

## Related

- Originating task: TASK-OBS-ABST (passive run-success observability)
- Origin review: `.claude/reviews/TASK-REV-ABST-review-report.md` §3.1
- Successor consumer: TASK-REV-ABST.1 (2026-05-17 trajectory re-eval)
- Sibling follow-up: TASK-FIX-DF51 (Coach `code_review.score` producer
  wiring — separate root cause discovered in the same autobuild run)
