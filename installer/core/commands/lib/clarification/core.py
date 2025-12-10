"""Core infrastructure for the unified clarification module.

This module provides shared dataclasses, response processing functions, and prompt
formatting utilities for all clarification contexts (review scope, implementation
preferences, implementation planning).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
import yaml


class ClarificationMode(Enum):
    """Mode for clarification prompts."""
    SKIP = "skip"              # Skip all questions
    QUICK = "quick"            # 2-3 critical questions
    FULL = "full"              # All relevant questions
    USE_DEFAULTS = "defaults"  # Use defaults without asking


@dataclass
class Question:
    """Single clarification question."""
    id: str                    # Unique identifier (e.g., "scope_01")
    category: str              # "scope", "technology", "trade-off", etc.
    text: str                  # Full question text
    options: List[str]         # Available options
    default: str               # Default option
    rationale: str             # Why this default was chosen

    def __post_init__(self):
        """Validate question data."""
        if not self.id:
            raise ValueError("Question ID cannot be empty")
        if not self.text:
            raise ValueError("Question text cannot be empty")
        if not self.options:
            raise ValueError("Question must have at least one option")
        if self.default not in self.options:
            raise ValueError(f"Default '{self.default}' must be in options")


@dataclass
class Decision:
    """Single clarification decision."""
    question_id: str           # Unique question identifier (e.g., "scope_01")
    category: str              # "scope", "technology", "trade-off", etc.
    question_text: str         # Full question text
    answer: str                # User's answer or default (short form)
    answer_display: str        # Full answer text for display
    default_used: bool         # True if user used default (alias for is_default)
    rationale: str             # Why this default was chosen
    confidence: float = 1.0    # 0-1, lower if assumed

    def __post_init__(self):
        """Validate decision data."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

    @property
    def is_default(self) -> bool:
        """Backward compatibility alias for default_used."""
        return self.default_used

    @property
    def question(self) -> str:
        """Backward compatibility alias for question_text."""
        return self.question_text


@dataclass
class ClarificationContext:
    """Context passed to planning/review agents."""
    context_type: str = "implementation_planning"  # or "review_scope", "implementation_prefs"
    explicit_decisions: List[Decision] = field(default_factory=list)
    assumed_defaults: List[Decision] = field(default_factory=list)
    not_applicable: List[str] = field(default_factory=list)
    total_questions: int = 0
    answered_count: int = 0
    skipped_count: int = 0
    complexity_triggered: bool = False
    user_override: Optional[str] = None  # "skip", "defaults", etc.
    timestamp: datetime = field(default_factory=datetime.utcnow)
    mode: str = "full"  # "skip", "quick", or "full"

    def add_decision(self, decision: Decision) -> None:
        """Add a decision to the appropriate list."""
        if decision.is_default:
            self.assumed_defaults.append(decision)
        else:
            self.explicit_decisions.append(decision)
        self.answered_count += 1

    def add_skipped(self, question_id: str) -> None:
        """Mark a question as skipped."""
        self.not_applicable.append(question_id)
        self.skipped_count += 1

    @property
    def is_complete(self) -> bool:
        """Check if all questions have been addressed."""
        if self.total_questions == 0:
            return False
        return (self.answered_count + self.skipped_count) == self.total_questions

    @property
    def has_explicit_decisions(self) -> bool:
        """Check if any explicit decisions were made."""
        return len(self.explicit_decisions) > 0

    @property
    def decisions(self) -> List[Decision]:
        """Get all decisions (explicit + assumed defaults)."""
        return self.explicit_decisions + self.assumed_defaults

    def persist_to_frontmatter(self, task_path: Path) -> None:
        """Persist clarification decisions to task frontmatter.

        Args:
            task_path: Path to task markdown file

        Raises:
            ValueError: If task file has invalid frontmatter
        """
        # Read existing frontmatter
        content = task_path.read_text()
        frontmatter, body = parse_frontmatter(content)

        # Get all decisions (explicit + assumed defaults)
        all_decisions = self.explicit_decisions + self.assumed_defaults

        # Add clarification section
        frontmatter['clarification'] = {
            'context': self.context_type,
            'timestamp': self.timestamp.isoformat(),
            'mode': self.mode,
            'decisions': [
                {
                    'question_id': d.question_id,
                    'category': d.category,
                    'question': d.question_text,
                    'answer': d.answer,
                    'answer_text': d.answer_display,
                    'default_used': d.default_used,
                    'rationale': d.rationale,
                }
                for d in all_decisions
            ]
        }

        # Write back
        new_content = serialize_frontmatter(frontmatter) + body
        task_path.write_text(new_content)

    @classmethod
    def load_from_frontmatter(cls, task_path: Path) -> Optional['ClarificationContext']:
        """Load previous clarification decisions from task frontmatter.

        Args:
            task_path: Path to task markdown file

        Returns:
            ClarificationContext if found, None otherwise

        Examples:
            >>> from pathlib import Path
            >>> path = Path("tasks/backlog/TASK-123.md")
            >>> ctx = ClarificationContext.load_from_frontmatter(path)
            >>> ctx is None or isinstance(ctx, ClarificationContext)
            True
        """
        if not task_path.exists():
            return None

        content = task_path.read_text()
        frontmatter, _ = parse_frontmatter(content)

        if 'clarification' not in frontmatter:
            return None

        clr = frontmatter['clarification']
        decisions = []

        for d in clr.get('decisions', []):
            decision = Decision(
                question_id=d['question_id'],
                category=d['category'],
                question_text=d['question'],
                answer=d['answer'],
                answer_display=d['answer_text'],
                default_used=d['default_used'],
                rationale=d['rationale'],
            )
            decisions.append(decision)

        # Create context with decisions
        ctx = cls(
            context_type=clr['context'],
            timestamp=datetime.fromisoformat(clr['timestamp']),
            mode=clr['mode'],
        )

        # Add decisions to appropriate lists
        for d in decisions:
            if d.default_used:
                ctx.assumed_defaults.append(d)
            else:
                ctx.explicit_decisions.append(d)

        ctx.total_questions = len(decisions)
        ctx.answered_count = len(decisions)

        return ctx


