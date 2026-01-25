# Integration Review Report: TASK-REV-INT01

## Executive Summary

This architectural review analyzes the integration between two in-flight features:
1. **AutoBuild task-work Delegation (TWD)** - 9 tasks across 5 waves
2. **Coach Security Integration (SEC)** - 6 tasks across 3 waves

**Overall Assessment**: These features are **complementary and can be developed in parallel** with minor coordination. The primary integration points are manageable with a clear merge strategy.

### Key Findings

| Category | Risk Level | Impact |
|----------|------------|--------|
| Shared File Conflicts | **MEDIUM** | 3 files with overlapping modifications |
| Execution Order | **LOW** | No hard dependencies, flexible implementation order |
| Coach Decision Flow | **MEDIUM** | Both modify Coach validation; clear integration path |
| Configuration Overlap | **LOW** | Orthogonal configurations, easy to merge |

---

## 1. Shared File Analysis

### File Conflict Matrix

| File | TWD Changes | SEC Changes | Conflict Risk | Resolution |
|------|-------------|-------------|---------------|------------|
| `.claude/agents/autobuild-coach.md` | Honesty verification section, Promise verification section | Security validation section | **MEDIUM** | Additive sections - low conflict |
| `guardkit/orchestrator/autobuild.py` | `_invoke_coach_safely()` changes, honesty history tracking | No direct changes | **LOW** | TWD owns this file |
| `guardkit/orchestrator/agent_invoker.py` | `invoke_player()` delegation, feedback file writing | No direct changes | **LOW** | TWD owns this file |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Minimal (already exists for TWD) | Security checks integration | **MEDIUM** | SEC extends existing class |
| `guardkit/orchestrator/quality_gates/security_checker.py` | Not touched | New file created | **NONE** | SEC owns this file |
| `guardkit/orchestrator/coach_verification.py` | New file for honesty verification | Not touched | **NONE** | TWD owns this file |

### Detailed File Conflict Analysis

#### `.claude/agents/autobuild-coach.md` (MEDIUM Risk)

**TWD Additions** (TASK-TWD-008, TASK-TWD-009):
```markdown
## Honesty Verification
- Cross-reference Player claims against actual results
- Verification categories: test_result, file_existence, test_count

## Promise Verification
- Verify completion_promise.criteria against acceptance criteria
- Coach verifies each criterion independently
```

**SEC Additions** (TASK-SEC-001, TASK-SEC-003):
```markdown
## Security Validation
- Quick security checks run on all tasks
- Full security-specialist review for tagged tasks
- Critical/high findings block approval
```

**Resolution Strategy**: Both additions are **independent sections** that can coexist. No structural conflict. The Coach agent definition supports multiple validation sections.

---

## 2. Execution Order Analysis

### Can SEC be implemented before TWD?

**YES** - Coach security integration works with the current SDK-based Player invocation. Security checks run in Coach validation phase regardless of how Player is invoked.

### Can TWD be implemented before SEC?

**YES** - task-work delegation modifies Player invocation, not Coach validation logic. Security checks would simply be added later.

### Parallel Development Feasibility

**RECOMMENDED** - Both features can develop in parallel because:
1. TWD primarily modifies **Player phase** (`invoke_player()` delegation)
2. SEC primarily modifies **Coach phase** (validation additions)
3. Shared files have **additive, non-overlapping changes**

