---
id: TASK-DOC-F3BA
title: Review documentation accuracy for template-create, agent-enhance, template-init, and task-review commands
status: review_complete
task_type: review
created: 2025-11-27T00:00:00Z
updated: 2025-11-27T00:00:00Z
priority: high
tags: [documentation, review, templates, commands]
complexity: 6
decision_required: true
review_results:
  mode: architectural
  depth: standard
  score: 85
  findings_count: 13
  recommendations_count: 16
  decision: implement
  report_path: .claude/task-plans/TASK-DOC-F3BA-review-report.md
  completed_at: 2025-11-27T02:00:00Z
---

# Task: Review Documentation Accuracy for Key Commands

## Context

Following the implementation guide in [DOCUMENTATION-IMPLEMENTATION-GUIDE.md](DOCUMENTATION-IMPLEMENTATION-GUIDE.md), we have previously completed TASK-063 to update documentation for 6 templates. However, since that task was completed, we have made significant updates to several core commands:

- **template-create**: New features and workflow changes
- **agent-enhance**: Enhanced boundary sections (ALWAYS/NEVER/ASK) and capabilities
- **template-init**: Updated initialization process
- **task-review**: New review modes and decision checkpoint system

## Objective

Conduct a comprehensive review to:

1. **Audit current documentation** against actual command implementations
2. **Identify discrepancies** between documented and actual behavior
3. **Detect missing documentation** for new features
4. **Generate task list** of required documentation updates

## Scope

### Commands to Review

1. **template-create** ([installer/core/commands/template-create.md](../../../installer/core/commands/template-create.md))
   - Phase 5.5: Agent Enhancement section
   - Boundary sections (ALWAYS/NEVER/ASK) documentation
   - Template validation levels (1-3)
   - Output location flags (--output-location=repo)
   - Agent enhancement task creation (default behavior from TASK-UX-3A8D)

2. **agent-enhance** ([installer/core/commands/agent-enhance.md](../../../installer/core/commands/agent-enhance.md))
   - Boundary sections format and validation
   - Enhancement strategies (ai/static/hybrid)
   - GitHub best practices integration
   - Relationship with /agent-format

3. **template-init** ([installer/core/commands/template-init.md](../../../installer/core/commands/template-init.md))
   - Updated template list (6 templates)
   - Template selection workflow
   - Integration with agent enhancement
   - Repository vs personal template handling

4. **task-review** ([installer/core/commands/task-review.md](../../../installer/core/commands/task-review.md))
   - Five review modes (architectural, code-quality, decision, technical-debt, security)
   - Decision checkpoint system ([A]ccept, [R]evise, [I]mplement, [C]ancel)
   - Review depth levels (quick, standard, comprehensive)
   - Integration with /task-work workflow

### Related Documentation Files

Cross-reference these commands with:
- [CLAUDE.md](../../../CLAUDE.md) - Main project documentation
- [docs/guides/template-philosophy.md](../../../docs/guides/template-philosophy.md)
- [docs/workflows/task-review-workflow.md](../../../docs/workflows/task-review-workflow.md)
- [docs/guides/template-validation-guide.md](../../../docs/guides/template-validation-guide.md)
- [docs/guides/agent-enhancement-decision-guide.md](../../../docs/guides/agent-enhancement-decision-guide.md) (if exists)
- [docs/workflows/incremental-enhancement-workflow.md](../../../docs/workflows/incremental-enhancement-workflow.md) (if exists)

## Review Methodology

### Phase 1: Command Implementation Analysis
1. Read each command's markdown specification
2. Identify all documented features, flags, and workflows
3. Note any recent changes or additions mentioned in git history
4. Compile feature inventory for each command

### Phase 2: Cross-Reference Documentation
1. Check CLAUDE.md for command references
2. Review guide documents for command usage examples
3. Identify workflow documentation dependencies
4. Map command relationships and integration points

### Phase 3: Gap Analysis
For each command, identify:
- **Missing Documentation**: Features implemented but not documented
- **Outdated Documentation**: Documentation that contradicts current implementation
- **Incomplete Documentation**: Partially documented features
- **Broken References**: Links to non-existent files or sections
- **Inconsistent Examples**: Examples that don't match current behavior

