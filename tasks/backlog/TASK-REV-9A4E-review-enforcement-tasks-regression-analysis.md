---
id: TASK-REV-9A4E
title: Review enforcement tasks for regressions in template/agent workflows
status: review_complete
created: 2025-11-27T13:55:00Z
updated: 2025-11-27T16:30:00Z
priority: high
tags: [review, regression-analysis, template-workflow, agent-discovery]
task_type: review
decision_required: false
decision_made: accept_with_modifications
epic: null
feature: null
requirements: []
dependencies: []
complexity: 0
related_to: TASK-8D3F
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 6
  recommendations_count: 15
  decision: accept_with_modifications
  report_path: .claude/reviews/TASK-REV-9A4E-review-report.md
  completed_at: 2025-11-27T16:30:00Z
  follow_up_tasks:
    - TASK-ENF-P0-1 (Fix agent discovery)
    - TASK-ENF-P0-2 (Update agent discovery documentation)
    - TASK-ENF-P0-3 (Update template-init)
    - TASK-ENF-P0-4 (Update agent-enhance)
---

# Review Task: Enforcement Tasks Regression Analysis

## Context

Five agent invocation enforcement tasks (TASK-ENF1 through TASK-ENF5) have been created to improve protocol compliance in `/task-work`. Before implementation, we need to analyze these tasks for potential regressions, particularly in workflows that create and initialize agents from local codebases.

**User Concerns**:
1. **Template workflows** (`/template-create`, `/template-init`) may be affected
2. **Agent enhancement** (`/agent-enhance`) may need updates
3. **TASK-ENF5** (agent selection table update) may not account for template-generated agents
4. **Agent discovery** from local codebases vs global agents needs consideration

**Critical Insight**: The agent selection table in `task-work.md` references global agents, but templates create **local agents** that are initialized via the template. This creates a potential mismatch.

## Review Objective

Analyze the 5 enforcement tasks to:
1. **Identify regression risks** in template and agent creation workflows
2. **Verify agent discovery compatibility** with template-generated agents
3. **Assess TASK-ENF5 accuracy** regarding local vs global agent handling
4. **Recommend adjustments** to prevent breaking existing workflows

## Review Scope

### Documents to Review

1. **Enforcement Tasks**:
   - `tasks/backlog/agent-invocation-enforcement/TASK-ENF1-add-pre-report-validation-checkpoint.md`
   - `tasks/backlog/agent-invocation-enforcement/TASK-ENF2-add-agent-invocation-tracking.md`
   - `tasks/backlog/agent-invocation-enforcement/TASK-ENF3-add-prominent-invocation-messages.md`
   - `tasks/backlog/agent-invocation-enforcement/TASK-ENF4-add-phase-gate-checkpoints.md`
   - `tasks/backlog/agent-invocation-enforcement/TASK-ENF5-update-agent-selection-table.md`

2. **Supporting Documents**:
   - `tasks/backlog/agent-invocation-enforcement/IMPLEMENTATION-GUIDE.md`
   - `tasks/backlog/agent-invocation-enforcement/README.md`

3. **Affected Commands**:
   - `installer/global/commands/template-create.md`
   - `installer/global/commands/template-init.md`
   - `installer/global/commands/agent-enhance.md`
   - `installer/global/commands/task-work.md` (agent selection table)

4. **Agent Discovery System**:
   - `docs/guides/agent-discovery-guide.md`
   - `installer/global/commands/lib/agent_discovery.py` (if exists)
   - Template-generated agent structure

## Review Questions

### Q1: Template Workflow Compatibility

**Question**: Will the enforcement changes break template creation and initialization workflows?

**Investigation Areas**:
- Does `/template-create` generate agents compatible with new tracking/validation?
- Does `/template-init` properly register template agents for discovery?
- Will template-generated agents be found by agent discovery system?
- Do template agents have required metadata (stack, phase, capabilities, keywords)?

