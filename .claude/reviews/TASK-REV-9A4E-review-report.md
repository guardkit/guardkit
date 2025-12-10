# Architectural Review Report: TASK-REV-9A4E

**Review Type**: Architectural Review - Enforcement Tasks Regression Analysis
**Review Mode**: architectural
**Review Depth**: standard (2 hours)
**Reviewed By**: architectural-reviewer agent (claude-opus-4-20250514)
**Date**: 2025-11-27
**Task**: TASK-REV-9A4E - Review enforcement tasks for regressions in template/agent workflows

---

## Executive Summary

This architectural review analyzed five agent invocation enforcement tasks (TASK-ENF1 through TASK-ENF5) to identify regression risks in template and agent creation workflows. The review revealed a **critical architectural gap** in the agent discovery system that would cause template-generated agents to be invisible to the enforcement mechanisms.

**Key Finding**: The agent discovery system does not scan `.claude/agents/` where template initialization copies local agents. This creates a fundamental mismatch where:
- Templates create local agents in `.claude/agents/`
- Agent discovery only looks in global/user locations
- Enforcement mechanisms will fail to recognize valid template agents
- Users will experience false-positive validation errors

**Overall Architecture Score**: **72/100**

**Recommendation**: **PAUSE all enforcement implementation** until agent discovery is fixed to properly handle local template agents. Without this fix, the enforcement system will break existing template workflows.

---

## Architecture Assessment Score: 72/100

### Workflow Integration: 14/20
- ✅ Enforcement mechanisms well-structured
- ✅ Phase-based approach aligns with existing workflow
- ❌ Missing local agent handling in discovery
- ❌ TASK-ENF5 only considers global agents

**Issues**:
1. Template-created agents not discoverable by enforcement
2. No coordination between `/template-init` and agent discovery
3. Enforcement validation will reject valid local agents

### Agent Discovery Compatibility: 12/20
- ✅ Metadata-based discovery is sound design
- ✅ Graceful degradation when metadata missing
- ❌ Critical gap: `.claude/agents/` not scanned
- ❌ Priority rules undefined for duplicate agents

**Issues**:
1. Agent discovery guide doesn't mention `.claude/agents/` scanning
2. When template copies agents locally, discovery can't find them
3. No precedence rules for local vs global agents with same name

### TASK-ENF5 Accuracy: 8/20
- ❌ Fundamentally flawed approach
- ❌ Only references global agents
- ❌ Ignores local template agent overrides
- ❌ Will create inconsistent behavior

**Issues**:
1. Hardcodes global agent names in selection table
2. Doesn't account for template-generated local agents
3. Suggests using `dotnet-domain-specialist` for MAUI, but MAUI templates may create `maui-usecase-specialist` locally
4. No mechanism to handle local agent precedence

### Extensibility: 18/20
- ✅ Well-structured enforcement tasks
- ✅ Clear separation of concerns
- ✅ Modular validation approach
- ⚠️ Would need refactoring if discovery changes

**Strengths**:
- Each enforcement task targets one specific improvement
- Tracking, validation, and phase gates are independent
- Easy to add new enforcement mechanisms

### Risk Management: 20/20
- ✅ Risks identified through this review
- ✅ Mitigation strategies clear
- ✅ Regression testing strategy defined
- ✅ All issues are fixable

**Strengths**:
- Review successfully identified critical gap
- All regressions can be prevented with fixes
- Clear path forward defined

---

## Findings

### Finding 1: Critical Agent Discovery Gap ⚠️ **CRITICAL**

**Issue**: Agent discovery system does not scan `.claude/agents/` directory

**Evidence**:
From `docs/guides/agent-discovery-guide.md`:
```python
# Discovery Flow (documented)
def discover_agents(phase, stack, keywords):
    # 1. Scan global agents
    global_agents = scan("installer/core/agents/*.md")

    # 2. Scan template agents
    template_agents = scan("installer/core/templates/*/agents/*.md")

    # 3. Scan user agents
    user_agents = scan("~/.agentecflow/agents/*.md")

    # MISSING: .claude/agents/ (where template-init copies local agents)
```

**Impact**:
- When users run `taskwright init react-typescript`, agents are copied to `.claude/agents/`
- Discovery system doesn't find these local agents
- Enforcement validation (TASK-ENF1) will fail with "agent not found"
- Phase gates (TASK-ENF4) will block valid tasks

**Severity**: CRITICAL - Breaks template workflows entirely

**Mitigation**: Add `.claude/agents/` scanning to discovery flow with highest precedence

---

### Finding 2: TASK-ENF5 Only References Global Agents ⚠️ **HIGH**

**Issue**: TASK-ENF5's agent selection table update only references global agents, ignoring local overrides

**Evidence**:
From `tasks/backlog/agent-invocation-enforcement/TASK-ENF5-update-agent-selection-table.md`:
- Updates `task-work.md` agent table to reference `installer/core/agents/` paths
- Suggests using `dotnet-domain-specialist` for MAUI
- Does NOT account for template-generated local agents

