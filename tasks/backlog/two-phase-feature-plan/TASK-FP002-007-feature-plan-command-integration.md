---
id: TASK-FP002-007
title: Feature-Plan Command Integration
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 3
implementation_mode: task-work
complexity: 7
complexity_score: 7
type: integration
domain_tags:
  - feature-plan
  - command-integration
  - orchestration
files_to_create: []
files_to_modify:
  - .claude/commands/feature-plan.md
files_not_to_touch:
  - guardkit/orchestrator/
  - guardkit/knowledge/
  - guardkit/cli/autobuild.py
dependencies:
  - TASK-FP002-001
  - TASK-FP002-002
  - TASK-FP002-003
  - TASK-FP002-004
  - TASK-FP002-005
  - TASK-FP002-006
relevant_decisions:
  - D1
  - D2
  - D6
  - D9
turn_budget:
  expected: 3
  max: 5
graphiti_context_budget: 6000
---

# TASK-FP002-007: Feature-Plan Command Integration

## Description

Update `.claude/commands/feature-plan.md` to support the new flags (`--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`) and integrate with all planning modules from Tasks 1-6. The command file instructs Claude Code how to use the modules — it does not implement them directly.

## Acceptance Criteria (Machine-Verifiable)

- [ ] `.claude/commands/feature-plan.md` updated with new flag descriptions
- [ ] When `--from-spec` is provided, command instructs Claude to use `SpecParser` to extract data
- [ ] When `--target local-model` is set, task output includes YAML frontmatter and structured Coach blocks
- [ ] When `--generate-adrs` is set, command produces ADR files from Decision Log
- [ ] When `--generate-quality-gates` is set, command produces quality gate YAML
- [ ] Existing behaviour (no new flags) is unchanged — backward compatible
- [ ] Command references correct module imports: `guardkit.planning.spec_parser`, `guardkit.planning.target_mode`, etc.
- [ ] Lint passes: `ruff check guardkit/planning/`

## Coach Validation Commands

```bash
python -c "
from pathlib import Path
content = Path('.claude/commands/feature-plan.md').read_text()
assert '--from-spec' in content
assert '--target' in content
assert '--generate-adrs' in content
assert '--generate-quality-gates' in content
assert 'SpecParser' in content or 'spec_parser' in content
print('Command file validation OK')
"
ruff check guardkit/planning/
```

## Player Constraints

- Modify ONLY `.claude/commands/feature-plan.md`
- Do NOT modify any Python code in orchestrator or CLI layers
- The command file instructs Claude Code how to use the modules — it does not implement them
- Preserve ALL existing content in feature-plan.md; add new sections, don't replace
- New flag sections should be additive — placed after existing content

## Implementation Notes (Prescriptive)

Add the following sections to the command file:

### New Flags Section
Add to the existing flags table:
```
| `--from-spec path/to/spec.md` | Parse Research-to-Implementation Template |
| `--target interactive\|local-model\|auto` | Set output verbosity for target executor |
| `--generate-adrs` | Generate ADR files from Decision Log |
| `--generate-quality-gates` | Generate per-feature quality gate YAML |
```

### New Execution Flow Section
When `--from-spec` is provided:
1. Read the spec file at the given path
2. Call `parse_research_template(Path(spec_path))` to get `ParsedSpec`
3. If `--target` is specified, call `resolve_target(target_value)` to get `TargetConfig`
4. For each task in `parsed_spec.tasks`, call `enrich_task(task, target_config, feature_id)`
5. Call `render_task_markdown(enriched_task)` for each task and write to task files
6. If `--generate-adrs`, call `generate_adrs(parsed_spec.decisions, feature_id)`
7. If `--generate-quality-gates`, call `generate_quality_gates(feature_id, parsed_spec.tasks)`
8. Call `extract_warnings(parsed_spec.warnings, feature_id)` if warnings exist
9. Call `generate_seed_script(feature_id, adr_paths, spec_path, warnings_path)`

### Backward Compatibility Note
All new flags are optional. Without `--from-spec`, the command behaves exactly as before — free-form text description triggers the existing review + implement flow.
