---
format_version: 1
description: Reference slices for /task-work — extended documentation, not a command. Run /task-work.
---

# Task Work — Flag Guides (Reference)

> **Reference file — not a command.** On-demand extension of `task-work.md`
> (K13 core/`-ext` shape, PB-13 wave 1). The core file's flag table, phase
> sequence, and state-transition rules are normative; nothing here overrides
> them. Flag semantics are defined ONCE in `task-work.md` § Available Flags (PB-9).

## AutoBuild Mode (TASK-POF-001)

The `--autobuild-mode` flag is a composite flag that bundles optimizations for autonomous (non-interactive) execution. It is equivalent to:

- `--no-questions` - Skip Phase 1.6 clarification (no human present)
- `--skip-arch-review` - Skip Phase 2.5B for complexity ≤5
- `--auto-approve-checkpoint` - Skip Phase 2.8 blocking wait
- `--docs=minimal` - Minimize documentation overhead

**Usage**:
```bash
# AutoBuild uses this internally - equivalent to all four flags
/task-work TASK-XXX --design-only --autobuild-mode

# Individual flags still work for manual use
/task-work TASK-XXX --design-only --no-questions --skip-arch-review --auto-approve-checkpoint --docs=minimal
```

**Note**: When `--autobuild-mode` is specified, individual sub-flags are ignored (the composite flag takes precedence). The individual flags remain available for manual fine-grained control.

## Documentation Level Control (NEW - TASK-036)

Control the verbosity of documentation generated during task execution. This significantly impacts execution time and token consumption.

### Flag: --docs=LEVEL

**Purpose**: Override automatic documentation level selection

**Values**:
- `--docs=minimal` - Structured data only, ~8-12 minutes, 2 files (DEFAULT)
- `--docs=standard` - Brief explanations, ~12-18 minutes, 2 files
- `--docs=comprehensive` - Full documentation, ~36+ minutes, 13+ files

**Auto-selection** (when flag not provided):
- Default: `minimal` mode (use `--docs=standard` to lift)
- Security/compliance keywords: `comprehensive` mode (forced)

**Configuration hierarchy** (highest to lowest priority):
1. Command-line flag (`--docs=minimal|standard|comprehensive`)
2. Force-comprehensive triggers (security, compliance, breaking changes)
3. Settings.json default (`.claude/settings.json` → `documentation.default_level`)
4. Default: `minimal` (use `--docs=standard` to lift)

**Examples**:
```bash
# Default minimal mode (fastest, recommended)
/task-work TASK-042

# Lift to standard mode when more documentation needed
/task-work TASK-043 --docs=standard

# Explicit comprehensive mode (security tasks)
/task-work TASK-044 --docs=comprehensive
```

**Performance impact**:
| Level | Duration | Files | Tokens | Use When |
|-------|----------|-------|--------|----------|
| **minimal** | 8-12 min | 2 | 100-150k | Simple tasks, fast iteration |
| **standard** | 12-18 min | 2 | 150-250k | Normal development |
| **comprehensive** | 36+ min | 13+ | 500k+ | Security, compliance, complex tasks |

**Agent context format**:
All agents receive documentation level via `<AGENT_CONTEXT>` block in prompts:
```
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: {1-10}
task_id: TASK-XXX
stack: {detected_stack}
phase: {1|2|2.5|4|5}
</AGENT_CONTEXT>
```

