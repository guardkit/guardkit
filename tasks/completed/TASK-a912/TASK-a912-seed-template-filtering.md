---
id: TASK-a912
title: Add template filtering to guardkit graphiti seed
status: completed
created: 2026-03-06T15:00:00Z
updated: 2026-03-06T16:20:00Z
completed: 2026-03-06T16:20:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-a912/
priority: high
task_type: implementation
complexity: 3
parent_review: TASK-REV-acbc
feature_id: FEAT-context-reduction
tags: [graphiti, seeding, templates, performance]
wave: 2
implementation_mode: task-work
---

# Add Template Filtering to `guardkit graphiti seed`

## Problem

The `guardkit graphiti seed` command seeds ALL 7 templates' rules (72 episodes), agents (18 episodes), and manifests (7 episodes) regardless of which template the project uses. For a single-template project, 79% of template-specific episodes are wasted, contributing to the 263-minute seed duration.

## Solution

Add a `--template` flag to `guardkit graphiti seed` (matching the existing flag on `seed-system`) that filters template-specific categories to only seed the relevant template plus `default`.

## Implementation

### 1. CLI Flag (graphiti.py)

Add `--template` option to the `seed` command, matching `seed-system`:

```python
@graphiti.command()
@click.option("--force", "-f", is_flag=True, ...)
@click.option("--template", "-t", default=None,
              help="Template to seed (auto-detected if not specified)")
def seed(force: bool, template: Optional[str]):
```

### 2. Orchestrator (seeding.py)

Add `template` parameter to `seed_all_system_context()`:

```python
async def seed_all_system_context(client, force=False, template=None):
    # Resolve template filter
    template_filter = None
    if template:
        template_filter = {template, "default"}

    for name, fn_name in categories:
        seed_fn = getattr(seeding_module, fn_name)
        if name in ("templates", "agents", "rules") and template_filter:
            result = await seed_fn(client, template_filter=template_filter)
        else:
            result = await seed_fn(client)
```

### 3. Template-Specific Seeders

Add `template_filter` parameter to:

**seed_templates.py** — filter `_discover_templates()` results:
```python
async def seed_templates(client, template_filter=None):
    # ... existing discovery ...
    if template_filter:
        discovered = [t for t in discovered if t["template_id"] in template_filter]
```

**seed_agents.py** — filter template iteration:
```python
async def seed_agents(client, template_filter=None):
    for template_entry in sorted(templates_dir.iterdir()):
        template_id = template_entry.name
        if template_filter and template_id not in template_filter:
            continue
```

**seed_rules.py** — filter template iteration:
```python
async def seed_rules(client, template_filter=None):
    for template_entry in sorted(templates_dir.iterdir()):
        template_id = template_entry.name
        if template_filter and template_id not in template_filter:
            continue
```

### 4. Auto-Detection (Optional Enhancement)

Use existing `resolve_template_path()` from `system_seeding.py` for auto-detection when `--template` is not provided:

```python
# In _cmd_seed():
if template is None:
    from guardkit.knowledge.system_seeding import resolve_template_path
    resolved = resolve_template_path()
    if resolved:
        template = resolved.name
```

### Files to Change

1. `guardkit/cli/graphiti.py` — add `--template` option to `seed` command, pass to `_cmd_seed()`
2. `guardkit/knowledge/seeding.py` — add `template` param to `seed_all_system_context()`
3. `guardkit/knowledge/seed_templates.py` — add `template_filter` param to `seed_templates()`
4. `guardkit/knowledge/seed_agents.py` — add `template_filter` param to `seed_agents()`
5. `guardkit/knowledge/seed_rules.py` — add `template_filter` param to `seed_rules()`

### Expected Impact

- Seed duration: ~263 min → ~105-155 min (40-60% reduction)
- Wasted episodes: 77 → 0
- Template-specific timeouts: 38 → ~5 (87% reduction)

## Acceptance Criteria

- [ ] `guardkit graphiti seed --template fastapi-python` only seeds fastapi-python + default
- [ ] `guardkit graphiti seed` without `--template` seeds all templates (backward compatible)
- [ ] Auto-detection from manifest.json works when no `--template` flag provided
- [ ] Episode counts logged show reduced template-specific episodes
- [ ] Existing seeding tests pass
- [ ] New test verifying template_filter parameter works correctly

## Cross-References

- `seed-system` command already has `--template` flag (graphiti.py:767-772)
- `resolve_template_path()` in system_seeding.py:128-163
- No cross-template dependencies (verified in TASK-REV-acbc)
