# TASK-REV-MCPS — Graphiti Preamble (Workstream A)

**Date**: 2026-04-24
**Task**: [TASK-REV-MCPS](../../tasks/backlog/TASK-REV-MCPS-mcp-namespace-collision-diagnostic-and-fix-plan.md)
**Reviewer**: task-review --mode=architectural --depth=standard
**Access method**: MCP (Tier 0) — `mcp__graphiti__search_nodes` and `mcp__graphiti__search_memory_facts` loaded via ToolSearch.

## Why this preamble exists

Per the task's explicit framing (*"ensure we use Graphiti for knowledge query, capture etc and we don't break anything"*) and paralleling TASK-REV-STKB Workstream A, the knowledge graph must be queried **before** any fix is proposed. What the graph already knows (or conspicuously fails to know) shapes the remediation path.

## Queries executed

| # | Tool | Query | Group IDs |
|---|------|-------|-----------|
| 1 | `search_nodes` | "mcp module namespace collision sys.path" | `guardkit__project_decisions`, `guardkit__project_architecture`, `architecture_decisions` |
| 2 | `search_memory_facts` | "installer core lib sys path insert" | `guardkit__project_decisions`, `guardkit__task_outcomes` |
| 3 | `search_nodes` | "greenfield_qa_session state_paths" | `guardkit__project_decisions`, `guardkit__task_outcomes` |
| 4 | `search_nodes` | "Context7 MCPMonitor Context7Client" | `product_knowledge`, `guardkit__project_architecture` |
| 5 | `search_memory_facts` | "claude-agent-sdk AutoBuild SDK not available import error" | `guardkit__task_outcomes`, `guardkit__project_decisions` |
| 6 | `search_nodes` | "runner without producer namespace hygiene external namespace audit" | `guardkit__project_decisions`, `architecture_decisions` |

## Relevant nodes retrieved

### N1 — `sys.path` modification in render-and-import smoke test
- **UUID**: `3c4f9320-367c-49b8-8c80-f92fcc9ab2ce`
- **Group**: `guardkit__project_decisions`
- **Created**: 2026-04-18
- **Summary**: *"sys.path is modified in the render-and-import smoke test to filter out the guardkit repo root. This prevents guardkit's lib/ from shadowing the rendered scratch project's lib/."*
- **Relevance**: **Direct meta-pattern match.** GuardKit already encountered lib/ shadowing once (2026-04-18) in a different surface (template render smoke test) and patched it locally. No generalized design rule was seeded. TASK-REV-MCPS is the second activation of the same class-of-defect.

### N2 — `namespace package`
- **UUID**: `b67923f1-6309-4146-bb39-9aea8ed87198`
- **Group**: `guardkit__project_decisions`
- **Summary**: *"A namespace package is a Python package that may not have an __init__.py file. This can cause issues with import order if a regular package with the same name exists in sys.path."*
- **Relevance**: Direct explanation of the mechanism. Confirms the import-order hazard is already understood at entity level but not translated into a behavioural rule.

### N3 — `runner without producer anti-pattern`
- **UUID**: `184731b0-3cb6-4eb2-a310-883421767dbf`
- **Group**: `guardkit__project_decisions`
- **Summary**: First seeded design-rule-candidate node in GuardKit (2026-04-22, TASK-REV-RWOP1).
- **Relevance**: Sibling precedent. The namespace-hygiene rule to be seeded by Workstream D follows the exact same node shape (symptom + detection recipe + remediation recipe + grep signature). Cross-reference explicitly in the new rule body.

## Relevant facts retrieved

### F1 — Editable install puts top-level dirs on sys.path
- **UUID**: `f868769a-32f8-4969-941b-062f509543cb`
- **Relationship**: `(editable installation of guardkit-py) --MODIFIES--> (sys.path)`
- **Fact**: *"The editable installation of guardkit-py adds its top-level directories to sys.path."*
- **Relevance**: **Validates Fix Option 1a.** Because the editable install already exposes the repo root on `sys.path`, the fully-qualified import path `from installer.core.lib.state_paths import ...` resolves cleanly without any `sys.path.insert`. This is the cheapest viable fix.