See individual agent files (installer/core/agents/*.md) for documentation level behavior specifications.

## Intensity Levels (NEW - TASK-INT-c3d4)

The `--intensity` flag controls the ceremony level and phase execution profile, allowing you to tune the workflow for task complexity and team preference.

### Flag: --intensity=LEVEL

**Purpose**: Select predefined phase execution profiles from a spectrum of ceremony levels.

**Values**:
- `minimal` - Fastest execution, minimal phases (alias: `--micro`)
- `light` - Fast execution with brief planning, no architecture review
- `standard` - Full workflow with smart MCP usage (default, current behavior)
- `strict` - Maximum rigor, all phases with blocking checkpoints

**Default**: `standard` (provides current behavior)

### Intensity Level Specifications

#### minimal (--micro alias)

**Use for**: Trivial tasks, cosmetic changes, typo fixes, simple documentation updates.

**Phases Executed**:
- Phase 1: Load context ✓
- Phase 2: Planning ✗
- Phase 2.1: Library Context ✗
- Phase 2.5A: Pattern MCP ✗
- Phase 2.5B: Architectural Review ✗
- Phase 2.7: Complexity Evaluation ✗
- Phase 2.8: Human Checkpoint ✗
- Phase 3: Implementation ✓ (simplified)
- Phase 4: Testing ✓ (no coverage requirement)
- Phase 4.5: Fix Loop ✓ (1 attempt max)
- Phase 5: Code Review ✓ (lint only)
- Phase 5.5: Plan Audit ✗

**Key Characteristics**:
- Execution time: 3-5 minutes
- No implementation plan generated
- Coverage requirements skipped
- Minimal human interaction
- Quick architectural validation (lint only)

**Quality Gates**:
- Compilation: REQUIRED
- Tests Pass: REQUIRED
- Coverage: SKIPPED
- Architectural Review: SKIPPED
- Code Review: Lightweight (lint only)

**Example**:
```bash
# Fix a typo in error message
/task-work TASK-047 --intensity=minimal

# Or use the --micro alias
/task-work TASK-047 --micro
```

#### light

**Use for**: Simple features, straightforward bug fixes, small refactoring tasks.

**Phases Executed**:
- Phase 1: Load context ✓
- Phase 2: Planning ✓ (brief, ~5 minutes)
- Phase 2.1: Library Context ✓ (if libraries detected)
- Phase 2.5A: Pattern MCP ✗
- Phase 2.5B: Architectural Review ✗
- Phase 2.7: Complexity Evaluation ✗
- Phase 2.8: Human Checkpoint ✓ (10s timeout, auto-proceed)
- Phase 3: Implementation ✓
- Phase 4: Testing ✓
- Phase 4.5: Fix Loop ✓ (2 attempts)
- Phase 5: Code Review ✓ (quick)
- Phase 5.5: Plan Audit ✓ (50% variance threshold)

**Key Characteristics**:
- Execution time: 10-15 minutes
- Brief implementation plan (essential elements only)
- Optional checkpoint with auto-proceed
- Faster planning process
- Lighter scope creep detection

**Quality Gates**:
- Compilation: REQUIRED
- Tests Pass: REQUIRED
- Coverage: ≥70% (vs 80% in standard)
- Architectural Review: SKIPPED
- Code Review: Quick pass (no detailed analysis)

**Plan Audit Variance Thresholds**:
- LOC variance: ±50% (vs ±20% in standard)
- Duration variance: ±50% (vs ±30% in standard)

**Example**:
```bash
# Add a simple feature with quick review
/task-work TASK-048 --intensity=light
```

#### standard (default)

**Use for**: Most tasks, normal development, features with clear requirements.

**This is the current default behavior. All phases execute with smart decisions**:
- Phase 1: Load context ✓
- Phase 2: Planning ✓ (full)
- Phase 2.1: Library Context ✓ (always, no-op if no libraries)
- Phase 2.5A: Pattern MCP ✓ (only if pattern need detected)
- Phase 2.5B: Architectural Review ✓
- Phase 2.7: Complexity Evaluation ✓
- Phase 2.8: Human Checkpoint ✓ (30s timeout, auto-proceed for 1-6, blocking for 7-10)
- Phase 3: Implementation ✓
- Phase 4: Testing ✓
- Phase 4.5: Fix Loop ✓ (3 attempts)
- Phase 5: Code Review ✓ (full)
- Phase 5.5: Plan Audit ✓ (20% variance threshold)

**Key Characteristics**:
- Execution time: 15-30 minutes
- Complete implementation plan
- Full architectural review when beneficial
- Complexity-gated checkpoints
- Standard scope creep detection

**Quality Gates**:
- Compilation: REQUIRED
- Tests Pass: REQUIRED
- Coverage: ≥80% lines, ≥75% branches
- Architectural Review: ≥60/100 (human checkpoint if lower)
- Code Review: Full analysis
- Pattern Review: Smart MCP usage

**Plan Audit Variance Thresholds**:
- LOC variance: ±20% acceptable
- Duration variance: ±30% acceptable
- File count variance: 0% (must match plan exactly)

**Example**:
```bash
# Standard workflow - full quality gates
/task-work TASK-049  # Same as /task-work TASK-049 --intensity=standard
```

#### strict

**Use for**: Critical code, security-sensitive changes, APIs, high-risk refactoring, financial systems.

**Phases Executed** (maximum rigor):
- Phase 1: Load context ✓
- Phase 2: Planning ✓ (detailed)
- Phase 2.1: Library Context ✓ (always, comprehensive docs fetch)
- Phase 2.5A: Pattern MCP ✓ (always, comprehensive pattern analysis)
- Phase 2.5B: Architectural Review ✓ (full with security scan)
- Phase 2.7: Complexity Evaluation ✓ (detailed)
- Phase 2.8: Human Checkpoint ✓ (blocking, no timeout)
- Phase 3: Implementation ✓
- Phase 4: Testing ✓ (comprehensive)
- Phase 4.5: Fix Loop ✓ (5 attempts)
- Phase 5: Code Review ✓ (full + security scan)
- Phase 5.5: Plan Audit ✓ (0% variance - any deviation flagged)

**Key Characteristics**:
- Execution time: 30-60+ minutes
- Comprehensive implementation plan
- Mandatory human checkpoint
- Full pattern analysis
- Security vulnerability scanning
- Zero-tolerance scope creep

**Quality Gates**:
- Compilation: REQUIRED
- Tests Pass: REQUIRED (all must pass)
- Coverage: ≥85% lines, ≥80% branches (elevated requirements)
- Architectural Review: ≥70/100 minimum, human checkpoint if lower
- Code Review: Full analysis + security scan
- Pattern Review: Comprehensive pattern analysis

**Plan Audit Variance Thresholds**:
- LOC variance: 0% variance allowed (any deviation flagged for review)
- Duration variance: ±10% only
- File count variance: 0% (exact match required)

**Blocking Checkpoints**:
- Phase 2.8: Mandatory, no timeout
- Phase 5: Full security review before approval

**Example**:
```bash
# Security-critical implementation with maximum rigor
/task-work TASK-050 --intensity=strict

# Financial system changes
/task-work TASK-051 --intensity=strict

# API endpoint changes
/task-work TASK-052 --intensity=strict
```

### Intensity Selection Guide

| Task Type | Recommended | Reason |
|-----------|-------------|--------|
| Typo fix | minimal | Skip unnecessary phases |
| Documentation update | minimal | Documentation-only exception |
| Simple bug fix | light | Brief planning, quick review |
| New UI component | standard | Full architecture review beneficial |
| Business logic feature | standard | Standard rigor recommended |
| Security implementation | strict | Mandatory security review |
| API endpoint changes | strict | Breaking changes require strict mode |
| Database migration | strict | High risk, zero-tolerance scope creep |
| Authentication changes | strict | Security-critical |

### Flag Combinations

**Valid combinations**:
```bash
# Intensity + mode
/task-work TASK-001 --intensity=strict --mode=tdd

# Intensity + documentation
/task-work TASK-002 --intensity=light --docs=comprehensive

# Intensity + clarification (--no-questions for automation)
/task-work TASK-003 --intensity=minimal --no-questions

# But NOT intensity + design flags (conflict)
# ❌ /task-work TASK-001 --intensity=strict --design-only  # Invalid
```

**Note**: `--intensity` cannot be combined with `--design-only` or `--implement-only`. Use design flags for the default intensity workflow only.

### Intensity Auto-Detection (NEW - TASK-INT-e5f6)

When `--intensity` is not explicitly provided, the system automatically detects the appropriate intensity level based on **provenance** and **complexity**.

#### Detection Algorithm

The auto-detection follows a prioritized decision tree:

1. **High-Risk Keywords** → STRICT (always overrides)
2. **Provenance: parent_review** → MINIMAL/LIGHT based on complexity
3. **Provenance: feature_id** → MINIMAL/LIGHT/STANDARD based on complexity
4. **Fresh task** → Complexity-based detection

#### Provenance-Based Rules

**Tasks from Reviews** (have `parent_review` field):
- Complexity ≤4 → **MINIMAL**
- Complexity >4 → **LIGHT**

**Rationale**: Tasks created from review recommendations are already well-scoped by the review process, so they can safely use lighter intensity levels.

**Tasks from Features** (have `feature_id` field):
- Complexity ≤3 → **MINIMAL**
- Complexity ≤5 → **LIGHT**
- Complexity >5 → **STANDARD**

**Rationale**: Feature subtasks benefit from feature-level planning and coordination, reducing the need for individual task rigor.

**Fresh Tasks** (no provenance):
- Complexity ≤3 → **MINIMAL**
- Complexity ≤5 → **LIGHT**
- Complexity ≤6 → **STANDARD**
- Complexity >6 → **STRICT**

**Rationale**: Fresh tasks require more rigor since they lack the benefit of prior planning from reviews or features.

#### High-Risk Keywords

The following keywords in the task description **always force STRICT mode**, regardless of complexity or provenance:

**Security & Authentication**:
- security, auth, authentication, authorization
- oauth, saml, jwt, session
- privilege, permission, access control
- encryption, crypto, cryptographic

**Data & Schema**:
- schema, migration, database

**Breaking Changes**:
- breaking, breaking change, api, endpoint

**Financial**:
- financial, payment, billing

**Vulnerabilities**:
- injection, xss, csrf

**Rationale**: These keywords indicate security-sensitive or high-risk changes that demand maximum rigor regardless of task complexity.

#### Examples

```bash
# Example 1: Task from review with low complexity
# Task: TASK-042
# Description: "Fix typo in error message"
# Complexity: 2
# parent_review: TASK-041
# → Auto-detected: MINIMAL

# Example 2: Task from feature with medium complexity
# Task: TASK-043
# Description: "Add dark mode toggle component"
# Complexity: 5
# feature_id: dark-mode
# → Auto-detected: LIGHT

# Example 3: Fresh task with high-risk keyword
# Task: TASK-044
# Description: "Implement OAuth authentication"
# Complexity: 6
# parent_review: None
# feature_id: None
# → Auto-detected: STRICT (high-risk keyword: "oauth")

# Example 4: Fresh task with high complexity
# Task: TASK-045
# Description: "Refactor payment processing system"
# Complexity: 8
# parent_review: None
# feature_id: None
# → Auto-detected: STRICT (high complexity + "payment" keyword)

# Example 5: User override takes precedence
# Task: TASK-046
# Auto-detected: LIGHT
# → /task-work TASK-046 --intensity=strict
# → Actual: STRICT (user override)
```

#### Provenance Field Expectations

The auto-detection algorithm expects the following fields in the task metadata:

```yaml
# Task frontmatter
task_id: TASK-042
description: "Add user authentication"
complexity: 6
parent_review: TASK-041  # Optional - set if created from review
feature_id: auth-feature # Optional - set if part of feature
```

**Field Sources**:
- `parent_review`: Set by `/task-review` when creating implementation tasks via [I]mplement decision
- `feature_id`: Set by `/feature-plan` when creating feature subtasks
- `complexity`: Set by complexity evaluation during task creation

#### Implementation Details

The auto-detection logic is implemented in `guardkit/orchestrator/intensity_detector.py`:

```python
from guardkit.orchestrator.intensity_detector import (
    IntensityLevel,
    determine_intensity,
    HIGH_RISK_KEYWORDS,
)

# Auto-detect intensity
task_data = {
    "description": task.description,
    "complexity": task.complexity,
    "parent_review": task.parent_review,
    "feature_id": task.feature_id,
}
intensity = determine_intensity(task_data, override=args.intensity)
```

**Module Characteristics**:
- Pure stateless functions (no side effects)
- Dict-based input (no Pydantic coupling)
- Enum-based type safety
- Graceful handling of missing/invalid data

#### Override Behavior

User-provided `--intensity` flag always takes precedence over auto-detection:

```bash
# Auto-detection would choose LIGHT, but user forces STRICT
/task-work TASK-042 --intensity=strict
```

Invalid override values fall back to auto-detection with a warning:

```bash
# Invalid value
/task-work TASK-042 --intensity=invalid
# Warning: Invalid intensity override 'invalid', falling back to auto-detection
# → Uses auto-detected intensity
```

#### Logging

Auto-detection decisions are logged for transparency:

```
INFO: Task from review (parent_review=TASK-041), complexity=3 → minimal
INFO: High-risk keywords detected in description, forcing STRICT intensity
INFO: Task from feature (feature_id=auth-feature), complexity=5 → light
INFO: Fresh task with complexity=7 → strict
```

## Micro-Task Mode (NEW - TASK-020)

The task-work command now supports a `--micro` flag for streamlined execution of trivial tasks (typo fixes, documentation updates, cosmetic changes) that don't require full architectural review.

### Flag: --micro

**Purpose**: Lightweight workflow for trivial tasks, completing in 3-5 minutes vs 15+ minutes.

**Criteria for micro-tasks** (ALL must be true) - TASK-TWP-c3d4 updated thresholds:
- Complexity: ≤3/10 (was 1/10 - simple tasks now qualify)
- Files: ≤3 file modifications (was single file)
- Risk: No high-risk keywords (security, schema, breaking changes, API changes)
- Estimated time: <2 hours (was <1 hour)

**Phases executed**:
- Phase 1: Load Task Context
- Phase 3: Implementation (simplified)
- Phase 4: Quick Testing (compilation + tests only, no coverage)
- Phase 4.5: Fix Loop (1 attempt max, vs 3 in standard)
- Phase 5: Quick Review (lint only, skip SOLID/DRY/YAGNI)

**Phases skipped**:
- Phase 1.7: Fleet-Memory Context Loading
- Phase 2: Implementation Planning
- Phase 2.1: Library Context Gathering
- Phase 2.5A: Pattern Suggestion
- Phase 2.5B: Architectural Review
- Phase 2.6: Human Checkpoint
- Phase 2.7: Complexity Evaluation
- Phase 5.5: Plan Audit (no plan in micro-task mode)

**Quality gates** (micro-task specific):
- Compilation: REQUIRED (same as standard)
- Tests Pass: REQUIRED (same as standard)
- Coverage: SKIPPED (not required for micro-tasks)
- Architectural Review: SKIPPED
- Code Review: LIGHTWEIGHT (lint only)

**Auto-detection**: System automatically suggests `--micro` flag when task qualifies:
- Analyzes task metadata (title, description, estimated effort)
- Detects high-risk keywords (security, database, API, etc.)
- Shows suggestion with 10-second timeout
- User can accept suggestion or continue with full workflow

**Validation**: If `--micro` flag is used but task doesn't qualify, escalates to full workflow with warning.

**Example** (micro-task success):
```bash
/task-work TASK-047 --micro

Micro-Task Mode Enabled

Phase 1: Load Task Context
  Task: Fix typo in error message
  File: src/services/AuthService.py
  Change: 'occured' → 'occurred'

Phase 3: Implementation
  Updated src/services/AuthService.py:45
  Changed error message

Phase 4: Quick Testing
  Compilation: PASSED
  Tests: 5/5 PASSED (coverage skipped)

Phase 5: Quick Review
  Lint: PASSED (no issues)

Task State: BACKLOG → IN_REVIEW
Duration: 2 minutes 34 seconds
```

**Example** (auto-detection):
```bash
/task-work TASK-047

Detected micro-task (confidence: 95%)
This task appears to be trivial (complexity ≤3/10, ≤3 files, <2 hours).

Suggest using: /task-work TASK-047 --micro
Saves ~12 minutes by skipping optional phases.

Auto-apply micro-mode? [y/N] (10s timeout): _
```

**Example** (escalation):
```bash
/task-work TASK-048 --micro

Task does not qualify as micro-task:
  - Complexity: 5/10 (threshold: ≤3/10)
  - High-risk keywords detected: authentication, database
  - Estimated effort: 4 hours (threshold: <2 hours)

Escalating to full workflow...

Phase 1: Load Task Context
Phase 2: Implementation Planning
Phase 2.5B: Architectural Review
...
(continues with full workflow)
```

**Documentation-only exception**: Tasks affecting only documentation files (.md, .txt, .rst) automatically qualify for micro-task mode, even if they affect multiple files.

**Use cases**:
- Typo fixes in code or documentation
- Comment updates and documentation improvements
- Cosmetic changes (formatting, whitespace)
- Simple configuration changes
- Minor UI text updates
- Small refactoring (variable renaming, etc.)

**NOT for**:
- Security-related changes (authentication, authorization, encryption)
- Database schema changes (migrations, table alterations)
- API changes (breaking changes, new endpoints)
- External integrations (third-party APIs, webhooks)
- Multi-file refactoring
- Complex business logic changes

## Design-First Workflow Flags (TASK-006)

The task-work command now supports optional flags for design-first workflow, enabling flexible execution modes based on task complexity and team collaboration needs.

### Flag: --design-only

**Purpose**: Execute design phases only, stop at approval checkpoint.

**Phases executed**:
- Phase 1: Load Task Context
- Phase 2: Implementation Planning
- Phase 2.1: Library Context Gathering
- Phase 2.5A: Pattern Suggestion (if Design Patterns MCP available)
- Phase 2.5B: Architectural Review
- Phase 2.7: Complexity Evaluation & Plan Persistence
- Phase 2.8: Human Checkpoint (mandatory for design-only)

**Phases skipped**:
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Fix Loop
- Phase 5: Code Review

**Outcome**: Task moves to `design_approved` state with saved implementation plan.

**Use cases**:
- Complex tasks (complexity ≥ 7) requiring upfront design approval
- Multi-day tasks where design and implementation happen on different days
- Architect-led design with developer-led implementation
- High-risk changes (security, breaking changes, schema changes)
- Unclear requirements needing design exploration

**Example**:
```bash
/task-work TASK-006 --design-only
```

### Flag: --implement-only

**Purpose**: Execute implementation phases using previously approved design.

**Prerequisite**: Task MUST be in `design_approved` state (approved via --design-only).

**Phases executed**:
- Phase 3: Implementation (using saved plan)
- Phase 4: Testing
- Phase 4.5: Fix Loop (ensure tests pass)
- Phase 5: Code Review

**Phases skipped**:
- Phase 1-2.8 (uses saved design from --design-only run)

**Outcome**: Task moves to `in_review` state (if quality gates pass) or `blocked` (if tests fail).

**Use cases**:
- Implementing previously approved designs
- Continuing work after design approval on different day
- Different person implementing than who designed
- Multi-day task workflow (design Day 1, implement Day 2)

**Example**:
```bash
/task-work TASK-006 --implement-only
```

### No Flags (Default Behavior - Unchanged)

**Purpose**: Execute complete workflow in single session.

**Phases executed**: All phases in sequence (1 → 1.7 → 2 → 2.1 → 2.5A → 2.5B → 2.7 → 2.8 → 3 → 4 → 4.5 → 5 → 5.5)

**Phase 2.8 checkpoint**: Triggered based on complexity evaluation (auto-proceed for 1-3, optional for 4-6, mandatory for 7-10).

**Use cases**:
- Simple to medium tasks (complexity 1-6)
- Straightforward implementation with clear approach
- Single developer handling both design and implementation
- Design and implementation can happen in same session
- Low-risk changes

**Example**:
```bash
/task-work TASK-006
```

### Flag Validation Rules

**Mutual Exclusivity**: --design-only and --implement-only cannot be used together.

```bash
# ❌ Invalid usage
/task-work TASK-006 --design-only --implement-only

# Error message:
❌ Error: Cannot use both --design-only and --implement-only flags together

Choose one workflow mode:
  --design-only     Execute design phases only (Phases 1-2.8)
  --implement-only  Execute implementation phases only (Phases 3-5)
  (no flags)        Execute complete workflow (default)
```

**State Validation**: --implement-only requires task to be in `design_approved` state.

```bash
# ❌ Invalid usage (task not in design_approved state)
/task-work TASK-006 --implement-only

# Error message:
❌ Cannot execute --implement-only workflow

Task TASK-006 is in 'backlog' state.
Required state: design_approved

To approve design first, run:
  /task-work TASK-006 --design-only

Or run complete workflow without flags:
  /task-work TASK-006
```

### New Task State: design_approved

Tasks can now be in a `design_approved` state:
- **Location**: `tasks/design_approved/{task_id}.md`
- **Purpose**: Indicates design has been approved and is ready for implementation
- **Metadata**: Includes saved implementation plan, architectural review scores, complexity evaluation

### Design Metadata Schema

When using --design-only, the following metadata is saved to task frontmatter:

```yaml
design:
  status: approved  # pending, approved, rejected, n/a
  approved_at: "2025-10-11T14:30:00Z"
  approved_by: "human"  # or "auto" for simple tasks
  implementation_plan_version: "v1"
  architectural_review_score: 85
  complexity_score: 7
  design_session_id: "design-TASK-006-20251011143000"
  design_notes: "Architectural review passed, ready for implementation"
```

### Implementation Plan Storage

Design plans are saved to:
```
docs/state/{task_id}/implementation_plan.json
```

This file contains:
- Files to create/modify
- External dependencies
- Estimated duration and LOC
- Implementation phases
- Test strategy
- Risk mitigations
- Architectural review results

## Clarifying Questions Flags (NEW - TASK-CLQ-007)

The task-work command now supports flags to control Phase 1.6 (Clarifying Questions) behavior, enabling flexible clarification workflows for different task complexities and automation scenarios.

### Flag: --no-questions

**Purpose**: Skip Phase 1.6 (Clarifying Questions) entirely and proceed directly from context loading to implementation planning.

**Use cases**:
- CI/CD automation where human input is not available
- Re-running tasks with previously clarified scope
- Tasks with complete specification in description
- Trivial tasks (complexity 1-2) where clarification adds no value
- Fast iteration during prototyping

**Example**:
```bash
/task-work TASK-a3f8 --no-questions
```

**Behavior**:
- Phase 1.6 is skipped regardless of task complexity
- Implementation planning proceeds with task description as-is
- Any ambiguities are resolved using default assumptions
- No user interaction required during execution

### Flag: --with-questions

**Purpose**: Force Phase 1.6 (Clarifying Questions) even for trivial tasks (complexity 1-2).

**Use cases**:
- Learning mode - understand what clarifications are available
- High-stakes tasks where even trivial scope needs confirmation
- Tasks where default assumptions may be incorrect
- Training new team members on clarification patterns

**Example**:
```bash
/task-work TASK-b2c4 --with-questions
```

**Behavior**:
- Phase 1.6 executes regardless of complexity score
- Questions are presented based on detected ambiguity
- For complexity 1-2: Uses quick mode (15s timeout)
- For complexity 3+: Uses appropriate mode based on score

### Flag: --defaults

**Purpose**: Proceed through Phase 1.6 using all default answers without prompting user.

**Use cases**:
- CI/CD pipelines requiring deterministic behavior
- Batch processing multiple tasks
- Testing workflows without manual intervention
- Quick iteration where defaults are acceptable

**Example**:
```bash
/task-work TASK-c5d7 --defaults
```

**Behavior**:
- Phase 1.6 executes (questions are generated)
- All questions are answered with their default values automatically
- No user interaction required
- Clarification context is still passed to Phase 2
- Useful for understanding what questions would be asked

### Flag: --answers="1:Y 2:N 3:JWT"

**Purpose**: Provide inline answers to clarifying questions for automation.

**Format**: Space-separated question-answer pairs using question number and answer code.

**Use cases**:
- CI/CD pipelines with predetermined answers
- Scripted task execution with known parameters
- Integration testing of clarification workflows
- Batch processing with consistent choices

**Example**:
```bash
# Answer 3 questions inline
/task-work TASK-d4e9 --answers="1:S 2:I 3:JWT"

# Breakdown:
# Q1: Implementation Scope → [S]tandard
# Q2: Testing Approach → [I]ntegration tests
# Q3: Auth Strategy → JWT
```

**Behavior**:
- Phase 1.6 executes and generates questions
- System matches provided answers to question numbers
- Answers are validated against question options
- If answer invalid or missing: Uses default for that question
- Clarification context is passed to Phase 2 with provided answers

**Error handling**:
```bash
# Invalid answer code
/task-work TASK-e7f2 --answers="1:X"

# Output:
⚠️ Warning: Invalid answer 'X' for question 1
   Valid options: [M]inimal, [S]tandard, [C]omplete
   Using default: [S]tandard
```

### Complexity-Based Behavior

Clarification flags interact with task complexity:

| Complexity | Default Behavior | With --no-questions | With --with-questions |
|------------|------------------|---------------------|----------------------|
| 1-2 (Trivial) | Skip Phase 1.6 | Skip Phase 1.6 | Execute (quick mode, 15s timeout) |
| 3-4 (Simple) | Execute (quick mode, 15s) | Skip Phase 1.6 | Execute (quick mode, 15s) |
| 5+ (Complex) | Execute (full mode, blocking) | Skip Phase 1.6 | Execute (full mode, blocking) |

### Flag Precedence

When multiple clarification flags are present:

1. **--no-questions** (highest priority): Skips Phase 1.6 entirely
   - Overrides --with-questions, --defaults, --answers

2. **--answers**: Provides inline answers
   - Overrides --defaults
   - Compatible with --with-questions

3. **--defaults**: Uses all defaults
   - Overridden by --answers if both present

4. **--with-questions**: Forces execution
   - Only effective if --no-questions not present

**Examples**:
```bash
# --no-questions overrides everything
/task-work TASK-f7g2 --no-questions --with-questions
# Result: Phase 1.6 skipped (--no-questions wins)

# --answers overrides --defaults
/task-work TASK-h8j3 --defaults --answers="1:C"
# Result: Q1 uses answer C, others use defaults

# --with-questions forces execution
/task-work TASK-k3m7 --with-questions
# Result: Phase 1.6 executes even if complexity is 1-2
```

### Integration with Design-First Workflow

Clarification flags work with design-first workflow:

```bash
# Design-only with clarifications
/task-work TASK-n6p2 --design-only --answers="1:C 2:F"

# Design-only without clarifications (faster)
/task-work TASK-n6p2 --design-only --no-questions

# Implement-only skips Phase 1.6 automatically
/task-work TASK-n6p2 --implement-only
# (uses clarifications from design-only session)
```

**Note**: When using --implement-only, Phase 1.6 is always skipped because clarifications were already captured during the --design-only session.

### See Also

- [Phase 1.6 Specification](#phase-16-clarifying-questions-complexity-gated) - Complete phase workflow
- [Clarifying Questions Feature](../../tasks/backlog/clarifying-questions/) - Implementation details
- [Context C Templates](../../.claude/clarification/templates/context_c_implementation_planning.py) - Question templates

## Context7 MCP Integration (Library Documentation)

During task implementation, **automatically use Context7 MCP** to retrieve up-to-date library documentation when implementing with specific libraries or frameworks.

### When to Use Context7

Context7 should be invoked automatically during these phases:

1. **Phase 2: Implementation Planning**
   - When selecting libraries or frameworks for the implementation
   - When planning API usage patterns
   - When determining best practices for a library

2. **Phase 3: Implementation**
   - When implementing features using specific libraries
   - When unfamiliar with a library's API
   - When library documentation is needed for correct usage
   - When implementing patterns specific to a framework (React hooks, FastAPI patterns, etc.)

3. **Phase 4: Testing**
   - When writing tests using testing frameworks (pytest, Vitest, xUnit)
   - When setting up test fixtures or mocks
   - When implementing test patterns specific to the stack

### Context7 Workflow

**Step 1: Resolve Library ID**

Always resolve library name to Context7-compatible ID first:

```python
# Use mcp__context7__resolve-library-id tool
mcp__context7__resolve_library_id("react")
# Returns: /facebook/react or /facebook/react/v18.2.0
```

**Step 2: Get Library Documentation**

Use resolved ID to fetch documentation:

```python
# Use mcp__context7__get-library-docs tool
mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/facebook/react",
  topic="hooks",              # Optional: focus area
  tokens=5000                 # Optional: max tokens (default: 5000)
)
```

### Examples by Stack

**React/TypeScript:**
- Libraries: "react", "next.js", "tailwindcss", "vitest", "playwright"
- Topics: "hooks", "routing", "styling", "testing"

**Python:**
- Libraries: "fastapi", "pytest", "pydantic", "langchain", "streamlit"
- Topics: "dependency-injection", "testing", "validation", "agents"

**.NET MAUI:**
- Libraries: "maui", "xamarin", "xunit", "moq"
- Topics: "mvvm", "data-binding", "navigation", "testing"

**TypeScript API:**
- Libraries: "nestjs", "typeorm", "jest", "supertest"
- Topics: "dependency-injection", "decorators", "testing", "validation"

### Integration Points in task-work Workflow

**Phase 2: Implementation Planning**
```
When task requires library usage:
1. Identify required libraries from requirements
2. Use Context7 to resolve library IDs
3. Fetch documentation for implementation approach
4. Incorporate library best practices into implementation plan
```

**Phase 3: Implementation**
```
When implementing with unfamiliar library APIs:
1. Use Context7 to get current documentation
2. Focus documentation on relevant topics (use `topic` parameter)
3. Implement according to latest library patterns
4. Verify implementation matches library best practices
```

**Phase 4: Testing**
```
When writing tests:
1. Use Context7 to get testing framework docs
2. Focus on testing patterns and assertions
3. Implement tests using framework best practices
```

### Best Practices

1. **Always resolve library ID first** - Don't assume library path format
2. **Use topic parameter** - Narrow documentation to relevant sections
3. **Limit token usage** - Default 5000 tokens is usually sufficient
4. **Cache library IDs** - Reuse resolved IDs within same task session
5. **Version awareness** - Use specific versions when available (/library/vX.Y.Z)
6. **Framework-specific patterns** - Always check library-specific patterns for the stack

### Error Handling

If Context7 library is not found:
- Proceed with general knowledge
- Document that library docs were unavailable
- Note in implementation for human review

### When NOT to Use Context7

- Standard language features (JavaScript, Python syntax)
- Well-established patterns (SOLID principles)
- General software engineering concepts
- Standard library functions (already in training data)

---


## Step 0 Display Banners (non-normative examples)

The active-flag display Step 0 emits after parsing (moved verbatim from the
retired imperative parser block):

**DISPLAY** active flags (if any):
```python
# TASK-BDD-FIX1: Display active mode
mode_display = {
    "standard": "STANDARD (implementation + tests together)",
    "tdd": "TDD (test-driven development: red → green → refactor)",
    "bdd": "BDD (behavior-driven: Gherkin scenarios → implementation)"
}
print(f"🎯 Development Mode: {mode_display[mode]}\n")

if design_only:
    print("🎨 Workflow Mode: DESIGN-ONLY (Phases 1-2.8)")
    print("   Task will stop at design approval checkpoint\n")
elif implement_only:
    print("🚀 Workflow Mode: IMPLEMENT-ONLY (Phases 3-5)")
    print("   Using previously approved design\n")
elif micro:
    print("⚡ Workflow Mode: MICRO-TASK (Streamlined)")
    print("   Lightweight workflow for trivial tasks\n")
else:
    print("🔄 Workflow Mode: STANDARD (All phases)")
    print("   Complete workflow with complexity-based checkpoints\n")

# TASK-POF-001: Display autobuild mode
if autobuild_mode:
    print("🤖 AutoBuild Mode: ON (--no-questions --skip-arch-review --auto-approve-checkpoint --docs=minimal)")
    print("   Optimized for autonomous execution\n")

# TASK-036: Display documentation level if explicitly set
if docs_flag:
    print(f"📄 Documentation Level: {docs_flag.upper()} (explicit override)")
    print(f"   Estimated time: {'8-12min' if docs_flag == 'minimal' else '12-18min' if docs_flag == 'standard' else '36+min'}\n")
```
