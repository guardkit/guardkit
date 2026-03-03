"""Tests for secret redaction pipeline.

Covers all acceptance criteria for TASK-INST-003:
- Standard secret patterns detected and replaced with [REDACTED]
- cmd, stdout_tail, stderr_tail all redacted before event emission
- Tool names sanitised against shell metacharacters
- Non-secret content preserved unchanged
- Redaction patterns configurable via list
- No secret values appear in emitted events
- Edge cases: empty strings, overlapping patterns, partial matches
"""

from __future__ import annotations

import re

import pytest

from guardkit.orchestrator.instrumentation.redaction import (
    DEFAULT_REDACTION_PATTERNS,
    SecretRedactor,
    redact_tool_exec_event,
    sanitise_tool_name,
)
from guardkit.orchestrator.instrumentation.schemas import ToolExecEvent


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def redactor() -> SecretRedactor:
    """Default SecretRedactor with standard patterns."""
    return SecretRedactor()


@pytest.fixture
def base_event_fields() -> dict:
    """Minimal valid fields for a ToolExecEvent."""
    return {
        "run_id": "run-test-001",
        "task_id": "TASK-TEST",
        "agent_role": "player",
        "attempt": 1,
        "timestamp": "2026-03-02T12:00:00Z",
        "tool_name": "bash",
        "exit_code": 0,
        "latency_ms": 100.0,
    }


# ============================================================================
# DEFAULT_REDACTION_PATTERNS Tests
# ============================================================================


class TestDefaultPatterns:
    """Tests for DEFAULT_REDACTION_PATTERNS list."""

    def test_default_patterns_is_list(self) -> None:
        """DEFAULT_REDACTION_PATTERNS is a non-empty list of strings."""
        assert isinstance(DEFAULT_REDACTION_PATTERNS, list)
        assert len(DEFAULT_REDACTION_PATTERNS) > 0

    def test_default_patterns_are_valid_regex(self) -> None:
        """All default patterns are valid regular expressions."""
        for pattern in DEFAULT_REDACTION_PATTERNS:
            assert isinstance(pattern, str)
            re.compile(pattern)  # raises re.error if invalid


# ============================================================================
# SecretRedactor Core Tests
# ============================================================================


class TestSecretRedactorInit:
    """Tests for SecretRedactor initialization."""

    def test_default_patterns_used(self) -> None:
        """SecretRedactor uses DEFAULT_REDACTION_PATTERNS when none specified."""
        redactor = SecretRedactor()
        assert len(redactor.patterns) == len(DEFAULT_REDACTION_PATTERNS)

    def test_custom_patterns(self) -> None:
        """SecretRedactor accepts custom patterns list."""
        custom = [r"CUSTOM_SECRET_\w+"]
        redactor = SecretRedactor(patterns=custom)
        assert len(redactor.patterns) == 1

    def test_empty_patterns_list(self) -> None:
        """SecretRedactor with empty patterns list does no redaction."""
        redactor = SecretRedactor(patterns=[])
        assert redactor.redact("sk-1234567890abcdef") == "sk-1234567890abcdef"


# ============================================================================
# API Key Pattern Tests
# ============================================================================


class TestAPIKeyRedaction:
    """Tests for API key detection and redaction."""

    def test_openai_sk_key(self, redactor: SecretRedactor) -> None:
        """OpenAI-style sk- keys are redacted."""
        text = "export OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz"
        result = redactor.redact(text)
        assert "sk-1234567890" not in result
        assert "[REDACTED]" in result

    def test_aws_akia_key(self, redactor: SecretRedactor) -> None:
        """AWS AKIA keys are redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED]" in result

    def test_github_personal_token(self, redactor: SecretRedactor) -> None:
        """GitHub personal access tokens (ghp_) are redacted."""
        text = "git clone https://ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcde12@github.com/repo"
        result = redactor.redact(text)
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result
        assert "[REDACTED]" in result

    def test_github_server_token(self, redactor: SecretRedactor) -> None:
        """GitHub server-to-server tokens (ghs_) are redacted."""
        text = "GITHUB_TOKEN=ghs_ABCDEFGHIJKLMNOPQRSTUVWXYZab"
        result = redactor.redact(text)
        assert "ghs_ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result
        assert "[REDACTED]" in result


# ============================================================================
# Bearer Token Pattern Tests
# ============================================================================


class TestBearerTokenRedaction:
    """Tests for Bearer token detection and redaction."""

    def test_bearer_jwt_token(self, redactor: SecretRedactor) -> None:
        """Bearer JWT tokens are redacted."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = redactor.redact(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED]" in result

    def test_bearer_case_insensitive(self, redactor: SecretRedactor) -> None:
        """Bearer token matching is case-insensitive for 'Bearer'."""
        text = "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = redactor.redact(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED]" in result


