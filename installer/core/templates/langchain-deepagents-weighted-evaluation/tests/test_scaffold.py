"""Smoke tests for the langchain-deepagents-weighted-evaluation template scaffold.

Verifies:
1. Template directory structure is correct
2. SKILL.md contains required metadata
3. manifest.json is valid and declares extension
4. Template variables are documented with defaults
5. All scaffold files exist and are parseable
6. Weighted evaluation dataclasses work correctly
7. Configuration loading produces valid defaults
8. Intensity routing behaves correctly for full/light/solo modes

Coverage Target: >=85%
Test Count: 110+ tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib

import pytest

# Template root relative to this test file
TEMPLATE_ROOT = pathlib.Path(__file__).parent.parent


def _load_module(name: str, file_path: pathlib.Path):
    """Load a Python module from an explicit file path using importlib.

    Uses SourceFileLoader directly to handle non-standard extensions (.j2)
    and to avoid sys.path pollution / module name collisions.

    Registers in sys.modules temporarily so that dataclasses and other
    stdlib machinery can resolve the module during exec_module().
    """
    import sys

    # Use a unique name to avoid collision with real packages
    unique_name = f"_test_scaffold_.{name}"
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


_BASE_LIB_ROOT = (
    TEMPLATE_ROOT.parent / "langchain-deepagents" / "lib"
)


def _preload_base_lib_module(mod_name: str) -> None:
    """Preload a base-template ``lib/<mod_name>.py`` under ``lib.<mod_name>``.

    The weighted-evaluation orchestrator imports ``from lib.session_logging``
    and ``from lib.retry_context`` (TASK-LCL-008). In the rendered project
    those resolve via the user's ``lib/`` package, but in this in-tree test
    environment ``lib`` is not on ``sys.path``. Preloading the real modules
    into ``sys.modules`` lets the scaffold's imports succeed and delegating
    wrappers execute against the canonical implementations from the base
    template (not stubs — that would defeat the behaviour tests below).
    """
    import sys
    import types

    # Ensure a parent ``lib`` package entry exists so ``from lib.x import y``
    # finds ``lib.x`` on the module path.
    if "lib" not in sys.modules:
        pkg = types.ModuleType("lib")
        pkg.__path__ = []
        sys.modules["lib"] = pkg

    full_name = f"lib.{mod_name}"
    if full_name in sys.modules:
        return

    file_path = _BASE_LIB_ROOT / f"{mod_name}.py"
    loader = importlib.machinery.SourceFileLoader(full_name, str(file_path))
    spec = importlib.util.spec_from_file_location(
        full_name, str(file_path), loader=loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(full_name, None)
        raise


def _load_j2_module(name: str, file_path: pathlib.Path):
    """Load a Jinja2 template (.j2) as a Python module after replacing placeholders.

    Replaces {{Placeholder}} template variables with valid Python values
    so the file can be loaded as a standard Python module. Used for
    testing scaffold files that contain Jinja2 template variables.
    """
    import re
    import sys
    import tempfile

    # Preload base-template lib modules that the scaffold imports from. This
    # runs before any stripping below so the scaffold's ``from lib.xxx import``
    # lines remain intact and resolve against the real implementations.
    _preload_base_lib_module("session_logging")
    _preload_base_lib_module("retry_context")

    content = file_path.read_text()

    # Replace Jinja2 template variables with valid Python values
    replacements = {
        "{{ProjectName}}": "_test_project",
        "{{DomainName}}": "test_domain",
        "{{AdversarialIntensity}}": "full",
        "{{AcceptanceThreshold}}": "0.7",
        "{{MaxRetries}}": "3",
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    # Remove any remaining {{ }} Jinja2 syntax (e.g., in f-strings)
    content = re.sub(r"\{\{(\w+)\}\}", r"'\1'", content)

    # Strip import lines that reference the fake project module
    lines = content.splitlines()
    filtered = []
    skip_continuation = False
    # Preserve ``from lib.session_logging`` / ``from lib.retry_context`` —
    # those are TASK-LCL-008 extractions and resolve via _preload_base_lib_module.
    _preserved_lib_modules = ("session_logging", "retry_context")
    for line in lines:
        if skip_continuation:
            if line.strip().endswith(")"):
                skip_continuation = False
            continue
        if "from _test_project." in line:
            if not line.strip().endswith(")"):
                skip_continuation = True
            continue
        if "from lib." in line:
            if any(
                f"from lib.{m}" in line for m in _preserved_lib_modules
            ):
                filtered.append(line)
                continue
            if not line.strip().endswith(")"):
                skip_continuation = True
            continue
        filtered.append(line)

    content = "\n".join(filtered)

    # Add stub imports for types referenced from other modules.
    # Must be inserted AFTER any `from __future__` import line.
    stubs = (
        "\n# Auto-generated stubs for testing\n"
        "class WeightedEvaluationPipeline: pass\n"
        "class WeightedVerdict:\n"
        "    def __init__(self, **kw): pass\n"
        "    @classmethod\n"
        "    def from_json(cls, raw, weights): pass\n"
        "class PipelineResult:\n"
        "    def __init__(self, success=False, content='', verdict=None, "
        "attempts=0, error=None):\n"
        "        self.success = success\n"
        "        self.content = content\n"
        "        self.verdict = verdict\n"
        "        self.attempts = attempts\n"
        "        self.error = error\n"
        "def load_adversarial_config(**kw): return {}\n"
        "def build_weighted_coach_prompt(*a, **kw): return ''\n"
        "PLAYER_SYSTEM_PROMPT = ''\n"
        "def build_player_prompt_with_domain(d): return d\n"
        "def assert_no_system_messages(d): pass\n"
        "class JsonExtractor:\n"
        "    @staticmethod\n"
        "    def extract(c, **kw): return {}\n"
        "class OrchestratorWriteGate:\n"
        "    def __init__(self, **kw): pass\n"
        "def validate_player_tools(t): pass\n"
        "def create_restricted_agent(**kw): return None\n"
    )

    # Insert stubs AFTER `from __future__` imports (which must be first)
    lines_out = content.splitlines()
    insert_idx = 0
    for i, line in enumerate(lines_out):
        if line.strip().startswith("from __future__"):
            insert_idx = i + 1
    lines_out.insert(insert_idx, stubs)
    content = "\n".join(lines_out)

    # Write to a temp file and load
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix=f"_test_{name}_", delete=False,
    ) as f:
        f.write(content)
        tmp_path = f.name

    unique_name = f"_test_scaffold_j2_.{name}"
    loader = importlib.machinery.SourceFileLoader(unique_name, tmp_path)
    spec = importlib.util.spec_from_file_location(
        unique_name, tmp_path, loader=loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(unique_name, None)
        raise
    return module


class TestDirectoryStructure:
    """Verify the template has the correct directory structure."""

    def test_template_root_exists(self):
        assert TEMPLATE_ROOT.is_dir()

    @pytest.mark.parametrize(
        "subdir",
        ["scaffold", "prompts", "hooks", "config", "tests", ".claude"],
    )
    def test_required_directories_exist(self, subdir: str):
        assert (TEMPLATE_ROOT / subdir).is_dir(), f"Missing directory: {subdir}"

    @pytest.mark.parametrize(
        "filepath",
        [
            "SKILL.md",
            "TEMPLATE-NOTES.md",
            "manifest.json",
            ".claude/CLAUDE.md",
            "scaffold/orchestrator.py.j2",
            "scaffold/pipeline.py.j2",
            "scaffold/goal_schema.py.j2",
            "prompts/coach_template.py",
            "prompts/adversarial_base.py",
            "hooks/hitl.py",
            "hooks/sprint_contract.py",
            "config/adversarial_config.py",
            "templates/other/other/.env.example.template",
        ],
    )
    def test_required_files_exist(self, filepath: str):
        assert (TEMPLATE_ROOT / filepath).is_file(), f"Missing file: {filepath}"


class TestSkillMd:
    """Verify SKILL.md contains required metadata."""

    @pytest.fixture
    def skill_content(self) -> str:
        return (TEMPLATE_ROOT / "SKILL.md").read_text()

    def test_has_title(self, skill_content: str):
        assert "Weighted Evaluation" in skill_content

    def test_declares_extends(self, skill_content: str):
        assert "langchain-deepagents" in skill_content

    def test_documents_template_variables(self, skill_content: str):
        required_vars = [
            "project_name",
            "domain_name",
            "adversarial_intensity",
            "evaluation_criteria",
        ]
        for var in required_vars:
            assert var in skill_content, f"Missing template variable: {var}"

    def test_documents_roles(self, skill_content: str):
        for role in ["Orchestrator", "Player", "Coach"]:
            assert role in skill_content, f"Missing role: {role}"

    def test_documents_intensity_modes(self, skill_content: str):
        for mode in ["full", "light", "solo"]:
            assert mode in skill_content, f"Missing intensity mode: {mode}"


class TestManifest:
    """Verify manifest.json is valid and declares extension."""

    @pytest.fixture
    def manifest(self) -> dict:
        content = (TEMPLATE_ROOT / "manifest.json").read_text()
        return json.loads(content)

    def test_valid_json(self):
        content = (TEMPLATE_ROOT / "manifest.json").read_text()
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_declares_extension(self, manifest: dict):
        assert manifest["extends"] == "langchain-deepagents"

    def test_has_required_fields(self, manifest: dict):
        required = [
            "schema_version",
            "name",
            "display_name",
            "description",
            "version",
            "language",
            "frameworks",
            "placeholders",
        ]
        for field in required:
            assert field in manifest, f"Missing manifest field: {field}"

    def test_name_matches_template(self, manifest: dict):
        assert manifest["name"] == "langchain-deepagents-weighted-evaluation"

    def test_has_weighted_evaluation_pattern(self, manifest: dict):
        assert "Weighted Evaluation" in manifest["patterns"]

    def test_requires_base_template(self, manifest: dict):
        assert "template:langchain-deepagents" in manifest["requires"]

    def test_placeholders_include_domain(self, manifest: dict):
        assert "DomainName" in manifest["placeholders"]

    def test_placeholders_include_intensity(self, manifest: dict):
        assert "AdversarialIntensity" in manifest["placeholders"]

    def test_placeholders_include_threshold(self, manifest: dict):
        assert "AcceptanceThreshold" in manifest["placeholders"]


class TestTemplateVariableDefaults:
    """Verify template variables have documented defaults."""

    @pytest.fixture
    def placeholders(self) -> dict:
        content = (TEMPLATE_ROOT / "manifest.json").read_text()
        manifest = json.loads(content)
        return manifest["placeholders"]

    def test_intensity_default(self, placeholders: dict):
        assert placeholders["AdversarialIntensity"]["default_value"] == "full"

    def test_threshold_default(self, placeholders: dict):
        assert placeholders["AcceptanceThreshold"]["default_value"] == "0.7"

    def test_max_retries_default(self, placeholders: dict):
        assert placeholders["MaxRetries"]["default_value"] == "3"

    def test_domain_default(self, placeholders: dict):
        assert placeholders["DomainName"]["default_value"] == "example-domain"


class TestWeightedVerdict:
    """Test the WeightedVerdict dataclass from the pipeline scaffold."""

    @pytest.fixture
    def goal_schema(self):
        """Load goal_schema module from the .j2 file via importlib."""
        return _load_module(
            "goal_schema",
            TEMPLATE_ROOT / "scaffold" / "goal_schema.py.j2",
        )

    def test_criterion_score_creation(self, goal_schema):
        """Import and test EvaluationCriterion from the scaffold."""
        criterion = goal_schema.EvaluationCriterion(
            name="accuracy",
            weight=0.3,
            description="Test criterion",
        )
        assert criterion.name == "accuracy"
        assert criterion.weight == 0.3

    def test_goal_schema_weight_validation(self, goal_schema):
        """Test GoalSchema weight validation."""
        schema = goal_schema.GoalSchema(
            domain_name="test",
            criteria=[
                goal_schema.EvaluationCriterion(name="a", weight=0.5),
                goal_schema.EvaluationCriterion(name="b", weight=0.5),
            ],
        )
        assert schema.validate_weights() is True

        bad_schema = goal_schema.GoalSchema(
            domain_name="test",
            criteria=[
                goal_schema.EvaluationCriterion(name="a", weight=0.5),
                goal_schema.EvaluationCriterion(name="b", weight=0.3),
            ],
        )
        assert bad_schema.validate_weights() is False

    def test_goal_schema_criteria_as_dict(self, goal_schema):
        """Test criteria_as_dict conversion."""
        schema = goal_schema.GoalSchema(
            domain_name="test",
            criteria=[
                goal_schema.EvaluationCriterion(name="accuracy", weight=0.6),
                goal_schema.EvaluationCriterion(name="quality", weight=0.4),
            ],
        )
        result = schema.criteria_as_dict()
        assert result == {"accuracy": 0.6, "quality": 0.4}

    def test_default_criteria_weights_sum_to_one(self, goal_schema):
        """Verify default criteria weights sum to 1.0."""
        total = sum(c.weight for c in goal_schema.DEFAULT_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestAdversarialConfig:
    """Test the adversarial configuration module."""

    @pytest.fixture
    def adv_config(self):
        """Load adversarial_config module via importlib to avoid path collision."""
        return _load_module(
            "adversarial_config",
            TEMPLATE_ROOT / "config" / "adversarial_config.py",
        )

    def test_default_config_loads(self, adv_config):
        """Test that DEFAULT_CONFIG contains required keys."""
        assert "intensity" in adv_config.DEFAULT_CONFIG
        assert "acceptance_threshold" in adv_config.DEFAULT_CONFIG
        assert "max_retries" in adv_config.DEFAULT_CONFIG
        assert "evaluation_criteria" in adv_config.DEFAULT_CONFIG

    def test_default_criteria_weights_valid(self, adv_config):
        """Default criteria weights must sum to 1.0."""
        criteria = adv_config.DEFAULT_CONFIG["evaluation_criteria"]
        total = sum(c["weight"] for c in criteria)
        assert abs(total - 1.0) < 0.01

    def test_intensity_overrides_exist(self, adv_config):
        """Verify intensity overrides for all modes."""
        assert "full" in adv_config.INTENSITY_OVERRIDES
        assert "light" in adv_config.INTENSITY_OVERRIDES
        assert "solo" in adv_config.INTENSITY_OVERRIDES

    def test_solo_mode_auto_accepts(self, adv_config):
        """Solo mode should have acceptance_threshold of 0.0."""
        assert adv_config.INTENSITY_OVERRIDES["solo"]["acceptance_threshold"] == 0.0

    def test_light_mode_disables_hitl(self, adv_config):
        """Light mode should disable HITL."""
        assert adv_config.INTENSITY_OVERRIDES["light"]["hitl"]["enabled"] is False

    def test_env_override_acceptance_threshold(self, adv_config, monkeypatch):
        """ACCEPTANCE_THRESHOLD env var overrides config (and beats intensity bucket)."""
        monkeypatch.setenv("ACCEPTANCE_THRESHOLD", "0.95")
        config = adv_config.load_adversarial_config()
        assert config["acceptance_threshold"] == 0.95

    def test_env_override_intensity_selects_bucket(self, adv_config, monkeypatch):
        """ADVERSARIAL_INTENSITY env var changes intensity AND triggers correct overrides."""
        monkeypatch.setenv("ADVERSARIAL_INTENSITY", "light")
        config = adv_config.load_adversarial_config()
        assert config["intensity"] == "light"
        # light bucket sets max_retries=1
        assert config["max_retries"] == 1

    def test_env_override_max_retries(self, adv_config, monkeypatch):
        """MAX_RETRIES env var overrides config."""
        monkeypatch.setenv("MAX_RETRIES", "7")
        config = adv_config.load_adversarial_config()
        assert config["max_retries"] == 7

    def test_env_threshold_beats_solo_intensity(self, adv_config, monkeypatch):
        """Env ACCEPTANCE_THRESHOLD wins over solo bucket's 0.0 auto-accept."""
        monkeypatch.setenv("ADVERSARIAL_INTENSITY", "solo")
        monkeypatch.setenv("ACCEPTANCE_THRESHOLD", "0.8")
        config = adv_config.load_adversarial_config()
        assert config["intensity"] == "solo"
        assert config["acceptance_threshold"] == 0.8


