"""
Test suite for implementation_mode_analyzer.py - Auto-tagging subtasks with modes.

Tests cover:
1. Manual task detection (script execution, migrations)
2. High-risk task detection (security, auth, database)
3. Low-risk task detection (documentation, CSS, config)
4. Complexity scoring based on keywords and files
5. Mode assignment decision matrix
6. Integration with subtask definitions
"""

import pytest
from lib.implementation_mode_analyzer import (
    ImplementationModeAnalyzer,
    assign_implementation_modes,
    get_mode_summary
)


class TestImplementationModeAnalyzer:
    """Test ImplementationModeAnalyzer class methods."""

    def test_is_manual_task_run_script(self):
        """Test detection of manual script execution tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Run database migration script",
            "description": ""
        }

        assert analyzer.is_manual_task(subtask) is True

    def test_is_manual_task_bulk_operation(self):
        """Test detection of bulk operation tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Execute bulk user import",
            "description": ""
        }

        assert analyzer.is_manual_task(subtask) is True

    def test_is_manual_task_regular_task(self):
        """Test regular tasks are not marked as manual."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Add CSS variables",
            "description": ""
        }

        assert analyzer.is_manual_task(subtask) is False

    def test_is_high_risk_security(self):
        """Test detection of security-related high-risk tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Implement authentication",
            "description": "Add JWT token validation"
        }

        assert analyzer.is_high_risk(subtask) is True

    def test_is_high_risk_database(self):
        """Test detection of database-related high-risk tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Refactor database schema",
            "description": ""
        }

        assert analyzer.is_high_risk(subtask) is True

    def test_is_high_risk_api(self):
        """Test detection of API-related high-risk tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Create REST API endpoint",
            "description": ""
        }

        assert analyzer.is_high_risk(subtask) is True

    def test_is_high_risk_low_risk_task(self):
        """Test low-risk tasks are not marked as high-risk."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Update documentation",
            "description": ""
        }

        assert analyzer.is_high_risk(subtask) is False

    def test_analyze_complexity_base_score(self):
        """Test complexity analysis with base score."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Simple task",
            "description": "",
            "files": [],
            "complexity": 3
        }

        complexity = analyzer.analyze_complexity(subtask)
        assert 1 <= complexity <= 10
        # Should stay around base score with no modifiers
        assert 2 <= complexity <= 4

    def test_analyze_complexity_risk_keywords(self):
        """Test complexity increases with risk keywords."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Implement authentication with OAuth",
            "description": "Add JWT token validation and database schema",
            "files": [],
            "complexity": 5
        }

        complexity = analyzer.analyze_complexity(subtask)
        # Should increase due to auth, oauth, jwt, database keywords
        assert complexity >= 7

    def test_analyze_complexity_low_risk_keywords(self):
        """Test complexity decreases with low-risk keywords."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Fix typo in documentation",
            "description": "Update README formatting",
            "files": [],
            "complexity": 5
        }

        complexity = analyzer.analyze_complexity(subtask)
        # Should decrease due to documentation, readme keywords
        assert complexity <= 4

    def test_analyze_complexity_file_count(self):
        """Test complexity increases with file count."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Simple task",
            "description": "",
            "files": ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py", "file6.py"],
            "complexity": 3
        }

        complexity = analyzer.analyze_complexity(subtask)
        # Should increase due to 6 files (>5)
        assert complexity >= 5

    def test_analyze_complexity_file_diversity(self):
        """Test complexity increases with diverse file types."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Update multiple file types",
            "description": "",
            "files": ["code.py", "styles.css", "config.json", "doc.md", "test.ts"],
            "complexity": 4
        }

        complexity = analyzer.analyze_complexity(subtask)
        # Should increase due to diverse extensions (py, css, json, md, ts)
        assert complexity >= 5

    def test_assign_mode_manual(self):
        """Test mode assignment for manual tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Run migration script",
            "description": "",
            "files": [],
            "complexity": 3
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "manual"

    def test_assign_mode_task_work_high_complexity(self):
        """Test mode assignment for high complexity tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Refactor authentication service",
            "description": "Major refactoring",
            "files": [],
            "complexity": 7
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_assign_mode_task_work_high_risk(self):
        """Test mode assignment for high-risk tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Implement OAuth 2.0 flow",
            "description": "",
            "files": [],
            "complexity": 5
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_assign_mode_direct_low_complexity(self):
        """Test mode assignment for low complexity tasks."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Add CSS variables",
            "description": "",
            "files": ["styles.css"],
            "complexity": 2
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_assign_mode_direct_medium_complexity_few_files(self):
        """Test mode assignment for medium complexity with few files."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Update configuration",
            "description": "",
            "files": ["config.json", "settings.py"],
            "complexity": 4
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_assign_mode_task_work_medium_complexity_many_files(self):
        """Test mode assignment for medium complexity with many files."""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Update multiple components",
            "description": "",
            "files": ["comp1.tsx", "comp2.tsx", "comp3.tsx", "comp4.tsx"],
            "complexity": 4
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_assign_modes_to_subtasks_multiple(self):
        """Test assigning modes to multiple subtasks."""
        analyzer = ImplementationModeAnalyzer()

        subtasks = [
            {
                "id": "TASK-001",
                "title": "Add CSS variables",
                "description": "",
                "files": [],
                "complexity": 2
            },
            {
                "id": "TASK-002",
                "title": "Refactor authentication",
                "description": "",
                "files": [],
                "complexity": 7
            },
            {
                "id": "TASK-003",
                "title": "Run database migration",
                "description": "",
                "files": [],
                "complexity": 3
            }
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        assert len(result) == 3
        assert result[0]["implementation_mode"] == "direct"
        assert result[1]["implementation_mode"] == "task-work"
        # "Run database migration" contains both "run" (manual) and "database" (high-risk)
        # In this case, high-risk wins since migrations need review
        assert result[2]["implementation_mode"] == "task-work"

    def test_assign_modes_adds_metadata(self):
        """Test that mode assignment adds analysis metadata."""
        analyzer = ImplementationModeAnalyzer()

        subtasks = [
            {
                "id": "TASK-001",
                "title": "Implement OAuth",
                "description": "",
                "files": [],
                "complexity": 5
            }
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        assert "implementation_mode" in result[0]
        assert "complexity_analyzed" in result[0]
        assert "risk_level" in result[0]
        assert result[0]["risk_level"] == "high"

    def test_assign_modes_preserves_existing_mode(self):
        """Test that existing modes are not overwritten."""
        analyzer = ImplementationModeAnalyzer()

        subtasks = [
            {
                "id": "TASK-001",
                "title": "Simple task",
                "description": "",
                "files": [],
                "complexity": 2,
                "implementation_mode": "manual"  # Manual override
            }
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        # Should preserve manual override
        assert result[0]["implementation_mode"] == "manual"


class TestAssignImplementationModes:
    """Test main entry point function."""

    def test_assign_implementation_modes_integration(self):
        """Test complete integration with subtask definitions."""
        subtasks = [
            {
                "id": "TASK-FW-001",
                "title": "Create /feature-plan command (markdown orchestration)",
                "description": "Create /feature-plan command",
                "files": ["installer/core/commands/feature-plan.md"],
                "complexity": 3
            },
            {
                "id": "TASK-FW-002",
                "title": "Auto-detect feature slug from review task title",
                "description": "",
                "files": [],
                "complexity": 3
            },
            {
                "id": "TASK-FW-003",
                "title": "Auto-detect subtasks from review recommendations",
                "description": "",
                "files": [],
                "complexity": 5
            }
        ]

        result = assign_implementation_modes(subtasks)

        assert len(result) == 3
        # All should have modes assigned
        assert all("implementation_mode" in s for s in result)
        # FW-001 and FW-002 should be direct (low complexity, simple)
        assert result[0]["implementation_mode"] == "direct"
        assert result[1]["implementation_mode"] == "direct"
        # FW-003 should be direct or task-work depending on analysis
        assert result[2]["implementation_mode"] in ["direct", "task-work"]

    def test_assign_implementation_modes_empty_list(self):
        """Test handling of empty subtask list."""
        result = assign_implementation_modes([])
        assert result == []

    def test_assign_implementation_modes_minimal_subtask(self):
        """Test handling of subtask with minimal fields."""
        subtasks = [
            {
                "id": "TASK-001",
                "title": "Simple task"
            }
        ]

        result = assign_implementation_modes(subtasks)

        assert len(result) == 1
        assert "implementation_mode" in result[0]


class TestGetModeSummary:
    """Test mode summary generation."""

    def test_get_mode_summary_all_modes(self):
        """Test summary with all mode types."""
        subtasks = [
            {"id": "T1", "implementation_mode": "direct"},
            {"id": "T2", "implementation_mode": "direct"},
            {"id": "T3", "implementation_mode": "task-work"},
            {"id": "T4", "implementation_mode": "task-work"},
            {"id": "T5", "implementation_mode": "task-work"},
            {"id": "T6", "implementation_mode": "manual"},
        ]

        summary = get_mode_summary(subtasks)

        assert summary["direct"] == 2
        assert summary["task-work"] == 3
        assert summary["manual"] == 1

    def test_get_mode_summary_single_mode(self):
        """Test summary with only one mode type."""
        subtasks = [
            {"id": "T1", "implementation_mode": "direct"},
            {"id": "T2", "implementation_mode": "direct"},
        ]

        summary = get_mode_summary(subtasks)

        assert summary["direct"] == 2
        assert summary["task-work"] == 0
        assert summary["manual"] == 0

    def test_get_mode_summary_no_modes(self):
        """Test summary with tasks missing mode field."""
        subtasks = [
            {"id": "T1"},
            {"id": "T2"},
        ]

        summary = get_mode_summary(subtasks)

        # Should default to 0 for all
        assert summary["direct"] == 0
        assert summary["task-work"] == 0
        assert summary["manual"] == 0

    def test_get_mode_summary_empty_list(self):
        """Test summary with empty list."""
        summary = get_mode_summary([])

        assert summary["direct"] == 0
        assert summary["task-work"] == 0
        assert summary["manual"] == 0


class TestRealWorldScenarios:
    """Test with real-world subtask examples from spec."""

    def test_add_css_variables(self):
        """Test: 'Add CSS variables' → direct"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Add CSS variables",
            "description": "Create CSS custom properties for theming",
            "files": ["styles/variables.css"],
            "complexity": 2
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_refactor_authentication_service(self):
        """Test: 'Refactor authentication service' → task-work"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Refactor authentication service",
            "description": "Major refactoring of auth logic",
            "files": ["services/auth.ts"],
            "complexity": 7
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_run_database_migration_script(self):
        """Test: 'Run database migration script' → manual"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Run database migration script",
            "description": "Execute schema migration",
            "files": [],
            "complexity": 3
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "manual"

    def test_update_documentation(self):
        """Test: 'Update documentation' → direct"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Update documentation",
            "description": "Add API usage examples",
            "files": ["docs/api.md"],
            "complexity": 2
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_implement_oauth_flow(self):
        """Test: 'Implement OAuth 2.0 flow' → task-work"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Implement OAuth 2.0 flow",
            "description": "Add OAuth authentication",
            "files": [],
            "complexity": 6
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_fix_typo_in_readme(self):
        """Test: 'Fix typo in README' → direct"""
        analyzer = ImplementationModeAnalyzer()

        subtask = {
            "title": "Fix typo in README",
            "description": "",
            "files": ["README.md"],
            "complexity": 1
        }

        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
