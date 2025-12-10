# Documentation Tasks Implementation Guide

**Created**: 2025-11-24
**Purpose**: Phased implementation strategy for 11 documentation tasks
**Target**: GitHub Pages documentation site + comprehensive user guides

---

## Executive Summary

**Total Tasks**: 11 documentation tasks
**Estimated Total Effort**: 20-25 hours
**Recommended Approach**: 4 parallel waves using Conductor.build worktrees
**Target Completion**: 3-4 days with parallel development

### Task Status Overview

| Status | Count | Tasks |
|--------|-------|-------|
| **Can Close** | 1 | TASK-063 (already complete) |
| **Claude Code Direct** | 5 | Simple content creation tasks |
| **Use `/task-work`** | 5 | Complex/infrastructure tasks |

---

## Wave-Based Implementation Strategy

### 🌊 Wave 1: Foundation & Planning (Parallel - Day 1)

**Duration**: 2-3 hours
**Strategy**: Can run in parallel using Conductor worktrees
**Dependencies**: None

#### Worktree 1: Audit & Planning
**Task**: [TASK-957C](TASK-957C-audit-documentation-structure.md) - Audit documentation structure
**Method**: **Claude Code Direct** (analysis task)
**Complexity**: 3/10 (Simple)
**Duration**: 2-3 hours
**Output**: Content organization plan, navigation structure

**Why Claude Code**: Pure analysis task, no code changes, produces planning document

**Prompt**:
```
Please analyze the documentation structure in docs/ and installer/core/ folders.
Create a content organization plan that categorizes all 325+ markdown files into:
- User-facing documentation (for GitHub Pages)
- Developer/contributor documentation
- Internal/temporary artifacts (exclude from site)

Include the new features since task creation:
- /agent-enhance, /agent-format, /agent-validate commands
- Task review workflow with 5 modes
- 6 templates (react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, taskwright-python, default)
- MCP integration guides
- Agent boundary sections (ALWAYS/NEVER/ASK)

Output: docs/planning/documentation-organization-plan.md
```

#### Worktree 2: Close Completed Task
**Task**: [TASK-063](TASK-063-update-documentation-4-templates.md) - Update documentation for 6 templates
**Method**: **Close/Archive** (already completed by TASK-074)
**Complexity**: N/A
**Duration**: 5 minutes

**Action**: Move to `tasks/completed/TASK-063/` with completion summary

---

### 🌊 Wave 2: Infrastructure Setup (Sequential - Day 1-2)

**Duration**: 4-5 hours
**Strategy**: Must run sequentially (dependencies)
**Dependencies**: Wave 1 → TASK-957C must complete first

#### Step 1: MkDocs Configuration
**Task**: [TASK-C5AC](TASK-C5AC-create-mkdocs-configuration.md) - Create MkDocs configuration
**Method**: **`/task-work`** (infrastructure setup)
**Complexity**: 4/10 (Medium)
**Duration**: 2-3 hours
**Dependencies**: TASK-957C (needs organization plan)

**Why `/task-work`**:
- Creates `mkdocs.yml` configuration file
- Requires testing (build verification)
- Quality gates: YAML validation, build success
- Architectural review beneficial for navigation structure

**Steps**:
```bash
/task-create "Create MkDocs configuration with Material theme and navigation structure based on TASK-957C audit" priority:high
/task-work TASK-{hash}
```

#### Step 2: GitHub Actions Workflow
**Task**: [TASK-DFFA](TASK-DFFA-setup-github-actions-workflow.md) - Setup GitHub Actions workflow
**Method**: **`/task-work`** (infrastructure + testing required)
**Complexity**: 5/10 (Medium)
**Duration**: 2-3 hours
**Dependencies**: TASK-C5AC (needs working mkdocs.yml)

**Why `/task-work`**:
- Creates `.github/workflows/docs.yml`
- Requires testing (workflow execution)
- Quality gates: Workflow syntax, build success, deployment verification
- Error handling and optimization needed

**Steps**:
```bash
/task-create "Setup GitHub Actions workflow for MkDocs deployment to GitHub Pages" priority:high
/task-work TASK-{hash}
```

---

### 🌊 Wave 3: Content Creation (Parallel - Day 2-3)

