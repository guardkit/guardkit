# Review Report: TASK-REV-GA01

## Executive Summary

**Review**: Global Agent Stack Filtering During Template Initialization
**Mode**: Architectural Review
**Depth**: Standard (Revised)
**Date**: 2025-12-03
**Duration**: ~60 minutes
**Status**: REVIEW COMPLETE (REVISED)

### Key Findings

1. **Root Cause Identified**: The `init-project.sh` script copies ALL global agents unconditionally (lines 209-223), ignoring the `stack` metadata already present in agent frontmatter.

2. **Deeper Architectural Issue Discovered**: Stack-specific agents exist in **TWO places**:
   - **Global agents** (`installer/core/agents/`): `python-api-specialist`, `react-state-specialist`, `dotnet-domain-specialist`, etc.
   - **Template agents** (`installer/core/templates/*/agents/`): `fastapi-specialist`, `feature-architecture-specialist`, etc.

3. **Redundancy Concern**: There's overlap between global and template agents:
   - `python-api-specialist` (global) vs `fastapi-specialist` (fastapi-python template)
   - `react-state-specialist` (global) vs `react-query-specialist` (react-typescript template)
   - Both serve similar purposes for the same stack

4. **Revised Recommendation**: **Approach E (Move Stack-Specific Agents to Templates)** - cleaner architecture that aligns with the template philosophy.

---

## Review Details

### Scope Analyzed

| Component | Files Examined |
|-----------|---------------|
| Installation script | `installer/scripts/install.sh` |
| Project init script | `installer/scripts/init-project.sh` |
| Global agents | 19 agents in `installer/core/agents/` |
| Template manifests | 4 manifest.json files |
| Agent discovery docs | `docs/guides/agent-discovery-guide.md` |

---

## Current State Analysis

### Agent Inventory by Stack

**Stack-Specific Agents (5 total)**:
| Agent | Stack | MCP Dependencies |
|-------|-------|------------------|
| `react-state-specialist` | `[react, typescript]` | None |
| `python-api-specialist` | `[python]` | None |
| `dotnet-domain-specialist` | `[dotnet]` | None |
| `figma-react-orchestrator` | `[react, typescript]` | figma-dev-mode (required) |
| `zeplin-maui-orchestrator` | `[dotnet, maui, xaml]` | zeplin (required) |

**Cross-Stack Agents (14 total)**:
All marked with `stack: [cross-stack]` - universally applicable.

### Current Installation Logic (init-project.sh)

```bash
# Lines 209-223: Copies ALL global agents unconditionally
for agent_file in "$AGENTECFLOW_HOME/agents"/*.md; do
    if [ -f "$agent_file" ]; then
        local agent_name=$(basename "$agent_file")
        # Only copy if file doesn't already exist (template takes precedence)
        if [ ! -f ".claude/agents/$agent_name" ]; then
            cp "$agent_file" ".claude/agents/$agent_name"
            ((global_agent_count++))
        fi
    fi
done
```

**Problem**: No stack filtering - copies all 19 agents to every project.

### Template Manifest Structure

Templates already declare their stack via manifest.json:
- `react-typescript`: `language: "TypeScript"`, frameworks include React
- `fastapi-python`: `language: "Python"`, frameworks include FastAPI
- `default`: `language: "generic"` (language-agnostic)

**Key insight**: The infrastructure for stack-based filtering already exists - it just isn't used.

---

## Approach Evaluation

### Approach A: Stack-Based Filtering (RECOMMENDED)

**Implementation**:
1. Parse template manifest to extract stack identifiers
2. Parse agent frontmatter to extract `stack` field
3. Filter: Install if `stack: [cross-stack]` OR stack matches template
4. Fall back to all agents for `default` template

**Pros**:
- Uses existing metadata infrastructure
- Clean, minimal project agent folders
- Accurate stack matching
- Easy to understand and maintain