def should_clarify(
    context_type: Literal["review", "implement_prefs", "planning"],
    complexity: int,
    flags: Dict[str, Any]
) -> ClarificationMode:
    """Determine clarification mode based on context and complexity.

    Args:
        context_type: Type of clarification context
        complexity: Task complexity score (0-10)
        flags: Command-line flags and options

    Returns:
        ClarificationMode indicating how to proceed

    Examples:
        >>> should_clarify("review", 3, {"no_questions": True})
        ClarificationMode.SKIP

        >>> should_clarify("planning", 6, {})
        ClarificationMode.FULL

        >>> should_clarify("implement_prefs", 4, {"defaults": True})
        ClarificationMode.USE_DEFAULTS
    """
    # Universal skip conditions
    if flags.get("no_questions", False):
        return ClarificationMode.SKIP
    if flags.get("micro", False):
        return ClarificationMode.SKIP
    if flags.get("defaults", False):
        return ClarificationMode.USE_DEFAULTS

    # Context-specific thresholds
    thresholds = {
        "review": {"skip": 2, "quick": 4, "full": 6},
        "implement_prefs": {"skip": 3, "quick": 5, "full": 7},
        "planning": {"skip": 2, "quick": 4, "full": 5},
    }

    context_thresholds = thresholds.get(context_type, thresholds["review"])

    if complexity <= context_thresholds["skip"]:
        return ClarificationMode.SKIP
    elif complexity <= context_thresholds["quick"]:
        return ClarificationMode.QUICK
    else:
        return ClarificationMode.FULL


def process_responses(
    questions: List[Question],
    user_input: Dict[str, str],
    mode: ClarificationMode
) -> ClarificationContext:
    """Process user responses and create clarification context.

    Args:
        questions: List of questions that were (or could be) asked
        user_input: Dictionary mapping question IDs to user answers
        mode: Clarification mode that was used

    Returns:
        ClarificationContext with processed decisions

    Examples:
        >>> questions = [
        ...     Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default"),
        ...     Question("q2", "tech", "Use async?", ["yes", "no"], "no", "Simple cases")
        ... ]
        >>> responses = {"q1": "yes", "q2": "yes"}
        >>> ctx = process_responses(questions, responses, ClarificationMode.FULL)
        >>> ctx.answered_count
        2
        >>> ctx.explicit_decisions[0].answer
        'yes'
    """
    context = ClarificationContext(
        total_questions=len(questions),
        complexity_triggered=(mode in [ClarificationMode.QUICK, ClarificationMode.FULL])
    )

    for question in questions:
        # Check if user provided an answer
        user_answer = user_input.get(question.id)

        if user_answer is None:
            # Question was skipped
            context.add_skipped(question.id)
            continue

        # Determine if user used the default
        is_default = (user_answer == question.default)

        # Confidence is higher for explicit choices
        confidence = 0.7 if is_default else 1.0

        # Create decision
        decision = Decision(
            question_id=question.id,
            category=question.category,
            question_text=question.text,
            answer=user_answer,
            answer_display=user_answer,  # For now, use same as answer
            default_used=is_default,
            confidence=confidence,
            rationale=question.rationale if is_default else f"User explicitly chose: {user_answer}"
        )

        context.add_decision(decision)

    # Record the mode used
    if mode == ClarificationMode.SKIP:
        context.user_override = "skip"
    elif mode == ClarificationMode.USE_DEFAULTS:
        context.user_override = "defaults"

    return context