class TestCoachPrompt:
    """Test the weighted Coach prompt builder."""

    @pytest.fixture
    def coach_mod(self):
        return _load_module(
            "coach_template",
            TEMPLATE_ROOT / "prompts" / "coach_template.py",
        )

    def test_build_weighted_coach_prompt(self, coach_mod):
        """Test that prompt builder produces valid output."""
        criteria = [
            {
                "name": "accuracy",
                "weight": 0.5,
                "description": "Test accuracy",
                "accept_example": "Good",
                "reject_example": "Bad",
            },
            {
                "name": "quality",
                "weight": 0.5,
                "description": "Test quality",
            },
        ]

        prompt = coach_mod.build_weighted_coach_prompt(
            criteria, acceptance_threshold=0.8,
        )

        assert "accuracy" in prompt
        assert "quality" in prompt
        assert "0.8" in prompt
        assert "50%" in prompt

    def test_scepticism_levels(self, coach_mod):
        """Test different scepticism levels in prompt."""
        criteria = [{"name": "test", "weight": 1.0}]

        strict = coach_mod.build_weighted_coach_prompt(criteria, scepticism="strict")
        assert "STRICT" in strict

        lenient = coach_mod.build_weighted_coach_prompt(criteria, scepticism="lenient")
        assert "LENIENT" in lenient


