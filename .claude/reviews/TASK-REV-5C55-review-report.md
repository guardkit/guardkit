# Review Report: TASK-REV-5C55 (Revised)

## Executive Summary

**reseed_guardkit_1** is a full system re-seed on a clean graph (post `graphiti clear`). **init_project_10** is a subsequent `guardkit init` run on vllm-profiling. Both runs were executed **after all 5 FEAT-SPR tasks were implemented** — this is the post-fix verification run.

**Verdict: All 5 FEAT-SPR fixes are confirmed working in the actual run output (per-template batching visible in log, ✓/⚠/✗ display shown, Seed Summary printed, circuit breaker resets preventing cross-template cascade). Seed success rate improved from 52% (init_9, pre-SPR) to 62% (reseed_guardkit_1, post-SPR). However, a CRITICAL regression was introduced by TASK-SPR-18fc: the per-template group_ids (`rules_fastapi_python`) don't match the timeout tier check at `graphiti_client.py:975`, giving rules 120s instead of the intended 180s. This is the primary remaining blocker — fixing it should push success rate above 75%.**

**Revision scope**: Full source code tracing across 7 files, C4 context and container diagrams, sequence diagrams across all technology seams, root cause validation with line-number evidence. Second revision corrects FEAT-SPR assessment. Third revision corrects timeline: both runs are post-FEAT-SPR, confirming all 5 fixes are active in the run output.

| Metric | init_9 (pre-SPR) | reseed_1 (post-SPR) | init_10 (post-SPR) | Trend |
|--------|------------------|---------------------|--------------------|----- |
| Seed success rate | 52% (101/193) | 62% (106/171) | N/A (init only) | **+10pp** with FEAT-SPR |
| Rules success | 1/72 (1.4%) | 25/72 (34.7%) | N/A | **+33pp** (batching works, but timeout tier regression limits further gains) |
| Circuit breaker trips | 4 (cascading) | 5 (isolated per-template) | 0 (only 3 episodes) | **Fixed** — no cross-category/template cascade |
| Init total time | 228.0s | N/A | 511.9s | Regressed (graph density) |
| FEAT-SPR features active | No | **Yes** — all 5 visible in output | **Yes** (LLM health check) | Confirmed |

## Review Details

- **Mode**: Code Quality (Revised — comprehensive depth with code tracing)
- **Depth**: Comprehensive (upgraded from standard for root cause verification)
- **Parent Review**: TASK-REV-F404
- **Feature**: FEAT-SPR (Seeding Production Readiness) — all 5 tasks completed before these runs
- **Run sequence**: FEAT-SPR implemented → `guardkit graphiti seed --force` → `guardkit init`
- **Sources**: `reseed_guardkit_1.md` (10,413 lines), `init_project_10.md` (70 lines)
- **Source files traced**: `graphiti_client.py`, `seeding.py`, `seed_helpers.py`, `seed_rules.py`, `project_seeding.py`, `init.py`, `_group_defs.py`
- **FEAT-SPR features confirmed in run output**: Per-template batching (log lines 5890-8581), ✓/⚠/✗ display (lines 10386-10402), Seed Summary (lines 10404-10408), circuit breaker reset (per-template results vary independently)

---

