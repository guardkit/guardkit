---
id: TASK-B479
legacy_id: TASK-DOCS-003
title: Create documentation landing pages and aggregate existing content
status: backlog
created: 2025-11-06T00:00:00Z
updated: 2025-11-06T00:00:00Z
priority: high
tags: [documentation, mkdocs, content-creation]
epic: null
feature: null
requirements: []
dependencies: ["TASK-DOCS-001", "TASK-DOCS-002"]
complexity_evaluation:
  score: 5
  level: "medium"
  review_mode: "QUICK_OPTIONAL"
  factor_scores:
    - factor: "file_complexity"
      score: 2
      max_score: 3
      justification: "Multiple markdown files to create"
    - factor: "pattern_familiarity"
      score: 1
      max_score: 2
      justification: "Writing markdown documentation is familiar"
    - factor: "risk_level"
      score: 0
      max_score: 3
      justification: "Zero risk - documentation only"
    - factor: "dependencies"
      score: 2
      max_score: 2
      justification: "Depends on gap analysis from TASK-DOCS-001"
---

# Task: Create Documentation Landing Pages and Aggregate Existing Content

## Context

After TASK-957C (audit) and TASK-C5AC (MkDocs config), we have:
- Gap analysis showing missing landing pages
- MkDocs navigation structure configured
- Understanding of existing comprehensive docs

Now we need to create landing pages that:
- Serve as entry points for each major section
- Aggregate/link to existing detailed documentation
- Provide clear overview without duplicating existing content
- Guide users to the right detailed docs

**Key Principle**: Don't duplicate existing comprehensive guides. Create concise landing pages that link to them.

## Objective

Create missing landing pages (index.md, section landing pages, etc.) that provide clear navigation entry points and aggregate existing documentation.

## Requirements

### Site Homepage (docs/index.md)
- [ ] Welcome message explaining Taskwright
- [ ] Quick overview of core features (from README)
- [ ] Quick navigation to main sections
- [ ] Link to Quickstart guide
- [ ] Link to GitHub repository
- [ ] Badge for version, license, etc.

### Getting Started Section
- [ ] Section landing page (if needed) OR use existing GETTING-STARTED.md
- [ ] Quick navigation to installation, quickstart, migration guide
- [ ] Link to templates overview

### Core Concepts Section
- [ ] Section landing page aggregating links to:
  - Taskwright Workflow
  - Complexity Management
  - Quality Gates
  - Task States
- [ ] Brief 1-sentence description of each

### Advanced Topics Section
- [ ] Section landing page aggregating links to:
  - Design-First Workflow
  - UX Design Integration
  - Iterative Refinement
  - Plan Modification
- [ ] Brief description of when to use each

### Templates Section (UPDATED 2025-11-27)
- [ ] Overview of 5 available templates (not 3, 4, or 6)
- [ ] Include all templates: react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, default
- [ ] Link to template selection guide
- [ ] Link to creating local templates guide
- [ ] Quick reference table of templates with quality scores

### Agent System Section (NEW 2025-11-23)
- [ ] Overview of agent enhancement workflow
- [ ] Link to `/agent-enhance` command (installer/global/commands/agent-enhance.md)
- [ ] Link to `/agent-format` command (installer/global/commands/agent-format.md)
- [ ] Link to `/agent-validate` command (installer/global/commands/agent-validate.md)
- [ ] Explain agent boundary sections (ALWAYS/NEVER/ASK)
- [ ] Link to GitHub agent best practices analysis

### Task Review Workflow Section (NEW 2025-11-23)
- [ ] Overview of `/task-review` command
- [ ] Explain 5 review modes (architectural, code-quality, decision, technical-debt, security)
- [ ] When to use `/task-review` vs `/task-work`
- [ ] Link to task-review-workflow.md

### MCP Integration Section (if separate section)
- [ ] Overview of optional MCP enhancements
- [ ] Core MCPs vs Design MCPs distinction
- [ ] Link to individual MCP setup guides (FIX PATHS - see TASK-957C)
- [ ] When to use each MCP
- [ ] **CRITICAL**: Fix path references to docs/deep-dives/mcp-integration/

### Troubleshooting Section
- [ ] Aggregate troubleshooting content from troubleshooting/ directory
- [ ] Common issues and solutions
- [ ] Link to /debug command
- [ ] Link to GitHub issues

### FAQ Section (if needed)
- [ ] Common questions about Taskwright
- [ ] When to use vs RequireKit
- [ ] Complexity evaluation questions
- [ ] Quality gates questions
- [ ] Link to detailed guides for answers

## Acceptance Criteria

