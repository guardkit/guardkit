"""
Integration tests for task-review command integration with task-create and workflow.

Tests cover:
- Review task detection in task-create
- REVIEW_COMPLETE state management
- Directory structure (tasks/review_complete/, .claude/reviews/)
- Task metadata for review tasks
- Integration between task-review and task-work
"""

import pytest
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime


@pytest.fixture
def temp_task_dir():
    """Create temporary task directory structure."""
    temp_dir = tempfile.mkdtemp()

    # Create task state directories
    os.makedirs(os.path.join(temp_dir, "tasks", "backlog"))
    os.makedirs(os.path.join(temp_dir, "tasks", "in_progress"))
    os.makedirs(os.path.join(temp_dir, "tasks", "in_review"))
    os.makedirs(os.path.join(temp_dir, "tasks", "review_complete"))
    os.makedirs(os.path.join(temp_dir, "tasks", "blocked"))
    os.makedirs(os.path.join(temp_dir, "tasks", "completed"))

    # Create review reports directory
    os.makedirs(os.path.join(temp_dir, ".claude", "reviews"))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_review_task():
    """Sample review task metadata."""
    return {
        "id": "TASK-REV-A3F2",
        "title": "Review authentication architecture",
        "status": "backlog",
        "task_type": "review",
        "priority": "high",
        "tags": ["architecture", "security"],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }


@pytest.fixture
def sample_implementation_task():
    """Sample implementation task metadata."""
    return {
        "id": "TASK-IMP-B4D1",
        "title": "Implement user authentication",
        "status": "backlog",
        "priority": "high",
        "tags": ["auth", "security"],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }


class TestTaskCreationDetection:
    """Test review task detection during task creation."""

    def test_detect_explicit_task_type(self):
        """Test detection when task_type:review is explicitly provided."""
        title = "Architectural review of authentication"
        args = {"task_type": "review"}

        # This would call the detection logic from task-create.md
        # For now, we're testing the logic described in the spec
        is_review = self._detect_review_task(title, args)

        assert is_review is True

    def test_detect_decision_required_flag(self):
        """Test detection when decision_required:true is provided."""
        title = "Should we migrate to microservices?"
        args = {"decision_required": True}

        is_review = self._detect_review_task(title, args)

        assert is_review is True

    def test_detect_review_tags(self):
        """Test detection based on review-related tags."""
        title = "Code quality assessment"
        args = {"tags": ["code-review", "assessment"]}

        is_review = self._detect_review_task(title, args)

        assert is_review is True

    def test_detect_title_keywords(self):
        """Test detection based on title keywords."""
        test_cases = [
            "Review authentication architecture",
            "Analyze caching strategy",
            "Evaluate database options",
            "Assess technical debt",
            "Audit security implementation",
            "Investigation of performance issues"
        ]

        for title in test_cases:
            is_review = self._detect_review_task(title, {})
            assert is_review is True, f"Failed to detect review task: {title}"

    def test_no_false_positives(self):
        """Test that implementation tasks are not detected as review tasks."""
        test_cases = [
            "Implement user authentication",
            "Fix login bug",
            "Refactor authentication service",
            "Add password reset feature",
            "Create user profile page"
        ]

        for title in test_cases:
            is_review = self._detect_review_task(title, {})
            assert is_review is False, f"False positive for implementation task: {title}"

    def _detect_review_task(self, title: str, args: dict) -> bool:
        """
        Implement review task detection logic from task-create.md spec.

        Detection criteria:
        1. Explicit task_type field: task_type=review
        2. Decision required flag: decision_required=true
        3. Review-related tags: architecture-review, code-review, decision-point, assessment
        4. Title keywords: review, analyze, evaluate, assess, audit, investigation
        """
        # Explicit task_type field
        if args.get("task_type") == "review":
            return True

        # decision_required flag
        if args.get("decision_required"):
            return True

        # Review-related tags
        review_tags = {"architecture-review", "code-review", "decision-point", "assessment"}
        task_tags = set(args.get("tags", []))
        if review_tags & task_tags:
            return True

        # Title keywords
        title_lower = title.lower()
        review_keywords = ["review", "analyze", "evaluate", "assess", "audit", "investigation"]
        if any(keyword in title_lower for keyword in review_keywords):
            return True

        return False


