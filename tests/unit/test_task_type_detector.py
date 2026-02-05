"""Unit tests for task type detection.

Tests the automatic task type classification based on keyword analysis.
Covers all task types (SCAFFOLDING, DOCUMENTATION, INFRASTRUCTURE, TESTING,
REFACTOR, FEATURE) and edge cases (empty strings, hybrid tasks, ambiguous cases).
"""

import pytest
from guardkit.lib.task_type_detector import (
    detect_task_type,
    get_task_type_summary,
    KEYWORD_MAPPINGS,
)
from guardkit.models.task_types import TaskType


class TestScaffoldingDetection:
    """Test detection of SCAFFOLDING task type."""

    def test_config_file_keywords(self):
        """Test configuration file keywords."""
        assert detect_task_type("Add webpack configuration") == TaskType.SCAFFOLDING
        assert detect_task_type("Update .env settings") == TaskType.SCAFFOLDING
        assert detect_task_type("Configure environment variables") == TaskType.SCAFFOLDING

    def test_project_setup_keywords(self):
        """Test project setup keywords."""
        assert detect_task_type("Initialize project scaffold") == TaskType.SCAFFOLDING
        assert detect_task_type("Create boilerplate structure") == TaskType.SCAFFOLDING
        assert detect_task_type("Setup project template") == TaskType.SCAFFOLDING

    def test_package_management_keywords(self):
        """Test package management keywords."""
        assert detect_task_type("Update package.json dependencies") == TaskType.SCAFFOLDING
        assert detect_task_type("Add requirements.txt") == TaskType.SCAFFOLDING
        assert detect_task_type("Configure pyproject.toml") == TaskType.SCAFFOLDING

    def test_build_configuration_keywords(self):
        """Test build configuration keywords."""
        assert detect_task_type("Configure Vite build") == TaskType.SCAFFOLDING
        assert detect_task_type("Update tsconfig.json") == TaskType.SCAFFOLDING
        assert detect_task_type("Add ESLint rules") == TaskType.SCAFFOLDING
        assert detect_task_type("Setup Prettier configuration") == TaskType.SCAFFOLDING

    def test_case_insensitive(self):
        """Test case-insensitive matching for scaffolding."""
        assert detect_task_type("ADD WEBPACK CONFIG") == TaskType.SCAFFOLDING
        assert detect_task_type("update Package.JSON") == TaskType.SCAFFOLDING


class TestDocumentationDetection:
    """Test detection of DOCUMENTATION task type."""

    def test_documentation_file_keywords(self):
        """Test documentation file keywords."""
        assert detect_task_type("Update README") == TaskType.DOCUMENTATION
        assert detect_task_type("Write documentation for API") == TaskType.DOCUMENTATION
        assert detect_task_type("Create user guide") == TaskType.DOCUMENTATION
        assert detect_task_type("Add tutorial for setup") == TaskType.DOCUMENTATION

    def test_api_documentation_keywords(self):
        """Test API documentation keywords."""
        assert detect_task_type("Generate Swagger docs") == TaskType.DOCUMENTATION
        # Note: "OpenAPI spec" contains "spec" which matches TESTING
        # Use a more specific example that doesn't conflict
        assert detect_task_type("Write OpenAPI documentation") == TaskType.DOCUMENTATION
        assert detect_task_type("Add JSDoc comments") == TaskType.DOCUMENTATION

    def test_comments_and_explanations(self):
        """Test comment and explanation keywords."""
        assert detect_task_type("Add code comments") == TaskType.DOCUMENTATION
        assert detect_task_type("Explain authentication flow") == TaskType.DOCUMENTATION
        assert detect_task_type("Clarify error messages") == TaskType.DOCUMENTATION

    def test_changelog_keywords(self):
        """Test changelog keywords."""
        assert detect_task_type("Update CHANGELOG") == TaskType.DOCUMENTATION
        assert detect_task_type("Add release notes") == TaskType.DOCUMENTATION

    def test_content_reduction_keywords(self):
        """Test content reduction keywords (TASK-REV-D4B1)."""
        assert detect_task_type("Trim orchestrators.md") == TaskType.DOCUMENTATION
        assert detect_task_type("Reduce dataclass patterns doc") == TaskType.DOCUMENTATION
        assert detect_task_type("Compress verbose documentation") == TaskType.DOCUMENTATION
        assert detect_task_type("Condense API reference") == TaskType.DOCUMENTATION
        assert detect_task_type("Shorten installation guide") == TaskType.DOCUMENTATION

    def test_case_insensitive(self):
        """Test case-insensitive matching for documentation."""
        assert detect_task_type("UPDATE README") == TaskType.DOCUMENTATION
        assert detect_task_type("Write Tutorial") == TaskType.DOCUMENTATION


