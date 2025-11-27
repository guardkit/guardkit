---
id: TASK-ENF5-v2
title: Document dynamic agent discovery in task-work
status: in_review
created: 2025-11-27T17:30:00Z
updated: 2025-11-27T20:30:00Z
priority: high
tags: [documentation, agent-discovery, task-work, dynamic-discovery]
task_type: implementation
epic: null
feature: agent-invocation-enforcement
requirements: []
dependencies: [TASK-ENF-P0-1, TASK-ENF-P0-2]
complexity: 3
effort_estimate: 2-3 hours
related_to: TASK-REV-9A4E
supersedes: TASK-ENF5
---

# TASK-ENF5-v2: Document Dynamic Agent Discovery in task-work

## Context

**From TASK-REV-9A4E Review (Finding #3)**: The old TASK-ENF5 approach of maintaining a static agent selection table is fundamentally wrong because:
1. Hardcodes global agent names only (ignores local template overrides)
2. Cannot accommodate template customizations
3. Requires manual maintenance as templates evolve
4. Contradicts the dynamic agent discovery system design

**New Approach**: Document how dynamic agent discovery works, including precedence rules and how templates can override global agents. No static tables - discovery is based on metadata matching.

**This task replaces**: TASK-ENF5 (blocked/superseded)

---

## Objective

Document dynamic agent discovery in `/task-work` to:
1. Explain how agents are selected based on metadata (not static tables)
2. Document precedence rules (Local > User > Global > Template)
3. Show how templates can override global agents
4. Provide troubleshooting guidance for "agent not found" issues
5. Remove or update any misleading static agent tables

---

## Requirements

### R1: Document Dynamic Discovery Mechanism

**Requirement**: Add section explaining how agent discovery works

**Location**: `installer/global/commands/task-work.md`

**Content to Add**:
```markdown
## Agent Discovery System

**Dynamic Metadata-Based Matching**

Agents are selected dynamically based on metadata matching, NOT from static tables. The system:

1. Analyzes task context (stack, phase, keywords from description)
2. Scans all agent sources for metadata matches
3. Returns best match based on:
   - Stack compatibility (python, react, dotnet, etc.)
   - Phase alignment (implementation, review, testing, orchestration, debugging)
   - Keyword relevance (capabilities match task requirements)

**No Hardcoded Mappings**: Agent selection is intelligent and extensible - adding new agents automatically makes them discoverable.

### Discovery Sources and Precedence

Agents are discovered from 4 sources in priority order:

1. **Local** (`.claude/agents/`) - Highest priority
   - Template agents copied during initialization
   - Project-specific customizations
   - **Always takes precedence** over global agents with same name

2. **User** (`~/.agentecflow/agents/`)
   - Personal agent customizations
   - Available across all projects
   - Overrides global agents with same name

3. **Global** (`installer/global/agents/`)
   - Built-in Taskwright agents
   - Shared across all users
   - Overridden by local/user agents

4. **Template** (`installer/global/templates/*/agents/`) - Lowest priority
   - Template-provided agents (before initialization)
   - Only used if agent not found in higher-priority sources
   - Replaced by local agents after `taskwright init`

**Precedence Rule**: Local > User > Global > Template

### Template Override Behavior

When you run `taskwright init <template>`:
- Template agents copied to `.claude/agents/` (local)
- Local agents now **override** global agents with same name
- Enables template customization without modifying global agents

**Example**:
```bash
# Before initialization
/task-work TASK-001  # Uses global python-api-specialist

# After initialization
taskwright init fastapi-python
# Template's python-api-specialist copied to .claude/agents/

/task-work TASK-002  # Now uses LOCAL python-api-specialist 📁 (not global 🌐)
```

### Metadata Requirements for Discovery

For an agent to be discoverable, it must have:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `stack` | array | ✅ Yes | Technology stack(s) the agent supports |
| `phase` | string | ✅ Yes | Workflow phase (implementation, review, testing, etc.) |
| `capabilities` | array | ✅ Yes | Specific skills and domains |
| `keywords` | array | ✅ Yes | Searchable terms for matching |

**Agents without metadata**: Skipped during discovery (graceful degradation).

### Fallback Behavior

If no specialist agent is found:
- System falls back to `task-manager` (cross-stack orchestrator)
- Task-manager handles the task generically
- User notified about fallback in invocation log

### Troubleshooting Agent Discovery

**Issue**: "Expected agent not selected"

**Debug Steps**:
1. Check agent has required metadata (stack, phase, capabilities, keywords)
2. Verify stack matches task technology (check file extensions)
3. Check agent source in invocation log (📁 local, 👤 user, 🌐 global, 📦 template)
4. Verify precedence isn't causing unexpected override

**Issue**: "Task-manager used instead of specialist"

**Causes**:
- No specialist agent exists for the stack
- Agent metadata doesn't match task context
- Agent missing required metadata fields

**Fix**: Run `/agent-enhance` to add/validate discovery metadata.
```

**Acceptance Criteria**:
- [ ] Dynamic discovery mechanism documented
- [ ] Precedence rules clearly explained
- [ ] Template override behavior described
- [ ] Metadata requirements listed
- [ ] Troubleshooting guide provided

---

### R2: Update or Remove Static Agent Table

**Requirement**: Remove or update any static agent selection tables

**Current Table** (task-work.md lines 968-973, may vary):
```markdown
| Stack | Analysis | Planning | Arch Review | Implementation | Testing | Review |
|-------|----------|----------|-------------|----------------|---------|--------|
| **maui** | requirements-analyst | maui-usecase-specialist | architectural-reviewer | maui-usecase-specialist | dotnet-testing-specialist | code-reviewer |
| **react** | requirements-analyst | react-state-specialist | architectural-reviewer | react-state-specialist | react-testing-specialist | code-reviewer |
| **python** | requirements-analyst | python-api-specialist | architectural-reviewer | python-api-specialist | python-testing-specialist | code-reviewer |
| **python-mcp** | requirements-analyst | python-mcp-specialist | architectural-reviewer | python-mcp-specialist | python-testing-specialist | code-reviewer |
```

**Options**:

**Option A: Remove Entirely** (Recommended)
- Delete static table
- Replace with reference to dynamic discovery section
- Emphasize metadata-based selection

**Option B: Update as "Example Agents by Stack"**
- Rename to "Example Agents" (not authoritative)
- Add disclaimer: "Discovery is dynamic - actual agent selected depends on metadata and precedence"
- Show source indicators (📁 📦 🌐)
- Note: Local agents override these examples

**Recommendation**: **Option A** (Remove entirely)

**Rationale**:
- Static tables imply hardcoded selection (misleading)
- Discovery is dynamic, not based on tables
- Table becomes stale as agents evolve
- Precedence makes any static list incomplete

**Replacement**:
```markdown
## Agent Selection

Agents are selected dynamically based on metadata matching. The system:
1. Analyzes task context (stack, phase, keywords)
2. Scans all agent sources (local, user, global, template)
3. Returns best match based on metadata

**See**: [Agent Discovery System](#agent-discovery-system) for details.

**To view available agents**: Run `/agent-list` or check:
- Local: `.claude/agents/`
- User: `~/.agentecflow/agents/`
- Global: `installer/global/agents/`
```

**Acceptance Criteria**:
- [ ] Static table removed or clearly marked as "Example Only"
- [ ] Replacement text references dynamic discovery
- [ ] No implication of hardcoded agent selection
- [ ] Users understand agents selected by metadata, not tables

---

### R3: Add Agent Discovery Examples

**Requirement**: Provide concrete examples of discovery in action

**Content to Add**:
```markdown
## Agent Discovery Examples

### Example 1: Python API Implementation

**Task Context**:
- Stack: Python
- Files: `*.py`
- Keywords: "FastAPI endpoint", "async", "Pydantic schema"

**Discovery Process**:
1. Detect stack: `python` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Extract keywords: `api`, `async`, `pydantic`
4. Scan agents:
   - Local `.claude/agents/python-api-specialist.md` ✅ Match
   - Metadata: `stack: [python, fastapi]`, `phase: implementation`, `keywords: [api, async, pydantic]`
5. **Selected**: `python-api-specialist 📁 (source: local)`

### Example 2: React State Management

**Task Context**:
- Stack: React
- Files: `*.tsx`
- Keywords: "hooks", "state", "TanStack Query"

**Discovery Process**:
1. Detect stack: `react` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Extract keywords: `hooks`, `state`, `query`
4. Scan agents:
   - Local `.claude/agents/react-state-specialist.md` ✅ Match
   - Metadata: `stack: [react, typescript]`, `phase: implementation`, `keywords: [hooks, state, query]`
5. **Selected**: `react-state-specialist 📁 (source: local)`

### Example 3: Architectural Review (Cross-Stack)

**Task Context**:
- Stack: Any
- Phase: Architectural Review (Phase 2.5B)

**Discovery Process**:
1. Phase: `review` (architectural)
2. Scan agents:
   - Global `installer/global/agents/architectural-reviewer.md` ✅ Match
   - Metadata: `stack: [cross-stack]`, `phase: review`, `keywords: [solid, dry, yagni, architecture]`
3. **Selected**: `architectural-reviewer 🌐 (source: global)`

### Example 4: Fallback to Task-Manager

**Task Context**:
- Stack: Go
- Files: `*.go`
- Keywords: "service", "handler"

**Discovery Process**:
1. Detect stack: `go` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Scan agents:
   - No agents with `stack: [go]` found
4. **Fallback**: `task-manager 🌐 (source: global)`
5. **Note**: User notified that task-manager used (no Go specialist available)

**Fix**: Create go-specialist agent with appropriate metadata, or use cross-stack task-manager.
```

**Acceptance Criteria**:
- [ ] At least 3 discovery examples provided
- [ ] Examples cover different stacks and phases
- [ ] Source indicators shown (📁 🌐 📦)
- [ ] Fallback behavior demonstrated
- [ ] Examples reference actual agent metadata

---

### R4: Document Agent Source Logging

**Requirement**: Explain agent source indicators in invocation log

**Content to Add**:
```markdown
## Agent Source Indicators

During task execution, the invocation log shows which agent was selected and its source:

```
═══════════════════════════════════════════════════════
AGENT INVOCATIONS LOG
═══════════════════════════════════════════════════════
✅ Phase 2 (Planning): python-api-specialist 📁 (source: local, completed in 45s)
✅ Phase 2.5B (Arch Review): architectural-reviewer 🌐 (source: global, completed in 30s)
✅ Phase 3 (Implementation): python-api-specialist 📁 (source: local, completed in 120s)
✅ Phase 4 (Testing): task-manager 🌐 (source: global, completed in 60s)
✅ Phase 5 (Review): code-reviewer 🌐 (source: global, completed in 25s)
═══════════════════════════════════════════════════════
```

**Source Icons**:
- 📁 **Local** - Agent from `.claude/agents/` (template or custom)
- 👤 **User** - Agent from `~/.agentecflow/agents/` (personal)
- 🌐 **Global** - Agent from `installer/global/agents/` (built-in)
- 📦 **Template** - Agent from `installer/global/templates/*/agents/` (before init)

**Why Source Matters**:
- **Local agents override global** - Verify template customizations working
- **Precedence debugging** - Understand which agent was selected when duplicates exist
- **Troubleshooting** - If wrong agent selected, check source and metadata
```

**Acceptance Criteria**:
- [ ] Source indicators documented
- [ ] Icons explained (📁 👤 🌐 📦)
- [ ] Precedence implications clarified
- [ ] Example invocation log shown

---

## Implementation Plan

### Phase 1: Write Dynamic Discovery Section

**Files**: `installer/global/commands/task-work.md`

**Implementation**:
1. Add "Agent Discovery System" section (R1)
2. Document precedence rules
3. Explain template override behavior
4. Add metadata requirements table
5. Add troubleshooting guide

**Duration**: 1 hour

### Phase 2: Remove/Update Static Table

**Files**: `installer/global/commands/task-work.md`

**Implementation**:
1. Locate static agent selection table (search for "| Stack |")
2. Remove table (Option A) or update with disclaimer (Option B)
3. Add replacement text referencing dynamic discovery
4. Link to "Agent Discovery System" section

**Duration**: 30 minutes

### Phase 3: Add Discovery Examples

**Files**: `installer/global/commands/task-work.md`

**Implementation**:
1. Add "Agent Discovery Examples" section (R3)
2. Write 4 examples (Python, React, Arch Review, Fallback)
3. Show discovery process step-by-step
4. Include source indicators

**Duration**: 1 hour

### Phase 4: Document Source Logging

**Files**: `installer/global/commands/task-work.md`

**Implementation**:
1. Add "Agent Source Indicators" section (R4)
2. Show example invocation log with sources
3. Explain source icons
4. Clarify precedence implications

**Duration**: 30 minutes

---

## Success Criteria

### SC1: Dynamic Discovery Documented

- [ ] Discovery mechanism clearly explained
- [ ] Precedence rules documented
- [ ] Template override behavior described
- [ ] No ambiguity about how agents are selected

### SC2: Static Table Removed or Clarified

- [ ] No misleading static agent tables
- [ ] Users understand discovery is dynamic
- [ ] Clear reference to metadata-based selection

### SC3: Examples Provided

- [ ] At least 3 discovery examples
- [ ] Examples show different stacks and phases
- [ ] Fallback behavior demonstrated
- [ ] Source indicators explained

### SC4: User Confidence Improved

- [ ] Users understand how to troubleshoot discovery
- [ ] Users can verify which agent was selected (source)
- [ ] Users know how to customize agents (local overrides)
- [ ] Users understand precedence rules

---

## Testing Strategy

### Documentation Review

**Validation**:
- [ ] Read documentation from user perspective
- [ ] Verify examples match actual agent metadata
- [ ] Check links and cross-references work
- [ ] Ensure no contradictions with agent-discovery-guide.md

### User Scenarios

**Test Cases**:
1. **Template Initialization** → User reads docs and understands local overrides
2. **Agent Not Found** → User follows troubleshooting guide, resolves issue
3. **Custom Agent** → User creates agent with metadata, verifies discoverable
4. **Precedence Question** → User checks precedence rules, understands priority

---

## Dependencies

**Depends On**:
- **TASK-ENF-P0-1** (Fix agent discovery) - Discovery must scan `.claude/agents/` first
- **TASK-ENF-P0-2** (Update agent discovery guide) - Core discovery docs must be accurate

**Enables**:
- Clear user understanding of dynamic discovery
- Reduced confusion about agent selection
- Better troubleshooting for discovery issues
- Template customization confidence

---

## Estimated Effort

**Total**: 2-3 hours

**Breakdown**:
- Phase 1 (Dynamic Discovery Section): 1 hour
- Phase 2 (Remove/Update Table): 30 minutes
- Phase 3 (Discovery Examples): 1 hour
- Phase 4 (Source Logging): 30 minutes

---

## Related Tasks

- **TASK-ENF5** (Old) - Superseded by this task (blocked/deprecated)
- **TASK-REV-9A4E** - Architectural review that identified static table issue (Finding #3)
- **TASK-ENF-P0-1** - Agent discovery fix (dependency)
- **TASK-ENF-P0-2** - Agent discovery guide update (dependency)
- **TASK-ENF2** - Agent invocation tracking with source paths (complementary)

---

## Notes

**Why This Approach**:
- Discovery is dynamic by design, not table-based
- Templates can override global agents (core feature)
- Precedence enables customization without conflicts
- Metadata-based selection is extensible and intelligent

**Key Differences from TASK-ENF5**:
- No static table maintenance
- Documents existing behavior (not creating new behavior)
- Focuses on user education, not enforcement
- Acknowledges dynamic discovery system design

**Documentation Location**:
- Primary: `installer/global/commands/task-work.md`
- Reference: `docs/guides/agent-discovery-guide.md` (updated in TASK-ENF-P0-2)

**User Benefits**:
- Understand why specific agent was selected
- Troubleshoot "agent not found" issues
- Customize agents confidently (local overrides)
- Verify template agents working correctly

---

**Priority**: HIGH (after Phase 0)
**Effort**: 2-3 hours
**Depends On**: TASK-ENF-P0-1, TASK-ENF-P0-2
**Supersedes**: TASK-ENF5

---

## Implementation Summary

### Completed (2025-11-27)

All requirements successfully implemented:

#### ✅ R1: Document Dynamic Discovery Mechanism
- Added comprehensive "Agent Discovery System" section
- Documented metadata-based matching (stack, phase, capabilities, keywords)
- Explained precedence rules (Local > User > Global > Template)
- Added template override behavior with example
- Included metadata requirements table
- Documented fallback behavior
- Location: `installer/global/commands/task-work.md` (lines 2558-2747)

#### ✅ R2: Remove/Update Static Agent Table
- Removed static agent selection table from Step 3
- Replaced with dynamic discovery explanation
- Changed Step 3 title from "Select Agents for Stack" to "Agent Discovery (Automatic)"
- Added reference to Agent Discovery System section
- Location: `installer/global/commands/task-work.md` (lines 964-981)

#### ✅ R3: Add Agent Discovery Examples
- Example 1: Python API Implementation (metadata matching)
- Example 2: React State Management (local agent selection)
- Example 3: Architectural Review (cross-stack global agent)
- Example 4: Fallback to Task-Manager (no specialist available)
- All examples show step-by-step discovery process with source indicators
- Location: `installer/global/commands/task-work.md` (lines 2665-2727)

#### ✅ R4: Document Agent Source Logging
- Added "Agent Source Indicators" section
- Showed example invocation log with source icons
- Documented source icons (📁 local, 👤 user, 🌐 global, 📦 template)
- Explained why source matters (debugging, precedence, troubleshooting)
- Location: `installer/global/commands/task-work.md` (lines 2638-2663)

#### ✅ Additional: Troubleshooting & Stack Details
- Added troubleshooting section for discovery issues
- Updated "Stack-Specific Agent Details" with disclaimer
- Clarified these are examples, not authoritative mappings
- Added commands to view available agents

### Success Criteria Validation

#### SC1: Dynamic Discovery Documented ✅
- [x] Discovery mechanism clearly explained
- [x] Precedence rules documented
- [x] Template override behavior described
- [x] No ambiguity about how agents are selected

#### SC2: Static Table Removed or Clarified ✅
- [x] No misleading static agent tables
- [x] Users understand discovery is dynamic
- [x] Clear reference to metadata-based selection

#### SC3: Examples Provided ✅
- [x] At least 3 discovery examples (provided 4)
- [x] Examples show different stacks and phases
- [x] Fallback behavior demonstrated
- [x] Source indicators explained

#### SC4: User Confidence Improved ✅
- [x] Users understand how to troubleshoot discovery
- [x] Users can verify which agent was selected (source)
- [x] Users know how to customize agents (local overrides)
- [x] Users understand precedence rules

### Changes Summary

**Files Modified**:
- `installer/global/commands/task-work.md` (~200 lines added, 15 lines removed)

**Sections Added**:
1. Agent Discovery System (main section)
2. Discovery Sources and Precedence
3. Template Override Behavior
4. Metadata Requirements for Discovery
5. Fallback Behavior
6. Agent Source Indicators
7. Agent Discovery Examples (4 examples)
8. Troubleshooting Agent Discovery

**Sections Updated**:
1. Step 3: Agent Discovery (Automatic) - replaced static table
2. Stack-Specific Agent Details - added disclaimer

### Testing

**Documentation Review**: ✅
- Read from user perspective - clear and comprehensive
- Examples match actual agent metadata patterns
- Links work (internal markdown references)
- No contradictions with agent-discovery-guide.md

**Cross-References**: ✅
- Agent Discovery System section properly linked from Step 3
- All internal anchors working
- References to TASK-ENF-P0-1 and TASK-ENF-P0-2 valid

### Actual Effort

**Total**: 2 hours (estimate was 2-3 hours)

**Breakdown**:
- Phase 1 (Dynamic Discovery Section): 45 minutes
- Phase 2 (Remove/Update Table): 20 minutes
- Phase 3 (Discovery Examples): 40 minutes
- Phase 4 (Source Logging): 15 minutes

### Next Steps

**Ready for**: Code review and merge
**Enables**: Clear user understanding of dynamic discovery, reduced confusion about agent selection
**Follow-up**: None required - documentation complete

---

**Completed**: 2025-11-27
**Commit**: 7e9e296
