# Graphiti MCP — Two-Tag Fix Campaign for FalkorDB + Local LLM (2026-05-07)

**Date:** 2026-05-07
**Repos touched:** `appmilla_github/graphiti` (fork) + `appmilla_github/guardkit`
**Production target:** Dell DGX Spark `promaxgb10-41b1`, FalkorDB at `whitestocks`, llama-swap on `:9000`
**Outcome:** Both the `get_episodes` empty-results bug **and** TASK-INF-5054 LLM endpoint misrouting are resolved. MCP read and write paths verified end-to-end against the published artifacts.

---

## TL;DR

Two bugs blocked Graphiti on the FalkorDB + local-LLM deployment. They presented as one symptom (memory operations silently dropping data) and were entangled enough that fixing one without the other looked like a regression rather than a partial win.

| Tag | Layer | What it actually fixes |
|---|---|---|
| `v0.29.5-guardkit.5` | Read path | `get_episodes` now returns episodes from FalkorDB's per-group named graphs. Two coordinated layers: MCP-side routing (already in `.4`, commit `83abbec`) **plus** the Dockerfile vendoring fix (`.5`, commit `4ba8a4d`) that makes the fork's `graphiti_core/` patches actually reach the runtime image. |
| `v0.29.5-guardkit.6` | Write path | `add_memory` now completes extraction against local llama-swap. Factory passes `base_url` to `LLMConfig` and auto-picks `OpenAIGenericClient` (`chat.completions` + `json_schema`) for any non-`api.openai.com` endpoint, instead of always returning `OpenAIClient` (which routes structured output to the OpenAI-cloud-only Responses API at `/v1/responses`). |

