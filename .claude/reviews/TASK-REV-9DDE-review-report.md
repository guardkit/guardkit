# Review Report: TASK-REV-9DDE

**Title**: Plan: Add a `--json` flag to `/task-status` that emits the dashboard as machine-readable JSON
**Mode**: decision | **Depth**: standard | **Date**: 2026-06-11
**Clarification (Context A)**: focus=all, trade-off=balanced

## Executive Summary

`/task-status` is a **pure markdown-interpreted slash command** — Claude reads task files from `tasks/{state}/` and formats the dashboard ad-hoc. There is no Python producer script. For genuinely *machine-readable* output, an LLM-formatted JSON blob is the wrong substrate: field ordering, value normalization, and schema adherence would vary run-to-run. The recommended approach is a small deterministic producer script (the established R1/R2 pattern: `generate_feature_yaml.py`, `feature_plan_bdd_link.py`) that the spec shells out to when `--json` is passed.

**Recommendation**: Option 1 (deterministic producer script). Effort 3–5 hours, complexity 4/10, risk low.

## Current Situation Assessment

| Aspect | Finding |
|---|---|
| Implementation | Markdown-only; Claude-as-runtime interprets the spec and scans `tasks/` directories |
| Spec locations | Two divergent specs: `.claude/commands/task-status.md` (local "Task Status Dashboard", 349 lines, kanban-focused) and `installer/core/commands/task-status.md` (installer "Epic/Feature Context" variant) |
| Existing JSON mention | Local spec lists `export:json` syntax with **no schema definition and no producer** — exactly the "runner without producer" anti-pattern documented in the knowledge graph (uuid `184731b0`) |
| Reusable infra | `installer/core/commands/lib/task_utils.py` already provides `parse_task_frontmatter()` / `read_task_file()`; `bin-entries.txt` is the manifest for promoting lib scripts to `~/.agentecflow/bin/` |
| Data source | Task markdown files with YAML frontmatter in `tasks/{backlog,in_progress,in_review,blocked,completed}/` |

## Context Used (Knowledge Graph)

- **"Slash commands are the correct interface for Claude Code integration"** + **"Claude Code's Task tool is a runtime-only API in the markdown-driven command flow"** — confirmed `/task-status` has no CLI subcommand; the `--json` flag must be wired through the command spec.
- **Methodological lesson for slash-command verification** ("start with static analysis as the first and cheapest verification step"; "applies to features whose execution is gated on Claude-as-runtime interpretation") — directly motivates moving JSON emission *out* of Claude-as-runtime into a deterministic script.
- **"USES_PRODUCER_SCRIPT: The producer script for /feature-plan is generate_feature_yaml.py"** — the precedent pattern to replicate.

## Option Evaluation Matrix

| Option | Determinism | Effort | Complexity | Testability | Risk |
|---|---|---|---|---|---|
| **1. Deterministic producer script** (recommended) | ✅ Byte-stable | 3–5 h | 4/10 | ✅ pytest unit tests | Low |
| 2. Spec-only (Claude emits JSON per schema in markdown) | ❌ LLM-variable | 1–2 h | 2/10 | ❌ Untestable | Medium — schema drift, hallucinated fields |
| 3. Hybrid (script primary, spec-defined fallback) | ⚠️ Mixed | 4–6 h | 5/10 | Partial | Medium — fallback path re-introduces non-determinism |

### Option 1: Deterministic producer script (Recommended)

Create `installer/core/commands/lib/task_status_json.py`:
- Scans `tasks/{backlog,in_progress,in_review,blocked,completed}/` (recursively, to include feature subfolders)
- Parses frontmatter via existing `task_utils.parse_task_frontmatter`
- Emits stable, sorted JSON to stdout; supports an optional positional `TASK-ID` for single-task output and `--base-path`
- Registered in `bin-entries.txt` → `~/.agentecflow/bin/task-status-json`
- Both `task-status.md` specs gain a `--json` flag section instructing: *Execute `python3 ~/.agentecflow/bin/task-status-json` via Bash and output its stdout verbatim — do not reformat*

**Pros**: deterministic and byte-stable; consumable by scripts/CI *without* a Claude session; testable; consistent with the R1/R2 producer pattern; closes the existing `export:json` runner-without-producer orphan.
**Cons**: requires install step (bin-entries + reinstall); slightly more effort than spec-only.

### Option 2: Spec-only

Define the schema in markdown; Claude formats JSON itself when `--json` passed. Fast, but "machine-readable" output that varies per run defeats the purpose; violates the seeded slash-command-verification lesson. Rejected for the stated goal.

### Option 3: Hybrid

Producer script plus a spec-defined fallback schema when the script is missing. The fallback path is exactly the non-determinism Option 1 eliminates. Rejected (YAGNI).

## Proposed JSON Schema (v1)

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-06-11T12:00:00Z",
  "base_path": ".",
  "summary": {
    "backlog": 5, "in_progress": 2, "in_review": 1,
    "blocked": 1, "completed": 12, "total": 21
  },
  "tasks": [
    {
      "id": "TASK-A3F2",
      "title": "Add search functionality",
      "status": "backlog",
      "priority": "high",
      "task_type": "feature",
      "complexity": 3,
      "tags": ["ui", "api"],
      "created": "2026-06-01T10:00:00Z",
      "updated": "2026-06-02T15:30:00Z",
      "epic": null,
      "feature": null,
      "parent_review": null,
      "feature_id": null,
      "file_path": "tasks/backlog/TASK-A3F2-add-search.md"
    }
  ]
}
```

Schema rules: keys emitted in fixed order; tasks sorted by `(status, id)`; missing frontmatter fields emitted as `null` (never omitted); `schema_version` bumped on breaking change; output is `json.dumps(..., indent=2, sort_keys=False)` for stable diffs.

## Backwards Compatibility

- Default (no flag) output unchanged — human dashboard as today.
- `--json` is additive; `--json` combined with a `TASK-ID` argument yields a single-task object (same task shape, no `summary`).
- The orphaned `export:json` mention in the local spec is replaced by/aliased to `--json` pointing at the producer.

## Recommended Implementation Breakdown

1. **TASK-TSJ-001** — Implement `task_status_json.py` producer (scan, parse, emit schema v1; single-task mode; unit tests). *feature, complexity 4, ~2–3 h*
2. **TASK-TSJ-002** — Register in `bin-entries.txt`; add `--json` flag documentation + execution instruction to both `task-status.md` specs; remove/redirect the orphaned `export:json` mention. *documentation, complexity 2, ~1 h, depends on TSJ-001*

**ESTIMATED EFFORT**: 3–5 hours total | **COMPLEXITY**: 4/10 (Medium) | **RISK**: Low

## Risks & Notes

- **Gate-stack freeze (2026-05-11→2026-05-17)** has passed; no frozen paths touched regardless — this change is outside the orchestrator gate stack.
- Recursive scan must include feature subfolders (`tasks/backlog/{feature-slug}/TASK-*.md`) and the `completed/YYYY-MM/` archive layout.
- Malformed frontmatter should degrade gracefully (emit task with `id` from filename, `"parse_error": true`) rather than crash — a dashboard that dies on one bad file is worse than no dashboard.