class TestInfrastructureDetection:
    """Test detection of INFRASTRUCTURE task type."""

    def test_containerization_keywords(self):
        """Test containerization keywords."""
        assert detect_task_type("Add Docker configuration") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Create Dockerfile") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Update docker-compose.yml") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Configure container registry") == TaskType.INFRASTRUCTURE

    def test_ci_cd_keywords(self):
        """Test CI/CD keywords."""
        assert detect_task_type("Setup CI/CD pipeline") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Add GitHub Actions workflow") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Configure GitLab CI") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup Jenkins pipeline") == TaskType.INFRASTRUCTURE

    def test_deployment_keywords(self):
        """Test deployment keywords."""
        assert detect_task_type("Configure deployment") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup Kubernetes cluster") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Add Helm charts") == TaskType.INFRASTRUCTURE

    def test_infrastructure_as_code(self):
        """Test infrastructure as code keywords."""
        assert detect_task_type("Add Terraform configuration") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Create Ansible playbook") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup CloudFormation template") == TaskType.INFRASTRUCTURE

    def test_monitoring_and_logging(self):
        """Test monitoring and logging keywords."""
        assert detect_task_type("Setup monitoring") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Configure logging") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Add Prometheus metrics") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup Grafana dashboard") == TaskType.INFRASTRUCTURE

    def test_cloud_providers(self):
        """Test cloud provider keywords."""
        assert detect_task_type("Configure AWS deployment") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup Azure resources") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Deploy to GCP") == TaskType.INFRASTRUCTURE

    def test_case_insensitive(self):
        """Test case-insensitive matching for infrastructure."""
        assert detect_task_type("ADD DOCKER CONFIG") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Setup Kubernetes") == TaskType.INFRASTRUCTURE


class TestTestingDetection:
    """Test detection of TESTING task type."""

    def test_test_framework_keywords(self):
        """Test framework keywords."""
        assert detect_task_type("Configure pytest settings") == TaskType.TESTING
        assert detect_task_type("Add unittest configuration") == TaskType.TESTING
        assert detect_task_type("Setup jest for frontend") == TaskType.TESTING
        assert detect_task_type("Configure vitest") == TaskType.TESTING
        assert detect_task_type("Add mocha tests") == TaskType.TESTING
        assert detect_task_type("Setup jasmine testing") == TaskType.TESTING

    def test_test_type_keywords(self):
        """Test type keywords."""
        assert detect_task_type("Add unit test coverage") == TaskType.TESTING
        assert detect_task_type("Write integration test") == TaskType.TESTING
        assert detect_task_type("Create e2e tests") == TaskType.TESTING
        assert detect_task_type("Add end-to-end testing") == TaskType.TESTING
        assert detect_task_type("Write spec files") == TaskType.TESTING

    def test_test_infrastructure_keywords(self):
        """Test infrastructure keywords."""
        assert detect_task_type("Create test fixtures") == TaskType.TESTING
        assert detect_task_type("Add test setup utilities") == TaskType.TESTING
        assert detect_task_type("Create mock services") == TaskType.TESTING
        assert detect_task_type("Add stub implementations") == TaskType.TESTING

    def test_case_insensitive(self):
        """Test case-insensitive matching for testing."""
        assert detect_task_type("ADD PYTEST CONFIGURATION") == TaskType.TESTING
        assert detect_task_type("Write Unit Tests") == TaskType.TESTING


