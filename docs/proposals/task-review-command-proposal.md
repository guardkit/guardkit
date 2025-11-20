# Proposal: /task-review Command

**Status**: Research Proposal
**Created**: 2025-01-20
**Author**: System Architecture Review (TASK-09E9 findings)
**Priority**: High (addresses workflow gap identified in production use)

---

## Executive Summary

Create a dedicated `/task-review` command for **analysis, decision-making, and assessment tasks** that are distinct from implementation work. This separates review workflows from implementation workflows, avoiding the pollution of `/task-work` with conditional logic and maintaining clarity of purpose.

**Key Principle**: `/task-work` is for building. `/task-review` is for analyzing.

---

## Problem Statement

### Current Situation

Users have **two distinct use cases** but only **one command**:

| Use Case | Current Command | Problem |
|----------|----------------|---------|
| "Implement feature X" | `/task-work TASK-XXX` | ✅ Works well (Phases 1-5) |
| "Should we implement X?" | `/task-work TASK-XXX` | ❌ Executes implementation anyway |
| "Review architecture of X" | Manual agent invocation | ❌ No structured workflow |
| "Analyze technical debt in X" | Manual agent invocation | ❌ No state tracking |

### Real-World Example (TASK-09E9)

**Task Goal**: "Provide a clear, actionable decision with supporting analysis"
**Task Type**: Architectural review (NOT implementation)
**What Happened**: `/task-work` executed the review (✅) but then proceeded to implement the recommended solution (❌)
**Root Cause**: `/task-work` assumes all tasks are implementation tasks

### User Feedback (from conversation)

> "I do quite often find myself looking to review implementations using the LLM, using sub-agents, using UltraThink. I think it would be better to create a task-review command."

This confirms a **recurring need** for structured review workflows.

---

## Proposed Solution: /task-review Command

### Command Philosophy

**`/task-work`**: Build things (implementation, testing, deployment)
**`/task-review`**: Analyze things (architecture, code quality, decisions, technical debt)

**Separation Benefits**:
- ✅ Clear purpose (no conditional logic in task-work)
- ✅ Specialized workflow (review-specific phases)
- ✅ Appropriate agents (reviewers, not implementers)
- ✅ Different outputs (documents, not code)

### Command Syntax

```bash
# Basic usage
/task-review TASK-XXX

# Review modes
/task-review TASK-XXX --mode=architectural  # Architecture review
/task-review TASK-XXX --mode=code-quality   # Code quality review
/task-review TASK-XXX --mode=decision       # Decision analysis
/task-review TASK-XXX --mode=technical-debt # Technical debt assessment
/task-review TASK-XXX --mode=security       # Security audit

# Depth control
/task-review TASK-XXX --depth=quick         # 15-30 minutes, surface-level
/task-review TASK-XXX --depth=standard      # 1-2 hours, thorough
/task-review TASK-XXX --depth=comprehensive # 4-6 hours, exhaustive

# Output format
/task-review TASK-XXX --output=summary      # Executive summary only
/task-review TASK-XXX --output=detailed     # Full analysis report
/task-review TASK-XXX --output=presentation # Slide deck format
```

### Review Workflow Phases

**Phase 1: Load Review Context**
- Read task description, acceptance criteria
- Identify review type (architectural, code quality, decision, etc.)
- Load relevant codebase files/modules
- Load related design documents

**Phase 2: Execute Review Analysis**
- Invoke appropriate review agents based on mode:
  - `architectural-reviewer` for architecture reviews
  - `code-reviewer` for code quality reviews
  - `software-architect` for decision analysis
  - `debugging-specialist` for root cause analysis
  - `security-specialist` for security audits
- Perform analysis using specialized prompts
- Generate findings with evidence

**Phase 3: Synthesize Recommendations**
- Aggregate findings from multiple agents (if used)
- Score/rate based on review criteria
- Generate actionable recommendations
- Identify decision options (if decision-making task)

**Phase 4: Generate Review Report**
- Create structured markdown report
- Include executive summary
- Document findings with evidence
- Provide recommendations with rationale
- Attach supporting artifacts (diagrams, metrics)

