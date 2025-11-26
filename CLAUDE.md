# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Taskwright - Lightweight AI-Assisted Development

This is the **Taskwright** project - a lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

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

### Design-First Workflow (Complex Tasks)
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
# [Review and approve implementation plan]
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### UX Design Integration
```bash
/figma-to-react <file-key> [node-id]    # Figma → TypeScript React + Tailwind
/zeplin-to-maui <project-id> <screen-id> # Zeplin → .NET MAUI + XAML
```

### Utilities
```bash
/debug  # Troubleshoot issues
```

**See**: `installer/global/commands/*.md` for complete command specifications.

## Task Workflow Phases

The `/task-work` command executes these phases automatically:

```
Phase 1: Requirements Analysis (require-kit only - skipped in taskwright)
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

**Note**: Taskwright starts directly at Phase 2 using task descriptions and acceptance criteria. For formal requirements analysis (EARS, BDD), use [require-kit](https://github.com/requirekit/require-kit).

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

## Review vs Implementation Workflows

Taskwright supports two distinct command workflows for different task types:

### Implementation Workflow (/task-work)
Use when **building** features, fixing bugs, or creating code:
```bash
/task-create "Add user authentication"
/task-work TASK-001  # Implements, tests, reviews code
/task-complete TASK-001
```

**Phases**: Planning → Architectural Review → Implementation → Testing → Code Review → Plan Audit

### Review Workflow (/task-review)
Use when **analyzing** architecture, making decisions, or assessing quality:
```bash
/task-create "Architectural review of authentication system" task_type:review
/task-review TASK-002  # Analyzes code, generates report, recommends decision
# If implementing findings: /task-work TASK-003
/task-complete TASK-002
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

# 2. Execute architectural review
/task-review TASK-002 --mode=architectural --depth=standard

# 3. Decision checkpoint (automated)
#    [A]ccept - Approve findings, move to IN_REVIEW
#    [R]evise - Request deeper analysis
#    [I]mplement - Create implementation task based on recommendations
#    [C]ancel - Discard review

# 4. If [I]mplement chosen, new task created automatically
/task-work TASK-003  # Implement recommended changes

# 5. Complete review task
/task-complete TASK-002
```

**See**: [Task Review Workflow](docs/workflows/task-review-workflow.md) for detailed guidance.

## UX Design Integration

Converts design system files (Figma, Zeplin) into components with **zero scope creep**.

**Supported:**
- `/figma-to-react` - Figma → TypeScript React + Tailwind + Playwright
- `/zeplin-to-maui` - Zeplin → XAML + C# + platform tests

**6-Phase Saga:**
1. MCP Verification
2. Design Extraction
3. Boundary Documentation (12-category prohibition checklist)
4. Component Generation
5. Visual Regression Testing (>95% similarity)
6. Constraint Validation (zero tolerance)

**Quality Gates:**
- Visual fidelity: >95%
- Constraint violations: 0
- Compilation: 100%

**See**: [UX Design Integration Workflow](docs/workflows/ux-design-integration-workflow.md)

## Template Validation

Taskwright provides a 3-level validation system for template quality assurance.

### Validation Levels

**Level 1: Automatic Validation** (Always On)
- Runs during `/template-create` (Phase 5.5)
- CRUD completeness checks
- Layer symmetry validation
- Auto-fix common issues
- Duration: ~30 seconds
- **No user action required**

**Level 2: Extended Validation** (Optional)
```bash
# Personal templates (default: ~/.agentecflow/templates/)
/template-create --validate

# Repository templates (installer/global/templates/)
/template-create --validate --output-location=repo
```
- All Level 1 checks
- Placeholder consistency validation
- Pattern fidelity spot-checks
- Documentation completeness
- Detailed quality report (saved in template directory)
- Exit code based on score
- Duration: 2-5 minutes
- Works with both personal and repository templates

**Level 3: Comprehensive Audit** (On-demand)
```bash
# Personal templates
/template-validate ~/.agentecflow/templates/my-template

