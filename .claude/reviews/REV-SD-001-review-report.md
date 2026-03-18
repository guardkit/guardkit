# Review Report: REV-SD-001 (Revised)

## Executive Summary

The `/system-design` command (and 7 other commands) defaults to "Graphiti unavailable" because its command specification contains **Python pseudocode** (`get_graphiti()`, `SystemDesignGraphiti`) that the executing LLM interprets as **intended behaviour logic** but cannot actually execute. The LLM has no Python runtime — it processes the command spec as natural-language instructions and, seeing non-importable modules, rationally takes the `else` fallback path.

This has been validated by tracing the complete execution flow across four system boundaries (User → VS Code → Claude Code → LLM → Tools) and confirmed by a live test showing `graphiti-check --status` returns `{"available": true}` on this machine.

**Root Cause Confidence: HIGH** — validated via C4 sequence diagrams, live connectivity test, and direct comparison with the working `/task-work` Phase 1.7 pattern.

## Review Details

- **Mode**: Architectural Review (Revised — deeper analysis)
- **Depth**: Comprehensive
- **Task**: REV-SD-001
- **Reviewer**: architectural-reviewer (manual trace analysis + live verification)

---

## C4 Context Diagram: Command Execution Landscape

```
┌─────────────────────────────────────────────────────────────┐
│                      GuardKit System                        │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Command      │    │  Python      │    │  Knowledge   │  │
│  │  Specs (.md)  │    │  Libraries   │    │  Graph       │  │
│  │              │    │              │    │  (FalkorDB)  │  │
│  │  8 commands   │    │  guardkit/   │    │              │  │
│  │  with Python  │    │  knowledge/  │    │  whitestocks │  │
│  │  pseudocode   │    │  planning/   │    │  :6379       │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         │    ┌──────────────┴───────┐           │           │
│         │    │  graphiti-check      │           │           │
│         │    │  CLI wrapper         ├───────────┘           │
│         │    │  (the bridge)        │                       │
│         │    └──────────────────────┘                       │
└─────────┼───────────────────────────────────────────────────┘
          │
    ┌─────┴─────┐         ┌──────────────┐
    │  Claude    │◄────────│   User       │
    │  Code LLM │         │   (VS Code)  │
    │           │         └──────────────┘
    │  Has:     │
    │  - Read   │
    │  - Bash   │
    │  - Edit   │
    │  - Grep   │
    │           │
    │  Does NOT │
    │  have:    │
    │  - Python │
    │    runtime│
    └───────────┘
```

**Key insight**: The command specs (left) and the Python libraries (centre) are in different execution domains. The `graphiti-check` CLI wrapper is the **only bridge** between them. Only `/task-work` uses it.

---

## C4 Container Diagram: System Boundaries

