"""Knowledge Gap Analyzer for Graphiti Integration.

This module identifies gaps in project knowledge by analyzing existing
knowledge in Graphiti and comparing it against a comprehensive question
template set.

The analyzer supports 9 knowledge categories including AutoBuild workflow
customization (role constraints, quality gates, workflow preferences).

Example Usage:
    analyzer = KnowledgeGapAnalyzer()
    gaps = await analyzer.analyze_gaps()
    for gap in gaps:
        print(f"{gap.category}: {gap.question}")

    # Focus on specific category
    arch_gaps = await analyzer.analyze_gaps(focus=KnowledgeCategory.ARCHITECTURE)

    # Limit number of questions
    top_gaps = await analyzer.analyze_gaps(max_questions=5)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any

from .graphiti_client import get_graphiti


class KnowledgeCategory(str, Enum):
    """Categories of project knowledge.

    This enum uses str as a mixin to allow string comparison and serialization.
    Categories include both traditional project knowledge and AutoBuild workflow
    customization areas.
    """

    PROJECT_OVERVIEW = "project_overview"
    ARCHITECTURE = "architecture"
    DOMAIN = "domain"
    CONSTRAINTS = "constraints"
    DECISIONS = "decisions"
    GOALS = "goals"
    # AutoBuild workflow customization categories (from TASK-REV-1505)
    ROLE_CUSTOMIZATION = "role_customization"
    QUALITY_GATES = "quality_gates"
    WORKFLOW_PREFERENCES = "workflow_preferences"


@dataclass
class KnowledgeGap:
    """Represents a gap in project knowledge.

    Attributes:
        category: The knowledge category this gap belongs to
        question: The question to ask the user
        importance: Priority level (high/medium/low)
        context: Explanation of why this question matters
        example_answer: Optional example of a good answer
    """

    category: KnowledgeCategory
    question: str
    importance: str  # high | medium | low
    context: str
    example_answer: Optional[str] = None


class KnowledgeGapAnalyzer:
    """Analyzes existing knowledge to identify gaps.

    The analyzer queries Graphiti for existing project knowledge and compares
    it against question templates to identify what information is missing.

    Supports focusing on specific categories and limiting the number of questions
    returned. Results are always sorted by importance (high → medium → low).
    """

    # Question templates by category with importance levels
    QUESTION_TEMPLATES = {
        KnowledgeCategory.PROJECT_OVERVIEW: [
            {
                "question": "What is the primary purpose of this project?",
                "importance": "high",
                "context": "Helps Claude understand the 'why' behind implementation decisions",
                "check_field": "purpose"
            },
            {
                "question": "Who are the target users of this project?",
                "importance": "medium",
                "context": "Influences UX decisions and documentation style",
                "check_field": "target_users"
            },
            {
                "question": "What are the key goals this project aims to achieve?",
                "importance": "high",
                "context": "Guides prioritization and feature decisions",
                "check_field": "goals"
            },
            {
                "question": "What problem does this project solve?",
                "importance": "high",
                "context": "Helps understand the value proposition",
                "check_field": "problem_statement"
            }
        ],
        KnowledgeCategory.ARCHITECTURE: [
            {
                "question": "What is the high-level architecture of this project?",
                "importance": "high",
                "context": "Essential for understanding how components fit together",
                "check_field": "architecture_summary"
            },
            {
                "question": "What are the main components or services?",
                "importance": "high",
                "context": "Helps scope tasks appropriately",
                "check_field": "key_components"
            },
            {
                "question": "What external APIs or services does this project integrate with?",
                "importance": "medium",
                "context": "Important for understanding dependencies",
                "check_field": "external_dependencies"
            },
            {
                "question": "What data flows through the system?",
                "importance": "medium",
                "context": "Helps understand data models and transformations",
                "check_field": "data_flow"
            }
        ],
        KnowledgeCategory.DOMAIN: [
            {
                "question": "What domain-specific terms should I understand?",
                "importance": "medium",
                "context": "Ensures correct terminology in code and docs",
                "check_field": "domain_terminology"
            },
            {
                "question": "Are there any business rules I should be aware of?",
                "importance": "medium",
                "context": "Prevents violations of domain constraints",
                "check_field": "business_rules"
            }
        ],
        KnowledgeCategory.CONSTRAINTS: [
            {
                "question": "What technical constraints does this project have?",
                "importance": "high",
                "context": "Prevents suggesting incompatible solutions",
                "check_field": "technical_constraints"
            },
            {
                "question": "Are there any business or time constraints?",
                "importance": "medium",
                "context": "Helps with prioritization and scope decisions",
                "check_field": "business_constraints"
            },
            {
                "question": "What technologies or approaches should be avoided?",
                "importance": "high",
                "context": "Prevents suggesting disallowed solutions",
                "check_field": "avoid_list"
            }
        ],
        KnowledgeCategory.DECISIONS: [
            {
                "question": "What key technology decisions have been made?",
                "importance": "high",
                "context": "Ensures consistency with existing choices",
                "check_field": "tech_decisions"
            },
            {
                "question": "Why were these technologies chosen over alternatives?",
                "importance": "medium",
                "context": "Helps understand trade-offs and rationale",
                "check_field": "decision_rationale"
            }
        ],
        KnowledgeCategory.GOALS: [
            {
                "question": "What are the key goals this project aims to achieve?",
                "importance": "high",
                "context": "Guides prioritization and feature decisions",
                "check_field": "goals"
            }
        ],
        # AutoBuild workflow customization categories (from TASK-REV-1505)
        KnowledgeCategory.ROLE_CUSTOMIZATION: [
            {
                "question": "What tasks should the AI Player ALWAYS ask about before implementing?",
                "importance": "high",
                "context": "Prevents autonomous changes to sensitive areas (from TASK-REV-7549)",
                "check_field": "player_ask_before"
            },
            {
                "question": "What decisions should the AI Coach escalate to humans rather than auto-approve?",
                "importance": "high",
                "context": "Defines human oversight boundaries (from TASK-REV-7549)",
                "check_field": "coach_escalate_when"
            },
            {
                "question": "Are there any areas where the AI should NEVER make changes autonomously?",
                "importance": "high",
                "context": "Defines hard boundaries for autonomous work",
                "check_field": "no_auto_zones"
            }
        ],
        KnowledgeCategory.QUALITY_GATES: [
            {
                "question": "What test coverage threshold is acceptable for this project?",
                "importance": "medium",
                "context": "Customizes quality gate thresholds (from TASK-REV-7549)",
                "check_field": "coverage_threshold",
                "example_answer": "80% for features, 60% for scaffolding"
            },
            {
                "question": "What architectural review score should block implementation?",
                "importance": "medium",
                "context": "Prevents threshold drift during sessions",
                "check_field": "arch_review_threshold",
                "example_answer": "Below 60 should block, 60-75 should warn"
            }
        ],
        KnowledgeCategory.WORKFLOW_PREFERENCES: [
            {
                "question": "Should complex tasks use task-work mode or direct implementation?",
                "importance": "medium",
                "context": "Clarifies implementation mode preferences (from TASK-REV-7549)",
                "check_field": "implementation_mode_preference"
            },
            {
                "question": "How many autonomous turns should feature-build attempt before asking for help?",
                "importance": "low",
                "context": "Prevents infinite loops in AutoBuild",
                "check_field": "max_auto_turns",
                "example_answer": "3-5 turns for most tasks, 1-2 for complex changes"
            }
        ]
    }

    def __init__(self):
        """Initialize the KnowledgeGapAnalyzer."""
        pass

    async def analyze_gaps(
        self,
        focus: Optional[KnowledgeCategory] = None,
        max_questions: int = 10
    ) -> List[KnowledgeGap]:
        """Analyze existing knowledge and identify gaps.

        Queries Graphiti for existing project knowledge and compares it against
        question templates to find missing information.

        Args:
            focus: Optional category to focus on. If None, checks all categories.
            max_questions: Maximum number of questions to return (default: 10).
                          If negative, returns empty list.
                          If 0, returns empty list.

        Returns:
            List of KnowledgeGap objects sorted by importance (high first).
            Empty list if:
            - max_questions <= 0
            - Graphiti is disabled or unavailable
            - No gaps found

        Example:
            # Get top 5 gaps across all categories
            gaps = await analyzer.analyze_gaps(max_questions=5)

            # Focus on architecture with unlimited questions
            arch_gaps = await analyzer.analyze_gaps(
                focus=KnowledgeCategory.ARCHITECTURE,
                max_questions=100
            )
        """
        # Handle edge cases
        if max_questions <= 0:
            return []

        # Get existing knowledge
        try:
            existing = await self._get_existing_knowledge()
        except Exception:
            # Graceful degradation - if Graphiti fails, return all gaps
            existing = {}

        # Determine which categories to check
        if focus is not None:
            categories = [focus]
        else:
            categories = list(KnowledgeCategory)

        # Find gaps
        gaps = []
        for category in categories:
            templates = self.QUESTION_TEMPLATES.get(category, [])

            for template in templates:
                # Check if we already have this knowledge
                check_field = template.get("check_field")
                if check_field and self._has_knowledge(existing, check_field):
                    continue

                # Create gap from template
                gaps.append(KnowledgeGap(
                    category=category,
                    question=template["question"],
                    importance=template["importance"],
                    context=template["context"],
                    example_answer=template.get("example_answer")
                ))

        # Sort by importance (high → medium → low)
        importance_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: importance_order[g.importance])

        # Limit to max_questions
        return gaps[:max_questions]

    async def _get_existing_knowledge(self) -> Dict[str, Any]:
        """Query Graphiti for existing project knowledge.

        Returns:
            Dictionary mapping check_fields to knowledge presence.
            Empty dict if Graphiti is unavailable or query fails.
        """
        # Get Graphiti instance
        graphiti = get_graphiti()

        # Handle Graphiti being None or disabled
        if graphiti is None:
            return {}

        if not graphiti.enabled:
            return {}

        try:
            # Query for various knowledge categories
            results = await graphiti.search(
                query="project overview architecture constraints goals",
                group_ids=[
                    "project_overview",
                    "project_architecture",
                    "project_constraints",
                    "project_decisions",
                    "domain_knowledge"
                ],
                num_results=20
            )

            # Aggregate into categories
            existing = {
                "purpose": None,
                "target_users": None,
                "goals": None,
                "problem_statement": None,
                "architecture_summary": None,
                "key_components": None,
                "external_dependencies": None,
                "data_flow": None,
                "domain_terminology": None,
                "business_rules": None,
                "technical_constraints": None,
                "business_constraints": None,
                "avoid_list": None,
                "tech_decisions": None,
                "decision_rationale": None,
                # AutoBuild fields
                "player_ask_before": None,
                "coach_escalate_when": None,
                "no_auto_zones": None,
                "coverage_threshold": None,
                "arch_review_threshold": None,
                "implementation_mode_preference": None,
                "max_auto_turns": None,
            }

            # Simple heuristic to check coverage
            for result in results:
                fact = result.get("fact", "")
                fact_lower = fact.lower()

                # Map facts to fields using simple keyword matching
                if "purpose" in fact_lower:
                    existing["purpose"] = fact
                if "user" in fact_lower and "target" in fact_lower:
                    existing["target_users"] = fact
                if "goal" in fact_lower:
                    existing["goals"] = fact
                if "problem" in fact_lower:
                    existing["problem_statement"] = fact
                if "architecture" in fact_lower:
                    existing["architecture_summary"] = fact
                if "component" in fact_lower:
                    existing["key_components"] = fact
                # Add more mappings as needed

            return existing

        except Exception:
            # Graceful degradation on any error
            return {}

    def _has_knowledge(self, existing: Dict[str, Any], field: str) -> bool:
        """Check if we have knowledge for a field.

        Args:
            existing: Dictionary of existing knowledge
            field: Field name to check

        Returns:
            True if knowledge exists for this field, False otherwise
        """
        return existing.get(field) is not None
