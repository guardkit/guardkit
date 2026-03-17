#!/usr/bin/env python3
"""
Graphiti availability check and task context loader for Claude Code.

This script provides a CLI interface for Claude Code to check Graphiti
availability and load task context WITHOUT requiring MCP tools.

It uses the guardkit Python client library directly to connect to
FalkorDB and retrieve knowledge graph context.

Usage:
    # Check if Graphiti is available (exit code 0 = available, 1 = unavailable)
    python -m installer.core.commands.lib.graphiti_check --status

    # Load task context for a specific task
    python -m installer.core.commands.lib.graphiti_check --task-context \
        --task-id TASK-001 \
        --description "Implement auth endpoint" \
        --stack python \
        --complexity 5 \
        --phase plan

    # Both in one call
    python -m installer.core.commands.lib.graphiti_check --status --task-context \
        --task-id TASK-001 --description "..." --stack python

Output:
    JSON on stdout with structure:
    {
        "available": true|false,
        "error": null|"error message",
        "context": null|"formatted context string",
        "categories": 0,
        "tokens_used": 0,
        "tokens_budget": 0
    }

References:
    - Replaces MCP-based Graphiti availability check in task-work Phase 1.7
    - Uses guardkit.knowledge.graphiti_client for direct FalkorDB access
    - Uses guardkit.knowledge.job_context_retriever for context loading
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure guardkit package is importable
# When run from project root, this should work directly
_project_root = Path(__file__).resolve().parents[4]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)


def _check_availability() -> dict:
    """Check if Graphiti is available via Python client.

    Returns:
        dict with 'available' (bool) and 'error' (str|None)
    """
    result = {"available": False, "error": None}

    # Check 1: Environment variable override
    env_enabled = os.environ.get("GRAPHITI_ENABLED", "true").lower()
    if env_enabled == "false":
        result["error"] = "Disabled via GRAPHITI_ENABLED=false"
        return result

    # Check 2: graphiti-core library available
    try:
        from graphiti_core import Graphiti  # noqa: F401
    except ImportError:
        result["error"] = "graphiti-core not installed"
        return result

    # Check 3: Configuration exists
    try:
        from guardkit.knowledge.config import load_graphiti_config
        settings = load_graphiti_config()
        if not settings.enabled:
            result["error"] = "Disabled in graphiti.yaml"
            return result
    except Exception as e:
        result["error"] = f"Config error: {e}"
        return result

    # Check 4: Can connect to FalkorDB
    try:
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(
            enabled=settings.enabled,
            graph_store=settings.graph_store,
            falkordb_host=settings.falkordb_host,
            falkordb_port=settings.falkordb_port,
            timeout=min(settings.timeout, 10.0),  # Cap at 10s for check
            project_id=getattr(settings, 'project_id', None),
        )

        # Quick connectivity test via FalkorDB ping
        if config.graph_store == "falkordb":
            import redis
            r = redis.Redis(
                host=config.falkordb_host,
                port=config.falkordb_port,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            r.ping()
            r.close()
        else:
            # Neo4j - just check config is present
            pass

        result["available"] = True
    except Exception as e:
        result["error"] = f"Connection failed: {e}"

    return result


async def _load_task_context(
    task_id: str,
    description: str,
    stack: str = "unknown",
    complexity: int = 5,
    phase: str = "plan",
    feature_id: str = None,
) -> dict:
    """Load task context from Graphiti knowledge graph.

    Returns:
        dict with context string and metadata
    """
    result = {
        "context": None,
        "categories": 0,
        "tokens_used": 0,
        "tokens_budget": 0,
        "error": None,
    }

    try:
        from guardkit.knowledge import get_graphiti, init_graphiti
        from guardkit.knowledge.config import load_graphiti_config
        from guardkit.knowledge.graphiti_client import GraphitiConfig
        from guardkit.knowledge.job_context_retriever import (
            JobContextRetriever,
            RetrievedContext,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        # Load config and initialize client
        settings = load_graphiti_config()
        config = GraphitiConfig(
            enabled=settings.enabled,
            graph_store=settings.graph_store,
            falkordb_host=settings.falkordb_host,
            falkordb_port=settings.falkordb_port,
            timeout=settings.timeout,
            project_id=getattr(settings, 'project_id', None),
        )

        await init_graphiti(config)
        client = get_graphiti()

        if not client or not client.enabled:
            result["error"] = "Client initialization failed"
            return result

        # Build task data
        task_data = {
            "id": task_id,
            "description": description,
            "tech_stack": stack,
            "complexity": complexity,
        }
        if feature_id:
            task_data["feature_id"] = feature_id

        # Map phase string to enum
        phase_mapping = {
            "load": TaskPhase.LOAD,
            "plan": TaskPhase.PLAN,
            "implement": TaskPhase.IMPLEMENT,
            "test": TaskPhase.TEST,
            "review": TaskPhase.REVIEW,
        }
        task_phase = phase_mapping.get(phase.lower(), TaskPhase.PLAN)

        # Retrieve context
        retriever = JobContextRetriever(client)
        context = await retriever.retrieve(task_data, task_phase)

        # Format for prompt
        prompt_text = context.to_prompt()

        # Count populated categories
        category_count = sum(1 for attr in [
            context.feature_context, context.similar_outcomes,
            context.relevant_patterns, context.architecture_context,
            context.warnings, context.domain_knowledge,
        ] if attr)

        result["context"] = prompt_text
        result["categories"] = category_count
        result["tokens_used"] = context.budget_used
        result["tokens_budget"] = context.budget_total

        # Clean up
        await client.close()

    except Exception as e:
        result["error"] = str(e)
        logger.debug("Context loading error: %s", e, exc_info=True)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Check Graphiti availability and load task context"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check if Graphiti is available",
    )
    parser.add_argument(
        "--task-context",
        action="store_true",
        help="Load task context from knowledge graph",
    )
    parser.add_argument("--task-id", type=str, default=None)
    parser.add_argument("--description", type=str, default="")
    parser.add_argument("--stack", type=str, default="unknown")
    parser.add_argument("--complexity", type=int, default=5)
    parser.add_argument("--phase", type=str, default="plan")
    parser.add_argument("--feature-id", type=str, default=None)
    parser.add_argument("--quiet", action="store_true", help="Suppress logging")

    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.WARNING)

    output = {
        "available": False,
        "error": None,
        "context": None,
        "categories": 0,
        "tokens_used": 0,
        "tokens_budget": 0,
    }

    # Check availability
    if args.status or not args.task_context:
        status = _check_availability()
        output["available"] = status["available"]
        output["error"] = status["error"]

    # Load task context
    if args.task_context and args.task_id:
        if output.get("available", True):  # Only try if status check passed (or wasn't run)
            try:
                ctx_result = asyncio.run(_load_task_context(
                    task_id=args.task_id,
                    description=args.description,
                    stack=args.stack,
                    complexity=args.complexity,
                    phase=args.phase,
                    feature_id=args.feature_id,
                ))
                output.update(ctx_result)
                if not output["available"]:
                    output["available"] = ctx_result["context"] is not None
            except Exception as e:
                output["error"] = str(e)

    # Output JSON to stdout
    print(json.dumps(output))

    # Exit code: 0 = available, 1 = unavailable
    sys.exit(0 if output["available"] else 1)


if __name__ == "__main__":
    main()
