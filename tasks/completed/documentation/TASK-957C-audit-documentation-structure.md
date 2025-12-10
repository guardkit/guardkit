---
id: TASK-957C
legacy_id: TASK-DOCS-001
title: Audit documentation structure and create content organization plan
status: completed
created: 2025-11-06 00:00:00+00:00
updated: '2025-11-26T06:37:15.524146+00:00'
priority: high
tags:
- documentation
- mkdocs
- github-pages
- planning
epic: null
feature: null
requirements: []
dependencies: []
complexity_evaluation:
  score: 3
  level: simple
  review_mode: AUTO_PROCEED
  factor_scores:
  - factor: file_complexity
    score: 1
    max_score: 3
    justification: Analysis task, no file creation
  - factor: pattern_familiarity
    score: 0
    max_score: 2
    justification: Standard documentation audit
  - factor: risk_level
    score: 0
    max_score: 3
    justification: Zero risk - analysis only
  - factor: dependencies
    score: 2
    max_score: 2
    justification: Requires understanding of current doc structure
completed_at: '2025-11-26T06:37:15.524278+00:00'
completion_metrics:
  total_duration: 1.5 hours
  files_created: 3
  total_lines: 18350
  directories_inventoried: 50
  files_analyzed: 417
  deliverables_met: 100%
---

# Task: Audit Documentation Structure and Create Content Organization Plan

## Context

The Taskwright repository has **59 subdirectories** with **325+ markdown files** in the docs/ folder, plus **81 markdown files** in installer/core/, mixing:
- **User-facing documentation** (guides/, workflows/, patterns/)
- **Development artifacts** (implementation/, test_reports/, fixes/)
- **Architecture decisions** (adr/, adrs/)
- **Internal research** (research/, analysis/, deep-dives/)
- **Command specifications** (installer/core/commands/ - 19 command files)
- **Agent definitions** (installer/core/agents/)
- **Template documentation** (installer/core/templates/ - 6 templates)

An external review (ChatGPT) suggested setting up MkDocs + Material for GitHub Pages, but the suggested navigation was too simplistic for our actual structure.

**Goal**: Create a clear plan for organizing docs into user-facing vs internal content, determining what should be prominent in the documentation site.

**UPDATE (2025-11-23)**: Include new features since task creation:
- `/agent-enhance` command (agent-enhance.md, 12 KB)
- `/agent-format` command (agent-format.md, 8.4 KB)
- `/agent-validate` command (agent-validate.md, 85 KB)
- `/task-review` workflow documentation (task-review.md, 12 KB)
- Agent boundary sections (ALWAYS/NEVER/ASK) - documented in CLAUDE.md
- 6 templates (not 3 or 4) - all with comprehensive READMEs
- MCP integration guides in docs/deep-dives/mcp-integration/

## Objective

Analyze the current documentation structure and create a content organization plan that separates user-facing docs (prominent) from internal development docs (still accessible but less prominent).

## Requirements

### Documentation Inventory
- [ ] List all 28 doc subdirectories with brief descriptions
- [ ] Categorize each as: User-Facing, Developer/Contributor, Internal/Temporary
- [ ] Identify missing key user docs (index.md, quickstart.md, etc.)
- [ ] Map existing comprehensive guides to suggested simple guides

### Content Categorization

**User-Facing (Prominent)**:
- [ ] Identify all guides meant for end users
- [ ] Identify all workflow documentation
- [ ] Identify all pattern documentation
- [ ] Identify MCP setup guides
- [ ] Identify troubleshooting guides

**Developer/Contributor (Accessible)**:
- [ ] Identify ADRs (architecture decision records)
- [ ] Identify contributing guides
- [ ] Identify architecture documentation
- [ ] Identify testing documentation

**Internal/Temporary (Exclude from Site)**:
- [ ] Identify implementation artifacts
- [ ] Identify test reports
- [ ] Identify research/analysis documents
- [ ] Identify fix summaries

### Navigation Structure Design
- [ ] Design main navigation tabs (Getting Started, Core Concepts, Advanced, etc.)
- [ ] Map existing docs to navigation structure
- [ ] Identify landing pages needed (aggregate existing content)
- [ ] Create navigation hierarchy (3 levels max recommended)

