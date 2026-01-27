# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GuardKit - Lightweight AI-Assisted Development

This is the **GuardKit** project - a lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

**Core Features:**
- **Quality Gates**: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- **Simple Workflow**: Create → Work → Complete (3 commands)
- **AI Collaboration**: AI handles implementation, humans make decisions
- **No Ceremony**: Minimal process, maximum productivity

### Core Principles

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **AI/Human Collaboration**: AI does heavy lifting, humans make decisions
4. **Zero Ceremony**: No unnecessary documentation or process
5. **Fail Fast**: Block bad code early, don't let it reach production

## Essential Commands

### Core Workflow
```bash
/task-create "Title" [priority:high|medium|low]
/task-work TASK-XXX [--mode=standard|tdd]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Review Workflow (Analysis/Decision Tasks)
```bash
/task-create "Title" task_type:review
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH]
/task-complete TASK-XXX
```

### Feature Planning Workflow (NEW - TASK-FW-001)
```bash
/feature-plan "feature description"  # Single command - auto-detects everything!
```

The `/feature-plan` command provides a streamlined, single-command experience for planning new features with automatic subtask generation.

**What it does**:
1. Creates review task automatically
2. Executes architectural review
3. On [I]mplement: Auto-creates complete feature structure
4. Generates all documentation and subtasks

**Example**:
```bash
/feature-plan "implement dark mode"

# System automatically:
# ✅ Creates review task
# ✅ Analyzes feature requirements
# ✅ Detects feature slug: "dark-mode"
# ✅ Extracts 7 subtasks from recommendations
# ✅ Assigns implementation modes (task-work/direct/manual)
# ✅ Detects 3 parallel waves
# ✅ Creates tasks/backlog/dark-mode/ with:
#    ├── README.md (feature documentation)
#    ├── IMPLEMENTATION-GUIDE.md (wave breakdown)
#    ├── TASK-DM-001-add-css-variables.md (direct, wave 1)
#    ├── TASK-DM-002-create-theme-toggle.md (task-work, wave 1)
#    └── ... (5 more subtasks)
```

**Benefits**:
- **Zero manual task creation** - All subtasks auto-generated from review
- **Smart mode assignment** - Automatic task-work/direct/manual tagging
- **Parallel execution ready** - Conductor workspace names included
- **Complete documentation** - README + Implementation Guide generated
- **95% time savings** - <1 minute vs 15-30 minutes manual setup

**See**: `installer/core/commands/feature-plan.md` for complete documentation

### Autonomous Build Workflow (AutoBuild)
```bash
/feature-build TASK-XXX [--max-turns N] [--sdk-timeout S] [--resume] [--verbose]
```

The `/feature-build` command provides fully autonomous task implementation using the Player-Coach adversarial workflow.

**What it does**:
1. Creates isolated git worktree
2. Runs Player-Coach dialectical loop
3. Player implements, Coach validates
4. Preserves worktree for human review (never auto-merges)

**Example**:
```bash
/feature-build TASK-AUTH-001

# Output:
# Turn 1: Player implements → Coach provides feedback
# Turn 2: Player improves → Coach approves
#
# Status: APPROVED
# Worktree: .guardkit/worktrees/TASK-AUTH-001
# Next: cd .guardkit/worktrees/TASK-AUTH-001 && git diff main
```

**When to use**:
- Well-defined requirements with clear acceptance criteria
- Standard implementation patterns
- Low-medium risk changes that can complete in 1-5 iterations

**When to use /task-work instead**:
- Exploratory work
- Complex architectural decisions
- High-risk changes requiring human judgment

#### Security Validation

AutoBuild includes automatic security validation:

**Quick Checks** (all tasks, ~30s):
- Hardcoded secrets, SQL injection, command injection
- CORS misconfiguration, debug mode

**Full Review** (security-tagged tasks, ~2-5min):
- OWASP Top 10 analysis
- Auth pattern review

**Configuration**:
```yaml
# In task frontmatter
security:
  level: standard  # strict | standard | minimal | skip