**Scenario**:
```bash
# User initializes MAUI template
taskwright init maui-template

# Template copies agents to .claude/agents/
.claude/agents/
├── maui-usecase-specialist.md  # Local override
└── ...

# TASK-ENF5 references global agent
task-work.md: "MAUI → dotnet-domain-specialist"

# Conflict: Local agent exists but table references global agent
# Question: Which one gets invoked?
```

**Impact**:
- Inconsistent agent selection behavior
- User customizations (local agents) ignored
- Template specialization defeated

**Severity**: HIGH - Incorrect system behavior

**Mitigation**: Redesign TASK-ENF5 to use dynamic discovery instead of hardcoded table

---

### Finding 3: No Agent Priority Rules Defined ⚠️ **MEDIUM**

**Issue**: When both global and local agents exist with same name, priority is undefined

**Evidence**:
Agent discovery guide does NOT specify precedence when duplicates exist:
- `installer/core/agents/react-state-specialist.md` (global)
- `.claude/agents/react-state-specialist.md` (local, from template)

**Impact**:
- Unpredictable agent selection
- Enforcement validation may fail inconsistently
- Users can't customize agents via templates

**Severity**: MEDIUM - Causes confusion and unreliable behavior

**Mitigation**: Define explicit priority rules: Local > User > Global

---

### Finding 4: Template-Init Doesn't Register Agents ⚠️ **MEDIUM**

**Issue**: `/template-init` copies agents but doesn't register them for discovery

**Evidence**:
From `installer/core/commands/template-init.md`:
- Copies agents from template to `.claude/agents/`
- No registration step mentioned
- Assumes discovery will "just work"

**Impact**:
- Copied agents invisible to discovery (due to Finding 1)
- No feedback to user that agents are available
- Silent failure mode

**Severity**: MEDIUM - Contributes to agent invisibility

**Mitigation**: Add explicit agent registration or ensure discovery scans `.claude/agents/`

---

### Finding 5: Agent Enhancement May Not Add Discovery Metadata ⚠️ **LOW**

**Issue**: `/agent-enhance` may not add required discovery metadata (stack, phase, capabilities, keywords)

**Evidence**:
From `installer/core/commands/agent-enhance.md`:
- Adds ALWAYS/NEVER/ASK boundary sections
- Template conformance validation
- Does NOT explicitly mention adding discovery metadata

**Impact**:
- Enhanced template agents may still not be discoverable
- Enforcement tracking (TASK-ENF2) won't work
- Phase gates (TASK-ENF4) will fail

**Severity**: LOW - Easily fixed during enhancement

**Mitigation**: Ensure `/agent-enhance` validates and adds discovery metadata

---

### Finding 6: Tracking Records Names, Not Sources ⚠️ **LOW**

**Issue**: TASK-ENF2 tracks agent names but not source paths (local vs global)

**Evidence**:
From `tasks/backlog/agent-invocation-enforcement/TASK-ENF2-add-agent-invocation-tracking.md`:
- Records: phase, agent name, status, duration
- Does NOT record: agent source path

**Impact**:
- Can't distinguish local vs global agent invocations
- Debugging agent selection issues difficult
- Enforcement validation can't verify correct agent source

**Severity**: LOW - Enhancement opportunity

**Mitigation**: Add `agent_source` field to tracking data

---

## Regression Risk Matrix

| Enforcement Task | Template Workflow Risk | Agent Discovery Risk | Severity | Mitigation Required |
|------------------|------------------------|---------------------|----------|---------------------|
| **TASK-ENF1** (Validation) | ⚠️ **CRITICAL** | ⚠️ **CRITICAL** | **CRITICAL** | Fix discovery to scan `.claude/agents/` |
| **TASK-ENF2** (Tracking) | ⚠️ MEDIUM | ⚠️ MEDIUM | MEDIUM | Add source path tracking |
| **TASK-ENF3** (Messages) | ✅ NONE | ✅ NONE | NONE | No changes needed |
| **TASK-ENF4** (Phase Gates) | ⚠️ **CRITICAL** | ⚠️ **CRITICAL** | **CRITICAL** | Fix discovery first |
| **TASK-ENF5** (Agent Table) | ⚠️ **HIGH** | ⚠️ **HIGH** | **HIGH** | Complete redesign required |

**Legend**:
- ⚠️ CRITICAL: Will break existing workflows, block implementation
- ⚠️ HIGH: Incorrect behavior, serious issues
- ⚠️ MEDIUM: Suboptimal behavior, degraded experience
- ⚠️ LOW: Minor issues, enhancement opportunities
- ✅ NONE: No impact, safe to implement

---

## Agent Discovery Flow Diagram

