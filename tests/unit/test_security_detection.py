"""
TDD RED Phase Tests for Security Detection Module (TASK-SEC-004)

Tests for pre-loop security tag and keyword detection that determines whether
a task requires full security review before implementation begins.

Test Categories:
- Tag Detection: Direct tag matching against SECURITY_TAGS
- Keyword Detection: Title and description keyword matching
- Configuration Override: Explicit force/skip flags and security levels
- Edge Cases: Empty data, case variations, missing metadata
"""

import pytest
from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
from guardkit.orchestrator.quality_gates.security_detection import (
    SECURITY_TAGS,
    HIGH_RISK_CATEGORIES,
    SECURITY_KEYWORDS,
    should_run_full_review
)


class TestSecurityTagsConstants:
    """Test that SECURITY_TAGS constant contains required categories."""

    def test_security_tags_contains_injection_attacks(self):
        """SECURITY_TAGS must include injection attack tags."""
        injection_tags = {
            'injection', 'sql', 'command', 'ldap', 'xpath', 'xxe'
        }
        assert injection_tags.issubset(SECURITY_TAGS), \
            f"Missing injection tags: {injection_tags - SECURITY_TAGS}"

    def test_security_tags_contains_authentication_authorization(self):
        """SECURITY_TAGS must include authentication and authorization tags."""
        auth_tags = {
            'authentication', 'authorization', 'security', 'auth',
            'session', 'token', 'jwt', 'oauth', 'oauth2',
            'rbac', 'acl', 'permissions', 'roles'
        }
        assert auth_tags.issubset(SECURITY_TAGS), \
            f"Missing auth tags: {auth_tags - SECURITY_TAGS}"

    def test_security_tags_contains_data_exposure(self):
        """SECURITY_TAGS must include data exposure tags."""
        exposure_tags = {'secrets', 'credentials', 'pii', 'gdpr'}
        assert exposure_tags.issubset(SECURITY_TAGS), \
            f"Missing exposure tags: {exposure_tags - SECURITY_TAGS}"

    def test_security_tags_contains_cryptography(self):
        """SECURITY_TAGS must include cryptography tags."""
        crypto_tags = {'crypto', 'encryption', 'hashing'}
        assert crypto_tags.issubset(SECURITY_TAGS), \
            f"Missing crypto tags: {crypto_tags - SECURITY_TAGS}"

    def test_security_tags_contains_input_validation(self):
        """SECURITY_TAGS must include input validation tags."""
        validation_tags = {'validation', 'input', 'sanitization'}
        assert validation_tags.issubset(SECURITY_TAGS), \
            f"Missing validation tags: {validation_tags - SECURITY_TAGS}"

    def test_security_tags_contains_configuration_security(self):
        """SECURITY_TAGS must include configuration security tags."""
        config_tags = {'cors', 'csrf', 'headers'}
        assert config_tags.issubset(SECURITY_TAGS), \
            f"Missing config tags: {config_tags - SECURITY_TAGS}"

    def test_security_tags_contains_code_execution(self):
        """SECURITY_TAGS must include code execution tags."""
        execution_tags = {'deserialization', 'pickle'}
        assert execution_tags.issubset(SECURITY_TAGS), \
            f"Missing execution tags: {execution_tags - SECURITY_TAGS}"

    def test_security_tags_contains_xss(self):
        """SECURITY_TAGS must include XSS tags."""
        assert 'xss' in SECURITY_TAGS, "Missing XSS tag"

    def test_security_tags_contains_sensitive_operations(self):
        """SECURITY_TAGS must include sensitive operation tags."""
        sensitive_tags = {'payment', 'checkout', 'billing'}
        assert sensitive_tags.issubset(SECURITY_TAGS), \
            f"Missing sensitive tags: {sensitive_tags - SECURITY_TAGS}"

    def test_security_tags_has_minimum_count(self):
        """SECURITY_TAGS must contain at least 25 tags."""
        assert len(SECURITY_TAGS) >= 25, \
            f"Expected ≥25 tags, got {len(SECURITY_TAGS)}"