class TestHITLCheckpoint:
    """Test HITL checkpoint trigger logic."""

    @pytest.fixture
    def hitl_mod(self):
        return _load_module("hitl", TEMPLATE_ROOT / "hooks" / "hitl.py")

    def test_borderline_triggers(self, hitl_mod):
        """Borderline scores should trigger checkpoint."""
        hitl = hitl_mod.HITLCheckpoint(enabled=True, borderline_range=0.05)
        assert hitl.should_trigger(
            composite_score=0.72,
            acceptance_threshold=0.7,
            attempt=1,
            max_retries=3,
        )

    def test_exhaustion_triggers(self, hitl_mod):
        """Retry exhaustion should trigger checkpoint."""
        hitl = hitl_mod.HITLCheckpoint(enabled=True)
        assert hitl.should_trigger(
            composite_score=0.5,
            acceptance_threshold=0.7,
            attempt=3,
            max_retries=3,
        )

    def test_disabled_never_triggers(self, hitl_mod):
        """Disabled checkpoint should never trigger."""
        hitl = hitl_mod.HITLCheckpoint(enabled=False)
        assert not hitl.should_trigger(
            composite_score=0.7,
            acceptance_threshold=0.7,
            attempt=3,
            max_retries=3,
        )


class TestSprintNegotiator:
    """Test sprint contract negotiation."""

    @pytest.fixture
    def sprint_mod(self):
        return _load_module(
            "sprint_contract",
            TEMPLATE_ROOT / "hooks" / "sprint_contract.py",
        )

    def test_negotiates_from_weak_criteria(self, sprint_mod):
        """Should create contract focusing on weakest criteria."""
        negotiator = sprint_mod.SprintNegotiator(max_sprints=3)
        contract = negotiator.negotiate(
            criterion_scores={"accuracy": 0.4, "quality": 0.8, "structure": 0.3},
            criteria_weights={"accuracy": 0.4, "quality": 0.3, "structure": 0.3},
            acceptance_threshold=0.7,
        )
        assert contract is not None
        assert "structure" in contract.focus_criteria or "accuracy" in contract.focus_criteria

    def test_returns_none_when_exhausted(self, sprint_mod):
        """Should return None when sprints exhausted."""
        negotiator = sprint_mod.SprintNegotiator(max_sprints=1)
        # Use up the sprint
        negotiator.negotiate(
            criterion_scores={"a": 0.3},
            criteria_weights={"a": 1.0},
            acceptance_threshold=0.7,
        )
        # Should be exhausted
        result = negotiator.negotiate(
            criterion_scores={"a": 0.3},
            criteria_weights={"a": 1.0},
            acceptance_threshold=0.7,
        )
        assert result is None


