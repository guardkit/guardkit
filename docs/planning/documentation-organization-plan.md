# GuardKit Documentation Organization Plan

**Date**: 2025-11-25
**Task**: TASK-957C
**Purpose**: Comprehensive audit and organization plan for MkDocs migration

---

## Executive Summary

The GuardKit repository contains **417 markdown files** across **59 subdirectories**, mixing user-facing documentation with internal development artifacts. This plan provides:

1. Complete inventory of all documentation
2. Clear categorization (User-Facing / Developer / Internal)
3. Navigation structure for MkDocs (max 3 levels)
4. Gap analysis and missing content identification
5. Path mismatch fixes for CLAUDE.md references

**Key Metrics**:
- **Total markdown files**: 417 (333 in docs/, 84 in installer/core/)
- **Top-level directories**: 42 in docs/, 8 in installer/core/
- **Command specifications**: 19 files
- **Agent definitions**: 19 files
- **Templates**: 5 with comprehensive READMEs
- **User-facing guides**: ~50 files
- **Internal artifacts**: ~200+ files

---

## Part 1: Complete Directory Inventory

### docs/ Directory Structure (333 files, 42 directories)

| Directory | Files | Category | Purpose | MkDocs Action |
|-----------|-------|----------|---------|---------------|
| **adr/** | 8 | Developer | Architecture Decision Records (legacy) | Include in "Contributing" |
| **adrs/** | 1 | Developer | Architecture Decision Records (current) | Include in "Contributing" |
| **analysis/** | 16 | Internal | Task analysis and research | Exclude |
| **architecture/** | 4 | Developer | System architecture documentation | Include in "Architecture" |
| **archive/** | 4 | Internal | Archived session notes and summaries | Exclude |
| **checklists/** | 1 | Developer | Development checklists | Include in "Contributing" |
| **checkpoints/** | 2 | Internal | Task checkpoint artifacts | Exclude |
| **code-review/** | 1 | Internal | Code review artifacts | Exclude |
| **completion-reports/** | 1 | Internal | Task completion reports | Exclude |
| **data-contracts/** | 6 | Developer | API/data contract specs | Include in "Reference" |
| **debugging/** | 9 | Internal | Debugging session notes | Exclude |
| **deep-dives/** | 8 | User-Facing | Technical deep dives (MCP integration, etc.) | Include in "Advanced Topics" |
| **design/** | 2 | Internal | Design artifacts | Exclude |
| **epics/** | 2 | Internal | Epic planning documents | Exclude |
| **fixes/** | 3 | Internal | Bug fix summaries | Exclude |
| **guides/** | 24 | User-Facing | Core user guides | Include in "Guides" |
| **implementation/** | 7 | Internal | Implementation artifacts | Exclude |
| **implementation-plans/** | 4 | Internal | Task implementation plans | Exclude |
| **implementation-summaries/** | 1 | Internal | Implementation summaries | Exclude |
| **initiatives/** | 1 | Internal | Initiative planning | Exclude |
| **investigations/** | 2 | Internal | Investigation notes | Exclude |
| **mcp-setup/** | 2 | User-Facing | MCP setup guides (Figma, Zeplin) | Include in "MCP Integration" |
| **migration/** | 1 | User-Facing | Migration guides | Include in "Guides" |
| **patterns/** | 2 | User-Facing | Design pattern documentation | Include in "Architecture" |
| **proposals/** | 11 | Internal | Feature proposals | Exclude |
| **quick-reference/** | 5 | User-Facing | Quick reference cards | Include in "Reference" |
| **reference/** | 1 | User-Facing | Reference documentation | Include in "Reference" |
| **requirements-gathering-api/** | 1 | Internal | RequireKit API design | Exclude |
| **research/** | 83 | Internal | Research documents and PDFs | Exclude |
| **reviews/** | 12 | Internal | Task review artifacts | Exclude |
| **schemas/** | 1 | Developer | Data schemas | Include in "Reference" |
| **shared/** | 3 | Developer | Shared documentation resources | Include in "Contributing" |
| **specifications/** | 2 | Developer | Technical specifications | Include in "Reference" |
| **state/** | 1 | Internal | Task state tracking | Exclude |
| **tasks/** | 1 | Internal | Task tracking | Exclude |
| **templates/** | 2 | User-Facing | Template documentation (see installer/core/templates/) | Include in "Templates" |
| **test_reports/** | 3 | Internal | Test execution reports | Exclude |
| **testing/** | 10 | Developer | Testing documentation | Include in "Contributing" |
| **tests/** | 2 | Internal | Test artifacts | Exclude |
| **troubleshooting/** | 1 | User-Facing | Troubleshooting guide | Include in "Troubleshooting" |
| **validation/** | 3 | Developer | Validation documentation | Include in "Reference" |
| **workflows/** | 14 | User-Facing | Workflow documentation | Include in "Workflows" |

### installer/core/ Directory Structure (84 files, 8 directories)

| Directory | Files | Category | Purpose | MkDocs Action |
|-----------|-------|----------|---------|---------------|
| **agents/** | 19 | User-Facing | Agent definitions (system prompts) | Include in "Agent System" |
| **commands/** | 19 | User-Facing | Slash command specifications | Include in "Commands" |
| **docs/** | 1 | Internal | Internal documentation | Exclude |
| **instructions/** | 4 | Developer | Installation instructions | Include in "Getting Started" |
| **lib/** | 4 | Developer | Shared library documentation | Include in "Contributing" |
| **templates/** | 31 | User-Facing | 5 templates with READMEs + agent files | Include in "Templates" |
| **utils/** | 0 | Developer | Utility documentation | Include in "Contributing" |
| **__pycache__/** | 0 | Internal | Python cache | Exclude |

---

## Part 2: Content Categorization

### User-Facing Documentation (Prominent in Site) - ~100 files

#### Core Guides (24 files in docs/guides/)
- **agent-discovery-guide.md** (6.3 KB) - Agent discovery system
- **claude-code-web-setup.md** (20 KB) - Claude Code web setup
- **creating-local-templates.md** (34 KB) - Template creation guide
- **external-ids-integration.md** (11 KB) - External ID system
- **GETTING-STARTED.md** (9.2 KB) - Getting started guide
- **maui-template-selection.md** (31 KB) - MAUI template selection
- **migration-guide.md** (6.7 KB) - Migration guide
- **quick-reference.md** (11 KB) - Quick reference
- **task-review-implementation-guide.md** (26 KB) - Task review implementation
- **guardkit-workflow.md** (45 KB) - Core workflow documentation
- **template-philosophy.md** - Template design philosophy
- **template-validation-guide.md** - Template validation system
- Plus 12 more guide files

#### Workflows (14 files in docs/workflows/)
- **complexity-management-workflow.md** (20 KB) - Complexity evaluation
- **context7-mcp-integration-workflow.md** (16 KB) - Context7 integration
- **design-first-workflow.md** (29 KB) - Design-first development
- **iterative-refinement-workflow.md** (16 KB) - Iterative refinement
- **markdown-plans-workflow.md** (18 KB) - Markdown planning
- **phase28-checkpoint-workflow.md** (17 KB) - Phase 2.8 checkpoint
- **plan-modification-workflow.md** (22 KB) - Plan modifications
- **quality-gates-workflow.md** (20 KB) - Quality gates
- **task-review-workflow.md** (22 KB) - Task review workflow
- **guardkit-vs-requirekit.md** (12 KB) - Product comparison
- **TEMPLATE-LIFECYCLE-complete-flow.md** (21 KB) - Template lifecycle
- **ux-design-integration-workflow.md** (28 KB) - UX design integration
- Plus 2 more workflow files

#### Advanced Topics (8 files in docs/deep-dives/)
- **deep-dives/mcp-integration/context7-setup.md** (17 KB) - Context7 MCP setup
- **deep-dives/mcp-integration/design-patterns-setup.md** (19 KB) - Design Patterns MCP setup
- **deep-dives/mcp-integration/mcp-optimization.md** (34 KB) - MCP optimization guide
- Plus 5 more deep-dive files

#### MCP Setup (2 files in docs/mcp-setup/)
- **figma-mcp-setup.md** - Figma MCP setup
- **zeplin-mcp-setup.md** - Zeplin MCP setup

#### Commands (19 files in installer/core/commands/)
- **agent-enhance.md** (12 KB) - Agent enhancement command
- **agent-format.md** (8.4 KB) - Agent formatting command
- **agent-validate.md** (85 KB) - Agent validation command
- **figma-to-react.md** - Figma to React conversion
- **task-complete.md** - Task completion
- **task-create.md** - Task creation
- **task-refine.md** - Task refinement
- **task-review.md** (12 KB) - Task review command
- **task-status.md** - Task status
- **task-work.md** - Task implementation
- **template-create.md** - Template creation
- **template-validate.md** - Template validation
- **zeplin-to-maui.md** - Zeplin to MAUI conversion
- Plus 6 more command files

#### Agent System (19 files in installer/core/agents/)
- **agent-content-enhancer.md** - Agent enhancement agent
- **architectural-reviewer.md** - Architecture review agent
- **build-validator.md** - Build validation agent
- **code-reviewer.md** - Code review agent
- **complexity-evaluator.md** - Complexity evaluation agent
- **database-specialist.md** - Database specialist
- **debugging-specialist.md** - Debugging specialist
- **devops-specialist.md** - DevOps specialist
- **dotnet-domain-specialist.md** - .NET domain specialist
- **figma-react-orchestrator.md** - Figma orchestrator
- **git-workflow-manager.md** - Git workflow manager
- **pattern-advisor.md** - Pattern advisor
- **python-api-specialist.md** - Python API specialist
- **qa-tester.md** - QA testing agent
- **react-state-specialist.md** - React specialist
- **security-specialist.md** - Security specialist
- **software-architect.md** - Software architect
- **task-manager.md** - Task manager agent
- **test-orchestrator.md** - Test orchestrator
- **test-verifier.md** - Test verifier
- **zeplin-maui-orchestrator.md** - Zeplin orchestrator

#### Templates (5 templates in installer/core/templates/)
Each template has:
- README.md (comprehensive documentation)
- Multiple agent .md files
- TEMPLATE.md (structure definition)

**Templates**:
1. **react-typescript** (9.0/10 quality) - Bulletproof React patterns
2. **fastapi-python** (9.0/10 quality) - FastAPI best practices
3. **nextjs-fullstack** (8.5/10 quality) - Next.js App Router
4. **react-fastapi-monorepo** (9.2/10 quality) - Full-stack monorepo
5. **default** (8.0/10 quality) - Language-agnostic foundation

**Note**: guardkit-python template was removed (ref: TASK-G6D4) as GuardKit's `.claude/` is git-managed.

#### Reference Documentation
- **quick-reference/** (5 files) - Quick reference cards
- **data-contracts/** (6 files) - API/data contracts
- **schemas/** (1 file) - Data schemas
- **specifications/** (2 files) - Technical specifications

#### Troubleshooting
- **troubleshooting/** (1 file) - Troubleshooting guide

### Developer/Contributor Documentation (~30 files)

#### Architecture
- **architecture/** (4 files) - System architecture
- **patterns/** (2 files) - Design patterns
- **adr/** + **adrs/** (9 files) - Architecture Decision Records

#### Testing & Quality
- **testing/** (10 files) - Testing documentation
- **validation/** (3 files) - Validation processes

#### Contributing
- **checklists/** (1 file) - Development checklists
- **shared/** (3 files) - Shared resources
- **lib/** (4 files) - Library documentation
- **instructions/** (4 files) - Installation/setup instructions

### Internal/Temporary Documentation (~200+ files)

**Exclude from MkDocs** (keep in repo for reference):
- **analysis/** (16 files) - Task analysis
- **archive/** (4 files) - Archived content
- **checkpoints/** (2 files) - Checkpoint artifacts
- **code-review/** (1 file) - Review artifacts
- **completion-reports/** (1 file) - Completion reports
- **debugging/** (9 files) - Debug sessions
- **design/** (2 files) - Design artifacts
- **epics/** (2 files) - Epic planning
- **fixes/** (3 files) - Fix summaries
- **implementation/** (7 files) - Implementation artifacts
- **implementation-plans/** (4 files) - Task plans
- **implementation-summaries/** (1 file) - Implementation summaries
- **initiatives/** (1 file) - Initiative planning
- **investigations/** (2 files) - Investigation notes
- **proposals/** (11 files) - Feature proposals
- **research/** (83 files) - Research documents
- **reviews/** (12 files) - Review artifacts
- **state/** (1+ files) - Task state tracking
- **tasks/** (1 file) - Task tracking
- **test_reports/** (3 files) - Test reports
- **tests/** (2 files) - Test artifacts

---

## Part 3: Proposed Navigation Structure

### Home
- **index.md** (to create) - Landing page with overview, key features, quick links

### Getting Started
- **Installation** (aggregate from README.md + installer/core/instructions/)
- **Quickstart** (aggregate from guides/GETTING-STARTED.md)
- **Your First Task** (new walkthrough or link to guardkit-workflow.md)
- **Migration Guide** (guides/migration-guide.md)
- **Claude Code Web Setup** (guides/claude-code-web-setup.md)

### Core Concepts
- **GuardKit Workflow** (guides/guardkit-workflow.md)
- **Task Lifecycle** (extract from workflow)
  - Create → Work → Complete
  - Task States & Transitions
- **Quality Gates** (workflows/quality-gates-workflow.md)
  - Phase 2.5: Architectural Review
  - Phase 4.5: Test Enforcement
  - Phase 5.5: Plan Audit
- **Complexity Management** (workflows/complexity-management-workflow.md)
- **Design-First Workflow** (workflows/design-first-workflow.md)
- **Iterative Refinement** (workflows/iterative-refinement-workflow.md)

### Commands Reference
Organized by category, linking to installer/core/commands/*.md:

#### Core Workflow
- **/task-create** - Create tasks
- **/task-work** - Implement tasks
- **/task-complete** - Complete tasks
- **/task-status** - Check status
- **/task-refine** - Iterative refinement
- **/task-review** - Analysis/review workflow

