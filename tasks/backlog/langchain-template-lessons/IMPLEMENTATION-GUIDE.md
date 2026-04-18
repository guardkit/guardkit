# Implementation Guide: LangChain Template Lessons (FEAT-LTL1)

This guide sequences the 12 sub-tasks into parallel-safe waves with
Conductor workspace assignments. Each wave can be executed as a
single `/feature-build` session or piecewise via `/task-work`.

## Execution Strategy Overview

| Wave | Tasks | Concurrency | Rationale |
|:-:|:-:|---|---|
| 1 | 3 | Full parallel | Unblockers — no file conflicts, foundation for Waves 2-3 |
| 2 | 4 | Full parallel (internal); depends on Wave 1's pyproject pattern (LCL-002) | Orchestrator back-port — all tasks touch orch template files, no cross-file overlap |
| 3 | 5 | Full parallel (internal); independent of Wave 2 | Shared-infra + medium/low fixes, touches base + weighted-eval |

**Wave 2 and Wave 3 can execute concurrently.** Only Wave 1 must fully
complete (specifically LCL-002 must be merged) before Wave 2's LCL-004
starts, because LCL-004 mirrors LCL-002's `[providers]` pattern.

## Wave 1 — Unblock (MUST run first)

3 tasks · all `.claude/rules` and template-source edits · no conflicts.

| Task | Workspace | Files |
|---|---|---|
| [LCL-001](TASK-LCL-001-fix-broken-imports-base-template.md) | `langchain-template-lessons-wave1-1` | `langchain-deepagents/templates/other/agents/coach.py.template`, `langchain-deepagents/templates/other/other/agent.py.template` |
| [LCL-002](TASK-LCL-002-providers-extras-base-pyproject.md) | `langchain-template-lessons-wave1-2` | `langchain-deepagents/templates/other/other/pyproject.toml.template`, `langchain-deepagents/.claude/CLAUDE.md` |
| [LCL-003](TASK-LCL-003-template-validate-render-import-smoke.md) | `langchain-template-lessons-wave1-3` | `tests/integration/test_template_render_import.py` (new), possible CI update |

**Execution**:
```bash
# Conductor parallel (recommended)
# Run all three in separate workspaces; merge LCL-001 and LCL-002 first
# so LCL-003 can assert against the fixed state.

# OR sequential
/task-work TASK-LCL-001
/task-work TASK-LCL-002
/task-work TASK-LCL-003
```

**Exit criteria**: all three merged; rendered base template imports cleanly
(`python -c "import <projname>.coach; import <projname>.agent"` exits 0).

## Wave 2 — Orchestrator Back-Port (depends on LCL-002)

4 tasks · all touch `installer/core/templates/langchain-deepagents-orchestrator/*`
· each touches disjoint files so internal parallelism is safe.

| Task | Workspace | Primary files |
|---|---|---|
| [LCL-004](TASK-LCL-004-providers-extras-orchestrator.md) | `langchain-template-lessons-wave2-1` | orch `pyproject.toml.template` (new), `CLAUDE.md` |
| [LCL-005](TASK-LCL-005-agents-md-orchestrator-ainvoke-contract.md) | `langchain-template-lessons-wave2-2` | orch `AGENTS.md.template` (new) |
| [LCL-006](TASK-LCL-006-env-var-resolution-orchestrator.md) | `langchain-template-lessons-wave2-3` | orch `agent.py.template`, `orchestrator-config.yaml.template` |
| [LCL-007](TASK-LCL-007-evaluator-subagent-tool-inventory-assertion.md) | `langchain-template-lessons-wave2-4` | orch `agents.py.template`, new `lib/factory_guards.py.template`, new `patterns/tool-delegation.md` |

**File-conflict check**: LCL-006 edits `agent.py.template` (module wiring);
LCL-007 edits `agents.py.template` (the factory functions). Different
files. LCL-004 and LCL-005 add new files only. Zero conflicts.

**Execution**:
```bash
# Conductor-friendly — all four in parallel after LCL-002 merges
# Dependency gate: LCL-004 waits on LCL-002 (same pyproject pattern)
```