**Duration**: 6-8 hours
**Strategy**: Can run in parallel using Conductor worktrees
**Dependencies**: Wave 2 (needs mkdocs.yml structure)

#### Worktree 1: Landing Pages
**Task**: [TASK-B479](TASK-B479-create-landing-pages.md) - Create landing pages
**Method**: **Claude Code Direct** (pure content creation)
**Complexity**: 5/10 (Medium)
**Duration**: 3-4 hours

**Why Claude Code**:
- Creating markdown files (no testing needed)
- Aggregating existing content (linking, not coding)
- Can validate with `mkdocs serve` manually

**Prompt**:
```
Based on the navigation structure in mkdocs.yml, create the following landing pages:
1. docs/index.md - Site homepage
2. Section landing pages for: Getting Started, Core Concepts, Advanced Topics, Templates, Agent System

Requirements:
- Aggregate links to existing comprehensive guides
- Include 6 templates (not 3 or 4): react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, taskwright-python, default
- Add Agent System section covering /agent-enhance, /agent-format, /agent-validate
- Add Task Review section covering 5 review modes
- Link to MCP integration guides in docs/deep-dives/mcp-integration/
- Don't duplicate existing content, just link to it

Reference TASK-B479 for detailed requirements.
```

#### Worktree 2: Agent Enhancement Workflow Documentation
**Task**: [TASK-DOC-B8F2](TASK-DOC-B8F2-clarify-template-agent-enhancement-workflow.md) - Clarify agent enhancement workflow
**Method**: **Claude Code Direct** (pure documentation)
**Complexity**: 3/10 (Simple)
**Duration**: 1-2 hours

**Why Claude Code**: Simple documentation update, no code changes

**Prompt**:
```
Update the following files to clarify the /agent-format vs /agent-enhance workflow:

1. docs/guides/template-philosophy.md - Add "Agent Enhancement Strategy" section
2. docs/guides/agent-enhancement-decision-guide.md - CREATE new file with decision matrix
3. installer/core/commands/agent-format.md - Add "Primary Use Case" section
4. installer/core/commands/agent-enhance.md - Add "Relationship with /agent-format" section
5. installer/core/commands/template-create.md - Add "Phase 5.5: Agent Enhancement" section

Key messages:
- /agent-format for templates (6/10 quality, fast, generic)
- /agent-enhance for project-specific (9/10 quality, AI-powered, domain-specific)
- Two-tier quality system: template (6/10) → project (9/10)
- Progressive enhancement workflow

Reference TASK-DOC-B8F2 for complete specification.
```

#### Worktree 3: Incremental Enhancement Guide
**Task**: [TASK-DOC-1E7B](TASK-DOC-1E7B-incremental-enhancement-workflow-guide.md) - Create incremental enhancement workflow guide
**Method**: **Claude Code Direct** (pure documentation)
**Complexity**: 4/10 (Medium)
**Duration**: 2-3 hours

**Why Claude Code**: Creating comprehensive workflow guide (no code/testing)

**Prompt**:
```
Create docs/workflows/incremental-enhancement-workflow.md covering:

1. Overview of Phase 8 incremental enhancement
2. When to use vs /template-create
3. Workflow comparison (automatic vs manual)
4. Step-by-step guides for:
   - First-time template creation
   - Existing template enhancement
   - Batch enhancement
   - Single agent enhancement
5. Enhancement strategies (ai/static/hybrid)
6. Best practices and troubleshooting

Target: 2000-2500 words, comprehensive but not overwhelming
Reference TASK-DOC-1E7B for detailed requirements.
```

#### Worktree 4: CLAUDE.md Phase 8 Update
**Task**: [TASK-DOC-9C4E](TASK-DOC-9C4E-update-claude-md-phase-8.md) - Update CLAUDE.md with Phase 8
**Method**: **Claude Code Direct** (documentation update)
**Complexity**: 3/10 (Simple)
**Duration**: 1-2 hours

**Why Claude Code**: Updating existing documentation file

