"""Comprehensive test suite for DomainValidator.

Covers type coercion (TRF-004), array validation (FRF-002), range notation
(TRF-028), required config fields (TRF-022), and regression values from
runs 1, 3, 9.

Coverage Target: >=90%
Test Count: 50+ tests
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load module directly — directory name contains hyphens, not importable.
# Register in sys.modules first so dataclass decorator can resolve __module__.
# ---------------------------------------------------------------------------
_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "domain_validator.py"
)

_spec = importlib.util.spec_from_file_location("domain_validator", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["domain_validator"] = _mod
_spec.loader.exec_module(_mod)

MetadataField = _mod.MetadataField
FieldType = _mod.FieldType
ValidationResult = _mod.ValidationResult
ValidationError = _mod.ValidationError
DomainValidator = _mod.DomainValidator
Range = _mod.Range
coerce_value = _mod.coerce_value
parse_range = _mod.parse_range
is_range_notation = _mod.is_range_notation
validate_field = _mod.validate_field
validate_config = _mod.validate_config


# ===========================================================================
# 1. Range notation parsing (TRF-028)
# ===========================================================================


class TestParseRange:
    """Range notation regex: r'^(\\d+)\\+$', r'^(\\d+)-(\\d+)$'"""

    def test_plus_notation(self):
        r = parse_range("1+")
        assert r is not None
        assert r.min_value == 1
        assert r.max_value is None

    def test_zero_plus(self):
        r = parse_range("0+")
        assert r is not None
        assert r.min_value == 0
        assert r.max_value is None

    def test_minmax_notation(self):
        r = parse_range("1-10")
        assert r is not None
        assert r.min_value == 1
        assert r.max_value == 10

    def test_zero_to_hundred(self):
        r = parse_range("0-100")
        assert r is not None
        assert r.min_value == 0
        assert r.max_value == 100

    def test_inverted_range_returns_none(self):
        assert parse_range("10-1") is None

    def test_non_range_string(self):
        assert parse_range("hello") is None

    def test_empty_string(self):
        assert parse_range("") is None

    def test_whitespace_stripped(self):
        r = parse_range("  5+  ")
        assert r is not None
        assert r.min_value == 5

    def test_single_number_not_range(self):
        assert parse_range("5") is None


class TestRangeContains:

    def test_plus_range_contains(self):
        r = Range(min_value=1)
        assert r.contains(1) is True
        assert r.contains(100) is True
        assert r.contains(0) is False

    def test_minmax_range_contains(self):
        r = Range(min_value=1, max_value=5)
        assert r.contains(1) is True
        assert r.contains(3) is True
        assert r.contains(5) is True
        assert r.contains(0) is False
        assert r.contains(6) is False

    def test_float_in_range(self):
        r = Range(min_value=0, max_value=2)
        assert r.contains(0.7) is True
        assert r.contains(1.5) is True


class TestIsRangeNotation:

    def test_string_range(self):
        assert is_range_notation("1+") is True
        assert is_range_notation("1-10") is True

    def test_list_not_range(self):
        assert is_range_notation(["a", "b"]) is False

    def test_non_range_string(self):
        assert is_range_notation("hello") is False


# ===========================================================================
# 2. Type coercion at model-output boundary (TRF-004)
# ===========================================================================


class TestCoerceValue:
    """TRF-004: Model sends int, schema has strings."""

    def test_int_to_string(self):
        assert coerce_value(3, FieldType.STRING) == "3"

    def test_string_to_int(self):
        assert coerce_value("42", FieldType.INTEGER) == 42

    def test_string_to_float(self):
        assert coerce_value("3.14", FieldType.FLOAT) == pytest.approx(3.14)

    def test_int_to_float(self):
        assert coerce_value(3, FieldType.FLOAT) == 3.0

    def test_string_to_boolean_true(self):
        for val in ("true", "True", "1", "yes"):
            assert coerce_value(val, FieldType.BOOLEAN) is True

    def test_string_to_boolean_false(self):
        for val in ("false", "False", "0", "no"):
            assert coerce_value(val, FieldType.BOOLEAN) is False

    def test_invalid_boolean_raises(self):
        with pytest.raises(ValueError, match="Cannot coerce"):
            coerce_value("maybe", FieldType.BOOLEAN)

    def test_string_to_array(self):
        result = coerce_value("a, b, c", FieldType.ARRAY)
        assert result == ["a", "b", "c"]

    def test_list_to_array(self):
        result = coerce_value(["x", "y"], FieldType.ARRAY)
        assert result == ["x", "y"]

    def test_scalar_to_array(self):
        result = coerce_value(42, FieldType.ARRAY)
        assert result == [42]

    def test_none_passthrough(self):
        assert coerce_value(None, FieldType.STRING) is None

    def test_float_to_string(self):
        assert coerce_value(3.14, FieldType.STRING) == "3.14"

    def test_bool_to_string(self):
        assert coerce_value(True, FieldType.STRING) == "True"


# ===========================================================================
# 3. Array vs scalar field validation (FRF-002)
# ===========================================================================


class TestArrayValidation:
    """FRF-002: Array field compared with scalar `in` check."""

    def test_valid_array_subset(self):
        f = MetadataField("tags", FieldType.ARRAY, ["ai", "ml", "nlp"])
        result = ValidationResult()
        validate_field(f, ["ai", "ml"], result)
        assert result.is_valid

    def test_invalid_array_item(self):
        f = MetadataField("tags", FieldType.ARRAY, ["ai", "ml", "nlp"])
        result = ValidationResult()
        validate_field(f, ["ai", "quantum"], result)
        assert not result.is_valid
        assert "quantum" in str(result.errors[0])

    def test_empty_array_valid(self):
        f = MetadataField("tags", FieldType.ARRAY, ["ai", "ml"])
        result = ValidationResult()
        validate_field(f, [], result)
        assert result.is_valid

    def test_scalar_enum_valid(self):
        f = MetadataField("topic", FieldType.STRING, ["science", "history"])
        result = ValidationResult()
        validate_field(f, "science", result)
        assert result.is_valid

    def test_scalar_enum_invalid(self):
        f = MetadataField("topic", FieldType.STRING, ["science", "history"])
        result = ValidationResult()
        validate_field(f, "math", result)
        assert not result.is_valid

    def test_int_coerced_for_enum(self):
        """TRF-004: Model sends int 3, schema valid_values are strings."""
        f = MetadataField("level", FieldType.STRING, ["1", "2", "3"])
        result = ValidationResult()
        validate_field(f, 3, result)
        assert result.is_valid, f"Errors: {result.errors}"

    def test_string_coerced_for_int_enum(self):
        f = MetadataField("priority", FieldType.INTEGER, ["1", "2", "3"])
        result = ValidationResult()
        validate_field(f, "2", result)
        assert result.is_valid


# ===========================================================================
# 4. Range validation (TRF-028)
# ===========================================================================


class TestRangeValidation:

    def test_integer_in_range(self):
        f = MetadataField("difficulty", FieldType.INTEGER, "1-5", required=True)
        result = ValidationResult()
        validate_field(f, 3, result)
        assert result.is_valid

    def test_integer_below_range(self):
        f = MetadataField("difficulty", FieldType.INTEGER, "1-5")
        result = ValidationResult()
        validate_field(f, 0, result)
        assert not result.is_valid

    def test_integer_above_range(self):
        f = MetadataField("difficulty", FieldType.INTEGER, "1-5")
        result = ValidationResult()
        validate_field(f, 6, result)
        assert not result.is_valid

    def test_plus_range_valid(self):
        f = MetadataField("turns", FieldType.INTEGER, "1+")
        result = ValidationResult()
        validate_field(f, 10, result)
        assert result.is_valid

    def test_plus_range_zero_invalid(self):
        f = MetadataField("turns", FieldType.INTEGER, "1+")
        result = ValidationResult()
        validate_field(f, 0, result)
        assert not result.is_valid

    def test_string_value_for_range_coerced(self):
        """Model sends string "3" for an integer range field."""
        f = MetadataField("difficulty", FieldType.INTEGER, "1-5")
        result = ValidationResult()
        validate_field(f, "3", result)
        assert result.is_valid

    def test_non_numeric_for_range_fails(self):
        f = MetadataField("difficulty", FieldType.STRING, "1-5")
        result = ValidationResult()
        validate_field(f, "abc", result)
        assert not result.is_valid

    def test_array_with_range_all_valid(self):
        f = MetadataField("scores", FieldType.ARRAY, "0-100")
        result = ValidationResult()
        validate_field(f, [50, 75, 100], result)
        assert result.is_valid

    def test_array_with_range_one_invalid(self):
        f = MetadataField("scores", FieldType.ARRAY, "0-100")
        result = ValidationResult()
        validate_field(f, [50, 101], result)
        assert not result.is_valid


# ===========================================================================
# 5. Required config fields (TRF-022)
# ===========================================================================


class TestValidateConfig:
    """TRF-022: max_tokens must be explicitly set."""

    def test_missing_max_tokens(self):
        result = validate_config({})
        assert not result.is_valid
        assert any("max_tokens" in str(e) for e in result.errors)

    def test_max_tokens_present(self):
        result = validate_config({"max_tokens": 4096})
        assert result.is_valid

    def test_max_tokens_none(self):
        result = validate_config({"max_tokens": None})
        assert not result.is_valid

    def test_missing_context_window_warning(self):
        result = validate_config({"max_tokens": 4096})
        assert result.is_valid
        assert any("context_window" in w for w in result.warnings)

    def test_context_window_present_no_warning(self):
        result = validate_config({"max_tokens": 4096, "context_window": 128000})
        assert len(result.warnings) == 0

    def test_temperature_in_range(self):
        result = validate_config({"max_tokens": 4096, "temperature": 0.7})
        assert result.is_valid

    def test_temperature_out_of_range(self):
        result = validate_config({"max_tokens": 4096, "temperature": 3.0})
        assert not result.is_valid
        assert any("temperature" in str(e) for e in result.errors)

    def test_temperature_non_numeric(self):
        result = validate_config({"max_tokens": 4096, "temperature": "hot"})
        assert not result.is_valid


# ===========================================================================
# 6. DomainValidator integration
# ===========================================================================


class TestDomainValidator:

    @pytest.fixture
    def schema(self):
        return [
            MetadataField("topic", FieldType.STRING, ["science", "history", "math"]),
            MetadataField("difficulty", FieldType.INTEGER, "1-5", required=True),
            MetadataField("tags", FieldType.ARRAY, ["ai", "ml", "nlp", "cv"]),
            MetadataField("turns", FieldType.INTEGER, "1+", required=True),
        ]

    @pytest.fixture
    def validator(self, schema):
        return DomainValidator(schema)

    def test_valid_data(self, validator):
        result = validator.validate({
            "topic": "science",
            "difficulty": 3,
            "tags": ["ai", "ml"],
            "turns": 5,
        })
        assert result.is_valid

    def test_missing_required_field(self, validator):
        result = validator.validate({"topic": "science"})
        assert not result.is_valid
        names = [e.field_name for e in result.errors]
        assert "difficulty" in names
        assert "turns" in names

    def test_invalid_enum_value(self, validator):
        result = validator.validate({
            "topic": "cooking",
            "difficulty": 3,
            "turns": 1,
        })
        assert not result.is_valid
        assert result.errors[0].field_name == "topic"

    def test_out_of_range(self, validator):
        result = validator.validate({
            "difficulty": 10,
            "turns": 1,
        })
        assert not result.is_valid
        assert result.errors[0].field_name == "difficulty"

    def test_with_config_validation(self, validator):
        result = validator.validate(
            {"difficulty": 3, "turns": 1},
            config={"max_tokens": 4096},
        )
        assert result.is_valid

    def test_with_missing_config(self, validator):
        result = validator.validate(
            {"difficulty": 3, "turns": 1},
            config={},
        )
        assert not result.is_valid
        assert any("max_tokens" in str(e) for e in result.errors)

    def test_unknown_field_ignored(self, validator):
        result = validator.validate({
            "difficulty": 3,
            "turns": 1,
            "unknown_field": "value",
        })
        assert result.is_valid

    def test_fields_property(self, validator):
        assert "topic" in validator.fields
        assert "difficulty" in validator.fields

    def test_no_valid_values_no_constraint(self):
        schema = [MetadataField("freetext", FieldType.STRING)]
        v = DomainValidator(schema)
        result = v.validate({"freetext": "anything goes"})
        assert result.is_valid


# ===========================================================================
# 7. Regression tests — actual failing values from runs 1, 3, 9
# ===========================================================================


class TestRegressionRuns:
    """Regression tests based on actual failures from agent runs."""

    def test_run1_int_vs_string_valid_values(self):
        """Run 1 TRF-004: Model returned difficulty=3 (int), valid_values=["1","2","3","4","5"]."""
        f = MetadataField("difficulty", FieldType.STRING, ["1", "2", "3", "4", "5"])
        result = ValidationResult()
        validate_field(f, 3, result)
        assert result.is_valid, f"Run 1 regression: {result.errors}"

    def test_run3_range_as_enum(self):
        """Run 3 TRF-028: turns field had valid_values="1+" treated as enum."""
        f = MetadataField("turns", FieldType.INTEGER, "1+")
        result = ValidationResult()
        validate_field(f, 5, result)
        assert result.is_valid, f"Run 3 regression: {result.errors}"

    def test_run3_range_boundary(self):
        """Run 3: difficulty range 1-5, model sent exactly 1."""
        f = MetadataField("difficulty", FieldType.INTEGER, "1-5")
        result = ValidationResult()
        validate_field(f, 1, result)
        assert result.is_valid

    def test_run9_array_scalar_check(self):
        """Run 9 FRF-002: tags=["ai","ml"] compared with `in` instead of set subset."""
        f = MetadataField("tags", FieldType.ARRAY, ["ai", "ml", "nlp", "cv", "rl"])
        result = ValidationResult()
        validate_field(f, ["ai", "ml"], result)
        assert result.is_valid, f"Run 9 regression: {result.errors}"

    def test_run1_missing_max_tokens(self):
        """Run 1 TRF-022: Config had no max_tokens."""
        result = validate_config({"model": "gpt-4", "temperature": 0.7})
        assert not result.is_valid
        assert any("max_tokens" in str(e) for e in result.errors)

    def test_run9_temperature_as_string(self):
        """Run 9: Temperature returned as string '0.7' by model."""
        result = validate_config({"max_tokens": 4096, "temperature": "0.7"})
        assert result.is_valid


# ===========================================================================
# 8. ValidationResult and ValidationError
# ===========================================================================


class TestValidationResult:

    def test_empty_is_valid(self):
        r = ValidationResult()
        assert r.is_valid

    def test_with_error_not_valid(self):
        r = ValidationResult()
        r.add_error("f", "bad")
        assert not r.is_valid

    def test_warnings_dont_invalidate(self):
        r = ValidationResult()
        r.add_warning("watch out")
        assert r.is_valid
        assert len(r.warnings) == 1


class TestValidationErrorRepr:

    def test_repr(self):
        e = ValidationError("field", "message")
        assert "field" in repr(e)
        assert "message" in repr(e)

    def test_str(self):
        e = ValidationError("field", "message")
        assert str(e) == "field: message"


# ===========================================================================
# 9. MetadataField construction
# ===========================================================================


class TestMetadataField:

    def test_defaults(self):
        f = MetadataField("name")
        assert f.type == FieldType.STRING
        assert f.valid_values == []
        assert f.required is False
        assert f.description == ""

    def test_with_all_fields(self):
        f = MetadataField(
            "topic",
            FieldType.ARRAY,
            ["a", "b"],
            required=True,
            description="Topic tags",
        )
        assert f.name == "topic"
        assert f.type == FieldType.ARRAY
        assert f.valid_values == ["a", "b"]
        assert f.required is True
        assert f.description == "Topic tags"


# ===========================================================================
# 10. Edge cases
# ===========================================================================


class TestEdgeCases:

    def test_coerce_tuple_to_array(self):
        result = coerce_value(("a", "b"), FieldType.ARRAY)
        assert result == ["a", "b"]

    def test_coerce_empty_string_to_array(self):
        result = coerce_value("", FieldType.ARRAY)
        assert result == []

    def test_type_coercion_failure_in_field(self):
        f = MetadataField("count", FieldType.INTEGER)
        result = ValidationResult()
        validate_field(f, "not_a_number", result)
        assert not result.is_valid
        assert "coercion" in result.errors[0].message.lower()

    def test_range_at_boundary_max(self):
        r = Range(min_value=0, max_value=100)
        assert r.contains(0) is True
        assert r.contains(100) is True

    def test_field_type_enum_values(self):
        assert FieldType.STRING.value == "string"
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.ARRAY.value == "array"
        assert FieldType.FLOAT.value == "float"
        assert FieldType.BOOLEAN.value == "boolean"
