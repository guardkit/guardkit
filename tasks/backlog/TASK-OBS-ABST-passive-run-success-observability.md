---
id: TASK-OBS-ABST
title: Passive autobuild run-success observability from existing on-disk artefacts
status: backlog
created: 2026-05-10T18:35:00Z
updated: 2026-05-10T18:35:00Z
priority: high
tags: [observability, telemetry, autobuild, narrow-recommendation, evidence-gap-closure]
parent_review: TASK-REV-ABST
complexity: 5
implementation_mode: task-work
estimated_effort_hours: 5
---

# Task: Passive autobuild run-success observability

> **Why this exists**: TASK-REV-ABST §9.1 flagged the largest evidence gap as
> *"first-pass success rate is filename-pattern-inferred, not telemetry-
> measured"*. The follow-up review on 2026-05-17 (TASK-REV-ABST.1) needs a
> proper metric to score the falsifiers in §8.2. This task builds a CLI
> subcommand that derives the metric from artefacts **already on disk** —
> `docs/history/` filenames, `.guardkit/worktrees/*/.guardkit/autobuild/*/coach_turn_*.json`,
> and `tasks/{backlog,in_review,completed}/` task density. **No autobuild
> reruns are required.** The metric is reusable for every future review and
> closes the §9.1 gap without a single new feature build.

## Description

Add a `guardkit observability run-success` CLI subcommand that scans every
configured consumer-repo path plus the GuardKit task-tree and produces a
weekly first-pass-success metric, multi-retry rate, stuck-feature count,
manual-flip count, and framework-FP-incident count. The output is
markdown-formatted by default for paste-into-review-reports and JSON-formatted
on `--format=json` for programmatic consumption (e.g. `TASK-REV-ABST.1`'s
input).

**Data sources** (all read-only, all already on disk):

1. **Filename pattern signal**: glob `docs/history/autobuild-FEAT-*.md` per
   repo and classify by suffix (`-success`, `-fail*`, `-cancelled`, `-timeout`,
   `-run-N-`, `-even-worse`, `-still-fails`).
2. **Coach-artefact signal** (stronger): glob
   `.guardkit/worktrees/*/.guardkit/autobuild/*/coach_turn_*.json` and read
   `decision`, `rationale`, `honesty_verification.discrepancy_count`,
   `criteria_verification[].verified` per turn. This gives the *actual* turn
   count and outcome class, not just filename inference.
3. **Task-density signal**: count files in
   `tasks/{backlog,in_progress,in_review,blocked,completed}/` and any nested
   feature/2026-NN/ subfolders, bucketed by frontmatter `created:` ISO week.
4. **Framework-FP-incident signal**: glob
   `docs/history/*incident*.md` and `docs/history/*review*.md` per repo;
   count files that match the incident-shape (presence of "honesty-path-
   mismatch", "wrong-Python", "ModuleNotFoundError", "false-fail",
   "framework rejected", etc. in the body — first 200 lines is enough).

**Metric definition** per consumer-repo per ISO-week:

| Metric | Definition |
|---|---|
| `features_attempted` | Distinct FEAT-IDs with at least one `autobuild-*` artefact |
| `first_pass_pass` | Features where the lone artefact has `-success-` qualifier OR `coach_turn_1.decision == "approve"` |
| `multi_retry_pass` | Features with ≥2 artefact files including a `-success-` qualifier |
| `multi_retry_stuck` | Features with ≥2 artefact files, no `-success-` qualifier, last activity > 7 days ago |
| `manual_flips` | Features whose YAML has been edited to flip a task's `status` to `completed` without an autobuild approval (heuristic: `git log -p .guardkit/features/*.yaml` for status-flip diffs) |
| `framework_fp_incidents` | Count of incident-shape files dated in the week |
| `last_activity` | Max mtime across all artefacts for the FEAT-ID |

**Aggregate rollup** across all configured repos: same metrics, summed by
week.

## Acceptance criteria

### AC-001 — CLI subcommand
**WHEN** the operator runs `guardkit observability run-success`, **THE SYSTEM
SHALL** print the metric table to stdout in markdown by default.