```

**See**: [Security Validation Guide](docs/guides/security-validation.md)

**See Also**: `installer/core/commands/feature-build.md` for complete documentation

### Feature Completion
```bash
/feature-complete TASK-XXX [--dry-run] [--force] [--verify]
/feature-complete FEAT-XXX [--dry-run] [--force] [--verify]
```

The `/feature-complete` command finalizes AutoBuild work by merging worktree changes to main:
- Archives worktree state to `.guardkit/archive/`
- Updates task status to COMPLETED
- Cleans up worktree (preserves archive)

**Modes**:
- **Single Task**: `/feature-complete TASK-XXX` - Merge one task
- **Feature**: `/feature-complete FEAT-XXX` - Merge all tasks in a feature

**Example**:
```bash
# Preview what will be merged
/feature-complete TASK-AUTH-001 --dry-run

# Merge with test verification
/feature-complete TASK-AUTH-001 --verify

# Merge entire feature
/feature-complete FEAT-A1B2
```

**Note**: Features completed successfully through `/feature-build` preserve worktrees for review. Use `/feature-complete` to:
- Merge approved worktree changes to main
- Archive AutoBuild state for audit trail
- Clean up after human review

**See**: `installer/core/commands/feature-complete.md` for complete documentation

### Agent & Template Management
```bash
/agent-format <template>/<agent>     # Format agent to template standards
/agent-validate <agent-file>         # Validate agent quality
/agent-enhance <agent-file> <template-dir> [--strategy=ai|static|hybrid] [--dry-run]
/template-validate <template-path>   # Comprehensive template audit
```

### Design-First Workflow (Complex Tasks)
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
# [Review and approve implementation plan]
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### UX Design Integration (Coming Soon)
Design-to-code workflows for Figma and Zeplin are under active development.
See `tasks/backlog/design-url-integration/` for implementation status.

### Utilities
```bash
/debug  # Troubleshoot issues
```

**See**: `installer/core/commands/*.md` for complete command specifications.

## AutoBuild

Autonomous task implementation using Player-Coach adversarial workflow.
Run: `guardkit autobuild task TASK-XXX [--mode=tdd]`
See: `.claude/rules/autobuild.md` for full documentation.

## Hash-Based Task IDs

Format: `TASK-{hash}` or `TASK-{prefix}-{hash}` (e.g., `TASK-FIX-a3f8`)
Benefits: Zero duplicates, concurrent-safe, Conductor compatible.
See: `.claude/rules/hash-based-ids.md` for full documentation.

## Task Workflow Phases

The `/task-work` command executes these phases automatically:

```
Phase 1: Requirements Analysis (require-kit only - skipped in guardkit)
Phase 2: Implementation Planning (Markdown format)
Phase 2.5: Architectural Review (SOLID/DRY/YAGNI scoring)
Phase 2.7: Complexity Evaluation (0-10 scale)
Phase 2.8: Human Checkpoint (if complexity ≥7 or review required)
Phase 3: Implementation
Phase 4: Testing (compilation + coverage)
Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
Phase 5: Code Review
Phase 5.5: Plan Audit (scope creep detection)
```

**Note**: GuardKit starts directly at Phase 2 using task descriptions and acceptance criteria. For formal requirements analysis (EARS, BDD), use [require-kit](https://github.com/requirekit/require-kit).

**Key Decision Points:**
- **Phase 2.7**: Auto-proceed (1-3) vs checkpoint (7-10)
- **Phase 2.8**: Approve/Modify/Simplify/Reject/Postpone
- **Phase 4.5**: Auto-fix vs block task
- **Phase 5.5**: Approve vs escalate

## Complexity Evaluation

**Two-Stage System:**
1. **Upfront (task-create)**: Decide if task should be split (threshold: 7/10)
2. **Planning (task-work)**: Decide review mode (auto/quick/full)

**Scoring (0-10 scale):**
- File Complexity (0-3): Based on number of files
- Pattern Familiarity (0-2): Known vs new patterns
- Risk Assessment (0-3): Low/medium/high risk
- Dependencies (0-2): Number of external dependencies

**Complexity Levels:**
- **1-3 (Simple)**: <4 hours, AUTO_PROCEED
- **4-6 (Medium)**: 4-8 hours, QUICK_OPTIONAL (30s timeout)
- **7-10 (Complex)**: >8 hours, FULL_REQUIRED (mandatory checkpoint)

**See**: [Complexity Management Workflow](docs/workflows/complexity-management-workflow.md)

## Clarifying Questions

GuardKit asks targeted questions before making assumptions during planning (~15% rework reduction).

**Flags** (all commands):
- `--no-questions` - Skip clarification
- `--with-questions` - Force clarification
- `--defaults` - Use defaults without prompting
- `--answers="..."` - Inline answers for automation

**Agent**: `clarification-questioner` at `~/.agentecflow/agents/`

**See**: `.claude/rules/clarifying-questions.md` for complexity gating, examples, and troubleshooting.

## Review vs Implementation Workflows

GuardKit supports two distinct command workflows for different task types:

### Implementation Workflow (/task-work)
Use when **building** features, fixing bugs, or creating code:
```bash
/task-create "Add user authentication"
# Created: TASK-a3f8
/task-work TASK-a3f8  # Implements, tests, reviews code
/task-complete TASK-a3f8
```

**Phases**: Planning → Architectural Review → Implementation → Testing → Code Review → Plan Audit

### Review Workflow (/task-review)
Use when **analyzing** architecture, making decisions, or assessing quality:
```bash
/task-create "Architectural review of authentication system" task_type:review
# Created: TASK-b2c4
/task-review TASK-b2c4  # Analyzes code, generates report, recommends decision
# If implementing findings: /task-work TASK-c5d7
/task-complete TASK-b2c4
```

**Phases**: Load Context → Execute Analysis → Synthesize Recommendations → Generate Report → Human Decision Checkpoint

### When to Use Each

| Scenario | Command |
|----------|---------|
| "Implement feature X" | `/task-work` |
| "Should we implement X?" | `/task-review` |
| "Fix bug in X" | `/task-work` |
| "Review architecture of X" | `/task-review` |
| "Add tests for X" | `/task-work` |
| "Assess technical debt in X" | `/task-review` |
| "Refactor X" | `/task-work` |
| "Security audit of X" | `/task-review` |

### Review Modes

`/task-review` supports five specialized modes:

1. **architectural** - SOLID/DRY/YAGNI compliance review
2. **code-quality** - Maintainability and complexity assessment
3. **decision** - Technical decision analysis with options evaluation
4. **technical-debt** - Debt inventory and prioritization
5. **security** - Security audit and vulnerability assessment

### Review Depth Levels

- **quick** (15-30 min) - Initial assessment, sanity checks
- **standard** (1-2 hours) - Regular reviews, architecture assessments
- **comprehensive** (4-6 hours) - Security audits, critical decisions

### Example Review Workflow

```bash
# 1. Create review task (system detects and suggests /task-review)
/task-create "Review authentication architecture" task_type:review
# Created: TASK-d4e9

# 2. Execute architectural review
/task-review TASK-d4e9 --mode=architectural --depth=standard

# 3. Decision checkpoint (automated)
#    [A]ccept - Approve findings, move to IN_REVIEW
#    [R]evise - Request deeper analysis
#    [I]mplement - Create implementation task based on recommendations
#    [C]ancel - Discard review

# 4. If [I]mplement chosen, new task created automatically
/task-work TASK-f7g2  # Implement recommended changes (auto-created)

# 5. Complete review task
/task-complete TASK-d4e9
```

**See**: [Task Review Workflow](docs/workflows/task-review-workflow.md) for detailed guidance.

## BDD Workflow (Agentic Systems)

For LangGraph state machines, multi-agent coordination, and safety-critical workflows requiring formal behavior specifications, use BDD mode with RequireKit.

```bash
/task-work TASK-XXX --mode=bdd
```

**Requires**: RequireKit installation (`~/.agentecflow/require-kit.marker.json`)

**See**: [BDD Workflow for Agentic Systems](docs/guides/bdd-workflow-for-agentic-systems.md) for complete setup, EARS notation, Gherkin generation, and examples.

## UX Design Integration (Coming Soon)

Design-to-code workflows for Figma and Zeplin are under active development.

**Planned Features:**
- `/figma-to-react` - Figma to TypeScript React + Tailwind
- `/zeplin-to-maui` - Zeplin to XAML + C# + platform tests

**Status:** Implementation tasks are tracked in `tasks/backlog/design-url-integration/`

**See**: [UX Design Integration Workflow (Archived)](docs/archive/ux-design-integration-workflow.md) for planned architecture

## Template Validation

3-level validation: Automatic (always), Extended (`--validate`), Comprehensive (`/template-validate`).
Reports saved to template directory.
**See**: [Template Validation Guide](docs/guides/template-validation-guide.md)

## Template Creation Workflow Phases

The `/template-create` command executes these phases automatically:

```
Phase 1: Source Analysis
Phase 2: File Discovery
Phase 3: Manifest Generation
Phase 4: Settings Extraction
Phase 5: CLAUDE.md Generation
Phase 6: Agent Discovery
Phase 7: Validation
Phase 8: Agent Task Creation [OPTIONAL]
  ├─ Creates one task per agent file
  ├─ Task metadata includes agent_file, template_dir, template_name
  ├─ Tasks can be enhanced incrementally using /task-work
  └─ Alternative: Manual enhancement with /agent-enhance
```

**Phase 8 Options**:
1. **Automatic** (with `--create-agent-tasks`): Creates tasks, enhance later
2. **Manual** (without flag): Use `/agent-enhance` directly per agent

**See**: [Incremental Enhancement Workflow](#incremental-enhancement-workflow)

## Design-First Workflow

Optional flags for complex tasks requiring upfront design approval.

**Flags:**
- `--design-only`: Phases 2-2.8, stops at checkpoint, saves plan
- `--implement-only`: Phases 3-5, requires `design_approved` state
- (default): All phases 2-5.5 in sequence

**Use `--design-only` when:**
- Complexity ≥7
- High-risk changes (security, breaking, schema)
- Multi-person teams (architect designs, dev implements)
- Multi-day tasks

**See**: [Design-First Workflow](docs/workflows/design-first-workflow.md)

## Incremental Enhancement Workflow

Enhance agents incrementally via task-based or direct enhancement.
Use `--create-agent-tasks` flag to generate enhancement tasks automatically.
**See**: [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md)

## Project Structure

```
.claude/                    # Configuration
├── agents/                # Specialized AI agents
├── commands/              # Command specifications
└── task-plans/            # Implementation plans (Markdown)

tasks/                      # Task management
├── backlog/
├── in_progress/
├── in_review/
├── blocked/
└── completed/

docs/                       # Documentation
├── guides/                # Workflow guides
└── workflows/             # Detailed workflows

installer/core/           # Global resources
├── agents/                # Core AI agents
├── commands/              # Command specs
└── templates/             # Stack templates
```

## Template Philosophy

5 high-quality templates for learning: react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, default.
Create production templates from your code with `/template-create`.
**See**: [Template Philosophy Guide](docs/guides/template-philosophy.md)

## Template Quality Standards

### Agent Content Quality

**Minimum Standards** (enforced by validation):
- Valid frontmatter with required fields
- Technologies list populated
- Priority set (0-10 scale)

**Production Standards** (incremental enhancement goal):
- 3-5 code examples from template source
- Best practices section (5-8 practices)
- Anti-patterns section (3-5 common mistakes)
- Meaningful "Why This Agent Exists" (not circular)
- Integration guidance with usage examples

**Enhancement Path**:
1. Template creation: Generates stub agents (minimum standards)
2. Phase 8: Creates enhancement tasks (if --create-agent-tasks)
3. Incremental work: Enhance agents to production standards
4. Validation: Verify quality with /template-validate

**See**: [Incremental Enhancement Workflow](#incremental-enhancement-workflow)

## Progressive Disclosure

Core files always load; extended files load on-demand (55-60% token reduction).
Default: rules structure (`--no-rules-structure` to opt out).
**See**: [Rules Structure Guide](docs/guides/rules-structure-guide.md)

## Claude Code Rules Structure

GuardKit templates support Claude Code's modular rules structure for optimized context loading.

### When to Use

| Scenario | Recommendation |
|----------|---------------|
| Simple templates (<15KB) | Single CLAUDE.md with split |
| Complex templates (>15KB) | Rules structure |
| Path-specific patterns | Rules structure |
| Universal rules only | Single CLAUDE.md |

### Structure Overview

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # paths: **/*.{ext}
    ├── testing.md               # paths: **/*.test.*
    ├── patterns/
    │   └── {pattern}.md
    └── agents/
        └── {agent}.md           # paths: **/relevant/**
