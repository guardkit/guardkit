# TASK-INF-5053 — Investigation audit

Date: 2026-05-02
Investigator: /task-work session
Outcome: Pivot to **document-and-close**. Original bug premise (server-side `group_id` coercion) is not reproducible against the running server. The real symptom that motivated TASK-FIX-B1F7 ("episode never appears under requested group on subsequent search") has a different root cause: silent LLM-extraction failure due to misrouted OpenAI calls.

## Premise (from TASK-FIX-B1F7 and TASK-INF-5053)

> The HTTP MCP server at `http://promaxgb10-41b1:8004/mcp` accepts a `group_id` parameter on `mcp__graphiti__add_memory` calls but silently overrides it with a server-side default (typically `product_knowledge`).

Cited evidence in TASK-FIX-B1F7 (verbatim):

```
# Server response:
# {"result":{"message":"Episode 'Task Completion: TASK-FPSG-003'
#   queued for processing in group 'product_knowledge'"}}
```

## Verification

### Deployment fingerprint

| Property | Value |
|---|---|
| Host | `promaxgb10-41b1` (reachable over Tailscale) |
| Container | `graphiti-mcp` |
| Image | `graphiti-mcp-standalone:local` (sha `2f486a69120c`) |
| Image built | 2026-04-24T17:20:04 +01:00 |
| Container created/started | 2026-05-02T10:34:31Z |
| Bootstrap | mounted from `/home/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-bootstrap.py` |
| Config | mounted from `/home/richardwoollcott/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml` |
| graphiti-core version | 0.28.1 |
| mcp library version | 1.27.0 |

The image and the bootstrap+config mounts have not changed since before TASK-FIX-B1F7 was filed at 14:45Z on 2026-05-02 — the same code path is what TASK-FIX-B1F7 was probing.

### Source-level inspection

`/app/mcp/src/graphiti_mcp_server.py` (running in the container), lines 374-375:

```python
# Use the provided group_id or fall back to the default from config
effective_group_id = group_id or config.graphiti.group_id
```

This is the standard "client-wins, fall back to default" pattern. There is no override. The same pattern repeats for the search functions (lines 430-435, 514-519, 639-644).

### Probe results (2026-05-02 16:13Z)

```
Request:
  mcp__graphiti__add_memory(
    name="TASK-INF-5053 probe2",
    episode_body="...",
    group_id="guardkit__test_inf5053",
    source="text",
  )

Response:
  {"result":{"message":"Episode 'TASK-INF-5053 probe2' queued for processing
   in group 'guardkit__test_inf5053'"}}

Server log (correlated by timestamp):
  2026-05-02 16:13:47 - services.queue_service - INFO -
    Processing episode None for group guardkit__test_inf5053
```

The server received the call, routed it to the requested group, and reported back the same group in the response message. **The server-side coercion bug as described does not exist** in the current image (which has been the only image since 2026-04-24).

### Why the original symptom looked like coercion

The probe's episode then fails background extraction:

```
2026-05-02 16:13:48 - httpx - INFO -
  HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 401 Unauthorized"
2026-05-02 16:13:48 - graphiti_core.llm_client.openai_base_client - ERROR -
  OpenAI Authentication Error: Error code: 401 -
  {'error': {'message': 'Incorrect API key provided: not-need*********ocal'}}
```

So:

1. Episode is correctly queued for `guardkit__test_inf5053`.
2. graphiti-core tries to extract entities/edges by calling the LLM at `https://api.openai.com/v1/responses`.
3. The placeholder API key (`not-needed-vllm-local`) gets a 401 from the real OpenAI endpoint.
4. After 2 retries, the queue worker logs `Failed to process episode None for group guardkit__test_inf5053` and drops it.
5. Subsequent `get_episodes(group_ids=["guardkit__test_inf5053"])` finds nothing.

This is exactly the symptom TASK-FIX-B1F7 observed in AC #5:

> "Verified empty during implementation (2026-05-02): `get_episodes(product_knowledge)` returned 0 episodes... Either the queued episodes never persisted (LLM extraction dropped them) or were already cleaned up."

The "or" in that sentence is now resolved: the queued episodes never persisted. The interpretation that they had been "misfiled to `product_knowledge`" was wrong. They were correctly routed to `guardkit__task_outcomes`, then dropped during extraction.

