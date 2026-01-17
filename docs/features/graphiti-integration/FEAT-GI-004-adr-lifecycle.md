# Feature 4: ADR Lifecycle Management

**Feature ID**: FEAT-GI-004  
**Status**: Ready for Planning  
**Priority**: High  
**Estimated Complexity**: Medium  
**Dependencies**: FEAT-GI-001 (Core Infrastructure)  
**Related ADR**: ADR-001-graphiti-integration-scope.md

---

## Overview

Capture explicit Architecture Decision Records (ADRs) from decisions made during GuardKit workflows. When a decision is made during `/feature-plan` (clarifying questions), `/task-review` (acceptance), or `/task-work` (implementation choices), that decision should be recorded as an ADR in Graphiti so future sessions can query "why did we decide X?"

This feature handles **explicit ADRs** - decisions made consciously during workflows. Discovered ADRs (from code analysis) are handled by FEAT-GI-007.

---

## Goals

1. **Capture Decisions**: Record significant decisions as ADRs automatically
2. **Rich Context**: Include rationale, alternatives considered, consequences
3. **Traceability**: Link ADRs to tasks/features that triggered them
4. **Queryable**: ADRs searchable via Graphiti semantic search
5. **Lifecycle**: Support ADR statuses (proposed, accepted, deprecated, superseded)

---

## User Stories

### US1: Decision Capture from Clarifying Questions
> As a developer using `/feature-plan`, when I answer a clarifying question that involves a scope or approach decision, that decision should be recorded as an ADR.

**Acceptance Criteria**:
- Clarifying question + answer is analyzed for decision significance
- Significant decisions create ADR with context from the question
- ADR links to the feature being planned
- Low-significance answers don't create ADRs (noise reduction)

### US2: Decision Capture from Task Review
> As a reviewer accepting or rejecting a task implementation, when I specify implementation approach preferences, those should become ADRs.

**Acceptance Criteria**:
- Task review acceptance with approach specification creates ADR
- Task review rejection with alternative suggestion creates ADR
- ADR includes the task context and review decision
- Rationale captured from review comments

### US3: Decision Capture from Implementation
> As a Claude Code session implementing a task, when I make a significant implementation choice (e.g., which library to use, which pattern to apply), that choice should be recorded.

**Acceptance Criteria**:
- Implementation decisions during Phase 3/4 can be flagged for ADR
- Agent can call `record_decision()` to create ADR
- Decision includes implementation context
- Links to task being implemented

### US4: ADR Querying
> As a Claude Code session, I should be able to query existing ADRs to see what decisions have been made about a topic.

**Acceptance Criteria**:
- Query by topic returns relevant ADRs
- Query returns ADR with full context (decision, rationale, alternatives)
- Superseded ADRs clearly marked
- Results ranked by relevance

---

## Technical Requirements

### ADR Entity Model

```python
# guardkit/knowledge/adr.py

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ADRStatus(Enum):
    PROPOSED = "proposed"      # Decision under consideration
    ACCEPTED = "accepted"      # Decision made and active
    DEPRECATED = "deprecated"  # Decision no longer recommended
    SUPERSEDED = "superseded"  # Replaced by another ADR

class ADRTrigger(Enum):
    CLARIFYING_QUESTION = "clarifying_question"  # From /feature-plan
    TASK_REVIEW = "task_review"                  # From /task-review acceptance
    IMPLEMENTATION_CHOICE = "implementation"      # From /task-work
    MANUAL = "manual"                            # Explicitly created
    DISCOVERED = "discovered"                    # From code analysis (FEAT-GI-007)

@dataclass
class ADREntity:
    """Architecture Decision Record stored in Graphiti."""
    
    # Identity
    id: str                              # ADR-XXXX
    title: str                           # Brief decision title
    status: ADRStatus = ADRStatus.ACCEPTED
    
    # Source
    trigger: ADRTrigger = ADRTrigger.MANUAL
    source_task_id: Optional[str] = None
    source_feature_id: Optional[str] = None
    source_command: Optional[str] = None  # e.g., "feature-plan", "task-review"
    
    # Decision content
    context: str = ""                    # What situation prompted this decision
    decision: str = ""                   # What we decided
    rationale: str = ""                  # Why we decided this
    alternatives_considered: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    
    # Relationships
    supersedes: Optional[str] = None     # ADR ID this replaces
    superseded_by: Optional[str] = None  # ADR ID that replaced this
    related_adrs: List[str] = field(default_factory=list)
    
    # Temporal
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0              # How confident in this decision (0-1)
```

### ADR Service

