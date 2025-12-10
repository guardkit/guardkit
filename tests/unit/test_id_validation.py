"""
Comprehensive Test Suite for Task ID Validation Functions

Tests validation, duplicate detection, and registry management functionality
added in TASK-047.

Coverage Target: ≥85%
Test Count: 20+ tests
"""

import os
import re
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib.util

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the module using importlib to avoid 'global' keyword issue
spec = importlib.util.spec_from_file_location(
    "id_generator",
    os.path.join(os.path.dirname(__file__), '../../installer/core/lib/id_generator.py')
)
id_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(id_generator)

# Import validation functions
validate_task_id = id_generator.validate_task_id
is_valid_prefix = id_generator.is_valid_prefix
build_id_registry = id_generator.build_id_registry
get_id_registry = id_generator.get_id_registry
check_duplicate = id_generator.check_duplicate
has_duplicate = id_generator.has_duplicate
ERROR_DUPLICATE = id_generator.ERROR_DUPLICATE
ERROR_INVALID_FORMAT = id_generator.ERROR_INVALID_FORMAT
ERROR_INVALID_PREFIX = id_generator.ERROR_INVALID_PREFIX


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_task_dirs(tmp_path):
    """Create temporary task directories for testing."""
    dirs = {}
    for dir_name in ['backlog', 'in_progress', 'in_review', 'completed', 'blocked']:
        dir_path = tmp_path / 'tasks' / dir_name
        dir_path.mkdir(parents=True)
        dirs[dir_name] = dir_path
    return dirs


@pytest.fixture
def mock_task_dirs(temp_task_dirs, monkeypatch):
    """Patch TASK_DIRECTORIES to use temp directories."""
    temp_dirs = [str(temp_task_dirs[name]) for name in temp_task_dirs]
    monkeypatch.setattr(id_generator, 'TASK_DIRECTORIES', temp_dirs)
    return temp_dirs


@pytest.fixture
def clear_registry_cache():
    """Clear registry cache before and after each test."""
    # Clear before test
    id_generator._id_registry_cache = None
    id_generator._cache_timestamp = None
    yield
    # Clear after test
    id_generator._id_registry_cache = None
    id_generator._cache_timestamp = None


# ============================================================================
# 1. Format Validation Tests (8 tests)
# ============================================================================

def test_validate_simple_hash():
    """Test validation of simple hash format (TASK-xxxx)."""
    # Valid 4-char hashes
    assert validate_task_id("TASK-a3f2") is True
    assert validate_task_id("TASK-0000") is True
    assert validate_task_id("TASK-ffff") is True

    # Valid 5-char hashes
    assert validate_task_id("TASK-a3f2d") is True
    assert validate_task_id("TASK-12345") is True

    # Valid 6-char hashes
    assert validate_task_id("TASK-a3f2d7") is True
    assert validate_task_id("TASK-abcdef") is True


def test_validate_with_prefix():
    """Test validation with prefix (TASK-XXX-xxxx)."""
    # Valid 2-char prefix
    assert validate_task_id("TASK-E0-a3f2") is True
    assert validate_task_id("TASK-AB-1234") is True

    # Valid 3-char prefix
    assert validate_task_id("TASK-E01-a3f2") is True
    assert validate_task_id("TASK-DOC-abcd") is True

    # Valid 4-char prefix
    assert validate_task_id("TASK-EPIC-a3f2") is True
    assert validate_task_id("TASK-FIX1-1234") is True


def test_validate_with_subtask():
    """Test validation with subtask notation (TASK-xxxx.N)."""
    # Simple hash with subtask
    assert validate_task_id("TASK-a3f2.1") is True
    assert validate_task_id("TASK-a3f2.99") is True
    assert validate_task_id("TASK-a3f2.123") is True

    # Prefix + hash with subtask
    assert validate_task_id("TASK-E01-a3f2.1") is True
    assert validate_task_id("TASK-DOC-abcd.5") is True
    assert validate_task_id("TASK-EPIC-1234.10") is True


def test_validate_invalid_format():
    """Test rejection of invalid formats."""
    # Hash too short (< 4 chars)
    assert validate_task_id("TASK-123") is False
    assert validate_task_id("TASK-a") is False

    # Hash too long (> 6 chars)
    assert validate_task_id("TASK-1234567") is False
    assert validate_task_id("TASK-abcdefg") is False

    # Invalid characters in hash
    assert validate_task_id("TASK-GGGG") is False  # G not valid hex
    assert validate_task_id("TASK-xyz!") is False  # Special char

    # Missing TASK prefix
    assert validate_task_id("XXX-a3f2") is False
    assert validate_task_id("a3f2") is False

    # Wrong separator
    assert validate_task_id("TASK_a3f2") is False
    assert validate_task_id("TASK.a3f2") is False


