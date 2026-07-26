"""Shared coach-contract resolution (TASK-CMIR-003 AC-1, completed 2026-07-26):
env > .guardkit/config.yaml autobuild.coach.contract > default — ONE resolver,
both consumers routed through it; plus the autobuild.coach.model fallback that
lets a repo config carry the whole coach-seat pairing without launch flags."""

from pathlib import Path

import pytest

from guardkit.orchestrator.coach_contract import (
    COACH_CONTRACT_ENV,
    resolve_coach_contract,
)


def _git_init(root: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def _write_config(root: Path, coach: dict) -> None:
    import yaml

    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"autobuild": {"coach": coach}})
    )


class TestResolutionTiers:
    def test_default_when_nothing_set(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        assert resolve_coach_contract(tmp_path) == "coachsplit"

    def test_config_tier(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        _write_config(tmp_path, {"contract": "v4"})
        assert resolve_coach_contract(tmp_path) == "v4"

    def test_env_wins_over_config(self, tmp_path, monkeypatch):
        _write_config(tmp_path, {"contract": "v4"})
        monkeypatch.setenv(COACH_CONTRACT_ENV, "coachsplit")
        assert resolve_coach_contract(tmp_path) == "coachsplit"

    def test_cwd_discovery(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        _write_config(tmp_path, {"contract": "v4"})
        monkeypatch.chdir(tmp_path)
        assert resolve_coach_contract() == "v4"

    def test_invalid_value_degrades_to_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        _write_config(tmp_path, {"contract": "v9-typo"})
        assert resolve_coach_contract(tmp_path) == "coachsplit"

    def test_broken_config_never_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        cfg = tmp_path / ".guardkit"
        cfg.mkdir()
        (cfg / "config.yaml").write_text("autobuild: [not, a, mapping")
        assert resolve_coach_contract(tmp_path) == "coachsplit"


class TestConsumersShareTheResolver:
    def test_parser_resolver_delegates(self, tmp_path, monkeypatch):
        from guardkit.orchestrator import coach_output_parser

        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        _write_config(tmp_path, {"contract": "v4"})
        monkeypatch.chdir(tmp_path)
        assert coach_output_parser._resolve_contract() == "v4"

    def test_invoker_resolver_delegates(self, tmp_path, monkeypatch):
        from guardkit.orchestrator.agent_invoker import _resolve_coach_contract

        monkeypatch.delenv(COACH_CONTRACT_ENV, raising=False)
        _write_config(tmp_path, {"contract": "v4"})
        monkeypatch.chdir(tmp_path)
        assert _resolve_coach_contract() == "v4"


class TestCoachModelConfigFallback:
    def test_config_model_used_when_cli_omitted(self, tmp_path):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        _git_init(tmp_path)
        _write_config(tmp_path, {"model": "coach-ft-v4", "contract": "v4"})
        ab = AutoBuildOrchestrator(repo_root=tmp_path)
        assert ab._coach_model_name == "coach-ft-v4"

    def test_cli_wins_over_config(self, tmp_path):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        _git_init(tmp_path)
        _write_config(tmp_path, {"model": "coach-ft-v4"})
        ab = AutoBuildOrchestrator(repo_root=tmp_path, coach_model="gemma4-coach")
        assert ab._coach_model_name == "gemma4-coach"

    def test_none_when_neither(self, tmp_path):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        _git_init(tmp_path)
        ab = AutoBuildOrchestrator(repo_root=tmp_path)
        assert ab._coach_model_name is None