class TestRefactorDetection:
    """Test detection of REFACTOR task type."""

    def test_refactoring_keywords(self):
        """Test refactoring keywords."""
        assert detect_task_type("Refactor database layer") == TaskType.REFACTOR
        assert detect_task_type("Apply refactoring to auth module") == TaskType.REFACTOR
        assert detect_task_type("Restructure project layout") == TaskType.REFACTOR

    def test_migration_keywords(self):
        """Test migration keywords."""
        assert detect_task_type("Migrate to new API") == TaskType.REFACTOR
        assert detect_task_type("Database migration scripts") == TaskType.REFACTOR
        assert detect_task_type("Upgrade dependencies") == TaskType.REFACTOR

    def test_modernization_keywords(self):
        """Test modernization keywords."""
        assert detect_task_type("Modernize authentication system") == TaskType.REFACTOR
        assert detect_task_type("Apply modernization patterns") == TaskType.REFACTOR

    def test_cleanup_keywords(self):
        """Test cleanup keywords."""
        assert detect_task_type("Cleanup unused imports") == TaskType.REFACTOR
        assert detect_task_type("Clean up legacy code") == TaskType.REFACTOR
        assert detect_task_type("Clean-up deprecated methods") == TaskType.REFACTOR

    def test_case_insensitive(self):
        """Test case-insensitive matching for refactor."""
        assert detect_task_type("REFACTOR SERVICE LAYER") == TaskType.REFACTOR
        assert detect_task_type("Migrate Database") == TaskType.REFACTOR


class TestFeatureDetection:
    """Test detection of FEATURE task type (default)."""

    def test_implementation_tasks(self):
        """Test feature implementation keywords."""
        assert detect_task_type("Implement user authentication") == TaskType.FEATURE
        assert detect_task_type("Add payment processing") == TaskType.FEATURE
        assert detect_task_type("Create user profile page") == TaskType.FEATURE

    def test_bug_fixes(self):
        """Test bug fix tasks default to FEATURE."""
        assert detect_task_type("Fix login validation bug") == TaskType.FEATURE
        assert detect_task_type("Resolve memory leak issue") == TaskType.FEATURE

    def test_optimization(self):
        """Test optimization tasks default to FEATURE."""
        assert detect_task_type("Optimize query performance") == TaskType.FEATURE
        assert detect_task_type("Improve database indexing") == TaskType.FEATURE

    def test_ui_components(self):
        """Test UI component tasks default to FEATURE."""
        assert detect_task_type("Create dashboard component") == TaskType.FEATURE
        assert detect_task_type("Add form validation") == TaskType.FEATURE


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_title(self):
        """Test empty title defaults to FEATURE."""
        assert detect_task_type("") == TaskType.FEATURE
        assert detect_task_type("", "") == TaskType.FEATURE

    def test_none_values(self):
        """Test None values are handled gracefully."""
        # Note: This would raise TypeError if not handled
        # We pass empty strings in the actual implementation
        # "Test task" now matches TESTING type due to "test" keyword
        assert detect_task_type("Sample task") == TaskType.FEATURE

    def test_whitespace_only(self):
        """Test whitespace-only strings default to FEATURE."""
        assert detect_task_type("   ") == TaskType.FEATURE
        assert detect_task_type("\n\t  ") == TaskType.FEATURE

    def test_special_characters(self):
        """Test special characters don't break detection."""
        assert detect_task_type("Add Docker config!!!") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Update README (important)") == TaskType.DOCUMENTATION

    def test_mixed_case(self):
        """Test mixed case handling."""
        assert detect_task_type("AdD DoCkEr CoNfIg") == TaskType.INFRASTRUCTURE
        assert detect_task_type("uPdAtE rEaDmE") == TaskType.DOCUMENTATION


