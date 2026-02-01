"""
Comprehensive Test Suite for Implementation Mode Analyzer

Tests the automatic assignment of implementation modes (task-work, direct)
to subtasks based on complexity and risk analysis.

Coverage Target: >=80%
Test Count: 40+ tests

Critical Validation:
- NO "manual" mode should EVER be assigned or tracked
- Only "task-work" and "direct" modes are valid
"""

import pytest
from installer.core.lib.implementation_mode_analyzer import (
    ImplementationModeAnalyzer,
    assign_implementation_modes,
    get_mode_summary
)


# ============================================================================
# 1. Complexity Analysis Tests (10 tests)
# ============================================================================

class TestComplexityAnalysis:
    """Test analyze_complexity() scoring logic."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ImplementationModeAnalyzer()

    def test_base_complexity_default(self, analyzer):
        """Test that base complexity defaults to 5 if not provided."""
        subtask = {
            "title": "Simple task",
            "description": "No special keywords"
        }
        complexity = analyzer.analyze_complexity(subtask)
        assert 1 <= complexity <= 10

    def test_base_complexity_from_subtask(self, analyzer):
        """Test that existing complexity score is used as base."""
        subtask = {
            "title": "Task",
            "complexity": 7,
            "description": ""
        }
        complexity = analyzer.analyze_complexity(subtask)
        assert complexity >= 7  # Should not decrease from base

    def test_high_risk_keywords_increase_complexity(self, analyzer):
        """Test that high-risk keywords increase complexity."""
        subtask = {
            "title": "Add authentication and authorization",
            "description": "Implement JWT tokens with OAuth",
            "complexity": 5
        }
        complexity = analyzer.analyze_complexity(subtask)
        # Should increase due to multiple high-risk keywords
        assert complexity > 5

    def test_low_risk_keywords_decrease_complexity(self, analyzer):
        """Test that low-risk keywords decrease complexity."""
        subtask = {
            "title": "Update documentation",
            "description": "Fix typos in README and add comments",
            "complexity": 5
        }
        complexity = analyzer.analyze_complexity(subtask)
        # Should decrease due to low-risk keywords
        assert complexity < 5

    def test_low_risk_dominates_over_high_risk(self, analyzer):
        """Test that low-risk keywords dominate if more prevalent."""
        subtask = {
            "title": "Update documentation for API endpoint",
            "description": "Add comments and formatting to config files",
            "complexity": 5
        }
        complexity = analyzer.analyze_complexity(subtask)
        # Low-risk keywords (documentation, comments, formatting, config) = 4
        # High-risk keywords (api, endpoint) = 2
        # Low-risk should dominate
        assert complexity < 5

    def test_file_count_increases_complexity(self, analyzer):
        """Test that file count affects complexity score."""
        subtask_few = {
            "title": "Update files",
            "files": ["file1.py", "file2.py"],
            "complexity": 5
        }
        subtask_many = {
            "title": "Update files",
            "files": [f"file{i}.py" for i in range(10)],
            "complexity": 5
        }

        complexity_few = analyzer.analyze_complexity(subtask_few)
        complexity_many = analyzer.analyze_complexity(subtask_many)

        # More files should result in higher complexity
        assert complexity_many > complexity_few

    def test_file_count_thresholds(self, analyzer):
        """Test file count threshold behavior (3 and 5 files)."""
        subtask_3_files = {
            "title": "Task",
            "files": ["a.py", "b.py", "c.py"],
            "complexity": 5
        }
        subtask_4_files = {
            "title": "Task",
            "files": ["a.py", "b.py", "c.py", "d.py"],
            "complexity": 5
        }
        subtask_6_files = {
            "title": "Task",
            "files": ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"],
            "complexity": 5
        }

        complexity_3 = analyzer.analyze_complexity(subtask_3_files)
        complexity_4 = analyzer.analyze_complexity(subtask_4_files)
        complexity_6 = analyzer.analyze_complexity(subtask_6_files)

        # >3 files adds +1, >5 files adds +2
        assert complexity_4 > complexity_3
        assert complexity_6 > complexity_4

    def test_file_type_diversity_increases_complexity(self, analyzer):
        """Test that diverse file types increase complexity."""
        subtask_same = {
            "title": "Task",
            "files": ["a.py", "b.py", "c.py", "d.py"],
            "complexity": 5
        }
        subtask_diverse = {
            "title": "Task",
            "files": ["a.py", "b.js", "c.css", "d.html", "e.json"],
            "complexity": 5
        }

        complexity_same = analyzer.analyze_complexity(subtask_same)
        complexity_diverse = analyzer.analyze_complexity(subtask_diverse)

        # >3 different extensions should increase complexity
        assert complexity_diverse > complexity_same

    def test_complexity_bounds_enforced(self, analyzer):
        """Test that complexity is always between 1 and 10."""
        # Try to push complexity very low
        subtask_low = {
            "title": "documentation typo whitespace",
            "description": "readme comment formatting lint css",
            "complexity": 1,
            "files": []
        }
        complexity_low = analyzer.analyze_complexity(subtask_low)
        assert complexity_low >= 1

        # Try to push complexity very high
        subtask_high = {
            "title": "security authentication authorization payment encryption",
            "description": "database migration breaking change refactor api integration",
            "complexity": 10,
            "files": [f"file{i}.ext{j}" for i in range(20) for j in range(5)]
        }
        complexity_high = analyzer.analyze_complexity(subtask_high)
        assert complexity_high <= 10

    def test_complexity_case_insensitive(self, analyzer):
        """Test that keyword matching is case-insensitive."""
        subtask_lower = {
            "title": "add authentication",
            "description": "implement oauth",
            "complexity": 5
        }
        subtask_upper = {
            "title": "Add AUTHENTICATION",
            "description": "Implement OAuth",
            "complexity": 5
        }
        subtask_mixed = {
            "title": "Add Authentication",
            "description": "Implement OAuTh",
            "complexity": 5
        }

        complexity_lower = analyzer.analyze_complexity(subtask_lower)
        complexity_upper = analyzer.analyze_complexity(subtask_upper)
        complexity_mixed = analyzer.analyze_complexity(subtask_mixed)

        # All should yield same result
        assert complexity_lower == complexity_upper == complexity_mixed


# ============================================================================
# 2. Risk Assessment Tests (8 tests)
# ============================================================================

class TestRiskAssessment:
    """Test is_high_risk() detection logic."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ImplementationModeAnalyzer()

    def test_security_keywords_flag_high_risk(self, analyzer):
        """Test that security-related keywords flag as high-risk."""
        high_risk_keywords = [
            "security", "authentication", "authorization",
            "oauth", "jwt", "encryption", "payment"
        ]

        for keyword in high_risk_keywords:
            subtask = {
                "title": f"Add {keyword}",
                "description": "Implementation task"
            }
            assert analyzer.is_high_risk(subtask) is True

    def test_database_keywords_flag_high_risk(self, analyzer):
        """Test that database keywords flag as high-risk."""
        subtask = {
            "title": "Database migration",
            "description": "Update schema and add transaction support"
        }
        assert analyzer.is_high_risk(subtask) is True

    def test_architecture_keywords_flag_high_risk(self, analyzer):
        """Test that architecture keywords flag as high-risk."""
        subtask = {
            "title": "Refactor core architecture",
            "description": "Breaking change to foundation"
        }
        assert analyzer.is_high_risk(subtask) is True

    def test_api_keywords_flag_high_risk(self, analyzer):
        """Test that API keywords flag as high-risk."""
        subtask = {
            "title": "Add API endpoint",
            "description": "Integration with external service via webhook"
        }
        assert analyzer.is_high_risk(subtask) is True

    def test_low_risk_context_overrides_most_keywords(self, analyzer):
        """Test that low-risk context can override high-risk keywords."""
        subtask = {
            "title": "Update API documentation",
            "description": "Add comments to endpoint config files"
        }
        # Has "api" and "endpoint" but in documentation context
        # Should NOT be high-risk due to low-risk context
        assert analyzer.is_high_risk(subtask) is False

    def test_critical_keywords_always_high_risk(self, analyzer):
        """Test that critical keywords flag high-risk even in low-risk context."""
        critical_cases = [
            {
                "title": "Document security implementation",
                "description": "Add comments explaining authentication flow"
            },
            {
                "title": "Update payment configuration",
                "description": "Document encryption settings"
            },
            {
                "title": "Authorization config documentation",
                "description": "Add README for authorization setup"
            }
        ]

        for subtask in critical_cases:
            # Even with documentation/config/comments, critical keywords
            # should still flag as high-risk
            assert analyzer.is_high_risk(subtask) is True

    def test_simple_tasks_not_high_risk(self, analyzer):
        """Test that simple tasks are not flagged as high-risk."""
        subtask = {
            "title": "Fix typo in README",
            "description": "Update whitespace and formatting"
        }
        assert analyzer.is_high_risk(subtask) is False

    def test_risk_assessment_case_insensitive(self, analyzer):
        """Test that risk assessment is case-insensitive."""
        subtask_lower = {
            "title": "add authentication",
            "description": ""
        }
        subtask_upper = {
            "title": "ADD AUTHENTICATION",
            "description": ""
        }

        assert analyzer.is_high_risk(subtask_lower) is True
        assert analyzer.is_high_risk(subtask_upper) is True