### Current Flow (BROKEN for Template Agents)

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Discovery System                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Scan Global Agents                                │
│  ├─ installer/core/agents/*.md                            │
│  └─ Example: react-state-specialist.md                      │
│                                                              │
│  Phase 2: Scan Template Agents (TEMPLATES, not initialized) │
│  ├─ installer/core/templates/*/agents/*.md                │
│  └─ Example: react-typescript/agents/react-state-specialist.md
│                                                              │
│  Phase 3: Scan User Agents                                  │
│  ├─ ~/.agentecflow/agents/*.md                              │
│  └─ Example: custom-specialist.md                           │
│                                                              │
│  ❌ MISSING: Scan Local Agents (.claude/agents/)            │
│  ├─ .claude/agents/*.md  ← CREATED BY TEMPLATE-INIT         │
│  └─ Example: react-state-specialist.md (local copy)         │
│                                                              │
│  Phase 4: Rank by Relevance                                 │
│  ├─ Match: stack + phase + keywords                         │
│  └─ Score each agent                                        │
│                                                              │
│  Phase 5: Return Best Match                                 │
│  └─ Highest scoring agent OR task-manager (fallback)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘

PROBLEM: When template-init copies agents to .claude/agents/,
         discovery system DOESN'T SEE THEM!
```

### Proposed Fixed Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Discovery System (FIXED)             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Scan Local Agents (HIGHEST PRIORITY) ← NEW        │
│  ├─ .claude/agents/*.md                                     │
│  └─ Example: react-state-specialist.md (template copy)      │
│  └─ Precedence: LOCAL > USER > GLOBAL                       │
│                                                              │
│  Phase 2: Scan User Agents                                  │
│  ├─ ~/.agentecflow/agents/*.md                              │
│  └─ Example: custom-specialist.md                           │
│                                                              │
│  Phase 3: Scan Global Agents                                │
│  ├─ installer/core/agents/*.md                            │
│  └─ Example: react-state-specialist.md (canonical)          │
│                                                              │
│  Phase 4: Scan Template Agents (lowest priority)            │
│  ├─ installer/core/templates/*/agents/*.md                │
│  └─ Only used if agent not found in local/user/global       │
│                                                              │
│  Phase 5: Remove Duplicates (by agent name)                 │
│  ├─ If multiple agents with same name exist:                │
│  └─ Keep LOCAL > USER > GLOBAL > TEMPLATE                   │
│                                                              │
│  Phase 6: Rank by Relevance                                 │
│  ├─ Match: stack + phase + keywords                         │
│  └─ Score each unique agent                                 │
│                                                              │
│  Phase 7: Return Best Match                                 │
│  └─ Highest scoring agent OR task-manager (fallback)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘

SOLUTION: Scan .claude/agents/ FIRST with HIGHEST precedence
          Template customizations always override global agents
```

### Priority Rules

**When duplicate agent names exist across sources**:

1. **Local** (`.claude/agents/`) - Highest priority
   - Created by `taskwright init <template>`
   - Project-specific customizations
   - Always wins

2. **User** (`~/.agentecflow/agents/`) - High priority
   - User's personal agent library
   - Cross-project customizations
   - Overrides global

3. **Global** (`installer/core/agents/`) - Standard priority
   - Canonical agent definitions
   - System defaults
   - Fallback for missing local/user

4. **Template** (`installer/core/templates/*/agents/`) - Lowest priority
   - Source definitions before initialization
   - Only used if agent not found elsewhere
   - Rarely invoked (templates copy to local on init)

---

## TASK-ENF5 Correction Recommendations

### Current Approach (WRONG)

**From TASK-ENF5**:
- Update `task-work.md` agent selection table
- Hardcode agent names and paths
- Reference global agents only

**Example**:
```markdown
| Stack | Phase | Agent |
|-------|-------|-------|
| React | Implementation | installer/core/agents/react-state-specialist.md |
| MAUI | Implementation | installer/core/agents/dotnet-domain-specialist.md |
```

**Problems**:
1. Ignores local agents created by templates
2. Hardcoded paths become stale
3. Can't handle user customizations
4. Creates inconsistent behavior

---

### Recommended Approach (CORRECT)

**Strategy**: Use dynamic discovery instead of static table

**Option 1: Remove Agent Table Entirely**
```markdown
# task-work.md (revised)

## Phase 3: Implementation

The system uses **agent discovery** to automatically select the appropriate
implementation agent based on:
- Detected stack (Python, React, .NET, etc.)
- Current phase (Implementation)
- Task keywords and complexity

**Discovery Process**:
1. Scan local agents (.claude/agents/) - Highest priority
2. Scan user agents (~/.agentecflow/agents/)
3. Scan global agents (installer/core/agents/)
4. Rank by relevance (stack + phase + keywords)
5. Invoke best match OR task-manager (fallback)

**Local Agent Precedence**: Template-generated agents in `.claude/agents/`
always take precedence over global agents, allowing project-specific
customization.

To see available agents: `/agent-list` (future command)
```

**Option 2: Convert Table to Discovery Examples**
```markdown
# task-work.md (revised)

## Phase 3: Implementation - Agent Discovery Examples

The system automatically selects implementation agents. Here are common matches:

| Stack | Typical Agent | Source Priority |
|-------|---------------|-----------------|
| React | react-state-specialist | Local → User → Global |
| Python API | python-api-specialist | Local → User → Global |
| .NET Domain | dotnet-domain-specialist | Local → User → Global |
| MAUI | dotnet-domain-specialist OR maui-usecase-specialist (if template provides) | Local → User → Global |

