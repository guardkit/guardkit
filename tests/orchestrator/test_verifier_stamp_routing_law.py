"""THE ROUTING LAW's stamp — schema, plan-load enforcement, toolchain linkage.

Card Q8/A.2 (ruled 2026-08-14): every approved scenario carries a
``verifier:`` stamp from a closed vocabulary; an unstamped scenario fails the
plan load — but only when a repo/feature has OPTED IN (``routing_law:
enforced``), so no existing repo breaks the day this ships.

Three walls pinned here, one per Wave-2 deliverable:

1. **SCHEMA is loud, flag or no flag** — an unknown ``verifier:`` value is a
   load ERROR with the full closed vocabulary in the message, never a silent
   fallback (the ``component:``-selector precedent, verbatim).
2. **ENFORCEMENT is opt-in and real** — with the flag on, the scenario
   universe comes from the declared Gherkin files and every title must be
   stamped; with the flag absent, behaviour is byte-equivalent to before the
   law existed.
3. **The toolchain LINKAGE rides the live conformance machinery** — a task
   stamped ``verifier: toolchain`` + ``test_ref`` gets a synthesized
   ``token_coverage`` rule inside the existing pre-turn-1 snapshot, and the
   existing executor fails the build when the named token is absent. Wire,
   not rebuild: no new executor is tested here because none was written.

Network-free, subprocess-free: YAML + tmp_path only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureParseError,
    FeatureValidationError,
)
from guardkit.orchestrator.quality_gates.spec_conformance import (
    TokenCoverageRule,
    evaluate_from_snapshot,
    parse_conformance_block,
    snapshot_paths,
    snapshot_task_conformance,
)
from guardkit.orchestrator.verifier_stamp import (
    DEFAULT_TEST_REF_PATHS,
    TEST_REF_RULE_ID,
    VERIFIER_HOMES,
    ScenarioStamp,
    build_rule_from_frontmatter,
    build_token_coverage_rule,
    extract_scenario_titles,
    load_repo_routing_law,
    parse_scenario_stamp,
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


def _write_task_file(repo_root: Path, task_id: str, frontmatter_yaml: str) -> Path:
    task_dir = repo_root / "tasks" / "backlog"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.md"
    task_file.write_text(f"---\n{frontmatter_yaml}---\n\n# {task_id}\n\nBody.\n")
    return task_file


def _worktree_shaped(repo_root: Path, task_id: str) -> Path:
    wt = repo_root / ".guardkit" / "worktrees" / task_id
    wt.mkdir(parents=True, exist_ok=True)
    return wt


# ===========================================================================
# 1. SCHEMA — the closed vocabulary is loud, flag or no flag
# ===========================================================================


class TestStampSchema:
    @pytest.mark.parametrize("home", VERIFIER_HOMES)
    def test_every_closed_list_home_is_accepted(self, home: str) -> None:
        assert parse_scenario_stamp(home).verifier == home
        assert parse_scenario_stamp({"verifier": home}).verifier == home

    def test_unknown_verifier_is_a_loud_error_naming_the_vocabulary(self) -> None:
        with pytest.raises(ValueError) as exc:
            parse_scenario_stamp({"verifier": "cypress"}, scenario=TITLE_A)
        msg = str(exc.value)
        for home in VERIFIER_HOMES:
            assert home in msg
        assert TITLE_A in msg  # names the scenario so one edit fixes it

    def test_unknown_stamp_key_is_rejected(self) -> None:
        """extra="forbid": a typo'd key is loud, never silently ignored."""
        with pytest.raises(ValueError):
            parse_scenario_stamp({"verifier": "hurl", "twin": "x.hurl"})

    def test_non_string_non_mapping_stamp_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_scenario_stamp(7)

    def test_test_paths_must_be_non_empty_strings(self) -> None:
        with pytest.raises(ValueError):
            parse_scenario_stamp({"verifier": "toolchain", "test_paths": []})
        with pytest.raises(ValueError):
            parse_scenario_stamp({"verifier": "toolchain", "test_paths": [""]})


