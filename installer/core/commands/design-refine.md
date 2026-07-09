---
format_version: 1
---

# /design-refine - Iterative Design Refinement Command

Enables iterative refinement of design decisions (DDRs, API contracts, data models) with temporal superseding and feature spec staleness detection. This command sits downstream of `/system-design` in the command pipeline: `/system-arch` (architecture) → `/system-design` (detailed design) → `/design-refine` (iterative refinement).

The command instructs Claude directly (Pattern A: command-spec-only) through a structured interactive session that identifies what to refine via disambiguation, applies changes with temporal superseding, detects staleness in downstream artefacts, and re-validates C4 diagrams.

## Command Syntax

```bash
/design-refine "refinement description" [--focus=CONTEXT] [--no-questions] [--defaults] [--context path/to/file.md]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--focus=CONTEXT` | Target a specific bounded context for refinement (e.g., `--focus="Order Management"`) |
| `--no-questions` | Skip interactive clarification (error — /design-refine requires interactive input) |
| `--defaults` | Use default resolution options without prompting |
| `--context path/to/file.md` | Include additional context files (can be used multiple times) |

## Overview

`/design-refine` is the refinement counterpart to `/system-design`. While `/system-design` creates design artefacts from scratch, `/design-refine` updates them iteratively when requirements change, issues are discovered, or architecture evolves.

**Use cases:**
- Refine DDRs (Design Decision Records) when design rationale changes
- Update API contracts when endpoints need modification
- Modify data models when domain understanding evolves
- Detect and resolve staleness in feature specs caused by design changes
- Ensure C4 L3 diagrams remain consistent after contract updates
- Detect contradictions between proposed design changes and existing ADRs

**Key differences from `/system-design`:**
- `/system-design` → *creates* design artefacts from scratch
- `/design-refine` → *updates* existing design artefacts iteratively
- `/design-refine` → adds temporal superseding for DDR versioning
- `/design-refine` → detects staleness in downstream feature specs

**Prerequisite:** Design context must exist (from a prior `/system-design` run).

## Prerequisite Gate

Before starting the refinement session, `/design-refine` MUST verify that design context exists. This ensures refinement builds on established design decisions rather than creating from scratch.

**Check fleet-memory availability** (see `docs/internals/commands-lib/memory-preamble.md` Tier 0 → Tier 1):

Check for the `mcp__fleet_memory__*` tools; else run `guardkit memory status`. Set `memory_available` (and `memory_access`) accordingly.
- If reachable: set `memory_available = true`
- Otherwise: set `memory_available = false` and display the unavailability warning from the preamble. If neither is reachable, continue markdown-only — never block.

Check for design context (either source satisfies the gate):
- If `memory_available = true`: search fleet-memory for design context — `mcp__fleet_memory__memory_search(project="guardkit", query="design decisions API contracts data models", payload_types=["adr","document"], domain_tags=["design"])`. A non-empty result = context exists.
- Always: use Glob to check for `docs/design/*.md`.
  - If no local design files found AND fleet-memory has no design context: display `NO_DESIGN_CONTEXT_MESSAGE`, ask "Run /system-design first? [Y/n]", and exit
  - If local files found: display `"Fleet-memory unavailable — reading design from local files"` (when `memory_available = false`) and continue

## Execution Flow

### Phase 0: Context Loading

**Load existing design context and validate prerequisites:**

**Check fleet-memory availability** (see `docs/internals/commands-lib/memory-preamble.md` Tier 0 → Tier 1):
Check for the `mcp__fleet_memory__*` tools; else `guardkit memory status`. Set `memory_available` (and `memory_access`) accordingly.

Load existing design context:
- If `memory_available = true`: design decisions (DDRs), API contracts, and ADRs for contradiction detection are available via fleet-memory — `mcp__fleet_memory__memory_search(project="guardkit", query=..., payload_types=["adr","document"], domain_tags=["design"])` for design artefacts and `domain_tags=["architecture"]` for ADRs
- If `memory_available = false`:
  - Use the Read tool on files in `docs/design/decisions/` for DDRs
  - Use the Read tool on files in `docs/design/contracts/` for API contracts
  - No fleet-memory ADRs available for contradiction detection (fall back to local `docs/architecture/ADR-*.md` files if present, else skip that step)
  - Display `"Fleet-memory unavailable — continuing without persistence"`

**Load additional context files (if --context provided):**

```python
context_files = flags.get("context", [])
for context_file in context_files:
    with open(context_file) as f:
        additional_context = f.read()
    print(f"Loaded context from {context_file}")
```

### Phase 1: Disambiguation — Identify What to Refine

**Semantic search via `mcp__fleet_memory__memory_search` (`domain_tags=["design"]`) on user input to identify the target design artefact. This disambiguation flow is identical to the pattern used by `/arch-refine`.**

```python
# Disambiguation flow
user_description = args[0]  # "refinement description"

if memory_available:
    # Semantic search across design artefacts (DDRs, API contracts, data models)
    # mcp__fleet_memory__memory_search(
    #   project="guardkit",
    #   query=user_description,
    #   payload_types=["adr", "document"],
    #   domain_tags=["design"],
    #   token_budget=2000,
    # )
    search_results = memory_search_design(user_description)
else:
    # Fallback: scan local files for matches
    search_results = scan_local_design_files(user_description)
```

