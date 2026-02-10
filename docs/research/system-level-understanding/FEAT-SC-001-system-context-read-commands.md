# Feature: System Context Read Commands

> **Feature ID**: FEAT-SC-001
> **Priority**: P0 (completes system-level command hierarchy with /system-plan)
> **Estimated Effort**: 2-3 days
> **Dependencies**: FEAT-SP-001 (/system-plan — defines data these commands read)

---

## Summary

Add three read-only commands that consume the architecture knowledge `/system-plan` produces: `/system-overview`, `/impact-analysis`, and `/context-switch`. These commands close the feedback loop between planning and execution — where `/system-plan` writes architecture context, these commands make it accessible during task workflows, AutoBuild sessions, and multi-project navigation.

Together with `/system-plan`, they complete the system-level command tier:

```
/system-plan       → Interactive, writes to Graphiti    (planning sessions)
/system-overview   → Read-only, queries Graphiti        (quick reference)
/impact-analysis   → Read-only, queries Graphiti        (pre-task validation)
/context-switch    → Read-only, loads project context    (multi-project navigation)
```

---

## Current State

- **No way to query architecture at a glance** — developers must manually read `docs/architecture/*.md` files, which is slow and disconnects them from Graphiti's queryable knowledge
- **No pre-task impact assessment** — tasks start without understanding what components, ADRs, or BDD scenarios they might affect, leading to the "locally correct but globally wrong" problem
- **Multi-project switching is entirely manual** — switching context between GuardKit, RequireKit, and future projects (PoA platform, Reachy) requires the developer to mentally reload everything
- **AutoBuild coach has no architectural anchoring** — the coach validates individual tasks but lacks system-level context to catch architectural violations
- **TASK-REV-1505 identified 5 of 11 context loss scenarios** unaddressed by current design; these commands address the "no big-picture context" and "multi-project cognitive overload" gaps

### What FEAT-SP-001 Provides

The completed `/system-plan` spec (FEAT-SP-001) establishes:

- **Graphiti groups**: `{project}__project_architecture` and `{project}__project_decisions`
- **Entity types**: `SystemContextDef`, `ComponentDef`, `CrosscuttingConcernDef`, `ArchitectureDecision`
- **Read operations on `SystemPlanGraphiti`**: `has_architecture_context()`, `get_architecture_summary()`, `get_relevant_context_for_topic()`
- **Markdown artefacts**: `docs/architecture/ARCHITECTURE.md`, `system-context.md`, `components.md` (or `bounded-contexts.md`), `crosscutting-concerns.md`, `decisions/ADR-NNN-*.md`
- **Complexity gating**: `get_arch_token_budget()` returns tiered budgets (0/1000/2000/3000 tokens) based on task complexity

These read commands build directly on this infrastructure. No new Graphiti write operations are needed.

### New Graphiti Group: `bdd_scenarios` (Project-Scoped)

The `/impact-analysis` deep mode introduces a dependency on a `bdd_scenarios` project group that does not yet exist. This group must be registered in `graphiti_client.py`'s project groups list during implementation:

```python
# Add to known project groups in graphiti_client.py
PROJECT_GROUPS = [
    "project_overview",
    "project_architecture",
    "feature_specs",
    "project_decisions",
    "project_constraints",
    "domain_knowledge",
    "bdd_scenarios",        # NEW: Added by FEAT-SC-001
]
```

**Population**: BDD scenarios would be seeded from `.feature` files in the project's test directories, or captured during `/system-plan` sessions that include BDD workflow documentation. The seeding mechanism is out of scope for this spec — deep mode gracefully degrades when the group is empty or missing (falls back to standard depth).