class TestTaskFrontmatterStamp:
    def test_absent_stamp_is_none_the_common_case(self) -> None:
        assert validate_task_verifier(TASK_ID, None) is None

    @pytest.mark.parametrize("home", VERIFIER_HOMES)
    def test_valid_stamp_resolves(self, home: str) -> None:
        assert validate_task_verifier(TASK_ID, home) == home

    def test_unknown_stamp_fails_the_task_load_loudly(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_task_verifier(TASK_ID, "cypress")
        msg = str(exc.value)
        assert TASK_ID in msg
        for home in VERIFIER_HOMES:
            assert home in msg

    @pytest.mark.parametrize("bad", ["", "   ", 7, ["hurl"]])
    def test_malformed_stamp_fails_the_task_load(self, bad) -> None:
        with pytest.raises(ValueError):
            validate_task_verifier(TASK_ID, bad)

    def test_orchestrator_seam_mirrors_the_component_selector(self) -> None:
        """_resolve_task_verifier: loud on unknown, None on absent — no
        fallback, exactly like _resolve_task_component directly above it."""
        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        assert orch._resolve_task_verifier(TASK_ID, None) is None
        assert orch._resolve_task_verifier(TASK_ID, "exam") == "exam"
        with pytest.raises(ValueError):
            orch._resolve_task_verifier(TASK_ID, "cypress")


class TestFeatureMapSchema:
    def test_unknown_verifier_in_map_rejected_without_any_flag(
        self, tmp_path: Path
    ) -> None:
        """The SCHEMA is validated whenever present — the opt-in flag only
        governs ABSENT stamps, never unknown values."""
        _write_feature_yaml(tmp_path, {"scenarios": {TITLE_A: "cypress"}})
        with pytest.raises(FeatureParseError) as exc:
            _load(tmp_path)
        assert "toolchain" in str(exc.value)  # vocabulary named in the reject

    def test_bare_string_shorthand_in_map(self, tmp_path: Path) -> None:
        _write_feature_yaml(tmp_path, {"scenarios": {TITLE_A: "hurl"}})
        feature = _load(tmp_path)
        assert feature.scenarios[TITLE_A].verifier == "hurl"

    def test_bad_feature_level_flag_value_is_loud(self, tmp_path: Path) -> None:
        _write_feature_yaml(tmp_path, {"routing_law": "enforce"})
        with pytest.raises(FeatureParseError):
            _load(tmp_path)


# ===========================================================================
# 2. VALIDATION — opt-in enforcement at plan load
# ===========================================================================


class TestRoutingLawEnforcement:
    def _stamped(self) -> dict:
        return {
            TITLE_A: {"verifier": "hurl"},
            TITLE_B: {"verifier": "toolchain", "test_ref": "test_rejected_variants"},
        }

    def test_no_flag_anywhere_means_no_enforcement(self, tmp_path: Path) -> None:
        """Byte-equivalent opt-in: unstamped scenarios load exactly as before
        the law existed when neither the repo nor the feature flips the flag."""
        rel = _write_gherkin(tmp_path)
        _write_feature_yaml(tmp_path, {"feature_files": [rel]})
        feature = _load(tmp_path)
        assert feature.scenarios == {}

    def test_enforced_and_fully_stamped_loads(self, tmp_path: Path) -> None:
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
        assert feature.routing_law == "enforced"
        assert feature.scenarios[TITLE_B].test_ref == "test_rejected_variants"

    def test_enforced_rejects_an_unstamped_scenario_by_name(
        self, tmp_path: Path
    ) -> None:
        rel = _write_gherkin(tmp_path)
        _write_feature_yaml(
            tmp_path,
            {
                "routing_law": "enforced",
                "feature_files": [rel],
                "scenarios": {TITLE_A: {"verifier": "hurl"}},  # TITLE_B unstamped
            },
        )
        with pytest.raises(FeatureValidationError) as exc:
            _load(tmp_path)
        msg = str(exc.value)
        assert "ROUTING LAW" in msg
        assert TITLE_B in msg  # the unstamped scenario is named
        assert TITLE_A not in msg.split("Unstamped:")[1]  # stamped one is not

    def test_enforced_requires_a_declared_scenario_universe(
        self, tmp_path: Path
    ) -> None:
        """Enforcement with no feature_files is a promise, not a law —
        rejected."""
        _write_feature_yaml(
            tmp_path,
            {"routing_law": "enforced", "scenarios": self._stamped()},
        )
        with pytest.raises(FeatureValidationError) as exc:
            _load(tmp_path)
        assert "feature_files" in str(exc.value)

    def test_enforced_rejects_a_missing_feature_file(self, tmp_path: Path) -> None:
        _write_feature_yaml(
            tmp_path,
            {
                "routing_law": "enforced",
                "feature_files": ["features/gone.feature"],
                "scenarios": self._stamped(),
            },
        )
        with pytest.raises(FeatureValidationError) as exc:
            _load(tmp_path)
        assert "features/gone.feature" in str(exc.value)

    def test_repo_flag_flips_enforcement_for_a_flagless_feature(
        self, tmp_path: Path
    ) -> None:
        """The per-repo flag in .guardkit/config.yaml — the api_test path."""
        _write_repo_config(tmp_path, "routing_law: enforced\n")
        rel = _write_gherkin(tmp_path)
        _write_feature_yaml(tmp_path, {"feature_files": [rel]})  # no stamps
        with pytest.raises(FeatureValidationError):
            _load(tmp_path)

    def test_feature_off_overrides_repo_enforced(self, tmp_path: Path) -> None:
        """The per-feature escape hatch: a flipped repo can still load a
        historical, pre-law feature marked routing_law: off."""
        _write_repo_config(tmp_path, "routing_law: enforced\n")
        rel = _write_gherkin(tmp_path)
        _write_feature_yaml(
            tmp_path, {"routing_law": "off", "feature_files": [rel]}
        )
        feature = _load(tmp_path)
        assert feature.routing_law == "off"

    def test_bad_repo_flag_value_is_loud_never_silently_off(
        self, tmp_path: Path
    ) -> None:
        """`routing_law: enforce` (typo) must never silently mean off."""
        _write_repo_config(tmp_path, "routing_law: enforce\n")
        _write_feature_yaml(tmp_path, {})
        with pytest.raises(FeatureValidationError) as exc:
            _load(tmp_path)
        assert "routing_law" in str(exc.value)

    def test_stale_stamp_warns_never_rejects(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        rel = _write_gherkin(tmp_path)
        stamps = self._stamped()
        stamps["A scenario that was renamed"] = {"verifier": "operator"}
        _write_feature_yaml(
            tmp_path,
            {
                "routing_law": "enforced",
                "feature_files": [rel],
                "scenarios": stamps,
            },
        )
        with caplog.at_level(logging.WARNING, "guardkit.orchestrator.feature_loader"):
            feature = _load(tmp_path)
        assert feature.id == FEATURE_ID
        assert any("stale" in r.message.lower() for r in caplog.records)

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


class TestRepoFlagReader:
    def test_absent_file_and_absent_key_mean_none(self, tmp_path: Path) -> None:
        assert load_repo_routing_law(tmp_path) is None
        _write_repo_config(tmp_path, "qa:\n  enforce_tier1: true\n")
        assert load_repo_routing_law(tmp_path) is None

    @pytest.mark.parametrize("value", ["enforced", "off"])
    def test_declared_values_read_back(self, tmp_path: Path, value: str) -> None:
        _write_repo_config(tmp_path, f"routing_law: {value}\n")
        assert load_repo_routing_law(tmp_path) == value

    def test_bad_value_raises(self, tmp_path: Path) -> None:
        _write_repo_config(tmp_path, "routing_law: yes please\n")
        with pytest.raises(ValueError):
            load_repo_routing_law(tmp_path)

    def test_yaml_boolean_true_is_loud_with_the_fix_named(
        self, tmp_path: Path
    ) -> None:
        """`routing_law: on` / `true` — YAML 1.1 booleans are never guessed
        into a law value; the error names `enforced` as the fix."""
        _write_repo_config(tmp_path, "routing_law: on\n")
        with pytest.raises(ValueError) as exc:
            load_repo_routing_law(tmp_path)
        assert "enforced" in str(exc.value)

    def test_unquoted_off_at_feature_level_loads(self, tmp_path: Path) -> None:
        """Hand-written `routing_law: off` (unquoted → YAML False) must load
        as the documented `off` value, feature-level too."""
        _write_repo_config(tmp_path, "routing_law: enforced\n")
        fdir = tmp_path / ".guardkit" / "features"
        fdir.mkdir(parents=True, exist_ok=True)
        (fdir / f"{FEATURE_ID}.yaml").write_text(
            f"id: {FEATURE_ID}\nname: Sign in\ntasks: []\nrouting_law: off\n",
            encoding="utf-8",
        )
        assert _load(tmp_path).routing_law == "off"


# ===========================================================================
# 3. LINKAGE — verifier: toolchain + test_ref rides the live conformance gate
# ===========================================================================


class TestTokenCoverageRuleBuilder:
    def test_rule_built_only_for_toolchain_with_test_ref(self) -> None:
        assert build_token_coverage_rule("toolchain", None) is None
        assert build_token_coverage_rule("hurl", "test_x") is None
        assert build_token_coverage_rule(None, "test_x") is None
        rule = build_token_coverage_rule("toolchain", "test_x")
        assert rule == {
            "id": TEST_REF_RULE_ID,
            "type": "token_coverage",
            "paths": list(DEFAULT_TEST_REF_PATHS),
            "require_tokens": ["test_x"],
        }

    def test_rule_validates_against_the_live_conformance_schema(self) -> None:
        """Wire, don't rebuild: the emitted dict IS a TokenCoverageRule under
        spec_conformance's own parser — no second executor exists."""
        rule = build_token_coverage_rule(
            "toolchain", "test_x", ["app/test/**/*"]
        )
        block = parse_conformance_block({"rules": [rule]})
        assert isinstance(block.rules[0], TokenCoverageRule)
        assert block.rules[0].require_tokens == ["test_x"]
        assert block.rules[0].paths == ["app/test/**/*"]

    def test_frontmatter_wrapper_warns_on_unconsumed_test_ref(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, "guardkit.orchestrator.verifier_stamp"):
            rule = build_rule_from_frontmatter(
                {"verifier": "hurl", "test_ref": "test_x"}, task_id=TASK_ID
            )
        assert rule is None
        assert any("NOT CONSUMED" in r.message for r in caplog.records)

    def test_frontmatter_wrapper_never_raises_on_garbage(self) -> None:
        assert build_rule_from_frontmatter({"verifier": 7, "test_ref": 9}) is None
        assert (
            build_rule_from_frontmatter(
                {"verifier": "toolchain", "test_ref": "t", "test_paths": "no"}
            )
            is not None  # bad test_paths degrades to the default, with a warning
        )


class TestSnapshotWiring:
    def test_stamped_task_without_declared_block_gets_the_rule(
        self, tmp_path: Path
    ) -> None:
        """The end-to-end linkage: stamp → synthesized rule → pre-turn-1
        snapshot → the LIVE executor fails while the named test token is
        absent and passes once it exists."""
        _write_task_file(
            tmp_path,
            TASK_ID,
            "task_type: FEATURE\n"
            "verifier: toolchain\n"
            "test_ref: test_rejected_variants\n",
        )
        wt = _worktree_shaped(tmp_path, TASK_ID)

        snap = snapshot_task_conformance(TASK_ID, wt, tmp_path)
        assert snap is not None
        # Pinned OUTSIDE the shared worktree, like every conformance snapshot.
        assert ".guardkit/worktrees" not in str(snap)

        # Token absent from the worktree ⇒ the named test has vanished ⇒ fail.
        result = evaluate_from_snapshot(snap, wt)
        assert result["status"] == "failed"
        assert result["failures"][0]["rule_id"] == TEST_REF_RULE_ID
        assert "test_rejected_variants" in result["failures"][0]["detail"]

        # Author the named test ⇒ pass.
        (wt / "tests").mkdir(parents=True)
        (wt / "tests" / "test_signin.py").write_text(
            "def test_rejected_variants():\n    assert True\n"
        )
        assert evaluate_from_snapshot(snap, wt)["status"] == "passed"

    def test_stamped_task_with_declared_block_gets_both(
        self, tmp_path: Path
    ) -> None:
        _write_task_file(
            tmp_path,
            TASK_ID,
            "task_type: FEATURE\n"
            "verifier: toolchain\n"
            "test_ref: test_rejected_variants\n"
            "conformance:\n"
            "  rules:\n"
            "    - id: R-DECLARED\n"
            "      type: token_coverage\n"
            "      paths: ['src/**/*']\n"
            "      require_tokens: ['declared_token']\n",
        )
        wt = _worktree_shaped(tmp_path, TASK_ID)
        snap = snapshot_task_conformance(TASK_ID, wt, tmp_path)
        assert snap is not None
        result = evaluate_from_snapshot(snap, wt)
        assert result["status"] == "failed"
        assert {f["rule_id"] for f in result["failures"]} == {
            "R-DECLARED",
            TEST_REF_RULE_ID,
        }

    def test_stamp_without_test_ref_stays_a_no_op(self, tmp_path: Path) -> None:
        """A toolchain stamp with no test_ref synthesizes nothing — and a
        stampless, blockless task remains the byte-equivalent no-op."""
        _write_task_file(
            tmp_path, TASK_ID, "task_type: FEATURE\nverifier: toolchain\n"
        )
        wt = _worktree_shaped(tmp_path, TASK_ID)
        assert snapshot_task_conformance(TASK_ID, wt, tmp_path) is None
        assert not snapshot_paths(TASK_ID, wt)["dir"].exists()

    def test_custom_test_paths_are_honoured(self, tmp_path: Path) -> None:
        _write_task_file(
            tmp_path,
            TASK_ID,
            "task_type: FEATURE\n"
            "verifier: toolchain\n"
            "test_ref: widgetSignInFlow\n"
            "test_paths: ['app/test/**/*']\n",
        )
        wt = _worktree_shaped(tmp_path, TASK_ID)
        snap = snapshot_task_conformance(TASK_ID, wt, tmp_path)
        assert snap is not None
        (wt / "app" / "test").mkdir(parents=True)
        (wt / "app" / "test" / "sign_in_test.dart").write_text(
            "void main() { widgetSignInFlow(); }\n"
        )
        assert evaluate_from_snapshot(snap, wt)["status"] == "passed"