**Present top 3-5 matches grouped by relevance and require explicit confirmation:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 DISAMBIGUATION: Matching design artefacts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your input: "update order endpoint response schema"

Found 4 matches (grouped by relevance):

  DDRs:
    1. [DDR-003] Use CQRS for Order Management (score: 0.89)
    2. [DDR-005] Event sourcing for order lifecycle (score: 0.72)

  API Contracts:
    3. [API-order-management] REST endpoints for orders (score: 0.94)
    4. [API-payment-processing] Payment integration API (score: 0.61)

Which artefact do you want to refine?
Enter number (1-4), or [N]ew search, or [C]ancel:
```

```python
# Present results and require explicit confirmation
if not search_results:
    print("No matching design artefacts found.")
    print("Try a more specific description, or run /system-design first.")
    exit(0)

# Group results by type
ddrs = [r for r in search_results if "DDR" in r.get("fact", "")]
contracts = [r for r in search_results if "API" in r.get("fact", "")]
models = [r for r in search_results if "DM" in r.get("fact", "")]

# Display grouped results
display_disambiguation_results(ddrs, contracts, models)

# Require explicit confirmation before proceeding
selected = input("Enter number, [N]ew search, or [C]ancel: ")
if selected.lower() == "c":
    print("Cancelled.")
    exit(0)
if selected.lower() == "n":
    # Re-prompt with new query
    new_query = input("New search query: ")
    search_results = memory_search_design(new_query)  # mcp__fleet_memory__memory_search
    # Re-display...
```

### Phase 2: Refinement — Apply Changes

Based on the selected artefact type, follow the appropriate refinement flow.

#### 2A: DDR Refinement (Temporal Superseding)

**When refining a Design Decision Record, apply temporal superseding: the existing DDR status is set to `"superseded"` and a new DDR is created with a `supersedes` reference. The prior DDR remains queryable in fleet-memory and preserved in `docs/design/decisions/`.**

```python
from guardkit.knowledge.entities.design_decision import DesignDecision
from guardkit.planning.design_writer import DesignWriter, scan_next_ddr_number

writer = DesignWriter()
output_dir = Path("docs/design")

# Get next DDR number
next_ddr = scan_next_ddr_number(output_dir / "decisions")

# Capture refined DDR
print(f"\n{'━' * 60}")
print(f"📝 REFINING DDR: {selected_ddr.entity_id}")
print(f"{'━' * 60}")
print(f"\nCurrent Decision:")
print(f"  Title: {selected_ddr.title}")
print(f"  Decision: {selected_ddr.decision}")
print(f"  Status: {selected_ddr.status}")
print(f"\nWhat has changed?")

new_context = input("Updated context (why is this change needed?): ")
new_decision = input("Updated decision (what is the new decision?): ")
new_rationale = input("Updated rationale (why this choice now?): ")

# Create new DDR with supersedes reference
new_ddr = DesignDecision(
    number=next_ddr,
    title=f"{selected_ddr.title} (revised)",
    context=new_context.strip(),
    decision=new_decision.strip(),
    rationale=new_rationale.strip(),
    alternatives_considered=selected_ddr.alternatives_considered,
    consequences=input("Updated consequences (comma-separated): ").split(","),
    related_components=selected_ddr.related_components,
    status="accepted",
    supersedes=selected_ddr.entity_id,  # Link to prior DDR
)

# Mark existing DDR as superseded
selected_ddr.status = "superseded"

# Write updated DDR files
writer.write_ddr(selected_ddr, output_dir)  # Update old DDR status
writer.write_ddr(new_ddr, output_dir)       # Write new DDR

# Seeding to fleet-memory is deferred to Phase 7 (mcp__fleet_memory__memory_write_payload).
# There, the NEW DDR payload carries a "supersedes" reference to the old DDR's natural key
# (adr:guardkit:DDR_{old}), and the OLD DDR payload is re-written with "status": "superseded".
# Fleet-memory upserts idempotently on the natural key — no separate stale-node tagging.

print(f"\n✓ {selected_ddr.entity_id} → superseded")
print(f"✓ {new_ddr.entity_id} created (supersedes {selected_ddr.entity_id})")
print(f"✓ Prior DDR remains queryable via fleet-memory search (domain_tags=[design])")
```

**Superseding Confirmation:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DDR SUPERSEDING SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Old: DDR-003 "Use CQRS for Order Management" → status: superseded
New: DDR-008 "Use CQRS for Order Management (revised)" → status: accepted
     supersedes: DDR-003

Changes:
  - Context: [diff of context changes]
  - Decision: [diff of decision changes]
  - Rationale: [diff of rationale changes]

[C]onfirm | [R]evise | [C]ancel

Your choice:
```

#### 2B: API Contract Refinement

**When refining an API contract, present the current contract, proposed changes, and a diff. Then regenerate the OpenAPI spec section for the affected bounded context and validate the updated spec.**

