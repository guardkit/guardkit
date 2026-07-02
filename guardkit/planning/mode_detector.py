"""
Mode detector for system-plan command.

This module determines whether ``/system-plan`` starts in setup mode
(no existing context) or refine mode (existing context found).

Architecture-context lookup was backed by the knowledge graph, which was
retired in the fleet-memory cutover (FEAT-MEM-09). Mode detection therefore
degrades to ``setup`` unless an explicit mode override is supplied by the
caller.

Example:
    from guardkit.planning.mode_detector import detect_mode

    mode = await detect_mode(project_id="my-project")
    # Returns "setup"
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _get_default_project_id() -> str:
    """Get default project ID from current working directory name.

    Returns:
        Project ID string based on cwd name.
    """
    return Path.cwd().name


async def detect_mode(
    graphiti_client: Optional[Any] = None,
    project_id: Optional[str] = None,
) -> str:
    """Detect the appropriate mode for the system-plan command.

    Architecture-context lookup was retired in the fleet-memory cutover, so
    this now degrades to ``setup`` mode. The ``graphiti_client`` parameter is
    retained for backwards compatibility and is ignored.

    Args:
        graphiti_client: Deprecated / ignored (retained for compatibility).
        project_id: Project ID for namespace prefixing. If None,
            uses default based on current directory name.

    Returns:
        "setup" (no persisted architecture context is available post-cutover).

    Example:
        >>> from guardkit.planning.mode_detector import detect_mode
        >>> mode = await detect_mode()
        >>> print(mode)  # "setup"
    """
    if project_id is None:
        project_id = _get_default_project_id()

    logger.info("Detected mode: setup (architecture-context lookup retired)")
    return "setup"


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "detect_mode",
]
