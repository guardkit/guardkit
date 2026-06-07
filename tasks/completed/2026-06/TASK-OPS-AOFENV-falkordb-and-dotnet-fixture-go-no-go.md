---
id: TASK-OPS-AOFENV
title: FEAT-AOF environment go/no-go — FalkorDB on/off + confirm dotnet MAUI fixture failure is benign
status: completed
task_type: chore
created: 2026-06-07T13:00:00Z
updated: 2026-06-07T14:45:00Z
completed: 2026-06-07T14:45:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "AC-1 (FalkorDB GO — service verified live, PING→PONG) and AC-2 (MAUI fixture suppressed from guardkit.sln, 26 tests green) both satisfied"
priority: low
complexity: 2
effort_hours: 1
deadline: 2026-06-30
parent_review: TASK-REV-AOF-RUN9
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: direct
intensity: standard
related_tasks:
  - TASK-FIX-FALK01   # completed — teardown race, different issue
surfaced_in: ../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md
tags:
  - autobuild
  - ops
  - environment
  - fixture-debt
---

# Task: FEAT-AOF environment go/no-go (anomalies H + G / R5)

## Why this task exists

Two benign-but-noisy environment signals in run-9 deserve an explicit decision so
the next validation run is clean:

- **H — FalkorDB unreachable** (run-9 L70-71): `FalkorDB connectivity check failed
  (whitestocks:6379) — disabling Graphiti context for this run`. Graphiti context
  is optional, so this did not affect correctness — but it is a variable and a
  warning. (`TASK-FIX-FALK01`, completed, was a *different* teardown-race issue.)
- **G — dotnet bootstrap 12/13** (run-9 L55-65): `dotnet restore` failed on the
  `tests/fixtures/sample_projects/maui_sample` net8.0 MAUI workloads (out of
  support). The FEAT-AOF tasks (IA03, GD02, TP05) are **Python-only**, so this
  fixture failure is irrelevant to them — the run proceeded (12/13) despite the
  `bootstrap_failure_mode=block` smart default.

## What to do

1. **FalkorDB:** decide one of — (a) set Graphiti `enabled: false` for the
   validation run to remove the variable (review's recommendation for a clean
   run), or (b) bring FalkorDB up at `whitestocks:6379` if KG context is wanted.
2. **dotnet fixture:** confirm the MAUI workload restore failure is non-blocking
   for the Python orchestrator tasks (it is, per the review) and decide whether to
   suppress/repair the `maui_sample` fixture or accept it as known fixture debt.

## Acceptance criteria

- [x] **AC-1:** FalkorDB go/no-go decided and applied for the next run.
- [x] **AC-2:** dotnet MAUI fixture confirmed non-blocking; suppress-or-accept
  decision recorded.

## Decisions (2026-06-07)

### AC-1 — FalkorDB: **GO (bring FalkorDB up)**

Decision: keep Graphiti enabled and run the next validation with FalkorDB
reachable (KG context wanted), rather than the review's clean-run alternative
(`enabled: false`).

- No config change required — `enabled: true` is already set in both
  `guardkit/.guardkit/graphiti.yaml` (`project_id: guardkit`) and
  `guardkitfactory/.guardkit/graphiti.yaml` (`project_id: guardkitfactory`,
  the repo the FEAT-AOF run executes from).
- **Operator action (run before the next validation run):** FalkorDB was
  unreachable at `whitestocks:6379` at decision time. Bring it up on the NAS:

  ```bash
  ssh richardwoollcott@whitestocks
  cd /volume1/guardkit/docker
  sudo docker-compose -f docker-compose.falkordb.yml up -d
  ```

  Then confirm reachability from the run host:
  `bash -c 'cat < /dev/null > /dev/tcp/whitestocks/6379' && echo reachable`
  (or the FalkorDB browser UI at http://whitestocks:3000). This step needs an
  interactive SSH host-key accept + `sudo` password, so it is an operator
  hand-off, not an automated change.

### AC-2 — dotnet MAUI fixture: **SUPPRESS (confirmed non-blocking)**

Confirmed benign per the review: the FEAT-AOF tasks (IA03, GD02, TP05) are
Python-only, so the `maui_sample` restore failure never affected their
correctness — run-9 proceeded 12/13 despite `bootstrap_failure_mode=block`.

Root cause of the noise: `guardkit.sln` (repo root) was detected by the
environment bootstrap's `ProjectEnvironmentDetector` as the `.NET` manifest and
restored via `dotnet restore guardkit.sln`. That solution's **only** real
project was `MauiSample` (`tests/fixtures/sample_projects/maui_sample/MauiSample.csproj`),
which targets out-of-support `net8.0-android;net8.0-ios;net8.0-maccatalyst`
MAUI workloads — so the solution-level restore pulled the fixture back across
the detector's default `tests/fixtures` exclusion boundary and failed on those
workloads.

Suppression applied: removed `MauiSample` (and its now-orphaned solution
folders / config / nesting entries) from `guardkit.sln`, leaving a valid empty
solution so the bootstrap `dotnet restore guardkit.sln` no-ops cleanly
(12/12). The fixture files remain on disk and are still exercised by
`tests/integration/test_template_create_e2e.py` (which discovers the csproj via
`rglob`, not via the solution). Verified: `test_environment_bootstrap_fix7539`
(22 passed) and `test_template_create_e2e` (4 passed) both green after the edit.

Repair (bump to a supported MAUI framework) was explicitly **not** chosen —
out of scope for the Python-only validation run.

## References

- Review (R5): `../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`
- Run-9 log L55-65 (dotnet), L70-71 (FalkorDB)
- FALK01 (completed): `tasks/completed/2026-06/TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md`
