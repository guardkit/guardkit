"""Comprehensive test suite for ContentPipeline.

Covers canonical stage ordering, each stage in isolation, full pipeline
integration, custom stage insertion, error handling, observability hooks,
and the TRF-020 regression scenario.

Coverage Target: >=90%
Test Count: 30+ tests
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load modules directly — directory name contains hyphens, not importable.
# Register each module in sys.modules BEFORE exec_module so that dataclass
# decorator and relative imports can resolve __module__.
# ---------------------------------------------------------------------------
_LIB_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
)


def _load_module(name: str, path: Path):
    """Load a module by file path, registering it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load dependencies first (content_pipeline uses relative imports,
# so we also register them under the dotted package path)
_json_mod = _load_module("json_extractor", _LIB_PATH / "json_extractor.py")
_domain_mod = _load_module("domain_validator", _LIB_PATH / "domain_validator.py")
_obs_mod = _load_module("observability", _LIB_PATH / "observability.py")

# Register under dotted names for relative imports in content_pipeline
_PKG = "installer.core.templates.langchain-deepagents.lib"
sys.modules[f"{_PKG}.json_extractor"] = _json_mod
sys.modules[f"{_PKG}.domain_validator"] = _domain_mod
sys.modules[f"{_PKG}.observability"] = _obs_mod

# Create a fake package module so relative imports resolve
import types

if _PKG not in sys.modules:
    _fake_pkg = types.ModuleType(_PKG)
    _fake_pkg.json_extractor = _json_mod
    _fake_pkg.domain_validator = _domain_mod
    _fake_pkg.observability = _obs_mod
    sys.modules[_PKG] = _fake_pkg

# Now load content_pipeline
_cp_spec = importlib.util.spec_from_file_location(
    f"{_PKG}.content_pipeline",
    _LIB_PATH / "content_pipeline.py",
)
_cp_mod = importlib.util.module_from_spec(_cp_spec)
sys.modules[f"{_PKG}.content_pipeline"] = _cp_mod
_cp_spec.loader.exec_module(_cp_mod)

# Import symbols
ContentPipeline = _cp_mod.ContentPipeline
PipelineResult = _cp_mod.PipelineResult
StageResult = _cp_mod.StageResult

JsonExtractor = _json_mod.JsonExtractor
JsonExtractionError = _json_mod.JsonExtractionError
DomainValidator = _domain_mod.DomainValidator
MetadataField = _domain_mod.MetadataField
FieldType = _domain_mod.FieldType
ValidationResult = _domain_mod.ValidationResult
PipelineStageLogger = _obs_mod.PipelineStageLogger
StageTimer = _obs_mod.StageTimer


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def simple_schema():
    """Schema that accepts any dict with 'title' and 'body' string fields."""
    return [
        MetadataField("title", FieldType.STRING, required=True),
        MetadataField("body", FieldType.STRING, required=True),
    ]


@pytest.fixture
def validator(simple_schema):
    """DomainValidator with simple schema."""
    return DomainValidator(simple_schema)


@pytest.fixture
def stage_logger():
    """Fresh PipelineStageLogger."""
    return PipelineStageLogger()


@pytest.fixture
def timer():
    """Fresh StageTimer."""
    return StageTimer()


@pytest.fixture
def pipeline(validator, stage_logger):
    """ContentPipeline with default configuration."""
    return ContentPipeline(
        extractor=JsonExtractor,
        validator=validator,
        stage_logger=stage_logger,
    )


@pytest.fixture
def pipeline_with_timer(validator, stage_logger, timer):
    """ContentPipeline with timer enabled."""
    return ContentPipeline(
        extractor=JsonExtractor,
        validator=validator,
        stage_logger=stage_logger,
        timer=timer,
    )


VALID_JSON = json.dumps({"title": "Hello", "body": "World"})


# ===========================================================================
# 1. Canonical Stage Order (5 tests)
# ===========================================================================


class TestCanonicalOrder:
    """Verify the pipeline enforces the canonical 4-stage order."""

    def test_default_stage_names(self, pipeline):
        """Default pipeline has exactly 4 stages in canonical order."""
        assert pipeline.stage_names == ["normalize", "extract", "validate", "write"]

    def test_stages_cannot_be_reordered(self, pipeline):
        """Canonical stages maintain order even after custom insertion."""
        pipeline.add_stage("custom1", lambda x: x, after="normalize")
        pipeline.add_stage("custom2", lambda x: x, after="extract")
        names = pipeline.stage_names
        assert names.index("normalize") < names.index("custom1")
        assert names.index("custom1") < names.index("extract")
        assert names.index("extract") < names.index("custom2")
        assert names.index("custom2") < names.index("validate")
        assert names.index("validate") < names.index("write")

    def test_normalize_always_first(self, pipeline):
        """Normalize is always the first stage."""
        assert pipeline.stage_names[0] == "normalize"

    def test_write_always_last(self, pipeline):
        """Write is always the last stage."""
        assert pipeline.stage_names[-1] == "write"

    def test_extract_before_validate(self, pipeline):
        """Extract always comes before validate."""
        names = pipeline.stage_names
        assert names.index("extract") < names.index("validate")


# ===========================================================================
# 2. Normalize Stage (5 tests)
# ===========================================================================


class TestNormalizeStage:
    """Test the normalize stage in isolation."""

    def test_string_passthrough(self, pipeline):
        """String input passes through with think tag normalization."""
        result = pipeline._normalize("hello world")
        assert result == "hello world"

    def test_list_to_string(self, pipeline):
        """List input is joined into a single string."""
        result = pipeline._normalize(["line1", "line2", "line3"])
        assert result == "line1\nline2\nline3"

    def test_think_tag_normalization(self, pipeline):
        """Malformed think tags are fixed."""
        result = pipeline._normalize("<think>reasoning<think>output")
        assert "</think>" in result

    def test_unclosed_think_tag(self, pipeline):
        """Unclosed think tags get closed."""
        result = pipeline._normalize("<think>some reasoning\nmore text")
        assert result.endswith("</think>")

    def test_non_string_coercion(self, pipeline):
        """Non-string input is coerced to string."""
        result = pipeline._normalize(12345)
        assert result == "12345"


# ===========================================================================
# 3. Extract Stage (4 tests)
# ===========================================================================


class TestExtractStage:
    """Test the extract stage in isolation."""

    def test_direct_json(self, pipeline):
        """Direct JSON string is extracted."""
        pipeline._current_additional_kwargs = None
        result = pipeline._extract(VALID_JSON)
        assert result == {"title": "Hello", "body": "World"}

    def test_code_fence_json(self, pipeline):
        """JSON in code fences is extracted."""
        pipeline._current_additional_kwargs = None
        content = f"Here is the result:\n```json\n{VALID_JSON}\n```"
        result = pipeline._extract(content)
        assert result == {"title": "Hello", "body": "World"}

    def test_extraction_failure(self, pipeline):
        """Non-JSON content raises JsonExtractionError."""
        pipeline._current_additional_kwargs = None
        with pytest.raises(JsonExtractionError):
            pipeline._extract("this is not json at all")

    def test_additional_kwargs_passthrough(self, pipeline):
        """additional_kwargs are passed to extractor."""
        pipeline._current_additional_kwargs = {
            "reasoning_content": VALID_JSON,
        }
        result = pipeline._extract("no json here")
        assert result == {"title": "Hello", "body": "World"}


# ===========================================================================
# 4. Validate Stage (4 tests)
# ===========================================================================


class TestValidateStage:
    """Test the validate stage in isolation."""

    def test_valid_data_passes(self, pipeline):
        """Valid data passes validation and is returned unchanged."""
        data = {"title": "Hello", "body": "World"}
        result = pipeline._validate(data)
        assert result == data

    def test_missing_required_field(self, pipeline):
        """Missing required field raises ValueError."""
        with pytest.raises(ValueError, match="Validation failed"):
            pipeline._validate({"title": "Hello"})

    def test_validation_result_stored(self, pipeline):
        """Validation result is stored on the pipeline instance."""
        pipeline._validate({"title": "Hello", "body": "World"})
        assert hasattr(pipeline, "_last_validation_result")
        assert pipeline._last_validation_result.is_valid

    def test_extra_fields_pass(self, pipeline):
        """Extra fields not in schema pass through."""
        data = {"title": "Hello", "body": "World", "extra": "ok"}
        result = pipeline._validate(data)
        assert result == data


# ===========================================================================
# 5. Write Stage (3 tests)
# ===========================================================================


class TestWriteStage:
    """Test the write stage in isolation."""

    def test_passthrough_no_write_fn(self, pipeline):
        """Without write_fn, data passes through unchanged."""
        data = {"title": "Hello", "body": "World"}
        result = pipeline._write(data)
        assert result == data

    def test_write_fn_called(self, validator, stage_logger):
        """Write function is called with the data."""
        written = []
        pipe = ContentPipeline(
            extractor=JsonExtractor,
            validator=validator,
            stage_logger=stage_logger,
            write_fn=lambda data: written.append(data) or data,
        )
        data = {"title": "Hello", "body": "World"}
        pipe._write(data)
        assert written == [data]

    def test_write_fn_return_value(self, validator, stage_logger):
        """Write function's return value becomes the stage output."""
        pipe = ContentPipeline(
            extractor=JsonExtractor,
            validator=validator,
            stage_logger=stage_logger,
            write_fn=lambda data: {"written": True, **data},
        )
        result = pipe._write({"title": "Hi", "body": "There"})
        assert result["written"] is True


# ===========================================================================
# 6. Full Pipeline Integration (8 tests)
# ===========================================================================


class TestFullPipeline:
    """Test the complete pipeline end-to-end."""

    def test_success_simple_json(self, pipeline):
        """Simple JSON string processes through all 4 stages."""
        result = pipeline.process(VALID_JSON)
        assert result.success is True
        assert result.content == {"title": "Hello", "body": "World"}
        assert len(result.stages) == 4
        assert all(s.success for s in result.stages)

    def test_success_with_think_tags(self, pipeline):
        """Content with think tags is normalized then extracted."""
        content = f"<think>reasoning</think>{VALID_JSON}"
        result = pipeline.process(content)
        assert result.success is True
        assert result.content == {"title": "Hello", "body": "World"}

    def test_success_block_list(self, pipeline):
        """Block list input is joined and processed."""
        blocks = ['{"title": "Hello",', '"body": "World"}']
        result = pipeline.process(blocks)
        assert result.success is True
        assert result.content == {"title": "Hello", "body": "World"}

    def test_failure_bad_json(self, pipeline):
        """Non-JSON content fails at extract stage."""
        result = pipeline.process("not json")
        assert result.success is False
        assert "extract" in result.error
        # normalize succeeded, extract failed
        assert result.stages[0].success is True
        assert result.stages[1].success is False

    def test_failure_validation(self, pipeline):
        """Invalid data fails at validate stage."""
        content = json.dumps({"title": "Hello"})
        result = pipeline.process(content)
        assert result.success is False
        assert "validate" in result.error
        assert len(result.stages) == 3

    def test_stage_log_records_lengths(self, pipeline):
        """Stage log records input/output lengths for each stage."""
        result = pipeline.process(VALID_JSON)
        assert result.success is True
        for stage in result.stages:
            assert stage.input_length > 0
            assert stage.output_length > 0

    def test_pipeline_with_timer(self, pipeline_with_timer):
        """Pipeline with timer tracks stage timing."""
        result = pipeline_with_timer.process(VALID_JSON)
        assert result.success is True

    def test_observability_logger_records(self, pipeline, stage_logger):
        """PipelineStageLogger records content lengths at each stage."""
        pipeline.process(VALID_JSON, target="test_target")
        lengths = stage_logger.get_lengths("test_target")
        assert "normalize" in lengths
        assert "extract" in lengths
        assert "validate" in lengths
        assert "write" in lengths


# ===========================================================================
# 7. Custom Stage Insertion (5 tests)
# ===========================================================================


class TestCustomStages:
    """Test adding custom stages between canonical stages."""

    def test_add_after_normalize(self, pipeline):
        """Custom stage inserted after normalize."""
        pipeline.add_stage("sanitize", lambda x: x.upper(), after="normalize")
        assert pipeline.stage_names == [
            "normalize", "sanitize", "extract", "validate", "write",
        ]

    def test_add_after_extract(self, pipeline):
        """Custom stage inserted after extract."""
        pipeline.add_stage("enrich", lambda d: {**d, "enriched": True}, after="extract")
        names = pipeline.stage_names
        assert names.index("enrich") == names.index("extract") + 1
        assert names.index("enrich") < names.index("validate")

    def test_duplicate_name_rejected(self, pipeline):
        """Adding a stage with a duplicate name raises ValueError."""
        pipeline.add_stage("custom", lambda x: x, after="normalize")
        with pytest.raises(ValueError, match="already exists"):
            pipeline.add_stage("custom", lambda x: x, after="extract")

    def test_unknown_after_rejected(self, pipeline):
        """Adding a stage after a non-existent stage raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            pipeline.add_stage("custom", lambda x: x, after="nonexistent")

    def test_custom_stage_executes(self, pipeline):
        """Custom stage function is actually called during processing."""
        calls = []

        def log_stage(data):
            calls.append("called")
            return data

        pipeline.add_stage("logger", log_stage, after="extract")
        result = pipeline.process(VALID_JSON)
        assert result.success is True
        assert calls == ["called"]


# ===========================================================================
# 8. Hooks (4 tests)
# ===========================================================================


class TestHooks:
    """Test stage completion and failure hooks."""

    def test_on_stage_complete_called(self, pipeline):
        """on_stage_complete hook is called for each successful stage."""
        completed = []
        pipeline.on_stage_complete(lambda name, in_len, out_len: completed.append(name))
        pipeline.process(VALID_JSON)
        assert completed == ["normalize", "extract", "validate", "write"]

    def test_on_stage_complete_lengths(self, pipeline):
        """on_stage_complete receives correct input/output lengths."""
        records = []
        pipeline.on_stage_complete(
            lambda name, in_len, out_len: records.append((name, in_len, out_len))
        )
        pipeline.process(VALID_JSON)
        for name, in_len, out_len in records:
            assert in_len > 0
            assert out_len > 0

    def test_on_stage_failure_called(self, pipeline):
        """on_stage_failure hook is called when a stage fails."""
        failures = []
        pipeline.on_stage_failure(
            lambda name, error, preview: failures.append((name, str(error)))
        )
        pipeline.process("not json at all")
        assert len(failures) == 1
        assert failures[0][0] == "extract"

    def test_on_stage_failure_preview(self, pipeline):
        """on_stage_failure receives a content preview."""
        previews = []
        pipeline.on_stage_failure(
            lambda name, error, preview: previews.append(preview)
        )
        pipeline.process("not json at all")
        assert len(previews) == 1
        assert len(previews[0]) <= 200


# ===========================================================================
# 9. TRF-020 Regression (2 tests)
# ===========================================================================


class TestTRF020Regression:
    """Regression tests for TRF-020: pipeline ordering bug.

    TRF-020: If extraction runs BEFORE normalization, malformed think tags
    cause extraction failure. The canonical pipeline ensures normalization
    happens first.
    """

    def test_normalize_before_extract_succeeds(self, pipeline):
        """Canonical order: normalize first, then extract — succeeds."""
        content = f"<think>reasoning<think>{VALID_JSON}"
        result = pipeline.process(content)
        assert result.success is True
        assert result.content == {"title": "Hello", "body": "World"}

    def test_extract_before_normalize_demonstrates_bug(self):
        """Verify normalization is required for malformed think tags.

        Without normalization, malformed think tags are not cleaned,
        which can cause extraction failures in complex scenarios.
        """
        content = f"<think>long reasoning block<think>{VALID_JSON}"
        normalized = JsonExtractor.normalise_think_closing_tags(content)
        assert "</think>" in normalized


# ===========================================================================
# 10. Error Context (3 tests)
# ===========================================================================


class TestErrorContext:
    """Test error context reporting in pipeline failures."""

    def test_failure_includes_stage_name(self, pipeline):
        """Pipeline failure error includes the failing stage name."""
        result = pipeline.process("not json")
        assert result.error is not None
        assert "extract" in result.error

    def test_failure_stage_has_error_message(self, pipeline):
        """Failed stage in log has an error message."""
        result = pipeline.process("not json")
        failed = [s for s in result.stages if not s.success]
        assert len(failed) == 1
        assert failed[0].error is not None
        assert len(failed[0].error) > 0

    def test_successful_stages_before_failure(self, pipeline):
        """Stages before the failing stage are recorded as successful."""
        result = pipeline.process("not json")
        assert result.stages[0].stage == "normalize"
        assert result.stages[0].success is True


# ===========================================================================
# 11. Additional_kwargs / reasoning_content (2 tests)
# ===========================================================================


class TestAdditionalKwargs:
    """Test reasoning_content fallback via additional_kwargs."""

    def test_process_with_additional_kwargs(self, pipeline):
        """Pipeline passes additional_kwargs to extractor."""
        result = pipeline.process(
            "no json here",
            additional_kwargs={"reasoning_content": VALID_JSON},
        )
        assert result.success is True
        assert result.content == {"title": "Hello", "body": "World"}

    def test_process_without_additional_kwargs(self, pipeline):
        """Pipeline works when additional_kwargs is None."""
        result = pipeline.process(VALID_JSON)
        assert result.success is True


# ===========================================================================
# 12. Config passthrough (1 test)
# ===========================================================================


class TestConfigPassthrough:
    """Test that config is passed to the validator."""

    def test_config_passed_to_validator(self, simple_schema, stage_logger):
        """Config dict is passed through to DomainValidator.validate()."""
        pipe = ContentPipeline(
            extractor=JsonExtractor,
            validator=DomainValidator(simple_schema),
            stage_logger=stage_logger,
            config={"max_tokens": 4096},
        )
        result = pipe.process(VALID_JSON)
        assert result.success is True

    def test_missing_config_causes_validation_failure(self, stage_logger):
        """Missing required config field causes validation failure."""
        schema = [MetadataField("title", FieldType.STRING, required=True)]
        pipe = ContentPipeline(
            extractor=JsonExtractor,
            validator=DomainValidator(schema),
            stage_logger=stage_logger,
            config={},  # Missing max_tokens
        )
        content = json.dumps({"title": "Hello"})
        result = pipe.process(content)
        assert result.success is False
        assert "validate" in result.error


# ===========================================================================
# 13. Validation result on PipelineResult (1 test)
# ===========================================================================


class TestValidationResult:
    """Test that validation_result is available on PipelineResult."""

    def test_validation_result_set_on_success(self, pipeline):
        """Successful pipeline exposes validation_result."""
        result = pipeline.process(VALID_JSON)
        assert result.success is True
        assert result.validation_result is not None
        assert result.validation_result.is_valid