**Prompt**:
```
Update CLAUDE.md to add:

1. Essential Commands section - Add /agent-format and /agent-validate
2. Incremental Enhancement Workflow section (new)
3. Agent Enhancement Best Practices (new)
4. Examples and use cases for Phase 8
5. Cross-references to:
   - docs/workflows/incremental-enhancement-workflow.md
   - installer/core/commands/agent-enhance.md
   - installer/core/commands/agent-format.md
   - installer/core/commands/agent-validate.md

Reference TASK-DOC-9C4E for detailed requirements.
Current status: PARTIALLY COMPLETE (has /agent-enhance mention, missing /agent-format and /agent-validate)
```

---

### 🌊 Wave 4: Finalization & Integration (Sequential - Day 3-4)

**Duration**: 4-5 hours
**Strategy**: Sequential (depends on Wave 3 content)
**Dependencies**: Wave 3 (needs all content created)

#### Step 1: Hash-Based ID Documentation
**Task**: [TASK-D01D](TASK-D01D-update-documentation.md) - Update documentation for hash-based IDs
**Method**: **`/task-work`** (multi-file updates + validation)
**Complexity**: 4/10 (Medium)
**Duration**: 2-3 hours
**Dependencies**: All previous waves (updates multiple files)

**Why `/task-work`**:
- Updates 9+ files across codebase
- Needs validation (all links work, examples accurate)
- Quality gates: Link validation, consistency check
- Creates new guide for parallel development workflow

**Steps**:
```bash
/task-create "Update documentation for hash-based IDs including wave-based development guide" priority:medium
/task-work TASK-{hash}
```

#### Step 2: Open Source Documentation
**Task**: [TASK-OPEN-SOURCE-DOCUMENTATION](TASK-OPEN-SOURCE-DOCUMENTATION.md) - Open source documentation
**Method**: **Claude Code Direct** (pure content creation)
**Complexity**: 3/10 (Simple)
**Duration**: 2-3 hours
**Dependencies**: All documentation complete

**Why Claude Code**: Creating beginner-friendly guides (no code/testing)

**Prompt**:
```
Create the following documentation for open source release:

1. docs/guides/template-creation-guide.md - Beginner-friendly user guide
2. docs/architecture/template-create-architecture.md - Architecture for contributors
3. docs/troubleshooting/template-create-troubleshooting.md - Troubleshooting guide
4. Update CLAUDE.md - Add template-create section
5. Update README.md - Add template-create feature

Focus on:
- Beginner-friendly language
- Quick start examples
- Clear architecture diagrams
- Common troubleshooting scenarios
- No references to "legacy" command

Reference TASK-OPEN-SOURCE-DOCUMENTATION for detailed requirements.
```

#### Step 3: GitHub Pages Enablement
**Task**: [TASK-061A](TASK-061A-enable-github-pages-and-update-readme.md) - Enable GitHub Pages
**Method**: **Manual Configuration + Claude Code** (hybrid)
**Complexity**: 2/10 (Simple)
**Duration**: 30 minutes
**Dependencies**: TASK-DFFA (needs GitHub Actions working)

**Why Hybrid**:
- Manual: GitHub repository settings configuration
- Claude Code: README.md updates

**Steps**:
1. Manual: Enable GitHub Pages in repository settings (select "GitHub Actions" source)
2. Manual: Verify site deployment at https://taskwright-dev.github.io/taskwright/
3. Claude Code: Update README.md with documentation links

**Prompt for Claude Code**:
```
Update README.md to add:
1. "Documentation" section near top with link to https://taskwright-dev.github.io/taskwright/
2. Link in "Quick Start" section
3. Optional: Add documentation badge

Keep existing documentation links (no breaking changes).
```

---

## Implementation Decision Matrix