#### Template System
- **/template-create** - Create templates
- **/template-validate** - Validate templates

#### Agent System
- **/agent-enhance** - Enhance agents
- **/agent-format** - Format agents
- **/agent-validate** - Validate agents

#### UX Design Integration
- **/figma-to-react** - Figma to React
- **/zeplin-to-maui** - Zeplin to MAUI

#### Utilities
- **/debug** - Troubleshooting

### Workflows
Comprehensive workflows from docs/workflows/:
- **Task Review Workflow** (task-review-workflow.md)
- **Complexity Management** (complexity-management-workflow.md)
- **Design-First Workflow** (design-first-workflow.md)
- **Quality Gates** (quality-gates-workflow.md)
- **Markdown Plans** (markdown-plans-workflow.md)
- **Plan Modification** (plan-modification-workflow.md)
- **Phase 2.8 Checkpoint** (phase28-checkpoint-workflow.md)
- **Iterative Refinement** (iterative-refinement-workflow.md)
- **UX Design Integration** (ux-design-integration-workflow.md)
- **Template Lifecycle** (TEMPLATE-LIFECYCLE-complete-flow.md)
- **Context7 MCP Integration** (context7-mcp-integration-workflow.md)
- **GuardKit vs RequireKit** (guardkit-vs-requirekit.md)

