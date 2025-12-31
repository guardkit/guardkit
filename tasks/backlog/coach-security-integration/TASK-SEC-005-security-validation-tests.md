---
id: TASK-SEC-005
title: Add security validation tests
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T14:45:00Z
priority: high
tags: [security, testing, quality-gates, autobuild]
complexity: 5
parent_review: TASK-REV-SEC1
implementation_mode: task-work
estimated_hours: 2-3
wave: 3
conductor_workspace: coach-security-wave3-1
dependencies: [TASK-SEC-001, TASK-SEC-002, TASK-SEC-003, TASK-SEC-004]
---

# TASK-SEC-005: Add Security Validation Tests

## Description

Create comprehensive test coverage for all security validation features: quick checks, configuration, full review invocation, and tag detection.

## Requirements

1. Unit tests for `SecurityChecker` class
2. Unit tests for `SecurityConfig` dataclass
3. Unit tests for `should_run_full_review()` function
4. Integration tests for Coach validation with security
5. Mock tests for security-specialist invocation
6. Test fixtures for vulnerable code samples

## Test Structure

```
tests/
├── unit/
│   ├── test_security_checker.py       # Quick checks
│   ├── test_security_config.py        # Configuration
│   ├── test_security_detection.py     # Tag/keyword detection
│   └── test_security_invocation.py    # Full review (mocked)
├── integration/
│   └── test_coach_security.py         # Coach + security flow
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

### 4. Integration Tests (`test_coach_security.py`)

```python
class TestCoachSecurityIntegration:
    """Test Coach validator with security checks."""

    async def test_critical_finding_blocks_approval(self, coach_validator):
        """Critical security finding should block approval."""
        # Create worktree with hardcoded secret
        write_file(coach_validator.worktree_path / "config.py",
                   'SECRET_KEY = "insecure-key-123"')

        task = {"id": "TASK-001", "acceptance_criteria": []}
        result = await coach_validator.validate("TASK-001", 1, task)

        assert result.decision == "feedback"
        assert any("security" in str(i) for i in result.issues)

    async def test_clean_code_passes_security(self, coach_validator):
        """Clean code should pass security checks."""
        # Create worktree with safe code
        write_file(coach_validator.worktree_path / "config.py",
                   'SECRET_KEY = os.environ["SECRET_KEY"]')

        task = {"id": "TASK-001", "acceptance_criteria": []}
        # Mock task-work results as passing
        mock_task_work_results(coach_validator, passing=True)

        result = await coach_validator.validate("TASK-001", 1, task)

        assert result.decision == "approve"
```

## Acceptance Criteria

- [ ] 20+ unit tests for quick checks
- [ ] 10+ unit tests for configuration
- [ ] 15+ unit tests for detection logic
- [ ] 5+ integration tests for Coach flow
- [ ] Test fixtures for vulnerable/safe code
- [ ] All tests pass
- [ ] Coverage > 90% for security modules
- [ ] Tests run in < 60 seconds total

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
