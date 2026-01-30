# FEAT-GR-004: Interactive Knowledge Capture

> **Purpose**: Enable interactive Q&A sessions to build comprehensive project knowledge through guided conversation, including AutoBuild workflow customization.
>
> **Priority**: Medium
> **Estimated Complexity**: 5
> **Estimated Time**: 19 hours (revised from 17h based on TASK-REV-1505 review)
> **Dependencies**: FEAT-GR-001 (Project Knowledge Seeding), FEAT-GR-002 (Context Addition Command)
> **Reviewed**: TASK-REV-1505 (2026-01-30)

---

## Problem Statement

Project knowledge often exists in developers' heads but isn't captured anywhere:

1. **Implicit decisions** - "We chose FastMCP because..." 
2. **Domain knowledge** - "A 'focus area' means..."
3. **Constraints** - "We can't use X because of Y"
4. **Goals** - "The ultimate objective is..."

Currently, this knowledge is lost between sessions. Interactive capture provides a natural way to extract and persist this knowledge.

---

## Proposed Solution

### Two Capture Modes

#### 1. CLI Interactive Mode

```bash
# Start interactive knowledge capture session
guardkit graphiti capture --interactive

# With specific focus
guardkit graphiti capture --interactive --focus project-overview
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus domain
```

#### 2. Task Review Integration

```bash
# During task review, capture insights
/task-review TASK-XXX --capture-knowledge

# Standalone knowledge review
/task-review --knowledge-only
```