# Repository templates
/template-validate installer/global/templates/react-typescript
```
- Interactive 16-section audit
- Section selection
- Session save/resume
- Inline issue fixes
- AI-assisted analysis (sections 8,11,12,13)
- Comprehensive audit report (saved in template directory)
- Decision framework
- Duration: 30-60 minutes (with AI)
- Works with templates in either location

### When to Use Each Level

**Use Level 1** (Automatic):
- Personal templates (default location: `~/.agentecflow/templates/`)
- Quick prototyping
- Learning template creation

**Use Level 2** (`--validate`):
- Before sharing with team
- Pre-deployment QA for repository templates (`--output-location=repo`)
- CI/CD integration
- Quality reporting

**Use Level 3** (`/template-validate`):
- Global template deployment (repository templates)
- Production-critical templates
- Comprehensive audit required
- Development/testing
- Works with templates in either personal or repository location

### Quality Reports

Level 2 and 3 generate markdown reports in the template directory:
- `validation-report.md` (Level 2)
- `audit-report.md` (Level 3)

Reports include:
- Quality scores (0-10)
- Detailed findings
- Actionable recommendations
- Production readiness assessment

**Template Locations**:
- **Personal templates**: `~/.agentecflow/templates/` (default, immediate use)
- **Repository templates**: `installer/global/templates/` (team/public distribution, requires `--output-location=repo` flag)

Validation works with templates in either location.

**See**: [Template Validation Guide](docs/guides/template-validation-guide.md)

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

installer/global/           # Global resources
├── agents/                # Core AI agents
├── commands/              # Command specs
└── templates/             # Stack templates
```

## Template Philosophy

Taskwright includes **5 high-quality templates** for learning and evaluation:

### Stack-Specific Reference Templates (9+/10 Quality)
1. **react-typescript** - Frontend best practices (from Bulletproof React)
2. **fastapi-python** - Backend API patterns (from FastAPI Best Practices)
3. **nextjs-fullstack** - Full-stack application (Next.js App Router)

### Specialized Templates (8-9+/10 Quality)
4. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)

### Language-Agnostic Template (8+/10 Quality)
5. **default** - For Go, Rust, Ruby, Elixir, PHP, and other languages

### Note on taskwright-python Template (Removed)

The `taskwright-python` template was removed because:
- **Taskwright's `.claude/` is git-managed** - Template initialization not needed for Taskwright development
- **User confusion** - Template suggested users should run `taskwright init` on Taskwright repo itself (incorrect)
- **Better alternatives exist** - Users needing Python CLI templates should use `fastapi-python` or create custom templates via `/template-create`

**For Taskwright development**: The `.claude/` directory is checked into git. Clone the repo and use the configuration as-is.

**For Python CLI projects**: Use `fastapi-python` template or create a custom template based on your architecture.

### Why This Approach?

**Templates are learning resources, not production code.**

Each template demonstrates:
- ✅ How to structure templates for `/template-create`
- ✅ Stack-specific best practices (or language-agnostic patterns)
- ✅ Taskwright workflow integration
- ✅ Boundary sections (ALWAYS/NEVER/ASK) for clear agent behavior
- ✅ High quality standards (all score 8+/10)

### For Production: Use `/template-create`

```bash
# Evaluate Taskwright (reference template)
taskwright init react-typescript

# Production workflow (recommended)
cd your-existing-project
/template-create  # Creates agents + enhancement tasks by default
taskwright init your-custom-template
```

**Default Behavior (TASK-UX-3A8D)**: `/template-create` now creates agent enhancement tasks by default, providing immediate guidance on next steps. Use `--no-create-agent-tasks` to opt out (e.g., CI/CD automation).

**Why?** Your production code is better than any generic template. Create templates from what you've proven works.

**See**: [Template Philosophy Guide](docs/guides/template-philosophy.md) for detailed explanation.

## Installation & Setup

```bash
# Install
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with template
taskwright init [react-typescript|fastapi-python|nextjs-fullstack|default]

# View template details
taskwright init react-typescript --info
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
- [react-typescript](installer/global/templates/react-typescript/README.md) - From Bulletproof React (28.5k stars)
- [fastapi-python](installer/global/templates/fastapi-python/README.md) - From FastAPI Best Practices (12k+ stars)
- [nextjs-fullstack](installer/global/templates/nextjs-fullstack/README.md) - Next.js App Router + production patterns
- [react-fastapi-monorepo](installer/global/templates/react-fastapi-monorepo/README.md) - React + FastAPI monorepo (9.2/10)
- [default](installer/global/templates/default/README.md) - Language-agnostic foundation

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
taskwright doctor              # Verify integration
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

### Agent Discovery System

Taskwright uses AI-powered agent discovery to automatically match tasks to appropriate specialists based on metadata (stack, phase, capabilities, keywords). No hardcoded mappings - discovery is intelligent and extensible.

**How It Works:**
1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans all agents for metadata match (stack + phase + keywords)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and why

**Discovery Metadata** (frontmatter in agent files):
- `stack`: [python, react, dotnet, typescript, cross-stack, etc.]
- `phase`: implementation | review | testing | orchestration | debugging
- `capabilities`: List of specific skills
- `keywords`: Searchable terms for matching

**Graceful Degradation**: Agents without metadata are skipped (no errors). System works during migration.

**Example: Agent Selection During `/task-work`**

```bash
/task-work TASK-042  # Task involves Python API implementation