## C4 Context Diagram: Seeding System

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       System Context (C4 Level 1)                       │
│                                                                         │
│  ┌──────────┐     CLI        ┌────────────────┐                         │
│  │          │───────────────▶│                │                         │
│  │  User    │                │  GuardKit CLI  │                         │
│  │          │◀───────────────│  (guardkit     │                         │
│  └──────────┘    stdout      │   graphiti     │                         │
│                              │   seed/init)   │                         │
│                              └───────┬────────┘                         │
│                                      │                                  │
│                      ┌───────────────┼───────────────┐                  │
│                      │               │               │                  │
│                      ▼               ▼               ▼                  │
│              ┌──────────────┐ ┌──────────┐  ┌──────────────┐            │
│              │ graphiti-core│ │ FalkorDB │  │ vLLM (local) │            │
│              │ (Python lib) │ │ (Graph)  │  │ Chat: :8000  │            │
│              │ v0.5.x       │ │ Redis    │  │ Embed: :8001 │            │
│              └──────────────┘ └──────────┘  └──────────────┘            │
│                                                                         │
│  Technology boundaries:                                                 │
│  ─── Python ──────── Python ──── Python/Redis ──── HTTP/OpenAI ───     │
│  GuardKit          graphiti-core      FalkorDB         vLLM             │
└─────────────────────────────────────────────────────────────────────────┘
```

## C4 Container Diagram: Seed Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Container Diagram (C4 Level 2)                     │
│                                                                         │
│  GuardKit Python Process                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                                                                 │    │
│  │  ┌───────────┐    ┌──────────────┐    ┌───────────────────┐     │    │
│  │  │ CLI Layer │───▶│  Seeding     │───▶│  seed_rules.py    │     │    │
│  │  │ graphiti  │    │  Orchestrator│    │  seed_agents.py   │     │    │
│  │  │ .py       │    │  seeding.py  │    │  seed_templates   │     │    │
│  │  │           │    │              │    │  ... (17 modules) │     │    │
│  │  └───────────┘    └──────┬───────┘    └────────┬──────────┘     │    │
│  │                          │                     │                │    │
│  │                   reset_circuit_               │                │    │
│  │                   breaker() ←──────────────────┤                │    │
│  │                          │                     │                │    │
│  │                          ▼                     ▼                │    │
│  │                   ┌──────────────┐    ┌───────────────────┐     │    │
│  │                   │ seed_helpers │    │                   │     │    │
│  │                   │ _add_episodes│───▶│ GraphitiClient    │     │    │
│  │                   └──────────────┘    │                   │     │    │
│  │                                       │ add_episode()     │     │    │
│  │                                       │   ↓               │     │    │
│  │                                       │ _create_episode() │     │    │
│  │                                       │   ├─ timeout tier │     │    │
│  │                                       │   ├─ circuit brkr │     │    │
│  │                                       │   └─ retry logic  │     │    │
│  │                                       └────────┬──────────┘     │    │
│  │                                                │                │    │
│  └────────────────────────────────────────────────┼────────────────┘    │
│                                                   │                     │
│           ┌───────────────────────────────────────┤                     │
│           │ asyncio.wait_for(timeout)             │                     │
│           ▼                                       ▼                     │
│    ┌──────────────┐                        ┌──────────────┐             │
│    │ graphiti-core│                        │ graphiti-core│             │
│    │ add_episode()│ ───LLM calls──────────▶│ edge_ops     │             │
│    │              │ ───embeddings──────────▶│ dedupe_edges │             │
│    └──────┬───────┘                        └──────────────┘             │
│           │                                                             │
│     ┌─────┴─────┐                                                       │
│     │           │                                                       │
│     ▼           ▼                                                       │
│  ┌────────┐ ┌────────┐                                                  │
│  │FalkorDB│ │ vLLM   │                                                  │
│  │(graph) │ │:8000   │                                                  │
│  │:6379   │ │:8001   │                                                  │
│  └────────┘ └────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ROOT CAUSE ANALYSIS: Rules Timeout Tier Bug

### The Bug (CRITICAL — TASK-SPR-18fc regression, confirmed active in reseed_guardkit_1)

**File**: [graphiti_client.py:973-984](guardkit/knowledge/graphiti_client.py#L973-L984)

```python
# _create_episode() timeout tier selection:
if group_id.endswith("project_overview"):
    episode_timeout = 300.0
elif group_id == "rules":              # ← EXACT MATCH on "rules"
    episode_timeout = 180.0
elif group_id == "role_constraints":
    episode_timeout = 150.0
elif group_id == "agents":             # ← EXACT MATCH on "agents"
    episode_timeout = 150.0
elif group_id == "templates":          # ← EXACT MATCH on "templates"
    episode_timeout = 180.0
else:
    episode_timeout = 120.0            # ← DEFAULT fallback
