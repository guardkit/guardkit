---
id: TASK-SC-002
title: "Implement context_switch.py and register bdd_scenarios group"
status: backlog
created: 2026-02-10T11:20:00Z
updated: 2026-02-10T11:20:00Z
priority: high
task_type: feature
parent_review: TASK-REV-AEA7
feature_id: FEAT-SC-001
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
tags: [context-switch, config, graphiti]
---

# Task: Implement context_switch.py and register bdd_scenarios group

## Description

Two related foundational changes:

1. **Create `guardkit/planning/context_switch.py`** — project switching logic with config management
2. **Register `bdd_scenarios` in `GraphitiClient.PROJECT_GROUP_NAMES`** — new project group for /impact-analysis deep mode

## Key Implementation Details

### Part 1: context_switch.py

#### GuardKitConfig class

```python
class GuardKitConfig:
    """Manages .guardkit/config.yaml for project context."""

    def __init__(self, config_path: Path = None):
        # Default: .guardkit/config.yaml in cwd
        self._path = config_path or Path(".guardkit/config.yaml")
        self._data = self._load()

    @property
    def active_project(self) -> Optional[dict]:
        """Get current active project."""

    def get_known_project(self, project_id: str) -> Optional[dict]:
        """Look up a project by ID."""

    def set_active_project(self, project_id: str) -> None:
        """Switch active project, update last_accessed timestamp."""

    def list_known_projects(self) -> List[dict]:
        """Return all known projects."""

    def _load(self) -> dict:
        """Load config from YAML file. Returns empty dict if missing."""

    def _save(self) -> None:
        """Write config back to YAML file."""
```

#### execute_context_switch function

```python
async def execute_context_switch(
    client: Optional[GraphitiClient],
    target_project: str,
    config: GuardKitConfig,
) -> dict:
    """Switch active project context and display orientation."""
```

- Validates target exists in `known_projects`
- Updates config with new active project
- Queries Graphiti for architecture overview (graceful if unavailable)
- Finds active tasks from task state files
- Returns structured dict for display

#### _find_active_tasks function

```python
def _find_active_tasks(project_path: Optional[str]) -> List[dict]:
    """Find in-progress and pending tasks from task directories."""
```

- Reads `tasks/in_progress/` and `tasks/backlog/` directories
- Extracts task ID, title, status from frontmatter
- Returns sorted list (in_progress first, then backlog)
- Returns empty list if path doesn't exist

#### format_context_switch_display function

- Orientation display for switch
- List mode for `--list`
- Current project mode for no-args

### Part 2: Register bdd_scenarios group

In `guardkit/knowledge/graphiti_client.py`, add `"bdd_scenarios"` to `GraphitiClient.PROJECT_GROUP_NAMES`:

```python
PROJECT_GROUP_NAMES = [
    "project_overview",
    "project_architecture",
    "feature_specs",
    "project_decisions",
    "project_constraints",
    "domain_knowledge",
    "bdd_scenarios",        # NEW: Added by FEAT-SC-001
]
```

This ensures `get_group_id("bdd_scenarios")` auto-detects as project scope (no explicit `scope="project"` needed).

## Acceptance Criteria

- [ ] `GuardKitConfig` loads and saves `.guardkit/config.yaml`
- [ ] `set_active_project()` updates project and `last_accessed` timestamp
- [ ] `get_known_project()` returns project dict or None for unknown
- [ ] `list_known_projects()` returns all known projects
- [ ] `execute_context_switch()` returns correct status for valid/invalid projects
- [ ] `execute_context_switch()` works when Graphiti is unavailable
- [ ] `_find_active_tasks()` reads task directories and extracts metadata
- [ ] `bdd_scenarios` registered in `PROJECT_GROUP_NAMES`
- [ ] `get_group_id("bdd_scenarios")` returns project-prefixed ID
- [ ] All functions have unit tests with >=80% line coverage

## Test Requirements

### Unit Tests (tests/unit/planning/test_context_switch.py)

- `test_load_config_from_yaml` — valid config file
- `test_load_config_missing_file` — graceful handling
- `test_switch_to_known_project` — updates active project
- `test_switch_to_unknown_project` — returns error status
- `test_switch_updates_last_accessed` — timestamp updated
- `test_list_known_projects` — returns all projects
- `test_current_project_display` — no-args shows current
- `test_find_active_tasks` — reads task directories
- `test_find_active_tasks_no_path` — returns empty list
- `test_execute_context_switch_graphiti_unavailable` — graceful degradation

### Unit Tests for bdd_scenarios group (tests/unit/knowledge/test_graphiti_client_bdd_group.py)

- `test_bdd_scenarios_in_project_groups` — group is registered
- `test_bdd_scenarios_auto_detects_project_scope` — is_project_group returns True
- `test_get_group_id_bdd_scenarios` — returns prefixed ID

## Implementation Notes

- Config management uses PyYAML (`yaml.safe_load`/`yaml.safe_dump`)
- Config path default should work from project root
- `_find_active_tasks()` is sync (file I/O, not Graphiti)
- `execute_context_switch()` is async (calls Graphiti)