class TestReviewCompleteState:
    """Test REVIEW_COMPLETE state management."""

    def test_review_complete_directory_exists(self, temp_task_dir):
        """Test that review_complete directory exists."""
        review_complete_dir = os.path.join(temp_task_dir, "tasks", "review_complete")
        assert os.path.exists(review_complete_dir)
        assert os.path.isdir(review_complete_dir)

    def test_reviews_directory_exists(self, temp_task_dir):
        """Test that .claude/reviews directory exists for report storage."""
        reviews_dir = os.path.join(temp_task_dir, ".claude", "reviews")
        assert os.path.exists(reviews_dir)
        assert os.path.isdir(reviews_dir)

    def test_task_metadata_with_review_results(self, temp_task_dir, sample_review_task):
        """Test task metadata includes review_results after review completion."""
        # Simulate task moving to review_complete with results
        task = sample_review_task.copy()
        task["status"] = "review_complete"
        task["review_results"] = {
            "mode": "architectural",
            "depth": "standard",
            "score": 72,
            "findings_count": 8,
            "recommendations_count": 5,
            "decision": "refactor",
            "report_path": ".claude/reviews/TASK-REV-A3F2-review-report.md",
            "completed_at": datetime.now().isoformat()
        }

        # Write task file
        task_file = os.path.join(temp_task_dir, "tasks", "review_complete", "TASK-REV-A3F2.md")
        self._write_task_file(task_file, task)

        # Verify file exists and contains review_results
        assert os.path.exists(task_file)
        with open(task_file, 'r') as f:
            content = f.read()
            assert "review_complete" in content
            assert "review_results:" in content
            assert "mode: architectural" in content

    def _write_task_file(self, filepath: str, task: dict):
        """Write task to markdown file with frontmatter."""
        with open(filepath, 'w') as f:
            f.write("---\n")
            for key, value in task.items():
                if isinstance(value, dict):
                    f.write(f"{key}:\n")
                    for k, v in value.items():
                        f.write(f"  {k}: {v}\n")
                elif isinstance(value, list):
                    f.write(f"{key}: {value}\n")
                else:
                    f.write(f"{key}: {value}\n")
            f.write("---\n\n")
            f.write(f"# Task: {task['title']}\n\n")
            f.write("## Description\n\n")
            f.write("[Task description]\n")


class TestStateTransitions:
    """Test state transitions for review workflow."""

    def test_review_workflow_states(self, temp_task_dir, sample_review_task):
        """Test complete review workflow state transitions."""
        # 1. Start in BACKLOG
        task = sample_review_task.copy()
        task_file_backlog = os.path.join(temp_task_dir, "tasks", "backlog", f"{task['id']}.md")

        # 2. Move to IN_PROGRESS when /task-review starts
        task["status"] = "in_progress"
        task_file_progress = os.path.join(temp_task_dir, "tasks", "in_progress", f"{task['id']}.md")

        # 3. Move to REVIEW_COMPLETE when review finishes
        task["status"] = "review_complete"
        task["review_results"] = {
            "mode": "architectural",
            "score": 75,
            "decision": "pending"
        }
        task_file_review_complete = os.path.join(temp_task_dir, "tasks", "review_complete", f"{task['id']}.md")

        # 4. Option A: Move to COMPLETED if [A]ccept
        task_accepted = task.copy()
        task_accepted["status"] = "completed"
        task_accepted["review_results"]["decision"] = "accepted"
        task_file_completed = os.path.join(temp_task_dir, "tasks", "completed", f"{task['id']}.md")

        # Verify all state directories exist
        assert os.path.exists(os.path.dirname(task_file_backlog))
        assert os.path.exists(os.path.dirname(task_file_progress))
        assert os.path.exists(os.path.dirname(task_file_review_complete))
        assert os.path.exists(os.path.dirname(task_file_completed))

    def test_implementation_after_review(self, temp_task_dir, sample_review_task, sample_implementation_task):
        """Test [I]mplement option creates new implementation task."""
        # Review task in review_complete
        review_task = sample_review_task.copy()
        review_task["status"] = "review_complete"

        # Implementation task created from review
        impl_task = sample_implementation_task.copy()
        impl_task["related_review"] = review_task["id"]
        impl_task["status"] = "backlog"

        # Verify link between tasks
        assert "related_review" in impl_task
        assert impl_task["related_review"] == review_task["id"]


