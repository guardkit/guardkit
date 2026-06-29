# HANDOFF — FEAT-MEM-08 (Graphiti → fleet-memory cutover) — 2026-06-29

Pick-up doc for the next conversation. **Next action: TASK-MEM08-005 (dual-write soak), then
merge → 010 → FEAT-MEM-09.** Everything below is verified unless marked TODO.

## Where we are

Autobuilt 8/10 (SDK harness); the rest finished by hand on branch **`autobuild/FEAT-MEM-08`**.

| Step | State |
|---|---|
| 009 config/docs flip | ✅ done (`.mcp.json`→fleet_memory stdio, `task-complete.md`, `graphiti.yaml`, rules/CLAUDE.md) |
| embed dims | ✅ corrected 768→**1024** (`embed` = Qwen3-Embedding-0.6B); verified 4 ways incl. stored `store_vectors.embedding :: vector(1024)` |
| secrets | ✅ moved to gitignored repo-root `.env` (env-indirection); non-secret embed infra in `graphiti.yaml` per TASK-REV-D2B5 |
| **006 reads** | ✅ **was a STUB, now real** — TASK-MEM08-011: `FleetMemoryClient.search` reuses `fleet_memory.retrieval.search`+`assemble_context`; added `enabled`/`initialize`/`health_check`/`close`. **007 PASSES** (live: result_count>0, 0.901 hit, context injected; 47 tests green) |
| Python pin | ✅ `.mcp.json` launches via `uv run --project ../fleet-memory`; `GUARDKIT_BOOTSTRAP_PYTHON` override added to env_bootstrap |
| **005 soak** | ⏭️ **NEXT — option a** |
| merge (`/feature-complete`) | ⏭️ after 005 |
| 010 sign-off | ⏭️ after merge (live MCP server + `guardkit memory`) |
| FEAT-MEM-09 decommission | ⏭️ after 010 sign-off |

### Branch commits (`autobuild/FEAT-MEM-08`)
`3ce7b920` 009 config/docs · `5a0423d2` embed→1024 · `bf8fb7c4` secrets→.env ·
`422d8b1e` real reads (TASK-MEM08-011) · `7cfab70b` .mcp.json uv-run launch

## Environment the next session needs (all verified present)

- **Python 3.12** is required for the read path (fleet-memory is `>=3.12`; guardkit is `>=3.11`).
  Host `python3` = 3.12.3. The fleet-memory repo venv (`../fleet-memory/.venv`, 3.12, has
  `fleet_memory`) is the easiest interpreter for ad-hoc verification.
- **`.env`** at the guardkit repo root (gitignored) holds the real `FLEET_MEMORY_*` (PG_DSN →
  `whitestocks.tailebf801.ts.net:5433/fleet_memory`, NATS auth, `embed`/1024). Loaded by both
  fleet_memory `Settings` and guardkit `load_dotenv`. From an autobuild **worktree**, guardkit's
  dotenv search stops at the worktree → pass `--env-file <repo>/.env` or run from the repo root.
- **Live infra (verified up):** relay container `fleet-memory-relay` (healthy 20h+), NATS
  `localhost:4222`, NAS Postgres (679-row corpus, all `payload_type=chunk`, 1024-dim).
