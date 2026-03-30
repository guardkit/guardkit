"""Tests for GOAL.md domain configuration schema.

Covers:
- MetadataFieldSchema dataclass
- QualityThresholds dataclass
- EvaluationCriterion score_range field
- GoalSchema extended fields (backward compat + new fields)
- _parse_markdown_table generic parser
- _parse_metadata_table column mapping
- _parse_criteria_table weight normalisation (% and decimal)
- _parse_quality_thresholds bullet list parser
- parse_goal_md full document parser
- build_coach_criteria_section Coach prompt generation
- _parse_list_value bracket / bare comma formats

Coverage Target: >=85%
Test Count: 39 tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import sys

import pytest

TEMPLATE_ROOT = pathlib.Path(__file__).parent.parent


def _load_module(name: str, file_path: pathlib.Path):
    """Load a Python module from an explicit file path using importlib.

    Uses SourceFileLoader directly to handle non-standard extensions (.j2)
    and to avoid sys.path pollution / module name collisions.
    """
    unique_name = f"_test_goal_schema_.{name}"
    loader = importlib.machinery.SourceFileLoader(unique_name, str(file_path))
    spec = importlib.util.spec_from_file_location(
        unique_name, str(file_path), loader=loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(unique_name, None)
        raise
    return module


@pytest.fixture(scope="module")
def gs():
    """Load goal_schema module once for the entire test module."""
    return _load_module(
        "goal_schema",
        TEMPLATE_ROOT / "scaffold" / "goal_schema.py.j2",
    )


# ============================================================================
# 1. MetadataFieldSchema (4 tests)
# ============================================================================


class TestMetadataFieldSchema:
    """Tests for MetadataFieldSchema dataclass."""

    def test_default_values(self, gs):
        f = gs.MetadataFieldSchema(name="topic")
        assert f.name == "topic"
        assert f.type == "string"
        assert f.valid_values == ""
        assert f.required is False
        assert f.description == ""

    def test_custom_values(self, gs):
        f = gs.MetadataFieldSchema(
            name="difficulty",
            type="integer",
            valid_values="range: 1-5",
            required=True,
            description="Difficulty level",
        )
        assert f.name == "difficulty"
        assert f.type == "integer"
        assert f.valid_values == "range: 1-5"
        assert f.required is True
        assert f.description == "Difficulty level"

    def test_required_field(self, gs):
        f = gs.MetadataFieldSchema(name="subject", required=True)
        assert f.required is True

    def test_array_type(self, gs):
        f = gs.MetadataFieldSchema(name="tags", type="array")
        assert f.type == "array"


# ============================================================================
# 2. QualityThresholds (3 tests)
# ============================================================================


class TestQualityThresholds:
    """Tests for QualityThresholds dataclass."""

    def test_default_values(self, gs):
        qt = gs.QualityThresholds()
        assert qt.minimum_weighted_score == 0.7
        assert qt.required_fields == []
        assert qt.format_requirements == []

    def test_custom_values(self, gs):
        qt = gs.QualityThresholds(
            minimum_weighted_score=0.85,
            required_fields=["topic", "difficulty"],
            format_requirements=["think_blocks"],
        )
        assert qt.minimum_weighted_score == 0.85
        assert qt.required_fields == ["topic", "difficulty"]
        assert qt.format_requirements == ["think_blocks"]

    def test_empty_lists_default(self, gs):
        qt = gs.QualityThresholds(minimum_weighted_score=0.6)
        assert qt.required_fields == []
        assert qt.format_requirements == []


# ============================================================================
# 3. EvaluationCriterion score_range (2 tests)
# ============================================================================


class TestEvaluationCriterionScoreRange:
    """Tests for the score_range field on EvaluationCriterion."""

    def test_default_score_range(self, gs):
        c = gs.EvaluationCriterion(name="accuracy", weight=0.5)
        assert c.score_range == "0.0-1.0"

    def test_custom_score_range(self, gs):
        c = gs.EvaluationCriterion(name="difficulty", weight=0.5, score_range="1-5")
        assert c.score_range == "1-5"


# ============================================================================
# 4. GoalSchema extended (3 tests)
# ============================================================================


class TestGoalSchemaExtended:
    """Tests for the extended GoalSchema fields."""

    def test_backward_compat(self, gs):
        """GoalSchema without new fields should still construct successfully."""
        schema = gs.GoalSchema(domain_name="legacy")
        assert schema.domain_name == "legacy"
        assert schema.metadata_schema == []
        assert schema.quality_thresholds is None
        assert schema.generation_target == ""

    def test_with_metadata_schema(self, gs):
        meta = [gs.MetadataFieldSchema(name="topic")]
        schema = gs.GoalSchema(domain_name="test", metadata_schema=meta)
        assert len(schema.metadata_schema) == 1
        assert schema.metadata_schema[0].name == "topic"

    def test_with_quality_thresholds(self, gs):
        qt = gs.QualityThresholds(minimum_weighted_score=0.8)
        schema = gs.GoalSchema(domain_name="test", quality_thresholds=qt)
        assert schema.quality_thresholds is not None
        assert schema.quality_thresholds.minimum_weighted_score == 0.8


# ============================================================================
# 5. _parse_markdown_table (5 tests)
# ============================================================================


class TestParseMarkdownTable:
    """Tests for the generic markdown table parser."""

    def test_simple_table(self, gs):
        text = (
            "| Name | Age |\n"
            "|------|-----|\n"
            "| Alice | 30 |\n"
            "| Bob | 25 |\n"
        )
        rows = gs._parse_markdown_table(text)
        assert len(rows) == 2
        assert rows[0]["Name"] == "Alice"
        assert rows[1]["Age"] == "25"

    def test_with_extra_whitespace(self, gs):
        text = (
            "|  Field  |  Type  |\n"
            "|---------|--------|\n"
            "|  topic  |  string  |\n"
        )
        rows = gs._parse_markdown_table(text)
        assert rows[0]["Field"] == "topic"
        assert rows[0]["Type"] == "string"

    def test_empty_section(self, gs):
        assert gs._parse_markdown_table("") == []

    def test_table_with_missing_pipes(self, gs):
        """A section without any pipe characters returns empty result gracefully."""
        text = "Just plain text\nNo table here\n"
        rows = gs._parse_markdown_table(text)
        assert rows == []

    def test_skips_separator_row(self, gs):
        """Separator rows (---) must not appear in output."""
        text = (
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
        )
        rows = gs._parse_markdown_table(text)
        assert len(rows) == 1
        assert rows[0]["A"] == "1"


# ============================================================================
# 6. _parse_metadata_table (5 tests)
# ============================================================================


class TestParseMetadataTable:
    """Tests for _parse_metadata_table column mapping."""

    def test_parse_enum_field(self, gs):
        text = (
            "| Field | Type | Valid Values | Required | Description |\n"
            "|-------|------|-------------|----------|-------------|\n"
            "| subject | string | enum: [science, history] | yes | Subject area |\n"
        )
        fields = gs._parse_metadata_table(text)
        assert len(fields) == 1
        assert fields[0].name == "subject"
        assert fields[0].valid_values == "enum: [science, history]"
        assert fields[0].required is True

    def test_parse_range_field(self, gs):
        """TRF-028 regression: range: 1-5 must be preserved verbatim."""
        text = (
            "| Field | Type | Valid Values | Required | Description |\n"
            "|-------|------|-------------|----------|-------------|\n"
            "| difficulty | integer | range: 1-5 | no | Difficulty |\n"
        )
        fields = gs._parse_metadata_table(text)
        assert fields[0].valid_values == "range: 1-5"

    def test_parse_range_plus(self, gs):
        """TRF-028 regression: range: 1+ must be preserved verbatim."""
        text = (
            "| Field | Type | Valid Values | Required | Description |\n"
            "|-------|------|-------------|----------|-------------|\n"
            "| count | integer | range: 1+ | no | Count |\n"
        )
        fields = gs._parse_metadata_table(text)
        assert fields[0].valid_values == "range: 1+"

    def test_parse_array_type(self, gs):
        """FRF-002 regression: type=array must be mapped correctly."""
        text = (
            "| Field | Type | Valid Values | Required | Description |\n"
            "|-------|------|-------------|----------|-------------|\n"
            "| tags | array | | no | Tag list |\n"
        )
        fields = gs._parse_metadata_table(text)
        assert fields[0].type == "array"

    def test_parse_required_field(self, gs):
        """'yes' -> True, 'no' -> False for the required column."""
        text = (
            "| Field | Type | Valid Values | Required | Description |\n"
            "|-------|------|-------------|----------|-------------|\n"
            "| alpha | string | | yes | First |\n"
            "| beta | string | | no | Second |\n"
        )
        fields = gs._parse_metadata_table(text)
        assert fields[0].required is True
        assert fields[1].required is False


# ============================================================================
# 7. _parse_criteria_table (4 tests)
# ============================================================================


class TestParseCriteriaTable:
    """Tests for _parse_criteria_table column mapping and weight normalisation."""

    def test_parse_basic_criteria(self, gs):
        text = (
            "| Criterion | Weight | Description | Score Range |\n"
            "|-----------|--------|-------------|-------------|\n"
            "| accuracy | 0.4 | Factual correctness | 0.0-1.0 |\n"
        )
        criteria = gs._parse_criteria_table(text)
        assert len(criteria) == 1
        assert criteria[0].name == "accuracy"
        assert criteria[0].weight == pytest.approx(0.4)

    def test_weight_as_percentage(self, gs):
        """Weight expressed as '30%' should be normalised to 0.3."""
        text = (
            "| Criterion | Weight | Description | Score Range |\n"
            "|-----------|--------|-------------|-------------|\n"
            "| quality | 30% | Writing quality | 0.0-1.0 |\n"
        )
        criteria = gs._parse_criteria_table(text)
        assert criteria[0].weight == pytest.approx(0.3)

    def test_weights_as_decimal(self, gs):
        """Weight expressed as '0.3' should be read directly as 0.3."""
        text = (
            "| Criterion | Weight | Description | Score Range |\n"
            "|-----------|--------|-------------|-------------|\n"
            "| structure | 0.3 | JSON schema | 0.0-1.0 |\n"
        )
        criteria = gs._parse_criteria_table(text)
        assert criteria[0].weight == pytest.approx(0.3)

    def test_score_range_parsed(self, gs):
        text = (
            "| Criterion | Weight | Description | Score Range |\n"
            "|-----------|--------|-------------|-------------|\n"
            "| depth | 0.5 | Depth of explanation | 1-5 |\n"
        )
        criteria = gs._parse_criteria_table(text)
        assert criteria[0].score_range == "1-5"


# ============================================================================
# 8. _parse_quality_thresholds (3 tests)
# ============================================================================


class TestParseQualityThresholds:
    """Tests for _parse_quality_thresholds bullet list parsing."""

    def test_parse_thresholds(self, gs):
        text = (
            "- minimum_weighted_score: 0.75\n"
            "- required_fields: [topic, difficulty]\n"
            "- format_requirements: [think_blocks, json_structure]\n"
        )
        qt = gs._parse_quality_thresholds(text)
        assert qt.minimum_weighted_score == pytest.approx(0.75)
        assert qt.required_fields == ["topic", "difficulty"]
        assert qt.format_requirements == ["think_blocks", "json_structure"]

    def test_parse_empty_lists(self, gs):
        text = (
            "- minimum_weighted_score: 0.7\n"
            "- required_fields: []\n"
            "- format_requirements: []\n"
        )
        qt = gs._parse_quality_thresholds(text)
        assert qt.required_fields == []
        assert qt.format_requirements == []

    def test_parse_missing_fields(self, gs):
        """Missing keys fall back to QualityThresholds defaults."""
        qt = gs._parse_quality_thresholds("- minimum_weighted_score: 0.6\n")
        assert qt.minimum_weighted_score == pytest.approx(0.6)
        assert qt.required_fields == []
        assert qt.format_requirements == []


# ============================================================================
# 9. parse_goal_md (4 tests)
# ============================================================================


_FULL_GOAL_MD = """\
# Domain: science-qa

