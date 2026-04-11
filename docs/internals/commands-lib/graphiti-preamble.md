# Graphiti Availability Preamble

Shared availability check pattern for GuardKit command specs.

**Reference from command specs with**: `See: docs/internals/commands-lib/graphiti-preamble.md`

---

## Background

GuardKit command specs are markdown files interpreted by the Claude Code LLM — **not** executed as Python scripts. The LLM has access to Read, Bash, Edit, Grep, Glob, and Write tools. It does **not** have a Python runtime.

Python pseudocode like `get_graphiti()` will always be interpreted as unavailable because the LLM cannot import Python modules. Use the tool-native patterns below instead.

---

## Tier 0: MCP Tools (Preferred — Zero Overhead)

Use this when Graphiti MCP tools are available in the current Claude Code session.

**When to use**: Any command that reads from or searches the knowledge graph. MCP tools provide direct access with no CLI overhead.

**Instructions for the LLM**:

Check whether `mcp__graphiti__search_nodes` is available in the current session's tool list.

- **IF** available:
  - SET `graphiti_available = true`
  - SET `graphiti_access_method = "mcp"`
  - Use `mcp__graphiti__search_nodes` and `mcp__graphiti__search_memory_facts` directly
  - Always pass explicit `group_ids` (see `.claude/rules/graphiti-knowledge-graph.md`)
  - **Skip Tier 1 and Tier 2** — MCP handles connectivity internally

- **IF** not available:
  - Fall through to Tier 1 (Read-Based Check)

> **Why prefer MCP?** MCP tools run in-process with the LLM session, avoiding
> the overhead of spawning a Python subprocess via Bash. They also provide
> richer results (structured entities and facts) compared to the CLI wrapper's
> flat text output.

---

## Tier 1: Read-Based Check (Always Available)

Use this for a fast availability signal that requires no CLI tools.

**When to use**: Any command that needs to know whether Graphiti is enabled before proceeding. Zero external dependencies.

**Instructions for the LLM**:

Use the Read tool to read `.guardkit/graphiti.yaml`.

- **IF** the file exists and contains `enabled: true`:
  - SET `graphiti_available = true`
  - Note the `group_ids` list for seeding references
  - Note connection details (`falkordb_host`, `falkordb_port`) for context

