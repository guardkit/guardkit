# Review Report: TASK-REV-G4C1

## Executive Summary

All 6 repos with Graphiti vLLM configs still reference `claude-sonnet-4-6` as `llm_model`, but the vLLM Graphiti instance on port 8000 now serves `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8`. The fix is straightforward: update `llm_model` in each `.guardkit/graphiti.yaml`.

**Recommendation**: Update configs directly to use the actual model name. Do **not** add `--served-model-name` alias.

**Embedding**: Unchanged — `nomic-embed-text-v1.5` on port 8001 is confirmed correct in all configs.

---

## Review Details

- **Mode**: Decision
- **Depth**: Standard
- **Task**: TASK-REV-G4C1
- **Date**: 2026-03-18

---

## Findings

### Finding 1: Confirmed model name mismatch in 5 repos (require-kit is exempt)

`docs/reviews/graphiti-nemotron/models.md` confirms the model served:
```
{"id":"nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8", ...}
```

All 5 repos with explicit `llm_model` still have `claude-sonnet-4-6`:

| Repo | Config | Status |
|------|--------|--------|
| guardkit | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| agentic-dataset-factory | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| deepagents-player-coach-exemplar | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| deepagents-player-coach-exemplar-original | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| vllm-profiling | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| youtube-transcript-mcp | `.guardkit/graphiti.yaml` | **NEEDS UPDATE** |
| require-kit | `.guardkit/graphiti.yaml` | **OK** — no `llm_model` (project_id only) |

### Finding 2: Error confirmed in production

`docs/reviews/additonal-templates/add-context-arch_4.md` shows the exact 404 from agentic-dataset-factory:
```
ERROR: The model `claude-sonnet-4-6` does not exist.
```
Graphiti connects to FalkorDB fine, but episode creation fails 100% of the time.

### Finding 3: `--served-model-name` alias approach is NOT recommended

Adding `--served-model-name claude-sonnet-4-6` to `vllm-graphiti.sh` would allow configs to work without changes, but:
- It creates a fake/misleading model name that obscures which model is actually running
- Breaks introspection (`/v1/models` would lie)
- When the model changes again, the alias breaks silently
- The script already has clear documentation of the actual model name

Using the real model name in configs is cleaner, more maintainable, and honest.

### Finding 4: `guardkit init --copy-graphiti` flow is correct but template needs updating

The `--copy-graphiti` path copies an existing repo's `graphiti.yaml`, replacing only `project_id`. This means new projects will inherit the correct `llm_model` once any source repo is updated.

However, the `guardkit init` flow without `--copy-graphiti` has no default template for vLLM configs — it creates a minimal `graphiti.yaml` with `project_id` only. New projects that don't use `--copy-graphiti` would fall back to defaults (OpenAI provider). This is an existing limitation, not new regression.

**Action**: No change needed to init flow — `--copy-graphiti` is the correct pattern for multi-project setups and is already documented.

### Finding 5: Embedding config confirmed unchanged

All 6 repos (that have explicit embedding config) show:
```yaml
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```
This is correct. No embedding changes needed.

---

## Recommendations

### Recommendation 1 (Critical): Update `llm_model` in all 6 repos

Change `llm_model: claude-sonnet-4-6` → `llm_model: nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` in:

1. `guardkit/.guardkit/graphiti.yaml`
2. `agentic-dataset-factory/.guardkit/graphiti.yaml`
3. `deepagents-player-coach-exemplar/.guardkit/graphiti.yaml`
4. `deepagents-player-coach-exemplar-original/.guardkit/graphiti.yaml`
5. `vllm-profiling/.guardkit/graphiti.yaml`
6. `youtube-transcript-mcp/.guardkit/graphiti.yaml`

### Recommendation 2 (Low): Add a comment to configs noting the port/model

Consider adding a comment like:
```yaml
# Model served by vllm-graphiti.sh (Nemotron 3 Nano 4B FP8, port 8000)
# Update this when switching models via vllm-graphiti.sh preset
llm_model: nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8
```

### Recommendation 3 (Post-fix): Verify agentic-dataset-factory seeding resumes

Per the task context, 4 agentic-dataset-factory architecture files still need seeding (from TASK-REV-5B3A). After the config fix, run:
```bash
cd ~/Projects/appmilla_github/agentic-dataset-factory
guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --timeout 900
```

---

## Decision

**[A]ccept with direct implementation** — this is a config-only change, no code involved.

The implementation is a series of single-line edits across 6 files. All repos are local at `/Users/richardwoollcott/Projects/appmilla_github/`.

---

## Implementation Plan

For each affected repo, change line:
```yaml
llm_model: claude-sonnet-4-6
```
to:
```yaml
llm_model: nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8
```

Files to edit:
1. `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml:46`
2. `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/.guardkit/graphiti.yaml`
3. `/Users/richardwoollcott/Projects/appmilla_github/deepagents-player-coach-exemplar/.guardkit/graphiti.yaml`
4. `/Users/richardwoollcott/Projects/appmilla_github/deepagents-player-coach-exemplar-original/.guardkit/graphiti.yaml`
5. `/Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.guardkit/graphiti.yaml`
6. `/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp/.guardkit/graphiti.yaml`

Verification:
```bash
guardkit graphiti add-context <any-file> --timeout 60
```
Should succeed without 404.