### Agent System
Documentation for all 19+ agents:

#### Overview
- **Agent Discovery** (guides/agent-discovery-guide.md)
- **Agent Architecture** (extract from agents/)
- **Agent Boundary Sections** (extract from CLAUDE.md)

#### Core Agents (Sonnet)
- **architectural-reviewer** - SOLID/DRY/YAGNI review
- **task-manager** - Workflow orchestration
- **test-orchestrator** + **test-verifier** - Test execution
- **code-reviewer** - Code quality
- **software-architect** - System design
- **pattern-advisor** - Design patterns

#### Stack-Specific Agents (Haiku)
- **python-api-specialist** - FastAPI/async
- **react-state-specialist** - React hooks
- **dotnet-domain-specialist** - DDD patterns

#### Specialist Agents
- **devops-specialist** - Infrastructure
- **security-specialist** - Security
- **database-specialist** - Data architecture
- **debugging-specialist** - Debugging
- **git-workflow-manager** - Git workflows
- **qa-tester** - QA testing

#### Orchestrators
- **figma-react-orchestrator** - Figma integration
- **zeplin-maui-orchestrator** - Zeplin integration
- **build-validator** - Build validation
- **complexity-evaluator** - Complexity evaluation
- **agent-content-enhancer** - Agent enhancement

### Template System

#### Overview
- **Template Philosophy** (guides/template-philosophy.md)
- **Creating Templates** (guides/creating-local-templates.md)
- **Template Validation** (guides/template-validation-guide.md)
- **Template Lifecycle** (workflows/TEMPLATE-LIFECYCLE-complete-flow.md)

