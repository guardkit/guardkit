---
id: TASK-QAWE-001
title: Stack-agnostic tree-sitter WiringAnalyzer core + dialects (Wave 0, no guardkit integration)
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-C332
wave: 1
implementation_mode: task-work
complexity: 6
dependencies: []
priority: medium
status: completed
completed_at: '2026-06-12T17:30:00'
completion_mode: manual (cross-repo evidence gap TASK-AB-XREPOEV01)
---

# Task: tree-sitter WiringAnalyzer core + dialects (Wave 0)

## Description

Build the **stack-agnostic** wiring-analysis engine in a NEW
`guardkitfactory/src/guardkitfactory/wiring/` subpackage, per
`docs/features/qa-verifier-wiring-probes-scope.md` §3–§5. One `WiringAnalyzer` over a
tree-sitter Concrete Syntax Tree + declarative per-language `WiringDialect` records
(DATA) for **python, javascript, typescript, csharp**. Detects UNWIRED_PATH and
MOCKED_SEAM. **Fixture-tested in isolation — no guardkit integration in this wave.**
(Bundle wiring is Wave 1; MOCKED field wiring Wave 2; SPEC_GAP Wave 3.)

## Acceptance Criteria

(from the scope doc — full text there)

- [ ] **AC-019 (tree-sitter API path pinned):** parse via
  `tree_sitter_language_pack.get_language(name)` + standalone `tree_sitter.Parser`
  (bytes) + `QueryCursor(query).captures(root)` — **NOT** the pack's `get_parser()`.
  Each dialect has a `smoke_test()` compiling its queries against the live grammar.
- [ ] **AC-020 (dependency location + packaging):** `tree-sitter` +
  `tree-sitter-language-pack` added to guardkitfactory **core `dependencies`**;
  `[tool.setuptools] packages` includes `guardkitfactory.wiring` +
  `guardkitfactory.wiring.dialects`; render-and-import smoke test confirms no PyPI
  top-level shadowing (`.claude/rules/namespace-hygiene.md`).
- [ ] **AC-001/003/004 (UNWIRED positive + control, multi-stack):** un-registered
  public symbol → one finding; registered (Python `cli.add_command`, C#
  `AddScoped<X>`, TS `app.use`/`<Route>`) → `findings:[]`, `status:"complete"`.
- [ ] **AC-005/007 (MOCKED positive, multi-stack):** acceptance file mocking an
  authored seam → `warning` finding (Python `patch`, C# `Mock<IAuthoredSeam>`).
- [ ] **AC-009 (unsupported stack → absent-signal):** language with no dialect →
  `status:"unsupported_stack"`, `findings:[]`, status **not** `complete`.
- [ ] **AC-010 (parse-degraded biases WIRED):** CST parse error → substring fallback,
  `status:"parse_degraded"`, never a false UNWIRED.
- [ ] **AC-021 (polyglot):** a fixture with both `.py` and `.ts` runs BOTH dialects;
  findings carry `dialect`/`language`.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation
- `pytest` over the new `guardkitfactory/.../tests` wiring fixtures (per-stack).
- Lint/format pass with zero errors.


## Completion record (2026-06-12)

Delivered MANUALLY in guardkitfactory commit `169f16c` (not via autobuild):
the FEAT-C332 run-1 Player wrote a real WIP into guardkitfactory via the
worktree symlink, but the Coach evidence loop is scoped to the guardkit
worktree, so every turn was rejected as "no implementation provided"
(filed as TASK-AB-XREPOEV01). The WIP was salvaged, then the semantic core
was rewritten after a 6-lens adversarial AC review.

Verification: 44 wiring tests green; full guardkitfactory suite 191 passed;
ruff + mypy clean on the wiring package; all four dialects pass smoke_test()
(query compile + canonical-snippet match); deps pinned tree-sitter>=0.25 +
tree-sitter-language-pack>=1.0,<2 with uv.lock updated (AC-020).

Public seam for Wave 1/2 (QAWE-002/003): `from guardkitfactory.wiring import
analyze_wiring` — returns None (probe didn't run) or the §5.1 wiring dict
with the MOCKED_SEAM result nested under `"mocked_seam"`.
