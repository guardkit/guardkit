---
complexity: 6
dependencies: []
feature_id: FEAT-10AC
id: TASK-QAV-001
implementation_mode: task-work
parent_review: TASK-REV-QAVG
priority: high
status: design_approved
task_type: feature
title: L2 anti-stub body scan — stack-agnostic core in guardkitfactory.wiring
wave: 1
---

# Task: L2 anti-stub body scan — stack-agnostic core in guardkitfactory.wiring

## Description

Add the anti-stub body scan to the EXISTING stack-agnostic analyzer package
`guardkitfactory/src/guardkitfactory/wiring/` (reached from the worktree via
the `.guardkit/worktrees/guardkitfactory` bridge symlink). The scan flags an
authored public function/method whose body contains **no executable logic**:
only `pass` / `...` / `raise NotImplementedError` / a bare `return` of
`None`/`[]`/`{}` (or the per-language equivalents), optionally preceded by a
docstring, or a body carrying TODO/FIXME/stub markers.

**Binding constraint** (consolidation §2 + `.claude/rules/stack-plugin-architecture.md`):
this is tree-sitter + **dialect DATA** — extend the existing `WiringDialect`
descriptors (add a `stub_body_query` / stub-pattern fields) and the one
analyzer engine. Do NOT build a parallel analyzer and do NOT use Python's
`ast` module. Follow the pinned tree-sitter API path
(`get_language()` + standalone `tree_sitter.Parser` + `QueryCursor.captures`).

## Acceptance Criteria

- [ ] **AC-1 (positive, Python):** a fixture authoring a public function whose
  body is only `pass` / `...` / `raise NotImplementedError` / `return None` /
  `return []` / `return {}` (each variant, with and without docstring) yields
  one stub finding per symbol with `{file, symbol, lineno, stub_kind,
  severity:"warning", pattern:"STUB_BODY"}` and `status:"complete"`.
- [ ] **AC-2 (no-false-positive control, Python):** a function with a docstring
  followed by real statements, and a function with genuine logic that happens
  to end in `return []`, yield `findings:[]` with `status:"complete"`.
- [ ] **AC-3 (multi-stack parity):** positive + control fixtures for at least
  TypeScript (`throw new Error("not implemented")` / empty body / `return
  null`) and C# (`throw new NotImplementedException()` / empty body) —
  expressed as dialect DATA, zero analyzer code branching per language.
- [ ] **AC-4 (status discriminator):** unsupported language →
  `status:"unsupported_stack"` with empty findings (absent signal, never a
  pass); parse-failed file → recorded degraded, no finding manufactured for it.
- [ ] **AC-5 (task-type gating + public API):** a public
  `analyze_stub_scan(authored_files, worktree_path, task_type, ...)` sibling of
  `analyze_wiring` returns `None` for SCAFFOLDING / DOCUMENTATION / TESTING
  task types and for zero authored targets; result exposes `.to_dict()` so the
  guardkit side stores a plain dict.
- [ ] **AC-6 (behavioural check, dogfood):** an independent round-trip test
  (not colocated with the unit fixtures) runs `analyze_stub_scan` end-to-end
  over a mini fixture project on disk and asserts the emitted dict is
  JSON-serialisable and matches the documented shape.
- [ ] **AC-7:** existing guardkitfactory suites (wiring + 42 BDD contract
  tests) remain green.
- [ ] **AC-8:** all modified files pass project-configured lint/format checks
  with zero errors.

## Test Requirements

Fixture-based unit tests per dialect under `guardkitfactory/tests/wiring/`
(mirror `test_ctor_arity.py`), plus the AC-6 round-trip. No guardkit-side
changes in this task.

## Implementation Notes

- Model the result on `WiringResult`/`MockSeamResult` + `WiringStatus` — reuse
  the status vocabulary (`complete`, `unsupported_stack`, `parse_degraded`,
  `skipped_no_targets`, `error`); no status ever maps to "pass".
- Stub patterns live in the dialect records
  (`wiring/dialects/{python,javascript,typescript,c_sharp}.py`) as S-expr
  queries + marker lists; adding a language stays a descriptor entry.
- Bias against false positives: when body classification is ambiguous
  (decorators, generated code, abstract methods on ABC/interface), do NOT
  flag — accepted false-negative, per the FEAT-C332 advisory posture.