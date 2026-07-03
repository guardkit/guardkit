# FEAT-MEM-09 §3.3 W1 — read-consumer settle: shared implementation guide

> Read this **before** any `TASK-MEM09-*` task in this folder. It carries the contract every task
> shares so each task file can stay short. Source of scope:
> [`docs/design/specs/memory-cutover/FEAT-MEM-09-3.3-code-scoping-2026-07-03.md`](../../../docs/design/specs/memory-cutover/FEAT-MEM-09-3.3-code-scoping-2026-07-03.md)
> (Fork A = Hybrid/repoint, Fork B = follows A — both **operator-confirmed 2026-07-03**).

---

## 1. What W1 is (and is NOT)

**Context.** The graphiti *implementation* was deleted in WS-2c. Every remaining read-consumer already
reads fleet-memory **through the shim** `get_memory_client()` (`guardkit/knowledge/fleet_memory_client.py`)
— **nothing imports a removed symbol**, the suite is green. The reads *work*. FEAT-MEM-08 (TASK-MEM08-006)
already wired `memory_search` into the GROI/context readers.

**So W1 is a SETTLE + PROVE wave, not a rewrite:**
1. **Settle** the legacy `group_id` read lists so each consumer's reads are honest and useful under the
   current shim routing (§2), keeping Fork A's Hybrid intent (keep high-value autobuild read-enrichment;
   drop only dead vestiges).
2. **Prove** each read fires against the **real** fleet-memory seam — replacing the current
   **mocked-shim tests** (which are the `per-task-green-is-not-feature-green` anti-pattern) with a
   **boundary test** (real shim + mapping, external MCP boundary stubbed) **plus** a `@pytest.mark.live`
   round-trip that runs for-real when the store is enabled.

**NOT in W1:** deleting graphiti implementation (done in WS-2c), infra/FalkorDB decommission (§3.5,
operator-only), or a new dataset sink (separate follow-up).

---

## 2. The shim's read routing (the fact every task depends on)