**Phase 5: Human Decision Checkpoint**
- Present findings to user
- Offer decision options:
  - **[A]ccept** - Approve findings, mark task IN_REVIEW
  - **[R]evise** - Request deeper analysis on specific areas
  - **[I]mplement** - Create implementation task based on recommendation
  - **[C]ancel** - Discard review, return to backlog

**NO Phase 6** - Reviews don't generate code (that's `/task-work`'s job)

---

## Review Modes (Detailed)

### Mode 1: Architectural Review

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
   - Current patterns identified
   - Pattern mismatches
   - Recommended patterns
3. Technical Debt Inventory
   - Architectural debt items
   - Priority and effort estimates
4. Recommendations
   - Keep/Refactor/Rewrite decisions
   - Migration path (if needed)

**Decision Matrix**:
| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| Continue Current | X/100 | Low | Medium | ... |
| Refactor | Y/100 | Medium | Low | ... |
| Rewrite | Z/100 | High | High | ... |

### Mode 2: Code Quality Review

**Purpose**: Assess code maintainability, complexity, test coverage

**Agents Used**:
- `code-reviewer` (primary)
- `test-orchestrator` (for coverage analysis)

**Output Sections**:
1. Code Metrics
   - Cyclomatic complexity
   - Lines of code (LOC)
   - Duplication percentage
   - Test coverage (line/branch)
2. Quality Issues
   - Code smells identified
   - Anti-patterns found
   - Style violations
3. Maintainability Score (0-10)
4. Recommendations
   - Refactoring priorities
   - Test improvement areas

### Mode 3: Decision Analysis

**Purpose**: Evaluate options and provide decision recommendation

**Agents Used**:
- `software-architect` (primary)
- `architectural-reviewer` (for technical assessment)
- Stack-specific specialists (for implementation details)

**Output Sections**:
1. Current Situation Assessment
2. Root Cause Analysis (if problem-solving)
3. Option Evaluation Matrix
   - Option A, B, C, D scoring
   - Technical Viability (0-10)
   - Effort vs Value (0-10)
   - Risk Assessment (0-10)
   - Strategic Alignment (0-10)
4. Recommended Decision
   - Highest-scoring option
   - Confidence level (Low/Medium/High)
   - Implementation plan (if proceeding)
   - Risk mitigation strategy

**Example** (from TASK-09E9):
```
OPTION B - PIVOT TO BATCH PROCESSING

Confidence: HIGH (85%)
Total Score: 38/40

Technical Viability: 10/10 (code exists, just needs wiring)
Effort vs Value: 10/10 (low effort, full value)
Risk: 9/10 (low risk, code already tested)
Strategic Alignment: 9/10 (delivers feature with good UX)

Recommendation: Proceed with Option B
Next Steps: Create implementation task
Estimated Effort: 4-8 hours
```

### Mode 4: Technical Debt Assessment

**Purpose**: Inventory and prioritize technical debt

**Agents Used**:
- `code-reviewer` (for code debt)
- `architectural-reviewer` (for design debt)
- `test-orchestrator` (for test debt)

**Output Sections**:
1. Debt Inventory
   - Code debt items
   - Design debt items
   - Test debt items
   - Documentation debt items
2. Debt Prioritization Matrix
   - Impact (High/Medium/Low)
   - Effort (High/Medium/Low)
   - Risk (High/Medium/Low)
3. Recommended Paydown Strategy
   - Quick wins (low effort, high impact)
   - Critical items (high risk)
   - Long-term items (high effort)

### Mode 5: Security Audit

**Purpose**: Identify security vulnerabilities and compliance issues

**Agents Used**:
- `security-specialist` (primary)
- `code-reviewer` (for code-level issues)

**Output Sections**:
1. Vulnerability Assessment
   - OWASP Top 10 check
   - Known CVEs in dependencies
   - Authentication/authorization issues
   - Data protection concerns
2. Compliance Check
   - GDPR/HIPAA/SOC2 requirements
   - Security best practices
3. Risk Scoring (Critical/High/Medium/Low)
4. Remediation Plan
   - Immediate actions (Critical/High)
   - Planned improvements (Medium/Low)

---

## Task State Transitions

### Review Task Lifecycle

```
BACKLOG
   ├─ (task-review) ──────→ IN_PROGRESS ──→ REVIEW_COMPLETE ──→ IN_REVIEW
   │                              ↓                                   ↓
   │                          BLOCKED                            COMPLETED
   │                                                                  ↓
   └─────────────────────────────────────────────────────→ (optionally creates)
                                                           IMPLEMENTATION_TASK
```

