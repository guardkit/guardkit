"""Orchestrator components for GuardKit AutoBuild feature."""

from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.exceptions import (
    AgentInvokerError,
    AgentInvocationError,
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
    OrchestrationError,
    SetupPhaseError,
    LoopPhaseError,
    FinalizePhaseError,
)
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.protocol import OrchestratorProtocol

__all__ = [
    # Agent invocation
    "AgentInvoker",
    "AgentInvocationResult",
    # AutoBuild orchestration
    "AutoBuildOrchestrator",
    "OrchestrationResult",
    "TurnRecord",
    # Protocol
    "OrchestratorProtocol",
    # Exceptions - AgentInvoker
    "AgentInvokerError",
    "AgentInvocationError",
    "PlayerReportNotFoundError",
    "PlayerReportInvalidError",
    "CoachDecisionNotFoundError",
    "CoachDecisionInvalidError",
    "SDKTimeoutError",
    # Exceptions - Orchestration
    "OrchestrationError",
    "SetupPhaseError",
    "LoopPhaseError",
    "FinalizePhaseError",
    # Progress display
    "ProgressDisplay",
]