- **For any re-autobuild of this feature:** `GUARDKIT_BOOTSTRAP_PYTHON=3.12 guardkit autobuild
  feature FEAT-MEM-08 --resume` (the 3.11 bootstrap default can't host fleet-memory).
- **For host CLI / live MCP:** install on 3.12: `uv sync --extra memory` (honours `[tool.uv.sources]`
  → editable `../fleet-memory`). Requires `../fleet-memory` and `../nats-core` checked out alongside.

### Re-verify reads in 30s (sanity before starting)
```bash
cd <guardkit-repo-root>
set -a; . ./.env; set +a; export FLEET_MEMORY_ENABLED=true PYTHONPATH="$PWD"
../fleet-memory/.venv/bin/python - <<'PY'
import asyncio
from guardkit.knowledge.fleet_memory_client import init_memory_client, get_memory_client, _load_fleet_config_from_env
async def m():
    init_memory_client(backend="fleet_memory", fleet_config=_load_fleet_config_from_env())
    c = get_memory_client()
    print("health:", await c.health_check(), "| hits:", len(await c.search("memory cutover", num_results=5)))
    await c.close()
asyncio.run(m())
PY   # expect health: True | hits: 1
```

## NEXT — TASK-MEM08-005 (dual-write soak) — option a

Task: `tasks/backlog/memory-cutover/TASK-MEM08-005-dual-write-soak-audit.md` (operator_handoff).
Goal: with `backend=dual`, every Graphiti task-outcome/ADR write **also** lands in fleet-memory's
Postgres, audited by natural key; `memory.dlq` empty. This is the W2 gate before reads cut over.

Steps:
1. `.guardkit/graphiti.yaml`: set `backend: dual` + `enabled: true` (currently `fleet_memory`/`false`).
   Export `FLEET_MEMORY_ENABLED=true`, the `FLEET_MEMORY_*` (from `.env`), and `GUARDKIT_NATS_PASSWORD`.
2. Drive real completions over a soak window — e.g. `guardkit task-complete` on a few tasks / ADR captures.
3. Audit published == stored: query the NAS store by natural key (`build_outcome:guardkit:<task_id>`,
   `adr:guardkit:<id>`). Connect: `psql "$FLEET_MEMORY_PG_DSN"` ; rows live under namespace
   `fleet_memory.guardkit.*`. Confirm `memory.dlq` is empty (relay logs: `docker logs fleet-memory-relay`).
4. Record the audit (published/stored counts, window, sign-off) under
   `docs/design/specs/memory-cutover/`.

**DECISION for the operator:** dual mode requires Graphiti **enabled** (re-enable the FalkorDB client),
but Graphiti is being decommissioned (FEAT-MEM-09) and the corpus was already populated via the
FEAT-HARV harvest relay (not guardkit dual-write). Decide whether to (a) run a genuine dual-write soak,
or (b) treat the harvest as the soak evidence and proceed. Either way, record the rationale.

## Then — merge, 010, FEAT-MEM-09

- **Merge:** `/feature-complete FEAT-MEM-08` (merges the branch + archives). Reconcile statuses:
  TASK-MEM08-011 is `in_review`; the feature YAML lists 10 tasks (011 is the new follow-up — add it
  or note it). 009/011 deliverables are on the branch; the secrets `.env` is operational (gitignored).
- **010 (live MCP):** from a fresh Claude Code session at the merged repo root, confirm the
  `.mcp.json` `fleet_memory` server starts (`uv run --project ../fleet-memory python -m fleet_memory.mcp`)
  and `mcp__fleet_memory__memory_search` responds; `guardkit memory search "<q>"` returns results;
  `guardkit memory status` healthy. Record sign-off + green-light FEAT-MEM-09.
- **FEAT-MEM-09:** decommission Graphiti / drop Qwen2.5 (see memory `graphiti-cutover-qwen25-removal`).

## Gotchas / lessons (don't relearn)

- **The read path was a stub that passed the per-task Coach** because 006/002 tests mock the client
  (per-task-green-is-not-feature-green). 007 (the assembly gate) caught it. Verify memory features
  against the **live store**, not mocks. Evidence: `TASK-MEM08-007-read-path-evidence.md`.
- **Corpus is `chunk`-only.** GROI queries whose `group_ids` map to `build_outcome`/`document`/`warning`
  payload types return 0 until the soak (005) populates them; unfiltered/search-all queries hit the
  679 doc chunks. Reads are functional; enrichment grows with the soak.
- **`.mcp.json` `command: python` would fail** (no bare `python` on host; fleet-memory needs 3.12) —
  hence `uv run --project ../fleet-memory`.

## Key files
- Reads: `guardkit/knowledge/fleet_memory_client.py` (search/initialize/health_check/close)
- Readers: `guardkit/knowledge/feature_plan_context.py`, `guardkit/planning/coach_context_builder.py`
- Mapping: `guardkit/knowledge/fleet_memory_mapping.py` (group_id → payload_type)
- Config: `.guardkit/graphiti.yaml` (backend flag + embed infra), repo-root `.env` (secrets)
- Bootstrap pin: `guardkit/orchestrator/environment_bootstrap.py` (`GUARDKIT_BOOTSTRAP_PYTHON`)
- Query-log evidence: `.guardkit/graphiti-query-log.jsonl` (written by the GROI readers)