#### Available Templates
Each with link to installer/core/templates/{name}/README.md:
- **react-typescript** (9.0/10) - Bulletproof React
- **fastapi-python** (9.0/10) - FastAPI Best Practices
- **nextjs-fullstack** (8.5/10) - Next.js App Router
- **react-fastapi-monorepo** (9.2/10) - Full-stack monorepo
- **default** (8.0/10) - Language-agnostic

**Note**: guardkit-python removed (TASK-G6D4) - GuardKit uses git-managed `.claude/`

#### Template Commands
- **/template-create** - Create from codebase
- **/template-validate** - 3-level validation

### Advanced Topics

#### MCP Integration
- **Context7 Setup** (deep-dives/mcp-integration/context7-setup.md)
- **Design Patterns Setup** (deep-dives/mcp-integration/design-patterns-setup.md)
- **MCP Optimization** (deep-dives/mcp-integration/mcp-optimization.md)
- **Context7 Workflow** (workflows/context7-mcp-integration-workflow.md)

#### UX Design Integration
- **Figma MCP Setup** (mcp-setup/figma-mcp-setup.md)
- **Zeplin MCP Setup** (mcp-setup/zeplin-mcp-setup.md)
- **UX Design Workflow** (workflows/ux-design-integration-workflow.md)

#### Other Deep Dives
- Additional deep-dive topics from docs/deep-dives/ (5 more files)

### Reference

#### API & Data Contracts
- **Data Contracts** (data-contracts/ - 6 files)
- **Schemas** (schemas/ - 1 file)
- **Specifications** (specifications/ - 2 files)

#### Quick Reference
- **Command Quick Reference** (quick-reference/)
- **Workflow Quick Reference** (quick-reference/)
- **Agent Quick Reference** (quick-reference/)

### Troubleshooting
- **Common Issues** (troubleshooting/)
- **Debug Command** (commands/debug.md)
- **Support Resources** (new section)

### Contributing

#### Getting Started
- **Development Setup** (from README.md)
- **Installation Scripts** (installer/core/instructions/)

#### Architecture
- **System Architecture** (architecture/ - 4 files)
- **Design Patterns** (patterns/ - 2 files)
- **ADRs** (adr/ + adrs/ - 9 files)

#### Development Practices
- **Testing** (testing/ - 10 files)
- **Validation** (validation/ - 3 files)
- **Checklists** (checklists/ - 1 file)
- **Shared Resources** (shared/ - 3 files)

#### Code Reference
- **Library Documentation** (lib/ - 4 files)

---

## Part 4: Gap Analysis

### Missing Landing Pages (Priority 0 - Must Create)

1. **docs/index.md** - Site home page
   - Aggregate: README.md overview + key features + architecture diagram
   - Add: Quick navigation to Getting Started, Core Concepts, Commands
   - Length: ~300-400 lines

2. **docs/getting-started/index.md** - Getting Started section home
   - Aggregate: Installation steps + first task walkthrough
   - Link to: guides/GETTING-STARTED.md, migration-guide.md
   - Length: ~150-200 lines

3. **docs/core-concepts/index.md** - Core Concepts section home
   - Overview: GuardKit philosophy, quality gates, workflows
   - Link to: All workflow documentation
   - Length: ~100-150 lines

4. **docs/commands/index.md** - Commands reference home
   - Category overview with command list
   - Link to: All 19 command files
   - Length: ~100 lines

5. **docs/agents/index.md** - Agent System section home
   - Agent architecture overview
   - Agent discovery explanation
   - Link to: All 19+ agent files
   - Length: ~150-200 lines

6. **docs/templates/index.md** - Template System section home
   - Template philosophy overview
   - Quality tier explanation (9+/10, 8-9/10)
   - Link to: All 5 templates + guides
   - Length: ~150 lines
   - **Note**: guardkit-python removed (TASK-G6D4)

7. **docs/advanced/index.md** - Advanced Topics section home
   - MCP integration overview
   - UX design integration overview
   - Link to: deep-dives/, mcp-setup/
   - Length: ~100 lines

8. **docs/reference/index.md** - Reference section home
   - API/data contract overview
   - Schema overview
   - Link to: All reference documentation
   - Length: ~100 lines

### Missing Quickstart Content (Priority 1 - High Value)

9. **docs/getting-started/first-task.md** - Your First Task walkthrough
   - Step-by-step: Install → Initialize → Create task → Work → Complete
   - Example: Simple "Add README badge" task
   - Length: ~200-250 lines
   - Alternative: Could be section in getting-started/index.md

10. **docs/faq.md** - Frequently Asked Questions
    - Common questions from CLAUDE.md troubleshooting section
    - When to use GuardKit vs RequireKit
    - MCP setup questions
    - Template selection questions
    - Length: ~150-200 lines

### Missing Troubleshooting Content (Priority 1 - High Value)

11. **docs/troubleshooting/index.md** - Troubleshooting home
    - Aggregate: Existing troubleshooting/ content + CLAUDE.md troubleshooting
    - Common issues: Command not found, permission denied, symlink issues
    - Link to: /debug command
    - Length: ~150-200 lines

### Missing Integration Guides (Priority 2 - Nice to Have)

12. **docs/integrations/conductor.md** - Conductor Integration
    - Extract from CLAUDE.md "Conductor Integration" section
    - Setup, state persistence, parallel development
    - Length: ~100-150 lines

13. **docs/integrations/requirekit.md** - RequireKit Integration
    - Extract from workflows/guardkit-vs-requirekit.md
    - When to use each, how they complement
    - Length: ~100 lines

### Existing Content to Reuse (No Action Needed)