### Dependency Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           AUTOBUILD FLOW                                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  PreLoopQualityGates ─────►  PLAYER PHASE  ─────► COACH PHASE            │
│                              │                    │                       │
│                              │ TWD owns this      │ SEC owns this         │
│                              │ - invoke_player()  │ - Quick checks        │
│                              │ - task-work        │ - Full review         │
│                              │   delegation       │ - Honesty verify*     │
│                              │                    │ - Promise verify*     │
│                              │                    │                       │
│                              │ *TWD adds to       │                       │
│                              │  Coach phase too   │                       │
└───────────────────────────────────────────────────────────────────────────┘
```

### Merge Conflict Scenarios

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Both merge to main same day | LOW | Additive changes, auto-resolvable |
| TWD-008 and SEC-001 overlap on coach_validator.py | MEDIUM | Define clear boundaries (see below) |
| Agent definition sections | LOW | Different sections, no overlap |

---

## 3. Coach Decision Flow Impact

### Current Coach Decision Flow

```python
def validate(task_id, turn, task):
    # 1. Read task-work results
    results = read_quality_gate_results(task_id)

    # 2. Verify quality gates passed
    if not results["test_results"]["all_passed"]:
        return feedback(...)

    # 3. Run tests independently (trust but verify)
    test_result = run_tests_yourself()

    # 4. Validate requirements
    if not all_criteria_met(...):
        return feedback(...)

    # 5. Approve
    return approve()
```

### Proposed Unified Decision Flow

Both features add checks to the Coach validation. The recommended integration order:

```python
def validate(task_id, turn, task):
    # 1. Read task-work results (existing)
    results = read_quality_gate_results(task_id)

    # 2. Verify quality gates passed (existing)
    if not results["test_results"]["all_passed"]:
        return feedback(...)

    # ═══════════════════════════════════════════════════════
    # NEW: SEC - Quick Security Checks (always run, ~30s)
    # ═══════════════════════════════════════════════════════
    security_config = load_security_config(task)
    if security_config.level != "skip":
        quick_findings = run_quick_security_checks()
        critical = [f for f in quick_findings if f.severity == "critical"]
        if critical:
            return feedback("Critical security issues", findings=critical)

    # ═══════════════════════════════════════════════════════
    # NEW: SEC - Full Security Review (conditional, ~2-5min)
    # ═══════════════════════════════════════════════════════
    if should_run_full_review(task, security_config):
        full_findings = invoke_security_specialist(task)
        blocking = [f for f in full_findings if f.severity in ["critical", "high"]]
        if blocking:
            return feedback("Security review issues", findings=blocking)

    # 3. Run tests independently (existing - trust but verify)
    test_result = run_tests_yourself()

    # ═══════════════════════════════════════════════════════
    # NEW: TWD - Honesty Verification (TASK-TWD-008)
    # ═══════════════════════════════════════════════════════
    honesty_check = verify_player_claims(player_report, test_result)
    if honesty_check.discrepancies:
        critical_discrepancies = [d for d in honesty_check.discrepancies
                                  if d.severity == "critical"]
        if critical_discrepancies:
            return feedback("Honesty verification failed", discrepancies=critical_discrepancies)

    # 4. Validate requirements (existing)
    if not all_criteria_met(...):
        return feedback(...)

    # ═══════════════════════════════════════════════════════
    # NEW: TWD - Promise Verification (TASK-TWD-009)
    # ═══════════════════════════════════════════════════════
    if "completion_promise" in player_report:
        criteria_verification = verify_completion_promises(player_report, task)
        unverified = [c for c in criteria_verification if not c.coach_verified]
        if unverified:
            return feedback("Not all criteria verified", unverified=unverified)

    # 5. Approve (existing)
    return approve()