class TestHighRiskCategoriesConstant:
    """Test that HIGH_RISK_CATEGORIES constant contains critical tags."""

    def test_high_risk_contains_auth_categories(self):
        """HIGH_RISK_CATEGORIES must include auth-related tags."""
        auth_categories = {'authentication', 'authorization', 'auth'}
        assert auth_categories.issubset(HIGH_RISK_CATEGORIES), \
            f"Missing auth categories: {auth_categories - HIGH_RISK_CATEGORIES}"

    def test_high_risk_contains_injection_categories(self):
        """HIGH_RISK_CATEGORIES must include injection tags."""
        injection_categories = {'injection', 'sql', 'command'}
        assert injection_categories.issubset(HIGH_RISK_CATEGORIES), \
            f"Missing injection categories: {injection_categories - HIGH_RISK_CATEGORIES}"

    def test_high_risk_contains_crypto_categories(self):
        """HIGH_RISK_CATEGORIES must include crypto tags."""
        crypto_categories = {'crypto', 'encryption'}
        assert crypto_categories.issubset(HIGH_RISK_CATEGORIES), \
            f"Missing crypto categories: {crypto_categories - HIGH_RISK_CATEGORIES}"

    def test_high_risk_contains_secrets_categories(self):
        """HIGH_RISK_CATEGORIES must include secrets tags."""
        secrets_categories = {'secrets', 'credentials'}
        assert secrets_categories.issubset(HIGH_RISK_CATEGORIES), \
            f"Missing secrets categories: {secrets_categories - HIGH_RISK_CATEGORIES}"


