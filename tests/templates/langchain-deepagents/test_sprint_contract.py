"""Tests for sprint contract negotiation pattern.

Validates SprintContract, QualityThreshold, Target, FeasibilityResult,
EscalationPolicy, SprintNegotiator, and HITL escalation integration.

Coverage Target: >=85%
Test Count: 30+ tests
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import the module from the template's lib directory
# ---------------------------------------------------------------------------
_LIB_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
)

_CONTRACT_PATH = _LIB_PATH / "sprint_contract.py"
_HOOKS_PATH = _LIB_PATH / "checkpoint_hooks.py"


@pytest.fixture(scope="module")
def _lib_package():
    """Set up the lib directory as a package so relative imports work."""
    import types
    from importlib.machinery import SourceFileLoader

    pkg_name = "deepagents_lib"

    # Create the package module
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(_LIB_PATH)]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    # Load checkpoint_hooks as a submodule of the package
    hooks_loader = SourceFileLoader(f"{pkg_name}.checkpoint_hooks", str(_HOOKS_PATH))
    hooks_spec = importlib.util.spec_from_loader(f"{pkg_name}.checkpoint_hooks", hooks_loader)
    hooks_mod = importlib.util.module_from_spec(hooks_spec)
    hooks_mod.__package__ = pkg_name
    sys.modules[f"{pkg_name}.checkpoint_hooks"] = hooks_mod
    hooks_loader.exec_module(hooks_mod)
    pkg.checkpoint_hooks = hooks_mod

    return pkg


@pytest.fixture(scope="module")
def hooks_mod(_lib_package):
    """Return the checkpoint_hooks module."""
    return _lib_package.checkpoint_hooks


@pytest.fixture(scope="module")
def contract_mod(_lib_package):
    """Load the sprint_contract module as a submodule of the lib package."""
    from importlib.machinery import SourceFileLoader

    pkg_name = "deepagents_lib"
    loader = SourceFileLoader(f"{pkg_name}.sprint_contract", str(_CONTRACT_PATH))
    spec = importlib.util.spec_from_loader(f"{pkg_name}.sprint_contract", loader)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = pkg_name
    sys.modules[f"{pkg_name}.sprint_contract"] = mod
    loader.exec_module(mod)
    _lib_package.sprint_contract = mod
    return mod


# ---------------------------------------------------------------------------
# Convenience fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def EscalationPolicy(contract_mod):
    return contract_mod.EscalationPolicy


@pytest.fixture
def QualityThreshold(contract_mod):
    return contract_mod.QualityThreshold


@pytest.fixture
def Target(contract_mod):
    return contract_mod.Target


@pytest.fixture
def SprintContract(contract_mod):
    return contract_mod.SprintContract


@pytest.fixture
def FeasibilityResult(contract_mod):
    return contract_mod.FeasibilityResult


@pytest.fixture
def NegotiationResult(contract_mod):
    return contract_mod.NegotiationResult


@pytest.fixture
def EscalationResult(contract_mod):
    return contract_mod.EscalationResult


@pytest.fixture
def SprintNegotiator(contract_mod):
    return contract_mod.SprintNegotiator


@pytest.fixture
def CheckpointDecision(hooks_mod):
    return hooks_mod.CheckpointDecision


# ---------------------------------------------------------------------------
# 1. EscalationPolicy enum tests
# ---------------------------------------------------------------------------


class TestEscalationPolicy:

    def test_all_values(self, EscalationPolicy):
        assert EscalationPolicy.RETRY.value == "retry"
        assert EscalationPolicy.ESCALATE.value == "escalate"
        assert EscalationPolicy.SKIP.value == "skip"
        assert EscalationPolicy.ABORT.value == "abort"

    def test_from_string(self, EscalationPolicy):
        assert EscalationPolicy("retry") is EscalationPolicy.RETRY
        assert EscalationPolicy("escalate") is EscalationPolicy.ESCALATE

    def test_invalid_value_raises(self, EscalationPolicy):
        with pytest.raises(ValueError):
            EscalationPolicy("invalid")


# ---------------------------------------------------------------------------
# 2. QualityThreshold tests
# ---------------------------------------------------------------------------


class TestQualityThreshold:

    def test_defaults(self, QualityThreshold):
        qt = QualityThreshold()
        assert qt.min_score == 4
        assert qt.required_criteria == []
        assert qt.allow_partial is False

    def test_custom_values(self, QualityThreshold):
        qt = QualityThreshold(min_score=3, required_criteria=["accuracy"], allow_partial=True)
        assert qt.min_score == 3
        assert qt.required_criteria == ["accuracy"]
        assert qt.allow_partial is True


# ---------------------------------------------------------------------------
# 3. Target tests
# ---------------------------------------------------------------------------


class TestTarget:

    def test_minimal(self, Target):
        t = Target(name="article-1", description="Write an article")
        assert t.name == "article-1"
        assert t.description == "Write an article"
        assert t.context == ""
        assert t.metadata == {}

    def test_with_context_and_metadata(self, Target):
        t = Target(
            name="article-1",
            description="Write an article",
            context="Use formal tone",
            metadata={"domain": "tech"},
        )
        assert t.context == "Use formal tone"
        assert t.metadata == {"domain": "tech"}


# ---------------------------------------------------------------------------
# 4. SprintContract tests
# ---------------------------------------------------------------------------


class TestSprintContract:

    def test_defaults(self, SprintContract, EscalationPolicy):
        sc = SprintContract()
        assert sc.targets == []
        assert sc.constraints == []
        assert sc.max_turns == 3
        assert sc.escalation_policy == EscalationPolicy.RETRY
        assert sc.agreed is False
        assert sc.agreed_at is None
        assert sc.negotiation_log == []

    def test_with_targets(self, SprintContract, Target, EscalationPolicy):
        targets = [Target(name="t1", description="d1")]
        sc = SprintContract(
            targets=targets,
            constraints=["max 500 words"],
            max_turns=5,
            escalation_policy=EscalationPolicy.ABORT,
        )
        assert len(sc.targets) == 1
        assert sc.constraints == ["max 500 words"]
        assert sc.max_turns == 5
        assert sc.escalation_policy == EscalationPolicy.ABORT

    def test_to_dict(self, SprintContract, Target, EscalationPolicy):
        sc = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.SKIP,
        )
        d = sc.to_dict()
        assert d["escalation_policy"] == "skip"
        assert isinstance(d["targets"], list)
        assert d["targets"][0]["name"] == "t1"
        assert d["agreed"] is False
        # Ensure JSON-serialisable
        json.dumps(d)

    def test_to_dict_json_serialisable(self, SprintContract):
        sc = SprintContract()
        serialised = json.dumps(sc.to_dict())
        assert isinstance(serialised, str)


# ---------------------------------------------------------------------------
# 5. FeasibilityResult tests
# ---------------------------------------------------------------------------


class TestFeasibilityResult:

    def test_defaults(self, FeasibilityResult):
        fr = FeasibilityResult()
        assert fr.feasible is True
        assert fr.adjustments == []
        assert fr.dropped_targets == []
        assert fr.requested_context == []

    def test_infeasible(self, FeasibilityResult):
        fr = FeasibilityResult(
            feasible=False,
            adjustments=["reduce target count"],
            dropped_targets=["t3"],
            requested_context=["domain glossary"],
        )
        assert fr.feasible is False
        assert "t3" in fr.dropped_targets


# ---------------------------------------------------------------------------
# 6. SprintNegotiator — negotiation flow tests
# ---------------------------------------------------------------------------


class TestNegotiation:

    def test_immediate_agreement(self, SprintNegotiator, SprintContract, Target, FeasibilityResult):
        """Player accepts the first proposal."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.negotiate(contract)

        assert result.success is True
        assert result.rounds == 1
        assert result.contract.agreed is True
        assert result.contract.agreed_at is not None
        fn.assert_called_once()

    def test_agreement_after_adjustment(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """Player rejects first, accepts after adjustment."""
        contract = SprintContract(
            targets=[
                Target(name="t1", description="d1"),
                Target(name="t2", description="d2"),
            ],
        )

        call_count = 0

        def feasibility_fn(c):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FeasibilityResult(
                    feasible=False,
                    dropped_targets=["t2"],
                )
            return FeasibilityResult(feasible=True)

        negotiator = SprintNegotiator(feasibility_fn)
        result = negotiator.negotiate(contract)

        assert result.success is True
        assert result.rounds == 2
        assert len(result.contract.targets) == 1
        assert result.contract.targets[0].name == "t1"

    def test_negotiation_failure_max_rounds(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """Player never agrees within max_rounds."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=False, adjustments=["need more"]))
        negotiator = SprintNegotiator(fn, max_rounds=2)

        result = negotiator.negotiate(contract)

        assert result.success is False
        assert result.rounds == 2
        assert result.error is not None
        assert "No agreement" in result.error

    def test_requested_context_appended(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """Player requests additional context; it gets appended to targets."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1", context="base ctx")],
        )

        call_count = 0

        def feasibility_fn(c):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FeasibilityResult(
                    feasible=False,
                    requested_context=["domain glossary"],
                )
            return FeasibilityResult(feasible=True)

        negotiator = SprintNegotiator(feasibility_fn)
        result = negotiator.negotiate(contract)

        assert result.success is True
        assert "domain glossary" in result.contract.targets[0].context

    def test_on_contract_agreed_callback(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """on_contract_agreed callback is invoked on success."""
        contract = SprintContract(targets=[Target(name="t1", description="d1")])
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        callback = MagicMock()
        negotiator = SprintNegotiator(fn, on_contract_agreed=callback)

        result = negotiator.negotiate(contract)

        assert result.success is True
        callback.assert_called_once_with(result.contract)

    def test_negotiation_log_populated(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """Negotiation log records all rounds."""
        contract = SprintContract(targets=[Target(name="t1", description="d1")])
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.negotiate(contract)

        log = result.contract.negotiation_log
        assert len(log) >= 3  # propose + review + accept
        assert log[0]["action"] == "propose"
        assert log[1]["action"] == "review"
        assert log[2]["action"] == "accept"

    def test_context_appended_to_empty(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult
    ):
        """Requested context works when target has no existing context."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
        )

        call_count = 0

        def feasibility_fn(c):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FeasibilityResult(
                    feasible=False,
                    requested_context=["extra info"],
                )
            return FeasibilityResult(feasible=True)

        negotiator = SprintNegotiator(feasibility_fn)
        result = negotiator.negotiate(contract)

        assert result.success is True
        assert result.contract.targets[0].context == "extra info"


# ---------------------------------------------------------------------------
# 7. Escalation policy tests
# ---------------------------------------------------------------------------


class TestEscalation:

    def test_retry_policy_below_max(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult, EscalationPolicy
    ):
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            max_turns=3,
            escalation_policy=EscalationPolicy.RETRY,
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["bad"]
        )
        assert result.action == "retry"

    def test_retry_policy_at_max(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult, EscalationPolicy
    ):
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            max_turns=3,
            escalation_policy=EscalationPolicy.RETRY,
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=3, coach_issues=["bad"]
        )
        assert result.action == "skip"

    def test_skip_policy(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult, EscalationPolicy
    ):
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.SKIP,
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["bad"]
        )
        assert result.action == "skip"

    def test_abort_policy(
        self, SprintNegotiator, SprintContract, Target, FeasibilityResult, EscalationPolicy
    ):
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ABORT,
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["bad"]
        )
        assert result.action == "abort"

    def test_escalate_policy_with_hook_proceed(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
        CheckpointDecision,
    ):
        """Escalate to human, human decides PROCEED -> retry."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ESCALATE,
        )
        mock_hook = MagicMock()
        mock_hook.on_checkpoint = AsyncMock(return_value=CheckpointDecision.PROCEED)

        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn, checkpoint_hook=mock_hook)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["issue"]
        )
        assert result.action == "retry"
        assert result.checkpoint_decision == CheckpointDecision.PROCEED

    def test_escalate_policy_with_hook_skip(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
        CheckpointDecision,
    ):
        """Escalate to human, human decides SKIP."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ESCALATE,
        )
        mock_hook = MagicMock()
        mock_hook.on_checkpoint = AsyncMock(return_value=CheckpointDecision.SKIP)

        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn, checkpoint_hook=mock_hook)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["issue"]
        )
        assert result.action == "skip"
        assert result.checkpoint_decision == CheckpointDecision.SKIP

    def test_escalate_policy_with_hook_abort(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
        CheckpointDecision,
    ):
        """Escalate to human, human decides ABORT."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ESCALATE,
        )
        mock_hook = MagicMock()
        mock_hook.on_checkpoint = AsyncMock(return_value=CheckpointDecision.ABORT)

        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn, checkpoint_hook=mock_hook)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["issue"]
        )
        assert result.action == "abort"
        assert result.checkpoint_decision == CheckpointDecision.ABORT

    def test_escalate_policy_with_hook_override(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
        CheckpointDecision,
    ):
        """Escalate to human, human decides OVERRIDE -> retry."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ESCALATE,
        )
        mock_hook = MagicMock()
        mock_hook.on_checkpoint = AsyncMock(return_value=CheckpointDecision.OVERRIDE)

        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn, checkpoint_hook=mock_hook)

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["issue"]
        )
        assert result.action == "retry"
        assert result.checkpoint_decision == CheckpointDecision.OVERRIDE

    def test_escalate_without_hook_defaults_to_skip(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
    ):
        """Escalation without a hook falls back to skip."""
        contract = SprintContract(
            targets=[Target(name="t1", description="d1")],
            escalation_policy=EscalationPolicy.ESCALATE,
        )
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        negotiator = SprintNegotiator(fn)  # No checkpoint_hook

        result = negotiator.apply_escalation(
            contract, contract.targets[0], attempt=1, coach_issues=["issue"]
        )
        assert result.action == "skip"
        assert result.checkpoint_decision is None


# ---------------------------------------------------------------------------
# 8. Integration test: full negotiate -> execute -> evaluate
# ---------------------------------------------------------------------------


class TestIntegration:

    def test_full_negotiate_execute_evaluate_cycle(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
    ):
        """Simulate full lifecycle: negotiate contract, then apply escalation."""
        # Set up targets
        targets = [
            Target(name="article-1", description="Write article about AI"),
            Target(name="article-2", description="Write article about ML"),
        ]
        contract = SprintContract(
            targets=targets,
            constraints=["max 1000 words", "formal tone"],
            max_turns=3,
            escalation_policy=EscalationPolicy.RETRY,
        )

        # Player accepts immediately
        fn = MagicMock(return_value=FeasibilityResult(feasible=True))
        agreed_contracts = []
        negotiator = SprintNegotiator(
            fn, on_contract_agreed=lambda c: agreed_contracts.append(c)
        )

        # Negotiate
        result = negotiator.negotiate(contract)
        assert result.success is True
        assert len(agreed_contracts) == 1

        agreed = result.contract

        # Simulate execution: first target accepted, second rejected
        # Apply escalation for second target
        escalation = negotiator.apply_escalation(
            agreed, agreed.targets[1], attempt=1, coach_issues=["missing sources"]
        )
        assert escalation.action == "retry"

        # Second attempt also rejected -> at max
        escalation2 = negotiator.apply_escalation(
            agreed, agreed.targets[1], attempt=3, coach_issues=["still bad"]
        )
        assert escalation2.action == "skip"

        # Verify audit log
        log = agreed.to_dict()
        assert log["agreed"] is True
        assert len(log["negotiation_log"]) >= 3

    def test_negotiate_with_adjustment_then_escalate(
        self,
        SprintNegotiator,
        SprintContract,
        Target,
        FeasibilityResult,
        EscalationPolicy,
        CheckpointDecision,
    ):
        """Full cycle with negotiation adjustment and human escalation."""
        targets = [
            Target(name="t1", description="d1"),
            Target(name="t2", description="d2"),
            Target(name="t3", description="d3"),
        ]
        contract = SprintContract(
            targets=targets,
            max_turns=2,
            escalation_policy=EscalationPolicy.ESCALATE,
        )

        call_count = 0

        def feasibility_fn(c):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FeasibilityResult(
                    feasible=False,
                    dropped_targets=["t3"],
                    requested_context=["extra docs"],
                )
            return FeasibilityResult(feasible=True)

        mock_hook = MagicMock()
        mock_hook.on_checkpoint = AsyncMock(return_value=CheckpointDecision.SKIP)

        negotiator = SprintNegotiator(
            feasibility_fn, checkpoint_hook=mock_hook
        )

        # Negotiate
        result = negotiator.negotiate(contract)
        assert result.success is True
        assert len(result.contract.targets) == 2  # t3 was dropped

        # Escalation for t1 rejection
        esc = negotiator.apply_escalation(
            result.contract, result.contract.targets[0],
            attempt=1, coach_issues=["bad quality"],
        )
        assert esc.action == "skip"
        assert esc.checkpoint_decision == CheckpointDecision.SKIP