**Cons**:
- Requires parsing agent YAML frontmatter in bash (or call Python)
- Templates without manifests need fallback behavior

**Complexity**: Low-Medium (4-8 hours)

**Implementation Sketch**:
```bash
# Pseudocode for init-project.sh modification
get_template_stacks() {
    # Extract from manifest.json: language, frameworks
    # Return: ["python"] or ["react", "typescript"] etc.
}

should_install_agent() {
    local agent_file=$1
    local template_stacks=$2

    # Parse agent frontmatter for stack field
    local agent_stack=$(grep "^stack:" "$agent_file" | sed 's/stack: //')

    # Always install cross-stack agents
    if [[ "$agent_stack" == *"cross-stack"* ]]; then
        return 0
    fi

    # Check if any template stack matches agent stack
    for stack in $template_stacks; do
        if [[ "$agent_stack" == *"$stack"* ]]; then
            return 0
        fi
    done

    return 1
}
```

### Approach B: Lazy Discovery (No Installation)

**Implementation**:
1. Don't copy agents to `.claude/agents/` at all
2. Symlink to global agents directory
3. Agent discovery filters at runtime based on project context

**Pros**:
- Zero duplication across projects
- Automatic updates when global agents change
- Already how commands work (symlinked)

**Cons**:
- Changes current architecture (agents copied, commands symlinked)
- Removes ability to customize agents per-project
- Requires runtime stack detection (already implemented)
- Users expect to see agents in their project folder

**Complexity**: Medium (8-16 hours)

**Assessment**: Architecturally clean but breaks user expectations and removes customization capability. NOT RECOMMENDED.

### Approach C: Opt-In Installation

**Implementation**:
1. Install only cross-stack agents by default
2. Add `--with-agents=react,python` flag to guardkit init
3. Or prompt user during interactive init

**Pros**:
- User control over agent selection
- Minimal default installation

**Cons**:
- Extra cognitive load for users
- Users may not know which agents they need
- Additional onboarding friction

**Complexity**: Low-Medium (4-8 hours)

**Assessment**: Adds friction without significant benefit. NOT RECOMMENDED unless user research shows demand.

### Approach D: Status Quo + Documentation

**Implementation**:
1. Keep current behavior (install all agents)
2. Add note to init output: "Unused agents are ignored at runtime"
3. Document that agent discovery filters irrelevant agents

**Pros**:
- Zero code changes
- Simple solution

**Cons**:
- Cluttered project folders (19 agents vs ~16-17 relevant)
- Potential confusion ("why do I have react-state-specialist?")
- Wastes disk space (minimal, but principle matters)

**Complexity**: Trivial (1 hour)

**Assessment**: Acceptable short-term but unsatisfying UX. NOT RECOMMENDED as long-term solution.

---

## Revised Analysis: Why Are Stack-Specific Agents in Global?

### The Architectural Question

The deeper question raised during review revision:

> **"Should stack-specific agents exist in global agents at all?"**

### Current Architecture

```
installer/core/
├── agents/                          # Global agents (19 total)
│   ├── task-manager.md             # cross-stack ✓
│   ├── architectural-reviewer.md    # cross-stack ✓
│   ├── code-reviewer.md             # cross-stack ✓
│   ├── python-api-specialist.md     # python ONLY ⚠️
│   ├── react-state-specialist.md    # react ONLY ⚠️
│   ├── dotnet-domain-specialist.md  # dotnet ONLY ⚠️
│   ├── figma-react-orchestrator.md  # react ONLY ⚠️
│   └── zeplin-maui-orchestrator.md  # dotnet ONLY ⚠️
│
└── templates/
    ├── fastapi-python/agents/       # Template-specific agents
    │   ├── fastapi-specialist.md    # Overlaps with python-api-specialist
    │   ├── fastapi-database-specialist.md
    │   └── fastapi-testing-specialist.md
    │
    ├── react-typescript/agents/
    │   ├── react-query-specialist.md  # Overlaps with react-state-specialist
    │   ├── feature-architecture-specialist.md
    │   └── form-validation-specialist.md
    │
    └── nextjs-fullstack/agents/
        ├── nextjs-fullstack-specialist.md
        └── ...
```