**New State**: `REVIEW_COMPLETE`
- Review analysis finished
- Report generated
- Awaiting human decision (Accept/Revise/Implement/Cancel)

**State Transitions**:
1. `BACKLOG → IN_PROGRESS` - Review started
2. `IN_PROGRESS → REVIEW_COMPLETE` - Analysis finished, report ready
3. `REVIEW_COMPLETE → IN_REVIEW` - Human accepted findings
4. `REVIEW_COMPLETE → BACKLOG` - Human requested revision
5. `REVIEW_COMPLETE → BLOCKED` - Review failed (missing files, etc.)
6. `IN_REVIEW → COMPLETED` - Decision approved, archived

**Optional**: `REVIEW_COMPLETE → creates → IMPLEMENTATION_TASK`
- User chooses "Implement" option
- System creates new task based on recommendation
- New task goes to BACKLOG for `/task-work` execution

---

## Task Metadata Schema

### Review Task Frontmatter

```yaml
---
id: TASK-XXX
title: "Architectural Review - Authentication System"
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: high

# Review-specific metadata
task_type: review  # NEW FIELD: review, implementation, research, docs
review_mode: architectural  # architectural, code-quality, decision, technical-debt, security
review_depth: comprehensive  # quick, standard, comprehensive
decision_required: true  # If true, must provide decision options

# Review targets
review_scope:
  - src/auth/
  - src/middleware/auth.py
  - docs/architecture/auth-design.md

# Acceptance criteria (for review tasks)
acceptance_criteria:
  - Architectural assessment scored (0-100)
  - SOLID/DRY/YAGNI compliance evaluated
  - Decision options provided (A/B/C/D)
  - Confidence level stated (Low/Medium/High)
  - Implementation plan provided (if proceeding)

# Agents required
agents_required:
  - architectural-reviewer
  - software-architect
  - pattern-advisor

# Estimated effort
estimated_effort: 4-6 hours

# Output format
output_format: detailed  # summary, detailed, presentation
---
```

### Review Output Metadata

After review completion, add to frontmatter:

```yaml
review_results:
  completion_date: 2025-01-20T18:30:00Z
  duration_hours: 4.5
  review_score: 72/100  # Overall assessment
  confidence: high  # Low, Medium, High

  findings_summary:
    critical_issues: 2
    high_priority: 5
    medium_priority: 12
    low_priority: 8

  decision_recommendation: "Option B - Refactor with incremental migration"

  artifacts:
    - docs/state/TASK-XXX/review-report.md
    - docs/state/TASK-XXX/decision-matrix.md
    - docs/state/TASK-XXX/architecture-diagrams/

  implementation_task: TASK-YYY  # If user chose "Implement"
```

---

## Integration with Existing Workflow

### Relationship to /task-work

**Scenario 1: Review → Decision → Implement**
```bash
# Step 1: Review
/task-review TASK-001 --mode=architectural

# Review output: "Recommend Option B - Refactor authentication"
# User chooses: [I]mplement

# Step 2: System creates implementation task
# Created: TASK-002 "Implement authentication refactoring (Option B)"

# Step 3: Implement
/task-work TASK-002

# Links: TASK-002.implements = TASK-001
```

**Scenario 2: Review → No Action**
```bash
# Step 1: Review
/task-review TASK-003 --mode=technical-debt

# Review output: "Current debt acceptable, no action needed"
# User chooses: [A]ccept

# Task marked COMPLETED, no implementation task created
```

### Relationship to /task-create

**Task Creation Hints**:

When users create tasks, `/task-create` could suggest the appropriate command:

```bash
/task-create "Evaluate whether to refactor authentication system"

Analyzing task description...

Detected task type: REVIEW (decision-making)
Suggested command: /task-review (not /task-work)

Recommended metadata:
  task_type: review
  review_mode: decision
  decision_required: true

Create task? [Y/n]:
```

---

## Command Implementation Plan

### Phase 1: Core Command (4-8 hours)

**File**: `installer/global/commands/task-review.md`