End-to-end verified on the GB10 with the published tags and zero env-var overrides. See [Verification](#verification) for the empirical PASS evidence.

---

## What I came in to do

User asked me to:

1. Pick up the new `v0.29.5-guardkit.4` graphiti tag they had created to fix `get_episodes` returning `[]` from FalkorDB ([bug doc](../../../graphiti/docs/bugs/get-episodes-mcp-empty-results.md)).
2. Update the build script at [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) to pull that tag.
3. Work through [`docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`](../research/dgx-spark/RUNBOOK-v3-production-deployment.md) and add a verification step to confirm the fix.

That sequence held together for the first 30 minutes and then unravelled — both bugs surfaced and required rework.

---

## What I actually found

### Bug 1: get_episodes empty results (resolved in v0.29.5-guardkit.5)

The `v0.29.5-guardkit.4` MCP-side fix (route `get_episodes` through `Graphiti.retrieve_episodes` instead of calling `EpisodicNode.get_by_group_ids` directly) was correct — but did not resolve the symptom. After rebuilding the image at `v0.29.5-guardkit.4` and re-testing, single-group `get_episodes(["command_workflows"])` still returned `[]` against a FalkorDB graph that empirically contained 169 Episodic nodes.

Empirical comparison:

| Call | Result |
|---|---|
| `get_episodes(group_ids=["command_workflows"])` | **0** episodes (FalkorDB has 169) |
| `get_episodes(group_ids=["command_workflows", "patterns"])` | **6** episodes returned correctly |
| Single-group call after hot-patching `decorators.py` | **3** episodes returned correctly |

The asymmetry pointed at `graphiti_core/decorators.py` `@handle_multiple_group_ids`, which gates the per-group `driver.clone(database=gid)` path on `len(group_ids) > 1`. Single-group calls fell through, hit the shared default driver, queried the wrong FalkorDB graph, and returned `[]`.

**Twist:** that decorator fix already existed in the fork. Commit `7a914ec` ("fix(decorator): handle single-group FalkorDB calls (TASK-FORK-PATCH bug #8)") had removed the `> 1` gate as part of `v0.29.5-guardkit.3`, and `git show v0.29.5-guardkit.4:graphiti_core/decorators.py` confirmed the patched code was on the tag.

But `docker exec graphiti-mcp grep -n 'len(group_ids)' /app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/decorators.py` returned `len(group_ids) > 1` — the **upstream** broken version. The fork patch was on disk in `graphiti_core/` but **not** in the running venv.

The Dockerfile was the culprit:

```dockerfile
# mcp_server/docker/Dockerfile.standalone (pre-fix)
RUN sed -i '/\[tool\.uv\.sources\]/,/graphiti-core/d' pyproject.toml && \
    sed -i "s/graphiti-core\[falkordb\][>=]\+[0-9]\+\.[0-9]\+\.[0-9]\+/graphiti-core[neo4j,falkordb]==${GRAPHITI_CORE_VERSION}/" pyproject.toml && \
    rm -f uv.lock && uv lock
```

It deliberately stripped `[tool.uv.sources]` (which would have pointed `uv` at the local fork tree) and pinned graphiti-core to upstream PyPI 0.28.1. Every fork patch in `graphiti_core/` (#5/#8/#9/#10/#11/#12) was orphaned at runtime.

Why was the override missing in the first place? Upstream commit `e1e652e` (PR #1186, "Pin mcp_server to graphiti-core 0.26.3") removed it. The fork inherited that change without re-adding it.

**Fix (`v0.29.5-guardkit.5`, commit `4ba8a4d`):**

- `mcp_server/pyproject.toml` — re-add `[tool.uv.sources] graphiti-core = { path = "../", editable = true }`.
- `mcp_server/uv.lock` — regenerated; resolves to `editable = "../"` at version 0.29.0.
- `mcp_server/docker/Dockerfile.standalone` — rewritten layout. Build context becomes the fork root (was `mcp_server/`); image lays out `/app/{pyproject.toml,README.md,graphiti_core/}` one level above `/app/mcp/` so `path = "../"` resolves; `WORKDIR` stays `/app/mcp` because `scripts/graphiti-mcp.sh` bind-mounts to `/app/mcp/{config,bootstrap.py}`. The `sed` shim and `GRAPHITI_CORE_VERSION` ARG are gone.
- [`scripts/graphiti-mcp-build.sh`](../../scripts/graphiti-mcp-build.sh) — `BUILD_CONTEXT=$GRAPHITI_REPO_DIR` (was `$GRAPHITI_REPO_DIR/mcp_server`), `GRAPHITI_TAG` default → `v0.29.5-guardkit.5`.

### Bug 2: TASK-INF-5054 LLM endpoint misrouting (resolved in v0.29.5-guardkit.6)

After Bug 1's fix landed, `get_episodes` worked. But the original Phase 8.1 verification I had drafted (synthetic `add_memory` → poll `get_episodes`) still failed: the episode never appeared. Logs showed:

```
httpx - INFO - HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 401 Unauthorized"
graphiti_core.llm_client.openai_base_client - ERROR - OpenAI Authentication Error:
   Error code: 401 - {'error': {'message': 'Incorrect API key provided: not-need*********ocal. ...'}}
services.queue_service - ERROR - Failed to process episode None for group <X>: Error code: 401
```

The MCP server, configured to point at llama-swap on `localhost:9000`, was sending LLM extraction calls to `api.openai.com/v1/responses` with the placeholder API key. **TASK-INF-5054** was a known open issue but I'd assumed it was external blocker; investigation showed it was a 30-line factory bug.

`mcp_server/src/services/factories.py` `LLMClientFactory.create` `'openai'` case had two coordinated bugs:

1. **`base_url` was being silently dropped.** It built `LLMConfig` from `api_key`, `model`, `temperature`, `max_tokens` — but never read `config.providers.openai.api_url`. The OpenAI SDK fell back to its default of `https://api.openai.com/v1`. (The embedder factory in the same file always passed `base_url`; the LLM factory was the asymmetric one.)
2. **`OpenAIClient` is OpenAI-cloud-only.** Even with the right `base_url`, `OpenAIClient._create_structured_completion` calls `client.responses.parse` (the OpenAI Responses API at `/v1/responses`), which exists only on OpenAI cloud. llama.cpp / llama-swap / vLLM / ollama only implement `/v1/chat/completions`.

The `graphiti-core` library already shipped `OpenAIGenericClient` (in `graphiti_core/llm_client/openai_generic_client.py`) which uses `chat.completions.create` with `response_format = {'type': 'json_schema', 'json_schema': {...}}` — works against any modern OpenAI-compatible server. Verified empirically against llama-swap (`POST http://localhost:9000/v1/chat/completions` with json_schema response_format returned valid extracted JSON in one shot).

**Fix (`v0.29.5-guardkit.6`, commit `c8b5a65`):**

```python
# mcp_server/src/services/factories.py — 'openai' case
api_url = config.providers.openai.api_url
...
llm_config = CoreLLMConfig(
    api_key=api_key,
    base_url=api_url,        # was missing
    model=config.model,
    small_model=small_model,
    temperature=config.temperature,
    max_tokens=config.max_tokens,
)

is_openai_cloud = (
    not api_url
    or api_url.startswith('https://api.openai.com')
)

if not is_openai_cloud:
    logger.info(
        f'OpenAI-compatible endpoint detected (api_url={api_url}); '
        f'using OpenAIGenericClient (chat.completions + json_schema). '
        f'OpenAIClient (Responses API) is reserved for openai.com.'
    )
    return OpenAIGenericClient(config=llm_config)

# OpenAI cloud path: keep OpenAIClient + Responses API + reasoning wiring
...
```

The OpenAI cloud path is unchanged — `gpt-5` / `o1` / `o3` reasoning model parameters (`reasoning='minimal'`, `verbosity='low'`) are still honoured for actual cloud users.

---

## Changes summary

### graphiti fork (pushed)

| Commit | Tag | Files | Effect |
|---|---|---|---|
| `4ba8a4d` | `v0.29.5-guardkit.5` | `mcp_server/pyproject.toml`, `mcp_server/uv.lock`, `mcp_server/docker/Dockerfile.standalone` | Vendor graphiti-core from local source so fork patches reach runtime |
| `c8b5a65` | `v0.29.5-guardkit.6` | `mcp_server/src/services/factories.py` | Pass `base_url` + auto-pick `OpenAIGenericClient` for non-cloud endpoints |

Both pushed to `main` on `github.com/guardkit/graphiti`.

### guardkit (pushed)

| Commit | Files | Effect |
|---|---|---|
| `705b7000` | `scripts/graphiti-mcp-build.sh`, `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` | Build context → fork root, default tag → `guardkit.5`, runbook Phase 8.1 rewritten read-only |
| `599c0e1e` | `scripts/graphiti-mcp-build.sh`, `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` | Default tag → `guardkit.6`, runbook Phase 8.1b added (round-trip smoke test) |

Both pushed to `main` on `github.com/guardkit/guardkit`.

### Documentation (this commit)

- `graphiti/docs/bugs/get-episodes-mcp-empty-results.md` — marked RESOLVED with the actual root cause (Dockerfile vendoring orphaned the patches).
- `graphiti/docs/bugs/llm-endpoint-misrouting-task-inf-5054.md` (new) — full bug doc for TASK-INF-5054.
- `guardkit/docs/fixes/2026-05-07-graphiti-mcp-falkordb-end-to-end.md` (this file) — operator-facing retrospective.

---

## Verification

End-to-end on `promaxgb10-41b1` (2026-05-07) with the **published** tags and zero env-var overrides:

```
$ git -C ~/Projects/appmilla_github/graphiti describe --tags --exact-match HEAD
v0.29.5-guardkit.6

$ ./scripts/graphiti-mcp-build.sh
... Built: graphiti-mcp-standalone:local

$ ./scripts/graphiti-mcp.sh
... Container started: graphiti-mcp

$ docker logs graphiti-mcp 2>&1 | grep "OpenAI-compatible endpoint"
INFO - OpenAI-compatible endpoint detected (api_url=http://localhost:9000/v1);
       using OpenAIGenericClient (chat.completions + json_schema).
       OpenAIClient (Responses API) is reserved for openai.com.

# Phase 8.1 (read-only)
=== single-group MCP get_episodes ===
  [PASS ] command_workflows           -> 3 episode(s)
  [PASS ] patterns                    -> 3 episode(s)
  [PASS ] guardkit__project_decisions -> 3 episode(s)
  [PASS ] guardkit__task_outcomes     -> 3 episode(s)
=== multi-group regression ===
  PASS : 8 episode(s)
exit: 0

# Phase 8.1b (round-trip)
add_memory: queued for processing in group runbook_v3_addmem_smoke_<ts>
PASS: add_memory → get_episodes round-trip works.
      Episode persisted in 45s (uuid=e54f1cef, name='TASK-INF-5054 round-trip smoke').
      v0.29.5-guardkit.6 (TASK-INF-5054) is in effect.
exit: 0

# Sanity: no api.openai.com calls
$ docker logs graphiti-mcp --since 5m 2>&1 | grep -E "POST.*chat/completions|api.openai.com"
... POST http://localhost:9000/v1/chat/completions "HTTP/1.1 200 OK"
... POST http://localhost:9000/v1/chat/completions "HTTP/1.1 200 OK"
# (no api.openai.com lines — clean)
```

---

## Operational notes for the next operator

- **To redeploy from a clean state on the GB10 (or another machine):**

  ```bash
  cd ~/Projects/appmilla_github/guardkit
  ./scripts/graphiti-mcp-build.sh        # pulls v0.29.5-guardkit.6
  docker stop graphiti-mcp; docker rm graphiti-mcp
  ./scripts/graphiti-mcp.sh
  ```

  Then run runbook Phase 7.2 (rebuild assertion) → 8.1 (read) → 8.1b (round-trip) to confirm.

- **If `get_episodes` returns `[]` after a rebuild:** check the running image actually contains the editable graphiti-core install:

  ```bash
  docker run --rm --entrypoint sh graphiti-mcp-standalone:local \
      -c 'test -f /app/graphiti_core/decorators.py && echo OK || echo MISSING'
  ```

  If `MISSING`, the build context is wrong — confirm `BUILD_CONTEXT` in `scripts/graphiti-mcp-build.sh` points at the fork root (not `mcp_server/`).

- **If `add_memory` writes never persist:** check the factory startup log:

  ```bash
  docker logs graphiti-mcp 2>&1 | grep -E "OpenAI-compatible endpoint|using OpenAIClient"
  ```

  The expected line for local llama-swap is `OpenAI-compatible endpoint detected ... using OpenAIGenericClient`. If you see `using OpenAIClient` instead (or no log line at all), the factory selected the wrong client class — check the image is at `v0.29.5-guardkit.6` or later.

- **Rollback:** the previous image SHA was `1d5649b1a986` (built from `v0.29.5-guardkit.5`). To roll back to that:

  ```bash
  GRAPHITI_TAG=v0.29.5-guardkit.5 ./scripts/graphiti-mcp-build.sh
  docker stop graphiti-mcp; docker rm graphiti-mcp
  ./scripts/graphiti-mcp.sh
  ```

  The read path will still work; the write path will revert to broken (TASK-INF-5054 active again).

---

## Lessons

1. **Source-level audit is not runtime audit.** `git show v0.29.5-guardkit.4:graphiti_core/decorators.py` showed the bug-fixed code, but `docker exec graphiti-mcp grep ...` against the running venv showed the upstream broken version. For vendored deps in any future fork, verify the runtime install matches the source intent before declaring the patch landed.

2. **Two oracles, two fixes.** The original `get_episodes` bug doc proposed the right MCP-side fix and that landed in `.4`. But verification via `add_memory` → `get_episodes` was confounded by TASK-INF-5054 (write path broken for unrelated reasons), so the read-path fix looked like it had failed when it actually hadn't. The eventual runbook Phase 8.1 is read-only against pre-populated groups specifically to isolate the read-path verification from any write-path defects.

3. **Symmetric APIs deserve symmetric construction.** The embedder factory always passed `base_url` to its config; the LLM factory never did. This wasn't a recent regression — it had been wrong since the factory was introduced. The kind of bug that's invisible until paired with a non-default endpoint **and** a code path that exercises an endpoint-specific feature (the OpenAI Responses API). Worth a sanity sweep of any other `*Factory.create` methods in the same file for similar omissions.

4. **The fork is a fork *because* of `graphiti_core/`.** Future Dockerfile changes in `appmilla_github/graphiti` must never strip `[tool.uv.sources]`. Add a CI smoke test or a pre-commit hook if practical.

---

## References

- Graphiti fork bug docs:
  - `graphiti/docs/bugs/get-episodes-mcp-empty-results.md` (RESOLVED, this fix)
  - `graphiti/docs/bugs/llm-endpoint-misrouting-task-inf-5054.md` (RESOLVED, this fix)
- Graphiti tag annotations: `git -C ~/Projects/appmilla_github/graphiti show v0.29.5-guardkit.5` and `v0.29.5-guardkit.6`
- GuardKit runbook: `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` Phase 7.2 / 8.1 / 8.1b
- GuardKit memory: `~/.claude/projects/-home-richardwoollcott-Projects-appmilla-github-guardkit/memory/graphiti_mcp_get_episodes_single_group.md`