# ============================================================================
# 8. Intensity Router Tests (TASK-TI-014)
# ============================================================================


class TestIntensityRouter:
    """Test the IntensityRouter from adversarial_config."""

    @pytest.fixture
    def adv_config(self):
        """Load adversarial_config module via importlib."""
        return _load_module(
            "adversarial_config_router",
            TEMPLATE_ROOT / "config" / "adversarial_config.py",
        )

    # --- Configuration defaults ---

    def test_default_config_has_light_sample_rate(self, adv_config):
        """Default config must include light_sample_rate."""
        assert "light_sample_rate" in adv_config.DEFAULT_CONFIG
        assert adv_config.DEFAULT_CONFIG["light_sample_rate"] == 0.33

    def test_default_config_has_solo_bypass_validation(self, adv_config):
        """Default config must include solo_bypass_validation."""
        assert "solo_bypass_validation" in adv_config.DEFAULT_CONFIG
        assert adv_config.DEFAULT_CONFIG["solo_bypass_validation"] is False

    # --- Full mode ---

    def test_full_mode_always_evaluates(self, adv_config):
        """Full mode must always return True from should_evaluate."""
        router = adv_config.IntensityRouter({"intensity": "full"})
        assert router.intensity == adv_config.AdversarialIntensity.FULL
        # Run multiple times — should always be True
        results = [router.should_evaluate() for _ in range(20)]
        assert all(results)

    def test_full_mode_always_validates(self, adv_config):
        """Full mode must always run validation."""
        router = adv_config.IntensityRouter({"intensity": "full"})
        assert router.should_validate() is True

    # --- Light mode ---

    def test_light_mode_samples_at_configured_rate(self, adv_config):
        """Light mode should sample at approximately the configured rate."""
        import random as random_mod

        rng = random_mod.Random(42)  # Deterministic seed
        router = adv_config.IntensityRouter(
            {"intensity": "light", "light_sample_rate": 0.5},
            rng=rng,
        )
        assert router.intensity == adv_config.AdversarialIntensity.LIGHT
        assert router.light_sample_rate == 0.5

        results = [router.should_evaluate() for _ in range(1000)]
        rate = sum(results) / len(results)
        # Should be approximately 0.5 (within 10%)
        assert 0.4 < rate < 0.6

    def test_light_mode_rate_zero_never_evaluates(self, adv_config):
        """Light mode with rate 0 should never evaluate."""
        router = adv_config.IntensityRouter(
            {"intensity": "light", "light_sample_rate": 0.0},
        )
        results = [router.should_evaluate() for _ in range(100)]
        assert not any(results)

    def test_light_mode_rate_one_always_evaluates(self, adv_config):
        """Light mode with rate 1.0 should always evaluate."""
        router = adv_config.IntensityRouter(
            {"intensity": "light", "light_sample_rate": 1.0},
        )
        results = [router.should_evaluate() for _ in range(100)]
        assert all(results)

    def test_light_mode_always_validates(self, adv_config):
        """Light mode must always run validation regardless of sampling."""
        router = adv_config.IntensityRouter({"intensity": "light"})
        assert router.should_validate() is True

    def test_light_mode_default_sample_rate(self, adv_config):
        """Light mode uses default 0.33 sample rate if not specified."""
        router = adv_config.IntensityRouter({"intensity": "light"})
        assert router.light_sample_rate == 0.33

    # --- Solo mode ---

    def test_solo_mode_never_evaluates(self, adv_config):
        """Solo mode must never evaluate via Coach."""
        router = adv_config.IntensityRouter({"intensity": "solo"})
        assert router.intensity == adv_config.AdversarialIntensity.SOLO
        results = [router.should_evaluate() for _ in range(20)]
        assert not any(results)

    def test_solo_mode_validates_by_default(self, adv_config):
        """Solo mode runs validation by default (bypass=False)."""
        router = adv_config.IntensityRouter({"intensity": "solo"})
        assert router.solo_bypass_validation is False
        assert router.should_validate() is True

    def test_solo_mode_bypass_validation(self, adv_config):
        """Solo mode skips validation when bypass is True."""
        router = adv_config.IntensityRouter(
            {"intensity": "solo", "solo_bypass_validation": True},
        )
        assert router.solo_bypass_validation is True
        assert router.should_validate() is False

    # --- Defaults and edge cases ---

    def test_router_defaults_to_full(self, adv_config):
        """Router defaults to full mode when intensity not specified."""
        router = adv_config.IntensityRouter({})
        assert router.intensity == adv_config.AdversarialIntensity.FULL

    def test_router_logs_mode_on_init(self, adv_config, caplog):
        """Router logs the active mode on initialization."""
        import logging

        with caplog.at_level(logging.INFO):
            adv_config.IntensityRouter({"intensity": "light"})
        assert "mode=light" in caplog.text

    def test_load_config_includes_new_fields(self, adv_config):
        """load_adversarial_config includes light_sample_rate and solo_bypass_validation."""
        config = adv_config.load_adversarial_config(
            config_path=pathlib.Path("nonexistent.yaml"),
        )
        assert "light_sample_rate" in config
        assert "solo_bypass_validation" in config

    def test_config_yaml_overrides_sample_rate(self, adv_config, tmp_path):
        """YAML config can override light_sample_rate."""
        yaml_content = "adversarial:\n  light_sample_rate: 0.5\n  intensity: light\n"
        config_file = tmp_path / "agent-config.yaml"
        config_file.write_text(yaml_content)

        config = adv_config.load_adversarial_config(config_path=config_file)
        assert config["light_sample_rate"] == 0.5

    def test_config_yaml_overrides_bypass(self, adv_config, tmp_path):
        """YAML config can override solo_bypass_validation."""
        yaml_content = "adversarial:\n  solo_bypass_validation: true\n  intensity: solo\n"
        config_file = tmp_path / "agent-config.yaml"
        config_file.write_text(yaml_content)

        config = adv_config.load_adversarial_config(config_path=config_file)
        assert config["solo_bypass_validation"] is True

    def test_intensity_transition_no_code_change(self, adv_config, tmp_path):
        """Switching intensity via YAML does not require code changes."""
        for mode in ("full", "light", "solo"):
            yaml_content = f"adversarial:\n  intensity: {mode}\n"
            config_file = tmp_path / "agent-config.yaml"
            config_file.write_text(yaml_content)

            config = adv_config.load_adversarial_config(config_path=config_file)
            router = adv_config.IntensityRouter(config)
            assert router.intensity.value == mode