> **Seeding pattern**: Following the Graphiti architecture's established pattern (see
> [Graphiti Architecture](https://guardkit.ai/architecture/graphiti-architecture/) §Knowledge Categories),
> new groups require: (1) a `seed_bdd_scenarios.py` module under `guardkit/knowledge/seeding/`,
> (2) registration in the `seeding.py` orchestrator, and (3) the group name added to the
> `PROJECT_GROUPS` list in `graphiti_client.py`. The existing 18 knowledge categories
> provide concrete examples of this pattern.

> **Note**: The previously listed dependency on Spec 3 (FEAT-GE-001) for `role_constraints`, `quality_gate_configs`, and `turn_states` has been removed — the Graphiti technical reference confirms all three entities already exist with full implementations, seeding, and operations modules.

---

## Commands

### /system-overview

A concise, one-screen summary of the current project's architecture context. Designed to be the "remind me where I am" command — fast, always available, and small enough to inject into AutoBuild coach context.

#### Arguments and Syntax

```bash
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--verbose` | No | Show extended detail (multi-page output with full component descriptions) |
| `--section=SECTION` | No | Show only a specific section: `components`, `decisions`, `crosscutting`, `stack`, `all` |
| `--format=FORMAT` | No | Output format: `display` (default, terminal-formatted), `markdown` (raw markdown), `json` (structured data) |

No positional arguments — `/system-overview` always operates on the current project context.

#### Output Format (Default: display)

The default display targets a single screen (~40-60 lines) with information density prioritised over verbosity:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SYSTEM OVERVIEW: Power of Attorney Platform
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Methodology: Domain-Driven Design
Last updated: 2026-02-07 (2 days ago)

BOUNDED CONTEXTS (4)
  Attorney Management    — donor/attorney relationships, LPA lifecycle
  Document Generation    — LPA forms, instructions, preferences
  Financial Oversight    — Moneyhub integration, transaction monitoring
  Compliance             — OPG registration, identity verification

KEY DECISIONS (3 active, 1 superseded)
  ADR-001 ✅ Use anti-corruption layer for Moneyhub API
  ADR-002 ✅ Event-driven communication between contexts
  ADR-003 ✅ Comprehensive audit trail for all mutations
  ADR-004 ⛔ [Superseded by ADR-002] REST for inter-service comms

CROSS-CUTTING CONCERNS (4)
  Authentication    — GOV.UK Verify integration, role-based access
  Audit Logging     — All mutations logged with actor and timestamp
  Error Handling    — Domain exception hierarchy per context
  Data Protection   — GDPR compliance, data residency (UK)

TECH STACK
  Backend: .NET 8 / C# | Frontend: React | Database: PostgreSQL
  Infrastructure: AWS (ECS Fargate) | External: Moneyhub, OPG, GOV.UK Verify

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 /impact-analysis TASK-XXX — assess task impact against this architecture
   /system-plan "topic"     — update or refine architecture
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Verbose mode** (`--verbose`) expands each section with full component descriptions, ADR context/consequences, and concern detail. Target: 2-3 screens.

**Section filter** (`--section=decisions`) shows only that section, useful for quick reference during implementation.

#### Graphiti Queries

```python
async def get_system_overview(
    sp: SystemPlanGraphiti,
    verbose: bool = False,
) -> dict:
    """
    Assemble system overview from Graphiti architecture context.

    Queries:
      1. project_architecture group for components, system context, crosscutting
      2. project_decisions group for ADRs
      3. project_overview group for tech stack (if available)

    Returns structured dict for formatting by display layer.

    Note: Uses sp.get_architecture_summary() which returns semantic facts
    from Graphiti. Entity type is inferred by parsing the fact `name` field
    (e.g. "Component: Attorney Management") and fact content via heuristic
    keyword matching — search() results do not include an explicit
    entity_type field. The _extract_entity_type() helper uses name prefixes
    and content patterns to classify facts.
    """
    # Primary: architecture summary (components + system context)
    summary = await sp.get_architecture_summary()

    if not summary or not summary.get("facts"):
        return {"status": "no_context"}

    # Parse facts into structured sections
    # Note: Graphiti search returns semantic facts, not structured JSON.
    # Each fact has: uuid, fact (text), name, created_at, valid_at, score.
    # Entity type is inferred from the episode name prefix and fact content
    # using heuristic pattern matching (e.g. "Component:" prefix, "ADR-" prefix,
    # keywords like "cross-cutting" or "concern").
    components = []
    decisions = []
    concerns = []
    system_ctx = None

    for fact in summary["facts"]:
        fact_text = fact.get("fact", "")
        entity_type = _extract_entity_type(fact)  # Infers from name/fact content

        if entity_type == "component":
            components.append(_parse_component_fact(fact, verbose))
        elif entity_type == "architecture_decision":
            decisions.append(_parse_decision_fact(fact, verbose))
        elif entity_type == "crosscutting_concern":
            concerns.append(_parse_concern_fact(fact, verbose))
        elif entity_type == "system_context":
            system_ctx = _parse_system_context_fact(fact)

    return {
        "status": "ok",
        "system": system_ctx,
        "components": components,
        "decisions": decisions,
        "concerns": concerns,
    }
```

#### Token Budget

| Context | Budget | Rationale |
|---------|--------|-----------|
| Manual invocation | Unlimited (displays to terminal) | User is actively reading |
| AutoBuild coach injection | 800 tokens max | Must fit within coach's total ~4000 token context budget |
| `/feature-plan` context | 600 tokens max | Alongside feature spec and pattern context |

For automated injection, the overview is condensed to a structured summary:

```python
def condense_for_injection(overview: dict, max_tokens: int = 800) -> str:
    """
    Produce a token-budgeted summary for injection into coach/feature-plan context.

    Priority order (stop when budget exhausted):
      1. Methodology + component names (always included, ~100 tokens)
      2. Active ADR titles (high priority, ~150 tokens)
      3. Cross-cutting concern names (medium priority, ~100 tokens)
      4. Component descriptions (if budget remains)
      5. ADR context/consequences (if budget remains)
    """
```

---

### /impact-analysis

Pre-task validation that cross-references a specific task (or topic) against the known architecture. Answers the question: "what does this task touch, and what constraints apply?"

#### Arguments and Syntax

```bash
/impact-analysis TASK-XXX [--depth=DEPTH] [--include-bdd] [--include-tasks]
/impact-analysis "topic description" [--depth=DEPTH] [--include-bdd] [--include-tasks]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `TASK-XXX` or `"topic"` | Yes | Task ID to analyse, or a free-text topic description for ad-hoc analysis |
| `--depth=DEPTH` | No | Analysis depth: `quick` (components only), `standard` (default — components + ADRs + risk), `deep` (all including BDD and related tasks) |
| `--include-bdd` | No | Include BDD scenario impact (automatically included in `deep` depth) |
| `--include-tasks` | No | Include related task status (automatically included in `deep` depth) |

**Design Decision**: Accept both task IDs and free-text topics. When given a task ID, the command reads the task file for title, description, and tags to build a richer semantic query. When given a topic string, it uses that directly. This supports both structured workflow usage (`/impact-analysis TASK-AUTH-003`) and exploratory usage (`/impact-analysis "add WebSocket support"`).

#### Analysis Depth Tiers

**Quick** (~5 seconds, minimal tokens):
- Affected components/bounded contexts
- Brief risk indication (low/medium/high based on number of affected components)

**Standard** (default, ~10 seconds):
- Affected components with explanation of why each is affected
- Constraining ADRs that apply to this work
- Risk assessment score (1-5) with rationale
- Suggested approach based on architectural constraints

**Deep** (~20 seconds, comprehensive):
- Everything in Standard, plus:
- BDD scenarios that might be affected (queries `{project}__bdd_scenarios`)
- Related tasks in the same feature (completed, in-progress, pending)
- Dependency chain analysis (what depends on affected components)
- Recommended review areas for the coach

#### Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 IMPACT ANALYSIS: TASK-AUTH-003 — Add MFA to attorney login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RISK: ██████░░░░ 3/5 (Medium)
  Touches 2 bounded contexts, conflicts with 1 ADR

AFFECTED COMPONENTS
  ⚠️ Attorney Management
     Authentication flow changes affect donor/attorney login paths
     Entry points: AuthController, LoginService
  ⚠️ Compliance
     MFA adds a new verification step to identity assurance chain
     Entry points: IdentityVerificationService

CONSTRAINING ADRs
  ⚠️ ADR-001: Anti-corruption layer for Moneyhub
     → MFA tokens must not leak into Moneyhub integration layer
  ℹ️ ADR-003: Comprehensive audit trail
     → MFA events (setup, verify, fail) must be audited

ARCHITECTURAL IMPLICATIONS
  • New shared concern: MFA Provider abstraction (TOTP, SMS, WebAuthn)
  • Cross-cutting: Session management needs MFA state tracking
  • Consider: Should MFA be its own module or part of Attorney Management?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Options:
  [P]roceed — Continue to task-work with this context loaded
  [R]eview  — Deep dive into a specific area
  [S]ystem-plan — Update architecture to account for MFA
  [C]ancel  — Stop here

Your choice:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Deep mode additions** (when `--depth=deep` or `--include-bdd`):

```
BDD SCENARIOS AT RISK (3)
  ⚠️ attorney_login.feature:12 — "Attorney can log in with valid credentials"
     → Login flow is changing; scenario may need MFA step added
  ⚠️ attorney_login.feature:24 — "Expired session redirects to login"
     → Session management affected by MFA state
  ℹ️ compliance_audit.feature:8 — "All authentication events are audited"
     → Should already cover MFA if audit trail is comprehensive

RELATED TASKS
  ✅ TASK-AUTH-001 — Set up authentication infrastructure (completed)
  🔄 TASK-AUTH-002 — Implement OAuth2 provider (in progress)
  📋 TASK-AUTH-004 — Session management hardening (pending, depends on this task)
```

#### Graphiti Queries

```python
from guardkit.knowledge import ADRService, ADRStatus

async def run_impact_analysis(
    sp: SystemPlanGraphiti,
    client: GraphitiClient,
    task_or_topic: str,
    depth: str = "standard",
    include_bdd: bool = False,
    include_tasks: bool = False,
) -> dict:
    """
    Cross-reference a task/topic against architecture knowledge.

    Query strategy:
      1. Semantic search against project_architecture for affected components
      2. Semantic search against project_decisions for constraining ADRs
      3. (if deep/include_bdd) Search bdd_scenarios for at-risk scenarios
      4. (if deep/include_tasks) Search feature_specs for related tasks

    Risk scoring:
      - 1 (Low):    0-1 components affected, no ADR conflicts
      - 2 (Low-Med): 1 component, informational ADR references
      - 3 (Medium):  2 components, or 1 ADR constraint
      - 4 (Med-High): 3+ components, or ADR conflict requiring resolution
      - 5 (High):    Multiple ADR conflicts, cross-cutting concern implications

    Content fidelity note: Graphiti search() returns semantic facts extracted
    by the LLM pipeline, not the original structured JSON episode bodies.
    The _parse_*_hits() functions use heuristic pattern matching (keyword
    extraction, name prefix parsing) to classify and structure the returned
    fact strings. This is consistent with how JobContextRetriever already
    processes search results elsewhere in GuardKit.
    """
    # Build query from task content or topic string
    query = await _build_query(task_or_topic)

    # Step 1: Find affected components
    # project_architecture is a registered project group — auto-prefixed
    arch_group = client.get_group_id("project_architecture")
    component_hits = await client.search(
        query=query,
        group_ids=[arch_group],
        num_results=10,
    )

    # Step 2: Find constraining ADRs
    # Uses the existing ADRService (guardkit/knowledge/adr_service.py) which
    # provides structured search with status filtering and significance scoring.
    # See Graphiti Architecture docs: https://guardkit.ai/architecture/graphiti-architecture/
    adr_service = ADRService(client, significance_threshold=0.4)
    adr_hits = await adr_service.search_adrs(
        query=query,
        status=ADRStatus.ACCEPTED,  # Only active decisions constrain
    )

    # Step 3 (optional): Find at-risk BDD scenarios
    # IMPORTANT: bdd_scenarios is NOT a registered project group.
    # This spec introduces it as a new project group — it must be registered
    # in graphiti_client.py's project groups list during implementation.
    # Until registered, explicit scope="project" is required.
    bdd_hits = []
    if depth == "deep" or include_bdd:
        bdd_group = client.get_group_id("bdd_scenarios", scope="project")
        bdd_hits = await client.search(
            query=query,
            group_ids=[bdd_group],
            num_results=10,
        )

    # Step 4 (optional): Find related tasks
    # feature_specs is a registered project group — auto-prefixed
    related_tasks = []
    if depth == "deep" or include_tasks:
        feature_group = client.get_group_id("feature_specs")
        related_tasks = await client.search(
            query=query,
            group_ids=[feature_group],
            num_results=5,
        )

    # Calculate risk score
    risk = _calculate_risk(component_hits, adr_hits, bdd_hits)

    return {
        "query": query,
        "risk": risk,
        "components": _parse_component_hits(component_hits),
        "adrs": _parse_adr_hits(adr_hits),
        "bdd_scenarios": _parse_bdd_hits(bdd_hits),
        "related_tasks": related_tasks,
        "implications": _derive_implications(component_hits, adr_hits),
    }
```

**Risk calculation heuristic**:

```python
def _calculate_risk(
    components: list,
    adrs: list,
    bdd_scenarios: list,
) -> dict:
    """
    Calculate risk score (1-5) from impact analysis results.

    Input format: Each list contains dicts parsed from Graphiti search()
    results by _parse_*_hits() functions. These are heuristically
    structured from semantic fact strings — fields like "conflict" on
    ADRs are inferred from fact content, not from Graphiti's API.

    Factors:
      - Number of affected components (each adds ~0.5)
      - ADR conflicts vs informational references (conflicts add 1.0 each)
      - Number of at-risk BDD scenarios (each adds ~0.3)

    Score is clamped to 1-5 range and rounded to nearest integer.
    """
    score = 1.0

    # Components: 0.5 per affected component beyond the first
    # Note: search() returns "score" (0.0-1.0) for relevance ranking
    num_components = len([c for c in components if c.get("score", 0) > 0.5])
    score += max(0, (num_components - 1)) * 0.5

    # ADRs: 1.0 for conflicts, 0.25 for informational
    # Note: "conflict" is inferred by _parse_adr_hits() from fact content
    # (e.g. keywords like "conflicts with", "violates", "superseded by")
    # not from a structured field in search results.
    for adr in adrs:
        if adr.get("conflict"):
            score += 1.0
        else:
            score += 0.25

    # BDD: 0.3 per at-risk scenario
    score += len(bdd_scenarios) * 0.3

    risk_score = max(1, min(5, round(score)))
    risk_labels = {1: "Low", 2: "Low-Medium", 3: "Medium", 4: "Medium-High", 5: "High"}

    return {
        "score": risk_score,
        "label": risk_labels[risk_score],
        "rationale": _build_risk_rationale(num_components, adrs, bdd_scenarios),
    }
```

#### Token Budget

| Context | Budget | Rationale |
|---------|--------|-----------|
| Manual invocation | Unlimited (displays to terminal) | User is actively reading |
| AutoBuild coach injection | 1200 tokens max | Task-specific context is highest value for coach |
| Pre-task-work preflight | 600 tokens max | Condensed summary before implementation starts |

#### Decision Checkpoint

The impact analysis includes an interactive decision checkpoint:

| Option | Action |
|--------|--------|
| `[P]roceed` | Continue to `/task-work` with impact context pre-loaded in session |
| `[R]eview` | Prompt for specific area to deep-dive (component, ADR, BDD scenario) |
| `[S]ystem-plan` | Chain to `/system-plan --mode=review` for architecture update |
| `[C]ancel` | Discard analysis, return to normal workflow |

When the user chooses `[P]roceed`, the impact analysis results are passed as enriched context to the subsequent `/task-work` session — the coach receives architecture constraints without the developer needing to re-state them.

---

### /context-switch

Multi-project navigation command that loads the appropriate Graphiti project namespace and displays an orientation summary. Designed to eliminate the cognitive overhead of switching between projects.

#### Arguments and Syntax

```bash
/context-switch [project-name]
/context-switch --list
```

| Argument | Required | Description |
|----------|----------|-------------|
| `project-name` | No | Project to switch to. If omitted, shows current project context |
| `--list` | No | List all known projects with their Graphiti status |

**Design Decision**: `/context-switch` manages Graphiti context only — it does not manage git worktrees, branch state, or file system operations. Project switching at the git/filesystem level is the developer's responsibility (using `cd`, `git worktree`, etc.). This keeps the command focused and avoids dangerous side effects.

#### State Management

The command operates on GuardKit's project configuration, stored in `.guardkit/config.yaml`:

```yaml
# .guardkit/config.yaml
project:
  id: "guardkit"
  name: "GuardKit CLI"
  graphiti_prefix: "guardkit"

# Known projects (populated by /system-plan runs across repos)
known_projects:
  - id: "guardkit"
    name: "GuardKit CLI"
    path: "/Users/rich/Projects/guardkit"
    last_accessed: "2026-02-09T10:30:00Z"
  - id: "requirekit"
    name: "RequireKit"
    path: "/Users/rich/Projects/requirekit"
    last_accessed: "2026-02-08T14:00:00Z"
  - id: "poa-platform"
    name: "Power of Attorney Platform"
    path: "/Users/rich/Projects/poa-platform"
    last_accessed: "2026-02-05T09:00:00Z"
```

**What switching does:**

1. Updates the active `project.id` and `project.graphiti_prefix` in config
2. All subsequent Graphiti queries use the new project's namespace (via `client.get_group_id()`)
3. Displays orientation summary (architecture overview of the target project)
4. Shows in-progress tasks and recent activity for the target project

**What switching does NOT do:**

- Change the current working directory
- Switch git branches or worktrees
- Close/open files
- Modify any project files

#### Orientation Display

When switching to a project, the command displays a compact orientation:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔀 CONTEXT SWITCH: GuardKit CLI → Power of Attorney Platform
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Architecture: DDD with 4 bounded contexts
   Attorney Management | Document Generation | Financial Oversight | Compliance

🔑 Key Decisions:
   ADR-001: ACL for Moneyhub | ADR-002: Event-driven comms | ADR-003: Audit trail

📋 Active Work:
   🔄 TASK-AUTH-002 — Implement OAuth2 provider (in progress)
   📋 TASK-AUTH-003 — Add MFA to attorney login (pending)
   📋 TASK-AUTH-004 — Session management hardening (pending)

⏱️ Last accessed: 4 days ago (2026-02-05)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Now working in: Power of Attorney Platform
   Graphiti namespace: poa-platform__*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**List mode** (`--list`):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 KNOWN PROJECTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ▶ guardkit          GuardKit CLI                    (current)
    requirekit        RequireKit                      last: 1 day ago
    poa-platform      Power of Attorney Platform      last: 4 days ago

🧠 Graphiti Status:
    guardkit       — 5 components, 1 ADR, 2 concerns
    requirekit     — 3 components, 0 ADRs, 1 concern
    poa-platform   — 4 bounded contexts, 3 ADRs, 4 concerns

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage: /context-switch <project-name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**No arguments** (show current project):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 CURRENT PROJECT: GuardKit CLI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Displays system-overview output for current project]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Graphiti Queries

```python
async def execute_context_switch(
    client: GraphitiClient,
    target_project: str,
    config: GuardKitConfig,
) -> dict:
    """
    Switch active project context and display orientation.

    Steps:
      1. Validate target project exists in known_projects
      2. Update config with new active project
      3. Query Graphiti for target project's architecture summary
      4. Query for in-progress tasks (from task state files)
      5. Build and display orientation

    Does NOT change working directory, git state, or files.
    """
    # Validate
    project = config.get_known_project(target_project)
    if not project:
        return {"status": "unknown_project", "suggestion": "Run /system-plan in target project first"}

    # Update active project
    previous = config.active_project
    config.set_active_project(project["id"])

    # Query architecture for orientation
    sp = SystemPlanGraphiti(client, project["id"])
    overview = await get_system_overview(sp, verbose=False)

    # Find active tasks (reads task state files)
    active_tasks = _find_active_tasks(project.get("path"))

    return {
        "status": "switched",
        "previous": previous,
        "current": project,
        "overview": overview,
        "active_tasks": active_tasks,
    }
```

#### Token Budget

Context-switch is display-only and does not inject into any automated context. No token budget allocation needed.

---

## Automatic Integration

### AutoBuild Coach Context

The AutoBuild coach should receive architecture context to prevent the "locally correct but globally wrong" problem. This integration is gated by task complexity.

> **Architecture note — Graphiti, not CLAUDE.md**: System-level context is stored in and
> retrieved from Graphiti's temporal knowledge graph, not injected via CLAUDE.md updates.
> This follows GuardKit's established pattern where persistent project knowledge lives in
> Graphiti (queryable, scoped, version-tracked) and CLAUDE.md remains a static agent
> configuration file. All three read commands consume Graphiti data exclusively.

**Integration point**: `guardkit/orchestrator/quality_gates/coach_validator.py` — the Coach prompt assembly within the AutoBuild orchestration layer.

The AutoBuild architecture separates concerns across three layers (see [AutoBuild Architecture Deep-Dive](https://guardkit.ai/deep-dives/autobuild-architecture/)):

```
Layer 1: CLI (guardkit/cli/autobuild.py)            — argument parsing, user interaction
Layer 2: Orchestration (guardkit/orchestrator/)      — workflow coordination, state management
Layer 3: Execution (Claude Agent SDK)                — LLM interaction, tool execution
```

The coach context builder lives in Layer 2 alongside the existing `CoachValidator` which makes approval/feedback decisions. Architecture context enriches the Coach's validation prompt — it does NOT modify the Player's implementation approach (the Player receives context through the separate `JobContextRetriever` pipeline via FEAT-GR-006).

**How it works:**

The `build_coach_context()` function follows the established Graphiti context loading pattern used by `load_critical_context()` and `JobContextRetriever`:

```python
from guardkit.planning.complexity_gating import get_arch_token_budget
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.knowledge import ADRService, ADRStatus

async def build_coach_context(
    task: dict,
    client: GraphitiClient,
    project_id: str,
) -> str:
    """
    Build architecture context for the AutoBuild coach prompt.

    Uses complexity gating to determine how much context to include.
    Integrates with the existing CoachValidator in
    guardkit/orchestrator/quality_gates/coach_validator.py.

    This function is called during the COACH TURN of the adversarial loop,
    after the Player has completed its task-work --implement-only delegation
    and before the Coach validates the results. The Coach uses this context
    to catch architectural violations that would be invisible at the task level.

    Design principle: Coach has read-only tools and validates independently
    of the Player (Block AI "discard the player's self-report" pattern).
    Architecture context gives the Coach the "big picture" to anchor its
    independent verification against.
    """
    complexity = task.get("complexity", 5)
    token_budget = get_arch_token_budget(complexity)

    if token_budget == 0:
        return ""  # Simple tasks: no architecture context

    sp = SystemPlanGraphiti(client, project_id)

    # System overview (condensed)
    overview = await get_system_overview(sp, verbose=False)
    overview_text = condense_for_injection(overview, max_tokens=min(800, token_budget // 2))

    # Task-specific impact (if budget allows)
    remaining_budget = token_budget - _estimate_tokens(overview_text)
    impact_text = ""
    if remaining_budget > 400:
        impact = await run_impact_analysis(
            sp, client,
            task_or_topic=task.get("title", ""),
            depth="quick",
        )
        impact_text = condense_impact_for_injection(impact, max_tokens=remaining_budget)

    return f"""## Architecture Context

{overview_text}

## Task Impact
{impact_text}
"""
```

**Complexity tiers** (from existing `complexity_gating.py`):

| Complexity | Arch Token Budget | Coach Receives |
|------------|-------------------|----------------|
| 1-3 | 0 tokens | No architecture context |
| 4-6 | 1000 tokens | Condensed overview only |
| 7-8 | 2000 tokens | Overview + quick impact analysis |
| 9-10 | 3000 tokens | Overview + standard impact analysis |

### Task-work Pre-flight

Before `/task-work` begins implementation, architecture context should be available. This is not a blocking gate — it's informational context that helps the developer and coach make better decisions.

**Design Decision**: Impact analysis does NOT run automatically before every `/task-work`. Instead:

1. For complexity ≥ 7, `/task-work` displays a one-line suggestion: `💡 Consider running /impact-analysis TASK-XXX first`
2. For complexity ≥ 4, architecture context is silently loaded into the coach context (via AutoBuild integration above)
3. For complexity 1-3, no architecture context is involved

This avoids ceremony for simple tasks while encouraging informed decision-making for complex ones.

**Implementation in task-work.md**:

```
### Pre-Implementation Architecture Check (Complexity ≥ 7)

If task complexity is 7 or higher and Graphiti has architecture context:

    💡 This is a high-complexity task. Architecture context available:
       /impact-analysis TASK-XXX — see what this task affects
       /system-overview — review current architecture

    Proceeding with task-work...

This is informational only — it does not block or require user action.
```

### Complexity Gating

The existing `complexity_gating.py` module (see Current State section) provides the foundation. No changes to the gating thresholds are needed — the module already returns the correct token budgets.

> **Relationship to FEAT-GR-006 budget system**: The `DynamicBudgetCalculator` (documented in
> [Job-Specific Context guide](https://guardkit.ai/guides/graphiti-job-context/)) manages base
> budgets of 2000/4000/6000 tokens by complexity (1-3/4-6/7-10) with dynamic adjustments
> (+30% first-of-type, +15% few similar, +20% refinement, +15% AutoBuild later turns).
> The architecture token budgets here are a SEPARATE, smaller allocation specifically for
> system-level context injected into the coach prompt. They do not compete with the
> `JobContextRetriever` budget — they supplement it with architecture-specific knowledge
> that `JobContextRetriever` does not currently retrieve.

The read commands hook into this via the `get_arch_token_budget()` function:

```python
# Existing function, no modification needed
budget = get_arch_token_budget(task_complexity)

# New consumption pattern
if budget > 0:
    overview = condense_for_injection(overview_data, max_tokens=budget // 2)
    impact = condense_impact_for_injection(impact_data, max_tokens=budget // 2)
```

---

## Graceful Degradation

All three commands must handle the case where architecture context doesn't exist — either because `/system-plan` hasn't been run, or because Graphiti is unavailable.

### No Architecture Context (system-plan not yet run)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ No architecture context found for this project.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Architecture context enables:
  • /system-overview — quick reference of your system design
  • /impact-analysis — pre-task validation against architecture
  • AutoBuild coach — architecture-aware code review

To set up architecture context:
  /system-plan "your project description"

This takes 5-10 minutes and significantly improves planning quality.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Partial Architecture Context

If some architecture exists but is incomplete (e.g., only one category was completed before the user cancelled), the commands display what's available with a note:

```
⚠️ Partial architecture context (2 of 6 categories completed)
   Run /system-plan "project" to complete the remaining categories.

[Display available components and decisions]
```

### Graphiti Unavailable

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Graphiti unavailable — architecture queries disabled.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Architecture documentation may still exist in docs/architecture/.
Use those files for manual reference.

To enable Graphiti:
  1. Start the Graphiti stack: docker compose -f docker/docker-compose.graphiti.yml up -d
  2. Verify: guardkit graphiti status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Behaviour by Command

| Command | No Context | Partial Context | Graphiti Down |
|---------|-----------|----------------|---------------|
| `/system-overview` | Suggest `/system-plan` | Display what exists + warning | Point to markdown files |
| `/impact-analysis` | Suggest `/system-plan` | Analyse against available context | Point to markdown files |
| `/context-switch` | Works (project config is local) | Switch succeeds, overview shows partial | Switch succeeds, overview unavailable |

---

## Acceptance Criteria

### /system-overview

- [ ] Displays condensed architecture summary that fits in one screen (~40-60 lines) by default
- [ ] `--verbose` flag shows extended multi-page output with full descriptions
- [ ] `--section` filter shows only the requested section
- [ ] `--format=json` returns structured data for programmatic consumption
- [ ] Shows methodology, components, active ADRs, cross-cutting concerns, and tech stack
- [ ] Shows "last updated" timestamp from Graphiti episode metadata
- [ ] `condense_for_injection()` produces output within specified token budget
- [ ] Handles no architecture context gracefully with helpful suggestion message
- [ ] Handles Graphiti unavailable gracefully with fallback guidance

### /impact-analysis

- [ ] Accepts both task IDs and free-text topic descriptions
- [ ] When given a task ID, reads task file for enriched semantic queries
- [ ] Quick depth returns affected components and risk score in <5 seconds
- [ ] Standard depth includes ADR constraints and architectural implications
- [ ] Deep depth includes BDD scenarios and related tasks
- [ ] Risk score (1-5) calculated from component count, ADR conflicts, BDD impact
- [ ] Decision checkpoint offers [P]roceed/[R]eview/[S]ystem-plan/[C]ancel options
- [ ] [P]roceed passes impact context to subsequent `/task-work` session
- [ ] Handles no architecture context gracefully
- [ ] Handles missing BDD group gracefully (deep mode degrades to standard when `bdd_scenarios` group is empty or unregistered)

### /context-switch

- [ ] Switches active project in `.guardkit/config.yaml`
- [ ] Displays orientation summary with architecture overview and active tasks
- [ ] `--list` shows all known projects with Graphiti status summary
- [ ] No-args mode shows current project context
- [ ] Does NOT change working directory, git state, or files
- [ ] Unknown project name returns helpful error with suggestion
- [ ] Works even when Graphiti is unavailable (project config is local)
- [ ] Updates `last_accessed` timestamp on switch

### AutoBuild Integration

- [ ] Coach receives architecture context for tasks with complexity ≥ 4
- [ ] Context is within token budget from `get_arch_token_budget()`
- [ ] Complexity 1-3 tasks receive no architecture context
- [ ] Task-work displays suggestion for complexity ≥ 7 tasks

---

## Testing Approach

### Unit Tests

```
tests/unit/planning/
├── test_system_overview.py        # Overview assembly and condensation
│   ├── test_get_system_overview_full
│   ├── test_get_system_overview_no_context
│   ├── test_condense_for_injection_within_budget
│   ├── test_condense_for_injection_priority_order
│   └── test_section_filter
├── test_impact_analysis.py        # Impact analysis and risk scoring
│   ├── test_run_impact_analysis_standard
│   ├── test_run_impact_analysis_deep_with_bdd
│   ├── test_calculate_risk_low
│   ├── test_calculate_risk_high
│   ├── test_build_query_from_task_id
│   ├── test_build_query_from_topic
│   └── test_missing_bdd_group_degrades
├── test_context_switch.py         # Context switching logic
│   ├── test_switch_to_known_project
│   ├── test_switch_to_unknown_project
│   ├── test_list_known_projects
│   ├── test_current_project_display
│   └── test_switch_updates_last_accessed
└── test_coach_context_builder.py  # Coach context assembly
    ├── test_build_coach_context_no_arch
    ├── test_build_coach_context_medium_complexity
    ├── test_build_coach_context_high_complexity
    └── test_build_coach_context_graphiti_unavailable
```

### Integration Tests

```
tests/integration/
├── test_system_overview_graphiti.py    # Real Graphiti queries
│   ├── test_overview_with_seeded_architecture
│   └── test_overview_empty_project
├── test_impact_analysis_graphiti.py    # Impact against real data
│   ├── test_impact_with_components_and_adrs
│   └── test_impact_with_bdd_scenarios
└── test_context_switch_config.py      # Config file manipulation
    ├── test_switch_persists_to_config
    └── test_switch_round_trip
```

### Manual Testing Scenarios

1. **Fresh project** — run all three commands on a project with no `/system-plan` output; verify graceful degradation messages
2. **After system-plan** — run `/system-plan` then immediately `/system-overview`; verify all captured data appears
3. **Impact analysis flow** — run `/impact-analysis` on a known task, choose [P]roceed, verify context flows to `/task-work`
4. **Multi-project switch** — switch between GuardKit and RequireKit projects, verify isolation and correct architecture display
5. **Coach integration** — run `/feature-build` on a complexity-7 task, verify coach prompt includes architecture context

---

## File Changes

### New Files

```
# Command files (Claude Code slash commands)
.claude/commands/system-overview.md          # /system-overview command spec
.claude/commands/impact-analysis.md          # /impact-analysis command spec
.claude/commands/context-switch.md           # /context-switch command spec

# Installer command files (for guardkit install distribution)
installer/core/commands/system-overview.md
installer/core/commands/impact-analysis.md
installer/core/commands/context-switch.md

# Planning module additions
guardkit/planning/system_overview.py         # Overview assembly and condensation
guardkit/planning/impact_analysis.py         # Impact analysis engine and risk scoring
guardkit/planning/context_switch.py          # Project switching logic

# Tests
tests/unit/planning/test_system_overview.py
tests/unit/planning/test_impact_analysis.py
tests/unit/planning/test_context_switch.py
tests/unit/planning/test_coach_context_builder.py
tests/integration/test_system_overview_graphiti.py
tests/integration/test_impact_analysis_graphiti.py
tests/integration/test_context_switch_config.py
```

### Modified Files

```
guardkit/orchestrator/quality_gates/coach_validator.py  # Add architecture context to coach prompt (Layer 2)
guardkit/knowledge/graphiti_client.py        # Register bdd_scenarios as project group
guardkit/planning/complexity_gating.py       # No changes needed (already correct)
guardkit/planning/__init__.py                # Export new modules
.claude/commands/task-work.md                # Add pre-flight architecture suggestion
installer/core/commands/task-work.md         # Same pre-flight suggestion
.guardkit/config.yaml                        # Add known_projects and active project
```

---

## Design Decision Summary

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | /system-overview output size | One screen default (~40-60 lines), --verbose for multi-page | Quick reference is the primary use case; verbosity available when needed |
| 2 | /impact-analysis depth | Three tiers: quick/standard/deep | Balances speed vs thoroughness; standard default covers most cases |
| 3 | /context-switch state management | Graphiti context only, no git/filesystem changes | Avoids dangerous side effects; filesystem is developer's responsibility |
| 4 | Automatic vs manual invocation | Coach gets auto-injected context (complexity-gated); manual invocation for commands | No blocking gates, but informed decisions via suggestions |
| 5 | Graceful degradation | Helpful message suggesting /system-plan; partial context displayed when available | Never fails silently; always shows what's available and what's missing |
| 6 | Token budgets | Overview: 800 coach / 600 feature-plan; Impact: 1200 coach / 600 preflight | Fits within existing 4000-token total coach budget from FEAT-GR-006 |
| 7 | Impact decision checkpoint | [P]roceed/[R]eview/[S]ystem-plan/[C]ancel | Follows established checkpoint pattern from /task-review; enables workflow chaining |
| 8 | Task-work pre-flight | Suggestion only (complexity ≥ 7), not blocking | Maintains "least ceremony" principle; avoids slowing down simple tasks |
| 9 | Risk scoring | Heuristic based on component count + ADR conflicts + BDD impact | Simple, explainable, tunable; avoids over-engineering |

---

## References

- `FEAT-SP-001-system-plan-command.md` — Spec 1 output (defines the data these commands read)
- `guardkit-requirekit-evolution-strategy.md` — Strategy document sections 4.4, 7
- `TASK-REV-1505-review-report.md` — Architectural review parts 3 and 4 (context budget allocation)
- `feature-plan.md` — Existing command pattern reference (Graphiti context integration)
- `task-review.md` — Interactive flow pattern reference (decision checkpoints)
- `guardkit/planning/graphiti_arch.py` — Existing SystemPlanGraphiti read operations
- `guardkit/planning/complexity_gating.py` — Existing complexity-based token budgets
- `guardkit-evolution-spec-kickoff.md` — Spec 2 requirements and key questions
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md` — Graphiti API surface, group IDs, search return format
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md` — Episode structure, content fidelity, graceful degradation patterns

### Documentation Site References

- [AutoBuild Architecture Deep-Dive](https://guardkit.ai/deep-dives/autobuild-architecture/) — Three-layer architecture (CLI/Orchestration/Execution), Player-Coach adversarial cooperation, Quality Gate Delegation (Option B), worktree isolation
- [AutoBuild Workflow Guide](https://guardkit.ai/guides/autobuild-workflow/) — Dialectical loop, tool asymmetry (Player full-access vs Coach read-only), independent verification ("discard self-report"), task-work delegation pattern
- [Graphiti Architecture](https://guardkit.ai/architecture/graphiti-architecture/) — Knowledge categories (18 groups), Python API (GraphitiClient, ADRService, OutcomeCapture), entity models, Phase 2 enhancements (JobContextRetriever, DynamicBudgetCalculator, ContextBudget)
- [Job-Specific Context Guide](https://guardkit.ai/guides/graphiti-job-context/) — DynamicBudgetCalculator allocation, standard vs AutoBuild budget splits, relevance filtering thresholds, caching (300s TTL), early termination (95% budget)

---

## Appendix: Graphiti Compatibility Review

This spec was cross-referenced against the updated Graphiti baseline documentation (post TASK-GBF and TASK-DOC-GTP6 revisions). The following items were identified and resolved:

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | `bdd_scenarios` group not registered as project group | 🔴 | Added to project groups list; explicit `scope="project"` in queries; graceful degradation when empty |
| 2 | `search()` results lack `entity_type` field | 🔴 | Clarified that entity type is inferred via heuristic name/content parsing, not from a result field |
| 3 | `get_group_id("bdd_scenarios")` would default to system scope | 🔴 | Fixed to use `scope="project"` explicitly; registration in project groups list also resolves |
| 4 | Content fidelity: parsing functions assume structured data from search | 🟡 | Added note that `_parse_*_hits()` functions use heuristic extraction from semantic fact strings |
| 5 | Stale dependency on Spec 3 (FEAT-GE-001) for already-existing entities | 🟡 | Removed; `role_constraints`, `quality_gate_configs`, `turn_states` confirmed as already implemented |
| 6 | Tech ref internal: CLI says "16 categories" but seeding lists 18 | ℹ️ | Flagged for separate doc fix (not a spec issue); see `graphiti-technical-reference.md` §5 vs §7 |
