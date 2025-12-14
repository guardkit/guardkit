---
id: TASK-REV-1DDD
title: Analyze self-templating GuardKit and RequireKit using template-create and agent-enhance
status: completed
created: 2025-12-13T10:00:00Z
updated: 2025-12-13T13:15:00Z
priority: high
tags: [progressive-disclosure, rules-structure, template-create, agent-enhance, self-reference, dogfooding, cross-repo]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 7
decision_required: true
related_tasks:
  - TASK-REV-PD01
  - TASK-REV-F1BA
  - TASK-TC-DEFAULT-FLAGS
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  recommendation: partial_proceed
  findings_count: 8
  recommendations_count: 6
  decision: hybrid_workflow
  report_path: .claude/reviews/TASK-REV-1DDD-review-report.md
  completed_at: 2025-12-13T12:30:00Z
  key_findings:
    - GuardKit .claude/ is 16MB but only 500KB relevant to template
    - RequireKit already optimized with progressive disclosure
    - Full template generation NOT recommended (creates maintenance burden)
    - Rules structure provides 40-50% context reduction for GuardKit
    - Hybrid approach recommended (use template-create --dry-run as reference)
  implementation_decision: implement
  implementation_tasks_created:
    folder: tasks/backlog/self-template-enhancement/
    task_count: 8
    waves: 4
---

# Task: Analyze self-templating GuardKit and RequireKit using template-create and agent-enhance

## Description

Analyze the feasibility and approach for applying GuardKit's progressive disclosure and Claude rules structure to the GuardKit and RequireKit repositories themselves by using the `/template-create` and `/agent-enhance` commands. This is a "dogfooding" analysis to determine:

1. Can we use `/template-create` to generate templates from these repositories?
2. Can we then use `guardkit init` to apply the generated template back?
3. What would be the workflow for maintaining consistency between source repos and generated templates?
4. How does this interact with the existing `.claude/` configurations in both repos?

## Background

GuardKit already has:
- Progressive disclosure implemented for templates (split files, -ext.md)
- Claude rules structure support (`--use-rules-structure` flag)
- `/template-create` command for extracting templates from existing projects
- `/agent-enhance` command for improving agent files

Both GuardKit and RequireKit have existing `.claude/` directories that are git-managed. The question is whether we should:
1. Treat them like any other project and generate templates
2. Use the templates to initialize/update the repos
3. Maintain the repos as the source of truth vs templates as the source of truth

## Target Repositories

| Repository | Location | Current State |
|------------|----------|---------------|
| GuardKit | `/Users/richardwoollcott/Projects/appmilla_github/guardkit` | `.claude/` is source of truth, git-managed |
| RequireKit | `/Users/richardwoollcott/Projects/appmilla_github/require-kit` | `.claude/` is source of truth, git-managed |

## Analysis Objectives

### 1. Current State Assessment

- [ ] Document current `.claude/` structure in GuardKit
- [ ] Document current `.claude/` structure in RequireKit
- [ ] Identify differences between the two configurations
- [ ] Measure current file sizes and token usage

### 2. Template Creation Feasibility

- [ ] Can `/template-create` successfully parse GuardKit as source?
- [ ] What would the output look like?
- [ ] Would it generate rules structure or split files?
- [ ] What command flags would be optimal?

**Test Commands:**
```bash
# Dry-run template creation for GuardKit
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
/template-create --name guardkit-dev --dry-run

# Dry-run for RequireKit
cd /Users/richardwoollcott/Projects/appmilla_github/require-kit
/template-create --name requirekit-dev --dry-run
```

### 3. Agent Enhancement Analysis

- [ ] Which agents in GuardKit would benefit from enhancement?
- [ ] Which agents in RequireKit would benefit from enhancement?
- [ ] Would `/agent-enhance` add value to already comprehensive agents?
- [ ] What enhancement strategy would be appropriate?

### 4. Workflow Options

Evaluate three potential workflows:

**Option A: Template-First (Generate then Apply)**
```bash
# 1. Generate template from current repo state
/template-create --name guardkit-dev --output-location ~/.agentecflow/templates/

# 2. Apply template back to repo
guardkit init guardkit-dev --force

# 3. Maintain template separately, periodically regenerate
```

**Option B: Repo-First (Manual Maintenance)**
```bash
# 1. Keep .claude/ as source of truth
# 2. Use /agent-enhance directly on repo files
# 3. Apply progressive disclosure/rules manually to repo files

/agent-enhance .claude/agents/task-manager.md .
```

**Option C: Hybrid (Selective Application)**
```bash
# 1. Generate template to understand ideal structure
/template-create --name guardkit-reference --dry-run

# 2. Cherry-pick improvements back to repo
# - Apply rules structure to specific areas
# - Enhance specific agents
# - Keep some files unchanged
```

### 5. Rules Structure Applicability

- [ ] Would rules structure reduce context usage for GuardKit development?
- [ ] What rules would be conditionally loaded?
- [ ] Is the overhead of maintaining rules/ worth the savings?

### 6. Risk Assessment

- [ ] Risk of breaking existing `.claude/` configuration
- [ ] Risk of template generation not capturing all customizations
- [ ] Risk of circular dependency (template derived from repo that uses template)
- [ ] Rollback strategy if something breaks

## Acceptance Criteria

- [ ] Current state documented for both repositories
- [ ] `/template-create` tested (dry-run) on both repos
- [ ] Workflow options evaluated with pros/cons
- [ ] Recommended approach identified with justification
- [ ] Implementation plan created if recommendation is to proceed
- [ ] Risk mitigation strategies defined

## Deliverables

1. **Analysis Report** (`.claude/reviews/TASK-REV-1DDD-review-report.md`)
   - Current state assessment
   - Feasibility analysis results
   - Workflow comparison matrix
   - Recommendation with rationale

2. **Command Reference** (if proceeding)
   - Exact commands to run
   - Order of operations
   - Verification steps

3. **Implementation Tasks** (if proceeding)
   - Breakdown of work for each repo
   - Dependencies between tasks

## Decision Framework

After review, recommend one of:

| Decision | Criteria |
|----------|----------|
| **[P]roceed** | High value, low risk, clear workflow identified |
| **[P]artial** | Value in some areas, proceed selectively |
| **[D]efer** | Not enough value now, revisit after X |
| **[R]eject** | Overhead exceeds benefits, maintain current approach |

## Questions to Answer

1. **Is self-templating valuable?** Do we gain enough from treating these repos like user projects?

2. **Which workflow?** Template-first, repo-first, or hybrid?

3. **Rules structure benefit?** Is the context reduction worth the maintenance overhead for development repos?

4. **Maintenance burden?** Who regenerates templates, how often, what triggers updates?

5. **Template vs Repo priority?** If they diverge, which is source of truth?

## Estimated Effort

- Analysis: 3-4 hours
- Testing (dry-runs): 1-2 hours
- Report generation: 1-2 hours
- **Total: 5-8 hours**

## Next Steps

After creating this task:
1. Execute review: `/task-review TASK-REV-1DDD --mode=architectural --depth=standard`
2. Review findings and make decision
3. If [P]roceed or [P]artial: Create implementation tasks