# ============================================================================
# Password/Environment Variable Pattern Tests
# ============================================================================


class TestPasswordRedaction:
    """Tests for password-in-environment-variable detection and redaction."""

    def test_password_env_var(self, redactor: SecretRedactor) -> None:
        """PASSWORD=value patterns are redacted."""
        text = "DATABASE_PASSWORD=mysupersecretpassword123"
        result = redactor.redact(text)
        assert "mysupersecretpassword123" not in result
        assert "[REDACTED]" in result

    def test_db_pass_env_var(self, redactor: SecretRedactor) -> None:
        """DB_PASS=value patterns are redacted."""
        text = "DB_PASS=s3cr3t_v@lue!"
        result = redactor.redact(text)
        assert "s3cr3t_v@lue!" not in result
        assert "[REDACTED]" in result

    def test_secret_env_var(self, redactor: SecretRedactor) -> None:
        """SECRET=value patterns are redacted."""
        text = "APP_SECRET=abcdef123456"
        result = redactor.redact(text)
        assert "abcdef123456" not in result
        assert "[REDACTED]" in result


# ============================================================================
# Generic Token Pattern Tests
# ============================================================================


class TestGenericTokenRedaction:
    """Tests for generic token= and api_key= patterns."""

    def test_token_equals_pattern(self, redactor: SecretRedactor) -> None:
        """token=value patterns are redacted."""
        text = "curl https://api.example.com?token=abc123def456"
        result = redactor.redact(text)
        assert "abc123def456" not in result
        assert "[REDACTED]" in result

    def test_api_key_equals_pattern(self, redactor: SecretRedactor) -> None:
        """api_key=value patterns are redacted."""
        text = "curl https://api.example.com?api_key=mykey12345678"
        result = redactor.redact(text)
        assert "mykey12345678" not in result
        assert "[REDACTED]" in result


# ============================================================================
# URL Credential Pattern Tests
# ============================================================================


class TestURLCredentialRedaction:
    """Tests for base64/plaintext credentials in URLs."""

    def test_url_with_credentials(self, redactor: SecretRedactor) -> None:
        """user:pass@host in URLs are redacted."""
        text = "psql postgresql://admin:s3cretPass@db.example.com:5432/mydb"
        result = redactor.redact(text)
        assert "admin:s3cretPass" not in result
        assert "[REDACTED]" in result

    def test_url_with_complex_password(self, redactor: SecretRedactor) -> None:
        """Complex passwords in URLs are redacted."""
        text = "https://user:p%40ssw0rd@api.example.com/resource"
        result = redactor.redact(text)
        assert "user:p%40ssw0rd" not in result
        assert "[REDACTED]" in result


# ============================================================================
# Tool Name Sanitisation Tests
# ============================================================================


class TestSanitiseToolName:
    """Tests for tool name sanitisation against shell metacharacters."""

    def test_clean_tool_name_unchanged(self) -> None:
        """Clean tool names pass through unchanged."""
        assert sanitise_tool_name("bash") == "bash"
        assert sanitise_tool_name("python3") == "python3"
        assert sanitise_tool_name("npm-run") == "npm-run"

    def test_semicolon_removed(self) -> None:
        """Semicolons are stripped from tool names."""
        assert ";" not in sanitise_tool_name("bash;rm -rf /")

    def test_pipe_removed(self) -> None:
        """Pipe characters are stripped from tool names."""
        assert "|" not in sanitise_tool_name("tool|evil")

    def test_ampersand_removed(self) -> None:
        """Ampersands are stripped from tool names."""
        assert "&" not in sanitise_tool_name("tool&bg")

    def test_dollar_removed(self) -> None:
        """Dollar signs are stripped from tool names."""
        assert "$" not in sanitise_tool_name("tool$var")

    def test_backtick_removed(self) -> None:
        """Backticks are stripped from tool names."""
        assert "`" not in sanitise_tool_name("tool`cmd`")

    def test_redirect_chars_removed(self) -> None:
        """Redirect characters (> <) are stripped."""
        assert ">" not in sanitise_tool_name("tool>file")
        assert "<" not in sanitise_tool_name("tool<file")

    def test_parentheses_removed(self) -> None:
        """Parentheses are stripped from tool names."""
        assert "(" not in sanitise_tool_name("tool(sub)")
        assert ")" not in sanitise_tool_name("tool(sub)")

    def test_all_metacharacters_at_once(self) -> None:
        """All shell metacharacters removed in a single pass."""
        dirty = "bash;|&$`><()"
        result = sanitise_tool_name(dirty)
        for char in ";|&$`><()":
            assert char not in result
        assert "bash" in result