### Interactive Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interactive Knowledge Capture                        │
│                                                                         │
│  1. Analyze existing knowledge (what we already know)                  │
│         ↓                                                               │
│  2. Identify gaps (what's missing or unclear)                          │
│         ↓                                                               │
│  3. Ask targeted questions                                              │
│         ↓                                                               │
│  4. Parse and structure answers                                         │
│         ↓                                                               │
│  5. Seed episodes to Graphiti                                          │
│         ↓                                                               │
│  6. Summarize what was learned                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Requirements

### Knowledge Gap Analyzer

```python
# guardkit/knowledge/gap_analyzer.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

from .graphiti_client import get_graphiti


class KnowledgeCategory(str, Enum):
    PROJECT_OVERVIEW = "project_overview"
    ARCHITECTURE = "architecture"
    DOMAIN = "domain"
    CONSTRAINTS = "constraints"
    DECISIONS = "decisions"
    GOALS = "goals"
    # NEW categories from TASK-REV-1505
    ROLE_CUSTOMIZATION = "role_customization"
    QUALITY_GATES = "quality_gates"
    WORKFLOW_PREFERENCES = "workflow_preferences"


@dataclass
class KnowledgeGap:
    """Represents a gap in project knowledge."""
    
    category: KnowledgeCategory
    question: str
    importance: str  # high | medium | low
    context: str  # Why we're asking
    example_answer: Optional[str] = None


class KnowledgeGapAnalyzer:
    """Analyzes existing knowledge to identify gaps."""
    
    # Questions by category with importance
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
        # NEW categories from TASK-REV-1505 - AutoBuild workflow customization
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
        self.graphiti = get_graphiti()
    
    async def analyze_gaps(
        self,
        focus: Optional[KnowledgeCategory] = None,
        max_questions: int = 10
    ) -> List[KnowledgeGap]:
        """Analyze existing knowledge and identify gaps."""
        
        # Get existing knowledge
        existing = await self._get_existing_knowledge()
        
        # Find gaps
        gaps = []
        categories = [focus] if focus else list(KnowledgeCategory)
        
        for category in categories:
            templates = self.QUESTION_TEMPLATES.get(category, [])
            
            for template in templates:
                # Check if we already have this knowledge
                check_field = template.get("check_field")
                if check_field and self._has_knowledge(existing, check_field):
                    continue
                
                gaps.append(KnowledgeGap(
                    category=category,
                    question=template["question"],
                    importance=template["importance"],
                    context=template["context"],
                    example_answer=template.get("example_answer")
                ))
        
        # Sort by importance and limit
        gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}[g.importance])
        return gaps[:max_questions]
    
    async def _get_existing_knowledge(self) -> Dict:
        """Query Graphiti for existing project knowledge."""
        
        results = await self.graphiti.search(
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
            "architecture_summary": None,
            "key_components": None,
            "technical_constraints": None,
            "domain_terminology": None
        }
        
        for result in results:
            fact = result.get("fact", "")
            # Simple heuristic to check coverage
            if "purpose" in fact.lower():
                existing["purpose"] = fact
            if "user" in fact.lower() and "target" in fact.lower():
                existing["target_users"] = fact
            # ... etc
        
        return existing
    
    def _has_knowledge(self, existing: Dict, field: str) -> bool:
        """Check if we have knowledge for a field."""
        return existing.get(field) is not None
```

### Interactive Capture Session

```python
# guardkit/knowledge/interactive_capture.py

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .gap_analyzer import KnowledgeGapAnalyzer, KnowledgeGap, KnowledgeCategory
from .graphiti_client import get_graphiti


@dataclass
class CapturedKnowledge:
    """Knowledge captured from a Q&A answer."""
    
    category: KnowledgeCategory
    question: str
    answer: str
    extracted_facts: List[str] = field(default_factory=list)
    confidence: float = 1.0


class InteractiveCaptureSession:
    """Runs an interactive knowledge capture session."""
    
    def __init__(self):
        self.graphiti = get_graphiti()
        self.analyzer = KnowledgeGapAnalyzer()
        self.captured: List[CapturedKnowledge] = []
    
    async def run_session(
        self,
        focus: Optional[KnowledgeCategory] = None,
        max_questions: int = 10,
        ui_callback=None  # For CLI/UI integration
    ) -> List[CapturedKnowledge]:
        """Run the interactive capture session."""
        
        # 1. Analyze gaps
        gaps = await self.analyzer.analyze_gaps(focus, max_questions)
        
        if not gaps:
            if ui_callback:
                ui_callback("info", "No knowledge gaps identified - your project knowledge is comprehensive!")
            return []
        
        # 2. Intro
        if ui_callback:
            ui_callback("intro", self._format_intro(gaps))
        
        # 3. Ask questions
        for i, gap in enumerate(gaps, 1):
            if ui_callback:
                # Display question
                ui_callback("question", {
                    "number": i,
                    "total": len(gaps),
                    "category": gap.category.value,
                    "question": gap.question,
                    "context": gap.context
                })
                
                # Get answer
                answer = ui_callback("get_input")
                
                if answer.lower() in ["skip", "s", ""]:
                    continue
                
                if answer.lower() in ["quit", "q", "exit"]:
                    break
                
                # Process answer
                captured = await self._process_answer(gap, answer)
                self.captured.append(captured)
                
                # Feedback
                ui_callback("captured", {
                    "facts": captured.extracted_facts,
                    "category": captured.category.value
                })
        
        # 4. Save to Graphiti
        await self._save_captured_knowledge()
        
        # 5. Summary
        if ui_callback:
            ui_callback("summary", self._format_summary())
        
        return self.captured
    
    async def _process_answer(
        self,
        gap: KnowledgeGap,
        answer: str
    ) -> CapturedKnowledge:
        """Process an answer and extract structured facts."""
        
        # Extract key facts from the answer
        # In a full implementation, this could use LLM to extract structured data
        facts = self._extract_facts(answer, gap.category)
        
        return CapturedKnowledge(
            category=gap.category,
            question=gap.question,
            answer=answer,
            extracted_facts=facts
        )
    
    def _extract_facts(self, answer: str, category: KnowledgeCategory) -> List[str]:
        """Extract key facts from an answer."""
        
        # Simple extraction - split by sentences and clean
        sentences = answer.replace('\n', ' ').split('.')
        facts = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        # Prefix with category context
        prefixed = []
        for fact in facts:
            if category == KnowledgeCategory.PROJECT_OVERVIEW:
                prefixed.append(f"Project: {fact}")
            elif category == KnowledgeCategory.ARCHITECTURE:
                prefixed.append(f"Architecture: {fact}")
            elif category == KnowledgeCategory.DOMAIN:
                prefixed.append(f"Domain: {fact}")
            elif category == KnowledgeCategory.CONSTRAINTS:
                prefixed.append(f"Constraint: {fact}")
            elif category == KnowledgeCategory.DECISIONS:
                prefixed.append(f"Decision: {fact}")
            else:
                prefixed.append(fact)
        
        return prefixed
    
    async def _save_captured_knowledge(self):
        """Save all captured knowledge to Graphiti."""
        
        # Group by category
        by_category: Dict[KnowledgeCategory, List[CapturedKnowledge]] = {}
        for captured in self.captured:
            if captured.category not in by_category:
                by_category[captured.category] = []
            by_category[captured.category].append(captured)
        
        # Create episodes per category
        for category, items in by_category.items():
            # Aggregate facts
            all_facts = []
            qa_pairs = []
            for item in items:
                all_facts.extend(item.extracted_facts)
                qa_pairs.append({
                    "question": item.question,
                    "answer": item.answer
                })
            
            # Determine group_id
            group_id = self._category_to_group_id(category)
            
            # Create episode
            episode_data = {
                "entity_type": "captured_knowledge",
                "category": category.value,
                "facts": all_facts,
                "qa_pairs": qa_pairs,
                "source": "interactive_capture",
                "captured_at": datetime.now().isoformat()
            }
            
            await self.graphiti.add_episode(
                name=f"captured_{category.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                episode_body=json.dumps(episode_data),
                group_id=group_id
            )
    
    def _category_to_group_id(self, category: KnowledgeCategory) -> str:
        """Map category to Graphiti group ID."""

        mapping = {
            KnowledgeCategory.PROJECT_OVERVIEW: "project_overview",
            KnowledgeCategory.ARCHITECTURE: "project_architecture",
            KnowledgeCategory.DOMAIN: "domain_knowledge",
            KnowledgeCategory.CONSTRAINTS: "project_constraints",
            KnowledgeCategory.DECISIONS: "project_decisions",
            KnowledgeCategory.GOALS: "project_overview",
            # NEW mappings from TASK-REV-1505
            KnowledgeCategory.ROLE_CUSTOMIZATION: "role_constraints",
            KnowledgeCategory.QUALITY_GATES: "quality_gate_configs",
            KnowledgeCategory.WORKFLOW_PREFERENCES: "implementation_modes"
        }
        return mapping.get(category, "project_knowledge")
    
    def _format_intro(self, gaps: List[KnowledgeGap]) -> str:
        """Format introduction message."""
        
        high_priority = sum(1 for g in gaps if g.importance == "high")
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║              Interactive Knowledge Capture Session                ║
╠══════════════════════════════════════════════════════════════════╣
║  I've identified {len(gaps)} knowledge gaps for your project.              ║
║  {high_priority} are high priority.                                         ║
║                                                                  ║
║  Commands:                                                       ║
║    - Type your answer to capture knowledge                       ║
║    - 'skip' or 's' to skip a question                           ║
║    - 'quit' or 'q' to end session early                         ║
╚══════════════════════════════════════════════════════════════════╝
"""
    
    def _format_summary(self) -> str:
        """Format session summary."""
        
        by_category = {}
        for c in self.captured:
            cat = c.category.value
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] += len(c.extracted_facts)
        
        lines = ["", "Session Summary:", "-" * 40]
        total = 0
        for cat, count in by_category.items():
            lines.append(f"  {cat}: {count} facts captured")
            total += count
        lines.append("-" * 40)
        lines.append(f"  Total: {total} facts added to Graphiti")
        lines.append("")
        
        return '\n'.join(lines)
```

### CLI Integration

```python
# guardkit/cli/graphiti_commands.py (addition)

@graphiti.command("capture")
@click.option(
    "--interactive", "-i",
    is_flag=True,
    help="Run interactive Q&A session"
)
@click.option(
    "--focus",
    type=click.Choice([
        "project-overview", "architecture", "domain",
        "constraints", "decisions",
        # NEW focus areas from TASK-REV-1505
        "role-customization", "quality-gates", "workflow-preferences"
    ]),
    help="Focus on specific knowledge category"
)
@click.option(
    "--max-questions",
    type=int,
    default=10,
    help="Maximum questions to ask"
)
def capture(interactive: bool, focus: Optional[str], max_questions: int):
    """Capture project knowledge through Q&A.
    
    Examples:
    
        guardkit graphiti capture --interactive
        
        guardkit graphiti capture --interactive --focus architecture
    """
    import asyncio
    
    if not interactive:
        click.echo("Use --interactive flag to start a capture session")
        return
    
    # Map focus string to enum
    focus_enum = None
    if focus:
        focus_enum = KnowledgeCategory(focus.replace("-", "_"))
    
    # Create UI callback
    def ui_callback(event: str, data=None):
        if event == "info":
            click.echo(click.style(data, fg="blue"))
        elif event == "intro":
            click.echo(data)
        elif event == "question":
            click.echo("")
            click.echo(click.style(
                f"[{data['number']}/{data['total']}] {data['category'].upper()}",
                fg="cyan", bold=True
            ))
            click.echo(click.style(f"Context: {data['context']}", fg="white", dim=True))
            click.echo("")
            click.echo(click.style(data['question'], fg="yellow", bold=True))
        elif event == "get_input":
            return click.prompt("Your answer", default="")
        elif event == "captured":
            click.echo(click.style("✓ Captured:", fg="green"))
            for fact in data['facts'][:3]:  # Show first 3
                click.echo(f"  - {fact[:80]}...")
        elif event == "summary":
            click.echo(click.style(data, fg="green"))
    
    # Run session
    session = InteractiveCaptureSession()
    asyncio.run(session.run_session(
        focus=focus_enum,
        max_questions=max_questions,
        ui_callback=ui_callback
    ))
```

---

## Success Criteria

1. **Gap analysis works** - Correctly identifies missing knowledge
2. **Interactive flow smooth** - Natural Q&A experience
3. **Facts extracted** - Answers parsed into structured facts
4. **Knowledge persisted** - Episodes created in Graphiti
5. **Queryable results** - Captured knowledge can be retrieved
6. **Skip/quit work** - User can skip questions or end early

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-004A | Implement KnowledgeGapAnalyzer | 3h |
| TASK-GR-004B | Implement InteractiveCaptureSession | 3h |
| TASK-GR-004C | Create CLI capture command | 2h |
| TASK-GR-004D | Add fact extraction logic | 2h |
| TASK-GR-004E | Implement Graphiti persistence | 2h |
| TASK-GR-004F | Add /task-review --capture-knowledge integration | 2h |
| TASK-GR-004G | **NEW**: Add AutoBuild workflow customization questions | 2h |
| TASK-GR-004H | Add tests (including AutoBuild categories) | 2h |
| TASK-GR-004I | Update documentation | 1h |

**Total Estimate**: 19 hours (revised from 17h based on TASK-REV-1505 review)

### New Tasks Rationale (from TASK-REV-1505)

- **TASK-GR-004G**: Adds interactive capture for role customization, quality gate thresholds, and workflow preferences - addressing TASK-REV-7549 findings on role reversal and threshold drift

---

## Usage Example

```
$ guardkit graphiti capture --interactive

╔══════════════════════════════════════════════════════════════════╗
║              Interactive Knowledge Capture Session                ║
╠══════════════════════════════════════════════════════════════════╣
║  I've identified 8 knowledge gaps for your project.              ║
║  4 are high priority.                                            ║
║                                                                  ║
║  Commands:                                                       ║
║    - Type your answer to capture knowledge                       ║
║    - 'skip' or 's' to skip a question                           ║
║    - 'quit' or 'q' to end session early                         ║
╚══════════════════════════════════════════════════════════════════╝

[1/8] PROJECT_OVERVIEW
Context: Helps Claude understand the 'why' behind implementation decisions

What is the primary purpose of this project?
Your answer: youtube-mcp is an MCP server that extracts insights from YouTube videos 
and podcasts, making content consumable during activities like driving or walking 
when full attention isn't available.

✓ Captured:
  - Project: youtube-mcp is an MCP server that extracts insights from YouTube v...
  - Project: making content consumable during activities like driving or walking...

[2/8] PROJECT_OVERVIEW
Context: Guides prioritization and feature decisions

What are the key goals this project aims to achieve?
Your answer: Extract actionable entrepreneurial strategies and investment trends. 
Support focus area presets. Integrate with Claude Desktop for natural conversation.

✓ Captured:
  - Project: Extract actionable entrepreneurial strategies and investment trends...
  - Project: Support focus area presets...
  - Project: Integrate with Claude Desktop for natural conversation...

[3/8] ARCHITECTURE
Context: Essential for understanding how components fit together

What is the high-level architecture of this project?
Your answer: Three-phase architecture where Claude orchestrates between YouTube MCP, 
Podcast MCP, and Google Sheets MCP. Each MCP is a separate server.

✓ Captured:
  - Architecture: Three-phase architecture where Claude orchestrates between You...
  - Architecture: Each MCP is a separate server...

...

Session Summary:
----------------------------------------
  project_overview: 5 facts captured
  architecture: 3 facts captured
  constraints: 2 facts captured
----------------------------------------
  Total: 10 facts added to Graphiti
```

---

## Integration with /task-review

When running `/task-review --capture-knowledge`:

```python
# In task_review.py

async def task_review_with_knowledge(task_id: str, capture_knowledge: bool):
    """Run task review with optional knowledge capture."""
    
    # Normal task review flow
    findings = await execute_task_review(task_id)
    
    # If capture_knowledge flag, run mini-capture session
    if capture_knowledge:
        print("\n--- Knowledge Capture ---")
        print("Based on this review, let me capture any insights.\n")
        
        # Ask context-specific questions
        questions = [
            f"What did you learn about {task.type} from this review?",
            "Were there any decisions made that should be remembered?",
            "Are there any warnings for similar future tasks?"
        ]
        
        session = InteractiveCaptureSession()
        # Run abbreviated session with task-specific questions
        await session.run_abbreviated(questions, task_context=task)
```

---

## AutoBuild Workflow Customization (NEW - from TASK-REV-1505)

Interactive capture now supports customizing AutoBuild workflows to prevent common issues:

### Role Customization Session

```bash
$ guardkit graphiti capture --interactive --focus role-customization

[1/3] ROLE_CUSTOMIZATION
Context: Prevents autonomous changes to sensitive areas (from TASK-REV-7549)

What tasks should the AI Player ALWAYS ask about before implementing?
Your answer: Database schema changes, auth/security changes, deployment configs

✓ Captured:
  - Player ask_before: Database schema changes...
  - Player ask_before: auth/security changes...
  - Player ask_before: deployment configs...

[2/3] ROLE_CUSTOMIZATION
Context: Defines human oversight boundaries (from TASK-REV-7549)

What decisions should the AI Coach escalate to humans rather than auto-approve?
Your answer: Architecture changes, breaking API changes, anything touching payments

✓ Captured:
  - Coach escalate_when: Architecture changes...
  - Coach escalate_when: breaking API changes...
  - Coach escalate_when: anything touching payments...
```

### Quality Gate Customization

```bash
$ guardkit graphiti capture --interactive --focus quality-gates

[1/2] QUALITY_GATES
Context: Customizes quality gate thresholds (from TASK-REV-7549)

What test coverage threshold is acceptable for this project?
Your answer: 85% for core business logic, 70% for utilities, 60% for scaffolding

✓ Captured:
  - Quality gate: coverage 85% for core business logic
  - Quality gate: coverage 70% for utilities
  - Quality gate: coverage 60% for scaffolding
```

These captured preferences are stored in `role_constraints`, `quality_gate_configs`, and `implementation_modes` groups and are automatically loaded during `/feature-build` workflows.

---

## Future Enhancements

1. **LLM-powered extraction** - Use Claude to extract more structured facts
2. **Confirmation prompts** - "I understood X, is that correct?"
3. **Knowledge health score** - Track completeness over time
4. **Scheduled reminders** - "It's been 2 weeks, want to update project knowledge?"
5. **Team knowledge sharing** - Multi-user knowledge capture and merge
6. **AutoBuild tuning wizard** - Guided workflow to optimize AutoBuild settings based on project type
