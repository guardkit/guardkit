# TASK-STND-773D Scope Analysis: Missing Agent-Enhance Instructions

## Executive Summary

**Issue**: User reported "instructions to run the agent-enhance command were missing" after TASK-STND-773D implementation.

**Root Cause**: TASK-STND-773D correctly updated `agent-content-enhancer.md` to generate ALWAYS/NEVER/ASK boundary sections, but this was **NOT a scope gap**. The agent-enhance instructions already exist and were displayed correctly.

**Conclusion**: **No action required**. The workflow is functioning as designed - TASK-STND-773D's scope was limited to updating the agent enhancement logic, not the instruction display. Instructions are already comprehensive.

---

## Analysis

### 1. Template-Create Workflow Overview

The `/template-create` command executes these phases:

```
Phase 1:   AI Codebase Analysis
Phase 2:   Manifest Generation (manifest.json)
Phase 3:   Settings Generation (settings.json)
Phase 4:   Template File Generation (*.template files)
Phase 4.5: Completeness Validation
Phase 5:   Agent Generation (basic agents)
Phase 6:   REMOVED (was agent enhancement, now Phase 8)
Phase 7:   CLAUDE.md Generation
Phase 7.5: REMOVED (was batch enhancement, now incremental)
Phase 8:   Agent Task Creation (NEW - creates individual tasks)
Phase 9:   Package Assembly
Phase 9.5: Extended Validation (optional, with --validate)
```

**Key Changes**:
- **Old workflow**: Phase 7.5 automatically enhanced all agents at once
- **New workflow** (TASK-PHASE-8-INCREMENTAL): Phase 8 creates tasks + shows instructions

### 2. Where Agent-Enhance Instructions Appear

#### Location in Code
**File**: `installer/global/commands/lib/template_create_orchestrator.py`
**Method**: `_print_agent_enhancement_instructions()` (lines 1523-1561)

#### When Called
Phase 8 execution (lines 904-932):
1. Creates one task per agent file
2. Generates unique task IDs (UUID-based)
3. Calls `_print_agent_enhancement_instructions()` to display options

#### Current Output Format

```
======================================================================
AGENT ENHANCEMENT OPTIONS
======================================================================

Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Use /agent-enhance for direct AI-powered enhancement

  /agent-enhance my-template/agent-1 --hybrid
  /agent-enhance my-template/agent-2 --hybrid
  /agent-enhance my-template/agent-3 --hybrid

Option B - Full Task Workflow (Optional): 30-60 minutes per agent
  Use /task-work for complete quality gates

  /task-work TASK-AGENT1-A3F2B1C8
  /task-work TASK-AGENT2-D7E8F9A1
  /task-work TASK-AGENT3-C2B4D6E8

Both approaches use the same AI enhancement logic.
======================================================================
```

### 3. TASK-STND-773D Scope Analysis

#### What TASK-STND-773D Changed

**Branch**: `agent-boundary-sections`

**Modified File**: `installer/global/agents/agent-content-enhancer.md`

**Changes Made**:
1. Added "Boundaries" section requirement to agent enhancement output
2. Defined ALWAYS (5-7 rules), NEVER (5-7 rules), ASK (3-5 scenarios) sections
3. Added validation thresholds for boundary sections
4. Updated quality enforcement checklist to require boundary sections
5. Added boundary_sections to validation report format

**Example from agent-content-enhancer.md** (lines 66-88):
```markdown
## Boundaries

### ALWAYS
- **Validate schemas**: All inputs must pass validation before processing
- **Log decisions**: Every choice must be logged with rationale
- **Run tests**: No code proceeds without 100% test pass rate
[... 4 more rules]

### NEVER
- **Skip validation**: Do not bypass security checks for convenience
- **Assume defaults**: Do not use implicit configurations
- **Auto-approve**: Do not approve changes without human review
[... 4 more rules]

### ASK
- **Ambiguous requirements**: If acceptance criteria conflict
- **Security tradeoffs**: If performance weakens security
- **Breaking changes**: If fix requires breaking API
[... 2 more scenarios]
```