# ============================================================================
# Non-Secret Content Preservation Tests
# ============================================================================


class TestContentPreservation:
    """Tests that non-secret content is preserved unchanged."""

    def test_plain_text_unchanged(self, redactor: SecretRedactor) -> None:
        """Plain text without secrets passes through unchanged."""
        text = "Running pytest tests/ -v --cov=src"
        assert redactor.redact(text) == text

    def test_empty_string_unchanged(self, redactor: SecretRedactor) -> None:
        """Empty string is preserved."""
        assert redactor.redact("") == ""

    def test_normal_output_preserved(self, redactor: SecretRedactor) -> None:
        """Normal test output is preserved."""
        text = "PASSED tests/test_something.py::test_ok - 3 passed in 1.2s"
        assert redactor.redact(text) == text

    def test_mixed_content_only_secrets_redacted(self, redactor: SecretRedactor) -> None:
        """Only secret portions are redacted; surrounding text preserved."""
        text = "Connecting to DB with PASSWORD=hunter2 on port 5432"
        result = redactor.redact(text)
        assert "hunter2" not in result
        assert "Connecting to DB with" in result
        assert "on port 5432" in result

    def test_multiline_preserves_non_secret_lines(self, redactor: SecretRedactor) -> None:
        """In multiline text, non-secret lines are unmodified."""
        text = "line1: safe\nline2: token=secret123\nline3: also safe"
        result = redactor.redact(text)
        assert "line1: safe" in result
        assert "line3: also safe" in result
        assert "secret123" not in result


# ============================================================================
# ToolExecEvent Redaction Tests
# ============================================================================


class TestRedactToolExecEvent:
    """Tests for redact_tool_exec_event integration function."""

    def test_cmd_field_redacted(self, base_event_fields: dict) -> None:
        """cmd field has secrets redacted."""
        event = ToolExecEvent(
            **base_event_fields,
            cmd="curl -H 'Authorization: Bearer eyJtoken123' https://api.com",
            stdout_tail="OK",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event)
        assert "eyJtoken123" not in redacted.cmd
        assert "[REDACTED]" in redacted.cmd

    def test_stdout_tail_redacted(self, base_event_fields: dict) -> None:
        """stdout_tail field has secrets redacted."""
        event = ToolExecEvent(
            **base_event_fields,
            cmd="env",
            stdout_tail="DATABASE_PASSWORD=supersecret",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event)
        assert "supersecret" not in redacted.stdout_tail
        assert "[REDACTED]" in redacted.stdout_tail

    def test_stderr_tail_redacted(self, base_event_fields: dict) -> None:
        """stderr_tail field has secrets redacted."""
        event = ToolExecEvent(
            **base_event_fields,
            cmd="deploy",
            stdout_tail="",
            stderr_tail="Error: token=leaked_secret_value",
        )
        redacted = redact_tool_exec_event(event)
        assert "leaked_secret_value" not in redacted.stderr_tail
        assert "[REDACTED]" in redacted.stderr_tail

    def test_tool_name_sanitised(self, base_event_fields: dict) -> None:
        """tool_name field is sanitised against shell metacharacters."""
        fields = {**base_event_fields, "tool_name": "bash;rm -rf /"}
        event = ToolExecEvent(
            **fields,
            cmd="echo hello",
            stdout_tail="hello",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event)
        assert ";" not in redacted.tool_name

    def test_non_redacted_fields_preserved(self, base_event_fields: dict) -> None:
        """Fields other than cmd/stdout_tail/stderr_tail/tool_name are preserved."""
        event = ToolExecEvent(
            **base_event_fields,
            cmd="safe command",
            stdout_tail="safe output",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event)
        assert redacted.run_id == "run-test-001"
        assert redacted.task_id == "TASK-TEST"
        assert redacted.exit_code == 0
        assert redacted.latency_ms == 100.0
        assert redacted.attempt == 1

    def test_returns_new_event_not_mutated_original(self, base_event_fields: dict) -> None:
        """redact_tool_exec_event returns a new event, does not mutate original."""
        original_cmd = "export API_KEY=sk-1234567890abcdef"
        event = ToolExecEvent(
            **base_event_fields,
            cmd=original_cmd,
            stdout_tail="",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event)
        # Original should be unchanged
        assert event.cmd == original_cmd
        # Redacted should be different
        assert "sk-1234567890" not in redacted.cmd

    def test_custom_patterns_via_redactor(self, base_event_fields: dict) -> None:
        """Custom redactor patterns can be passed through."""
        custom_redactor = SecretRedactor(patterns=[r"CUSTOM_\w+"])
        event = ToolExecEvent(
            **base_event_fields,
            cmd="echo CUSTOM_SECRET_VALUE",
            stdout_tail="",
            stderr_tail="",
        )
        redacted = redact_tool_exec_event(event, redactor=custom_redactor)
        assert "CUSTOM_SECRET_VALUE" not in redacted.cmd
        assert "[REDACTED]" in redacted.cmd

    def test_all_three_fields_redacted_simultaneously(self, base_event_fields: dict) -> None:
        """Secrets in cmd, stdout_tail, and stderr_tail are all redacted."""
        event = ToolExecEvent(
            **base_event_fields,
            cmd="curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig'",
            stdout_tail="token=output_secret_value",
            stderr_tail="AKIA1234567890ABCDEF",
        )
        redacted = redact_tool_exec_event(event)
        assert "eyJhbGciOiJIUzI1NiJ9" not in redacted.cmd
        assert "output_secret_value" not in redacted.stdout_tail
        assert "AKIA1234567890ABCDEF" not in redacted.stderr_tail