`fleet_memory_client.FleetMemoryClient.search(query, group_ids=[...])`
([`fleet_memory_client.py:227-300`](../../../guardkit/knowledge/fleet_memory_client.py#L227)) resolves each
`group_id` via `fleet_memory_mapping.resolve(gid)`:

| group disposition | shim behavior | effect |
|---|---|---|
| **migrate** (e.g. `architecture_decisions`→`adr`/`[system]`, `failure_patterns`→`warning`/`[failure,pattern]`, `task_outcomes`→`build_outcome`/`[task]`, `turn_states`→`document`/`[turn,state]`) | adds `payload_type` (+ `domain_tags` for `document`) to the filter | **typed, filtered** search over the migrated records |
| **retire** or **unmapped** (e.g. `product_knowledge`, `command_workflows`, `quality_gate_phases`, `feature_build_architecture`, `role_constraints`, `feature_overviews`) | contributes **no** filter | leaves `payload_types`/`domain_tags` empty → **unfiltered semantic search over the whole store** (which *includes* the 679-chunk harvest corpus) |

**Two consequences every task must respect:**
- A read of **only retire groups** already hits the harvest corpus via whole-store semantic search — so the
  query *text* is what makes it useful. Keep the read; make the query specific.
- **Mixing migrate + retire group_ids in one `search()` call is a trap:** the migrate group's
  `payload_type`/`domain_tags` filter then *restricts* the whole-store intent of the retire group. If a
  consumer needs both a typed read and a corpus read, **split them into separate `search()` calls.**

The authoritative table is `guardkit/knowledge/fleet_memory_mapping.py` (`resolve(group_id)` → `payload_type`,
`domain_tags`, `disposition`). Do not hardcode the mapping in consumers — call `resolve()`.

---

## 3. The two-test pattern (baked into every task — this is the point)

The current consumer tests (`tests/knowledge/test_context_loader.py`,
`test_job_context_retriever.py`) do `mock_client = MagicMock(); mock_client.search = AsyncMock(...)` and
patch `get_memory_client` to return it. **That mocks the primary first-party seam** → the Coach can approve
with zero evidence the real read path works. This is exactly
[`.claude/rules/per-task-green-is-not-feature-green.md`](../../../.claude/rules/per-task-green-is-not-feature-green.md).
Each task MUST replace/augment it with:

**(a) Boundary test — REAL shim + mapping, external MCP boundary stubbed (autobuild-runnable, always runs).**
Patch **only** the true external boundary — the `memory_search` MCP/subprocess call at the very edge of
`FleetMemoryClient.search` — NOT `get_memory_client` and NOT `FleetMemoryClient`. Then assert the **real**
`get_memory_client()` → `FleetMemoryClient.search()` → `fleet_memory_mapping.resolve()` path ran and produced
the **correct `memory_search(payload_types=[...], domain_tags=[...])` args** for each read. Example intent:

```python
# _load_architecture_decisions must resolve architecture_decisions -> payload_types=["adr"], domain_tags=["system"]
captured = {}
def fake_memory_search(**kw): captured.update(kw); return {"context_block": "", "coverage_score": 0.0}
# patch ONLY the MCP/subprocess edge inside fleet_memory_client (the real boundary), then:
await _load_architecture_decisions(get_memory_client())
assert captured["payload_types"] == ["adr"]
assert captured["domain_tags"] == ["system"]        # proves the real mapping+shim ran, not a mock
```
Mocking the external MCP edge is **allowed** by the rule ("mocking a true external boundary … is correct");
mocking `get_memory_client`/`FleetMemoryClient` is **not** (that's the mocked-primary-seam defect).

**(b) Live round-trip — `@pytest.mark.live` (skips in autobuild, real proof when store is up).**
The `live` marker is registered (`pytest.ini:37` — "Live tests requiring real infrastructure"). Locally and
in the autobuild worktree the store is **DISABLED** (`guardkit memory status` → `Status: DISABLED`), so this
test **skips cleanly** (autobuild stays green). With the store enabled (operator / post-merge), it asserts a
**non-empty** result:

```python
@pytest.mark.live
@pytest.mark.asyncio
async def test_<consumer>_returns_real_context_live():
    from guardkit.knowledge.fleet_memory_client import get_memory_client
    client = get_memory_client()
    if client is None or not client.enabled:
        pytest.skip("fleet-memory store not enabled (Status: DISABLED)")
    ctx = await load_critical_context(...)          # the real consumer entry point
    assert any(ctx.<field> for field in ...)         # real hits from the live store
```

**Acceptance for the live proof is operator-run**, mirroring FEAT-MEM-08's `operator_handoff` split
(MEM08-007 "PROVE a real run reads"): the autobuild Coach approves on the **boundary test** (real seam,
no network); the operator runs `pytest -m live` with the store enabled to sign off the round-trip. Note this
in each task's "Operator verification" section.

---

## 4. Per-task-green / anti-mock guardrails (hard requirements)

- **Do NOT** `MagicMock`/`AsyncMock` `get_memory_client` or `FleetMemoryClient` as the *primary* assertion of
  "the read works." Boundary-stub the MCP edge instead (§3a).
- **Keep** the existing graceful-degradation tests (client `None` / `enabled=False` / exception → empty) —
  those are correct and must stay green.
- **Do NOT** hardcode `payload_type`/`domain_tags` in the consumer — resolve via `fleet_memory_mapping`.
- A read that returns empty because the store is disabled is an **absent** signal, never a pass — the boundary
  test asserts the *call was correctly formed*, the live test asserts *real hits*. (Absence-of-failure family.)

---

## 5. Run / verify

```bash
# autobuild a single task (store disabled → live tests skip, boundary tests run):
guardkit autobuild task TASK-MEM09-CTXLOAD

# full unit gate (must stay at the 7 pre-existing fails, zero new):
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --timeout=120 -q --tb=no tests/ | tail -3

# operator live proof (store ENABLED), post-merge:
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/knowledge/ -v
```

Baseline of 7 pre-existing fails: see the §3.3 scoping doc / `[[main-has-preexisting-red-tests]]`.