# ============================================================================
# 9. Mode-Specific Criteria Overrides (Category E fix)
# ============================================================================


class TestModeOverrides:
    """Test mode-specific criteria weight overrides in adversarial_config."""

    @pytest.fixture
    def adv_config(self):
        """Load adversarial_config module via importlib."""
        return _load_module(
            "adversarial_config_mode",
            TEMPLATE_ROOT / "config" / "adversarial_config.py",
        )

    def test_no_mode_returns_base_weights(self, adv_config):
        """Without a mode, base criteria weights are unchanged."""
        config = adv_config.load_adversarial_config(
            config_path=pathlib.Path("nonexistent.yaml"),
        )
        criteria = config["evaluation_criteria"]
        weights = {c["name"]: c["weight"] for c in criteria}
        assert weights["accuracy"] == 0.3
        assert weights["completeness"] == 0.3

    def test_mode_with_no_overrides_returns_base_weights(self, adv_config):
        """A mode with no matching overrides keeps base weights."""
        config = adv_config.load_adversarial_config(
            config_path=pathlib.Path("nonexistent.yaml"),
            mode="nonexistent_mode",
        )
        criteria = config["evaluation_criteria"]
        weights = {c["name"]: c["weight"] for c in criteria}
        assert weights["accuracy"] == 0.3

    def test_mode_overrides_applied(self, adv_config, tmp_path):
        """Mode overrides are applied and weights re-normalized."""
        yaml_content = (
            "adversarial:\n"
            "  intensity: full\n"
            "coach:\n"
            "  mode_overrides:\n"
            "    scope:\n"
            "      accuracy: 0.1\n"
            "      completeness: 0.1\n"
        )
        config_file = tmp_path / "agent-config.yaml"
        config_file.write_text(yaml_content)

        config = adv_config.load_adversarial_config(
            config_path=config_file, mode="scope",
        )
        criteria = config["evaluation_criteria"]
        weights = {c["name"]: c["weight"] for c in criteria}

        # accuracy and completeness should be reduced relative to structure/quality
        assert weights["accuracy"] < 0.3
        assert weights["completeness"] < 0.3
        # Weights should still sum to ~1.0 after re-normalization
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_mode_overrides_renormalize(self, adv_config, tmp_path):
        """Override weights that don't sum to 1.0 are re-normalized."""
        yaml_content = (
            "adversarial:\n"
            "  intensity: full\n"
            "coach:\n"
            "  mode_overrides:\n"
            "    test_mode:\n"
            "      accuracy: 0.5\n"
            "      quality: 0.5\n"
        )
        config_file = tmp_path / "agent-config.yaml"
        config_file.write_text(yaml_content)

        config = adv_config.load_adversarial_config(
            config_path=config_file, mode="test_mode",
        )
        criteria = config["evaluation_criteria"]
        total = sum(c["weight"] for c in criteria)
        assert abs(total - 1.0) < 0.01

    def test_mode_overrides_without_mode_arg_ignored(self, adv_config, tmp_path):
        """mode_overrides in YAML are ignored when mode arg is not passed."""
        yaml_content = (
            "adversarial:\n"
            "  intensity: full\n"
            "coach:\n"
            "  mode_overrides:\n"
            "    scope:\n"
            "      accuracy: 0.01\n"
        )
        config_file = tmp_path / "agent-config.yaml"
        config_file.write_text(yaml_content)

        config = adv_config.load_adversarial_config(config_path=config_file)
        criteria = config["evaluation_criteria"]
        weights = {c["name"]: c["weight"] for c in criteria}
        # Should still have original weight since no mode was passed
        assert weights["accuracy"] == 0.3