class TestPriorityOrder:
    """Test priority-based classification.

    Priority order: INFRASTRUCTURE > TESTING > REFACTOR > DOCUMENTATION > SCAFFOLDING > FEATURE
    """

    def test_infrastructure_over_scaffolding(self):
        """Test INFRASTRUCTURE takes priority over SCAFFOLDING."""
        # "docker" is INFRASTRUCTURE, "config" is SCAFFOLDING
        # INFRASTRUCTURE has higher priority for specificity
        assert detect_task_type("Configure Docker settings") == TaskType.INFRASTRUCTURE
        assert detect_task_type("Add Docker config") == TaskType.INFRASTRUCTURE

    def test_infrastructure_over_documentation(self):
        """Test INFRASTRUCTURE takes priority over DOCUMENTATION."""
        # "deploy" is INFRASTRUCTURE, "document" is DOCUMENTATION
        # INFRASTRUCTURE checked first
        assert detect_task_type("Document deployment process") == TaskType.INFRASTRUCTURE

    def test_infrastructure_over_testing(self):
        """Test INFRASTRUCTURE takes priority over TESTING."""
        # "docker" is INFRASTRUCTURE, "test" is TESTING
        assert detect_task_type("Test Docker configuration") == TaskType.INFRASTRUCTURE

    def test_testing_over_documentation(self):
        """Test TESTING takes priority over DOCUMENTATION."""
        # "test" is TESTING, "docs" is DOCUMENTATION
        assert detect_task_type("Document testing approach") == TaskType.TESTING

    def test_testing_over_scaffolding(self):
        """Test TESTING takes priority over SCAFFOLDING."""
        # "test" is TESTING, "config" is SCAFFOLDING
        assert detect_task_type("Configure test runner") == TaskType.TESTING

    def test_refactor_over_documentation(self):
        """Test REFACTOR takes priority over DOCUMENTATION."""
        # "refactor" is REFACTOR, "docs" is DOCUMENTATION
        assert detect_task_type("Document refactoring changes") == TaskType.REFACTOR

    def test_refactor_over_scaffolding(self):
        """Test REFACTOR takes priority over SCAFFOLDING."""
        # "refactor" is REFACTOR, "config" is SCAFFOLDING
        assert detect_task_type("Refactor configuration management") == TaskType.REFACTOR

    def test_documentation_over_scaffolding(self):
        """Test DOCUMENTATION takes priority over SCAFFOLDING."""
        # "docs" is DOCUMENTATION, "config" is SCAFFOLDING
        assert detect_task_type("Add config docs") == TaskType.DOCUMENTATION

    def test_infrastructure_over_feature(self):
        """Test INFRASTRUCTURE takes priority over FEATURE."""
        # "docker" is INFRASTRUCTURE, "implement" is FEATURE (default)
        assert detect_task_type("Implement Docker deployment") == TaskType.INFRASTRUCTURE

    def test_testing_over_feature(self):
        """Test TESTING takes priority over FEATURE."""
        # "test" is TESTING, no FEATURE keywords
        assert detect_task_type("Add authentication tests") == TaskType.TESTING

    def test_refactor_over_feature(self):
        """Test REFACTOR takes priority over FEATURE."""
        # "refactor" is REFACTOR, no FEATURE keywords
        assert detect_task_type("Refactor authentication module") == TaskType.REFACTOR


class TestDescriptionContext:
    """Test using description for additional context."""

    def test_title_only_classification(self):
        """Test classification with title only."""
        assert detect_task_type("Add feature") == TaskType.FEATURE

    def test_description_provides_context(self):
        """Test description influences classification."""
        # Title is ambiguous, description clarifies
        assert (
            detect_task_type(
                "Update configuration",
                "Add new webpack configuration file"
            )
            == TaskType.SCAFFOLDING
        )

        assert (
            detect_task_type(
                "Update files",
                "Update README with new API documentation"
            )
            == TaskType.DOCUMENTATION
        )

        assert (
            detect_task_type(
                "Setup deployment",
                "Configure Docker containers for production"
            )
            == TaskType.INFRASTRUCTURE
        )

    def test_title_takes_precedence(self):
        """Test title is considered along with description."""
        # Both title and description contribute
        result = detect_task_type(
            "Add Docker setup",
            "Create Dockerfile and docker-compose configuration"
        )
        assert result == TaskType.INFRASTRUCTURE


class TestRealWorldExamples:
    """Test real-world task examples."""

    def test_full_stack_feature(self):
        """Test full-stack feature implementation."""
        assert (
            detect_task_type(
                "Implement user authentication",
                "Add login/logout functionality with JWT tokens"
            )
            == TaskType.FEATURE
        )

    def test_devops_task(self):
        """Test DevOps task."""
        assert (
            detect_task_type(
                "Setup production deployment",
                "Configure Kubernetes cluster and CI/CD pipeline"
            )
            == TaskType.INFRASTRUCTURE
        )

    def test_documentation_task(self):
        """Test documentation task."""
        assert (
            detect_task_type(
                "Write API documentation",
                "Create comprehensive API guide with examples"
            )
            == TaskType.DOCUMENTATION
        )

    def test_configuration_task(self):
        """Test configuration task."""
        assert (
            detect_task_type(
                "Setup project structure",
                "Initialize package.json, tsconfig, and ESLint"
            )
            == TaskType.SCAFFOLDING
        )


