---
paths: tests/**/*.py, **/test_*.py, **/conftest.py
---

# pytest Testing Patterns

These patterns are extracted from GuardKit's test suite for consistency.

## Test File Documentation

Include coverage targets in module docstrings:

```python
"""
Comprehensive Test Suite for Task ID Validation Functions

Tests validation, duplicate detection, and registry management.

Coverage Target: >=85%
Test Count: 20+ tests
"""
```

## Fixture Patterns

### Temporary Directories

```python
@pytest.fixture
def temp_task_dirs(tmp_path):
    """Create temporary task directories for testing."""
    dirs = {}
    for dir_name in ['backlog', 'in_progress', 'in_review', 'completed', 'blocked']:
        dir_path = tmp_path / 'tasks' / dir_name
        dir_path.mkdir(parents=True)
        dirs[dir_name] = dir_path
    return dirs
```

### Monkeypatch for Module Attributes

```python
@pytest.fixture
def mock_task_dirs(temp_task_dirs, monkeypatch):
    """Patch TASK_DIRECTORIES to use temp directories."""
    temp_dirs = [str(temp_task_dirs[name]) for name in temp_task_dirs]
    monkeypatch.setattr(id_generator, 'TASK_DIRECTORIES', temp_dirs)
    return temp_dirs
```

### Cache Cleanup Fixtures

```python
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
```

### Environment Variable Mocking

```python
def test_get_state_dir_creates_directory(self, tmp_path, monkeypatch):
    """Test that get_state_dir creates the directory if it doesn't exist."""
    mock_home = tmp_path / "test_home"
    mock_home.mkdir()
    monkeypatch.setenv("HOME", str(mock_home))

    state_dir = mock_home / ".agentecflow" / "state"
    assert not state_dir.exists()

    result = get_state_dir()
    assert result.exists()
```

## Dynamic Module Imports

Use importlib for isolated module loading:

```python
import importlib.util
import os

# Import the module using importlib to avoid global state issues
spec = importlib.util.spec_from_file_location(
    "id_generator",
    os.path.join(os.path.dirname(__file__), '../../installer/core/lib/id_generator.py')
)
id_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(id_generator)

# Import specific functions
validate_task_id = id_generator.validate_task_id
is_valid_prefix = id_generator.is_valid_prefix
```

## Test Class Organization

Group related tests in classes with section comments:

```python
# ============================================================================
# 1. Format Validation Tests (8 tests)
# ============================================================================

def test_validate_simple_hash():
    """Test validation of simple hash format (TASK-xxxx)."""
    assert validate_task_id("TASK-a3f2") is True
    assert validate_task_id("TASK-0000") is True

def test_validate_with_prefix():
    """Test validation with prefix (TASK-XXX-xxxx)."""
    assert validate_task_id("TASK-E01-a3f2") is True
    assert validate_task_id("TASK-DOC-abcd") is True

def test_validate_invalid_format():
    """Test rejection of invalid formats."""
    assert validate_task_id("TASK-123") is False  # too short
    assert validate_task_id("TASK-GGGG") is False  # invalid hex
```

## Class-Based Test Organization

```python
class TestStatePaths:
    """Test state path helper functions."""

    def test_get_state_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that get_state_dir creates the directory."""
        ...

    def test_get_state_file_returns_absolute_path(self, tmp_path, monkeypatch):
        """Test that get_state_file returns absolute path."""
        ...
```

## Mock Patterns

### Using unittest.mock.patch

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with patched dependency."""
    with patch('module.external_function') as mock_fn:
        mock_fn.return_value = {'result': 'value'}
        result = function_under_test()
        mock_fn.assert_called_once()
```

### Using monkeypatch.setattr

```python
def test_with_monkeypatch(monkeypatch):
    """Test with monkeypatched module attribute."""
    monkeypatch.setattr(module, 'CONSTANT', 'new_value')
    result = function_using_constant()
    assert result == 'expected'
```

## Performance Tests

```python
import time

def test_validate_1000_ids_under_100ms():
    """Test that 1,000 validations complete in under 100ms."""
    test_ids = [f"TASK-{i:04x}" for i in range(1000)]
    start_time = time.time()
    for task_id in test_ids:
        validate_task_id(task_id)
    elapsed_time = time.time() - start_time
    assert elapsed_time < 0.1, f"Took {elapsed_time*1000:.1f}ms, expected < 100ms"
```

## Assertion Patterns

```python
# Check boolean
assert validate_task_id("TASK-a3f2") is True

# Check equality
assert result.name == ".test-state.json"

# Check paths
assert result.is_absolute()
assert str(result).endswith(".agentecflow/state/.test-state.json")

# Check existence
assert not state_dir.exists()

# Check type
assert isinstance(AGENT_ENHANCE_STATE, str)

# Check starting pattern
assert AGENT_ENHANCE_STATE.startswith(".")
```

## Test Coverage Requirements

- Line coverage: >=85%
- Branch coverage: >=75%
- All public functions must have tests
- Edge cases must be covered (empty, None, invalid)