```

### Recommended Check Order

| Order | Check | Source | Rationale |
|-------|-------|--------|-----------|
| 1 | Quality gates (tests, coverage) | Existing | Fast, fundamental gate |
| 2 | Quick security checks | SEC | Fast (~30s), critical blocker |
| 3 | Full security review | SEC | Conditional, blocks on critical/high |
| 4 | Independent test verification | Existing | Trust-but-verify pattern |
| 5 | Honesty verification | TWD | Cross-reference Player claims |
| 6 | Requirements validation | Existing | Functional completeness |
| 7 | Promise verification | TWD | Criterion-level granularity |

**Rationale for Order**:
1. **Security before honesty**: Security is objective (patterns exist or not); honesty verification may re-run tests, so security should gate first
2. **Quick before full**: Fail fast on obvious issues
3. **Honesty after tests**: Uses test results to compare against Player claims
4. **Promise last**: Most granular check, assumes basics pass

### Key Integration Questions

#### Q: Should security block override honesty approval?
**A: YES** - Security checks are objective and critical. Even if Player is honest about test results, security vulnerabilities must block. Security gates run **before** honesty verification.

#### Q: How do security findings interact with honesty discrepancies?
**A: Independent concerns** - Security findings are about code vulnerabilities. Honesty discrepancies are about Player claim accuracy. Both should be checked, both can independently block approval.

```python
# Example: Player claims tests pass but there's a security issue
{
  "decision": "feedback",
  "security_issues": [{...}],      # From SEC
  "honesty_verified": True,         # From TWD
  "feedback": "Security issue found despite accurate test claims"
}
```

---

## 4. Player Phase Interactions

### Current Player Phase

```python
async def invoke_player(task_id, turn, requirements, feedback=None):
    prompt = build_player_prompt(...)
    await invoke_with_role(prompt, ...)  # Direct SDK invocation
    report = load_agent_report(task_id, turn, "player")
    return result
```

### TWD Changes to Player Phase

```python
async def invoke_player(task_id, turn, requirements, feedback=None, mode="tdd"):
    # NEW: Write feedback file if present
    if feedback and turn > 1:
        write_coach_feedback(task_id, feedback)

    # NEW: Delegate to task-work instead of direct SDK
    result = await invoke_task_work_implement(
        task_id=task_id,
        mode=mode,
        feedback_file=feedback_path if feedback else None,
    )
    return result
```

### SEC Impact on Player Phase

**NONE** - SEC adds security checks to Coach phase, not Player phase.

### Does task-work --implement-only include security checks?

**NO** - Current task-work phases:
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Test Enforcement
- Phase 5: Code Review

Security checks are **not** part of task-work. SEC adds them to the **Coach validation phase** after task-work completes.

### Should SEC checks happen in Player phase or Coach phase?

**COACH PHASE (Recommended)** because:
1. **Separation of concerns**: Player implements, Coach validates
2. **Independent verification**: Coach runs security checks on code Player wrote
3. **Avoids duplication**: If security checks were in task-work AND Coach, they'd run twice
4. **Matches existing pattern**: Coach already does independent test verification

---

## 5. Configuration Compatibility

### TWD Configuration

```yaml
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd  # NEW: tdd | standard
  player_model: claude-sonnet-4-5-20250929
  coach_model: claude-sonnet-4-5-20250929
```

### SEC Configuration

```yaml
autobuild:
  security:
    enabled: true
    default_level: standard  # strict | standard | minimal | skip
    quick_check_timeout: 30
    full_review_timeout: 300
    block_on_critical: true
    exclude_categories: [dos, rate-limiting]
    exclude_patterns: ["*.md", "*.test.*"]
```

### Compatibility Assessment

| Aspect | TWD | SEC | Compatible? |
|--------|-----|-----|-------------|
| Namespace | `autobuild.mode` | `autobuild.security.*` | ✅ Yes - different keys |
| Task frontmatter | None added | `security.level`, `security.skip_checks` | ✅ Yes - no overlap |
| Feature YAML | None added | `security.default_level`, `security.force_full_review` | ✅ Yes - no overlap |
| Environment vars | None | `GUARDKIT_SECURITY_SKIP` | ✅ Yes - no overlap |

**Conclusion**: Configurations are **fully orthogonal**. They can be merged without conflict.

### Merged Configuration Example

```yaml
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd                    # From TWD
  player_model: claude-sonnet-4-5-20250929
  coach_model: claude-sonnet-4-5-20250929
  security:                    # From SEC
    enabled: true
    default_level: standard
    quick_check_timeout: 30
    full_review_timeout: 300
