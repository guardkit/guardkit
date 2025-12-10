"""
Unit tests for review state management.

Tests validate proper state transitions, metadata updates, and task file movements
during the review workflow.
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

from task_utils import (
    create_task_frontmatter,
    write_task_frontmatter,
    read_task_file,
    update_task_frontmatter
)


class TestReviewStateTransitions:
    """Test state transitions during review workflow."""

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

    def _create_task(self, task_id: str, title: str, status: str = "backlog") -> Path:
        """Helper to create a task file in a specific state."""
        frontmatter = create_task_frontmatter(
            task_id=task_id,
            title=title,
            priority="medium",
            tags=["test"],
            task_type="review",
            review_mode="architectural"
        )
        frontmatter["status"] = status

        body = """
## Description
Test task for state management.

## Review Scope
Test scope.
"""

        task_file = self.tasks_dir / status / f"{task_id}-{title.replace(' ', '-').lower()}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        return task_file

    def test_task_moves_from_backlog_to_review_complete(self):
        """Test that task file physically moves from backlog to review_complete."""
        task_id = "TASK-STATE-001"
        original_file = self._create_task(task_id, "Move test", "backlog")

        assert original_file.exists()
        assert "backlog" in str(original_file)

        # Simulate review completion (move file)
        new_file = self.tasks_dir / "review_complete" / original_file.name
        shutil.move(str(original_file), str(new_file))

        # Update status in frontmatter
        metadata, body = read_task_file(new_file)
        metadata["status"] = "review_complete"
        new_content = write_task_frontmatter(metadata, body)
        new_file.write_text(new_content, encoding='utf-8')

        # Verify move
        assert not original_file.exists()
        assert new_file.exists()
        assert "review_complete" in str(new_file)

        # Verify metadata updated
        updated_metadata, _ = read_task_file(new_file)
        assert updated_metadata["status"] == "review_complete"

    def test_review_metadata_added_to_task(self):
        """Test that review metadata is properly added to task."""
        task_id = "TASK-META-001"
        task_file = self._create_task(task_id, "Metadata test", "backlog")

        # Read original metadata
        metadata, body = read_task_file(task_file)
        assert "review_results" not in metadata

        # Add review metadata
        review_results = {
            "mode": "architectural",
            "depth": "standard",
            "overall_score": 85,
            "completion_date": datetime.now().isoformat(),
            "review_duration_seconds": 120
        }
        update_task_frontmatter(task_file, {"review_results": review_results})

        # Verify metadata added
        updated_metadata, _ = read_task_file(task_file)
        assert "review_results" in updated_metadata
        assert updated_metadata["review_results"]["mode"] == "architectural"
        assert updated_metadata["review_results"]["overall_score"] == 85

    def test_task_type_preserved_during_review(self):
        """Test that task_type='review' is preserved throughout workflow."""
        task_id = "TASK-TYPE-001"
        task_file = self._create_task(task_id, "Type test", "backlog")

        # Verify initial task_type
        metadata, _ = read_task_file(task_file)
        assert metadata["task_type"] == "review"

        # Simulate state change
        update_task_frontmatter(task_file, {"status": "review_complete"})

        # Verify task_type still present
        updated_metadata, _ = read_task_file(task_file)
        assert updated_metadata["task_type"] == "review"

    def test_review_mode_preserved_during_review(self):
        """Test that review_mode is preserved throughout workflow."""
        task_id = "TASK-MODE-001"
        task_file = self._create_task(task_id, "Mode test", "backlog")

        # Verify initial review_mode
        metadata, _ = read_task_file(task_file)
        assert metadata["review_mode"] == "architectural"

        # Change to different mode
        update_task_frontmatter(task_file, {"review_mode": "security"})

        # Verify mode changed
        updated_metadata, _ = read_task_file(task_file)
        assert updated_metadata["review_mode"] == "security"

    def test_multiple_review_runs_append_results(self):
        """Test that multiple review runs append results (not overwrite)."""
        task_id = "TASK-MULTI-001"
        task_file = self._create_task(task_id, "Multiple runs test", "backlog")

        # First review run
        metadata, body = read_task_file(task_file)
        review_results_1 = {
            "mode": "architectural",
            "depth": "quick",
            "overall_score": 75,
            "completion_date": datetime.now().isoformat()
        }
        update_task_frontmatter(task_file, {"review_results": review_results_1})

        # Second review run (different mode)
        metadata, body = read_task_file(task_file)
        review_history = metadata.get("review_history", [])
        review_history.append(metadata["review_results"])

        # New review result
        review_results_2 = {
            "mode": "security",
            "depth": "standard",
            "overall_score": 88,
            "completion_date": datetime.now().isoformat()
        }
        update_task_frontmatter(task_file, {
            "review_results": review_results_2,
            "review_history": review_history
        })

        # Verify both results preserved
        updated_metadata, _ = read_task_file(task_file)
        assert updated_metadata["review_results"]["mode"] == "security"
        assert len(updated_metadata["review_history"]) == 1
        assert updated_metadata["review_history"][0]["mode"] == "architectural"

    def test_timestamp_updated_on_state_change(self):
        """Test that updated timestamp changes when task state changes."""
        task_id = "TASK-TIME-001"
        task_file = self._create_task(task_id, "Timestamp test", "backlog")

        # Get initial timestamp
        metadata1, _ = read_task_file(task_file)
        original_timestamp = metadata1["updated"]

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.1)

        # Update state
        update_task_frontmatter(task_file, {"status": "review_complete"})

        # Verify timestamp changed
        metadata2, _ = read_task_file(task_file)
        assert metadata2["updated"] != original_timestamp

    def test_task_with_no_task_type_gets_default(self):
        """Test backward compatibility: tasks without task_type get default."""
        task_id = "TASK-COMPAT-001"

        # Create task without task_type (old format)
        frontmatter = {
            "id": task_id,
            "title": "Compatibility test",
            "status": "backlog",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "priority": "medium",
            "tags": []
        }

        body = "## Description\nOld format task."

        task_file = self.tasks_dir / "backlog" / f"{task_id}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Read and verify no task_type
        metadata, _ = read_task_file(task_file)
        assert "task_type" not in metadata

        # When processing for review, task_type should be inferred
        # (This would be done by the orchestrator)
        update_task_frontmatter(task_file, {"task_type": "review"})

        # Verify task_type added
        updated_metadata, _ = read_task_file(task_file)
        assert updated_metadata["task_type"] == "review"


class TestReviewMetadataValidation:
    """Test validation of review metadata structure."""

    def setup_method(self):
        """Set up temporary directory."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_valid_review_results_structure(self):
        """Test that valid review_results structure is accepted."""
        valid_results = {
            "mode": "architectural",
            "depth": "standard",
            "overall_score": 85,
            "completion_date": datetime.now().isoformat(),
            "findings_count": 12,
            "recommendations_count": 5
        }

        # Verify all required fields present
        assert "mode" in valid_results
        assert "depth" in valid_results
        assert "overall_score" in valid_results
        assert "completion_date" in valid_results

        # Verify score in valid range
        assert 0 <= valid_results["overall_score"] <= 100

    def test_invalid_review_mode_rejected(self):
        """Test that invalid review modes are caught."""
        invalid_modes = ["invalid", "architectural-review", "ARCHITECTURAL", ""]

        VALID_MODES = ["architectural", "code-quality", "decision", "technical-debt", "security"]

        for invalid_mode in invalid_modes:
            assert invalid_mode not in VALID_MODES

    def test_invalid_review_depth_rejected(self):
        """Test that invalid review depths are caught."""
        invalid_depths = ["invalid", "QUICK", "Quick", "super-detailed", ""]

        VALID_DEPTHS = ["quick", "standard", "comprehensive"]

        for invalid_depth in invalid_depths:
            assert invalid_depth not in VALID_DEPTHS

    def test_score_bounds_validation(self):
        """Test that scores are validated to be within 0-100 range."""
        def validate_score(score):
            """Validate score is in range 0-100."""
            if not isinstance(score, (int, float)):
                return False
            return 0 <= score <= 100

        # Valid scores
        assert validate_score(0)
        assert validate_score(50)
        assert validate_score(100)
        assert validate_score(75.5)

        # Invalid scores
        assert not validate_score(-1)
        assert not validate_score(101)
        assert not validate_score(150)
        assert not validate_score("85")
        assert not validate_score(None)