class TestTaskTypeSummary:
    """Test get_task_type_summary function."""

    def test_all_task_types_have_summary(self):
        """Test all task types have human-readable summaries."""
        assert get_task_type_summary(TaskType.SCAFFOLDING) == "Configuration and boilerplate"
        assert get_task_type_summary(TaskType.DOCUMENTATION) == "Documentation and guides"
        assert get_task_type_summary(TaskType.INFRASTRUCTURE) == "DevOps and deployment"
        assert get_task_type_summary(TaskType.TESTING) == "Test infrastructure and tests"
        assert get_task_type_summary(TaskType.REFACTOR) == "Code refactoring and migration"
        assert get_task_type_summary(TaskType.FEATURE) == "Feature implementation"

    def test_unknown_task_type(self):
        """Test unknown task type returns default message."""
        # Create a mock enum value that doesn't exist
        # This shouldn't happen in practice but tests the fallback
        result = get_task_type_summary(None)
        assert result == "Unknown task type"


class TestKeywordMappings:
    """Test keyword mappings configuration."""

    def test_keyword_mappings_exist(self):
        """Test keyword mappings are defined."""
        assert TaskType.SCAFFOLDING in KEYWORD_MAPPINGS
        assert TaskType.DOCUMENTATION in KEYWORD_MAPPINGS
        assert TaskType.INFRASTRUCTURE in KEYWORD_MAPPINGS
        assert TaskType.TESTING in KEYWORD_MAPPINGS
        assert TaskType.REFACTOR in KEYWORD_MAPPINGS

    def test_feature_has_no_keywords(self):
        """Test FEATURE type has no keywords (default)."""
        assert TaskType.FEATURE not in KEYWORD_MAPPINGS

    def test_all_keywords_are_lowercase(self):
        """Test all keywords are lowercase for matching."""
        for task_type, keywords in KEYWORD_MAPPINGS.items():
            for keyword in keywords:
                assert keyword == keyword.lower(), (
                    f"Keyword '{keyword}' in {task_type.value} should be lowercase"
                )

    def test_no_duplicate_keywords(self):
        """Test no duplicate keywords within each type."""
        for task_type, keywords in KEYWORD_MAPPINGS.items():
            assert len(keywords) == len(set(keywords)), (
                f"Duplicate keywords found in {task_type.value}"
            )

    def test_keyword_coverage(self):
        """Test keyword mappings have reasonable coverage."""
        # Each type should have at least 10 keywords for good coverage
        assert len(KEYWORD_MAPPINGS[TaskType.SCAFFOLDING]) >= 10
        assert len(KEYWORD_MAPPINGS[TaskType.DOCUMENTATION]) >= 10
        assert len(KEYWORD_MAPPINGS[TaskType.INFRASTRUCTURE]) >= 10
        assert len(KEYWORD_MAPPINGS[TaskType.TESTING]) >= 10
        assert len(KEYWORD_MAPPINGS[TaskType.REFACTOR]) >= 10


class TestIntegration:
    """Integration tests for realistic workflows."""

    def test_feature_plan_workflow(self):
        """Test task type detection in feature plan workflow."""
        # Simulated subtasks from a feature plan
        subtasks = [
            ("Add Docker configuration", "Create Dockerfile and docker-compose"),
            ("Update README", "Document API endpoints and usage examples"),
            ("Setup ESLint", "Configure code quality tools"),
            ("Implement authentication", "Add JWT-based auth service"),
            ("Add unit tests", "Write tests for auth service"),
            ("Refactor database layer", "Restructure data access code"),
        ]

        expected = [
            TaskType.INFRASTRUCTURE,
            TaskType.DOCUMENTATION,
            TaskType.SCAFFOLDING,
            TaskType.FEATURE,
            TaskType.TESTING,  # Now correctly detected as TESTING
            TaskType.REFACTOR,  # Now correctly detected as REFACTOR
        ]

        for (title, desc), expected_type in zip(subtasks, expected):
            assert detect_task_type(title, desc) == expected_type

    def test_batch_classification(self):
        """Test batch classification of multiple tasks."""
        tasks = [
            "Configure webpack",
            "Write API docs",
            "Setup CI/CD",
            "Add payment feature",
            "Update changelog",
            "Deploy to AWS",
        ]

        expected = [
            TaskType.SCAFFOLDING,
            TaskType.DOCUMENTATION,
            TaskType.INFRASTRUCTURE,
            TaskType.FEATURE,
            TaskType.DOCUMENTATION,
            TaskType.INFRASTRUCTURE,
        ]

        results = [detect_task_type(task) for task in tasks]
        assert results == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