# ============================================================================
# Configurable Patterns Tests
# ============================================================================


class TestConfigurablePatterns:
    """Tests for configurable redaction patterns."""

    def test_add_custom_pattern(self) -> None:
        """Custom pattern detects project-specific secrets."""
        custom = [r"PROJ_[A-Z0-9]{16}"]
        redactor = SecretRedactor(patterns=custom)
        text = "key=PROJ_ABCD1234EFGH5678"
        result = redactor.redact(text)
        assert "PROJ_ABCD1234EFGH5678" not in result
        assert "[REDACTED]" in result

    def test_extend_default_patterns(self) -> None:
        """Custom patterns can be combined with defaults."""
        extra = DEFAULT_REDACTION_PATTERNS + [r"PROJ_[A-Z0-9]{16}"]
        redactor = SecretRedactor(patterns=extra)
        # Default pattern still works
        text1 = "key=sk-abcdef1234567890"
        assert "[REDACTED]" in redactor.redact(text1)
        # Custom pattern also works
        text2 = "key=PROJ_ABCD1234EFGH5678"
        assert "[REDACTED]" in redactor.redact(text2)

    def test_no_secrets_emitted_comprehensive(self, base_event_fields: dict) -> None:
        """Comprehensive test: no secret values appear in emitted event dump."""
        secrets = [
            "sk-abcdef1234567890abcdef1234",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_ABCDEFabcdef1234567890",
            "Bearer eyJhbGciOiJIUzI1NiJ9.test.sig",
        ]
        event = ToolExecEvent(
            **base_event_fields,
            cmd=f"curl -H 'Authorization: {secrets[3]}' https://api.com",
            stdout_tail=f"key={secrets[0]} access={secrets[1]}",
            stderr_tail=f"token: {secrets[2]}",
        )
        redacted = redact_tool_exec_event(event)
        dumped = redacted.model_dump()
        dump_str = str(dumped)
        for secret in secrets:
            # Extract the core secret part (skip "Bearer " prefix for that check)
            core = secret.replace("Bearer ", "")
            assert core not in dump_str, f"Secret leaked in emitted event: {core[:10]}..."


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_multiple_secrets_in_same_string(self, redactor: SecretRedactor) -> None:
        """Multiple different secrets in one string are all redacted."""
        text = "KEY1=sk-abc123456789 KEY2=AKIAIOSFODNN7EXAMPLE"
        result = redactor.redact(text)
        assert "sk-abc123456789" not in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_repeated_secret_pattern(self, redactor: SecretRedactor) -> None:
        """Same secret appearing multiple times is redacted everywhere."""
        text = "first sk-abc123456789 second sk-abc123456789"
        result = redactor.redact(text)
        assert "sk-abc123456789" not in result

    def test_very_long_string(self, redactor: SecretRedactor) -> None:
        """Redaction works on very long strings without error."""
        safe_prefix = "A" * 10000
        text = f"{safe_prefix} PASSWORD=longsecrethidden"
        result = redactor.redact(text)
        assert "longsecrethidden" not in result
        assert safe_prefix in result

    def test_unicode_content_preserved(self, redactor: SecretRedactor) -> None:
        """Unicode characters in non-secret content are preserved."""
        text = "Output: success \u2714 token=leaked123"
        result = redactor.redact(text)
        assert "\u2714" in result
        assert "leaked123" not in result

    def test_newlines_in_text(self, redactor: SecretRedactor) -> None:
        """Secrets spanning or near newlines are still caught."""
        text = "line1\nPASSWORD=secret123\nline3"
        result = redactor.redact(text)
        assert "secret123" not in result
        assert "line1" in result
        assert "line3" in result
