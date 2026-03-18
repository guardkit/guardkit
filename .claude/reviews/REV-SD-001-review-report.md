# Review Report: REV-SD-001

## Executive Summary

The `/system-design` command (and 7 other commands) uses **Python pseudocode** in its prompt template to check Graphiti availability. Since these commands are executed by an LLM (Claude Code), the LLM cannot actually run `get_graphiti()` imports — it has no Python runtime. The LLM correctly recognises the code is non-executable and defaults to the `else` branch ("Graphiti unavailable"), even when Graphiti is fully configured and operational.

The fix is well-understood: replace the Python pseudocode pattern with the **file-existence + CLI check pattern** already proven in `/task-work` Phase 1.7.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Task**: REV-SD-001
- **Reviewer**: architectural-reviewer (manual analysis)

## Architecture Score: 45/100

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - SRP | 6/10 | Command specs mix "what the LLM should do" with "illustrative Python" |
| SOLID - OCP | 5/10 | Adding new Graphiti checks requires modifying each command spec |
| SOLID - LSP | 7/10 | N/A — no inheritance hierarchy |
| SOLID - ISP | 6/10 | Commands depend on imports they can't use |
| SOLID - DIP | 3/10 | **Critical**: Commands depend on concrete Python imports instead of abstract availability signals |
| DRY | 2/10 | **Critical**: Same broken pattern copy-pasted across 8 commands |
| YAGNI | 7/10 | No unnecessary features, but pseudocode adds confusion |

## Findings

### Finding 1: Python Pseudocode Is Non-Executable by the LLM (CRITICAL)

