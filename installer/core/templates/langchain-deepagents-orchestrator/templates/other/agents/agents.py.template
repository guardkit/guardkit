"""Agent definitions for the DeepAgents orchestrator exemplar.

Provides factory functions for all four agent roles:

- **Orchestrator**: Top-level reasoning agent built via ``create_deep_agent()``.
- **Implementer**: Sync SubAgent with the four orchestrator tools.
- **Evaluator**: Sync SubAgent with NO tools (pure assessment).
- **Builder**: Async SubAgent targeting a remote LangGraph deployment.

Each SubAgent factory accepts a ``model`` string in ``provider:model`` format
so the entrypoint can configure models from the YAML config file.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from deepagents import AsyncSubAgent, SubAgent, create_deep_agent
from langgraph.graph.state import CompiledStateGraph

from prompts import EVALUATOR_SYSTEM_PROMPT, IMPLEMENTER_SYSTEM_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT
from tools import analyse_context, execute_command, plan_pipeline, verify_output

logger = logging.getLogger(__name__)

# The four orchestrator tools shared between the orchestrator and implementer.
_ORCHESTRATOR_TOOLS = [analyse_context, plan_pipeline, execute_command, verify_output]


def implementer_subagent(model: str) -> SubAgent:
    """Build the Implementer SubAgent spec.

    The Implementer is a focused execution agent that receives plans from the
    Orchestrator and produces concrete outputs.  It has access to the four
    orchestrator tools for context analysis, planning, execution, and
    verification.

    Args:
        model: Model identifier in ``provider:model`` format (e.g.
            ``"anthropic:claude-haiku-4-5"``).

    Returns:
        A ``SubAgent`` TypedDict ready to pass to ``create_deep_agent(subagents=...)``.
    """
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")

    today = datetime.date.today().isoformat()
    prompt = IMPLEMENTER_SYSTEM_PROMPT.format(date=today)

    return SubAgent(
        name="implementer",
        description=(
            "Focused execution agent that implements plans by writing code, "
            "creating files, and running commands.  Delegates to the orchestrator "
            "tools for context analysis, pipeline planning, command execution, "
            "and output verification."
        ),
        system_prompt=prompt,
        model=model,
        tools=list(_ORCHESTRATOR_TOOLS),
    )


def evaluator_subagent(model: str) -> SubAgent:
    """Build the Evaluator SubAgent spec.

    The Evaluator is an objective quality-assurance agent that assesses outputs
    against acceptance criteria and returns structured JSON verdicts.  It has
    **no tools** — evaluation is purely analytical.

    Args:
        model: Model identifier in ``provider:model`` format (e.g.
            ``"anthropic:claude-sonnet-4-6"``).

    Returns:
        A ``SubAgent`` TypedDict ready to pass to ``create_deep_agent(subagents=...)``.
    """
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")

    today = datetime.date.today().isoformat()
    prompt = EVALUATOR_SYSTEM_PROMPT.format(date=today)

    return SubAgent(
        name="evaluator",
        description=(
            "Objective quality-assurance agent that reviews completed work "
            "against acceptance criteria and returns a structured JSON verdict "
            "with decision, score, issues, and quality assessment.  Has no "
            "tools — evaluation is purely reasoning-based."
        ),
        system_prompt=prompt,
        model=model,
        tools=[],
    )


def builder_async_subagent(
    url: str | None = None,
    graph_id: str = "builder",
) -> AsyncSubAgent:
    """Build the Builder AsyncSubAgent spec.

    The Builder is a non-blocking async subagent that targets a remote
    LangGraph deployment for long-running build tasks.

    Args:
        url: Optional URL of the remote LangGraph server.  Omit for ASGI
            transport (local development).
        graph_id: The graph name on the remote server.  Defaults to
            ``"builder"``.

    Returns:
        An ``AsyncSubAgent`` TypedDict ready to pass to
        ``create_deep_agent(subagents=...)``.
    """
    spec: dict[str, Any] = AsyncSubAgent(
        name="builder",
        description=(
            "Non-blocking async subagent for long-running build and deployment "
            "tasks.  Connects to a remote LangGraph deployment and returns "
            "results asynchronously."
        ),
        graph_id=graph_id,
    )
    if url is not None:
        spec["url"] = url
    return spec  # type: ignore[return-value]


def create_orchestrator(
    reasoning_model: str,
    implementation_model: str,
    domain_prompt: str,
) -> CompiledStateGraph:
    """Create the top-level Orchestrator agent with its three subagents.

    Assembles the orchestrator by combining the reasoning model, orchestrator
    tools, system prompt (with domain context injected), and the three
    subagents (implementer, evaluator, builder).

    Args:
        reasoning_model: Model identifier for the orchestrator's reasoning
            (e.g. ``"anthropic:claude-sonnet-4-6"``).
        implementation_model: Model identifier for the implementer subagent
            (e.g. ``"anthropic:claude-haiku-4-5"``).
        domain_prompt: Domain-specific instructions to inject into the
            orchestrator system prompt via the ``{domain_prompt}`` placeholder.

    Returns:
        A compiled ``CompiledStateGraph`` representing the orchestrator agent
        graph, ready to be invoked or served via LangGraph.

    Raises:
        ValueError: If any model string is empty or not a string.
    """
    if not reasoning_model or not isinstance(reasoning_model, str):
        raise ValueError(f"reasoning_model must be a non-empty string, got: {reasoning_model!r}")
    if not implementation_model or not isinstance(implementation_model, str):
        raise ValueError(f"implementation_model must be a non-empty string, got: {implementation_model!r}")

    today = datetime.date.today().isoformat()
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        date=today,
        domain_prompt=domain_prompt,
    )

    subagents = [
        implementer_subagent(model=implementation_model),
        evaluator_subagent(model=reasoning_model),
        builder_async_subagent(),
    ]

    graph = create_deep_agent(
        model=reasoning_model,
        tools=list(_ORCHESTRATOR_TOOLS),
        system_prompt=system_prompt,
        subagents=subagents,
        memory=["./AGENTS.md"],
        skills=None,
        context_schema=None,
    )

    return graph
