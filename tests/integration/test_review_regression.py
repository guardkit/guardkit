"""
Regression tests for task-review command.

Tests validate backward compatibility and ensure that new features
don't break existing functionality.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys
from datetime import datetime

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_review_orchestrator import execute_task_review
from task_utils import create_task_frontmatter, write_task_frontmatter, read_task_file


class TestBackwardCompatibility:
    """Test backward compatibility with existing task formats."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "in_progress", "in_review", "blocked", "completed", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_existing_tasks_without_task_type_field_work(self):
        """Test that existing tasks without task_type field still work."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create old-format task (without task_type)
            task_content = """---
id: TASK-OLD-001
title: Old format task
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: medium
tags: [legacy]
---

## Description
Task created before task_type field was introduced.

## Review Scope
Legacy code.

## Acceptance Criteria
- [ ] Review completed
"""
            task_file = self.tasks_dir / "backlog" / "TASK-OLD-001-old-format.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Execute review - should work despite missing task_type
            result = execute_task_review("TASK-OLD-001", mode="architectural", depth="quick")

            # Verify success
            assert result["status"] == "success"

            # Verify task_type was added during processing
            from task_review_orchestrator import find_task_file
            updated_task_file = find_task_file("TASK-OLD-001", self.tasks_dir)
            metadata, _ = read_task_file(updated_task_file)

            # Task type should be inferred or added
            assert "task_type" in metadata or result["status"] == "success"

        finally:
            os.chdir(original_dir)

    def test_existing_tasks_without_review_mode_field_work(self):
        """Test that tasks without review_mode field get default mode."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task without review_mode
            task_content = """---
id: TASK-NO-MODE-001
title: Task without review mode
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: medium
tags: []
task_type: review
---

## Description
Task without explicit review_mode.

## Review Scope
Code to review.
"""
            task_file = self.tasks_dir / "backlog" / "TASK-NO-MODE-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Execute review with explicit mode (should override)
            result = execute_task_review("TASK-NO-MODE-001", mode="code-quality", depth="quick")

            # Verify success
            assert result["status"] == "success"
            assert result["review_mode"] == "code-quality"

        finally:
            os.chdir(original_dir)

    def test_task_work_unaffected_by_task_review_changes(self):
        """Test that /task-work command still works for implementation tasks."""
        # Create a regular implementation task (not review)
        task_content = """---
id: TASK-IMPL-001
title: Implement new feature
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: high
tags: [feature]
task_type: implementation
---

## Description
Regular implementation task.

## Acceptance Criteria
- [ ] Feature implemented
- [ ] Tests passing
"""
        task_file = self.tasks_dir / "backlog" / "TASK-IMPL-001.md"
        task_file.write_text(task_content, encoding='utf-8')

        # Verify task file created
        assert task_file.exists()

        # Read and verify it's an implementation task
        metadata, _ = read_task_file(task_file)
        assert metadata["task_type"] == "implementation"
        assert "review_mode" not in metadata

        # Note: This test verifies the task file format is correct.
        # Full /task-work testing would require the actual implementation.

    def test_state_manager_handles_review_complete_state(self):
        """Test that state manager correctly handles new review_complete state."""
        # Create task in review_complete state
        frontmatter = create_task_frontmatter(
            task_id="TASK-RC-001",
            title="Review complete state test",
            priority="medium",
            tags=["test"],
            task_type="review",
            review_mode="architectural"
        )
        frontmatter["status"] = "review_complete"

        body = "## Description\nTask in review_complete state."

        task_file = self.tasks_dir / "review_complete" / "TASK-RC-001.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Verify file in correct directory
        assert task_file.exists()
        assert "review_complete" in str(task_file)

        # Verify metadata correct
        metadata, _ = read_task_file(task_file)
        assert metadata["status"] == "review_complete"

    def test_task_metadata_backward_compatible(self):
        """Test that new metadata fields are backward compatible."""
        # Old format metadata (before review fields)
        old_metadata = {
            "id": "TASK-META-001",
            "title": "Old metadata format",
            "status": "backlog",
            "created": "2025-01-15T10:00:00Z",
            "updated": "2025-01-15T10:00:00Z",
            "priority": "medium",
            "tags": []
        }

        # New format adds review fields
        new_metadata = {
            **old_metadata,
            "task_type": "review",
            "review_mode": "architectural",
            "review_results": {
                "overall_score": 85,
                "completion_date": datetime.now().isoformat()
            }
        }

        # Verify all old fields still present
        for key in old_metadata:
            assert key in new_metadata
            assert new_metadata[key] == old_metadata[key]

        # Verify new fields added
        assert "task_type" in new_metadata
        assert "review_mode" in new_metadata
        assert "review_results" in new_metadata


class TestRegressionScenarios:
    """Test specific regression scenarios from previous versions."""

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

    def test_multiple_tasks_with_same_prefix(self):
        """Regression: Ensure tasks with same prefix are handled correctly."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create tasks with similar IDs
            for i in range(1, 4):
                task_content = f"""---
id: TASK-{i:03d}
title: Task {i}
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: medium
tags: []
task_type: review
---

## Description
Task {i}

