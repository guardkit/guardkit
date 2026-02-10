# Feature-Plan Command Reference

**Command**: `/feature-plan`
**Version**: 2.0
**Last Updated**: 2025-02-10

## Overview

The `/feature-plan` command orchestrates feature planning by combining task creation and review analysis into a single workflow. It automatically creates a review task, executes decision-making analysis, and optionally creates implementation tasks from recommendations.

## Command Syntax

```bash
/feature-plan "feature description" [flags]
```

## Available Flags

### Core Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--context path/to/file.md` | Explicitly specify context files (can be used multiple times) | Auto-detect |
| `--no-questions` | Skip all clarification (review scope + implementation prefs) | Off |
| `--with-questions` | Force clarification even for simple features | Off |
| `--defaults` | Use clarification defaults throughout workflow | Off |
| `--answers="..."` | Inline answers (propagated to task-review and subtask creation) | None |
| `--no-structured` | Disable structured YAML feature file output | Enabled by default |

### Research-to-Implementation Flags (FEAT-FP-002)

| Flag | Description | Default |
|------|-------------|---------|
| `--from-spec path/to/spec.md` | Parse Research-to-Implementation Template | None |
| `--target interactive\|local-model\|auto` | Set output verbosity for target executor | `interactive` |
| `--generate-adrs` | Generate ADR files from Decision Log | Off |
| `--generate-quality-gates` | Generate per-feature quality gate YAML | Off |

## Flag Details

### --from-spec

**Purpose**: Parse a Research-to-Implementation Template and generate tasks directly, bypassing the standard review flow.

**Syntax**:
```bash
/feature-plan --from-spec path/to/spec.md
```

**Behavior**:
1. Reads the Research-to-Implementation Template from the given path
2. Parses tasks, decisions, warnings, and quality gates
3. Generates task files in `tasks/design_approved/` state
4. Optionally generates ADRs, quality gates, and seed scripts

**Example**:
```bash
# Parse a feature specification
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md

# With target optimization
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md --target local-model

# With all optional outputs
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md \
              --target interactive \
              --generate-adrs \
              --generate-quality-gates
```

**Template Requirements**:
The Research-to-Implementation Template must contain:
- Task list with acceptance criteria
- Decision log entries
- Warnings and risks (optional)
- Quality gate definitions (optional)

### --target

**Purpose**: Set output verbosity based on the intended executor (human or AI model).

**Syntax**:
```bash
/feature-plan --from-spec path/to/spec.md --target <target>
```

**Target Values**:

| Target | Verbosity | Best For | Description |
|--------|-----------|----------|-------------|
| `interactive` | Full | Human execution | Complete detail with explanations, rationale, and context |
| `local-model` | Optimized | Claude-level models | Balanced detail optimized for AI consumption |
| `auto` | Minimal | Autonomous systems | Minimal detail for fully autonomous execution |

**Output Format Comparison**:

#### Interactive Target Output

Interactive mode produces full documentation suitable for human developers:

```markdown
# TASK-FP002-001: Create Project Structure

## Description
Initialize the project with proper directory structure, configuration files,
and development tooling.

## Rationale
A well-organized project structure is essential for maintainability and
allows multiple developers to work efficiently...

## Acceptance Criteria
- [ ] pyproject.toml created with all dependencies
- [ ] src/ directory structure matches specification
- [ ] Development tools (ruff, mypy, pytest) configured

## Implementation Notes
- Use Poetry for dependency management
- Follow src-layout for package structure
- Include type stubs for external dependencies
...
```

#### Local-Model Target Output

Local-model mode produces optimized output for AI execution:

```markdown
# TASK-FP002-001: Create Project Structure

## Acceptance Criteria
- [ ] pyproject.toml created with all dependencies
- [ ] src/ directory structure matches specification
- [ ] Development tools configured

## Files
- pyproject.toml
- src/__init__.py
- tests/conftest.py

## Coach Validation
```bash
python -c "import toml; toml.load('pyproject.toml')"
pytest --collect-only
```
```

### Task Metadata Fields (Local-Model Mode)