```

### Generating Rules Structure

```bash
# Default (rules structure - TASK-TC-DEFAULT-FLAGS)
/template-create

# Opt-out to progressive disclosure (split files)
/template-create --no-rules-structure
```

### Path-Specific Loading

Rules files can include `paths:` frontmatter for conditional loading:

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules
...
```

Rules without `paths:` frontmatter load unconditionally.

### Benefits

- **60-70% context reduction** - Rules load only when relevant
- **Better organization** - Related rules grouped in subdirectories
- **Conditional agents** - Agent guidance loads for relevant files only
- **Recursive discovery** - Subdirectories automatically scanned

**See**: [Rules Structure Guide](docs/guides/rules-structure-guide.md)

## Installation & Setup

```bash
# Basic installation (shell script)
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Or with pip (Python package)
pip install guardkit-py

# With AutoBuild support (required for /feature-build)
pip install guardkit-py[autobuild]

# Development installation
pip install guardkit-py[dev]      # Testing dependencies
pip install guardkit-py[all]      # Everything

# Initialize with template
guardkit init [react-typescript|fastapi-python|nextjs-fullstack|default]

# View template details
guardkit init react-typescript --info
```

**Note**: AutoBuild features (`/feature-build`, `guardkit autobuild`) require the optional `claude-agent-sdk` dependency. If you see "Claude Agent SDK not installed", run:
```bash
pip install guardkit-py[autobuild]
# OR
pip install claude-agent-sdk
```

