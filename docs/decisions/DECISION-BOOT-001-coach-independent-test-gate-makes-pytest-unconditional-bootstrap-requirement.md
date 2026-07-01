# DECISION-BOOT-001 — Coach Independent-Test Gate Makes pytest an Unconditional Bootstrap Requirement for Python AutoBuild Features

**Status:** ACCEPTED (implemented) · **Date:** 2026-06-12 · **Task:** TASK-FIX-BOOTPYTEST01 · **Commit:** `12b031124`

## Context

The autobuild Coach runs an **independent test gate** — it re-runs `pytest` in the
feature worktree's bootstrap venv for *every* Python task, pinning the interpreter
to the bootstrap-provided venv Python (`_resolve_venv_python`, defined in
`guardkit/orchestrator/coach_verification.py:35` and reused by the deterministic
`CoachValidator` at `guardkit/orchestrator/quality_gates/coach_validator.py:1468`,
per TASK-FIX-COACHPYENV, commit `0499bfb4f`). This "trust but verify" step is
unconditional; it does not depend on any operator configuration.

But bootstrap-extras resolution did not know that. Before this change,
`derive_bootstrap_extras()` only installed a test extra (`[dev]` / `[test]`) into
the worktree venv under two conditions: the operator explicitly declared
`feature.bootstrap_extras`, or the feature configured a pytest smoke gate (whose
command matched `\bpytest\b`). A Python feature that declared **neither** got
`pip install -e .` with no extras — so `pytest` never landed in the venv the Coach
was pinned to.

The failure surfaced in **FEAT-E2CB run-1**: the feature declared no
`bootstrap_extras` and no pytest smoke gate, so the Coach's pinned interpreter
could not `import pytest` and reported *"missing pytest dependency"* on turns 1-2.
The run burned early turns (contributing to a timeout) until the Player
*incidentally* installed pytest during implementation. The root cause was
bootstrap-missing-test-deps, not an interpreter race — bootstrap is synchronous
and completes before Wave 1.

## Decision

For Python autobuild features, a pytest-providing test extra must be installed
into the worktree venv **regardless** of whether the operator declared
`bootstrap_extras` or configured a pytest smoke gate. A test-capable interpreter
is a guaranteed requirement of the always-on Coach gate, not an opt-in keyed on
smoke-gate config.

This is realised as **resolution branch 3** ("Coach-always-needs-pytest") of
`derive_bootstrap_extras()`, run after the operator-declared (branch 1) and
smoke-gate (branch 2) branches fall through. Branch 3 probes the same
`[dev]`-then-`[test]` candidates, but gated by a **content-aware**
`_extra_provides_pytest()` guard: it auto-adds an extra only if that extra's
requirement list demonstrably carries pytest (a `\bpytest\b` word-boundary match,
which also accepts plugins such as `pytest-bdd` / `pytest-asyncio`). A `[dev]`
group of only linters (e.g. `ruff`, `mypy`) is deliberately **not** force-added.

## Rationale

- **Match the install surface to the always-on gate.** The Coach verifies with
  pytest unconditionally, so the interpreter must be test-capable from turn 1.
  Keying the install on smoke-gate/operator config left a structural blind spot
  whenever both signals were absent — exactly the FEAT-E2CB case.
- **Precision guard over blanket install.** Branch 2 (smoke gate) trusts an
  operator's explicit pytest command and can install the canonical extra *by
  name*. Branch 3 has no operator signal, so a *by-name* `[dev]` install would be
  too coarse — it would force-add a linter-only `[dev]`. The content-aware
  `_extra_provides_pytest` filter installs an extra only when it actually carries
  the pytest toolchain, avoiding false positives.
- **Inverse-direction complement to `absence-of-failure-is-not-success`.** That
  rule keeps the Coach from *approving* when it could not verify (an absent oracle
  signal must not read as a pass). This decision approaches the same "the Coach
  must be able to verify" concern from the other side: ensure the Coach *can*
  verify (pytest present) from turn 1, rather than being structurally blind on
  early turns and burning turns until the Player incidentally installs pytest.
- **Supersedes the narrower prior assumption.** TASK-GK-BS-001 AC-6 encoded a
  "no operator declaration and no pytest smoke gate → no extras" negative case.
  For the pytest-providing case, branch 3 now overrides that: the Coach's
  unconditional gate is the missing signal AC-6 did not account for.

## Consequences / Implementation

- `guardkit/orchestrator/feature_loader.py`:
  - `derive_bootstrap_extras()` (`:1693`) — branch 3 loop over
    `_AUTO_DETECT_EXTRA_CANDIDATES` (`[dev]` then `[test]`), returning the first
    candidate for which `_extra_provides_pytest` is true (`:1785-1794`).
  - `_extra_provides_pytest()` (`:1654`) — the content-aware guard; reuses
    `_PYTEST_COMMAND_PATTERN = re.compile(r"\bpytest\b", re.IGNORECASE)` (`:1615`)
    against each requirement string in the extra's dependency list.
- The function stays **pure** (no mutation of `feature`, nothing persisted back to
  YAML): the orchestrator re-derives extras at every bootstrap, keeping the
  operator-declared field unambiguous.
- Note the precedence ordering: branch 1 (operator-declared) and branch 2
  (smoke-gate) still win first, so an explicit operator list or a named smoke-gate
  extra is unaffected. Branch 3 only fires when both fall through.
- Tests: `tests/unit/orchestrator/test_environment_bootstrap_extras.py` — new
  `TestCoachAlwaysNeedsPytest` (8 tests) plus an end-to-end install-command
  assertion; three branch-2 fixtures were isolated to non-pytest extras to
  preserve their original intent.

## References

- **Task:** `tasks/completed/autobuild-harness-migration/TASK-FIX-BOOTPYTEST01-worktree-venv-missing-pytest-on-early-coach-turns.md`
- **Commit:** `12b031124` — *fix(bootstrap): install pytest extra for Coach independent-test gate (TASK-FIX-BOOTPYTEST01)*
- **Related task (interpreter pinning):** TASK-FIX-COACHPYENV (commit `0499bfb4f`) — pins Coach independent tests to the bootstrap venv interpreter via `_resolve_venv_python`.
- **Superseded assumption:** TASK-GK-BS-001 AC-6 — `tasks/completed/2026-05/TASK-GK-BS-001/TASK-GK-BS-001-bootstrap-extras-for-smoke-gate-deps.md` (introduced branches 1-2 of `derive_bootstrap_extras`).
- **Sibling rule (inverse direction):** `.claude/rules/absence-of-failure-is-not-success.md`.
