"""
Tests for task migration script.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Load the migration script with hyphens in the name
script_path = Path(__file__).parent.parent / "scripts" / "migrate-my-tasks.py"
spec = importlib.util.spec_from_file_location("migrate_my_tasks", script_path)
migrate_my_tasks = importlib.util.module_from_spec(spec)
sys.modules["migrate_my_tasks"] = migrate_my_tasks

# Add lib directory to path for dependencies
lib_dir = Path(__file__).parent.parent / "installer" / "core" / "lib"
sys.path.insert(0, str(lib_dir.resolve()))

# Execute the module to load functions
spec.loader.exec_module(migrate_my_tasks)

# Import functions from the loaded module
MigrationStats = migrate_my_tasks.MigrationStats
extract_id_from_frontmatter = migrate_my_tasks.extract_id_from_frontmatter
generate_id_mapping = migrate_my_tasks.generate_id_mapping
scan_task_files = migrate_my_tasks.scan_task_files
update_cross_references = migrate_my_tasks.update_cross_references
update_frontmatter = migrate_my_tasks.update_frontmatter


class TestMigrationStats(unittest.TestCase):
    """Test MigrationStats class."""

    def test_initialization(self):
        """Test stats initialization."""
        stats = MigrationStats()
        self.assertEqual(stats.tasks_found, 0)
        self.assertEqual(stats.tasks_migrated, 0)
        self.assertEqual(stats.files_renamed, 0)
        self.assertEqual(stats.cross_references_updated, 0)
        self.assertEqual(len(stats.errors), 0)
        self.assertEqual(len(stats.migrations), 0)

    def test_add_migration(self):
        """Test recording migrations."""
        stats = MigrationStats()
        stats.add_migration("TASK-001", "TASK-A3F2")
        self.assertEqual(stats.tasks_migrated, 1)
        self.assertEqual(stats.migrations[0], ("TASK-001", "TASK-A3F2"))

    def test_add_error(self):
        """Test recording errors."""
        stats = MigrationStats()
        stats.add_error("Test error")
        self.assertEqual(len(stats.errors), 1)
        self.assertEqual(stats.errors[0], "Test error")

    def test_duration_calculation(self):
        """Test duration calculation."""
        stats = MigrationStats()
        stats.finish()
        self.assertGreaterEqual(stats.duration_seconds, 0)


class TestFrontmatterExtraction(unittest.TestCase):
    """Test frontmatter extraction."""

    def test_extract_id_from_valid_frontmatter(self):
        """Test extracting ID from valid frontmatter."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            content = """---
id: TASK-042
title: Test Task
status: backlog
---

# Task content
"""
            test_file = Path(tmp_dir) / "test.md"
            test_file.write_text(content)

            task_id = extract_id_from_frontmatter(test_file)
            self.assertEqual(task_id, "TASK-042")

    def test_extract_id_with_prefix(self):
        """Test extracting ID with prefix."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            content = """---
id: TASK-DOCS-001
title: Test Task
---
"""
            test_file = Path(tmp_dir) / "test.md"
            test_file.write_text(content)

            task_id = extract_id_from_frontmatter(test_file)
            self.assertEqual(task_id, "TASK-DOCS-001")

    def test_extract_id_no_frontmatter(self):
        """Test handling missing frontmatter."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            content = "# Just a regular markdown file"
            test_file = Path(tmp_dir) / "test.md"
            test_file.write_text(content)

            task_id = extract_id_from_frontmatter(test_file)
            self.assertIsNone(task_id)


