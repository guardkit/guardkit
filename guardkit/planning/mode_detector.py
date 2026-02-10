"""
Mode detector for system-plan command.

This module provides automatic mode detection based on existing
Graphiti architecture context. Used to determine whether to start
in setup mode (no existing context) or refine mode (existing context found).

Example:
    from guardkit.planning.mode_detector import detect_mode
    from guardkit.knowledge.graphiti_client import get_graphiti

    client = get_graphiti()
    mode = await detect_mode(graphiti_client=client, project_id="my-project")
    # Returns "setup" or "refine"
"""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.knowledge.graphiti_client import GraphitiClient

from guardkit.planning.graphiti_arch import SystemPlanGraphiti

logger = logging.getLogger(__name__)


def _get_default_project_id() -> str:
    """Get default project ID from current working directory name.

    Returns:
        Project ID string based on cwd name.
    """
    return Path.cwd().name


async def detect_mode(
    graphiti_client: Optional["GraphitiClient"] = None,
    project_id: Optional[str] = None,
) -> str:
    """Detect the appropriate mode for system-plan command.

    Checks Graphiti for existing architecture context to determine
    whether to start in setup mode or refine mode.

    Args:
        graphiti_client: GraphitiClient instance. If None or disabled,
            returns "setup" with graceful degradation.
        project_id: Project ID for namespace prefixing. If None,
            uses default based on current directory name.

    Returns:
        "setup" if no existing architecture context or on error.
        "refine" if existing architecture context is found.

    Example:
        >>> from guardkit.planning.mode_detector import detect_mode
        >>> mode = await detect_mode(graphiti_client=client)
        >>> print(mode)  # "setup" or "refine"
    """
    # Use default project_id if not provided
    if project_id is None:
        project_id = _get_default_project_id()

    # Graceful degradation: no client
    if graphiti_client is None:
        logger.info("Graphiti client is None, fallback to setup mode")
        return "setup"

    # Graceful degradation: client disabled
    if not getattr(graphiti_client, "enabled", False):
        logger.info("Graphiti disabled, fallback to setup mode")
        return "setup"

    try:
        # Create SystemPlanGraphiti instance to check for context
        service = SystemPlanGraphiti(
            client=graphiti_client,
            project_id=project_id,
        )

        # Check if architecture context exists
        has_context = await service.has_architecture_context()

        if has_context:
            logger.info("Detected mode: refine (existing architecture context found)")
            return "refine"
        else:
            logger.info("Detected mode: setup (no existing architecture context)")
            return "setup"

    except Exception as e:
        # Graceful degradation: any error falls back to setup
        logger.warning(f"Mode detection failed with error: {e}, fallback to setup mode")
        return "setup"


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "detect_mode",
]