### Site Homepage ✅
- [ ] docs/index.md created
- [ ] Clear value proposition (1-2 paragraphs)
- [ ] Quick navigation to all main sections
- [ ] Links to quickstart and installation
- [ ] Professional appearance with badges/formatting

### Section Landing Pages ✅
- [ ] Each main section has entry point
- [ ] Landing page lists subsection with 1-sentence descriptions
- [ ] Links to detailed guides work
- [ ] No duplication of existing guide content

### Content Strategy ✅
- [ ] Landing pages are concise (<200 words each)
- [ ] Link to existing comprehensive guides
- [ ] Don't duplicate detailed content
- [ ] Provide clear navigation cues

### Linking ✅
- [ ] All internal links work (relative paths correct)
- [ ] Links to existing guides verified
- [ ] Links to README sections work (if any)
- [ ] External links (GitHub, RequireKit) work

### Formatting ✅
- [ ] Consistent markdown style across all pages
- [ ] Proper heading hierarchy (H1 → H2 → H3)
- [ ] Code blocks formatted correctly
- [ ] Lists and tables formatted correctly
- [ ] Admonitions used where appropriate (!!! note, !!! warning)

## Implementation Plan

### Phase 1: Site Homepage
1. Create docs/index.md
2. Extract value proposition from README
3. Add quick navigation to main sections
4. Add badges and links
5. Test links work

### Phase 2: Getting Started
1. Check if existing GETTING-STARTED.md sufficient
2. Create section landing page if needed
3. Ensure clear path: Home → Getting Started → Quickstart
4. Link to installation, migration guide, templates

### Phase 3: Core Concepts Landing
1. Create docs/core-concepts/index.md (or docs/concepts.md)
2. List: Workflow, Complexity, Quality Gates, Task States
3. Add 1-sentence descriptions
4. Link to detailed guides
5. Test navigation flow

### Phase 4: Advanced Topics Landing
1. Create docs/advanced/index.md (or docs/advanced.md)
2. List: Design-First, UX Integration, Iterative Refinement
3. Add brief descriptions and when to use
4. Link to detailed workflow guides
5. Test navigation flow

### Phase 5: Templates Overview
1. Create docs/templates/index.md (or docs/templates.md)
2. Table of available templates (from README)
3. Link to MAUI template selection guide
4. Link to creating local templates guide
5. Quick reference for choosing template

### Phase 6: MCP Integration (if separate)
1. Create docs/mcp/index.md or docs/mcp-integration.md
2. Explain optional nature of MCPs
3. Distinguish Core vs Design MCPs
4. Link to individual setup guides
5. Table showing which MCP for which purpose

### Phase 7: Troubleshooting
1. Audit troubleshooting/ directory content
2. Create docs/troubleshooting/index.md
3. List common issues
4. Link to detailed troubleshooting docs
5. Link to /debug command docs
6. Link to GitHub issues for reporting bugs

### Phase 8: FAQ (Optional)
1. Collect common questions from README, guides
2. Create docs/faq.md
3. Organize by category
4. Link to detailed guides for complex answers
5. Keep answers brief (1-3 sentences + link)

### Phase 9: Review and Test
1. Check all internal links work
2. Check external links work
3. Verify no content duplication
4. Test navigation flow from homepage through sections
5. Check formatting consistency
6. Run `mkdocs build --strict` to catch warnings

## Example Content Structure

### docs/index.md (Site Homepage)

```markdown
# Taskwright

**Lightweight AI-assisted development with built-in quality gates.**

Stop shipping broken code. Get architectural review before implementation and automatic test enforcement after. Simple task workflow, no ceremony.

## Key Features

- **Architectural Review**: SOLID, DRY, YAGNI evaluation before coding
- **Test Enforcement**: Automatic test fixing, ensures 100% pass rate
- **Quality Gates**: Coverage thresholds, compilation checks, code review
- **Simple Workflow**: Create → Work → Complete (3 commands)

## Quick Start

New to Taskwright? Start here:

- [**Quickstart Guide**](guides/GETTING-STARTED.md) - Get up and running in 5 minutes
- [**Taskwright Workflow**](guides/taskwright-workflow.md) - Learn the core workflow
- [**Choose a Template**](templates/index.md) - Select your tech stack

## Documentation Sections

### 📚 [Core Concepts](concepts/index.md)
Learn the fundamentals: workflow, complexity evaluation, quality gates

### 🚀 [Advanced Topics](advanced/index.md)
Design-first workflow, UX integration, iterative refinement

### 🎨 [Templates](templates/index.md)
React, Python, .NET, MAUI templates and customization

### 🔌 [MCP Integration](mcp/index.md) (Optional)
Enhance with Model Context Protocol servers

### 🛠️ [Troubleshooting](troubleshooting/index.md)
Common issues and solutions

## Links

- [GitHub Repository](https://github.com/taskwright-dev/taskwright)
- [Report an Issue](https://github.com/taskwright-dev/taskwright/issues)
- [RequireKit](https://github.com/requirekit/require-kit) - For formal requirements management

---

**Built for pragmatic developers who ship quality code fast.**
```

