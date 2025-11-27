# Task Review

Analysis and decision-making workflows separate from implementation.

## Overview

The `/task-review` command provides a dedicated workflow for analysis tasks, separate from the implementation-focused `/task-work` command.

### When to Use

| Use `/task-review` for | Use `/task-work` for |
|------------------------|---------------------|
| "Should we implement X?" | "Implement feature X" |
| "Review architecture of X" | "Fix bug in X" |
| "Assess technical debt in X" | "Add tests for X" |
| "Security audit of X" | "Refactor X" |

## Review Modes

The `/task-review` command supports five specialized modes:

### 1. Architectural Review

**Purpose**: Evaluate system design against SOLID/DRY/YAGNI principles

**Output:**

- Architecture Assessment (scored 0-100)
- SOLID Compliance (0-10 per principle)
- DRY Adherence (0-10)
- YAGNI Compliance (0-10)
- Design Patterns Analysis
- Technical Debt Inventory
- Recommendations (Keep/Refactor/Rewrite)

### 2. Code Quality Review

**Purpose**: Assess code maintainability, complexity, test coverage

**Output:**

- Code Metrics (complexity, LOC, duplication, coverage)
- Quality Issues (code smells, anti-patterns)
- Maintainability Score (0-10)
- Refactoring Recommendations

### 3. Decision Analysis

**Purpose**: Evaluate options and provide decision recommendation

**Output:**

- Current Situation Assessment
- Root Cause Analysis (if applicable)
- Option Evaluation Matrix
- Recommended Decision with Rationale

### 4. Technical Debt Assessment

**Purpose**: Inventory and prioritize technical debt

**Output:**

- Technical Debt Inventory
- Priority Matrix (effort vs impact)
- Remediation Roadmap
- Quick Wins vs Strategic Improvements

### 5. Security Audit

**Purpose**: Security vulnerability assessment

**Output:**

- Security Findings (OWASP Top 10 mapping)
- Vulnerability Severity Ratings
- Remediation Recommendations
- Compliance Assessment (if applicable)

## Depth Levels

| Depth | Duration | Use For |
|-------|----------|---------|
| **quick** | 15-30 min | Initial assessment, sanity checks |
| **standard** | 1-2 hours | Regular reviews, architecture assessments |
| **comprehensive** | 4-6 hours | Security audits, critical decisions |

## Usage Examples

### Example 1: Architectural Review

```bash
# Create review task
/task-create "Review authentication architecture" task_type:review

# Execute architectural review
/task-review TASK-002 --mode=architectural --depth=standard

# Decision checkpoint (automated)
# [A]ccept - Approve findings, move to IN_REVIEW
# [R]evise - Request deeper analysis
# [I]mplement - Create implementation task based on recommendations
# [C]ancel - Discard review
```

### Example 2: Security Audit

```bash
# Create security audit task
/task-create "Security audit of payment processing" task_type:review

# Execute comprehensive security review
/task-review TASK-SEC-D7E2 --mode=security --depth:comprehensive

# Review identifies 12 vulnerabilities
# Choose [I]mplement to create implementation task

# Implement fixes
/task-work TASK-IMP-E8F3

# Verification review
/task-create "Verify security fixes" task_type:review
/task-review TASK-VER-F9G4 --mode=security --depth=standard
```

## Model Selection

The command automatically selects the optimal Claude model based on review mode and depth:

### When Opus 4.5 Is Used

- **Security reviews** (all depths) - Security breaches cost $100K-$10M
- **Decision analysis** (standard/comprehensive) - Complex trade-offs
- **Comprehensive architectural reviews** - Thorough analysis
- **Comprehensive technical debt** - Nuanced prioritization

**Cost**: $0.45-$1.65 per review (67% premium vs Sonnet)

### When Sonnet 4.5 Is Used

- **Quick reviews** (except security) - Speed matters
- **Code quality reviews** (all depths) - Metrics are objective
- **Standard architectural reviews** - Pattern-based analysis
- **Standard technical debt** - Straightforward prioritization

**Cost**: $0.09-$0.68 per review

## Integration with /task-work

Review tasks seamlessly integrate with implementation tasks:

**Complete Workflow:**

1. **Review** → Identify what needs to be done
2. **[I]mplement** → Creates implementation task automatically
3. **Implement** → Execute via `/task-work`
4. **Verify** → Optional verification review

**[Task Review Workflow Guide](workflows/task-review-workflow.md)** - Complete documentation.

## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review`.

**Detection Criteria** (any of the following):

1. `task_type:review` parameter
2. `decision_required:true` parameter
3. Review-related tags: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. Title keywords: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

**[Automatic Review Task Detection](https://github.com/taskwright-dev/taskwright/blob/main/installer/global/commands/task-review.md#automatic-review-task-detection)** - Full documentation.

---

## Next Steps

- **Understand**: [Task Review Workflow Guide](workflows/task-review-workflow.md)
- **Command Reference**: [task-review.md](https://github.com/taskwright-dev/taskwright/blob/main/installer/global/commands/task-review.md)
- **Try It**: Create a review task with `/task-create "Review X" task_type:review`