```
┌─ USER SPACE ──────────────────────────────────────────────────────────┐
│                                                                       │
│   User types: /system-design                                          │
│                                                                       │
└───────────────────────────┬───────────────────────────────────────────┘
                            │
                            ▼
┌─ VS CODE + CLAUDE CODE ──────────────────────────────────────────────┐
│                                                                       │
│   1. Skill tool resolves "system-design"                              │
│   2. Loads ~/.claude/commands/system-design.md                        │
│      (symlink → ~/.agentecflow/commands/system-design.md)             │
│   3. Injects full markdown as prompt context for the LLM              │
│                                                                       │
│   NOTE: NO Python interpreter is invoked. The markdown is treated     │
│   as instructions for the LLM to follow.                              │
│                                                                       │
└───────────────────────────┬───────────────────────────────────────────┘
                            │
                            ▼
┌─ LLM EXECUTION CONTEXT ─────────────────────────────────────────────┐
│                                                                       │
│   The LLM reads the command spec and encounters:                      │
│                                                                       │
│   "CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE"                        │
│   "you MUST execute these steps in order"                             │
│                                                                       │
│   Step 1 contains:                                                    │
│   ```python                                                           │
│   from guardkit.knowledge.graphiti_client import get_graphiti         │
│   client = get_graphiti()                                             │
│   if client:                                                          │
│       ...                                                             │
│   else:                                                               │
│       print("⚠️ Graphiti unavailable")                                │
│   ```                                                                 │
│                                                                       │
│   LLM reasoning:                                                      │
│   - "I must execute these steps"                                      │
│   - "Step 1 is a Python code block with imports"                      │
│   - "I cannot import guardkit.knowledge.graphiti_client"              │
│   - "get_graphiti() would return None (I can't call it)"             │
│   - "Therefore: client = None → else branch → unavailable"           │
│                                                                       │
│   Available tools: Read, Bash, Edit, Grep, Write, Glob, Agent        │
│   NOT available: Python runtime, pip, import system                   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram: BROKEN Flow (/system-design)

```
User          VS Code/Claude Code    LLM                   graphiti-check    FalkorDB
 │                 │                   │                         │               │
 │ /system-design  │                   │                         │               │
 ├────────────────►│                   │                         │               │
 │                 │ Load skill:       │                         │               │
 │                 │ system-design.md  │                         │               │
 │                 ├──────────────────►│                         │               │
 │                 │                   │                         │               │
 │                 │  [Full markdown   │                         │               │
 │                 │   injected as     │                         │               │
 │                 │   prompt context] │                         │               │
 │                 │                   │                         │               │
 │                 │                   │ Parse: "CRITICAL        │               │
 │                 │                   │ EXECUTION INSTRUCTIONS" │               │
 │                 │                   │                         │               │
 │                 │                   │ Step 1: Python block    │               │
 │                 │                   │ "get_graphiti()"        │               │
 │                 │                   │                         │               │
 │                 │                   │ ┌─────────────────┐     │               │
 │                 │                   │ │ LLM REASONING:  │     │               │
 │                 │                   │ │                 │     │               │
 │                 │                   │ │ I see Python    │     │               │
 │                 │                   │ │ imports I can't │     │               │
 │                 │                   │ │ execute. No     │     │               │
 │                 │                   │ │ Python runtime. │     │               │
 │                 │                   │ │                 │     │               │
 │                 │                   │ │ → Take else     │     │               │
 │                 │                   │ │   branch        │     │               │
 │                 │                   │ └─────────────────┘     │               │
 │                 │                   │                         │               │
 │                 │                   │  ╔═══════════════════╗  │               │
 │                 │                   │  ║ graphiti-check    ║  │               │
 │                 │                   │  ║ NEVER CALLED      ║  │               │
 │                 │                   │  ║                   ║  │               │
 │                 │                   │  ║ FalkorDB          ║  │               │
 │                 │                   │  ║ NEVER CONTACTED   ║  │               │
 │                 │                   │  ╚═══════════════════╝  │               │
 │                 │                   │                         │               │
 │  "⚠️ Graphiti   │                   │                         │               │
 │   unavailable"  │◄─────────────────│                         │               │
 │◄────────────────│                   │                         │               │
 │                 │                   │                         │               │
```

**Failure point**: The LLM never crosses the boundary into the Python/infrastructure layer. It stays entirely within the LLM execution context and makes a reasoning-based decision that `get_graphiti()` would return None.

---

## Sequence Diagram: WORKING Flow (/task-work Phase 1.7)

```
User          VS Code/Claude Code    LLM                   graphiti-check    FalkorDB
 │                 │                   │                         │               │
 │ /task-work      │                   │                         │               │
 ├────────────────►│                   │                         │               │
 │                 │ Load skill:       │                         │               │
 │                 │ task-work.md      │                         │               │
 │                 ├──────────────────►│                         │               │
 │                 │                   │                         │               │
 │                 │                   │ Parse Phase 1.7:        │               │
 │                 │                   │ "Run the graphiti       │               │
 │                 │                   │  check wrapper"         │               │
 │                 │                   │                         │               │
 │                 │                   │ ```bash                 │               │
 │                 │                   │ graphiti-check           │               │
 │                 │                   │   --status --quiet      │               │
 │                 │                   │ ```                     │               │
 │                 │                   │                         │               │
 │                 │                   │ ┌─────────────────┐     │               │
 │                 │                   │ │ LLM REASONING:  │     │               │
 │                 │                   │ │                 │     │               │
 │                 │                   │ │ It says "Run"   │     │               │
 │                 │                   │ │ + bash block.   │     │               │
 │                 │                   │ │ I have a Bash   │     │               │
 │                 │                   │ │ tool. Use it.   │     │               │
 │                 │                   │ └─────────────────┘     │               │
 │                 │                   │                         │               │
 │                 │     Bash tool     │                         │               │
 │                 │◄──────────────────│                         │               │
 │                 │                   │                         │               │
 │                 │  Execute:         │                         │               │
 │                 │  graphiti-check   │                         │               │
 │                 │  --status --quiet │                         │               │
 │                 │                   │                         │               │
 │                 │                   │         ┌───────────────┤               │
 │                 │                   │         │ Python exec   │               │
 │                 │                   │         │               │               │
 │                 │                   │         │ Check 1: ENV  │               │
 │                 │                   │         │ Check 2: lib  │               │
 │                 │                   │         │ Check 3: yaml │               │
 │                 │                   │         │ Check 4: ping ├──────────────►│
 │                 │                   │         │               │     PING      │
 │                 │                   │         │               │◄──────────────│
 │                 │                   │         │               │     PONG      │
 │                 │                   │         └───────┬───────┘               │
 │                 │                   │                 │                       │
 │                 │  JSON stdout:     │                 │                       │
 │                 │  {"available":    │◄────────────────┘                       │
 │                 │   true, ...}      │                                         │
 │                 ├──────────────────►│                                         │
 │                 │                   │                                         │
 │                 │                   │ Parse JSON → available = true           │
 │                 │                   │ Proceed with Graphiti context           │
 │                 │                   │                                         │
 │ "[Graphiti]     │                   │                                         │
 │  Context loaded"│◄─────────────────│                                         │
 │◄────────────────│                   │                                         │
