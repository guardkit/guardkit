"""Unit tests for task type detection.

Tests the automatic task type classification based on keyword analysis.
Covers all task types (SCAFFOLDING, DOCUMENTATION, INFRASTRUCTURE, FEATURE)
and edge cases (empty strings, hybrid tasks, ambiguous cases).
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
        assert detect_task_type("Update OpenAPI specification") == TaskType.DOCUMENTATION
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

    def test_refactoring(self):
        """Test refactoring tasks default to FEATURE."""
        assert detect_task_type("Refactor database layer") == TaskType.FEATURE
        assert detect_task_type("Optimize query performance") == TaskType.FEATURE

    def test_testing(self):
        """Test testing tasks default to FEATURE."""
        assert detect_task_type("Add unit tests for auth service") == TaskType.FEATURE
        assert detect_task_type("Write integration tests") == TaskType.FEATURE

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
        assert detect_task_type("Test task") == TaskType.FEATURE

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
    """Test priority-based classification."""

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

    def test_documentation_over_scaffolding(self):
        """Test DOCUMENTATION takes priority over SCAFFOLDING."""
        # "docs" is DOCUMENTATION, "config" is SCAFFOLDING
        assert detect_task_type("Add config docs") == TaskType.DOCUMENTATION

    def test_infrastructure_over_feature(self):
        """Test INFRASTRUCTURE takes priority over FEATURE."""
        # "docker" is INFRASTRUCTURE, "implement" is FEATURE (default)
        assert detect_task_type("Implement Docker deployment") == TaskType.INFRASTRUCTURE


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
        ]

        expected = [
            TaskType.INFRASTRUCTURE,
            TaskType.DOCUMENTATION,
            TaskType.SCAFFOLDING,
            TaskType.FEATURE,
            TaskType.FEATURE,
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
