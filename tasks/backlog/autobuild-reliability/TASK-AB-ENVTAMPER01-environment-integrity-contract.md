---
id: TASK-AB-ENVTAMPER01
title: Environment-integrity contract — skip-guard dependency parity probe + product-file sys.modules probe
status: backlog
created: 2026-07-04T09:38:00Z
priority: high
tags: [autobuild, environment, bootstrap, sys-modules, tree-sitter, guardkitfactory, cross-repo, design-first]
complexity: 8
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Environment-integrity contract (two halves) — skip-guard parity probe + sys.modules probe

> **Status note: backlog, NOT scheduled — design-first.** Cross-repo
> (guardkit + guardkitfactory). Requires a design pass before
> implementation; do not pick up via plain `/task-work` without
> `--design-only` first.

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 11 (R1 —
FEAT-ABL-001 `nats_core` stub; the class-level fix). Per xref §7,
environment/bootstrap gaps are **the dominant historical killer** across all
five repos, and the repeating downstream shape is: *an env gap becomes
either a false-red loop or a Player workaround that corrupts the oracle*
(FEAT-HARV's `sys.modules` self-mock; R1's stub in `guardkit/__init__.py`).
This task is the class-level close, in two halves:

**(a) Upstream — post-bootstrap skip-guard dependency parity probe.** After
environment bootstrap, scan the test tree for skip-guard markers
(`skipif(find_spec("X"))` / `importorskip("X")`), verify each probed module
imports standalone from the **worktree-venv interpreter**, map missing ones
to pyproject optional-dependency groups, and surface "extra `<name>` missing
→ N tests will skip" as an **advisory** signal (optionally auto-add the
extra — this *extends* the open TASK-FIX-A7B6 `bootstrap_extras` work rather
than duplicating it). In R1, this probe would have converted a silent
missing-`memory`-extra into a loud pre-run advisory before the Player ever
faced un-runnable tests.

**(b) Gate-side — product-file `sys.modules` probe.** A narrow,
deterministic detector for the tamper move itself: a **direct subscript
assignment to `sys.modules`** in an **authored-this-turn, non-test** file.
Implemented as tree-sitter dialect DATA in `guardkitfactory.wiring` (a query
descriptor, NOT a python-`ast` monolith), advisory-first with bounded
feedback — exactly the UNWIRED disposition. Today this move is invisible:
the wiring/mocked-seam probe scans only acceptance-tier files and
mock-primitive *calls* (guardkitfactory `wiring/analyzer.py:767-776`,
`dialects/python.py:70-110`); a `sys.modules["x"] =` subscript assignment in
`guardkit/__init__.py` matches nothing; honesty verification checks
file/test claims, never the environment; no grep/AST guard on `sys.modules`
exists anywhere in the orchestrator. R1 was caught only because the stub was
imperfect (a *lucky* red).

Both halves **activate by artefact** (skip-guards present in the test tree;
authored files present this turn) — no opt-in flag. Skips remain ABSENT
signals throughout.

## Acceptance Criteria

- [ ] AC-001 (design gate): a design doc covering both halves is reviewed
      and approved before implementation (probe placement in the bootstrap
      sequence; the guardkitfactory dialect-DATA contract; the cross-repo
      seam test; feedback wording and bounds).
