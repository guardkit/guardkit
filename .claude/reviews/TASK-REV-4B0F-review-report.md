# Architectural Review Report: TASK-REV-4B0F

## Executive Summary

**Review Task**: Review FEAT-SEC architecture for feature-build compatibility
**Review Mode**: Architectural
**Review Depth**: Standard
**Date**: 2026-01-24
**Overall Assessment**: **PROCEED WITH MODIFICATIONS**

The FEAT-SEC (Coach Security Integration) feature design has **fundamental architectural misalignments** with the current AutoBuild Player-Coach workflow. The design was created before `/feature-build` was fully implemented and makes assumptions that violate the Coach's read-only architecture. However, the core security validation concept is sound and can be adapted.

**Architecture Score**: 62/100 (below 85 target)
- SOLID Compliance: 6/10 (violates Single Responsibility in Coach)
- DRY Adherence: 8/10 (good code reuse concepts)
- YAGNI Compliance: 7/10 (some over-engineering in agent invocation)

**Recommendation**: Modify architecture to run security checks in **pre-loop quality gates** (like Phase 2.5B) rather than during Coach validation.

---

## Key Findings

### Finding 1: CRITICAL - Coach Agent Invocation Violation

**Severity**: Critical
**Location**: [TASK-SEC-003-security-specialist-invocation.md](../../tasks/backlog/coach-security-integration/TASK-SEC-003-security-specialist-invocation.md)

**Issue**: The design proposes that Coach invokes `security-specialist` agent via the Task tool:

```python
# From TASK-SEC-003 design
async def invoke_security_specialist(
    worktree_path: Path,
    task: dict,
    timeout: int = 300
) -> List[SecurityFinding]:
    result = await invoke_task(
        subagent_type="security-specialist",
        ...
    )
```

**Why This Violates Architecture**:

The Coach agent is explicitly defined as **read-only** ([autobuild-coach.md:27-31](../../.claude/agents/autobuild-coach.md#L27-L31)):

```markdown
### NEVER
- ❌ Never write or modify code (you validate, you don't implement)
```

More importantly, Coach's tools are limited to: `Read, Bash, Grep, Glob` (line 9). The Task tool is NOT available to Coach.

The Coach's role is to **read task-work quality gate results**, not to invoke additional agents or run analysis. This is the "Option D" architecture principle explicitly stated in [coach_validator.py:6-15](../../guardkit/orchestrator/quality_gates/coach_validator.py#L6-L15):

```
Architecture:
    Implements Option D: 100% code reuse by reading
    task-work quality gate outputs instead of reimplementing validation.
```

**Impact**: If implemented as designed, this would require changing Coach's fundamental architecture, violating the "lightweight validator" principle.

---

### Finding 2: HIGH - Quality Gate Location Mismatch

**Severity**: High
**Location**: Multiple files in coach-security-integration/

**Issue**: The design places security checks **during Coach validation**, but quality gates run in the **pre-loop phase** (Phase 2.5) or **during Player's task-work execution** (Phases 4-5), NOT during Coach validation.

**Current Architecture** (from [pre_loop.py:102-107](../../guardkit/orchestrator/quality_gates/pre_loop.py#L102-L107)):
```
Quality Gates Executed (via task-work --design-only):
- Phase 1.6: Clarifying Questions
- Phase 2: Implementation Planning
- Phase 2.5A: Pattern Suggestions
- Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)  <-- Security would fit here
- Phase 2.7: Complexity Evaluation
- Phase 2.8: Human Checkpoint
```

**During Player execution**:
- Phase 4: Test execution
- Phase 4.5: Test enforcement loop
- Phase 5: Code review
- Phase 5.5: Plan audit

**Coach's role** is to READ these results and verify, not to add new gates.

**Where Security Should Run**:
1. **Quick Checks**: During Phase 4 (test execution) or as a Phase 4.3 security scan
2. **Full Review**: Before Phase 3 (implementation) for security-tagged tasks, or as Phase 2.5C

---

### Finding 3: MEDIUM - Async/Sync Incompatibility

**Severity**: Medium
**Location**: [TASK-SEC-003-security-specialist-invocation.md](../../tasks/backlog/coach-security-integration/TASK-SEC-003-security-specialist-invocation.md)

**Issue**: The design proposes `async def invoke_security_specialist()`, but [CoachValidator](../../guardkit/orchestrator/quality_gates/coach_validator.py) is currently **synchronous**:

```python
def validate(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
    skip_arch_review: bool = False,
) -> CoachValidationResult:  # Not async
```

**Impact**: Would require converting CoachValidator to async or using async-to-sync bridges, adding complexity.

---

### Finding 4: LOW - Feature File Structure Compatible

**Severity**: Low (Positive)
**Location**: [FEAT-SEC.yaml](../../.guardkit/features/FEAT-SEC.yaml)

**Finding**: The FEAT-SEC.yaml file structure is **compatible** with `/feature-build`:

- Has required `id`, `name`, `status`, `tasks` fields
- Has `orchestration.parallel_groups` for wave execution
- Tasks have `dependencies`, `complexity`, `implementation_mode`
- All task markdown files exist

**No changes needed** for feature-level compatibility.

---

### Finding 5: LOW - Subtask Files Well-Structured

**Severity**: Low (Positive)
**Location**: All TASK-SEC-*.md files

**Finding**: Individual subtask files have proper structure:
- Complete frontmatter with `id`, `status`, `task_type`, `complexity`
- `acceptance_criteria` lists are well-defined
- `dependencies` are correctly specified
- `wave` and `conductor_workspace` assigned
- `parent_review` and `feature_id` for traceability

**Minor Issue**: `task_type: feature` should likely be `task_type: feature_task` or just omit (default to `feature`). Current value is valid but inconsistent with other tasks in the codebase.

---

## Compatibility Matrix

| Subtask | Feature-Build Compatible | Needs Modification | Critical Issue |
|---------|-------------------------|-------------------|----------------|
| TASK-SEC-001 | Yes | No | None |
| TASK-SEC-002 | Yes | No | None |
| TASK-SEC-003 | **NO** | **YES** | Coach invocation violation |
| TASK-SEC-004 | Partial | Yes | Should run in pre-loop |
| TASK-SEC-005 | Yes | Minor | Integration tests need rewrite |
| TASK-SEC-006 | Yes | Minor | Docs need architecture update |

---

## Architecture Assessment

### Current Design (As-Is)

```
CURRENT PROPOSAL (PROBLEMATIC):

Player (task-work)
    │
    ├── Implementation
    │
    └── Quality Gates (Phase 4-5)
              │
              ▼
Coach (validation)
    │
    ├── Read task-work results
    ├── Run quick security checks     <-- PROBLEMATIC: Coach does analysis
    ├── Invoke security-specialist    <-- CRITICAL: Coach lacks Task tool
    │
    └── Approve/Feedback
```

### Recommended Design (To-Be)

```
RECOMMENDED ARCHITECTURE:

Pre-Loop Quality Gates (Phase 2.5C - Security Pre-Check)
    │
    ├── Load task metadata (tags, security config)
    ├── IF security-tagged: Run full security review
    │       └── Invoke security-specialist (via TaskWorkInterface)
    └── Store security_review_results.json
              │
              ▼
Player (task-work --implement-only)
    │
    ├── Implementation (Phase 3)
    │
    ├── Quick Security Scan (Phase 4.3 - NEW)
    │       └── SecurityChecker.run_quick_checks()
    │       └── Write to task_work_results.json
    │
    └── Quality Gates (Phase 4-5.5)
              │
              ▼
Coach (validation)
    │
    ├── Read task-work results (including security findings)
    ├── Verify security gates passed
    │       └── results["security"]["all_passed"] == true
    │
    └── Approve/Feedback (NO agent invocation)
```

**Key Changes**:
1. Move full security review to **pre-loop** (Phase 2.5C)
2. Add quick security checks to **task-work** (Phase 4.3)
3. Coach only **reads** security results from `task_work_results.json`
4. Coach does NOT invoke security-specialist

---

## SOLID/DRY/YAGNI Analysis

### Single Responsibility Principle (SRP)

**Current Score**: 5/10

**Violation**: The design has Coach doing two distinct things:
1. Validating task-work quality gate results (its actual responsibility)
2. Running security analysis and invoking agents (new responsibility)

**Fix**: Security analysis should be a separate concern, handled by task-work or pre-loop, not Coach.

### Open/Closed Principle (OCP)

**Current Score**: 7/10

**Positive**: The SecurityConfig and SecurityChecker designs are extensible:
- New check IDs can be added without modifying existing checks
- Configuration levels (strict/standard/minimal/skip) are enumerated

**Concern**: Hard-coded exclusion categories limit extensibility.

### Liskov Substitution Principle (LSP)

**Current Score**: 8/10

**Positive**: SecurityFinding dataclass is well-designed and can be extended.

### Interface Segregation Principle (ISP)

**Current Score**: 6/10

**Concern**: SecurityConfig has many fields that may not be needed for all use cases. Consider splitting into:
- `QuickCheckConfig` for Phase 4.3
- `FullReviewConfig` for Phase 2.5C

### Dependency Inversion Principle (DIP)

**Current Score**: 6/10

**Concern**: TASK-SEC-003 design has direct coupling to Task tool:
```python
result = await invoke_task(subagent_type="security-specialist", ...)
```

Should depend on an abstract `SecurityReviewProvider` interface.

---

## Recommendations

### 1. Restructure Quality Gate Location

**Priority**: Critical
**Effort**: Medium (4-6 hours)

Move security validation from Coach to appropriate phases:

```yaml
# REVISED WAVE STRUCTURE

Wave 1: Foundation (No Change)
  - TASK-SEC-001: Quick security checks → runs in Phase 4.3 (task-work)
  - TASK-SEC-002: Security config schema → no change

Wave 2: Pre-Loop Integration (NEW)
  - TASK-SEC-003: REWRITE → Pre-loop security review (Phase 2.5C)
  - TASK-SEC-004: Tag detection → runs in pre-loop decision logic

Wave 3: Testing (Adjust Integration Tests)
  - TASK-SEC-005: Tests → update integration tests for new architecture

Wave 4: Documentation (Update)
  - TASK-SEC-006: Docs → reflect new architecture
```

### 2. Rewrite TASK-SEC-003

**Priority**: Critical
**Effort**: High (6-8 hours)

Replace Coach-invoked security specialist with pre-loop integration:

**Current Design** (Violates Architecture):
```python
# In coach_validator.py
full_findings = await invoke_security_specialist(task)  # WRONG
```

**Recommended Design**:
```python
# In pre_loop.py
class PreLoopQualityGates:
    async def execute(self, task_id: str, options: Dict[str, Any]) -> PreLoopResult:
        # Existing gates...
        design_result = await self._interface.execute_design_phase(...)

        # NEW: Phase 2.5C - Security Pre-Check
        if self._should_run_security_review(task):
            security_result = await self._run_security_review(task)
            self._save_security_review_result(task_id, security_result)

        return self._extract_pre_loop_results(...)

    async def _run_security_review(self, task: dict) -> SecurityReviewResult:
        """Invoke security-specialist via TaskWorkInterface."""
        return await self._interface.execute_security_review(task)
```

```python
# In task_work_interface.py
class TaskWorkInterface:
    async def execute_security_review(self, task: dict) -> SecurityReviewResult:
        """Run full security review for security-tagged tasks."""
        # Invoke security-specialist agent here
        # This is where Task tool invocation is appropriate
```

### 3. Add Phase 4.3 to Task-Work

**Priority**: High
**Effort**: Medium (3-4 hours)

Modify task-work to include quick security scan after tests:

```python
# In task_work execution flow

# Phase 4: Testing
test_results = run_tests()

# Phase 4.3: Quick Security Scan (NEW)
if security_config.level != SecurityLevel.SKIP:
    security_findings = SecurityChecker(worktree).run_quick_checks()
    if has_critical_findings(security_findings):
        return blocked("Critical security vulnerabilities detected")
    task_work_results["security"] = {
        "quick_check_passed": True,
        "findings": [f.to_dict() for f in security_findings]
    }

# Phase 4.5: Test Enforcement
...
```

### 4. Update Coach to Read Security Results

**Priority**: Medium
**Effort**: Low (1-2 hours)

Coach should read security results from task_work_results.json:

```python
# In coach_validator.py verify_quality_gates()

def verify_quality_gates(self, task_work_results: Dict) -> QualityGateStatus:
    # Existing gates...
    tests_passed = ...
    coverage_met = ...

    # NEW: Security gate
    security = task_work_results.get("security", {})
    security_passed = security.get("quick_check_passed", True)
    critical_findings = [f for f in security.get("findings", [])
                        if f["severity"] == "critical"]

    return QualityGateStatus(
        tests_passed=tests_passed,
        coverage_met=coverage_met,
        security_passed=security_passed and len(critical_findings) == 0,
        # ...
    )
```

### 5. Update FEAT-SEC.yaml Orchestration

**Priority**: Low
**Effort**: Low (30 minutes)

Adjust parallel groups if TASK-SEC-003 scope changes significantly.

---

## Risk Assessment

### Risk of Implementing As-Is

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Coach architecture violation | Certain | High | Redesign to recommended architecture |
| Async compatibility issues | High | Medium | Keep Coach synchronous, async in pre-loop |
| Tool permission errors | Certain | High | Don't add Task tool to Coach |
| Test failures in integration | High | Medium | Rewrite integration tests |

### Risk of Recommended Changes

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pre-loop complexity increase | Medium | Low | Modular design with separate security module |
| Task-work phase sprawl | Low | Low | Phase 4.3 fits naturally after tests |
| Documentation overhead | Low | Low | Update TASK-SEC-006 scope |

---

## Action Items

### Immediate (Before Implementation)

1. **Approve or reject** this architectural review
2. **If approved**, create modification tasks:
   - TASK-SEC-003a: Rewrite as pre-loop security integration
   - TASK-SEC-003b: Add Phase 4.3 quick security scan to task-work
3. **Update** FEAT-SEC.yaml with revised task structure

### During Implementation

4. **TASK-SEC-001**: Implement as designed (no changes needed)
5. **TASK-SEC-002**: Implement as designed (no changes needed)
6. **TASK-SEC-003**: Implement revised architecture (pre-loop + task-work)
7. **TASK-SEC-004**: Adjust to run in pre-loop, not Coach
8. **TASK-SEC-005**: Update integration tests for new architecture
9. **TASK-SEC-006**: Update documentation to reflect architecture

### Post-Implementation

10. **Validate** that Coach remains read-only (no Task tool)
11. **Verify** security results appear in task_work_results.json
12. **Test** end-to-end with `/feature-build TASK-XXX` (security-tagged)

---

## Appendix: Files Reviewed

| File | Lines | Purpose |
|------|-------|---------|
| FEAT-SEC.yaml | 135 | Feature definition |
| TASK-SEC-001-quick-security-checks.md | 178 | Quick checks subtask |
| TASK-SEC-002-security-config-schema.md | 230 | Config schema subtask |
| TASK-SEC-003-security-specialist-invocation.md | 270 | Agent invocation subtask |
| TASK-SEC-004-task-tagging-detection.md | 222 | Tag detection subtask |
| TASK-SEC-005-security-validation-tests.md | 368 | Testing subtask |
| TASK-SEC-006-coach-documentation-update.md | 287 | Documentation subtask |
| coach_validator.py | 1093 | Current Coach implementation |
| pre_loop.py | 407 | Pre-loop quality gates |
| autobuild-coach.md | 532 | Coach agent definition |
| autobuild-player.md | 485 | Player agent definition |
| feature-build.md | 933 | Feature-build command spec |

---

## Review Metadata

```yaml
review_id: TASK-REV-4B0F
review_mode: architectural
review_depth: standard
architecture_score: 62
solid_score: 6.4
dry_score: 8
yagni_score: 7
findings_count: 5
recommendations_count: 5
decision: modify
report_path: .claude/reviews/TASK-REV-4B0F-review-report.md
reviewed_at: 2026-01-24T16:30:00Z
```
