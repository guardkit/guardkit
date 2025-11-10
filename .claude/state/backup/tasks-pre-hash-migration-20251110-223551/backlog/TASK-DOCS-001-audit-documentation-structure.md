---
id: TASK-DOCS-001
title: Audit documentation structure and create content organization plan
status: backlog
created: 2025-11-06T00:00:00Z
updated: 2025-11-06T00:00:00Z
priority: high
tags: [documentation, mkdocs, github-pages, planning]
epic: null
feature: null
requirements: []
dependencies: []
complexity_evaluation:
  score: 3
  level: "simple"
  review_mode: "AUTO_PROCEED"
  factor_scores:
    - factor: "file_complexity"
      score: 1
      max_score: 3
      justification: "Analysis task, no file creation"
    - factor: "pattern_familiarity"
      score: 0
      max_score: 2
      justification: "Standard documentation audit"
    - factor: "risk_level"
      score: 0
      max_score: 3
      justification: "Zero risk - analysis only"
    - factor: "dependencies"
      score: 2
      max_score: 2
      justification: "Requires understanding of current doc structure"
---

# Task: Audit Documentation Structure and Create Content Organization Plan

## Context

The Taskwright repository has 28 subdirectories in the docs/ folder, mixing:
- **User-facing documentation** (guides/, workflows/, patterns/)
- **Development artifacts** (implementation/, test_reports/, fixes/)
- **Architecture decisions** (adr/)
- **Internal research** (research/, analysis/, deep-dives/)

An external review (ChatGPT) suggested setting up MkDocs + Material for GitHub Pages, but the suggested navigation was too simplistic for our actual structure.

**Goal**: Create a clear plan for organizing docs into user-facing vs internal content, determining what should be prominent in the documentation site.

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
- [ ] Ready to inform TASK-DOCS-002 (MkDocs configuration)

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

## Notes

### Key Decisions Needed

1. **What to exclude from site build?**
   - Recommendation: Exclude implementation/, test_reports/, fixes/, research/
   - Keep in repo but use MkDocs exclude pattern

2. **How to handle deep-dives/?**
   - User wants deep-dives prominent
   - Include in main navigation or separate "Advanced Topics" section?

3. **Versioned docs?**
   - User said "keep it simple, no versioning for now"
   - Plan for single version initially

4. **Custom domain?**
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
1. Move to TASK-DOCS-002: Create MkDocs configuration
2. Use this plan to design mkdocs.yml nav structure
3. Use gap analysis to create TASK-DOCS-003: Create landing pages
