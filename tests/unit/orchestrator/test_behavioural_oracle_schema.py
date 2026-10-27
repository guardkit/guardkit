"""TS-lane D.1a — the schema home ``behavioural_oracle`` never had.

Honest NOT-FOUND carried into this lane (design §A.3): *"No schema of any
kind for behavioural_oracle — no Pydantic model, no JSON schema, no
frontmatter validator, no Feature field."* A verdict-bearing declaration
with no schema means a typo is silently ignored and the leg quietly goes
absent — a false green wearing a spelling mistake.

``BehaviouralOracle`` is modelled on :class:`SmokeGates`. Since the cull
(27 October 2026, GKT-035):

  - an unknown key is ignored and the timeout is not range-checked;
  - a non-empty command is still needed to form a declaration;
  - a block the loader cannot read is skipped, and the feature loads
    without it;
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

    @pytest.mark.parametrize("timeout", [0, 1, 300, 3600, 7200])
    def test_any_timeout_is_kept(self, timeout: int) -> None:
        assert BehaviouralOracle(command="x", timeout=timeout).timeout == timeout

    def test_unknown_key_is_ignored(self) -> None:
        oracle = BehaviouralOracle(command="npm test", timeout_seconds=600)
        assert oracle.command == "npm test" and oracle.timeout is None

    def test_extra_ignore_matches_smoke_gates(self) -> None:
        assert (
            BehaviouralOracle.model_config["extra"]
            == SmokeGates.model_config["extra"]
            == "ignore"
        )

    def test_required_declaration_need_not_name_its_checker(self) -> None:
        oracle = BehaviouralOracle(command="npm test", required=True)
        assert oracle.required is True and oracle.checker_sha256 is None


# ---------------------------------------------------------------------------
# 2. A declaration needs a command
# ---------------------------------------------------------------------------


class TestNoCommand:
    def test_missing_command_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle()  # type: ignore[call-arg]

    def test_empty_command_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle(command="")

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

    def test_a_block_without_a_command_is_skipped_at_load(
        self, repo: Path
    ) -> None:
        """A typo'd or missing command leaves nothing to run; the block is
        skipped and the feature loads (the cull, 27 October 2026)."""
        for block in ("behavioural_oracle:\n  commnad: npm test\n",
                      "behavioural_oracle:\n  timeout: 600\n"):
            feature = _load(repo, block)
            assert feature.behavioural_oracle is None

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