### Gap Analysis
- [ ] List missing landing pages
- [ ] List missing quickstart content
- [ ] List missing FAQ
- [ ] List missing troubleshooting content

## Acceptance Criteria

### Documentation Inventory ✅
- [ ] All 28 subdirectories catalogued
- [ ] Each directory categorized (User/Developer/Internal)
- [ ] File count per directory noted
- [ ] Key files in each directory identified

### Content Map ✅
- [ ] User-facing docs clearly identified
- [ ] Developer docs clearly identified
- [ ] Internal docs clearly identified
- [ ] Mapping rationale documented

### Navigation Design ✅
- [ ] Multi-level navigation structure proposed
- [ ] All user-facing docs mapped to navigation
- [ ] No navigation deeper than 3 levels
- [ ] Clear hierarchy (Home → Section → Page)

### Gap Analysis ✅
- [ ] Missing pages identified
- [ ] For each gap, note if: create new OR aggregate existing OR link to existing
- [ ] Priority ranking (must-have vs nice-to-have)

### Deliverable ✅
- [ ] Markdown document: `docs/planning/documentation-organization-plan.md`
- [ ] Contains: inventory, categorization, navigation design, gap analysis
- [ ] Ready to inform TASK-C5AC (MkDocs configuration)

## Implementation Plan

### Phase 1: Directory Inventory
1. List all docs/ subdirectories
2. Count files in each
3. Read 1-2 sample files per directory to understand purpose
4. Categorize each directory

### Phase 2: Content Analysis
1. Identify key user-facing guides
2. Identify workflow documentation
3. Identify pattern documentation
4. Identify MCP setup guides
5. Identify developer documentation

### Phase 3: Navigation Design
1. Sketch main navigation tabs
2. Map docs to tabs
3. Identify missing landing pages
4. Design 3-level hierarchy

### Phase 4: Gap Analysis
1. Compare existing docs to ChatGPT suggestions
2. Note what exists vs what's missing
3. Decide: create new, aggregate existing, or link to existing
4. Prioritize gaps

### Phase 5: Documentation
1. Create planning document
2. Include inventory table
3. Include navigation structure diagram
4. Include gap analysis with recommendations

## Expected Deliverable Structure

```markdown
# Taskwright Documentation Organization Plan

## Current Structure Inventory

| Directory | Files | Category | Purpose |
|-----------|-------|----------|---------|
| guides/ | 6 | User-Facing | Core workflow guides |
| workflows/ | 12 | User-Facing | Detailed workflows |
| patterns/ | X | User-Facing | Architecture patterns |
| ... | ... | ... | ... |

## Categorization

### User-Facing (Prominent in Site)
- guides/ - Core workflow guides
- workflows/ - Detailed workflow documentation
- ...

### Developer/Contributor (Accessible in Site)
- adr/ - Architecture decision records
- architecture/ - System architecture
- ...

### Internal/Temporary (Exclude from Site)
- implementation/ - Task implementation artifacts
- test_reports/ - Test execution reports
- ...

## Proposed Navigation Structure

```
Home (index.md)
├── Getting Started
│   ├── Quickstart (aggregate guides/GETTING-STARTED.md)
│   ├── Installation (link to README section)
│   └── Migration Guide (guides/MIGRATION-GUIDE.md)
├── Core Concepts
│   ├── Taskwright Workflow (guides/taskwright-workflow.md)
│   ├── Complexity Management (workflows/complexity-management-workflow.md)
│   └── Quality Gates (workflows/quality-gates-workflow.md)
...
```

## Gap Analysis

### Missing Landing Pages
- [ ] docs/index.md - Site home (aggregate README + links)
- [ ] docs/getting-started/index.md - Getting started section home
- ...

### Missing Content
- [ ] docs/faq.md - Frequently asked questions
- ...

### Existing Content to Reuse
- ✅ guides/GETTING-STARTED.md - exists, use as quickstart
- ✅ guides/taskwright-workflow.md - exists, core concept
- ...
```

## Success Criteria

### Deliverables
- [ ] Planning document created at `docs/planning/documentation-organization-plan.md`
- [ ] All 28 directories inventoried
- [ ] Navigation structure designed
- [ ] Gap analysis completed

