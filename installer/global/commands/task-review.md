# Task Review - Structured Analysis and Decision-Making

Execute structured review and analysis workflows for tasks that require assessment, evaluation, or decision-making rather than implementation.

## Command Syntax

```bash
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT]
```

## Overview

The `/task-review` command provides a dedicated workflow for analysis and decision-making tasks, separate from the implementation-focused `/task-work` command.

**Use `/task-review` for**:
- Architectural reviews and assessments
- Code quality evaluations
- Technical decision analysis
- Technical debt assessment
- Security audits
- Root cause analysis

**Use `/task-work` for**:
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if **any** of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. **Title keywords**: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

### Suggestion Behavior

When a review task is detected during `/task-create`, you'll see:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

**Important**: The suggestion is **informational only** and doesn't block task creation. You can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### Detection Examples

**Example 1: Explicit task_type**
```bash
/task-create "Architectural review of authentication system" task_type:review
# ✅ Detected: Explicit task_type field
```

**Example 2: Decision required flag**
```bash
/task-create "Should we migrate to microservices?" decision_required:true
# ✅ Detected: Decision flag indicates review/analysis needed
```

**Example 3: Review tags**
```bash
/task-create "Code quality assessment" tags:[code-review,assessment]
# ✅ Detected: Tags indicate review task
```

**Example 4: Title keywords**
```bash
/task-create "Evaluate caching strategy options"
# ✅ Detected: "Evaluate" keyword in title
```

**Example 5: Not a review task**
```bash
/task-create "Implement user authentication"
# ❌ Not detected: Implementation task, no review indicators
# Suggestion not shown, proceeds normally
```

### Why Detection Helps

1. **Command Selection**: Helps you choose `/task-review` vs `/task-work`
2. **Workflow Efficiency**: Review tasks skip implementation phases
3. **Better Reports**: Review mode generates structured analysis reports
4. **Decision Support**: Review tasks include decision checkpoints ([A]ccept/[R]evise/[I]mplement/[C]ancel)

### Overriding Detection

If you want to use `/task-work` for a task that was detected as review:

```bash
# Task detected as review, but you want implementation workflow
/task-create "Review authentication architecture"
# [Suggestion shown]
# Choose Y to create task

# Use /task-work instead of /task-review
/task-work TASK-XXX
# Works fine, detection is only a suggestion
```

### See Also