| Task ID | Task Name | Method | Complexity | Duration | Dependencies |
|---------|-----------|--------|------------|----------|--------------|
| **TASK-063** | Update docs for 6 templates | **Close** | N/A | 5min | None |
| **TASK-957C** | Audit documentation structure | **Claude Code** | 3/10 | 2-3h | None |
| **TASK-C5AC** | Create MkDocs config | **`/task-work`** | 4/10 | 2-3h | TASK-957C |
| **TASK-DFFA** | Setup GitHub Actions | **`/task-work`** | 5/10 | 2-3h | TASK-C5AC |
| **TASK-B479** | Create landing pages | **Claude Code** | 5/10 | 3-4h | TASK-C5AC |
| **TASK-DOC-B8F2** | Clarify agent enhancement | **Claude Code** | 3/10 | 1-2h | TASK-C5AC |
| **TASK-DOC-1E7B** | Incremental enhancement guide | **Claude Code** | 4/10 | 2-3h | TASK-C5AC |
| **TASK-DOC-9C4E** | Update CLAUDE.md Phase 8 | **Claude Code** | 3/10 | 1-2h | TASK-C5AC |
| **TASK-D01D** | Hash-based ID docs | **`/task-work`** | 4/10 | 2-3h | Wave 3 |
| **TASK-OPEN-SOURCE** | Open source documentation | **Claude Code** | 3/10 | 2-3h | Wave 3 |
| **TASK-061A** | Enable GitHub Pages | **Hybrid** | 2/10 | 30min | TASK-DFFA |

---

## Conductor.build Parallel Development Strategy

### Worktree Setup

```bash
# Wave 1 - Foundation (Parallel)
conductor create-worktree docs-audit main
conductor create-worktree docs-close-063 main

# Wave 2 - Infrastructure (Sequential)
conductor create-worktree docs-mkdocs main
conductor create-worktree docs-github-actions main

# Wave 3 - Content (Parallel)
conductor create-worktree docs-landing-pages main
conductor create-worktree docs-agent-enhancement main
conductor create-worktree docs-incremental-guide main
conductor create-worktree docs-claude-md main

# Wave 4 - Finalization (Sequential)
conductor create-worktree docs-hash-ids main
conductor create-worktree docs-open-source main
```

### Parallel Execution Pattern

**Wave 1** (Run simultaneously):
```bash
# Terminal 1
cd docs-audit
# Work on TASK-957C

# Terminal 2
cd docs-close-063
# Close TASK-063
```

**Wave 3** (Run simultaneously - 4 terminals):
```bash
# Terminal 1
cd docs-landing-pages
# Work on TASK-B479

# Terminal 2
cd docs-agent-enhancement
# Work on TASK-DOC-B8F2

# Terminal 3
cd docs-incremental-guide
# Work on TASK-DOC-1E7B

# Terminal 4
cd docs-claude-md
# Work on TASK-DOC-9C4E
```

### Merge Strategy

After each wave:
```bash
# Merge completed worktrees back to main
git checkout main
git merge docs-audit
git merge docs-mkdocs
# etc.

# Delete merged worktrees
conductor delete-worktree docs-audit
```

---

## Why `/task-work` vs Claude Code Direct?

### Use `/task-work` When:

1. **Testing Required**:
   - TASK-C5AC: Must verify `mkdocs build` succeeds
   - TASK-DFFA: Must verify GitHub Actions workflow executes
   - TASK-D01D: Must validate all links work

2. **Quality Gates Beneficial**:
   - Architectural review for navigation structure (TASK-C5AC)
   - Build verification for deployment (TASK-DFFA)
   - Consistency check across multiple files (TASK-D01D)

3. **Multi-File Changes**:
   - TASK-D01D updates 9+ files (needs plan + validation)

### Use Claude Code Direct When:

1. **Pure Content Creation**:
   - TASK-957C: Analysis → planning document
   - TASK-B479: Writing markdown landing pages
   - TASK-DOC-1E7B: Creating workflow guide

2. **Simple Documentation Updates**:
   - TASK-DOC-B8F2: Updating 5 documentation files
   - TASK-DOC-9C4E: Updating CLAUDE.md
   - TASK-OPEN-SOURCE: Creating beginner guides

3. **No Testing Needed**:
   - Markdown files can be validated manually with `mkdocs serve`
   - No compilation, no deployment, no complex validation

---

## Success Metrics

### Wave Completion Criteria

**Wave 1 Complete** ✅ when:
- [ ] Documentation organization plan created
- [ ] TASK-063 closed and archived

**Wave 2 Complete** ✅ when:
- [ ] `mkdocs.yml` configuration file created
- [ ] `mkdocs build` succeeds locally
- [ ] GitHub Actions workflow created
- [ ] Workflow builds and deploys successfully