def test_validate_case_sensitivity():
    """Test that hash accepts both uppercase and lowercase."""
    # Lowercase hash (valid)
    assert validate_task_id("TASK-abcd") is True
    assert validate_task_id("TASK-E01-abcd") is True

    # Uppercase hash (valid - generator produces uppercase)
    assert validate_task_id("TASK-ABCD") is True
    assert validate_task_id("TASK-E01-ABCD") is True

    # Mixed case hash (valid - both cases allowed)
    assert validate_task_id("TASK-AbCd") is True
    assert validate_task_id("TASK-E01-aBcD") is True


def test_validate_prefix_case():
    """Test that prefix must be uppercase."""
    # Uppercase prefix (valid)
    assert validate_task_id("TASK-E01-a3f2") is True
    assert validate_task_id("TASK-DOC-1234") is True

    # Lowercase prefix (invalid)
    assert validate_task_id("TASK-e01-a3f2") is False
    assert validate_task_id("TASK-doc-1234") is False

    # Mixed case prefix (invalid)
    assert validate_task_id("TASK-E01-a3f2") is True  # Already uppercase
    assert validate_task_id("TASK-Doc-1234") is False


def test_validate_empty_and_none():
    """Test handling of empty strings and None."""
    assert validate_task_id("") is False
    assert validate_task_id("   ") is False
    assert validate_task_id(None) is False


def test_validate_type_errors():
    """Test handling of non-string inputs."""
    assert validate_task_id(123) is False
    assert validate_task_id(['TASK-a3f2']) is False
    assert validate_task_id({'id': 'TASK-a3f2'}) is False


# ============================================================================
# 2. Prefix Validation Tests (6 tests)
# ============================================================================

def test_valid_prefix_2_chars():
    """Test 2-character valid prefixes."""
    assert is_valid_prefix("E0") is True
    assert is_valid_prefix("AB") is True
    assert is_valid_prefix("12") is True
    assert is_valid_prefix("Z9") is True


def test_valid_prefix_3_chars():
    """Test 3-character valid prefixes."""
    assert is_valid_prefix("E01") is True
    assert is_valid_prefix("DOC") is True
    assert is_valid_prefix("FIX") is True
    assert is_valid_prefix("123") is True


def test_valid_prefix_4_chars():
    """Test 4-character valid prefixes."""
    assert is_valid_prefix("EPIC") is True
    assert is_valid_prefix("BUG1") is True
    assert is_valid_prefix("FEAT") is True
    assert is_valid_prefix("1234") is True


def test_invalid_prefix_length():
    """Test rejection of invalid prefix lengths."""
    # Too short (< 2 chars)
    assert is_valid_prefix("E") is False
    assert is_valid_prefix("1") is False

    # Too long (> 4 chars)
    assert is_valid_prefix("EXTRA") is False
    assert is_valid_prefix("TOOLONG") is False
    assert is_valid_prefix("12345") is False


def test_invalid_prefix_chars():
    """Test rejection of invalid characters."""
    # Lowercase (invalid)
    assert is_valid_prefix("e01") is False
    assert is_valid_prefix("doc") is False

    # Special characters (invalid)
    assert is_valid_prefix("E-01") is False
    assert is_valid_prefix("E_01") is False
    assert is_valid_prefix("E.01") is False

    # Spaces (invalid)
    assert is_valid_prefix("E 01") is False


def test_prefix_empty_and_none():
    """Test handling of empty strings and None."""
    assert is_valid_prefix("") is False
    assert is_valid_prefix("   ") is False
    assert is_valid_prefix(None) is False


# ============================================================================
# 3. Registry Building Tests (5 tests)
# ============================================================================

def test_build_registry_empty_dirs(mock_task_dirs, clear_registry_cache):
    """Test registry building with empty directories."""
    registry = build_id_registry()

    assert isinstance(registry, set)
    assert len(registry) == 0


