# Task Review Workflow

## Overview

The `/task-review` command provides structured analysis and decision-making workflows for review tasks that require assessment, evaluation, or decision-making rather than implementation.

**Purpose**: Separate review/analysis work from implementation work to:
- Provide specialized review tools and agents
- Generate structured review reports
- Enable decision-making checkpoints
- Track review outcomes separately from code changes

## When to Use Task Review

### Use `/task-review` for:
- ✅ Architectural reviews and assessments
- ✅ Code quality evaluations
- ✅ Technical decision analysis
- ✅ Technical debt assessment
- ✅ Security audits
- ✅ Root cause analysis
- ✅ "Should we implement X?" questions

### Use `/task-work` for:
- ❌ Feature implementation
- ❌ Bug fixes
- ❌ Refactoring
- ❌ Test creation
- ❌ "Implement feature X" tasks

## Workflow Steps

### Step 1: Create Review Task

```bash
/task-create "Architectural review of authentication" task_type:review
```

**Task Creation Hints:**

The system automatically detects review tasks based on:
1. **Explicit type**: `task_type:review` parameter
2. **Decision flag**: `decision_required:true` parameter
3. **Review tags**: architecture-review, code-review, decision-point, assessment
4. **Title keywords**: review, analyze, evaluate, assess, audit, investigation

When detected, the system displays:
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
```

**Task Metadata:**
```yaml
---
id: TASK-REV-A3F2
title: Review authentication architecture
status: backlog
task_type: review              # NEW: Indicates review task
priority: high
tags: [architecture, security]
---
```

### Step 2: Execute Review

```bash
/task-review TASK-REV-A3F2 --mode=architectural --depth=standard
```

**Available Modes:**
- `architectural` (default) - Architecture and design review
- `code-quality` - Code quality and maintainability assessment
- `decision` - Technical decision analysis
- `technical-debt` - Technical debt inventory and prioritization
- `security` - Security audit and vulnerability assessment

**Available Depths:**
- `quick` (15-30 min) - Surface-level review
- `standard` (1-2 hours) - Thorough review (default)
- `comprehensive` (4-6 hours) - Exhaustive analysis

### Step 3: Review Phases (Automatic)

The `/task-review` command executes these phases automatically:

#### Phase 1: Load Review Context
- Read task description and acceptance criteria
- Identify review scope and objectives
- Load relevant codebase files/modules
- Load related design documents and ADRs

**Example Output:**
```
📋 Loading Review Context
  Task: TASK-REV-A3F2
  Mode: architectural
  Depth: standard
  Scope: src/auth/ directory (15 files)
```

#### Phase 2: Execute Review Analysis
- Invoke appropriate review agents based on mode
- Perform analysis using specialized prompts
- Generate findings with supporting evidence
- Score/rate based on review criteria

**Agents by Mode:**

| Mode | Primary Agent | Supporting Agents |
|------|--------------|-------------------|
| architectural | architectural-reviewer | pattern-advisor, software-architect |
| code-quality | code-reviewer | test-orchestrator |
| decision | software-architect | architectural-reviewer, stack specialists |
| technical-debt | code-reviewer | architectural-reviewer |
| security | security-specialist | code-reviewer |

**Example Output:**
```
🔍 Executing Architectural Review
  Agent: architectural-reviewer
  Analyzing: SOLID principles, DRY adherence, YAGNI compliance
  Progress: [████████████████░░] 80% (12/15 files)
```

#### Phase 3: Synthesize Recommendations
- Aggregate findings from multiple agents
- Generate actionable recommendations
- Identify decision options (for decision-making tasks)
- Prioritize recommendations by impact

**Example Output:**
```
📊 Synthesizing Findings
  Findings: 8 issues identified
  Recommendations: 5 action items
  Decision options: 3 (Keep, Refactor, Rewrite)
```

#### Phase 4: Generate Review Report
- Create structured markdown report
- Include executive summary
- Document findings with evidence
- Provide recommendations with rationale
- Attach supporting artifacts

**Report Location:** `.claude/reviews/TASK-REV-A3F2-review-report.md`

**Report Structure:**
```markdown
# Review Report: TASK-REV-A3F2

## Executive Summary
[Brief overview of findings and recommendations]

## Review Details
- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: 1.5 hours
- **Reviewer**: architectural-reviewer agent

