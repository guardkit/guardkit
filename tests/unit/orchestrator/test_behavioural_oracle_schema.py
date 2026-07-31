"""TS-lane D.1a — the schema home ``behavioural_oracle`` never had.

Honest NOT-FOUND carried into this lane (design §A.3): *"No schema of any
kind for behavioural_oracle — no Pydantic model, no JSON schema, no
frontmatter validator, no Feature field."* A verdict-bearing declaration
with no schema means a typo is silently ignored and the leg quietly goes
absent — a false green wearing a spelling mistake.

``BehaviouralOracle`` is modelled on :class:`SmokeGates`, which sits three
lines above it in the same module, and these tests hold it to the same
posture:

  - ``extra="forbid"`` — an unknown key is LOUD;
  - a non-empty command is mandatory;
  - the timeout is bounded;
  - the loader raises ``SchemaValidationError`` on a malformed block,
    before ``/feature-build`` starts, never at Wave-1 o'clock;
  - and the absence path (no key at all) yields ``None``, exactly as
    before the field existed.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from guardkit.orchestrator.feature_loader import (
    BehaviouralOracle,
    Feature,
    FeatureLoader,
    SchemaValidationError,
    SmokeGates,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _feature_body(extra_block: str = "") -> str:
    body = dedent(
        """\
        id: FEAT-TSD1A
        name: TS-lane D.1a fixture
        description: behavioural_oracle schema fixture.
        created: 2026-07-31T12:00:00Z
        complexity: 3
        estimated_tasks: 1
        tasks:
          - id: TASK-TSD1A-T1
            file_path: tasks/in_progress/TASK-TSD1A-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-TSD1A-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )
    return body + extra_block


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".guardkit" / "features").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    return tmp_path


def _load(repo: Path, extra_block: str = "") -> Feature:
    path = repo / ".guardkit" / "features" / "FEAT-TSD1A.yaml"
    path.write_text(_feature_body(extra_block))
    return FeatureLoader.load_feature("FEAT-TSD1A", repo_root=repo)


# ---------------------------------------------------------------------------
# 1. The model itself — good shapes
# ---------------------------------------------------------------------------


class TestGoodShapes:
    def test_minimal_declaration(self) -> None:
        oracle = BehaviouralOracle(command="npm test")
        assert oracle.command == "npm test"
        # LAW §B.4 default: the exit code is the verdict, and 0 means pass.
        assert oracle.expected_exit == 0
        # None -> the executor keeps its historical GUARDKIT_ORACLE_TIMEOUT
        # behaviour, so the absence path is unchanged.
        assert oracle.timeout is None

    def test_full_declaration(self) -> None:
        oracle = BehaviouralOracle(
            command="npm test", expected_exit=3, timeout=600
        )
        assert (oracle.command, oracle.expected_exit, oracle.timeout) == (
            "npm test",
            3,
            600,
        )

    @pytest.mark.parametrize("timeout", [1, 300, 3600])
    def test_timeout_bounds_accept_the_edges(self, timeout: int) -> None:
        assert BehaviouralOracle(command="x", timeout=timeout).timeout == timeout


# ---------------------------------------------------------------------------
# 2. The model itself — bad shapes are LOUD
# ---------------------------------------------------------------------------


class TestBadShapes:
    def test_unknown_key_is_rejected(self) -> None:
        """extra="forbid" posture, matching SmokeGates exactly.

        A silently-ignored ``timeout_seconds:`` typo would leave the oracle
        running on the 300s default while the author believed otherwise.
        """
        with pytest.raises(ValidationError) as exc:
            BehaviouralOracle(command="npm test", timeout_seconds=600)
        assert "timeout_seconds" in str(exc.value)

    def test_extra_forbid_matches_smoke_gates(self) -> None:
        """The posture is copied, not merely similar."""
        assert (
            BehaviouralOracle.model_config["extra"]
            == SmokeGates.model_config["extra"]
            == "forbid"
        )

    def test_missing_command_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle()  # type: ignore[call-arg]

    def test_empty_command_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle(command="")

    @pytest.mark.parametrize("timeout", [0, -1, 3601])
    def test_out_of_bounds_timeout_is_rejected(self, timeout: int) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle(command="npm test", timeout=timeout)

    def test_non_string_command_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle(command=["npm", "test"])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. The Feature field and its loader validation
