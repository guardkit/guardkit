# TASK-DOC-1C5A: Update template-create Instructions for ALWAYS/NEVER/ASK Boundary Sections

**Task ID**: TASK-DOC-1C5A
**Priority**: HIGH
**Status**: BACKLOG
**Created**: 2025-11-22T16:30:00Z
**Updated**: 2025-11-22T16:30:00Z
**Tags**: [documentation, user-experience, template-create, boundary-sections]
**Complexity**: 4/10 (Medium - straightforward documentation updates)
**Related**: TASK-STND-773D (completed - agent-content-enhancer update)

---

## Overview

Update template-create workflow documentation and end-user instructions to communicate the new ALWAYS/NEVER/ASK boundary sections feature introduced by TASK-STND-773D.

**Current State**:
- ✅ agent-content-enhancer.md generates ALWAYS/NEVER/ASK boundary sections (TASK-STND-773D implemented)
- ✅ Boundary validation enforces 5-7/5-7/3-5 rule counts with emoji format
- ❌ template-create Phase 8 instructions don't mention boundary sections
- ❌ Users see unfamiliar ALWAYS/NEVER/ASK structure without context
- ❌ No discovery mechanism for this new feature

**Target State**:
- ✅ Phase 8 instructions explain boundary sections feature
- ✅ Users understand ALWAYS/NEVER/ASK format before reviewing agents
- ✅ template-create.md documentation includes boundary section guidance
- ✅ CLAUDE.md provides accessible reference documentation
- ✅ Clear user journey from feature announcement to usage

**Scope**:
- Update template-create workflow instructions (Phase 8 output)
- Update template-create.md command documentation
- Enhance CLAUDE.md user guidance
- **NOT in scope**: Changing agent-content-enhancer behavior (already done in TASK-STND-773D)

**Impact**:
- **User Discovery**: Eliminates confusion when users encounter boundary sections
- **Feature Visibility**: Makes TASK-STND-773D improvements discoverable
- **Documentation Quality**: Brings user-facing docs in sync with implementation

---

## Acceptance Criteria

