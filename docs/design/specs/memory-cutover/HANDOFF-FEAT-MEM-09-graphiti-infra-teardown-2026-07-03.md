# HANDOFF — FEAT-MEM-09 §3.5 / WS-6: Graphiti INFRA teardown (next steps to fully get rid of Graphiti) — 2026-07-03

Pick-up doc for a **fresh conversation**. The guardkit **application** is fully off Graphiti; what's left
is the **infrastructure teardown**, which is **fleet-wide, one-way, and operator-gated**. This doc is the
step-by-step plan to finish removing Graphiti — read the ⛔ GATE in §1 before touching anything shared.

---

## 0. TL;DR — where we are

- **guardkit-the-application: DONE.** No live Graphiti code paths; `.mcp.json` = `fleet_memory` only;
  installer/rules/docs/command-specs de-graphiti'd; §3.3 W1 read-consumers proven on the fleet-memory seam.
  (Full arc: `HANDOFF-FEAT-MEM-09-W1-and-degraphiti-2026-07-03.md`.)
- **The GB10 / NAS INFRA: STILL STANDING.** The Graphiti MCP server, its Docker image, its stand-up/backup
  scripts (in guardkit's `scripts/`), the **FalkorDB** database, and the **`qwen-graphiti`** LLM are all live.
- **This is bigger than "pull FalkorDB + Qwen2.5."** It's a whole shared stack, and — critically —
  **only guardkit has been migrated.** Other consumers still exist (§1).

---

## 1. ⛔ THE GATE — do NOT tear down shared infra until every consumer is off Graphiti

**FalkorDB is FLEET-WIDE**, not guardkit-local: ~**11.8k nodes / ~92 graphs / ~18 projects** (memory
`[[falkordb-fleet-wide-not-guardkit-local]]`). guardkit's ~4,154 nodes were **never migrated** to
fleet-memory (guardkit's reads just went dark to Graphiti; the data stayed in FalkorDB).

**Named other graph consumers** (memory `[[graphiti-cutover-qwen25-removal]]`, and the shared llama-swap
comment in `scripts/graphiti-stack-down.sh` — "llama-swap … shared by graphiti-mcp, jarvis, autobuild"):
**forge, jarvis, specialist-agent, study-tutor** (+ whatever else populates the ~18 project graphs).

**None of those were touched this session — I only did guardkit.** So:

> **Destroying FalkorDB or pulling `qwen-graphiti` now would break every consumer that still reads them.**
> The teardown CANNOT proceed until **all** consumers are confirmed migrated off Graphiti/FalkorDB.

**First real task of the teardown = an audit:** for each of forge / jarvis / specialist-agent / study-tutor
(and any other repo that ever wrote to the shared FalkorDB), confirm it no longer reads/writes Graphiti/
FalkorDB (same shape as guardkit's cutover). Until that audit is green, everything below §2's guardkit-only
steps is **blocked**.

---

## 2. The Graphiti infra inventory (verified 2026-07-03)

### 2a. guardkit's `scripts/graphiti-*` (the GB10 stand-up/manage tooling — all still present)
| Script | What it does |
|---|---|
| `graphiti-mcp.sh` | Starts the Graphiti MCP **HTTP server** container on the GB10 (talks to llama-swap :9000 + FalkorDB). |
| `graphiti-stack-up.sh` / `graphiti-stack-down.sh` | Bring the stack up / stop+remove the `graphiti-mcp` container. **stack-down is idempotent + safe**; it deliberately does **NOT** stop llama-swap (:9000 is systemd-managed and shared). |
| `graphiti-mcp-build.sh` | Builds the standalone `graphiti-mcp` Docker image (clones the `guardkit/graphiti` fork at `$GRAPHITI_TAG`). |
| `graphiti-mcp-bootstrap.py`, `graphiti-mcp-config.yaml` (+ `.pre-llamacpp.bak`) | MCP server bootstrap + config (points at FalkorDB + the `qwen-graphiti`/`nomic-embed` llama-swap aliases). |
| `graphiti-backup.sh` | **FalkorDB backup/restore** — Redis `BGSAVE` + volume tar of the `guardkit-falkordb` container. `backup` / `restore` / `list` / `verify`. **This is the tool you use to snapshot before destroy.** |
| `graphiti-endpoint-toggle.sh`, `graphiti-validation/` | Endpoint toggle + validation helpers. |

> ⚠️ **Do NOT `git rm` these first.** You *need* `graphiti-backup.sh` + `graphiti-stack-down.sh` to *perform*
> the decommission. Remove the script files **last**, as the final commit after the infra is actually gone.

### 2b. The runtime pieces (on the GB10 / NAS)
- **FalkorDB** — Docker container `guardkit-falkordb`, reachable at `whitestocks:6379` (Synology NAS via
  Tailscale). Holds the fleet-wide graph data. Backup/restore via `graphiti-backup.sh`.
- **Graphiti MCP server** — the `graphiti-mcp` container (was the HTTP MCP on `:8004`).
- **llama-swap on `:9000`** — serves `qwen-graphiti` (the Graphiti extraction **LLM**) **and** an embedder
  (`nomic-embed`). **Shared** infra (systemd `llama-swap-keepalive.timer` / `-healthcheck.timer`), also used
  by autobuild/jarvis — see `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md`.

### 2c. ⚠️ KEEP the embedder fleet-memory needs
The teardown pulls the **`qwen-graphiti` LLM**, NOT the embedder. **fleet-memory requires an embedder.**
Per memory `[[qwen-embed-switch-1024]]`, fleet-memory was switched to a **qwen embed (1024-dim), pinned
resident** on llama-swap — a *different* alias from Graphiti's `nomic-embed`. **Before removing any embed
alias, confirm which one fleet-memory uses (`EMBED_URL`/`FLEET_MEMORY_*` in `.env` + `.mcp.json`) and keep
it.** Do not assume `nomic-embed` is safe to pull — verify against the live fleet-memory config.

---

## 3. The teardown sequence (ordered; each step gated on the previous)

**Phase A — un-gate (fleet-wide audit).** §1. Confirm forge/jarvis/specialist-agent/study-tutor (+ any
other FalkorDB writer) are off Graphiti. **Blocks everything below.**

**Phase B — decide the DATA fate (one-way).** guardkit's ~4,154 FalkorDB nodes (and the other projects')
are **not** in fleet-memory. Decide per project:
- **Migrate** the prose you want to keep: `guardkit memory migrate-graph` (`guardkit/cli/memory.py:328`)
  reads FalkorDB via `read_falkordb_episodics` (`guardkit/memory/graph_export.py:224`) and writes
  `document` payloads to fleet-memory. Dry-run first: `guardkit memory migrate-graph --dry-run --limit 5`.
  (Other repos need their own export, or accept the loss.)
- **Or accept the loss** and document it. Either way, this is **irreversible** once FalkorDB is destroyed.

**Phase C — snapshot (safety net).** `./scripts/graphiti-backup.sh backup --output <dir>` then
`graphiti-backup.sh verify`. Copy the tarball somewhere durable (the NAS backup per `[[nas-backup-whitestocks-access]]`).
This is your rollback if Phase D is premature.

**Phase D — stop + remove the Graphiti MCP stack.** `./scripts/graphiti-stack-down.sh` (stops + removes the
`graphiti-mcp` container; idempotent; leaves llama-swap alone). Confirm nothing depends on the MCP being up
(re-check the Phase-A consumers). Optionally remove the built Docker image.

**Phase E — destroy FalkorDB (⛔ one-way, fleet-wide).** Only after B–D and the Phase-A audit are all green.
Stop + remove the `guardkit-falkordb` container **and its volume** on the NAS. This is the irreversible,
fleet-wide data destruction. Keep the Phase-C backup.

**Phase F — pull the `qwen-graphiti` LLM from llama-swap.** Remove the `qwen-graphiti` alias from the
**personal** llama-swap config (per `[[dgx-spark-repo-and-config-split]]` — public vs personal configs; the
`qwen-graphiti` alias lives in the personal one). **KEEP the fleet-memory embedder alias** (§2c). This is the
"drop Qwen2.5-instruct" step — coordinate with the other 4 consumers so none still needs it.

**Phase G — remove the guardkit-side tooling (last).** Now that the stack is gone: `git rm` the
`scripts/graphiti-*` cluster (§2a) + fix the two stale in-comment refs to the deleted rule file in
`scripts/graphiti-mcp-config.yaml` (+ `.bak`). Update `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md` to drop
the graphiti-stack sections. Commit. Grep gate: `grep -rli graphiti scripts/ docs/runbooks/` → empty (bar
history).

**Phase H — final verify + sign-off.** `guardkit memory status` still REACHABLE (fleet-memory unaffected);
`grep -rln graphiti guardkit/ scripts/` returns only intentional history; FalkorDB gone; the personal
llama-swap config Graphiti-free; document the rollback-loss.

---

## 4. What is safe to do WITHOUT the fleet-wide gate

Essentially nothing infra-side — the scripts manage **shared** infra other repos may still use, so even
`git rm`-ing them early would strand the operator's ability to back up / stop the still-running shared stack.
The guardkit **application** work is already complete and needs nothing here. **Do not start Phases D–G
until Phase A (all-consumers-migrated) is confirmed.**

The one genuinely-safe-anytime tidy: the **two stale in-comment references** to the deleted
`.claude/rules/graphiti-knowledge-graph.md` inside `scripts/graphiti-mcp-config.yaml` and its `.bak` — but
since those files are slated for deletion in Phase G anyway, it's not worth a separate commit.

---

## 5. Answering the two questions that prompted this doc

- **"Are all the repos that referenced Graphiti now clear of it?"** — **No. Only guardkit.** forge / jarvis /
  specialist-agent / study-tutor (+ the ~18 FalkorDB projects) were **not** audited or migrated this session.
  That audit is Phase A and is the precondition for the whole teardown.
- **"Is Graphiti gone from the scripts that stand up the GB10 infra?"** — **No.** The full
  `scripts/graphiti-*` cluster (§2a) is still present and functional; it's removed in **Phase G**, last.

---

## 6. Pointers

- **App-side completion + the reusable test pattern:** `HANDOFF-FEAT-MEM-09-W1-and-degraphiti-2026-07-03.md`.
- **Scoping / disposition:** `FEAT-MEM-09-3.3-code-scoping-2026-07-03.md`, `FEAT-MEM-09-consumer-disposition-map.md`
  (§4 W5/W6 = this infra teardown).
- **Infra runbook to update in Phase G:** `docs/runbooks/RUNBOOK-INFRA-ORCHESTRATION.md`.
- **Migrate tool:** `guardkit memory migrate-graph` (`guardkit/cli/memory.py:328`) / `guardkit/memory/graph_export.py`.
- **Backup tool:** `scripts/graphiti-backup.sh`.
- **Spark infra runbooks (sibling repo):** `../dgx-spark` (per `[[dgx-spark-repo-and-config-split]]`) — the
  llama-swap config edits (Phase F) live with that repo's runbooks; the public config is already Qwen2.5-free,
  the **personal** (`coach-ft-v3`) one still has `qwen-graphiti`.
- **Memory to load:** `falkordb-fleet-wide-not-guardkit-local`, `graphiti-cutover-qwen25-removal`,
  `qwen-embed-switch-1024`, `dgx-spark-repo-and-config-split`, `nas-backup-whitestocks-access`,
  `dgx-litellm-frontdoor-community-stack`, `main-has-preexisting-red-tests`, `git-workflow-commit-to-main`.

---

## 7. Suggested next move

Don't reach for FalkorDB/Qwen2.5 first. **Start with Phase A**: audit forge / jarvis / specialist-agent /
study-tutor for any remaining Graphiti/FalkorDB reads or writes (repo by repo, same cutover shape as
guardkit). Only when that's green does the destructive teardown (Phases B→F) become safe. A good first
concrete step is to run each of those repos' equivalent of `grep -rln "get_graphiti\|GraphitiClient\|
falkordb\|:8004" <repo>/ --include='*.py'` and check their `.mcp.json` for a graphiti server.
