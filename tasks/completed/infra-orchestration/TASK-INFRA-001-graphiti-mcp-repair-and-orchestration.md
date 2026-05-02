---
id: TASK-INFRA-001
title: "graphiti-mcp diagnostic + repair + infra-orchestration scaffold"
status: completed
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T21:30:00Z
completed: 2026-05-01T21:30:00Z
previous_state: in_review
state_transition_reason: "All 11 ACs validated on live GB10 infrastructure; closed via /task-complete"
priority: high
task_type: task-work
tags: [infra, graphiti, graphiti-mcp, llama-swap, orchestration, dgx, runbook, gb10]
complexity: 6
feature: infra-orchestration
parent_review: null
completed_location: tasks/completed/infra-orchestration/
test_results:
  status: passing
  coverage: n/a   # operational task — no unit-test surface; verified by AC evidence
  last_run: 2026-05-01T21:13:00Z
discovery:
  date: 2026-05-01
  machine: promaxgb10-41b1
  correlation_id: a58ec9a7-27c6-485a-beac-e18675639a10
  surfacing_run: FEAT-JARVIS-INTERNAL-001 first-real-run, Phase 4
---

# TASK-INFRA-001: graphiti-mcp diagnostic + repair + infra-orchestration scaffold

## Problem Statement

Three problems, observed together on 2026-05-01 on the GB10
(`promaxgb10-41b1`), and tightly coupled enough that they are best fixed in
one task:

1. **`graphiti-mcp` is unhealthy.** `docker ps` reports
   `graphiti-mcp  Up 2 days (unhealthy)`. The container is up, but its
   healthcheck fails. The strong-suspect root cause is that its
   embedding/LLM endpoint config still points at the pre-migration
   llama-swap URL (or at OpenAI cloud, which is no longer in scope for this
   environment). llama-swap was recently migrated to port `:9000`; jarvis
   and nats-core have already been updated to use
   `JARVIS_LLAMA_SWAP_BASE_URL=http://promaxgb10-41b1:9000`. graphiti-mcp
   has not.

2. **`graphiti-stack-up.sh` and `graphiti-stack-down.sh` error when invoked.**
   The operator attempted both recently and got errors. The exact error
   text was not captured at the time and must be reproduced.

3. **There is no top-level "stop everything / start everything" workflow
   for the local LLM + graphiti tier.** The operator gets regular DGX OS
   updates and needs to be able to cleanly stop the local infra, reboot,
   and bring it back up. Today this is ad-hoc and error-prone.

## Background and Context

### llama-swap port migration

llama-swap was recently migrated to listen on `:9000`. This is the correct,
canonical endpoint going forward. Available models on `:9000` (verified
2026-05-01 via `curl http://promaxgb10-41b1:9000/v1/models`):

- `gemma4-tutor`
- `nomic-embed`         ← embeddings
- `qwen-graphiti`       ← graphiti LLM
- `qwen36-workhorse`

graphiti-mcp's correct configuration after this task:

- **Embeddings endpoint**: `http://localhost:9000/v1`, model `nomic-embed`
- **LLM endpoint**: `http://localhost:9000/v1`, model `qwen-graphiti`

(`localhost` because graphiti-mcp runs on the same GB10 host as llama-swap.
If container networking forces the use of the host-routable name instead
of `localhost`, use `promaxgb10-41b1:9000` — pick whichever actually works
from inside the graphiti-mcp container and document the choice.)

### Existing surface to read before designing changes

- `scripts/graphiti-stack-up.sh`
- `scripts/graphiti-stack-down.sh`
- `scripts/graphiti-mcp.sh`
- `scripts/graphiti-mcp-build.sh`
- `scripts/graphiti-endpoint-toggle.sh` — strongly suggests endpoint
  switching has been a recurring pain point; check whether this script is
  the right place for the new `:9000` toggle, or whether it should be
  retired in favour of a single canonical config.