**Python Command Scripts**: All Python-based command scripts are symlinked to `~/.agentecflow/bin/` for global accessibility. This allows commands to work from any directory, including Conductor worktrees. The symlinks point to the actual repository scripts, so updates propagate automatically.

**Directory Structure**:
```
~/.agentecflow/
├── bin/              # Python script symlinks
├── commands/         # Slash command definitions
├── agents/           # Agent markdown files
└── templates/        # User templates
```

**Template Documentation:**
- [react-typescript](installer/core/templates/react-typescript/README.md) - From Bulletproof React (28.5k stars)
- [fastapi-python](installer/core/templates/fastapi-python/README.md) - From FastAPI Best Practices (12k+ stars)
- [nextjs-fullstack](installer/core/templates/nextjs-fullstack/README.md) - Next.js App Router + production patterns
- [react-fastapi-monorepo](installer/core/templates/react-fastapi-monorepo/README.md) - React + FastAPI monorepo (9.2/10)
- [default](installer/core/templates/default/README.md) - Language-agnostic foundation

**See Also:**
- [Template Philosophy Guide](docs/guides/template-philosophy.md) - Why these 5 templates?
- [Creating Local Templates](docs/guides/creating-local-templates.md) - Team-specific templates
- [Template Migration Guide](docs/guides/template-migration.md) - Migrating from old templates