### docs/core-concepts/index.md (Section Landing)

```markdown
# Core Concepts

Understand the fundamentals of Taskwright's workflow and quality gates.

## 🔄 [Taskwright Workflow](../guides/taskwright-workflow.md)
The complete workflow from task creation to completion, including all phases and quality gates.

## 📊 [Complexity Management](../workflows/complexity-management-workflow.md)
How Taskwright evaluates task complexity and decides when to require human review.

## ✅ [Quality Gates](../workflows/quality-gates-workflow.md)
Automatic enforcement of compilation, testing, coverage, and architectural standards.

## 📋 [Task States & Transitions](../guides/taskwright-workflow.md#task-states)
How tasks move through backlog, in_progress, in_review, blocked, and completed states.

## 🎯 [Development Modes](../guides/taskwright-workflow.md#development-modes)
Standard vs TDD mode for different types of tasks.

---

**Next Steps:**
- Start with [Taskwright Workflow](../guides/taskwright-workflow.md)
- Try creating your first task: [Quickstart Guide](../guides/GETTING-STARTED.md)
```

## Success Criteria

### Deliverables
- [ ] docs/index.md (site homepage)
- [ ] Section landing pages (2-5 pages based on gap analysis)
- [ ] All landing pages link to existing detailed guides
- [ ] No duplication of existing comprehensive content

### Quality Metrics
- [ ] All landing pages <300 words (concise)
- [ ] All internal links work (verified)
- [ ] All external links work (verified)
- [ ] `mkdocs build --strict` succeeds
- [ ] Navigation flows logically from homepage to details

### User Experience
- [ ] Clear path from homepage to any detailed guide (max 3 clicks)
- [ ] Each section has clear overview
- [ ] Users know where to go next
- [ ] No dead ends or circular navigation

### Ready for Next Task
- [ ] All gaps from TASK-957C addressed
- [ ] Site ready for GitHub Actions deployment
- [ ] Content complete enough for public launch

## Notes

### Content Reuse Strategy

**Do:**
- Extract 1-2 paragraph summaries from README
- Link to existing comprehensive guides
- Create navigation tables/lists
- Provide clear next steps

**Don't:**
- Copy/paste entire sections from existing guides
- Duplicate detailed explanations
- Create new comprehensive guides (use existing)

### Existing Comprehensive Guides to Link To

- `guides/taskwright-workflow.md` - Complete workflow (43KB)
- `guides/creating-local-templates.md` - Template customization (34KB)
- `guides/maui-template-selection.md` - MAUI templates (32KB)
- `workflows/complexity-management-workflow.md` - Complexity (20KB)
- `workflows/design-first-workflow.md` - Design-first (29KB)
- `workflows/quality-gates-workflow.md` - Quality gates (20KB)
- And many more...

**Strategy**: These are already comprehensive. Don't rewrite them. Just create entry points.

### Admonitions to Use

MkDocs Material supports admonitions (callout boxes):

```markdown
!!! note
    This is a note callout

!!! warning
    This is a warning callout

!!! tip
    This is a tip callout
```

Use these to highlight:
- Notes: Additional context
- Warnings: Important caveats
- Tips: Helpful suggestions

### Reusability for RequireKit

Same landing page structure applies:
- requirekit/docs/index.md (homepage)
- Section landing pages for RequireKit concepts
- Links to RequireKit's detailed guides
- Similar navigation strategy

The *structure* is reusable, the *content* will be different.

## Timeline Estimate

**Estimated Duration**: 3-4 hours

### Breakdown:
- Site homepage: 45 minutes
- Getting Started section: 20 minutes
- Core Concepts landing: 30 minutes
- Advanced Topics landing: 30 minutes
- Templates overview: 30 minutes
- MCP integration: 20 minutes
- Troubleshooting: 30 minutes
- FAQ (optional): 30 minutes
- Review and testing: 30 minutes

## Related Documents

- `docs/planning/documentation-organization-plan.md` (from TASK-957C)
- `mkdocs.yml` (from TASK-C5AC)
- `README.md` (source for value proposition)
- All existing comprehensive guides in docs/guides/ and docs/workflows/

## Next Steps After Completion

After this task completes:
1. Move to TASK-DFFA: Set up GitHub Actions workflow
2. All content is ready for deployment
3. Site is complete enough for public launch