```python
# guardkit/knowledge/adr_service.py

class ADRService:
    """Service for creating and managing ADRs."""
    
    def __init__(self, client: GraphitiClient):
        self.client = client
    
    async def create_adr(self, adr: ADREntity) -> str:
        """Create a new ADR in Graphiti."""
        
        # Generate ID if not provided
        if not adr.id:
            adr.id = await self._generate_adr_id()
        
        # Store as episode
        await self.client.add_episode(
            name=f"adr_{adr.id}",
            episode_body=json.dumps(asdict(adr), default=str),
            group_id="adrs",
            source_description=f"ADR from {adr.trigger.value}"
        )
        
        # Create relationship edges if linked to task/feature
        if adr.source_task_id:
            await self._create_task_edge(adr.id, adr.source_task_id)
        if adr.source_feature_id:
            await self._create_feature_edge(adr.id, adr.source_feature_id)
        if adr.supersedes:
            await self._create_supersedes_edge(adr.id, adr.supersedes)
        
        return adr.id
    
    async def search_adrs(
        self, 
        query: str, 
        status: Optional[ADRStatus] = None,
        num_results: int = 10
    ) -> List[ADREntity]:
        """Search for ADRs by topic."""
        
        results = await self.client.search(
            query=query,
            group_ids=["adrs"],
            num_results=num_results
        )
        
        adrs = [self._parse_adr(r) for r in results]
        
        if status:
            adrs = [a for a in adrs if a.status == status]
        
        return adrs
    
    async def supersede_adr(
        self, 
        old_adr_id: str, 
        new_adr: ADREntity
    ) -> str:
        """Create new ADR that supersedes an existing one."""
        
        # Update old ADR
        old_adr = await self.get_adr(old_adr_id)
        old_adr.status = ADRStatus.SUPERSEDED
        old_adr.superseded_by = new_adr.id
        await self._update_adr(old_adr)
        
        # Create new ADR with reference
        new_adr.supersedes = old_adr_id
        return await self.create_adr(new_adr)
    
    async def deprecate_adr(self, adr_id: str, reason: str) -> None:
        """Mark an ADR as deprecated."""
        
        adr = await self.get_adr(adr_id)
        adr.status = ADRStatus.DEPRECATED
        adr.deprecated_at = datetime.now()
        adr.consequences.append(f"Deprecated: {reason}")
        await self._update_adr(adr)
```

### Decision Significance Detection

Not every clarifying question answer is an ADR. Detect significance:

```python
# guardkit/knowledge/decision_detector.py

class DecisionDetector:
    """Detect whether a decision is significant enough to be an ADR."""
    
    # Indicators of significant decisions
    DECISION_INDICATORS = [
        "we will use",
        "we should use", 
        "prefer",
        "instead of",
        "rather than",
        "not include",
        "defer",
        "out of scope",
        "approach",
        "pattern",
        "architecture",
        "framework",
        "library",
    ]
    
    # Topics that are always significant
    SIGNIFICANT_TOPICS = [
        "security",
        "authentication",
        "authorization",
        "database",
        "api",
        "architecture",
        "testing",
        "deployment",
    ]
    
    def is_significant_decision(
        self, 
        question: str, 
        answer: str,
        context: Optional[str] = None
    ) -> tuple[bool, float]:
        """
        Determine if a Q&A represents a significant decision.
        
        Returns: (is_significant, confidence)
        """
        
        combined_text = f"{question} {answer}".lower()
        
        # Check for decision indicators
        indicator_count = sum(
            1 for indicator in self.DECISION_INDICATORS
            if indicator in combined_text
        )
        
        # Check for significant topics
        topic_match = any(
            topic in combined_text 
            for topic in self.SIGNIFICANT_TOPICS
        )
        
        # Calculate confidence
        confidence = min(1.0, (indicator_count * 0.2) + (0.3 if topic_match else 0))
        
        # Significant if confidence > 0.4
        is_significant = confidence > 0.4
        
        return is_significant, confidence
    
    def extract_decision_components(
        self, 
        question: str, 
        answer: str
    ) -> dict:
        """Extract ADR components from Q&A."""
        
        return {
            "title": self._extract_title(question, answer),
            "context": question,
            "decision": answer,
            "rationale": self._extract_rationale(answer),
            "alternatives": self._extract_alternatives(question, answer),
        }
```

### Integration Hooks

#### In Clarifying Questions Handler

