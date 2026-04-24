# Implementation Guide: AutoBuild SDK Stall Resilience (FEAT-7A00)

## Quick Reference

- **Waves**: 2
- **Parallelism**: Wave 1 has 4 disjoint-file subtasks → all run in parallel
  Conductor workspaces. Wave 2 has 2 subtasks that rebase on Wave 1 output
  (shared-file dependencies).
- **Testing depth**: `default-by-complexity` (Q3 selection). Concretely:
  - Complexity 2 → minimal (compile + smoke)
  - Complexity 3–4 → standard (≥80% coverage on changed lines + arch review)
  - Complexity 5 → standard/strict (add focused edge-case tests for
    streaming & interpreter-selection seams)

## Wave 1 — Parallel, disjoint files

Each of these can be started in its own Conductor workspace without rebase:

### W1-1 · TASK-FIX-7A01 — Pin SDK + version log

- Workspace: `autobuild-sdk-stall-resilience-w1-1`
- Command: `/task-work TASK-FIX-7A01`
- Touches:
  - `pyproject.toml` (two extras)
  - `requirements.txt`
  - `installer/scripts/install.sh`
  - `guardkit/orchestrator/autobuild.py` (**startup-log site only** — do not
    touch the final-summary region; that's W2-1's)
- Gate: unit test asserting the startup log line is produced.

### W1-2 · TASK-FIX-7A03 — Defensive SDK message handling

- Workspace: `autobuild-sdk-stall-resilience-w1-2`
- Command: `/task-work TASK-FIX-7A03`
- Touches:
  - `guardkit/orchestrator/agent_invoker.py` (`_invoke_with_role`
    streaming + catch cascade)
  - `guardkit/orchestrator/exceptions.py` if `AgentInvocationError`
    gains `error_class`
- Gate: simulated-stream tests (unknown-message + all-unknown + ValueError).
- **Important**: before implementing, check whether `claude_agent_sdk`
  exposes a stream-level `strict=False` flag; prefer that if so.

### W1-3 · TASK-FIX-7A04 — Bootstrap hard-fail gate