## Generation Target

Generate high-quality science question-answer pairs for training.

## Metadata Schema

| Field | Type | Valid Values | Required | Description |
|-------|------|-------------|----------|-------------|
| topic | string | enum: [biology, physics] | yes | Subject topic |
| difficulty | integer | range: 1-5 | no | Difficulty level |

## Evaluation Criteria

| Criterion | Weight | Description | Score Range |
|-----------|--------|-------------|-------------|
| accuracy | 0.4 | Factual correctness | 0.0-1.0 |
| completeness | 0.3 | Coverage of topic | 0.0-1.0 |
| clarity | 0.3 | Clear explanation | 0.0-1.0 |

## Quality Thresholds

- minimum_weighted_score: 0.75
- required_fields: [topic, difficulty]
- format_requirements: [think_blocks]
"""


class TestParseGoalMd:
    """Tests for the top-level parse_goal_md function."""

    def test_full_goal_md(self, gs):
        schema = gs.parse_goal_md(_FULL_GOAL_MD)
        assert schema.domain_name == "science-qa"
        assert "Generate high-quality" in schema.generation_target
        assert len(schema.metadata_schema) == 2
        assert len(schema.criteria) == 3
        assert schema.quality_thresholds is not None
        assert schema.quality_thresholds.minimum_weighted_score == pytest.approx(0.75)

    def test_domain_name_from_heading(self, gs):
        schema = gs.parse_goal_md("# Domain: my-domain\n\n## Generation Target\nSomething\n")
        assert schema.domain_name == "my-domain"

    def test_missing_sections(self, gs):
        """A minimal document with only H1 should produce a valid GoalSchema."""
        schema = gs.parse_goal_md("# Domain: minimal\n")
        assert schema.domain_name == "minimal"
        assert schema.metadata_schema == []
        assert schema.criteria == []
        assert schema.quality_thresholds is None
        assert schema.generation_target == ""

    def test_round_trip(self, gs):
        """Build a GoalSchema from defaults, parse back, verify key fields."""
        # Build a minimal GOAL.md string manually
        text = (
            "# Domain: roundtrip\n\n"
            "## Generation Target\n\nTest target.\n\n"
            "## Evaluation Criteria\n\n"
            "| Criterion | Weight | Description | Score Range |\n"
            "|-----------|--------|-------------|-------------|\n"
            "| accuracy | 0.6 | Accuracy check | 0.0-1.0 |\n"
            "| quality | 0.4 | Quality check | 0.0-1.0 |\n\n"
            "## Quality Thresholds\n\n"
            "- minimum_weighted_score: 0.7\n"
            "- required_fields: []\n"
            "- format_requirements: []\n"
        )
        schema = gs.parse_goal_md(text)
        assert schema.domain_name == "roundtrip"
        assert len(schema.criteria) == 2
        total_weight = sum(c.weight for c in schema.criteria)
        assert total_weight == pytest.approx(1.0)
        assert schema.quality_thresholds.minimum_weighted_score == pytest.approx(0.7)


# ============================================================================
# 10. build_coach_criteria_section (3 tests)
# ============================================================================


class TestBuildCoachCriteriaSection:
    """Tests for build_coach_criteria_section prompt generation."""

    @pytest.fixture
    def sample_goal(self, gs):
        return gs.GoalSchema(
            domain_name="test-domain",
            criteria=[
                gs.EvaluationCriterion(
                    name="accuracy",
                    weight=0.6,
                    description="Factual correctness",
                    accept_example="All facts cited",
                    reject_example="No citations",
                    score_range="0.0-1.0",
                ),
                gs.EvaluationCriterion(
                    name="quality",
                    weight=0.4,
                    description="Writing quality",
                    score_range="0.0-1.0",
                ),
            ],
            quality_thresholds=gs.QualityThresholds(
                minimum_weighted_score=0.75,
                required_fields=["topic"],
                format_requirements=["think_blocks"],
            ),
        )

    def test_includes_criteria(self, gs, sample_goal):
        section = gs.build_coach_criteria_section(sample_goal)
        assert "accuracy" in section
        assert "quality" in section

    def test_includes_weights(self, gs, sample_goal):
        section = gs.build_coach_criteria_section(sample_goal)
        # 0.6 -> 60%, 0.4 -> 40%
        assert "60%" in section
        assert "40%" in section

    def test_includes_thresholds(self, gs, sample_goal):
        section = gs.build_coach_criteria_section(sample_goal)
        assert "0.75" in section
        assert "topic" in section
        assert "think_blocks" in section


# ============================================================================
# 11. _parse_list_value (3 tests)
# ============================================================================


class TestParseListValue:
    """Tests for _parse_list_value helper."""

    def test_bracket_list(self, gs):
        result = gs._parse_list_value("[a, b, c]")
        assert result == ["a", "b", "c"]

    def test_bare_values(self, gs):
        result = gs._parse_list_value("a, b, c")
        assert result == ["a", "b", "c"]

    def test_empty(self, gs):
        assert gs._parse_list_value("") == []
        assert gs._parse_list_value("[]") == []
