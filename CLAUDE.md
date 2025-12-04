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

**See**: `installer/global/commands/*.md` for complete command specifications.

## Hash-Based Task IDs

GuardKit uses hash-based task IDs to prevent duplicates and support concurrent creation:

### Format
- **Simple**: `TASK-{hash}` (e.g., `TASK-a3f8`)
- **With prefix**: `TASK-{prefix}-{hash}` (e.g., `TASK-E01-b2c4`, `TASK-FIX-a3f8`)
- **With subtask**: `TASK-{prefix}-{hash}.{number}` (e.g., `TASK-E01-b2c4.1`)

### Benefits
- ✅ **Zero duplicates** - Mathematically guaranteed unique IDs
- ✅ **Concurrent creation** - Safe for parallel development across worktrees
- ✅ **Conductor.build compatible** - No ID collisions in parallel workflows
- ✅ **PM tool integration** - Automatic mapping to JIRA, Azure DevOps, Linear, GitHub

### Common Prefixes
- `E{number}`: Epic-related tasks (E01, E02, E03)
- `DOC`: Documentation tasks
- `FIX`: Bug fixes
- `TEST`: Test-related tasks
- Custom prefixes: Any 2-4 uppercase alphanumeric characters

### Examples

```bash
# Simple hash-based ID
/task-create "Fix login bug"
# Created: TASK-a3f8

# With prefix
/task-create "Fix login bug" prefix:FIX
# Created: TASK-FIX-a3f8

# Epic-related task
/task-create "Implement user authentication" prefix:E01
# Created: TASK-E01-b2c4

# Subtask
/task-create "Add unit tests for auth" parent:TASK-E01-b2c4
# Created: TASK-E01-b2c4.1
```

### PM Tool Integration

GuardKit automatically maps internal hash IDs to external sequential IDs:

**Internal ID**: `TASK-E01-b2c4`

**External IDs** (automatic):
- JIRA: `PROJ-456`
- Azure DevOps: `#1234`
- Linear: `TEAM-789`
- GitHub: `#234`

This mapping is:
- ✅ Automatic when tasks are exported
- ✅ Bidirectional (internal ↔ external)
- ✅ Persistent across sessions
- ✅ Transparent to users

### For Developers

If you're implementing the hash-based ID system:
- **Implementation Guide**: [Implementation Tasks Summary](docs/research/implementation-tasks-summary.md) - Wave-based execution plan
- **Parallel Development**: [Conductor.build Workflow](docs/guides/hash-id-parallel-development.md) - 20-33% faster completion
- **PM Tool Integration**: [External ID Mapping](docs/guides/hash-id-pm-tools.md) - Integration patterns
- **Technical Details**: [Strategy Analysis](docs/research/task-id-strategy-analysis.md) - Architecture and design decisions
- **Decision Rationale**: [Decision Guide](docs/research/task-id-decision-guide.md) - Why hash-based IDs?

### Migration Note

**Existing tasks with old sequential IDs?** Run the personal migration script:

```bash
# Preview changes
python3 scripts/migrate-my-tasks.py --dry-run

# Execute migration
python3 scripts/migrate-my-tasks.py --execute

# Rollback if needed
bash .claude/state/rollback-migration.sh
```

Old IDs are preserved in the `legacy_id` field. See script source for details.

### FAQ

**Q: Why hash-based instead of sequential?**
A: Prevents duplicates in concurrent and distributed workflows. Critical for Conductor.build support and parallel development.

**Q: Will users hate typing TASK-a3f8?**
A: Users rarely type IDs manually. Shell completion, copy/paste, and IDE integration handle this automatically.

**Q: How do PM tools handle hash IDs?**
A: They don't see them! GuardKit maps internal hash IDs to external sequential IDs automatically (see PM Tool Integration above).

**Q: Can I still use sequential IDs?**
A: No. Hash-based IDs are mandatory to prevent duplicates and enable parallel development.

**Q: How long are the IDs?**
A: 4-6 characters for the hash, plus optional 2-4 char prefix. Total: 9-15 characters (e.g., `TASK-FIX-a3f8`).

**Q: What about parallel development?**
A: Hash-based IDs enable safe concurrent task creation across multiple Conductor.build worktrees with zero collision risk. See [Parallel Development Guide](docs/guides/hash-id-parallel-development.md).

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

For formal agentic orchestration systems, GuardKit integrates with RequireKit for BDD workflow.

### When to Use BDD Mode