### The Problem

**Redundancy**: We have TWO layers of stack-specific agents:
1. **Global stack agents**: Generic stack specialists (python-api, react-state, dotnet-domain)
2. **Template stack agents**: Framework-specific specialists (fastapi-specialist, react-query-specialist)

**Confusion**:
- When using `fastapi-python` template, user gets BOTH `python-api-specialist` (global) AND `fastapi-specialist` (template)
- These agents have significant overlap in purpose and capabilities
- Which one should the agent discovery prefer?

### Historical Reason (Hypothesis)

The global stack-specific agents likely exist for:
1. **Fallback coverage**: If someone uses `default` template but writes Python, they still get a Python specialist
2. **Discovery system support**: Runtime discovery can match based on file extensions even without template-specific agents
3. **Incremental development**: Added before the template agent system was mature

### Alternative Architecture: Templates Own Stack Agents

```
installer/core/
├── agents/                          # ONLY cross-stack agents (14 total)
│   ├── task-manager.md             # orchestration
│   ├── architectural-reviewer.md    # review
│   ├── code-reviewer.md             # review
│   ├── test-orchestrator.md         # testing
│   ├── security-specialist.md       # review
│   ├── devops-specialist.md         # implementation
│   ├── database-specialist.md       # implementation
│   └── ...                          # All cross-stack
│
└── templates/
    ├── fastapi-python/agents/
    │   ├── python-api-specialist.md     # MOVED from global
    │   ├── fastapi-specialist.md
    │   └── ...
    │
    ├── react-typescript/agents/
    │   ├── react-state-specialist.md    # MOVED from global
    │   ├── figma-react-orchestrator.md  # MOVED from global
    │   └── ...
    │
    ├── dotnet-*/agents/                 # (if we add .NET templates)
    │   ├── dotnet-domain-specialist.md  # MOVED from global
    │   ├── zeplin-maui-orchestrator.md  # MOVED from global
    │   └── ...
    │
    └── default/agents/
        └── (empty or minimal)           # Language-agnostic by design
```

---

## Recommendation (Revised)

### Primary Recommendation: Approach E (Refined)

**Move, Archive, or Delete Stack-Specific Agents Based on Value**

After analyzing overlap between global and template agents, the refined recommendation:

| Agent | Action | Rationale |
|-------|--------|-----------|
| `python-api-specialist` | **DELETE** | Redundant with `fastapi-specialist` (template) - both cover FastAPI patterns |
| `react-state-specialist` | **MOVE to react-typescript** | Valuable Zustand + client state coverage not in template agents |
| `figma-react-orchestrator` | **MOVE to react-typescript** | React-specific design integration |
| `dotnet-domain-specialist` | **DELETE** | No .NET template exists; recreate when template added |
| `zeplin-maui-orchestrator` | **ARCHIVE** | Archive to `tasks/backlog/design-url-integration/` for future use |

**Rationale**:
1. **Single source of truth**: Templates own their complete agent set
2. **No filtering needed**: `init-project.sh` copies global (cross-stack only) + template agents
3. **Eliminates redundancy**: Delete agents that duplicate template coverage
4. **Preserves value**: Move agents with unique content to templates
5. **Future-proofs**: Archive agents for features not yet implemented

### Analysis: `react-state-specialist` vs Template Agents

| Content | `react-state-specialist` | Template Agents |
|---------|-------------------------|-----------------|
| TanStack Query | ✅ Covered | ✅ `react-query-specialist` (deeper) |
| Zustand | ✅ Covered | ❌ Not in templates |
| Context + useReducer | ✅ Covered | ❌ Not in templates |
| State location guide | ✅ Covered | ❌ Not in templates |
| Feature organization | ❌ | ✅ `feature-architecture-specialist` |
| Forms | Mentioned | ✅ `form-validation-specialist` |

