# Conversation starter — GuardKit autobuild snapshot/reset workflow handoff

> **For the next Claude session picking up this work.** Context is
> running low so this is a compact handoff. The user is running
> autobuild test runs on FEAT-AOF (cutover-validation) and FEAT-9DDE
> (next feature) and asking for snapshot + reset cycles after each run.

## What you'll be asked to do

The user repeats the same workflow after every autobuild run:

1. **After a run finishes**: *"please can you also commit run N files
   for the GB10 to analyse see [path-to-run-log]"*
   → snapshot artifacts, write an analysis README, commit + push
2. **Before the next run**: *"please reset for the next run"*
   → reset feature-state YAML + revert per-task frontmatters

Occasionally also:
- *"yes please" / "B+C"* to confirm prior options
- File bug-class fixes when issues surface

## Hard-won context (DON'T relitigate)

### TASK-HMIG-010 cutover-baseline is DURABLE

Three independent successful FEAT-AOF runs:

| Run | Date | Shape | Wall |
|---|---|---|---|
| 19 | 2026-06-07 | B-min default, parallel waves, 3/3 first-pass approve | 52m 4s |
| 20 | 2026-06-07 | B-min default, parallel waves, 3/3 first-pass approve, COACHTESTTO validated | 52m 31s |
| **25** | **2026-06-11** | **Lever-3 B-full → B-min degrade, sequential waves, 3/3 first-pass approve, 10 ACs each w/ populated criteria_verification** | **45m 23s** (fastest) |

**TASK-HMIG-011 cutover ceremony is unblocked.** Don't suggest
"more validation needed" — the evidence is overwhelming and
reproducible. The user knows.

### F-numbered findings — all resolved

- F1, F4, F9, F10, F11, F12, F14, F17, F18, F22: closed in runs 1-12
- F20 (gemma4 ctx overflow): closed by D-3 (run 19), reconfirmed runs 20/22/25
- F23A (gemma4:31b OOM): closed by D-3 (run 19), reconfirmed
- F23-residual (transient 502): non-recurrence in run 12 = F23D transient
- F24 (gemma4 schema-correct emission): closed by D-3, reconfirmed
- Run-13 grammar-no-op finding: closed architecturally by D-3 toolless split

### Architecture is in three-layer adversarial-cooperation mode

```
Player → SPECCOCH01 (contains SPECHANG specialists)
       → Coach quality gates (deterministic)
       → Coach LLM (B-full Phase-A → B-min synthesis with GBNF grammar)
       → Smoke gate (post-Coach, catches CLI/runtime divergence)
       → stop_on_failure
```

Each layer catches what the others miss. Run-23 demonstrated Coach
catches Player bugs (real TypeError in `specialist_invocations.py:924`).
FEAT-9DDE run-1 demonstrated smoke gate catches Coach-approved-but-
runtime-broken code (`ModuleNotFoundError: installer`).

## The snapshot workflow

### Where artifacts live

| Type | Path |
|---|---|
| Worktree (live, regenerated each `--fresh`) | `.guardkit/worktrees/{FEAT-XXX}/.guardkit/autobuild/{TASK-XXX}/` |
| Run logs | `docs/reviews/autobuild-migration/autobuild-{FEAT-XXX}-run-{N}.md` |
| **Snapshot path (committed)** | `docs/state/{FEAT-XXX}/run-{N}-artifacts/{TASK-XXX}/` for FEAT-9DDE, `docs/state/TASK-REV-HMIG/run-{N}-artifacts/{TASK-XXX}/` for FEAT-AOF (legacy from when these were HMIG-010 validation runs) |
| Audit trail | `docs/state/TASK-REV-HMIG/{feature-run-incidents.md,feature-run-analysis.md,feature-results.json}` (last updated for run 12; rolling these up post-cutover is a known TODO) |

### What to copy

For each task that ran in the wave, copy ALL `*.json` from
`.guardkit/worktrees/{FEAT}/.guardkit/autobuild/{TASK}/` to the
snapshot path. Files typically include:

- `coach_turn_1.json` (verdict — the headline)
- `player_turn_1.json`, `task_work_results.json`
- `specialist_results.json`, `turn_state_turn_1.json`
- `checkpoints.json`, `state_transitions.json`, `turn_context.json`
- Sometimes `phase_4_summary.json` (Coach reached phase 4)
- Sometimes `coverage_detail.json` (COACHTESTTO output — **see .gitignore note below**)

### `.gitignore` gotcha (FIXED in this session)

The user's `.gitignore` has `coverage*.json` rules that USED to
silently filter `coverage_detail.json` out of snapshot commits.
Just fixed with `!docs/state/**/coverage*.json` exceptions. Should
no longer need `git add -f` for coverage artifacts. **Verify the
exception is in `.gitignore` before each snapshot** — if it got
reverted, `git add -f` is the workaround.

### README structure

Each snapshot has a `README.md` with this rough shape:

1. **TL;DR** — outcome in one line + table
2. **Headline finding(s)** — what's architecturally interesting
3. **Architecture invariants status** — which mechanisms fired
4. **Run progression at a glance** — timeline table
5. **What's in this snapshot** — file inventory
6. **What's NOT in this snapshot** — usually llama.cpp logs on GB10
7. **Diagnostic hypotheses for the GB10 session** — actionable
8. **Cross-reference** — sibling runs + relevant commits/tasks
9. **Suggested next steps** — operator-facing

Length: 150-300 lines is typical. Be substantive but not exhaustive.

### Commit message style

```
docs(FEAT-XXX): snapshot run-N — [one-line headline]

[Multi-paragraph context: outcome, root cause if failure, what
this proves/disproves, architecture invariants status]

Snapshot contents:
- TASK-XXX/ (N files, [characterisation])
- ...

[Suggested next steps]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Push handling

`git push origin main` may reject with non-fast-forward. Standard
recovery:

```bash
git stash push -u -m "transient state"
git pull --rebase origin main
git push origin main
git stash pop
```

The transient state being stashed = orchestrator-written FEAT-AOF.yaml
modifications + DECISION-DF-* dev work + task frontmatters. Stash
is safe.

## The reset workflow

### What needs resetting

After each run, the orchestrator writes:

1. `.guardkit/features/{FEAT}.yaml` — updates each task's `status`,
   `result`, `started_at`, `completed_at` + feature-level `status`
   and `execution` block
2. `tasks/backlog/.../TASK-XXX-*.md` frontmatters — populates
   `autobuild_state` block with turn telemetry

### How to reset

Standard pattern (FEAT-AOF, the user's primary loop):

1. **Edit yaml** to reset all 3 task `status: pending`, null
   `result`/`started_at`/`completed_at`. Reset execution metadata to
   nulls/zeros.
2. **`git checkout HEAD --`** the 2 modified task frontmatters
   (GD02 + TP05 typically; IA03 is in a special state — see below).
3. **PRESERVE `parallel_groups`** — the user has it split into 3
   sequential single-task waves (operator workaround for
   parallel-substrate F23A risk; redundant with `--max-parallel 1`
   now that TASK-FIX-MAXPARALLEL01 landed, but kept for resilience).
4. **Leave alone**:
   - `docs/decisions/DECISION-DF-*` (user's unrelated dev work)
   - `tasks/backlog/TASK-DATA-COACHHARVEST-*` (user's unrelated work)
   - `tasks/backlog/autobuild-observability-fixes/TASK-FIX-IA03-*`
     (special — see below)

### The IA03 special case

IA03 was marked task-completed back in commit `f57c7a85` and moved to
`tasks/completed/TASK-FIX-IA03/TASK-FIX-IA03.md`. The original backlog
file was deleted from HEAD. To allow `--fresh` re-runs:

- A restored copy of the IA03 backlog file lives at
  `tasks/backlog/autobuild-observability-fixes/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md`
  as an **untracked** file (`??` in `git status`)
- The FEAT-AOF.yaml's `file_path` points at this backlog path
- This duplication is acceptable for now; cleanup is a known TODO

Don't try to "clean up" the untracked IA03 backlog file — the next
run needs it there.

### The pre-flight validator pins

The orchestrator's pre-flight validator requires:
- `file_path` to exist (catches `/task-complete`-moved files)
- `file_path` to start with `tasks/backlog/` (the
  `Invalid task file_path` error)

Both apply. The IA03 special case satisfies both.

## Run command (B-full posture)

```bash
GUARDKIT_COACH_GATHER=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature {FEAT-XXX} \
    --fresh --model qwen36-workhorse --coach-model gemma4:31b \
    --task-timeout 4800 --sdk-timeout 3600 --no-context \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/{FEAT-XXX}-run-{N}-stdout.log
