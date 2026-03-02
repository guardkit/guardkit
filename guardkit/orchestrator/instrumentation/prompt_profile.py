"""Prompt profile switching for AutoBuild agents.

Supports four composition profiles that control what context sources
are included in the system prompt during an AutoBuild run:

    - digest_only:                  Role digest only
    - digest+graphiti:              Role digest + Graphiti knowledge context
    - digest+rules_bundle:          Role digest + full rules bundle (Phase 1 default)
    - digest+graphiti+rules_bundle: All three (transitional phase)

Phase 1 Migration:
    The default profile is ``digest+rules_bundle`` which keeps the full rules
    bundle alongside the digest. This ensures no regression while the digest
    system is validated. Instrumentation events are tagged with the active
    profile for A/B comparison.

Example:
    >>> from guardkit.orchestrator.instrumentation.prompt_profile import (
    ...     PromptProfile, PromptProfileAssembler,
    ... )
    >>> from guardkit.orchestrator.instrumentation.digests import DigestLoader
    >>> loader = DigestLoader(Path(".guardkit/digests"))
    >>> assembler = PromptProfileAssembler(loader=loader)
    >>> prompt = assembler.assemble(role="player", profile=PromptProfile.DIGEST_ONLY)
"""

from __future__ import annotations

import enum
import logging
from typing import Optional

from guardkit.orchestrator.instrumentation.digests import DigestLoader

logger = logging.getLogger(__name__)


# ============================================================================
# PromptProfile Enum
# ============================================================================


class PromptProfile(enum.Enum):
    """Controlled vocabulary for prompt composition profiles.

    Each profile defines which context sources are included when
    assembling the system prompt for an agent role.
    """

    DIGEST_ONLY = "digest_only"
    """Role digest only, no rules bundle, no Graphiti."""

    DIGEST_GRAPHITI = "digest+graphiti"
    """Role digest plus retrieved Graphiti context."""

    DIGEST_RULES_BUNDLE = "digest+rules_bundle"
    """Role digest plus full rules bundle (Phase 1 baseline)."""

    DIGEST_GRAPHITI_RULES_BUNDLE = "digest+graphiti+rules_bundle"
    """Transitional: role digest + Graphiti + full rules bundle."""


# ============================================================================
# PromptProfileAssembler
# ============================================================================


class PromptProfileAssembler:
    """Assembles system prompts based on the active profile.

    Combines the role-specific digest with optional Graphiti context
    and/or the full rules bundle, depending on the selected profile.

    The assembler tracks the last-used profile for instrumentation
    tagging (events are tagged with which profile was active).

    Args:
        loader: DigestLoader instance for loading role digests.
        default_profile: Default profile to use. Defaults to
            DIGEST_RULES_BUNDLE for Phase 1 migration safety.

    Example:
        >>> assembler = PromptProfileAssembler(loader=loader)
        >>> prompt = assembler.assemble("player", PromptProfile.DIGEST_ONLY)
        >>> assembler.last_profile
        <PromptProfile.DIGEST_ONLY: 'digest_only'>
    """

    def __init__(
        self,
        loader: DigestLoader,
        default_profile: PromptProfile = PromptProfile.DIGEST_RULES_BUNDLE,
    ) -> None:
        self._loader = loader
        self._default_profile = default_profile
        self._last_profile: Optional[PromptProfile] = None

    @property
    def default_profile(self) -> PromptProfile:
        """The default prompt profile (Phase 1: digest+rules_bundle)."""
        return self._default_profile

    @property
    def last_profile(self) -> Optional[PromptProfile]:
        """The most recently used prompt profile, for instrumentation tagging."""
        return self._last_profile

    def assemble(
        self,
        role: str,
        profile: Optional[PromptProfile] = None,
        rules_bundle: Optional[str] = None,
        graphiti_context: Optional[str] = None,
    ) -> str:
        """Assemble a system prompt based on the active profile.

        Loads the role-specific digest and combines it with additional
        context sources as determined by the profile.

        Args:
            role: Agent role name (player, coach, resolver, router).
            profile: Prompt profile to use. If None, uses default_profile.
            rules_bundle: Optional full rules bundle content.
                Required when profile includes rules_bundle.
            graphiti_context: Optional Graphiti knowledge context.
                Required when profile includes graphiti.

        Returns:
            Assembled prompt string ready for system prompt injection.
        """
        active_profile = profile if profile is not None else self._default_profile
        self._last_profile = active_profile

        # Always start with the role digest
        digest_content = self._loader.load(role)
        sections: list[str] = [digest_content]

        # Add Graphiti context if profile requires it
        if active_profile in (
            PromptProfile.DIGEST_GRAPHITI,
            PromptProfile.DIGEST_GRAPHITI_RULES_BUNDLE,
        ):
            if graphiti_context:
                sections.append(graphiti_context)
            else:
                logger.debug(
                    "Profile '%s' expects Graphiti context but none provided",
                    active_profile.value,
                )

        # Add rules bundle if profile requires it
        if active_profile in (
            PromptProfile.DIGEST_RULES_BUNDLE,
            PromptProfile.DIGEST_GRAPHITI_RULES_BUNDLE,
        ):
            if rules_bundle:
                sections.append(rules_bundle)
            else:
                logger.debug(
                    "Profile '%s' expects rules bundle but none provided",
                    active_profile.value,
                )

        assembled = "\n\n".join(sections)
        logger.debug(
            "Assembled prompt for role='%s', profile='%s' (%d chars)",
            role,
            active_profile.value,
            len(assembled),
        )
        return assembled


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "PromptProfile",
    "PromptProfileAssembler",
]