**Specific Concerns**:
- TASK-ENF2 (tracking): Can tracker find template agents?
- TASK-ENF4 (phase gates): Will gates work with template agents?
- TASK-ENF1 (validation): Will validation recognize template agents as valid?

**Expected Output**: Compatibility matrix showing which enforcement tasks affect template workflows

---

### Q2: Agent Discovery for Template-Generated Agents

**Question**: Does the agent discovery system properly handle agents created from templates?

**Investigation Areas**:
- **Agent Sources**: Where does discovery look for agents?
  - Global: `installer/global/agents/*.md`
  - Template: `installer/global/templates/*/agents/*.md`
  - **User/Local**: `.claude/agents/*.md` (created by template-init)
- **Discovery Priority**: Which source takes precedence?
- **Metadata Requirements**: Do template agents have discovery metadata?

**Current Understanding** (from TASK-8D3F review):
```python
# Agent Discovery Flow (from agent-discovery-guide.md)
def discover_agents(phase, stack, keywords):
    # 1. Scan global agents
    global_agents = scan("installer/global/agents/*.md")

    # 2. Scan template agents
    template_agents = scan("installer/global/templates/*/agents/*.md")

    # 3. Scan user agents
    user_agents = scan("~/.agentecflow/agents/*.md")  # ← LOCAL AGENTS

    # Merge and rank by relevance
    all_agents = global_agents + template_agents + user_agents
    return rank_by_relevance(all_agents, phase, stack, keywords)
```

**Key Question**: When `/template-init react-typescript` copies agents to `.claude/agents/`, will those agents be discovered during `/task-work`?

**Expected Output**: Discovery flow diagram showing local agent resolution

---

### Q3: TASK-ENF5 Agent Table Accuracy

**Question**: Is TASK-ENF5's agent selection table update correct for template workflows?

**Current TASK-ENF5 Approach**:
- Updates `task-work.md` agent table to reference only global agents
- Suggests using `dotnet-domain-specialist` for MAUI instead of non-existent `maui-usecase-specialist`
- Does NOT account for template-generated local agents

**Problem Scenario**:
```bash
# User initializes react-typescript template
taskwright init react-typescript

# Template copies agents to .claude/agents/
.claude/agents/
├── react-state-specialist.md      # LOCAL copy
├── react-testing-specialist.md    # LOCAL copy (if exists)
└── ...

# User runs task-work
/task-work TASK-001  # React stack detected

# Question: Which agent is invoked?
# Option A: .claude/agents/react-state-specialist.md (local)
# Option B: installer/global/agents/react-state-specialist.md (global)
# Option C: task-manager (fallback if discovery fails)
```

**TASK-ENF5 Assumption**: Agent table should reference global agents only

**Reality Check**: Templates create LOCAL agents that may override global agents

**Potential Issue**: If TASK-ENF5 updates table to reference `dotnet-domain-specialist` for MAUI, but a MAUI template creates `maui-usecase-specialist` locally, which one gets invoked?

**Expected Output**: Clarification of local vs global agent precedence and TASK-ENF5 adjustments if needed

---

### Q4: Agent Enhancement Workflow Impact

**Question**: Does `/agent-enhance` need updates to ensure template agents are compatible with enforcement?

**Investigation Areas**:
- Does `/agent-enhance` add discovery metadata (stack, phase, capabilities, keywords)?
- When template agents are enhanced, do they become discoverable?
- Will enhanced template agents work with tracking (ENF2) and validation (ENF1)?

**Current `/agent-enhance` Behavior** (assumed):
```bash
# Enhance a template agent
/agent-enhance .claude/agents/react-state-specialist.md

# Expected: Adds/updates frontmatter metadata for discovery
# Expected: Agent becomes compatible with enforcement system
```

**Risk**: If `/agent-enhance` doesn't add required metadata, template agents won't be discovered

**Expected Output**: Agent enhancement requirements checklist

---

### Q5: Agent Selection Priority and Fallback

**Question**: What happens when both global and local agents exist for the same stack?