```

For FEAT-AOF the log path has been
`.guardkit/autobuild/TASK-REV-HMIG-feature-run/run-{N}-stdout.log`
(legacy). For FEAT-9DDE use `FEAT-9DDE-run-{N}-stdout.log`.

`--max-parallel 1` is optional since TASK-FIX-MAXPARALLEL01 landed
(commit `a83fb2ea`) AND the user's yaml already splits into single-task
waves. Keep it for belt-and-braces if you like.

## Known bugs that surfaced during these runs (some may already be fixed)

| Task ID (filed) | Description | Status |
|---|---|---|
| TASK-FIX-FRESHRESET01 | `--fresh` silently no-ops on previously-completed feature (only clears state when `is_incomplete()`) | Filed, may not have landed |
| TASK-FIX-FEATYAMLPATH01 (suggested, not filed) | `/task-complete` doesn't update downstream feature YAMLs when moving task files out of `tasks/backlog/` | Suggested, see IA03 special case |
| TASK-FIX-WTCLEANUP01 (suggested, not filed) | Worktree auto-cleanup runs `git branch -D` before `git worktree remove` (wrong order) — error message itself documents the bug | Suggested |
| TASK-FIX-MAXPARALLEL01 | `--max-parallel 1` was silently ignored by Wave-level execution | **LANDED** commit `a83fb2ea` |
| TASK-FIX-BACKENDKWARG | `build_autobuild_backend()` cross-repo kwarg mismatch (run 24's 25-second failure) | **LANDED** commit `3efb2562` |
| TASK-PERF-COACHTURNBUDGET | Lever-3 B-full budget design | **LANDED** commit `f4b6422a` |
| TASK-INFRA-CIGREEN | green-gating pytest CI | **LANDED** commit `fe85db6a` |
| TASK-INFRA-XREPOCONTRACT | cross-repo harness contract CI seam test | **LANDED** commit `5b3dff0d` |
| TypeError in `specialist_invocations.py:924` | Coach found in run 23 (Player bug: `'<' not supported between instances of 'int' and 'Mock'`) | Operator probably fixed pre-run-25 since run 25 was 3/3 approve; verify in code if it matters |

## What's NOT to do

- ❌ Don't suggest TASK-HMIG-011 cutover needs more evidence —
  it's ready
- ❌ Don't try to update the audit trail
  (`feature-run-incidents.md`, etc.) on every run — that's a roll-up
  TODO for post-cutover, not per-run
- ❌ Don't run autobuild yourself — the user does this from their
  Mac; you receive the output log
- ❌ Don't touch `docs/decisions/DECISION-DF-*` files (user's
  unrelated dev work)
- ❌ Don't suggest more diagnostics on F20/F21/F22/F23A/F24 — all
  closed
- ❌ Don't suggest `git add -A` or `git add .` — always stage specific
  files. The user's .gitignore is well-tuned; trust it (with the new
  exception for `docs/state/**/coverage*.json` you just added)

## Useful greps for triage

When analysing a run log:

```bash
# Coach verdict shape + outcomes
grep -nE "Completed turn|FEATURE RESULT|Status:|Duration:|Tasks: [0-9]+/[0-9]+|Coach approved|Coach failed|coach_primary_synthetic|APPROVED|TIMEOUT|Wave [0-9] " path/to/run-log.md

# Substrate failures (HTTP 4xx/5xx)
grep -nE "502|503|Connection error|exceed_context|recursion_limit|Phase-A gather failed|degraded" path/to/run-log.md

# Specific task investigation
grep -nE "TASK-XXX.*Coach|TASK-XXX.*Phase" path/to/run-log.md
```

When checking artifact verdict shape quickly:

```bash
python3 -c "
import json
d = json.load(open('.guardkit/worktrees/{FEAT}/.guardkit/autobuild/{TASK}/coach_turn_1.json'))
print(f'decision={d[\"decision\"]}, ACs={len(d[\"validation_results\"][\"requirements_met\"])}, criteria_verification={len(d.get(\"criteria_verification\", []))}')
"
```

## Last known state at handoff

- **Last run**: FEAT-9DDE run-1 (2026-06-11 12:21 UTC) — Wave 1 approve, Wave 2 skipped via smoke-gate-caught-bug
- **Last commit**: `f8e74fa6` — coverage_detail.json patch into FEAT-9DDE run-1 snapshot
- **`.gitignore` exception added** for `docs/state/**/coverage*.json`
  paths (not yet committed at handoff — please commit when you pick up)
- **Working tree at handoff**: `.gitignore` modified (the exception), plus the usual unrelated working-tree modifications (DECISION-DF-*, TASK-DATA-COACHHARVEST, FEAT-AOF.yaml from run 25, IA03 untracked backlog restoration)
- **Cutover status**: TASK-HMIG-011 unblocked, awaiting user execution
- **Next likely user request**: either reset for FEAT-9DDE run-2 (after they land TASK-TSJ-002 or sys.path fix), or move on to TASK-HMIG-011 cutover

## Cross-reference

- Architectural baseline run analyses: [`run-19-artifacts/README.md`](run-19-artifacts/README.md), [`run-20-artifacts/README.md`](run-20-artifacts/README.md), [`run-25-artifacts/README.md`](run-25-artifacts/README.md)
- Bug-class evolution: [`run-21`](run-21-artifacts/README.md) (parallel substrate crash) → [`run-22`](run-22-artifacts/README.md) (F20 returns under B-full) → [`run-23`](run-23-artifacts/README.md) (Coach catches real bug) → [`run-24`](run-24-artifacts/README.md) (kwarg regression) → [`run-25`](run-25-artifacts/README.md) (Lever-3 budget works)
- FEAT-9DDE: [`../FEAT-9DDE/run-1-artifacts/README.md`](../FEAT-9DDE/run-1-artifacts/README.md) — smoke gate caught CLI import bug
- F23 forensics handoff (closed): [`run-11-f23-forensics-handoff.md`](run-11-f23-forensics-handoff.md) — pattern reusable if any 5xx recurs

Good luck. This work has been a marathon and the architecture is in
excellent shape. Most-likely-next request is a reset or a snapshot;
both are well-rehearsed.