## Findings
1. **Violation of Single Responsibility Principle**
   - Location: src/auth/AuthService.ts:45-120
   - Evidence: Class handles authentication, authorization, and session management
   - Severity: Medium
   - Impact: Maintainability

2. [Additional findings...]

## Recommendations
1. **Refactor AuthService into separate concerns**
   - Effort: 4 hours
   - Impact: High
   - Risk: Low
   - Rationale: Improves maintainability and testability

2. [Additional recommendations...]

## Decision Matrix
| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| Keep as-is | 6/10 | 0h | High | Not recommended |
| Refactor | 9/10 | 8h | Low | ✅ Recommended |
| Rewrite | 7/10 | 24h | Medium | Only if adding features |

## Appendix
- Architecture diagram
- Code metrics
- SOLID scoring breakdown
```

#### Phase 5: Human Decision Checkpoint

Present findings to user with decision options:

```
=========================================================================
REVIEW COMPLETE - TASK-REV-A3F2
=========================================================================

Review Report: .claude/reviews/TASK-REV-A3F2-review-report.md

FINDINGS SUMMARY:
  Score: 72/100 (Acceptable with improvements)
  Issues: 8 identified
  Recommendations: 5 action items
  Decision: Refactor (recommended)

DECISION OPTIONS:

[A] Accept
    - Approve findings and recommendations
    - Move task to COMPLETED
    - Archive review report

[R] Revise
    - Request deeper analysis on specific areas
    - Re-run review with additional focus
    - Useful for: "Need more detail on security implications"

[I] Implement
    - Create implementation task based on recommendations
    - New task links to this review
    - Automatically populate acceptance criteria from recommendations

[C] Cancel
    - Discard review
    - Return task to BACKLOG
    - Review report is saved but not acted upon

Your choice [A/R/I/C]:
```

### Step 4: Make Decision

#### Option A: Accept Findings
```bash
# User chooses [A]
# System actions:
# - Task moved to completed/
# - Review report archived
# - Task metadata updated with review results
```

**Task Update:**
```yaml
---
status: completed
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: accepted
  report_path: .claude/reviews/TASK-REV-A3F2-review-report.md
  completed_at: 2025-01-20T16:30:00Z
---
```

#### Option R: Revise Review
```bash
# User chooses [R]
# System prompts for focus areas
Enter focus areas (comma-separated): security implications, performance impact

# Re-run review with additional depth
/task-review TASK-REV-A3F2 --mode=architectural --depth=comprehensive --focus="security,performance"
```

#### Option I: Implement Recommendations
```bash
# User chooses [I]
# System creates new implementation task

Creating implementation task based on review findings...

✅ Task Created: TASK-IMP-B4D1

📋 Task Details
Title: Refactor AuthService based on TASK-REV-A3F2 findings
Related Review: TASK-REV-A3F2
Priority: high
Status: backlog

📑 Acceptance Criteria (from review):
- [ ] Split AuthService into AuthenticationService, AuthorizationService, SessionService
- [ ] Maintain backward compatibility with existing API
- [ ] Achieve 90%+ test coverage
- [ ] Update architecture documentation
- [ ] Verify no performance regression