```

**File**: [seed_rules.py:267](guardkit/knowledge/seed_rules.py#L267)

```python
group_id = f"rules_{template_id}"  # e.g., "rules_fastapi_python"
```

**File**: [seed_helpers.py:48-54](guardkit/knowledge/seed_helpers.py#L48-L54)

```python
result = await client.add_episode(
    name=name,
    episode_body=json.dumps(body),
    group_id=group_id,  # ← passes "rules_fastapi_python"
    ...
)
```

**File**: [graphiti_client.py:1106](guardkit/knowledge/graphiti_client.py#L1106) (add_episode → _apply_group_prefix)

```python
prefixed_group_id = self._apply_group_prefix(group_id, scope)
# "rules_fastapi_python" is NOT in SYSTEM_GROUP_IDS
# NOT starts with "guardkit_"
# → is_project_group() returns True
# → prefixed to "guardkit__rules_fastapi_python"
```

**File**: [_group_defs.py:43](guardkit/_group_defs.py#L43)

```python
SYSTEM_GROUPS = {
    ...
    "rules": "Rule definitions and enforcement policies",  # ← "rules" is system
    ...
}
# But "rules_fastapi_python" is NOT in this dict → treated as project group
```

### The Mismatch Chain

1. `seed_rules.py:267` creates `group_id = "rules_fastapi_python"`
2. `seed_helpers.py:48` passes this to `client.add_episode(group_id="rules_fastapi_python")`
3. `graphiti_client.py:1106` prefixes it to `"guardkit__rules_fastapi_python"` (because `rules_fastapi_python` ∉ SYSTEM_GROUP_IDS)
4. `graphiti_client.py:975` checks `group_id == "rules"` — **does NOT match** `"guardkit__rules_fastapi_python"`
5. Falls through to `else` → **120s timeout** instead of intended 180s

### Impact

All 72 rule episodes run with **120s timeout instead of 180s**. This means:
- Episodes that would complete between 120s-180s are unnecessarily killed
- 3 consecutive 120s timeouts trip the circuit breaker faster than 3x 180s would
- The circuit breaker cascade is **60s more sensitive** per episode than intended

### Why agents and templates are NOT affected

- `seed_agents.py:233`: `group_id="agents"` → in SYSTEM_GROUP_IDS → NOT prefixed → exact match at line 979 ✓
- `seed_templates.py:158`: `group_id="templates"` → in SYSTEM_GROUP_IDS → NOT prefixed → exact match at line 981 ✓

### Why the bug was invisible during TASK-SPR-18fc implementation

The `"rules"` bare group_id IS in SYSTEM_GROUP_IDS, so if `seed_rules.py` used `group_id="rules"` it would work. But TASK-SPR-18fc refactored `seed_rules.py` to use per-template group_ids (`rules_fastapi_python`, etc.) for batching — and the timeout tier in `_create_episode` was never updated to match. The bug is invisible at the code level because there are no tests that verify timeout tier assignment for prefixed group_ids. It only manifests at runtime as excess timeouts in the rules category — which the reseed_guardkit_1 output now clearly shows (25/72, with per-template breakdown showing high skip rates).

---

## Sequence Diagram 1: Rules Seeding — Circuit Breaker Cascade (with bug)

```
┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐
│seeding.py│  │seed_rules│  │seed_helper│  │graphiti_client│  │graphiti- │  │ FalkorDB │  │  vLLM  │
│:168-172  │  │.py       │  │s.py       │  │.py            │  │core      │  │ :6379    │  │ :8000  │
└────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬────────┘  └────┬─────┘  └────┬─────┘  └───┬────┘
     │              │              │               │                │             │            │
     │ reset_circuit│              │               │                │             │            │
     │ _breaker()   │              │               │                │             │            │
     │─────────────────────────────────────────────>│                │             │            │
     │              │              │               │ failures=0     │             │            │
     │              │              │               │ tripped=False  │             │            │
     │              │              │               │                │             │            │
     │ seed_rules() │              │               │                │             │            │
     │─────────────>│              │               │                │             │            │
     │              │              │               │                │             │            │
     │              │ LOOP templates (seed_rules.py:261)            │             │            │
     │              │══════════════════════════════════════════════════════════════│            │
     │              │              │               │                │             │            │
     │              │ Template: fastapi-python (12 rules)           │             │            │
     │              │              │               │                │             │            │
     │              │ reset_circuit_breaker()       │                │             │            │
     │              │─────────────────────────────>│ failures=0     │             │            │
     │              │              │               │                │             │            │
     │              │ group_id =   │               │                │             │            │
     │              │ "rules_      │               │                │             │            │
     │              │  fastapi_    │               │                │             │            │
     │              │  python"     │               │                │             │            │
     │              │              │               │                │             │            │
     │              │ _add_episodes│               │                │             │            │
     │              │─────────────>│               │                │             │            │
     │              │              │               │                │             │            │
     │              │              │  LOOP 12 episodes (seed_helpers.py:46)       │            │
     │              │              │  ═══════════════════════════════════          │            │
     │              │              │               │                │             │            │
     │              │              │  Episode 1: rule_fastapi_python_api_routing  │            │
     │              │              │               │                │             │            │
     │              │              │ add_episode(  │                │             │            │
     │              │              │  group_id=    │                │             │            │
     │              │              │  "rules_      │                │             │            │
     │              │              │   fastapi_    │                │             │            │
     │              │              │   python")    │                │             │            │
     │              │              │──────────────>│                │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ _apply_group_  │             │            │
     │              │              │               │ prefix()       │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ "rules_fastapi_│             │            │
     │              │              │               │  python" NOT   │             │            │
     │              │              │               │  in SYSTEM_    │             │            │
     │              │              │               │  GROUP_IDS     │             │            │
     │              │              │               │  → PREFIXED to │             │            │
     │              │              │               │  "guardkit__   │             │            │
     │              │              │               │   rules_fastapi│             │            │
     │              │              │               │   _python"     │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ _create_episode│             │            │
     │              │              │               │ (group_id=     │             │            │
     │              │              │               │  "guardkit__   │             │            │
     │              │              │               │   rules_fastapi│             │            │
     │              │              │               │   _python")    │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ ┌─BUG─────────────────────┐  │            │
     │              │              │               │ │ Timeout tier check:     │  │            │
     │              │              │               │ │                         │  │            │
     │              │              │               │ │ group_id.endswith(      │  │            │
     │              │              │               │ │  "project_overview")    │  │            │
     │              │              │               │ │  → NO                   │  │            │
     │              │              │               │ │                         │  │            │
     │              │              │               │ │ group_id == "rules"     │  │            │
     │              │              │               │ │  → NO! ("guardkit__     │  │            │
     │              │              │               │ │    rules_fastapi_python"│  │            │
     │              │              │               │ │    ≠ "rules")           │  │            │
     │              │              │               │ │                         │  │            │
     │              │              │               │ │ → Falls to ELSE:        │  │            │
     │              │              │               │ │   timeout = 120s ✗      │  │            │
     │              │              │               │ │   (should be 180s)      │  │            │
     │              │              │               │ └─────────────────────────┘  │            │
     │              │              │               │                │             │            │
     │              │              │               │ asyncio.wait_for(timeout=120s)            │
     │              │              │               │───────────────>│             │            │
     │              │              │               │                │ add_episode │            │
     │              │              │               │                │────────────>│ Cypher     │
     │              │              │               │                │             │ queries    │
     │              │              │               │                │  LLM calls ─│───────────>│
     │              │              │               │                │             │            │
     │              │              │               │                │   ...120s elapse...      │
     │              │              │               │                │             │            │
     │              │              │               │ TIMEOUT!       │             │            │
     │              │              │               │<─ ─ ─ ─ ─ ─ ─ │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ _record_failure()            │            │
     │              │              │               │ failures=1     │             │            │
     │              │              │               │                │             │            │
     │              │              │  (Episodes 2,3 also timeout at 120s)         │            │
     │              │              │               │ failures=2, 3  │             │            │
     │              │              │               │                │             │            │
     │              │              │               │ ┌─CIRCUIT BREAKER TRIP─────┐ │            │
     │              │              │               │ │ failures(3) >= max(3)    │ │            │
     │              │              │               │ │ → tripped = True         │ │            │
     │              │              │               │ │ "Graphiti disabled after │ │            │
     │              │              │               │ │  3 consecutive failures" │ │            │
     │              │              │               │ └─────────────────────────┘  │            │
     │              │              │               │                │             │            │
     │              │              │  Episodes 4-12: _check_circuit_breaker()     │            │
     │              │              │               │ → True (tripped)             │            │
     │              │              │               │ → return None (SKIPPED)      │            │
     │              │              │               │                │             │            │
     │              │              │  Result: 1/12 created          │             │            │
     │              │              │  (only if ep1 completed before │             │            │
     │              │              │   the first 3 consecutive      │             │            │
     │              │              │   timeouts hit)                │             │            │
     │              │              │               │                │             │            │
     │              │ Next template: reset_circuit_breaker()        │             │            │
     │              │─────────────────────────────>│ failures=0     │             │            │
     │              │              │               │ tripped=False  │             │            │
     │              │              │               │                │             │            │
     │              │ (Pattern repeats for each template batch)     │             │            │
     │              │══════════════════════════════════════════════════════════════│            │
```

---

## Sequence Diagram 2: Init Project Seeding — Timeout at 300s

```
┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐
│ init.py  │  │ project_ │  │graphiti_client│  │graphiti- │  │ FalkorDB │  │  vLLM  │
│ :738-744 │  │seeding.py│  │.py            │  │core      │  │ :6379    │  │ :8000  │
└────┬─────┘  └────┬─────┘  └──────┬────────┘  └────┬─────┘  └────┬─────┘  └───┬────┘
     │              │               │                │             │            │
     │ seed_project_│               │                │             │            │
     │ knowledge(   │               │                │             │            │
     │  "vllm-      │               │                │             │            │
     │   profiling") │               │                │             │            │
     │─────────────>│               │                │             │            │
     │              │               │                │             │            │
     │              │ seed_project_ │               │                │             │            │
     │              │ overview()    │               │                │             │            │
     │              │ (3 parsed     │               │                │             │            │
     │              │  episodes)    │               │                │             │            │
     │              │               │                │             │            │
     │              │ LOOP 3 episodes (project_seeding.py:139)     │            │
     │              │ ════════════════════════════════════════════  │            │
     │              │               │                │             │            │
     │              │ Episode 1/3: project_purpose_vllm-profiling  │            │
     │              │               │                │             │            │
     │              │ upsert_       │                │             │            │
     │              │ episode(      │                │             │            │
     │              │  group_id=    │                │             │            │
     │              │  "project_    │                │             │            │
     │              │   overview")  │                │             │            │
     │              │──────────────>│                │             │            │
     │              │               │                │             │            │
     │              │               │ _apply_group_  │             │            │
     │              │               │ prefix()       │             │            │
     │              │               │ "project_      │             │            │
     │              │               │  overview" IS  │             │            │
     │              │               │  in PROJECT_   │             │            │
     │              │               │  GROUP_NAMES   │             │            │
     │              │               │ → "vllm-       │             │            │
     │              │               │  profiling__   │             │            │
     │              │               │  project_      │             │            │
     │              │               │  overview"     │             │            │
     │              │               │                │             │            │
     │              │               │ add_episode()  │             │            │
     │              │               │  → _create_    │             │            │
     │              │               │   episode(     │             │            │
     │              │               │    group_id=   │             │            │
     │              │               │    "vllm-prof.│             │            │
     │              │               │    __project_  │             │            │
     │              │               │    overview")  │             │            │
     │              │               │                │             │            │
     │              │               │ ┌─CORRECT─────────────────┐  │            │
     │              │               │ │ group_id.endswith(      │  │            │
     │              │               │ │  "project_overview")    │  │            │
     │              │               │ │  → YES! ✓              │  │            │
     │              │               │ │                         │  │            │
     │              │               │ │ timeout = 300s          │  │            │
     │              │               │ └─────────────────────────┘  │            │
     │              │               │                │             │            │
     │              │               │ asyncio.wait_for(timeout=300s)             │
     │              │               │───────────────>│             │            │
     │              │               │                │ add_episode │            │
     │              │               │                │────────────>│ Cypher     │
     │              │               │                │             │ queries    │
     │              │               │                │             │            │
     │              │               │                │  LLM chat ──│───────────>│
     │              │               │                │  embeddings─│───────────>│
     │              │               │                │             │            │
     │              │               │                │  ...LLM slow (graph has  │
     │              │               │                │   106 system episodes    │
     │              │               │                │   from reseed)...        │
     │              │               │                │             │            │
     │              │               │                │  duplicate_facts warnings│
     │              │               │                │  (13x — LLM returns     │
     │              │               │                │   invalid edge indices)  │
     │              │               │                │             │            │
     │              │               │                │   ...300s elapse...      │
     │              │               │ TIMEOUT!       │             │            │
     │              │               │<─ ─ ─ ─ ─ ─ ─ │             │            │
     │              │               │                │             │            │
     │              │               │ _record_failure()            │            │
     │              │               │ (but no cascade — only 1     │            │
     │              │               │  failure in init, circuit    │            │
     │              │               │  breaker threshold is 3)     │            │
     │              │               │                │             │            │
     │              │ Episode 2/3: project_overview_vllm-profiling │            │
     │              │──────────────>│                │             │            │
     │              │               │ (same path, timeout=300s)    │            │
     │              │               │ Completed in 112.3s ✓       │            │
     │              │               │                │             │            │
     │              │               │ ┌─COROUTINE WARNING─────────┐│            │
     │              │               │ │ "resolve_extracted_edge   ││            │
     │              │               │ │  was never awaited"       ││            │
     │              │               │ │ (graphiti-core bug:       ││            │
     │              │               │ │  edge coroutine created   ││            │
     │              │               │ │  but not gathered)        ││            │
     │              │               │ └───────────────────────────┘│            │
     │              │               │                │             │            │
     │              │ Episode 3/3: project_architecture_vllm-profiling          │
     │              │──────────────>│                │             │            │
     │              │               │ Completed in 99.1s ✓        │            │
     │              │               │                │             │            │
     │ Result:      │               │                │             │            │
     │ 2/3 created  │               │                │             │            │
     │ 1 timed out  │               │                │             │            │
     │ 511.9s total │               │                │             │            │
     │              │               │                │             │            │
     │ ┌─DISPLAY BUG (init.py:753)─────────────────────────────┐  │            │
     │ │ Only shows results where success=True:                │  │            │
     │ │   "OK project_overview: Seeded from CLAUDE.md"        │  │            │
     │ │                                                       │  │            │
     │ │ The timed-out project_purpose episode returns         │  │            │
     │ │ episodes_created=0 but success=True (graceful         │  │            │
     │ │ degradation at project_seeding.py:180-184)            │  │            │
     │ │ → swallowed into the "OK" aggregate                   │  │            │
     │ └───────────────────────────────────────────────────────┘  │            │
```

---

## Sequence Diagram 3: Circuit Breaker State Machine

```
                    ┌─────────────────────────────────────────┐
                    │      Circuit Breaker State Machine       │
                    │      (graphiti_client.py:255-502)        │
                    └─────────────────────────────────────────┘

  ┌────────────────┐                                   ┌────────────────┐
  │                │  _record_failure()                 │                │
  │    CLOSED      │  failures < 3                      │    CLOSED      │
  │  (operational) │────────────────────────────────────│  failures++    │
  │  failures=0    │                                   │                │
  │                │                                   │                │
  └───────┬────────┘                                   └────────────────┘
          │
          │  _record_failure()
          │  failures >= 3  (graphiti_client.py:474)
          │
          ▼
  ┌────────────────┐
  │                │
  │    OPEN        │  _check_circuit_breaker() → True
  │  (tripped)     │  → all operations return None
  │  tripped=True  │  → episodes auto-skipped
  │  timestamp=now │
  │                │
  └───────┬────────┘
          │
          │  Two reset paths:
          │
          ├─── Path A: reset_circuit_breaker() ──────────────────────┐
          │    (explicit, called between categories/templates)       │
          │    seeding.py:172, seed_rules.py:265                    │
          │    → failures=0, tripped=False                          │
          │                                                          │
          ├─── Path B: Half-open timeout (60s elapsed)     ──────────┤
          │    _check_circuit_breaker() (graphiti_client.py:497)    │
          │    → auto-reset if 60s since trip                       │
          │    → failures=0, tripped=False                          │
          │                                                          │
          ▼                                                          │
  ┌────────────────┐                                                │
  │                │◀───────────────────────────────────────────────┘
  │    CLOSED      │
  │  (reset)       │  Next operation: if success → stays closed
  │  failures=0    │                  if failure → starts counting again
  │                │
  └────────────────┘


  Key insight: The circuit breaker counts CONSECUTIVE failures.
  A single success resets the counter (_record_success → failures=0).
  This is why mcp-typescript (2/4) and nextjs-fullstack (8/12) avoid
  tripping — their successes are interspersed with failures.

  Templates with homogeneous content (all similar size) are more likely
  to have consecutive timeouts → cascade.
```

---

## Sequence Diagram 4: Group ID Prefixing Flow

```
                         group_id Transformation Pipeline
                         ═════════════════════════════════

  seed_rules.py:267          seed_helpers.py:48         graphiti_client.py:1106     graphiti_client.py:973
  ─────────────────          ──────────────────         ───────────────────────     ─────────────────────

  group_id =                 client.add_episode(        _apply_group_prefix()       _create_episode()
  "rules_fastapi_            group_id=                  ↓                           timeout tier check
   python"                   "rules_fastapi_            is_project_group(           ↓
                              python")                  "rules_fastapi_python")
                                                        ↓
                                                        NOT in SYSTEM_GROUP_IDS     group_id ==
                                                        NOT starts with "guardkit_" "guardkit__rules_
                                                        → True (project group)       fastapi_python"
                                                        ↓
                                                        prefix with project_id      ≠ "rules"
                                                        ↓                           → FALLS TO ELSE
                                                        "guardkit__rules_           → timeout = 120s ✗
                                                         fastapi_python"

  ──────────────────────────────────────────────────────────────────────────────────────────────────
  COMPARISON: agents path (WORKS CORRECTLY)

  seed_agents.py:233         seed_helpers.py:48         graphiti_client.py:1106     graphiti_client.py:979

  group_id =                 client.add_episode(        _apply_group_prefix()       _create_episode()
  "agents"                   group_id=                  ↓                           timeout tier check
                              "agents")                 is_project_group("agents")  ↓
                                                        ↓
                                                        "agents" IS in              group_id ==
                                                        SYSTEM_GROUP_IDS            "agents"
                                                        → False (system group)      → YES! ✓
                                                        ↓                           → timeout = 150s ✓
                                                        NO prefix applied
                                                        ↓
                                                        "agents" (unchanged)
```

---

## Corrected Finding 3: Circuit Breaker Root Cause (Revised)

The circuit breaker cascade in the rules category has **two compounding root causes**:

### Root Cause 1: Timeout Tier Bug (CRITICAL — NEW)

Rules episodes receive **120s timeout** instead of the intended **180s** because:
- `seed_rules.py:267` uses per-template group_ids: `"rules_{template_id}"`
- `_group_defs.py:43` only registers bare `"rules"` as a system group
- `graphiti_client.py:1106` therefore prefixes the group_id (project scope)
- `graphiti_client.py:975` checks `group_id == "rules"` — exact match fails

**Fix**: Change line 975 from:
```python
elif group_id == "rules":
```
to:
```python
elif "rules" in group_id:
```
Or more precisely: `elif group_id == "rules" or "_rules_" in group_id or group_id.startswith("rules_") or group_id.endswith("__rules"):`.

### Root Cause 2: Within-Template Cascade (CONFIRMED from init_9, still present)

Even with correct 180s timeout, the circuit breaker trips after 3 consecutive timeouts within a template batch. Per-template reset (seed_rules.py:262-265) prevents cross-template cascade but does NOT help within a template.

Templates with many rules (fastapi-python: 12, react-fastapi-monorepo: 21) only need 3 consecutive timeouts to lose the remaining episodes.

### Combined Effect

With **120s** (buggy) timeout: Rules that would complete between 120-180s are killed → more timeouts → faster cascade → 47/72 skipped.

With **180s** (correct) timeout: Many of these would succeed → fewer consecutive failures → fewer cascades → significantly more than 25/72 would succeed.

**Estimated improvement**: Based on episode timing data from reseed_guardkit_1, the successful rule episodes complete in 41-118s. At 180s timeout, episodes in the 120-180s range would succeed instead of failing, potentially reducing cascade triggers by 30-50%.

---

## Finding 1: Reseed Phase — All 17 Categories Assessment

| # | Category | Result | Episodes | Time Range (ms) | Notes |
|---|----------|--------|----------|-----------------|-------|
| 1 | product_knowledge | OK | 3/3 | 27,765-53,618 | Clean |
| 2 | command_workflows | PARTIAL | 19/20 | 10,584-116,169 | 1 skipped: `command_feature_spec` timed out at 120s |
| 3 | quality_gate_phases | OK | 12/12 | 20,981-51,844 | Clean |
| 4 | technology_stack | OK | 7/7 | 4,012-118,769 | Improved from 6/7 in init_9 |
| 5 | feature_build_architecture | OK | 8/8 | 6,704-72,704 | Improved from 7/8 in init_9 |
| 6 | architecture_decisions | OK | 3 ADRs | 71,711-110,861 | Clean |
| 7 | failure_patterns | OK | 4/4 | 28,135-43,395 | Clean |
| 8 | component_status | PARTIAL | 5/6 | 15,500-113,912 | 1 skipped: `component_taskwork_interface` timed out at 120s |
| 9 | integration_points | OK | 3/3 | 15,500-55,960 | Clean |
| 10 | templates | PARTIAL | 3/7 | 23,831-155,143 | 4 skipped: all timed out at 180s (correct tier) |
| 11 | agents | PARTIAL | 6/18 | 46,133-106,635 | 12 skipped: 3x 150s timeouts → circuit breaker → 9 auto-skipped |
| 12 | patterns | OK | 5/5 | 15,443-62,179 | Clean |
| 13 | rules | PARTIAL | 25/72 | 41,511-118,026 | 47 skipped — **120s timeout bug** + circuit breaker cascade |
| 14 | project_overview | OK | 3/3 | 40,190-138,319 | Major improvement — was 0/3 in init_9 |
| 15 | project_architecture | OK | 3/3 | 70,564-106,876 | Major improvement — was 0/3 in init_9 |
| 16 | failed_approaches | OK | 5/5 | 38,520-73,800 | Clean |
| 17 | pattern_examples | OK | 17/17 | 44,583-92,924 | 5 dataclass + 5 Pydantic + 7 orchestrator |

**Total**: 106/171 episodes = **62.0%** (12 full, 5 partial, 0 failed)

---

## Finding 2: Init Phase Analysis (init_project_10)

| Episode | Time | Status | Timeout Tier | Group ID After Prefix |
|---------|------|--------|-------------|----------------------|
| 1/3 (project_purpose) | 300.5s | TIMEOUT | 300s (correct) | `vllm-profiling__project_overview` |
| 2/3 (project_overview) | 112.3s | OK | 300s (correct) | `vllm-profiling__project_overview` |
| 3/3 (project_architecture) | 99.1s | OK | 300s (correct) | `vllm-profiling__project_overview` |

**Total**: 511.9s (8.5 min). The init path timeout tiers are **correct** — `group_id.endswith("project_overview")` matches the prefixed group_id. The project_purpose timeout is a genuine LLM/graph density issue, not a tier bug.

**Display bug**: `init.py:753` only shows `OK project_overview: Seeded from CLAUDE.md` — the timeout on project_purpose is swallowed because `project_seeding.py:180-184` returns `success=True` even with 0 episodes created (graceful degradation).

---

## Finding 4: Warning Investigation

### 4a. `resolve_extracted_edge was never awaited`

**Location**: init_project_10 line 54 (during episode 2/3)
**Root cause**: graphiti-core upstream bug — a coroutine is created but not gathered in the edge resolution pipeline.
**Impact**: Medium — some edges silently dropped. Appears only once in init, not in reseed (lower graph density during early reseed phases).

### 4b. `duplicate_facts idx` Warnings

| Run | Count | Per Episode |
|-----|-------|-------------|
| reseed_guardkit_1 | 269 | ~2.5 |
| init_project_10 | 13 | ~4.3 |

**Root cause**: graphiti-core upstream — vLLM returns invalid edge indices during deduplication. Safely ignored by the library. Correlates with graph density (more existing edges → more dedup candidates → more LLM errors).

---

## Finding 5: Cross-Run Trend Analysis

| Metric | init_8 | init_9 (final) | init_10 | reseed_guardkit_1 |
|--------|--------|----------------|---------|-------------------|
| Seed success | Unknown | 52% | N/A | 62% |
| Rules | Unknown | 1/72 | N/A | 25/72 |
| project_overview | Unknown | 0/3 | N/A | 3/3 |
| Init total time | 392.5s | 228.0s | 511.9s | N/A |
| Init ep1 time | 249.7s | 31.0s | 300.5s TIMEOUT | N/A |

**Convergence assessment**: FEAT-SPR delivered measurable improvement: 52% → 62% success rate, rules from 1/72 to 25/72, cross-category cascade eliminated, honest display and summary working. The pipeline is converging. The rules category remains the critical weakness due to the timeout tier regression introduced by TASK-SPR-18fc — fixing this one-line bug should push the overall rate above 75%.

---

## Finding 6: FEAT-SPR Task Assessment — All 5 Verified in Run Output

All 5 FEAT-SPR tasks were implemented via `/task-work`, completed, and **confirmed active in the reseed_guardkit_1 and init_project_10 run output**.

| Task | Status | Code Evidence | Run Output Evidence |
|------|--------|--------------|---------------------|
| TASK-SPR-5399 | **Verified** | `seeding.py:172` — reset between categories | Per-template results vary independently (mcp-typescript 2/4, nextjs 8/12) — no cross-template cascade |
| TASK-SPR-18fc | **Verified** | `seed_rules.py:261-274` — per-template batching | Log lines 5890-8581: `rules/default`, `rules/fastapi-python`, etc. shown separately |
| TASK-SPR-2cf7 | **Verified** | `graphiti.py:174-202` — ✓/⚠/✗ display | Log lines 10386-10402: `✓ product_knowledge`, `⚠ rules (25/72 episodes, 47 skipped)` |
| TASK-SPR-9d9b | **Verified** | `graphiti.py:207-237` + `seeding.py:208-254` | Log lines 10404-10408: `Categories: 12/17`, `Episodes: 106/171 (62.0%)`, `Duration: 209m 29s` |
| TASK-SPR-47f8 | **Verified** | `graphiti_client.py:769-834` — `wait_for_llm_endpoints()` | No connection errors in either run (vLLM was available) |

**Note on init path**: The `guardkit init` CLI path (`init.py:753`) still uses the simpler `OK`/`WARN` status display. This is a separate UI path from the `guardkit graphiti seed` path. TASK-SPR-2cf7 targeted the seed display (which handles 17 categories) — the init path only seeds 3 project episodes and was not in scope.

**Regression from TASK-SPR-18fc**: The per-template batching created group_ids like `rules_fastapi_python` that don't match the timeout tier at `graphiti_client.py:975`. This was introduced by the fix and is visible in the run output: rules categories show high skip rates (47/72 total) despite per-template isolation working correctly. The 120s timeout (instead of intended 180s) is the primary remaining bottleneck.

---

## Recommendations (Revised Priority — Post FEAT-SPR)

### Priority 1: Fix Rules Timeout Tier Bug (CRITICAL — TASK-SPR-18fc regression)

**File**: `graphiti_client.py:975`
**Current**: `elif group_id == "rules":`
**Problem**: TASK-SPR-18fc changed `seed_rules.py:267` to use `group_id = f"rules_{template_id}"` (e.g. `"rules_fastapi_python"`). After prefixing this becomes `"guardkit__rules_fastapi_python"`. The exact match `== "rules"` at line 975 never matches, so rules fall through to the 120s default instead of the intended 180s.
**Fix**: Change to `"rules" in group_id` or use `group_id.startswith("rules")` (pre-prefix) or `"rules" in group_id` (post-prefix)

**Expected impact**: Rules success rate should improve from 25/72 (34.7%) to an estimated 40-50/72 (55-70%) as episodes in the 120-180s range stop timing out.

**Suggested task**: Create TASK-FIX for this one-line fix + add a test that verifies timeout tier assignment for prefixed group_ids.

### Priority 2: Improve Init Path Display (Optional follow-up)

**File**: `init.py:753` and `project_seeding.py:180-184`
**Context**: The `guardkit graphiti seed` path now has ✓/⚠/✗ display (TASK-SPR-2cf7). The `guardkit init` path still uses `OK`/`WARN` — timeouts return `success=True` with 0 episodes, making them invisible.
**Scope**: Not a FEAT-SPR gap, but a nice-to-have for init UX consistency.

### Priority 3: Monitor `resolve_extracted_edge` Warning

Track across future runs. Open upstream graphiti-core issue if frequency increases. This is an unawaited coroutine in graphiti-core's edge resolution pipeline.

### Priority 4: Consider Within-Template Retry Strategy

Even with the 180s fix, templates with 12+ rules will still cascade if 3 consecutive episodes time out within a single template batch. Consider:
- **Shuffling** episode order within a template batch (spread heavy episodes)
- **Increasing max_failures** for rules batches (e.g., 5 instead of 3)
- **Adding a cooldown** between episodes within a batch

### Priority 5: Investigate Init Timing Regression

Init_10 (511.9s) is 30% slower than init_8 (392.5s). Likely graph density growth (more edges to deduplicate) rather than a code issue. `duplicate_facts idx` warnings increased significantly (13 in init_10 vs ~3 in init_8), supporting graph growth hypothesis. Monitor in future runs.

### Priority 6: Run Post-Fix Verification

After fixing P1, run `guardkit graphiti seed --force` and compare:
- Rules success rate (target: >60%)
- Total seed success rate (target: >75%)
- Circuit breaker trip count (target: <=2)
- The ✓/⚠/✗ display and summary statistics will now provide clear visibility into results

---

## Acceptance Criteria Assessment

- [x] Reseed phase analysed: all 17 categories assessed (12 full, 5 partial, 0 failed)
- [x] Init phase analysed: 3 project episodes assessed (1 timeout, 2 OK)
- [x] Circuit breaker behaviour documented (root cause traced to source with line numbers)
- [x] Coroutine warning investigated (`resolve_extracted_edge` — upstream bug)
- [x] duplicate_facts warnings assessed (269+13 — upstream LLM quality issue)
- [x] Comparison with init_project_8 and init_project_9
- [x] FEAT-SPR task relevance confirmed: all 5 completed and verified in run output
- [x] Cross-run trend analysis (pre-SPR init_9 → post-SPR reseed_1/init_10): converging, +10pp success rate
- [x] Recommendations for next steps (6 prioritised — P1 timeout tier regression fix as sole critical item)
