---
id: TASK-INF-5054
title: "graphiti-mcp openai provider ignores api_url; falls through to api.openai.com and 401s"
status: backlog
created: 2026-05-02T17:05:00Z
updated: 2026-05-03T22:00:00Z
priority: high
task_type: feature
tags:
  - infra
  - graphiti
  - mcp
  - upstream
  - llm
  - knowledge-graph
complexity: 5
estimated_minutes: 120
parent_task: TASK-INF-5053
superseded_by: TASK-FORK-PATCH
remediation_decision: "option_b_openai_generic"
execution_location: "promaxgb10-41b1 (work directly on the GB10, not via SSH from a Mac dev machine)"
---

# Task: `graphiti-mcp` `openai` provider branch silently ignores `api_url`

## Superseded — see TASK-FORK-PATCH (2026-05-03)

**Status: superseded by [TASK-FORK-PATCH](../../../graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) in the appmilla graphiti fork.** The strategic call to fork `getzep/graphiti` (rather than maintain local-only patches with rebuild-time reminders) consolidates this task's implementation work alongside ~12 other graphiti-core / graphiti-mcp defects discovered during the 2026-05-03 audit. This task remains here as the audit trail for the original investigation; archive alongside TASK-FORK-PATCH per its AC-FORK-09 sweep.

### What the supersession means in practice

| AC in this task | Status under TASK-FORK-PATCH |
|---|---|
| AC #1 — pick remediation path | ✅ Done. Decision **option (b) `openai_generic`** is locked. TASK-FORK-PATCH Decision 6 refines this to **Approach A — auto-detect on `base_url`** (single `case 'openai':` arm that switches to `OpenAIGenericClient` when host is not `api.openai.com`), which matches the in-flight diff already drafted at `~/Projects/appmilla_github/graphiti-official/mcp_server/src/services/factories.py`. Approach A wins on zero-config-migration burden — no consumer YAML changes needed. |
| AC #2 — apply the remediation | ✅ Subsumed by **AC-FORK-03** (factory branch lands in the fork) and **AC-FORK-15** (Decision 6 capture). The "comment block in `graphiti-mcp-build.sh` reminding the next person to re-apply the patch" hack from this task's Implementation Notes disappears entirely — the patch IS the fork. |
| AC #3 — verify end-to-end | ✅ Subsumed by **AC-FORK-08** (full end-to-end verification block) and **AC-FORK-17** (specific `docker logs graphiti-mcp` log-line check confirming `OpenAIGenericClient` routing). |
| AC #4 — decide fate of TASK-FIX-B1F7's defence-in-depth fallback | ✅ **Decided: keep**. Per TASK-FORK-PATCH's "Defence-in-depth code (stays put)" section, `installer/core/commands/lib/graphiti_response_parser.py` remains as a zero-cost regression guard against any future graphiti-mcp regression that silently misroutes episodes. No further action required on this AC. |
| AC #5 — update documentation | ⏳ **Residual guardkit-side work**, not subsumed. After TASK-FORK-PATCH lands and AC-FORK-08 verifies end-to-end, the following docs need cleanup (touchpoints unchanged from the original AC #5 below): `docs/guides/graphiti-claude-code-integration.md` (remove the "Episode written but not retrievable" troubleshooting subsection); `docs/state/TASK-INF-5053/audit.md` (add a "follow-up resolved" note pointing at TASK-FORK-PATCH). Optionally also a short note in `scripts/graphiti-mcp-config.yaml` comments documenting the `openai` (now auto-routing) vs. explicit-provider distinction. **Sequencing**: do this after TASK-FORK-PATCH closes; can be done as part of the AC-FORK-09 archive sweep, or filed as a small follow-up task at that point if scope creeps. |
| AC #6 — backfill missed episodes | ⏳ **Optional residual**. Per the original AC, "likely not worth it for general writes, but task-outcome writes from `/task-complete` ARE recoverable" via `guardkit graphiti capture-outcome --from-task-file`. Re-evaluate after TASK-FORK-PATCH lands; defer or skip based on operator judgement. |