Next Steps:
1. Review implementation task: tasks/backlog/TASK-IMP-B4D1.md
2. When ready: /task-work TASK-IMP-B4D1
```

#### Option C: Cancel Review
```bash
# User chooses [C]
# System actions:
# - Task moved to backlog/
# - Review report saved but marked as discarded
# - Can be re-reviewed later
```

### Step 5: Optional Implementation

If implementation task was created ([I] option chosen):

```bash
/task-work TASK-IMP-B4D1
```

**Implementation task benefits:**
- Pre-populated acceptance criteria from review
- Linked to review report for context
- Priority inherited from review task
- Architecture already validated

### Step 6: Complete Review Task

```bash
/task-complete TASK-REV-A3F2
```

**Completion actions:**
- Archives task to `completed/`
- Preserves review report
- Updates task metadata
- Links to implementation task (if created)

## Review Modes (Detailed)

### 1. Architectural Review Mode

**Purpose:** Evaluate system design against SOLID/DRY/YAGNI principles

**Command:**
```bash
/task-review TASK-XXX --mode=architectural
```

**Agents:**
- `architectural-reviewer` (primary)
- `pattern-advisor` (if Design Patterns MCP available)
- `software-architect` (for recommendations)

**Output Sections:**
1. **Architecture Assessment** (scored 0-100)
   - SOLID Compliance (0-10 per principle)
   - DRY Adherence (0-10)
   - YAGNI Compliance (0-10)
2. **Design Patterns Analysis**
3. **Technical Debt Inventory**
4. **Recommendations** (Keep/Refactor/Rewrite)

**Scoring:**
- 90-100: Excellent architecture
- 70-89: Good with minor improvements
- 60-69: Acceptable with improvements needed
- Below 60: Significant refactoring recommended

### 2. Code Quality Review Mode

**Purpose:** Assess code maintainability, complexity, test coverage

**Command:**
```bash
/task-review TASK-XXX --mode=code-quality
```

**Agents:**
- `code-reviewer` (primary)
- `test-orchestrator` (for coverage analysis)

**Output Sections:**
1. **Code Metrics**
   - Cyclomatic complexity
   - Lines of code (LOC)
   - Code duplication percentage
   - Test coverage (line/branch)
2. **Quality Issues**
   - Code smells
   - Anti-patterns
   - Naming conventions
3. **Maintainability Score** (0-10)
4. **Refactoring Recommendations**

**Example Findings:**
```markdown
## Code Quality Issues

1. High Cyclomatic Complexity
   - Function: processPayment() at src/payment/processor.ts:145
   - Complexity: 23 (threshold: 10)
   - Recommendation: Extract payment validation and error handling

2. Code Duplication
   - Files: src/auth/login.ts, src/auth/register.ts
   - Duplication: 45 lines (32%)
   - Recommendation: Extract shared validation logic
```

### 3. Decision Analysis Mode

**Purpose:** Evaluate options and provide decision recommendation

**Command:**
```bash
/task-review TASK-XXX --mode=decision
```

**Agents:**
- `software-architect` (primary)
- `architectural-reviewer` (for technical assessment)
- Stack-specific specialists (for implementation details)

**Output Sections:**
1. **Current Situation Assessment**
2. **Root Cause Analysis** (if applicable)
3. **Option Evaluation Matrix**
4. **Recommended Decision with Rationale**

**Decision Matrix Example:**
```markdown
## Option Evaluation

### Option 1: Migrate to Microservices
- **Pros:** Better scalability, technology flexibility, team autonomy
- **Cons:** Increased complexity, operational overhead, data consistency challenges
- **Effort:** 6-12 months
- **Risk:** High
- **Score:** 7/10

### Option 2: Modularize Monolith
- **Pros:** Lower risk, incremental migration, maintains simplicity
- **Cons:** Limited scalability, shared deployment
- **Effort:** 2-4 months
- **Risk:** Low
- **Score:** 9/10 ✅ Recommended

### Option 3: Keep Current Architecture
- **Pros:** Zero cost, no risk
- **Cons:** Scalability issues persist, team friction continues
- **Effort:** 0 months
- **Risk:** None (technical debt accumulates)
- **Score:** 4/10
```

### 4. Technical Debt Mode

**Purpose:** Inventory and prioritize technical debt

**Command:**
```bash
/task-review TASK-XXX --mode=technical-debt
```

**Agents:**
- `code-reviewer` (primary)
- `architectural-reviewer` (for architectural debt)

**Output Sections:**
1. **Technical Debt Inventory**
   - Code debt (duplication, complexity, outdated patterns)
   - Architectural debt (coupling, cohesion, scalability)
   - Test debt (coverage gaps, flaky tests)
   - Documentation debt (missing, outdated)
2. **Priority Matrix** (effort vs impact)
3. **Remediation Roadmap**
4. **Quick Wins vs Strategic Improvements**

**Debt Prioritization:**
```markdown
## Technical Debt Priority Matrix

### Quick Wins (Low Effort, High Impact)
1. ✅ Extract duplicated validation logic (2h, High impact)
2. ✅ Add missing error handling (3h, High impact)
3. ✅ Update outdated dependencies (1h, Medium impact)

### Strategic Improvements (High Effort, High Impact)
1. 🔄 Refactor authentication system (40h, High impact)
2. 🔄 Implement caching layer (24h, High impact)
3. 🔄 Migrate to TypeScript (80h, Very high impact)