**Structure**:
```markdown
# Task Review - Structured Analysis and Decision-Making

## Command Syntax
(as documented above)

## Workflow Phases
(Phases 1-5 as documented above)

## Execution Protocol
(Similar to task-work but for review)
```

**File**: `installer/global/commands/lib/task_review_orchestrator.py`

**Core Functions**:
```python
def execute_task_review(task_id: str, mode: str, depth: str, output: str):
    """Main orchestrator for task-review command."""
    # Phase 1: Load review context
    task_context = load_review_context(task_id)

    # Phase 2: Execute review analysis
    review_results = execute_review_analysis(task_context, mode, depth)

    # Phase 3: Synthesize recommendations
    recommendations = synthesize_recommendations(review_results)

    # Phase 4: Generate review report
    report = generate_review_report(review_results, recommendations, output)

    # Phase 5: Human decision checkpoint
    decision = present_decision_checkpoint(report, recommendations)

    # Handle decision
    handle_review_decision(task_id, decision, recommendations)
```

### Phase 2: Review Modes (8-12 hours)

Implement each review mode with specialized prompts and agent configurations:

1. **Architectural Review** (2 hours)
2. **Code Quality Review** (2 hours)
3. **Decision Analysis** (2 hours)
4. **Technical Debt Assessment** (2 hours)
5. **Security Audit** (2 hours)

### Phase 3: Report Generation (4-6 hours)

**File**: `installer/global/commands/lib/review_report_generator.py`

**Output Formats**:
1. **Summary** (1-page executive summary)
2. **Detailed** (full analysis report with evidence)
3. **Presentation** (slide deck format)

**Report Structure**:
```markdown
# Review Report - TASK-XXX

**Review Type**: Architectural Review
**Review Date**: 2025-01-20
**Reviewer**: Claude (Sonnet 4.5)
**Duration**: 4.5 hours

## Executive Summary
(1-page overview)

## Detailed Findings
(Section-by-section analysis)

## Decision Recommendation
(If decision_required: true)

## Implementation Plan
(If user chooses "Implement")

## Appendices
(Supporting artifacts)
```

### Phase 4: Integration (2-4 hours)

1. **Update /task-create** to suggest `/task-review` for review tasks
2. **Add state transitions** for `REVIEW_COMPLETE` state
3. **Implement "Create Implementation Task" flow**
4. **Update documentation** (CLAUDE.md, workflow guides)

### Phase 5: Testing (4-6 hours)

**Test Scenarios**:
1. Architectural review with decision options
2. Code quality review with metrics
3. Decision analysis with option matrix
4. Technical debt assessment with prioritization
5. Security audit with compliance check

**Test Coverage**:
- Unit tests for orchestrator functions
- Integration tests for review workflows
- End-to-end tests with real tasks

---

## Success Metrics

### Command Adoption
- `/task-review` used for 100% of review/decision tasks (vs 0% currently)
- `/task-work` used only for implementation tasks (cleaner separation)

### Review Quality
- Review reports include all required sections (100%)
- Decision recommendations have confidence levels (100%)
- Implementation tasks created have clear acceptance criteria (100%)

### User Satisfaction
- Users can distinguish review vs implementation workflows (100%)
- Users receive actionable recommendations (not just "here's a problem")
- Users can make informed decisions based on review output

---

## Alternative Approaches Considered

### Alternative 1: Add --review Flag to /task-work

```bash
/task-work TASK-XXX --review-only
```

**Pros**:
- Single command for all tasks
- Easier to discover

**Cons**:
- ❌ Pollutes `/task-work` with conditional logic
- ❌ Confusing: "task-work" implies implementation
- ❌ Phases 3-5 make no sense for review tasks
- ❌ Hard to maintain (two workflows in one command)

**Decision**: Rejected - violates separation of concerns

### Alternative 2: Use Task Type Field in /task-work

```yaml
task_type: review  # Routes to review workflow
```

**Pros**:
- Automatic routing based on metadata
- Single command

**Cons**:
- ❌ Same as Alternative 1 (pollution, complexity)
- ❌ User confusion about what `/task-work` does
- ❌ Difficult to document (two behaviors)

**Decision**: Rejected - same issues as Alternative 1

### Alternative 3: Manual Agent Invocation (Status Quo)

```bash
# User manually invokes agents
Task tool: architectural-reviewer
Task tool: software-architect
# User manually writes report
```