def test_build_registry_with_tasks(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test registry building with existing tasks."""
    # Create test task files
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / "TASK-a3f2.md").touch()
    (backlog_dir / "TASK-b7d1.md").touch()

    in_progress_dir = temp_task_dirs['in_progress']
    (in_progress_dir / "TASK-c9e4.md").touch()

    # Build registry
    registry = build_id_registry()

    # Should contain all task IDs (without .md)
    assert len(registry) == 3
    assert "TASK-a3f2" in registry
    assert "TASK-b7d1" in registry
    assert "TASK-c9e4" in registry


def test_build_registry_all_directories(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test registry scans all 5 task directories."""
    # Create one task in each directory
    for dir_name, dir_path in temp_task_dirs.items():
        (dir_path / f"TASK-{dir_name}.md").touch()

    registry = build_id_registry()

    # Should find all 5 tasks
    assert len(registry) == 5
    assert "TASK-backlog" in registry
    assert "TASK-in_progress" in registry
    assert "TASK-in_review" in registry
    assert "TASK-completed" in registry
    assert "TASK-blocked" in registry


def test_build_registry_ignores_non_task_files(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test registry ignores non-TASK files."""
    backlog_dir = temp_task_dirs['backlog']

    # Create task files
    (backlog_dir / "TASK-a3f2.md").touch()

    # Create non-task files
    (backlog_dir / "README.md").touch()
    (backlog_dir / "notes.txt").touch()
    (backlog_dir / "TASK-a3f2.bak").touch()  # Wrong extension

    registry = build_id_registry()

    # Should only contain actual task
    assert len(registry) == 1
    assert "TASK-a3f2" in registry


def test_build_registry_handles_missing_dirs(monkeypatch, clear_registry_cache):
    """Test graceful handling when directories don't exist."""
    # Patch to non-existent directories
    monkeypatch.setattr(
        id_generator, 'TASK_DIRECTORIES',
        ['/nonexistent/path1', '/nonexistent/path2']
    )

    # Should return empty registry without errors
    registry = build_id_registry()
    assert isinstance(registry, set)
    assert len(registry) == 0


# ============================================================================
# 4. Registry Caching Tests (4 tests)
# ============================================================================

def test_registry_caching(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test that registry is cached and reused."""
    # Create a task
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / "TASK-a3f2.md").touch()

    # First call - builds registry
    registry1 = get_id_registry()
    assert len(registry1) == 1
    assert "TASK-a3f2" in registry1

    # Add another task
    (backlog_dir / "TASK-b7d1.md").touch()

    # Second call within TTL - should use cache (doesn't see new task)
    registry2 = get_id_registry()
    assert len(registry2) == 1  # Still only sees original task

    # Force refresh - should see new task
    registry3 = get_id_registry(force_refresh=True)
    assert len(registry3) == 2
    assert "TASK-a3f2" in registry3
    assert "TASK-b7d1" in registry3


def test_registry_cache_ttl(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test that cache expires after TTL."""
    # Create a task
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / "TASK-a3f2.md").touch()

    # First call - builds registry
    registry1 = get_id_registry()
    assert len(registry1) == 1

    # Add another task
    (backlog_dir / "TASK-b7d1.md").touch()

    # Mock time to simulate TTL expiration
    with patch('time.time') as mock_time:
        # Initial time
        mock_time.return_value = 1000.0
        get_id_registry()  # Refresh cache with mocked time

        # Set cache timestamp
        id_generator._cache_timestamp = 1000.0

        # Time just before expiration (4.9 seconds later)
        mock_time.return_value = 1004.9
        registry_before = get_id_registry()
        assert len(registry_before) == 1  # Still cached

        # Time after expiration (5.1 seconds later)
        mock_time.return_value = 1005.1
        registry_after = get_id_registry()
        assert len(registry_after) == 2  # Cache expired, rebuilt


def test_registry_returns_copy(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test that get_id_registry returns a copy to prevent external modification."""
    # Create a task
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / "TASK-a3f2.md").touch()

    # Get registry
    registry1 = get_id_registry()
    original_len = len(registry1)

    # Modify the returned registry
    registry1.add("TASK-fake")

    # Get registry again - should not include the fake task
    registry2 = get_id_registry()
    assert len(registry2) == original_len
    assert "TASK-fake" not in registry2


def test_registry_thread_safety(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test that registry caching is thread-safe."""
    # Create some tasks
    backlog_dir = temp_task_dirs['backlog']
    for i in range(10):
        (backlog_dir / f"TASK-{i:04d}.md").touch()

    results = []

    def get_registry_worker():
        """Worker function to get registry."""
        registry = get_id_registry()
        results.append(len(registry))

    # Launch 10 threads simultaneously
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=get_registry_worker)
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    # All threads should see the same registry size
    assert len(results) == 10
    assert all(r == 10 for r in results)


# ============================================================================
# 5. Duplicate Detection Tests (5 tests)
# ============================================================================

def test_check_duplicate_not_exists(mock_task_dirs, clear_registry_cache):
    """Test that check_duplicate returns None for non-existent ID."""
    result = check_duplicate("TASK-nonexistent")
    assert result is None


def test_check_duplicate_exists(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test that check_duplicate returns path for existing ID."""
    # Create a task
    backlog_dir = temp_task_dirs['backlog']
    task_file = backlog_dir / "TASK-a3f2.md"
    task_file.touch()

    # Check duplicate
    result = check_duplicate("TASK-a3f2")

    # Should return the path
    assert result is not None
    assert "TASK-a3f2.md" in result
    assert result == str(task_file)


def test_check_duplicate_multiple_dirs(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test duplicate detection across multiple directories."""
    # Create tasks in different directories
    (temp_task_dirs['backlog'] / "TASK-a3f2.md").touch()
    (temp_task_dirs['in_progress'] / "TASK-b7d1.md").touch()
    (temp_task_dirs['completed'] / "TASK-c9e4.md").touch()

    # Should find all tasks
    assert check_duplicate("TASK-a3f2") is not None
    assert check_duplicate("TASK-b7d1") is not None
    assert check_duplicate("TASK-c9e4") is not None


def test_has_duplicate_boolean(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test has_duplicate returns boolean only."""
    # Create a task
    (temp_task_dirs['backlog'] / "TASK-a3f2.md").touch()

    # has_duplicate should return boolean
    assert has_duplicate("TASK-a3f2") is True
    assert has_duplicate("TASK-nonexistent") is False

    # Type check
    assert isinstance(has_duplicate("TASK-a3f2"), bool)
    assert isinstance(has_duplicate("TASK-nonexistent"), bool)


def test_check_duplicate_edge_case_deleted_file(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test edge case where file is in registry but deleted from filesystem."""
    # Create a task and build registry
    backlog_dir = temp_task_dirs['backlog']
    task_file = backlog_dir / "TASK-a3f2.md"
    task_file.touch()

    # Build registry (caches the task)
    registry = get_id_registry()
    assert "TASK-a3f2" in registry

    # Delete the file
    task_file.unlink()

    # check_duplicate should handle gracefully
    result = check_duplicate("TASK-a3f2")
    # Should return None (file not found) even though in registry
    assert result is None


# ============================================================================
# 6. Performance Tests (2 tests)
# ============================================================================

def test_validate_1000_ids_under_100ms():
    """Test that 1,000 validations complete in under 100ms."""
    # Generate 1,000 test IDs
    test_ids = [
        f"TASK-{i:04x}" for i in range(1000)
    ]

    # Time the validations
    start_time = time.time()

    for task_id in test_ids:
        validate_task_id(task_id)

    elapsed_time = time.time() - start_time

    # Should complete in under 100ms
    assert elapsed_time < 0.1, f"Took {elapsed_time*1000:.1f}ms, expected < 100ms"


def test_build_registry_performance(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test registry building performance with 1,000 tasks."""
    # Create 1,000 task files
    backlog_dir = temp_task_dirs['backlog']
    for i in range(1000):
        (backlog_dir / f"TASK-{i:04x}.md").touch()

    # Time registry building
    start_time = time.time()
    registry = build_id_registry()
    elapsed_time = time.time() - start_time

    # Should build registry reasonably fast (< 200ms for 1,000 tasks)
    assert elapsed_time < 0.2, f"Took {elapsed_time*1000:.1f}ms, expected < 200ms"

    # Should have all tasks
    assert len(registry) == 1000


# ============================================================================
# 7. Error Message Constants Tests (3 tests)
# ============================================================================

def test_error_duplicate_message():
    """Test ERROR_DUPLICATE message format."""
    msg = ERROR_DUPLICATE.format(task_id="TASK-a3f2", path="tasks/backlog/TASK-a3f2.md")

    assert "TASK-a3f2" in msg
    assert "tasks/backlog/TASK-a3f2.md" in msg
    assert "ERROR" in msg
    assert "Duplicate" in msg


def test_error_invalid_format_message():
    """Test ERROR_INVALID_FORMAT message format."""
    msg = ERROR_INVALID_FORMAT.format(task_id="TASK-INVALID")

    assert "TASK-INVALID" in msg
    assert "ERROR" in msg
    assert "Invalid" in msg
    assert "format" in msg


def test_error_invalid_prefix_message():
    """Test ERROR_INVALID_PREFIX message format."""
    msg = ERROR_INVALID_PREFIX.format(prefix="x")

    assert "x" in msg
    assert "ERROR" in msg
    assert "prefix" in msg


# ============================================================================
# 8. Integration Tests (3 tests)
# ============================================================================

def test_end_to_end_validation_workflow(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test complete validation workflow."""
    # 1. Validate format
    task_id = "TASK-E01-a3f2"
    assert validate_task_id(task_id) is True

    # 2. Check not duplicate (should be None)
    assert check_duplicate(task_id) is None

    # 3. Create the task file
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / f"{task_id}.md").touch()

    # 4. Force refresh registry
    get_id_registry(force_refresh=True)

    # 5. Now should find duplicate
    duplicate_path = check_duplicate(task_id)
    assert duplicate_path is not None
    assert task_id in duplicate_path


def test_subtask_validation_workflow(mock_task_dirs, temp_task_dirs, clear_registry_cache):
    """Test subtask notation handling."""
    # Validate parent task
    parent_id = "TASK-E01-a3f2"
    assert validate_task_id(parent_id) is True

    # Validate subtasks
    subtask1 = "TASK-E01-a3f2.1"
    subtask2 = "TASK-E01-a3f2.2"
    assert validate_task_id(subtask1) is True
    assert validate_task_id(subtask2) is True

    # Create parent task
    backlog_dir = temp_task_dirs['backlog']
    (backlog_dir / f"{parent_id}.md").touch()

    # Refresh registry
    get_id_registry(force_refresh=True)

    # Parent should be duplicate
    assert has_duplicate(parent_id) is True

    # Subtasks should NOT be duplicates (different IDs with dot notation)
    assert has_duplicate(subtask1) is False
    assert has_duplicate(subtask2) is False


def test_prefix_validation_integration(mock_task_dirs, clear_registry_cache):
    """Test prefix validation integration."""
    # Valid prefixes
    valid_prefixes = ["E0", "E01", "DOC", "EPIC"]
    for prefix in valid_prefixes:
        assert is_valid_prefix(prefix) is True

        # Build task ID with prefix
        task_id = f"TASK-{prefix}-a3f2"
        assert validate_task_id(task_id) is True

    # Invalid prefixes
    invalid_prefixes = ["e01", "X", "TOOLONG", "E-01"]
    for prefix in invalid_prefixes:
        assert is_valid_prefix(prefix) is False


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Coverage Summary:

1. Format Validation Tests (8 tests):
   - test_validate_simple_hash
   - test_validate_with_prefix
   - test_validate_with_subtask
   - test_validate_invalid_format
   - test_validate_case_sensitivity
   - test_validate_prefix_case
   - test_validate_empty_and_none
   - test_validate_type_errors

2. Prefix Validation Tests (6 tests):
   - test_valid_prefix_2_chars
   - test_valid_prefix_3_chars
   - test_valid_prefix_4_chars
   - test_invalid_prefix_length
   - test_invalid_prefix_chars
   - test_prefix_empty_and_none

3. Registry Building Tests (5 tests):
   - test_build_registry_empty_dirs
   - test_build_registry_with_tasks
   - test_build_registry_all_directories
   - test_build_registry_ignores_non_task_files
   - test_build_registry_handles_missing_dirs

4. Registry Caching Tests (4 tests):
   - test_registry_caching
   - test_registry_cache_ttl
   - test_registry_returns_copy
   - test_registry_thread_safety

5. Duplicate Detection Tests (5 tests):
   - test_check_duplicate_not_exists
   - test_check_duplicate_exists
   - test_check_duplicate_multiple_dirs
   - test_has_duplicate_boolean
   - test_check_duplicate_edge_case_deleted_file

6. Performance Tests (2 tests):
   - test_validate_1000_ids_under_100ms
   - test_build_registry_performance

7. Error Message Constants Tests (3 tests):
   - test_error_duplicate_message
   - test_error_invalid_format_message
   - test_error_invalid_prefix_message

8. Integration Tests (3 tests):
   - test_end_to_end_validation_workflow
   - test_subtask_validation_workflow
   - test_prefix_validation_integration

Total: 36 tests
Target Coverage: ≥85%
"""