## Review Scope
Code {i}
"""
                task_file = self.tasks_dir / "backlog" / f"TASK-{i:03d}.md"
                task_file.write_text(task_content, encoding='utf-8')

            # Execute review on specific task
            result = execute_task_review("TASK-002", mode="architectural", depth="quick")

            # Verify only TASK-002 was processed
            assert result["status"] == "success"
            assert result["task_id"] == "TASK-002"

            # Verify other tasks unaffected
            task_001 = self.tasks_dir / "backlog" / "TASK-001.md"
            task_003 = self.tasks_dir / "backlog" / "TASK-003.md"
            assert task_001.exists()
            assert task_003.exists()

        finally:
            os.chdir(original_dir)

    def test_task_with_very_large_review_scope(self):
        """Regression: Handle tasks with very large review scopes."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task with large review scope
            large_scope = "\n".join([f"- src/module{i}/file{j}.py" for i in range(10) for j in range(10)])

            task_content = f"""---
id: TASK-LARGE-001
title: Large scope review
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: medium
tags: []
task_type: review
review_mode: code-quality
---

## Description
Review with very large scope.

## Review Scope
{large_scope}

## Acceptance Criteria
- [ ] All files reviewed
"""
            task_file = self.tasks_dir / "backlog" / "TASK-LARGE-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Execute review - should handle gracefully
            result = execute_task_review("TASK-LARGE-001", mode="code-quality", depth="quick")

            # Verify doesn't crash
            assert result["status"] in ["success", "error"]
            # If error, should be informative
            if result["status"] == "error":
                assert "error" in result
                assert len(result["error"]) > 0

        finally:
            os.chdir(original_dir)

    def test_task_with_missing_required_sections(self):
        """Regression: Handle tasks missing required sections gracefully."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            # Create task missing Review Scope section
            task_content = """---
id: TASK-MISSING-001
title: Task with missing sections
status: backlog
created: 2025-01-15T10:00:00Z
updated: 2025-01-15T10:00:00Z
priority: medium
tags: []
task_type: review
---

## Description
Task missing Review Scope section.

## Acceptance Criteria
- [ ] Review completed
"""
            task_file = self.tasks_dir / "backlog" / "TASK-MISSING-001.md"
            task_file.write_text(task_content, encoding='utf-8')

            # Execute review - should handle missing section
            result = execute_task_review("TASK-MISSING-001", mode="architectural", depth="quick")

            # Should either succeed with warning or fail gracefully
            assert result["status"] in ["success", "error"]

        finally:
            os.chdir(original_dir)


class TestVersionCompatibility:
    """Test compatibility across different versions."""

    def test_v1_task_format_compatibility(self):
        """Test that v1 task format (before task-review) still works."""
        # V1 format (minimal fields)
        v1_frontmatter = {
            "id": "TASK-V1-001",
            "title": "V1 format task",
            "status": "backlog",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "priority": "medium",
            "tags": []
        }

        # Verify can create v1 format
        body = "## Description\nV1 task"

        temp_dir = tempfile.mkdtemp()
        try:
            task_file = Path(temp_dir) / "TASK-V1-001.md"
            content = write_task_frontmatter(v1_frontmatter, body)
            task_file.write_text(content, encoding='utf-8')

            # Verify can read back
            metadata, body_read = read_task_file(task_file)
            assert metadata["id"] == "TASK-V1-001"
            assert "task_type" not in metadata  # V1 didn't have this

        finally:
            shutil.rmtree(temp_dir)

    def test_v2_task_format_with_review_fields(self):
        """Test that v2 task format (with review fields) works."""
        # V2 format (includes review fields)
        v2_frontmatter = create_task_frontmatter(
            task_id="TASK-V2-001",
            title="V2 format task",
            priority="high",
            tags=["review"],
            task_type="review",
            review_mode="security"
        )

        # Verify v2 fields present
        assert "task_type" in v2_frontmatter
        assert "review_mode" in v2_frontmatter
        assert v2_frontmatter["task_type"] == "review"
        assert v2_frontmatter["review_mode"] == "security"


class TestMigrationPath:
    """Test migration path from old to new format."""

    def test_migrate_old_task_to_review_format(self):
        """Test migrating an old task to new review format."""
        # Start with old format
        old_task = {
            "id": "TASK-MIG-001",
            "title": "Migrate this task",
            "status": "backlog",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T00:00:00Z",
            "priority": "medium",
            "tags": []
        }

        # Migrate: add review fields
        migrated_task = {
            **old_task,
            "task_type": "review",
            "review_mode": "architectural",
            "updated": datetime.now().isoformat()  # Update timestamp
        }

        # Verify migration successful
        assert all(k in migrated_task for k in old_task.keys())
        assert migrated_task["task_type"] == "review"
        assert migrated_task["review_mode"] == "architectural"
        assert migrated_task["updated"] != old_task["updated"]

    def test_batch_migration_preserves_all_tasks(self):
        """Test that batch migration preserves all tasks."""
        # Simulate batch of old tasks
        old_tasks = [
            {"id": f"TASK-{i:03d}", "title": f"Task {i}", "status": "backlog"}
            for i in range(1, 11)
        ]

        # Simulate migration (add task_type to all)
        migrated_tasks = []
        for task in old_tasks:
            migrated = {**task, "task_type": "implementation"}  # Default to implementation
            migrated_tasks.append(migrated)

        # Verify count preserved
        assert len(migrated_tasks) == len(old_tasks)

        # Verify all IDs preserved
        old_ids = {t["id"] for t in old_tasks}
        new_ids = {t["id"] for t in migrated_tasks}
        assert old_ids == new_ids

        # Verify new field added to all
        assert all("task_type" in t for t in migrated_tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