```

---

## 6. Recommendations

### Implementation Order Recommendation

**PARALLEL DEVELOPMENT** with the following coordination:

```
WEEK 1-2: Both start in parallel
──────────────────────────────────────────────────────────────
TWD Wave 1-2                    SEC Wave 1-2
├── TWD-001: invoke_player()    ├── SEC-001: Quick checks
├── TWD-002: State bridging     ├── SEC-002: Config schema
├── TWD-003: Feedback           ├── SEC-003: Full review
└── TWD-004: CLI mode           └── SEC-004: Tag detection

WEEK 3: Merge preparation
──────────────────────────────────────────────────────────────
1. TWD merges first (modifies invoke_player, minimal Coach changes)
2. SEC merges second (adds Coach validation, no invoke_player changes)

WEEK 4: Quality enhancements + Integration
──────────────────────────────────────────────────────────────
TWD Wave 4-5                    SEC Wave 3
├── TWD-007: Escape hatch       ├── SEC-005: Tests
├── TWD-008: Honesty verify     └── SEC-006: Docs
└── TWD-009: Promise verify

INTEGRATION TASK (new): Unified Coach validation flow
└── Ensure security, honesty, and promise checks integrate cleanly
```

### Merge Strategy

| Phase | Action | Owner |
|-------|--------|-------|
| Pre-merge | Both features complete Waves 1-2 | Both teams |
| First merge | TWD merges Waves 1-3 to main | TWD team |
| Second merge | SEC merges Waves 1-2 to main | SEC team |
| Post-merge | Run integration tests | Both teams |
| Enhancement merge | TWD Waves 4-5 + SEC Wave 3 | Both teams |
| Final integration | Create unified validation flow task | Both teams |

### Design Conflicts Requiring Resolution

| Conflict | Severity | Resolution |
|----------|----------|------------|
| Coach validation order | MEDIUM | Use recommended order (security → honesty → promise) |
| Shared coach_validator.py | MEDIUM | Define clear method boundaries per feature |
| autobuild-coach.md sections | LOW | Additive sections, no structural conflict |

### New Integration Tasks to Add

#### TASK-INT-001: Unified Coach Validation Flow
**Priority**: HIGH
**Depends on**: TWD-008, TWD-009, SEC-001, SEC-003

```yaml
---
id: TASK-INT-001
title: Implement unified Coach validation flow integrating security and honesty checks
status: backlog
complexity: 4
dependencies: [TASK-TWD-008, TASK-TWD-009, TASK-SEC-001, TASK-SEC-003]
---

Integrate security checks, honesty verification, and promise verification
into a single coherent Coach validation flow per the integration review.

Acceptance Criteria:
- [ ] Security checks run before honesty verification
- [ ] Quick security checks always run (~30s)
- [ ] Full security review conditional on tags/config
- [ ] Honesty verification uses security-gated test results
- [ ] Promise verification runs after all other checks
- [ ] Clear priority ordering when multiple issues found
```

#### TASK-INT-002: Integration Tests for Combined Features
**Priority**: MEDIUM

```yaml
---
id: TASK-INT-002
title: Add integration tests for combined TWD + SEC functionality
status: backlog
complexity: 3
dependencies: [TASK-INT-001]
---

Create tests that exercise both features together:
- Task with security issues AND honesty discrepancy
- Task with security issues but honest Player
- Task with honest Player but security issues
- Full approval flow with both features enabled
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Merge conflicts in coach_validator.py | Medium | Low | Clear method ownership per feature |
| Validation order bugs | Low | Medium | Well-defined order in integration task |
| Performance regression (double test runs) | Low | Low | Honesty verification caches test results |
| Security checks timeout affecting loop | Low | Medium | Timeout handling in SEC-003 |

---

## 7. SOLID/DRY/YAGNI Assessment

### Single Responsibility Principle (SRP)