**Conclusion**: `react-state-specialist` adds value (Zustand, Context patterns) → **MOVE to template**

### Implementation Plan (Final)

**Phase 1: Delete Redundant Agents** (30 min)
- Delete `installer/core/agents/python-api-specialist.md`
- Delete `installer/core/agents/dotnet-domain-specialist.md`

**Phase 2: Archive Design Integration Agents** (30 min)
- Create `tasks/backlog/design-url-integration/` directory
- Move `installer/core/agents/figma-react-orchestrator.md` → archive
- Move `installer/core/agents/zeplin-maui-orchestrator.md` → archive
- Create task to remove documentation references

**Phase 3: Move React Agent to Template** (30 min)
- Move `installer/core/agents/react-state-specialist.md` → `installer/core/templates/react-typescript/agents/`
- Also copy to `nextjs-fullstack/agents/` (Next.js uses React)

**Phase 4: Update init-project.sh** (0 hours)
- No changes needed! Current logic already:
  1. Copies template agents first
  2. Copies global agents (but skips if file exists)
- With stack agents removed, global only has cross-stack, so all get copied

**Phase 5: Update Documentation** (1 hour)
- Update CLAUDE.md agent inventory
- Update agent discovery guide
- Remove `/figma-to-react` and `/zeplin-to-maui` command references
- Create task for future design integration implementation

**Phase 6: Create Follow-up Task** (15 min)
- Create task: "Remove design integration command references from documentation"
- Link to archived agents for context

### Alternative: Approach A (Stack-Based Filtering)

If moving agents is deemed too disruptive:

**Implementation**:
1. Parse template manifest to get stack identifiers
2. Parse agent frontmatter to get `stack` field
3. Filter: Install if `stack: [cross-stack]` OR stack matches template
4. Fallback to all agents for `default` template

**Complexity**: Low-Medium (4-8 hours)

This preserves current architecture but adds filtering logic.

### Stack Mapping

| Template | Language | Stacks to Match |
|----------|----------|-----------------|
| react-typescript | TypeScript | `react`, `typescript` |
| fastapi-python | Python | `python` |
| nextjs-fullstack | TypeScript | `react`, `typescript` |
| react-fastapi-monorepo | TypeScript + Python | `react`, `typescript`, `python` |
| default | generic | ALL (no filtering) |
| Custom (no manifest) | unknown | ALL (fallback) |

### Fallback Behavior

For templates without manifest or with unknown stacks, install ALL agents (current behavior). This ensures backwards compatibility.

---

## Impact Assessment

### Positive Impacts

1. **Cleaner Projects**: 5 fewer irrelevant agents in project folder
2. **Reduced Confusion**: No "why is react-state-specialist here?" questions
3. **Faster Init**: Slightly faster (fewer file copies)
4. **Better UX**: Projects feel right-sized for their stack

### Negative Impacts

1. **Minor Complexity**: Adds parsing logic to init script
2. **Edge Cases**: Must handle missing manifests gracefully

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False negatives (missing needed agent) | Low | Medium | Fallback to all for unknown stacks |
| Breaking existing projects | None | N/A | Only affects new inits |
| Manifest parsing fails | Low | Low | Fallback to install all |

---

## Decision Options (Final)

| Option | Action | Effort | Recommendation |
|--------|--------|--------|----------------|
| **[E]** | Implement Approach E (Refined): Delete/Move/Archive per agent | 2-3 hours | **RECOMMENDED** |
| **[A]** | Implement Approach A: Stack-based filtering (keep agents in global) | 4-8 hours | Alternative |
| **[I]mplement** | Create implementation task for Approach E | Immediate | If [E] chosen |
| **[C]ancel** | Discard review | - | Not recommended |

### Decision Summary (Final)

**Approach E (Refined)** is recommended:

| Agent | Action | Why |
|-------|--------|-----|
| `python-api-specialist` | DELETE | Redundant with `fastapi-specialist` |
| `dotnet-domain-specialist` | DELETE | No .NET template exists |
| `react-state-specialist` | MOVE to react templates | Unique Zustand/Context coverage |
| `figma-react-orchestrator` | ARCHIVE | Future design integration |
| `zeplin-maui-orchestrator` | ARCHIVE | Future design integration |

**Result**: Global agents become cross-stack only (14 agents). Stack-specific agents live in their respective templates.

**Benefits**:
1. Cleaner separation (global = universal, template = specialized)
2. No filtering needed - architecture solves the problem
3. Eliminates redundancy with template agents
4. Preserves valuable content (react-state-specialist moved)
5. Future-proofs design integration (agents archived)

---

## Appendix

### Files Modified (If Implementing)

1. `installer/scripts/init-project.sh` - Add stack filtering logic
2. (Optional) `installer/core/lib/stack_filter.py` - Parser utility

### Agent Stack Matrix (Complete)

| Agent | Stack | Phase | Install Condition |
|-------|-------|-------|-------------------|
| task-manager | cross-stack | orchestration | ALWAYS |
| architectural-reviewer | cross-stack | review | ALWAYS |
| code-reviewer | cross-stack | review | ALWAYS |
| test-orchestrator | cross-stack | testing | ALWAYS |
| test-verifier | cross-stack | testing | ALWAYS |
| security-specialist | cross-stack | review | ALWAYS |
| devops-specialist | cross-stack | implementation | ALWAYS |
| database-specialist | cross-stack | implementation | ALWAYS |
| debugging-specialist | cross-stack | debugging | ALWAYS |
| git-workflow-manager | cross-stack | cross-stack | ALWAYS |
| pattern-advisor | cross-stack | cross-stack | ALWAYS |
| build-validator | cross-stack | cross-stack | ALWAYS |
| complexity-evaluator | cross-stack | orchestration | ALWAYS |
| agent-content-enhancer | cross-stack | cross-stack | ALWAYS |
| react-state-specialist | react, typescript | implementation | IF react/typescript |
| python-api-specialist | python | implementation | IF python |
| dotnet-domain-specialist | dotnet | implementation | IF dotnet |
| figma-react-orchestrator | react, typescript | orchestration | IF react/typescript |
| zeplin-maui-orchestrator | dotnet, maui, xaml | orchestration | IF dotnet/maui |

### Template Stack Detection Logic

```python
# Pseudocode for stack detection from manifest
def get_template_stacks(manifest_path: str) -> list[str]:
    manifest = json.load(open(manifest_path))
    stacks = []

    # Map language to stack
    language = manifest.get("language", "").lower()
    if language in ["typescript", "javascript"]:
        stacks.append("typescript")
    elif language == "python":
        stacks.append("python")
    elif language in ["c#", "csharp"]:
        stacks.append("dotnet")

    # Check frameworks for additional stacks
    for fw in manifest.get("frameworks", []):
        name = fw.get("name", "").lower()
        if "react" in name:
            stacks.append("react")
        if "fastapi" in name or "django" in name:
            stacks.append("python")
        if "maui" in name or ".net" in name:
            stacks.append("dotnet")

    return list(set(stacks)) or ["all"]  # Fallback to all
```

---

## Review Metadata

```yaml
review_id: TASK-REV-GA01
status: REVIEW_COMPLETE (REVISED)
mode: architectural
depth: standard (revised)
score: N/A (decision review)
findings_count: 4
recommendations_count: 2 (primary + alternative)
primary_decision: Approach E (Move Stack Agents to Templates)
alternative_decision: Approach A (Stack-Based Filtering)
implementation_complexity:
  approach_e: 4-6 hours
  approach_a: 4-8 hours
revision_note: "Revised to question why stack-specific agents exist in global at all"
```