- [ ] AC-002 (a): after bootstrap, skip-guard markers in the test tree are
      discovered and each probed module's importability is verified against
      the worktree-venv interpreter (subprocess import, clean PYTHONPATH —
      never an in-process import from guardkit's own env).
- [ ] AC-003 (a): missing modules are mapped to pyproject
      optional-dependency groups and surfaced as "extra `<name>` missing →
      N tests will skip" — advisory, never a hard bootstrap failure.
- [ ] AC-004 (a): optional auto-add of the mapped extra reuses/extends the
      TASK-FIX-A7B6 `bootstrap_extras` mechanism (no duplicate install
      path).
- [ ] AC-005 (b): a tree-sitter query descriptor (dialect DATA) in
      `guardkitfactory.wiring` detects direct `sys.modules[...] = ...`
      subscript assignment, scoped to authored-this-turn, non-test files.
- [ ] AC-006 (b): findings are advisory-first with bounded feedback
      (mirroring the wiring gate's UNWIRED disposition — never
      turn-rejecting on first landing, never terminating).
- [ ] AC-007: both halves activate by artefact presence; grep confirms no
      new `*_enabled`/opt-in boolean was added.
- [ ] AC-008: a cross-repo seam test pins the guardkitfactory dialect
      contract (the `ctor_arity` seam-test analogue) so factory version skew
      fails in CI, not on a live run.
- [ ] AC-009: legitimate `sys.modules` use in *test* files (fixtures,
      monkeypatching) is NOT flagged; the single-task path
      (`guardkit autobuild task`, which performs no bootstrap —
      `autobuild.py:1693-1800`) is considered in the design (probe placement
      or explicit scoping-out in writing).

## Implementation Notes

File:line anchors from the xref (§3 R1, §5 item 11):

- `guardkit/tasks/feature_loader.py:1609` — extras auto-detection hard-coded
  to `['dev','test']` (why `memory` was structurally unreachable without a
  declaration); `pyproject.toml:91-97` documents the hazard;
  FEAT-HARV.yaml:142-144 is the working declaration precedent.
- Skip blindness (companion visibility task TASK-AB-SKIPVIS01):
  `specialist_invocations.py:174-180`, `agent_invoker.py:868-880/1090-1100`.
- guardkitfactory `wiring/analyzer.py:767-776` + `dialects/python.py:70-110`
  — current probe aperture (acceptance-tier files, mock-primitive calls
  only); the new descriptor extends this data, same analyzer.
- `guardkit/orchestrator/autobuild.py:1693-1800` — `guardkit autobuild task`
  performs no initial bootstrap (worktree + invoker only); any single-task
  run hits the same missing-dep temptation regardless of YAML.
- `guardkit/orchestrator/environment_bootstrap.py` — probe (a) hooks after
  the install commands; respect every existing install path.
- Prior art for the disposition: `_run_post_wave_wiring_gate` /
  `_collect_turn_rejecting_wiring_findings`
  (`feature_orchestrator.py`) — UNWIRED stays advisory.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Stack-agnostic by default**
  (`.claude/rules/stack-plugin-architecture.md`): half (b) is tree-sitter
  dialect **DATA** in `guardkitfactory.wiring`, never a guardkit-side
  python-`ast` monolith. A new language = a descriptor, not a plugin.
- **Advisory-first, UNWIRED disposition**
  (`.claude/rules/per-task-green-is-not-feature-green.md`, §6 "new
  heuristics start advisory, never join the turn-rejecting set lightly"):
  the `sys.modules` probe feeds back bounded, never terminates, and does not
  become turn-rejecting without its own follow-up review.
- **Activate by artefact, not opt-in flag**
  (`.claude/rules/activate-by-artefact-not-opt-in-flag.md`): skip-guards in
  the test tree and authored-this-turn files ARE the activation; absent
  artefact → silent, behaviour-identical skip.
- **Skips remain ABSENT signals**
  (`.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md`): the
  parity probe's "N tests will skip" is advisory evidence; it must never be
  coerced into a pass or a fail.
- **uv-sources on every install path + PyPI namespace audit**
  (`.claude/rules/uv-sources-must-survive-every-install-path.md`,
  `.claude/rules/namespace-hygiene.md`): anything half (a) adds to bootstrap
  must honour `[tool.uv.sources]` on every path it introduces and audit any
  new module/dep name against PyPI.
- **Subprocess import with clean worktree-only PYTHONPATH**
  (`.claude/rules/namespace-hygiene.md`,
  `.claude/rules/direct-mode-relaxed-gates-require-positive-evidence.md`
  remediation 4): the importability probe must not let guardkit's own
  installed packages mask a missing worktree dep.
- **Cross-repo seam test required**
  (`.claude/rules/harness-cancellation-contract.md` /
  `per-task-green-is-not-feature-green.md` CI-guard pattern): the
  guardkitfactory contract must fail loud in CI on version skew.
- **Extends, not duplicates, TASK-FIX-A7B6** (xref §5 item 11a) — the
  auto-add path reuses `bootstrap_extras`.
