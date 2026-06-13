"""Cross-repo evidence contract seam test (TASK-AB-XREPOEV01 AC-006-adjacent).

CI enforcement for the namespace-hygiene / absent-signal posture: a feature
that declares ``evidence_repos`` must fail **loudly** if the orchestrator
stops supporting it, never be silently degraded to absent-signal (the
``.claude/rules/absence-of-failure-is-not-success.md`` /
``.claude/rules/namespace-hygiene.md`` meta-class; the guardkit <->
guardkitfactory boundary that ``harness-cancellation-contract.md`` governs).

Unlike a full autobuild run, these are ``inspect.signature`` + model-field
assertions that fail in seconds when any link in the wiring chain is removed:

    Feature.evidence_repos (declaration)
        -> resolve_evidence_repos (resolution)
        -> AgentInvoker / CoachVerifier / CoachValidator /
           WorktreeCheckpointManager / AutoBuildOrchestrator (consumers)
        -> CoachEvidenceBundle.evidence_repo_tests (AC-002 landing site)

If a future refactor drops the ``evidence_repos`` parameter from any consumer
constructor, or the field from the Feature model, this seam fails in CI
instead of silently producing "0 files modified" false-reds on a live run.
"""

from __future__ import annotations

import inspect
import subprocess

import pytest

pytestmark = [pytest.mark.seam]


def _has_param(func, name: str) -> bool:
    return name in inspect.signature(func).parameters


def _init_git(path) -> None:
    """Both orchestrators validate ``repo_root`` is a git repo on construction."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)


class TestEvidenceContractDeclaration:
    def test_feature_model_has_evidence_repos_field(self):
        from guardkit.orchestrator.feature_loader import Feature

        assert "evidence_repos" in Feature.model_fields

    def test_malformed_declaration_fails_loudly_not_silently(self):
        # The rule's core: a typo'd / malformed evidence_repos declaration must
        # raise at parse time, not be silently swallowed (absent-signal).
        from pydantic import ValidationError

        from guardkit.orchestrator.feature_loader import Feature

        with pytest.raises(ValidationError):
            Feature(id="FEAT-X", name="x", evidence_repos=[123])
        with pytest.raises(ValidationError):
            Feature(id="FEAT-X", name="x", evidence_repos=[{"no_path": "y"}])

    def test_resolver_is_importable(self):
        from guardkit.orchestrator.evidence_repos import resolve_evidence_repos

        assert callable(resolve_evidence_repos)


class TestEvidenceContractConsumers:
    """Every consumer constructor must still accept ``evidence_repos``."""

    def test_agent_invoker_accepts_evidence_repos(self):
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        assert _has_param(AgentInvoker.__init__, "evidence_repos")

    def test_coach_verifier_accepts_evidence_repos(self):
        from guardkit.orchestrator.coach_verification import CoachVerifier

        assert _has_param(CoachVerifier.__init__, "evidence_repos")

    def test_coach_validator_accepts_evidence_repos(self):
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        assert _has_param(CoachValidator.__init__, "evidence_repos")

    def test_checkpoint_manager_accepts_evidence_repos(self):
        from guardkit.orchestrator.worktree_checkpoints import (
            WorktreeCheckpointManager,
        )

        assert _has_param(WorktreeCheckpointManager.__init__, "evidence_repos")

    def test_autobuild_orchestrator_accepts_evidence_repos(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        assert _has_param(AutoBuildOrchestrator.__init__, "evidence_repos")

    def test_coach_evidence_bundle_has_test_landing_field(self):
        # AC-002 results must have somewhere in the bundle to land.
        from guardkit.orchestrator.quality_gates.coach_evidence import (
            CoachEvidenceBundle,
        )

        assert "evidence_repo_tests" in CoachEvidenceBundle.__dataclass_fields__


class TestEvidenceContractThreading:
    def test_autobuild_orchestrator_stores_evidence_repos(self, tmp_path):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        from guardkit.orchestrator.evidence_repos import EvidenceRepo

        _init_git(tmp_path)
        repo = EvidenceRepo(name="guardkitfactory", root=tmp_path / "gkf")
        orch = AutoBuildOrchestrator(repo_root=tmp_path, evidence_repos=[repo])
        assert orch._evidence_repos == [repo]

    def test_feature_orchestrator_has_resolved_slot(self, tmp_path):
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        _init_git(tmp_path)
        orch = FeatureOrchestrator(repo_root=tmp_path)
        # Default empty until _setup_phase resolves from the loaded feature.
        assert orch._evidence_repos_resolved == []

    def test_feature_orchestrator_threads_resolved_repos_to_tasks(self):
        # Source-level guard: the per-task AutoBuildOrchestrator construction
        # must forward the resolved repos. If this threading is deleted, the
        # whole feature path silently degrades to absent-signal.
        import inspect as _inspect

        from guardkit.orchestrator import feature_orchestrator

        src = _inspect.getsource(feature_orchestrator)
        assert "evidence_repos=self._evidence_repos_resolved" in src

    def test_coach_honesty_verifier_receives_evidence_repos(self):
        # CRITICAL regression guard (review finding): the CoachVerifier built
        # INSIDE coach_validator._verify_honesty must receive evidence_repos,
        # else the Coach's own honesty gate fail-open-skips every sibling-repo
        # claim and a Player can lie about sibling files undetected.
        import inspect as _inspect

        from guardkit.orchestrator.quality_gates import coach_validator

        src = _inspect.getsource(coach_validator)
        assert "evidence_repos=self._evidence_repos" in src

    def test_both_coach_paths_run_the_sibling_test_gate(self):
        # HIGH regression guard (review finding): both the primary and legacy
        # (GUARDKIT_COACH_LEGACY=1) Coach paths must run the AC-002 gate, or the
        # legacy revert silently ignores a declared sibling test_command (a
        # BDDW-002 false-green re-opens). Shared via _evidence_repo_gate; assert
        # it is invoked from at least two sites.
        import inspect as _inspect

        from guardkit.orchestrator import autobuild

        src = _inspect.getsource(autobuild)
        assert src.count("self._evidence_repo_gate(") >= 2