```python
from guardkit.knowledge.entities.api_contract import ApiContract

# Load current contract
print(f"\n{'━' * 60}")
print(f"📡 REFINING API CONTRACT: {selected_contract.entity_id}")
print(f"{'━' * 60}")

# Present current contract
print(f"\nCurrent Contract: {selected_contract.bounded_context}")
print(f"Protocol: {selected_contract.protocol}")
print(f"Endpoints:")
for endpoint in selected_contract.endpoints:
    print(f"  {endpoint['method']:6s} {endpoint['path']} — {endpoint.get('description', '')}")

# Capture proposed changes
print(f"\nWhat changes are needed?")
print("  [A]dd endpoint — Add new endpoint(s)")
print("  [M]odify endpoint — Change existing endpoint(s)")
print("  [R]emove endpoint — Remove endpoint(s)")
print("  [S]chema change — Update request/response schemas")

change_type = input("Change type [A/M/R/S]: ")

# Apply changes based on type
updated_contract = apply_contract_changes(selected_contract, change_type)

# Show diff between current and proposed
print(f"\n{'━' * 60}")
print(f"📊 CONTRACT DIFF")
print(f"{'━' * 60}")
display_contract_diff(selected_contract, updated_contract)

# Require confirmation
approval = input("\n[A]pprove changes | [R]evise | [C]ancel: ")
if approval.lower() == "c":
    print("Cancelled.")
    exit(0)

# Write updated contract
writer.write_api_contract(updated_contract, output_dir)

# Regenerate OpenAPI spec section for affected context
print(f"\nRegenerating OpenAPI spec for {updated_contract.bounded_context}...")
regenerate_openapi_section(updated_contract, output_dir / "openapi.yaml")

# Validate updated OpenAPI spec
validate_openapi_spec(output_dir / "openapi.yaml")

# Seeding to fleet-memory is deferred to Phase 7 — the updated contract is written as a
# document payload (domain_tags=["design","api_contract"]), idempotently upserted on its
# natural key (document:guardkit:<contract_slug>).
print(f"✓ {updated_contract.entity_id} written — will re-seed to fleet-memory in Phase 7")
```

#### 2C: Data Model Refinement

```python
from guardkit.knowledge.entities.data_model import DataModel

# Load current data model
print(f"\n{'━' * 60}")
print(f"📊 REFINING DATA MODEL: {selected_model.entity_id}")
print(f"{'━' * 60}")

# Present current model
print(f"\nBounded Context: {selected_model.bounded_context}")
print(f"Entities:")
for entity in selected_model.entities:
    print(f"  • {entity['name']}: {', '.join(entity.get('attributes', []))}")

# Capture changes
print(f"\nWhat changes are needed?")
change_description = input("> ")

# Apply changes interactively
updated_model = apply_model_changes(selected_model, change_description)

# Show diff
display_model_diff(selected_model, updated_model)

# Confirm and persist
approval = input("\n[A]pprove | [R]evise | [C]ancel: ")
if approval.lower() == "a":
    writer.write_data_model(updated_model, output_dir)
    # Seeding to fleet-memory is deferred to Phase 7 — the updated model is written as a
    # document payload (domain_tags=["design","data_model"]), idempotently upserted on its
    # natural key (document:guardkit:<model_slug>).
```

### Phase 3: Contradiction Detection

**Before finalising design changes, check proposed changes against existing ADRs (fleet-memory `payload_types=["adr"]`, `domain_tags=["architecture"]`, or local `docs/architecture/ADR-*.md`). Flag any proposed design change that contradicts existing architecture decisions.**

```python
# Query existing ADRs from fleet-memory (architecture-tagged adr payloads)
if memory_available:
    # mcp__fleet_memory__memory_search(
    #   project="guardkit",
    #   query="architecture decision ADR constraint protocol communication",
    #   payload_types=["adr"],
    #   domain_tags=["architecture"],
    #   token_budget=2000,
    # )
    existing_adrs = memory_search_architecture_adrs()

    # Check proposed changes against existing ADRs
    contradictions = detect_contradictions(
        proposed_changes=get_proposed_changes(),
        existing_adrs=existing_adrs,
    )

    if contradictions:
        print(f"\n{'━' * 60}")
        print(f"⚠️  CONTRADICTION DETECTION: {len(contradictions)} conflict(s) found")
        print(f"{'━' * 60}")
        for c in contradictions:
            print(f"\n  Proposed Change: {c['change']}")
            print(f"  Conflicting ADR: {c['adr']}")
            print(f"  Contradiction: {c['reason']}")

        print(f"\n{'━' * 60}")
        print("Options:")
        print("  [R]evise change — Modify the proposed change to comply with ADR")
        print("  [S]upersede ADR — Create a new ADR superseding the conflicting one")
        print("  [A]ccept risk — Proceed with the contradiction documented")
        choice = input("Your choice [R/S/A]: ")

        if choice.lower() == "r":
            # Return to Phase 2 to revise
            pass
        elif choice.lower() == "s":
            # Capture superseding ADR inline
            capture_superseding_adr(c['adr'])
        elif choice.lower() == "a":
            print("Contradiction accepted and documented.")
    else:
        print("\n✓ No contradictions detected with existing ADRs")
```

### Phase 4: Feature Spec Staleness Detection

**After applying design changes, search fleet-memory for feature-spec artefacts that reference the changed API contracts or domain entities. Flag affected feature specs as potentially stale.**