**Pros**:
- No new command needed
- Maximum flexibility

**Cons**:
- ❌ No structured workflow
- ❌ No state tracking
- ❌ No consistent output format
- ❌ User must know which agents to invoke
- ❌ No decision checkpoint

**Decision**: Rejected - lacks structure and repeatability

---

## Recommendation

**Create `/task-review` as a dedicated command** (Proposed Solution)

**Rationale**:
1. ✅ Clean separation of concerns
2. ✅ Specialized workflow for reviews
3. ✅ Clear naming (task-review = reviewing tasks)
4. ✅ No pollution of task-work
5. ✅ Easier to maintain
6. ✅ Better user experience

**Estimated Total Effort**: 22-36 hours (3-5 days)

**Priority**: High (addresses real user need identified in TASK-09E9)

---

## Next Steps

### Immediate (Week 1)
1. Review and approve this proposal
2. Create implementation task: TASK-XXX "Implement /task-review command"
3. Design detailed workflow specification

### Short-term (Week 2-3)
1. Implement core command and orchestrator (Phase 1)
2. Implement 2-3 review modes (Phase 2)
3. Implement basic report generation (Phase 3)

### Medium-term (Week 4)
1. Complete all 5 review modes
2. Add integration with task-create
3. Write comprehensive tests

### Long-term (Month 2)
1. Add advanced features (presentation output, metrics dashboard)
2. Integrate with external tools (GitHub Issues, Linear, Jira)
3. Add review templates for common scenarios

---

## Open Questions

1. **State Management**: Should `REVIEW_COMPLETE` be a separate state or a flag in `IN_PROGRESS`?
2. **Report Storage**: Save to `docs/state/{task_id}/` or `tasks/reviews/{task_id}/`?
3. **Agent Reuse**: Can we reuse existing agents or need review-specific agents?
4. **MCP Integration**: Should review command use Context7 for library docs?
5. **Output Format**: Markdown only, or also JSON/PDF/HTML?

---

## Appendix A: Example Review Reports

### Example 1: Architectural Review

```markdown
# Architectural Review Report - TASK-009

**System**: Authentication Service
**Review Date**: 2025-01-20
**Reviewer**: Claude (architectural-reviewer)
**Duration**: 4.5 hours
**Review Mode**: architectural
**Review Depth**: comprehensive

## Executive Summary

The authentication system has significant architectural debt (score: 72/100) with opportunities for improvement in SOLID compliance and pattern consistency. Current implementation is functional but not scalable beyond 10K users.

**Recommendation**: Refactor with incremental migration (Option B)
**Confidence**: HIGH (85%)
**Estimated Effort**: 16-24 hours

## Architecture Assessment

**Overall Score**: 72/100 (Adequate but needs improvement)

| Principle | Score | Notes |
|-----------|-------|-------|
| Single Responsibility | 7/10 | AuthService handles too many concerns |
| Open/Closed | 8/10 | Good use of interfaces |
| Liskov Substitution | 9/10 | Inheritance used correctly |
| Interface Segregation | 6/10 | IAuthService too broad |
| Dependency Inversion | 8/10 | Good DI usage |
| DRY | 7/10 | Some duplication in validation |
| YAGNI | 6/10 | Over-engineered for current needs |

## Findings

### Critical Issues (2)

1. **Password Storage Not Hashed** (CRITICAL)
   - Location: src/auth/UserService.cs:45
   - Risk: HIGH - Security vulnerability
   - Effort: 2 hours
   - Recommendation: Use BCrypt.Net immediately

2. **No Rate Limiting** (CRITICAL)
   - Location: src/auth/LoginController.cs
   - Risk: HIGH - Brute force attacks possible
   - Effort: 4 hours
   - Recommendation: Add AspNetCoreRateLimit middleware

(Full findings omitted for brevity)

## Decision Matrix

| Option | Technical Viability | Effort vs Value | Risk | Strategic Alignment | Total |
|--------|-------------------|-----------------|------|-------------------|-------|
| **Option A**: Continue Current | 6/10 | 8/10 | 3/10 | 5/10 | 22/40 |
| **Option B**: Refactor (Recommended) | 9/10 | 9/10 | 8/10 | 9/10 | **35/40** |
| **Option C**: Rewrite | 10/10 | 4/10 | 5/10 | 7/10 | 26/40 |

## Recommended Decision: Option B - Refactor with Incremental Migration

**Confidence**: HIGH (85%)

**Implementation Plan**:
1. Fix critical security issues (Week 1)
2. Refactor AuthService into smaller services (Week 2)
3. Add rate limiting and logging (Week 3)
4. Migrate to JWT tokens (Week 4)

**Success Criteria**:
- Zero security vulnerabilities
- Architecture score ≥85/100
- Supports 100K users

## Supporting Artifacts

- Architecture diagrams: docs/state/TASK-009/architecture-current.png
- Code metrics: docs/state/TASK-009/code-metrics.json
- Test coverage: docs/state/TASK-009/coverage-report.html
```

