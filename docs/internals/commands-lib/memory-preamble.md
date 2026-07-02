# Fleet-Memory Availability, Seeding & Search Preamble

Shared knowledge-capture pattern for GuardKit command specs.

**Reference from command specs with**: `See: docs/internals/commands-lib/memory-preamble.md`

> **FEAT-MEM-09 (2026-07-02):** GuardKit's knowledge-capture backend is **fleet-memory**
> (a pure-embeddings store). The Graphiti/FalkorDB implementation was **removed** — the
> `get_graphiti()` client, the `guardkit graphiti` CLI group, the `SystemDesignGraphiti` /
> `SystemPlanGraphiti` classes, the `graphiti-check` binary, and the `.guardkit/graphiti.yaml`
> `enabled:` flag **no longer exist**. Do not reference them. This preamble replaces the
> retired `graphiti-preamble.md`.

---

## Background

GuardKit command specs are markdown files interpreted by the Claude Code LLM — **not**
executed as Python scripts. The LLM has Read, Bash, Edit, Grep, Glob, Write, and (when the
server is connected) MCP tools. It has **no** Python runtime, so Python pseudocode like
`get_graphiti()` will always be unavailable — use the tool-native patterns below.

Knowledge capture is reached two ways:

- **MCP tools** (preferred, in-session, zero subprocess overhead) — `mcp__fleet_memory__memory_search`
  (read) and `mcp__fleet_memory__memory_write_payload` (write).
- **`guardkit memory` CLI** (Bash fallback) — `guardkit memory search` / `guardkit memory status`.
  The CLI covers **search and status only**; it has **no** arbitrary-write subcommand, so
  seeding new artefacts requires the MCP write tool.

Fleet-memory is **env-driven** (`FLEET_MEMORY_*` in a gitignored `.env`, plus the
`fleet_memory` server in `.mcp.json`). There is no per-project `enabled:` config file to read.

---

## Tier 0: MCP Tools (Preferred)

**Instructions for the LLM:**

Check whether `mcp__fleet_memory__memory_search` (read) and
`mcp__fleet_memory__memory_write_payload` (write) are available. Check BOTH the immediate
tool list AND the deferred-tool list shown in system reminders (deferred tools are loadable
on demand via `ToolSearch`).

- **IF** present in the immediate tool list:
  - SET `memory_available = true`, `memory_access = "mcp"`

- **IF** present only in the deferred-tool list (system reminder):
  - Load their schemas first, then treat them as available:
    ```
    ToolSearch(query: "select:mcp__fleet_memory__memory_search,mcp__fleet_memory__memory_write_payload")
    ```
    If that exact-name select returns no match, discover the tools by keyword (the server may
    expose a suffixed name such as `..._tool`):
    ```
    ToolSearch(query: "fleet_memory memory search write payload")
    ```
  - SET `memory_available = true`, `memory_access = "mcp"`

- **IF** the fleet-memory MCP tools are absent from BOTH lists:
  - Fall through to Tier 1 (CLI check).