```python
# Search fleet-memory for feature-spec artefacts referencing changed entities
if memory_available:
    changed_entity_ids = get_changed_entity_ids()  # e.g., ["API-order-management", "DM-order"]

    stale_specs = []
    for entity_id in changed_entity_ids:
        # mcp__fleet_memory__memory_search(
        #   project="guardkit",
        #   query=f"feature spec scenario referencing {entity_id}",
        #   payload_types=["document"],
        #   domain_tags=["feature_spec"],
        #   token_budget=2000,
        # )
        results = memory_search_feature_specs(entity_id)
        if results:
            stale_specs.extend(results)

    if stale_specs:
        print(f"\n{'━' * 60}")
        print(f"⚠️  FEATURE SPEC STALENESS: {len(stale_specs)} potentially stale spec(s)")
        print(f"{'━' * 60}")
        for spec in stale_specs:
            print(f"  • {spec.get('fact', 'Unknown spec')}")

        print(f"\nThese feature specs reference changed API contracts or domain entities.")
        print(f"They may need updating to reflect the design changes.")
        print()
        print("Options:")
        print("  [R]e-run /feature-spec — Regenerate affected feature specs")
        print("  [A]ccept delta — Mark as reviewed, no regeneration needed")
        print("  [S]kip — Defer staleness resolution to later")

        staleness_choice = input("Your choice [R/A/S]: ")
        if staleness_choice.lower() == "r":
            print("Run: /feature-spec --from docs/design/ to regenerate affected specs")
        elif staleness_choice.lower() == "a":
            print("Staleness accepted. Feature specs marked as reviewed.")
    else:
        print("\n✓ No stale feature specs detected")
```

### Phase 5: Downstream Staleness Flagging

**Flag downstream fleet-memory artefacts that depend on the changed design artefacts. This ensures consumers of the design context are aware that upstream changes may affect their assumptions.**

```python
# Flag downstream design artefacts as potentially stale via fleet-memory search
if memory_available:
    changed_entities = get_changed_entity_ids()

    # Search for downstream artefacts referencing changed entities
    for entity_id in changed_entities:
        # mcp__fleet_memory__memory_search(
        #   project="guardkit",
        #   query=f"depends on {entity_id} references {entity_id}",
        #   payload_types=["adr", "document"],
        #   domain_tags=["design"],
        #   token_budget=2000,
        # )
        downstream = memory_search_design(f"depends on {entity_id} references {entity_id}")

        for node in downstream:
            # Flag as potentially stale
            print(f"  ⚠️ Downstream artefact may be stale: {node.get('fact', 'Unknown')}")

    print(f"\n{'━' * 60}")
    print(f"📋 DOWNSTREAM STALENESS SUMMARY")
    print(f"{'━' * 60}")
    print(f"  Changed: {len(changed_entities)} design artefact(s)")
    print(f"  Downstream affected: {len(downstream)} artefact(s) flagged as stale")
    print(f"  Feature specs: {len(stale_specs)} spec(s) flagged as potentially stale")
else:
    print("⚠️ Fleet-memory unavailable — downstream staleness detection skipped")
    print("  Review docs/design/ manually for affected artefacts")
```

### Phase 6: C4 L3 Diagram Re-Review Gate

**If API contract or data model changes affect component structure, generate revised C4 Level 3 Component diagrams. These MUST be presented for mandatory approval before finalising the refinement.**

```python
from guardkit.planning.design_writer import DesignWriter

writer = DesignWriter()

# Determine if C4 L3 diagrams need regeneration
affected_contexts = get_affected_bounded_contexts()

if affected_contexts:
    print(f"\n{'━' * 60}")
    print(f"🔍 C4 COMPONENT DIAGRAM RE-REVIEW")
    print(f"{'━' * 60}")
    print(f"\nDesign changes affect {len(affected_contexts)} bounded context(s).")
    print("Revised Component diagrams require your approval.")

    for bc in affected_contexts:
        # Generate revised C4 L3 diagram
        components = bc.get("internal_components", [])
        writer.write_component_diagram(
            container=bc["name"],
            components=components,
            output_dir=output_dir,
        )

        # Present for mandatory approval
        print(f"\n{'━' * 60}")
        print(f"📊 C4 L3: {bc['name']} (REVISED)")
        print(f"{'━' * 60}")

        # Display Mermaid diagram
        display_component_diagram(bc)

        # Mandatory approval gate — cannot skip
        approval = input("[A]pprove | [R]evise | [R]eject: ")

        if approval.lower() == "a":
            print(f"  ✓ {bc['name']} diagram approved")
        elif approval.lower().startswith("r"):
            if "eject" in approval.lower():
                print(f"  ⚠️ {bc['name']} diagram rejected — excluded from output")
            else:
                changes = input("  What changes are needed? ")
                # Regenerate and re-present
                regenerate_and_review(bc, changes)
```

### Phase 7: Fleet-Memory Seeding

**Seed all updated design artefacts into fleet-memory as typed payloads (see `docs/internals/commands-lib/memory-preamble.md` — Payload Model Reference + Seeding Pattern):**

If `memory_available` is true, build one typed payload per changed artefact, display them, and ask: `"Seed these to fleet-memory now? [Y/n]"`. On yes, if `memory_access = "mcp"`, write each via `mcp__fleet_memory__memory_write_payload`. (If `memory_access = "cli"`, note that writes require the MCP tools connected and skip.)

