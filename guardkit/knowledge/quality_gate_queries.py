"""
Quality Gate Configuration queries for Graphiti knowledge graph.

This module provides query functions to retrieve quality gate configurations
based on task type and complexity from the Graphiti knowledge graph.
"""

import logging
from typing import Optional

from guardkit.knowledge.facts.quality_gate_config import QualityGateConfigFact
from guardkit.knowledge import get_graphiti

logger = logging.getLogger(__name__)


async def get_quality_gate_config(
    task_type: str,
    complexity: int
) -> Optional[QualityGateConfigFact]:
    """Get quality gate configuration for task type and complexity.

    Queries Graphiti for quality gate configurations matching the given
    task type and complexity level.

    Args:
        task_type: Task category (e.g., "feature", "scaffolding", "testing", "docs")
        complexity: Task complexity level (1-10)

    Returns:
        QualityGateConfigFact if found, None otherwise.

    Example:
        config = await get_quality_gate_config("feature", 5)
        if config:
            print(f"Arch review threshold: {config.arch_review_threshold}")
    """
    graphiti = get_graphiti()

    # Handle disabled or None client
    if graphiti is None or not graphiti.enabled:
        logger.debug("Graphiti is disabled or unavailable, returning None")
        return None

    try:
        # Search for quality gate configurations
        results = await graphiti.search(
            query=f"quality_gate_config {task_type} complexity {complexity}",
            group_ids=["quality_gate_configs"],
            num_results=5
        )

        # Find matching config
        for result in results:
            body = result.get('body', {})

            # Skip if body is empty or missing required fields
            if not body or 'task_type' not in body or 'complexity_range' not in body:
                continue

            # Check task type match
            if body.get('task_type') != task_type:
                continue

            # Check complexity range match
            complexity_range = body.get('complexity_range', [0, 10])
            # Handle both tuple and list formats
            if isinstance(complexity_range, (list, tuple)) and len(complexity_range) >= 2:
                min_c, max_c = complexity_range[0], complexity_range[1]
                if min_c <= complexity <= max_c:
                    # Reconstruct QualityGateConfigFact from body
                    return _body_to_fact(body)

        return None

    except Exception as e:
        logger.warning(f"Error querying quality gate config: {e}")
        return None


def _body_to_fact(body: dict) -> QualityGateConfigFact:
    """Convert Graphiti body dict to QualityGateConfigFact.

    Args:
        body: Dictionary from Graphiti episode body

    Returns:
        QualityGateConfigFact instance
    """
    from datetime import datetime

    # Handle complexity_range conversion (list to tuple)
    complexity_range = body.get('complexity_range', (1, 10))
    if isinstance(complexity_range, list):
        complexity_range = tuple(complexity_range)

    # Handle effective_from conversion (string to datetime)
    effective_from = body.get('effective_from')
    if isinstance(effective_from, str):
        effective_from = datetime.fromisoformat(effective_from)
    elif effective_from is None:
        effective_from = datetime.now()

    return QualityGateConfigFact(
        id=body.get('id', ''),
        name=body.get('name', ''),
        task_type=body.get('task_type', ''),
        complexity_range=complexity_range,
        arch_review_required=body.get('arch_review_required', True),
        arch_review_threshold=body.get('arch_review_threshold'),
        test_pass_required=body.get('test_pass_required', True),
        coverage_required=body.get('coverage_required', True),
        coverage_threshold=body.get('coverage_threshold'),
        lint_required=body.get('lint_required', True),
        rationale=body.get('rationale', ''),
        version=body.get('version', '1.0.0'),
        effective_from=effective_from,
        supersedes=body.get('supersedes')
    )