**Use for**:
- **LangGraph state machines** - Precise behavior specs for state transitions and routing
- **Multi-agent coordination** - Complex interactions between agents
- **Safety-critical workflows** - Quality gates, approval checkpoints, auth/security
- **Formal behavior specifications** - Compliance, audit trails, regulatory requirements

**Don't use for**:
- General CRUD features
- Simple UI components
- Bug fixes and refactoring
- Prototyping and exploration

### Prerequisites

**Required**: RequireKit + GuardKit installed

```bash
# Install RequireKit
cd ~/Projects/require-kit
./installer/scripts/install.sh

# Verify installation
ls ~/.agentecflow/require-kit.marker.json  # Or require-kit.marker (legacy)
```

### Complete Workflow

```bash
# 1. In RequireKit: Create requirements
cd ~/Projects/require-kit
/req-create "System behavior"
/formalize-ears REQ-001
/generate-bdd REQ-001

# 2. In GuardKit: Implement from scenarios
cd ~/Projects/your-project
/task-create "Implement behavior" requirements:[REQ-001]

# Edit task frontmatter to link scenarios:
# bdd_scenarios: [BDD-001]

# 3. Execute BDD workflow
/task-work TASK-042 --mode=bdd
```

### What Happens in BDD Mode

1. **Checks RequireKit installed** - Verifies `~/.agentecflow/require-kit.marker.json` exists (or legacy `require-kit.marker`)
2. **Loads Gherkin scenarios** - Reads scenarios from task `bdd_scenarios` frontmatter field
3. **Routes to bdd-generator agent** - Specialized agent for BDD implementation
4. **Generates step definitions** - Creates pytest-bdd/Cucumber/SpecFlow step functions
5. **Implements to pass scenarios** - Writes code that makes all scenarios pass
6. **Runs BDD tests as quality gate** - 100% BDD test pass rate required

### Example: LangGraph Orchestration

```python
# EARS Requirement (RequireKit)
REQ-ORCH-001: Phase 2.8 Complexity Routing
WHEN task complexity_score ≥ 7, system SHALL invoke FULL_REQUIRED checkpoint.
WHEN task complexity_score is 4-6, system SHALL invoke QUICK_OPTIONAL checkpoint.
WHEN task complexity_score is 1-3, system SHALL proceed automatically.

# Gherkin Scenario (Generated)
Scenario: High complexity triggers mandatory review
  Given a task with complexity score 8
  When the workflow reaches Phase 2.8
  Then the system should invoke FULL_REQUIRED checkpoint
  And the workflow should interrupt with full plan display

# Implementation (GuardKit BDD mode)
def complexity_router(state: GuardKitState) -> Literal["auto_proceed", "quick_review", "full_review"]:
    """Route based on complexity score to appropriate approval path."""
    score = state.complexity_score
    if score >= 7:
        return "full_review"
    elif score >= 4:
        return "quick_review"
    else:
        return "auto_proceed"

# BDD Test (pytest-bdd)
@scenario('complexity-routing.feature', 'High complexity triggers mandatory review')
def test_high_complexity_mandatory_review():
    pass

@given('a task with complexity score 8')
def task_high_complexity(context):
    context.state = GuardKitState(complexity_score=8)

@when('the workflow reaches Phase 2.8')
def reach_phase_28(context):
    context.result = complexity_router(context.state)

@then('the system should invoke FULL_REQUIRED checkpoint')
def verify_full_required(context):
    assert context.result == "full_review"
```

### Benefits for Agentic Systems

✅ **State transition correctness** - All routing paths tested with boundary cases
✅ **Interrupt point validation** - LangGraph `interrupt()` semantics clearly specified
✅ **Approval logic verification** - Decision options and timeouts tested
✅ **Traceability** - REQ-ORCH-001 → Gherkin → Code → Tests
✅ **Living documentation** - Gherkin scenarios document orchestration logic
✅ **Regression protection** - Changes to routing logic are immediately caught

### Error Scenarios

**RequireKit Not Installed**:
```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Alternative modes:
    /task-work TASK-042 --mode=tdd      # Test-first development
    /task-work TASK-042 --mode=standard # Default workflow
```

**No BDD Scenarios Linked**:
```bash
ERROR: BDD mode requires linked Gherkin scenarios

  Add to task frontmatter:
    bdd_scenarios: [BDD-001, BDD-002]

  Or generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /generate-bdd REQ-XXX
```

**See**: [BDD Workflow for Agentic Systems](docs/guides/bdd-workflow-for-agentic-systems.md)

## UX Design Integration (Coming Soon)

Design-to-code workflows for Figma and Zeplin are under active development.