```
# Superseded DDR(s): re-write the OLD DDR payload with status "superseded"
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr", "project": "guardkit",
  "identifier": "DDR_{old_NNN}",                # underscores only (DDR-003 → DDR_003)
  "decision": "<the original decision>", "status": "superseded",
  "domain_tags": ["design"],
  "source_ref": "docs/design/decisions/DDR-{old_NNN}.md"})

# New DDR(s): write with a "supersedes" reference to the old DDR's natural key
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr", "project": "guardkit",
  "identifier": "DDR_{new_NNN}",
  "decision": "<the revised decision>", "status": "accepted",
  "supersedes": ["adr:guardkit:DDR_{old_NNN}"],
  "domain_tags": ["design"],
  "source_ref": "docs/design/decisions/DDR-{new_NNN}.md"})

# Updated API contract(s) → document payload, domain_tags ["design","api_contract"]
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "document", "project": "guardkit",
  "identifier": "<contract_slug>",              # underscores only
  "content": "<updated contract markdown>",
  "domain_tags": ["design", "api_contract"],
  "source_ref": "docs/design/contracts/<contract-slug>.md"})

# Updated data model(s) → document payload, domain_tags ["design","data_model"]
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "document", "project": "guardkit",
  "identifier": "<model_slug>",
  "content": "<updated data-model markdown>",
  "domain_tags": ["design", "data_model"],
  "source_ref": "docs/design/models/<model-slug>.md"})
```

Fleet-memory upserts idempotently on the derived `natural_key` (e.g. `adr:guardkit:DDR_003`), so re-writing the old DDR with `status: "superseded"` overwrites the prior payload in place — there is no separate stale-node tagging step.

If fleet-memory is unavailable, display the unavailability warning from the preamble:

```
⚠️  Fleet-memory unavailable — artefacts written to markdown only.
    Re-run /design-refine with the fleet_memory MCP server connected to seed the store.
```

### Phase 8: Summary Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DESIGN REFINEMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Changes Applied:
  DDRs:
    • DDR-003 → superseded
    • DDR-008 → created (supersedes DDR-003)

  API Contracts:
    • API-order-management → updated (2 endpoints modified)

  Data Models:
    • DM-order-management → updated (1 entity added)

Quality Checks:
  ✓ OpenAPI spec validated
  ✓ C4 L3 diagrams approved
  ✓ No contradictions with existing ADRs
  ⚠️ 2 feature specs flagged as potentially stale

Fleet-memory:
  ✓ 3 design artefacts seeded (adr/document, domain_tags=[design])
  ✓ 1 API contract seeded (document, domain_tags=[design,api_contract])

Updated: docs/design/
  ├── openapi.yaml (regenerated)
  ├── contracts/
  │   └── API-order-management.md (updated)
  ├── models/
  │   └── DM-order-management.md (updated)
  ├── diagrams/
  │   └── order-management.md (C4 L3 revised)
  └── decisions/
      ├── DDR-003.md (status: superseded)
      └── DDR-008.md (new, supersedes DDR-003)

Next steps:
  1. Review stale feature specs: /feature-spec --from docs/design/
  2. Continue refining: /design-refine "description"
  3. Plan features: /feature-plan "feature description"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Graceful Degradation

### Fleet-Memory Unavailable

When `memory_available = false`, display the unavailability warning from `docs/internals/commands-lib/memory-preamble.md`:

```
⚠️  Fleet-memory unavailable — continuing without knowledge capture.
    Reason: MCP tools not connected and CLI not reachable

    Artefacts are written to markdown only. Re-run with the fleet_memory
    MCP server connected (see .mcp.json) to seed the knowledge store.
```

Then inform the user of the specific limitations for design refinement:
- Disambiguation uses local file scanning (less accurate)
- Feature spec staleness detection skipped
- Downstream staleness flagging skipped
- Contradiction detection limited to local ADR files
- Changes won't be queryable by `/feature-spec`, `/feature-plan`, or `/system-plan`

Ask: "Continue without persistence? [Y/n]"

If no: display "Cancelled." and stop. Do not block if no input — default to continue.

### Partial Seeding Failure

```python
# Track successful writes
seeded_count = 0
failed_writes = []

for artefact in all_changed_artefacts:
    try:
        # mcp__fleet_memory__memory_write_payload(payload={...})
        natural_key = memory_write_payload(build_payload(artefact))
        if natural_key:
            seeded_count += 1
        else:
            failed_writes.append(artefact.entity_id)
    except Exception as e:
        print(f"WARNING: Fleet-memory error seeding {artefact.entity_id}: {e}")
        failed_writes.append(artefact.entity_id)

if failed_writes:
    print(f"⚠️ {len(failed_writes)} artefact(s) failed to seed to fleet-memory:")
    for entity_id in failed_writes:
        print(f"  ✗ {entity_id}")
    print()
    print("Markdown artefacts are still up to date.")
    print("Re-run /design-refine with the fleet_memory MCP server connected to retry.")
```

## Error Handling

### No Design Context

```python
if not has_design_context:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("❌ No design context found")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("/design-refine requires design context from /system-design.")
    print("The design defines API contracts, data models, and DDRs")
    print("that /design-refine iterates upon.")
    print()
    print("Run /system-design first to establish design context.")
    exit(0)
```