✅ **guides/GETTING-STARTED.md** - Excellent quickstart (9.2 KB)
✅ **guides/guardkit-workflow.md** - Comprehensive workflow (45 KB)
✅ **workflows/complexity-management-workflow.md** - Complete complexity guide (20 KB)
✅ **workflows/quality-gates-workflow.md** - Quality gates explained (20 KB)
✅ **workflows/task-review-workflow.md** - Task review process (22 KB)
✅ **deep-dives/mcp-integration/*.md** - MCP setup guides (70 KB total)
✅ **installer/core/commands/*.md** - All 19 command specs (comprehensive)
✅ **installer/core/agents/*.md** - All 19 agent definitions
✅ **installer/core/templates/*/README.md** - All 6 template docs

### Path Mismatches to Fix (Priority 0 - Critical)

**Issue**: CLAUDE.md references files at incorrect paths

14. **Context7 MCP Setup Path Mismatch**
    - Referenced: `docs/guides/context7-mcp-setup.md`
    - Actual: `docs/deep-dives/mcp-integration/context7-setup.md`
    - **Solution**: Create symlink OR update CLAUDE.md reference
    - **Recommendation**: Update CLAUDE.md to use deep-dives path (maintains single source of truth)

15. **Design Patterns MCP Setup Path Mismatch**
    - Referenced: `docs/guides/design-patterns-mcp-setup.md`
    - Actual: `docs/deep-dives/mcp-integration/design-patterns-setup.md`
    - **Solution**: Create symlink OR update CLAUDE.md reference
    - **Recommendation**: Update CLAUDE.md to use deep-dives path

16. **MCP Optimization Guide Path Mismatch**
    - Referenced: `docs/guides/mcp-optimization-guide.md`
    - Actual: `docs/deep-dives/mcp-integration/mcp-optimization.md`
    - **Solution**: Create symlink OR update CLAUDE.md reference
    - **Recommendation**: Update CLAUDE.md to use deep-dives path

### Missing Workflow Documentation (Priority 2 - Low)

17. **Incremental Enhancement Workflow**
    - Referenced in CLAUDE.md context
    - Expected: `docs/workflows/incremental-enhancement-workflow.md`
    - Status: Content exists in agent-enhance.md command spec
    - **Solution**: Create dedicated workflow doc OR clarify that command spec contains workflow
    - **Recommendation**: Create workflow doc for consistency (extract from agent-enhance.md)

---

## Part 5: Content Organization Strategy

### Include in MkDocs Build (~150 files)

**User-Facing** (prominent):
- docs/guides/ (24 files)
- docs/workflows/ (14 files)
- docs/deep-dives/ (8 files)
- docs/mcp-setup/ (2 files)
- docs/quick-reference/ (5 files)
- docs/troubleshooting/ (1 file)
- installer/core/commands/ (19 files)
- installer/core/agents/ (19 files)
- installer/core/templates/ (31 files - 6 READMEs + agents)
- **Total**: ~123 existing files

**Developer** (accessible):
- docs/architecture/ (4 files)
- docs/patterns/ (2 files)
- docs/adr/ + docs/adrs/ (9 files)
- docs/testing/ (10 files)
- docs/validation/ (3 files)
- docs/data-contracts/ (6 files)
- docs/schemas/ (1 file)
- docs/specifications/ (2 files)
- docs/checklists/ (1 file)
- docs/shared/ (3 files)
- installer/core/lib/ (4 files)
- installer/core/instructions/ (4 files)
- **Total**: ~49 files

**Total in MkDocs**: ~172 existing files + ~13 new landing pages = **~185 files**

### Exclude from MkDocs Build (~230 files)

**Internal/Temporary** (exclude pattern in mkdocs.yml):
```yaml
exclude_docs: |
  analysis/
  archive/
  checkpoints/
  code-review/
  completion-reports/
  debugging/
  design/
  epics/
  fixes/
  implementation/
  implementation-plans/
  implementation-summaries/
  initiatives/
  investigations/
  proposals/
  research/
  reviews/
  state/
  tasks/
  test_reports/
  tests/
  installer/core/docs/
  installer/core/__pycache__/
```

### MkDocs Configuration Preview

