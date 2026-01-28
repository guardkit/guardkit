"""
Decision Significance Detector.

Analyzes question-answer pairs to detect significant decisions that should
be captured as Architecture Decision Records (ADRs).

Public API:
    DecisionDetector: Main class for detecting and extracting decisions

Example:
    from guardkit.knowledge.decision_detector import DecisionDetector
    from guardkit.knowledge.adr import ADRTrigger

    detector = DecisionDetector(significance_threshold=0.4)

    question = "Which database should we use?"
    answer = "PostgreSQL for ACID compliance"

    significance = detector.detect_significance(question, answer)
    if significance > detector.significance_threshold:
        adr = detector.create_adr_from_decision(
            question=question,
            answer=answer,
            trigger=ADRTrigger.CLARIFYING_QUESTION
        )
"""

import logging
import re
from typing import Dict, List, Optional

from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger

logger = logging.getLogger(__name__)


# Keywords that indicate high-significance decisions
HIGH_SIGNIFICANCE_KEYWORDS = {
    # Architectural decisions
    "architecture", "architectural", "structure", "design", "pattern",
    "microservices", "monolith", "service", "layer", "testability",
    "dependency injection", "injection",
    # Technology choices
    "database", "framework", "library", "technology", "stack",
    "postgresql", "mysql", "mongodb", "redis", "docker",
    # Approach decisions
    "approach", "strategy", "method", "methodology", "acid",
    # Authentication/Security
    "authentication", "authorization", "oauth", "jwt", "security",
    # Integration decisions
    "api", "graphql", "rest", "grpc",
    # Performance decisions
    "caching", "performance", "scalability",
    # Deployment
    "deployment", "environment", "environments",
}

# Keywords that indicate low-significance (trivial) decisions
LOW_SIGNIFICANCE_KEYWORDS = {
    "name", "naming", "variable", "rename",
    "comment", "comments",
    "format", "formatting", "indent",
    "color", "style", "css",
    "typo", "spelling",
}

# Keywords that indicate medium-significance decisions
MEDIUM_SIGNIFICANCE_KEYWORDS = {
    "logging",
    "error handling", "validation",
}

# Patterns that indicate rationale in answers
RATIONALE_PATTERNS = [
    r"because\s+(.+?)(?:\.|$)",
    r"since\s+(.+?)(?:\.|$)",
    r"as\s+(.+?)(?:,|\.|$)",
    r"for\s+(.+?)(?:\.|$)",
    r"due to\s+(.+?)(?:\.|$)",
]

# Patterns that indicate alternatives in answers
ALTERNATIVE_PATTERNS = [
    r"(?:over|versus|vs\.?)\s+(\w+(?:\s+or\s+\w+)*)",
    r"instead of\s+(\w+(?:\s+or\s+\w+)*)",
    r"rather than\s+(\w+(?:\s+or\s+\w+)*)",
    r"(?:not|don't use)\s+(\w+)",
    # Handle "PostgreSQL over MySQL or MongoDB" pattern
    r"\w+\s+over\s+(\w+)",
]