### AC1: Phase 8 Output Enhancement
- [ ] **AC1.1**: Update `_print_agent_enhancement_instructions()` method to include boundary sections announcement
- [ ] **AC1.2**: Add explanation of ALWAYS/NEVER/ASK format (5-7/5-7/3-5 rule counts)
- [ ] **AC1.3**: Show example validation output with boundary_completeness metrics
- [ ] **AC1.4**: Include emoji format explanation (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- [ ] **AC1.5**: Reference agent-content-enhancer.md for detailed specification

### AC2: template-create.md Documentation
- [ ] **AC2.1**: Update Phase 6 (Agent Recommendation) description to mention boundary generation
- [ ] **AC2.2**: Update Phase 8 (Agent Task Creation) description to explain boundary sections
- [ ] **AC2.3**: Add "Understanding Boundary Sections" subsection with format specification
- [ ] **AC2.4**: Include DO/DON'T examples for good boundary rules
- [ ] **AC2.5**: Reference GitHub analysis document for background

### AC3: CLAUDE.md User Guidance
- [ ] **AC3.1**: Move boundary section note from "MCP Integration" to "Core AI Agents" section (better placement)
- [ ] **AC3.2**: Expand boundary explanation with concrete examples (testing agent, repository agent)
- [ ] **AC3.3**: Add guidance on interpreting ALWAYS/NEVER/ASK rules during review
- [ ] **AC3.4**: Document how to validate boundary quality (rule counts, emoji format, placement)
- [ ] **AC3.5**: Include link to github-agent-best-practices-analysis.md for context

### AC4: User Discovery Flow
- [ ] **AC4.1**: Phase 8 output appears immediately after template creation
- [ ] **AC4.2**: Boundary announcement visible before agent enhancement instructions
- [ ] **AC4.3**: Users can find detailed docs via references in Phase 8 output
- [ ] **AC4.4**: CLAUDE.md section easily discoverable (table of contents, search)
- [ ] **AC4.5**: Cross-references between CLAUDE.md, template-create.md, and agent-content-enhancer.md

### AC5: Example Quality
- [ ] **AC5.1**: Include 2-3 concrete ALWAYS/NEVER/ASK examples
- [ ] **AC5.2**: Examples show correct emoji format (✅/❌/⚠️)
- [ ] **AC5.3**: Examples demonstrate proper rule structure: `[emoji] [action] ([rationale])`
- [ ] **AC5.4**: Examples cover different agent types (testing, repository, UI)
- [ ] **AC5.5**: Examples show both GitHub-compliant format and AI-enhanced format

### AC6: Validation & Testing
- [ ] **AC6.1**: Run `/template-create` and verify Phase 8 output includes boundary announcement
- [ ] **AC6.2**: Verify template-create.md accurately describes new output
- [ ] **AC6.3**: Verify CLAUDE.md section is findable via table of contents
- [ ] **AC6.4**: Verify all cross-references resolve correctly
- [ ] **AC6.5**: User can understand boundary sections without reading implementation plan

---

## Implementation Plan

### Summary

**Phase 1**: Update Phase 8 Output (1 hour)
- Modify `_print_agent_enhancement_instructions()` method
- Add boundary sections announcement
- Include validation output example

**Phase 2**: Update Command Documentation (45 minutes)
- Update template-create.md Phase 6 and Phase 8 descriptions
- Add "Understanding Boundary Sections" subsection

**Phase 3**: Update CLAUDE.md (45 minutes)
- Reorganize boundary content to "Core AI Agents"
- Expand with examples and guidance

**Total Effort**: 2.5 hours
**Risk**: Low (documentation-only changes, no code logic modifications)

### Files Modified

1. `installer/global/commands/lib/template_create_orchestrator.py`:
   - Lines 1523-1561: `_print_agent_enhancement_instructions()` method

2. `installer/global/commands/template-create.md`:
   - Phase 6 description (Agent Recommendation section)
   - Phase 8 description (Agent Task Creation section)
   - New subsection: "Understanding Boundary Sections"

3. `CLAUDE.md`:
   - Move from "MCP Integration Best Practices" (line ~550+)
   - To: "Core AI Agents" section
   - Expand with examples and usage guidance

---

## Detailed Implementation Steps

### Phase 1: Update Phase 8 Output (1 hour)

#### Step 1.1: Modify `_print_agent_enhancement_instructions()` (45 minutes)

**File**: `installer/global/commands/lib/template_create_orchestrator.py` (lines 1523-1561)

**Update method** to include boundary sections announcement:

```python
def _print_agent_enhancement_instructions(
    self,
    task_ids: List[str],
    agent_names: List[str],
    template_name: str
) -> None:
    """
    Print agent enhancement instructions with Option A/B format (TASK-UX-2F95).
    Includes boundary sections announcement (TASK-DOC-1C5A).
    """
    print(f"\n{'='*70}")
    print("AGENT ENHANCEMENT OPTIONS")
    print(f"{'='*70}\n")

    # NEW: Boundary sections feature announcement
    print("📋 Enhanced Agents Now Include Boundary Sections (GitHub Best Practices)")
    print("   Automatically generated in all enhanced agents:\n")
    print("   • ALWAYS (5-7 rules): Non-negotiable actions the agent MUST perform")
    print("   • NEVER (5-7 rules): Prohibited actions the agent MUST avoid")
    print("   • ASK (3-5 scenarios): Situations requiring human escalation\n")
    print("   Format: [emoji] [action] ([brief rationale])")
    print("   - ✅ ALWAYS prefix")
    print("   - ❌ NEVER prefix")
    print("   - ⚠️ ASK prefix\n")
    print("   📖 See: installer/global/agents/agent-content-enhancer.md for details")
    print(f"   {'─'*68}\n")

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

    # Enhanced footer note
    print(f"\nBoth approaches use the same AI enhancement logic with boundary validation.")
    print(f"\nExpected Validation:")
    print(f"  ✅ boundary_sections: ['ALWAYS', 'NEVER', 'ASK']")
    print(f"  ✅ boundary_completeness: always_count=5-7, never_count=5-7, ask_count=3-5")
    print(f"{'='*70}\n")
```

**Acceptance Criteria**: AC1.1, AC1.2, AC1.3, AC1.4, AC1.5

#### Step 1.2: Test Phase 8 Output (15 minutes)

**Method**:
```bash
# Run template-create on test codebase
/template-create

# Verify Phase 8 output includes:
# - "Enhanced Agents Now Include Boundary Sections" header
# - Explanation of ALWAYS/NEVER/ASK format
# - Emoji format guidance
# - Expected validation output
# - Reference to agent-content-enhancer.md
```

**Success Criteria**:
- Boundary announcement visible before Option A/B
- All 5 AC1 sub-criteria present in output
- Output is clear and concise (<15 lines for boundary section)

**Acceptance Criteria**: AC6.1

---

### Phase 2: Update Command Documentation (45 minutes)

#### Step 2.1: Update Phase 6 Description (15 minutes)

**File**: `installer/global/commands/template-create.md`

**Locate** Phase 6 (Agent Recommendation) section and **update**:

**Before**:
```markdown
### Phase 6: Agent Recommendation (2-5 minutes)

Generate specialized AI agents for this template based on codebase patterns.
```

**After**:
```markdown
### Phase 6: Agent Recommendation (2-5 minutes)

Generate specialized AI agents for this template based on codebase patterns.

**Boundary Sections**: Agents include ALWAYS/NEVER/ASK sections conforming to GitHub best practices (2,500+ repo analysis). See [Understanding Boundary Sections](#understanding-boundary-sections) below.
```

**Acceptance Criteria**: AC2.1

#### Step 2.2: Update Phase 8 Description (15 minutes)

**File**: `installer/global/commands/template-create.md`

**Locate** Phase 8 (Agent Task Creation) section and **update**:

**Before**:
```markdown
### Phase 8: Agent Task Creation (1-2 minutes)

Create tasks for enhancing agents with project-specific examples.

**Output**: Shows Option A (fast enhancement) and Option B (full workflow).
```

**After**:
```markdown
### Phase 8: Agent Task Creation (1-2 minutes)

Create tasks for enhancing agents with project-specific examples.

**Output**:
- Boundary sections announcement (new feature from TASK-STND-773D)
- Option A: Fast enhancement (`/agent-enhance` command)
- Option B: Full task workflow (`/task-work` command)
- Expected validation output showing boundary_completeness metrics

**Boundary Sections**: Enhanced agents automatically include:
- ALWAYS (5-7 rules): Non-negotiable actions
- NEVER (5-7 rules): Prohibited actions
- ASK (3-5 scenarios): Escalation situations

See [Understanding Boundary Sections](#understanding-boundary-sections) for details.
```

**Acceptance Criteria**: AC2.2

#### Step 2.3: Add "Understanding Boundary Sections" Subsection (15 minutes)

**File**: `installer/global/commands/template-create.md`

**Add new subsection** after Phase 8 description:

```markdown
## Understanding Boundary Sections

As of TASK-STND-773D (2025-11-22), all enhanced agents include **ALWAYS/NEVER/ASK boundary sections** conforming to GitHub best practices (analysis of 2,500+ repositories).

### Format Specification

**Structure**:
- **ALWAYS** (5-7 rules): Non-negotiable actions the agent MUST perform
- **NEVER** (5-7 rules): Prohibited actions the agent MUST avoid
- **ASK** (3-5 scenarios): Situations requiring human escalation

**Emoji Format**:
- ✅ ALWAYS prefix (green checkmark)
- ❌ NEVER prefix (red X)
- ⚠️ ASK prefix (warning sign)

**Rule Format**: `[emoji] [action] ([brief rationale])`

### Examples

**Testing Agent** (GitHub-compliant format):
```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

**Repository Agent** (GitHub-compliant format):
```markdown
## Boundaries

### ALWAYS
- ✅ Inject repositories via constructor (enforces DI pattern)
- ✅ Return ErrorOr<T> for all operations (consistent error handling)
- ✅ Use async/await for database operations (prevents thread blocking)
- ✅ Implement IDisposable for database connections (resource cleanup)
- ✅ Validate input parameters before database access (prevent injection)

### NEVER
- ❌ Never use `new()` for repository instantiation (breaks testability and DI)
- ❌ Never expose IQueryable outside repository (violates encapsulation)
- ❌ Never use raw SQL without parameterization (SQL injection risk)
- ❌ Never ignore database errors (silent failures prohibited)
- ❌ Never commit transactions within repository (violates SRP)

### ASK
- ⚠️ Complex joins across >3 tables: Ask if raw SQL vs EF Core query
- ⚠️ Caching strategy needed: Ask if in-memory vs distributed cache
- ⚠️ Soft delete vs hard delete: Ask for data retention policy decision
```

### DO and DON'T

**✅ DO**:
- Use specific, actionable verbs ("Validate input", "Run tests", "Log errors")
- Include brief rationale in parentheses ("(prevents SQL injection)", "(ensures audit trail)")
- Follow emoji format consistently (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- Maintain rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)

**❌ DON'T**:
- Use vague language ("Handle things properly", "Be careful")
- Omit rationale ("Validate input" without explaining why)
- Mix emoji formats (🚫 instead of ❌)
- Exceed count limits (8+ rules per section becomes overwhelming)

### Validation

Enhanced agents are validated for:
- **Section Presence**: All three sections (ALWAYS, NEVER, ASK) must exist
- **Rule Counts**: 5-7 ALWAYS, 5-7 NEVER, 3-5 ASK
- **Emoji Format**: Correct emoji prefixes (✅/❌/⚠️)
- **Placement**: Boundaries section after "Quick Start", before "Capabilities"

**Validation Output**:
```yaml
validation_report:
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 6 ✅
    never_count: 6 ✅
    ask_count: 4 ✅
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
  overall_status: PASSED
```

### Background

**Why Boundary Sections?**

GitHub analysis of 2,500+ repositories identified explicit boundaries as **Critical Gap #4** (0/10 score). Research shows:
- Boundary clarity prevents mistakes and reduces human intervention by 40%
- Explicit ALWAYS/NEVER/ASK framework reduces ambiguity in agent behavior
- Consistent format improves agent discoverability and reusability

**References**:
- [GitHub Agent Best Practices Analysis](../../docs/analysis/github-agent-best-practices-analysis.md)
- [agent-content-enhancer.md](../../installer/global/agents/agent-content-enhancer.md) (detailed specification)
- [TASK-STND-773D](../../tasks/backlog/TASK-STND-773D-standardize-agent-boundary-sections.md) (implementation task)
```

**Acceptance Criteria**: AC2.3, AC2.4, AC2.5, AC5.1, AC5.2, AC5.3, AC5.4, AC5.5

---

### Phase 3: Update CLAUDE.md (45 minutes)

#### Step 3.1: Locate Current Boundary Note (5 minutes)

**File**: `CLAUDE.md`

**Find** existing boundary section note (currently in "MCP Integration Best Practices" section, around line 550+):

```markdown
### Agent Enhancement Quality Standards

As of TASK-STND-773D (2025-11-22), all agents enhanced via `/agent-enhance` now conform to GitHub best practices by including **ALWAYS/NEVER/ASK boundary sections**.
```

**Action**: Identify exact location and content to move

#### Step 3.2: Move to "Core AI Agents" Section (15 minutes)

**File**: `CLAUDE.md`

**Locate** "Core AI Agents" section (search for "## Core AI Agents")

**Add new subsection** before the list of agents:

```markdown
## Core AI Agents

### Agent Enhancement with Boundary Sections

As of TASK-STND-773D (2025-11-22), all agents enhanced via `/agent-enhance` now conform to GitHub best practices by including **ALWAYS/NEVER/ASK boundary sections**.

**What Are Boundary Sections?**

Boundary sections explicitly define agent behavior using a three-tier framework:
- **ALWAYS** (5-7 rules): Non-negotiable actions the agent MUST perform
- **NEVER** (5-7 rules): Prohibited actions the agent MUST avoid
- **ASK** (3-5 scenarios): Situations requiring human escalation

**Format**: `[emoji] [action] ([brief rationale])`
- ✅ ALWAYS prefix
- ❌ NEVER prefix
- ⚠️ ASK prefix

**Why Boundary Sections?**

GitHub analysis of 2,500+ repositories identified explicit boundaries as Critical Gap #4 (was 0/10, now 9/10). Boundary clarity:
- Prevents costly mistakes
- Reduces human intervention by 40%
- Improves agent discoverability and reusability
- Sets clear expectations for agent behavior

**Example: Testing Agent Boundaries**

```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

**Example: Repository Agent Boundaries**

```markdown
## Boundaries

### ALWAYS
- ✅ Inject repositories via constructor (enforces DI pattern)
- ✅ Return ErrorOr<T> for all operations (consistent error handling)
- ✅ Use async/await for database operations (prevents thread blocking)
- ✅ Implement IDisposable for database connections (resource cleanup)
- ✅ Validate input parameters before database access (prevent injection)

### NEVER
- ❌ Never use `new()` for repository instantiation (breaks testability and DI)
- ❌ Never expose IQueryable outside repository (violates encapsulation)
- ❌ Never use raw SQL without parameterization (SQL injection risk)
- ❌ Never ignore database errors (silent failures prohibited)
- ❌ Never commit transactions within repository (violates SRP)

### ASK
- ⚠️ Complex joins across >3 tables: Ask if raw SQL vs EF Core query
- ⚠️ Caching strategy needed: Ask if in-memory vs distributed cache
- ⚠️ Soft delete vs hard delete: Ask for data retention policy decision
```

**How to Interpret Boundary Rules**

When reviewing enhanced agents:

1. **ALWAYS Rules**: Verify your implementation follows these guidelines
   - Example: If agent says "✅ Validate input parameters", ensure all inputs are validated

2. **NEVER Rules**: Check you're not violating these prohibitions
   - Example: If agent says "❌ Never use `new()` for repositories", use dependency injection instead

3. **ASK Scenarios**: Recognize when human decision is required
   - Example: "⚠️ Coverage 70-79%: Ask if acceptable" means you should evaluate risk and decide

**Validation During Enhancement**

When you run `/agent-enhance` or `/template-create`, boundary sections are automatically validated:
- Section presence (all three required: ALWAYS, NEVER, ASK)
- Rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- Emoji format (✅/❌/⚠️ prefixes)
- Placement (after "Quick Start", before "Capabilities")

**References**:
- [GitHub Agent Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md)
- [agent-content-enhancer.md](installer/global/agents/agent-content-enhancer.md)
- [template-create.md - Understanding Boundary Sections](installer/global/commands/template-create.md#understanding-boundary-sections)
```

**Action**: Delete old note from "MCP Integration Best Practices" section

**Acceptance Criteria**: AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC4.4, AC4.5

#### Step 3.3: Update Table of Contents (10 minutes)

**File**: `CLAUDE.md`

**If table of contents exists**, add entry for new subsection:

```markdown
## Table of Contents
...
- [Core AI Agents](#core-ai-agents)
  - [Agent Enhancement with Boundary Sections](#agent-enhancement-with-boundary-sections)
...
```

**Acceptance Criteria**: AC4.4

#### Step 3.4: Add Cross-References (15 minutes)

**File**: `CLAUDE.md`

**Update existing references** to boundary sections:

1. In "Template Philosophy" section, mention boundary sections:
   ```markdown
   Each template demonstrates:
   - ✅ How to structure templates for `/template-create`
   - ✅ Stack-specific best practices (or language-agnostic patterns)
   - ✅ Taskwright workflow integration
   - ✅ **Boundary sections (ALWAYS/NEVER/ASK) for clear agent behavior**
   - ✅ High quality standards (all score 8+/10)
   ```

2. In "Core AI Agents" section (agent list), add note:
   ```markdown
   **Global Agents:**
   - **architectural-reviewer**: SOLID/DRY/YAGNI compliance review
   - **task-manager**: Unified workflow management
   - **test-verifier/orchestrator**: Test execution and quality gates
   ...

   **Note**: All agents include ALWAYS/NEVER/ASK boundary sections. See [Agent Enhancement with Boundary Sections](#agent-enhancement-with-boundary-sections) for details.
   ```

**Acceptance Criteria**: AC4.5

---

## Testing Strategy

### Test 1: Phase 8 Output Verification

**Objective**: Verify Phase 8 output includes boundary sections announcement

**Method**:
```bash
# Run template-create on a test codebase
cd /path/to/test/codebase
/template-create

# Capture Phase 8 output
# Verify output contains:
# - "Enhanced Agents Now Include Boundary Sections" header
# - Explanation of ALWAYS (5-7), NEVER (5-7), ASK (3-5)
# - Emoji format guidance (✅/❌/⚠️)
# - Expected validation output
# - Reference to agent-content-enhancer.md
```

**Success Criteria**:
- Boundary announcement appears before Option A/B
- All AC1 sub-criteria present
- Output is clear and concise (<20 lines for boundary section)

**Acceptance Criteria**: AC6.1, AC1.1-AC1.5, AC4.1, AC4.2

### Test 2: Command Documentation Accuracy

**Objective**: Verify template-create.md accurately describes new output and boundary sections

**Method**:
1. Read template-create.md
2. Verify Phase 6 description mentions boundary generation
3. Verify Phase 8 description explains boundary sections
4. Verify "Understanding Boundary Sections" subsection exists
5. Verify examples are correct and complete

**Success Criteria**:
- Phase 6 description includes boundary section note
- Phase 8 description matches actual output
- "Understanding Boundary Sections" section includes:
  - Format specification (5-7/5-7/3-5)
  - Emoji format (✅/❌/⚠️)
  - 2-3 concrete examples (testing agent, repository agent)
  - DO/DON'T guidance
  - Validation explanation
  - Background/rationale

**Acceptance Criteria**: AC6.2, AC2.1-AC2.5, AC5.1-AC5.5

### Test 3: CLAUDE.md Discoverability

**Objective**: Verify CLAUDE.md section is findable and comprehensive

**Method**:
1. Open CLAUDE.md
2. Search for "boundary" (should find section)
3. Navigate via table of contents (if exists)
4. Verify section is in "Core AI Agents" (not "MCP Integration")
5. Verify examples are present and correct
6. Verify cross-references work

**Success Criteria**:
- Section is in "Core AI Agents" section
- Search for "boundary" finds the section
- Table of contents includes entry (if TOC exists)
- Examples are complete and formatted correctly
- Cross-references to github-agent-best-practices-analysis.md, agent-content-enhancer.md, and template-create.md work

**Acceptance Criteria**: AC6.3, AC6.4, AC3.1-AC3.5, AC4.3, AC4.4, AC4.5

### Test 4: User Comprehension Test

**Objective**: Verify user can understand boundary sections without reading implementation plan

**Method**:
1. Show Phase 8 output to a user unfamiliar with boundary sections
2. Ask: "What are boundary sections?"
3. Ask: "What do ALWAYS, NEVER, ASK mean?"
4. Ask: "How do you know if boundary sections are correct?"
5. Ask: "Where can you find more details?"

**Success Criteria**:
- User can explain ALWAYS/NEVER/ASK framework
- User understands emoji format (✅/❌/⚠️)
- User knows rule counts (5-7/5-7/3-5)
- User knows where to find more info (CLAUDE.md, template-create.md, agent-content-enhancer.md)
- User doesn't need to read TASK-STND-773D implementation plan

**Acceptance Criteria**: AC6.5

### Test 5: Cross-Reference Validation

**Objective**: Verify all cross-references resolve correctly

**Method**:
```bash
# Check all markdown links
grep -r "github-agent-best-practices-analysis.md" CLAUDE.md template-create.md
grep -r "agent-content-enhancer.md" CLAUDE.md template-create.md
grep -r "template-create.md" CLAUDE.md

# Verify files exist
ls docs/analysis/github-agent-best-practices-analysis.md
ls installer/global/agents/agent-content-enhancer.md
ls installer/global/commands/template-create.md
```

**Success Criteria**:
- All references use correct relative paths
- All referenced files exist
- All anchor links (#section-name) resolve correctly

**Acceptance Criteria**: AC6.4, AC4.5

---

## Design Decisions & Rationale

### Decision 1: Phase 8 Output Location

**Chosen**: Add boundary announcement BEFORE Option A/B instructions
**Alternative**: Add after Option A/B, or in separate section

**Rationale**:
- ✅ Users see new feature first (highest priority information)
- ✅ Context for why agents look different
- ✅ Maintains flow: Feature → How to use → Options
- ⚠️ Adds 10-12 lines to Phase 8 output (acceptable tradeoff)

### Decision 2: CLAUDE.md Section Placement

**Chosen**: Move to "Core AI Agents" section
**Alternative**: Keep in "MCP Integration Best Practices"

**Rationale**:
- ✅ Better semantic organization (boundary sections are agent feature, not MCP feature)
- ✅ Improves discoverability (users look in agent section for agent docs)
- ✅ Reduces cognitive load (MCP section already dense)
- ✅ Aligns with user mental model

### Decision 3: Example Selection

**Chosen**: Show testing agent + repository agent examples
**Alternative**: Generic examples, or 4+ examples

**Rationale**:
- ✅ Testing and repository are most common agent types
- ✅ Two examples show pattern without overwhelming
- ✅ Concrete examples more useful than abstract guidance
- ✅ Demonstrates different domains (quality vs data access)

### Decision 4: Emoji Format Documentation

**Chosen**: Include emoji format in all documentation
**Alternative**: Reference GitHub standard (no emoji) only

**Rationale**:
- ✅ AI-enhanced format uses emojis (agent-content-enhancer generates them)
- ✅ Emojis improve readability and scannability
- ✅ GitHub standard permits emojis (optional, not required)
- ✅ Users will see emoji format in generated agents

---

## Success Metrics

### Quantitative

- **Documentation updates**: 3 files updated (template_create_orchestrator.py, template-create.md, CLAUDE.md)
- **Lines added**: ~250 lines (orchestrator: 15, template-create.md: 180, CLAUDE.md: 55)
- **Cross-references**: 5+ links between docs
- **Examples included**: 2-3 concrete agent examples
- **Time to complete**: ≤2.5 hours

### Qualitative

- **User discovery**: Users understand boundary sections from Phase 8 output
- **Documentation quality**: Comprehensive coverage with examples
- **Consistency**: All docs use same terminology and format
- **Maintainability**: Clear structure for future updates

### Validation

**Before Completion**:
- [ ] Phase 8 output includes boundary announcement
- [ ] template-create.md Phase 6/8 updated
- [ ] template-create.md "Understanding Boundary Sections" subsection added
- [ ] CLAUDE.md section moved to "Core AI Agents"
- [ ] All cross-references validated
- [ ] All 30 acceptance criteria met (AC1-AC6)
- [ ] Changes committed

**After Deployment** (1 week):
- [ ] No user questions about "what are ALWAYS/NEVER/ASK sections?"
- [ ] No confusion reports about unfamiliar agent structure
- [ ] Users reference boundary sections in agent reviews
- [ ] Documentation remains accurate with no corrections needed

---

## Risk Assessment

### Risk 1: Output Too Verbose

**Likelihood**: Low (Phase 8 output carefully designed to be concise)
**Impact**: Low (users can scroll past if too long)

**Mitigation**:
- Keep boundary announcement to <15 lines
- Use clear headers and structure
- Include "skip to" instructions if needed

### Risk 2: Documentation Becomes Outdated

**Likelihood**: Medium (if agent-content-enhancer changes in future)
**Impact**: Medium (user confusion if docs don't match behavior)

**Mitigation**:
- Add cross-references to agent-content-enhancer.md (single source of truth)
- Include TASK-STND-773D reference for historical context
- Set reminder to review docs when agent-content-enhancer changes

### Risk 3: Users Ignore Documentation

**Likelihood**: High (users often skip docs)
**Impact**: Low (Phase 8 output provides immediate context)

**Mitigation**:
- **Primary**: Phase 8 output is impossible to miss (appears automatically)
- **Secondary**: Cross-references make discovery easy
- **Tertiary**: Examples show format without requiring reading

---

## Rollout Plan

### Phase 1: Implementation (2.5 hours)
- Update template_create_orchestrator.py (1 hour)
- Update template-create.md (45 minutes)
- Update CLAUDE.md (45 minutes)
- **Checkpoint**: All files updated, cross-references work

### Phase 2: Testing (30 minutes)
- Run `/template-create` and verify Phase 8 output
- Verify template-create.md accuracy
- Verify CLAUDE.md discoverability
- **Checkpoint**: All 5 tests pass

### Phase 3: Documentation (15 minutes)
- Update task status
- Commit changes with descriptive message
- **Checkpoint**: Changes committed

**Total Estimated Time**: 3 hours (includes buffer)

---

## Dependencies

**Blocks**: None
**Blocked By**: None
**Related**:
- TASK-STND-773D (Update agent-content-enhancer to generate boundaries) - ✅ Completed
- GitHub Agent Best Practices Analysis - ✅ Available
- agent-content-enhancer.md - ✅ Updated on branch agent-boundary-sections

---

## Completion Checklist

Before marking this task complete:

- [ ] **AC1**: Phase 8 Output Enhancement (5 sub-criteria)
  - [ ] AC1.1: `_print_agent_enhancement_instructions()` includes boundary announcement
  - [ ] AC1.2: ALWAYS/NEVER/ASK format explained (5-7/5-7/3-5)
  - [ ] AC1.3: Example validation output shown
  - [ ] AC1.4: Emoji format explained (✅/❌/⚠️)
  - [ ] AC1.5: Reference to agent-content-enhancer.md included

- [ ] **AC2**: template-create.md Documentation (5 sub-criteria)
  - [ ] AC2.1: Phase 6 description mentions boundary generation
  - [ ] AC2.2: Phase 8 description explains boundary sections
  - [ ] AC2.3: "Understanding Boundary Sections" subsection added
  - [ ] AC2.4: DO/DON'T examples included
  - [ ] AC2.5: GitHub analysis document referenced

- [ ] **AC3**: CLAUDE.md User Guidance (5 sub-criteria)
  - [ ] AC3.1: Boundary content moved to "Core AI Agents"
  - [ ] AC3.2: Expanded with concrete examples
  - [ ] AC3.3: Guidance on interpreting rules added
  - [ ] AC3.4: Validation guidance documented
  - [ ] AC3.5: Link to github-agent-best-practices-analysis.md included

- [ ] **AC4**: User Discovery Flow (5 sub-criteria)
  - [ ] AC4.1: Phase 8 output appears immediately after creation
  - [ ] AC4.2: Boundary announcement visible before options
  - [ ] AC4.3: Detailed docs findable via references
  - [ ] AC4.4: CLAUDE.md section easily discoverable
  - [ ] AC4.5: Cross-references between all docs work

- [ ] **AC5**: Example Quality (5 sub-criteria)
  - [ ] AC5.1: 2-3 concrete examples included
  - [ ] AC5.2: Examples show correct emoji format
  - [ ] AC5.3: Examples demonstrate proper rule structure
  - [ ] AC5.4: Examples cover different agent types
  - [ ] AC5.5: Examples show GitHub-compliant and AI-enhanced formats

- [ ] **AC6**: Validation & Testing (5 sub-criteria)
  - [ ] AC6.1: `/template-create` Phase 8 output verified
  - [ ] AC6.2: template-create.md accuracy verified
  - [ ] AC6.3: CLAUDE.md section findable
  - [ ] AC6.4: All cross-references resolve
  - [ ] AC6.5: Users can understand without implementation plan

- [ ] All 3 phases complete (2.5 hours total)
- [ ] All 5 tests pass
- [ ] Changes committed to git
- [ ] Task marked complete

---

**Created**: 2025-11-22T16:30:00Z
**Updated**: 2025-11-22T16:30:00Z
**Status**: BACKLOG
**Ready for Implementation**: YES
**Complexity**: 4/10 (Medium - straightforward documentation updates)
**Estimated Effort**: 2.5 hours

---

## Related Documents

- **Related Task**: [TASK-STND-773D](./TASK-STND-773D-standardize-agent-boundary-sections.md) (agent-content-enhancer update)
- **GitHub Analysis**: [docs/analysis/github-agent-best-practices-analysis.md](../../docs/analysis/github-agent-best-practices-analysis.md)
- **Target Agent**: [installer/global/agents/agent-content-enhancer.md](../../installer/global/agents/agent-content-enhancer.md)
- **Command Spec**: [installer/global/commands/template-create.md](../../installer/global/commands/template-create.md)
- **User Guide**: [CLAUDE.md](../../CLAUDE.md)
