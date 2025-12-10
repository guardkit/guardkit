---
id: TASK-053
title: Design Q&A flow structure for /template-init command
status: backlog
created: 2025-11-01T15:45:00Z
priority: medium
complexity: 5
estimated_hours: 6
tags: [template-init, interactive, qa-flow]
epic: EPIC-001
feature: template-init
dependencies: []
blocks: [TASK-054, TASK-055, TASK-056]
---

# TASK-053: Design Q&A Flow Structure for /template-init

## Objective

Create an interactive Q&A flow framework for `/template-init` that guides users through creating custom templates from scratch with:
- 9 structured sections
- Technology-aware question sets
- Input validation
- Progress tracking
- Session persistence (save/resume)

## Context

This is the foundation for `/template-init` (Phase 4). Unlike `/template-create` which analyzes existing code, `/template-init` helps users design templates for greenfield projects through guided conversation.

## Scope

### In Scope
- Q&A framework and structure
- Section definitions (9 sections)
- Progress tracking system
- Input validation
- Session save/resume
- Technology-aware branching

### Out of Scope
- Specific section implementations (TASK-054 through TASK-058)
- Agent discovery integration (TASK-059)
- Template generation (TASK-060)

## Requirements

### Functional Requirements

**REQ-1**: Define 9-section structure
```
The Q&A flow shall consist of 9 sections:
1. Basic Information (name, description, version)
2. Technology Stack (language, frameworks, tools)
3. Architecture & Patterns (MVVM, Clean Architecture, etc.)
4. Layer Structure (Domain, Repository, Service, Presentation)
5. Testing Strategy (framework, approach, coverage)
6. Quality Standards (SOLID, gates, thresholds)
7. Company Standards (optional: logging, security, docs)
8. Agent Discovery (automatic matching and selection)
9. Template Generation (validation, packaging)
```

**REQ-2**: Implement navigation
```
The system shall support:
- Next: Proceed to next question
- Previous: Go back to previous question
- Skip: Skip optional questions
- Jump: Jump to specific section
- Save: Save progress and exit
- Resume: Resume from saved session
```

**REQ-3**: Validate input
```
For each question, the system shall:
- Validate input type (string, number, choice)
- Enforce required fields
- Provide helpful error messages
- Suggest valid options when applicable
```

**REQ-4**: Track progress
```
The system shall:
- Display section progress (Section 2/9)
- Show completion percentage
- Highlight completed sections
- Indicate current section
```

**REQ-5**: Support technology branching
```
When technology is selected, the system shall:
- Load technology-specific questions
- Skip irrelevant questions
- Provide technology-appropriate defaults
- Adjust validation rules
```

## Acceptance Criteria

### AC1: Flow Structure
- [ ] 9 sections defined with clear boundaries
- [ ] Each section has title, description, questions
- [ ] Sections have dependencies (Technology → Architecture)
- [ ] Flow validates section completion

### AC2: Navigation
- [ ] Next/Previous navigation works
- [ ] Skip optional questions works
- [ ] Jump to section works
- [ ] Save/Resume works correctly
- [ ] Progress persisted to disk

### AC3: Input Validation
- [ ] String input validated (length, format)
- [ ] Number input validated (range)
- [ ] Choice input validated (valid option)
- [ ] Required fields enforced
- [ ] Helpful error messages displayed

### AC4: Progress Tracking
- [ ] Section progress displayed
- [ ] Completion percentage accurate
- [ ] Progress bar/indicator shown
- [ ] Current section highlighted

### AC5: Technology Branching
- [ ] React questions loaded for React
- [ ] Python questions loaded for Python
- [ ] .NET questions loaded for .NET
- [ ] Irrelevant questions skipped
- [ ] Defaults applied correctly

### AC6: Session Persistence
- [ ] Session saved to JSON file
- [ ] Session resumed from file
- [ ] Partial answers preserved
- [ ] Timestamp included
- [ ] Multiple sessions supported (by template name)

