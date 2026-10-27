"""Scenario ``verifier:`` stamps — kept as written, and the toolchain linkage.

Card Q8/A.2. Since the cull (27 October 2026, GKT-036 / GKT-041) GuardKit no
longer refuses a plan or a task over a stamp: an unknown home, a bare
``toolchain`` stamp, an unstamped scenario, an ownership map naming no task
of the feature and any ``routing_law:`` value all load. The toolchain
linkage (a ``token_coverage`` rule for the spec-conformance check) went with
that check.

Network-free, subprocess-free: YAML + tmp_path only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
)
from guardkit.orchestrator.verifier_stamp import (
    VERIFIER_HOMES,
    extract_scenario_titles,
    validate_task_verifier,
)

FEATURE_ID = "FEAT-RL01"
TASK_ID = "TASK-RL-001"

GHERKIN = """\
Feature: Sign in

  Background:
    Given the auth service is up

  Scenario: User signs in with valid credentials
    When the user submits valid credentials
    Then a session is created

  Scenario Outline: Rejected credential variants
    When the user submits <variant>
    Then the attempt is refused
    Examples:
      | variant |
      | expired |
      | revoked |
"""

TITLE_A = "User signs in with valid credentials"
TITLE_B = "Rejected credential variants"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_repo_config(repo_root: Path, content: str) -> None:
    cfg = repo_root / ".guardkit" / "config.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(content, encoding="utf-8")


def _write_feature_yaml(repo_root: Path, extra: dict) -> None:
    data = {"id": FEATURE_ID, "name": "Sign in", "tasks": [], **extra}
    fdir = repo_root / ".guardkit" / "features"
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / f"{FEATURE_ID}.yaml").write_text(
        yaml.dump(data, sort_keys=False), encoding="utf-8"
    )


def _write_gherkin(repo_root: Path, rel: str = "features/sign-in.feature") -> str:
    path = repo_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(GHERKIN, encoding="utf-8")
    return rel


def _load(repo_root: Path) -> Feature:
    return FeatureLoader.load_feature(FEATURE_ID, repo_root=repo_root)


# ===========================================================================
# 1. Stamps load as written
# ===========================================================================


class TestStampsLoadAsWritten:
    def _stamped(self) -> dict:
        return {
            TITLE_A: {"verifier": "hurl"},
            TITLE_B: {"verifier": "toolchain", "test_ref": "test_rejected_variants"},
        }

    def test_unknown_verifier_loads_as_written(self, tmp_path: Path) -> None:
        _write_feature_yaml(tmp_path, {"scenarios": {TITLE_A: "cypress"}})
        assert _load(tmp_path).scenarios[TITLE_A].verifier == "cypress"

    def test_bare_string_shorthand_in_map(self, tmp_path: Path) -> None:
        _write_feature_yaml(tmp_path, {"scenarios": {TITLE_A: "hurl"}})
        feature = _load(tmp_path)
        assert feature.scenarios[TITLE_A].verifier == "hurl"

    def test_bare_toolchain_stamp_loads(self, tmp_path: Path) -> None:
        _write_feature_yaml(tmp_path, {"scenarios": {TITLE_A: "toolchain"}})
        stamp = _load(tmp_path).scenarios[TITLE_A]
        assert stamp.verifier == "toolchain"
        assert stamp.test_ref is None

    def test_a_stamp_that_cannot_be_read_is_skipped(self, tmp_path: Path) -> None:
        _write_feature_yaml(
            tmp_path,
            {"scenarios": {TITLE_A: 7, TITLE_B: {"verifier": "hurl", "typo": 1}}},
        )
        feature = _load(tmp_path)
        assert TITLE_A not in feature.scenarios
        assert feature.scenarios[TITLE_B].verifier == "hurl"

    def test_owner_naming_no_task_of_the_feature_loads(self, tmp_path: Path) -> None:
        _write_feature_yaml(
            tmp_path,
            {
                "scenarios": {TITLE_A: {"verifier": "hurl", "owner_task": "TASK-NONE"}},
                "scenario_owners": {TITLE_A: "TASK-NONE"},
            },
        )
        feature = _load(tmp_path)
        assert feature.scenarios[TITLE_A].owner_task == "TASK-NONE"
        assert feature.scenario_owners == {TITLE_A: "TASK-NONE"}

    @pytest.mark.parametrize("raw", ["enforced", "enforce", True, False])
    def test_any_routing_law_value_loads(self, tmp_path: Path, raw) -> None:
        _write_feature_yaml(tmp_path, {"routing_law": raw})
        assert _load(tmp_path).routing_law == raw

    def test_unstamped_scenarios_under_enforced_load(self, tmp_path: Path) -> None:
        _write_repo_config(tmp_path, "routing_law: enforced\n")
        _write_feature_yaml(
            tmp_path,
            {"routing_law": "enforced", "feature_files": ["features/missing.feature"]},
        )
        feature = _load(tmp_path)
        assert feature.scenarios == {}

    def test_save_round_trip_keeps_stamps_and_stays_minimal(
        self, tmp_path: Path
    ) -> None:
        """Stamps survive save→load; a stamp-free feature's YAML never
        sprouts the new keys (missing-key-equals-null law)."""
        rel = _write_gherkin(tmp_path)
        _write_feature_yaml(
            tmp_path,
            {
                "routing_law": "enforced",
                "feature_files": [rel],
                "scenarios": self._stamped(),
            },
        )
        feature = _load(tmp_path)
        FeatureLoader.save_feature(feature, repo_root=tmp_path)
        reloaded = _load(tmp_path)
        assert reloaded.scenarios[TITLE_A].verifier == "hurl"
        assert reloaded.scenarios[TITLE_B].test_ref == "test_rejected_variants"
        # And the persisted stamp is compact — no `test_ref: null` noise.
        raw = (tmp_path / ".guardkit" / "features" / f"{FEATURE_ID}.yaml").read_text()
        assert "test_ref: null" not in raw

        # A stamp-free feature stays stamp-free on disk.
        bare = Feature.model_validate({"id": "FEAT-BARE", "name": "bare"})
        FeatureLoader.save_feature(bare, repo_root=tmp_path)
        bare_raw = (
            tmp_path / ".guardkit" / "features" / "FEAT-BARE.yaml"
        ).read_text()
        for key in ("routing_law", "feature_files", "scenarios"):
            assert key not in bare_raw



class TestTaskFrontmatterStamp:
    def test_absent_stamp_is_none_the_common_case(self) -> None:
        assert validate_task_verifier(TASK_ID, None) is None

    @pytest.mark.parametrize("home", VERIFIER_HOMES)
    def test_stamp_resolves_as_written(self, home: str) -> None:
        assert validate_task_verifier(TASK_ID, home) == home

    def test_unknown_stamp_is_kept(self) -> None:
        assert validate_task_verifier(TASK_ID, " cypress ") == "cypress"

    @pytest.mark.parametrize("bad", ["", "   ", 7, ["hurl"]])
    def test_unusable_stamp_reads_as_none(self, bad) -> None:
        assert validate_task_verifier(TASK_ID, bad) is None


class TestScenarioTitleExtraction:
    def test_outline_alias_and_examples_header(self) -> None:
        text = (
            "Feature: F\n"
            "  Scenario: One\n"
            "  Scenario Outline: Two\n"
            "    Examples:\n"
            "      | a |\n"
            "  Example: Three\n"
            "  Scenario Template: Four\n"
        )
        assert extract_scenario_titles(text) == ["One", "Two", "Three", "Four"]

    def test_examples_table_header_never_titles_a_scenario(self) -> None:
        assert extract_scenario_titles("Examples: not a scenario\n") == []



def test_validate_yaml_accepts_any_routing_law_value():
    for raw in (False, True, "on", "enforce", "off"):
        data = {"id": "FEAT-OFF1", "name": "Off trap", "tasks": [], "routing_law": raw}
        assert FeatureLoader.validate_yaml(data) == [], raw
