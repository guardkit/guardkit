---
acceptance_criteria:
- 20+ unit tests for quick checks (SecurityChecker)
- 10+ unit tests for configuration (SecurityConfig)
- 15+ unit tests for detection logic (should_run_full_review)
- 5+ integration tests for pre-loop security review (Phase 2.5C)
- 5+ integration tests for task-work quick scan (Phase 4.3)
- 3+ integration tests for Coach read-only security verification
- Test fixtures for vulnerable and safe code
- All tests pass
- Coverage greater than 90% for security modules
- Tests run in less than 60 seconds total
- 8+ tests for false positive filtering
- Tests for confidence threshold of 0.8
- Tests for exclusion categories including DOS and rate limiting
- Tests verify Coach does NOT invoke agents
complexity: 5
conductor_workspace: coach-security-wave3-1
created: 2026-01-24 15:00:00+00:00
dependencies:
- TASK-SEC-001
- TASK-SEC-002
- TASK-SEC-003
- TASK-SEC-004
estimated_minutes: 180
feature_id: FEAT-SEC
id: TASK-SEC-005
implementation_mode: task-work
parent_review: TASK-REV-SEC1
priority: high
status: design_approved
tags:
- security
- testing
- quality-gates
- pre-loop
- task-work
- autobuild
task_type: testing
title: Add security validation tests for revised architecture
updated: 2026-01-24 17:00:00+00:00
wave: 3
---

# TASK-SEC-005: Add Security Validation Tests for Revised Architecture

## Description

**REVISED ARCHITECTURE (from TASK-REV-4B0F)**: Tests must verify the new architecture where:
- Full security review runs in **pre-loop** (Phase 2.5C) via TaskWorkInterface
- Quick security scan runs in **task-work** (Phase 4.3)
- Coach only **reads** security results (no agent invocation)

Create comprehensive test coverage for all security validation features with the new integration points.

## Requirements

1. Unit tests for `SecurityChecker` class (quick checks)
2. Unit tests for `SecurityConfig` dataclass
3. Unit tests for `should_run_full_review()` function
4. Integration tests for **pre-loop** security review (Phase 2.5C)
5. Integration tests for **task-work** quick scan (Phase 4.3)
6. Integration tests for **Coach read-only** verification
7. Mock tests for security-specialist invocation via TaskWorkInterface
8. Test fixtures for vulnerable code samples
9. **[From TASK-REV-SEC2]** False positive filtering tests
10. **[From TASK-REV-SEC2]** Confidence threshold tests
11. **[From TASK-REV-SEC2]** Exclusion category tests (DOS, rate limiting, etc.)
12. **[From TASK-REV-4B0F]** Tests verifying Coach does NOT invoke agents

## Test Structure

```
tests/
├── unit/
│   ├── test_security_checker.py       # Quick checks
│   ├── test_security_config.py        # Configuration
│   ├── test_security_detection.py     # Tag/keyword detection (pre-loop)
│   ├── test_security_review.py        # Full review response parsing
│   └── test_security_filtering.py     # [From TASK-REV-SEC2] False positive filtering
├── integration/
│   ├── test_pre_loop_security.py      # Pre-loop Phase 2.5C tests (NEW)
│   ├── test_task_work_security.py     # Task-work Phase 4.3 tests (NEW)
│   └── test_coach_security.py         # Coach read-only verification (REVISED)
└── fixtures/
    └── security/
        ├── vulnerable_code/            # Samples with issues
        └── safe_code/                  # Clean samples
```

## Test Categories

### 1. Quick Check Tests (`test_security_checker.py`)