```

**Success point**: The LLM crosses into the infrastructure layer via the Bash tool, which invokes `graphiti-check` (a real Python process), which pings FalkorDB and returns a concrete boolean.

---

## Sequence Diagram: PROPOSED Fix for /system-design

```
User          VS Code/Claude Code    LLM                   Read tool         .guardkit/
 │                 │                   │                         │            graphiti.yaml
 │ /system-design  │                   │                         │               │
 ├────────────────►│                   │                         │               │
 │                 │ Load skill:       │                         │               │
 │                 │ system-design.md  │                         │               │
 │                 ├──────────────────►│                         │               │
 │                 │                   │                         │               │
 │                 │                   │ Parse Step 1:           │               │
 │                 │                   │ "Read .guardkit/        │               │
 │                 │                   │  graphiti.yaml"         │               │
 │                 │                   │                         │               │
 │                 │     Read tool     │                         │               │
 │                 │◄──────────────────│                         │               │
 │                 │                   │                         │               │
 │                 │  Read file:       │                         │               │
 │                 │  .guardkit/       ├────────────────────────►│               │
 │                 │  graphiti.yaml    │                         │               │
 │                 │                   │◄────────────────────────│               │
 │                 │                   │  File contents:         │               │
 │                 │  YAML content     │  enabled: true          │               │
 │                 ├──────────────────►│  group_ids: [...]       │               │
 │                 │                   │                         │               │
 │                 │                   │ Parse YAML → enabled    │               │
 │                 │                   │ = true → Graphiti       │               │
 │                 │                   │ available               │               │
 │                 │                   │                         │               │
 │                 │                   │ [Continue with design   │               │
 │                 │                   │  session, using         │               │
 │                 │                   │  guardkit graphiti CLI  │               │
 │                 │                   │  for seeding]           │               │
 │                 │                   │                         │               │
 │ "🏗️ Architecture│                  │                         │               │
 │  loaded..."     │◄─────────────────│                         │               │
 │◄────────────────│                   │                         │               │
```

**Fix**: Replace the Python pseudocode with a Read tool instruction. The LLM has a Read tool. Reading a YAML file is something it can do. No bridge script needed for the availability check — `graphiti-check` is still valuable for the full connectivity test if desired, but the basic availability signal is just a file read.

---

## Root Cause Analysis: Validated

### The Three System Boundaries

| Boundary | From | To | Crossing Mechanism |
|----------|------|----|--------------------|
| **B1**: User → LLM | User intent | Claude Code prompt | Skill tool (loads .md as prompt) |
| **B2**: LLM → OS | LLM reasoning | Shell commands | Bash tool |
| **B3**: OS → Infrastructure | Shell process | FalkorDB | Python client / TCP |

**The broken commands never cross B2.** They present Python code at the prompt level (B1) and expect it to somehow reach the infrastructure layer (B3) — but there's no mechanism for that. The LLM reads the Python as descriptive pseudocode and makes a reasoning-based judgment.

**The working command (/task-work) crosses all three boundaries**: prompt → Bash tool (B2) → graphiti-check Python process → FalkorDB ping (B3).

### Why the LLM Takes the `else` Branch

The command spec says: "you MUST execute these steps in order" and then shows:

```python
client = get_graphiti()
if client:
    ...
