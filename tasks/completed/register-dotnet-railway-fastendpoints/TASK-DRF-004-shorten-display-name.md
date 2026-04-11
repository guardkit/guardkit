---
id: TASK-DRF-004
title: Shorten dotnet-railway-fastendpoints display_name in registered manifest
status: completed
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T13:20:00Z
completed: 2026-04-11T13:20:00Z
previous_state: in_review
priority: low
tags: [template, dotnet, manifest, polish, cosmetic]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
wave: 3
complexity: 1
depends_on: [TASK-DRF-002]
---

# Task: Shorten dotnet-railway-fastendpoints display_name in registered manifest

## Description

Cosmetic polish follow-up from the TASK-REV-D0C1 review. The current `display_name` in `manifest.json` is verbose:

```
"display_name": "C# Modular Monolith With Bounded Context Isolation"
```

Compare with existing builtins which use terse names:

| Template | display_name |
|----------|--------------|
| python-library | `"Python Library"` |
| fastapi-python | (short) |
| langchain-deepagents | (short) |
| **dotnet-railway-fastendpoints** | `"C# Modular Monolith With Bounded Context Isolation"` ⚠️ |

A shorter, more consistent display name improves readability in `guardkit init --help` and any future template-picker UI.

## Scope

**Edit only the registered copy** at `installer/core/templates/dotnet-railway-fastendpoints/manifest.json`. The source at `~/.agentecflow/templates/...` is local-only and can be left as-is.

**Why this runs post-copy (depends on TASK-DRF-002)**: avoids merge conflict with TASK-DRF-001 which also edits the source manifest.json. By editing the copied version only, this task stays orthogonal to the DRF-001/002 pipeline.

## Acceptance Criteria

- [ ] **Decide on a new display_name** — candidates (pick one or propose better):
  - `"C# Railway-Oriented Monolith"` ← recommended in review
  - `"C# Modular Monolith (Railway)"`
  - `"C# ASP.NET Core Railway Monolith"`
  - `"C# FastEndpoints Monolith"`
- [ ] **Edit `installer/core/templates/dotnet-railway-fastendpoints/manifest.json`** — update the `display_name` field to the chosen value. Preserve JSON validity.
- [ ] **Update the README.md** at `installer/core/templates/dotnet-railway-fastendpoints/README.md` if the old display_name appears in its text.
- [ ] **Preserve** the full `description` field — it can remain descriptive; only `display_name` is shortened.

## Verification

- [ ] `python -c "import json; print(json.load(open('installer/core/templates/dotnet-railway-fastendpoints/manifest.json'))['display_name'])"` prints the new name.
- [ ] `grep -n 'Bounded Context Isolation' installer/core/templates/dotnet-railway-fastendpoints/manifest.json` returns zero matches (or only appears in the `description`, not `display_name`).

## Notes

- **Recommended name**: `"C# Railway-Oriented Monolith"` — short, distinctive, captures both the functional style (Railway-Oriented Programming) and the architecture (Modular Monolith).
- **Not a blocker** for registration — this is cosmetic. The current verbose name is technically correct; this task is purely about consistency with other builtins.

## Completion Notes (2026-04-11)

- **Chosen name**: `"C# Railway-Oriented Monolith"` (the review's recommended candidate).
- **Edited**: `installer/core/templates/dotnet-railway-fastendpoints/manifest.json` — `display_name` only. JSON validity verified via `python3 -c "import json; ..."` → prints new value.
- **README check**: `grep "Modular Monolith With Bounded Context"` against the template README returned no matches. The lowercase descriptive variant ("Modular Monolith with Bounded Context isolation") still appears in `description`/CLAUDE.md, which is intentional per scope (preserve `description`).
- **`description` field unchanged** — still reads "C# template using Modular Monolith with Bounded Context isolation architecture with ASP.NET Core 10.0, FastEndpoints".
- Direct execution (complexity 1, parent_review provenance → MINIMAL intensity, no agent invocations).