# ============================================================================
# 10. Retry Input Builder (Category C fix)
# ============================================================================


class TestRetryInputBuilder:
    """Test _build_retry_input from the orchestrator scaffold."""

    @pytest.fixture
    def orch_mod(self):
        """Load orchestrator module via importlib (with J2 preprocessing)."""
        return _load_j2_module(
            "orchestrator_retry",
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2",
        )

    def test_basic_retry_input(self, orch_mod):
        """Basic retry input contains feedback and previous output."""
        result = orch_mod._build_retry_input(
            "previous content", issues=["issue1", "issue2"],
        )
        content = result["messages"][0]["content"]
        assert "issue1; issue2" in content
        assert "previous content" in content
        assert result["messages"][0]["role"] == "user"

    def test_retry_input_with_context_manifest(self, orch_mod):
        """Context manifest is included in retry input when provided."""
        manifest = "### Document manifest\n- doc1.md\n- doc2.md"
        result = orch_mod._build_retry_input(
            "previous content",
            issues=["bad quality"],
            context_manifest=manifest,
        )
        content = result["messages"][0]["content"]
        assert "doc1.md" in content
        assert "doc2.md" in content
        assert "Available Context" in content

    def test_retry_input_without_context_manifest(self, orch_mod):
        """Without context_manifest, retry input omits context section."""
        result = orch_mod._build_retry_input(
            "previous content", issues=["bad quality"],
        )
        content = result["messages"][0]["content"]
        assert "Available Context" not in content