else:
    print("⚠️ Graphiti unavailable")
```

The LLM's reasoning chain:
1. "I need to execute `get_graphiti()` to get a client"
2. "This requires importing `guardkit.knowledge.graphiti_client`"
3. "I have no Python runtime and cannot import this module"
4. "Therefore `client` would be `None`"
5. "Therefore I follow the `else` branch"
6. Output: "Graphiti unavailable"

This is **correct LLM reasoning given incorrect instructions**. The LLM is not broken — the prompt is asking it to do something impossible.

### Live Verification

```bash
$ /Users/richardwoollcott/.agentecflow/bin/graphiti-check --status --quiet
{"available": true, "error": null, "context": null, "categories": 0, "tokens_used": 0, "tokens_budget": 0}
```

Graphiti IS available. The Python client, config, and FalkorDB connectivity all pass. The only thing broken is the command spec's instruction to the LLM.

### Additional Finding: `graphiti-check` Not on PATH

`~/.agentecflow/bin/` is not in `$PATH`. The `/task-work` command references `graphiti-check` as a bare command — this may work if the user's shell profile adds it, but it's fragile. The full path `/Users/richardwoollcott/.agentecflow/bin/graphiti-check` is more reliable, or a `Read` tool approach avoids PATH issues entirely.

---

## Architecture Score: 42/100 (revised from 45)

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - SRP | 5/10 | Command specs conflate "LLM instructions" with "Python implementation reference" |
| SOLID - OCP | 5/10 | Adding Graphiti to a new command requires copy-pasting the broken pattern |
| SOLID - LSP | 7/10 | N/A |
| SOLID - ISP | 5/10 | Commands present an interface (Python imports) that the consumer (LLM) cannot use |
| SOLID - DIP | 2/10 | **Critical**: All 8 commands depend on concrete Python class instantiation for a simple boolean check |
| DRY | 2/10 | **Critical**: Same broken pattern in 20+ locations across 8 files |
| YAGNI | 7/10 | The Python classes themselves are well-designed; the problem is how they're referenced |

**Score decreased** because the deeper analysis confirmed the DIP violation is more severe than initially assessed — the entire Graphiti integration surface area is broken, not just the availability check.

---

## Findings (Revised)

### Finding 1: Two Execution Models — Only One Works (CRITICAL, CONFIRMED)

The command spec system supports two execution models:

| Model | Mechanism | Python code blocks interpreted as | Works for Graphiti? |
|-------|-----------|-----------------------------------|---------------------|
| **A: Script delegation** | Command delegates to `python3 ~/.agentecflow/bin/<script>` | Executable code run by Python interpreter | Yes |
| **B: Markdown interpretation** | Full markdown injected as LLM prompt | Pseudocode describing intended behaviour | **No** |

`/system-design` uses Model B. The LLM sees the Python as behavioural intent, not executable code.

`/task-work` Phase 1.7 works because it uses **bash code blocks with explicit "Run" instructions** — which the LLM can execute via its Bash tool.

**Key quote from task-work.md (line 1703)**:
> "Instead, **run the Python check script via bash** as described below."

**Key quote from system-design.md (line 1132)**:
> "you MUST execute these steps in order" — followed by `python` code blocks

The difference: task-work explicitly tells the LLM *how* (Bash tool). system-design tells the LLM *what* (Python pseudocode) without a viable *how*.

### Finding 2: Broken Pattern Spans 20+ Code Block Instances Across 8 Commands

| Command | `get_graphiti()` instances | Other Python Graphiti calls |
|---------|---------------------------|----------------------------|
| `/system-design` | 3 (lines 50, 88, 1142) | `SystemDesignGraphiti`, `SystemPlanGraphiti`, `upsert_*` |
| `/system-arch` | 3 (lines 40, 62, 1003) | `has_architecture_context()`, `upsert_*`, `sanitise_for_graphiti()` |
| `/system-plan` | 3 (lines 46, 796, 1066) | `SystemPlanGraphiti`, context queries |
| `/system-overview` | 2 (lines 43, 287) | Architecture context queries |
| `/impact-analysis` | 2 (lines 92, 433) | `SystemPlanGraphiti`, impact queries |
| `/arch-refine` | 3 (lines 48, 76, 762) | `sanitise_for_graphiti()`, ADR context |
| `/design-refine` | 3 (lines 52, 89, 1029) | `SystemDesignGraphiti`, design updates |
| `/context-switch` | 1 (line 449) | Project context queries |

**Total**: ~20 `get_graphiti()` call sites + ~30 method calls on Graphiti objects = **~50 non-executable Python references** across the command spec corpus.

### Finding 3: Seeding Is Doubly Broken

Even if the availability check were fixed, the seeding phase (e.g., system-design Step 8) uses:

```python
design_sp.upsert_api_contract(contract)
```

The LLM cannot call Python methods on objects. Even with correct availability detection, the seeding step requires either:
- A CLI command (`guardkit graphiti add-context ...`) the LLM can run via Bash tool
- A separate Script Delegation model (Model A) for the seeding phase

### Finding 4: `graphiti-check` Not on PATH (NEW)

The `graphiti-check` wrapper lives at `~/.agentecflow/bin/graphiti-check` but `~/.agentecflow/bin/` is NOT in `$PATH`:

```
$ which graphiti-check
graphiti-check not found
```

This means even the working `/task-work` pattern is fragile — it works only if:
- The user's shell profile adds `~/.agentecflow/bin` to PATH, or
- Claude Code resolves the wrapper via some other mechanism

The Read-based approach (reading `.guardkit/graphiti.yaml` directly) avoids this entirely.

### Finding 5: Group ID Configuration Is By Design (DOWNGRADED)

The `group_ids` in `graphiti.yaml` (`product_knowledge`, `command_workflows`, `architecture_decisions`) are **seeding groups**, not an exhaustive registry. `SystemDesignGraphiti` uses `project_design` and `api_contracts` which are auto-prefixed by `GraphitiClient.get_group_id()`. This is working as designed in the Python layer — the only issue is that the command spec presents these groups in non-executable Python code.

### Finding 6: Import Path Inconsistency (CONFIRMED)

`/system-arch` and `/system-plan` reference `guardkit.knowledge.graphiti_service` (doesn't exist as a file). All other commands reference `guardkit.knowledge.graphiti_client` (exists). Since these are pseudocode anyway, the inconsistency is cosmetic — but it adds to the confusion about whether these are meant to be executable.

---

## Revised Recommendations

### Recommendation 1: Replace Python Pseudocode with Tool-Native Instructions (CRITICAL)

**Two-tier approach for the availability check:**

**Tier 1 (Simple — Read tool):** For the availability boolean, instruct the LLM to read the config file:

```markdown
### Step 1: Check Graphiti Availability