```python
class TestSecurityChecker:
    """Test quick security checks."""

    def test_detect_hardcoded_api_key(self, temp_worktree):
        """Hardcoded API_KEY should be detected as critical."""
        write_file(temp_worktree / "config.py", 'API_KEY = "sk-1234567890"')
        checker = SecurityChecker(temp_worktree)
        findings = checker.run_quick_checks()
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].check_id == "hardcoded-secrets"

    def test_detect_sql_injection(self, temp_worktree):
        """SQL string formatting should be detected as critical."""
        write_file(temp_worktree / "db.py",
                   'query = f"SELECT * FROM users WHERE id = {user_id}"')
        checker = SecurityChecker(temp_worktree)
        findings = checker.run_quick_checks()
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_detect_cors_wildcard(self, temp_worktree):
        """CORS wildcard should be detected as high."""
        write_file(temp_worktree / "main.py", 'allow_origins=["*"]')
        checker = SecurityChecker(temp_worktree)
        findings = checker.run_quick_checks()
        assert len(findings) == 1
        assert findings[0].severity == "high"

    def test_no_false_positives_on_comments(self, temp_worktree):
        """Comments mentioning secrets should not trigger."""
        write_file(temp_worktree / "docs.py",
                   '# API_KEY should be set in environment')
        checker = SecurityChecker(temp_worktree)
        findings = checker.run_quick_checks()
        assert len(findings) == 0

    def test_performance_under_30_seconds(self, large_worktree):
        """Checks should complete in under 30 seconds."""
        checker = SecurityChecker(large_worktree)
        start = time.time()
        checker.run_quick_checks()
        duration = time.time() - start
        assert duration < 30
```

### 2. Configuration Tests (`test_security_config.py`)

```python
class TestSecurityConfig:
    """Test security configuration parsing."""

    def test_parse_task_config(self):
        """Parse security config from task frontmatter."""
        task = {
            "security": {
                "level": "strict",
                "skip_checks": ["debug-mode"],
                "force_full_review": True
            }
        }
        config = SecurityConfig.from_task(task)
        assert config.level == SecurityLevel.STRICT
        assert "debug-mode" in config.skip_checks
        assert config.force_full_review is True

    def test_default_values(self):
        """Missing config uses defaults."""
        config = SecurityConfig.from_task({})
        assert config.level == SecurityLevel.STANDARD
        assert config.skip_checks == []
        assert config.force_full_review is False

    def test_config_merge_precedence(self):
        """Task config overrides feature and global."""
        task_config = SecurityConfig(level=SecurityLevel.STRICT)
        feature_config = SecurityConfig(level=SecurityLevel.MINIMAL)
        global_config = SecurityConfig(level=SecurityLevel.STANDARD)

        merged = SecurityConfig.merge(task_config, feature_config, global_config)
        assert merged.level == SecurityLevel.STRICT
```

### 3. Detection Tests (`test_security_detection.py`)

```python
class TestSecurityDetection:
    """Test should_run_full_review() logic."""

    def test_auth_tag_triggers_review(self):
        """Task with 'authentication' tag triggers full review."""
        task = {"tags": ["authentication"]}
        config = SecurityConfig()
        assert should_run_full_review(task, config) is True

    def test_login_keyword_triggers_review(self):
        """Task with 'login' in title triggers full review."""
        task = {"title": "Implement login endpoint", "tags": []}
        config = SecurityConfig()
        assert should_run_full_review(task, config) is True

    def test_force_config_overrides_tags(self):
        """force_full_review=True always triggers."""
        task = {"title": "Add UI button", "tags": ["ui"]}
        config = SecurityConfig(force_full_review=True)
        assert should_run_full_review(task, config) is True

    def test_skip_level_never_triggers(self):
        """level=skip never triggers full review."""
        task = {"tags": ["authentication", "security"]}
        config = SecurityConfig(level=SecurityLevel.SKIP)
        assert should_run_full_review(task, config) is False
```

### 4. False Positive Filtering Tests (`test_security_filtering.py`)