### Defer (Low Impact)
1. ⏸️ Rename variables for consistency (8h, Low impact)
2. ⏸️ Consolidate config files (4h, Low impact)
```

### 5. Security Audit Mode

**Purpose:** Security vulnerability assessment

**Command:**
```bash
/task-review TASK-XXX --mode=security
```

**Agents:**
- `security-specialist` (primary)
- `code-reviewer` (for code-level issues)

**Output Sections:**
1. **Security Findings** (OWASP Top 10 mapping)
2. **Vulnerability Severity Ratings**
3. **Remediation Recommendations**
4. **Compliance Assessment** (if applicable)

**Example Security Report:**
```markdown
## Security Findings

### Critical Vulnerabilities (Fix Immediately)
1. **SQL Injection Risk**
   - Location: src/api/users.ts:78
   - OWASP: A03:2021 - Injection
   - Evidence: Direct string concatenation in SQL query
   - Remediation: Use parameterized queries
   - Effort: 2h

### High Severity
2. **Missing Authentication**
   - Location: src/api/admin.ts
   - OWASP: A01:2021 - Broken Access Control
   - Evidence: Admin endpoints lack authentication middleware
   - Remediation: Add authentication middleware
   - Effort: 4h

### Medium Severity
3. **Weak Password Policy**
   - Location: src/auth/registration.ts
   - OWASP: A07:2021 - Identification and Authentication Failures
   - Evidence: Minimum 6 characters, no complexity requirements
   - Remediation: Implement NIST password guidelines
   - Effort: 6h
```

## Review Depth Levels

### Quick (15-30 minutes)

**Use for:**
- Initial assessment before major work
- Sanity check on proposed approach
- High-level overview for stakeholders

**Limitations:**
- Surface-level analysis only
- May miss deeper architectural issues
- Not suitable for compliance or security audits

**Example:**
```bash
/task-review TASK-XXX --mode=architectural --depth=quick

# Output:
Quick Architectural Review (20 minutes)
- SOLID Score: 7/10 (Good)
- Major Issues: 2 identified
- Recommendation: Proceed with caution
```

### Standard (1-2 hours)

**Use for:**
- Regular code reviews
- Architecture assessments
- Decision analysis for medium complexity
- Most review tasks (default)

**Coverage:**
- Thorough analysis of identified scope
- Pattern detection
- Evidence-based recommendations
- Structured report

**Example:**
```bash
/task-review TASK-XXX --mode=code-quality --depth=standard

# Output:
Standard Code Quality Review (1.5 hours)
- Files Analyzed: 15
- Issues Found: 12
- Code Smells: 8
- Recommendations: 6
- Maintainability: 7.5/10
```

### Comprehensive (4-6 hours)

**Use for:**
- Security audits
- Critical architectural decisions
- Large-scale refactoring planning
- Compliance assessments
- Production incident root cause analysis

**Coverage:**
- Exhaustive analysis
- Multiple agent perspectives
- Cross-cutting concerns
- Risk analysis
- Detailed remediation roadmap

**Example:**
```bash
/task-review TASK-XXX --mode=security --depth=comprehensive

# Output:
Comprehensive Security Audit (5 hours)
- OWASP Top 10 Coverage: Complete
- Vulnerabilities: 23 identified
- Critical: 2, High: 7, Medium: 11, Low: 3
- Compliance: GDPR, SOC2 checks
- Remediation Roadmap: 6-month plan
```

## Best Practices

### 1. Choose the Right Mode

Match the review mode to your needs:
- Architecture decisions → `architectural`
- Code maintenance concerns → `code-quality`
- "Should we...?" questions → `decision`
- Cleanup planning → `technical-debt`
- Security concerns → `security`

### 2. Set Appropriate Depth

Start quick, go deeper if needed:
```bash
# Initial assessment
/task-review TASK-XXX --depth=quick

# If concerns found, go deeper
/task-review TASK-XXX --depth=comprehensive --focus="authentication layer"
```

### 3. Link Reviews to Implementation

Always create implementation tasks from review findings:
```bash
# Review
/task-review TASK-REV-001 --mode=architectural