```yaml
site_name: GuardKit Documentation
site_description: Lightweight AI-Assisted Development with Quality Gates
site_url: https://guardkit.github.io  # or custom domain
repo_url: https://github.com/guardkit/guardkit
repo_name: guardkit/guardkit

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

plugins:
  - search
  - awesome-pages

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.highlight
  - pymdownx.inlinehilite
  - pymdownx.tabbed
  - pymdownx.tasklist
  - toc:
      permalink: true

exclude_docs: |
  analysis/
  archive/
  checkpoints/
  code-review/
  completion-reports/
  debugging/
  design/
  epics/
  fixes/
  implementation/
  implementation-plans/
  implementation-summaries/
  initiatives/
  investigations/
  proposals/
  research/
  reviews/
  state/
  tasks/
  test_reports/
  tests/
  installer/core/docs/
  installer/core/__pycache__/

nav:
  - Home: index.md
  - Getting Started:
      - getting-started/index.md
      - Installation: getting-started/installation.md
      - Quickstart: getting-started/quickstart.md
      - Your First Task: getting-started/first-task.md
      - Migration Guide: guides/migration-guide.md
      - Claude Code Web Setup: guides/claude-code-web-setup.md
  - Core Concepts:
      - core-concepts/index.md
      - GuardKit Workflow: guides/guardkit-workflow.md
      - Quality Gates: workflows/quality-gates-workflow.md
      - Complexity Management: workflows/complexity-management-workflow.md
      - Design-First Workflow: workflows/design-first-workflow.md
      - Iterative Refinement: workflows/iterative-refinement-workflow.md
  - Commands:
      - commands/index.md
      - Core Workflow:
          - task-create: ../installer/core/commands/task-create.md
          - task-work: ../installer/core/commands/task-work.md
          - task-complete: ../installer/core/commands/task-complete.md
          - task-status: ../installer/core/commands/task-status.md
          - task-refine: ../installer/core/commands/task-refine.md
          - task-review: ../installer/core/commands/task-review.md
      - Template System:
          - template-create: ../installer/core/commands/template-create.md
          - template-validate: ../installer/core/commands/template-validate.md
      - Agent System:
          - agent-enhance: ../installer/core/commands/agent-enhance.md
          - agent-format: ../installer/core/commands/agent-format.md
          - agent-validate: ../installer/core/commands/agent-validate.md
      - UX Design:
          - figma-to-react: ../installer/core/commands/figma-to-react.md
          - zeplin-to-maui: ../installer/core/commands/zeplin-to-maui.md
      - Utilities:
          - debug: ../installer/core/commands/debug.md
  - Workflows:
      - Task Review: workflows/task-review-workflow.md
      - Complexity Management: workflows/complexity-management-workflow.md
      - Design-First: workflows/design-first-workflow.md
      - Quality Gates: workflows/quality-gates-workflow.md
      - Markdown Plans: workflows/markdown-plans-workflow.md
      - Plan Modification: workflows/plan-modification-workflow.md
      - Phase 2.8 Checkpoint: workflows/phase28-checkpoint-workflow.md
      - Iterative Refinement: workflows/iterative-refinement-workflow.md
      - UX Design Integration: workflows/ux-design-integration-workflow.md
      - Template Lifecycle: workflows/TEMPLATE-LIFECYCLE-complete-flow.md
      - Context7 MCP: workflows/context7-mcp-integration-workflow.md
      - GuardKit vs RequireKit: workflows/guardkit-vs-requirekit.md
  - Agent System:
      - agents/index.md
      - Overview:
          - Agent Discovery: guides/agent-discovery-guide.md
          - Agent Architecture: agents/architecture.md
          - Boundary Sections: agents/boundary-sections.md
      - Core Agents:
          - architectural-reviewer: ../installer/core/agents/architectural-reviewer.md
          - task-manager: ../installer/core/agents/task-manager.md
          - test-orchestrator: ../installer/core/agents/test-orchestrator.md
          - test-verifier: ../installer/core/agents/test-verifier.md
          - code-reviewer: ../installer/core/agents/code-reviewer.md
          - software-architect: ../installer/core/agents/software-architect.md
          - pattern-advisor: ../installer/core/agents/pattern-advisor.md
      - Stack-Specific:
          - python-api-specialist: ../installer/core/agents/python-api-specialist.md
          - react-state-specialist: ../installer/core/agents/react-state-specialist.md
          - dotnet-domain-specialist: ../installer/core/agents/dotnet-domain-specialist.md
      - Specialists:
          - devops-specialist: ../installer/core/agents/devops-specialist.md
          - security-specialist: ../installer/core/agents/security-specialist.md
          - database-specialist: ../installer/core/agents/database-specialist.md
          - debugging-specialist: ../installer/core/agents/debugging-specialist.md
          - git-workflow-manager: ../installer/core/agents/git-workflow-manager.md
          - qa-tester: ../installer/core/agents/qa-tester.md
      - Orchestrators:
          - figma-react-orchestrator: ../installer/core/agents/figma-react-orchestrator.md
          - zeplin-maui-orchestrator: ../installer/core/agents/zeplin-maui-orchestrator.md
          - build-validator: ../installer/core/agents/build-validator.md
          - complexity-evaluator: ../installer/core/agents/complexity-evaluator.md
          - agent-content-enhancer: ../installer/core/agents/agent-content-enhancer.md
  - Templates:
      - templates/index.md
      - Overview:
          - Template Philosophy: guides/template-philosophy.md
          - Creating Templates: guides/creating-local-templates.md
          - Template Validation: guides/template-validation-guide.md
          - Template Lifecycle: workflows/TEMPLATE-LIFECYCLE-complete-flow.md
      - Available Templates:
          - react-typescript: ../installer/core/templates/react-typescript/README.md
          - fastapi-python: ../installer/core/templates/fastapi-python/README.md
          - nextjs-fullstack: ../installer/core/templates/nextjs-fullstack/README.md
          - react-fastapi-monorepo: ../installer/core/templates/react-fastapi-monorepo/README.md
          - default: ../installer/core/templates/default/README.md
  - Advanced Topics:
      - advanced/index.md
      - MCP Integration:
          - Context7 Setup: deep-dives/mcp-integration/context7-setup.md
          - Design Patterns Setup: deep-dives/mcp-integration/design-patterns-setup.md
          - MCP Optimization: deep-dives/mcp-integration/mcp-optimization.md
          - Context7 Workflow: workflows/context7-mcp-integration-workflow.md
      - UX Design Integration:
          - Figma MCP Setup: mcp-setup/figma-mcp-setup.md
          - Zeplin MCP Setup: mcp-setup/zeplin-mcp-setup.md
          - UX Design Workflow: workflows/ux-design-integration-workflow.md
  - Reference:
      - reference/index.md
      - API & Data Contracts: data-contracts/
      - Schemas: schemas/
      - Specifications: specifications/
      - Quick Reference: quick-reference/
  - Troubleshooting:
      - troubleshooting/index.md
      - Common Issues: troubleshooting/common-issues.md
      - Debug Command: ../installer/core/commands/debug.md
  - Contributing:
      - Development Setup: contributing/setup.md
      - Architecture:
          - System Architecture: architecture/
          - Design Patterns: patterns/
          - ADRs: adr/
      - Development Practices:
          - Testing: testing/
          - Validation: validation/
          - Checklists: checklists/
          - Shared Resources: shared/
      - Code Reference:
          - Library Documentation: ../installer/core/lib/
```