```python
# guardkit/commands/lib/clarification/handler.py

async def handle_clarifying_answer(
    question: ClarifyingQuestion,
    answer: str,
    feature_id: str,
    adr_service: ADRService,
    detector: DecisionDetector
):
    """Handle a clarifying question answer, potentially creating ADR."""
    
    # Check if this is a significant decision
    is_significant, confidence = detector.is_significant_decision(
        question.text, 
        answer,
        context=question.context
    )
    
    if is_significant:
        # Extract decision components
        components = detector.extract_decision_components(question.text, answer)
        
        # Create ADR
        adr = ADREntity(
            title=components["title"],
            context=components["context"],
            decision=components["decision"],
            rationale=components["rationale"],
            alternatives_considered=components["alternatives"],
            trigger=ADRTrigger.CLARIFYING_QUESTION,
            source_feature_id=feature_id,
            source_command="feature-plan",
            confidence=confidence,
            tags=question.tags if hasattr(question, 'tags') else []
        )
        
        adr_id = await adr_service.create_adr(adr)
        
        logger.info(f"Created ADR {adr_id} from clarifying question")
        
        return adr_id
    
    return None
```

#### In Task Review

```python
# guardkit/commands/task_review.py

async def on_task_review_complete(
    task_id: str,
    review_result: ReviewResult,
    adr_service: ADRService
):
    """Handle task review completion, potentially creating ADRs."""
    
    if review_result.has_decisions:
        for decision in review_result.decisions:
            adr = ADREntity(
                title=decision.title,
                context=f"During review of {task_id}: {decision.context}",
                decision=decision.choice,
                rationale=decision.rationale,
                alternatives_considered=decision.alternatives,
                trigger=ADRTrigger.TASK_REVIEW,
                source_task_id=task_id,
                source_command="task-review",
                consequences=decision.implications
            )
            
            await adr_service.create_adr(adr)
```

#### Agent-Callable Decision Recording

```python
# guardkit/knowledge/decision_recorder.py

async def record_decision(
    title: str,
    decision: str,
    rationale: str,
    task_id: Optional[str] = None,
    alternatives: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> str:
    """
    Record an implementation decision as an ADR.
    
    Call this when making significant implementation choices.
    """
    
    adr_service = ADRService(await get_graphiti())
    
    adr = ADREntity(
        title=title,
        decision=decision,
        rationale=rationale,
        alternatives_considered=alternatives or [],
        trigger=ADRTrigger.IMPLEMENTATION_CHOICE,
        source_task_id=task_id,
        source_command="task-work",
        tags=tags or []
    )
    
    return await adr_service.create_adr(adr)
```

---

## Testing Requirements

### Unit Tests
- ADR entity creation and serialization
- Decision significance detection
- ADR search and filtering
- Supersede/deprecate logic

### Integration Tests
- ADR creation in Graphiti
- ADR retrieval by query
- Integration with clarifying questions
- Integration with task review

### Test Cases

```python
async def test_adr_creation():
    """Test basic ADR creation."""
    
    service = ADRService(graphiti_client)
    
    adr = ADREntity(
        title="Use repository pattern for data access",
        decision="Implement repository pattern for all database operations",
        rationale="Provides abstraction, improves testability",
        alternatives_considered=["Direct ORM usage", "Raw SQL"],
        trigger=ADRTrigger.TASK_REVIEW,
        source_task_id="TASK-123"
    )
    
    adr_id = await service.create_adr(adr)
    
    assert adr_id.startswith("ADR-")
    
    # Verify searchable
    results = await service.search_adrs("repository pattern")
    assert len(results) > 0
    assert results[0].id == adr_id

async def test_decision_significance_detection():
    """Test that significant decisions are detected."""
    
    detector = DecisionDetector()
    
    # Significant decision
    is_sig, conf = detector.is_significant_decision(
        question="Should we use SQL or NoSQL for this feature?",
        answer="We will use PostgreSQL because we need ACID transactions"
    )
    assert is_sig == True
    assert conf > 0.5
    
    # Not significant
    is_sig, conf = detector.is_significant_decision(
        question="What color should the button be?",
        answer="Blue"
    )
    assert is_sig == False
```

---

## Definition of Done

- [ ] ADREntity model implementation
- [ ] ADRService with create, search, supersede, deprecate
- [ ] Decision significance detector
- [ ] Integration with clarifying questions handler
- [ ] Integration with task review
- [ ] Agent-callable `record_decision()` function
- [ ] ADR ID generation (ADR-XXXX format)
- [ ] Task/feature relationship edges in Graphiti
- [ ] Unit tests with >80% coverage
- [ ] Integration tests with Graphiti
- [ ] Documentation updated

---

## Open Questions

1. **Significance threshold**: What confidence threshold for auto-creating ADRs?
   - Recommendation: 0.4 for auto-create, allow manual creation for anything

2. **Human confirmation**: Should significant decisions ask for confirmation before creating ADR?
   - Recommendation: No for MVP - create automatically, can be deprecated later

3. **ADR numbering**: Sequential (ADR-001) or hash-based?
   - Recommendation: Sequential within project for human readability

---

## References

- ADR-001: Graphiti Integration Scope
- FEAT-GI-001: Core Infrastructure
- FEAT-GI-007: ADR Discovery from Code (for discovered ADRs)