When `memory_access = "mcp"`, use the tools directly (see [Search Pattern](#search-pattern-read)
and [Seeding Pattern](#seeding-pattern-write)). MCP handles store connectivity internally.

---

## Tier 1: CLI Availability Check (Bash Fallback)

Use this when the MCP tools are not in-session. Run via the Bash tool:

```bash
guardkit memory status
```

- **IF** the output reports `Status: REACHABLE`:
  - SET `memory_available = true`, `memory_access = "cli"`
  - **Search** works via `guardkit memory search` (below). **Writes still require the MCP
    tool** — if `memory_access = "cli"`, offer the seeding payloads for review but note they
    can only be persisted when the fleet-memory MCP tools are connected; otherwise skip seeding.

- **IF** the output reports `UNAVAILABLE`, `DISABLED`, `DEGRADED`, or errors:
  - SET `memory_available = false`
  - Display the [unavailability warning](#warning-message-template) and continue with markdown
    artefacts only — **do not block the command**.

> Env for the CLI (if needed): `set -a; . ./.env; set +a; export FLEET_MEMORY_ENABLED=true
> GUARDKIT_MEMORY_BACKEND=fleet_memory`.

---

## Payload Model Reference (the write contract)

Fleet-memory stores **typed payloads**. Every write is a dict with a `payload_type` and the
shared `BasePayload` fields. The seven registered payload types are: `adr`, `review_report`,
`build_outcome`, `pattern`, `warning`, `seed_module`, `document`.

**Shared `BasePayload` fields (required on every write):**

| Field | Value |
|-------|-------|
| `payload_type` | one of the seven types |
| `project` | `"guardkit"` (underscores only — `^[a-zA-Z0-9_]+$`) |
| `identifier` | stable id, **underscores only** — sanitise hyphens/colons to `_` (e.g. `ADR-007` → `ADR_007`, `user-service` → `user_service`) |
| `source_ref` | provenance — the artefact's file path or source id |
| `domain_tags` | list of category tags (drives group-scoped reads) |

The server derives `natural_key = "{payload_type}:{project}:{identifier}"` and upserts
idempotently on it. Type-specific required fields:

- **`adr`** → `decision` (str), `status` (str, e.g. `"accepted"`).
- **`document`** → `content` (str, optional but include it — the prose is embedded for
  semantic retrieval AND tagged for group-scoped reads).

**Canonical mapping for architecture/design artefacts** (write tag == read tag — use these
consistently so a later search finds what a command wrote):

| Artefact | `payload_type` | `domain_tags` | `identifier` | body |
|----------|---------------|---------------|--------------|------|
| ADR (`/system-arch`, `/arch-refine`) | `adr` | `["architecture"]` | `ADR_NNN` | `decision`, `status` |
| Design Decision Record / DDR (`/system-design`) | `adr` | `["design"]` | `DDR_NNN` | `decision`, `status` |
| API contract (`/system-design`) | `document` | `["design", "api_contract"]` | `<contract_slug>` | `content` = contract markdown |
| Data model (`/system-design`) | `document` | `["design", "data_model"]` | `<model_slug>` | `content` = model markdown |
| Architecture doc (`/system-arch`) | `document` | `["architecture"]` | `<doc_slug>` | `content` = doc markdown |
| System plan artefact (`/system-plan`) | `document` | `["architecture", "plan"]` | `<slug>` | `content` = plan markdown |

> This vocabulary aligns with `guardkit/knowledge/fleet_memory_mapping.py` (the authoritative
> group→payload mapping). ADRs and design decisions are `adr` payloads; contracts, models,
> and prose docs are `document` payloads with `content`.

---

## Seeding Pattern (write)

When the command produces artefacts worth capturing AND `memory_available` is true:

1. Build the payload dict(s) per the mapping table above.
2. **Display** the payloads and ask: `"Seed these to fleet-memory now? [Y/n]"`.
3. On yes, if `memory_access = "mcp"`, write each via the MCP tool; if `memory_access = "cli"`,
   note that writes need the MCP tools connected and skip (artefacts remain on disk).

**ADR / DDR example:**

```
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr",
  "project": "guardkit",
  "identifier": "ADR_007",
  "decision": "Adopt CQRS for the ordering bounded context",
  "status": "accepted",
  "domain_tags": ["architecture"],
  "source_ref": "docs/architecture/decisions/ADR-007.md"
})
```

**Document (API contract / data model / architecture doc) example:**

```
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "document",
  "project": "guardkit",
  "identifier": "ordering_api",
  "content": "<the generated API-contract markdown>",
  "domain_tags": ["design", "api_contract"],
  "source_ref": "docs/design/contracts/ordering-api.md"
})
```

The tool returns the derived `natural_key` (e.g. `adr:guardkit:ADR_007`) on success. Writes
are idempotent (content-hash upsert), so re-running a command is safe.

If a write fails or `memory_available` is false, display the warning and continue — the
artefacts on disk are the primary deliverable; seeding is the optional tail.

---

## Search Pattern (read)

**MCP** (`memory_access = "mcp"`):

```
mcp__fleet_memory__memory_search(
  project="guardkit",
  query="<what you are looking for>",
  payload_types=["adr", "document"],     # optional filter
  domain_tags=["architecture"],           # optional filter
  token_budget=2000
)
```

Returns `{context_block, coverage_score, contributing_types, tokens_used}`. A non-empty
`context_block` (or `coverage_score > 0`) means matching knowledge exists.

**CLI** (`memory_access = "cli"`):

```bash
guardkit memory search "<query>" --payload-types adr --domain-tags architecture --token-budget 2000
```

(`guardkit memory search --help` for options: `--token-budget`, `--payload-types`,
`--domain-tags`. There is no `--limit`.)

---

## Prerequisite Check Pattern (architecture context exists)

Several commands need to know whether **architecture context** already exists (this replaces
the removed `has_architecture_context()` / `SystemPlanGraphiti` prerequisite). Check **both**
sources; either satisfies the prerequisite:

1. **Fleet-memory** (if `memory_available`): search for architecture context —
   `memory_search(project="guardkit", query="architecture components services bounded contexts",
   payload_types=["adr", "document"], domain_tags=["architecture"])`. A non-empty result =
   context exists.
2. **Filesystem** (always): Glob `docs/architecture/**` and `docs/design/**`. Matching files =
   context exists.

If neither source has context, tell the user to run the upstream command (e.g. `/system-arch`)
first — the same gate the command already documents.

---

## Warning Message Template

When fleet-memory is unavailable, display this and continue (never block):

```
⚠️  Fleet-memory unavailable — continuing without knowledge capture.
    Reason: {status output, or "MCP tools not connected and CLI not reachable"}

    Artefacts are written to markdown only. Re-run with the fleet_memory MCP server
    connected (see .mcp.json) to seed the knowledge store.
```

All commands with knowledge-capture integration MUST degrade gracefully.

---

## How to Reference from Command Specs

Replace any Python/Graphiti pseudocode with a reference to the appropriate section here.

**Availability check** (replaces `get_graphiti()` / `graphiti.yaml` reads):

```markdown
### Step N: Check Fleet-Memory Availability

Follow `docs/internals/commands-lib/memory-preamble.md` Tier 0 → Tier 1:
check for the `mcp__fleet_memory__*` tools; else `guardkit memory status`. Set
`memory_available` and `memory_access` accordingly, and degrade to markdown-only if neither.
```

**Seeding** (replaces `guardkit graphiti add-context` / `SystemDesignGraphiti`):

```markdown
### Step N: Seed Fleet-Memory (if available)

If `memory_available`, build the payloads per the memory-preamble mapping table and offer
them for review ("Seed these to fleet-memory now? [Y/n]"). On yes, write each via
`mcp__fleet_memory__memory_write_payload`.
```

**Search / prerequisite** (replaces `has_architecture_context()` / graphiti search):

```markdown
Follow the memory-preamble "Prerequisite Check Pattern": search fleet-memory
(`domain_tags=["architecture"]`) and/or Glob `docs/architecture/**` — either satisfies the gate.
```