class DecisionDetector:
    """Detects significant decisions from Q&A pairs.

    Analyzes clarifying questions and answers to determine if they represent
    significant architectural or design decisions that should be captured
    as ADRs.

    Attributes:
        significance_threshold: Minimum significance score (0-1) for ADR creation

    Example:
        detector = DecisionDetector(significance_threshold=0.4)

        sig = detector.detect_significance(
            "Which authentication method?",
            "JWT for stateless scalability"
        )

        if sig > detector.significance_threshold:
            adr = detector.create_adr_from_decision(...)
    """

    def __init__(self, significance_threshold: float = 0.4):
        """Initialize DecisionDetector with a significance threshold.

        Args:
            significance_threshold: Minimum score (0-1) for ADR creation.
                                   Default is 0.4.

        Raises:
            ValueError: If threshold is not between 0 and 1.
        """
        if significance_threshold < 0 or significance_threshold > 1:
            raise ValueError(
                f"significance_threshold must be between 0 and 1, "
                f"got {significance_threshold}"
            )
        self.significance_threshold = significance_threshold

    def detect_significance(self, question: str, answer: str) -> float:
        """Detect the significance of a Q&A pair.

        Analyzes the question and answer to determine if they represent
        a significant decision worthy of an ADR.

        Scoring factors:
        - High-significance keywords (architecture, database, etc.)
        - Answer length and complexity
        - Presence of rationale ("because...")
        - Low-significance keywords reduce score

        Args:
            question: The clarifying question asked
            answer: The answer provided

        Returns:
            Significance score between 0.0 and 1.0.
            Higher scores indicate more significant decisions.

        Example:
            sig = detector.detect_significance(
                "Which database?",
                "PostgreSQL for ACID compliance"
            )
            assert sig > 0.6  # High significance
        """
        # Empty inputs get 0 significance
        if not question or not answer:
            return 0.0

        score = 0.0
        combined_text = (question + " " + answer).lower()

        # Check for high-significance keywords
        high_keyword_count = sum(
            1 for kw in HIGH_SIGNIFICANCE_KEYWORDS
            if kw in combined_text
        )
        score += min(high_keyword_count * 0.2, 0.6)  # Max 0.6 from keywords

        # Check for low-significance keywords (reduce score)
        low_keyword_count = sum(
            1 for kw in LOW_SIGNIFICANCE_KEYWORDS
            if kw in combined_text
        )
        score -= low_keyword_count * 0.15

        # Check for medium-significance keywords (moderate boost)
        medium_keyword_count = sum(
            1 for kw in MEDIUM_SIGNIFICANCE_KEYWORDS
            if kw in combined_text
        )
        score += min(medium_keyword_count * 0.1, 0.3)  # Max 0.3 from medium keywords

        # Short answers are less significant
        answer_words = len(answer.split())
        if answer_words <= 2:
            score -= 0.3
        elif answer_words >= 10:
            score += 0.15

        # Rationale presence increases significance
        has_rationale = any(
            re.search(pattern, answer.lower())
            for pattern in RATIONALE_PATTERNS
        )
        if has_rationale:
            score += 0.25

        # Questions about "should" or "which" suggest decision points
        question_lower = question.lower()
        if any(word in question_lower for word in ["should", "which", "how should"]):
            score += 0.15

        # Yes/No answers are low significance
        if answer.strip().lower() in ["yes", "no", "y", "n", "ok", "okay"]:
            score -= 0.5

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def extract_decision_context(
        self,
        question: str,
        answer: str
    ) -> Dict[str, str | List[str]]:
        """Extract decision context from a Q&A pair.

        Parses the question and answer to extract structured context
        including the decision made, rationale, and alternatives considered.

        Args:
            question: The clarifying question asked
            answer: The answer provided

        Returns:
            Dictionary with keys:
            - question: Original question
            - answer: Original answer
            - rationale: Extracted rationale (if found)
            - alternatives: List of alternatives mentioned

        Example:
            context = detector.extract_decision_context(
                "Database choice?",
                "PostgreSQL over MySQL because ACID compliance"
            )
            assert context["rationale"] == "ACID compliance"
            assert "MySQL" in context["alternatives"]
        """
        context: Dict[str, str | List[str]] = {
            "question": question,
            "answer": answer,
            "rationale": "",
            "alternatives": [],
        }

        answer_lower = answer.lower()

        # Extract rationale
        for pattern in RATIONALE_PATTERNS:
            match = re.search(pattern, answer_lower)
            if match:
                context["rationale"] = match.group(1).strip()
                break

        # Extract alternatives
        alternatives = []

        # First check for "X over Y or Z" pattern - use original answer for case
        over_match = re.search(r"\w+\s+over\s+(.+?)(?:because|$)", answer, re.IGNORECASE)
        if over_match:
            alt_text = over_match.group(1).strip()
            # Split on "or" to get individual alternatives
            alts = re.split(r"\s+or\s+", alt_text, flags=re.IGNORECASE)
            for a in alts:
                a_clean = a.strip()
                if a_clean:
                    alternatives.append(a_clean)

        # Then try other patterns on lowercase
        for pattern in ALTERNATIVE_PATTERNS:
            match = re.search(pattern, answer_lower)
            if match:
                # Get position from match and extract from original answer
                start = match.start(1)
                end = match.end(1)
                alt_text = answer[start:end] if start < len(answer) else match.group(1)
                # Split on "or" to get individual alternatives
                alts = re.split(r"\s+or\s+", alt_text, flags=re.IGNORECASE)
                for alt in alts:
                    alt_clean = alt.strip()
                    if alt_clean and alt_clean not in alternatives:
                        alternatives.append(alt_clean)

        context["alternatives"] = alternatives

        return context

    def _generate_title(self, question: str, answer: str) -> str:
        """Generate a title from the Q&A pair.

        Creates a concise title based on the question and answer.

        Args:
            question: The clarifying question
            answer: The answer provided

        Returns:
            Generated title string
        """
        # Try to extract key terms from the question
        question_lower = question.lower()

        # Look for "which X" or "what X" patterns
        match = re.search(r"(?:which|what)\s+(\w+(?:\s+\w+)?)", question_lower)
        if match:
            subject = match.group(1)
            # Try to find the decision from the answer
            answer_words = answer.split()
            if answer_words:
                decision = answer_words[0]
                if len(answer_words) > 1:
                    # Take first few significant words
                    decision = " ".join(answer_words[:3])
                return f"Use {decision} for {subject}"

        # Fallback: use first few words of question + answer
        q_words = question.rstrip("?").split()[:3]
        a_words = answer.split()[:2]

        if a_words:
            return f"Decision: {' '.join(a_words)}"
        elif q_words:
            return f"Decision on {' '.join(q_words)}"
        else:
            return "Architecture Decision"

    def create_adr_from_decision(
        self,
        question: str,
        answer: str,
        trigger: ADRTrigger,
        source_task_id: Optional[str] = None,
        source_feature_id: Optional[str] = None,
        source_command: Optional[str] = None,
        **kwargs
    ) -> Optional[ADREntity]:
        """Create an ADR from a significant decision.

        Analyzes the Q&A pair and creates an ADREntity if the decision
        is significant enough (above threshold).

        Args:
            question: The clarifying question asked
            answer: The answer provided
            trigger: What triggered the ADR (e.g., CLARIFYING_QUESTION)
            source_task_id: Optional task ID for traceability
            source_feature_id: Optional feature ID for traceability
            source_command: Optional command name for traceability
            **kwargs: Additional ADREntity fields

        Returns:
            ADREntity if significant, None if below threshold.

        Example:
            adr = detector.create_adr_from_decision(
                question="Which caching strategy?",
                answer="Redis for session storage",
                trigger=ADRTrigger.CLARIFYING_QUESTION,
                source_task_id="TASK-GI-004"
            )
        """
        # Check significance
        significance = self.detect_significance(question, answer)
        if significance < self.significance_threshold:
            logger.debug(
                f"Decision below threshold ({significance:.2f} < "
                f"{self.significance_threshold}): {question[:50]}..."
            )
            return None

        # Extract context
        context_data = self.extract_decision_context(question, answer)

        # Generate title
        title = self._generate_title(question, answer)

        # Create ADR
        adr = ADREntity(
            id="",  # Will be generated by ADRService
            title=title,
            status=ADRStatus.ACCEPTED,
            trigger=trigger,
            source_task_id=source_task_id,
            source_feature_id=source_feature_id,
            source_command=source_command,
            context=question,
            decision=answer,
            rationale=str(context_data.get("rationale", "")),
            alternatives_considered=list(context_data.get("alternatives", [])),
            confidence=significance,
            **kwargs
        )

        logger.info(f"Created ADR from decision: {title}")
        return adr
