---
id: TASK-FP002-001
title: Research Template Spec Parser
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 1
implementation_mode: task-work
complexity: 5
complexity_score: 5
type: implementation
domain_tags:
- spec-parser
- markdown-parsing
- data-extraction
files_to_create:
- guardkit/planning/spec_parser.py
- tests/unit/test_spec_parser.py
files_to_modify: []
files_not_to_touch:
- .claude/commands/feature-plan.md
- guardkit/cli/
dependencies: []
relevant_decisions:
- D2
- D6
turn_budget:
  expected: 2
  max: 5
graphiti_context_budget: 4000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T17:38:08.347313'
  last_updated: '2026-02-10T17:50:11.756660'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T17:38:08.347313'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-FP002-001: Research Template Spec Parser

## Description

Create `guardkit/planning/spec_parser.py` that parses the Research-to-Implementation Template markdown format into structured Python dataclasses. This is the foundation module — all other tasks depend on its output types.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/spec_parser.py`
- [ ] File exists: `tests/unit/test_spec_parser.py`
- [ ] Function `parse_research_template(Path) -> ParsedSpec` exists and is importable
- [ ] Parses Decision Log table into `list[Decision]` with fields: number, title, rationale, alternatives_rejected, adr_status
- [ ] Parses Implementation Tasks section into `list[TaskDefinition]` with all metadata fields
- [ ] Parses Warnings & Constraints into `list[str]`
- [ ] Parses Problem Statement section into `str`
- [ ] Parses Out of Scope section into `list[str]`
- [ ] Parses Open Questions into `list[ResolvedQuestion]`
- [ ] Handles missing sections gracefully (returns warnings, not exceptions)
- [ ] Tests pass: `pytest tests/unit/test_spec_parser.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/spec_parser.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_spec_parser.py -v
ruff check guardkit/planning/spec_parser.py
python -c "from guardkit.planning.spec_parser import parse_research_template; print('Import OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Do NOT modify any existing files
- Use standard library `re` and `dataclasses` — no external markdown parsing libraries
- Parse markdown tables using regex, not a full AST parser

## Implementation Notes (Prescriptive)

Use regex-based section extraction keyed on `## N. Section Title` headers. The Decision Log is a markdown table starting with `| # | Decision |`. Each task block starts with `### Task N:`. Warnings are a bullet list under `**Warnings & Constraints**`. The parser should be lenient — sections may use slightly different heading levels or have extra whitespace.

### Dataclass Definitions

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

@dataclass
class Decision:
    number: str  # "D1", "D2", etc.
    title: str
    rationale: str
    alternatives_rejected: str
    adr_status: str  # "Accepted", "Proposed", "Superseded"

@dataclass
class TaskDefinition:
    name: str
    complexity: str  # "low", "medium", "high"
    complexity_score: int
    task_type: str  # "implementation", "refactor", "integration", "configuration", "documentation"
    domain_tags: list[str]
    files_to_create: list[str]
    files_to_modify: list[str]
    files_not_to_touch: list[str]
    dependencies: list[str]
    inputs: str
    outputs: str
    relevant_decisions: list[str]
    acceptance_criteria: list[str]
    implementation_notes: str
    player_constraints: list[str]
    coach_validation_commands: list[str]
    turn_budget_expected: int = 2
    turn_budget_max: int = 5

@dataclass
class ResolvedQuestion:
    question: str
    resolution: str

@dataclass
class Component:
    name: str
    file_path: str
    purpose: str
    new_or_modified: str

@dataclass
class TestStrategy:
    unit_tests: list[dict[str, str]]
    integration_tests: list[dict[str, str]]
    manual_verification: list[str]

@dataclass
class DependencySet:
    python: list[str]
    system: list[str]
    environment: dict[str, str]

@dataclass
class APIContract:
    name: str
    content: str

@dataclass
class ParsedSpec:
    problem_statement: str
    decisions: list[Decision]
    warnings: list[str]
    components: list[Component]
    data_flow: str
    message_schemas: dict[str, Any]
    api_contracts: list[APIContract]
    tasks: list[TaskDefinition]
    test_strategy: Optional[TestStrategy] = None
    dependencies: Optional[DependencySet] = None
    file_tree: str = ""
    out_of_scope: list[str] = field(default_factory=list)
    resolved_questions: list[ResolvedQuestion] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
```

### Key Design Decisions
- Missing sections produce entries in `parse_warnings`, not exceptions
- The parser must handle the exact format from `docs/research/system-level-understanding/research-to-implementation-template.md`
- Use `re.DOTALL` for multi-line section extraction
- Section headers use `## N.` pattern (e.g., `## 1. Problem Statement`, `## 2. Decision Log`)
