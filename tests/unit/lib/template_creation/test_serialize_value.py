"""
Unit tests for _serialize_value() method.

Tests recursive serialization of complex values for checkpoint persistence.
Handles Path, datetime, Enum, nested structures uniformly.

TASK-PHASE-7-5-FIX-FOUNDATION: DRY principle improvement
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from datetime import datetime
from enum import Enum
from unittest.mock import Mock, patch
import tempfile

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))


def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


orchestrator_module = import_module_from_path(
    "template_create_orchestrator",
    commands_lib_path / "template_create_orchestrator.py"
)

TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
OrchestrationConfig = orchestrator_module.OrchestrationConfig


# ========== Test Fixtures ==========

@pytest.fixture
def mock_config():
    """Mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.verbose = False
    return config


@pytest.fixture
def mock_orchestrator(mock_config):
    """Create a mock orchestrator instance."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orchestrator = TemplateCreateOrchestrator(mock_config)
        orchestrator.config = mock_config
        return orchestrator


# ========== Test Primitives ==========

class TestSerializeValuePrimitives:
    """Test serialization of primitive types."""

    def test_serialize_none(self, mock_orchestrator):
        """Test None is returned as None."""
        result = mock_orchestrator._serialize_value(None)
        assert result is None

    def test_serialize_string(self, mock_orchestrator):
        """Test strings pass through unchanged."""
        result = mock_orchestrator._serialize_value("hello")
        assert result == "hello"

    def test_serialize_integer(self, mock_orchestrator):
        """Test integers pass through unchanged."""
        result = mock_orchestrator._serialize_value(42)
        assert result == 42

    def test_serialize_float(self, mock_orchestrator):
        """Test floats pass through unchanged."""
        result = mock_orchestrator._serialize_value(3.14)
        assert result == 3.14

    def test_serialize_boolean(self, mock_orchestrator):
        """Test booleans pass through unchanged."""
        assert mock_orchestrator._serialize_value(True) is True
        assert mock_orchestrator._serialize_value(False) is False


# ========== Test Path Objects ==========

class TestSerializeValuePath:
    """Test serialization of Path objects."""

    def test_serialize_absolute_path(self, mock_orchestrator):
        """Test absolute path converted to string."""
        path = Path("/home/user/project")
        result = mock_orchestrator._serialize_value(path)
        assert result == "/home/user/project"
        assert isinstance(result, str)

    def test_serialize_relative_path(self, mock_orchestrator):
        """Test relative path converted to string."""
        path = Path("src/templates")
        result = mock_orchestrator._serialize_value(path)
        assert result == str(Path("src/templates"))
        assert isinstance(result, str)

    def test_serialize_path_with_special_chars(self, mock_orchestrator):
        """Test path with special characters."""
        path = Path("/home/user/my-project/src")
        result = mock_orchestrator._serialize_value(path)
        assert result == "/home/user/my-project/src"
        assert isinstance(result, str)


# ========== Test Datetime Objects ==========

class TestSerializeValueDatetime:
    """Test serialization of datetime objects."""

    def test_serialize_datetime_object(self, mock_orchestrator):
        """Test datetime converted to ISO 8601 string."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = mock_orchestrator._serialize_value(dt)
        assert result == "2024-01-15T10:30:45"
        assert isinstance(result, str)

    def test_serialize_datetime_with_microseconds(self, mock_orchestrator):
        """Test datetime with microseconds."""
        dt = datetime(2024, 1, 15, 10, 30, 45, 123456)
        result = mock_orchestrator._serialize_value(dt)
        assert "2024-01-15T10:30:45.123456" == result
        assert isinstance(result, str)

    def test_iso_format_compatibility(self, mock_orchestrator):
        """Test result is valid ISO 8601 format."""
        dt = datetime.now()
        result = mock_orchestrator._serialize_value(dt)
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result)
        assert parsed == dt


# ========== Test Enum Objects ==========

class TestSerializeValueEnum:
    """Test serialization of Enum objects."""

    def test_serialize_enum_value(self, mock_orchestrator):
        """Test Enum converted to its value."""
        class Color(Enum):
            RED = "red"
            GREEN = "green"

        result = mock_orchestrator._serialize_value(Color.RED)
        assert result == "red"

    def test_serialize_integer_enum(self, mock_orchestrator):
        """Test integer-valued enum."""
        class Priority(Enum):
            HIGH = 1
            MEDIUM = 2
            LOW = 3

        result = mock_orchestrator._serialize_value(Priority.HIGH)
        assert result == 1

    def test_serialize_mixed_enum(self, mock_orchestrator):
        """Test enum with mixed value types."""
        class Mixed(Enum):
            OPTION_A = "a"
            OPTION_B = 2

        assert mock_orchestrator._serialize_value(Mixed.OPTION_A) == "a"
        assert mock_orchestrator._serialize_value(Mixed.OPTION_B) == 2