**Scenario**:
```
Global: installer/global/agents/react-state-specialist.md (stack: [react])
Local:  .claude/agents/react-state-specialist.md (stack: [react])

Task: React stack detected, Phase 3 (Implementation)

Which agent is invoked?
A. Local agent (user customization takes precedence)
B. Global agent (canonical source)
C. Most recently modified
D. Explicit priority in discovery config
```

**Current Agent Discovery Guide** (from TASK-8D3F review):
- Scans: global, template, user agents
- Ranks by relevance (stack + phase + keywords)
- No explicit priority mentioned for duplicates

**Risk**: If priority is unclear, enforcement validation may fail inconsistently

**Expected Output**: Priority rules documentation and enforcement task adjustments

---

### Q6: Template-Init Agent Registration

**Question**: Does `/template-init` properly register template agents for discovery?

**Investigation Areas**:
- When `/template-init react-typescript` copies agents to `.claude/agents/`, are they immediately discoverable?
- Does template-init update any agent registry or cache?
- Are template agents copied with correct metadata?

**Template-Init Flow** (assumed):
```bash
taskwright init react-typescript

# 1. Copy agents
cp installer/global/templates/react-typescript/agents/*.md .claude/agents/

# 2. Register agents for discovery (?)
# Question: Is there a registration step?

# 3. Agents should be immediately available
/task-work TASK-001  # Should find .claude/agents/react-state-specialist.md
```

**Risk**: If registration is missing, discovery may not find local agents

**Expected Output**: Template-init agent registration verification

---

## Review Deliverables

### Deliverable 1: Regression Risk Matrix

**Content**:
| Enforcement Task | Template Workflow Risk | Agent Discovery Risk | Severity | Mitigation Required |
|------------------|------------------------|---------------------|----------|---------------------|
| TASK-ENF1 | ... | ... | ... | ... |
| TASK-ENF2 | ... | ... | ... | ... |
| TASK-ENF3 | ... | ... | ... | ... |
| TASK-ENF4 | ... | ... | ... | ... |
| TASK-ENF5 | ... | ... | ... | ... |

**Format**: Markdown table with risk assessment

---

### Deliverable 2: Agent Discovery Flow Diagram

**Content**:
- Visual diagram showing agent discovery order (global → template → local)
- Priority rules when duplicates exist
- Fallback behavior when no agent found
- Integration with enforcement tracking

**Format**: Mermaid diagram or ASCII flowchart

---

### Deliverable 3: TASK-ENF5 Correction Recommendations

**Content**:
- Analysis of current TASK-ENF5 approach
- Identification of local vs global agent handling gaps
- Specific corrections needed to agent selection table update strategy
- Template agent accommodation strategy

**Format**: Markdown with specific file/line corrections

---

### Deliverable 4: Template Workflow Adjustments

**Content**:
- Required changes to `/template-create` (if any)
- Required changes to `/template-init` (if any)
- Required changes to `/agent-enhance` (if any)
- Agent metadata requirements for template compatibility

**Format**: Checklist with specific implementation tasks

---

### Deliverable 5: Decision Summary

**Content**:
- Which enforcement tasks can proceed as-is
- Which tasks need modifications before implementation
- Priority order for addressing issues
- Estimated effort for corrections

**Format**: Executive summary with actionable recommendations

---

## Review Approach

### Phase 1: Document Analysis

1. Read all 5 enforcement task files
2. Read IMPLEMENTATION-GUIDE.md and README.md
3. Map out affected workflows (template-create, template-init, agent-enhance)
4. Identify integration points with agent discovery

### Phase 2: Agent Discovery Deep Dive

1. Review agent-discovery-guide.md for source priority rules
2. Examine template structure (how agents are stored)
3. Trace agent discovery flow (global → template → local)
4. Test agent resolution with template-generated agents

### Phase 3: TASK-ENF5 Specific Analysis

