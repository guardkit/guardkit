---
id: TASK-REV-QAVG
title: "Plan: QA Verifier Behavioural-Evidence Gates"
task_type: review
priority: high
status: completed
created: 2026-07-04T16:20:00+01:00
completed: 2026-07-04T16:35:00+01:00
review_mode: decision
review_depth: standard
decision: implement
feature_id: FEAT-QAV (canonical ID assigned by generate-feature-yaml)
clarification:
  context_a: skipped (--no-questions)
  context_b: skipped (--no-questions, defaults)
context_files:
  - features/qav-behavioural-gates/qav-behavioural-gates_summary.md
  - docs/retro/qa-verifier-state-consolidation-2026-07-04.md
  - docs/features/qa-verifier-wiring-probes-scope.md
  - docs/research/ideas/qa-verifier-behavioural-evidence-gates-conversation-starter.md
---

# Review: Plan QA Verifier Behavioural-Evidence Gates

Decision review for the NEW QAV gates (L2 anti-stub / L3 coverage / L4
behavioural oracle) per the 2026-07-04 state consolidation §3.3. Spec:
`features/qav-behavioural-gates/qav-behavioural-gates.feature` (22 scenarios).

## Technical options analysis

**Option 1 (RECOMMENDED): extend the existing evidence architecture.**
Factory-side tree-sitter stub-scan as new analysis queries in
`guardkitfactory.wiring` dialect DATA (per-language stub-body S-exprs, a
`StubScanResult` with the FEAT-C332 status discriminator); guardkit-side three
sibling `Optional` bundle fields + the proven lazy-import seam; L3 coverage as
stack-plugin execution (python `pytest --cov` day one, absent-signal
elsewhere); L4 oracle discovery by artefact presence with the
COACHRUNPARITY01 timeout asymmetry and a deterministic verdict override that
re-persists `coach_turn_N.json`. Complexity 7 aggregate. Reuses every verified
seam FEAT-C332 landed (bundle `to_dict`, complete-path population point,
render/truncation archetype, guard archetype + None-safety).

**Option 2 (REJECTED): standalone Python-`ast` scanner in guardkit.** The
exact stack-blindness anti-pattern `.claude/rules/stack-plugin-architecture.md`
exists to prevent, and the consolidation's binding constraint explicitly
forbids it ("tree-sitter + dialect data, NOT Python-ast; extend the existing
WiringAnalyzer dialect descriptors; do not build a parallel analyzer").

**Option 3 (REJECTED): LLM-judge stub detection (prompt the Coach to spot
stubs).** Violates A1 (deterministic Python collects evidence; LLM judges it)
and `.claude/rules/structural-defence-beats-prompt-instruction.md` — a prompt
instruction is a probabilistic defence for an LLM-chosen behaviour; the stub
class needs a structural gate.

## Risks

- **False-red surface (highest).** Stub/coverage heuristics turning
  turn-rejecting would re-create the false-red class
  (`path-string-mismatch-is-not-dishonesty`). Mitigation: L2 + L3 are advisory
  (severity=warning) in v0; ONLY a ran-and-failed L4 oracle overrides verdicts
  (ASSUM-006).
- **Absent-signal corruption.** Three new signals traverse the reconciliation
  layers; any absent→False coercion is an ABFIX-010-class regression.
  Mitigation: explicit ACs pinning absence survival end-to-end.
- **Cross-repo seam skew.** TASK-QAV-001 lands in guardkitfactory; guardkit
  consumes it. Mitigation: seam test mirroring
  `tests/orchestrator/test_wiring_ctor_arity_seam.py`; `evidence_repos:
  ['../guardkitfactory']` declared in the feature YAML.
- **Oracle-independence spoofing.** A Player could edit an existing oracle.
  Mitigation: independence = oracle file NOT in the turn's authored set
  (ASSUM-004); an authored oracle degrades to absent + warning.

## Decision

**[I]mplement** — Option 1, five tasks in five sequential waves (003/004 both
touch `coach_validator.py` + `agent_invoker.py`; sequential avoids shared-
worktree file conflicts and matches the validated GB10 `--max-parallel 1`
recipe). Defaults applied for Context B (--no-questions): recommended
approach, sequential execution, standard testing plus the dogfood rule from
the execution plan (every task carries an independent behavioural check).

Task breakdown: see `tasks/backlog/qav-behavioural-gates/` +
`.guardkit/features/` YAML (canonical ID assigned at generation).
