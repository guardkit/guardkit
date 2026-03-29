"""Type-aware domain validator for LangChain DeepAgents templates.

Prevents the 4 validation bugs (TRF-004, TRF-028, FRF-002, TRF-022)
by handling type coercion, array fields, and range notation at the
model-output boundary.

Fixes Prevented:
    TRF-004: Model sends int, schema has strings -> type mismatch
    TRF-028: Range notation treated as enum -> false failures
    FRF-002: Array field compared with scalar `in` check
    TRF-022: max_tokens not explicitly set in config
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Range notation regexes (acceptance criteria)
# ---------------------------------------------------------------------------
_RANGE_PLUS_RE = re.compile(r"^(\d+)\+$")  # e.g. "1+", "0+"
_RANGE_MINMAX_RE = re.compile(r"^(\d+)-(\d+)$")  # e.g. "1-10", "0-100"


class FieldType(str, Enum):
    """Metadata field types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    ARRAY = "array"
    BOOLEAN = "boolean"


@dataclass
class MetadataField:
    """Schema definition for a single metadata field.

    Attributes:
        name: Field identifier.
        type: Field type (string, integer, float, array, boolean).
        valid_values: Allowed values (enum list) or range notation string.
            Empty list means no enum constraint.
            A string like ``"1+"`` or ``"1-10"`` is range notation.
        required: Whether the field must be present.
        description: Human-readable description.
    """

    name: str
    type: FieldType = FieldType.STRING
    valid_values: Union[List[str], str] = field(default_factory=list)
    required: bool = False
    description: str = ""


class ValidationError:
    """A single validation failure."""

    def __init__(self, field_name: str, message: str, value: Any = None) -> None:
        self.field_name = field_name
        self.message = message
        self.value = value

    def __repr__(self) -> str:
        return f"ValidationError({self.field_name!r}, {self.message!r})"

    def __str__(self) -> str:
        return f"{self.field_name}: {self.message}"


@dataclass
class ValidationResult:
    """Aggregated validation outcome."""

    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, field_name: str, message: str, value: Any = None) -> None:
        self.errors.append(ValidationError(field_name, message, value))

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


# ---------------------------------------------------------------------------
# Range notation parsing
# ---------------------------------------------------------------------------


@dataclass
class Range:
    """Parsed range with inclusive min and optional max."""

    min_value: int
    max_value: Optional[int] = None  # None means unbounded (e.g. "1+")

    def contains(self, value: Union[int, float]) -> bool:
        if value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True


def parse_range(notation: str) -> Optional[Range]:
    """Parse range notation into a Range object.

    Supported formats:
        ``"1+"``    -> Range(min_value=1, max_value=None)
        ``"0+"``    -> Range(min_value=0, max_value=None)
        ``"1-10"``  -> Range(min_value=1, max_value=10)
        ``"0-100"`` -> Range(min_value=0, max_value=100)

    Returns None if the string is not range notation.
    """
    m = _RANGE_PLUS_RE.match(notation.strip())
    if m:
        return Range(min_value=int(m.group(1)))

    m = _RANGE_MINMAX_RE.match(notation.strip())
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo > hi:
            return None
        return Range(min_value=lo, max_value=hi)

    return None


def is_range_notation(value: Union[List[str], str]) -> bool:
    """Return True if *value* is a range-notation string."""
    if isinstance(value, str):
        return parse_range(value) is not None
    return False


# ---------------------------------------------------------------------------
# Type coercion at model-output boundary (TRF-004)
# ---------------------------------------------------------------------------


def coerce_value(value: Any, target_type: FieldType) -> Any:
    """Coerce a model output value to match the schema type.

    Applied BEFORE comparison with valid_values so that e.g. an int ``3``
    from the model is coerced to ``"3"`` when the schema type is string.

    Raises ValueError if coercion is impossible.
    """
    if value is None:
        return value

    if target_type == FieldType.STRING:
        return str(value)

    if target_type == FieldType.INTEGER:
        if isinstance(value, str):
            return int(value)
        return int(value)

    if target_type == FieldType.FLOAT:
        if isinstance(value, str):
            return float(value)
        return float(value)

    if target_type == FieldType.BOOLEAN:
        if isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "1", "yes"):
                return True
            if lower in ("false", "0", "no"):
                return False
            raise ValueError(f"Cannot coerce {value!r} to boolean")
        return bool(value)

    if target_type == FieldType.ARRAY:
        if isinstance(value, str):
            # Try comma-separated
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    return value


# ---------------------------------------------------------------------------
# Field validation (FRF-002, TRF-028)
# ---------------------------------------------------------------------------


