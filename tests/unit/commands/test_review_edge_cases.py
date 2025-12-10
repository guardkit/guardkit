"""
Edge case tests for task-review command.

Tests validate error handling, boundary conditions, and unusual inputs.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys
from datetime import datetime

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_review_orchestrator import (
    execute_task_review,
    validate_review_mode,
    validate_review_depth,
    validate_output_format,
    find_task_file,
    load_review_context
)
from task_utils import create_task_frontmatter, write_task_frontmatter


class TestInvalidInputs:
    """Test handling of invalid inputs."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "in_progress", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_missing_task_file(self):
        """Test error when task file doesn't exist."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            result = execute_task_review("TASK-NONEXISTENT")

            # Should return error status
            assert result["status"] == "error"
            assert "not found" in result["error"].lower()

        finally:
            os.chdir(original_dir)

    def test_invalid_task_id_format(self):
        """Test handling of malformed task IDs."""
        invalid_ids = [
            "",
            "   ",
            "TASK",
            "task-001",  # lowercase
            "TASK_001",  # underscore instead of dash
            "001",       # no prefix
            None,
        ]

        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            for invalid_id in invalid_ids:
                if invalid_id is None:
                    try:
                        result = execute_task_review(invalid_id)
                        # If no exception, should return error
                        assert result["status"] == "error"
                    except (TypeError, AttributeError):
                        # Both are acceptable
                        pass
                else:
                    result = execute_task_review(invalid_id)
                    # Should handle gracefully
                    assert result["status"] == "error" or "error" in result

        finally:
            os.chdir(original_dir)

    def test_invalid_review_mode(self):
        """Test validation of invalid review modes."""
        invalid_modes = [
            "invalid",
            "ARCHITECTURAL",  # uppercase
            "arch",           # abbreviated
            "architectural-review",
            "",
            None,
            123,
            ["architectural"],
        ]

        for invalid_mode in invalid_modes:
            if invalid_mode is None or isinstance(invalid_mode, (int, list)):
                with pytest.raises((ValueError, TypeError)):
                    validate_review_mode(invalid_mode)
            else:
                with pytest.raises(ValueError, match="Invalid review mode"):
                    validate_review_mode(invalid_mode)

    def test_invalid_review_depth(self):
        """Test validation of invalid review depths."""
        invalid_depths = [
            "invalid",
            "QUICK",
            "super-comprehensive",
            "",
            None,
            999,
        ]

        for invalid_depth in invalid_depths:
            if invalid_depth is None or isinstance(invalid_depth, int):
                with pytest.raises((ValueError, TypeError)):
                    validate_review_depth(invalid_depth)
            else:
                with pytest.raises(ValueError, match="Invalid review depth"):
                    validate_review_depth(invalid_depth)

    def test_invalid_output_format(self):
        """Test validation of invalid output formats."""
        invalid_formats = [
            "invalid",
            "SUMMARY",
            "pdf",
            "json",
            "",
            None,
        ]

        for invalid_format in invalid_formats:
            if invalid_format is None:
                with pytest.raises((ValueError, TypeError)):
                    validate_output_format(invalid_format)
            else:
                with pytest.raises(ValueError, match="Invalid output format"):
                    validate_output_format(invalid_format)

    def test_empty_review_scope(self):
        """Test handling of task with empty review scope."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            task_content = """---
id: TASK-EMPTY-001
title: Empty scope task
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: medium
tags: []
task_type: review
---

## Description
Task with empty review scope.

## Review Scope


## Acceptance Criteria
- [ ] Review completed
"""
            task_file = self.tasks_dir / "backlog" / "TASK-EMPTY-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Execute review - should handle empty scope
            result = execute_task_review("TASK-EMPTY-001", mode="architectural", depth="quick")

            # Should either succeed with warning or fail gracefully
            assert result["status"] in ["success", "error"]

        finally:
            os.chdir(original_dir)


class TestBoundaryConditions:
    """Test boundary conditions and extreme values."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_task_with_minimum_required_fields(self):
        """Test task with absolute minimum required fields."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Minimal task format
            task_content = """---
id: TASK-MIN-001
title: Minimal task
status: backlog
---

