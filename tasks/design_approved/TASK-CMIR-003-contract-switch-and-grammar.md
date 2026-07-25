---
complexity: 4
dependencies:
- TASK-CMIR-001
- TASK-CMIR-002
feature_id: FEAT-CV4M
id: TASK-CMIR-003
implementation_mode: task-work
status: design_approved
task_type: feature
title: Contract switch plumbing + v4 grammar
wave: 2
---

# Contract switch plumbing + coach-verdict-v4.gbnf

Single contract resolution (env GUARDKIT_COACH_CONTRACT > .guardkit/config.yaml
autobuild.coach.contract > default "coachsplit"; precedence mirrors _get_coach_test_model
in quality_gates/coach_validator.py:2077-2099), threaded to the prompt builder
(TASK-CMIR-002), the parser call site (TASK-CMIR-001), and grammar selection in
invoke_coach (agent_invoker.py:2305-2322). New grammar
guardkit/orchestrator/grammars/coach-verdict-v4.gbnf enforcing exactly the v4 wire shape
(optional leading whitespace; {"verdict": "approve"|"reject", "findings": [{"locus":
string}...]} with the two keys in that order and no others; forced end), mirrored
byte-identical to the docs/research/dgx-spark/grammars/ twin per the existing parity
convention. Binding spec: docs/coach-contract-mirror-scope-and-buildplan.md §3 + §4 Fix C.

## Acceptance Criteria
- [ ] One shared resolution function decides the contract with precedence env > config > default; unit tests cover all three tiers; consumers (prompt, parser, grammar selection) all use it — no duplicated env reads
- [ ] With contract=v4, invoke_coach selects coach-verdict-v4.gbnf; with contract=coachsplit the existing grammar files, loader behaviour, and load-failure degrade path are byte-identical to main (the existing grammar assertions in tests/orchestrator/test_coach_synthesis_split.py pass UNMODIFIED; a new parity test pins the v4 grammar's repo/docs twins byte-identical)
- [ ] The v4 grammar accepts the canonical serve-gate outputs ({"verdict": "approve", "findings": []} and a reject with locus strings containing escaped quotes/unicode escapes) and rejects: fenced output, a "class" key, prose before the object — asserted by a hermetic grammar-shape test (string/structural checks; no llama.cpp dependency)
- [ ] COACH_DECISION_SCHEMA (agent_invoker.py:820-824) is UNCHANGED, and with the switch at default the full existing suite is green with zero modifications