def validate_field(
    field_def: MetadataField,
    value: Any,
    result: ValidationResult,
) -> None:
    """Validate a single field value against its schema definition.

    Handles:
    - Type coercion (TRF-004)
    - Array vs scalar validation (FRF-002)
    - Range notation (TRF-028)
    """
    # Step 1: Coerce type
    try:
        coerced = coerce_value(value, field_def.type)
    except (ValueError, TypeError) as exc:
        result.add_error(
            field_def.name,
            f"Type coercion failed: {exc}",
            value,
        )
        return

    # Step 2: Check valid_values constraint
    valid = field_def.valid_values

    # No constraint
    if not valid:
        return

    # Range notation
    if is_range_notation(valid):
        rng = parse_range(valid)  # type: ignore[arg-type]
        if rng is None:
            result.add_error(field_def.name, f"Invalid range notation: {valid!r}")
            return

        if field_def.type == FieldType.ARRAY:
            if not isinstance(coerced, list):
                coerced = [coerced]
            for item in coerced:
                try:
                    num = float(item) if isinstance(item, str) else item
                except (ValueError, TypeError):
                    result.add_error(
                        field_def.name,
                        f"Array item {item!r} is not numeric for range {valid}",
                        item,
                    )
                    return
                if not rng.contains(num):
                    result.add_error(
                        field_def.name,
                        f"Value {num} out of range {valid}",
                        num,
                    )
            return

        # Scalar range check
        try:
            num = float(coerced) if isinstance(coerced, str) else coerced
        except (ValueError, TypeError):
            result.add_error(
                field_def.name,
                f"Value {coerced!r} is not numeric for range {valid}",
                coerced,
            )
            return
        if not rng.contains(num):
            result.add_error(
                field_def.name,
                f"Value {num} out of range {valid}",
                num,
            )
        return

    # Enum-style valid_values (must be a list)
    if not isinstance(valid, list):
        return

    if field_def.type == FieldType.ARRAY:
        # Array: set-based validation (FRF-002)
        # valid_values are element-level enums, compare as strings
        valid_set = set(str(v) for v in valid)
        if not isinstance(coerced, list):
            coerced = [coerced]
        coerced_strs = set(str(item) for item in coerced)
        invalid_items = coerced_strs - valid_set
        if invalid_items:
            result.add_error(
                field_def.name,
                f"Invalid values: {sorted(invalid_items)}. "
                f"Allowed: {sorted(valid_set)}",
                coerced,
            )
    else:
        # Scalar: coerce valid_values to match field type for comparison
        coerced_valid = []
        for v in valid:
            try:
                coerced_valid.append(coerce_value(v, field_def.type))
            except (ValueError, TypeError):
                coerced_valid.append(v)
        if coerced not in coerced_valid:
            result.add_error(
                field_def.name,
                f"Value {coerced!r} not in {coerced_valid!r}",
                coerced,
            )


# ---------------------------------------------------------------------------
# Required config fields validation (TRF-022)
# ---------------------------------------------------------------------------

REQUIRED_CONFIG_FIELDS = ["max_tokens"]
RECOMMENDED_CONFIG_FIELDS = ["context_window"]
TEMPERATURE_RANGE = Range(min_value=0, max_value=2)


def validate_config(
    config: Dict[str, Any],
    result: Optional[ValidationResult] = None,
) -> ValidationResult:
    """Validate required and recommended config fields.

    Checks:
    - ``max_tokens`` must be explicitly set (TRF-022)
    - ``context_window`` recommended
    - ``temperature`` within 0-2 if present
    """
    if result is None:
        result = ValidationResult()

    for field_name in REQUIRED_CONFIG_FIELDS:
        if field_name not in config or config[field_name] is None:
            result.add_error(
                field_name,
                f"Required config field '{field_name}' must be explicitly set",
            )

    for field_name in RECOMMENDED_CONFIG_FIELDS:
        if field_name not in config or config[field_name] is None:
            result.add_warning(
                f"Recommended config field '{field_name}' is not documented"
            )

    if "temperature" in config and config["temperature"] is not None:
        temp = config["temperature"]
        try:
            temp_val = float(temp)
            if not TEMPERATURE_RANGE.contains(temp_val):
                result.add_error(
                    "temperature",
                    f"Temperature {temp_val} outside recommended range 0-2",
                    temp_val,
                )
        except (ValueError, TypeError):
            result.add_error(
                "temperature",
                f"Temperature {temp!r} is not numeric",
                temp,
            )

    return result


# ---------------------------------------------------------------------------
# DomainValidator: main entry point
# ---------------------------------------------------------------------------


class DomainValidator:
    """Validate model output metadata against a domain schema.

    Usage::

        schema = [
            MetadataField("topic", FieldType.STRING, ["science", "history"]),
            MetadataField("difficulty", FieldType.INTEGER, "1-5", required=True),
            MetadataField("tags", FieldType.ARRAY, ["ai", "ml", "nlp"]),
        ]
        validator = DomainValidator(schema)
        result = validator.validate({"topic": "science", "difficulty": 3, "tags": ["ai", "ml"]})
        assert result.is_valid
    """

    def __init__(self, schema: Sequence[MetadataField]) -> None:
        self._schema = {f.name: f for f in schema}

    @property
    def fields(self) -> Dict[str, MetadataField]:
        return dict(self._schema)

    def validate(
        self,
        data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate model output data against the schema.

        Args:
            data: Model output metadata dict.
            config: Optional runtime config to validate (max_tokens etc.).

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        # Check required fields
        for name, field_def in self._schema.items():
            if field_def.required and name not in data:
                result.add_error(name, "Required field is missing")

        # Validate present fields
        for name, value in data.items():
            if name not in self._schema:
                logger.debug("Skipping unknown field %r", name)
                continue
            validate_field(self._schema[name], value, result)

        # Validate config if provided
        if config is not None:
            validate_config(config, result)

        return result