```python
# [From TASK-REV-SEC2] Tests based on Claude Code security-review filtering
class TestFalsePositiveFiltering:
    """Test that low-value findings are filtered."""

    def test_dos_findings_excluded(self):
        """DOS vulnerabilities should be filtered."""
        finding = SecurityFinding(
            check_id="test-1",
            severity="medium",
            confidence=0.9,
            description="Infinite loop could cause denial of service",
            file_path="app.py",
            line_number=42,
        )
        assert is_excluded(finding) is True

    def test_rate_limit_findings_excluded(self):
        """Rate limiting recommendations should be filtered."""
        finding = SecurityFinding(
            check_id="test-2",
            severity="low",
            confidence=0.85,
            description="Missing rate limiting on API endpoint",
            file_path="api.py",
            line_number=100,
        )
        assert is_excluded(finding) is True

    def test_resource_management_findings_excluded(self):
        """Resource management issues should be filtered."""
        finding = SecurityFinding(
            check_id="test-3",
            severity="medium",
            confidence=0.9,
            description="Memory leak in connection pool",
            file_path="db.py",
            line_number=50,
        )
        assert is_excluded(finding) is True

    def test_open_redirect_findings_excluded(self):
        """Open redirect vulnerabilities should be filtered."""
        finding = SecurityFinding(
            check_id="test-4",
            severity="medium",
            confidence=0.88,
            description="Open redirect vulnerability in login flow",
            file_path="auth.py",
            line_number=75,
        )
        assert is_excluded(finding) is True

    def test_real_vulnerabilities_not_excluded(self):
        """Real security issues should NOT be filtered."""
        finding = SecurityFinding(
            check_id="test-5",
            severity="critical",
            confidence=0.95,
            description="SQL injection via user input",
            file_path="query.py",
            line_number=30,
        )
        assert is_excluded(finding) is False

    def test_low_confidence_filtered(self):
        """Findings with confidence < 0.8 should be filtered."""
        finding = SecurityFinding(
            check_id="test-6",
            severity="high",
            confidence=0.6,
            description="Possible XSS vulnerability",
            file_path="template.py",
            line_number=20,
        )
        # Assuming filter_by_confidence function
        assert finding.confidence < 0.8

    def test_markdown_files_excluded(self):
        """Findings in .md files should be excluded."""
        finding = SecurityFinding(
            check_id="test-7",
            severity="high",
            confidence=0.9,
            description="Hardcoded API key",
            file_path="README.md",
            line_number=10,
        )
        # Based on file pattern exclusion
        assert should_exclude_file("README.md") is True
```

### 5. Pre-Loop Security Integration Tests (`test_pre_loop_security.py`)

```python
# [From TASK-REV-4B0F] Tests for revised pre-loop architecture
class TestPreLoopSecurityIntegration:
    """Test pre-loop security review (Phase 2.5C)."""

    async def test_security_tagged_task_triggers_review(self, pre_loop_gates):
        """Security-tagged task should trigger full review in pre-loop."""
        task = {"id": "TASK-001", "tags": ["authentication"]}

        result = await pre_loop_gates.execute("TASK-001", task)

        assert result.security_review_executed is True
        assert (pre_loop_gates.worktree_path / ".guardkit" / "security_review_results.json").exists()

    async def test_non_security_task_skips_review(self, pre_loop_gates):
        """Non-security task should skip full review."""
        task = {"id": "TASK-001", "tags": ["ui", "component"]}

        result = await pre_loop_gates.execute("TASK-001", task)

        assert result.security_review_executed is False

    async def test_security_review_via_task_work_interface(self, pre_loop_gates, mock_task_interface):
        """Full review should invoke security-specialist via TaskWorkInterface."""
        task = {"id": "TASK-001", "tags": ["authentication"]}

        await pre_loop_gates.execute("TASK-001", task)

        mock_task_interface.execute_security_review.assert_called_once()
```

### 6. Task-Work Security Integration Tests (`test_task_work_security.py`)

```python
# [From TASK-REV-4B0F] Tests for Phase 4.3 quick scan
class TestTaskWorkSecurityIntegration:
    """Test task-work quick security scan (Phase 4.3)."""

    async def test_quick_scan_runs_after_tests(self, task_work_executor):
        """Quick security scan should run after tests pass."""
        result = await task_work_executor.execute("TASK-001", {})

        assert "security" in result.task_work_results
        assert result.task_work_results["security"]["quick_check_passed"] is True

    async def test_critical_finding_blocks_progression(self, task_work_executor, temp_worktree):
        """Critical finding should block task progression."""
        write_file(temp_worktree / "config.py", 'API_KEY = "sk-12345"')

        result = await task_work_executor.execute("TASK-001", {})

        assert result.blocked is True
        assert result.block_reason == "Critical security vulnerabilities detected"

    async def test_results_written_to_task_work_results(self, task_work_executor):
        """Quick scan results should be in task_work_results.json."""
        result = await task_work_executor.execute("TASK-001", {})

        assert "findings_count" in result.task_work_results["security"]
        assert "critical_count" in result.task_work_results["security"]
```

### 7. Coach Read-Only Security Tests (`test_coach_security.py`)