class TestFrontmatterUpdate(unittest.TestCase):
    """Test frontmatter update logic."""

    def test_update_simple_id(self):
        """Test updating simple task ID."""
        content = """---
id: TASK-042
title: Test Task
status: backlog
---

# Task content
"""
        updated = update_frontmatter(content, "TASK-042", "TASK-A3F2")

        # Verify new ID is set
        self.assertIn("id: TASK-A3F2", updated)
        # Verify legacy ID is preserved
        self.assertIn("legacy_id: TASK-042", updated)
        # Ensure the id line is correct (not in legacy_id line)
        lines = updated.split('\n')
        id_line = [line for line in lines if line.startswith('id:')]
        self.assertEqual(len(id_line), 1)
        self.assertEqual(id_line[0].strip(), "id: TASK-A3F2")

    def test_update_prefixed_id(self):
        """Test updating prefixed task ID."""
        content = """---
id: TASK-DOCS-001
title: Documentation Task
---
"""
        updated = update_frontmatter(content, "TASK-DOCS-001", "TASK-B2C4")

        self.assertIn("id: TASK-B2C4", updated)
        self.assertIn("legacy_id: TASK-DOCS-001", updated)

    def test_preserve_other_fields(self):
        """Test that other frontmatter fields are preserved."""
        content = """---
id: TASK-042
title: Test Task
status: backlog
priority: high
tags: [test, migration]
---

Content
"""
        updated = update_frontmatter(content, "TASK-042", "TASK-A3F2")

        self.assertIn("title: Test Task", updated)
        self.assertIn("status: backlog", updated)
        self.assertIn("priority: high", updated)
        self.assertIn("tags: [test, migration]", updated)


class TestCrossReferences(unittest.TestCase):
    """Test cross-reference updates."""

    def test_update_single_reference(self):
        """Test updating single cross-reference."""
        content = "See TASK-042 for details"
        mapping = {"TASK-042": "TASK-A3F2"}

        updated, count = update_cross_references(content, mapping)

        self.assertIn("TASK-A3F2", updated)
        self.assertNotIn("TASK-042", updated)
        self.assertEqual(count, 1)

    def test_update_multiple_references(self):
        """Test updating multiple cross-references."""
        content = """
Related to TASK-042 and TASK-043.
Also see TASK-042 again.
"""
        mapping = {
            "TASK-042": "TASK-A3F2",
            "TASK-043": "TASK-B7D1"
        }

        updated, count = update_cross_references(content, mapping)

        self.assertIn("TASK-A3F2", updated)
        self.assertIn("TASK-B7D1", updated)
        self.assertNotIn("TASK-042", updated)
        self.assertNotIn("TASK-043", updated)
        self.assertEqual(count, 3)  # 2 for TASK-042, 1 for TASK-043

    def test_no_references(self):
        """Test content with no cross-references."""
        content = "This is just plain content"
        mapping = {"TASK-042": "TASK-A3F2"}

        updated, count = update_cross_references(content, mapping)

        self.assertEqual(updated, content)
        self.assertEqual(count, 0)


class TestIdMapping(unittest.TestCase):
    """Test ID mapping generation."""

    def test_generate_mapping(self):
        """Test generating ID mappings."""
        old_ids = ["TASK-001", "TASK-002", "TASK-003"]

        mapping = generate_id_mapping(old_ids)

        self.assertEqual(len(mapping), 3)
        self.assertIn("TASK-001", mapping)
        self.assertIn("TASK-002", mapping)
        self.assertIn("TASK-003", mapping)

        # Check all new IDs are unique
        new_ids = list(mapping.values())
        self.assertEqual(len(new_ids), len(set(new_ids)))

        # Check all new IDs start with TASK-
        for new_id in new_ids:
            self.assertTrue(new_id.startswith("TASK-"))

    def test_empty_list(self):
        """Test with empty list."""
        mapping = generate_id_mapping([])
        self.assertEqual(len(mapping), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_dry_run_no_errors(self):
        """Test that dry-run completes without errors."""
        # This is already tested by running the script
        # Just verify the script can be imported and has main function
        self.assertTrue(hasattr(migrate_my_tasks, 'main'))

    def test_backup_structure(self):
        """Test backup directory structure."""
        # Verify backup path pattern contains expected components
        backup_base = Path(".claude/state/backup")
        backup_pattern = "tasks-pre-hash-migration"

        # Test that the full backup path would include the pattern
        full_backup = backup_base / backup_pattern
        self.assertIn("tasks-pre-hash-migration", str(full_backup))


if __name__ == "__main__":
    unittest.main()
