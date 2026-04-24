---
id: TASK-FIX-7A04
title: Add bootstrap_failure_mode gate so 0/N install success can hard-fail (+ requires-python pre-check)
status: backlog
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T14:00:00Z
priority: medium
tags: [autobuild, environment-bootstrap, orchestrator, configuration, requires-python, preflight]
parent_review: TASK-REV-E4F5
additional_review: TASK-REV-JMBP
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-w1-3
complexity: 4
depends_on: []
---

# Task: Bootstrap hard-fail gate when essential stacks fail

## Description

Address review TASK-REV-E4F5 finding **F6** and recommendation **R4a**.
Currently `guardkit/orchestrator/feature_orchestrator.py` calls
`self._bootstrap_environment(worktree)` at two sites (≈ lines 713–726 and
1330–1360) and **discards the returned `BootstrapResult`**. The only
observable effect of `0/N succeeded` is a yellow-`⚠` console line:
`Environment bootstrap partial: 0/1 succeeded`.

For the forge/GB10 case the bootstrap fails because forge requires Python ≥3.13
and GB10 runs 3.12 — but AutoBuild proceeds to Wave 1 regardless. In the
FEAT-FORGE-002 incident this wasn't causal (Player failed before the venv
was exercised), but it is a latent foot-gun: the user gets no loud signal
that the environment is broken, and Coach (TASK-FIX-7A05) will later run
tests against the wrong interpreter.

Grep for `strict_bootstrap` / `bootstrap_required` / `fail_on_bootstrap`:
no such configuration exists today.

## Acceptance Criteria

- [ ] New configuration knob `bootstrap_failure_mode: "block" | "warn"`,
      default `"warn"` (preserves current behavior for existing users).
      Readable from feature-level config / CLI flag. Where it should live:
      `.guardkit/config.yaml` at the repo root, with a CLI override.
- [ ] When `mode == "block"` AND `installs_attempted > 0` AND
      `installs_failed == installs_attempted` (i.e. zero partial success)
      AND at least one detected stack is declared essential (default: all
      detected stacks are essential unless explicitly marked optional):
      - raise `FeatureOrchestrationError` with message containing:
        - the list of attempted stacks
        - the PEP-668 stderr excerpt from `BootstrapResult`
        - the `requires-python` (if any) from the manifest
        - a hint: _"Set `bootstrap_failure_mode: warn` to override."_
      - do **not** proceed to Wave 1.
- [ ] When `mode == "warn"` (default), behavior is unchanged from today
      (yellow-⚠ line, continue). **No existing test should regress.**
- [ ] When `mode == "block"` AND bootstrap succeeded (or partially succeeded
      with ≥1 install) → behavior unchanged from today.
- [ ] Unit tests:
      1. `mode=block` + zero success + essential stack → raises
      2. `mode=block` + partial success → proceeds (warning logged)
      3. `mode=warn` + zero success → proceeds (today's behavior)
      4. Config plumbing: CLI flag overrides yaml default.
- [ ] Documentation: a short section in
      `docs/guides/autobuild-instrumentation-guide.md` explaining the flag
      and when to use `block` (coordinate with TASK-DOC-7A06).

### Amendment per TASK-REV-JMBP Workstream E (added 2026-04-24)

The MacBook Pro jarvis FEAT-J002 run surfaced a second hazard that fits the
same gate: pip's error message for an interpreter/requires-python mismatch
is opaque ("Package 'jarvis' requires a different Python: 3.14.2 not in
'<3.13,>=3.12'"), and users hitting it lose diagnostic time. Pre-checking
*before* pip avoids the pip-stderr dump and gives clean guidance.

- [ ] **AC-REQPY-PRECHECK** — Before invoking `pip install -e .` (or
      equivalent) for any Python-stack bootstrap target, read the manifest's
      `requires-python` specifier (from `pyproject.toml` `[project]` or
      `tool.poetry.python`) and compare against `sys.version_info` of the
      active interpreter. If the active interpreter does not satisfy the
      specifier:
        - In `mode == "warn"`: emit a structured warning
          "Python {active_version} does not satisfy requires-python=
          `{specifier}`; pip install is expected to fail" and continue
          (pip will emit its own error shortly after).
        - In `mode == "block"`: raise `FeatureOrchestrationError` with a
          message suggesting remediation:
          "Install a compatible interpreter with one of:
          `uv python install 3.12`, `pyenv install 3.12.6 && pyenv local 3.12.6`,
          or `conda create -n <name> python=3.12 && conda activate <name>`"
          (list the top N suggestions; do not try to auto-detect the
          available package manager).
      Skip the pre-check gracefully if `packaging.specifiers` is unavailable
      or the manifest has no `requires-python` (fall through to pip and let
      it be authoritative).
- [ ] Unit test covering: active interpreter satisfies / doesn't satisfy
      specifier; `mode=block` blocks with the remediation hint; `mode=warn`
      proceeds with a structured warning line; missing `requires-python`
      skips the check silently.
- [ ] Integration-style fixture: replay the jarvis pyproject.toml
      (`<3.13,>=3.12`) against Python 3.14 → assert block path fires with
      the expected message; against Python 3.12 → assert proceed path.

## Files

- `guardkit/orchestrator/feature_orchestrator.py` (both call sites:
  ≈ 713–726 initial bootstrap, ≈ 1330–1360 inter-wave bootstrap)
- `guardkit/orchestrator/environment_bootstrap.py` (if the decision logic
  belongs in `BootstrapResult`)
- `guardkit/config/` or wherever feature-level config is parsed — confirm
  the existing shape before adding the field.
- CLI entry: `guardkit/cli/autobuild.py` (flag plumbing).
- `tests/orchestrator/test_bootstrap_gating.py` (new).

## Implementation Notes

- Do **not** break existing call sites that pass `relevant_stacks`
  (environment_bootstrap.py:652) — the gate should compose with that,
  not replace it.
- The essential-vs-optional distinction of a stack is out of scope for
  this task; default all detected stacks essential. If the repo has an
  existing mechanism (e.g. `optional_stacks: [...]` in `.guardkit/config.yaml`)
  honor it; otherwise just take "all detected".
- Error message should be actionable: tell the user what interpreter /
  package manager / version they need. Don't be cute about the language
  — a PEP-668 stderr dump is fine.

## Notes

- Cross-link: findings F6+F7 + recommendation R4a in TASK-REV-E4F5.
- Latent-hazard scope — not causal for the FEAT-FORGE-002 stall, but this
  fix prevents a *silent* Coach-runs-against-wrong-interpreter future
  incident (actual Coach wiring is TASK-FIX-7A05).
- Pairs with TASK-FIX-7A05 (Wave 2). They both touch `feature_orchestrator.py`
  so W2 must rebase on W1.
- **Amendment from TASK-REV-JMBP**: the `requires-python` pre-check
  addresses a MacBook Pro incident where the orchestrator proceeded past
  an incompatible Python (3.14 vs `<3.13,>=3.12`). See the review's
  Workstream E for the rationale — folded here rather than filed as a
  separate task because the same gate surface handles both semantics.