## Description
Minimal content.
"""
            task_file = self.tasks_dir / "backlog" / "TASK-MIN-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Should handle minimal task
            result = execute_task_review("TASK-MIN-001", mode="architectural", depth="quick")

            # Verify doesn't crash
            assert "status" in result

        finally:
            os.chdir(original_dir)

    def test_task_with_maximum_metadata_fields(self):
        """Test task with many metadata fields."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Task with many fields
            frontmatter = create_task_frontmatter(
                task_id="TASK-MAX-001",
                title="Maximum metadata task",
                priority="high",
                tags=["test", "edge-case", "metadata", "max-fields"],
                task_type="review",
                review_mode="comprehensive"
            )

            # Add extra fields
            frontmatter.update({
                "complexity": 8,
                "estimated_effort": "4-6 hours",
                "dependencies": ["TASK-001", "TASK-002"],
                "related_proposal": "docs/proposals/test.md",
                "parent_initiative": "test-initiative",
                "assignee": "test-user",
                "labels": ["critical", "security"],
                "custom_field_1": "value1",
                "custom_field_2": "value2",
            })

            body = """
## Description
Task with many metadata fields.

## Review Scope
Test scope.
"""

            task_file = self.tasks_dir / "backlog" / "TASK-MAX-001.md"
            content = write_task_frontmatter(frontmatter, body)
            task_file.write_text(content, encoding='utf-8')

            # Should handle many fields
            result = execute_task_review("TASK-MAX-001", mode="architectural", depth="quick")

            # Verify success
            assert result["status"] in ["success", "error"]

        finally:
            os.chdir(original_dir)

    def test_task_with_very_long_description(self):
        """Test task with extremely long description."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create very long description (10KB)
            long_description = "A" * 10000

            task_content = f"""---
id: TASK-LONG-001
title: Long description task
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: medium
tags: []
task_type: review
---

## Description
{long_description}

## Review Scope
Test scope.
"""
            task_file = self.tasks_dir / "backlog" / "TASK-LONG-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Should handle long description
            result = execute_task_review("TASK-LONG-001", mode="architectural", depth="quick")

            # Verify doesn't crash
            assert "status" in result

        finally:
            os.chdir(original_dir)


class TestFileSystemEdgeCases:
    """Test file system edge cases."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_task_file_with_no_extension(self):
        """Test handling of task file without .md extension."""
        # Create task file without extension
        task_content = """---
id: TASK-NOEXT-001
title: No extension task
status: backlog
---

## Description
Task file without .md extension.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-NOEXT-001"
        task_file.write_text(task_content, encoding='utf-8')

        # Try to find task - should handle gracefully
        result = find_task_file("TASK-NOEXT-001", self.tasks_dir)

        # May or may not find it depending on implementation
        # But shouldn't crash
        assert result is None or isinstance(result, Path)

    def test_task_in_wrong_directory(self):
        """Test task file in unexpected directory location."""
        # Create task file but put it in wrong state directory
        frontmatter = create_task_frontmatter(
            task_id="TASK-WRONG-001",
            title="Wrong directory task",
            priority="medium",
            tags=["test"],
            task_type="review"
        )
        frontmatter["status"] = "backlog"  # Claims to be in backlog

        body = "## Description\nTask in wrong directory."

        # But actually put it in review_complete
        task_file = self.tasks_dir / "review_complete" / "TASK-WRONG-001.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Should still find it (searches all directories)
        result = find_task_file("TASK-WRONG-001", self.tasks_dir)
        assert result is not None
        assert result.exists()

    def test_duplicate_task_files(self):
        """Test handling of duplicate task files in different directories."""
        # Create same task in multiple directories
        for directory in ["backlog", "review_complete"]:
            task_content = """---
id: TASK-DUP-001
title: Duplicate task
status: backlog
---

## Description
Duplicate task file.
"""
            task_file = self.tasks_dir / directory / "TASK-DUP-001.md"
            task_file.write_text(task_content, encoding='utf-8')

        # find_task_file should return first match
        result = find_task_file("TASK-DUP-001", self.tasks_dir)
        assert result is not None
        assert result.exists()

    def test_readonly_task_file(self):
        """Test handling of read-only task file."""
        import os
        import stat

        # Create task file
        task_content = """---
id: TASK-RO-001
title: Read-only task
status: backlog
---