- [task-create.md - Review Task Detection](./task-create.md#review-task-detection)
- [CLAUDE.md - Review Workflow](../../CLAUDE.md#review-vs-implementation-workflows)

## Examples

```bash
# Basic architectural review (default mode)
/task-review TASK-042

# Code quality review with comprehensive depth
/task-review TASK-043 --mode=code-quality --depth=comprehensive

# Quick decision analysis with summary output
/task-review TASK-044 --mode=decision --depth=quick --output=summary

# Security audit with detailed report
/task-review TASK-045 --mode=security --output=detailed
```

## Flags

### --mode=MODE

Specifies the type of review to perform.

**Values**:
- `architectural` (default) - Architecture and design review
- `code-quality` - Code quality and maintainability assessment
- `decision` - Technical decision analysis
- `technical-debt` - Technical debt inventory and prioritization
- `security` - Security audit and vulnerability assessment

**Examples**:
```bash
/task-review TASK-XXX --mode=architectural
/task-review TASK-XXX --mode=code-quality
/task-review TASK-XXX --mode=decision
```

### --depth=DEPTH

Controls the thoroughness of the review.

**Values**:
- `quick` - Surface-level review (15-30 minutes)
- `standard` (default) - Thorough review (1-2 hours)
- `comprehensive` - Exhaustive analysis (4-6 hours)

**Examples**:
```bash
/task-review TASK-XXX --depth=quick
/task-review TASK-XXX --depth=standard
/task-review TASK-XXX --depth=comprehensive
```

### --output=FORMAT

Specifies the output format for the review report.

**Values**:
- `summary` - Executive summary only
- `detailed` (default) - Full analysis report
- `presentation` - Presentation/slide deck format

**Examples**:
```bash
/task-review TASK-XXX --output=summary
/task-review TASK-XXX --output=detailed
/task-review TASK-XXX --output=presentation
```

## Workflow Phases

The `/task-review` command executes these phases automatically:

### Phase 1: Load Review Context
- Read task description and acceptance criteria
- Identify review scope and objectives
- Load relevant codebase files/modules
- Load related design documents and ADRs

### Phase 2: Execute Review Analysis
- Invoke appropriate review agents based on mode
- Perform analysis using specialized prompts
- Generate findings with supporting evidence
- Score/rate based on review criteria

### Phase 3: Synthesize Recommendations
- Aggregate findings from multiple agents (if applicable)
- Generate actionable recommendations
- Identify decision options (for decision-making tasks)
- Prioritize recommendations by impact

### Phase 4: Generate Review Report
- Create structured markdown report
- Include executive summary
- Document findings with evidence
- Provide recommendations with rationale
- Attach supporting artifacts (diagrams, metrics)

### Phase 5: Human Decision Checkpoint
Present findings to user with decision options:
- **[A]ccept** - Approve findings, mark task as `REVIEW_COMPLETE`
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation task based on recommendation
- **[C]ancel** - Discard review, return task to backlog

## Model Selection Strategy

The `/task-review` command automatically selects the optimal Claude model based on review mode and depth, balancing cost efficiency with quality requirements.

### When Opus 4.5 Is Used

**Opus 4.5** provides superior reasoning for high-value scenarios:

1. **Security reviews** (all depths) - Security breaches cost $100K-$10M, model costs $1-5
2. **Decision analysis** (standard/comprehensive) - Complex trade-offs require deep reasoning
3. **Comprehensive architectural reviews** - Thorough SOLID/DRY/YAGNI analysis
4. **Comprehensive technical debt** - Nuanced effort vs impact prioritization

**Cost**: $0.45-$1.65 per review (67% premium vs Sonnet)

### When Sonnet 4.5 Is Used

**Sonnet 4.5** provides excellent quality for most scenarios:

1. **Quick reviews** (except security) - Speed matters
2. **Code quality reviews** (all depths) - Metrics are objective
3. **Standard architectural reviews** - Pattern-based analysis sufficient
4. **Standard technical debt** - Straightforward prioritization

**Cost**: $0.09-$0.68 per review

### Cost Transparency

Before each review, you'll see:
```
======================================================================
📊 Review Cost Estimate
======================================================================
Model: claude-opus-4-20250514
Estimated tokens: 150,000
Estimated cost: $1.13
Rationale: comprehensive depth requires deep analysis,
           security reviews always use Opus 4.5
======================================================================
```

This ensures you always know which model will be used and why.

## Review Modes (Detailed)

### Architectural Review Mode

**Purpose**: Evaluate system design against SOLID/DRY/YAGNI principles

**Agents Used**:
- `architectural-reviewer` (primary)
- `pattern-advisor` (if Design Patterns MCP available)
- `software-architect` (for recommendations)

**Output Sections**:
1. Architecture Assessment (scored 0-100)
   - SOLID Compliance (0-10 per principle)
   - DRY Adherence (0-10)
   - YAGNI Compliance (0-10)
2. Design Patterns Analysis
3. Technical Debt Inventory
4. Recommendations (Keep/Refactor/Rewrite)

### Code Quality Review Mode

**Purpose**: Assess code maintainability, complexity, test coverage

**Agents Used**:
- `code-reviewer` (primary)
- `test-orchestrator` (for coverage analysis)

**Output Sections**:
1. Code Metrics (complexity, LOC, duplication, coverage)
2. Quality Issues (code smells, anti-patterns)
3. Maintainability Score (0-10)
4. Refactoring Recommendations

### Decision Analysis Mode

**Purpose**: Evaluate options and provide decision recommendation

**Agents Used**:
- `software-architect` (primary)
- `architectural-reviewer` (for technical assessment)
- Stack-specific specialists (for implementation details)

**Output Sections**:
1. Current Situation Assessment
2. Root Cause Analysis (if applicable)
3. Option Evaluation Matrix
4. Recommended Decision with Rationale

### Technical Debt Mode

**Purpose**: Inventory and prioritize technical debt

**Agents Used**:
- `code-reviewer` (primary)
- `architectural-reviewer` (for architectural debt)

**Output Sections**:
1. Technical Debt Inventory
2. Priority Matrix (effort vs impact)
3. Remediation Roadmap
4. Quick Wins vs Strategic Improvements

### Security Audit Mode

**Purpose**: Security vulnerability assessment

**Agents Used**:
- `security-specialist` (primary)
- `code-reviewer` (for code-level issues)

**Output Sections**:
1. Security Findings (OWASP Top 10 mapping)
2. Vulnerability Severity Ratings
3. Remediation Recommendations
4. Compliance Assessment (if applicable)

## Task States and Transitions

```
BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → Completed/Implemented
              ↓
           BLOCKED
```

**States**:
- `BACKLOG`: Review task not started
- `IN_PROGRESS`: Review in progress
- `REVIEW_COMPLETE`: Review finished, awaiting human decision
- `BLOCKED`: Review cannot proceed (missing context, access issues)

**After Review**:
- Accept findings → Task archived as completed
- Create implementation task → New task in backlog linked to review

## Task Metadata

Review tasks use extended metadata fields:

```yaml
---
id: TASK-XXX
title: Review authentication architecture
status: in_progress
task_type: review                    # NEW: review | implementation | research | docs
review_mode: architectural           # NEW: architectural | code-quality | decision | etc.
review_depth: standard               # NEW: quick | standard | comprehensive
priority: high
tags: [architecture, security]
---
```

After review completion:

```yaml
---
id: TASK-XXX
status: review_complete
review_results:                      # NEW: Added after review
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
---
```

## Integration with Task States

### Creating Review Tasks

```bash
# Create review task
/task-create "Review authentication architecture" task_type:review

# Task created with task_type=review in frontmatter
```

### Executing Review

```bash
# Execute review (automatically detects task_type=review)
/task-review TASK-XXX --mode=architectural

# Review runs, generates report, updates task metadata
```

### Post-Review Actions

**Option 1: Accept findings (archive task)**
```bash
# User chooses [A]ccept at checkpoint
# Task moved to completed, report archived
```

**Option 2: Create implementation task**
```bash
# User chooses [I]mplement at checkpoint
# New task created in backlog:
# /task-create "Refactor authentication based on TASK-XXX findings" related_to:TASK-XXX
```

**Option 3: Revise review**
```bash
# User chooses [R]evise at checkpoint
# Review re-runs with additional focus areas
/task-review TASK-XXX --mode=architectural --depth=comprehensive
```

## Execution Protocol

### Prerequisites
1. Task must exist in `tasks/` directory
2. Task must have `task_type: review` in frontmatter (optional, defaults to review)
3. Review scope must be defined in task description

### Validation
- Validates `--mode` against allowed values
- Validates `--depth` against allowed values
- Validates `--output` against allowed values
- Checks task exists and is accessible

### Error Handling

**Common Errors**:

```bash
# Invalid review mode
❌ Error: Invalid review mode 'invalid-mode'
   Allowed: architectural, code-quality, decision, technical-debt, security

# Task not found
❌ Error: Task TASK-XXX not found in any task directory

# Missing review scope
❌ Error: Task TASK-XXX missing review scope in description
   Add "Review Scope" section to task description

# Insufficient context
⚠️  Warning: Review scope references non-existent files
   Proceeding with available context
```

## Output Files

### Review Report
**Location**: `.claude/reviews/TASK-XXX-review-report.md`

**Format**:
```markdown
# Review Report: TASK-XXX

## Executive Summary
[Brief overview of findings and recommendations]

## Review Details
- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: 1.5 hours
- **Reviewer**: architectural-reviewer agent

## Findings
1. [Finding 1 with evidence]
2. [Finding 2 with evidence]
...

## Recommendations
1. [Recommendation 1 with rationale]
2. [Recommendation 2 with rationale]
...

## Decision Matrix
| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| ... | ... | ... | ... | ... |

## Appendix
- Supporting diagrams
- Code samples
- Metrics
```

### Task Metadata Update
**Location**: Task file frontmatter

**Added Fields**:
```yaml
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
  completed_at: 2025-01-20T16:30:00Z
```

## Best Practices

### When to Use `/task-review`

**Use for**:
- ✅ "Should we implement X?" (decision analysis)
- ✅ "Review the architecture of X" (architectural review)
- ✅ "Assess code quality of X" (code quality review)
- ✅ "Identify technical debt in X" (technical debt assessment)
- ✅ "Audit security of X" (security audit)

**Don't use for**:
- ❌ "Implement feature X" (use `/task-work`)
- ❌ "Fix bug in X" (use `/task-work`)
- ❌ "Refactor X" (use `/task-work`)

### Review Depth Selection

**Quick** (15-30 min):
- Initial assessment
- Sanity check before major work
- High-level overview for stakeholders

**Standard** (1-2 hours):
- Regular code reviews
- Architecture assessments
- Decision analysis for medium complexity

**Comprehensive** (4-6 hours):
- Security audits
- Critical architectural decisions
- Large-scale refactoring planning
- Compliance assessments

### Output Format Selection

**Summary**:
- Executive presentations
- Quick decision-making
- Stakeholder communication

**Detailed**:
- Technical team consumption
- Implementation planning
- Audit trail

**Presentation**:
- Architecture reviews with stakeholders
- Decision presentations
- Training materials

## Advanced Usage

### Chaining Reviews and Implementation

```bash
# 1. Architectural review
/task-review TASK-001 --mode=architectural

# 2. Based on findings, create implementation task
/task-create "Refactor auth based on TASK-001" related_to:TASK-001

# 3. Implement refactoring
/task-work TASK-002

# 4. Post-implementation review
/task-review TASK-003 --mode=code-quality
```

### Iterative Review Refinement

```bash
# 1. Quick initial assessment
/task-review TASK-XXX --depth=quick

# 2. Based on findings, go deeper
/task-review TASK-XXX --depth=comprehensive --focus="authentication layer"
```

## Notes

**Phase 1 Implementation** (Current):
- Core orchestrator structure (Phases 1-5 skeleton)
- Command specification (this file)
- State management (`REVIEW_COMPLETE` state)
- Metadata schema (task_type, review_mode, review_depth)

**Future Phases** (Upcoming):
- Phase 2: Review mode implementations
- Phase 3: Report generation templates
- Phase 4: Integration with task-create
- Phase 5: Comprehensive testing