### Cross-references

- **TASK-FORK-PATCH** — `~/Projects/appmilla_github/graphiti/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md` (the consolidated fork-application task; carries the implementation work formerly described in this task's "Implementation Notes" section)
- **TASK-FORK-PATCH `patches/`** — `~/Projects/appmilla_github/graphiti/patches/` (pre-built diffs for bugs #5/#10/#11/#12/#13; the openai_generic factory fix lives in the in-flight diff at `~/Projects/appmilla_github/graphiti-official/`, separate from `patches/`)
- **TASK-INF-5053** (parent investigation) — `tasks/completed/2026-05/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`

The original task body is preserved verbatim below for the audit trail. The "Decision (2026-05-03)", "Patch shape (option b)", and "Suggested order of operations on the GB10" sections still describe the work accurately at a per-step level — TASK-FORK-PATCH just re-homes them into the fork-management workflow.

---

## Description

While investigating TASK-INF-5053 (the alleged group_id coercion bug,
which turned out not to exist) the *actual* reason episodes never
appear on subsequent searches was identified: background LLM
extraction is failing with 401 against `https://api.openai.com/v1/responses`
even though `scripts/graphiti-mcp-config.yaml` configures
`api_url: http://localhost:9000/v1` for a local llama-swap endpoint.

This means **every episode written via the MCP server is dropped** —
the queue worker logs `Failed to process episode None for group <X>`
and the episode never produces nodes/edges. The graph is effectively
read-only for the MCP path right now (writes succeed at the queue
layer, fail at the extraction layer).

The Python CLI path (`guardkit graphiti capture-outcome` →
`GraphitiClient`) is unaffected because it reads `llm_base_url` from
`.guardkit/graphiti.yaml` and constructs its own client with the
correct `base_url`.

## Background

### Where the misrouting happens

Two cooperating layers:

**1. graphiti-core 0.28.1 hardcodes the Responses API in `OpenAIClient`**

`/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/openai_client.py:99`:

```python
response = await self.client.responses.parse(**request_kwargs)
```

The new OpenAI Responses API at `/v1/responses` is not implemented by
most local OpenAI-compatible servers (vLLM, llama-swap, llama.cpp).
Calling `.responses.parse()` against such a server would 404. Because
the call instead reaches `api.openai.com` (see layer 2) and gets a
401 from the placeholder API key, the symptom is a 401 not a 404.

**2. The MCP server's LLM factory `openai` branch never passes `base_url`**

`/app/mcp/src/services/factories.py:109-141`:

```python
case 'openai':
    if not config.providers.openai:
        raise ValueError('OpenAI provider configuration not found')

    api_key = config.providers.openai.api_key
    _validate_api_key('OpenAI', api_key, logger)

    from graphiti_core.llm_client.config import LLMConfig as CoreLLMConfig

    small_model = config.model

    llm_config = CoreLLMConfig(
        api_key=api_key,
        model=config.model,
        small_model=small_model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    # NOTE: no `base_url=config.providers.openai.api_url` ← the bug
    ...
    return OpenAIClient(config=llm_config, ...)
```

`config.providers.openai.api_url` is read from the YAML and held on
the config object, but is **never passed to the `OpenAIClient`**.
Compare the `groq` branch at line 230-244 which does pass
`base_url=config.providers.groq.api_url`. The result: the OpenAI
client falls back to its default base URL (`api.openai.com`) and
sends the placeholder key, which 401s.

### Evidence (from TASK-INF-5053 probe, 2026-05-02 16:13Z)

```
2026-05-02 16:13:47 - services.queue_service - INFO -
  Processing episode None for group guardkit__test_inf5053
2026-05-02 16:13:48 - httpx - INFO -
  HTTP Request: POST https://api.openai.com/v1/responses "401 Unauthorized"
2026-05-02 16:13:48 - graphiti_core.llm_client.openai_base_client - ERROR -
  OpenAI Authentication Error: Error code: 401 -
  {'error': {'message': 'Incorrect API key provided: not-need*********ocal'}}
2026-05-02 16:13:48 - services.queue_service - ERROR -
  Failed to process episode None for group guardkit__test_inf5053
```

Group routing is correct (`guardkit__test_inf5053`); the LLM call goes
to `api.openai.com` instead of the configured `http://localhost:9000/v1`.

## Decision (2026-05-03): Option (b)

**Decision: option (b) — add `openai_generic` factory branch + switch
config to `provider: openai_generic`.**

**Operating constraint that drives the decision:** Graphiti's LLM
endpoint will *only ever* be local — either the MacBook Pro or the
GB10 running llama-swap / vLLM / llama.cpp / Ollama. Cloud OpenAI is
ruled out (cost + rate-limit ceilings). With "local-only" as a hard
constraint, the three options collapse:

| Option | What it does | Why it fails / works given local-only LLM |
|---|---|---|
| (a) Pass `base_url` on existing `openai` branch | Routes to llama-swap, but `OpenAIClient` still calls `.responses.parse()` | **Insufficient.** Local OpenAI-compatible servers don't implement `/v1/responses` — you'd trade a 401 at `api.openai.com` for a 404 at `localhost:9000`. Episodes still drop. |
| (b) Add `openai_generic` provider + use `OpenAIGenericClient` | Calls `chat.completions.create` instead of `.responses.parse()` | **Correct.** Every OpenAI-compatible local server implements `chat.completions.create`. This is the durable fix for a local-only deployment. |
| (c) Switch config to `provider: groq` | Re-uses the factory's groq branch which already forwards `base_url` | **Hack.** Semantically wrong (we're not using Groq), risks divergent default headers / timeout / retry behaviour, confusing for future readers. |

The Responses API is for OpenAI's hosted reasoning models. Local
OpenAI-compatible servers implement the Chat Completions API. Option
(b) maps "local OpenAI-compatible server" to the matching graphiti-core
client, which is what the architecture actually needs.

## Acceptance Criteria

- [x] **Remediation path chosen.** Option (b) — see Decision section
      above. Rationale: local-only LLM constraint makes (a) insufficient
      (Responses API not implemented locally) and (c) semantically
      wrong (we're not using Groq).

- [ ] **Apply the chosen remediation.** This means rebuilding the
      `graphiti-mcp-standalone:local` image (likely via
      `scripts/graphiti-mcp-build.sh`) with the patch, then
      `scripts/graphiti-mcp.sh` to restart the container.

- [ ] **Verify end-to-end.** Repeat the TASK-INF-5053 probe:
      ```
      mcp__graphiti__add_memory(
        name="TASK-INF-5054 verification",
        episode_body="...",
        group_id="guardkit__test_inf5054",
        source="text",
      )
      ```
      Wait ~10s for background processing, then:
      ```
      mcp__graphiti__get_episodes(group_ids=["guardkit__test_inf5054"])
      ```
      The episode should now be retrievable (extraction succeeded).
      Confirm via server logs that the LLM call went to
      `http://localhost:9000/v1/...` not `api.openai.com`.
      Clean up the test episode after.

- [ ] **Decide fate of TASK-FIX-B1F7's defence-in-depth fallback.**
      Once writes work end-to-end, the `/task-complete` Step 2a
      override-detection becomes pure defence-in-depth (it's already
      that today since the override doesn't fire — see TASK-INF-5053).
      Recommend leaving it in place; it's cheap and the parser tests
      are already there.

- [ ] **Update documentation.** Once writes are persisting:
      - `docs/guides/graphiti-claude-code-integration.md` — remove or
        update the "Episode written but not retrievable on search
        (LLM-extraction failure)" troubleshooting subsection (added
        by TASK-INF-5053).
      - `docs/state/TASK-INF-5053/audit.md` — add a "follow-up
        resolved" note pointing to this task's completion.
      - Consider a short note in the `scripts/graphiti-mcp-config.yaml`
        comments documenting the `openai` vs `openai_generic` distinction.

- [ ] **Backfill any episodes missed.** All MCP-path writes since the
      LLM endpoint regression started have been silently dropped. If
      any are recoverable from logs (the queue worker logs `Processing
      episode <name> for group <X>`), consider whether a manual
      re-capture is worthwhile. Likely not for general writes, but
      task-outcome writes from `/task-complete` ARE recoverable since
      the source data is the completed task file:
      ```bash
      for f in tasks/completed/2026-05/*.md; do
        guardkit graphiti capture-outcome --from-task-file "$f" --timeout 300
      done
      ```
      (CLI path bypasses the MCP server entirely.)

## Test Requirements

- [ ] Manual end-to-end probe per AC #3 — automated test surface for
      the live server doesn't exist (same as TASK-INF-5053).
- [ ] If a smoke-test script is added under `scripts/` that exercises
      a probe-then-retrieve cycle and asserts the episode is
      retrievable, document its expected exit codes and add it to
      `README.md`.

## Implementation Notes

### Execute on the GB10 directly

This task should be picked up **on `promaxgb10-41b1`**, not from a Mac
dev machine reaching across SSH. Reasons:

- `scripts/graphiti-mcp-build.sh` runs `docker build` against the local
  Docker daemon. Building on a Mac would produce an image that lives on
  Mac Docker, not on the GB10 where the container actually runs. We'd
  then need to push to a registry or `docker save | ssh ... docker load`
  — extra moving parts for no benefit.
- The build script clones `getzep/graphiti` into
  `$HOME/Projects/appmilla_github/graphiti` (read-only by design). The
  patch to `mcp_server/src/services/factories.py` lives in that clone.
  Doing it on the GB10 means the clone, the patched factory, the built
  image, and the running container are all on one host with one set of
  paths.
- The verification probe (`mcp__graphiti__add_memory` → wait → search)
  reaches `http://promaxgb10-41b1:8004/mcp`. Whoever runs verification
  also needs `docker logs graphiti-mcp` access to confirm the LLM call
  hit `localhost:9000` and not `api.openai.com`. Both are easiest from
  the GB10.

Suggested order of operations on the GB10:

1. `cd ~/Projects/appmilla_github/guardkit && git pull`
2. Edit `~/Projects/appmilla_github/graphiti/mcp_server/src/services/factories.py`
   — add the `openai_generic` case (see "Patch shape" below).
3. Edit `scripts/graphiti-mcp-config.yaml` — switch `provider:` to
   `openai_generic`.
4. Edit `scripts/graphiti-mcp-build.sh` — add a comment block noting
   that the upstream `factories.py` is patched locally and pointing at
   this task and the patch shape (so the next person who pulls upstream
   knows the patch needs reapplying).
5. `./scripts/graphiti-mcp-build.sh --no-cache` — rebuild image.
6. `./scripts/graphiti-mcp.sh` — restart container.
7. End-to-end probe per AC #3 (verification).
8. Docs cleanup (audit follow-up note, troubleshooting section, rule
   note) — only after verification passes.
9. Commit + push from the GB10.

### Where the patch lands (option b)

The upstream graphiti repo is cloned by `scripts/graphiti-mcp-build.sh`
to `$HOME/Projects/appmilla_github/graphiti` (read-only by design,
treated as a vendored dependency). The factory file we patch is at:

```
$HOME/Projects/appmilla_github/graphiti/mcp_server/src/services/factories.py
```

The corresponding in-image path (for reference when reading server
logs) is `/app/mcp/src/services/factories.py`. The build script's
Dockerfile context is `$GRAPHITI_REPO_DIR/mcp_server`, so any edits
to files under that subtree get baked in on the next `--no-cache`
build.

The patch shape (option b):

```python
# In factories.py, ADD a new case alongside `openai`, `groq`, etc.
case 'openai_generic':
    if not config.providers.openai_generic:
        raise ValueError('openai_generic provider configuration not found')

    api_key = config.providers.openai_generic.api_key
    _validate_api_key('OpenAIGeneric', api_key, logger)

    from graphiti_core.llm_client.config import LLMConfig as CoreLLMConfig
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

    small_model = config.model

    llm_config = CoreLLMConfig(
        api_key=api_key,
        base_url=config.providers.openai_generic.api_url,  # ← key line
        model=config.model,
        small_model=small_model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return OpenAIGenericClient(config=llm_config, ...)
```

The `openai_generic` provider also needs to be defined in the YAML
schema (matching the existing `openai` and `groq` provider shapes —
api_key + api_url). The exact location depends on graphiti-mcp's
config-model file (likely `mcp_server/src/config/...` or
`mcp_server/src/services/config.py`).

Then in `scripts/graphiti-mcp-config.yaml`:

```yaml
provider: openai_generic   # was: openai
providers:
  openai_generic:
    api_key: ${OPENAI_API_KEY:-not-needed-vllm-local}
    api_url: ${LLM_API_URL:-http://localhost:9000/v1}
```

Patch is **local-only** — not pushed upstream right now. Document it
in `scripts/graphiti-mcp-build.sh` (a comment block at the top
pointing at this task and the affected upstream file) so the next
person to pull upstream knows the patch needs reapplying. If we ever
do contribute upstream, version-pin the image build to the patched
commit at that point.

### Why this is high priority

Until this is fixed, **every episode written via the MCP server is
silently dropped**. The graph remains useful for reads (existing nodes
from earlier seedings) but cannot accept new writes via MCP. The CLI
path still works, so this isn't a total outage — but it makes
ad-hoc `mcp__graphiti__add_memory` calls effectively no-ops.

### Why this is medium-complexity

- Requires container rebuild + restart on remote host.
- May require upstream patch contribution (depending on the upstream
  project's responsiveness).
- Verification needs a live MCP probe (no automated test surface for
  the running server).

### Pattern relevance

Same shape as TASK-INF-5053 itself: a local design decision (use
local LLM endpoint via config) silently broken by an
externally-controlled component (MCP server's factory routing).
The detection-and-mitigate pattern from TASK-FIX-B1F7 doesn't apply
here — there's nothing in the MCP response message that indicates
extraction failed. The only signals are server logs (out of band)
and "episodes don't appear in search" (lagging signal).

See `.claude/rules/namespace-hygiene.md` for the broader meta-rule
about local design decisions touching externally-defined contracts.

## Files

In-repo touch points (committed from the GB10 after verification):

- `scripts/graphiti-mcp-config.yaml` — switch to
  `provider: openai_generic` and add a matching `providers.openai_generic`
  block (mirrors the existing `providers.openai` shape).
- `scripts/graphiti-mcp-build.sh` — comment block at the top noting
  the local-only patch to upstream `factories.py` (so the next person
  who pulls upstream knows to re-apply it).
- `docs/guides/graphiti-claude-code-integration.md` — remove
  "Episode written but not retrievable" troubleshooting subsection
  (or pin it to a specific server version range)
- `.claude/rules/graphiti-knowledge-graph.md` — possibly remove the
  TASK-INF-5053 status note once writes are working

Out-of-repo touch points:

- `factories.py` in the upstream graphiti-mcp source (the actual
  patch — either contributed upstream or applied as a local image
  build step)

## Notes

Filed 2026-05-02 as a follow-up to TASK-INF-5053. The investigation
audit at `docs/state/TASK-INF-5053/audit.md` has the full chain of
evidence: image SHA, source line numbers, probe response, server log
correlation.
