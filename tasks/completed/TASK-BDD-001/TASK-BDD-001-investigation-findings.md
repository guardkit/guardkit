# TASK-BDD-001: Investigation Findings
## Mode Implementation Mechanism for task-work Command

**Date**: 2025-11-28
**Task**: TASK-BDD-001 - Investigate task-work mode implementation mechanism
**Status**: Complete
**Investigator**: Claude (via Conductor.build)

---

## Executive Summary

The `/task-work` command is a **pure slash command** (prompt-based), NOT a Python script. Mode flags like `--mode=tdd` are:
1. **Documented** in the command specification (`task-work.md`)
2. **Parsed** by Claude Code when executing the slash command
3. **Interpreted** by the task-manager agent during workflow orchestration
4. **NOT handled** by any Python orchestration script

**Key Insight**: Adding `--mode=bdd` requires:
- Documentation in `task-work.md` specification
- Logic in `task-manager.md` agent to route BDD workflow
- Integration with require-kit detection (`supports_bdd()`)
- No Python code changes required (it's all prompt-driven)

---

## 1. Mode Flag Implementation

### 1.1 Where `--mode=tdd` is Parsed

**Location**: `installer/core/commands/task-work.md:2743-2762`

```markdown
### Development Modes

The command supports multiple development modes via `--mode` flag:

#### Standard Mode (Default)
```bash
/task-work TASK-XXX
```
- Implementation and tests together
- Fastest approach for straightforward features
- All 5 phases execute in sequence

#### TDD Mode
```bash
/task-work TASK-XXX --mode=tdd
```
- RED: Testing agent generates failing tests first
- GREEN: Implementation agent writes minimal code to pass
- REFACTOR: Implementation agent improves code quality
- Best for complex business logic
```

**Mechanism**:
- Mode flag is **documented** in the slash command specification
- Claude Code **reads the specification** when `/task-work` is invoked
- The specification becomes part of Claude's **prompt context**
- No Python script parses the flag

### 1.2 How Flags Reach Workflow Logic

**Flow**:
```
User: /task-work TASK-042 --mode=tdd
         ↓
Claude Code reads task-work.md specification
         ↓
Claude Code invokes task-manager agent with mode context
         ↓
task-manager.md agent routing logic (prompt-based)
         ↓
Different workflow phases based on mode
```

**Evidence**: No Python file `task-work.py` exists in `installer/core/commands/`

---

## 2. TDD Mode Workflow Routing

### 2.1 Phase Execution Differences

**Standard Mode** (all phases in sequence):
```
Phase 1: Load Task Context
Phase 2: Implementation Planning
Phase 2.5A: Pattern Suggestion (if MCP available)
Phase 2.5B: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if complexity ≥7)
Phase 3: Implementation
Phase 4: Testing
Phase 4.5: Fix Loop (auto-fix, 3 attempts)
Phase 5: Code Review
Phase 5.5: Plan Audit
```

**TDD Mode** (RED-GREEN-REFACTOR):
```
Phase 1: Load Task Context
Phase 2: Implementation Planning
Phase 2.5A: Pattern Suggestion
Phase 2.5B: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if complexity ≥7)
Phase 3-TDD-RED: Testing agent generates FAILING tests first
Phase 3-TDD-GREEN: Implementation agent writes minimal code to pass
Phase 3-TDD-REFACTOR: Implementation agent improves code quality
Phase 4: Testing (verify all tests pass)
Phase 4.5: Fix Loop
Phase 5: Code Review
Phase 5.5: Plan Audit
```

**Location**: `installer/core/commands/task-work.md:2753-2760`

**Key Difference**: TDD mode splits Phase 3 into RED-GREEN-REFACTOR cycle, where **tests are written BEFORE implementation**.

### 2.2 Agent Selection Logic

**Location**: `installer/core/commands/task-work.md:1910-1955` (Phase 3 implementation)

**Standard Mode**:
```markdown
**INVOKE** Task tool:
subagent_type: "{selected_implementation_agent_from_table}"
description: "Implement TASK-XXX"
prompt: "Implement TASK-XXX following {stack} best practices..."
```

**TDD Mode** (inferred from documentation):
- Phase 3-RED: Invoke `test-orchestrator` to generate failing tests
- Phase 3-GREEN: Invoke implementation agent to write minimal passing code
- Phase 3-REFACTOR: Invoke implementation agent to improve code quality

**Agent Discovery**: Dynamic metadata-based matching (no hardcoded tables)
- Stack: `[python, react, dotnet, cross-stack]`
- Phase: `implementation | review | testing | orchestration | debugging`
- Capabilities: Specific skills
- Keywords: Searchable terms

**Source Precedence**: Local > User > Global > Template

---

## 3. Agent Invocation Mechanism

### 3.1 Where Agents are Invoked

**Location**: Throughout `task-work.md` at each phase boundary

**Example - Phase 2.5B (Architectural Review)**:
```markdown
**INVOKE** Task tool with documentation context:
subagent_type: "architectural-reviewer"
description: "Review architecture for TASK-XXX"
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 2.5B
</AGENT_CONTEXT>
..."
```

**Location**: `installer/core/commands/task-work.md:1169-1203`

### 3.2 How Agents are Selected

**Agent Discovery System**: `task-work.md:2764-2838`

1. **Analyze task context**:
   - Stack detection (file extensions, project structure)
   - Phase identification (1, 2, 2.5, 3, 4, 5)
   - Keyword extraction (from task description)

2. **Scan agent sources** (precedence order):
   - Local: `.claude/agents/`
   - User: `~/.agentecflow/agents/`
   - Global: `installer/core/agents/`
   - Template: `installer/core/templates/*/agents/`

3. **Match based on metadata**:
   - Stack compatibility
   - Phase alignment
   - Keyword relevance
   - Capability matching

4. **Fallback**: If no specialist found, use `task-manager` (orchestration agent)

### 3.3 Where require-kit Integration Happens

**Location**: `installer/core/lib/feature_detection.py:106-113`

```python
def supports_bdd(self) -> bool:
    """
    Check if BDD/Gherkin scenario generation is available.

    Returns:
        True if require-kit is installed, False otherwise
    """
    return self.is_require_kit_installed()
```

**Marker File Check**: `~/.agentecflow/require-kit.marker`

**Integration Points in task-work**:
- **Phase 1**: Feature detection (lines 3-19)
  ```markdown
  ### Taskwright + Require-Kit (Enhanced Workflow)
  - Loads EARS requirements if linked in task frontmatter
  - Loads Gherkin scenarios if linked (for BDD workflow)
  - Includes epic/feature context for hierarchy
  ```

---

## 4. Integration Points for BDD Mode

### 4.1 Where to Add BDD Validation

**Location**: Phase 1 (Load Task Context) - **BEFORE** workflow starts

**Recommended Location**: `task-work.md:400-600` (Phase 1 section)

**Validation Logic**:
```markdown
**IF** --mode=bdd flag present:
1. Check if require-kit is installed
   - Use `supports_bdd()` from feature_detection.py
   - If False: Display error, suggest installing require-kit
   - If True: Continue to scenario loading

2. Check for marker file
   - Path: ~/.agentecflow/require-kit.marker
   - If missing: Display error message
   - If present: Proceed
```

**Error Message Pattern**:
```
⚠️  BDD Mode Not Available

The --mode=bdd flag requires require-kit to be installed.

BDD mode enables:
  • EARS requirements → Gherkin scenarios
  • Scenario-driven implementation
  • Acceptance test automation

Install require-kit:
  1. Clone: git clone https://github.com/requirekit/require-kit
  2. Install: cd require-kit && ./installer/scripts/install.sh
  3. Verify: supports_bdd() returns True

For now, use --mode=standard or --mode=tdd
```

### 4.2 Where to Load Scenarios

**Location**: Phase 1 (Load Task Context) - **AFTER** BDD validation passes

**Recommended Location**: `task-work.md:600-800` (after task frontmatter loading)

**Loading Logic**:
```markdown
**IF** --mode=bdd AND supports_bdd() == True:
1. Check task frontmatter for scenario links
   - Field: `scenarios: [SCENARIO-001, SCENARIO-002]`
   - Or: `gherkin_files: [path/to/feature.feature]`

2. Load scenario content from require-kit
   - Location: ~/.agentecflow/scenarios/{scenario_id}.md
   - Or: Project scenarios/ directory

3. Parse Gherkin syntax
   - Feature: ...
   - Scenario: ...
   - Given/When/Then steps

4. Add to task context for agents
   - Scenarios become acceptance criteria
   - Steps guide test generation
```

### 4.3 Where to Invoke bdd-generator Agent

**Location**: NEW Phase 3-BDD (between Phase 2.8 and current Phase 3)

**Recommended Location**: `task-work.md:1750-1800` (after Phase 2.8 checkpoint)

**Invocation Logic**:
```markdown
#### Phase 3-BDD: Scenario-Driven Test Generation

**DISPLAY INVOCATION MESSAGE**:
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: bdd-generator
═══════════════════════════════════════════════════════
Phase: 3-BDD (BDD Test Generation)
Model: Sonnet (Gherkin → Test mapping requires reasoning)
Mode: BDD (Scenario-driven development)
Specialization:
  - Gherkin scenario parsing
  - Given/When/Then → test code mapping
  - Acceptance test generation

Starting agent execution...
═══════════════════════════════════════════════════════

**INVOKE** Task tool:
subagent_type: "bdd-generator"
description: "Generate BDD tests for TASK-XXX from Gherkin scenarios"
prompt: "Generate BDD acceptance tests for TASK-XXX.

Scenarios loaded:
{loaded_scenarios}

Requirements:
1. Parse Gherkin scenarios (Feature/Scenario/Given/When/Then)
2. Generate test code matching {stack} BDD framework
   - Python: pytest-bdd or behave
   - JavaScript/TypeScript: Cucumber.js or Jest + Cucumber
   - .NET: SpecFlow or xUnit + Gherkin
3. Create step definitions for each Given/When/Then
4. Map scenarios to test methods
5. Generate FAILING tests (BDD is test-first)

Output:
- Test files in {stack}-specific location
- Step definition files
- Test data/fixtures
- Documentation mapping scenarios → tests

Ready for Phase 3 implementation (write code to pass tests)."

**WAIT** for agent to complete before proceeding.
```

**Cross-Reference**: This agent should be sourced from **require-kit**, not taskwright
- Taskwright: Workflow orchestration only
- Require-kit: BDD generation, EARS → Gherkin, scenario management

### 4.4 Where to Run BDD Tests

**Location**: Phase 4 (Testing) - **SAME as standard workflow**

**Recommended Location**: `task-work.md:1970-2057` (existing Phase 4)

**No Changes Required**: BDD tests run through same test-orchestrator agent
- BDD frameworks integrate with standard test runners
- pytest-bdd → pytest
- Cucumber.js → Jest
- SpecFlow → dotnet test

**Quality Gates Apply**:
- 100% test pass rate (includes BDD scenarios)
- 80%+ line coverage
- 75%+ branch coverage
- Phase 4.5 fix loop (3 attempts)

### 4.5 Integration Point Summary

| Phase | Integration Point | Action | Location |
|-------|-------------------|--------|----------|
| **Phase 1** | Feature Detection | Check `supports_bdd()`, validate marker file | `task-work.md:400-600` |
| **Phase 1** | Scenario Loading | Load Gherkin from require-kit, parse scenarios | `task-work.md:600-800` |
| **Phase 3-BDD** | Test Generation | Invoke `bdd-generator` to create BDD tests | `task-work.md:1750-1800` (NEW) |
| **Phase 3** | Implementation | Write code to pass BDD tests | `task-work.md:1910-1955` (existing) |
| **Phase 4** | BDD Test Execution | Run BDD scenarios through test-orchestrator | `task-work.md:1970-2057` (existing) |
| **Phase 4.5** | Fix Loop | Auto-fix failing BDD scenarios (3 attempts) | `task-work.md:2059-2180` (existing) |

---

## 5. Architecture Diagram

### 5.1 Text Diagram

```
/task-work TASK-XXX --mode=bdd
         ↓
┌─────────────────────────────────────────┐
│ Phase 1: Load Task Context             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Read task frontmatter                 │
│ • Detect project stack                  │
│ • Check --mode flag                     │
│ ┌─────────────────────────────────┐    │
│ │ IF --mode=bdd:                  │    │
│ │ 1. supports_bdd() check         │    │
│ │ 2. Marker file validation       │    │
│ │ 3. Load Gherkin scenarios       │    │
│ │ 4. Parse Given/When/Then        │    │
│ └─────────────────────────────────┘    │
│                                         │
│ Integration: feature_detection.py      │
│ Location: task-work.md:400-800         │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 2: Implementation Planning        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: task-manager                   │
│ • Generate implementation plan          │
│ • Include scenario context in plan      │
│ • Plan saved to .claude/task-plans/     │
│                                         │
│ Location: task-work.md:1100-1400       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 2.5: Architectural Review         │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: architectural-reviewer         │
│ • SOLID/DRY/YAGNI compliance check      │
│ • Review BDD scenario coverage          │
│ • Score: 0-100 (≥60 to proceed)         │
│                                         │
│ Location: task-work.md:1152-1250       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 2.7: Complexity Evaluation        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Score 0-10 (files, patterns, risk)    │
│ • Auto-proceed (1-3), Checkpoint (7-10) │
│                                         │
│ Location: task-work.md:1367-1500       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 2.8: Human Checkpoint (if ≥7)    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Review plan and architecture          │
│ • Approve/Modify/Reject/Postpone        │
│                                         │
│ Location: task-work.md:1550-1700       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 3-BDD: Test Generation [NEW]     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: bdd-generator                  │
│ • Parse Gherkin scenarios               │
│ • Generate BDD test code                │
│ • Create step definitions               │
│ • Generate FAILING tests (BDD RED)      │
│ ┌─────────────────────────────────┐    │
│ │ BDD Frameworks by Stack:        │    │
│ │ • Python: pytest-bdd / behave   │    │
│ │ • JS/TS: Cucumber.js            │    │
│ │ • .NET: SpecFlow                │    │
│ └─────────────────────────────────┘    │
│                                         │
│ Integration: require-kit bdd-generator  │
│ Location: task-work.md:1750-1800 [NEW] │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 3: Implementation (BDD GREEN)     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: stack-specific specialist      │
│ • Write code to pass BDD tests          │
│ • Implement Given/When/Then steps       │
│ • Focus on making scenarios pass        │
│                                         │
│ Location: task-work.md:1910-1955       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 4: Testing (BDD Execution)        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: test-orchestrator              │
│ • Compilation check (MANDATORY)         │
│ • Run BDD scenarios + unit tests        │
│ • Coverage: 80%+ line, 75%+ branch      │
│ • Report: Pass/fail counts              │
│                                         │
│ Location: task-work.md:1970-2057       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 4.5: Fix Loop (Auto-fix)          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • IF tests fail: Auto-fix (3 attempts)  │
│ • Re-run tests after each fix           │
│ • 100% pass rate required               │
│ • BLOCK task if all attempts fail       │
│                                         │
│ Location: task-work.md:2059-2180       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 5: Code Review                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Agent: code-reviewer                  │
│ • Quality assessment                    │
│ • BDD scenario traceability             │
│ • Score: 0-10                           │
│                                         │
│ Location: task-work.md:2200-2300       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 5.5: Plan Audit                   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ • Scope creep detection                 │
│ • File count match (100%)               │
│ • Implementation completeness           │
│ • 0 violations required                 │
│                                         │
│ Location: task-work.md:2350-2450       │
└─────────────────────────────────────────┘
         ↓
Task State: BACKLOG → IN_REVIEW
```

### 5.2 Comparison: Standard vs TDD vs BDD

| Phase | Standard | TDD | BDD (Proposed) |
|-------|----------|-----|----------------|
| **Phase 1** | Load task | Load task | Load task + scenarios |
| **Phase 2** | Plan | Plan | Plan with scenario context |
| **Phase 2.5** | Arch review | Arch review | Arch review + scenario coverage |
| **Phase 3** | Implement + tests together | RED: Generate failing tests → GREEN: Minimal code → REFACTOR: Improve | Generate BDD tests → Implement to pass |
| **Phase 4** | Run all tests | Verify TDD tests pass | Run BDD scenarios + unit tests |
| **Phase 4.5** | Fix loop (3x) | Fix loop (3x) | Fix loop (3x) |
| **Phase 5** | Code review | Code review | Code review + scenario traceability |

---

## 6. Code References

### 6.1 Command Specification

**File**: `installer/core/commands/task-work.md`

| Section | Lines | Purpose |
|---------|-------|---------|
| Feature Detection | 3-19 | Require-kit integration documentation |
| Command Syntax | 95-99 | Flag definition |
| Documentation Level | 101-156 | `--docs=LEVEL` flag |
| Micro-Task Mode | 158-276 | `--micro` flag |
| Design-First Flags | 277-349 | `--design-only`, `--implement-only` |
| Phase 1 | 400-800 | **BDD: Add validation + scenario loading** |
| Phase 2 | 1100-1400 | Implementation planning |
| Phase 2.5B | 1152-1250 | Architectural review invocation |
| Phase 2.7 | 1367-1500 | Complexity evaluation |
| Phase 2.8 | 1550-1700 | Human checkpoint |
| **Phase 3-BDD** | **1750-1800** | **NEW: BDD test generation** |
| Phase 3 | 1910-1955 | Implementation agent invocation |
| Phase 4 | 1970-2057 | Testing agent invocation |
| Phase 4.5 | 2059-2180 | Fix loop logic |
| Phase 5 | 2200-2300 | Code review |
| Phase 5.5 | 2350-2450 | Plan audit |
| Development Modes | 2743-2762 | **BDD: Add mode documentation** |
| Agent Discovery | 2764-2838 | Dynamic agent selection |

### 6.2 Agent Files

**File**: `installer/core/agents/task-manager.md`

| Section | Lines | Purpose |
|---------|-------|---------|
| Frontmatter | 1-20 | **BDD: Add to capabilities, keywords** |
| Model Rationale | 6 | "TDD, BDD, standard modes" (already mentions BDD) |
| Capabilities | 11-16 | "Workflow orchestration (TDD, BDD, standard)" |

**File**: `installer/core/agents/architectural-reviewer.md`
- No changes required (already reviews all implementations)

**File**: `installer/core/agents/test-orchestrator.md`
- No changes required (already runs all test types)

**File**: `installer/core/agents/code-reviewer.md`
- No changes required (already reviews all code)

### 6.3 Feature Detection Library

**File**: `installer/core/lib/feature_detection.py`

| Section | Lines | Purpose |
|---------|-------|---------|
| Header | 1-49 | SHARED FILE warning (sync with require-kit) |
| `supports_bdd()` | 106-113 | BDD availability check |
| `is_require_kit_installed()` | 74-77 | Marker file check |

**Usage in task-work**:
```python
from lib.feature_detection import supports_bdd

if mode == "bdd":
    if not supports_bdd():
        print("Error: BDD mode requires require-kit")
        print("Install: cd require-kit && ./installer/scripts/install.sh")
        exit(1)
```

---

## 7. Recommendations

### 7.1 Cleanest Integration Approach

**Option A: Minimal Changes (Recommended)**

1. **Update task-work.md**:
   - Add BDD mode to Development Modes section (line 2762)
   - Add BDD validation logic to Phase 1 (lines 400-600)
   - Add scenario loading logic to Phase 1 (lines 600-800)
   - Add Phase 3-BDD section (lines 1750-1800)

2. **Update task-manager.md**:
   - Add BDD to capabilities/keywords (frontmatter)
   - Add routing logic for BDD mode (in workflow section)

3. **Leverage existing**:
   - `supports_bdd()` already exists (no changes)
   - Phase 4 testing works with BDD frameworks (no changes)
   - Phase 4.5 fix loop applies to BDD tests (no changes)

**Why Minimal?**
- No Python code changes required
- All prompt-driven through markdown specs
- Consistent with existing TDD pattern
- Leverages agent discovery system

### 7.2 What to Avoid

**❌ Don't create Python orchestration scripts**
- task-work is prompt-based, not script-based
- Keep it simple: markdown specification only

**❌ Don't duplicate feature_detection.py**
- This file is SHARED with require-kit
- Changes must sync between repos
- Minimal changes only

**❌ Don't hardcode agent mappings**
- Use agent discovery system (metadata-based)
- No static tables for BDD agent selection

**❌ Don't skip quality gates**
- BDD tests must pass 100% (Phase 4.5 fix loop)
- Coverage requirements apply (80%+ line, 75%+ branch)
- Architectural review still required (Phase 2.5)

### 7.3 Where to Add New Code

**Primary Changes**:
1. `installer/core/commands/task-work.md:2762` - Add BDD mode documentation
2. `installer/core/commands/task-work.md:400-800` - Add Phase 1 BDD logic
3. `installer/core/commands/task-work.md:1750-1800` - Add Phase 3-BDD section
4. `installer/core/agents/task-manager.md` - Add BDD routing logic

**Secondary Changes**:
- Update CLAUDE.md to document BDD mode
- Update template CLAUDE.md files
- Add BDD workflow guide to docs/workflows/

**No Changes Required**:
- `feature_detection.py` (already has `supports_bdd()`)
- `test-orchestrator.md` (already runs BDD frameworks)
- `architectural-reviewer.md` (already reviews all code)
- `code-reviewer.md` (already reviews all code)

---

## 8. Next Steps (Ready for TASK-BDD-003)

### 8.1 Implementation Checklist

Based on these findings, TASK-BDD-003 should:

- [ ] **Add BDD mode to task-work.md**
  - [ ] Development Modes section (line 2762)
  - [ ] Phase 1 validation logic (lines 400-600)
  - [ ] Phase 1 scenario loading (lines 600-800)
  - [ ] Phase 3-BDD test generation (lines 1750-1800)

- [ ] **Update task-manager.md**
  - [ ] Add BDD to capabilities (frontmatter)
  - [ ] Add BDD routing logic (workflow section)

- [ ] **Test integration**
  - [ ] Verify `supports_bdd()` detection works
  - [ ] Verify marker file check works
  - [ ] Verify scenario loading from require-kit

- [ ] **Documentation**
  - [ ] Update CLAUDE.md with BDD mode examples
  - [ ] Create BDD workflow guide
  - [ ] Update template CLAUDE.md files

### 8.2 Dependencies on Other Tasks

**Blocks**:
- TASK-BDD-003 (restore mode flag) - needs these findings
- TASK-BDD-004 (workflow routing) - needs integration points

**Parallel With**:
- TASK-BDD-002 (documentation) - can proceed independently
- TASK-BDD-006 (RequireKit agents) - can proceed independently

**Blocked By**:
- None (Wave 1 starter task)

---

## 9. Questions Answered

### 9.1 Is task-work a pure slash command?

**Answer**: ✅ **YES**

Evidence:
- No `task-work.py` file exists
- All workflow logic in `task-work.md` (markdown specification)
- Claude Code reads specification as prompt context
- Agents invoked via Task tool (not Python functions)

### 9.2 Where does `--mode=tdd` actually affect behavior?

**Answer**: In the **task-manager agent's interpretation** of the workflow

- Mode flag documented in `task-work.md:2753-2760`
- Claude reads specification when command invoked
- task-manager agent receives mode context
- Agent routes to different phase sequences (RED-GREEN-REFACTOR vs standard)

### 9.3 How do we add `--mode=bdd` in the same pattern?

**Answer**: Follow the TDD pattern exactly:

1. **Document in task-work.md** (Development Modes section)
2. **Add routing logic** in task-manager.md agent
3. **Add validation** in Phase 1 (check `supports_bdd()`)
4. **Add scenario loading** in Phase 1 (parse Gherkin)
5. **Add Phase 3-BDD** (invoke bdd-generator agent)
6. **Leverage existing** Phase 4/4.5/5 (no changes)

### 9.4 Where should we call `supports_bdd()`?

**Answer**: **Phase 1 (Load Task Context)** - BEFORE workflow starts

Location: `task-work.md:400-600`

Logic:
```python
if mode == "bdd":
    if not supports_bdd():
        print("Error: BDD mode requires require-kit")
        exit(1)

    # Load scenarios from require-kit
    scenarios = load_scenarios(task_context.scenario_ids)
    task_context.add_scenarios(scenarios)
```

### 9.5 Where is bdd-generator agent invoked?

**Answer**: **NEW Phase 3-BDD** (between Phase 2.8 and current Phase 3)

Location: `task-work.md:1750-1800` (NEW section to add)

Invocation:
```markdown
**INVOKE** Task tool:
subagent_type: "bdd-generator"
description: "Generate BDD tests for TASK-XXX"
prompt: "Parse scenarios: {scenarios}
         Generate BDD test code for {stack}
         Create step definitions
         Output: FAILING tests (BDD RED)"
```

---

## 10. Conclusion

The investigation reveals a **clean, prompt-driven architecture** where:

1. **Mode flags** are documented in slash command specifications
2. **Workflow routing** is handled by agent interpretation (not Python scripts)
3. **BDD integration** follows the same pattern as TDD mode
4. **Quality gates** automatically apply to all modes
5. **Agent discovery** makes specialization extensible

**Primary finding**: Adding `--mode=bdd` requires **markdown specification changes only** - no Python orchestration code needed.

**Ready for**: TASK-BDD-003 (implement mode flag) and TASK-BDD-004 (workflow routing)

---

## Appendix A: File Locations Quick Reference

```
installer/core/commands/task-work.md       # Primary integration point
installer/core/agents/task-manager.md      # Workflow routing logic
installer/core/agents/bdd-generator.md     # BDD test generation (require-kit)
installer/core/lib/feature_detection.py    # supports_bdd() function
~/.agentecflow/require-kit.marker           # Detection marker file
~/.agentecflow/scenarios/*.md                # Gherkin scenario storage
```

## Appendix B: Key Code Patterns

### Pattern 1: Agent Invocation
```markdown
**INVOKE** Task tool:
subagent_type: "{agent_name}"
description: "{short_description}"
prompt: "{detailed_instructions}"
```

### Pattern 2: Feature Detection
```python
from lib.feature_detection import supports_bdd

if not supports_bdd():
    print("Error: Feature not available")
    exit(1)
```

### Pattern 3: Phase Gate Validation
```python
try:
    validator.validate_phase_completion("3", "Implementation")
except ValidationError as e:
    move_task_to_blocked(task_id, reason=str(e))
    exit(1)
```

---

**End of Investigation**