# ============================================================================
# 3. Mode Assignment Tests (12 tests)
# ============================================================================

class TestModeAssignment:
    """Test assign_mode() decision matrix."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ImplementationModeAnalyzer()

    def test_high_complexity_assigns_task_work(self, analyzer):
        """Test that complexity >= 6 assigns task-work."""
        subtask = {
            "title": "Complex task with multiple files",
            "description": "Refactor authentication system",
            "complexity": 8,
            "files": ["a.py", "b.py", "c.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_high_risk_assigns_task_work(self, analyzer):
        """Test that high-risk tasks assign task-work."""
        subtask = {
            "title": "Add security audit",
            "description": "Implement encryption",
            "complexity": 3,
            "files": ["security.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_low_complexity_assigns_direct(self, analyzer):
        """Test that complexity <= 3 assigns direct."""
        subtask = {
            "title": "Fix typo",
            "description": "Update README formatting",
            "complexity": 2,
            "files": ["README.md"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_medium_complexity_many_files_assigns_task_work(self, analyzer):
        """Test that medium complexity with >3 files assigns task-work."""
        subtask = {
            "title": "Update components",
            "description": "Standard implementation",
            "complexity": 5,
            "files": ["a.py", "b.py", "c.py", "d.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_medium_complexity_few_files_assigns_direct(self, analyzer):
        """Test that medium complexity with <=3 files assigns direct."""
        subtask = {
            "title": "Update components",
            "description": "Standard implementation",
            "complexity": 4,
            "files": ["a.py", "b.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_complexity_boundary_6_assigns_task_work(self, analyzer):
        """Test that complexity exactly 6 assigns task-work."""
        subtask = {
            "title": "Task",
            "complexity": 6,
            "description": "",
            "files": []
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_complexity_boundary_3_assigns_direct(self, analyzer):
        """Test that complexity exactly 3 assigns direct."""
        subtask = {
            "title": "Task",
            "complexity": 3,
            "description": "",
            "files": []
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_medium_complexity_exactly_3_files_assigns_direct(self, analyzer):
        """Test that medium complexity with exactly 3 files assigns direct."""
        subtask = {
            "title": "Update files",
            "description": "",
            "complexity": 5,
            "files": ["a.py", "b.py", "c.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "direct"

    def test_medium_complexity_exactly_4_files_assigns_task_work(self, analyzer):
        """Test that medium complexity with exactly 4 files assigns task-work."""
        subtask = {
            "title": "Update files",
            "description": "",
            "complexity": 5,
            "files": ["a.py", "b.py", "c.py", "d.py"]
        }
        mode = analyzer.assign_mode(subtask)
        assert mode == "task-work"

    def test_no_manual_mode_ever_assigned(self, analyzer):
        """CRITICAL: Verify NO subtask ever gets manual mode."""
        test_cases = [
            # Low complexity
            {"title": "Simple", "complexity": 1, "files": []},
            # Medium complexity, few files
            {"title": "Medium", "complexity": 5, "files": ["a.py"]},
            # Medium complexity, many files
            {"title": "Medium", "complexity": 5, "files": ["a.py", "b.py", "c.py", "d.py"]},
            # High complexity
            {"title": "Complex", "complexity": 8, "files": []},
            # High risk
            {"title": "Security audit", "description": "authentication", "complexity": 3},
            # Boundary cases
            {"title": "Task", "complexity": 3, "files": []},
            {"title": "Task", "complexity": 6, "files": []},
        ]

        for subtask in test_cases:
            mode = analyzer.assign_mode(subtask)
            assert mode in ["task-work", "direct"], \
                f"Invalid mode '{mode}' for subtask: {subtask}"
            assert mode != "manual", \
                f"Manual mode should NEVER be assigned, got for: {subtask}"

    def test_empty_subtask_assigns_valid_mode(self, analyzer):
        """Test that empty subtask still assigns valid mode."""
        subtask = {}
        mode = analyzer.assign_mode(subtask)
        assert mode in ["task-work", "direct"]

    def test_missing_files_field_handled(self, analyzer):
        """Test that missing files field is handled gracefully."""
        subtask = {
            "title": "Task without files",
            "description": "No files field",
            "complexity": 5
        }
        mode = analyzer.assign_mode(subtask)
        # Should use file count = 0, so <=3 files -> direct
        assert mode == "direct"


# ============================================================================
# 4. Batch Mode Assignment Tests (8 tests)
# ============================================================================

class TestBatchModeAssignment:
    """Test assign_modes_to_subtasks() batch processing."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ImplementationModeAnalyzer()

    def test_assigns_modes_to_all_subtasks(self, analyzer):
        """Test that mode is assigned to all subtasks."""
        subtasks = [
            {"title": "Task 1", "complexity": 2},
            {"title": "Task 2", "complexity": 5, "files": ["a.py"]},
            {"title": "Task 3", "complexity": 7}
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        assert len(result) == 3
        for subtask in result:
            assert "implementation_mode" in subtask
            assert subtask["implementation_mode"] in ["task-work", "direct"]

    def test_adds_metadata_fields(self, analyzer):
        """Test that metadata fields are added to each subtask."""
        subtasks = [
            {"title": "Task", "complexity": 5}
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        assert "complexity_analyzed" in result[0]
        assert "risk_level" in result[0]
        assert isinstance(result[0]["complexity_analyzed"], int)
        assert result[0]["risk_level"] in ["high", "medium", "low"]

    def test_risk_level_categorization(self, analyzer):
        """Test that risk_level is correctly categorized."""
        subtasks = [
            {"title": "Security", "description": "authentication"},  # High risk
            {"title": "Medium", "complexity": 5},  # Medium (complexity >= 4)
            {"title": "Low", "complexity": 2}  # Low (complexity < 4)
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        assert result[0]["risk_level"] == "high"
        assert result[1]["risk_level"] == "medium"
        assert result[2]["risk_level"] == "low"

    def test_preserves_explicit_override(self, analyzer):
        """Test that explicit implementation_mode override is preserved."""
        subtasks = [
            {
                "title": "Override task",
                "complexity": 2,
                "implementation_mode": "task-work"  # Explicit override
            }
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        # Should preserve override, not auto-assign
        assert result[0]["implementation_mode"] == "task-work"
        # Should NOT have metadata fields when skipped
        assert "complexity_analyzed" not in result[0]

    def test_empty_list_returns_empty(self, analyzer):
        """Test that empty list returns empty list."""
        result = analyzer.assign_modes_to_subtasks([])
        assert result == []

    def test_modifies_in_place(self, analyzer):
        """Test that subtasks are modified in place."""
        subtasks = [{"title": "Task", "complexity": 5}]
        original_id = id(subtasks[0])

        result = analyzer.assign_modes_to_subtasks(subtasks)

        # Should be same object
        assert id(result[0]) == original_id
        assert "implementation_mode" in subtasks[0]

    def test_mixed_explicit_and_auto_assignment(self, analyzer):
        """Test mix of explicit override and auto-assignment."""
        subtasks = [
            {"title": "Auto 1", "complexity": 2},
            {"title": "Explicit", "complexity": 8, "implementation_mode": "direct"},
            {"title": "Auto 2", "complexity": 7}
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        # Auto-assigned should have modes
        assert result[0]["implementation_mode"] == "direct"
        assert result[2]["implementation_mode"] == "task-work"

        # Explicit should be preserved
        assert result[1]["implementation_mode"] == "direct"

        # Auto-assigned should have metadata
        assert "complexity_analyzed" in result[0]
        assert "complexity_analyzed" in result[2]

        # Explicit should NOT have metadata
        assert "complexity_analyzed" not in result[1]

    def test_no_manual_mode_in_batch(self, analyzer):
        """CRITICAL: Verify no subtask in batch gets manual mode."""
        subtasks = [
            {"title": "Task 1", "complexity": 1},
            {"title": "Task 2", "complexity": 5, "files": ["a.py", "b.py"]},
            {"title": "Task 3", "complexity": 10},
            {"title": "Security", "description": "authentication"},
            {"title": "Docs", "description": "README formatting"}
        ]

        result = analyzer.assign_modes_to_subtasks(subtasks)

        for subtask in result:
            mode = subtask.get("implementation_mode")
            assert mode in ["task-work", "direct"], \
                f"Invalid mode '{mode}' for subtask: {subtask['title']}"
            assert mode != "manual", \
                f"Manual mode should NEVER be assigned to: {subtask['title']}"


# ============================================================================
# 5. Module Function Tests (6 tests)
# ============================================================================

class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_assign_implementation_modes_function(self):
        """Test assign_implementation_modes() convenience function."""
        subtasks = [
            {"title": "Simple", "complexity": 2},
            {"title": "Complex", "complexity": 8}
        ]

        result = assign_implementation_modes(subtasks)

        assert len(result) == 2
        assert result[0]["implementation_mode"] == "direct"
        assert result[1]["implementation_mode"] == "task-work"

    def test_get_mode_summary_counts_modes(self):
        """Test that get_mode_summary() counts each mode correctly."""
        subtasks = [
            {"implementation_mode": "direct"},
            {"implementation_mode": "direct"},
            {"implementation_mode": "task-work"},
            {"implementation_mode": "task-work"},
            {"implementation_mode": "task-work"}
        ]

        summary = get_mode_summary(subtasks)

        assert summary["direct"] == 2
        assert summary["task-work"] == 3

    def test_get_mode_summary_ignores_invalid_modes(self):
        """Test that invalid modes are ignored in summary."""
        subtasks = [
            {"implementation_mode": "direct"},
            {"implementation_mode": "invalid"},
            {"implementation_mode": "task-work"},
            {"implementation_mode": None}
        ]

        summary = get_mode_summary(subtasks)

        assert summary["direct"] == 1
        assert summary["task-work"] == 1
        # Invalid modes should not affect counts

    def test_get_mode_summary_handles_missing_mode(self):
        """Test that missing implementation_mode field is handled."""
        subtasks = [
            {"implementation_mode": "direct"},
            {"title": "No mode field"},
            {"implementation_mode": "task-work"}
        ]

        summary = get_mode_summary(subtasks)

        assert summary["direct"] == 1
        assert summary["task-work"] == 1

    def test_get_mode_summary_no_manual_key(self):
        """CRITICAL: Verify summary NEVER includes 'manual' key."""
        subtasks = [
            {"implementation_mode": "direct"},
            {"implementation_mode": "task-work"},
            {"implementation_mode": "task-work"}
        ]

        summary = get_mode_summary(subtasks)

        # Should only have task-work and direct
        assert set(summary.keys()) == {"task-work", "direct"}
        assert "manual" not in summary

    def test_get_mode_summary_empty_list(self):
        """Test that empty list returns zero counts."""
        summary = get_mode_summary([])

        assert summary["task-work"] == 0
        assert summary["direct"] == 0


# ============================================================================
# 6. Edge Cases and Integration Tests (6 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ImplementationModeAnalyzer()

    def test_unicode_in_title_and_description(self, analyzer):
        """Test that unicode characters are handled correctly."""
        subtask = {
            "title": "Add 日本語 support",
            "description": "Implement émojis 🚀 and spëcial çharacters"
        }

        # Should not crash
        mode = analyzer.assign_mode(subtask)
        assert mode in ["task-work", "direct"]

    def test_very_long_title_and_description(self, analyzer):
        """Test that very long text is handled correctly."""
        subtask = {
            "title": "Task " * 1000,  # 5000 chars
            "description": "Description " * 1000  # 11000 chars
        }

        # Should not crash or timeout
        mode = analyzer.assign_mode(subtask)
        assert mode in ["task-work", "direct"]

    def test_special_characters_in_filenames(self, analyzer):
        """Test that special characters in filenames don't cause issues."""
        subtask = {
            "title": "Update files",
            "files": [
                "file-with-dashes.py",
                "file_with_underscores.js",
                "file.multiple.dots.ts",
                "file (with parens).css"
            ]
        }

        # Should handle extension parsing gracefully
        mode = analyzer.assign_mode(subtask)
        assert mode in ["task-work", "direct"]

    def test_files_without_extensions(self, analyzer):
        """Test that files without extensions are handled."""
        subtask = {
            "title": "Update files",
            "files": [
                "Makefile",
                "Dockerfile",
                "README",
                ".gitignore"
            ]
        }

        # Should not crash when splitting extensions
        mode = analyzer.assign_mode(subtask)
        assert mode in ["task-work", "direct"]

    def test_complete_workflow_integration(self):
        """Test complete workflow from parsing to summary."""
        # Simulate subtasks from review parser
        subtasks = [
            {
                "id": "TASK-001",
                "title": "Fix typo in README",
                "description": "Simple documentation fix",
                "complexity": 1,
                "files": ["README.md"]
            },
            {
                "id": "TASK-002",
                "title": "Add API endpoint",
                "description": "Create new REST endpoint with authentication",
                "complexity": 6,
                "files": ["api/routes.py", "api/auth.py", "tests/test_api.py"]
            },
            {
                "id": "TASK-003",
                "title": "Update styles",
                "description": "CSS formatting changes",
                "complexity": 3,
                "files": ["styles/main.css", "styles/theme.css"]
            }
        ]

        # Assign modes
        result = assign_implementation_modes(subtasks)

        # Verify results
        assert result[0]["implementation_mode"] == "direct"  # Low complexity
        assert result[1]["implementation_mode"] == "task-work"  # High complexity + high risk
        assert result[2]["implementation_mode"] == "direct"  # Low risk

        # Get summary
        summary = get_mode_summary(result)
        assert summary["direct"] == 2
        assert summary["task-work"] == 1
        assert "manual" not in summary

    def test_analyzer_reusability(self):
        """Test that analyzer can be reused for multiple batches."""
        analyzer = ImplementationModeAnalyzer()

        batch1 = [{"title": "Task 1", "complexity": 2}]
        batch2 = [{"title": "Task 2", "complexity": 8}]

        result1 = analyzer.assign_modes_to_subtasks(batch1)
        result2 = analyzer.assign_modes_to_subtasks(batch2)

        # Should work correctly for both batches
        assert result1[0]["implementation_mode"] == "direct"
        assert result2[0]["implementation_mode"] == "task-work"
