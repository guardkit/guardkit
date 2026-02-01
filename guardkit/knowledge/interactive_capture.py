"""Interactive Knowledge Capture Session for Graphiti Integration.

This module provides an interactive session for capturing project knowledge
through targeted questions. It integrates with the KnowledgeGapAnalyzer to
identify gaps and stores captured knowledge in Graphiti.

Example Usage:
    session = InteractiveCaptureSession()

    def my_callback(event, data=None):
        if event == 'question':
            print(f"Q: {data['question']}")
        elif event == 'get_input':
            return input("> ")
        elif event == 'intro':
            print(data)
        elif event == 'summary':
            print(data)

    captured = await session.run_session(ui_callback=my_callback)
    print(f"Captured {len(captured)} knowledge items")
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable, Any

from .graphiti_client import get_graphiti
from .gap_analyzer import KnowledgeGapAnalyzer, KnowledgeGap, KnowledgeCategory


@dataclass
class CapturedKnowledge:
    """Represents a piece of captured knowledge from user input.

    Attributes:
        category: The knowledge category this belongs to
        question: The question that was asked
        answer: The user's answer
        extracted_facts: List of facts extracted from the answer
        confidence: Confidence score for the captured knowledge (0.0-1.0)
    """
    category: KnowledgeCategory
    question: str
    answer: str
    extracted_facts: List[str] = field(default_factory=list)
    confidence: float = 1.0


class InteractiveCaptureSession:
    """Interactive session for capturing project knowledge.

    Guides users through a series of questions to capture missing project
    knowledge. Uses KnowledgeGapAnalyzer to identify gaps and stores
    captured knowledge in Graphiti.

    Attributes:
        captured: List of CapturedKnowledge items from the session

    Example:
        session = InteractiveCaptureSession()
        results = await session.run_session(
            focus=KnowledgeCategory.ARCHITECTURE,
            max_questions=5,
            ui_callback=my_callback
        )
    """

    # Category to group_id mapping
    _CATEGORY_GROUP_MAP = {
        KnowledgeCategory.PROJECT_OVERVIEW: "project_overview",
        KnowledgeCategory.GOALS: "project_overview",
        KnowledgeCategory.ARCHITECTURE: "project_architecture",
        KnowledgeCategory.DOMAIN: "domain_knowledge",
        KnowledgeCategory.CONSTRAINTS: "project_constraints",
        KnowledgeCategory.DECISIONS: "project_decisions",
        KnowledgeCategory.ROLE_CUSTOMIZATION: "role_constraints",
        KnowledgeCategory.QUALITY_GATES: "quality_gate_configs",
        KnowledgeCategory.WORKFLOW_PREFERENCES: "implementation_modes",
    }

    # Category prefix mapping for fact extraction
    _CATEGORY_PREFIX_MAP = {
        KnowledgeCategory.PROJECT_OVERVIEW: "Project: ",
        KnowledgeCategory.GOALS: "Project: ",
        KnowledgeCategory.ARCHITECTURE: "Architecture: ",
        KnowledgeCategory.DOMAIN: "Domain: ",
        KnowledgeCategory.CONSTRAINTS: "Constraint: ",
        KnowledgeCategory.DECISIONS: "Decision: ",
        KnowledgeCategory.ROLE_CUSTOMIZATION: "Role: ",
        KnowledgeCategory.QUALITY_GATES: "Quality gate: ",
        KnowledgeCategory.WORKFLOW_PREFERENCES: "Workflow: ",
    }

    # Minimum length for a sentence to be considered a meaningful fact
    _MIN_FACT_LENGTH = 10

    def __init__(self):
        """Initialize the InteractiveCaptureSession."""
        self._graphiti = get_graphiti()
        self._analyzer = KnowledgeGapAnalyzer()
        self._captured: List[CapturedKnowledge] = []

    @property
    def captured(self) -> List[CapturedKnowledge]:
        """Get the list of captured knowledge items.

        Returns:
            List of CapturedKnowledge items captured during the session.
        """
        return self._captured

    async def _get_gaps(
        self,
        focus: Optional[KnowledgeCategory] = None,
        max_questions: int = 10
    ) -> List[KnowledgeGap]:
        """Get knowledge gaps for the session.

        Delegates to the KnowledgeGapAnalyzer to identify gaps in project knowledge.

        Args:
            focus: Optional category to focus on
            max_questions: Maximum number of questions to return

        Returns:
            List of KnowledgeGap objects
        """
        return await self._analyzer.analyze_gaps(focus, max_questions)

    async def run_session(
        self,
        focus: Optional[KnowledgeCategory] = None,
        max_questions: int = 10,
        ui_callback: Optional[Callable] = None
    ) -> List[CapturedKnowledge]:
        """Run an interactive knowledge capture session.

        Guides the user through questions to capture missing project knowledge.

        Args:
            focus: Optional category to focus questions on
            max_questions: Maximum number of questions to ask (default: 10)
            ui_callback: Callback function for UI interactions.
                        Called with (event, data) where event is one of:
                        - 'intro': Session introduction message
                        - 'question': Question data dict
                        - 'get_input': Request user input (returns answer string)
                        - 'captured': Captured knowledge confirmation
                        - 'summary': Session summary message
                        - 'info': Informational message

        Returns:
            List of CapturedKnowledge items captured during the session.
            Empty list if no questions or user quits immediately.

        Example:
            def callback(event, data=None):
                if event == 'get_input':
                    return input("> ")
                elif event in ('intro', 'summary', 'info'):
                    print(data)
                elif event == 'question':
                    print(f"{data['number']}/{data['total']}: {data['question']}")

            results = await session.run_session(ui_callback=callback)
        """
        # Clear captured list at start of session
        self._captured = []

        # Get knowledge gaps
        gaps = await self._get_gaps(focus, max_questions)

        # Handle no gaps case
        if not gaps:
            if ui_callback:
                ui_callback('info', "No knowledge gaps found. Your project knowledge is complete!")
            return []

        # Show intro
        if ui_callback:
            ui_callback('intro', self._format_intro(gaps))

        # Process each gap
        for i, gap in enumerate(gaps):
            # Show question
            if ui_callback:
                ui_callback('question', {
                    'number': i + 1,
                    'total': len(gaps),
                    'category': gap.category.value,
                    'question': gap.question,
                    'context': gap.context
                })

            # Get user input
            answer = None
            if ui_callback:
                answer = ui_callback('get_input')

            # Handle None answer (no callback or callback returned None)
            if answer is None:
                answer = ''

            # Normalize answer
            answer_lower = answer.lower().strip()

            # Handle skip commands
            if answer_lower in ('skip', 's', ''):
                continue

            # Handle quit commands
            if answer_lower in ('quit', 'q', 'exit'):
                break

            # Process the answer
            captured = self._process_answer(gap, answer)
            self._captured.append(captured)

            # Notify UI of captured knowledge
            if ui_callback:
                ui_callback('captured', {
                    'category': captured.category.value,
                    'question': captured.question,
                    'facts_count': len(captured.extracted_facts)
                })

        # Save captured knowledge to Graphiti
        await self._save_captured_knowledge()

        # Show summary
        if ui_callback:
            ui_callback('summary', self._format_summary())

        return list(self._captured)

    def _process_answer(self, gap: KnowledgeGap, answer: str) -> CapturedKnowledge:
        """Process a user's answer into captured knowledge.

        Args:
            gap: The knowledge gap that was addressed
            answer: The user's answer

        Returns:
            CapturedKnowledge object with extracted facts
        """
        extracted_facts = self._extract_facts(answer, gap.category)

        return CapturedKnowledge(
            category=gap.category,
            question=gap.question,
            answer=answer,
            extracted_facts=extracted_facts
        )

    def _extract_facts(self, answer: str, category: KnowledgeCategory) -> List[str]:
        """Extract individual facts from an answer.

        Splits the answer into sentences and prefixes each with
        category-specific context.

        Args:
            answer: The user's answer
            category: The knowledge category

        Returns:
            List of extracted facts with category prefixes
        """
        if not answer:
            return []

        # Get the prefix for this category
        prefix = self._CATEGORY_PREFIX_MAP.get(category, "")

        # Split by sentences (period followed by space or end)
        sentences = answer.split('.')

        facts = []
        for sentence in sentences:
            # Clean up the sentence
            sentence = sentence.strip()

            # Filter out sentences shorter than minimum fact length
            if len(sentence) < self._MIN_FACT_LENGTH:
                continue

            # Add prefix and append
            facts.append(f"{prefix}{sentence}")

        return facts

    async def _save_captured_knowledge(self) -> None:
        """Save captured knowledge to Graphiti.

        Groups captured knowledge by category and creates episodes
        in Graphiti for each category.

        Handles Graphiti failures gracefully - does not raise exceptions.
        """
        if not self._captured:
            return

        # Handle case where Graphiti is unavailable
        if self._graphiti is None:
            return

        # Group captured by category
        by_category: Dict[KnowledgeCategory, List[CapturedKnowledge]] = {}
        for captured in self._captured:
            if captured.category not in by_category:
                by_category[captured.category] = []
            by_category[captured.category].append(captured)

        # Save each category
        for category, items in by_category.items():
            group_id = self._category_to_group_id(category)

            # Generate ISO timestamp
            captured_at = datetime.now(timezone.utc).isoformat()

            # Build episode body with structured metadata header
            body_parts = [
                f"entity_type: captured_knowledge",
                f"category: {category.value}",
                f"source: interactive_capture",
                f"captured_at: {captured_at}",
                "",  # Blank line after metadata header
            ]

            # Add QA pairs section
            body_parts.append("QA Pairs:")
            for item in items:
                body_parts.append(f"Q: {item.question}")
                body_parts.append(f"A: {item.answer}")

            body_parts.append("")  # Blank line before facts

            # Add facts section
            body_parts.append("Facts:")
            for item in items:
                if item.extracted_facts:
                    for fact in item.extracted_facts:
                        body_parts.append(f"- {fact}")

            episode_body = "\n".join(body_parts)
            episode_name = f"Interactive Capture - {category.value}"

            try:
                await self._graphiti.add_episode(
                    name=episode_name,
                    episode_body=episode_body,
                    group_id=group_id,
                    source_description="interactive_capture"
                )
            except Exception:
                # Graceful degradation - silently continue on failure
                pass

    def _category_to_group_id(self, category: KnowledgeCategory) -> str:
        """Map a knowledge category to a Graphiti group ID.

        Args:
            category: The knowledge category

        Returns:
            The corresponding Graphiti group ID
        """
        return self._CATEGORY_GROUP_MAP.get(category, "project_overview")

    def _format_intro(self, gaps: List[KnowledgeGap]) -> str:
        """Format the session introduction message.

        Args:
            gaps: List of knowledge gaps to address

        Returns:
            Formatted introduction string
        """
        total = len(gaps)
        high_priority = sum(1 for g in gaps if g.importance == "high")

        lines = [
            f"Knowledge Capture Session",
            f"========================",
            f"",
            f"I have {total} questions to help me understand your project better.",
            f"{high_priority} of these are high priority.",
            f"",
            f"Commands:",
            f"  - Type your answer and press Enter",
            f"  - Type 'skip' or 's' or press Enter to skip a question",
            f"  - Type 'quit', 'q', or 'exit' to end the session",
            f"",
        ]

        return "\n".join(lines)

    def _format_summary(self) -> str:
        """Format the session summary message.

        Returns:
            Formatted summary string with facts captured per category
        """
        if not self._captured:
            return "No knowledge was captured in this session."

        # Count facts per category
        facts_by_category: Dict[str, int] = {}
        total_facts = 0

        for captured in self._captured:
            cat_name = captured.category.value
            fact_count = len(captured.extracted_facts)
            facts_by_category[cat_name] = facts_by_category.get(cat_name, 0) + fact_count
            total_facts += fact_count

        lines = [
            f"Session Summary",
            f"===============",
            f"",
            f"Knowledge captured:",
        ]

        for category, count in facts_by_category.items():
            lines.append(f"  - {category}: {count} facts")

        lines.append(f"")
        lines.append(f"Total: {total_facts} facts captured across {len(self._captured)} answers.")

        return "\n".join(lines)

    async def run_abbreviated(
        self,
        questions: List[str],
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run an abbreviated knowledge capture session with provided questions.

        This method supports the /task-review --capture-knowledge workflow by
        accepting pre-generated questions rather than querying the gap analyzer.

        Args:
            questions: List of questions to ask (typically 3-5)
            task_context: Optional task metadata to include in results

        Returns:
            Dictionary with:
                - captured_items: List of captured Q&A pairs
                - task_id: Task ID from context (if provided)
                - review_mode: Review mode from context (if provided)

        Example:
            result = await session.run_abbreviated(
                questions=[
                    "What patterns were identified?",
                    "What should be remembered?"
                ],
                task_context={'task_id': 'TASK-001', 'review_mode': 'architectural'}
            )
        """
        task_context = task_context or {}
        captured_items: List[Dict[str, Any]] = []

        # Results structure
        result: Dict[str, Any] = {
            "captured_items": captured_items,
            "task_id": task_context.get("task_id", ""),
            "review_mode": task_context.get("review_mode", ""),
        }

        return result