Use the Read tool to read `.guardkit/graphiti.yaml`.

**IF** the file exists and contains `enabled: true`:
  - SET graphiti_available = true
  - Note the configured group_ids and connection details

**IF** the file does not exist, or `enabled:` is false or missing:
  - SET graphiti_available = false
  - DISPLAY: "⚠️ Graphiti unavailable — continuing with markdown artefacts only"
```

**Tier 2 (Full connectivity — Bash tool):** For commands that need live Graphiti access (seeding):

```markdown
### Graphiti Connectivity Check (optional)

Run via Bash tool to verify FalkorDB is reachable:

```bash
/Users/richardwoollcott/.agentecflow/bin/graphiti-check --status --quiet
```

Parse JSON: `{"available": true|false, "error": "..."|null}`
```

**Effort**: 1-2 days across all 8 commands
**Impact**: Fixes the root cause for all affected commands

### Recommendation 2: Replace Python Seeding Pseudocode with CLI Commands (HIGH)

For seeding phases, replace:
```python
design_sp.upsert_api_contract(contract)  # LLM can't do this
```

With:
```markdown
**IF graphiti_available**, generate and display seeding commands:

```bash
guardkit graphiti add-context docs/design/contracts/{context}-api.yaml \
  --group project_design

guardkit graphiti add-context docs/design/decisions/DDR-{NNN}.md \
  --group architecture_decisions
```