```python
# [From TASK-REV-4B0F] Tests verifying Coach ONLY reads security results
class TestCoachSecurityReadOnly:
    """Test Coach validator reads (not generates) security results."""

    def test_coach_reads_security_from_results(self, coach_validator):
        """Coach should read security results from task_work_results.json."""
        task_work_results = {
            "security": {
                "quick_check_passed": True,
                "findings_count": 0,
                "critical_count": 0,
            }
        }

        status = coach_validator.verify_quality_gates(task_work_results)

        assert status.security_passed is True

    def test_coach_fails_on_critical_findings(self, coach_validator):
        """Coach should fail security gate on critical findings."""
        task_work_results = {
            "security": {
                "quick_check_passed": False,
                "critical_count": 1,
            }
        }

        status = coach_validator.verify_quality_gates(task_work_results)

        assert status.security_passed is False

    def test_coach_does_not_invoke_security_specialist(self, coach_validator):
        """CRITICAL: Coach must NOT invoke security-specialist agent."""
        # Verify Coach has no Task tool or agent invocation capability
        assert not hasattr(coach_validator, 'invoke_security_specialist')
        assert not hasattr(coach_validator, 'invoke_task')

        # Coach should only have read-only verification methods
        assert hasattr(coach_validator, 'verify_quality_gates')

    def test_coach_handles_missing_security_results(self, coach_validator):
        """Coach should handle missing security results gracefully."""
        task_work_results = {}  # No security key

        status = coach_validator.verify_quality_gates(task_work_results)

        # Default to passed when no security results (backward compatibility)
        assert status.security_passed is True
```

## Acceptance Criteria

- [ ] 20+ unit tests for quick checks
- [ ] 10+ unit tests for configuration
- [ ] 15+ unit tests for detection logic
- [ ] 5+ integration tests for pre-loop security review (Phase 2.5C)
- [ ] 5+ integration tests for task-work quick scan (Phase 4.3)
- [ ] 3+ integration tests for Coach read-only verification
- [ ] Test fixtures for vulnerable/safe code
- [ ] All tests pass
- [ ] Coverage > 90% for security modules
- [ ] Tests run in < 60 seconds total
- [ ] **[From TASK-REV-SEC2]** 8+ tests for false positive filtering
- [ ] **[From TASK-REV-SEC2]** Tests for confidence threshold (0.8)
- [ ] **[From TASK-REV-SEC2]** Tests for exclusion categories (DOS, rate limiting, etc.)
- [ ] **[From TASK-REV-4B0F]** Tests verify Coach does NOT invoke agents

## Test Fixtures

### Vulnerable Code Samples
```
fixtures/security/vulnerable_code/
├── hardcoded_secrets.py    # API_KEY = "xxx"
├── sql_injection.py        # f"SELECT {x}"
├── command_injection.py    # subprocess.run(f"...")
├── cors_wildcard.py        # allow_origins=["*"]
├── debug_mode.py           # DEBUG = True
└── eval_exec.py            # eval(user_input)
```

### Safe Code Samples
```
fixtures/security/safe_code/
├── env_secrets.py          # os.environ["API_KEY"]
├── parameterized_sql.py    # cursor.execute("SELECT ?", (x,))
├── safe_subprocess.py      # subprocess.run(["ls", "-la"])
├── cors_explicit.py        # allow_origins=["https://..."]
├── debug_conditional.py    # DEBUG = os.getenv("DEBUG", "false")
└── no_eval.py              # ast.literal_eval(...)
```

## Out of Scope

- Actual security-specialist agent testing (mocked)
- Performance benchmarking beyond basic checks
- Fuzzing/property-based testing

## Key Architecture Verification

**[From TASK-REV-4B0F]** Tests MUST verify:

1. **Pre-loop owns security review**: `PreLoopQualityGates.execute()` calls `TaskWorkInterface.execute_security_review()`
2. **Task-work owns quick scan**: Phase 4.3 runs `SecurityChecker.run_quick_checks()`
3. **Coach is read-only**: `CoachValidator.verify_quality_gates()` only reads `task_work_results["security"]`
4. **No agent invocation in Coach**: Coach has NO Task tool, NO `invoke_task()` method

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- False positive filtering tests for DOS, rate limiting, resource management
- Confidence threshold tests (filter below 0.8)
- File pattern exclusion tests (markdown, test files)