- Workspace: `autobuild-sdk-stall-resilience-w1-3`
- Command: `/task-work TASK-FIX-7A04`
- Touches:
  - `guardkit/orchestrator/feature_orchestrator.py` (**bootstrap-gate
    decision site only** — don't touch Coach instantiation; that's W2-2's)
  - `guardkit/orchestrator/environment_bootstrap.py` if `BootstrapResult`
    needs the essential-stack classification
  - `guardkit/cli/autobuild.py` (CLI flag plumbing)
  - `.guardkit/config.yaml` schema additions (if applicable)
- Gate: 4-branch unit test (block+fail, block+pass, warn+fail, warn+pass).

### W1-4 · TASK-DOC-7A06 — Runbook + graph seed

- Workspace: `autobuild-sdk-stall-resilience-w1-4`
- Command: this is a `direct`-mode doc task; either `/task-work
  TASK-DOC-7A06` (will skip code-path gates) or edit manually + mark complete.
- Touches:
  - `docs/guides/autobuild-instrumentation-guide.md`
  - `CLAUDE.md` (Key References table)
  - Graphiti: one `add_memory` call to `guardkit__project_decisions`
- Gate: doc file exists, contains triage table; `guardkit graphiti search
  "player invocation stall"` returns ≥1 result.

## Wave 2 — Rebase on Wave 1

These share files with Wave 1; they should be started after the Wave 1
workspaces have merged or at least produced reviewable PRs.

### W2-1 · TASK-FIX-7A02 — Player-invocation-stall classification

- Workspace: `autobuild-sdk-stall-resilience-w2-1`
- Command: `/task-work TASK-FIX-7A02`
- Depends on: TASK-FIX-7A01 (same file — `autobuild.py` — startup log vs.
  final-summary region). Also **consumes** the `error_class` signal
  introduced by TASK-FIX-7A03 (Wave 1 parallel); if the error_class field is
  not yet merged, fall back to string-matching on
  `type(e).__name__` in the error message.
- Touches:
  - `guardkit/orchestrator/autobuild.py` (final-summary / hint block
    ≈ lines 4538–4561; decision-label enum where `unrecoverable_stall`
    is defined)
  - `tests/orchestrator/test_stall_classification.py` (new or extended)
- Gate: replay of the two saved transcripts produces
  `player_invocation_stall`.

### W2-2 · TASK-FIX-7A05 — Wire venv to Coach pytest

- Workspace: `autobuild-sdk-stall-resilience-w2-2`
- Command: `/task-work TASK-FIX-7A05`
- Depends on: TASK-FIX-7A04 (same file — `feature_orchestrator.py` — gate
  logic vs. Coach constructor plumbing).
- Touches:
  - `guardkit/orchestrator/coach_verification.py`
  - `guardkit/orchestrator/feature_orchestrator.py` (Coach instantiation)
  - `guardkit/orchestrator/autobuild.py` (same — if Coach is instantiated
    there too)
  - `guardkit/orchestrator/environment_bootstrap.py` — confirm
    `BootstrapResult.venv_python` exists; add if not
  - `tests/orchestrator/test_coach_interpreter_selection.py` (new)
- Gate: argv-shape test + non-Python-stack regression test.

## Feature-Level Verification

After all subtasks merge, verify feature-level acceptance with:

1. **Transcript replay** — a small script that feeds the two
   `docs/reviews/bdd-acceptance-wired-up/forge-run-[1-2].md` turn records
   into the orchestrator's final-summary classifier and asserts
   `player_invocation_stall` is emitted with the new hint. (Can be a
   pytest in `tests/orchestrator/`.)
2. **Live GB10 verification** (manual) — after upgrading
   `claude-agent-sdk` on GB10 per TASK-FIX-7A01's runbook entry:
   - re-run `guardkit autobuild feature FEAT-FORGE-002 --verbose`
   - confirm Wave 1 turn 1 does **not** emit
     `Unknown message type: rate_limit_event`
   - Player actually runs (turn 1 produces a real report, not synthetic)
3. **Macbook regression check** — rerun an already-working feature (e.g.
   `FEAT-J002` on jarvis) on macbook to confirm the SDK pin doesn't break
   the currently-passing environment.

## Execution Strategy

Recommended order (given Q2=Parallel):

```
Time ─────────────────────────────────────────────►

Wave 1:  ├──W1-1 (R1)──────────────┤
         ├──W1-2 (R3)──────────────┤       ← all parallel Conductor workspaces
         ├──W1-3 (R4a)─────────────┤
         ├──W1-4 (R5+R6 docs)──┤

Wave 2:                               ├──W2-1 (R2)───────────┤  ← rebase autobuild.py
                                      ├──W2-2 (R4b)──────────┤  ← rebase feature_orch.py
```

## Rollback / Risk Management

- **TASK-FIX-7A03** is the riskiest change (stream semantics). If the
  per-message try/except produces false-positive "partial success" turns,
  gate it behind a config flag
  `autobuild.sdk_strict_stream: true (default)` that preserves current
  behavior; flip to `false` to opt into drop-and-warn.
- **TASK-FIX-7A04** is behavior-compatible by default
  (`bootstrap_failure_mode: "warn"`); risk is low.
- **TASK-FIX-7A05** preserves PATH fallback when no venv exists — no
  regression on non-Python stacks if the resolution order is respected.
- **TASK-FIX-7A01** could overly constrain users if the upper bound is
  too tight. Pin to `<0.2` (or whatever the next-major-risk boundary is
  per SDK CHANGELOG) rather than a patch-level cap.

## Completion

When all six subtasks are in `completed/`:

```bash
/task-complete TASK-REV-E4F5
```

…and update the review task's `status: review_complete` → `completed`,
plus capture feature-level outcome to Graphiti under
`guardkit__task_outcomes` (FEAT-7A00).