# ============================================================================
# 11. Context Manifest Builder
# ============================================================================


class TestContextManifestBuilder:
    """Test _build_context_manifest from the orchestrator scaffold."""

    @pytest.fixture
    def orch_mod(self):
        return _load_j2_module(
            "orchestrator_manifest",
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2",
        )

    def test_manifest_from_files_list(self, orch_mod):
        """Manifest built from target['files'] list."""
        target = {"files": ["doc1.md", "doc2.md", "doc3.md"]}
        manifest = orch_mod._build_context_manifest(target, "some context")
        assert "doc1.md" in manifest
        assert "doc2.md" in manifest
        assert "doc3.md" in manifest

    def test_manifest_from_documents_list(self, orch_mod):
        """Manifest built from target['documents'] list."""
        target = {"documents": [{"name": "report.pdf"}]}
        manifest = orch_mod._build_context_manifest(target, "some context")
        assert "report.pdf" in manifest

    def test_manifest_includes_scope(self, orch_mod):
        """Scope from target is included in manifest."""
        target = {"scope": "Only cover European markets"}
        manifest = orch_mod._build_context_manifest(target, "context")
        assert "European markets" in manifest

    def test_manifest_fallback_to_context_length(self, orch_mod):
        """Without files or scope, manifest reports context size."""
        target = {"id": "test-1"}
        context = "line1\nline2\nline3"
        manifest = orch_mod._build_context_manifest(target, context)
        assert "3 lines" in manifest

    def test_manifest_empty_context(self, orch_mod):
        """Empty context and no metadata produces empty manifest."""
        target = {}
        manifest = orch_mod._build_context_manifest(target, "")
        assert manifest == ""