**Planned Features:**
- `/figma-to-react` - Figma to TypeScript React + Tailwind
- `/zeplin-to-maui` - Zeplin to XAML + C# + platform tests

**Status:** Implementation tasks are tracked in `tasks/backlog/design-url-integration/`

**See**: [UX Design Integration Workflow](docs/workflows/ux-design-integration-workflow.md) for planned architecture

## Template Validation

GuardKit provides a 3-level validation system for template quality assurance.

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

Phase 8 enables **incremental agent enhancement** - you can improve agent files over time instead of all at once.

### When to Use

**Use Incremental Enhancement**:
- Template has 5+ agents (too many to enhance at once)
- Want to prioritize critical agents first
- Learning template patterns gradually
- Testing enhancement quality on small subset

**Use Full Enhancement** (during template creation):
- Template has 1-3 agents (quick to enhance)
- Need all agents complete immediately
- One-time template creation

### Workflow Options

#### Option A: Task-Based (Recommended)

```bash
# 1. Create template with agent tasks
/template-create --name my-template --create-agent-tasks

# 2. Review created tasks
/task-status

# Output:
# BACKLOG:
#   TASK-AGENT-API-ABC123 - Enhance api-service-specialist
#   TASK-AGENT-DATABASE-DEF456 - Enhance database-specialist
#   ...

# 3. Work on high-priority agents first
/task-work TASK-AGENT-API-ABC123

# 4. Complete when satisfied
/task-complete TASK-AGENT-API-ABC123

# 5. Repeat for other agents as needed
```

**Benefits**:
- Tracked in task system
- Can prioritize enhancement work
- Integrated with /task-work workflow
- Progress visible

#### Option B: Direct Enhancement

```bash
# 1. Create template (without --create-agent-tasks)
/template-create --name my-template

# 2. Enhance specific agent
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template

# 3. Review changes (dry-run first)
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template \
               --dry-run

# 4. Apply if satisfied
/agent-enhance ~/.agentecflow/templates/my-template/agents/api-service-specialist.md \
               ~/.agentecflow/templates/my-template
```

**Benefits**:
- Immediate enhancement
- No task overhead
- Quick iteration

### Enhancement Strategies

#### AI Strategy (Recommended)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=ai
```
- Uses agent-content-enhancer
- Analyzes template code
- Generates examples and best practices
- **Requires**: AI integration

#### Static Strategy (Fallback)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=static
```
- Uses template-based enhancement
- Extracts patterns from source
- No AI required
- Good for offline use

#### Hybrid Strategy (Default)
```bash
/agent-enhance AGENT_FILE TEMPLATE_DIR --strategy=hybrid
```
- Tries AI first
- Falls back to static if AI fails
- Best reliability
- Recommended for most users

### Best Practices

1. **Start with Critical Agents**
   - Enhance high-priority agents first (priority >= 9)
   - Use task system to track priorities

2. **Review Before Applying**
   - Always use `--dry-run` first
   - Review generated content
   - Validate examples compile

3. **Iterate on Quality**
   - Enhance incrementally
   - Test agent guidance in practice
   - Refine based on user feedback

4. **Maintain Consistency**
   - Use same strategy across agents
   - Follow same content structure
   - Keep quality bar consistent

**See Also**:
- [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md)
- [Agent Enhance Command](installer/global/commands/agent-enhance.md)

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

GuardKit includes **5 high-quality templates** for learning and evaluation:

### Stack-Specific Reference Templates (9+/10 Quality)
1. **react-typescript** - Frontend best practices (from Bulletproof React)
2. **fastapi-python** - Backend API patterns (from FastAPI Best Practices)
3. **nextjs-fullstack** - Full-stack application (Next.js App Router)

### Specialized Templates (8-9+/10 Quality)
4. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)

### Language-Agnostic Template (8+/10 Quality)
5. **default** - For Go, Rust, Ruby, Elixir, PHP, and other languages

### Note on guardkit-python Template (Removed)

The `guardkit-python` template was removed because:
- **GuardKit's `.claude/` is git-managed** - Template initialization not needed for GuardKit development
- **User confusion** - Template suggested users should run `guardkit init` on GuardKit repo itself (incorrect)
- **Better alternatives exist** - Users needing Python CLI templates should use `fastapi-python` or create custom templates via `/template-create`

**For GuardKit development**: The `.claude/` directory is checked into git. Clone the repo and use the configuration as-is.

**For Python CLI projects**: Use `fastapi-python` template or create a custom template based on your architecture.

### Why This Approach?