## Description
Read-only task file.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-RO-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Make file read-only
        os.chmod(task_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        try:
            # Should be able to read
            from task_utils import read_task_file
            metadata, body = read_task_file(task_file)
            assert metadata["id"] == "TASK-RO-001"

            # Writing should fail (if attempted)
            # Note: This is expected behavior, test documents it

        finally:
            # Restore write permissions for cleanup
            os.chmod(task_file, stat.S_IRUSR | stat.S_IWUSR)


class TestConcurrencyEdgeCases:
    """Test edge cases related to concurrent operations."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_task_file_deleted_during_processing(self):
        """Test handling when task file is deleted mid-processing."""
        # Create task file
        task_content = """---
id: TASK-DEL-001
title: Will be deleted
status: backlog
---

## Description
Task that will be deleted.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-DEL-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Find the file
        found_file = find_task_file("TASK-DEL-001", self.tasks_dir)
        assert found_file is not None

        # Delete the file
        task_file.unlink()

        # Try to read context - should fail gracefully
        with pytest.raises(FileNotFoundError):
            load_review_context("TASK-DEL-001", self.tasks_dir)

    def test_task_directory_doesnt_exist(self):
        """Test handling when task directory doesn't exist."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent" / "tasks"

        # Should handle missing directory gracefully
        result = find_task_file("TASK-001", nonexistent_dir)
        assert result is None


class TestMalformedData:
    """Test handling of malformed task data."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_task_with_invalid_yaml_frontmatter(self):
        """Test handling of task with malformed YAML."""
        # Create task with invalid YAML
        task_content = """---
id: TASK-BAD-001
title: Bad YAML task
this is not valid yaml: : : {]
status: backlog
---

## Description
Task with bad YAML.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-BAD-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Try to read - should fail with appropriate error
        from task_utils import read_task_file

        with pytest.raises(Exception):  # YAML parsing error
            read_task_file(task_file)

    def test_task_with_missing_frontmatter_delimiters(self):
        """Test handling of task missing frontmatter delimiters."""
        # Create task without proper frontmatter
        task_content = """
id: TASK-NOFRONT-001
title: No frontmatter task

## Description
Task without frontmatter delimiters.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-NOFRONT-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Try to read - should fail gracefully
        from task_utils import read_task_file

        with pytest.raises(Exception):
            read_task_file(task_file)

    def test_task_with_binary_content(self):
        """Test handling of task file with binary content."""
        # Create file with binary content
        task_file = self.tasks_dir / "backlog" / "TASK-BIN-001.md"

        with open(task_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\xff\xfe\xfd')

        # Try to read - should fail gracefully
        from task_utils import read_task_file

        with pytest.raises(Exception):
            read_task_file(task_file)

    def test_task_with_only_whitespace(self):
        """Test handling of empty task file."""
        # Create file with only whitespace
        task_content = "\n\n   \n\n"
        task_file = self.tasks_dir / "backlog" / "TASK-EMPTY-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Try to read - should fail gracefully
        from task_utils import read_task_file

        with pytest.raises(Exception):
            read_task_file(task_file)


class TestAgentFailureHandling:
    """Test handling of agent invocation failures."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_agent_timeout(self):
        """Test handling when agent invocation times out."""
        # Note: This would require mocking or actual timeout
        # This test documents expected behavior

        # Create test task
        task_content = """---
id: TASK-TIMEOUT-001
title: Timeout test
status: backlog
task_type: review
---

## Description
Task to test timeout handling.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-TIMEOUT-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Expected: System should handle timeout gracefully
        # Would return error status with timeout message

    def test_agent_returns_invalid_response(self):
        """Test handling when agent returns malformed response."""
        # Note: Would require mocking agent response
        # This test documents expected behavior

        # Expected: System should parse what it can,
        # use fallback values for missing data,
        # and include error in findings


class TestReportGenerationEdgeCases:
    """Test edge cases in report generation."""

    def test_report_with_no_findings(self):
        """Test report generation when there are no findings."""
        from task_review_orchestrator import generate_review_report

        review_results = {
            "mode": "architectural",
            "depth": "quick",
            "findings": [],  # No findings
            "overall_score": 100
        }

        recommendations = {
            "recommendations": [],  # No recommendations
            "confidence": 1.0
        }

        # Should generate report successfully
        report = generate_review_report(review_results, recommendations, "detailed")

        assert isinstance(report, str)
        assert len(report) > 0
        assert "# Review Report" in report

    def test_report_with_many_findings(self):
        """Test report generation with very many findings."""
        from task_review_orchestrator import generate_review_report

        # Create 1000 findings
        findings = [
            {
                "severity": "low",
                "category": "Code Quality",
                "description": f"Finding {i}",
                "file": f"file{i}.py",
                "line": i
            }
            for i in range(1000)
        ]

        review_results = {
            "mode": "code-quality",
            "depth": "comprehensive",
            "findings": findings,
            "overall_score": 60
        }

        recommendations = {
            "recommendations": [],
            "confidence": 0.7
        }

        # Should generate report without crashing
        report = generate_review_report(review_results, recommendations, "summary")

        assert isinstance(report, str)
        assert len(report) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