### F2 — Prior shadowing incident, same class-of-defect
- **UUID**: `cced8d00-d0f5-4cf5-bfef-f20ce3c001fd`
- **Relationship**: `(editable guardkit-py lib/) --CAUSES_CONFLICT_WITH--> (rendered template lib/)`
- **Fact**: *"The lib/ directory from an editable guardkit-py installation shadowed the lib/ namespace package rendered by the orchestrator template, causing an import conflict."*
- **Relevance**: **Direct evidentiary precedent.** Identical mechanism (editable install exposing GuardKit internals on sys.path causing shadow of an external namespace). Mitigation was a local filter in a single test. No generalized rule. This bug is a direct consequence of that rule never being seeded.

### F3 — Python import machinery walks sys.path
- **UUID**: `4c419a93-63fc-4167-975a-a3861542c8fe`
- **Fact**: *"Python's import machinery iterates over sys.path to find packages."*
- **Relevance**: Elementary but confirms why `sys.path.insert(0, ...)` is architecturally dangerous — position-zero inserts beat everything else including site-packages.

## Conspicuous absences (finding-by-silence)

### A1 — No node captures the "internal mcp module named after Anthropic's PyPI mcp" decision
- Query 4 (Context7 / MCPMonitor / Context7Client) returned zero hits. The internal `installer/core/lib/mcp/` module is not represented in `product_knowledge` or `guardkit__project_architecture`.
- **Implication**: There is no recorded past decision that the internal module MUST be called `mcp` for any reason. Rename (Fix #2) faces no discoverable historical objection.

### A2 — No node captures the `greenfield_qa_session.py` sys.path fallback
- Query 3 returned zero relevant hits. The bug itself was never seeded.
- **Implication**: If this review doesn't seed the rule, the next occurrence will re-derive the diagnosis from scratch.

### A3 — No node captures the opaque `_check_sdk_available` error message
- Query 5 returned SDK-related but unrelated facts (template SDK imports in rendered projects). No decision about AutoBuild's SDK preflight wording.
- **Implication**: Fix #3 (better diagnostics) is not opposed by any past decision.

## Findings summary

1. **The meta-pattern is recurrent, not novel.** Graphiti holds direct evidence of a prior editable-install-shadowing incident (F2, 2026-04-18). That bug was patched locally; the generalized rule was never seeded. TASK-REV-MCPS is the predicted re-activation. This is the exact failure mode TASK-REV-STKB Workstream D warned about: local fix without rule-level remediation.
2. **The sibling rule shape is available.** The `runner without producer anti-pattern` node (N3, uuid `184731b0`) was seeded on 2026-04-22 and serves as a template for the shape of the rule Workstream D will seed.
3. **No past decision argues against any of the three proposed fixes.** A1/A2/A3 confirm the graph carries no objections to renaming `installer/core/lib/mcp/`, to removing the `sys.path.insert` fallback in `greenfield_qa_session.py`, or to surfacing the real `ImportError` in `_check_sdk_available`.
4. **Fix Option 1a is validated by F1.** The editable install places the repo root on sys.path, so `from installer.core.lib.state_paths import ...` resolves naturally — no `sys.path.insert` and no `importlib` gymnastics needed.

## How these findings bind the review

| Workstream | Binding from this preamble |
|---|---|
| B (name-collision sweep) | Use N2 + F2 as prior art — the sweep must distinguish *active* (currently on sys.path[0]) from *latent* (collision exists but no import chain activates it). |
| C (fix triage) | Fix Option 1a has direct graph support (F1). Fix #2 has no recorded objection (A1). Fix #3 has no recorded objection (A3). Risk columns should say so. |
| D (rule seeding) | The rule node body must (a) cite F2 as direct prior-art, (b) cross-reference N3 as sibling under a shared meta-rule, (c) follow the symptom + detection recipe + remediation recipe + grep signature shape. |
| E (execution strategy) | Because F2 shows the class-of-defect has already recurred once without rule-level remediation, "Minimal only" (ship #1+#3, defer #2 indefinitely) is the wrong shape — the rule would be seeded but the evidentiary instance would remain on disk. Prefer **Minimal-then-complete** or **Complete**. |