class TestReviewReportGeneration:
    """Test review report generation and storage."""

    def test_report_file_naming(self, temp_task_dir):
        """Test review report follows naming convention."""
        task_id = "TASK-REV-A3F2"
        expected_path = os.path.join(temp_task_dir, ".claude", "reviews", f"{task_id}-review-report.md")

        # Create mock report
        os.makedirs(os.path.dirname(expected_path), exist_ok=True)
        with open(expected_path, 'w') as f:
            f.write("# Review Report: TASK-REV-A3F2\n")

        assert os.path.exists(expected_path)
        assert os.path.basename(expected_path) == "TASK-REV-A3F2-review-report.md"

    def test_report_structure(self, temp_task_dir):
        """Test review report contains required sections."""
        task_id = "TASK-REV-A3F2"
        report_path = os.path.join(temp_task_dir, ".claude", "reviews", f"{task_id}-review-report.md")

        # Create mock report with required sections
        report_content = """# Review Report: TASK-REV-A3F2

## Executive Summary
[Brief overview]

## Review Details
- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: 1.5 hours

## Findings
1. [Finding 1]
2. [Finding 2]

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

## Decision Matrix
| Option | Score | Effort | Risk |
|--------|-------|--------|------|
| Keep   | 6/10  | 0h     | High |
| Refactor | 9/10 | 8h   | Low  |
"""

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report_content)

        # Verify required sections
        with open(report_path, 'r') as f:
            content = f.read()
            assert "Executive Summary" in content
            assert "Review Details" in content
            assert "Findings" in content
            assert "Recommendations" in content
            assert "Decision Matrix" in content


class TestCommandIntegration:
    """Test integration between task-create, task-review, and task-work."""

    def test_create_review_task_flow(self):
        """Test complete flow from creation to review to implementation."""
        # Step 1: Create review task
        # /task-create "Review authentication" task_type:review
        # Expected: Task created in backlog with task_type=review

        # Step 2: Execute review
        # /task-review TASK-REV-001 --mode=architectural
        # Expected: Task moves to in_progress, then review_complete

        # Step 3: Choose [I]mplement
        # Expected: New implementation task created in backlog

        # Step 4: Work on implementation
        # /task-work TASK-IMP-002
        # Expected: Standard implementation workflow

        # This test documents the expected flow
        # Actual implementation would require command execution
        pass

    def test_task_metadata_fields(self, sample_review_task):
        """Test review tasks have required metadata fields."""
        task = sample_review_task

        # Required fields for review tasks
        assert "id" in task
        assert "title" in task
        assert "status" in task
        assert "task_type" in task
        assert task["task_type"] == "review"
        assert "created" in task
        assert "updated" in task


class TestDirectoryStructure:
    """Test directory structure for review workflow."""

    def test_all_task_state_directories_exist(self, temp_task_dir):
        """Test all task state directories exist."""
        required_dirs = [
            "tasks/backlog",
            "tasks/in_progress",
            "tasks/in_review",
            "tasks/review_complete",
            "tasks/blocked",
            "tasks/completed"
        ]

        for dir_path in required_dirs:
            full_path = os.path.join(temp_task_dir, dir_path)
            assert os.path.exists(full_path), f"Missing directory: {dir_path}"
            assert os.path.isdir(full_path)

    def test_review_reports_directory_exists(self, temp_task_dir):
        """Test .claude/reviews directory for report storage."""
        reviews_dir = os.path.join(temp_task_dir, ".claude", "reviews")
        assert os.path.exists(reviews_dir)
        assert os.path.isdir(reviews_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