## Conductor Integration

Fully compatible with [Conductor.build](https://conductor.build) for parallel development.

**State Persistence:** ✅
- Symlink architecture + auto-commit
- 100% state preservation across worktrees
- Zero manual intervention required

**Setup:**
```bash
./installer/scripts/install.sh  # Creates symlinks automatically
guardkit doctor              # Verify integration
```

**How It Works:**
- Commands/agents: `~/.claude/* → ~/.agentecflow/*`
- State: `{worktree}/.claude/state → {main-repo}/.claude/state`
- All commands available in every worktree
- Automatic state sync across parallel sessions

## Testing by Stack

**Python:**
```bash
pytest tests/ -v --cov=src --cov-report=term --cov-report=json
```

**TypeScript/JavaScript:**
```bash
npm test -- --coverage
```

**.NET:**
```bash
dotnet test --collect:"XPlat Code Coverage" --logger:"json"
```

## Quality Gates (Automatic with `/task-work`)

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Review | ≥60/100 | Human checkpoint |
| Plan Audit | 0 violations | Variance review |

**Phase 4.5 Test Enforcement:**
1. Compilation check
2. Test execution
3. Failure analysis (if needed)
4. Auto-fix + re-run (up to 3 attempts)
5. Block if all attempts fail

**Phase 5.5 Plan Audit:**
- File count match (100%)
- Implementation completeness (100%)
- Scope creep detection (0 violations)
- LOC variance (±20% acceptable)
- Duration variance (±30% acceptable)

## Task States & Transitions

```
BACKLOG
   ├─ (task-work) ──────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                            ↓              ↓
   │                        BLOCKED        BLOCKED
   │
   ├─ (task-review) ─────→ IN_PROGRESS ──→ REVIEW_COMPLETE ──→ COMPLETED
   │                            ↓              ↓                      ↑
   │                        BLOCKED     [I]mplement → task-work ─────┘
   │
   └─ (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (task-work --implement-only) ─→ IN_PROGRESS ──→ IN_REVIEW
```

**States:**
- **BACKLOG**: New task, not started
- **DESIGN_APPROVED**: Design approved (design-first workflow)
- **IN_PROGRESS**: Active development or review in progress
- **IN_REVIEW**: All quality gates passed (implementation tasks)
- **REVIEW_COMPLETE**: Review finished, awaiting decision (review tasks)
- **BLOCKED**: Tests failed or quality gates not met
- **COMPLETED**: Finished and archived

**Review Task Flow:**
1. Create with `task_type:review` → BACKLOG
2. Execute `/task-review TASK-XXX` → IN_PROGRESS
3. Review completes → REVIEW_COMPLETE
4. Decision checkpoint:
   - [A]ccept → COMPLETED (archive review)
   - [I]mplement → Creates new implementation task
   - [R]evise → Stays in REVIEW_COMPLETE, re-run review
   - [C]ancel → Back to BACKLOG

## Core AI Agents

GuardKit uses AI-powered agent discovery to match tasks to specialists based on metadata (stack, phase, capabilities).

**Agent Categories:**
- **Orchestration**: task-manager
- **Review**: architectural-reviewer, code-reviewer, software-architect
- **Testing**: test-orchestrator, test-verifier, qa-tester
- **Debugging**: debugging-specialist
- **Infrastructure**: devops-specialist, security-specialist, database-specialist
- **Stack-specific**: Template-based (fastapi-specialist, react-state-specialist, etc.)

**See**: [Agent Discovery Guide](docs/guides/agent-discovery-guide.md) for discovery system, installation, and customization.

## MCP Integration Best Practices

The system integrates with 4 MCP servers for enhanced capabilities. **All MCPs are optional** - the system works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):
- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