- **IF** the file does not exist, or `enabled:` is `false` or missing:
  - SET `graphiti_available = false`
  - Display the unavailability warning (see [Warning Message Template](#warning-message-template) below)
  - Continue with markdown artefacts only — do not block the command

---

## Tier 2: CLI Connectivity Check (Full Verification)

Use this when the command will actually write to or read from Graphiti (seeding phase). Tier 2 confirms FalkorDB is reachable, not just that the config says `enabled: true`.

**When to use**: Before executing any `guardkit graphiti` seeding commands. Requires Tier 1 to pass first.

**Instructions for the LLM**:

Run via Bash tool:

```bash
/Users/richardwoollcott/.agentecflow/bin/graphiti-check --status --quiet
```

Parse the JSON output:

```json
{"available": true, "error": null, "context": null, "categories": 0, "tokens_used": 0, "tokens_budget": 0}
```

- **IF** `available` is `true`: Graphiti is reachable — proceed with seeding
- **IF** `available` is `false`: Display the unavailability warning, skip seeding, continue

> **Note**: Use the absolute path `/Users/richardwoollcott/.agentecflow/bin/graphiti-check` — the `~/.agentecflow/bin/` directory is not on `$PATH` by default.

---

## Warning Message Template

When Graphiti is unavailable, display this standard message and continue:

```
⚠️  Graphiti unavailable — continuing without knowledge graph context.
    Reason: {error from graphiti-check, or "Config disabled / file not found"}

    To enable: ensure .guardkit/graphiti.yaml has `enabled: true` and
    FalkorDB is reachable at the configured host.
```

Do **not** block or fail the command. All commands with Graphiti integration must degrade gracefully.

---

## Seeding Commands Template

When Graphiti **is** available and the command produces artefacts worth capturing, generate seeding commands for the user to review and optionally execute.

**Display the commands**, then ask: `"Run these seeding commands now? [Y/n]"`

If yes, execute each via the Bash tool.

### Available `guardkit graphiti add-context` patterns

```bash
# Add a design document
guardkit graphiti add-context docs/design/{output-file}.md \
  --group architecture_decisions

# Add an API contract or spec
guardkit graphiti add-context docs/design/contracts/{name}-api.yaml \
  --group project_design

# Add command workflow knowledge
guardkit graphiti add-context docs/workflows/{workflow}.md \
  --group command_workflows

# Add product/domain knowledge
guardkit graphiti add-context docs/{domain-doc}.md \
  --group product_knowledge
```

### Group IDs reference

Knowledge is stored in two scopes — **system groups** (shared, no prefix) and **project groups**
(project-isolated, prefixed with `{project_id}__`).

#### System Groups (no prefix — shared across all projects on the FalkorDB instance)

| Group ID | Purpose |
|----------|---------|
| `product_knowledge` | GuardKit product knowledge, features, capabilities |
| `command_workflows` | GuardKit command patterns and usage |
| `architecture_decisions` | Global ADRs, design rationale, system decisions |

Seeded by `guardkit graphiti seed-system`. Use these when adding/searching GuardKit
product-level knowledge that should be visible to **all** projects.

#### Project Groups (prefixed — isolated to one project)

| Group ID pattern | Purpose |
|-----------------|---------|
| `{project_id}__project_overview` | Project purpose, goals, problem statement |
| `{project_id}__project_architecture` | Component structure, services, data flow |
| `{project_id}__project_decisions` | Project-level ADRs and technical decisions |
| `{project_id}__feature_specs` | Feature specifications for this project |
| `{project_id}__task_outcomes` | Task completion outcomes and lessons learned |

Seeded by `guardkit graphiti capture`. Replace `{project_id}` with the value from
`.guardkit/graphiti.yaml` (e.g., `guardkit__project_overview` for the guardkit project).

**Isolation rule**: Always use `{project_id}__` prefixed group IDs for project-specific
data. This prevents knowledge from leaking across projects sharing the same FalkorDB instance.

> **MCP access**: When adding knowledge via MCP `add_memory`, always specify the
> appropriate prefixed group_id. Never rely on the MCP server's default `group_id`
> config value — it may not match what the Python client searches. See
> `.claude/rules/graphiti-knowledge-graph.md` for per-project MCP search instructions.

---

## How to Reference from Command Specs

Replace Python pseudocode blocks in command specs with a reference to the appropriate tier.

### Replacing availability check pseudocode

**Before** (broken — LLM cannot execute this):
```python
from guardkit.knowledge.graphiti_client import get_graphiti
client = get_graphiti()
if client:
    ...
else:
    print("Graphiti unavailable")
```

**After** (tool-native — LLM can execute this):
```markdown
### Step N: Check Graphiti Availability

Follow the Tier 1 check from `docs/internals/commands-lib/graphiti-preamble.md`:
Use the Read tool to read `.guardkit/graphiti.yaml`.
If the file exists and `enabled: true`, set `graphiti_available = true`.
Otherwise set `graphiti_available = false` and display the unavailability warning.
```

### Replacing seeding pseudocode

**Before** (broken — LLM cannot call Python methods):
```python
design_sp.upsert_api_contract(contract)
```

**After** (tool-native):
```markdown
### Step N: Seed Graphiti (if available)

If `graphiti_available` is true, run the Tier 2 connectivity check from
`docs/internals/commands-lib/graphiti-preamble.md`, then generate and offer the seeding commands:

```bash
guardkit graphiti add-context docs/design/{output}.md \
  --group architecture_decisions
```

Ask the user: "Run these seeding commands now? [Y/n]"
```

### Inline shorthand (for simple commands)

For commands that only need the availability boolean with no seeding:

```markdown
**Check Graphiti availability** (see `docs/internals/commands-lib/graphiti-preamble.md` Tier 1):
Read `.guardkit/graphiti.yaml` — if `enabled: true`, Graphiti is available.
```