# [I]mplement option creates task automatically
# Then work on it
/task-work TASK-IMP-002
```

### 4. Document Decisions

The review report provides audit trail:
- Why decisions were made
- What options were considered
- What evidence supported the decision
- When the decision was made

### 5. Iterative Review

Use the [R]evise option for deeper analysis:
```bash
# Initial review
/task-review TASK-XXX --mode=decision

# User chooses [R] to focus on security
# System re-runs with focus
/task-review TASK-XXX --mode=decision --depth=comprehensive --focus="security implications"
```

## Integration with Task Workflow

### Review → Implementation Flow

```bash
# 1. Architectural review identifies issues
/task-review TASK-REV-001 --mode=architectural

# 2. Create implementation task (via [I] option)
# Output: TASK-IMP-002 created

# 3. Implement recommended changes
/task-work TASK-IMP-002

# 4. Post-implementation review
/task-review TASK-REV-003 --mode=code-quality

# 5. Both tasks completed
/task-complete TASK-IMP-002
/task-complete TASK-REV-001
```

### Decision → Implementation Flow

```bash
# 1. Decision analysis
/task-review TASK-DEC-001 --mode=decision

# 2. Decision made: Proceed with Option 2
# Create implementation tasks

# 3. Implementation
/task-work TASK-IMP-003  # Implement chosen option

# 4. Complete decision task
/task-complete TASK-DEC-001
```

## Output Files

### Review Report Location

**Path:** `.claude/reviews/TASK-{ID}-review-report.md`

**Example:** `.claude/reviews/TASK-REV-A3F2-review-report.md`

### Task Metadata Updates

After review completion, task file updated:
```yaml
---
id: TASK-REV-A3F2
status: review_complete  # or completed if [A]ccepted
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-REV-A3F2-review-report.md
  completed_at: 2025-01-20T16:30:00Z
---
```

### Implementation Task Linking

If [I]mplement chosen:
```yaml
---
id: TASK-IMP-B4D1
title: Refactor AuthService based on TASK-REV-A3F2
related_review: TASK-REV-A3F2  # Links back to review
status: backlog
---

# Task: Refactor AuthService based on TASK-REV-A3F2

## Context
This task implements recommendations from architectural review TASK-REV-A3F2.

**Review Findings:** See [Review Report](.claude/reviews/TASK-REV-A3F2-review-report.md)

## Acceptance Criteria
- [ ] Split AuthService into separate concerns (from review)
- [ ] Achieve SOLID score >80 (from review)
- [ ] Maintain backward compatibility
- [ ] Test coverage ≥90%
```

## Troubleshooting

### Issue: Review scope too broad

**Symptom:** Review takes too long or produces unclear findings

**Solution:** Narrow the scope
```bash
# Instead of reviewing entire codebase
/task-review TASK-XXX --mode=architectural

# Review specific module
/task-create "Review auth module only" task_type:review
# In task description: "Review Scope: src/auth/ directory only"
/task-review TASK-YYY --mode=architectural
```

### Issue: Need different perspective

**Symptom:** Review findings don't address your concern

**Solution:** Use [R]evise with specific focus
```bash
# Initial review
/task-review TASK-XXX --mode=architectural

# [R]evise with focus
Enter focus areas: performance implications, database query optimization
```

### Issue: Review report too technical

**Symptom:** Stakeholders can't understand review report

**Solution:** Use summary output format
```bash
/task-review TASK-XXX --mode=decision --output=summary

# Or manually create executive summary from detailed report
```

### Issue: Conflicting recommendations

**Symptom:** Different agents provide contradictory advice

**Solution:** Request decision analysis
```bash
/task-review TASK-XXX --mode=decision --depth=comprehensive
```

The decision mode will evaluate trade-offs and provide unified recommendation.

## Summary

**Task Review Workflow** provides:
- ✅ Structured analysis for non-implementation tasks
- ✅ Specialized review modes for different needs
- ✅ Automatic report generation
- ✅ Decision checkpoints with multiple options
- ✅ Seamless integration with implementation workflow

**Key Takeaways:**
1. Use `/task-review` for analysis, `/task-work` for implementation
2. Choose appropriate mode and depth for your needs
3. Review reports provide audit trail and context
4. [I]mplement option creates linked implementation tasks
5. Iterative refinement via [R]evise option

**Next Steps:**
- Read command specification: `installer/global/commands/task-review.md`
- Review CLAUDE.md for integration details
- Practice with sample review tasks