When using `--target local-model`, task files include optimized frontmatter:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Task identifier (e.g., `TASK-FP002-001`) |
| `title` | string | Concise task title |
| `complexity` | int | Complexity score 1-10 |
| `dependencies` | list | List of task IDs this task depends on |
| `feature_id` | string | Parent feature identifier |
| `implementation_mode` | string | `task-work` or `direct` |
| `wave` | int | Parallel execution wave number |
| `turn_budget` | object | Expected/max agent turns |
| `files_to_create` | list | Files this task will create |
| `files_to_modify` | list | Files this task will modify |
| `files_not_to_touch` | list | Files explicitly off-limits |
| `graphiti_context_budget` | int | Token budget for Graphiti queries |
| `domain_tags` | list | Domain categories for context |
| `relevant_decisions` | list | Decision IDs from spec |

**Example Frontmatter (Local-Model)**:
```yaml
---
id: TASK-FP002-003
title: Implement Spec Parser Module
complexity: 6
dependencies:
  - TASK-FP002-001
  - TASK-FP002-002
feature_id: FEAT-FP-002
implementation_mode: task-work
wave: 2
turn_budget:
  expected: 3
  max: 5
files_to_create:
  - guardkit/planning/spec_parser.py
  - tests/test_spec_parser.py
files_to_modify: []
files_not_to_touch:
  - guardkit/cli/main.py
graphiti_context_budget: 2000
domain_tags:
  - parsing
  - planning
relevant_decisions:
  - D1
  - D3
---
```

### --generate-adrs

**Purpose**: Generate Architecture Decision Record (ADR) files from the Decision Log in the specification.

**Syntax**:
```bash
/feature-plan --from-spec path/to/spec.md --generate-adrs
```

**Behavior**:
- Parses Decision Log entries from the specification
- Creates ADR files in `.guardkit/adrs/`
- Uses standard ADR format (Context, Decision, Consequences)
- Naming: `ADR-{feature_id}-{decision_number}-{slug}.md`

**Example Output**:
```
✅ Created .guardkit/adrs/ADR-FP002-001-use-pydantic-for-schemas.md
✅ Created .guardkit/adrs/ADR-FP002-002-markdown-plus-json-output.md
✅ Created .guardkit/adrs/ADR-FP002-003-design-approved-state.md
```

**ADR File Structure**:
```markdown
# ADR-FP002-001: Use Pydantic for Schema Validation

## Status
Accepted

## Context
The spec parser needs to validate complex nested structures...

## Decision
Use Pydantic v2 models for all schema definitions...

## Consequences
### Positive
- Type-safe validation at runtime
- Automatic JSON serialization

### Negative
- Additional dependency
- Learning curve for team
```

### --generate-quality-gates

**Purpose**: Generate per-feature quality gate configuration in YAML format.

**Syntax**:
```bash
/feature-plan --from-spec path/to/spec.md --generate-quality-gates
```

**Behavior**:
- Extracts quality gate definitions from specification
- Creates YAML configuration in `.guardkit/quality-gates/`
- Defines per-task thresholds and validation commands
- Enables task-type-specific quality profiles

**Example Output**:
```
✅ Created .guardkit/quality-gates/FEAT-FP002.yaml
```

**Quality Gate File Structure**:
```yaml
# .guardkit/quality-gates/FEAT-FP002.yaml
feature_id: FEAT-FP002
version: "1.0"
created: "2025-02-10T12:00:00Z"

defaults:
  coverage_threshold: 80
  branch_coverage: 75
  architectural_review: true
  complexity_threshold: 10

task_overrides:
  TASK-FP002-001:
    task_type: scaffolding
    architectural_review: false
    coverage_threshold: 0

  TASK-FP002-002:
    task_type: feature
    coverage_threshold: 85

  TASK-FP002-009:
    task_type: documentation
    coverage_threshold: 0
    architectural_review: false

validation_commands:
  python:
    lint: "ruff check ."
    type_check: "mypy src/"
    test: "pytest tests/ --cov=src --cov-report=json"
```

### --context

**Purpose**: Explicitly specify context files when auto-detection isn't sufficient.

**Syntax**:
```bash
/feature-plan "description" --context path/to/file.md
/feature-plan "description" --context file1.md --context file2.md
```

**Behavior**:
- Loads specified files before analysis
- Works alongside auto-detection (explicit files loaded first)
- Supports multiple `--context` flags

**Example**:
```bash
# Single context file
/feature-plan "implement OAuth" --context docs/auth-design.md

# Multiple context files
/feature-plan "add API" --context docs/api-spec.md --context docs/security-requirements.md
```

### --no-questions, --with-questions, --defaults, --answers

