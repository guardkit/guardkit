"""
Tests for the shared slug generation utility.

Coverage Target: 100%
"""

import sys
from pathlib import Path

import pytest

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from slug_utils import slugify_task_name


class TestSlugifyBasic:
    """Tests for basic slug conversion behavior."""

    def test_basic_conversion(self):
        assert slugify_task_name("Create auth service") == "create-auth-service"

    def test_uppercase_to_lowercase(self):
        assert slugify_task_name("Create AUTH Service") == "create-auth-service"

    def test_numbers_preserved(self):
        assert slugify_task_name("Phase 1 setup") == "phase-1-setup"

    def test_version_numbers(self):
        assert slugify_task_name("Add OAuth 2.0 Provider") == "add-oauth-2-0-provider"


class TestSlugifySpecialCharacters:
    """Tests for special character handling."""

    def test_punctuation_removed(self):
        assert slugify_task_name("Fix bug! (urgent)") == "fix-bug-urgent"

    def test_underscores_replaced(self):
        assert slugify_task_name("snake_case_name") == "snake-case-name"

    def test_slashes_replaced(self):
        assert slugify_task_name("path/to/thing") == "path-to-thing"

    def test_mixed_special_chars(self):
        assert slugify_task_name("Update docs & tests") == "update-docs-tests"

    def test_brackets_removed(self):
        assert slugify_task_name("Bug #123 [Critical]") == "bug-123-critical"

    def test_colons_removed(self):
        assert slugify_task_name("TASK-123: Implement API") == "task-123-implement-api"


class TestSlugifyWhitespace:
    """Tests for whitespace handling."""

    def test_multiple_spaces_collapsed(self):
        assert slugify_task_name("Create   auth   service") == "create-auth-service"

    def test_leading_trailing_spaces(self):
        assert slugify_task_name("  Create auth service  ") == "create-auth-service"

    def test_tabs_replaced(self):
        assert slugify_task_name("Create\tauth\tservice") == "create-auth-service"


class TestSlugifyEdgeCases:
    """Tests for edge case inputs."""

    def test_empty_string(self):
        assert slugify_task_name("") == ""

    def test_only_special_chars(self):
        assert slugify_task_name("!!!@@@###") == ""

    def test_single_word(self):
        assert slugify_task_name("hello") == "hello"

    def test_single_number(self):
        assert slugify_task_name("42") == "42"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify_task_name("---start-end---") == "start-end"

    def test_consecutive_hyphens_collapsed(self):
        assert slugify_task_name("a---b---c") == "a-b-c"


class TestSlugifyMaxLength:
    """Tests for length limiting behavior."""

    def test_default_max_length_is_50(self):
        long_name = "a " * 40  # 80 chars of "a-a-a-..."
        result = slugify_task_name(long_name)
        assert len(result) <= 50

    def test_custom_max_length(self):
        long_name = "a " * 40
        result = slugify_task_name(long_name, max_length=20)
        assert len(result) <= 20

    def test_no_length_limit_with_none(self):
        long_name = "a " * 60  # produces "a-a-a-..." of 119 chars
        result = slugify_task_name(long_name, max_length=None)
        assert len(result) > 50

    def test_no_length_limit_with_zero(self):
        long_name = "a " * 60
        result = slugify_task_name(long_name, max_length=0)
        assert len(result) > 50

    def test_truncation_strips_trailing_hyphen(self):
        # "this-is-a-very-long-" should not end with hyphen after truncation
        name = "this is a very long task name that exceeds the limit"
        result = slugify_task_name(name, max_length=20)
        assert not result.endswith("-")
        assert len(result) <= 20

    def test_short_name_not_truncated(self):
        result = slugify_task_name("short")
        assert result == "short"

    def test_exact_length_not_truncated(self):
        # Exactly 50 chars slug should not be truncated
        name = "a" * 50
        result = slugify_task_name(name)
        assert result == "a" * 50
        assert len(result) == 50


class TestSlugifyRealWorldExamples:
    """Tests with realistic task names from GuardKit usage."""

    def test_feature_task(self):
        assert slugify_task_name("Implement user authentication") == "implement-user-authentication"

    def test_bug_fix(self):
        assert slugify_task_name("Fix login validation error") == "fix-login-validation-error"

    def test_refactor(self):
        assert slugify_task_name("Unify slug generation into shared utility") == "unify-slug-generation-into-shared-utility"

    def test_review_task(self):
        result = slugify_task_name("Review: Feature plan path generation bug investigation")
        assert len(result) <= 50
        assert not result.endswith("-")