# ============================================================================
# 12. CLI Args and Logging Configuration
# ============================================================================


class TestLoggingConfig:
    """Test _configure_logging from the orchestrator scaffold."""

    @pytest.fixture
    def orch_mod(self):
        return _load_j2_module(
            "orchestrator_logging",
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2",
        )

    def test_configure_logging_debug(self, orch_mod):
        """Debug flag configures DEBUG level."""
        import logging

        orch_mod._configure_logging(debug=True)
        assert logging.getLogger().level == logging.DEBUG

    def test_configure_logging_verbose(self, orch_mod):
        """Verbose flag configures INFO level."""
        import logging

        orch_mod._configure_logging(verbose=True)
        assert logging.getLogger().level == logging.INFO

    def test_configure_logging_default(self, orch_mod):
        """Neither flag leaves logging unconfigured (no error)."""
        # Should not raise
        orch_mod._configure_logging()


# ============================================================================
# 13. Session Log Writer
# ============================================================================


class TestSessionLogWriter:
    """Test _write_session_log from the orchestrator scaffold."""

    @pytest.fixture
    def orch_mod(self):
        return _load_j2_module(
            "orchestrator_session",
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2",
        )

    def test_writes_log_on_success(self, orch_mod, tmp_path):
        """Session log is written for successful results."""
        import json

        result = orch_mod.PipelineResult(
            success=True, content='{"test": true}', attempts=1,
        )
        log_dir = str(tmp_path / "logs")
        orch_mod._write_session_log("target-1", result, log_dir=log_dir)

        logs = list((tmp_path / "logs").glob("target-1_*.json"))
        assert len(logs) == 1
        data = json.loads(logs[0].read_text())
        assert data["success"] is True
        assert data["target_id"] == "target-1"

    def test_writes_log_on_failure(self, orch_mod, tmp_path):
        """Session log is written for failed results — the key fix."""
        import json

        result = orch_mod.PipelineResult(
            success=False, attempts=3, error="Exhausted 3 retries",
        )
        log_dir = str(tmp_path / "logs")
        orch_mod._write_session_log("target-fail", result, log_dir=log_dir)

        logs = list((tmp_path / "logs").glob("target-fail_*.json"))
        assert len(logs) == 1
        data = json.loads(logs[0].read_text())
        assert data["success"] is False
        assert data["error"] == "Exhausted 3 retries"


# ============================================================================
# 14. Player Prompt Guideline (Category C fix)
# ============================================================================


class TestPlayerPromptGuideline:
    """Verify Player prompt includes the Coach-separation guideline."""

    @pytest.fixture
    def prompt_mod(self):
        return _load_module(
            "adversarial_base_guideline",
            TEMPLATE_ROOT / "prompts" / "adversarial_base.py",
        )

    def test_module_docstring_has_guideline(self, prompt_mod):
        """Module docstring includes the template guideline."""
        assert "Do not duplicate enforcement rules" in prompt_mod.__doc__

    def test_player_prompt_unchanged(self, prompt_mod):
        """Player prompt itself is unchanged (guideline is meta, not in prompt)."""
        assert "Player agent" in prompt_mod.PLAYER_SYSTEM_PROMPT
        assert "search_data" in prompt_mod.PLAYER_SYSTEM_PROMPT


# ============================================================================
# 15. TEMPLATE-NOTES.md Exists
# ============================================================================


class TestTemplateNotes:
    """Verify TEMPLATE-NOTES.md exists with prompt-schema contract docs."""

    def test_file_exists(self):
        assert (TEMPLATE_ROOT / "TEMPLATE-NOTES.md").is_file()

    def test_documents_prompt_schema_contract(self):
        content = (TEMPLATE_ROOT / "TEMPLATE-NOTES.md").read_text()
        assert "Prompt-Schema Contract" in content
        assert "Pydantic" in content
        assert "WeightedVerdict" in content

    def test_documents_enum_alignment(self):
        content = (TEMPLATE_ROOT / "TEMPLATE-NOTES.md").read_text()
        assert "Enum" in content or "enum" in content
        assert "prompt" in content.lower()