**Note**: Actual agent selected depends on discovery scan at runtime.
Template-initialized agents (`.claude/agents/`) take precedence.
```

**Benefits**:
- No hardcoded paths
- Supports local agent overrides
- Self-documenting
- Always accurate

---

### Specific TASK-ENF5 Corrections

**Before Implementation**:
1. ❌ **Don't** update agent table with hardcoded paths
2. ❌ **Don't** reference only global agents
3. ✅ **Do** document discovery process instead
4. ✅ **Do** explain local agent precedence

**Implementation Changes**:
- Replace static table with discovery explanation
- Add examples showing common agent matches
- Document precedence rules (Local > User > Global)
- Add note about template customization

**Effort**: 2-3 hours (complete rewrite of TASK-ENF5 approach)

---

## Template Workflow Adjustments

### Required Changes to `/template-create`

**Status**: ✅ No changes required

**Verification**:
- Templates already create agents with proper structure
- Agent enhancement adds discovery metadata
- Boundary sections included

**Action**: None

---

### Required Changes to `/template-init`

**Status**: ⚠️ Changes required

**Current Behavior**:
```bash
taskwright init react-typescript

# Copies agents from template to .claude/agents/
cp installer/core/templates/react-typescript/agents/*.md .claude/agents/
```

**Required Changes**:
1. **Verify agent metadata** on copy
2. **Log registered agents** for user feedback
3. **Test discovery** after initialization

**Implementation**:
```python
# template-init.py (pseudo-code)

def initialize_template(template_name):
    # ... existing initialization ...

    # Copy agents
    agents_copied = copy_agents(template, ".claude/agents/")

    # NEW: Verify agents are discoverable
    for agent in agents_copied:
        if not has_discovery_metadata(agent):
            log_warning(f"Agent {agent} missing discovery metadata")

    # NEW: Test discovery
    test_agents = discover_agents(phase="implementation", stack=template.stack)

    # NEW: Report registered agents
    print("✅ Registered agents:")
    for agent in agents_copied:
        print(f"  - {agent.name} (stack: {agent.stack}, phase: {agent.phase})")
```

**Effort**: 1-2 hours

---

### Required Changes to `/agent-enhance`

**Status**: ⚠️ Changes required

**Current Behavior**:
- Adds ALWAYS/NEVER/ASK boundary sections
- Validates template conformance
- Does NOT explicitly add discovery metadata

**Required Changes**:
1. **Validate discovery metadata** exists
2. **Add missing metadata** if not present
3. **Verify agent is discoverable** after enhancement

**Implementation**:
```python
# agent-enhance.py (pseudo-code)

def enhance_agent(agent_path):
    # ... existing enhancement ...

    # NEW: Validate discovery metadata
    required_fields = ["stack", "phase", "capabilities", "keywords"]
    for field in required_fields:
        if not agent.frontmatter.get(field):
            if field == "stack":
                agent.frontmatter["stack"] = prompt_user("Enter stack (e.g., python, react)")
            elif field == "phase":
                agent.frontmatter["phase"] = "implementation"  # default
            elif field == "capabilities":
                agent.frontmatter["capabilities"] = extract_capabilities(agent.content)
            elif field == "keywords":
                agent.frontmatter["keywords"] = extract_keywords(agent.content)

    # Save enhanced agent
    save_agent(agent)

    # NEW: Verify discoverability
    test_discovery = discover_agents(phase=agent.phase, stack=agent.stack)
    if agent not in test_discovery:
        log_warning(f"Agent {agent.name} may not be discoverable")
```

**Effort**: 2-3 hours

---

### Agent Metadata Requirements for Template Compatibility

**Minimum Required Metadata** (frontmatter):

```yaml
---
name: react-state-specialist
stack: [react, typescript]
phase: implementation
capabilities: [hooks, state-management, tanstack-query, zustand]
keywords: [useState, useEffect, useReducer, context, react-query]
model: haiku  # optional
---
```

**Field Descriptions**:

| Field | Required | Format | Purpose |
|-------|----------|--------|---------|
| `name` | ✅ Yes | string | Agent identifier |
| `stack` | ✅ Yes | array of strings | Technology stack(s) |
| `phase` | ✅ Yes | string | Workflow phase (implementation, review, testing, etc.) |
| `capabilities` | ✅ Yes | array of strings | Specific skills/domains |
| `keywords` | ✅ Yes | array of strings | Searchable terms for matching |
| `model` | ⚠️ Optional | string | Claude model (haiku, sonnet, opus) |

**Validation Checklist**:
- [ ] All required fields present
- [ ] Stack values match project technology
- [ ] Phase matches workflow phase names
- [ ] Capabilities are specific and actionable
- [ ] Keywords cover common search terms
- [ ] Agent file follows naming convention (`<name>-specialist.md`)

---

## Decision Summary

### Decision: [A] Accept with Modifications ✅ RECOMMENDED

**Rationale**:
The enforcement tasks are architecturally sound but have critical integration gaps that must be fixed before implementation. All issues are fixable within reasonable effort (10-16 hours total).

---

### Which Tasks Can Proceed As-Is

**TASK-ENF3** (Prominent Invocation Messages): ✅ **SAFE TO IMPLEMENT**
- Cosmetic changes only
- No impact on agent discovery
- No template workflow integration
- Estimated effort: 1-2 hours
- Can implement immediately

---

### Which Tasks Need Modifications Before Implementation

**TASK-ENF1** (Pre-Report Validation): ⚠️ **BLOCKED** until discovery fixed
- Depends on agent discovery scanning `.claude/agents/`
- Will fail to validate template agents without fix
- Required modifications:
  1. Fix agent discovery to scan local agents
  2. Update validation to check local agents first
  3. Add precedence rules to validation logic
- Estimated additional effort: 3-4 hours

**TASK-ENF2** (Agent Invocation Tracking): ⚠️ **NEEDS ENHANCEMENT**
- Currently tracks agent name only
- Should track agent source path for debugging
- Required modifications:
  1. Add `agent_source` field to tracking data
  2. Record whether agent is local/user/global
  3. Update tracking reports to show source
- Estimated additional effort: 1-2 hours

**TASK-ENF4** (Phase Gate Checkpoints): ⚠️ **BLOCKED** until discovery fixed
- Depends on agent discovery scanning `.claude/agents/`
- Will block valid template agents without fix
- Required modifications:
  1. Same discovery fixes as TASK-ENF1
  2. Gate validation must check local agents
  3. Add precedence-aware validation
- Estimated additional effort: 2-3 hours

**TASK-ENF5** (Agent Selection Table): ⚠️ **COMPLETE REDESIGN REQUIRED**
- Current approach fundamentally flawed
- Hardcoding global agents ignores local overrides
- Required modifications:
  1. Remove static agent table
  2. Replace with discovery explanation
  3. Document precedence rules
  4. Add discovery examples
- Estimated additional effort: 2-3 hours

---

### Priority Order for Addressing Issues

**Phase 0: Foundation Fixes** (4-6 hours) - MUST DO FIRST
1. **Fix agent discovery system** (2-3 hours)
   - Add `.claude/agents/` scanning
   - Implement precedence rules (Local > User > Global)
   - Update agent-discovery-guide.md
   - Test with template initialization

2. **Update agent discovery documentation** (1-2 hours)
   - Document `.claude/agents/` scanning
   - Explain precedence rules with examples
   - Add troubleshooting guide
   - Create discovery flow diagram

3. **Test template agent discovery** (1 hour)
   - Initialize react-typescript template
   - Verify agents copied to `.claude/agents/`
   - Run `/task-work` with React task
   - Confirm local agent selected

**Phase 1: Safe Implementations** (3-5 hours)
4. **Implement TASK-ENF3** (1-2 hours)
   - Add prominent invocation messages
   - No dependencies, safe to proceed

5. **Redesign TASK-ENF5** (2-3 hours)
   - Remove static agent table
   - Add discovery explanation
   - Document precedence rules

**Phase 2: Enhanced Tracking** (1-2 hours)
6. **Enhance TASK-ENF2** (1-2 hours)
   - Add agent source tracking
   - Update tracking reports

**Phase 3: Enforcement with Local Support** (5-7 hours)
7. **Update TASK-ENF1** (2-3 hours)
   - Local agent validation
   - Precedence-aware checks

8. **Update TASK-ENF4** (2-3 hours)
   - Local agent gate validation
   - Precedence-aware checkpoints

9. **Integration testing** (1 hour)
   - End-to-end template workflow test
   - Verify all enforcement works with local agents

---

### Estimated Total Additional Effort

**Total Time Required**: 10-16 hours

**Breakdown by Phase**:
- Phase 0 (Foundation): 4-6 hours
- Phase 1 (Safe Changes): 3-5 hours
- Phase 2 (Tracking): 1-2 hours
- Phase 3 (Enforcement): 5-7 hours

**Critical Path**:
1. Agent discovery fix (blocks everything)
2. Documentation update (enables development)
3. TASK-ENF3 + TASK-ENF5 redesign (safe implementations)
4. Enhanced tracking (TASK-ENF2)
5. Enforcement with local support (TASK-ENF1, TASK-ENF4)

**Parallelization Opportunities**:
- TASK-ENF3 can be done during Phase 0
- TASK-ENF5 redesign can be done during Phase 0
- TASK-ENF2 enhancement can be done during Phase 1

**Realistic Timeline**: 2-3 days for single developer

---

## Critical Success Factors

### CSF #1: Agent Discovery Must Support `.claude/agents/`

**Why Critical**:
- Templates copy agents to `.claude/agents/` during initialization
- Without discovery support, these agents are invisible
- All enforcement mechanisms depend on agent discovery
- Template workflows break entirely without this

**Acceptance Criteria**:
- [ ] Discovery scans `.claude/agents/` as first source
- [ ] Local agents take precedence over global agents
- [ ] Template-initialized agents are immediately discoverable
- [ ] Duplicate agent names resolved with clear precedence

**Test Scenario**:
```bash
# 1. Initialize template
taskwright init react-typescript

# 2. Verify agents copied
ls .claude/agents/react-state-specialist.md  # Should exist

# 3. Run task with React stack
/task-create "Add authentication" stack:react
/task-work TASK-001

# 4. Verify local agent selected
# Expected: .claude/agents/react-state-specialist.md invoked
# NOT: installer/core/agents/react-state-specialist.md
```

---

### CSF #2: TASK-ENF5 Must Use Dynamic Discovery

**Why Critical**:
- Static agent tables become stale immediately
- Can't accommodate template customizations
- Creates confusion when local agents don't match table
- Maintenance burden grows with every new template

**Acceptance Criteria**:
- [ ] No hardcoded agent paths in task-work.md
- [ ] Discovery process documented clearly
- [ ] Precedence rules explained with examples
- [ ] Users understand local agents override global

**Test Scenario**:
```bash
# 1. Read task-work.md agent selection section
# Expected: Explanation of discovery, not static table

# 2. Initialize template with custom agent
taskwright init custom-template  # Has custom-specialist.md

# 3. Run task
/task-work TASK-001

# 4. Verify custom agent selected (not global fallback)
```

---

### CSF #3: Template Workflows Must Remain Unbroken

**Why Critical**:
- Templates are core value proposition
- Breaking templates destroys user trust
- Enforcement should enhance, not hinder
- Regression would be catastrophic

**Acceptance Criteria**:
- [ ] Template creation works without changes
- [ ] Template initialization registers agents
- [ ] Enforcement validates template agents correctly
- [ ] Phase gates don't block valid template tasks

**Test Scenario**:
```bash
# 1. Create new template
/template-create custom-stack

# 2. Initialize template
taskwright init custom-stack

# 3. Run task workflow
/task-create "Implement feature"
/task-work TASK-001

# 4. Verify enforcement doesn't block
# Expected: Validation passes, gates allow, task completes
```

---

## Recommendations

### Immediate Actions (Before Any Enforcement Implementation)

1. **PAUSE all enforcement task implementation** ⚠️
   - Do NOT implement TASK-ENF1, ENF2, ENF4, ENF5 yet
   - Only TASK-ENF3 is safe to proceed
   - Rationale: Avoid breaking template workflows

2. **Fix agent discovery system** (2-3 hours)
   - Add `.claude/agents/` scanning
   - Implement precedence rules
   - Update documentation
   - Test with template initialization

3. **Update agent-discovery-guide.md** (1-2 hours)
   - Document `.claude/agents/` scanning
   - Explain precedence: Local > User > Global
   - Add troubleshooting section
   - Include discovery flow diagram

---

### Phase 1: Foundation Fixes (4-6 hours)

4. **Test template agent discovery** (1 hour)
   - Initialize each template (react-typescript, fastapi-python, etc.)
   - Verify agents copied correctly
   - Confirm discovery finds local agents
   - Validate precedence rules work

5. **Update `/template-init` command** (1-2 hours)
   - Add agent registration verification
   - Log registered agents for user
   - Test discovery after initialization
   - Handle missing metadata gracefully

6. **Update `/agent-enhance` command** (2-3 hours)
   - Validate discovery metadata exists
   - Add missing metadata with prompts
   - Verify agent discoverable after enhancement
   - Update enhancement checklist

---

### Phase 2: Safe Enforcement (3-5 hours)

7. **Implement TASK-ENF3** (1-2 hours)
   - Add prominent invocation messages
   - No dependencies, safe to proceed
   - Visual confirmation for users

8. **Redesign and implement TASK-ENF5** (2-3 hours)
   - Remove static agent table
   - Add discovery explanation
   - Document precedence rules
   - Include examples

---

### Phase 3: Enhanced Enforcement (6-9 hours)

9. **Enhance TASK-ENF2** (1-2 hours)
   - Add agent source path tracking
   - Record local/user/global source
   - Update tracking reports

10. **Update TASK-ENF1** (2-3 hours)
    - Local agent validation
    - Precedence-aware checks
    - Test with template agents

11. **Update TASK-ENF4** (2-3 hours)
    - Local agent gate validation
    - Precedence-aware checkpoints
    - Test with template workflows

12. **Integration testing** (1 hour)
    - End-to-end template workflow
    - Verify all enforcement mechanisms
    - Confirm no regressions

---

### Long-Term Improvements (Future)

13. **Add `/agent-list` command**
    - Show all discovered agents
    - Indicate source (local/user/global)
    - Help users understand precedence

14. **Add agent discovery debugging**
    - Verbose mode showing discovery process
    - Explain why specific agent selected
    - Help troubleshoot agent issues

15. **Create agent precedence visualization**
    - Interactive diagram or tool
    - Show which agents override others
    - Clarify template customization

---

## Appendix A: Test Scenarios

### Scenario 1: Template Initialization and Discovery

**Goal**: Verify template agents are discovered after initialization

**Steps**:
```bash
# 1. Initialize react-typescript template
taskwright init react-typescript

# 2. Verify agents copied to .claude/agents/
ls -la .claude/agents/
# Expected: react-state-specialist.md exists

# 3. Check agent metadata
cat .claude/agents/react-state-specialist.md
# Expected: frontmatter with stack, phase, capabilities, keywords

# 4. Create React task
/task-create "Add user authentication with React hooks" stack:react

# 5. Run task workflow
/task-work TASK-001

# 6. Verify local agent invoked (not global)
# Expected: Logs show ".claude/agents/react-state-specialist.md" invoked
#           NOT "installer/core/agents/react-state-specialist.md"
```

**Expected Outcome**: ✅ Local agent discovered and invoked

**Failure Mode**: ❌ Global agent invoked instead (discovery gap)

---

### Scenario 2: Local Agent Precedence

**Goal**: Verify local agents override global agents with same name

**Steps**:
```bash
# 1. Initialize template
taskwright init react-typescript
# Result: .claude/agents/react-state-specialist.md created

# 2. Modify local agent (add custom capability)
echo "Custom capability: form-validation" >> .claude/agents/react-state-specialist.md

# 3. Verify global agent still exists
ls installer/core/agents/react-state-specialist.md
# Expected: Exists and unchanged

# 4. Run task workflow
/task-create "Build form validation" stack:react
/task-work TASK-002

# 5. Check which agent invoked
# Expected: Local agent (.claude/agents/) with custom capability
#           NOT global agent (installer/core/agents/)
```

**Expected Outcome**: ✅ Local agent takes precedence

**Failure Mode**: ❌ Global agent invoked (no precedence rules)

---

### Scenario 3: Enforcement with Template Agents

**Goal**: Verify enforcement mechanisms work with template agents

**Steps**:
```bash
# 1. Initialize template
taskwright init fastapi-python

# 2. Create Python API task
/task-create "Add user authentication endpoint" stack:python

# 3. Run task with enforcement (after fixes)
/task-work TASK-003

# Expected Checkpoints:
# - Phase 3 Gate: Verify python-api-specialist discoverable
# - Pre-Report Validation: Verify local agent validated
# - Tracking: Record local agent invocation with source path
```

**Expected Outcome**: ✅ All enforcement passes, task completes

**Failure Mode**: ❌ Validation fails with "agent not found"

---

### Scenario 4: Agent Enhancement and Discovery

**Goal**: Verify enhanced agents become discoverable

**Steps**:
```bash
# 1. Create custom agent without metadata
cat > .claude/agents/custom-specialist.md <<EOF
# Custom Specialist

This is a custom agent.

## Capabilities
- Custom capability 1
- Custom capability 2
EOF

# 2. Run agent enhancement
/agent-enhance .claude/agents/custom-specialist.md

# 3. Verify metadata added
cat .claude/agents/custom-specialist.md
# Expected: Frontmatter with stack, phase, capabilities, keywords

# 4. Test discovery
/task-create "Custom task" stack:custom
/task-work TASK-004

# 5. Verify enhanced agent discovered
# Expected: custom-specialist.md invoked (or task-manager if stack not matched)
```

**Expected Outcome**: ✅ Enhanced agent has metadata and is discoverable

**Failure Mode**: ❌ Agent still missing metadata, not discovered

---

## Appendix B: Discovery Implementation Pseudo-Code

### Current Discovery (BROKEN)

```python
# lib/agent_discovery.py (current, BROKEN)

def discover_agents(phase: str, stack: str, keywords: list) -> list:
    """Discover agents matching phase, stack, and keywords"""

    all_agents = []

    # Scan global agents
    global_agents = glob("installer/core/agents/*.md")
    all_agents.extend(parse_agents(global_agents))

    # Scan template agents (TEMPLATES, not initialized)
    template_agents = glob("installer/core/templates/*/agents/*.md")
    all_agents.extend(parse_agents(template_agents))

    # Scan user agents
    user_agents = glob("~/.agentecflow/agents/*.md")
    all_agents.extend(parse_agents(user_agents))

    # MISSING: .claude/agents/ (where template-init copies local agents)

    # Filter and rank by relevance
    matched = filter_by_criteria(all_agents, phase, stack, keywords)
    ranked = rank_by_relevance(matched)

    return ranked[0] if ranked else "task-manager"  # fallback
```

**Problem**: `.claude/agents/` not scanned → template agents invisible

---

### Proposed Discovery (FIXED)

```python
# lib/agent_discovery.py (proposed, FIXED)

def discover_agents(phase: str, stack: str, keywords: list) -> list:
    """Discover agents matching phase, stack, and keywords with precedence"""

    agent_sources = {}  # name -> (agent_data, source, priority)

    # Priority levels
    PRIORITY_LOCAL = 1   # Highest
    PRIORITY_USER = 2
    PRIORITY_GLOBAL = 3
    PRIORITY_TEMPLATE = 4  # Lowest

    # Scan local agents (HIGHEST PRIORITY) - NEW
    local_agents = glob(".claude/agents/*.md")
    for agent in parse_agents(local_agents):
        agent_sources[agent.name] = (agent, "local", PRIORITY_LOCAL)

    # Scan user agents
    user_agents = glob("~/.agentecflow/agents/*.md")
    for agent in parse_agents(user_agents):
        if agent.name not in agent_sources:  # Only add if not already found
            agent_sources[agent.name] = (agent, "user", PRIORITY_USER)

    # Scan global agents
    global_agents = glob("installer/core/agents/*.md")
    for agent in parse_agents(global_agents):
        if agent.name not in agent_sources:
            agent_sources[agent.name] = (agent, "global", PRIORITY_GLOBAL)

    # Scan template agents (lowest priority)
    template_agents = glob("installer/core/templates/*/agents/*.md")
    for agent in parse_agents(template_agents):
        if agent.name not in agent_sources:
            agent_sources[agent.name] = (agent, "template", PRIORITY_TEMPLATE)

    # Extract unique agents (duplicates already removed by precedence)
    all_agents = [data for data, source, priority in agent_sources.values()]

    # Filter and rank by relevance
    matched = filter_by_criteria(all_agents, phase, stack, keywords)
    ranked = rank_by_relevance(matched)

    if ranked:
        best_match = ranked[0]
        source = next(s for n, (a, s, p) in agent_sources.items() if a == best_match)
        log(f"Selected: {best_match.name} (source: {source})")
        return best_match
    else:
        log("No match found, using task-manager (fallback)")
        return "task-manager"
```

**Fixes**:
- ✅ Scans `.claude/agents/` first (highest priority)
- ✅ Implements precedence: Local > User > Global > Template
- ✅ Removes duplicates, keeping highest priority source
- ✅ Logs selected agent and source for debugging

---

## Appendix C: Precedence Examples

### Example 1: Local Agent Overrides Global

**Setup**:
```
installer/core/agents/react-state-specialist.md (global)
.claude/agents/react-state-specialist.md (local, from template)
```

**Task**: React implementation task

**Discovery Result**:
```
Selected: react-state-specialist (source: local)
```

**Rationale**: Local agent takes precedence over global

---

### Example 2: User Agent Overrides Global

**Setup**:
```
installer/core/agents/python-api-specialist.md (global)
~/.agentecflow/agents/python-api-specialist.md (user custom)
```

**Task**: Python API implementation

**Discovery Result**:
```
Selected: python-api-specialist (source: user)
```

**Rationale**: User customization overrides global default

---

### Example 3: Local Overrides Both User and Global

**Setup**:
```
installer/core/agents/dotnet-domain-specialist.md (global)
~/.agentecflow/agents/dotnet-domain-specialist.md (user)
.claude/agents/dotnet-domain-specialist.md (local, project-specific)
```

**Task**: .NET domain implementation

**Discovery Result**:
```
Selected: dotnet-domain-specialist (source: local)
```

**Rationale**: Local > User > Global precedence chain

---

### Example 4: Fallback to Global When Local Missing

**Setup**:
```
installer/core/agents/react-state-specialist.md (global)
.claude/agents/ (empty, no local agents)
```

**Task**: React implementation

**Discovery Result**:
```
Selected: react-state-specialist (source: global)
```

**Rationale**: Global agent used when no local override exists

---

### Example 5: Fallback to task-manager When No Match

**Setup**:
```
installer/core/agents/ (no Go specialists)
.claude/agents/ (no Go specialists)
```

**Task**: Go implementation

**Discovery Result**:
```
No match found, using task-manager (fallback)
```

**Rationale**: No specialist found, use general-purpose task-manager

---

## Appendix D: Enforcement Task Dependency Graph

```
Foundation (Phase 0)
├── Fix Agent Discovery (.claude/agents/ scanning)
│   └── BLOCKS: TASK-ENF1, TASK-ENF2, TASK-ENF4, TASK-ENF5
└── Update Documentation (agent-discovery-guide.md)
    └── ENABLES: All enforcement development

Safe Implementations (Phase 1)
├── TASK-ENF3 (Invocation Messages)
│   └── No dependencies, can implement immediately
└── TASK-ENF5 (Agent Table Redesign)
    └── Depends on: Agent Discovery documentation

Enhanced Tracking (Phase 2)
└── TASK-ENF2 (Invocation Tracking)
    └── Depends on: Agent Discovery fix (for source path tracking)

Enforcement with Local Support (Phase 3)
├── TASK-ENF1 (Pre-Report Validation)
│   └── Depends on: Agent Discovery fix, TASK-ENF2 (for tracking)
└── TASK-ENF4 (Phase Gate Checkpoints)
    └── Depends on: Agent Discovery fix, TASK-ENF1 (for validation logic)
```

**Critical Path**: Agent Discovery fix → All enforcement tasks

---

## Review Metadata

**Review Duration**: 2 hours (standard depth)
**Documents Reviewed**: 12 files
**Findings Identified**: 6 (1 critical, 2 high, 2 medium, 1 low)
**Regression Risks**: 3 critical, 2 high, 1 medium
**Recommendations**: 15 action items across 3 phases
**Estimated Fix Effort**: 10-16 hours
**Review Status**: ✅ Complete
**Decision Required**: Yes (Accept with Modifications recommended)

---

## Conclusion

The enforcement tasks are well-designed but have critical integration gaps with template workflows due to agent discovery not supporting `.claude/agents/`. **PAUSE all enforcement implementation** until discovery is fixed and documentation updated.

**Next Steps**:
1. Review findings with stakeholders
2. Approve recommended approach (Accept with Modifications)
3. Create Phase 0 foundation fix tasks
4. Implement fixes before any enforcement tasks
5. Test thoroughly with template workflows
6. Proceed with enforcement implementation in phases

**Risk Assessment**: ⚠️ HIGH risk of breaking template workflows if enforcement implemented without fixes. Mitigation: Implement recommended fixes first.

---

**Report Generated**: 2025-11-27
**Reviewer**: architectural-reviewer (claude-opus-4-20250514)
**Review Mode**: architectural
**Review Depth**: standard