### Example 2: Decision Analysis

```markdown
# Decision Analysis Report - TASK-042

**Decision**: Should we adopt GraphQL for our API?
**Analysis Date**: 2025-01-20
**Analyst**: Claude (software-architect)
**Duration**: 3 hours

## Current Situation

REST API with 50+ endpoints, increasing client complexity, over-fetching and under-fetching issues.

## Options Evaluated

### Option A: Continue with REST
- Technical Viability: 8/10 (mature, well-understood)
- Effort vs Value: 6/10 (low effort but limited value)
- Risk: 9/10 (low risk, proven approach)
- Strategic Alignment: 4/10 (doesn't solve client pain)
- **Total**: 27/40

### Option B: Adopt GraphQL (Recommended)
- Technical Viability: 7/10 (newer but proven)
- Effort vs Value: 8/10 (moderate effort, high value)
- Risk: 6/10 (learning curve, tooling maturity)
- Strategic Alignment: 9/10 (solves client pain)
- **Total**: 30/40

### Option C: Hybrid (REST + GraphQL)
- Technical Viability: 6/10 (complex to maintain)
- Effort vs Value: 5/10 (high effort, mixed value)
- Risk: 5/10 (two systems to maintain)
- Strategic Alignment: 7/10 (flexibility)
- **Total**: 23/40

## Recommendation: Option B - Adopt GraphQL

**Confidence**: MEDIUM (70%)

**Rationale**:
- Solves client over-fetching/under-fetching
- Better developer experience
- Industry trend (GitHub, Shopify, Netflix)
- Incremental adoption possible

**Implementation Plan**:
1. POC with 3 queries (Week 1)
2. GraphQL gateway for existing REST (Week 2-3)
3. Migrate 10 most-used endpoints (Week 4-5)
4. Client SDK generation (Week 6)

**Risks & Mitigations**:
- Risk: Team unfamiliarity → Mitigation: Training + external consultant
- Risk: N+1 queries → Mitigation: DataLoader pattern
- Risk: Tooling gaps → Mitigation: Evaluate tools upfront

## Next Steps

If approved:
1. Create TASK-043 "POC GraphQL with top 3 queries"
2. Schedule team training session
3. Evaluate GraphQL servers (Apollo, Hasura, etc.)
```

---

## Appendix B: Task Metadata Examples

### Example: Architectural Review Task

```yaml
---
id: TASK-009
title: Architectural Review - Authentication System
status: backlog
created: 2025-01-20T00:00:00Z
priority: high

task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: false

review_scope:
  - src/auth/
  - src/middleware/auth.py

acceptance_criteria:
  - SOLID/DRY/YAGNI scores provided
  - Critical issues identified and prioritized
  - Refactoring recommendations with effort estimates

agents_required:
  - architectural-reviewer
  - security-specialist

estimated_effort: 4-6 hours
---
```

### Example: Decision Analysis Task

```yaml
---
id: TASK-042
title: Decision Analysis - GraphQL vs REST
status: backlog
created: 2025-01-20T00:00:00Z
priority: medium

task_type: review
review_mode: decision
review_depth: standard
decision_required: true

review_scope:
  - Evaluate API architecture options
  - Compare GraphQL vs REST vs Hybrid

acceptance_criteria:
  - Options evaluated with scoring matrix
  - Decision recommended with confidence level
  - Implementation plan provided if proceeding

agents_required:
  - software-architect
  - architectural-reviewer

estimated_effort: 2-3 hours
---
```

---

**End of Proposal**
