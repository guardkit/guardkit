---
complexity: 6
consumer_context:
- consumes: GROUP_ID_MAP
  driver: in-process import
  format_note: resolve(group_id) -> GroupMapping(project, payload_type, domain_tags,
    disposition); None = retired/unmapped → fail-open skip
  framework: guardkit.knowledge.fleet_memory_mapping (dict[str, GroupMapping] + resolve())
  task: TASK-MEM08-001
dependencies:
- TASK-MEM08-001
feature_id: FEAT-MEM-08
id: TASK-MEM08-002
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: completed
task_type: feature
title: Add fleet_memory_client.py adapter (graphiti-client-shaped, flag-switched)
wave: 2
---

# TASK-MEM08-002 — fleet_memory_client.py adapter + config

> Source: brief — "Add an adapter `guardkit/knowledge/fleet_memory_client.py` exposing the same shape
> graphiti_client.py call-sites use, switched by a config flag, so callers change by swapping the factory
> not every call." **No behaviour change to existing call-sites in this task** — adapter + config only.

## Goal

Create a fleet-memory client whose public surface matches the subset of `graphiti_client.py` that
call-sites actually use (factory + `add_episode` + `search`), so W2/W3 repoint by swapping the factory.

## Deliverables

1. `guardkit/knowledge/fleet_memory_client.py`:
   - `FleetMemoryClient` with:
     - `async def search(query, group_ids=None, num_results=10, scope=None) -> list[dict]` — calls fleet-memory
       `memory_search(project="guardkit", query, payload_types, domain_tags, token_budget)` (payload_types/
       domain_tags derived from `group_ids` via `fleet_memory_mapping.resolve`), and **adapts the single
       `context_block` response into the existing `[{"fact","uuid","score"}, …]` shape** readers expect
       (one synthetic hit carrying the context block, or split on headings — keep `fact` text intact).
     - `async def add_episode(name, episode_body, group_id, source="user_added", entity_type="generic") -> str|None`
       — resolves `group_id` via the mapping, builds the typed `MemoryEpisodeV1` (or `memory_write_payload`
       dict), and writes via the configured write path; returns the natural key.
   - A **factory** mirroring graphiti's: `get_memory_client()` / `init_memory_client(config)` returning the
     fleet-memory client **or** the graphiti client based on the config flag (the swap point).
2. Config (`guardkit/knowledge/config.py` + `.guardkit/graphiti.yaml`): a `backend` flag
   (`graphiti` | `fleet_memory` | `dual`) and `FLEET_MEMORY_*` env wiring (PG_DSN, EMBED_URL/MODEL/DIMS,
   NATS_URL). Default `graphiti` (no behaviour change until W2 flips it).
3. Unit tests with the fleet-memory MCP/NATS boundary **mocked** (no live infra).

## Acceptance Criteria

- [ ] `FleetMemoryClient.search` returns the same `list[dict]` shape (`fact`, `uuid`, `score`) the existing
      readers consume; a generous default `token_budget` is applied (relevant heading must land).
- [ ] `FleetMemoryClient.add_episode` maps `group_id` → typed payload via `fleet_memory_mapping`, and an
      unmapped/`retire` group_id is a **no-op that returns None** (fail-open — never raise).
- [ ] The factory returns a fleet-memory / graphiti / dual client purely from config; default is `graphiti`.
- [ ] No existing call-site is modified in this task (grep: `coach_context_builder`, `feature_plan_context`,
      `outcome_manager`, `adr_service` unchanged).
- [ ] Unit tests mock the fleet-memory boundary (MCP tool calls / `nats_core.publish_episode`); no test
      touches live Postgres/NATS. Cover: search shape, write mapping, unmapped-group no-op, flag routing.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
pytest tests/unit/knowledge/test_fleet_memory_client.py -v
python -c "import guardkit.knowledge.fleet_memory_client as m; assert hasattr(m,'get_memory_client')"
```

## Seam Tests

```python
"""Seam test: verify FleetMemoryClient.search returns the graphiti-shaped contract."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("fleet_memory_search_shape")
def test_fleet_memory_search_returns_fact_dicts():
    """Readers consume only fact/uuid/score; the adapter must preserve that shape.

    Contract: search(query, group_ids) -> list[{"fact": str, "uuid": str, "score": float}]
    Producer: TASK-MEM08-001 mapping + fleet-memory memory_search
    """
    # With memory_search mocked to return {"context_block": "...", ...},
    # FleetMemoryClient.search must yield list[dict] each carrying a non-empty "fact".
    hits = []  # await client.search("q", group_ids=["task_outcomes"])
    for h in hits:
        assert "fact" in h and h["fact"], "each hit must carry non-empty fact text"
```

## Implementation Notes

The adapter is the §4 contract producer for W2/W3/W4. Do **not** reason over graph edges — fleet-memory
has no topology; `memory_search` returns one context block.

**⚠️ Do NOT `import fleet_memory` in guardkit.** fleet-memory is *not* a guardkit dependency (no
`[tool.uv.sources]` entry, no extra) and would `ModuleNotFoundError` in the autobuild worktree venv.
Reach fleet-memory only via:
- **writes:** `nats_core.publish_episode(MemoryEpisodeV1(...))` — `nats_core` IS wired (the `memory`
  extra → editable `../nats-core`); build the typed `build_outcome`/`adr` body as a **dict** matching the
  fleet-memory payload schema (TASK-MEM08-003), not by importing `fleet_memory.payloads`. Optionally the
  `memory_write_payload` MCP tool.
- **reads:** the `memory_search` MCP tool (the `.mcp.json` fleet-memory stdio server).

Pick one default write path and **mock it in tests** (no live NATS/MCP). See
`.claude/rules/namespace-hygiene.md` — also do not name the module `fleet_memory` (that is the sibling's
import name); `fleet_memory_client` is collision-safe.