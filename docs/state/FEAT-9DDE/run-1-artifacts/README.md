# Run-1 FEAT-9DDE autobuild artifacts snapshot — smoke gate catches import-path bug post-Coach approval

> **Purpose**: snapshot the FEAT-9DDE artifact tree from run 1 — a
> DIFFERENT feature from FEAT-AOF (the `/task-status --json`
> deterministic producer script, planned in commit `1af525fb`). First
> autobuild test of FEAT-9DDE after FEAT-AOF's cutover-baseline
> validation (runs 19, 20, 25).
>
> **Source**: live worktree artifacts copied 2026-06-11T12:40Z.
> **Run log**:
> [`autobuild-FEAT-9DDE-run-1.md`](../../../reviews/autobuild-migration/autobuild-FEAT-9DDE-run-1.md)
> (committed in the same change as this snapshot).

## TL;DR — Wave 1 ✓ approve; Wave 2 never started because smoke gate caught real bug

```
FEATURE RESULT: FAILED
Status: FAILED
Tasks: 1/2 completed
Duration: 18m 48s
```

| Task | Wave | Outcome | Notes |
|---|---|---|---|
| TASK-TSJ-001 | 1 | ✓ Coach approved, 10/10 ACs, populated `criteria_verification` (10 entries) | Player created 36 files, schema-valid B-full→B-min verdict |
| TASK-TSJ-002 | 2 | ⏭ never started | `stop_on_failure=True` halted execution after smoke-gate failure |

The "FAILED" is misleading at the architecture level — **Wave 1's
Coach approved correctly on its own merits**, and the smoke gate then
caught a *separate* infrastructure bug that the unit tests didn't
surface. That's adversarial-cooperation working at multiple layers.

## 🎯 The architectural win — smoke gate caught what tests missed