---

## Part 6: Implementation Roadmap

### Phase 1: Critical Fixes (IMMEDIATE)
**Task**: TASK-XXX (create follow-up task)

1. Fix path mismatches in CLAUDE.md (3 files)
2. Update references to use deep-dives/mcp-integration/ paths
3. Verify all CLAUDE.md links resolve correctly

**Duration**: 15 minutes
**Impact**: High (broken links in primary user-facing doc)

### Phase 2: MkDocs Configuration (TASK-C5AC)
**Task**: TASK-C5AC

1. Create mkdocs.yml with navigation structure above
2. Configure Material theme
3. Set up exclude patterns
4. Configure plugins (search, awesome-pages)
5. Test local build

**Duration**: 1-2 hours
**Impact**: High (enables documentation site)

### Phase 3: Landing Pages (TASK-B479)
**Task**: TASK-B479 (create follow-up task)

Create 13 landing pages in priority order:

**P0 (Must Have)**:
1. docs/index.md
2. docs/getting-started/index.md
3. docs/core-concepts/index.md
4. docs/commands/index.md
5. docs/agents/index.md
6. docs/templates/index.md
7. docs/advanced/index.md
8. docs/reference/index.md

**P1 (High Value)**:
9. docs/getting-started/first-task.md
10. docs/faq.md
11. docs/troubleshooting/index.md

**P2 (Nice to Have)**:
12. docs/integrations/conductor.md
13. docs/integrations/requirekit.md

**Duration**: 4-6 hours (all 13 pages)
**Impact**: High (user navigation and discovery)

### Phase 4: GitHub Pages Deployment (TASK-XXX)
**Task**: Create follow-up task

1. Create .github/workflows/deploy-docs.yml
2. Configure GitHub Pages source
3. Test deployment
4. Update README.md with documentation link

**Duration**: 30 minutes
**Impact**: High (public accessibility)

### Phase 5: Polish & Refinement (TASK-XXX)
**Task**: Create follow-up task

1. Add search functionality
2. Add version selector (if needed in future)
3. Custom CSS/branding
4. Analytics (optional)

**Duration**: 1-2 hours
**Impact**: Medium (user experience)

---

## Part 7: Success Metrics

### Completeness Metrics
- ✅ All 42 docs/ directories inventoried
- ✅ All 8 installer/core/ directories inventoried
- ✅ 172 existing user-facing files identified
- ✅ 49 developer files identified
- ✅ ~230 internal files marked for exclusion
- ✅ Navigation structure designed (3 levels max)
- ✅ 13 missing landing pages identified
- ✅ 4 path mismatches identified

### Quality Metrics
- ✅ Clear categorization rationale for all directories
- ✅ Navigation hierarchy follows best practices
- ✅ Gap analysis prioritized (P0, P1, P2)
- ✅ All critical path mismatches documented

### Actionability Metrics
- ✅ MkDocs configuration ready to implement
- ✅ Landing page content specs defined
- ✅ Exclude patterns specified
- ✅ Implementation roadmap with time estimates

---

## Part 8: Key Decisions & Recommendations

### Decision 1: Fix Path Mismatches
**Recommendation**: Update CLAUDE.md references (Option B)

**Rationale**:
- Maintains single source of truth (deep-dives/ location)
- No symlink maintenance overhead
- Clearer semantic organization (MCP docs belong in deep-dives/)
- Simpler for MkDocs build

**Action**: Update CLAUDE.md with corrected paths

### Decision 2: Exclude Internal Directories
**Recommendation**: Use MkDocs exclude patterns (keep in repo)

**Rationale**:
- Preserves history and context for contributors
- Git-friendly (no .gitignore changes)
- Clean public documentation site
- Easy to include specific files if needed later

**Action**: Configure exclude_docs in mkdocs.yml

### Decision 3: Deep Dives Location
**Recommendation**: Prominent navigation section

**Rationale**:
- User explicitly wants deep-dives prominent
- Contains high-value technical content (MCP integration, etc.)
- Differentiates from surface-level guides
- Appeals to advanced users

**Action**: Create "Advanced Topics" top-level nav section

### Decision 4: Template Documentation
**Recommendation**: Dedicated "Templates" section

**Rationale**:
- 5 templates with comprehensive docs (~26 files after guardkit-python removal)
- Template system is core differentiator
- Multiple related guides (philosophy, creation, validation)
- Justifies dedicated navigation section

**Action**: Create "Templates" top-level nav section

**Note**: guardkit-python removed (TASK-G6D4) - GuardKit's `.claude/` is git-managed

### Decision 5: Agent Documentation
**Recommendation**: Dedicated "Agent System" section

**Rationale**:
- 19+ agent definitions
- Agent discovery system
- Agent enhancement workflow
- Core to GuardKit value proposition

**Action**: Create "Agent System" top-level nav section

### Decision 6: Command Organization
**Recommendation**: Categorical grouping in navigation

**Rationale**:
- 19 commands - too many for flat list
- Clear categories: Core Workflow, Template, Agent, UX Design, Utilities
- Easier discovery for new users
- Aligns with mental models

**Action**: Group commands by category in nav

---

## Part 9: Next Steps

### Immediate Actions (This Task)
1. ✅ Create this planning document
2. ✅ Commit to docs/planning/documentation-organization-plan.md
3. ✅ Review with user for feedback

### Follow-up Tasks (Create)