### Quality Metrics
- [ ] Every existing doc file accounted for
- [ ] Clear rationale for each categorization
- [ ] Navigation structure has clear hierarchy
- [ ] Gap analysis prioritized (P0, P1, P2)

### Ready for Next Task
- [ ] Plan informs MkDocs nav configuration
- [ ] Plan identifies which landing pages to create
- [ ] Plan specifies what to include/exclude from site build

## Critical Findings (2025-11-23)

### Path Mismatches in CLAUDE.md

**URGENT**: CLAUDE.md references files at incorrect paths. These must be fixed:

1. **Context7 MCP Setup**
   - Referenced: `docs/guides/context7-mcp-setup.md`
   - Actual: `docs/deep-dives/mcp-integration/context7-setup.md` (17 KB, 728 lines)
   - **Fix**: Create symlink or update reference

2. **Design Patterns MCP Setup**
   - Referenced: `docs/guides/design-patterns-mcp-setup.md`
   - Actual: `docs/deep-dives/mcp-integration/design-patterns-setup.md` (18 KB, 745 lines)
   - **Fix**: Create symlink or update reference

3. **MCP Optimization Guide**
   - Referenced: `docs/guides/mcp-optimization-guide.md`
   - Actual: `docs/deep-dives/mcp-integration/mcp-optimization.md` (34 KB, 1134 lines)
   - **Fix**: Create symlink or update reference

### Missing Workflow Documentation

4. **Incremental Enhancement Workflow**
   - Referenced in CLAUDE.md context
   - Expected: `docs/workflows/incremental-enhancement-workflow.md`
   - Status: Missing (content exists in agent-enhance.md command spec)
   - **Fix**: Create dedicated workflow doc or update references

### Key Metrics

- **Total markdown files**: 406 (325 in docs/, 81 in installer/core/)
- **Total subdirectories**: 59
- **Command specifications**: 19 files
- **Templates documented**: 6
- **Agent definitions**: Multiple in installer/core/agents/
- **Workflow guides**: 14 documented
- **Deep-dive guides**: 3+ in mcp-integration/

## Notes

### Key Decisions Needed

1. **Fix Path Mismatches** (Priority 1)
   - Option A: Create symlinks in docs/guides/ → docs/deep-dives/mcp-integration/
   - Option B: Update CLAUDE.md to reference deep-dives/ paths
   - Option C: Copy files to docs/guides/ for consistency
   - **Recommendation**: Option A (symlinks) - maintains single source of truth

2. **What to exclude from site build?**
   - Recommendation: Exclude implementation/, test_reports/, fixes/, research/
   - Keep in repo but use MkDocs exclude pattern
   - **KEEP**: deep-dives/ (user-facing technical content)

3. **How to handle deep-dives/?**
   - User wants deep-dives prominent
   - Include in main navigation or separate "Advanced Topics" section?
   - **Recommendation**: Main navigation section "Technical Deep Dives"

4. **New Feature Documentation**
   - Agent enhancement commands (3 commands)
   - Task review workflow
   - Agent boundary sections
   - Template validation system
   - **Recommendation**: Dedicated "Agent System" and "Template System" sections

5. **Versioned docs?**
   - User said "keep it simple, no versioning for now"
   - Plan for single version initially

6. **Custom domain?**
   - Decision pending (separate task)
   - Plan should work with both GitHub Pages default and custom domain

### Reusability for RequireKit

This task format should be copied to requirekit repo for their documentation setup. The audit process will be similar but the content will differ.

## Timeline Estimate

**Estimated Duration**: 1-2 hours

### Breakdown:
- Directory inventory: 30 minutes
- Content analysis: 30 minutes
- Navigation design: 20 minutes
- Gap analysis: 20 minutes
- Documentation: 20 minutes

## Related Documents

- `/docs/` - All existing documentation
- ChatGPT conversation about MkDocs setup
- README.md - Current user-facing documentation

## Next Steps After Completion

After this task completes:
1. Move to TASK-C5AC: Create MkDocs configuration
2. Use this plan to design mkdocs.yml nav structure
3. Use gap analysis to create TASK-B479: Create landing pages