#### What TASK-STND-773D Did NOT Change

**Files NOT modified**:
- `template_create_orchestrator.py` - Workflow orchestration
- `template-create.md` - Command specification
- Any instruction display logic

**Why**: TASK-STND-773D's scope was to **enhance the quality of generated agent content**, not to change the workflow that displays instructions.

### 4. Expected vs Actual Behavior

#### Expected After TASK-STND-773D

When `/agent-enhance` runs (either standalone or via `/task-work`):

**Before TASK-STND-773D**:
```markdown
## Capabilities
1. Repository pattern implementation
2. CRUD operations
...

## Related Templates
- templates/repositories/LoadingRepository.cs.template
...
```

**After TASK-STND-773D**:
```markdown
## Capabilities
1. Repository pattern implementation
2. CRUD operations
...

## Boundaries

### ALWAYS
- **Validate input models**: All repository inputs must pass validation
- **Use ErrorOr pattern**: Return ErrorOr<T> for all operations
- **Log all operations**: Every CRUD operation must be logged
...

### NEVER
- **Skip null checks**: Never bypass null validation for convenience
- **Expose DbContext**: Never leak database context to callers
- **Auto-commit**: Never auto-commit without explicit request
...

### ASK
- **Ambiguous cardinality**: If relationship type is unclear
- **Performance vs safety**: If caching weakens data integrity
- **Breaking changes**: If refactor requires API changes
...

## Related Templates
- templates/repositories/LoadingRepository.cs.template
...
```

#### Actual Behavior

**Template-create Phase 8 already displays instructions correctly**:
1. Shows Option A (recommended): `/agent-enhance template/agent --hybrid`
2. Shows Option B (optional): `/task-work TASK-ID`
3. Both approaches use same AI enhancement logic (agent-content-enhancer)

**The instructions were ALWAYS there** - TASK-STND-773D just made the enhancement better.

### 5. User Expectation Gap Analysis

#### What User Might Have Expected

**Hypothesis 1**: User expected instructions to mention ALWAYS/NEVER/ASK sections
```
Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Enhances agents with boundaries (ALWAYS/NEVER/ASK sections)

  /agent-enhance my-template/agent-1 --hybrid
```

**Hypothesis 2**: User expected validation report preview
```
After enhancement, you'll receive:
  - ALWAYS section (5-7 rules)
  - NEVER section (5-7 rules)
  - ASK section (3-5 scenarios)
  - Validation report with quality metrics
```

**Hypothesis 3**: User missed the instructions (display timing issue)
- Instructions appear AFTER Phase 8 completes
- If user stopped reading output early, might have missed them

#### What Actually Happened

The instructions are displayed in `_print_agent_enhancement_instructions()` which is called from Phase 8:

**Line 921**:
```python
self._print_agent_enhancement_instructions(task_ids, agent_names, template_name)
```

This happens AFTER:
1. Phase 1-7: Template creation
2. Phase 8: Task creation
3. Package assembly
4. Success message

**Possible Issues**:
1. **Output overload**: User might scroll past instructions in long output
2. **Not prominent enough**: Instructions appear after main success message
3. **Unclear what changed**: No mention of ALWAYS/NEVER/ASK in instructions

### 6. Architectural Decision Points

#### Should Instructions Mention Boundary Sections?

**Option 1: Status Quo (Current Implementation)**
```
Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Use /agent-enhance for direct AI-powered enhancement

  /agent-enhance my-template/agent-1 --hybrid
```

**Pros**:
- Simple, concise
- Doesn't over-promise (AI might fail to generate boundaries)
- Implementation-agnostic (works even if boundary generation changes)

**Cons**:
- Doesn't communicate what's new in TASK-STND-773D
- User doesn't know what to expect from enhancement

**Option 2: Mention Boundary Sections Explicitly**
```
Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Enhances agents with ALWAYS/NEVER/ASK boundary sections

  /agent-enhance my-template/agent-1 --hybrid
```

**Pros**:
- Clearly communicates TASK-STND-773D improvements
- Sets user expectations
- Highlights value proposition