**Evidence**: [system-design.md:44-74](installer/core/commands/system-design.md#L44-L74), [system-arch.md:36-52](installer/core/commands/system-arch.md#L36-L52)

The command prompt contains:

```python
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.knowledge.graphiti_client import get_graphiti

client = get_graphiti()  # Returns None if Graphiti unavailable
if client:
    # ... use Graphiti
else:
    print("⚠️ Graphiti unavailable — reading architecture from local files")
```

When Claude Code reads this prompt, it cannot execute these Python imports. It sees code that references modules it has no way to import, so it rationally takes the `else` path. **This is the root cause of the bug.**

**Severity**: Critical — renders all Graphiti integration non-functional for affected commands.

### Finding 2: Proven Fix Pattern Exists in task-work Phase 1.7

**Evidence**: [task-work.md:1700-1804](installer/core/commands/task-work.md#L1700-L1804)

The `/task-work` command solved this problem correctly using a **CLI-executable pattern**:

```bash
graphiti-check --status --quiet
# Returns JSON: {"available": true|false, "error": null|"...", ...}
```

This works because:
1. Claude Code **can** execute bash commands
2. The `graphiti-check` script ([graphiti_check.py](installer/core/commands/lib/graphiti_check.py)) performs all 4 checks (env var, library, config, connectivity)
3. The result is a simple JSON boolean — no Python import gymnastics

### Finding 3: 8 Commands Share the Same Broken Pattern (DRY Violation)

**Evidence**: Grep across `installer/core/commands/*.md`

| Command | Import Pattern | Lines |
|---------|---------------|-------|
| `/system-design` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 47, 85, 1139 |
| `/system-arch` | `from guardkit.knowledge.graphiti_service import get_graphiti` | 37, 62, 1001 |
| `/system-plan` | `from guardkit.knowledge.graphiti_service import get_graphiti` | 43, 792, 1066 |
| `/system-overview` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 39, 284 |
| `/impact-analysis` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 89, 430 |
| `/arch-refine` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 45, 74, 760 |
| `/design-refine` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 49, 86, 1027 |
| `/context-switch` | `from guardkit.knowledge.graphiti_client import get_graphiti` | 447 |

Note: Two different import paths are used (`graphiti_service` vs `graphiti_client`) — an additional inconsistency.

### Finding 4: Group ID Mismatch

**Evidence**: [graphiti.yaml:57-62](.guardkit/graphiti.yaml#L57-L62) vs [system-design.md:689](installer/core/commands/system-design.md#L689)

| Source | Group IDs |
|--------|-----------|
| `.guardkit/graphiti.yaml` | `product_knowledge`, `command_workflows`, `architecture_decisions` |
| `/system-design` Phase 5 | `project_design`, `api_contracts` |
| `/system-arch` Phase 4 | `project_architecture`, `project_decisions` |
| `graphiti-knowledge.md` rules | `product_knowledge`, `command_workflows`, `patterns`, `agents`, `project_overview`, `project_architecture`, `feature_specs`, `project_decisions`, `architecture_decisions`, `task_outcomes`, `failure_patterns`, `successful_fixes`, `turn_states` |

The `SystemDesignGraphiti` class references `project_design` and `api_contracts` groups. These are **not** listed in `graphiti.yaml`'s `group_ids` section. However, the `GraphitiClient.get_group_id()` method likely auto-creates/prefixes groups, so this may be working as designed — the YAML `group_ids` list is for seeding, not an exhaustive registry. This needs confirmation.

### Finding 5: Seeding Instructions Missing from Command Prompts

**Evidence**: [system-design.md:687-714](installer/core/commands/system-design.md#L687-L714)

Phase 5 (Graphiti Seeding) uses Python pseudocode with `SystemDesignGraphiti` method calls. When Graphiti is "unavailable" (per Finding 1), this entire phase is skipped. Even if the availability check were fixed, the LLM still can't call `design_sp.upsert_api_contract()` directly.

The command should instead emit `guardkit graphiti add-context` CLI commands that the user (or automation) can run.

### Finding 6: graphiti_check.py Is Well-Designed but Under-Utilised

**Evidence**: [graphiti_check.py](installer/core/commands/lib/graphiti_check.py)

The `graphiti_check.py` script performs robust 4-layer availability checking:
1. Environment variable override (`GRAPHITI_ENABLED`)
2. Library availability (`graphiti-core` installed)
3. Configuration validation (`.guardkit/graphiti.yaml` + `enabled: true`)
4. Connectivity test (FalkorDB ping)

This is exactly what the other 8 commands need, but only `/task-work` uses it.

### Finding 7: Inconsistent Import Paths

**Evidence**: `/system-arch` and `/system-plan` use `guardkit.knowledge.graphiti_service`, while all others use `guardkit.knowledge.graphiti_client`.

This inconsistency suggests the commands were written at different times and not harmonised. The actual module is `graphiti_client` (confirmed by file existence at [guardkit/knowledge/](guardkit/knowledge/)).

### Finding 8: No Graphiti Availability Caching

Each command checks Graphiti availability independently. If the user runs `/system-arch` followed by `/system-design`, the availability check runs twice. This is minor (the check is fast) but worth noting for the file-existence pattern, which is essentially free.

## Recommendations

### Recommendation 1: Replace Python Pseudocode with CLI/File-Check Pattern (Priority: CRITICAL)

**For all 8 affected commands**, replace the Python import pattern with:

```markdown
### Graphiti Availability Check

**Check `.guardkit/graphiti.yaml` for Graphiti availability:**

1. Read `.guardkit/graphiti.yaml` — if file does not exist, Graphiti is unavailable
2. Check `enabled: true` in the YAML — if false or missing, Graphiti is unavailable
3. If available, note the `group_ids` for seeding operations

**OR** run the CLI check for full connectivity verification:

```bash
graphiti-check --status --quiet
```

Parse JSON output: `{"available": true|false, "error": null|"..."}`
```

**Effort**: Medium (each command spec needs targeted edits)
**Impact**: Fixes the core bug across all commands

### Recommendation 2: Standardise Seeding to CLI Commands (Priority: HIGH)

Replace Phase 5 Python pseudocode with actionable CLI commands:

```markdown
### Phase 5: Graphiti Seeding

**IF Graphiti available**, emit these commands for the user to run:

```bash
guardkit graphiti add-context docs/design/contracts/{context}-api.yaml --group project_design
guardkit graphiti add-context docs/design/models/{context}-models.md --group project_design
guardkit graphiti add-context docs/design/decisions/DDR-{NNN}.md --group architecture_decisions
```

**IF Graphiti unavailable**:
```
⚠️ Graphiti unavailable — artefacts written to markdown only
   Re-run with Graphiti enabled to seed knowledge graph
```
```

**Effort**: Medium
**Impact**: Makes seeding actually executable

### Recommendation 3: Create a Shared Graphiti Preamble Include (Priority: MEDIUM)

Extract the availability check into a reusable snippet that all commands reference:

```markdown
<!-- In installer/core/commands/lib/graphiti-preamble.md -->
## Graphiti Availability Check

Read `.guardkit/graphiti.yaml`. If the file exists and contains `enabled: true`,
Graphiti is available. Store this as a boolean for use throughout the command.

Alternatively, run: `graphiti-check --status --quiet`
```

Each command then includes: `**See**: lib/graphiti-preamble.md for Graphiti availability check`

**Effort**: Low
**Impact**: Eliminates DRY violation, single point of maintenance

### Recommendation 4: Harmonise Import Paths (Priority: LOW)

Replace all `guardkit.knowledge.graphiti_service` references with `guardkit.knowledge.graphiti_client` (the actual module name). This affects `/system-arch` and `/system-plan`.

**Effort**: Low (search-and-replace)
**Impact**: Removes confusion if anyone reads the pseudocode for reference

### Recommendation 5: Document Group ID Strategy (Priority: LOW)

Add a section to `graphiti-knowledge.md` that documents all group IDs used across commands:

| Group | Created By | Used By |
|-------|-----------|---------|
| `product_knowledge` | `guardkit init` | General queries |
| `project_architecture` | `/system-arch` | `/system-design`, `/impact-analysis` |
| `project_design` | `/system-design` | `/feature-spec`, `/feature-plan` |
| `api_contracts` | `/system-design` | `/feature-spec`, `/feature-plan` |
| `architecture_decisions` | `/system-arch` | `/arch-refine`, `/design-refine` |

**Effort**: Low
**Impact**: Clarifies the group ID landscape

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| Fix all 8 commands at once | 95 | High (2-3 days) | Low | **Recommended** |
| Fix system-design only, others later | 70 | Low (4 hours) | Medium (inconsistency) | Acceptable |
| Create shared preamble + fix all | 98 | High (3-4 days) | Low | Best long-term |
| Do nothing | 10 | None | High (broken feature) | Not recommended |

## Appendix

### Affected Files

| File | Type | Changes Needed |
|------|------|---------------|
| `installer/core/commands/system-design.md` | Command spec | Replace 3 pseudocode blocks |
| `installer/core/commands/system-arch.md` | Command spec | Replace 3 pseudocode blocks |
| `installer/core/commands/system-plan.md` | Command spec | Replace 3 pseudocode blocks |
| `installer/core/commands/system-overview.md` | Command spec | Replace 2 pseudocode blocks |
| `installer/core/commands/impact-analysis.md` | Command spec | Replace 2 pseudocode blocks |
| `installer/core/commands/arch-refine.md` | Command spec | Replace 3 pseudocode blocks |
| `installer/core/commands/design-refine.md` | Command spec | Replace 3 pseudocode blocks |
| `installer/core/commands/context-switch.md` | Command spec | Replace 1 pseudocode block |
| `.claude/rules/graphiti-knowledge.md` | Rules | Add group ID documentation |

### Pattern Comparison

**Broken Pattern** (current — system-design et al.):
```python
from guardkit.knowledge.graphiti_client import get_graphiti
client = get_graphiti()  # LLM cannot execute this
if client:
    # Graphiti path (never reached)
else:
    print("⚠️ Graphiti unavailable")  # Always reached
```

**Working Pattern** (task-work Phase 1.7):
```bash
graphiti-check --status --quiet
# LLM CAN execute this via Bash tool
# Returns JSON: {"available": true, ...}
```

**Proposed Simplest Pattern** (file-existence check):
```markdown
Read `.guardkit/graphiti.yaml`.
If the file exists and contains `enabled: true`, Graphiti is available.
```
