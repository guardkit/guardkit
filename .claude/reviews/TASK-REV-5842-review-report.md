# Review Report: TASK-REV-5842

## Executive Summary

The GuardKit codebase is well-prepared for multi-project Graphiti namespace isolation. The `normalize_project_id()` function and `{project_id}__{group_name}` prefixing pattern provide robust isolation. The `guardkit init fastapi-python` command will correctly scaffold the new project and write the `project_id` to `.guardkit/graphiti.yaml`. The recommended project ID is **`vllm-profiling`**.

**Overall Assessment**: Ready to proceed with minimal caveats.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Date**: 2026-03-03
- **Task**: Review vLLM profiling project setup and Graphiti naming

---

## Area 1: Project ID / Graphiti Namespace Isolation

### How `normalize_project_id()` Works

Located at [graphiti_client.py:60](guardkit/knowledge/graphiti_client.py#L60):

```python
def normalize_project_id(name: str) -> str:
    # 1. Convert to lowercase
    # 2. Replace spaces and underscores with hyphens
    # 3. Remove non-alphanumeric characters (except hyphens)
    # 4. Collapse multiple consecutive hyphens
    # 5. Truncate to max 50 characters
```

**Validation in `GraphitiConfig.__post_init__`** ([graphiti_client.py:182-199](guardkit/knowledge/graphiti_client.py#L182-L199)):
- Rejects characters like `@#$%^&*()+=[]{}|\\;:'",.< >?/~``
- Rejects strings longer than 50 characters
- Normalizes valid strings; sets to `None` if empty after normalization

### Recommended Project ID: `vllm-profiling`

| Candidate | After `normalize_project_id()` | Notes |
|-----------|-------------------------------|-------|
| `vllm-profiling` | `vllm-profiling` | Clean, descriptive, recommended |
| `vllm-tuning` | `vllm-tuning` | Also valid, narrower scope |
| `vllm_profiling` | `vllm-profiling` | Underscores converted to hyphens |
| `vLLM Profiling` | `vllm-profiling` | Spaces/case normalized |

**Recommendation**: Use `vllm-profiling` - it's already in normalized form, descriptive, and allows the project scope to expand beyond just tuning.

### Namespace Isolation Mechanism

Group IDs are prefixed with `{project_id}__` via `_apply_group_prefix()` ([graphiti_client.py:380-412](guardkit/knowledge/graphiti_client.py#L380-L412)):

- GuardKit project groups: `guardkit__product_knowledge`, `guardkit__architecture_decisions`, etc.
- New project groups: `vllm-profiling__product_knowledge`, `vllm-profiling__architecture_decisions`, etc.
- System groups (`guardkit_templates`, `guardkit_patterns`, etc.) are **not prefixed** and are shared

The `__` double-underscore delimiter is used for prefix detection ([graphiti_client.py:344](guardkit/knowledge/graphiti_client.py#L344)):
```python
def _is_already_prefixed(self, group_id: str) -> bool:
    return "__" in group_id
```

**Finding**: Isolation is robust. The `clear_project_knowledge()` method at line 1437 correctly scopes deletion to groups matching `{project_name}__` prefix.

### Current GuardKit Config

From [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml):
```yaml
project_id: guardkit
```

This confirms the existing project uses explicit `project_id: guardkit`, which means all project-scoped groups are prefixed with `guardkit__`.

---

## Area 2: Template Initialization Process

### What `guardkit init fastapi-python` Creates

The `apply_template()` function at [init.py:316](guardkit/cli/init.py#L316) creates:

**Directory Structure** (always created):
```
.claude/
.claude/commands/
.claude/agents/
.claude/task-plans/
tasks/
tasks/backlog/
tasks/in_progress/
tasks/in_review/
tasks/blocked/
tasks/completed/
.guardkit/
```

**From `fastapi-python` template** (copied if not already present):
- `.claude/agents/` - 6 agent files (fastapi-specialist, database-specialist, testing-specialist + extended variants)
- `.claude/rules/` - 10+ rule files covering API, database, testing, code-style, patterns
- `CLAUDE.md` - FastAPI-specific project instructions
- `.claude/manifest.json` - Template metadata

**NOT copied** (code scaffold): `templates/`, `config/`, `docker/` directories are skipped (line 49: `_SKIP_DIRS`).

### Graphiti Config Writing

The `write_graphiti_config()` function at [init.py:262](guardkit/cli/init.py#L262):
1. Normalizes the project name via `normalize_project_id()`
2. Loads existing `.guardkit/graphiti.yaml` if present
3. Updates/writes the `project_id` field
4. Uses `yaml.dump()` for clean output

**Important**: The init command uses `--project-name` / `-n` to override the project name (defaults to directory name). For a directory named e.g. `vllm-profiling`, the auto-detected name would already be correct.

### Graphiti Seeding

After template application, `_cmd_init()` at [init.py:468](guardkit/cli/init.py#L468):
1. Creates `GraphitiConfig(project_id=project_name)`
2. Initializes client and seeds project knowledge
3. Syncs template content to Graphiti

This means the new project will get its own seeded knowledge under the `vllm-profiling__` namespace.

---

## Area 3: Graphiti Configuration for New Project

### FalkorDB Instance: Share or Separate?

**Recommendation: Share the same FalkorDB instance** (`whitestocks:6379`).

| Factor | Share Instance | Separate Instance |
|--------|---------------|-------------------|
| Isolation | Namespace-based (`vllm-profiling__*`) | Physical |
| Setup effort | Zero (copy connection config) | Significant (new container) |
| Resource usage | Efficient | Duplicated |
| Cross-project queries | Possible if needed | Not possible |
| Risk | Low (prefixing is battle-tested) | None |

The namespace prefixing pattern (`{project_id}__{group_name}`) provides sufficient logical isolation. There is no need for a separate FalkorDB instance.

### Group IDs Configuration

The default group IDs from the current config are appropriate:

```yaml
group_ids:
  - product_knowledge      # vLLM domain concepts, model tuning terminology
  - command_workflows      # GuardKit command patterns
  - architecture_decisions # Design rationale for profiling setup
```

These will be prefixed as `vllm-profiling__product_knowledge`, etc.

**No custom groups needed** for MVP. If the project evolves to need specialized groups (e.g., `profiling_results`, `model_configs`), they can be added later.

### LLM/Embedding Provider Settings

**Configuration Decision Required**:

The current GuardKit config uses:
```yaml
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

For the new vLLM profiling project, these settings should be **copied as-is initially** since the Graphiti extraction pipeline needs a working LLM/embedding stack. If the new project will be experimenting with different models, the profiled models should be separate from the Graphiti extraction model.

---

## Area 4: Multi-Project Coexistence

### `/context-switch` Compatibility

The `/context-switch` command reads from `.guardkit/config.yaml`. Currently this file **does not exist** in the GuardKit project. To use context-switch:

1. Create `.guardkit/config.yaml` in the GuardKit project
2. After creating the new project, add it to `known_projects`

Example config:
```yaml
active_project: guardkit
known_projects:
  - name: guardkit
    path: /Users/richardwoollcott/Projects/appmilla_github/guardkit
    last_accessed: 2026-03-03T00:00:00Z
  - name: vllm-profiling
    path: /Users/richardwoollcott/Projects/vllm-profiling
    last_accessed: 2026-03-03T00:00:00Z
```

### Knowledge Isolation Verification

The isolation is enforced at three levels:

1. **Write path**: `_apply_group_prefix()` ensures all project groups get the correct prefix
2. **Read path**: `search()` applies the same prefix to `group_ids` before querying
3. **Clear path**: `clear_project_knowledge()` only clears groups with matching `{project_name}__` prefix

**No cross-project leakage is possible** as long as each project has a distinct `project_id` in `.guardkit/graphiti.yaml`.

### `guardkit graphiti status`

The `get_status()` method at line 1494 can report per-project groups when called with `project_only=True`. It auto-detects the project name from `get_current_project_name()` (cwd-based).

---

## Recommendations

### Step-by-Step Setup Instructions

```bash
# 1. Create project directory
mkdir -p ~/Projects/vllm-profiling
cd ~/Projects/vllm-profiling

# 2. Initialize with fastapi-python template
guardkit init fastapi-python -n vllm-profiling

# 3. Verify .guardkit/graphiti.yaml was created correctly
cat .guardkit/graphiti.yaml
# Should show: project_id: vllm-profiling

# 4. Update Graphiti connection settings
# Edit .guardkit/graphiti.yaml to add FalkorDB connection:
#   enabled: true
#   graph_store: falkordb
#   falkordb_host: whitestocks
#   falkordb_port: 6379
#   llm_provider: vllm
#   llm_base_url: http://promaxgb10-41b1:8000/v1
#   llm_model: claude-sonnet-4-6
#   embedding_provider: vllm
#   embedding_base_url: http://promaxgb10-41b1:8001/v1
#   embedding_model: nomic-embed-text-v1.5

# 5. Verify Graphiti connectivity
guardkit graphiti status

# 6. (Optional) Set up context-switch
# Add .guardkit/config.yaml in both projects
```

### Gotchas and Prerequisites

1. **PyYAML required**: `write_graphiti_config()` needs PyYAML installed (`pip install pyyaml`). It should be present if GuardKit is installed with `pip install guardkit-py`.

2. **FalkorDB must be running**: The seeding step will gracefully degrade if FalkorDB is unavailable, but knowledge won't be captured.

3. **LLM/Embedding endpoints must be reachable**: The `promaxgb10-41b1` machine must be accessible from the new project's execution environment.

4. **Auto-detect fallback**: If `project_id` is not set in `.guardkit/graphiti.yaml`, the client falls back to `get_current_project_name()` (directory name). This is fragile if the directory is renamed. Always set `project_id` explicitly.

5. **`guardkit init` writes `project_id` only**: The init command writes only the `project_id` field. You must manually add FalkorDB connection details, LLM provider settings, and group_ids. Consider copying the existing `.guardkit/graphiti.yaml` as a starting point and changing only `project_id`.

6. **No `.guardkit/config.yaml`**: The current GuardKit project lacks this file, so `/context-switch` won't work until it's created in both projects.

---

## Decision Matrix

| Decision | Recommendation | Confidence | Notes |
|----------|---------------|------------|-------|
| Project ID | `vllm-profiling` | High | Already normalized, descriptive |
| FalkorDB instance | Shared (`whitestocks:6379`) | High | Namespace isolation sufficient |
| LLM/Embedding config | Copy from GuardKit | High | Same infrastructure |
| Custom groups | None initially | Medium | Add as needed |
| Template | `fastapi-python` | High | Matches vLLM profiling use case |
| Context-switch setup | Create config in both projects | Medium | Nice-to-have, not blocking |

---

## Appendix: Key File References

| File | Purpose | Key Lines |
|------|---------|-----------|
| [graphiti_client.py](guardkit/knowledge/graphiti_client.py) | Namespace isolation logic | L60-89 (normalize), L346-412 (prefixing) |
| [init.py](guardkit/cli/init.py) | `guardkit init` implementation | L262-313 (config write), L468-586 (init flow) |
| [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml) | Current project config | L22 (project_id: guardkit) |
| [context-switch.md](installer/core/commands/context-switch.md) | Multi-project navigation | L206-225 (config format) |
| [fastapi-python/manifest.json](installer/core/templates/fastapi-python/manifest.json) | Template metadata | Full file |