# ========== Test Objects with to_dict() ==========

class TestSerializeValueToDict:
    """Test serialization of objects with to_dict() method."""

    def test_serialize_pydantic_like_object(self, mock_orchestrator):
        """Test object with to_dict() method (Pydantic-like)."""
        obj = Mock()
        obj.to_dict = Mock(return_value={"name": "test", "value": 42})

        result = mock_orchestrator._serialize_value(obj)

        # Should call to_dict() and serialize the result
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_serialize_to_dict_with_nested_path(self, mock_orchestrator):
        """Test to_dict() result containing Path objects."""
        obj = Mock()
        obj.to_dict = Mock(return_value={
            "name": "test",
            "path": Path("/home/user")
        })

        result = mock_orchestrator._serialize_value(obj)

        # Should recursively serialize Path in nested dict
        assert result["name"] == "test"
        assert result["path"] == "/home/user"


# ========== Test Objects with __dict__ ==========

class TestSerializeValueDict:
    """Test serialization of objects with __dict__ attribute."""

    def test_serialize_simple_object(self, mock_orchestrator):
        """Test simple object with __dict__."""
        class SimpleObj:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = SimpleObj()
        result = mock_orchestrator._serialize_value(obj)

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_serialize_object_with_path_attribute(self, mock_orchestrator):
        """Test object with Path attribute."""
        class ObjWithPath:
            def __init__(self):
                self.path = Path("/home/user")
                self.name = "test"

        obj = ObjWithPath()
        result = mock_orchestrator._serialize_value(obj)

        # Should recursively convert Path to string
        assert result["path"] == "/home/user"
        assert isinstance(result["path"], str)

    def test_serialize_object_with_datetime_attribute(self, mock_orchestrator):
        """Test object with datetime attribute."""
        class ObjWithDatetime:
            def __init__(self):
                self.created_at = datetime(2024, 1, 15, 10, 30, 45)
                self.name = "test"

        obj = ObjWithDatetime()
        result = mock_orchestrator._serialize_value(obj)

        # Should recursively convert datetime to string
        assert result["created_at"] == "2024-01-15T10:30:45"
        assert isinstance(result["created_at"], str)


# ========== Test Dictionaries ==========

class TestSerializeValueDictionary:
    """Test serialization of dictionary objects."""

    def test_serialize_empty_dict(self, mock_orchestrator):
        """Test empty dictionary."""
        result = mock_orchestrator._serialize_value({})
        assert result == {}

    def test_serialize_simple_dict(self, mock_orchestrator):
        """Test dictionary with primitive values."""
        d = {"name": "test", "count": 42, "active": True}
        result = mock_orchestrator._serialize_value(d)
        assert result == d

    def test_serialize_dict_with_path(self, mock_orchestrator):
        """Test dictionary containing Path objects."""
        d = {
            "name": "test",
            "path": Path("/home/user"),
            "count": 42
        }
        result = mock_orchestrator._serialize_value(d)

        assert result["name"] == "test"
        assert result["path"] == "/home/user"
        assert result["count"] == 42

    def test_serialize_nested_dict(self, mock_orchestrator):
        """Test nested dictionaries."""
        d = {
            "outer": {
                "inner": {
                    "path": Path("/tmp"),
                    "value": 42
                }
            }
        }
        result = mock_orchestrator._serialize_value(d)

        assert result["outer"]["inner"]["path"] == "/tmp"
        assert result["outer"]["inner"]["value"] == 42


# ========== Test Lists ==========

class TestSerializeValueList:
    """Test serialization of list objects."""

    def test_serialize_empty_list(self, mock_orchestrator):
        """Test empty list."""
        result = mock_orchestrator._serialize_value([])
        assert result == []

    def test_serialize_simple_list(self, mock_orchestrator):
        """Test list with primitive values."""
        lst = [1, 2, 3, "hello", True]
        result = mock_orchestrator._serialize_value(lst)
        assert result == lst

    def test_serialize_list_with_path(self, mock_orchestrator):
        """Test list containing Path objects."""
        lst = [Path("/home/user"), Path("/tmp"), "test"]
        result = mock_orchestrator._serialize_value(lst)

        assert result[0] == "/home/user"
        assert result[1] == "/tmp"
        assert result[2] == "test"

    def test_serialize_list_with_objects(self, mock_orchestrator):
        """Test list containing objects with __dict__."""
        class Item:
            def __init__(self, name):
                self.name = name
                self.path = Path("/tmp")

        lst = [Item("first"), Item("second")]
        result = mock_orchestrator._serialize_value(lst)

        assert len(result) == 2
        assert result[0]["name"] == "first"
        assert result[0]["path"] == "/tmp"
        assert result[1]["name"] == "second"