### Phase 4: Task Generation
Create a prioritized list of documentation tasks:
- **Critical** (P1): Incorrect information that misleads users
- **High** (P2): Missing documentation for new features
- **Medium** (P3): Incomplete or unclear documentation
- **Low** (P4): Enhancement opportunities (examples, diagrams, etc.)

## Expected Deliverables

### 1. Review Report
Create a comprehensive markdown report: `.claude/task-plans/TASK-DOC-F3BA-review-report.md`

**Structure**:
```markdown
# Documentation Review Report: Template & Task Commands

## Executive Summary
- Commands reviewed: 4
- Critical issues: X
- High-priority gaps: Y
- Recommended tasks: Z

## Command-by-Command Analysis

### template-create
#### Current Documentation Status
- [Feature list with status: ✅ Complete / ⚠️ Incomplete / ❌ Missing]

#### Issues Found
1. **[CRITICAL/HIGH/MEDIUM/LOW]** Issue description
   - Location: [file:line]
   - Impact: [user impact]
   - Recommended action: [task to create]

### [Repeat for agent-enhance, template-init, task-review]

## Cross-Cutting Issues
- [Issues affecting multiple commands or docs]

## Recommended Task List
1. **TASK-DOC-XXXX**: [Task title] (Priority: P1)
   - Scope: [what needs updating]
   - Files affected: [list]
   - Estimated effort: [hours]

[Continue for all tasks...]
```

### 2. Task Specifications
For each identified documentation gap, create a task specification ready for `/task-create`:

```markdown
## Task Specification: TASK-DOC-XXXX

**Title**: Update template-create documentation for Phase 5.5

**Priority**: high

**Tags**: [documentation, template-create, agent-enhancement]

**Description**:
[Detailed description of what needs updating]

**Files to Update**:
- installer/core/commands/template-create.md
- CLAUDE.md
- docs/guides/template-philosophy.md

**Acceptance Criteria**:
- [ ] Phase 5.5 section added to template-create.md
- [ ] Examples updated to show boundary sections
- [ ] Cross-references updated in CLAUDE.md
- [ ] No broken links

**Estimated Effort**: 2-3 hours
```

### 3. Implementation Recommendations
Suggest the optimal approach for each documentation task:
- **Claude Code Direct**: Simple updates, no testing needed
- **`/task-work`**: Multi-file updates requiring validation
- **Manual Review**: Complex decisions requiring human judgment

## Success Criteria

- [ ] All 4 commands thoroughly reviewed
- [ ] Cross-references validated
- [ ] Gap analysis complete with severity ratings
- [ ] Task specifications generated for all documentation updates
- [ ] Implementation recommendations provided
- [ ] Review report saved to `.claude/task-plans/TASK-DOC-F3BA-review-report.md`

## Decision Checkpoint

After completing the review, the following decision options will be presented:

1. **[A]ccept** - Approve findings and create documentation tasks
2. **[R]evise** - Request deeper analysis on specific commands
3. **[I]mplement** - Create implementation tasks for documentation updates (batch create)
4. **[C]ancel** - Discard review

## Notes

- This is a **review task** - use `/task-review TASK-DOC-F3BA` (NOT `/task-work`)
- Focus on accuracy and completeness, not stylistic improvements
- Prioritize user-facing documentation over internal notes
- Consider the impact on users following DOCUMENTATION-IMPLEMENTATION-GUIDE.md
- TASK-063 was completed previously - build upon that work, don't redo it

## Related Tasks

- TASK-063: Update documentation for 6 templates (completed)
- TASK-UX-3A8D: Default agent enhancement task creation
- TASK-STND-773D: Agent boundary sections implementation

## Review Mode

**Recommended**: `architectural` or `code-quality`
- Architectural: Focus on documentation structure and relationships
- Code-quality: Focus on accuracy and completeness

**Depth**: `standard` (1-2 hours)

## Next Steps

```bash
# Execute this review
/task-review TASK-DOC-F3BA --mode=architectural --depth=standard

# After review completion and decision [I]mplement:
# Batch create documentation tasks from recommendations
/task-create [generated task 1]
/task-create [generated task 2]
# ... etc.
```