# ---------------------------------------------------------------------------


class TestFeatureField:
    def test_absent_block_yields_none(self, repo: Path) -> None:
        """THE ABSENCE PIN: no key -> None, byte-identical to pre-D.1a."""
        feature = _load(repo)
        assert feature.behavioural_oracle is None

    def test_mapping_block_is_parsed(self, repo: Path) -> None:
        feature = _load(
            repo,
            dedent(
                """\
                behavioural_oracle:
                  command: npm test
                  timeout: 600
                """
            ),
        )
        assert isinstance(feature.behavioural_oracle, BehaviouralOracle)
        assert feature.behavioural_oracle.command == "npm test"
        assert feature.behavioural_oracle.timeout == 600

    def test_string_shortcut_is_parsed(self, repo: Path) -> None:
        """Parity with CoachValidator._extract_command's string shortcut."""
        feature = _load(repo, 'behavioural_oracle: "npm test"\n')
        assert isinstance(feature.behavioural_oracle, BehaviouralOracle)
        assert feature.behavioural_oracle.command == "npm test"

    def test_typo_raises_schema_validation_error_at_load(
        self, repo: Path
    ) -> None:
        """Loud at load time — the same seam smoke_gates uses, so the
        author learns before the worktree bootstraps, not after Wave 1."""
        with pytest.raises(SchemaValidationError) as exc:
            _load(
                repo,
                dedent(
                    """\
                    behavioural_oracle:
                      commnad: npm test
                    """
                ),
            )
        assert "behavioural_oracle" in str(exc.value)

    def test_missing_command_raises_at_load(self, repo: Path) -> None:
        with pytest.raises(SchemaValidationError):
            _load(
                repo,
                dedent(
                    """\
                    behavioural_oracle:
                      timeout: 600
                    """
                ),
            )

    def test_declaration_is_not_silently_dropped(self, repo: Path) -> None:
        """Regression pin against the evidence_repos class of bug
        (TASK-FIX-XREPO-CAUD): ``Feature`` is ``extra="ignore"``, so a field
        that is not explicitly threaded into ``Feature.model_validate``
        vanishes without a word."""
        feature = _load(repo, 'behavioural_oracle: {command: "npm test"}\n')
        assert feature.behavioural_oracle is not None

    def test_feature_model_default_is_none(self) -> None:
        """Constructing a Feature without the field keeps the leg absent."""
        feature = Feature(id="FEAT-X", name="x")
        assert feature.behavioural_oracle is None


# ---------------------------------------------------------------------------
# 4. The model is readable by the executor's extractor
# ---------------------------------------------------------------------------


class TestModelIsExecutorReadable:
    def test_extract_command_reads_the_model(self) -> None:
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        validator = CoachValidator(worktree_path=Path("/tmp"))
        task: Dict[str, Any] = {
            "behavioural_oracle": BehaviouralOracle(command="npm test")
        }
        assert validator._extract_command(task) == "npm test"

    def test_declaration_normalises_to_a_plain_dict(self) -> None:
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        declaration = CoachValidator._oracle_declaration(
            {
                "behavioural_oracle": BehaviouralOracle(
                    command="npm test", expected_exit=2, timeout=42
                )
            }
        )
        assert declaration == {
            "command": "npm test",
            "expected_exit": 2,
            "timeout": 42,
        }


def test_save_never_persists_behavioural_oracle_null():
    """Coordinator-cure pin (D.1a coach): an unset declaration must not write
    ``behavioural_oracle: null`` into every rewritten feature file — mirror of
    the smoke_gates pop."""
    from guardkit.orchestrator.feature_loader import Feature, FeatureLoader

    data = FeatureLoader._feature_to_dict(Feature(id="FEAT-X", name="x"))
    assert "behavioural_oracle" not in data