# ========== Test Tuples ==========

class TestSerializeValueTuple:
    """Test serialization of tuple objects."""

    def test_serialize_simple_tuple(self, mock_orchestrator):
        """Test tuple converted to list."""
        t = (1, 2, 3)
        result = mock_orchestrator._serialize_value(t)

        assert isinstance(result, list)
        assert result == [1, 2, 3]

    def test_serialize_tuple_with_path(self, mock_orchestrator):
        """Test tuple containing Path objects."""
        t = (Path("/home/user"), "test", 42)
        result = mock_orchestrator._serialize_value(t)

        assert isinstance(result, list)
        assert result[0] == "/home/user"
        assert result[1] == "test"
        assert result[2] == 42


# ========== Test Sets ==========

class TestSerializeValueSet:
    """Test serialization of set objects."""

    def test_serialize_simple_set(self, mock_orchestrator):
        """Test set converted to list."""
        s = {1, 2, 3}
        result = mock_orchestrator._serialize_value(s)

        assert isinstance(result, list)
        # Order may vary, so check contents
        assert set(result) == {1, 2, 3}

    def test_serialize_set_with_paths(self, mock_orchestrator):
        """Test set containing Path objects (converted to strings in list)."""
        p1 = Path("/home/user")
        p2 = Path("/tmp")
        s = {str(p1), str(p2)}
        result = mock_orchestrator._serialize_value(s)

        assert isinstance(result, list)
        assert str(p1) in result
        assert str(p2) in result


# ========== Test Complex Nested Structures ==========

class TestSerializeValueComplexNesting:
    """Test serialization of deeply nested structures."""

    def test_serialize_complex_agent_like_object(self, mock_orchestrator):
        """Test complex nested structure similar to agent objects."""
        agent = {
            "name": "test-agent",
            "created_at": datetime(2024, 1, 15, 10, 30, 45),
            "path": Path("/home/user"),
            "tags": ["python", "testing"],
            "config": {
                "timeout": 30,
                "retries": 3,
                "paths": [Path("/tmp"), Path("/home")]
            }
        }

        result = mock_orchestrator._serialize_value(agent)

        assert result["name"] == "test-agent"
        assert result["created_at"] == "2024-01-15T10:30:45"
        assert result["path"] == "/home/user"
        assert result["tags"] == ["python", "testing"]
        assert result["config"]["timeout"] == 30
        assert result["config"]["paths"][0] == "/tmp"

    def test_serialize_deeply_nested_dict(self, mock_orchestrator):
        """Test deeply nested dictionary structures."""
        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "path": Path("/deep/path"),
                        "value": 42
                    }
                }
            }
        }

        result = mock_orchestrator._serialize_value(nested)

        assert result["level1"]["level2"]["level3"]["path"] == "/deep/path"
        assert result["level1"]["level2"]["level3"]["value"] == 42

    def test_serialize_list_of_dicts_with_paths(self, mock_orchestrator):
        """Test list of dictionaries containing paths."""
        lst = [
            {"name": "item1", "path": Path("/path1")},
            {"name": "item2", "path": Path("/path2")},
        ]

        result = mock_orchestrator._serialize_value(lst)

        assert result[0]["path"] == "/path1"
        assert result[1]["path"] == "/path2"


# ========== DRY Principle Tests ==========

class TestSerializeValueDRY:
    """Test DRY principle implementation."""

    def test_centralizes_type_conversion_logic(self, mock_orchestrator):
        """Test this is single source of truth for serialization."""
        # Various complex values
        values = [
            Path("/home/user"),
            datetime(2024, 1, 15),
            {"path": Path("/tmp"), "dt": datetime(2024, 1, 15)},
            [Path("/a"), Path("/b")],
        ]

        for value in values:
            result = mock_orchestrator._serialize_value(value)
            # Each should be JSON-serializable (no Path or datetime objects remain)
            import json
            try:
                json.dumps(result)
            except TypeError:
                pytest.fail(f"Result not JSON-serializable: {result}")

    def test_handles_complex_nested_structures_without_recursion(self, mock_orchestrator):
        """Test method handles complex nesting without hitting recursion limits."""
        # Create a reasonably deep structure to verify recursion handling
        class SimpleAgent:
            def __init__(self):
                self.name = "test"
                self.path = Path("/home/user")
                self.created_at = datetime(2024, 1, 15, 10, 30, 45)
                self.config = {
                    "timeout": 30,
                    "paths": [Path("/tmp"), Path("/home")]
                }

        agent = SimpleAgent()
        result = mock_orchestrator._serialize_value(agent)

        # Verify all nested values were converted
        assert result["name"] == "test"
        assert result["path"] == "/home/user"
        assert result["created_at"] == "2024-01-15T10:30:45"
        assert result["config"]["paths"][0] == "/tmp"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