## Implementation Plan

### Step 1: Define Core Data Structures

```python
# installer/core/commands/lib/template_init/qa_flow.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import json
from pathlib import Path
from datetime import datetime

class QuestionType(Enum):
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    BOOLEAN = "boolean"

@dataclass
class Question:
    id: str
    text: str
    type: QuestionType
    required: bool = True
    default: Optional[Any] = None
    choices: List[str] = field(default_factory=list)
    validator: Optional[Callable[[Any], bool]] = None
    validation_message: Optional[str] = None
    help_text: Optional[str] = None
    depends_on: Optional[Dict[str, Any]] = None  # {"technology": "react"}

@dataclass
class Section:
    id: str
    title: str
    description: str
    questions: List[Question]
    required: bool = True
    depends_on: Optional[Dict[str, Any]] = None

@dataclass
class QASession:
    template_name: str
    started_at: str
    updated_at: str
    current_section: int
    current_question: int
    answers: Dict[str, Any]
    sections: List[Section]
    completed: bool = False

class QAFlowManager:
    SESSION_DIR = Path.home() / ".agentecflow" / "sessions"

    def __init__(self, template_name: str):
        self.template_name = template_name
        self.session = None
        self.sections = self._define_sections()

    def start_session(self) -> QASession:
        """Start new Q&A session"""
        pass

    def resume_session(self) -> Optional[QASession]:
        """Resume existing session"""
        pass

    def save_session(self):
        """Save current session to disk"""
        pass

    def next_question(self) -> Optional[Question]:
        """Get next question in flow"""
        pass

    def previous_question(self) -> Optional[Question]:
        """Get previous question"""
        pass

    def answer_question(self, answer: Any) -> bool:
        """Record answer and validate"""
        pass

    def jump_to_section(self, section_id: str):
        """Jump to specific section"""
        pass

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress info"""
        pass

    def _define_sections(self) -> List[Section]:
        """Define all 9 sections"""
        pass
```

### Step 2: Implement Section Definitions

```python
def _define_sections(self) -> List[Section]:
    """Define all 9 sections with questions"""

    sections = []

    # Section 1: Basic Information
    sections.append(Section(
        id="basic_info",
        title="Basic Information",
        description="Template metadata and identification",
        questions=[
            Question(
                id="template_name",
                text="Template name (e.g., mycompany-react):",
                type=QuestionType.TEXT,
                required=True,
                validator=lambda x: len(x) >= 3 and '-' in x,
                validation_message="Name must be at least 3 characters with hyphen separator"
            ),
            Question(
                id="description",
                text="Template description:",
                type=QuestionType.TEXT,
                required=True,
                validator=lambda x: len(x) >= 10,
                validation_message="Description must be at least 10 characters"
            ),
            Question(
                id="version",
                text="Initial version (default: 1.0.0):",
                type=QuestionType.TEXT,
                required=False,
                default="1.0.0"
            ),
            Question(
                id="author",
                text="Author/Team name:",
                type=QuestionType.TEXT,
                required=False
            )
        ]
    ))

    # Section 2: Technology Stack
    sections.append(Section(
        id="technology",
        title="Technology Stack",
        description="Select primary technology and frameworks",
        questions=[
            Question(
                id="technology",
                text="Primary technology:",
                type=QuestionType.CHOICE,
                required=True,
                choices=[
                    "React (TypeScript + Vite)",
                    "Python (FastAPI + pytest)",
                    ".NET MAUI (C# + XAML)",
                    "TypeScript API (NestJS)",
                    ".NET Microservice (FastEndpoints)",
                    "Other"
                ]
            ),
            Question(
                id="framework_version",
                text="Framework version (or 'latest'):",
                type=QuestionType.TEXT,
                required=False,
                default="latest"
            ),
            Question(
                id="additional_libraries",
                text="Key libraries/packages (comma-separated):",
                type=QuestionType.TEXT,
                required=False,
                help_text="Example: tailwindcss, react-query, zustand"
            )
        ]
    ))

    # Section 3: Architecture & Patterns
    sections.append(Section(
        id="architecture",
        title="Architecture & Patterns",
        description="Define architectural patterns and conventions",
        questions=[
            Question(
                id="architecture_pattern",
                text="Application architecture:",
                type=QuestionType.CHOICE,
                required=True,
                choices=[
                    "MVVM (Model-View-ViewModel)",
                    "Clean Architecture (Domain/Application/Infrastructure)",
                    "Domain-Driven Design (DDD)",
                    "Layered Architecture",
                    "Custom"
                ]
            ),
            Question(
                id="domain_operations_naming",
                text="Domain operations naming convention:",
                type=QuestionType.CHOICE,
                required=True,
                choices=[
                    "Verb-based (GetProducts, CreateOrder)",
                    "CQRS (Queries/Commands)",
                    "UseCase suffix (GetProductsUseCase)",
                    "Custom"
                ],
                depends_on={"architecture_pattern": ["MVVM", "Clean Architecture"]}
            ),
            Question(
                id="error_handling",
                text="Error handling pattern:",
                type=QuestionType.CHOICE,
                required=True,
                choices=[
                    "ErrorOr<T> (functional)",
                    "Result<T> (functional)",
                    "Exceptions (try/catch)",
                    "Custom"
                ]
            )
        ]
    ))

    # Additional sections defined similarly...
    # Section 4: Layer Structure
    # Section 5: Testing Strategy
    # Section 6: Quality Standards
    # Section 7: Company Standards (optional)
    # Section 8: Agent Discovery
    # Section 9: Template Generation

    return sections
```

