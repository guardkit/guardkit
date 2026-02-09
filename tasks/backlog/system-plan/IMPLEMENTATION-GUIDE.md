# Implementation Guide: /system-plan Command (FEAT-SP-001)

## Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────┐
│ .claude/commands/    │     │ guardkit/cli/         │
│ system-plan.md       │     │ system_plan.py        │
│ (slash command spec) │     │ (Click CLI command)   │
└────────┬────────────┘     └────────┬─────────────┘
         │                           │
         │    Both call into:        │
         ▼                           ▼
┌────────────────────────────────────────────────┐
│ guardkit/planning/system_plan.py               │
│ (Main orchestration logic)                     │
│  - detect_mode() → setup/refine/review         │
│  - run_setup() → entities + files + Graphiti   │
│  - run_refine() → targeted updates             │
│  - run_review() → impact analysis              │
└──────────┬──────────┬──────────┬───────────────┘
           │          │          │
    ┌──────▼──┐  ┌────▼────┐  ┌─▼──────────────┐
    │question │  │arch     │  │graphiti_arch.py │
    │adapter  │  │writer   │  │SystemPlan       │
    │.py      │  │.py      │  │Graphiti         │
    └─────────┘  └────┬────┘  └──────┬──────────┘
                      │              │
              ┌───────▼───┐   ┌──────▼──────────┐
              │templates/  │   │GraphitiClient   │
              │*.md.j2     │   │(existing)       │
              └────────────┘   └─────────────────┘
                                     │
              ┌──────────────────────▼───────────┐
              │ guardkit/knowledge/entities/      │
              │ component.py, system_context.py,  │
              │ crosscutting.py,                  │
              │ architecture_context.py           │
              └──────────────────────────────────┘
```

## Wave 1: Foundation Layer (No Dependencies)

### TASK-SP-001: Entity Definitions
**Files**: `guardkit/knowledge/entities/component.py`, `system_context.py`, `crosscutting.py`, `architecture_context.py`

Key conventions:
- Follow `feature_overview.py` pattern exactly
- `to_episode_body()` returns dict with domain data only
- `entity_id` property is deterministic (based on name slug)
- Use `@dataclass` with `field(default_factory=list)` for collections
- `ArchitectureContext.format_for_prompt()` filters by score > 0.5

### TASK-SP-002: Complexity Gating
**Files**: `guardkit/planning/__init__.py`, `guardkit/planning/complexity_gating.py`

Pure functions, no external dependencies. Creates the `guardkit/planning/` package.

## Wave 2: Core Logic Layer (Depends on Wave 1 Entities)

### TASK-SP-003: Graphiti Operations
**Files**: `guardkit/planning/graphiti_arch.py`

Critical patterns:
```python
# CORRECT: use get_group_id()
group_id = self.client.get_group_id("project_architecture")

# WRONG: hardcode group ID
group_id = "project_architecture"

# CORRECT: use upsert_episode() with entity_id
await self.client.upsert_episode(
    name=f"Component: {component.name}",
    episode_body=json.dumps(component.to_episode_body()),
    group_id=group_id,
    entity_id=component.entity_id,
    source="system_plan",
    entity_type=component.entity_type,
)

# WRONG: use add_episode() (creates duplicates)
await self.client.add_episode(...)

# CORRECT: use num_results for search
results = await self.client.search(query=..., group_ids=[...], num_results=10)

# WRONG: use limit for search
results = await self.client.search(query=..., group_ids=[...], limit=10)
```

### TASK-SP-004: Question Adapter
**Files**: `guardkit/planning/question_adapter.py`

Question adaptation rules:
- DDD questions only when `methodology == "ddd"`
- Event-driven questions when `methodology in ("event_driven", "ddd")`
- Microservice questions only when `deployment != "monolith"`
- "Not sure" defaults to modular

### TASK-SP-005: Architecture Writer
**Files**: `guardkit/planning/architecture_writer.py`, `guardkit/templates/*.md.j2`

Template loading:
```python
import jinja2

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        Path(__file__).parent.parent / "templates"
    ),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

## Wave 3: User-Facing Layer (Depends on Wave 2)

### TASK-SP-006: CLI Command
**Files**: `guardkit/cli/system_plan.py`, `guardkit/planning/system_plan.py`, `guardkit/planning/mode_detector.py`

CLI registration in `main.py`:
```python
from guardkit.cli.system_plan import system_plan
cli.add_command(system_plan)
```

Async boundary pattern (from `review.py`):
```python
result = asyncio.run(some_async_function(...))
```

### TASK-SP-007: Slash Command Spec
**Files**: `.claude/commands/system-plan.md`

This is a Claude Code spec file, not Python. It contains instructions that Claude interprets.

## Wave 4: Validation Layer (Depends on All)

### TASK-SP-008: Integration & Seam Tests
**Files**: `tests/integration/test_system_plan_seams.py`, `tests/integration/test_system_plan_e2e.py`

Covers 9 technology seams — see task file for complete checklist.

## Technology Seam Reference

| Seam | Risk | Historical Bug | Test Coverage |
|------|------|----------------|---------------|
| Entity serialization | `_metadata` leak | — | TASK-SP-001 unit + SP-008 integration |
| Async/sync boundary | `await` on sync | TASK-FIX-GCI0 | SP-006 unit + SP-008 integration |
| Group ID prefixing | Hardcoded ID | — | SP-003 unit + SP-008 integration |
| Upsert idempotency | Duplicate episodes | — | SP-003 unit + SP-008 integration |
| Graceful degradation | Crash on None | TASK-FIX-64EE | SP-003 unit + SP-008 integration |
| Template rendering | Jinja2 error | — | SP-005 unit + SP-008 integration |
| CLI registration | Missing command | — | SP-006 unit + SP-008 integration |
| Context assembly | Malformed prompt | — | SP-001 unit + SP-008 integration |
| Feature-plan integration | Empty context | — | SP-008 integration |

## File Structure (Final)

```
guardkit/
├── planning/
│   ├── __init__.py
│   ├── system_plan.py            # Main orchestration
│   ├── mode_detector.py          # detect_mode() async
│   ├── question_adapter.py       # SetupQuestionAdapter
│   ├── architecture_writer.py    # Jinja2 markdown writer
│   ├── graphiti_arch.py          # SystemPlanGraphiti
│   └── complexity_gating.py      # Token budget gating
│
├── knowledge/entities/
│   ├── component.py              # ComponentDef
│   ├── system_context.py         # SystemContextDef
│   ├── crosscutting.py           # CrosscuttingConcernDef
│   └── architecture_context.py   # ArchitectureContext + ArchitectureDecision
│
├── templates/
│   ├── system-context.md.j2
│   ├── components.md.j2
│   ├── crosscutting.md.j2
│   ├── adr.md.j2
│   └── architecture-index.md.j2
│
├── cli/
│   └── system_plan.py            # Click command
│
.claude/commands/
└── system-plan.md                # Slash command spec

tests/
├── unit/
│   ├── knowledge/
│   │   └── test_architecture_entities.py
│   └── planning/
│       ├── test_complexity_gating.py
│       ├── test_graphiti_arch.py
│       ├── test_question_adapter.py
│       ├── test_architecture_writer.py
│       └── test_mode_detector.py
├── unit/cli/
│   └── test_system_plan_cli.py
└── integration/
    ├── test_system_plan_seams.py
    └── test_system_plan_e2e.py
```