After Wave 1's Coach approval, the orchestrator's smoke gate ran
([run-1 log:275-276](../../../reviews/autobuild-migration/autobuild-FEAT-9DDE-run-1.md#L275)):

```bash
python3 installer/core/commands/lib/task_status_json.py --base-path . \
  | python3 -m json.tool > /dev/null
(cwd=.../worktrees/FEAT-9DDE, timeout=120s, expected_exit=0)
```

Outcome: exit=1, with stderr:

```
Traceback (most recent call last):
  File ".../installer/core/commands/lib/task_status_json.py", line 29, in <module>
    from installer.core.commands.lib.task_utils import parse_task_frontmatter
ModuleNotFoundError: No module named 'installer'
```

**The unit tests passed cleanly** (21/21 in
`tests/unit/commands/test_task_status_json.py`) because pytest
auto-resolves `installer.*` imports from the package layout. But the
CLI invocation pattern (`python3 installer/core/commands/lib/...py`)
doesn't add the repo root to `sys.path`, so the import fails.

This is a **classic test/runtime divergence**: the tests prove the
*function* works, but the *CLI invocation* doesn't because the package
isn't installed or sys.path-extended. Two ways to fix:

1. **(preferred)** Add a proper bin entry / pyproject.toml CLI shim
   so `task-status-json` is installed as an executable. This is what
   TSJ-002 is meant to do ("register-bin-entry-and-wire-specs").
2. **(quick)** Have the script add the repo root to sys.path on import
   if running as `__main__`.

The smoke gate's job is exactly this — catch the runtime/packaging
divergence before merge. **It did its job.** The "FAILED" status is
correct: the feature isn't ready, even though Wave 1's implementation
is sound.

## 🎯 Architectural cooperation across multiple layers

This run demonstrates the full adversarial-cooperation chain working:

| Layer | Mechanism | Outcome on this run |
|---|---|---|
| Player | task-work delegation (qwen36-workhorse) | ✓ Created 36 files implementing TSJ-001 |
| test-orchestrator specialist | SPECHANG hang detected | ✓ contained by SPECCOCH01 (specialist failure didn't block Coach) |
| Coach quality gates | independent tests + coverage + audit | ✓ All passed |
| Coach (B-full → B-min) | Phase-A degrade → grammar-enforced synthesis | ✓ approve with 10/10 `criteria_verification` |
| **Smoke gate (post-Coach, post-wave)** | **deterministic CLI smoke runs the actual script** | **✗ caught import bug Coach + tests missed** |
| stop_on_failure | halt orchestration | ✓ Wave 2 (TSJ-002) correctly didn't start |

Each layer caught what the others couldn't. The smoke gate is the
last line of defence against test/runtime divergence — and it fired
exactly when it should have.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Feature start | 12:21:03 UTC | task budget 4800s × 2 |
| Wave 1 / TSJ-001 Player | → 12:31:51 (~11m) | ✓ 36 files created |
| Wave 1 / TSJ-001 SPECHANG specialist | → 12:34 (~2.5m) | contained |
| Wave 1 / TSJ-001 Coach (B-full → B-min) | → 12:39:45 (~5m) | ✓ APPROVE, 10/10 ACs, populated criteria_verification |
| **Wave 1 smoke gate** | ~12:39:46 | ✗ ModuleNotFoundError: installer |
| Wave 2 / TSJ-002 | not started | stop_on_failure halted |
| FEATURE | FAILED (correctly) | 18m 48s |

## What's in this snapshot

### `TASK-TSJ-001/` — 9 files (Wave 1 success)

The same canonical set as recent FEAT-AOF snapshots, plus a new artifact:

| File | Notes |
|---|---|
| `coach_turn_1.json` | Real approve verdict, 10/10 ACs, **10 entries in `criteria_verification`** |
| **`coverage_detail.json`** | **New artifact — coverage detail emitted alongside the verdict** |
| `phase_4_summary.json` would be here but isn't — Coach approved via Phase-4 quality gates inline |
| `player_turn_1.json`, `task_work_results.json` | Player output for the 36 files |
| `specialist_results.json` | test-orchestrator specialist (SPECHANG contained) |
| `turn_state_turn_1.json`, `checkpoints.json` | Orchestrator's post-turn-1 record |
| `turn_context.json`, `state_transitions.json` | per-thread loader + state-bridge |

### What's NOT in this snapshot

- TASK-TSJ-002 artifacts — never ran due to stop_on_failure
- The smoke-gate stderr/stdout itself is in the run log, not a
  separate artifact. Worth noting for future smoke-gate diagnostic
  improvement (a captured smoke-gate report file in the worktree
  could complement the inline log lines).

## Diagnostic hypotheses for the GB10 session

This run is mostly a **success story for the multi-layer adversarial-
cooperation design**, not a regression. The action items are
forward-looking:

1. **Fix the import path in `task_status_json.py`** — either land
   TSJ-002 first (bin entry + pyproject.toml shim), OR add a
   `sys.path` setup at the top of the script when running as `__main__`.
   Once fixed, re-run FEAT-9DDE.

2. **Worth flagging**: the test failure mode is "unit tests pass via
   pytest's package magic, but CLI invocation fails because the
   package isn't installed". Consider whether Coach's evidence-bundle
   could include a "does this run as a CLI?" smoke check by default,
   not just rely on the orchestrator-level smoke gate. That would
   surface the issue earlier (during Coach validation rather than
   post-approval).

3. **Smoke-gate artifact**: consider persisting smoke-gate stdout/stderr
   to `phase_5_smoke_gate.json` (or similar) in the autobuild dir, so
   future runs can compare smoke outcomes alongside the Coach verdicts.
   Right now it's only in the orchestrator log.

## Cross-reference

- **FEAT-9DDE planning commit**: `1af525fb feat(FEAT-9DDE): plan /task-status --json via deterministic producer script`
- **Cutover-baseline runs** (FEAT-AOF): runs 19, 20, 25
- **Run-25 README** (latest FEAT-AOF success): the Lever-3 budget
  shape this run inherits (`GUARDKIT_COACH_GATHER=1`, B-full → B-min
  graceful-degradation)
- **TASK-TSJ-002** task file: `tasks/backlog/...` (the next task that
  will register the bin entry + wire specs)

## Suggested next steps

1. **Land TASK-TSJ-002** (or a quick sys.path fix in
   `task_status_json.py`) to resolve the smoke-gate failure.
2. **Re-run FEAT-9DDE** with the standard B+C posture:
   ```bash
   GUARDKIT_COACH_GATHER=1 GUARDKIT_HARNESS=langgraph \
     OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
     OPENAI_API_KEY=llama-swap-local-key \
     guardkit autobuild feature FEAT-9DDE --fresh ... \
     2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/FEAT-9DDE-run-2-stdout.log
   ```
3. The FEAT-AOF cutover decision (TASK-HMIG-011) is independent of
   FEAT-9DDE — the FEAT-AOF baseline (run 25) is unchanged by this
   run.