**Design MCPs** (Coming Soon):
- **figma-dev-mode**: Planned for future `/figma-to-react` command
- **zeplin**: Planned for future `/zeplin-to-maui` command

**Note**: Design MCPs are reserved for future design-to-code workflows currently under development. See `tasks/backlog/design-url-integration/` for implementation status.

### Setup Guides

**Core MCPs** (recommended for all users):
- [Context7 MCP Setup](docs/deep-dives/mcp-integration/context7-setup.md) - Up-to-date library documentation
- [Design Patterns MCP Setup](docs/deep-dives/mcp-integration/design-patterns-setup.md) - Pattern recommendations

**Design MCPs** (Coming Soon):
- Figma MCP Setup - Planned for future release
- Zeplin MCP Setup - Planned for future release

See `tasks/backlog/design-url-integration/` for implementation details.

### Performance & Optimization

**Optimization Status**: ✅ All MCPs optimized (4.5-12% context window usage)

**Token Budgets**:
- context7: 2000-6000 tokens (phase-dependent)
- design-patterns: ~5000 tokens (5 results), ~3000 per detailed pattern
- figma-dev-mode: Image-based (minimal token impact)
- zeplin: Design-based (minimal token impact)

**For detailed usage guidelines**: [MCP Optimization Guide](docs/deep-dives/mcp-integration/mcp-optimization.md)

## Development Best Practices

**Quality Standards:**
1. **NEVER implement** features not explicitly specified (zero scope creep)
2. **ALWAYS use `/task-work`** for implementation (handles review, testing, gates automatically)
3. **Trust architectural review** (Phase 2.5 catches issues before implementation)
4. **Trust test enforcement** (Phase 4.5 ensures 100% pass rate)
5. **Track everything in tasks** (complete traceability)

**Development Mode Selection:**
- **TDD**: Complex business logic (Red → Green → Refactor)
- **Standard**: Straightforward implementations

