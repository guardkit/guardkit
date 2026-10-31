"""
Job-Specific Context Retriever for GuardKit.

This module provides the JobContextRetriever class for retrieving job-specific
context from the memory backend (fleet-memory; formerly Graphiti) based on task
characteristics and budget allocation.
It integrates TaskAnalyzer and DynamicBudgetCalculator to make smart decisions
about what context to load.

Public API:
    RetrievedContext: Dataclass for retrieved context data
    JobContextRetriever: Main retriever class

Example:
    from guardkit.knowledge.job_context_retriever import (
        JobContextRetriever,
        RetrievedContext,
    )
    from guardkit.knowledge.task_analyzer import TaskPhase
    from guardkit.knowledge.relevance_tuning import RelevanceConfig

    # Use default thresholds
    retriever = JobContextRetriever(graphiti_client)

    # Or with custom relevance config
    config = RelevanceConfig(standard_threshold=0.7)
    retriever = JobContextRetriever(graphiti_client, relevance_config=config)

    context = await retriever.retrieve(
        task={"id": "TASK-001", "description": "Implement auth"},
        phase=TaskPhase.IMPLEMENT,
        collect_metrics=True,  # Optional: collect quality metrics
    )

    # Use context in prompt
    prompt_text = context.to_prompt()

    # Check quality metrics (if collected)
    if context.quality_metrics:
        if context.quality_metrics.is_quality_acceptable():
            print("Good quality context retrieved")

References:
    - TASK-GR6-003: Implement JobContextRetriever
    - TASK-GR6-011: Add relevance tuning
    - TASK-GR6-012: Performance optimization
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

logger = logging.getLogger(__name__)

from .task_analyzer import TaskAnalyzer, TaskPhase, TaskCharacteristics
from .budget_calculator import DynamicBudgetCalculator, ContextBudget
from .relevance_tuning import (
    RelevanceConfig,
    ContextQualityMetrics,
    MetricsCollector,
    default_config,
)


@dataclass
class RetrievedContext:
    """Retrieved context data from the memory backend.

    Contains task-specific context organized by category, along with
    budget tracking information and optional quality metrics.

    Attributes:
        task_id: Task identifier
        budget_used: Tokens used for context retrieval
        budget_total: Total token budget available
        feature_context: Feature-related context items
        similar_outcomes: Similar task outcome items
        relevant_patterns: Relevant pattern items
        architecture_context: Architecture context items
        warnings: Warning/failure pattern items
        domain_knowledge: Domain knowledge items
        role_constraints: AutoBuild role constraint items
        quality_gate_configs: AutoBuild quality gate config items
        turn_states: AutoBuild turn state items
        implementation_modes: AutoBuild implementation mode items
        quality_metrics: Optional quality metrics for the retrieval (TASK-GR6-011)

    Example:
        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=2500,
            budget_total=4000,
            feature_context=[{"name": "Feature A"}],
            similar_outcomes=[],
            relevant_patterns=[{"pattern": "Repository"}],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
        )

        prompt = context.to_prompt()

        # Check quality metrics if collected
        if context.quality_metrics:
            if context.quality_metrics.is_quality_acceptable():
                print("Good quality context")
    """

    task_id: str
    budget_used: int
    budget_total: int
    feature_context: List[Dict[str, Any]]
    similar_outcomes: List[Dict[str, Any]]
    relevant_patterns: List[Dict[str, Any]]
    architecture_context: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    domain_knowledge: List[Dict[str, Any]]
    role_constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality_gate_configs: List[Dict[str, Any]] = field(default_factory=list)
    turn_states: List[Dict[str, Any]] = field(default_factory=list)
    implementation_modes: List[Dict[str, Any]] = field(default_factory=list)
    quality_metrics: Optional[ContextQualityMetrics] = None

    def to_prompt(self, include_coach_feedback: bool = True) -> str:
        """Format retrieved context as a prompt string.

        Args:
            include_coach_feedback: ``False`` (the Coach's context) leaves out
                the feedback earlier Coaches wrote on rejected turns, so the
                Coach judges this turn's evidence (build 7010, 12 October
                2026). The Player's context keeps it.

        Returns:
            Formatted string suitable for prompt injection

        Example:
            prompt_text = context.to_prompt()
            full_prompt = f"{system_prompt}\\n\\n{prompt_text}"
        """
        lines = []
        lines.append("## Job-Specific Context")
        lines.append("")
        lines.append(f"Budget: {self.budget_used}/{self.budget_total} tokens")
        lines.append("")

        # Standard categories
        if self.feature_context:
            lines.append("### 📋 Feature Context")
            for item in self.feature_context:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.similar_outcomes:
            lines.append("### ✅ Similar Outcomes")
            for item in self.similar_outcomes:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.relevant_patterns:
            lines.append("### 🎨 Relevant Patterns")
            for item in self.relevant_patterns:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.architecture_context:
            lines.append("### 🏗️ Architecture Context")
            for item in self.architecture_context:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.warnings:
            lines.append("### ⚠️ Warnings")
            for item in self.warnings:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.domain_knowledge:
            lines.append("### 📚 Domain Knowledge")
            for item in self.domain_knowledge:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        # AutoBuild categories
        if self.role_constraints:
            lines.append("### 🎭 Role Constraints")
            for item in self.role_constraints:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        if self.quality_gate_configs:
            # Use dedicated formatter for quality gates with enhanced formatting
            from .quality_gate_formatter import format_quality_gates
            quality_gates_section = format_quality_gates(self.quality_gate_configs)
            if quality_gates_section:
                lines.append(quality_gates_section)

        if self.turn_states:
            # Use dedicated formatter for turn states with cross-turn learning format
            turn_states_section = self._format_turn_states(
                include_coach_feedback=include_coach_feedback
            )
            if turn_states_section:
                lines.append(turn_states_section)

        if self.implementation_modes:
            lines.append("### 🛠️ Implementation Modes")
            for item in self.implementation_modes:
                lines.append(f"- {self._format_item(item)}")
            lines.append("")

        return "\n".join(lines)

    def _format_turn_states(self, include_coach_feedback: bool = True) -> str:
        """Format turn states for cross-turn learning.

        Returns formatted string with:
        - Header: "### Previous Turn Context"
        - Guidance: "Learn from previous turns - don't repeat mistakes"
        - Per-turn format: "**Turn N**: DECISION\\n  Progress: summary"
        - REJECTED turns get warning emphasis with feedback

        Returns:
            Formatted string for turn states section
        """
        if not self.turn_states:
            return ""

        lines = []
        lines.append("### 🔄 Turn States")
        lines.append("*Learn from previous turns - don't repeat mistakes*")
        lines.append("")

        for turn in self.turn_states:
            turn_number = turn.get("turn_number", "?")
            decision = turn.get("coach_decision", "?")
            progress = turn.get("progress_summary", "")

            # Format turn header with decision
            lines.append(f"**Turn {turn_number}**: {decision}")

            # Add progress summary
            if progress:
                lines.append(f"  Progress: {progress}")

            # Emphasize REJECTED turns with warning and feedback
            if decision == "REJECTED" and include_coach_feedback:
                feedback = turn.get("feedback_summary", "")
                if feedback:
                    lines.append(f"  ⚠️ Feedback: \"{feedback}\"")

            lines.append("")

        return "\n".join(lines)

    def _format_item(self, item: Dict[str, Any]) -> str:
        """Format a single context item for display.

        Args:
            item: Dictionary with context item data

        Returns:
            Formatted string representation
        """
        # Declared Fleet rule sections keep the exact section bytes in
        # ``fact`` and render provenance beside, rather than inside, those bytes.
        if item.get("score_kind") == "document" and "fact" in item:
            source = item.get("source_ref", "unknown")
            natural_key = item.get("uuid", "unknown")
            score = item.get("score", 0.0)
            start = item.get("section_start_byte", "?")
            end = item.get("section_end_byte", "?")
            return (
                f"[Fleet source excerpt: {source}; key: {natural_key}; "
                f"document score: {score:.6f}; bytes: {start}-{end}]\n"
                f"{item['fact']}"
            )

        # Try common field names for display
        if "name" in item:
            name = item["name"]
            if "content" in item:
                return f"{name}: {item['content']}"
            if "description" in item:
                return f"{name}: {item['description']}"
            return str(name)

        if "content" in item:
            return str(item["content"])

        if "pattern" in item:
            return str(item["pattern"])

        if "warning" in item:
            return str(item["warning"])

        if "outcome" in item:
            return str(item["outcome"])

        if "concept" in item:
            return str(item["concept"])

        if "component" in item:
            return str(item["component"])

        # Fallback to JSON representation
        return json.dumps(item, default=str)


def _outcome_as_paragraph(item: Dict[str, Any]) -> Dict[str, Any]:
    """Give a stored build outcome to the builder as its paragraph, not its record.

    PASS ON THE PARAGRAPH (2026-10-04). A retrieved outcome is the store's
    whole record as escaped JSON. It reached the prompt like that, and it was
    costed like that too: the fixed fields alone used about 220 of the 418-644
    tokens the outcomes share gets, so at most one outcome fitted. The record's
    ``lessons`` paragraph is the part written for a later build to read. So an
    outcome with a non-empty ``lessons`` becomes ``{"content": <lessons>,
    "uuid", "score"}``: ``_format_item`` prints ``content`` as it is, and
    ``_estimate_tokens`` costs the paragraph alone. Anything else is left
    exactly as it came.
    """
    if not isinstance(item, dict) or not isinstance(item.get("fact"), str):
        return item
    try:
        record = json.loads(item["fact"])
    except ValueError:
        return item
    lessons = record.get("lessons") if isinstance(record, dict) else None
    if not isinstance(lessons, str) or not lessons.strip():
        return item
    return {"content": lessons, "uuid": item.get("uuid"), "score": item.get("score", 1.0)}


#: Marks an item :func:`_record_as_text` rendered, so the budget charges its
#: text as the builder sees it, not its JSON serialisation.
RENDERED_RECORD_KEY = "rendered_from"

#: The decisions-only relevance cut-off. 31 October 2026, measured on 43
#: recorded tasks that cite 67 decisions: the decisions they cite score in the
#: band around 0.5 (median 0.50 for those the 0.5 cut-off dropped, 0.63 for
#: those it kept), so 0.45 lets them through without flooding the share.
DECISION_THRESHOLD = 0.45


def _record_as_text(item: Dict[str, Any]) -> Dict[str, Any]:
    """Give a stored decision record or document to the builder as plain text.

    23 October 2026: fleet memory stores each record as its whole payload in
    JSON, and every search hit carries that JSON string as ``fact``. Printed
    and costed like that, a decision record's decision, context and
    consequences reached the builder as escaped JSON inside JSON, and the
    escaping counted against the small architecture share, so fewer records
    fitted. Following :func:`_outcome_as_paragraph`, an ``adr`` record becomes
    a heading (its identifier, title and status), its decision, and where the
    full record lives; a ``document`` record becomes its identifier and its
    ``content`` body.

    31 October 2026: a decision record used to carry its context,
    consequences and alternatives too, 426 to 3,540 tokens as rendered, so
    usually only the smallest one fitted the architecture share (about 521
    tokens). The decision itself is what a builder must follow; its source
    file is named so the agent can open the rest. On 43 recorded tasks this
    took the cited decisions delivered from 30 to 39 of 67, in fewer tokens.

    The result is ``{"content", "uuid", "score", "rendered_from"}``: ``_format_item``
    prints the text as it is, and ``_estimate_tokens`` charges the rendered
    text itself, never its JSON form (which escapes line breaks and
    non-ASCII characters and counts the key and score). Anything that cannot
    be decoded, or is another kind of record, is left exactly as it came.
    """
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("fact"), str)
        or "score_kind" in item
    ):
        return item
    try:
        record = json.loads(item["fact"])
    except ValueError:
        return item
    if not isinstance(record, dict):
        return item
    # The record's type is the first part of its key ("adr:<project>:<id>").
    # A hit without a typed key is recognised by the fields its type requires.
    key = item.get("uuid")
    kind = key.split(":", 1)[0] if isinstance(key, str) and ":" in key else None
    if kind is None:
        if isinstance(record.get("decision"), str) and isinstance(
            record.get("status"), str
        ):
            kind = "adr"
        elif isinstance(record.get("content"), str) and isinstance(
            record.get("source_ref"), str
        ):
            kind = "document"

    def text(name: str) -> Optional[str]:
        value = record.get(name)
        return value.strip() if isinstance(value, str) and value.strip() else None

    heading = text("title") or text("identifier")
    lines: List[str] = []
    if kind == "adr":
        if text("decision") is None:
            return item
        status = text("status")
        identifier = text("identifier")
        title = text("title")
        if title:
            head = f"Decision record {identifier}: {title}" if identifier else f"Decision record: {title}"
        else:
            head = f"Decision record {identifier}" if identifier else "Decision record: untitled"
        lines.append(head + (f" ({status})" if status else ""))
        lines.append(f"Decision: {text('decision')}")
        if text("source_ref"):
            lines.append(f"Full record: {text('source_ref')}")
    elif kind == "document":
        body = text("content")
        if body is None:
            return item
        if heading:
            lines.append(f"Document: {heading}")
        lines.append(body)
    else:
        return item
    return {
        "content": "\n".join(lines),
        "uuid": item.get("uuid"),
        "score": item.get("score", 1.0),
        RENDERED_RECORD_KEY: kind,
    }


class JobContextRetriever:
    """Retrieves job-specific context from the memory backend.

    The JobContextRetriever uses TaskAnalyzer to understand task characteristics
    and DynamicBudgetCalculator to determine appropriate context allocation.
    It then queries the memory backend for each context category, filters by
    relevance, and trims results to fit the budget.

    Supports configurable relevance thresholds via RelevanceConfig (TASK-GR6-011)
    and optional quality metrics collection.

    Performance optimizations (TASK-GR6-012):
    - Parallel queries using asyncio.gather()
    - LRU cache with TTL for repeated queries
    - Early termination when budget exhausted

    Attributes:
        graphiti: memory client instance for querying the knowledge store
        relevance_config: Configuration for relevance thresholds (optional)
        cache_ttl: Cache time-to-live in seconds (default: 300)

    Example:
        from guardkit.knowledge.fleet_memory_client import get_memory_client
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        client = get_memory_client()

        # Default thresholds
        retriever = JobContextRetriever(graphiti)

        # Custom thresholds and cache TTL
        config = RelevanceConfig(standard_threshold=0.7)
        retriever = JobContextRetriever(graphiti, relevance_config=config, cache_ttl=600)

        task = {
            "id": "TASK-001",
            "description": "Implement user authentication",
            "tech_stack": "python",
            "complexity": 6,
        }

        context = await retriever.retrieve(
            task,
            TaskPhase.IMPLEMENT,
            collect_metrics=True,
        )

        if context.feature_context:
            print(f"Found {len(context.feature_context)} feature items")

        if context.quality_metrics:
            print(f"Quality: {context.quality_metrics.is_quality_acceptable()}")

        # Use parallel retrieval for better performance
        context = await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)
    """

    # Legacy relevance thresholds (kept for backwards compatibility)
    FIRST_OF_TYPE_THRESHOLD = 0.5
    STANDARD_THRESHOLD = 0.6

    # Characters per token estimation (conservative estimate for JSON structures)
    CHARS_PER_TOKEN = 2

    # Priority order for categories (high to low) - used for early termination
    # Based on TASK-GR6-012 requirements:
    # 1. feature_specs (15%)
    # 2. task_outcomes (25%)
    # 3. patterns (20%)
    # 4. project_architecture (20%)
    # 5. failure_patterns (15%)
    # 6. domain_knowledge (5%) - lowest priority
    CATEGORY_PRIORITY = [
        "feature_specs",       # 15% - feature context
        "task_outcomes",       # 25% - similar outcomes
        "patterns",            # 20% - relevant patterns (stack-specific)
        "project_architecture",# 20% - architecture context
        "failure_patterns",    # 15% - warnings
        "domain_knowledge",    # 5%  - lowest priority
    ]

    # Memory groups searched for the architecture category: the project's
    # architecture documents and its decision records (ADRs). /system-arch,
    # /system-plan and ``guardkit memory seed`` save each ADR as an ``adr``
    # record tagged ``architecture``; ``project_architecture`` alone asks for
    # ``document`` records only, so no decision record was ever found.
    #
    # 31 October 2026: the two are searched separately (see
    # ``_query_architecture``). In one search the documents took nearly half
    # the results and the share, and only about 1.4 decisions a task arrived.
    ARCHITECTURE_GROUP_IDS = ("project_architecture", "project_decisions")
    DECISION_GROUP_ID = "project_decisions"

    # AutoBuild category priority (appended after standard categories)
    AUTOBUILD_CATEGORY_PRIORITY = [
        "role_constraints",
        "quality_gate_configs",
        "turn_states",
        "implementation_modes",
    ]

    # RetrievedContext field order, from highest to lowest retrieval priority.
    # AutoBuild uses this order when an eligible record that missed its category
    # share can fit in otherwise-unused total capacity.
    RESULT_CATEGORY_PRIORITY = [
        "feature_context",
        "similar_outcomes",
        "relevant_patterns",
        "architecture_context",
        "warnings",
        "domain_knowledge",
        *AUTOBUILD_CATEGORY_PRIORITY,
    ]

    def __init__(
        self,
        graphiti: Any,
        relevance_config: Optional[RelevanceConfig] = None,
        cache_ttl: float = 300.0,
        relevant_pattern_document_tags: tuple[str, ...] = (),
    ) -> None:
        """Initialize JobContextRetriever with a memory client.

        Args:
            graphiti: memory client instance for knowledge store queries
            relevance_config: Optional RelevanceConfig for custom thresholds.
                If not provided, default thresholds are used.
            cache_ttl: Cache time-to-live in seconds (default: 300).
                Set to 0 to disable caching.
        """
        self.graphiti = graphiti
        self.relevance_config = relevance_config or default_config()
        self.cache_ttl = cache_ttl
        self.relevant_pattern_document_tags = relevant_pattern_document_tags
        # Cache: Dict[cache_key, Tuple[RetrievedContext, timestamp]]
        self._cache: Dict[str, Tuple[RetrievedContext, float]] = {}
        # Category queries that failed here, in the except branches below.
        # Together with the memory client's own ``reads`` counter this lets
        # the per-turn memory line tell a failed read from an empty one.
        self.failed_reads: int = 0

    def _generate_cache_key(
        self,
        task: Dict[str, Any],
        phase: TaskPhase,
        method: str = "retrieve",
    ) -> str:
        """Generate a cache key from task, phase, and method.

        The cache key includes:
        - task_id
        - description hash (for uniqueness)
        - phase name
        - method name (retrieve vs retrieve_parallel)

        Args:
            task: Task dictionary
            phase: Current execution phase
            method: Method name for key differentiation

        Returns:
            Cache key string
        """
        task_id = task.get("id", "")
        description = task.get("description", "")
        # Use SHA-256 with 16 chars for better collision resistance (2^64 space)
        description_hash = hashlib.sha256(description.encode()).hexdigest()[:16]
        phase_name = phase.name if hasattr(phase, "name") else str(phase)
        return f"{task_id}:{description_hash}:{phase_name}:{method}"

    def _get_from_cache(
        self,
        cache_key: str,
    ) -> Optional[RetrievedContext]:
        """Get cached result if valid (not expired).

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached RetrievedContext if valid, None otherwise
        """
        if self.cache_ttl <= 0:
            return None

        if cache_key not in self._cache:
            return None

        context, timestamp = self._cache[cache_key]
        age = time.time() - timestamp

        if age > self.cache_ttl:
            # Cache entry expired, remove it
            del self._cache[cache_key]
            return None

        return context

    def _store_in_cache(
        self,
        cache_key: str,
        context: RetrievedContext,
    ) -> None:
        """Store result in cache with current timestamp.

        Args:
            cache_key: Cache key
            context: RetrievedContext to cache
        """
        if self.cache_ttl <= 0:
            return

        self._cache[cache_key] = (context, time.time())

    async def retrieve(
        self,
        task: Dict[str, Any],
        phase: TaskPhase,
        collect_metrics: bool = False,
        early_termination: bool = False,
    ) -> RetrievedContext:
        """Retrieve job-specific context for a task.

        Analyzes task characteristics, calculates budget allocation,
        queries the memory backend for each context category, filters by
        relevance, and trims results to fit budget.

        Supports caching for repeated queries (TASK-GR6-012).

        Args:
            task: Task dictionary with fields like id, description, tech_stack
            phase: Current execution phase (TaskPhase enum)
            collect_metrics: If True, collect quality metrics (TASK-GR6-011)
            early_termination: If True, stop when budget >= 95% full (TASK-GR6-012)

        Returns:
            RetrievedContext with all retrieved context organized by category.
            If collect_metrics=True, includes quality_metrics attribute.

        Example:
            context = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
            print(f"Retrieved {context.budget_used} tokens of context")

            # With quality metrics
            context = await retriever.retrieve(
                task, TaskPhase.IMPLEMENT, collect_metrics=True
            )
            if context.quality_metrics.is_quality_acceptable():
                print("Good quality context")

            # With early termination
            context = await retriever.retrieve(
                task, TaskPhase.IMPLEMENT, early_termination=True
            )
        """
        # Check cache first
        cache_key = self._generate_cache_key(task, phase)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        # Analyze task characteristics
        analyzer = TaskAnalyzer(self.graphiti)
        characteristics = await analyzer.analyze(task, phase)

        # Calculate budget allocation
        calculator = DynamicBudgetCalculator()
        try:
            budget = calculator.calculate(characteristics)
            # Access characteristics fields (validates they're real)
            description = characteristics.description
            tech_stack = characteristics.tech_stack
        except (TypeError, AttributeError):
            # Fallback for mocked characteristics without proper fields
            # This handles test scenarios where TaskAnalyzer is mocked
            budget = ContextBudget(
                total_tokens=4000,
                feature_context=0.15,
                similar_outcomes=0.25,
                relevant_patterns=0.20,
                architecture_context=0.20,
                warnings=0.15,
                domain_knowledge=0.05,
            )
            description = task.get("description", "")
            tech_stack = task.get("tech_stack", "")

        # Determine relevance threshold using RelevanceConfig (TASK-GR6-011)
        try:
            threshold = self.relevance_config.get_threshold(characteristics)
        except (TypeError, AttributeError):
            # Fallback for mocked characteristics
            threshold = self.relevance_config.standard_threshold

        # Initialize metrics collector if requested
        metrics_collector: Optional[MetricsCollector] = None
        if collect_metrics:
            metrics_collector = MetricsCollector(
                threshold=threshold,
                total_budget=budget.total_tokens,
                budget_per_category={
                    "feature_context": budget.get_allocation("feature_context"),
                    "similar_outcomes": budget.get_allocation("similar_outcomes"),
                    "relevant_patterns": budget.get_allocation("relevant_patterns"),
                    "architecture_context": budget.get_allocation("architecture_context"),
                    "warnings": budget.get_allocation("warnings"),
                    "domain_knowledge": budget.get_allocation("domain_knowledge"),
                },
            )

        # AutoBuild may reuse capacity left by sparse categories. Keep the
        # already-fetched, threshold-filtered candidates local to this call;
        # production can issue concurrent reads through one retriever.
        is_autobuild = task.get("is_autobuild", False)
        candidate_pools: Optional[Dict[str, List[Dict[str, Any]]]] = (
            {name: [] for name in self.RESULT_CATEGORY_PRIORITY}
            if is_autobuild
            else None
        )

        # Track total budget used
        budget_used = 0

        # Initialize result containers
        feature_context: List[Dict[str, Any]] = []
        similar_outcomes: List[Dict[str, Any]] = []
        relevant_patterns: List[Dict[str, Any]] = []
        architecture_context: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        domain_knowledge: List[Dict[str, Any]] = []

        # Define category query order with allocations for early termination
        # Priority order (high to low): feature_specs, task_outcomes, patterns, architecture, warnings, domain
        category_configs = [
            (["feature_specs"], "feature_context", budget.get_allocation("feature_context")),
            (["task_outcomes"], "similar_outcomes", budget.get_allocation("similar_outcomes")),
            (["patterns"], "relevant_patterns", budget.get_allocation("relevant_patterns")),
            (list(self.ARCHITECTURE_GROUP_IDS), "architecture_context", budget.get_allocation("architecture_context")),
            (["failure_patterns"], "warnings", budget.get_allocation("warnings")),
            (["domain_knowledge"], "domain_knowledge", budget.get_allocation("domain_knowledge")),
        ]

        # Helper to check if we should stop (early termination)
        # Stops when budget is >= 95% full
        def should_stop() -> bool:
            if not early_termination:
                return False
            return budget_used >= budget.total_tokens * 0.95

        # Results dictionary to collect results
        results: Dict[str, List[Dict[str, Any]]] = {}

        # Reset circuit breaker before querying (RC7: TASK-REV-F8BA)
        if hasattr(self.graphiti, 'reset_circuit_breaker'):
            self.graphiti.reset_circuit_breaker()

        # Query categories in priority order
        for group_ids, category_name, allocation in category_configs:
            if should_stop():
                results[category_name] = []
                continue

            # With early termination, allow high-priority categories to use remaining budget
            # This fills budget more completely so we actually hit 95% threshold
            if early_termination:
                remaining_budget = budget.total_tokens - budget_used
                # Use the larger of: category allocation OR remaining budget (capped at 2x allocation)
                # Hard cap: never exceed remaining budget to prevent budget overflow
                effective_allocation = min(
                    max(allocation, remaining_budget),
                    allocation * 2,  # Cap at 2x to prevent one category from taking everything
                    remaining_budget,  # Hard cap: never exceed remaining budget
                )
            else:
                effective_allocation = allocation

            category_results, tokens = await self._query_category(
                query=description,
                group_ids=group_ids,
                budget_allocation=effective_allocation,
                threshold=threshold,
                metrics_collector=metrics_collector,
                category=category_name,
                candidate_pool=(
                    candidate_pools[category_name]
                    if candidate_pools is not None
                    else None
                ),
            )
            results[category_name] = category_results
            budget_used += tokens

        # Unpack results
        feature_context = results.get("feature_context", [])
        similar_outcomes = results.get("similar_outcomes", [])
        relevant_patterns = results.get("relevant_patterns", [])
        architecture_context = results.get("architecture_context", [])
        warnings = results.get("warnings", [])
        domain_knowledge = results.get("domain_knowledge", [])

        # AutoBuild categories (only if is_autobuild)
        role_constraints: List[Dict[str, Any]] = []
        quality_gate_configs: List[Dict[str, Any]] = []
        turn_states: List[Dict[str, Any]] = []
        implementation_modes: List[Dict[str, Any]] = []

        if is_autobuild:
            assert candidate_pools is not None
            if not should_stop():
                remaining_budget = max(0, budget.total_tokens - budget_used)
                role_constraints, tokens = await self._query_category(
                    query=description,
                    group_ids=["role_constraints"],
                    budget_allocation=min(
                        budget.get_allocation("role_constraints"), remaining_budget
                    ),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="role_constraints",
                    candidate_pool=candidate_pools["role_constraints"],
                )
                budget_used += tokens

            if not should_stop():
                remaining_budget = max(0, budget.total_tokens - budget_used)
                quality_gate_configs, tokens = await self._query_category(
                    query=description,
                    group_ids=["quality_gate_configs"],
                    budget_allocation=min(
                        budget.get_allocation("quality_gate_configs"),
                        remaining_budget,
                    ),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="quality_gate_configs",
                    candidate_pool=candidate_pools["quality_gate_configs"],
                )
                budget_used += tokens

            if not should_stop():
                # Query turn_states with feature_id/task_id format for cross-turn learning
                feature_id = task.get("feature_id", "")
                task_id_val = task.get("id", "")
                remaining_budget = max(0, budget.total_tokens - budget_used)
                turn_states, tokens = await self._query_turn_states(
                    feature_id=feature_id,
                    task_id=task_id_val,
                    budget_allocation=min(
                        budget.get_allocation("turn_states"), remaining_budget
                    ),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    candidate_pool=candidate_pools["turn_states"],
                )
                budget_used += tokens

            if not should_stop():
                remaining_budget = max(0, budget.total_tokens - budget_used)
                implementation_modes, tokens = await self._query_category(
                    query=description,
                    group_ids=["implementation_modes"],
                    budget_allocation=min(
                        budget.get_allocation("implementation_modes"),
                        remaining_budget,
                    ),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="implementation_modes",
                    candidate_pool=candidate_pools["implementation_modes"],
                )
                budget_used += tokens

            selected = {
                "feature_context": feature_context,
                "similar_outcomes": similar_outcomes,
                "relevant_patterns": relevant_patterns,
                "architecture_context": architecture_context,
                "warnings": warnings,
                "domain_knowledge": domain_knowledge,
                "role_constraints": role_constraints,
                "quality_gate_configs": quality_gate_configs,
                "turn_states": turn_states,
                "implementation_modes": implementation_modes,
            }
            budget_used = self._reuse_autobuild_capacity(
                selected, candidate_pools, budget.total_tokens
            )
            feature_context = selected["feature_context"]
            similar_outcomes = selected["similar_outcomes"]
            relevant_patterns = selected["relevant_patterns"]
            architecture_context = selected["architecture_context"]
            warnings = selected["warnings"]
            domain_knowledge = selected["domain_knowledge"]
            role_constraints = selected["role_constraints"]
            quality_gate_configs = selected["quality_gate_configs"]
            turn_states = selected["turn_states"]
            implementation_modes = selected["implementation_modes"]

        # Collect final quality metrics if requested
        quality_metrics: Optional[ContextQualityMetrics] = None
        if metrics_collector is not None:
            metrics_collector.add_budget_usage(budget_used)
            quality_metrics = metrics_collector.get_metrics()

        result = RetrievedContext(
            task_id=task.get("id", ""),
            budget_used=budget_used,
            budget_total=budget.total_tokens,
            feature_context=feature_context,
            similar_outcomes=similar_outcomes,
            relevant_patterns=relevant_patterns,
            architecture_context=architecture_context,
            warnings=warnings,
            domain_knowledge=domain_knowledge,
            role_constraints=role_constraints,
            quality_gate_configs=quality_gate_configs,
            turn_states=turn_states,
            implementation_modes=implementation_modes,
            quality_metrics=quality_metrics,
        )

        # Store result in cache
        self._store_in_cache(cache_key, result)

        return result

    async def retrieve_parallel(
        self,
        task: Dict[str, Any],
        phase: TaskPhase,
        collect_metrics: bool = False,
        early_termination: bool = False,
    ) -> RetrievedContext:
        """Retrieve job-specific context using parallel queries.

        Uses asyncio.gather() to query all categories concurrently,
        significantly improving retrieval time.

        Args:
            task: Task dictionary with fields like id, description, tech_stack
            phase: Current execution phase (TaskPhase enum)
            collect_metrics: If True, collect quality metrics (TASK-GR6-011)
            early_termination: If True, apply priority-based filtering after retrieval

        Returns:
            RetrievedContext with all retrieved context organized by category.

        Example:
            context = await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)
            print(f"Retrieved {context.budget_used} tokens of context in parallel")
        """
        # Check cache first (use different key for parallel method)
        cache_key = self._generate_cache_key(task, phase, method="retrieve_parallel")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Analyze task characteristics
        analyzer = TaskAnalyzer(self.graphiti)
        characteristics = await analyzer.analyze(task, phase)

        # Calculate budget allocation
        calculator = DynamicBudgetCalculator()
        try:
            budget = calculator.calculate(characteristics)
            description = characteristics.description
            tech_stack = characteristics.tech_stack
        except (TypeError, AttributeError):
            budget = ContextBudget(
                total_tokens=4000,
                feature_context=0.15,
                similar_outcomes=0.25,
                relevant_patterns=0.20,
                architecture_context=0.20,
                warnings=0.15,
                domain_knowledge=0.05,
            )
            description = task.get("description", "")
            tech_stack = task.get("tech_stack", "")

        # Determine relevance threshold
        try:
            threshold = self.relevance_config.get_threshold(characteristics)
        except (TypeError, AttributeError):
            threshold = self.relevance_config.standard_threshold

        # Initialize metrics collector if requested
        metrics_collector: Optional[MetricsCollector] = None
        if collect_metrics:
            metrics_collector = MetricsCollector(
                threshold=threshold,
                total_budget=budget.total_tokens,
                budget_per_category={
                    "feature_context": budget.get_allocation("feature_context"),
                    "similar_outcomes": budget.get_allocation("similar_outcomes"),
                    "relevant_patterns": budget.get_allocation("relevant_patterns"),
                    "architecture_context": budget.get_allocation("architecture_context"),
                    "warnings": budget.get_allocation("warnings"),
                    "domain_knowledge": budget.get_allocation("domain_knowledge"),
                },
            )

        is_autobuild = task.get("is_autobuild", False)
        candidate_pools: Optional[Dict[str, List[Dict[str, Any]]]] = (
            {name: [] for name in self.RESULT_CATEGORY_PRIORITY}
            if is_autobuild
            else None
        )

        # Build list of coroutines for standard categories
        standard_queries = [
            self._query_category(
                query=description,
                group_ids=["feature_specs"],
                budget_allocation=budget.get_allocation("feature_context"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="feature_context",
                candidate_pool=(
                    candidate_pools["feature_context"]
                    if candidate_pools is not None
                    else None
                ),
            ),
            self._query_category(
                query=description,
                group_ids=["task_outcomes"],
                budget_allocation=budget.get_allocation("similar_outcomes"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="similar_outcomes",
                candidate_pool=(
                    candidate_pools["similar_outcomes"]
                    if candidate_pools is not None
                    else None
                ),
            ),
            self._query_category(
                query=description,
                group_ids=["patterns"],
                budget_allocation=budget.get_allocation("relevant_patterns"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="relevant_patterns",
                candidate_pool=(
                    candidate_pools["relevant_patterns"]
                    if candidate_pools is not None
                    else None
                ),
            ),
            self._query_category(
                query=description,
                group_ids=list(self.ARCHITECTURE_GROUP_IDS),
                budget_allocation=budget.get_allocation("architecture_context"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="architecture_context",
                candidate_pool=(
                    candidate_pools["architecture_context"]
                    if candidate_pools is not None
                    else None
                ),
            ),
            self._query_category(
                query=description,
                group_ids=["failure_patterns"],
                budget_allocation=budget.get_allocation("warnings"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="warnings",
                candidate_pool=(
                    candidate_pools["warnings"]
                    if candidate_pools is not None
                    else None
                ),
            ),
            self._query_category(
                query=description,
                group_ids=["domain_knowledge"],
                budget_allocation=budget.get_allocation("domain_knowledge"),
                threshold=threshold,
                metrics_collector=metrics_collector,
                category="domain_knowledge",
                candidate_pool=(
                    candidate_pools["domain_knowledge"]
                    if candidate_pools is not None
                    else None
                ),
            ),
        ]

        # Reset circuit breaker before querying to prevent cascading failures
        # from previous operations (RC7: TASK-REV-F8BA)
        if hasattr(self.graphiti, 'reset_circuit_breaker'):
            self.graphiti.reset_circuit_breaker()

        # Execute all standard queries in parallel
        results = await asyncio.gather(*standard_queries)

        # Unpack results
        feature_context, feature_tokens = results[0]
        similar_outcomes, outcomes_tokens = results[1]
        relevant_patterns, patterns_tokens = results[2]
        architecture_context, arch_tokens = results[3]
        warnings, warnings_tokens = results[4]
        domain_knowledge, domain_tokens = results[5]

        budget_used = (
            feature_tokens + outcomes_tokens + patterns_tokens +
            arch_tokens + warnings_tokens + domain_tokens
        )

        # AutoBuild categories (only if is_autobuild)
        role_constraints: List[Dict[str, Any]] = []
        quality_gate_configs: List[Dict[str, Any]] = []
        turn_states: List[Dict[str, Any]] = []
        implementation_modes: List[Dict[str, Any]] = []

        if is_autobuild:
            assert candidate_pools is not None
            # Reset circuit breaker before AutoBuild queries (RC7: TASK-REV-F8BA)
            if hasattr(self.graphiti, 'reset_circuit_breaker'):
                self.graphiti.reset_circuit_breaker()

            feature_id = task.get("feature_id", "")
            task_id_val = task.get("id", "")

            autobuild_queries = [
                self._query_category(
                    query=description,
                    group_ids=["role_constraints"],
                    budget_allocation=budget.get_allocation("role_constraints"),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="role_constraints",
                    candidate_pool=candidate_pools["role_constraints"],
                ),
                self._query_category(
                    query=description,
                    group_ids=["quality_gate_configs"],
                    budget_allocation=budget.get_allocation("quality_gate_configs"),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="quality_gate_configs",
                    candidate_pool=candidate_pools["quality_gate_configs"],
                ),
                self._query_turn_states(
                    feature_id=feature_id,
                    task_id=task_id_val,
                    budget_allocation=budget.get_allocation("turn_states"),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    candidate_pool=candidate_pools["turn_states"],
                ),
                self._query_category(
                    query=description,
                    group_ids=["implementation_modes"],
                    budget_allocation=budget.get_allocation("implementation_modes"),
                    threshold=threshold,
                    metrics_collector=metrics_collector,
                    category="implementation_modes",
                    candidate_pool=candidate_pools["implementation_modes"],
                ),
            ]

            await asyncio.gather(*autobuild_queries)

            remaining_budget = max(0, budget.total_tokens - budget_used)
            role_constraints, role_tokens = self._trim_to_budget(
                candidate_pools["role_constraints"],
                min(budget.get_allocation("role_constraints"), remaining_budget),
            )
            remaining_budget -= role_tokens
            quality_gate_configs, gate_tokens = self._trim_to_budget(
                candidate_pools["quality_gate_configs"],
                min(
                    budget.get_allocation("quality_gate_configs"),
                    remaining_budget,
                ),
            )
            remaining_budget -= gate_tokens
            turn_states, turn_tokens = self._trim_to_budget(
                candidate_pools["turn_states"],
                min(budget.get_allocation("turn_states"), remaining_budget),
            )
            remaining_budget -= turn_tokens
            implementation_modes, mode_tokens = self._trim_to_budget(
                candidate_pools["implementation_modes"],
                min(
                    budget.get_allocation("implementation_modes"),
                    remaining_budget,
                ),
            )

            budget_used += role_tokens + gate_tokens + turn_tokens + mode_tokens

            selected = {
                "feature_context": feature_context,
                "similar_outcomes": similar_outcomes,
                "relevant_patterns": relevant_patterns,
                "architecture_context": architecture_context,
                "warnings": warnings,
                "domain_knowledge": domain_knowledge,
                "role_constraints": role_constraints,
                "quality_gate_configs": quality_gate_configs,
                "turn_states": turn_states,
                "implementation_modes": implementation_modes,
            }
            budget_used = self._reuse_autobuild_capacity(
                selected, candidate_pools, budget.total_tokens
            )
            feature_context = selected["feature_context"]
            similar_outcomes = selected["similar_outcomes"]
            relevant_patterns = selected["relevant_patterns"]
            architecture_context = selected["architecture_context"]
            warnings = selected["warnings"]
            domain_knowledge = selected["domain_knowledge"]
            role_constraints = selected["role_constraints"]
            quality_gate_configs = selected["quality_gate_configs"]
            turn_states = selected["turn_states"]
            implementation_modes = selected["implementation_modes"]

        # Collect final quality metrics if requested
        quality_metrics: Optional[ContextQualityMetrics] = None
        if metrics_collector is not None:
            metrics_collector.add_budget_usage(budget_used)
            quality_metrics = metrics_collector.get_metrics()

        result = RetrievedContext(
            task_id=task.get("id", ""),
            budget_used=budget_used,
            budget_total=budget.total_tokens,
            feature_context=feature_context,
            similar_outcomes=similar_outcomes,
            relevant_patterns=relevant_patterns,
            architecture_context=architecture_context,
            warnings=warnings,
            domain_knowledge=domain_knowledge,
            role_constraints=role_constraints,
            quality_gate_configs=quality_gate_configs,
            turn_states=turn_states,
            implementation_modes=implementation_modes,
            quality_metrics=quality_metrics,
        )

        # Store result in cache
        self._store_in_cache(cache_key, result)

        return result

    async def _query_category(
        self,
        query: str,
        group_ids: List[str],
        budget_allocation: int,
        threshold: float,
        metrics_collector: Optional[MetricsCollector] = None,
        category: str = "",
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Query a single context category from the memory backend.

        Args:
            query: Search query (typically task description)
            group_ids: memory group IDs to search
            budget_allocation: Maximum token budget for this category
            threshold: Minimum relevance score to include
            metrics_collector: Optional MetricsCollector for tracking quality
            category: Category name for metrics tracking
            candidate_pool: Optional per-invocation destination for all
                threshold-filtered candidates, before category trimming

        Returns:
            Tuple of (filtered_results, tokens_used)
        """
        if (
            category == "architecture_context"
            and self.DECISION_GROUP_ID in group_ids
            and len(group_ids) > 1
        ):
            return await self._query_architecture(
                query=query,
                group_ids=group_ids,
                budget_allocation=budget_allocation,
                threshold=threshold,
                metrics_collector=metrics_collector,
                candidate_pool=candidate_pool,
            )
        try:
            # Only Fleet's contextual task-outcome path opts into substantive
            # records. Generic history consumers retain metadata-only availability.
            search_kwargs: dict[str, Any] = {"group_ids": group_ids}
            if (
                category == "relevant_patterns"
                and group_ids == ["patterns"]
                and self.relevant_pattern_document_tags
                and getattr(
                    self.graphiti, "supports_document_source_tags", False
                ) is True
            ):
                search_kwargs = {
                    "group_ids": [],
                    "document_source_tags": list(
                        self.relevant_pattern_document_tags
                    ),
                }
            if (
                category == "similar_outcomes"
                and group_ids == ["task_outcomes"]
                and getattr(
                    self.graphiti, "supports_substantive_search", False
                ) is True
            ):
                search_kwargs["require_substantive"] = True

            # Query the memory backend.
            results = await self.graphiti.search(query, **search_kwargs)

            # Handle None or empty results
            if not results:
                return [], 0

            if category == "similar_outcomes" and group_ids == ["task_outcomes"]:
                results = [_outcome_as_paragraph(item) for item in results]
            results = [_record_as_text(item) for item in results]

            # Filter by relevance threshold and collect metrics
            filtered = []
            for item in results:
                score = item.get("score", 1.0)  # Default to 1.0 if no score

                # Add to metrics collector (before filtering)
                if metrics_collector is not None:
                    metrics_collector.add_result(item, category=category)

                if score >= threshold:
                    filtered.append(item)

            if candidate_pool is not None:
                candidate_pool.extend(filtered)

            # Trim to fit budget allocation
            trimmed, tokens_used = self._trim_to_budget(filtered, budget_allocation)

            return trimmed, tokens_used

        except Exception as e:
            self.failed_reads += 1
            logger.warning(
                "[Memory] Category '%s' query failed: %s", category, e
            )
            return [], 0

    async def _query_architecture(
        self,
        query: str,
        group_ids: List[str],
        budget_allocation: int,
        threshold: float,
        metrics_collector: Optional[MetricsCollector] = None,
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """The architecture category: documents and decision records apart.

        31 October 2026, measured on 43 recorded tasks that cite 67 decisions:
        searched together, documents took nearly half the results and the
        share, the 0.5 cut-off fell inside the band the cited decisions score
        in, and the builder received 30 of the 67. Searched apart, decisions
        come first from their own search, with the :data:`DECISION_THRESHOLD`
        cut-off; documents keep the category's threshold and fill what the
        decisions left of the share, so the category spends no more than
        before. AutoBuild's spare-capacity pass can still add more of either
        from the candidates fetched here.

        Returns:
            Tuple of (decisions then documents, tokens_used)
        """
        decisions: List[Dict[str, Any]] = []
        try:
            results = await self.graphiti.search(
                query, group_ids=[self.DECISION_GROUP_ID]
            )
        except Exception as e:
            self.failed_reads += 1
            logger.warning("[Memory] Decision records query failed: %s", e)
            results = []
        for item in (_record_as_text(hit) for hit in results or []):
            # The group's read also matches architecture documents; those come
            # from the documents search below.
            if not isinstance(item, dict) or item.get(RENDERED_RECORD_KEY) == "document":
                continue
            if metrics_collector is not None:
                metrics_collector.add_result(item, category="architecture_context")
            # The decisions-only cut-off applies to decision records; anything
            # the store could not type keeps the category's threshold.
            is_decision = item.get(RENDERED_RECORD_KEY) == "adr"
            cut_off = min(threshold, DECISION_THRESHOLD) if is_decision else threshold
            if item.get("score", 1.0) >= cut_off:
                decisions.append(item)
        if candidate_pool is not None:
            candidate_pool.extend(decisions)
        kept, decision_tokens = self._trim_to_budget(decisions, budget_allocation)

        # Documents fill what the decisions left of the same share, so the
        # category never spends more than it was given.
        documents, _ = await self._query_category(
            query=query,
            group_ids=[g for g in group_ids if g != self.DECISION_GROUP_ID],
            budget_allocation=budget_allocation,
            threshold=threshold,
            metrics_collector=metrics_collector,
            category="architecture_context",
            candidate_pool=candidate_pool,
        )
        seen = {d.get("uuid") for d in kept if d.get("uuid")}
        documents = [
            d
            for d in documents
            if d.get(RENDERED_RECORD_KEY) != "adr" and d.get("uuid") not in seen
        ]
        if decision_tokens:
            documents, document_tokens = self._trim_to_budget(
                documents, max(0, budget_allocation - decision_tokens)
            )
        else:
            document_tokens = sum(self._estimate_tokens(d) for d in documents)
        return kept + documents, decision_tokens + document_tokens

    async def _query_turn_states(
        self,
        feature_id: str,
        task_id: str,
        budget_allocation: int,
        threshold: float,
        metrics_collector: Optional[MetricsCollector] = None,
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Query turn_states for cross-turn learning.

        Uses 'turn {feature_id} {task_id}' format and returns last 5 turns
        sorted by turn_number ascending.

        Args:
            feature_id: Feature identifier (e.g., "FEAT-GR6")
            task_id: Task identifier (e.g., "TASK-GR6-001")
            budget_allocation: Maximum token budget for this category
            threshold: Minimum relevance score to include
            metrics_collector: Optional MetricsCollector for tracking quality
            candidate_pool: Optional per-invocation destination for the sorted,
                last-five threshold-filtered candidates before budget trimming

        Returns:
            Tuple of (filtered_results, tokens_used)
        """
        try:
            # Build query with feature_id and task_id format
            query = f"turn {feature_id} {task_id}"

            # Query the memory backend with num_results=5 for last 5 turns
            results = await self.graphiti.search(
                query,
                group_ids=["turn_states"],
                num_results=5,
            )

            # Handle None or empty results
            if not results:
                return [], 0

            # Filter by relevance threshold and collect metrics
            filtered = []
            for item in results:
                score = item.get("score", 1.0)  # Default to 1.0 if no score

                # Add to metrics collector (before filtering)
                if metrics_collector is not None:
                    metrics_collector.add_result(item, category="turn_states")

                if score >= threshold:
                    filtered.append(item)

            # Sort by turn_number ascending
            filtered.sort(key=lambda x: x.get("turn_number", 0))

            # Limit to last 5 turns (take the most recent ones)
            if len(filtered) > 5:
                filtered = filtered[-5:]

            if candidate_pool is not None:
                candidate_pool.extend(filtered)

            # Trim to fit budget allocation
            trimmed, tokens_used = self._trim_to_budget(filtered, budget_allocation)

            return trimmed, tokens_used

        except Exception as e:
            self.failed_reads += 1
            logger.warning(
                "[Memory] turn_states query failed (feature=%s, task=%s): %s",
                feature_id,
                task_id,
                e,
            )
            return [], 0

    def _reuse_autobuild_capacity(
        self,
        selected: Dict[str, List[Dict[str, Any]]],
        candidate_pools: Dict[str, List[Dict[str, Any]]],
        total_budget: int,
    ) -> int:
        """Fill unused AutoBuild capacity from candidates already retrieved.

        The first pass remains category-budgeted. Its selected identities are
        reserved before any extra candidate is considered, so a larger
        high-ranked record cannot evict a smaller record that already fitted.
        Added records follow the existing category priority, and each category
        is finally emitted in its original source rank order.

        Args:
            selected: Mutable selected records by RetrievedContext field name.
            candidate_pools: Threshold-filtered records fetched by this call.
            total_budget: Strict total selected-record token budget.

        Returns:
            Estimated tokens used by the final selected records.
        """
        total_budget = max(0, total_budget)
        tokens_used = 0
        selected_by_id: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = {}
        selected_order: Dict[str, List[Tuple[str, str]]] = {}

        # Reserve every valid first-pass selection before reusing spare capacity.
        for category in self.RESULT_CATEGORY_PRIORITY:
            selected_by_id[category] = {}
            selected_order[category] = []
            for item in selected.get(category, []):
                identity = self._context_item_identity(item)
                if identity in selected_by_id[category]:
                    continue
                item_tokens = self._estimate_tokens(item)
                if tokens_used + item_tokens > total_budget:
                    continue
                selected_by_id[category][identity] = item
                selected_order[category].append(identity)
                tokens_used += item_tokens

        # Add only unselected identities. An oversized record does not prevent
        # a smaller lower-ranked record in the same already-fetched pool.
        for category in self.RESULT_CATEGORY_PRIORITY:
            for item in candidate_pools.get(category, []):
                identity = self._context_item_identity(item)
                if identity in selected_by_id[category]:
                    continue
                item_tokens = self._estimate_tokens(item)
                if tokens_used + item_tokens > total_budget:
                    continue
                selected_by_id[category][identity] = item
                selected_order[category].append(identity)
                tokens_used += item_tokens

        # Source-pool order is the original rank order. The fallback tail is
        # only for a defensive case where an initial selection is absent from
        # the retained pool; it preserves that selection's first-pass order.
        for category in self.RESULT_CATEGORY_PRIORITY:
            emitted: set[Tuple[str, str]] = set()
            ordered: List[Dict[str, Any]] = []
            for item in candidate_pools.get(category, []):
                identity = self._context_item_identity(item)
                if identity in selected_by_id[category] and identity not in emitted:
                    ordered.append(selected_by_id[category][identity])
                    emitted.add(identity)
            for identity in selected_order[category]:
                if identity not in emitted:
                    ordered.append(selected_by_id[category][identity])
                    emitted.add(identity)
            selected[category] = ordered

        return tokens_used

    @staticmethod
    def _context_item_identity(item: Dict[str, Any]) -> Tuple[str, str]:
        """Return a stable per-category identity for a retrieved record."""
        record_identity: Optional[Tuple[str, str]] = None
        for field_name in ("uuid", "natural_key", "id", "key"):
            value = item.get(field_name)
            if value is not None and str(value):
                record_identity = (field_name, str(value))
                break

        # Fleet declared-rule search returns independently ranked sections of
        # one document with the same UUID. Preserve those distinct excerpts,
        # while repeated copies of the same section still share an identity.
        section_provenance = {
            field_name: item[field_name]
            for field_name in (
                "section_sha256",
                "section_start_byte",
                "section_end_byte",
            )
            if field_name in item
        }
        if section_provenance:
            return "section", json.dumps(
                {
                    "record": record_identity,
                    "section": section_provenance,
                },
                sort_keys=True,
                default=str,
            )

        if record_identity is not None:
            return record_identity
        return "value", json.dumps(item, sort_keys=True, default=str)

    def _trim_to_budget(
        self,
        items: List[Dict[str, Any]],
        budget: int,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Trim items to fit within token budget.

        Args:
            items: List of context items
            budget: Maximum tokens for this category

        Returns:
            Tuple of (trimmed_items, tokens_used)
        """
        if not items or budget <= 0:
            return [], 0

        trimmed = []
        tokens_used = 0

        for item in items:
            # Estimate tokens for this item
            item_tokens = self._estimate_tokens(item)

            # Check if we can fit this item
            if tokens_used + item_tokens <= budget:
                trimmed.append(item)
                tokens_used += item_tokens
            else:
                # This item does not fit. Keep looking: a smaller lower-ranked
                # result may still fit without exceeding the strict category total.
                continue

        return trimmed, tokens_used

    def _estimate_tokens(self, item: Dict[str, Any]) -> int:
        """Estimate token count for a context item.

        Uses a simple character-based estimation (~4 chars per token).

        Args:
            item: Context item dictionary

        Returns:
            Estimated token count
        """
        # A decision record or document rendered as text is charged on that
        # text, as the builder sees it (23 October 2026).
        if item.get(RENDERED_RECORD_KEY) in ("adr", "document") and isinstance(
            item.get("content"), str
        ):
            return max(1, len(item["content"]) // self.CHARS_PER_TOKEN)

        # Convert to string for character count
        item_str = json.dumps(item, default=str)
        char_count = len(item_str)

        # Estimate tokens (approximately 4 chars per token)
        return max(1, char_count // self.CHARS_PER_TOKEN)