**Cons**:
- Couples instructions to implementation details
- If boundary generation fails, instructions are misleading
- Requires updating instructions whenever enhancement logic changes

**Option 3: Show Validation Report Preview**
```
Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  Enhanced agents include:
    ✓ ALWAYS section (5-7 non-negotiable rules)
    ✓ NEVER section (5-7 prohibited actions)
    ✓ ASK section (3-5 escalation scenarios)
    ✓ Code examples (40-50% density)
    ✓ Time to first example: <50 lines

  /agent-enhance my-template/agent-1 --hybrid
```

**Pros**:
- Very clear value proposition
- Educational (teaches users what quality enhancement means)
- Aligns with GitHub best practices analysis

**Cons**:
- Verbose (adds 5 lines per option)
- Makes promises (AI might not always deliver)
- Harder to maintain (must update if standards change)

### 7. Where Instructions Are Defined

#### Command Specification
**File**: `installer/global/commands/template-create.md`
**Section**: Lines 126-134 (Phase 8 description)

```markdown
Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95, TASK-UX-3A8D) [DEFAULT - skip with --no-create-agent-tasks]
├─ Creates one task per agent file
├─ Task metadata includes agent_file, template_dir, template_name, agent_name
├─ Tasks created in backlog with priority: medium
├─ Displays two enhancement options:
│  ├─ Option A (Recommended): /agent-enhance template-name/agent-name --hybrid (2-5 minutes per agent)
│  └─ Option B (Optional): /task-work TASK-AGENT-XXX (30-60 minutes per agent - full workflow)
└─ Both approaches use the same AI enhancement logic
```

**This is documentation ONLY** - not displayed to user during execution.

#### Actual Display Logic
**File**: `installer/global/commands/lib/template_create_orchestrator.py`
**Method**: `_print_agent_enhancement_instructions()` (lines 1523-1561)

**Current implementation** (lines 1540-1561):
```python
print(f"\n{'='*70}")
print("AGENT ENHANCEMENT OPTIONS")
print(f"{'='*70}\n")

# Option A: Fast Enhancement (Recommended)
print("Option A - Fast Enhancement (Recommended): 2-5 minutes per agent")
print("  Use /agent-enhance for direct AI-powered enhancement\n")

for agent_name in agent_names:
    print(f"  /agent-enhance {template_name}/{agent_name} --hybrid")

# Option B: Full Task Workflow (Optional)
print(f"\nOption B - Full Task Workflow (Optional): 30-60 minutes per agent")
print("  Use /task-work for complete quality gates\n")

for task_id in task_ids:
    print(f"  /task-work {task_id}")

# Footer note
print(f"\nBoth approaches use the same AI enhancement logic.")
print(f"{'='*70}\n")
```

### 8. Integration with Agent-Enhance Command

#### Agent-Enhance Command Spec
**File**: `installer/global/commands/agent-enhance.md`

**Lines 127-154**: Validation Report Section (added in TASK-STND-773D scope)
```markdown
### Validation Report (Post-GitHub Standards)

When enhancing agents, you'll now receive a validation report showing quality metrics:

```yaml
✅ Enhanced architectural-reviewer.md

Validation Report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: 28 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.3:1 ✅
  overall_status: PASSED
  iterations_required: 1
  warnings: []
```

**Validation Status**:
- ✅ = Passed quality threshold
- ⚠️ = Warning (below target but acceptable)
- ❌ = Failed (agent quality below minimum)
```

**This documentation exists** - but users need to know to run `/agent-enhance` to see it.

### 9. Gap Assessment

#### Is There a Scope Gap?

**Question**: Should TASK-STND-773D have updated template-create instructions?

**Answer**: **NO**

**Reasoning**:
1. **TASK-STND-773D scope**: Enhance agent generation quality (agent-content-enhancer.md)
2. **Template-create scope**: Workflow orchestration (template_create_orchestrator.py)
3. **Clear separation of concerns**: Agent enhancement logic ≠ workflow instructions
4. **Instructions already exist**: Phase 8 displays two clear options

#### What Changed vs What Stayed Same

