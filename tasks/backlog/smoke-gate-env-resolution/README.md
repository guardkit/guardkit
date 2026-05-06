# FEAT-SGER — Smoke-Gate Environment Resolution

Filed as a follow-up to **specialist-agent** TASK-REV-61F1 (cross-repo).

- Source review: `specialist-agent/.claude/reviews/TASK-REV-61F1-review-report.md`
- Originating failure: `specialist-agent/docs/history/autobuild-FEAT-61F1-failed-history.md` (wave-2 smoke gate)
- Same failure shape previously observed: `specialist-agent/docs/history/autobuild-D40B-history.md` (wave-5 smoke gate)

## Problem Statement

The autobuild orchestrator's post-wave smoke gate has two compounding defects that
together turn correctly-built features into opaque `FAILED` results:

### Defect 1 — Stderr is captured but never surfaced

`guardkit/orchestrator/smoke_gates.py:run_smoke_gate` runs the gate with
`capture_output=True` and stores `proc.stderr` on `SmokeGateResult` (line 253). But
the failure-path log at lines 240–247 emits only:

```
WARNING:guardkit.orchestrator.smoke_gates:Smoke gate failed after wave N (exit=X, expected=Y)
```

The captured exception text is discarded. Operators see a single line with no
diagnostic, and have to manually re-run the gate to learn what actually failed. On
FEAT-61F1 this turned a 30-second diagnosis (a `ModuleNotFoundError`) into a 30-minute
investigation.

### Defect 2 — `_bootstrap_venv_python` is `None` on the macOS happy path

The orchestrator passes `venv_python=self._bootstrap_venv_python` into `run_smoke_gate`
([feature_orchestrator.py:2034](../../../guardkit/orchestrator/feature_orchestrator.py#L2034)),
which prepends the venv's `bin/` to PATH so the gate's bare `python` resolves to the
right interpreter. But `EnvironmentBootstrapper._ensure_venv` only creates a
worktree-local venv at `<worktree>/.guardkit/venv/` on the **PEP 668 fallback path or
uv "no venv discoverable" path** ([environment_bootstrap.py:1395-1428](../../../guardkit/orchestrator/environment_bootstrap.py#L1395-L1428)).

On the macOS happy path, `uv pip install -e .` succeeds against the orchestrator's
**parent shell venv** — the install is fine (the package IS installed and importable
from the orchestrator's `sys.executable`), but `result.venv_python` stays `None`
because no worktree-local venv was created. So `self._bootstrap_venv_python = None`
([feature_orchestrator.py:1376-1391 — the `else` branch](../../../guardkit/orchestrator/feature_orchestrator.py#L1376-L1391)),
and the smoke gate inherits the orchestrator subprocess's PATH unchanged.

The history confirms this: line 32 shows `Running install for python (pyproject.toml): uv pip install -e .`
followed by line 33 `Install succeeded`, and **no** `Coach will verify using interpreter:`
line — the `else` branch was taken.

When PATH ordering doesn't make `python` resolve to the orchestrator's own interpreter
(e.g. because system Python's `/usr/local/bin/` precedes the project venv's `bin/`),
the smoke gate fires against the wrong Python. On FEAT-61F1, that wrong Python had
`specialist_agent` editable-installed pointing at the **main repo's `src/`** instead
of the worktree's, producing the `ModuleNotFoundError` that masked four correct
artefacts.

## Solution Approach

Two independent fixes, each on its own task:

| Wave | Task | Mode | Risk | Description |
|------|------|------|------|-------------|
| 1 | [TASK-SGER-001](TASK-SGER-001-include-stderr-in-failure-log.md) | direct | low | Include captured stdout/stderr in the failure-path WARNING in `smoke_gates.py:240-247` |
| 1 | [TASK-SGER-002](TASK-SGER-002-fallback-venv-python-to-sys-executable.md) | task-work | medium | When `result.venv_python is None` but bootstrap succeeded, fall back to the orchestrator's `sys.executable` so the smoke gate sees the same interpreter that ran the install |

Both can run in parallel — they touch different modules and have no shared state.

SGER-001 is the high-leverage fix: it converts every future opaque `exit=N, expected=Y`
into an immediately-diagnosable failure, regardless of root cause. Worth landing on
its own merit even before SGER-002 is designed.

SGER-002 is the structural fix: it closes the actual environmental resolution gap so
the next autobuild on a similar feature shape doesn't repeat FEAT-61F1's experience.

## Cross-Repo Context

The originating review lives in the **specialist-agent** repo. The fix-forward for
FEAT-61F1's content (landing the worktree to main, running the test suite) is also
in that repo as `feat-61f1-fix-forward/TASK-AKQT-006`. That fix-forward does NOT
depend on SGER landing — it bypasses the orchestrator. SGER is needed to prevent
**future** features from hitting the same gap.