### AC-002 — Configurable repo list
**WHEN** the operator passes `--repo PATH` (repeatable), **THE SYSTEM SHALL**
scan only those paths. **WHEN** no `--repo` flags are passed, **THE SYSTEM
SHALL** read a default list from `~/.guardkit/observability.yaml` (with a
schema documented in code), falling back to a built-in default of the five
repos: jarvis, forge, study-tutor, specialist-agent, fleet-gateway under
`~/Projects/appmilla_github/`.

### AC-003 — Time window flag
**WHEN** the operator passes `--since=YYYY-MM-DD`, **THE SYSTEM SHALL**
include only artefacts and tasks dated on or after that date. **THE DEFAULT**
shall be `2026-04-01` (covers the BDD-verification trajectory).

### AC-004 — Output formats
**WHEN** the operator passes `--format=md` (default), **THE SYSTEM SHALL**
emit a markdown table per repo plus an aggregate. **WHEN** the operator passes
`--format=json`, **THE SYSTEM SHALL** emit a JSON object suitable for
programmatic consumption by `TASK-REV-ABST.1`. The JSON schema is documented
inline in the implementation.

### AC-005 — Filename + JSON dual signal
**WHEN** scanning a feature, **THE SYSTEM SHALL** prefer the coach-artefact
signal over the filename-pattern signal **IF** both are available. **WHEN**
only the filename signal is available, **THE SYSTEM SHALL** mark the row
`signal: filename-only` so downstream readers can weight confidence. **WHEN**
the two signals disagree (filename says `-success-` but coach_turn_*.json
shows `decision: feedback`), **THE SYSTEM SHALL** mark the row
`signal: divergent` and prefer the JSON.

### AC-006 — Framework-FP incident detection
**THE SYSTEM SHALL** scan `docs/history/*incident*.md` and `*review*.md`
files (per repo) for at least one of the marker phrases:
*"honesty path"*, *"path mismatch"*, *"ModuleNotFoundError"*,
*"wrong Python"*, *"framework rejected"*, *"false-fail"*,
*"shared worktree"*, *"per-task glue"*, *"editable-install leak"*.
A file matching ≥1 phrase increments `framework_fp_incidents` for the file's
mtime week.

### AC-007 — Test fixture coverage
**THE SYSTEM SHALL** ship with a test fixture under
`tests/observability/fixtures/` exercising every classification path:
filename-only success, filename-only failure, JSON-only success, JSON-only
failure, divergent signals, multi-retry recovery, multi-retry stuck, manual-
flip, incident file. Tests live at `tests/observability/test_run_success.py`.

### AC-008 — README + invocation example
**THE SYSTEM SHALL** ship with a `docs/guides/observability.md` documenting:
the subcommand, the metric definitions, the data-source assumptions, and a
worked example output. The doc explicitly notes that no autobuild runs are
required and the metric works retrospectively against any GuardKit
deployment that has a `docs/history/` archive.

### AC-009 — Idempotent + read-only
**THE SYSTEM SHALL** never write to or modify any source artefact. Repeated
invocations on the same data set produce identical output (modulo timestamp
fields).

### AC-010 — Reasonable runtime
**THE SYSTEM SHALL** complete a scan over the five default repos in under 60
seconds on a developer laptop (no remote calls, no LLM invocations, just
filesystem + JSON parsing).

## Implementation notes

- Recommended layout:
  - `guardkit/observability/__init__.py`
  - `guardkit/observability/run_success.py` (the scanner + metric calculator)
  - `guardkit/observability/sources.py` (filesystem + JSON readers)
  - `guardkit/observability/output.py` (markdown + JSON formatters)
  - Register the subcommand in whichever module owns CLI subcommand
    registration (likely `guardkit/cli.py` or `guardkit/commands/`).
- Use `dataclasses` (not Pydantic) for the internal metric records — see
  `.claude/rules/patterns/dataclasses.md`. Use Pydantic only at the `--format=
  json` boundary if needed for schema generation.