def format_for_prompt(context: ClarificationContext) -> str:
    """Format clarification context for agent prompts.

    Args:
        context: ClarificationContext to format

    Returns:
        Formatted string for inclusion in agent prompts

    Examples:
        >>> ctx = ClarificationContext(
        ...     explicit_decisions=[
        ...         Decision("scope", "Include tests?", "yes", False, 1.0, "User choice")
        ...     ],
        ...     assumed_defaults=[
        ...         Decision("tech", "Use async?", "no", True, 0.7, "Simple case")
        ...     ],
        ...     total_questions=2,
        ...     answered_count=2
        ... )
        >>> output = format_for_prompt(ctx)
        >>> "EXPLICIT DECISIONS" in output
        True
        >>> "yes" in output
        True
    """
    if not context.explicit_decisions and not context.assumed_defaults:
        # Still show summary if there's a user override or skipped questions
        if context.user_override or context.skipped_count > 0:
            lines = ["# Clarification Context"]
            lines.append("")
            lines.append(f"Total Questions: {context.total_questions}")
            lines.append(f"Answered: {context.answered_count}")
            lines.append(f"Skipped: {context.skipped_count}")
            if context.user_override:
                lines.append(f"User Override: {context.user_override}")
            lines.append("")
            lines.append("No clarification questions were asked (complexity too low or skipped).")
            return "\n".join(lines)
        return "No clarification questions were asked (complexity too low or skipped)."

    lines = ["# Clarification Context"]
    lines.append("")

    # Summary
    lines.append(f"Total Questions: {context.total_questions}")
    lines.append(f"Answered: {context.answered_count}")
    lines.append(f"Skipped: {context.skipped_count}")
    if context.user_override:
        lines.append(f"User Override: {context.user_override}")
    lines.append("")

    # Explicit decisions
    if context.explicit_decisions:
        lines.append("## EXPLICIT DECISIONS (User Provided)")
        lines.append("")
        for decision in context.explicit_decisions:
            lines.append(f"**{decision.category.title()}**: {decision.question}")
            lines.append(f"- Answer: {decision.answer}")
            lines.append(f"- Confidence: {decision.confidence:.0%}")
            lines.append(f"- Rationale: {decision.rationale}")
            lines.append("")

    # Assumed defaults
    if context.assumed_defaults:
        lines.append("## ASSUMED DEFAULTS (Not Explicitly Confirmed)")
        lines.append("")
        for decision in context.assumed_defaults:
            lines.append(f"**{decision.category.title()}**: {decision.question}")
            lines.append(f"- Default: {decision.answer}")
            lines.append(f"- Confidence: {decision.confidence:.0%}")
            lines.append(f"- Rationale: {decision.rationale}")
            lines.append("")

    # Not applicable questions
    if context.not_applicable:
        lines.append("## NOT APPLICABLE")
        lines.append("")
        lines.append(f"Skipped {len(context.not_applicable)} question(s) as not relevant to this task.")
        lines.append("")

    return "\n".join(lines)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content with frontmatter

    Returns:
        Tuple of (frontmatter dict, body text)

    Examples:
        >>> content = "---\\nid: TASK-123\\n---\\nBody text"
        >>> fm, body = parse_frontmatter(content)
        >>> fm['id']
        'TASK-123'
    """
    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2]
    return frontmatter, body


def serialize_frontmatter(frontmatter: dict) -> str:
    """Serialize frontmatter dict to YAML string.

    Args:
        frontmatter: Dictionary to serialize

    Returns:
        YAML string with frontmatter delimiters

    Examples:
        >>> fm = {'id': 'TASK-123', 'title': 'Test'}
        >>> yaml_str = serialize_frontmatter(fm)
        >>> yaml_str.startswith('---\\n')
        True
    """
    return '---\n' + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + '---\n'


def get_clarification_summary(task_path: Path) -> str:
    """Generate human-readable summary of clarification decisions.

    Args:
        task_path: Path to task markdown file

    Returns:
        Human-readable summary string

    Examples:
        >>> from pathlib import Path
        >>> path = Path("tasks/backlog/TASK-123.md")
        >>> summary = get_clarification_summary(path)
        >>> "No clarification recorded" in summary or "Clarification:" in summary
        True
    """
    ctx = ClarificationContext.load_from_frontmatter(task_path)
    if not ctx:
        return "No clarification recorded"

    lines = [
        f"Clarification: {ctx.context_type}",
        f"Mode: {ctx.mode}",
        f"Timestamp: {ctx.timestamp}",
        f"Decisions ({len(ctx.decisions)}):",
    ]

    for d in ctx.decisions:
        default_marker = " (default)" if d.default_used else ""
        lines.append(f"  - {d.question_id}: {d.answer_display}{default_marker}")

    return "\n".join(lines)