**Purpose**: Control clarification behavior during planning.

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip all clarification prompts |
| `--with-questions` | Force clarification even for simple features |
| `--defaults` | Use defaults without prompting |
| `--answers="..."` | Provide inline answers for automation |

**Example (CI/CD automation)**:
```bash
/feature-plan "add caching" --answers="focus:technical tradeoff:speed approach:1 execution:sequential testing:minimal"
```

### --no-structured

**Purpose**: Disable structured YAML feature file generation.

**Default Behavior**:
By default, `/feature-plan` generates both:
1. Task markdown files in `tasks/backlog/{feature-slug}/`
2. Structured YAML file in `.guardkit/features/FEAT-XXX.yaml`

**With --no-structured**:
Only task markdown files are created, skipping the YAML generation.

**Example**:
```bash
# Default (both markdown and YAML)
/feature-plan "add OAuth2 authentication"

# Markdown only (skip YAML)
/feature-plan "add OAuth2 authentication" --no-structured
```

## Complete Examples

### Example 1: Standard Feature Planning

```bash
/feature-plan "implement dark mode"
```

Creates:
- Review task: `TASK-REV-xxxx`
- After [I]mplement decision:
  - `tasks/backlog/dark-mode/TASK-DM-001.md`
  - `tasks/backlog/dark-mode/IMPLEMENTATION-GUIDE.md`
  - `.guardkit/features/FEAT-xxxx.yaml`

### Example 2: From Research Specification

```bash
/feature-plan --from-spec docs/research/FEAT-GR-003-spec.md \
              --target local-model \
              --generate-adrs \
              --generate-quality-gates
```

Creates:
- `tasks/design_approved/TASK-GR003-001.md`
- `tasks/design_approved/TASK-GR003-002.md`
- `.guardkit/adrs/ADR-GR003-001-*.md`
- `.guardkit/quality-gates/FEAT-GR003.yaml`
- `.guardkit/warnings/FEAT-GR003.md` (if warnings exist)
- `.guardkit/seed/FEAT-GR003-seed.sh`

### Example 3: Automated Pipeline

```bash
/feature-plan "add user notifications" \
              --no-questions \
              --answers="focus:all tradeoff:balanced approach:1 execution:parallel testing:standard"
```

Runs complete flow with predetermined answers for CI/CD integration.

### Example 4: Context-Rich Planning

```bash
/feature-plan "implement FEAT-AUTH-001" \
              --context docs/features/FEAT-AUTH-001-spec.md \
              --context docs/security-requirements.md \
              --with-questions
```

Loads explicit context and forces clarification prompts.

## Output Summary

### Standard Flow Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: implement dark mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Creating review task...
✅ Task created: TASK-REV-A3F2

Step 2: Analyzing technical options...
[Analysis output]

Step 3: Decision checkpoint
[A/R/I/C options]

Step 4: Creating implementation structure...
✅ Feature folder created
✅ 5 subtasks generated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### From-Spec Flow Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: From Research-to-Implementation Template
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Parsing spec file...
✅ Spec parsed: 5 tasks, 3 decisions, 2 warnings

Step 2: Resolving target configuration...
✅ Target: local-model (optimized verbosity)

Step 3: Enriching tasks...
✅ Enriched 5 tasks with target-specific details

Step 4: Rendering task files...
✅ Created tasks/design_approved/TASK-FP002-001.md
[...]

Step 5: Generating ADRs...
✅ Created 3 ADR files

Step 6: Generating quality gates...
✅ Created .guardkit/quality-gates/FEAT-FP002.yaml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Tasks: 5 (in design_approved state)
📁 ADRs: 3
⚠️  Warnings: 2
🔒 Quality gates: Configured

Next steps:
  1. Review tasks in tasks/design_approved/
  2. Run seed script: bash .guardkit/seed/FEAT-FP002-seed.sh
  3. Begin implementation: /task-work TASK-FP002-001 --implement-only
```

## Related Commands

| Command | Purpose |
|---------|---------|
| `/task-create` | Create individual tasks |
| `/task-review` | Run review on existing tasks |
| `/task-work` | Implement tasks |
| `/feature-build` | Autonomous feature implementation |
| `/feature-complete` | Complete and verify features |

## See Also

- [Task Workflow Guide](../guides/task-workflow-guide.md)
- [AutoBuild Documentation](../../.claude/rules/autobuild.md)
- [Research-to-Implementation Template](../templates/research-to-implementation.md)
