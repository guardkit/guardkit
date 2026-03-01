---
id: TASK-SAD-005
title: "Create SystemDesignGraphiti service class and DesignWriter"
task_type: feature
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 2
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-SAD-003
---

# Task: Create SystemDesignGraphiti service class and DesignWriter

## Description

Create two new classes that provide the Graphiti and file-writing infrastructure for `/system-design` and `/design-refine`. These follow the patterns established by `SystemPlanGraphiti` and `ArchitectureWriter`.

## Acceptance Criteria

- [ ] Create `guardkit/planning/graphiti_design.py` with `SystemDesignGraphiti` class:
  - GROUP constants: `project_design`, `api_contracts`
  - `upsert_design_decision(decision: DesignDecision)` method
  - `upsert_api_contract(contract: ApiContract)` method
  - `upsert_data_model(model: DataModel)` method
  - `search_design_context(query: str, num_results: int = 5)` method
  - `has_design_context()` method (returns bool — checks if `/system-design` has been run)
  - `get_design_decisions()` method
  - `get_api_contracts()` method
  - Thread-safe (follows `SystemPlanGraphiti` pattern)
- [ ] Create `guardkit/planning/design_writer.py` with `DesignWriter` class:
  - `write_ddr(decision: DesignDecision, output_dir: Path)` — renders `ddr.md.j2`
  - `write_api_contract(contract: ApiContract, output_dir: Path)` — renders `api-contract.md.j2`
  - `write_data_model(model: DataModel, output_dir: Path)` — writes data model markdown
  - `write_component_diagram(container: str, components: list, output_dir: Path)` — renders `component-l3.md.j2`
  - Output directory: `docs/design/` (with subdirectories: `decisions/`, `contracts/`, `models/`, `diagrams/`)
  - Creates directories if they don't exist
- [ ] Add `scan_next_ddr_number(decisions_dir: Path) -> int` helper function
- [ ] Both classes have comprehensive unit tests
- [ ] Integration test: create entities, write via DesignWriter, verify file output

## Implementation Notes

- `SystemDesignGraphiti` follows `guardkit/planning/graphiti_arch.py` exactly
- `DesignWriter` follows `guardkit/planning/architecture_writer.py` pattern
- Group IDs are project-scoped: `{project_id}__project_design`, `{project_id}__api_contracts`
- DDR numbering: scan `docs/design/decisions/DDR-*.md` for max number
- Ensure graceful degradation when Graphiti is unavailable (markdown artefacts still written)