**Note:** For BDD workflows (EARS → Gherkin → Implementation), use [require-kit](https://github.com/requirekit/require-kit) which provides complete requirements management.

**Architecture Compliance:**
- Pattern consistency per stack
- Self-documenting code
- Clean separation of concerns

## Key Workflow

**Simple Task Workflow:**
```bash
# Create task
/task-create "Add user authentication"
# Created: TASK-k3m7

# Work on it (Phases 2-5.5 automatic)
/task-work TASK-k3m7

# Complete
/task-complete TASK-k3m7
```

**Complex Task Workflow (Design-First):**
```bash
# Create complex task
/task-create "Refactor authentication system" priority:high
# Created: TASK-n6p2

# Design phase only
/task-work TASK-n6p2 --design-only

# [Human reviews and approves plan]

# Implementation phase
/task-work TASK-n6p2 --implement-only

# Complete
/task-complete TASK-n6p2
```

**See**: [GuardKit Workflow](docs/guides/guardkit-workflow.md)

## Iterative Refinement

**`/task-refine`**: Lightweight improvement without full re-work.

**Use for:**
- Minor code improvements
- Linting fixes
- Renaming/formatting
- Adding comments

**Don't use for:**
- New features (use `/task-work`)
- Architecture changes
- Major refactoring

**See**: [GuardKit Workflow - Iterative Refinement](docs/guides/guardkit-workflow.md#37-iterative-refinement)

## Markdown Implementation Plans

All plans saved as human-readable Markdown in `.claude/task-plans/{task_id}-implementation-plan.md`.

**Benefits:**
- Human-reviewable (plain text)
- Git-friendly (meaningful diffs)
- Searchable (grep, ripgrep, IDE)
- Editable (manual edits before `--implement-only`)

## Quick Reference

**Command Specifications:** `installer/core/commands/*.md`
**Agent Definitions:** `installer/core/agents/*.md`
**Workflow Guides:** `docs/guides/*.md` and `docs/workflows/*.md`
**Stack Templates:** `installer/core/templates/*/`

## Troubleshooting

### Command Not Found

If a slash command fails with "file not found":

1. **Check symlink exists**:
   ```bash
   ls -l ~/.agentecflow/bin/agent-enhance
   ```

2. **Verify target is valid**:
   ```bash
   readlink ~/.agentecflow/bin/agent-enhance
   ```

3. **Re-run installation**:
   ```bash
   cd ~/Projects/appmilla_github/guardkit
   ./installer/scripts/install.sh
   ```

### Permission Denied

If you get permission errors:

```bash
# Make scripts executable
chmod +x ~/.agentecflow/bin/*

# Or re-run installation
./installer/scripts/install.sh
```

## Known Limitations

### Monorepo Support in VS Code Extension

**Issue**: When using GuardKit in a monorepo (multiple projects in one workspace) via the VS Code Claude Code Extension, task commands may create files at the workspace root level instead of the intended project's `tasks/` directory.

**Why**: The VS Code Extension always opens at the workspace root. There's no facility to change the working directory within the extension.

**Workaround**: For monorepos, use the CLI instead of the VS Code Extension:

```bash
# Navigate to the specific project first
cd my-monorepo/project-a
claude

# Now run GuardKit commands - files will be created in project-a/tasks/
/feature-plan "implement feature"
/task-create "Fix bug"
```

**Affected Commands**: All task commands (`/task-create`, `/task-work`, `/task-review`, `/task-refine`, `/task-complete`, `/feature-plan`)

**Single-Project Workspaces**: This limitation does not affect single-project workspaces. Only monorepos with multiple `tasks/` directories are affected.

## When to Use GuardKit

### Use When:
- Individual tasks or small features (1-8 hours)
- Solo dev or small teams (1-3 developers)
- Need quality enforcement without ceremony
- Want AI assistance with human oversight
- Small-to-medium projects
- **Learning new stack** (use reference templates)
- **Creating team templates** (use `/template-create`)

### Use RequireKit When:
- Need formal requirements management (EARS notation, BDD scenarios)
- Need epic/feature hierarchy
- Need requirements traceability matrices
- Need PM tool integration (Jira, Linear, Azure DevOps, GitHub)
- See [RequireKit](https://github.com/requirekit/require-kit) for seamless integration