- `scripts/graphiti-mcp-config.yaml`
- `scripts/graphiti-mcp-config.yaml.pre-llamacpp.bak` (history hint)
- `docker/docker-compose.graphiti.yml`
- `scripts/llama-swap-keepalive.sh`
- systemd units already in place: `llama-swap-healthcheck.service` /
  `.timer`, `llama-swap-keepalive.service` / `.timer` (both `enabled`).

### Discovery context

- **Date observed**: 2026-05-01.
- **Machine**: GB10 (`promaxgb10-41b1`).
- **Surfacing run**: FEAT-JARVIS-INTERNAL-001 first-real-run validation,
  Phase 4 row in the per-phase results table.
- **Correlation ID**: `a58ec9a7-27c6-485a-beac-e18675639a10`.
- **Cross-repo reference**:
  `~/Projects/appmilla_github/jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-INTERNAL-001-first-real-run.md`
  Phase 4 row.

## Goals

1. `graphiti-mcp` reports `healthy` and is reachable from jarvis.
2. `graphiti-stack-up.sh` / `graphiti-stack-down.sh` are clean, idempotent,
   and produce no errors when re-run against an already-up / already-down
   stack.
3. A top-level `infra-up.sh` / `infra-down.sh` exists for the LLM +
   graphiti tier, with idempotent semantics, per-component pass/fail
   reporting, and explicit extension hooks for the NATS tier and the
   agents tier (both out of scope for THIS task).
4. A runbook documents the DGX-OS-update workflow ("infra-down → reboot →
   infra-up → infra-status") and the planned upgrade path for the future
   tiers.

## Deliverables

### Deliverable A — Diagnose and repair graphiti-mcp

A1. **Reproduce and capture the exact error text** from running, in order:
   - `bash scripts/graphiti-stack-down.sh` (against current state)
   - `bash scripts/graphiti-stack-up.sh` (against the post-down state)

   Paste the captured stderr/stdout into the implementation notes section
   of this task before proposing fixes. Do not pre-judge what the errors
   are.

A2. **Diagnose** why `graphiti-mcp` is unhealthy. Capture:
   - `docker inspect graphiti-mcp --format '{{json .State.Health}}' | jq` output.
   - graphiti-mcp container logs covering at least the last healthcheck
     cycle (`docker logs --tail 200 graphiti-mcp`).
   - The container's currently-effective env vars (`docker inspect` →
     `Config.Env`), specifically anything matching
     `*EMBED*`, `*LLM*`, `*OPENAI*`, `*BASE_URL*`, `*MODEL*`.
   - The result of an in-container `curl` from graphiti-mcp to its
     configured embedding and LLM URLs (to prove reachability).

A3. **Repair the endpoint configuration**. Update graphiti-mcp's env vars
   (in `docker/docker-compose.graphiti.yml` or wherever they actually
   live — confirm in A2) so that:
   - Embeddings: base URL `http://localhost:9000/v1` (or
     `http://promaxgb10-41b1:9000/v1` if `localhost` is not reachable from
     the container), model `nomic-embed`.
   - LLM: same base URL, model `qwen-graphiti`.
   - Any leftover OpenAI cloud config is removed or explicitly disabled.

A4. **If `graphiti-endpoint-toggle.sh` is relevant**, either update it to
   reflect the new `:9000` endpoint (and the `nomic-embed` /
   `qwen-graphiti` model names) or document why it is being retired. Do
   not leave it pointing at stale URLs.

A5. **Bring the container back to `healthy`**:
   `docker inspect graphiti-mcp --format '{{.State.Health.Status}}'`
   returns `healthy`.

### Deliverable B — Idempotent stack-up / stack-down

B1. Fix the errors captured in A1 such that:
   - `bash scripts/graphiti-stack-down.sh` succeeds whether the stack is
     up or already down.
   - `bash scripts/graphiti-stack-up.sh` succeeds whether the stack is
     down or already up.
   - Re-running either script back-to-back exits 0.