### No Description Provided

```python
if not description or not description.strip():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("ERROR: Refinement description is required")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("Usage: /design-refine \"description of what to refine\"")
    print()
    print("Examples:")
    print('  /design-refine "update order endpoint to include pagination"')
    print('  /design-refine "change payment flow from sync to async"')
    print('  /design-refine "add audit trail to compliance context"')
    exit(1)
```

### No Matches Found

```python
if not search_results:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️ No matching design artefacts found")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"No DDRs, API contracts, or data models matched: \"{description}\"")
    print()
    print("Suggestions:")
    print("  • Try a more specific description")
    print("  • Run /system-design to create design artefacts first")
    print("  • Check docs/design/ for available artefacts")
    exit(0)
```

### --no-questions Flag

```python
if flags.get("no_questions"):
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("ERROR: /design-refine requires interactive input")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("The --no-questions flag is not supported for /design-refine.")
    print("Design refinement decisions require human input and review.")
    exit(1)
```

### Fleet-Memory Unavailable Mid-Session

```python
try:
    # mcp__fleet_memory__memory_write_payload(payload=build_ddr_payload(new_ddr))
    memory_write_payload(build_ddr_payload(new_ddr))
except ConnectionError:
    print("WARNING: Fleet-memory connection lost during session")
    print("Remaining artefacts will be updated in markdown only.")
    print("Re-run /design-refine with the fleet_memory MCP server connected to retry.")
    memory_available = False  # Disable further fleet-memory writes
    # Continue with markdown-only updates
```

### Cancelled / Partial Session

```python
if user_cancelled:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚠️ Refinement cancelled")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("No changes have been applied.")
    print("Design artefacts remain unchanged.")
    print()
    print("Run /design-refine again to start a new refinement session.")
    exit(0)
```

### OpenAPI Validation Failure

```python
import subprocess

openapi_path = output_dir / "openapi.yaml"

if openapi_path.exists():
    result = subprocess.run(
        ["python", "-m", "openapi_spec_validator", str(openapi_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("  ✓ Updated OpenAPI specification valid")
    else:
        print(f"  ⚠️ OpenAPI validation failed:")
        print(f"    {result.stderr}")
        print()
        print("  Attempting to fix validation errors...")

        # Attempt fix: re-generate with errors as context
        for attempt in range(2):
            openapi_spec = fix_openapi_spec(openapi_spec, result.stderr)
            openapi_path.write_text(openapi_spec)

            result = subprocess.run(
                ["python", "-m", "openapi_spec_validator", str(openapi_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"  ✓ OpenAPI specification valid (fixed on attempt {attempt + 1})")
                break
        else:
            print("  ❌ OpenAPI validation failed after 2 fix attempts")
            print("  Manual review required: docs/design/openapi.yaml")
```

## Flag Handling

### --focus

```python
focus_context = flags.get("focus")
if focus_context:
    # Narrow search to specific bounded context
    search_results = [
        r for r in search_results
        if focus_context.lower() in r.get("fact", "").lower()
    ]

    if not search_results:
        print(f"❌ No design artefacts found for context '{focus_context}'")
        print("Available contexts can be found in docs/design/contracts/")
        exit(1)

    print(f"📌 Focused on bounded context: {focus_context}")
```

### --context

```python
context_files = flags.get("context", [])
for context_file in context_files:
    with open(context_file) as f:
        additional_context = f.read()
    print(f"✓ Loaded context from {context_file}")
```

## Examples

### Example 1: Refine a DDR (Temporal Superseding)

```bash
/design-refine "change order processing from synchronous to event-driven"

Design context loaded:
  5 design decisions (DDRs)
  8 API contracts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 DISAMBIGUATION: Matching design artefacts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your input: "change order processing from synchronous to event-driven"

Found 3 matches (grouped by relevance):

  DDRs:
    1. [DDR-003] Synchronous order processing (score: 0.91)

  API Contracts:
    2. [API-order-management] Order Management REST API (score: 0.85)

  Data Models:
    3. [DM-order-management] Order domain model (score: 0.72)

Which artefact do you want to refine?
> 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 REFINING DDR: DDR-003
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Decision:
  Title: Synchronous order processing
  Decision: Use synchronous HTTP calls for order processing pipeline
  Status: accepted

What has changed?
  Updated context: Load testing revealed synchronous processing creates bottleneck
  Updated decision: Use event-driven processing with domain events
  Updated rationale: Event-driven approach handles 10x throughput

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DDR SUPERSEDING SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Old: DDR-003 → status: superseded
New: DDR-006 → status: accepted (supersedes DDR-003)

[C]onfirm | [R]evise | [C]ancel
> C

⚠️ CONTRADICTION DETECTION: 1 conflict found
  Proposed Change: Event-driven order processing
  Conflicting ADR: ADR-ARCH-005 "Synchronous inter-service communication"
  Contradiction: Event-driven pattern conflicts with synchronous ADR

  [R]evise | [S]upersede ADR | [A]ccept risk
  > S
  [Capture superseding ADR...]

✓ No stale feature specs detected
✓ C4 L3 diagram approved

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DESIGN REFINEMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example 2: Refine an API Contract

```bash
/design-refine "add pagination to order listing endpoint" --focus="Order Management"