The cited TASK-FIX-B1F7 reproducer string `"queued for processing in group 'product_knowledge'"` is most likely a misread or misremembered response — the running code path (line 375 above) cannot produce that string when the caller passes `guardkit__task_outcomes`. There is no version skew that could explain it (image hasn't changed since before TASK-FIX-B1F7 was filed).

## Root cause of the *real* problem (not in scope for this task)

graphiti-core 0.28.1's `OpenAIClient.generate_response()` (line 99 of `openai_client.py`):

```python
response = await self.client.responses.parse(**request_kwargs)
```

It calls the new OpenAI Responses API (`/v1/responses`), not chat completions. Local OpenAI-compatible servers (vLLM, llama-swap, llama.cpp) typically don't implement that endpoint.

The MCP server's LLM factory at `/app/mcp/src/services/factories.py:109-141` (the `case 'openai':` branch) creates the graphiti-core `OpenAIClient` with `LLMConfig(api_key=..., model=..., small_model=..., temperature=..., max_tokens=...)` — **no `base_url`**. So the OpenAI client defaults to `api.openai.com` regardless of what's in `graphiti.providers.openai.api_url`. Compare the `groq` branch (line 238) which does pass `base_url=config.providers.groq.api_url`.

Result: with `provider: openai` in the config, calls always go to `api.openai.com`, and the configured `api_url: http://localhost:9000/v1` is dead config.

This is filed as a separate task (see "New task" section below).

## Decisions

### AC #1 — Locate deployment artefacts

- Container is `graphiti-mcp` on `promaxgb10-41b1`, image `graphiti-mcp-standalone:local`.
- Deployment artefacts ARE in this repo (the task description's claim that they're not is misleading): `scripts/graphiti-mcp-bootstrap.py`, `scripts/graphiti-mcp-config.yaml`, `scripts/graphiti-mcp.sh` (launcher).
- Bootstrap purpose: patches `mcp.server.transport_security.TransportSecurityMiddleware` to disable DNS rebinding protection so non-localhost `Host` headers (Tailscale hostname) are accepted.

### AC #2 — Identify the override mechanism

**No override mechanism exists.** Source code at line 375 explicitly honours client `group_id`. Probe response and server log confirm. **Task pivots to AC #2 option (c): document and close.**

### AC #3 — Apply server-side fix

**No fix applied.** No bug to fix. Documentation updated to reflect actual behaviour.

### AC #4 — Verify end-to-end

**Verified.** See "Probe results" above. Test group `guardkit__test_inf5053` was used. The probe episode failed background extraction (LLM endpoint problem, separate issue), so `get_episodes` returns nothing — which has nothing to do with `group_id` routing.

### AC #5 — Update documentation

**Done in this task.** See files-modified list below. The "Known transport limitation" prose is replaced with the corrected diagnosis.

### AC #6 — Decide fate of TASK-FIX-B1F7's CLI fallback

**Recommendation: keep as defence-in-depth (option a).**

Rationale:
- The fallback is small (single Python module + one Step in `task-complete.md` + 11-test suite).
- It does no harm when no override fires — `detect_group_override` returns "no override" and the MCP path runs through unchanged.
- It would defend against future regressions if a future server version introduces real coercion.
- Removing it would also remove the regression-test surface, leaving no automated guard at all.

The doc in `task-complete.md` Step 2a is being updated to reframe it from "addressing a known live bug" to "defence-in-depth against an alleged historical bug; not currently observed".

## Files modified

In this repo (in scope for `/task-work`):

- `.claude/rules/graphiti-knowledge-graph.md` — replaced "Known transport limitation" section with the corrected diagnosis pointing here for the audit trail.
- `docs/guides/graphiti-claude-code-integration.md` — same correction in the troubleshooting section.
- `installer/core/commands/task-complete.md` — softened the rationale around Step 2a's override-detection (kept as defence-in-depth, not addressing a known live bug).
- `tasks/in_progress/TASK-INF-5053-...md` (this task) — moved to `in_progress`, then to `in_review` after audit landed.
- `tasks/backlog/TASK-INF-5054-graphiti-llm-endpoint-misrouting.md` (NEW) — separate task for the real LLM endpoint problem (see below).
- `docs/state/TASK-INF-5053/audit.md` (this file).

Out of scope (the actual server-side LLM endpoint fix): tracked in TASK-INF-5054.

## Test cleanup

The probe episode `TASK-INF-5053 probe2` (group `guardkit__test_inf5053`) never persisted past the queue (extraction failed), so there's no node/edge to delete. The episode itself may live as a transient queue record in FalkorDB but cannot be retrieved via `get_episodes` since the extraction-failed path doesn't write the episode metadata to the graph. No cleanup action needed.

## Lessons (worth seeding to graphiti once the LLM endpoint is fixed and writes can persist)

1. **Verify the symptom against the source before designing the workaround.** TASK-FIX-B1F7 designed an override-detection + CLI-fallback mitigation around a snippet of response text. Reading the running server source (one `grep` away over SSH) would have shown the override couldn't happen via this code path, and the same investigation would have surfaced the real LLM-endpoint problem instead.
2. **Same shape as TASK-FIX-B1F7's own AC #5 lesson** — "verifying via `get_episodes` and `search_nodes` before assuming the live state matches the bug report saved an unnecessary destructive operation". Same lesson, applied one level deeper.
3. **`scripts/` is part of the deployment surface.** The task description's "no `infra/` in this repo" is technically true but misleading: the live server's bootstrap and config live in `scripts/` and are mounted into the container via `scripts/graphiti-mcp.sh`. Treat that triple as deployment artefacts.
4. **Image SHA + container start time are cheap evidence.** `docker inspect --format '{{.Image}}/{{.Created}}'` is a one-liner that immediately falsifies "the bug was real but has been fixed" hypotheses when the timestamps don't allow for a fix.