Ask user: "Run these seeding commands now? [Y/n]"
If yes, execute each via Bash tool.
```

**Effort**: Medium (each command's seeding phase needs rewriting)
**Impact**: Makes Graphiti seeding actually work

### Recommendation 3: Create Shared Graphiti Preamble (MEDIUM)

Create `installer/core/commands/lib/graphiti-preamble.md`:

```markdown
## Graphiti Availability Check

1. Use the Read tool to read `.guardkit/graphiti.yaml`
2. If file exists and `enabled: true` → graphiti_available = true
3. If missing or disabled → graphiti_available = false, warn user
4. For full connectivity: run `graphiti-check --status --quiet` via Bash tool
```

Each command references this instead of duplicating the pattern.

**Effort**: Low
**Impact**: Single point of maintenance, prevents future drift

### Recommendation 4: Fix `graphiti-check` PATH Issue (MEDIUM)

Either:
- Use absolute path in command specs: `~/.agentecflow/bin/graphiti-check`
- Or add `~/.agentecflow/bin` to PATH in installer's shell profile setup
- Or prefer the Read-based approach (Recommendation 1 Tier 1) which avoids PATH entirely

**Effort**: Low
**Impact**: Makes the existing /task-work integration more robust

### Recommendation 5: Harmonise Import Paths and Document Group IDs (LOW)

- Replace `graphiti_service` → `graphiti_client` in system-arch, system-plan pseudocode
- Add group ID registry to `graphiti-knowledge.md`

**Effort**: Low
**Impact**: Cosmetic clarity

---

## Decision Matrix (Revised)

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| Fix all 8 commands (Read-based check + CLI seeding) | 98 | 2-3 days | Low | **Recommended** |
| Fix system-design only as pilot, then roll out | 80 | 4-6 hours | Low | Good starting point |
| Create shared preamble first, then fix all | 95 | 3-4 days | Low | Best architecture |
| Do nothing | 5 | None | Critical | Entire Graphiti pipeline broken |

---

## Appendix A: Affected Files

| File | Lines | Python pseudocode blocks to replace |
|------|-------|-------------------------------------|
| `installer/core/commands/system-design.md` | 1338 | 3 availability + 1 seeding |
| `installer/core/commands/system-arch.md` | ~1160 | 3 availability + 1 seeding |
| `installer/core/commands/system-plan.md` | ~1070 | 3 availability + 1 seeding |
| `installer/core/commands/system-overview.md` | ~300 | 2 availability |
| `installer/core/commands/impact-analysis.md` | ~440 | 2 availability |
| `installer/core/commands/arch-refine.md` | ~960 | 3 availability + 1 seeding |
| `installer/core/commands/design-refine.md` | ~1150 | 3 availability + 1 seeding |
| `installer/core/commands/context-switch.md` | ~450 | 1 availability |
| `installer/core/commands/lib/graphiti-preamble.md` | New | Shared availability check |
| `.claude/rules/graphiti-knowledge.md` | Existing | Add group ID registry |

## Appendix B: Pattern Comparison (Three Variants)

**BROKEN (current)** — Python pseudocode, LLM can't execute:
```python
from guardkit.knowledge.graphiti_client import get_graphiti
client = get_graphiti()  # ← LLM has no Python runtime
if client:
    ...  # Never reached
else:
    print("Graphiti unavailable")  # Always reached
```

**WORKING (task-work)** — Bash command, LLM can execute:
```markdown
Run the graphiti check wrapper:
```bash
graphiti-check --status --quiet
```
Parse JSON output...
```

**PROPOSED (simplest)** — Read tool, LLM can execute:
```markdown
Read `.guardkit/graphiti.yaml` using the Read tool.
If the file exists and contains `enabled: true`, Graphiti is available.
```

## Appendix C: Live Test Results

```
$ /Users/richardwoollcott/.agentecflow/bin/graphiti-check --status --quiet
{"available": true, "error": null, "context": null, "categories": 0, "tokens_used": 0, "tokens_budget": 0}

$ cat .guardkit/graphiti.yaml | grep enabled
enabled: true
```

Both methods confirm Graphiti is available. The system-design command never checks either way.