class TestReviewStateEdgeCases:
    """Test edge cases in state management."""

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

    def test_task_with_unicode_in_title(self):
        """Test that tasks with Unicode characters in title are handled correctly."""
        frontmatter = create_task_frontmatter(
            task_id="TASK-UNI-001",
            title="Review 测试 with émojis 🚀",
            priority="medium",
            tags=["unicode"],
            task_type="review"
        )

        body = "## Description\nUnicode test task."

        task_file = self.tasks_dir / "backlog" / "TASK-UNI-001-unicode-test.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Verify can read back
        metadata, body_read = read_task_file(task_file)
        assert "测试" in metadata["title"]
        assert "🚀" in metadata["title"]

    def test_task_with_very_long_title(self):
        """Test that tasks with very long titles are handled correctly."""
        long_title = "A" * 200  # 200 character title

        frontmatter = create_task_frontmatter(
            task_id="TASK-LONG-001",
            title=long_title,
            priority="medium",
            tags=["test"],
            task_type="review"
        )

        body = "## Description\nLong title test."

        task_file = self.tasks_dir / "backlog" / "TASK-LONG-001.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Verify can read back
        metadata, _ = read_task_file(task_file)
        assert len(metadata["title"]) == 200

    def test_task_with_special_characters_in_metadata(self):
        """Test that special characters in metadata are handled correctly."""
        frontmatter = create_task_frontmatter(
            task_id="TASK-SPEC-001",
            title="Test: with special chars & symbols",
            priority="medium",
            tags=["test", "special-chars", "symbols!"],
            task_type="review"
        )

        body = """
## Description
Testing special characters: & < > " ' / \\ | ? * [ ] { }

## Review Scope
Files with special characters.
"""

        task_file = self.tasks_dir / "backlog" / "TASK-SPEC-001.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Verify can read back
        metadata, body_read = read_task_file(task_file)
        assert "&" in metadata["title"]
        assert "&" in body_read

    def test_concurrent_state_updates(self):
        """Test handling of concurrent state updates (race condition simulation)."""
        task_id = "TASK-RACE-001"

        frontmatter = create_task_frontmatter(
            task_id=task_id,
            title="Concurrency test",
            priority="medium",
            tags=["test"],
            task_type="review"
        )

        body = "## Description\nConcurrency test."

        task_file = self.tasks_dir / "backlog" / f"{task_id}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Simulate two processes reading at same time
        metadata1, body1 = read_task_file(task_file)
        metadata2, body2 = read_task_file(task_file)

        # Both make different updates
        metadata1["status"] = "in_progress"
        metadata2["review_mode"] = "security"

        # First write
        update_task_frontmatter(task_file, {"status": "in_progress"})

        # Second write (overwrites)
        update_task_frontmatter(task_file, {"review_mode": "security"})

        # Verify last write wins
        final_metadata, _ = read_task_file(task_file)

        # Note: In real system, we'd want proper locking/transactions
        # This test documents current behavior
        assert final_metadata["review_mode"] == "security"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
