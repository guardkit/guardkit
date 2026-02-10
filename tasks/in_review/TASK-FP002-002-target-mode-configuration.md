---
complexity: 3
complexity_score: 3
dependencies: []
domain_tags:
- target-mode
- configuration
- output-formatting
feature_id: FEAT-FP-002
files_not_to_touch:
- .claude/commands/feature-plan.md
- guardkit/cli/
files_to_create:
- guardkit/planning/target_mode.py
- tests/unit/test_target_mode.py
files_to_modify: []
graphiti_context_budget: 2000
id: TASK-FP002-002
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D1
- D9
status: in_review
task_type: feature
title: Target Mode Configuration
turn_budget:
  expected: 1
  max: 3
type: implementation
wave: 1
---

# TASK-FP002-002: Target Mode Configuration

## Description

Create `guardkit/planning/target_mode.py` that handles the `--target` flag logic. Provides `TargetMode` enum and `TargetConfig` dataclass that drives output verbosity when generating task files for local model execution.

## Acceptance Criteria (Machine-Verifiable)

- [x] File exists: `guardkit/planning/target_mode.py`
- [x] File exists: `tests/unit/test_target_mode.py`
- [x] `TargetMode` enum has values: `INTERACTIVE`, `LOCAL_MODEL`, `AUTO`
- [x] `TargetConfig` dataclass has fields: mode, model_name, output_verbosity, include_imports, include_type_hints, structured_coach_blocks
- [x] `resolve_target("local-model")` returns config with `output_verbosity="explicit"`
- [x] `resolve_target("interactive")` returns config with `output_verbosity="standard"`
- [x] `resolve_target("auto")` reads `.guardkit/config.yaml` for `autobuild.endpoint` presence
- [x] `resolve_target(None)` defaults to `AUTO`
- [x] Tests pass: `pytest tests/unit/test_target_mode.py -v`
- [x] Lint passes: `ruff check guardkit/planning/target_mode.py`

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