**Wave 3 Complete** ✅ when:
- [ ] All landing pages created (index.md + section pages)
- [ ] Agent enhancement workflow documentation complete (5 files)
- [ ] Incremental enhancement guide created
- [ ] CLAUDE.md updated with Phase 8 content

**Wave 4 Complete** ✅ when:
- [ ] Hash-based ID documentation updated (9+ files)
- [ ] Open source documentation created (3 guides + 2 updates)
- [ ] GitHub Pages enabled and verified
- [ ] README.md updated with documentation links

### Final Validation

- [ ] All 11 tasks complete or closed
- [ ] GitHub Pages site accessible at https://taskwright-dev.github.io/taskwright/
- [ ] All navigation links work (no 404s)
- [ ] Search functionality works
- [ ] All code examples are accurate
- [ ] No broken internal links
- [ ] Responsive on mobile/tablet/desktop

---

## Risk Mitigation

### Risk 1: Wave 3 Merge Conflicts
**Risk**: 4 parallel worktrees editing documentation files simultaneously
**Mitigation**:
- Each worktree works on different files (verified in task descriptions)
- If conflicts occur, use 3-way merge with context awareness

### Risk 2: GitHub Actions Workflow Fails
**Risk**: TASK-DFFA workflow doesn't deploy successfully
**Mitigation**:
- Use `/task-work` for testing and quality gates
- Test locally with `mkdocs build` before committing
- Add troubleshooting to workflow file

### Risk 3: Documentation Becomes Stale
**Risk**: Content created in Wave 3 references features that change
**Mitigation**:
- Wave 1 audit captures current state accurately
- Wave 4 provides final validation pass
- Create versioning strategy for documentation

---

## Estimated Timeline

### Optimistic (Parallel Development)
- **Day 1**: Wave 1 + Wave 2 (5-6 hours)
- **Day 2**: Wave 3 (6-8 hours)
- **Day 3**: Wave 4 (4-5 hours)
- **Total**: 3 days, 15-19 hours

### Conservative (Sequential Development)
- **Day 1**: Wave 1 (2-3 hours)
- **Day 2**: Wave 2 (4-5 hours)
- **Day 3-4**: Wave 3 (6-8 hours)
- **Day 5**: Wave 4 (4-5 hours)
- **Total**: 5 days, 16-21 hours

### Recommended: Hybrid Approach
- **Day 1**: Wave 1 parallel + Wave 2 Step 1 (5-6 hours)
- **Day 2**: Wave 2 Step 2 + Wave 3 parallel (8-10 hours)
- **Day 3**: Wave 4 (4-5 hours)
- **Total**: 3 days, 17-21 hours

---

## Appendix: Task File Locations

All tasks are located in: `tasks/backlog/documentation/`

- [TASK-061A-enable-github-pages-and-update-readme.md](TASK-061A-enable-github-pages-and-update-readme.md)
- [TASK-063-update-documentation-4-templates.md](TASK-063-update-documentation-4-templates.md)
- [TASK-957C-audit-documentation-structure.md](TASK-957C-audit-documentation-structure.md)
- [TASK-B479-create-landing-pages.md](TASK-B479-create-landing-pages.md)
- [TASK-C5AC-create-mkdocs-configuration.md](TASK-C5AC-create-mkdocs-configuration.md)
- [TASK-D01D-update-documentation.md](TASK-D01D-update-documentation.md)
- [TASK-DFFA-setup-github-actions-workflow.md](TASK-DFFA-setup-github-actions-workflow.md)
- [TASK-DOC-1E7B-incremental-enhancement-workflow-guide.md](TASK-DOC-1E7B-incremental-enhancement-workflow-guide.md)
- [TASK-DOC-9C4E-update-claude-md-phase-8.md](TASK-DOC-9C4E-update-claude-md-phase-8.md)
- [TASK-DOC-B8F2-clarify-template-agent-enhancement-workflow.md](TASK-DOC-B8F2-clarify-template-agent-enhancement-workflow.md)
- [TASK-OPEN-SOURCE-DOCUMENTATION.md](TASK-OPEN-SOURCE-DOCUMENTATION.md)

---

**End of Documentation Implementation Guide**