📌 Focused on bounded context: Order Management

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 REFINING API CONTRACT: API-order-management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Contract: Order Management
Protocol: REST
Endpoints:
  POST   /api/v1/orders          — Create order
  GET    /api/v1/orders/{id}     — Get order by ID
  GET    /api/v1/orders          — List orders
  PATCH  /api/v1/orders/{id}     — Update status
  DELETE /api/v1/orders/{id}     — Cancel order

Change type [A/M/R/S]: M

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 CONTRACT DIFF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  GET /api/v1/orders — List orders
  - Query params: (none)
  + Query params: page (int), page_size (int, default=20), sort_by (string)
  + Response: Added pagination metadata (total, page, page_size, total_pages)

[A]pprove changes | [R]evise | [C]ancel
> A

Regenerating OpenAPI spec for Order Management...
  ✓ Updated OpenAPI specification valid

⚠️ FEATURE SPEC STALENESS: 1 potentially stale spec
  • "Order listing scenario" references GET /api/v1/orders

  [R]e-run /feature-spec | [A]ccept delta | [S]kip
  > A

✓ C4 L3 diagram — no structural changes, review skipped

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DESIGN REFINEMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example 3: Fleet-Memory Unavailable (Degraded Mode)

```bash
/design-refine "update payment schema"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WARNING: Fleet-memory unavailable
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Design refinement will continue WITHOUT persistence.
Markdown artefacts will be updated, but changes won't be
queryable by /feature-spec, /feature-plan, or /system-plan.

Continue without persistence? [Y/n]: Y

[Disambiguation using local file scanning...]
[Changes applied to markdown files only...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DESIGN REFINEMENT COMPLETE (degraded mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Changes NOT synced to fleet-memory
  Re-run with the fleet_memory MCP server connected to persist changes
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**IMPORTANT: YOU MUST FOLLOW THESE STEPS EXACTLY. THIS IS AN INTERACTIVE DESIGN REFINEMENT COMMAND.**

When the user runs `/design-refine "description"`, you MUST execute these steps in order:

### Step 1: Parse Arguments

```python
# Extract description and flags
description = args[0]  # Required — error if missing
focus = flags.get("focus", None)
no_questions = flags.get("no_questions", False)
defaults = flags.get("defaults", False)
context_files = flags.get("context", [])

# Validate description
if not description or not description.strip():
    print("ERROR: Refinement description is required")
    print('Usage: /design-refine "description of what to refine"')
    exit(1)

# Reject --no-questions
if no_questions:
    print("ERROR: /design-refine requires interactive input")
    exit(1)