# System analyzes:
# - Files: *.py (Python detected)
# - Keywords: "API endpoint", "FastAPI"
# - Phase: Implementation (Phase 3)

# Discovery matches:
# - Stack: python ✓
# - Phase: implementation ✓
# - Capabilities: api, async-patterns, pydantic ✓

# Selected: python-api-specialist (from template or global)
# Fallback: task-manager (if no specialist found)
```

### Stack-Specific Implementation Agents (Haiku Model)

**Python Stack:**
- **python-api-specialist**: FastAPI endpoints, async patterns, Pydantic schemas

**React Stack:**
- **react-state-specialist**: React hooks, TanStack Query, state management

**.NET Stack:**
- **dotnet-domain-specialist**: Domain models, DDD patterns, value objects

**Benefits:**
- 4-5x faster implementation (Haiku vs Sonnet)
- 48-53% total cost savings (vs all-Sonnet)
- 90%+ quality maintained via Phase 4.5 test enforcement

**See**: [Agent Discovery Guide](docs/guides/agent-discovery-guide.md) for comprehensive documentation.

### Agent Enhancement with Boundary Sections

As of TASK-STND-773D (2025-11-22), all agents enhanced via `/agent-enhance` or `/template-create` now conform to GitHub best practices by including **ALWAYS/NEVER/ASK boundary sections**.

**What Are Boundary Sections?**

Boundary sections explicitly define agent behavior using a three-tier framework:
- **ALWAYS** (5-7 rules): Non-negotiable actions the agent MUST perform
- **NEVER** (5-7 rules): Prohibited actions the agent MUST avoid
- **ASK** (3-5 scenarios): Situations requiring human escalation

**Format**: `[emoji] [action] ([brief rationale])`
- ✅ ALWAYS prefix
- ❌ NEVER prefix
- ⚠️ ASK prefix

**Why Boundary Sections?**

GitHub analysis of 2,500+ repositories identified explicit boundaries as Critical Gap #4 (was 0/10, now 9/10). Boundary clarity:
- Prevents costly mistakes
- Reduces human intervention by 40%
- Improves agent discoverability and reusability
- Sets clear expectations for agent behavior

**Example: Testing Agent Boundaries**

```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

**Example: Repository Agent Boundaries**

```markdown
## Boundaries

### ALWAYS
- ✅ Inject repositories via constructor (enforces DI pattern)
- ✅ Return ErrorOr<T> for all operations (consistent error handling)
- ✅ Use async/await for database operations (prevents thread blocking)
- ✅ Implement IDisposable for database connections (resource cleanup)
- ✅ Validate input parameters before database access (prevent injection)

### NEVER
- ❌ Never use `new()` for repository instantiation (breaks testability and DI)
- ❌ Never expose IQueryable outside repository (violates encapsulation)
- ❌ Never use raw SQL without parameterization (SQL injection risk)
- ❌ Never ignore database errors (silent failures prohibited)
- ❌ Never commit transactions within repository (violates SRP)

### ASK
- ⚠️ Complex joins across >3 tables: Ask if raw SQL vs EF Core query
- ⚠️ Caching strategy needed: Ask if in-memory vs distributed cache
- ⚠️ Soft delete vs hard delete: Ask for data retention policy decision
```

**How to Interpret Boundary Rules**

When reviewing enhanced agents:

1. **ALWAYS Rules**: Verify your implementation follows these guidelines
   - Example: If agent says "✅ Validate input parameters", ensure all inputs are validated

2. **NEVER Rules**: Check you're not violating these prohibitions
   - Example: If agent says "❌ Never use `new()` for repositories", use dependency injection instead

3. **ASK Scenarios**: Recognize when human decision is required
   - Example: "⚠️ Coverage 70-79%: Ask if acceptable" means you should evaluate risk and decide

**Validation During Enhancement**

When you run `/agent-enhance` or `/template-create`, boundary sections are automatically validated:
- Section presence (all three required: ALWAYS, NEVER, ASK)
- Rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- Emoji format (✅/❌/⚠️ prefixes)
- Placement (after "Quick Start", before "Capabilities")