**Changed (TASK-STND-773D)**:
- Agent enhancement output format (now includes boundaries)
- Validation criteria (now checks for ALWAYS/NEVER/ASK)
- Quality standards (GitHub best practices)

**Stayed Same (Not TASK-STND-773D scope)**:
- Workflow orchestration
- Instruction display logic
- Task creation process

### 10. Recommendations

#### Immediate Actions (None Required)

The system is working as designed:
1. ✅ Instructions ARE displayed (Phase 8, lines 1523-1561)
2. ✅ Two clear options provided (Option A/B format)
3. ✅ Agent-enhance command documented (agent-enhance.md)
4. ✅ Validation report format documented (lines 127-154)

#### Optional Enhancements (Low Priority)

If user feedback indicates confusion:

**Enhancement 1: Add "What's New" Note**
```python
print("\n🆕 NEW: Enhanced agents now include ALWAYS/NEVER/ASK boundary sections")
print("     See validation report after each enhancement.\n")
```

**Enhancement 2: Preview Validation Report Format**
```python
print("\nExpected Output (per agent):")
print("  ✅ Enhanced agent-name.md")
print("  Validation Report:")
print("    boundary_sections: [ALWAYS, NEVER, ASK] ✅")
print("    example_density: 47% ✅")
print("    time_to_first_example: 35 lines ✅\n")
```

**Enhancement 3: Make Instructions More Prominent**
- Move instructions before success message
- Use color/bold formatting
- Add separator lines

**Trade-offs**:
- Adds verbosity
- Couples instructions to implementation
- Requires maintenance when standards change

### 11. Conclusion

#### Finding

**No scope gap exists**. TASK-STND-773D correctly updated the agent enhancement logic to generate ALWAYS/NEVER/ASK sections. The workflow instructions were already present and comprehensive.

#### User Issue Root Cause

Most likely:
1. **Output overload**: User missed instructions in long output
2. **Expectation mismatch**: User expected instructions to explain new boundary sections
3. **Documentation gap**: User didn't know what to expect from enhancement

#### Recommended Response

**To User**:
"The instructions ARE displayed at the end of template-create Phase 8. You should see:

```
AGENT ENHANCEMENT OPTIONS
Option A - Fast Enhancement (Recommended): 2-5 minutes per agent
  /agent-enhance template-name/agent-name --hybrid

Option B - Full Task Workflow (Optional): 30-60 minutes per agent
  /task-work TASK-ID
```

TASK-STND-773D enhanced what happens WHEN you run those commands (agents now get ALWAYS/NEVER/ASK sections), but didn't change the instructions themselves.

Would you like the instructions to explicitly mention the new boundary sections?"

#### Future Consideration

If multiple users report confusion, consider adding a brief "What's New" note mentioning ALWAYS/NEVER/ASK sections. But this is NOT a bug or scope gap - it's a UX enhancement opportunity.

---

## Supporting Evidence

### File References

**Template-Create Orchestrator**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/lib/template_create_orchestrator.py`
  - Lines 904-932: Phase 8 execution
  - Lines 1523-1561: `_print_agent_enhancement_instructions()`

**Agent-Enhance Command Spec**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/agent-enhance.md`
  - Lines 127-154: Validation report documentation

**Agent-Content-Enhancer**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/agents/agent-content-enhancer.md`
  - Lines 59-88: Boundary sections specification (TASK-STND-773D changes)
  - Lines 138-169: Self-validation protocol
  - Lines 263-295: Validation output format

**Template-Create Command Spec**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/template-create.md`
  - Lines 126-134: Phase 8 documentation

### Change History

**TASK-STND-773D** (branch: agent-boundary-sections):
- Updated: `agent-content-enhancer.md` (added boundary section requirements)
- NOT updated: `template_create_orchestrator.py` (workflow unchanged)
- NOT updated: `template-create.md` (instructions unchanged)

---

**Document Status**: ANALYSIS COMPLETE
**Conclusion**: NO ACTION REQUIRED - System functioning as designed
**Created**: 2025-11-22
**Analyzed By**: Claude Code (Software Architect)