#### TASK-XXX: Fix CLAUDE.md Path Mismatches
- Priority: P0 (Critical)
- Duration: 15 minutes
- Update 3 MCP integration references to correct paths

#### TASK-C5AC: Create MkDocs Configuration
- Priority: P0 (Critical)
- Duration: 1-2 hours
- Create mkdocs.yml with navigation structure
- Configure theme and plugins
- Test local build

#### TASK-B479: Create Landing Pages
- Priority: P1 (High)
- Duration: 4-6 hours
- Create 13 landing pages (8 P0, 3 P1, 2 P2)
- Aggregate existing content
- Write new introductory content

#### TASK-XXX: GitHub Pages Deployment
- Priority: P1 (High)
- Duration: 30 minutes
- Create deployment workflow
- Configure GitHub Pages
- Update README

#### TASK-XXX: Documentation Polish
- Priority: P2 (Medium)
- Duration: 1-2 hours
- Custom CSS/branding
- Search optimization
- Analytics (optional)

---

## Part 10: Appendix

### Appendix A: Directory Purpose Reference

**User-Facing Directories**:
- `guides/` - Core user guides (workflow, getting started, etc.)
- `workflows/` - Detailed workflow documentation
- `deep-dives/` - Technical deep dives (MCP, architecture, etc.)
- `mcp-setup/` - MCP server setup guides
- `quick-reference/` - Quick reference cards
- `troubleshooting/` - Troubleshooting guide

**Developer Directories**:
- `architecture/` - System architecture
- `patterns/` - Design patterns
- `adr/` + `adrs/` - Architecture Decision Records
- `testing/` - Testing documentation
- `validation/` - Validation processes
- `data-contracts/` - API/data contracts
- `schemas/` - Data schemas
- `specifications/` - Technical specifications

**Internal Directories** (exclude from site):
- `analysis/` - Task analysis artifacts
- `archive/` - Archived content
- `checkpoints/` - Task checkpoint artifacts
- `code-review/` - Code review artifacts
- `completion-reports/` - Task completion reports
- `debugging/` - Debug session notes
- `design/` - Design artifacts
- `epics/` - Epic planning
- `fixes/` - Fix summaries
- `implementation/` - Implementation artifacts
- `implementation-plans/` - Task implementation plans
- `implementation-summaries/` - Implementation summaries
- `initiatives/` - Initiative planning
- `investigations/` - Investigation notes
- `proposals/` - Feature proposals
- `research/` - Research documents (83 files!)
- `reviews/` - Review artifacts
- `state/` - Task state tracking
- `tasks/` - Task tracking
- `test_reports/` - Test execution reports
- `tests/` - Test artifacts

### Appendix B: File Count Summary

**Total**: 417 markdown files

**By Location**:
- docs/: 333 files
- installer/core/: 84 files

**By Category**:
- User-Facing: ~100 files (24%)
- Developer: ~30 files (7%)
- Internal: ~230 files (55%)
- Templates: ~57 files (14%)

**Largest Directories**:
1. research/ - 83 files (exclude)
2. guides/ - 24 files (include)
3. commands/ - 19 files (include)
4. agents/ - 19 files (include)
5. analysis/ - 16 files (exclude)
6. workflows/ - 14 files (include)
7. reviews/ - 12 files (exclude)
8. proposals/ - 11 files (exclude)

### Appendix C: Template Documentation Structure

Each of the 5 templates has:
- **README.md** (5-15 KB) - Template overview, features, structure
- **TEMPLATE.md** - Template structure definition
- **Multiple agent .md files** - Stack-specific agent definitions
- **Example code** - Sample implementations

**Total template documentation**: ~26 markdown files (after guardkit-python removal)

**Templates by quality score**:
- 9.0-9.2/10: react-typescript, fastapi-python, react-fastapi-monorepo (3 templates)
- 8.0-8.5/10: nextjs-fullstack, default (2 templates)

**Note**: guardkit-python template removed (TASK-G6D4) - GuardKit's `.claude/` is git-managed, so template initialization is not needed for GuardKit development

### Appendix D: Command Categories

**Core Workflow** (6 commands):
- task-create, task-work, task-complete, task-status, task-refine, task-review

**Template System** (2 commands):
- template-create, template-validate

**Agent System** (3 commands):
- agent-enhance, agent-format, agent-validate

**UX Design Integration** (2 commands):
- figma-to-react, zeplin-to-maui

**Utilities** (6 commands):
- debug, plus others

**Total**: 19 commands

### Appendix E: Agent Categories

**Core Agents (Sonnet)** (7 agents):
- architectural-reviewer, task-manager, test-orchestrator, test-verifier
- code-reviewer, software-architect, pattern-advisor

**Stack-Specific (Haiku)** (3 agents):
- python-api-specialist, react-state-specialist, dotnet-domain-specialist

**Specialists** (6 agents):
- devops-specialist, security-specialist, database-specialist
- debugging-specialist, git-workflow-manager, qa-tester

**Orchestrators** (5 agents):
- figma-react-orchestrator, zeplin-maui-orchestrator, build-validator
- complexity-evaluator, agent-content-enhancer

**Total**: 21+ agents

---

## Conclusion

This plan provides a comprehensive roadmap for organizing GuardKit's 417 markdown files into a clean, navigable documentation site. Key outcomes:

1. **Clear categorization**: 172 user-facing, 49 developer, 230 internal
2. **Navigation structure**: 8 top-level sections, max 3 levels deep
3. **Gap analysis**: 13 landing pages to create (8 P0, 3 P1, 2 P2)
4. **Critical fixes**: 4 path mismatches identified
5. **MkDocs-ready**: Complete configuration and exclude patterns

**Next**: Review with user, then proceed to TASK-C5AC (MkDocs configuration).