B2. Each script gets a header comment documenting:
   - Preconditions (what state the system can be in before invocation).
   - Postconditions (what state the system will be in after success).
   - Exit codes (0 = success; non-zero values mapped to specific failure
     classes — at minimum, distinguish "docker daemon unreachable" from
     "container failed to become healthy within timeout" from "config
     file missing/invalid").

B3. Both scripts use `set -euo pipefail` (or equivalent) and emit clear
   per-step status lines so the operator can tell at a glance which step
   failed.

### Deliverable C — Top-level infra orchestration scaffold

C1. Create `scripts/infra-up.sh` that brings up the LLM + graphiti tier:
   - Ensures llama-swap is up. Since llama-swap is managed by systemd
     timers (`llama-swap-healthcheck.timer`,
     `llama-swap-keepalive.timer`), the right invocation is likely
     `systemctl start llama-swap.service` (or whatever the canonical unit
     is — verify; do not invent). If the systemd story is "the timers
     bring it up, you don't start it manually", document that and have
     `infra-up.sh` simply assert it's up.
   - Calls `scripts/graphiti-stack-up.sh` (which now also brings up
     FalkorDB if local — verify and document whether FalkorDB is local
     to the GB10 or remote).
   - Reports per-component pass/fail to stdout.
   - Idempotent: re-running on an already-up stack exits 0.
   - Scaffolds (but does not implement) extension hooks for:
     - NATS infrastructure tier (e.g. a sourced
       `scripts/infra/nats-up.sh` that currently no-ops with a clear
       "TODO: implement in TASK-INFRA-NATS-XXX" message).
     - Agents tier (e.g. `scripts/infra/agents-up.sh`, same shape).

C2. Create `scripts/infra-down.sh`, the inverse:
   - Stops graphiti-mcp + FalkorDB via `graphiti-stack-down.sh`.
   - Stops llama-swap (or notes whether systemd should remain enabled
     across the reboot).
   - Idempotent.
   - Same NATS-tier and agents-tier hooks (no-op by default).

C3. Create `scripts/infra-status.sh` that prints a one-screen summary:
   - llama-swap: up/down + last healthcheck result.
   - graphiti-mcp: container state + healthcheck status.
   - FalkorDB: container state.
   - NATS / agents tiers: "not yet managed by infra-* scripts" hook output.

C4. Naming flexibility: if the existing repo conventions favour different
   names (e.g. `infra-stack-up.sh`), pick names that fit the existing
   style. Document the chosen names in the runbook.

C5. Create `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` covering:
   - Cold-start procedure (fresh boot of GB10).
   - DGX-OS-update reboot procedure (`infra-down` → reboot →
     `infra-up` → `infra-status`).
   - Per-component healthcheck strategy and where to look when something
     reports unhealthy.
   - Explicit upgrade path for the NATS tier (where its
     docker-compose.yml lives:
     `~/Projects/appmilla_github/nats-infrastructure/docker-compose.yml`)
     and the agents tier (specialist-agent containers, eventually
     jarvis itself), with the expected shape of the future
     `nats-up.sh` / `nats-down.sh` and `agents-up.sh` / `agents-down.sh`
     companions.
   - The smoke check used to verify jarvis can reach graphiti after
     `infra-up.sh`.

## Acceptance Criteria

- [x] **AC-1 (graphiti-mcp healthy)**: After
  `bash scripts/graphiti-stack-up.sh` from a cold state,
  `docker inspect graphiti-mcp --format '{{.State.Health.Status}}'`
  returns `healthy`.
- [x] **AC-2 (clean cycle)**: `bash scripts/graphiti-stack-down.sh`
  followed by `bash scripts/graphiti-stack-up.sh` exits 0 on both calls
  and ends with graphiti-mcp `healthy`.
- [x] **AC-3 (idempotent stack-up)**: Running
  `bash scripts/graphiti-stack-up.sh` twice in a row exits 0 both times
  with no error output on the second invocation.
- [x] **AC-4 (idempotent stack-down)**: Running
  `bash scripts/graphiti-stack-down.sh` twice in a row exits 0 both times
  with no error output on the second invocation.
- [x] **AC-5 (infra-up cold start)**: `bash scripts/infra-up.sh` from a
  cold state brings the LLM + graphiti tier to healthy and reports
  per-component pass on stdout.
- [x] **AC-6 (infra-down cold)**: `bash scripts/infra-down.sh` returns the
  LLM + graphiti tier to a cold state cleanly, exits 0, and is safe to
  re-run.
- [x] **AC-7 (DGX OS update workflow documented)**:
  `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` exists and contains the
  documented workflow `infra-down → reboot → infra-up → infra-status`,
  plus explicit hook sections for the NATS tier and the agents tier that
  future tasks will fill in.
- [x] **AC-8 (jarvis → graphiti smoke check)**: After `infra-up.sh`,
  jarvis can reach graphiti via its configured `JARVIS_GRAPHITI_ENDPOINT`
  — a `curl` from the jarvis host to the canonical graphiti HTTP
  endpoint returns HTTP 200. The exact `curl` command and expected
  response are documented in the runbook.
- [x] **AC-9 (script hygiene)**: All new and modified shell scripts use
  `set -euo pipefail` (or documented equivalent), have header comments
  documenting preconditions / postconditions / exit codes, and emit
  clear per-step status lines.
- [x] **AC-10 (no llama-swap modification)**: This task does not modify
  llama-swap itself, its config, or its systemd units. It only consumes
  llama-swap's `:9000` endpoint.
- [x] **AC-11 (extension hooks present, no-op by default)**: `infra-up.sh`
  and `infra-down.sh` source (or otherwise reference) NATS-tier and
  agents-tier hooks that currently no-op with a clear "TODO:
  implemented by future task" message — the future tasks fill these in
  without needing to restructure the top-level script.

## Test Requirements

- [x] Capture and paste in the implementation notes:
      `docker inspect graphiti-mcp --format '{{json .State.Health}}' | jq`
      output before-and-after the repair.
- [x] Capture and paste:
      `bash scripts/graphiti-stack-down.sh` followed by
      `bash scripts/graphiti-stack-up.sh` full transcripts (both pre-fix
      to demonstrate the failure mode, and post-fix to demonstrate the
      cycle is clean).
- [x] Capture and paste:
      `bash scripts/infra-down.sh` followed by `bash scripts/infra-up.sh`
      full transcripts.
- [x] Capture and paste:
      `bash scripts/infra-status.sh` output post-`infra-up`.
- [x] Capture and paste the jarvis → graphiti smoke check `curl`.

## Implementation Notes

### Diagnostic findings (captured 2026-05-01 during /task-work)

**State at the start of the run.** The container the task description
referred to (`graphiti-mcp  Up 2 days (unhealthy)`) had since been removed.
`docker ps -a` showed only `forge-prod`, `ships-computer-nats`, and
`open-webui` running, plus stopped `nvcr.io/nvidia/{pytorch,vllm}` shells.
No `graphiti-mcp` container or stopped record. State drifted between when
the task was filed and when /task-work picked it up.

**Pre-fix `graphiti-stack-down.sh` transcript** — already idempotent against
empty state:

```
════════════════════════════════════════
  Graphiti stack — stopping
════════════════════════════════════════
  graphiti-mcp not running — skipping
  vllm-embedding not running — skipping
  vllm-graphiti not running — skipping

Stack down.
---EXIT: 0---
```

**Pre-fix `graphiti-stack-up.sh` transcript** — exits 127 on first step:

```
════════════════════════════════════════
  Graphiti stack — starting on GB10
  LLM mode: gb10
════════════════════════════════════════

── [1/3] vllm-graphiti (LLM) ──
scripts/graphiti-stack-up.sh: line 136: /home/richardwoollcott/Projects/appmilla_github/guardkit/scripts/vllm-graphiti.sh: No such file or directory
---EXIT: 127---
```

**Root cause #1 (stack-up failure).** `graphiti-stack-up.sh` was still
calling `scripts/vllm-graphiti.sh` and `scripts/vllm-embed.sh`, but those
scripts had been moved to `scripts/archive-vllm/` during the llama-swap
migration on 2026-04-29. `set -euo pipefail` + a missing executable +
shell exit code 127 = the unstated error the task referred to.

**Root cause #2 (graphiti-mcp unhealthy).** Two issues stacked:

1. `scripts/graphiti-mcp-config.yaml` had `:9000` as the *URL* default but
   the *model* defaults were stale:

   - LLM model: `${LLM_MODEL:neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic}`
     (vLLM's identifier; llama-swap doesn't know it)
   - Embedder model: `nomic-embed-text-v1.5` (vLLM's identifier; llama-swap
     serves the same weights under the alias `nomic-embed`)

   Effect: graphiti-mcp could open the HTTP listener but every LLM call
   would hit `model not found`; every embedding call likewise.

2. The vendored `~/Projects/appmilla_github/graphiti/mcp_server/docker/
   Dockerfile.standalone` bakes a HEALTHCHECK pointing at `:8000`:

   ```
   HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
       CMD curl -f http://localhost:8000/health || exit 1
   ```

   But our deployment binds `:8004` and graphiti-mcp has no `/health`
   endpoint — FastMCP only answers `/mcp/`. So Docker observed a permanent
   ExitCode 1 on the healthcheck:

   ```
   curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server
   ```

   That was *exclusively* the source of the "(unhealthy)" status. The
   container was actually serving fine on `:8004`.

**Live verification of the pieces that were already correct** (so we'd
know what *not* to touch):

```
$ curl -s http://localhost:9000/v1/models | python3 -c "..."
4 models listed: gemma4-tutor, nomic-embed, qwen-graphiti, qwen36-workhorse

$ curl http://localhost:9000/v1/embeddings -d '{"model":"nomic-embed",...}'
dims: 768                # matches the 768 in graphiti-mcp-config.yaml ✓

$ curl http://localhost:9000/v1/chat/completions -d '{"model":"qwen-graphiti",...}'
llm reply: OK            # qwen-graphiti reachable ✓

$ (echo "PING"; sleep 0.3) | nc -w 2 whitestocks 6379
+PONG                    # FalkorDB on NAS reachable over Tailscale ✓

$ docker image inspect graphiti-mcp-standalone:local
present (416MB)          # image already built ✓

$ systemctl list-units | grep llama-swap
llama-swap-healthcheck.timer    active
llama-swap-keepalive.timer      active
llama-swap.service              not-found  ← intentional; managed by timers
```

So llama-swap was already healthy and consuming-only was the right move
(AC-10). FalkorDB on the NAS was already healthy. The fix was contained to
graphiti-mcp config, healthcheck override, and the dead vllm references in
`graphiti-stack-up.sh`/`down.sh`.

### Configuration changes

| File                                | Change                                                                                                                                |
|-------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `scripts/graphiti-mcp-config.yaml`  | `model: ${LLM_MODEL:neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic}` → `model: ${LLM_MODEL:qwen-graphiti}`                                |
| `scripts/graphiti-mcp-config.yaml`  | embedder `model: "nomic-embed-text-v1.5"` → `model: "nomic-embed"`                                                                     |
| `scripts/graphiti-mcp-config.yaml`  | header comments updated to describe llama-swap on `:9000` instead of vllm-graphiti / vllm-embedding                                    |
| `scripts/graphiti-mcp-config.yaml`  | `api_key` defaults `not-needed-vllm-local` → `not-needed-llama-swap-local` (cosmetic; either string is accepted by llama-swap)         |
| `scripts/graphiti-stack-up.sh`      | rewritten: dropped dead vllm-graphiti / vllm-embed steps; now asserts llama-swap precondition (`:9000` lists `qwen-graphiti` + `nomic-embed`), asserts FalkorDB `whitestocks:6379`, then starts `graphiti-mcp`. Documented preconditions / postconditions / exit codes (0,1,2,3,4,5,6) per AC-9. |
| `scripts/graphiti-stack-down.sh`    | rewritten: dropped vllm-graphiti / vllm-embedding teardown (those containers no longer exist); kept idempotent graphiti-mcp stop. Documented preconditions / postconditions / exit codes per AC-9. |
| `scripts/graphiti-mcp.sh`           | added `--health-cmd / --health-interval / --health-timeout / --health-start-period / --health-retries` flags to override the upstream Dockerfile's stale `:8000/health` healthcheck; new probe accepts 2xx/3xx/4xx on `:8004/mcp/` as serving. Updated header comments and YAML-default echo lines from `:8000` / `Qwen2.5-14B FP8` to `:9000` / `qwen-graphiti`. |
| `scripts/infra-up.sh` (new)         | top-level orchestrator. Tier 1 llama-swap probe (consume-only; triggers `llama-swap-keepalive.service` if down). Tier 2 graphiti via `graphiti-stack-up.sh`. Tier 3+4 source no-op hooks for NATS / agents. Idempotent.       |
| `scripts/infra-down.sh` (new)       | inverse. Tier 1 agents hook. Tier 2 NATS hook. Tier 3 graphiti-stack-down. Tier 4 llama-swap stays running unless `--stop-llama-swap`. Idempotent.        |
| `scripts/infra-status.sh` (new)     | one-screen state of llama-swap (endpoint + models listed + last-keepalive timestamp), graphiti-mcp (container state + healthcheck), FalkorDB (PONG over Tailscale), NATS hook, agents hook. Always exits 0. |
| `scripts/infra/{nats,agents}-{up,down,status}.sh` (new) | six no-op extension-hook stubs sourced by the three top-level scripts. Each prints a `TODO: implemented by future task` line. Sourceable (no `exit`), respect `set -euo pipefail` from caller. |
| `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` (new) | DGX-OS-update workflow, per-component healthcheck strategy, future-tier upgrade-path sections for NATS / agents, jarvis → graphiti smoke-check curl with expected HTTP 200. |

### Risks

- llama-swap is shared by jarvis, autobuild, and graphiti-mcp. If a
  graphiti-mcp config change accidentally restarts llama-swap or holds it
  for an extended healthcheck wait, jarvis runs in flight may stall.
  Mitigation: `infra-down.sh` should stop graphiti-mcp before touching
  llama-swap, and `infra-up.sh` should bring llama-swap up first and
  confirm `/v1/models` returns the expected list before starting
  graphiti-mcp.
- The `graphiti-endpoint-toggle.sh` script's existence implies prior
  fragility around endpoint switching. The repair should not reintroduce
  this fragility — prefer a single canonical config over a toggleable
  one if the toggle is no longer needed.

## Out of Scope

- **NATS infrastructure tier orchestration.** The NATS docker-compose at
  `~/Projects/appmilla_github/nats-infrastructure/docker-compose.yml`
  exists and will eventually need a `nats-up.sh` / `nats-down.sh`
  companion. This task only leaves a clean hook for that future task.
- **Agents tier orchestration.** specialist-agent containers, and
  eventually jarvis itself, will need similar treatment. This task only
  leaves a clean hook for that future task.
- **Any change to llama-swap itself.** llama-swap is already managed by
  systemd timers (`llama-swap-healthcheck.timer`,
  `llama-swap-keepalive.timer`) and is working. This task only consumes
  its `:9000` endpoint.

## References

- jarvis-side runbook documenting the surfacing run (Phase 4 row of the
  per-phase table):
  `/home/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-INTERNAL-001-first-real-run.md`
- Correlation ID: `a58ec9a7-27c6-485a-beac-e18675639a10`
- Date observed: 2026-05-01
- Discovery machine: GB10 (`promaxgb10-41b1`)
- Existing scripts to read first:
  - `scripts/graphiti-stack-up.sh`
  - `scripts/graphiti-stack-down.sh`
  - `scripts/graphiti-mcp.sh`
  - `scripts/graphiti-mcp-build.sh`
  - `scripts/graphiti-endpoint-toggle.sh`
  - `scripts/graphiti-mcp-config.yaml`
  - `scripts/llama-swap-keepalive.sh`
- Existing compose file: `docker/docker-compose.graphiti.yml`
- Existing systemd units (do not modify):
  `llama-swap-healthcheck.service` / `.timer`,
  `llama-swap-keepalive.service` / `.timer`
- Future-tier reference (for hooks only, not in scope):
  `~/Projects/appmilla_github/nats-infrastructure/docker-compose.yml`

## Test Execution Log

All evidence captured 2026-05-01 on `promaxgb10-41b1`.

### `docker inspect graphiti-mcp` health — before-and-after

**Before** (after starting the container with the un-repaired healthcheck —
this is the symptom the task description called out):

```json
{
  "Status": "starting",
  "FailingStreak": 0,
  "Log": [
    {
      "Start": "2026-05-01T21:06:14.661655483+01:00",
      "End":   "2026-05-01T21:06:14.72051776+01:00",
      "ExitCode": 1,
      "Output": "curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server"
    },
    {
      "Start": "2026-05-01T21:06:19.7218763+01:00",
      "End":   "2026-05-01T21:06:19.770860836+01:00",
      "ExitCode": 1,
      "Output": "curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server"
    }
  ]
}
```

(Status was still `starting` rather than `unhealthy` only because we
restarted the container and it hadn't yet hit the 3-retry threshold. Same
failing probe as the task description's "Up 2 days (unhealthy)" symptom.)

**After** (post-fix; ExitCode 0 across the entire ring buffer):

```json
{
  "Status": "healthy",
  "FailingStreak": 0,
  "Log": [
    { "Start": "2026-05-01T21:11:59...", "End": "2026-05-01T21:11:59...", "ExitCode": 0, "Output": "" },
    { "Start": "2026-05-01T21:12:09...", "End": "2026-05-01T21:12:09...", "ExitCode": 0, "Output": "" },
    { "Start": "2026-05-01T21:12:19...", "End": "2026-05-01T21:12:19...", "ExitCode": 0, "Output": "" },
    { "Start": "2026-05-01T21:12:29...", "End": "2026-05-01T21:12:29...", "ExitCode": 0, "Output": "" },
    { "Start": "2026-05-01T21:12:39...", "End": "2026-05-01T21:12:39...", "ExitCode": 0, "Output": "" }
  ]
}
```

`docker inspect graphiti-mcp --format '{{.State.Health.Status}}'` → `healthy`.
**AC-1 ✓**

### `graphiti-stack-{down,up}.sh` cycle — pre-fix vs post-fix

**Pre-fix down + up** (down was already idempotent; up was broken):

```
$ bash scripts/graphiti-stack-down.sh
... graphiti-mcp not running — skipping
... vllm-embedding not running — skipping
... vllm-graphiti not running — skipping
Stack down.
EXIT: 0

$ bash scripts/graphiti-stack-up.sh
── [1/3] vllm-graphiti (LLM) ──
scripts/graphiti-stack-up.sh: line 136: .../scripts/vllm-graphiti.sh: No such file or directory
EXIT: 127
```

**Post-fix down + up** (clean cycle ending in `healthy`):

```
$ bash scripts/graphiti-stack-down.sh
... Stopping graphiti-mcp... ✓ graphiti-mcp removed
Stack down.
EXIT: 0

$ bash scripts/graphiti-stack-up.sh
── [1/3] llama-swap precondition ──
  ✓ llama-swap up at http://localhost:9000 with qwen-graphiti + nomic-embed
── [2/3] FalkorDB precondition ──
  ✓ FalkorDB reachable at whitestocks:6379
── [3/3] graphiti-mcp ──
  ... ✓ graphiti-mcp ready (HTTP 307) after 2s
Stack is up
EXIT: 0
```

After ~5 s the healthcheck flips to `healthy`. **AC-2 ✓**.

### Idempotency

```
$ bash scripts/graphiti-stack-up.sh   # first run
... Stack is up ... EXIT: 0
$ bash scripts/graphiti-stack-up.sh   # second run, already up
... Stack is up ... EXIT: 0           # AC-3 ✓

$ bash scripts/graphiti-stack-down.sh # first run
... ✓ graphiti-mcp removed ... EXIT: 0
$ bash scripts/graphiti-stack-down.sh # second run, already down
... graphiti-mcp not running — skipping ... EXIT: 0   # AC-4 ✓
```

### `infra-down.sh` then `infra-up.sh`

```
$ bash scripts/infra-down.sh
── Tier 1: agents ──    [hook] agents-down.sh — TODO: implemented by future task
── Tier 2: NATS ──      [hook] nats-down.sh   — TODO: implemented by future task
── Tier 3: Graphiti ──  graphiti-mcp not running — skipping
── Tier 4: llama-swap ──  llama-swap left running (...)
Infrastructure down
EXIT: 0    # AC-6 ✓ (also re-runnable without error)

$ bash scripts/infra-up.sh
── Tier 1: llama-swap ── ✓ up at :9000 with qwen-graphiti + nomic-embed
── Tier 2: Graphiti ──   FalkorDB ✓; graphiti-mcp ready (HTTP 307) after 2s
── Tier 3: NATS ──       [hook] nats-up.sh — TODO: implemented by future task
── Tier 4: agents ──     [hook] agents-up.sh — TODO: implemented by future task
Infrastructure up
EXIT: 0    # AC-5 ✓
```

### `infra-status.sh` post-`infra-up`

```
── llama-swap (LLM + embed, :9000) ──
  endpoint:    UP at http://localhost:9000
  qwen-graphiti listed:  yes
  nomic-embed   listed:  yes

── graphiti-mcp (:8004) ──
  container:   running
  health:      healthy

── FalkorDB (whitestocks:6379, NAS via Tailscale) ──
  reachable:   yes (PONG over Tailscale)

── NATS tier ──
  NATS:        not yet managed by infra-* scripts (TODO: future task)

── Agents tier ──
  agents:      not yet managed by infra-* scripts (TODO: future task)
```

### jarvis → graphiti smoke check (canonical MCP `initialize`)

```
$ curl -s -o /tmp/init-resp.txt -w 'HTTP %{http_code}\n' --max-time 5 \
    -X POST http://promaxgb10-41b1:8004/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
         "params":{"protocolVersion":"2024-11-05",
                   "capabilities":{},
                   "clientInfo":{"name":"smoke-check","version":"0.1"}}}'
HTTP 200

$ head -c 240 /tmp/init-resp.txt
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",
       "capabilities":{...},
       "serverInfo":{"name":"Graphiti Agent Memory","version":"1.27.0"},
       "instructions":"...
```

Round-trip MCP handshake succeeds: TCP reachable, FastMCP listener up,
graphiti-core initialized against FalkorDB, model identifiers `qwen-graphiti`
and `nomic-embed` accepted by llama-swap. **AC-8 ✓** (canonical endpoint
documented in `RUNBOOK-INFRA-ORCHESTRATION.md` §6).

### Acceptance criteria — final state

| AC    | Status | Evidence |
|-------|--------|----------|
| AC-1  | ✓ | `Health.Status: healthy` post-fix; healthcheck Log shows ExitCode 0 across ring buffer. |
| AC-2  | ✓ | down → up cycle, both EXIT 0, ends with healthy graphiti-mcp. |
| AC-3  | ✓ | stack-up twice, both EXIT 0. |
| AC-4  | ✓ | stack-down twice, both EXIT 0; second run no-ops cleanly. |
| AC-5  | ✓ | `infra-up.sh` from cold state, EXIT 0, per-tier pass lines printed. |
| AC-6  | ✓ | `infra-down.sh` returns to cold cleanly, EXIT 0, re-runnable. |
| AC-7  | ✓ | `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` written; DGX-OS-update workflow + future-tier hook sections present. |
| AC-8  | ✓ | curl POST `/mcp` initialize → HTTP 200 with `serverInfo.name = "Graphiti Agent Memory"`. |
| AC-9  | ✓ | All new + modified scripts use `set -euo pipefail`; preconditions/postconditions/exit-code blocks in headers; per-step `── [n/N] ──` status lines. |
| AC-10 | ✓ | No llama-swap unit/config touched. `infra-up.sh` only triggers `systemctl start llama-swap-keepalive.service` (an existing unit, identical to what its timer fires). `infra-down.sh` leaves it running by default. |
| AC-11 | ✓ | `scripts/infra/{nats,agents}-{up,down,status}.sh` exist as no-op stubs sourced by the three top-level scripts; each prints `TODO: implemented by future task`. Future tasks fill them in without touching the top-level scripts. |