**References**:
- [GitHub Agent Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md)
- [agent-content-enhancer.md](installer/global/agents/agent-content-enhancer.md)
- [template-create.md - Understanding Boundary Sections](installer/global/commands/template-create.md#understanding-boundary-sections)

---

**Orchestration Agents** (cross-stack):
- **task-manager**: Unified workflow management (phase: orchestration)

**Review Agents** (cross-stack):
- **architectural-reviewer**: SOLID/DRY/YAGNI compliance review (phase: review)
- **code-reviewer**: Code quality enforcement (phase: review)
- **software-architect**: System design decisions (phase: review)

**Testing Agents** (cross-stack):
- **test-orchestrator**: Test execution and quality gates (phase: testing)
- **test-verifier**: Test result verification (phase: testing)
- **qa-tester**: QA and testing workflows (phase: testing)

**Debugging Agents** (cross-stack):
- **debugging-specialist**: Systematic debugging and root cause analysis (phase: debugging)

**Infrastructure & Data Agents** (cross-stack):
- **devops-specialist**: Infrastructure patterns and CI/CD (phase: implementation)
- **security-specialist**: Security validation and audits (phase: review)
- **database-specialist**: Data architecture and optimization (phase: implementation)

**Stack-Specific Implementation Agents** (Haiku):
- **python-api-specialist**: FastAPI, async, Pydantic (phase: implementation)
- **react-state-specialist**: Hooks, TanStack Query, Zustand (phase: implementation)
- **dotnet-domain-specialist**: DDD, entities, value objects (phase: implementation)

**Note**: All agents include ALWAYS/NEVER/ASK boundary sections. See [Agent Enhancement with Boundary Sections](#agent-enhancement-with-boundary-sections) for details.

**See**: `installer/global/agents/*.md` for agent specifications.

## MCP Integration Best Practices

The system integrates with 4 MCP servers for enhanced capabilities. **All MCPs are optional** - the system works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):
- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

**Design MCPs** (ONLY used for specific commands):
- **figma-dev-mode**: Figma design extraction (ONLY for `/figma-to-react` command)
- **zeplin**: Zeplin design extraction (ONLY for `/zeplin-to-maui` command)

**Important**: Design MCPs should only be installed if you're actively using those specific design-to-code commands. They are NOT used during regular `/task-work` execution.

### Setup Guides

**Core MCPs** (recommended for all users):
- [Context7 MCP Setup](docs/deep-dives/mcp-integration/context7-setup.md) - Up-to-date library documentation
- [Design Patterns MCP Setup](docs/deep-dives/mcp-integration/design-patterns-setup.md) - Pattern recommendations

**Design MCPs** (only if using design-to-code workflows):
- [Figma MCP Setup](docs/mcp-setup/figma-mcp-setup.md) - For `/figma-to-react` command only
- [Zeplin MCP Setup](docs/mcp-setup/zeplin-mcp-setup.md) - For `/zeplin-to-maui` command only

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

# Work on it (Phases 2-5.5 automatic)
/task-work TASK-001

# Complete
/task-complete TASK-001
```

**Complex Task Workflow (Design-First):**
```bash
# Create complex task
/task-create "Refactor authentication system" priority:high

# Design phase only
/task-work TASK-002 --design-only

# [Human reviews and approves plan]

# Implementation phase
/task-work TASK-002 --implement-only

# Complete
/task-complete TASK-002
```

**See**: [Taskwright Workflow](docs/guides/taskwright-workflow.md)

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

**See**: [Taskwright Workflow - Iterative Refinement](docs/guides/taskwright-workflow.md#37-iterative-refinement)

## Markdown Implementation Plans

All plans saved as human-readable Markdown in `.claude/task-plans/{task_id}-implementation-plan.md`.

**Benefits:**
- Human-reviewable (plain text)
- Git-friendly (meaningful diffs)
- Searchable (grep, ripgrep, IDE)
- Editable (manual edits before `--implement-only`)

## Quick Reference

**Command Specifications:** `installer/global/commands/*.md`
**Agent Definitions:** `installer/global/agents/*.md`
**Workflow Guides:** `docs/guides/*.md` and `docs/workflows/*.md`
**Stack Templates:** `installer/global/templates/*/`

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
   cd ~/Projects/appmilla_github/taskwright
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

## When to Use Taskwright

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

## Need Requirements Management?

For formal requirements (EARS notation, BDD with Gherkin, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with Taskwright.
