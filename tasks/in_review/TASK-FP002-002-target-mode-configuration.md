---
id: TASK-FP002-002
title: Target Mode Configuration
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 1
implementation_mode: task-work
complexity: 3
complexity_score: 3
type: implementation
domain_tags:
- target-mode
- configuration
- output-formatting
files_to_create:
- guardkit/planning/target_mode.py
- tests/unit/test_target_mode.py
files_to_modify: []
files_not_to_touch:
- .claude/commands/feature-plan.md
- guardkit/cli/
dependencies: []
relevant_decisions:
- D1
- D9
turn_budget:
  expected: 1
  max: 3
graphiti_context_budget: 2000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T17:38:08.347500'
  last_updated: '2026-02-10T17:49:43.645009'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T17:38:08.347500'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-FP002-002: Target Mode Configuration

## Description

Create `guardkit/planning/target_mode.py` that handles the `--target` flag logic. Provides `TargetMode` enum and `TargetConfig` dataclass that drives output verbosity when generating task files for local model execution.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/target_mode.py`
- [ ] File exists: `tests/unit/test_target_mode.py`
- [ ] `TargetMode` enum has values: `INTERACTIVE`, `LOCAL_MODEL`, `AUTO`
- [ ] `TargetConfig` dataclass has fields: mode, model_name, output_verbosity, include_imports, include_type_hints, structured_coach_blocks
- [ ] `resolve_target("local-model")` returns config with `output_verbosity="explicit"`
- [ ] `resolve_target("interactive")` returns config with `output_verbosity="standard"`
- [ ] `resolve_target("auto")` reads `.guardkit/config.yaml` for `autobuild.endpoint` presence
- [ ] `resolve_target(None)` defaults to `AUTO`
- [ ] Tests pass: `pytest tests/unit/test_target_mode.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/target_mode.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_target_mode.py -v
ruff check guardkit/planning/target_mode.py
python -c "from guardkit.planning.target_mode import TargetMode, resolve_target; print('OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Do NOT read or modify `.guardkit/config.yaml` in tests — use mock/fixture
- Use `yaml` (pyyaml) for config file reading — already in project dependencies

## Implementation Notes (Prescriptive)

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

class TargetMode(Enum):
    INTERACTIVE = "interactive"
    LOCAL_MODEL = "local-model"
    AUTO = "auto"

@dataclass
class TargetConfig:
    mode: TargetMode
    model_name: Optional[str] = None
    output_verbosity: str = "standard"  # "standard" or "explicit"
    include_imports: bool = False
    include_type_hints: bool = False
    structured_coach_blocks: bool = False

def resolve_target(
    flag_value: Optional[str] = None,
    config_path: Path = Path(".guardkit/config.yaml")
) -> TargetConfig:
    """Resolve target mode from flag or config file."""
```

- When `mode=LOCAL_MODEL`: set `output_verbosity="explicit"`, `include_imports=True`, `include_type_hints=True`, `structured_coach_blocks=True`
- When `mode=AUTO`: check if `config_path` exists and contains `autobuild.endpoint` — if yes, resolve as `LOCAL_MODEL`; otherwise `INTERACTIVE`
- Config file parsing should handle missing file gracefully (default to INTERACTIVE)
