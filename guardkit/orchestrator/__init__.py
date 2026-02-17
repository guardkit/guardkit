"""Orchestrator components for GuardKit AutoBuild feature."""

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    TaskWorkStreamParser,
)
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    PreLoopPhaseError,
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
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
    FeatureNotFoundError,
    FeatureParseError,
    FeatureValidationError,
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationResult,
    FeatureOrchestrationError,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.environment_bootstrap import (
    ProjectEnvironmentDetector,
    EnvironmentBootstrapper,
    BootstrapResult,
    DetectedManifest,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.protocol import OrchestratorProtocol

# Import browser verifier module
from guardkit.orchestrator.browser_verifier import (
    BrowserVerifier,
    AgentBrowserVerifier,
    PlaywrightAppiumVerifier,
    select_verifier,
    BrowserVerifierError,
    AgentBrowserNotInstalledError,
)

# Import quality gates module
from guardkit.orchestrator.quality_gates import (
    PreLoopQualityGates,
    TaskWorkInterface,
    QualityGateError,
    QualityGateBlocked,
    DesignPhaseError,
    CheckpointRejectedError,
)

__all__ = [
    # Agent invocation
    "AgentInvoker",
    "AgentInvocationResult",
    "TaskWorkStreamParser",
    # AutoBuild orchestration
    "AutoBuildOrchestrator",
    "OrchestrationResult",
    "TurnRecord",
    # Feature orchestration
    "Feature",
    "FeatureTask",
    "FeatureOrchestration",
    "FeatureExecution",
    "FeatureLoader",
    "FeatureOrchestrator",
    "FeatureOrchestrationResult",
    "TaskExecutionResult",
    "WaveExecutionResult",
    # Environment bootstrap
    "ProjectEnvironmentDetector",
    "EnvironmentBootstrapper",
    "BootstrapResult",
    "DetectedManifest",
    # Paths
    "TaskArtifactPaths",
    # Protocol
    "OrchestratorProtocol",
    # Browser Verifier
    "BrowserVerifier",
    "AgentBrowserVerifier",
    "PlaywrightAppiumVerifier",
    "select_verifier",
    # Quality Gates
    "PreLoopQualityGates",
    "TaskWorkInterface",
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
    "PreLoopPhaseError",
    "LoopPhaseError",
    "FinalizePhaseError",
    # Exceptions - Feature Orchestration
    "FeatureNotFoundError",
    "FeatureParseError",
    "FeatureValidationError",
    "FeatureOrchestrationError",
    # Exceptions - Browser Verifier
    "BrowserVerifierError",
    "AgentBrowserNotInstalledError",
    # Exceptions - Quality Gates
    "QualityGateError",
    "QualityGateBlocked",
    "DesignPhaseError",
    "CheckpointRejectedError",
    # Progress display
    "ProgressDisplay",
]