```

### Step 2: Check Fleet-Memory and Verify Prerequisite

**Check fleet-memory availability** (see `docs/internals/commands-lib/memory-preamble.md` Tier 0 → Tier 1):

Check for the `mcp__fleet_memory__*` tools; else run `guardkit memory status`. Set `memory_available` (and `memory_access`) accordingly. If neither is reachable, set `memory_available = false` — never block.

Check for design context (either source satisfies the gate):
- If `memory_available = true`: search fleet-memory for design context — `mcp__fleet_memory__memory_search(project="guardkit", query="design decisions API contracts data models", payload_types=["adr","document"], domain_tags=["design"])`. A non-empty result = context exists.
- Always: use Glob to check for `docs/design/*.md`.
  - If no local files AND fleet-memory has no design context: display `"❌ No design context found"` and exit
  - If local files exist: display the unavailability warning from the preamble (when `memory_available = false`) and ask: "Continue? [Y/n]"

### Step 3: Disambiguation

```python
# Semantic search for matching design artefacts
if memory_available:
    # mcp__fleet_memory__memory_search(project="guardkit", query=description,
    #   payload_types=["adr", "document"], domain_tags=["design"], token_budget=2000)
    results = memory_search_design(description)
else:
    results = scan_local_design_files(description)

# Present top 3-5 matches grouped by relevance
# Require explicit confirmation before proceeding
```

### Step 4: Apply Refinement

Based on selected artefact type:
- **DDR**: Temporal superseding (set old → superseded, create new with `supersedes` reference)
- **API Contract**: Present current, proposed changes, diff. Regenerate and validate OpenAPI spec.
- **Data Model**: Present current, proposed changes, diff. Update model file.

### Step 5: Contradiction Detection

```python
# Search fleet-memory for existing ADRs (payload_types=["adr"], domain_tags=["architecture"])
# Compare proposed changes against ADR constraints
# Flag contradictions and offer: [R]evise / [S]upersede / [A]ccept risk
```

### Step 6: Feature Spec Staleness Detection

```python
# Search fleet-memory for feature-spec artefacts referencing changed entities
#   (payload_types=["document"], domain_tags=["feature_spec"])
# Flag affected specs as potentially stale
# Offer: [R]e-run /feature-spec / [A]ccept delta / [S]kip
```

### Step 7: Downstream Staleness Flagging

```python
# Search fleet-memory for downstream artefacts referencing changed entities
#   (payload_types=["adr", "document"], domain_tags=["design"])
# Flag affected artefacts as stale
# Report summary of downstream impact
```

### Step 8: C4 L3 Re-Review Gate (Mandatory)

```python
# If changes affect component structure:
#   Generate revised C4 L3 diagrams
#   Present for mandatory approval: [A]pprove / [R]evise / [R]eject
#   DO NOT proceed without approval
```

### Step 9: Fleet-Memory Seeding

**Seed fleet-memory** (if `memory_available` is true):

Build one typed payload per changed artefact (see `docs/internals/commands-lib/memory-preamble.md` — Payload Model Reference + Seeding Pattern):

```
# Superseded DDR → re-write with status "superseded"
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr", "project": "guardkit", "identifier": "DDR_{old_NNN}",
  "decision": "<original decision>", "status": "superseded", "domain_tags": ["design"],
  "source_ref": "docs/design/decisions/DDR-{old_NNN}.md"})

# New DDR → write with a supersedes reference to the old DDR's natural key
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "adr", "project": "guardkit", "identifier": "DDR_{new_NNN}",
  "decision": "<revised decision>", "status": "accepted",
  "supersedes": ["adr:guardkit:DDR_{old_NNN}"], "domain_tags": ["design"],
  "source_ref": "docs/design/decisions/DDR-{new_NNN}.md"})

# Changed API contract → document / ["design","api_contract"]
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "document", "project": "guardkit", "identifier": "<contract_slug>",
  "content": "<updated contract markdown>", "domain_tags": ["design", "api_contract"],
  "source_ref": "docs/design/contracts/<contract-slug>.md"})

# Changed data model → document / ["design","data_model"]
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "document", "project": "guardkit", "identifier": "<model_slug>",
  "content": "<updated data-model markdown>", "domain_tags": ["design", "data_model"],
  "source_ref": "docs/design/models/<model-slug>.md"})
```

Ask: "Seed these to fleet-memory now? [Y/n]"

If yes and `memory_access = "mcp"`, write each via the MCP tool. If `memory_access = "cli"`, note writes need the MCP tools connected and skip. Fleet-memory upserts idempotently on each `natural_key`, so re-seeding is safe.

### Step 10: Summary

Display file tree, fleet-memory status, staleness summary, and next steps.

### What NOT to Do

DO NOT:
- Skip the disambiguation phase — always identify the target before changing it
- Apply changes without explicit user confirmation
- Skip the C4 L3 review gate — diagrams require mandatory approval
- Skip contradiction detection — always check against existing ADRs
- Skip feature spec staleness detection — always check for stale specs
- Delete superseded DDRs — they must remain queryable
- Batch all fleet-memory writes at the end — write DDRs immediately
- Seed fleet-memory via Python — always use the `mcp__fleet_memory__memory_write_payload` tool
- Generate code implementations — this is a design command
- Skip the prerequisite gate — always verify design context exists
- Silently swallow fleet-memory errors — always inform the user
- Proceed without user confirmation at decision points
- Auto-answer disambiguation — always present options and wait for user selection

### Example Execution Trace

```
User: /design-refine "add rate limiting to payment API"

Claude executes:
  1. Parse arguments → description = "add rate limiting to payment API"
  2. Check fleet-memory availability → mcp__fleet_memory__* tools else `guardkit memory status`, verify design context
  3. Disambiguation → mcp__fleet_memory__memory_search("add rate limiting to payment API", domain_tags=["design"])
  4. Present top 3-5 matches → user selects API-payment-processing
  5. API Contract refinement → present current, capture changes, show diff
  6. Confirm changes → user approves
  7. Contradiction detection → search fleet-memory ADRs (domain_tags=["architecture"])
  8. Feature spec staleness → search fleet-memory feature-spec artefacts for affected scenarios
  9. Downstream staleness → flag dependent fleet-memory artefacts
  10. C4 L3 re-review → present revised diagram if structure changed
  11. Fleet-memory seeding → write updated contract via mcp__fleet_memory__memory_write_payload
  12. OpenAPI validation → validate updated spec
  13. Summary → display changes, staleness, next steps
```

Remember: This is an **interactive design refinement command**. You MUST present disambiguation results, wait for user selection, show diffs, require confirmations, and present C4 diagrams for approval. DO NOT try to auto-complete the flow or make decisions on behalf of the user.

---

## Message Constants

```python
NO_DESIGN_CONTEXT_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ No design context found
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/design-refine requires design context from /system-design.
The design defines API contracts, data models, and DDRs
that /design-refine iterates upon.

Run /system-design first to establish design context.
"""

MEMORY_UNAVAILABLE_MESSAGE:
Use the warning template from `docs/internals/commands-lib/memory-preamble.md`. Additional context for design refinement:
- Changes won't be queryable by /feature-spec, /feature-plan, or /system-plan
- Feature spec staleness detection skipped
- Downstream staleness flagging skipped

SESSION_CANCELLED_MESSAGE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Refinement cancelled
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

No changes have been applied.
Design artefacts remain unchanged.

Run /design-refine again to start a new refinement session.
"""
```

---

## Related Commands

- `/system-arch` — Establish structural architecture (upstream of design pipeline)
- `/system-design` — Create design artefacts from scratch (prerequisite for `/design-refine`)
- `/arch-refine` — Refine architecture decisions (shares disambiguation flow pattern)
- `/feature-spec` — Generate BDD specifications grounded in design artefacts
- `/feature-plan` — Plan feature implementation using design and architecture context
- `/system-plan` — System-level planning that consumes design context
