---
id: TASK-REF-AD6B
title: Relocate README/docs markdown files out of commands/lib/
status: completed
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T18:35:00Z
completed: 2026-04-11T18:35:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-REF-AD6B/
priority: low
tags: [cleanup, refactor, commands-lib, directory-hygiene, docs]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 1
conductor_workspace: commands-lib-cleanup-wave1-4
implementation_mode: task-work
complexity: 3
depends_on: []
---

# Task: Relocate 8 Markdown files out of `commands/lib/`

## Background

Surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 2. Eight
documentation files currently live inside `installer/core/commands/lib/`, a directory whose stated purpose is
"command-support libraries". Mixing code and docs at the same directory level creates the visual noise that let
the E841 shim rot unnoticed — a reader scanning `commands/lib/` cannot easily tell what is supposed to be live
code vs. supporting docs vs. dead historical artifacts.

### Files to move

1. `README.md`
2. `README-CHECKPOINT-DISPLAY.md`
3. `README-PLAN-MODIFIER.md`
4. `QUICK-START-PLAN-MODIFIER.md`
5. `QUICK_REVIEW_API.md`
6. `AGENT_TRACKER_INTEGRATION.md`
7. `MICRO_TASK_README.md`
8. `graphiti-preamble.md`

## Description

Move the 8 files to `docs/internals/commands-lib/` (new directory). Update any cross-references.

### ⚠️ Special case: `graphiti-preamble.md`

This file is explicitly referenced by the `/task-review` command specification:

```
installer/core/commands/task-review.md:
  "See lib/graphiti-preamble.md for the shared availability check pattern."
```

The reference appears in **Phase 1.5 of task-review.md** (multiple occurrences). When you move
`graphiti-preamble.md` to `docs/internals/commands-lib/graphiti-preamble.md`, you MUST update every reference
inside `task-review.md` to point at the new path. Do a repo-wide grep for `graphiti-preamble` before moving and
after moving — the before/after counts should match.

Other slash command `.md` files may also reference `lib/graphiti-preamble.md`. Grep to find them all:

```bash
# Use the Grep tool with pattern:
graphiti-preamble
# glob: **/*.md
```

### Cross-reference audit (other files)

Before moving each file, grep for its exact name in:
- `installer/core/commands/*.md` (slash command specs)
- `installer/core/agents/*.md` (agent definitions)
- `.claude/rules/*.md`
- `docs/guides/*.md`
- Any `*.py` that might reference it via `read_file` or similar

Update every live reference. Historical artifacts (`.claude/reviews/`, `docs/reviews/`, `docs/archive/`,
`docs/implementation-plans/`, `docs/adr/`, `tasks/completed/`, `tasks/archived/`, `.claude/state/backup/`) are
read-only — do NOT edit them, but verify that their references don't constitute a "live" use before moving.

### Target structure

```
docs/
└── internals/
    └── commands-lib/
        ├── README.md
        ├── README-CHECKPOINT-DISPLAY.md
        ├── README-PLAN-MODIFIER.md
        ├── QUICK-START-PLAN-MODIFIER.md
        ├── QUICK_REVIEW_API.md
        ├── AGENT_TRACKER_INTEGRATION.md
        ├── MICRO_TASK_README.md
        └── graphiti-preamble.md
```

## Acceptance Criteria

- [ ] 8 files moved from `installer/core/commands/lib/` to `docs/internals/commands-lib/`.
- [ ] Every live reference to `graphiti-preamble.md` (especially in `task-review.md`) updated to the new path.
- [ ] Pre-move grep count of `graphiti-preamble` matches post-move grep count (zero broken references).
- [ ] Pre-move grep count of each other file name matches post-move grep count.
- [ ] `installer/core/commands/lib/` no longer contains any `*.md` files.

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 2
- Cross-reference risk: `installer/core/commands/task-review.md` uses `lib/graphiti-preamble.md`