### Step 3: Implement Navigation Logic

```python
def next_question(self) -> Optional[Question]:
    """Get next question, handling skips and dependencies"""

    if not self.session:
        return None

    section_idx = self.session.current_section
    question_idx = self.session.current_question

    # Get current section
    if section_idx >= len(self.sections):
        return None  # Flow complete

    section = self.sections[section_idx]

    # Check if section should be skipped (dependencies)
    if section.depends_on:
        if not self._check_dependencies(section.depends_on):
            self.session.current_section += 1
            self.session.current_question = 0
            return self.next_question()  # Recursive: skip section

    # Get next question in section
    if question_idx >= len(section.questions):
        # Move to next section
        self.session.current_section += 1
        self.session.current_question = 0
        return self.next_question()

    question = section.questions[question_idx]

    # Check question dependencies
    if question.depends_on:
        if not self._check_dependencies(question.depends_on):
            self.session.current_question += 1
            return self.next_question()  # Recursive: skip question

    return question

def _check_dependencies(self, depends_on: Dict[str, Any]) -> bool:
    """Check if dependencies are met"""

    for key, expected_values in depends_on.items():
        actual_value = self.session.answers.get(key)

        if isinstance(expected_values, list):
            if actual_value not in expected_values:
                return False
        else:
            if actual_value != expected_values:
                return False

    return True
```

### Step 4: Implement Session Persistence

```python
def save_session(self):
    """Save session to JSON file"""

    if not self.session:
        return

    self.SESSION_DIR.mkdir(parents=True, exist_ok=True)

    session_file = self.SESSION_DIR / f"{self.template_name}.json"

    self.session.updated_at = datetime.now().isoformat()

    session_data = {
        "template_name": self.session.template_name,
        "started_at": self.session.started_at,
        "updated_at": self.session.updated_at,
        "current_section": self.session.current_section,
        "current_question": self.session.current_question,
        "answers": self.session.answers,
        "completed": self.session.completed
    }

    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)

def resume_session(self) -> Optional[QASession]:
    """Resume existing session from file"""

    session_file = self.SESSION_DIR / f"{self.template_name}.json"

    if not session_file.exists():
        return None

    with open(session_file, 'r') as f:
        data = json.load(f)

    self.session = QASession(
        template_name=data["template_name"],
        started_at=data["started_at"],
        updated_at=data["updated_at"],
        current_section=data["current_section"],
        current_question=data["current_question"],
        answers=data["answers"],
        sections=self.sections,
        completed=data.get("completed", False)
    )

    return self.session
```