class TestSecurityKeywordsConstant:
    """Test that SECURITY_KEYWORDS constant contains required keywords."""

    def test_security_keywords_contains_authentication_terms(self):
        """SECURITY_KEYWORDS must include authentication terms."""
        auth_terms = {'login', 'logout', 'signup', 'signin', 'password', 'credential'}
        assert auth_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing auth terms: {auth_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_contains_authorization_terms(self):
        """SECURITY_KEYWORDS must include authorization terms."""
        authz_terms = {'permission', 'access', 'role', 'privilege', 'admin'}
        assert authz_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing authz terms: {authz_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_contains_token_terms(self):
        """SECURITY_KEYWORDS must include token-related terms."""
        token_terms = {'jwt', 'token', 'refresh', 'bearer', 'api_key', 'apikey'}
        assert token_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing token terms: {token_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_contains_secrets_terms(self):
        """SECURITY_KEYWORDS must include secrets-related terms."""
        secrets_terms = {'secret', 'key', 'certificate', 'private'}
        assert secrets_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing secrets terms: {secrets_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_contains_security_features(self):
        """SECURITY_KEYWORDS must include security feature terms."""
        feature_terms = {'rate_limit', 'rate-limit', 'throttle', 'cors', 'csrf'}
        assert feature_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing feature terms: {feature_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_contains_sensitive_data_terms(self):
        """SECURITY_KEYWORDS must include sensitive data terms."""
        sensitive_terms = {'pii', 'gdpr', 'encrypt', 'decrypt', 'hash'}
        assert sensitive_terms.issubset(SECURITY_KEYWORDS), \
            f"Missing sensitive terms: {sensitive_terms - SECURITY_KEYWORDS}"

    def test_security_keywords_has_minimum_count(self):
        """SECURITY_KEYWORDS must contain at least 25 keywords."""
        assert len(SECURITY_KEYWORDS) >= 25, \
            f"Expected ≥25 keywords, got {len(SECURITY_KEYWORDS)}"


class TestTagDetection:
    """Test security tag detection in task metadata."""

    def test_authentication_tag_triggers_review(self):
        """Task with 'authentication' tag should trigger security review."""
        task = {
            'id': 'TASK-001',
            'title': 'Some task',
            'tags': ['authentication']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_security_tag_triggers_review(self):
        """Task with 'security' tag should trigger security review."""
        task = {
            'id': 'TASK-002',
            'title': 'Some task',
            'tags': ['security']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_non_security_tag_does_not_trigger(self):
        """Task with 'ui-component' tag should not trigger security review."""
        task = {
            'id': 'TASK-003',
            'title': 'Some task',
            'tags': ['ui-component']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is False

    def test_multiple_tags_with_auth_triggers_review(self):
        """Task with multiple tags including 'auth' should trigger review."""
        task = {
            'id': 'TASK-004',
            'title': 'Some task',
            'tags': ['feature', 'auth', 'backend']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_sql_tag_triggers_review(self):
        """Task with 'sql' tag should trigger security review (injection)."""
        task = {
            'id': 'TASK-005',
            'title': 'Database query',
            'tags': ['sql', 'database']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_crypto_tag_triggers_review(self):
        """Task with 'crypto' tag should trigger security review."""
        task = {
            'id': 'TASK-006',
            'title': 'Encryption task',
            'tags': ['crypto']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True


class TestKeywordDetection:
    """Test security keyword detection in title and description."""

    def test_login_in_title_triggers_review(self):
        """Title 'Implement login endpoint' should trigger security review."""
        task = {
            'id': 'TASK-007',
            'title': 'Implement login endpoint',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_non_security_title_does_not_trigger(self):
        """Title 'Add user profile page' should not trigger security review."""
        task = {
            'id': 'TASK-008',
            'title': 'Add user profile page',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is False

    def test_jwt_in_title_triggers_review(self):
        """Title 'JWT token refresh' should trigger security review."""
        task = {
            'id': 'TASK-009',
            'title': 'JWT token refresh',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_multiple_keywords_in_description_triggers_review(self):
        """Description with 'password' and 'authentication' should trigger review."""
        task = {
            'id': 'TASK-010',
            'title': 'Update user flow',
            'description': 'Add password validation and authentication checks',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_single_keyword_in_description_does_not_trigger(self):
        """Description with single 'user' keyword should not trigger review."""
        task = {
            'id': 'TASK-011',
            'title': 'Update profile',
            'description': 'Allow user to update their profile information',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is False

    def test_permission_keyword_triggers_review(self):
        """Title with 'permission' keyword should trigger review."""
        task = {
            'id': 'TASK-012',
            'title': 'Update permission checks',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_admin_keyword_triggers_review(self):
        """Title with 'admin' keyword should trigger review."""
        task = {
            'id': 'TASK-013',
            'title': 'Add admin dashboard',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True


class TestConfigurationOverride:
    """Test configuration-based override of security detection."""

    def test_force_full_review_overrides_no_tags(self):
        """force_full_review: True should trigger review regardless of tags."""
        task = {
            'id': 'TASK-014',
            'title': 'Regular task',
            'tags': ['feature']
        }
        config = SecurityConfig(
            level=SecurityLevel.STANDARD,
            force_full_review=True
        )

        assert should_run_full_review(task, config) is True

    def test_skip_level_overrides_security_tags(self):
        """level: skip should prevent review regardless of tags."""
        task = {
            'id': 'TASK-015',
            'title': 'Implement authentication',
            'tags': ['authentication', 'security']
        }
        config = SecurityConfig(level=SecurityLevel.SKIP)

        assert should_run_full_review(task, config) is False

    def test_strict_level_triggers_regardless_of_tags(self):
        """level: strict should trigger review regardless of tags."""
        task = {
            'id': 'TASK-016',
            'title': 'Regular task',
            'tags': ['ui-component']
        }
        config = SecurityConfig(level=SecurityLevel.STRICT)

        assert should_run_full_review(task, config) is True

    def test_minimal_level_does_not_trigger_without_tags(self):
        """level: minimal should not trigger review without security tags."""
        task = {
            'id': 'TASK-017',
            'title': 'Regular task',
            'tags': ['feature']
        }
        config = SecurityConfig(level=SecurityLevel.MINIMAL)

        assert should_run_full_review(task, config) is False

    def test_standard_level_with_auth_tag_triggers(self):
        """level: standard with auth tag should trigger review."""
        task = {
            'id': 'TASK-018',
            'title': 'Some task',
            'tags': ['auth']
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_minimal_level_with_high_risk_tag_triggers(self):
        """level: minimal should still trigger for HIGH_RISK_CATEGORIES."""
        task = {
            'id': 'TASK-019',
            'title': 'Database task',
            'tags': ['sql']
        }
        config = SecurityConfig(level=SecurityLevel.MINIMAL)

        # Even minimal should trigger for high-risk tags like SQL injection
        assert should_run_full_review(task, config) is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tags_falls_back_to_keyword_detection(self):
        """Empty tags list should fall back to keyword detection."""
        task = {
            'id': 'TASK-020',
            'title': 'Implement login',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_empty_title_uses_description_only(self):
        """Empty title should use description for keyword detection."""
        task = {
            'id': 'TASK-021',
            'title': '',
            'description': 'Add authentication and password hashing',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_no_task_metadata_returns_false(self):
        """Task with no metadata should not trigger review."""
        task = {
            'id': 'TASK-022'
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is False

    def test_case_insensitive_tag_matching(self):
        """Tag matching should be case-insensitive (Authentication)."""
        task = {
            'id': 'TASK-023',
            'title': 'Some task',
            'tags': ['Authentication']  # Capital A
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_case_insensitive_keyword_matching_uppercase(self):
        """Keyword matching should be case-insensitive (AUTHENTICATION)."""
        task = {
            'id': 'TASK-024',
            'title': 'AUTHENTICATION system',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_case_insensitive_keyword_matching_mixed(self):
        """Keyword matching should be case-insensitive (mixed case)."""
        task = {
            'id': 'TASK-025',
            'title': 'Add LoGiN functionality',
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_none_tags_does_not_crash(self):
        """None tags should not cause crash, fall back to keywords."""
        task = {
            'id': 'TASK-026',
            'title': 'JWT token handling',
            'tags': None
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_none_description_does_not_crash(self):
        """None description should not cause crash."""
        task = {
            'id': 'TASK-027',
            'title': 'Regular task',
            'description': None,
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is False


class TestPriorityOrder:
    """Test that detection follows correct priority order."""

    def test_force_full_review_overrides_skip_level(self):
        """force_full_review should override level: skip."""
        task = {
            'id': 'TASK-028',
            'title': 'Regular task',
            'tags': []
        }
        config = SecurityConfig(
            level=SecurityLevel.SKIP,
            force_full_review=True
        )

        # Force flag takes precedence over skip level
        assert should_run_full_review(task, config) is True

    def test_skip_level_prevents_tag_detection(self):
        """level: skip should prevent review even with security tags."""
        task = {
            'id': 'TASK-029',
            'title': 'Auth task',
            'tags': ['authentication']
        }
        config = SecurityConfig(
            level=SecurityLevel.SKIP,
            force_full_review=False
        )

        assert should_run_full_review(task, config) is False

    def test_strict_level_triggers_without_tags_or_keywords(self):
        """level: strict should trigger even without security indicators."""
        task = {
            'id': 'TASK-030',
            'title': 'Regular task',
            'description': 'Normal implementation',
            'tags': ['feature']
        }
        config = SecurityConfig(level=SecurityLevel.STRICT)

        assert should_run_full_review(task, config) is True

    def test_tags_take_priority_over_keywords(self):
        """When both tags and keywords present, tags are checked first."""
        task = {
            'id': 'TASK-031',
            'title': 'login implementation',  # Has keyword
            'tags': ['authentication']  # Has security tag
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        # Should trigger (both would work, but tags checked first)
        assert should_run_full_review(task, config) is True

    def test_description_density_requires_multiple_keywords(self):
        """Description needs ≥2 keywords to trigger (density threshold)."""
        task = {
            'id': 'TASK-032',
            'title': 'Update system',
            'description': 'The admin user will have access to settings',  # admin, access = 2
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_single_description_keyword_not_enough(self):
        """Single keyword in description should not trigger review."""
        task = {
            'id': 'TASK-033',
            'title': 'Update feature',
            'description': 'Allow admin to view reports',  # Only 'admin' = 1
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        # Single keyword in description is not enough (need title or ≥2)
        assert should_run_full_review(task, config) is False


class TestKeywordDensity:
    """Test keyword density detection in description field."""

    def test_two_keywords_in_description_triggers(self):
        """Description with exactly 2 security keywords should trigger."""
        task = {
            'id': 'TASK-034',
            'title': 'Update system',
            'description': 'Implement encryption for password storage',  # encryption, password
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_three_keywords_in_description_triggers(self):
        """Description with 3+ security keywords should trigger."""
        task = {
            'id': 'TASK-035',
            'title': 'Update system',
            'description': 'Add JWT token authentication with permission checks',  # jwt, token, authentication, permission = 4
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_keywords_case_insensitive_in_description(self):
        """Keyword density should be case-insensitive."""
        task = {
            'id': 'TASK-036',
            'title': 'Update system',
            'description': 'Add ENCRYPTION and PASSWORD validation',  # Case variations
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        assert should_run_full_review(task, config) is True

    def test_repeated_keyword_counts_once(self):
        """Same keyword repeated should count as single occurrence."""
        task = {
            'id': 'TASK-037',
            'title': 'Update system',
            'description': 'password password password',  # Repeated 3x but counts as 1
            'tags': []
        }
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        # Only 1 unique keyword, should not trigger
        assert should_run_full_review(task, config) is False