| Component | Assessment | Score |
|-----------|------------|-------|
| CoachValidator | GOOD - Each validation is a separate method | 8/10 |
| SecurityChecker | GOOD - Dedicated to security checks only | 9/10 |
| CoachVerifier (TWD) | GOOD - Dedicated to honesty verification | 9/10 |

**Overall SRP**: 8.5/10 - Both features maintain clear responsibilities.

### Open/Closed Principle (OCP)

| Component | Assessment | Score |
|-----------|------------|-------|
| Coach validation | GOOD - New checks added without modifying existing | 8/10 |
| Security config | GOOD - Extensible via configuration | 9/10 |

**Overall OCP**: 8.5/10 - Both features extend via configuration, not modification.

### Liskov Substitution Principle (LSP)

Not directly applicable - no inheritance hierarchies introduced.

### Interface Segregation Principle (ISP)

| Component | Assessment | Score |
|-----------|------------|-------|
| SecurityChecker | GOOD - Focused interface | 8/10 |
| CoachVerifier | GOOD - Focused interface | 8/10 |

**Overall ISP**: 8/10

### Dependency Inversion Principle (DIP)

| Component | Assessment | Score |
|-----------|------------|-------|
| SecurityChecker | MEDIUM - Could abstract file scanning | 7/10 |
| CoachVerifier | GOOD - Accepts worktree_path as dependency | 8/10 |

**Overall DIP**: 7.5/10

### DRY Assessment

| Pattern | Assessment | Score |
|---------|------------|-------|
| Test execution | CONCERN - Tests may run twice (task-work + honesty verification) | 6/10 |
| Configuration loading | GOOD - Single pattern for loading configs | 8/10 |
| Finding structures | GOOD - Both use similar SecurityFinding pattern | 8/10 |

**Overall DRY**: 7.5/10 - Minor concern about test duplication.

### YAGNI Assessment

| Feature | Assessment | Score |
|---------|------------|-------|
| Security levels (strict/standard/minimal/skip) | GOOD - Needed for flexibility | 9/10 |
| Honesty history tracking | MEDIUM - Useful but could defer | 7/10 |
| Promise verification | GOOD - Provides clear acceptance criteria mapping | 9/10 |

**Overall YAGNI**: 8.5/10

### Combined Score

| Principle | Score |
|-----------|-------|
| SRP | 8.5/10 |
| OCP | 8.5/10 |
| ISP | 8.0/10 |
| DIP | 7.5/10 |
| DRY | 7.5/10 |
| YAGNI | 8.5/10 |
| **Overall** | **8.1/10** |

---

## 8. Conclusion

### Summary

Both features are **well-designed** and **compatible** for parallel development. The primary integration point (Coach validation flow) requires explicit coordination but presents no architectural conflicts.

### Action Items

1. ✅ Document all shared/conflicting file modifications - **COMPLETE** (Section 1)
2. ✅ Identify execution order requirements - **COMPLETE** (Section 2)
3. ✅ Propose unified Coach decision flow - **COMPLETE** (Section 3)
4. ✅ Recommend merge strategy - **COMPLETE** (Section 6)
5. ✅ Flag design conflicts requiring resolution - **COMPLETE** (Section 6)
6. ✅ Estimate additional integration work - **COMPLETE** (2 new tasks proposed)

### Final Recommendation

**PROCEED WITH PARALLEL DEVELOPMENT**

- Both teams can start immediately
- Merge TWD first, then SEC (minimizes conflicts)
- Create TASK-INT-001 for unified validation flow after both features complete core tasks
- Run integration tests after final merge

---

## Review Metadata

| Field | Value |
|-------|-------|
| Review ID | TASK-REV-INT01 |
| Review Mode | architectural |
| Review Depth | standard |
| Duration | ~1.5 hours |
| Reviewer | architectural-reviewer agent |
| Date | 2026-01-01 |
| Overall Score | 8.1/10 (SOLID/DRY/YAGNI) |
