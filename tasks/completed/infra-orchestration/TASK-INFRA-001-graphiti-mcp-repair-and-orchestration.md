---
id: TASK-INFRA-001
title: "graphiti-mcp diagnostic + repair + infra-orchestration scaffold"
status: backlog
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T00:00:00Z
priority: high
task_type: task-work
tags: [infra, graphiti, graphiti-mcp, llama-swap, orchestration, dgx, runbook, gb10]
complexity: 6
feature: infra-orchestration
parent_review: null
test_results:
  status: pending
  coverage: null
  last_run: null
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

- [ ] **AC-1 (graphiti-mcp healthy)**: After
  `bash scripts/graphiti-stack-up.sh` from a cold state,
  `docker inspect graphiti-mcp --format '{{.State.Health.Status}}'`
  returns `healthy`.
- [ ] **AC-2 (clean cycle)**: `bash scripts/graphiti-stack-down.sh`
  followed by `bash scripts/graphiti-stack-up.sh` exits 0 on both calls
  and ends with graphiti-mcp `healthy`.
- [ ] **AC-3 (idempotent stack-up)**: Running
  `bash scripts/graphiti-stack-up.sh` twice in a row exits 0 both times
  with no error output on the second invocation.
- [ ] **AC-4 (idempotent stack-down)**: Running
  `bash scripts/graphiti-stack-down.sh` twice in a row exits 0 both times
  with no error output on the second invocation.
- [ ] **AC-5 (infra-up cold start)**: `bash scripts/infra-up.sh` from a
  cold state brings the LLM + graphiti tier to healthy and reports
  per-component pass on stdout.
- [ ] **AC-6 (infra-down cold)**: `bash scripts/infra-down.sh` returns the
  LLM + graphiti tier to a cold state cleanly, exits 0, and is safe to
  re-run.
- [ ] **AC-7 (DGX OS update workflow documented)**:
  `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` exists and contains the
  documented workflow `infra-down → reboot → infra-up → infra-status`,
  plus explicit hook sections for the NATS tier and the agents tier that
  future tasks will fill in.
- [ ] **AC-8 (jarvis → graphiti smoke check)**: After `infra-up.sh`,
  jarvis can reach graphiti via its configured `JARVIS_GRAPHITI_ENDPOINT`
  — a `curl` from the jarvis host to the canonical graphiti HTTP
  endpoint returns HTTP 200. The exact `curl` command and expected
  response are documented in the runbook.
- [ ] **AC-9 (script hygiene)**: All new and modified shell scripts use
  `set -euo pipefail` (or documented equivalent), have header comments
  documenting preconditions / postconditions / exit codes, and emit
  clear per-step status lines.
- [ ] **AC-10 (no llama-swap modification)**: This task does not modify
  llama-swap itself, its config, or its systemd units. It only consumes
  llama-swap's `:9000` endpoint.
- [ ] **AC-11 (extension hooks present, no-op by default)**: `infra-up.sh`
  and `infra-down.sh` source (or otherwise reference) NATS-tier and
  agents-tier hooks that currently no-op with a clear "TODO:
  implemented by future task" message — the future tasks fill these in
  without needing to restructure the top-level script.

## Test Requirements

- [ ] Capture and paste in the implementation notes:
      `docker inspect graphiti-mcp --format '{{json .State.Health}}' | jq`
      output before-and-after the repair.
- [ ] Capture and paste:
      `bash scripts/graphiti-stack-down.sh` followed by
      `bash scripts/graphiti-stack-up.sh` full transcripts (both pre-fix
      to demonstrate the failure mode, and post-fix to demonstrate the
      cycle is clean).
- [ ] Capture and paste:
      `bash scripts/infra-down.sh` followed by `bash scripts/infra-up.sh`
      full transcripts.
- [ ] Capture and paste:
      `bash scripts/infra-status.sh` output post-`infra-up`.
- [ ] Capture and paste the jarvis → graphiti smoke check `curl`.

## Implementation Notes

### Diagnostic findings

(Filled in during `/task-work` Phase 1 — the actual error text from
`graphiti-stack-{up,down}.sh`, the actual healthcheck failure reason from
`docker inspect`, and the actual current env var values for graphiti-mcp.
Do not pre-judge — capture what is, not what is suspected.)

### Configuration changes

(Filled in during `/task-work` — list each env var or config line changed,
with old value → new value.)

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

(Populated by `/task-work`.)