1. Review current TASK-ENF5 agent table update approach
2. Identify local agent accommodation gaps
3. Propose corrections to agent selection strategy
4. Validate corrections against template workflows

### Phase 4: Regression Testing Strategy

1. Define test scenarios (template-init → task-work flow)
2. Identify edge cases (duplicate agents, missing metadata)
3. Propose validation tests for each enforcement task
4. Create regression test checklist

### Phase 5: Recommendation Synthesis

1. Summarize all findings
2. Prioritize issues by severity
3. Propose specific corrections to enforcement tasks
4. Estimate effort for adjustments

---

## Decision Framework

At the end of the review, the following decision options will be presented:

### [A] Accept with Modifications

Enforcement tasks are sound but need specific adjustments before implementation.

**Next Steps**:
- Create modification tasks for identified issues
- Update TASK-ENF5 with local agent handling
- Update IMPLEMENTATION-GUIDE.md with template workflow considerations

---

### [I] Implement Selected Tasks Only

Some enforcement tasks can proceed as-is, others need revision.

**Example**: "Implement TASK-ENF1, TASK-ENF2, TASK-ENF3 as-is. Revise TASK-ENF5 before implementation."

**Next Steps**:
- Proceed with approved tasks
- Create revision tasks for blocked tasks

---

### [R] Revise Analysis

Request deeper investigation on specific areas before deciding.

**Example Areas**:
- Agent discovery source priority rules
- Template-init registration mechanism
- Local vs global agent precedence

**Next Steps**: Re-run review with adjusted scope

---

### [B] Block All Tasks

Critical regressions identified, all enforcement tasks must be revised.

**Next Steps**:
- Document blocking issues
- Create comprehensive revision plan
- Re-submit tasks after corrections

---

## Success Criteria

### SC1: Regression Risks Identified

- [ ] All template workflow integration points analyzed
- [ ] Agent discovery compatibility verified
- [ ] Local vs global agent handling clarified
- [ ] Specific regression scenarios documented with examples

### SC2: TASK-ENF5 Accuracy Verified

- [ ] Agent selection table update approach validated
- [ ] Local agent accommodation strategy defined
- [ ] Template agent compatibility confirmed
- [ ] Corrections specified (if needed)

### SC3: Template Workflow Compatibility

- [ ] `/template-create` impact assessed
- [ ] `/template-init` agent registration verified
- [ ] `/agent-enhance` metadata requirements confirmed
- [ ] No breaking changes to existing workflows

### SC4: Recommendations Actionable

- [ ] Each issue has specific correction proposal
- [ ] Effort estimates provided for adjustments
- [ ] Priority ranking clear and justified
- [ ] Implementation order specified

---

## Expected Duration

**Review Mode**: architectural (focus on workflow integration and compatibility)
**Depth**: standard (1-2 hours)
**Output**: Regression risk matrix + TASK-ENF5 corrections + workflow adjustments

---

## Next Steps After Review

1. Present findings and recommendations at decision checkpoint
2. If [A]ccept with modifications: Create adjustment tasks for enforcement tasks
3. If [I]mplement selected: Proceed with approved tasks, revise others
4. If [R]evise: Adjust scope and re-run review
5. If [B]lock all: Create comprehensive revision plan

---

## Key Questions to Answer

**Primary Questions**:
1. ✅ Do template workflows break with enforcement changes? (Yes/No + specifics)
2. ✅ Does TASK-ENF5 correctly handle local agents? (Yes/No + corrections)
3. ✅ Is agent discovery compatible with template agents? (Yes/No + adjustments)
4. ✅ What modifications are needed before implementation? (Specific tasks)

**Secondary Questions**:
5. What is the agent discovery priority order? (global > template > local, or different?)
6. Does `/agent-enhance` add required metadata? (Yes/No + missing fields)
7. Does `/template-init` register agents for discovery? (Yes/No + registration mechanism)

---

**This is a REVIEW task** - Use `/task-review TASK-REV-9A4E --mode=architectural --depth=standard` to execute this analysis.