**Templates are learning resources, not production code.**

Each template demonstrates:
- ✅ How to structure templates for `/template-create`
- ✅ Stack-specific best practices (or language-agnostic patterns)
- ✅ GuardKit workflow integration
- ✅ Boundary sections (ALWAYS/NEVER/ASK) for clear agent behavior
- ✅ High quality standards (all score 8+/10)

### For Production: Use `/template-create`

```bash
# Evaluate GuardKit (reference template)
guardkit init react-typescript

# Production workflow (recommended)
cd your-existing-project
/template-create  # Creates agents + enhancement tasks by default
guardkit init your-custom-template
```

**Default Behavior (TASK-UX-3A8D)**: `/template-create` now creates agent enhancement tasks by default, providing immediate guidance on next steps. Use `--no-create-agent-tasks` to opt out (e.g., CI/CD automation).

**Why?** Your production code is better than any generic template. Create templates from what you've proven works.

**See**: [Template Philosophy Guide](docs/guides/template-philosophy.md) for detailed explanation.

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

## Installation & Setup

```bash
# Install
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with template
guardkit init [react-typescript|fastapi-python|nextjs-fullstack|default]

# View template details
guardkit init react-typescript --info
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

### Agent Discovery System

GuardKit uses AI-powered agent discovery to automatically match tasks to appropriate specialists based on metadata (stack, phase, capabilities, keywords). No hardcoded mappings - discovery is intelligent and extensible.

**How It Works:**
1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans agents with precedence (local > user > global > template)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and source (local/user/global)

**Discovery Metadata** (frontmatter in agent files):
- `stack`: [python, react, dotnet, typescript, cross-stack, etc.]
- `phase`: implementation | review | testing | orchestration | debugging
- `capabilities`: List of specific skills
- `keywords`: Searchable terms for matching

**Graceful Degradation**: Agents without metadata are skipped (no errors). System works during migration.

**Example: Agent Selection During `/task-work`**

```bash
/task-work TASK-h8j3  # Task involves Python API implementation

# System analyzes:
# - Files: *.py (Python detected)
# - Keywords: "API endpoint", "FastAPI"
# - Phase: Implementation (Phase 3)

# Discovery matches:
# - Stack: python ✓
# - Phase: implementation ✓
# - Capabilities: api, async-patterns, pydantic ✓

# Selected: fastapi-specialist (source: template)
# Fallback: task-manager (if no specialist found)
```

### Stack-Specific Implementation Agents (Template-Based, Haiku Model)

Stack-specific agents are distributed across templates and automatically discovered:

**Python Stack** (via `fastapi-python` template):
- **fastapi-specialist**: FastAPI endpoints, async patterns, Pydantic schemas
- **fastapi-database-specialist**: Database operations and query optimization
- **fastapi-testing-specialist**: Testing patterns and pytest integration

**React Stack** (via `react-typescript` template):
- **react-state-specialist**: React hooks, TanStack Query, state management
- **react-query-specialist**: TanStack Query patterns and cache management
- **form-validation-specialist**: React Hook Form + Zod patterns
- **feature-architecture-specialist**: Feature-based organization

**Next.js Stack** (via `nextjs-fullstack` template):
- **nextjs-fullstack-specialist**: Full-stack Next.js patterns
- **nextjs-server-components-specialist**: Server component patterns
- **nextjs-server-actions-specialist**: Server action patterns

**Benefits:**
- 4-5x faster implementation (Haiku vs Sonnet)
- 48-53% total cost savings (vs all-Sonnet)
- 90%+ quality maintained via Phase 4.5 test enforcement
- Agents co-located with template patterns for consistency

**See**: [Agent Discovery Guide](docs/guides/agent-discovery-guide.md) for comprehensive documentation.

### Agent Enhancement with Boundary Sections

All agents enhanced via `/agent-enhance` or `/template-create` now conform to GitHub best practices by including **ALWAYS/NEVER/ASK boundary sections**.

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

**Stack-Specific Implementation Agents** (Template-Based, Haiku):
Stack-specific agents are now in templates - see [Stack-Specific Implementation Agents](#stack-specific-implementation-agents-template-based-haiku-model) above.

**Note**: All agents include ALWAYS/NEVER/ASK boundary sections. See [Agent Enhancement with Boundary Sections](#agent-enhancement-with-boundary-sections) for details.

**See**: `installer/global/agents/*.md` for cross-stack agent specifications.

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

## Need Requirements Management?

For formal requirements (EARS notation, BDD with Gherkin, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with GuardKit.
