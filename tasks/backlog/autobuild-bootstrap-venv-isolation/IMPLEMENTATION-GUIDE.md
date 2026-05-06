# Implementation Guide: FEAT-FFC6 — Autobuild Worktree Venv Isolation

**Feature ID:** FEAT-FFC6
**Parent review:** [TASK-REV-FFC6](../../in_review/TASK-REV-FFC6-autobuild-bootstrap-leaks-worktree-into-parent-venv.md)
**Review report:** [.claude/reviews/TASK-REV-FFC6-review-report.md](../../../.claude/reviews/TASK-REV-FFC6-review-report.md)

## Wave Breakdown

```
Wave 1 (sequential):
  └─ TASK-FIX-FF61: Bootstrap worktree-venv isolation
     ├─ R1: Eager worktree-local venv + env override on first try, all 3 install paths
     ├─ R3: Test invariant fix (test_preexisting_venv_succeeds_without_retry + siblings)
     └─ Replace false-success block at line 1239 with BootstrapEnvironmentLeakError invariant

Wave 2 (sequential, depends on Wave 1):
  └─ TASK-FIX-FF62: /feature-complete detect-and-warn on dangling .pth references
     └─ Pre-cleanup .pth scanner; warns but does not abort; one-line repair command per match
```

## Why Sequential

Layer 3 (FF62) is defense-in-depth on top of Layer 1 (FF61). FF61 should make FF62's warning unreachable for new runs. Running them in parallel introduces:
- Merge risk: both tasks may want a shared utility for "scan editable .pth files" — FF62 should reuse anything FF61 introduces (e.g. a `worktree_path_in_pth_files()` helper).
- Test conflict: FF62's e2e test depends on FF61 having landed (it relies on the worktree-local venv existing).
- Review burden: a Layer 3 warning shipped without Layer 1 would be confusing — it would fire on every fresh autobuild.

Net: ~30 minutes saved by parallel execution is dwarfed by merge risk and review overhead.

## Pre-Implementation Reading (mandatory)

Both tasks must:
1. Read [the review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md) — especially Sequence Diagrams 1-5 (current bug paths) and Sequence Diagram 5 (Layer 1 fixed flow).
2. Read [.claude/rules/absence-of-failure-is-not-success.md](../../../.claude/rules/absence-of-failure-is-not-success.md) — the false-success block at line 1239 is a textbook instance.
3. Read [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md) — parent venv is an externally-defined namespace.

## Critical Don't-Break Targets

These tests/behaviours must continue to pass:

| Target | File | What it guards |
|--------|------|----------------|
| PEP 668 fallback | [test_environment_bootstrap.py:1677](../../../tests/unit/test_environment_bootstrap.py#L1677) | `<worktree>/.guardkit/venv/` creation when host Python is externally-managed |
| AB60 uv-no-venv retry | [test_environment_bootstrap_uv_venv.py:118](../../../tests/unit/test_environment_bootstrap_uv_venv.py#L118) | `<worktree>/.venv` creation when uv emits "No virtual environment found" |
| FD32 uv-sync routing | [test_environment_bootstrap_uv_venv.py:182](../../../tests/unit/test_environment_bootstrap_uv_venv.py#L182) | `uv sync --frozen` is NOT intercepted by the AB60 retry |
| F09A2 uv-sources detection | [environment_bootstrap.py:686](../../../guardkit/orchestrator/environment_bootstrap.py#L686) | `[tool.uv.sources]` correctly routes to `uv pip install` |
| A7B6 extras install | [tasks/backlog/TASK-FIX-A7B6...](../TASK-FIX-A7B6-bootstrap-install-optional-extras.md) | Sequence FFC6 first; A7B6 lands extras into the FFC6 worktree venv |
| Coach pytest interpreter | [coach_verification.py:29](../../../guardkit/orchestrator/coach_verification.py#L29) | `_resolve_venv_python` continues to find the venv via explicit param OR `<worktree>/.guardkit/venv/bin/python`. After FFC6, ALSO via `<worktree>/.venv/bin/python` (or directly via `BootstrapResult.venv_python`). |

## Implementation Hints

### TASK-FIX-FF61

The retry block at [environment_bootstrap.py:1664-1671](../../../guardkit/orchestrator/environment_bootstrap.py#L1664-L1671) is the template — copy its env-construction shape to a helper:

```python
def _isolated_env(self, worktree_venv: Path) -> Dict[str, str]:
    """Subprocess env that forces VIRTUAL_ENV to the worktree-local venv.

    Strips inherited VIRTUAL_ENV first so we never accidentally fall through
    to the parent shell's venv even if a future uv version changes precedence.
    """
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["VIRTUAL_ENV"] = str(worktree_venv)
    env["PATH"] = (
        str(worktree_venv / "bin") + os.pathsep + env.get("PATH", "")
    )
    return env
```

Apply to **every** `subprocess.run` in `_run_install` and `_run_single_command` for Python installs — first try AND retry.

For the pip path ([line 704](../../../guardkit/orchestrator/environment_bootstrap.py#L704)), replace `cmd[0] = sys.executable` with `cmd[0] = str(worktree_venv / "bin" / "python")` BEFORE `subprocess.run`. (Existing logic at [line 1567-1568](../../../guardkit/orchestrator/environment_bootstrap.py#L1567-L1568) already does this when `self._venv_python` is set; the change is to set it eagerly for ALL Python installs, not only after PEP 668.)

The false-success block at [line 1239-1249](../../../guardkit/orchestrator/environment_bootstrap.py#L1239-L1249) becomes:
```python
if (
    overall_success
    and any(m.stack == "python" for m in manifests)
    and self._venv_python is not None
    and not str(self._venv_python).startswith(str(self._root))
):
    raise BootstrapEnvironmentLeakError(
        f"Python install completed but interpreter "
        f"{self._venv_python} is outside worktree {self._root}. "
        f"Refusing to claim success — this would silently corrupt "
        f"the parent venv. See "
        f".claude/reviews/TASK-REV-FFC6-review-report.md."
    )
```

### TASK-FIX-FF62

The `.pth` scanner is read-only; it must never abort cleanup. Sample shape:

```python
def find_pth_leaks(repo_root: Path, worktree_path: Path) -> List[Tuple[Path, str]]:
    """Find editable .pth files referencing worktree_path.

    Returns (pth_file, line) tuples; empty list when clean.
    Read-only; never raises. Symlinks NOT followed.
    """
    leaks: List[Tuple[Path, str]] = []
    scan_roots = [
        repo_root / ".venv",
        repo_root / ".guardkit" / "venv",
    ]
    needle = str(worktree_path)
    for venv_root in scan_roots:
        if not venv_root.is_dir():
            continue
        try:
            for pth in venv_root.glob("lib/python*/site-packages/_editable_impl_*.pth"):
                try:
                    for line in pth.read_text().splitlines():
                        if needle in line:
                            leaks.append((pth, line.strip()))
                            break
                except OSError:
                    continue
        except OSError:
            continue
    return leaks
```

Wire into the cleanup flow at [cli/autobuild.py](../../../guardkit/cli/autobuild.py) — find the `WorktreeManager.cleanup` call site, scan immediately before it, print per-leak warning, then proceed.

## Verification (post-merge)

After both tasks merge, run:

```bash
# 1. Full bootstrap test suite (all four files)
pytest tests/unit/test_environment_bootstrap.py \
       tests/unit/test_environment_bootstrap_uv_venv.py \
       tests/unit/test_environment_bootstrap_fix7539.py \
       tests/orchestrator/test_bootstrap_gating.py -v

# 2. End-to-end smoke (manual, slow tier)
#    From a fresh clone with an active parent .venv:
guardkit autobuild feature FEAT-NOOP   # any small no-op feature
/feature-complete FEAT-NOOP
test -z "$(grep -l "$(pwd)/.guardkit/worktrees" .venv/lib/python*/site-packages/*.pth 2>/dev/null)"
echo $?  # MUST print 0

# 3. Coach pytest interpreter check
#    Inspect a fresh autobuild log for "Coach pytest interpreter set from
#    bootstrap venv: <worktree>/.venv/bin/python" — NOT the parent venv path
#    and NOT sys.executable.
```
