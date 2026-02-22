---
id: TASK-FS-002
title: "Create feature spec Python orchestration module"
status: backlog
task_type: feature
parent_review: TASK-REV-F445
feature_id: FEAT-FS01
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T12:00:00Z
priority: high
tags: [feature-spec, commands, file-io, codebase-scanning, orchestration, graphiti]
complexity: 5
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create feature spec Python orchestration module

## Description

Create the Python module that provides stack detection, codebase scanning, file I/O, and Graphiti seeding for the `/feature-spec` command. This is the supporting infrastructure -- the slash command (TASK-FS-001) is the product, this module is the tooling.

v1 uses inline implementations (no separate formatter modules -- those are deferred to v2).

## Files to Create

1. `guardkit/commands/feature_spec.py` (new)
2. `tests/unit/commands/test_feature_spec.py` (new)

## Files NOT to Touch

- All existing command modules (`guardkit/commands/feature_plan_integration.py`, etc.)
- All existing Graphiti modules (`guardkit/knowledge/`)
- No changes to `pyproject.toml` (pyyaml already present)

## Reference Patterns

Study these for conventions:
- `guardkit/commands/feature_plan_integration.py` -- class structure, async pattern, graceful degradation
- `guardkit/knowledge/seed_helpers.py` -- `_add_episodes()` helper for Graphiti seeding
- `guardkit/planning/architecture_writer.py` -- file output pattern (mkdir + write_text)
- `tests/unit/commands/test_feature_plan_integration.py` -- test structure, fixtures, mocking

## Implementation Specification

### Public API

```python
# guardkit/commands/feature_spec.py

@dataclass
class FeatureSpecResult:
    """Result of /feature-spec execution."""
    feature_file: Path
    assumptions_file: Path
    summary_file: Path
    scaffolding_files: dict[str, Path]  # empty in v1
    scenarios_count: int
    assumptions_count: int
    stack: str


def detect_stack(root: Path) -> dict:
    """Detect project technology stack.

    Priority order (first match wins):
    1. pyproject.toml -> Python (pytest-bdd)
    2. requirements.txt or setup.py -> Python (pytest-bdd)
    3. go.mod -> Go (godog)
    4. Cargo.toml -> Rust (cucumber-rs)
    5. package.json (only if no Python signals) -> TypeScript (cucumber-js)
    6. None -> Generic (no scaffolding)

    Returns: {"stack": str, "bdd_runner": str | None, "step_extension": str | None}
    """


def scan_codebase(root: Path, stack: dict) -> dict:
    """Scan codebase for context.

    Returns: {
        "modules": list[str],           # module/package tree
        "existing_features": list[Path], # existing .feature files
        "patterns": list[str],          # detected patterns (models, routes, etc.)
    }
    """


def write_outputs(
    feature_content: str,
    assumptions: list[dict],
    source: str,
    output_dir: Path,
) -> dict[str, Path]:
    """Write all output files.

    Creates {output_dir}/{feature_name}/:
    - {name}.feature
    - {name}_assumptions.yaml (via yaml.dump)
    - {name}_summary.md

    Returns: {"feature": Path, "assumptions": Path, "summary": Path}
    """


async def seed_to_graphiti(
    feature_id: str,
    feature_content: str,
    assumptions: list[dict],
    output_paths: dict,
) -> None:
    """Seed feature spec to Graphiti.

    Seeds:
    - Feature spec overview to 'feature_specs' group
    - Individual scenarios as distinct episodes (NOT the whole file as one blob)
    - Assumptions to 'domain_knowledge' group

    Non-blocking: logs warning and continues if Graphiti unavailable.
    """


class FeatureSpecCommand:
    """Orchestrates /feature-spec execution."""

    def __init__(self, project_root: Path):
        ...

    async def execute(
        self,
        input_text: str,
        options: dict,
    ) -> FeatureSpecResult:
        """Execute the full /feature-spec pipeline."""
        ...
```

### Key Implementation Details

1. **Stack detection** (~15 lines): Simple `if (root / 'pyproject.toml').exists()` chain. Return dict, not a class.

2. **Codebase scanning**: Walk `root` for module structure. Use `glob('**/*.feature')` for existing feature files. Keep lightweight -- this provides context for the AI, not analysis.

3. **File output**: Follow `architecture_writer.py` pattern:
   ```python
   output_path.mkdir(parents=True, exist_ok=True)
   (output_path / f"{name}.feature").write_text(feature_content)
   ```
   For YAML: `yaml.dump(assumptions_data, f, default_flow_style=False, sort_keys=False)`

4. **Graphiti seeding**: Use `_add_episodes()` helper from `guardkit.knowledge.seed_helpers`. Parse feature content into individual scenarios and seed each as a separate episode. Group ID: `"feature_specs"` for scenarios, `"domain_knowledge"` for assumptions.

5. **File input handling**: Read `.md`, `.txt` files via `Path.read_text()`. Concatenate multiple `--from` inputs with newlines.

6. **Graceful degradation**: All Graphiti operations wrapped in try/except with `logger.warning()`. Never crash if Graphiti is unavailable.

### Anti-Stub Requirements

All public functions MUST contain meaningful implementation logic:
- `detect_stack()` must actually check file existence and return appropriate stack info
- `scan_codebase()` must actually walk the directory tree
- `write_outputs()` must actually create directories and write files
- `seed_to_graphiti()` must actually call Graphiti client (or gracefully degrade)
- NO `raise NotImplementedError`, NO `pass`, NO stubs

## Acceptance Criteria

- [ ] File exists: `guardkit/commands/feature_spec.py`
- [ ] `detect_stack(root: Path) -> dict` implements priority-based detection per Section 5.2
- [ ] `detect_stack` returns `{"stack": str, "bdd_runner": str | None, "step_extension": str | None}`
- [ ] Python detected when `pyproject.toml` exists even if `package.json` also exists
- [ ] `scan_codebase(root: Path, stack: dict) -> dict` extracts module tree and existing `.feature` files
- [ ] `write_outputs()` creates correct directory structure and writes all 3 files
- [ ] `seed_to_graphiti()` seeds individual scenarios (not whole file) and is non-blocking
- [ ] `FeatureSpecCommand` class with `execute()` method orchestrating the above
- [ ] `FeatureSpecResult` dataclass with all required fields
- [ ] File input handling: reads `.md`, `.txt` files; concatenates multiple inputs
- [ ] Unit tests pass: `pytest tests/unit/commands/test_feature_spec.py -v`
- [ ] Lint passes: `ruff check guardkit/commands/feature_spec.py`
- [ ] Import check: `python -c "from guardkit.commands.feature_spec import FeatureSpecCommand, FeatureSpecResult, detect_stack, scan_codebase"`

## Coach Validation Commands

```bash
pytest tests/unit/commands/test_feature_spec.py -v
ruff check guardkit/commands/feature_spec.py
python -c "from guardkit.commands.feature_spec import FeatureSpecCommand, FeatureSpecResult, detect_stack, scan_codebase; print('Import OK')"
```

## Player Constraints

- Do not modify any existing command modules, formatter modules, or Graphiti integration code
- Follow `feature_plan_integration.py` patterns for class structure
- Follow `seed_helpers.py` patterns for Graphiti seeding
- Follow `architecture_writer.py` patterns for file output