**Exit criteria**: orch template has its own pyproject with `[providers]`,
ships AGENTS.md with R2A1 contract, resolves models via
`AGENT_MODELS__REASONING_MODEL` env, and asserts Evaluator tool inventory
= `set()` at construction.

## Wave 3 — Shared Infrastructure + Tail (independent of Wave 2)

5 tasks. LCL-008 is the heaviest (complexity 6); the other four are
doc/manifest/env changes.

| Task | Workspace | Primary files |
|---|---|---|
| [LCL-008](TASK-LCL-008-extract-session-logging-retry-context-to-base-lib.md) | `langchain-template-lessons-wave3-1` | base `lib/session_logging.py` (new), `lib/retry_context.py` (new), weighted-eval `scaffold/orchestrator.py.j2` (refactor), orch vendored copies, base tests |
| [LCL-009](TASK-LCL-009-patterns-long-running-tools-rule.md) | `langchain-template-lessons-wave3-2` | base `patterns/long-running-tools.md` (new), orch `patterns/long-running-tools.md` (new) |
| [LCL-010](TASK-LCL-010-patterns-source-path-convention-doc.md) | `langchain-template-lessons-wave3-3` | base `.claude/CLAUDE.md` (edit) |
| [LCL-011](TASK-LCL-011-align-weighted-eval-manifest-pattern-attribution.md) | `langchain-template-lessons-wave3-4` | weighted-eval `manifest.json` (+ optionally base `manifest.json`) |
| [LCL-012](TASK-LCL-012-weighted-eval-env-example.md) | `langchain-template-lessons-wave3-5` | weighted-eval `.env.example.template` (new), optional `config/adversarial_config.py` |

**File-conflict notes**:
- LCL-008 touches both weighted-eval and orch — but orch work is
  *additive* (new vendored files), so it doesn't collide with LCL-009
  (which also adds new orch files at a different path).
- LCL-008 edits base `lib/__init__.py` — no other Wave 3 task touches it.
- LCL-010 edits base `.claude/CLAUDE.md` — LCL-002 also edits this file
  (Wave 1). If LCL-010 runs *before* LCL-002 merges, a trivial rebase is
  expected. Recommend merging LCL-002 first (Wave 1 gate already requires).

**Execution**:
```bash
# Conductor-friendly — five in parallel, no internal dependencies
```

**Exit criteria**: base `lib/` exports session_logging + retry_context;
weighted-eval imports them instead of defining inline; orchestrator vendors
copies; long-running-tools rule present in base and orch; manifest
attribution clarified; weighted-eval ships its own `.env.example`.

## Parallel Execution Matrix (Conductor)

Assuming Wave 1 completes first, Waves 2 and 3 can run fully in parallel:

```
Wave 1 (3 workspaces) ──→ merge all three
        │
        ├──→ Wave 2 (4 workspaces — orch) ──┐
        │                                    ├──→ /feature-complete
        └──→ Wave 3 (5 workspaces — base)  ──┘
```

Maximum concurrency: 9 workspaces (Wave 2 + Wave 3 simultaneously). For
less aggressive setups, serialise Wave 3 after Wave 2.

## Suggested Verification Sequence (post-merge)

1. Render each template with `guardkit init <template-name>` into a
   scratch project.
2. `pip install .[providers]` in each rendered project.
3. `python -c "import <projname>.<entrypoint>"` for each.
4. Run `pytest` in each rendered project.
5. (Optional) Open a follow-up `/task-review TASK-XXX --mode=architectural --depth=quick`
   that re-applies the LES1 6-surface matrix to confirm the per-template
   parity scores improved.

## When to Stop

This feature intentionally **does not** address:
- MCP stdio / NATS transport surfaces (not applicable to code-only templates).
- Dockerfile parity (code-only templates should not ship a Dockerfile).
- `nats-asyncio-service` template audit (separate review task).

If those surfaces become load-bearing for a future agent, introduce a
deployment-focused sibling template (e.g. `langchain-deepagents-nats-service`)
and audit it against LES1 §1-2 and §7 at that time.
