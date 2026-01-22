"""Integration test for task type detection in feature-plan workflow.

Tests that the implement_orchestrator correctly detects and assigns task types
when generating subtask files from feature plan recommendations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from installer.core.lib.implement_orchestrator import ImplementOrchestrator
from guardkit.models.task_types import TaskType


class TestFeaturePlanTaskTypeDetection:
    """Test task type detection in feature-plan workflow."""

    def setup_method(self):
        """Setup test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Note: We don't actually change directory, we just track it

    def teardown_method(self):
        """Cleanup temporary directory."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_task_type_detection_in_subtask_generation(self):
        """Test that task types are correctly detected and added to subtasks."""
        # Create mock review task
        review_task = {
            "id": "TASK-REV-001",
            "title": "Review authentication system",
            "created": "2026-01-22T00:00:00Z",
        }

        # Create mock subtasks with different types
        orchestrator = ImplementOrchestrator(review_task, "dummy-report.md")
        orchestrator.feature_slug = "auth-system"
        orchestrator.subtasks = [
            {
                "id": "TASK-AUTH-001",
                "title": "Add Docker configuration",
                "description": "Create Dockerfile for authentication service",
                "complexity": 3,
                "implementation_mode": "direct",
                "files": ["Dockerfile", "docker-compose.yml"],
                "dependencies": [],
            },
            {
                "id": "TASK-AUTH-002",
                "title": "Update README",
                "description": "Document authentication API endpoints",
                "complexity": 2,
                "implementation_mode": "direct",
                "files": ["README.md"],
                "dependencies": [],
            },
            {
                "id": "TASK-AUTH-003",
                "title": "Configure ESLint",
                "description": "Setup code quality rules",
                "complexity": 2,
                "implementation_mode": "direct",
                "files": [".eslintrc.js"],
                "dependencies": [],
            },
            {
                "id": "TASK-AUTH-004",
                "title": "Implement JWT authentication",
                "description": "Add JWT token generation and validation",
                "complexity": 7,
                "implementation_mode": "task-work",
                "files": ["src/auth/jwt.py", "src/auth/middleware.py"],
                "dependencies": [],
            },
        ]

        # Create subfolder in temp directory
        orchestrator.subfolder_path = Path(self.temp_dir) / "auth-system"
        orchestrator.subfolder_path.mkdir(parents=True, exist_ok=True)

        # Generate subtask files
        orchestrator.generate_subtask_files()

        # Verify files were created
        subtask_files = list(orchestrator.subfolder_path.glob("TASK-AUTH-*.md"))
        assert len(subtask_files) == 4, f"Expected 4 files, found {len(subtask_files)}"

        # Verify task types in frontmatter
        expected_task_types = {
            "TASK-AUTH-001": TaskType.INFRASTRUCTURE.value,  # Docker
            "TASK-AUTH-002": TaskType.DOCUMENTATION.value,  # README
            "TASK-AUTH-003": TaskType.SCAFFOLDING.value,    # ESLint
            "TASK-AUTH-004": TaskType.FEATURE.value,        # Implementation
        }

        for task_file in subtask_files:
            content = task_file.read_text()

            # Extract task ID from content
            for line in content.split('\n'):
                if line.startswith('id:'):
                    task_id = line.split(':', 1)[1].strip()
                    break

            # Verify task_type field exists and has correct value
            assert 'task_type:' in content, f"task_type field missing in {task_file.name}"

            # Extract task_type value
            for line in content.split('\n'):
                if line.startswith('task_type:'):
                    task_type_value = line.split(':', 1)[1].strip()
                    expected_type = expected_task_types[task_id]
                    assert task_type_value == expected_type, (
                        f"Task {task_id}: expected {expected_type}, got {task_type_value}"
                    )
                    break

    def test_task_type_with_empty_description(self):
        """Test task type detection when description is empty."""
        review_task = {
            "id": "TASK-REV-002",
            "title": "Review deployment",
            "created": "2026-01-22T00:00:00Z",
        }

        orchestrator = ImplementOrchestrator(review_task, "dummy-report.md")
        orchestrator.feature_slug = "deployment"
        orchestrator.subtasks = [
            {
                "id": "TASK-DEP-001",
                "title": "Setup Kubernetes cluster",
                "description": "",  # Empty description
                "complexity": 8,
                "implementation_mode": "task-work",
                "files": [],
                "dependencies": [],
            },
        ]

        orchestrator.subfolder_path = Path(self.temp_dir) / "deployment"
        orchestrator.subfolder_path.mkdir(parents=True, exist_ok=True)

        orchestrator.generate_subtask_files()

        # Verify file created
        subtask_file = next(orchestrator.subfolder_path.glob("TASK-DEP-001-*.md"))
        content = subtask_file.read_text()

        # Should still detect INFRASTRUCTURE from "Kubernetes" in title
        assert 'task_type: infrastructure' in content

    def test_task_type_ambiguous_title_with_description(self):
        """Test that description helps disambiguate ambiguous titles."""
        review_task = {
            "id": "TASK-REV-003",
            "title": "Review configuration",
            "created": "2026-01-22T00:00:00Z",
        }

        orchestrator = ImplementOrchestrator(review_task, "dummy-report.md")
        orchestrator.feature_slug = "config"
        orchestrator.subtasks = [
            {
                "id": "TASK-CFG-001",
                "title": "Update configuration",
                "description": "Configure Docker container settings",
                "complexity": 3,
                "implementation_mode": "direct",
                "files": [],
                "dependencies": [],
            },
            {
                "id": "TASK-CFG-002",
                "title": "Update configuration",
                "description": "Update webpack build configuration",
                "complexity": 3,
                "implementation_mode": "direct",
                "files": [],
                "dependencies": [],
            },
        ]

        orchestrator.subfolder_path = Path(self.temp_dir) / "config"
        orchestrator.subfolder_path.mkdir(parents=True, exist_ok=True)

        orchestrator.generate_subtask_files()

        # Verify both files created
        subtask_files = list(orchestrator.subfolder_path.glob("TASK-CFG-*.md"))
        assert len(subtask_files) == 2

        # First should be INFRASTRUCTURE (Docker in description)
        cfg_001 = next(f for f in subtask_files if "TASK-CFG-001" in f.name)
        assert 'task_type: infrastructure' in cfg_001.read_text()

        # Second should be SCAFFOLDING (webpack in description)
        cfg_002 = next(f for f in subtask_files if "TASK-CFG-002" in f.name)
        assert 'task_type: scaffolding' in cfg_002.read_text()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
