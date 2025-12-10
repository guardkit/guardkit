"""
Integration tests for task-review workflow.

Tests the complete workflow from task creation through review execution
and state transitions.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

import sys

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_review_orchestrator import (
    execute_task_review,
    find_task_file,
    load_review_context
)
from task_utils import (
    create_task_frontmatter,
    write_task_frontmatter,
    read_task_file
)


class TestReviewWorkflowIntegration:
    """Integration tests for complete review workflow."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        # Create all task state directories
        for state in ["backlog", "in_progress", "in_review", "blocked", "completed", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def _create_review_task(
        self,
        task_id: str,
        title: str,
        description: str,
        review_scope: str,
        task_type: str = "review",
        review_mode: str = "architectural"
    ) -> Path:
        """Helper to create a review task file."""
        # Create frontmatter
        frontmatter = create_task_frontmatter(
            task_id=task_id,
            title=title,
            priority="medium",
            tags=["review", "integration-test"],
            task_type=task_type,
            review_mode=review_mode
        )

        # Create body
        body = f"""
## Description
{description}

## Review Scope
{review_scope}

## Acceptance Criteria
- [ ] Review completed
- [ ] Findings documented
- [ ] Recommendations provided
"""

        # Write task file
        task_file = self.tasks_dir / "backlog" / f"{task_id}-{title.replace(' ', '-').lower()}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        return task_file

    def test_create_and_execute_architectural_review(self):
        """Test creating and executing an architectural review."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create review task
            task_id = "TASK-INT-001"
            self._create_review_task(
                task_id=task_id,
                title="Review authentication architecture",
                description="Comprehensive review of authentication system architecture",
                review_scope="Authentication controllers, JWT handling, password hashing",
                review_mode="architectural"
            )

            # Execute review
            result = execute_task_review(
                task_id,
                mode="architectural",
                depth="standard",
                output="detailed"
            )

            # Verify success
            assert result["status"] == "success"
            assert result["review_mode"] == "architectural"
            assert result["review_depth"] == "standard"

            # Verify task moved to review_complete
            task_file = find_task_file(task_id, self.tasks_dir)
            assert task_file is not None
            assert "review_complete" in str(task_file)

            # Verify metadata updated
            metadata, body = read_task_file(task_file)
            assert metadata["status"] == "review_complete"
            assert metadata["task_type"] == "review"
            assert metadata["review_mode"] == "architectural"
            assert metadata["review_depth"] == "standard"

        finally:
            os.chdir(original_dir)

    def test_create_and_execute_code_quality_review(self):
        """Test creating and executing a code quality review."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create review task
            task_id = "TASK-INT-002"
            self._create_review_task(
                task_id=task_id,
                title="Code quality review",
                description="Review code quality and maintainability",
                review_scope="Core business logic modules",
                review_mode="code-quality"
            )

            # Execute review
            result = execute_task_review(
                task_id,
                mode="code-quality",
                depth="comprehensive",
                output="summary"
            )

            # Verify success
            assert result["status"] == "success"
            assert result["review_mode"] == "code-quality"
            assert result["review_depth"] == "comprehensive"

            # Verify task state
            task_file = find_task_file(task_id, self.tasks_dir)
            metadata, _ = read_task_file(task_file)
            assert metadata["status"] == "review_complete"
            assert metadata["review_mode"] == "code-quality"

        finally:
            os.chdir(original_dir)

    def test_create_and_execute_decision_analysis(self):
        """Test creating and executing a decision analysis review."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create review task
            task_id = "TASK-INT-003"
            self._create_review_task(
                task_id=task_id,
                title="Database migration decision",
                description="Analyze options for database migration strategy",
                review_scope="Database architecture, migration tools, downtime requirements",
                review_mode="decision"
            )

            # Execute review
            result = execute_task_review(
                task_id,
                mode="decision",
                depth="quick",
                output="presentation"
            )

            # Verify success
            assert result["status"] == "success"
            assert result["review_mode"] == "decision"

        finally:
            os.chdir(original_dir)

    def test_execute_review_from_in_progress_state(self):
        """Test executing review on task already in progress."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task in in_progress state
            task_id = "TASK-INT-004"
            frontmatter = create_task_frontmatter(
                task_id=task_id,
                title="In-progress review",
                priority="high",
                task_type="review",
                review_mode="security"
            )
            frontmatter["status"] = "in_progress"  # Already in progress

            body = """
## Description
Security review already started.

## Review Scope
Authentication and authorization.
"""
            task_file = self.tasks_dir / "in_progress" / f"{task_id}-in-progress.md"
            content = write_task_frontmatter(frontmatter, body)
            task_file.write_text(content, encoding='utf-8')

            # Execute review
            result = execute_task_review(
                task_id,
                mode="security",
                depth="comprehensive",
                output="detailed"
            )

            # Should succeed
            assert result["status"] == "success"

            # Should move to review_complete
            task_file = find_task_file(task_id, self.tasks_dir)
            assert "review_complete" in str(task_file)

        finally:
            os.chdir(original_dir)

    def test_review_workflow_preserves_task_metadata(self):
        """Test that review workflow preserves original task metadata."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task with specific metadata
            task_id = "TASK-INT-005"
            original_priority = "high"
            original_tags = ["critical", "security", "review"]

            frontmatter = create_task_frontmatter(
                task_id=task_id,
                title="Metadata preservation test",
                priority=original_priority,
                tags=original_tags,
                task_type="review",
                review_mode="security",
                complexity=7
            )

            body = """
## Description
Test metadata preservation.

## Review Scope
All components.
"""
            task_file = self.tasks_dir / "backlog" / f"{task_id}-metadata-test.md"
            content = write_task_frontmatter(frontmatter, body)
            task_file.write_text(content, encoding='utf-8')

            # Execute review
            result = execute_task_review(task_id, mode="security")

            # Verify success
            assert result["status"] == "success"

            # Verify metadata preserved
            task_file = find_task_file(task_id, self.tasks_dir)
            metadata, _ = read_task_file(task_file)

            assert metadata["priority"] == original_priority
            assert metadata["tags"] == original_tags
            assert metadata["complexity"] == 7
            assert metadata["id"] == task_id

            # Verify review-specific metadata added
            assert metadata["task_type"] == "review"
            assert metadata["review_mode"] == "security"
            assert metadata["review_depth"] == "standard"  # default

        finally:
            os.chdir(original_dir)

    def test_multiple_reviews_sequential(self):
        """Test executing multiple reviews sequentially."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create multiple review tasks
            task_ids = ["TASK-SEQ-001", "TASK-SEQ-002", "TASK-SEQ-003"]

            for i, task_id in enumerate(task_ids):
                self._create_review_task(
                    task_id=task_id,
                    title=f"Sequential review {i+1}",
                    description=f"Review task {i+1}",
                    review_scope="Test scope"
                )

            # Execute all reviews
            results = []
            for task_id in task_ids:
                result = execute_task_review(task_id)
                results.append(result)

            # Verify all succeeded
            for result in results:
                assert result["status"] == "success"

            # Verify all moved to review_complete
            for task_id in task_ids:
                task_file = find_task_file(task_id, self.tasks_dir)
                assert task_file is not None
                assert "review_complete" in str(task_file)

        finally:
            os.chdir(original_dir)

    def test_error_handling_missing_task(self):
        """Test error handling when task doesn't exist."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Try to review non-existent task
            result = execute_task_review("TASK-MISSING-999")

            # Should fail gracefully
            assert result["status"] == "error"
            assert "not found" in result["error"].lower()

        finally:
            os.chdir(original_dir)

    def test_error_handling_invalid_parameters(self):
        """Test error handling for invalid review parameters."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task
            task_id = "TASK-ERR-001"
            self._create_review_task(
                task_id=task_id,
                title="Error handling test",
                description="Test error handling",
                review_scope="Error cases"
            )

            # Try with invalid mode
            result = execute_task_review(task_id, mode="invalid-mode")
            assert result["status"] == "error"
            assert "Invalid review mode" in result["error"]

            # Try with invalid depth
            result = execute_task_review(task_id, depth="invalid-depth")
            assert result["status"] == "error"
            assert "Invalid review depth" in result["error"]

            # Try with invalid output
            result = execute_task_review(task_id, output="invalid-output")
            assert result["status"] == "error"
            assert "Invalid output format" in result["error"]

        finally:
            os.chdir(original_dir)


class TestReviewContextLoading:
    """Integration tests for review context loading."""

    def setup_method(self):
        """Set up temporary task directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()
        (self.tasks_dir / "backlog").mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_load_context_with_all_sections(self):
        """Test loading context when all sections present."""
        task_content = """---
id: TASK-CTX-001
title: Full context test
status: backlog
created: 2025-01-20T00:00:00Z
updated: 2025-01-20T00:00:00Z
priority: high
tags: [test]
task_type: review
review_mode: architectural
---

## Description
This is a comprehensive test of context loading.
It has multiple lines and paragraphs.

## Review Scope
- Component A
- Component B
- Component C

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Additional Notes
Some additional notes here.
"""
        task_file = self.tasks_dir / "backlog" / "TASK-CTX-001-test.md"
        task_file.write_text(task_content)

        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            context = load_review_context("TASK-CTX-001", self.tasks_dir)

            # Verify all sections loaded
            assert context["task_id"] == "TASK-CTX-001"
            assert context["title"] == "Full context test"
            assert "comprehensive test" in context["description"]
            assert "Component A" in context["review_scope"]
            assert context["metadata"]["task_type"] == "review"
            assert context["metadata"]["review_mode"] == "architectural"

        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
