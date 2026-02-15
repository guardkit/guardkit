"""
AutoBuild Context Loader for /feature-build integration.

This module provides the AutoBuildContextLoader class which bridges
JobContextRetriever with AutoBuildOrchestrator, enabling context-aware
Player and Coach turns during autonomous implementation.

Public API:
    AutoBuildContextLoader: Main loader class for AutoBuild context

Architecture:
    AutoBuildOrchestrator -> AutoBuildContextLoader -> JobContextRetriever
                                                    -> RetrievedContext

Example:
    from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader

    # Initialize with optional Graphiti client
    loader = AutoBuildContextLoader(graphiti=graphiti_client)

    # Get Player context for turn
    context = await loader.get_player_context(
        task_id="TASK-001",
        feature_id="FEAT-GR6",
        turn_number=1,
        description="Implement OAuth2 flow",
        tech_stack="python",
    )

    # Get Coach context for validation
    context = await loader.get_coach_context(
        task_id="TASK-001",
        feature_id="FEAT-GR6",
        turn_number=1,
        description="Implement OAuth2 flow",
    )

References:
    - TASK-GR6-006: Integrate with /feature-build
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .job_context_retriever import JobContextRetriever, RetrievedContext
from .task_analyzer import TaskPhase

if TYPE_CHECKING:
    pass  # Future type imports

logger = logging.getLogger(__name__)


@dataclass
class AutoBuildContextResult:
    """Result from AutoBuild context loading.

    Attributes:
        context: The retrieved context
        prompt_text: Formatted prompt text for injection
        budget_used: Tokens used
        budget_total: Total budget available
        categories_populated: List of category names with content
        verbose_details: Extra details for --verbose flag
    """

    context: RetrievedContext
    prompt_text: str
    budget_used: int
    budget_total: int
    categories_populated: List[str]
    verbose_details: Optional[str] = None


class AutoBuildContextLoader:
    """Loads context for AutoBuild Player and Coach turns.

    This class bridges JobContextRetriever with AutoBuildOrchestrator,
    providing tailored context for each actor type during the adversarial
    workflow.

    Player Context:
        - Full context including role_constraints, implementation_modes
        - Emphasized warnings for refinement attempts
        - Turn states for cross-turn learning

    Coach Context:
        - Quality gate configurations for validation
        - Turn states for decision continuity
        - Role constraints for Coach responsibilities

    Attributes:
        graphiti: Optional GraphitiClient for knowledge queries
        retriever: JobContextRetriever instance (created lazily)
        verbose: Whether to include detailed context information

    Example:
        loader = AutoBuildContextLoader(graphiti=client)

        # Player turn context
        result = await loader.get_player_context(
            task_id="TASK-001",
            feature_id="FEAT-GR6",
            turn_number=2,
            description="Implement OAuth2",
            tech_stack="python",
            previous_feedback="Add tests for edge cases",
        )

        # Use in prompt
        player_prompt = f"{base_prompt}\\n\\n{result.prompt_text}"

        # Coach turn context
        result = await loader.get_coach_context(
            task_id="TASK-001",
            feature_id="FEAT-GR6",
            turn_number=2,
            description="Implement OAuth2",
        )
    """

    def __init__(
        self,
        graphiti: Optional[Any] = None,
        verbose: bool = False,
    ) -> None:
        """Initialize AutoBuildContextLoader.

        Args:
            graphiti: Optional GraphitiClient instance for knowledge queries.
                If not provided, context loading is a no-op (graceful degradation).
            verbose: If True, include detailed context information in results.
        """
        self.graphiti = graphiti
        self.verbose = verbose
        self._retriever: Optional[JobContextRetriever] = None

    @property
    def retriever(self) -> Optional[JobContextRetriever]:
        """Get or create JobContextRetriever instance.

        Returns:
            JobContextRetriever if Graphiti is available, None otherwise.
        """
        if self._retriever is None and self.graphiti is not None:
            self._retriever = JobContextRetriever(self.graphiti)
        return self._retriever

    async def get_player_context(
        self,
        task_id: str,
        feature_id: str,
        turn_number: int,
        description: str,
        tech_stack: str = "python",
        complexity: int = 5,
        previous_feedback: Optional[str] = None,
        acceptance_criteria: Optional[List[str]] = None,
    ) -> AutoBuildContextResult:
        """Get context for Player turn.

        Retrieves full AutoBuild context including:
        - Role constraints for Player responsibilities
        - Quality gate configurations for implementation targets
        - Turn states for cross-turn learning
        - Implementation modes for workflow guidance
        - Warnings emphasized for refinement attempts

        Args:
            task_id: Task identifier (e.g., "TASK-GR6-006")
            feature_id: Feature identifier (e.g., "FEAT-GR6")
            turn_number: Current turn number (1-indexed)
            description: Task description for context queries
            tech_stack: Technology stack (default: "python")
            complexity: Task complexity 1-10 (default: 5)
            previous_feedback: Optional feedback from previous Coach turn
            acceptance_criteria: Optional list of acceptance criteria

        Returns:
            AutoBuildContextResult with Player-tailored context
        """
        if self.retriever is None:
            # Graceful degradation - return empty context
            logger.debug(f"Graphiti not available, skipping Player context for {task_id}")
            return self._empty_result(task_id)

        logger.info("[Graphiti] Loading Player context (turn %d)...", turn_number)

        # Build task dict for JobContextRetriever
        task = self._build_task_dict(
            task_id=task_id,
            feature_id=feature_id,
            turn_number=turn_number,
            description=description,
            tech_stack=tech_stack,
            complexity=complexity,
            current_actor="player",
            has_previous_turns=turn_number > 1,
            previous_feedback=previous_feedback,
        )

        try:
            # Retrieve context
            context = await self.retriever.retrieve(
                task=task,
                phase=TaskPhase.IMPLEMENT,
                collect_metrics=self.verbose,
            )

            # Load turn continuation context for turn > 1
            turn_continuation = None
            if turn_number > 1 and self.graphiti is not None:
                try:
                    from guardkit.knowledge.turn_state_operations import load_turn_continuation_context
                    turn_continuation = await load_turn_continuation_context(
                        graphiti_client=self.graphiti,
                        feature_id=feature_id,
                        task_id=task_id,
                        current_turn=turn_number,
                    )
                    if turn_continuation:
                        logger.info(
                            "[Graphiti] Turn continuation loaded: %d chars for turn %d",
                            len(turn_continuation), turn_number,
                        )
                    else:
                        logger.debug("[Graphiti] No turn continuation available for turn %d", turn_number)
                except Exception as e:
                    logger.warning("[Graphiti] Failed to load turn continuation context: %s", e)

            # Build result
            result = self._build_result(context, actor="player", turn_continuation=turn_continuation)

            # Log similar outcomes count
            similar_outcomes_count = len(context.similar_outcomes) if context.similar_outcomes else 0
            if similar_outcomes_count > 0:
                logger.info("[Graphiti] Similar outcomes found: %d matches", similar_outcomes_count)

            logger.info(
                "[Graphiti] Player context: %d categories, %d/%d tokens",
                len(result.categories_populated),
                result.budget_used,
                result.budget_total,
            )
            return result

        except Exception as e:
            logger.warning(f"Failed to retrieve Player context for {task_id}: {e}")
            return self._empty_result(task_id)

    async def get_coach_context(
        self,
        task_id: str,
        feature_id: str,
        turn_number: int,
        description: str,
        tech_stack: str = "python",
        complexity: int = 5,
        player_report: Optional[Dict[str, Any]] = None,
    ) -> AutoBuildContextResult:
        """Get context for Coach turn.

        Retrieves Coach-relevant context including:
        - Quality gate configurations for validation thresholds
        - Turn states for decision continuity
        - Role constraints for Coach responsibilities

        Args:
            task_id: Task identifier (e.g., "TASK-GR6-006")
            feature_id: Feature identifier (e.g., "FEAT-GR6")
            turn_number: Current turn number (1-indexed)
            description: Task description for context queries
            tech_stack: Technology stack (default: "python")
            complexity: Task complexity 1-10 (default: 5)
            player_report: Optional Player report from current turn

        Returns:
            AutoBuildContextResult with Coach-tailored context
        """
        if self.retriever is None:
            # Graceful degradation - return empty context
            logger.debug(f"Graphiti not available, skipping Coach context for {task_id}")
            return self._empty_result(task_id)

        logger.info("[Graphiti] Loading Coach context (turn %d)...", turn_number)

        # Build task dict for JobContextRetriever
        task = self._build_task_dict(
            task_id=task_id,
            feature_id=feature_id,
            turn_number=turn_number,
            description=description,
            tech_stack=tech_stack,
            complexity=complexity,
            current_actor="coach",
            has_previous_turns=turn_number > 1,
        )

        try:
            # Retrieve context
            context = await self.retriever.retrieve(
                task=task,
                phase=TaskPhase.IMPLEMENT,
                collect_metrics=self.verbose,
            )

            # Load turn continuation context for turn > 1
            turn_continuation = None
            if turn_number > 1 and self.graphiti is not None:
                try:
                    from guardkit.knowledge.turn_state_operations import load_turn_continuation_context
                    turn_continuation = await load_turn_continuation_context(
                        graphiti_client=self.graphiti,
                        feature_id=feature_id,
                        task_id=task_id,
                        current_turn=turn_number,
                    )
                    if turn_continuation:
                        logger.info(
                            "[Graphiti] Turn continuation loaded: %d chars for turn %d",
                            len(turn_continuation), turn_number,
                        )
                    else:
                        logger.debug("[Graphiti] No turn continuation available for turn %d", turn_number)
                except Exception as e:
                    logger.warning("[Graphiti] Failed to load turn continuation context: %s", e)

            # Build result with Coach-specific formatting
            result = self._build_result(context, actor="coach", turn_continuation=turn_continuation)

            # Log coach context categories
            logger.info("[Graphiti] Coach context categories: %s", result.categories_populated)

            logger.info(
                "[Graphiti] Coach context: %d categories, %d/%d tokens",
                len(result.categories_populated),
                result.budget_used,
                result.budget_total,
            )
            return result

        except Exception as e:
            logger.warning(f"Failed to retrieve Coach context for {task_id}: {e}")
            return self._empty_result(task_id)

    def _build_task_dict(
        self,
        task_id: str,
        feature_id: str,
        turn_number: int,
        description: str,
        tech_stack: str,
        complexity: int,
        current_actor: str,
        has_previous_turns: bool,
        previous_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build task dictionary for JobContextRetriever.

        Args:
            task_id: Task identifier
            feature_id: Feature identifier
            turn_number: Current turn number
            description: Task description
            tech_stack: Technology stack
            complexity: Task complexity
            current_actor: "player" or "coach"
            has_previous_turns: Whether there are previous turns
            previous_feedback: Optional feedback from previous turn

        Returns:
            Task dictionary with AutoBuild characteristics
        """
        task = {
            "id": task_id,
            "description": description,
            "tech_stack": tech_stack,
            "complexity": complexity,
            "is_autobuild": True,
            "feature_id": feature_id,
            "turn_number": turn_number,
            "current_actor": current_actor,
            "has_previous_turns": has_previous_turns,
        }

        # Add refinement attempt info for turn > 1
        if turn_number > 1:
            task["refinement_attempt"] = turn_number

        # Add previous feedback if available
        if previous_feedback:
            task["last_feedback"] = previous_feedback

        return task

    def _build_result(
        self,
        context: RetrievedContext,
        actor: str,
        turn_continuation: Optional[str] = None,
    ) -> AutoBuildContextResult:
        """Build AutoBuildContextResult from RetrievedContext.

        Args:
            context: Retrieved context from JobContextRetriever
            actor: "player" or "coach"
            turn_continuation: Optional formatted turn continuation context

        Returns:
            AutoBuildContextResult with formatted prompt
        """
        # Format prompt text
        prompt_text = context.to_prompt()

        # Append turn continuation context if available
        if turn_continuation:
            prompt_text += f"\n\n{turn_continuation}"

        # Identify populated categories
        categories = self._get_populated_categories(context)

        # Build verbose details if enabled
        verbose_details = None
        if self.verbose:
            verbose_details = self._format_verbose_details(context, categories)

        return AutoBuildContextResult(
            context=context,
            prompt_text=prompt_text,
            budget_used=context.budget_used,
            budget_total=context.budget_total,
            categories_populated=categories,
            verbose_details=verbose_details,
        )

    def _get_populated_categories(self, context: RetrievedContext) -> List[str]:
        """Get list of categories with content.

        Args:
            context: Retrieved context

        Returns:
            List of category names that have content
        """
        categories = []

        if context.feature_context:
            categories.append("feature_context")
        if context.similar_outcomes:
            categories.append("similar_outcomes")
        if context.relevant_patterns:
            categories.append("relevant_patterns")
        if context.architecture_context:
            categories.append("architecture_context")
        if context.warnings:
            categories.append("warnings")
        if context.domain_knowledge:
            categories.append("domain_knowledge")
        if context.role_constraints:
            categories.append("role_constraints")
        if context.quality_gate_configs:
            categories.append("quality_gate_configs")
        if context.turn_states:
            categories.append("turn_states")
        if context.implementation_modes:
            categories.append("implementation_modes")

        return categories

    def _format_verbose_details(
        self,
        context: RetrievedContext,
        categories: List[str],
    ) -> str:
        """Format verbose details for --verbose flag.

        Args:
            context: Retrieved context
            categories: List of populated categories

        Returns:
            Formatted string with verbose details
        """
        lines = []
        lines.append("=== Context Retrieval Details ===")
        lines.append(f"Task: {context.task_id}")
        lines.append(f"Budget: {context.budget_used}/{context.budget_total} tokens")
        lines.append(f"Categories populated: {len(categories)}")

        for cat in categories:
            cat_content = getattr(context, cat, [])
            lines.append(f"  - {cat}: {len(cat_content)} items")

        if context.quality_metrics:
            metrics = context.quality_metrics
            lines.append(f"Quality acceptable: {metrics.is_quality_acceptable()}")

        lines.append("=================================")

        return "\n".join(lines)

    def _empty_result(self, task_id: str) -> AutoBuildContextResult:
        """Create empty result for graceful degradation.

        Args:
            task_id: Task identifier

        Returns:
            Empty AutoBuildContextResult
        """
        empty_context = RetrievedContext(
            task_id=task_id,
            budget_used=0,
            budget_total=0,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        return AutoBuildContextResult(
            context=empty_context,
            prompt_text="",
            budget_used=0,
            budget_total=0,
            categories_populated=[],
            verbose_details=None,
        )