- Filename classification logic should be a single `classify_filename(name:
  str) -> Outcome` function with a clear regex table; test it directly against
  the real filenames listed in TASK-REV-ABST §3 (e.g. `autobuild-FEAT-FORGE-
  009-success-history.md` → recovered_after_n_retries=3, success=True).
- The coach_turn JSON parser should be defensive: not every turn file will
  exist; the scan should pick up whatever's there. Specifically guard against:
  - File exists but is empty (non-blocking advisory turn that aborted before
    write);
  - File exists but has `criteria_verification: []` (the FFC3 short-circuit
    case — count this as a framework-FP candidate even if the rationale is
    "approve");
  - File exists with `decision: error` rather than approve/feedback (rare but
    happens).
- For the manual-flip detector: parse `git log -p .guardkit/features/*.yaml`
  and flag commits where a task's `status` field changes from `in_progress`
  or `failed` to `completed` *without* a corresponding `coach_turn_*.json`
  decision=approve. This is heuristic — false-positive rate may be ~10%; that's
  acceptable for a leading indicator.
- The metric is a *passive* signal. Do not treat it as ground truth. The
  output should explicitly say "passive metric — does not run autobuild;
  reflects on-disk state at scan time".

## Validation against TASK-REV-ABST baseline

The first invocation of this command (after implementation) should reproduce —
within ±10% — the per-repo numbers in TASK-REV-ABST §3.1. If it doesn't, the
classification logic is wrong; debug before declaring complete. Specifically:

- `forge` should show ~12 features, ~3 eventual passes, ~1 first-pass.
- `jarvis` should show ~5 features, 0 confirmed passes (per the report's
  uncertain signal).
- `fleet-gateway` should show 1 feature (FG-001), 0 passes, last activity
  2026-05-10.

Treat the report's §3.1 table as the regression target.

## Files to create

- `guardkit/observability/__init__.py`
- `guardkit/observability/run_success.py`
- `guardkit/observability/sources.py`
- `guardkit/observability/output.py`
- `tests/observability/test_run_success.py`
- `tests/observability/fixtures/*` (synthetic docs/history + coach JSON)
- `docs/guides/observability.md`
- `~/.guardkit/observability.yaml` (default config — operator-installed, not
  versioned in the repo; document the schema in the guide)

## Files to modify

- `guardkit/cli.py` (or whichever CLI registration module exists — check for
  a `commands/` directory or click/typer group definition)
- `pyproject.toml` (no new deps expected; existing pyyaml/typer/click suffice)

## References

- Originating review: `.claude/reviews/TASK-REV-ABST-review-report.md` §3,
  §8.1.2, §9.1
- Existing data sources confirmed on disk (cited in the review):
  - `~/Projects/appmilla_github/jarvis/docs/history/`
  - `~/Projects/appmilla_github/forge/docs/history/`
  - `~/Projects/appmilla_github/study-tutor/docs/history/`
  - `~/Projects/appmilla_github/specialist-agent/docs/history/`
  - `~/Projects/appmilla_github/fleet-gateway/docs/history/`
  - `~/Projects/appmilla_github/specialist-agent/docs/history/autobuild-FFC3-honesty-path-mismatch-incident.md` (15KB — full read confirmed marker phrases present)
  - `~/Projects/appmilla_github/fleet-gateway/docs/history/autobuild-FEAT-FG-001-review.md` (17KB — full read confirmed marker phrases present)
- Pattern library:
  - `.claude/rules/patterns/dataclasses.md` (use dataclasses for internal
    metric records)
  - `.claude/rules/patterns/orchestrators.md` (multi-step pipeline pattern if
    the scanner grows beyond a single function)

## Definition of done

- [ ] All 10 ACs pass
- [ ] First invocation reproduces the §3.1 baseline within ±10%
- [ ] `pytest tests/observability/` green
- [ ] `docs/guides/observability.md` reviewed and complete
- [ ] CLI registered (`guardkit observability --help` shows the new command)
- [ ] Sample JSON output saved as
  `.claude/observability/run-success-snapshot-2026-05-10.json` to serve as
  TASK-REV-ABST.1's input baseline
- [ ] Task moved to `completed` with provenance fields populated