### Step 5: Implement Progress Tracking

```python
def get_progress(self) -> Dict[str, Any]:
    """Get current progress information"""

    if not self.session:
        return {}

    total_questions = sum(len(s.questions) for s in self.sections)
    answered_questions = len(self.session.answers)

    completion_pct = int((answered_questions / total_questions) * 100)

    current_section = self.sections[self.session.current_section] if self.session.current_section < len(self.sections) else None

    return {
        "section": f"{self.session.current_section + 1}/{len(self.sections)}",
        "current_section_title": current_section.title if current_section else "Complete",
        "questions_answered": answered_questions,
        "questions_total": total_questions,
        "completion_percentage": completion_pct,
        "sections_completed": self.session.current_section,
        "sections_total": len(self.sections)
    }
```

## Testing Strategy

### Unit Tests

```python
def test_section_definition():
    """Should define all 9 sections"""
    flow = QAFlowManager("test-template")

    assert len(flow.sections) == 9
    assert flow.sections[0].id == "basic_info"
    assert flow.sections[1].id == "technology"

def test_navigation_next():
    """Should navigate to next question"""
    flow = QAFlowManager("test-template")
    flow.start_session()

    q1 = flow.next_question()
    assert q1.id == "template_name"

    flow.answer_question("mycompany-react")

    q2 = flow.next_question()
    assert q2.id == "description"

def test_skip_dependent_question():
    """Should skip questions with unmet dependencies"""
    flow = QAFlowManager("test-template")
    flow.start_session()

    # Answer technology as React
    flow.session.answers["architecture_pattern"] = "Layered Architecture"

    # Question with depends_on should be skipped
    question = flow.next_question()
    # Should skip domain_operations_naming (depends on MVVM/Clean Architecture)
    assert question.id != "domain_operations_naming"

def test_session_persistence():
    """Should save and resume session"""
    flow = QAFlowManager("test-template")
    flow.start_session()

    flow.answer_question("test-value")
    flow.save_session()

    # Resume in new instance
    flow2 = QAFlowManager("test-template")
    session = flow2.resume_session()

    assert session is not None
    assert session.template_name == "test-template"
    assert len(session.answers) > 0
```

## Files to Create

1. `installer/core/commands/lib/template_init/qa_flow.py` - Flow manager (~500 lines)
2. `installer/core/commands/lib/template_init/sections.py` - Section definitions (~600 lines)
3. `installer/core/commands/lib/template_init/validators.py` - Input validators (~150 lines)
4. `tests/unit/test_qa_flow.py` - Unit tests (~400 lines)
5. `tests/fixtures/qa_flow_sessions/` - Session fixtures for testing

## Definition of Done

- [ ] QAFlowManager class implemented
- [ ] All 9 sections defined
- [ ] Navigation (next/previous/jump) working
- [ ] Input validation functional
- [ ] Session save/resume working
- [ ] Progress tracking accurate
- [ ] Technology branching implemented
- [ ] Unit tests passing (>85% coverage)
- [ ] Documentation and examples

## Success Metrics

- Complete flow in <15 minutes (user experience)
- Session persistence: 100% reliable
- Dependency logic: 0 errors
- Navigation: Smooth, no stuck states
- Validation: Clear, helpful messages

## Related Tasks

- **Blocks**: TASK-054 (Basic Information Section)
- **Blocks**: TASK-055 (Technology Stack Section)
- **Blocks**: TASK-056 (Architecture Section)
- **Epic**: EPIC-001 (Template Creation Automation)

---

**Estimated Time**: 6 hours
**Complexity**: 5/10 (Medium)
**Priority**: MEDIUM (Foundation for template-init)
