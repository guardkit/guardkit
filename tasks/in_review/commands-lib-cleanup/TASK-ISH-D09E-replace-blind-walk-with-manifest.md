---
id: TASK-ISH-D09E
title: Replace install.sh blind directory walk with explicit CLI manifest
status: in_review
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T19:15:00Z
previous_state: in_progress
state_transition_reason: "task-work complete, all acceptance criteria met"
priority: medium
tags: [cleanup, install-script, refactor, root-cause]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 3
conductor_workspace: commands-lib-cleanup-wave3-1
implementation_mode: task-work
complexity: 5
depends_on:
  - TASK-FIX-CF8D
---

# Task: Replace `install.sh` blind directory walk with explicit CLI manifest

## Background

This is the **root-cause fix** surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md)
Section 2 and reiterated in Section 5. The `install.sh` function `setup_python_bin_symlinks()` (currently lines
1826–1910) performs a blind `find ... -maxdepth 1 -name "*.py"` walk over `installer/core/commands/` and
`installer/core/commands/lib/`, and creates a `~/.agentecflow/bin/` symlink for every file it finds (skipping only
`__init__.py` and `test_*.py`).

This means **every `.py` file in `commands/lib/` is promoted to a globally-installed CLI command**, regardless of
whether it is:

- Actually intended to be a user-facing CLI tool (e.g., `graphiti_check.py` — yes)
- A dead handler for an abandoned command design (e.g., `upfront_complexity_cli.py` — no, dead per TASK-FIX-7A3E)
- An exploratory debug script with hardcoded infrastructure (e.g., `graphiti_diagnose_v2.py` — no, dead per TASK-FIX-8B4F)
- A manual developer demo (e.g., `demo_template_qa.py` — no, should be under `examples/` per TASK-REF-9C5A)
- An internal orchestrator library that is imported, not invoked (e.g., `agent_discovery.py`, `task_breakdown.py`,
  `clarification/...` — no, these are libraries, shells shouldn't run them directly)

The blind-walk is the structural reason [TASK-FIX-E841](../../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md)'s
dead shim went unnoticed for so long: once a file is in `commands/lib/`, it gets a shell command regardless of
purpose, and nobody audits the resulting `bin/` directory for things that shouldn't be there.

## Description

Replace the blind walk with an **explicit manifest** of files that are intended to become user-facing shell
commands. Everything else stays internal.

### Manifest format (choose one)

**Option 1 — Dedicated manifest file** (recommended for shell-script compatibility):

```
# installer/core/commands/bin-entries.txt
# One path per line, relative to repo root. Lines starting with # are comments.
# Each listed file will become a shell command in ~/.agentecflow/bin/
# with name = basename (without .py) with underscores replaced by hyphens.

installer/core/commands/agent-enhance.py
installer/core/commands/agent-format.py
installer/core/commands/agent-validate.py
# graphiti_check.py intentionally omitted — has a dedicated wrapper
installer/core/commands/lib/graphiti_diagnose.py
# (add further entries here as live CLI tools are introduced)
```

**Option 2 — Section in `pyproject.toml`**:

```toml
[tool.guardkit.bin-entries]
commands = [
    "installer/core/commands/agent-enhance.py",
    ...
]
```

Default to **Option 1** — it's trivial for `install.sh` to parse with `while read line`, no TOML parser needed in
bash. If the project later gains a Python-only installer, migrating to Option 2 is straightforward.

### New `install.sh` behavior

1. **Prune pass** — already added by TASK-FIX-CF8D. Keep it.
2. **Read manifest** — load `installer/core/commands/bin-entries.txt`, strip comments, resolve each path to
   an absolute file, verify the file exists (warn and skip if not — do not fail the whole install).
3. **Create symlinks only for manifest entries** — replace the `find ... -name "*.py"` walk with iteration over
   the manifest list.
4. **Unlisted-file drift warning** — after creating symlinks, scan `commands/` and `commands/lib/` for any
   `*.py` files not in the manifest and not beginning with `test_`/`demo_`/`__init__`. Print a **warning**
   (not an error) listing them, with the message: "File not in bin-entries.txt — will not be exposed as a CLI.
   Add to manifest if intentional, or delete/relocate if not."
5. **Manifest entry validation** — for each manifest entry, verify the target has a `main()` function or an
   `if __name__ == "__main__":` block. If not, warn that the entry is listed as a CLI but has no entry point.

### Initial manifest population

When writing the new `bin-entries.txt`, list **only files known to be live CLI entry points**:

- `installer/core/commands/agent-enhance.py`
- `installer/core/commands/agent-format.py`
- `installer/core/commands/agent-validate.py`
- (any other `.py` directly in `installer/core/commands/` that currently has a wrapper or symlink and is
  confirmed in use — audit at implementation time; the review did not scope top-level `commands/`)
- `installer/core/commands/lib/graphiti_diagnose.py` (portable diagnostic, kept by TASK-FIX-8B4F)

**Do NOT include** the ~60 command-library files (`agent_discovery.py`, `task_breakdown.py`, etc.) that are
imported by Python orchestrators but never meant to be run as shell commands. The review verified these are all
importers — not CLI entry points — and the symlinks currently created for them serve no purpose.

### Migration risk

The biggest risk is removing a symlink that some user has baked into their muscle memory or shell history. The
review did not catalog which of the ~60 auto-created symlinks are actually used by anyone. Mitigation:

- Do a `/task-review`-style evidence pass for each symlink about to be removed: grep the repo for its invocation,
  check shell history patterns if available, and ask the user before finalizing the initial manifest.
- Phase the rollout: print a deprecation warning for 1-2 releases before removing unlisted symlinks.
- Document the change in `CHANGELOG.md` with the exact list of removed symlinks and their replacements (if any).

This task is **Wave 3** because it builds on TASK-FIX-CF8D's prune pass (Wave 2) and must be sequential with it —
both touch `install.sh`. Do not start until TASK-FIX-CF8D is merged.

## Acceptance Criteria

- [x] `installer/core/commands/bin-entries.txt` (or equivalent) exists with an initial list of confirmed live
      CLI entries.
- [x] `install.sh` reads the manifest instead of blindly walking `commands/lib/`.
- [x] `install.sh` preserves TASK-FIX-CF8D's prune pass.
- [x] `install.sh` emits an **informational warning** (not error) for any unlisted `.py` file in `commands/` or
      `commands/lib/`.
- [x] Re-running the installer after the refactor removes all symlinks corresponding to files NOT in the manifest,
      while leaving manifest-listed symlinks intact.
- [x] Before-state audit recorded in the task progress notes: the exact list of symlinks that existed under
      `~/.agentecflow/bin/` before the refactor (for rollback / user notification).
- [x] `CHANGELOG.md` entry describing the change and listing any symlinks that will be removed for users of
      prior versions.
- [x] Re-running the installer is idempotent.

## Implementation Notes

### Files changed

- **Added** `installer/core/commands/bin-entries.txt` — manifest file with 4 live
  CLI entries: `agent-enhance.py`, `agent-format.py`, `agent-validate.py`,
  `lib/graphiti_diagnose.py`. Includes documentation for the format and how to
  add/deprecate entries.
- **Modified** `installer/scripts/install.sh` — `setup_python_bin_symlinks()` now:
  1. Reads `bin-entries.txt` (the manifest is REQUIRED — install fails loudly
     if it is missing rather than silently falling back to a walk).
  2. Strips comments / blank lines, resolves each entry to an absolute path
     under repo root, and verifies the file exists (warns and skips if not).
  3. For each manifest entry: validates the target has `def main(` or
     `if __name__ == "__main__":` and warns if not.
  4. Refuses to overwrite a regular file (e.g. a `create_cli_commands` wrapper
     such as `graphiti-check`) — printed as an error with remediation hint.
  5. After creating manifest symlinks, scans `commands/` and `commands/lib/`
     for unlisted `.py` files (excluding `__init__.py`, `test_*`, `demo_*`,
     and `graphiti_check.py` which has a wrapper) and prints an informational
     warning listing each one.
  6. The TASK-FIX-CF8D prune pass (`prune_stale_bin_symlinks`) runs first and
     is unchanged — it removes symlinks whose targets no longer exist or are
     no longer in the manifest after a reinstall.
- **Modified** `CHANGELOG.md` — added a Breaking Changes entry under
  `[Unreleased]` documenting the manifest, the 4 retained CLIs, and the full
  list of 62 symlinks that will be removed on next reinstall.

### Validation

Tested with an isolated bash harness that sources `prune_stale_bin_symlinks`
and the new `setup_python_bin_symlinks` against a temp `INSTALL_DIR` and the
real repo:

- **Cold install**: 4 manifest entries → 4 created (`agent-enhance`,
  `agent-format`, `agent-validate`, `graphiti-diagnose`).
- **Idempotency**: re-running with the same manifest → 0 created, 0 updated,
  4 unchanged.
- **Stale link pruning**: injected a fake symlink whose target doesn't exist
  → prune pass removed it, manifest pass left the 4 valid links intact.
- **Drift warning**: 62 unlisted `.py` files under `commands/lib/` listed
  one-per-line as informational warnings (not errors), exactly as required.
- **Syntax**: `bash -n install.sh` clean.
- The 4 manifest targets all have either `def main(` or `if __name__ ==
  "__main__":`, so the entry-point validation pass emits no warnings.

### Before-state audit (the 71 entries in `~/.agentecflow/bin/` before refactor)

Captured at task start. Of these 71, the new behavior keeps:

- **5 wrapper scripts** (created by `create_cli_commands`, regular files —
  unaffected by this change): `gk`, `gki`, `guardkit`, `guardkit-init`,
  `graphiti-check`.
- **4 manifest-driven symlinks**: `agent-enhance`, `agent-format`,
  `agent-validate`, `graphiti-diagnose`.

The remaining **62 symlinks pointing into `installer/core/commands/lib/`**
will be removed on next reinstall by the new manifest-driven sweep added
to `setup_python_bin_symlinks`. The sweep complements TASK-FIX-CF8D's
`prune_stale_bin_symlinks` (which only removes links whose targets are
missing on disk): it walks `BIN_DIR`, identifies symlinks whose targets
point under `installer/core/commands/`, and removes any that are NOT in
the manifest. Symlinks pointing elsewhere (user-added tools) are NOT
touched — verified in the test harness with a synthetic
`my-personal-tool -> /etc/hosts` link that survived the sweep intact.

The full pre-refactor list (snapshotted to `/tmp/before-state-bin.txt` at
task start):

```
agent-discovery, agent-enhance, agent-format, agent-invocation-tracker,
agent-invocation-validator, agent-utils, agent-validate, api-call-preview,
breakdown-strategies, change-tracker, checkpoint-display,
complexity-calculator, complexity-factors, complexity-models, constants,
distribution-helpers, duplicate-detector, error-messages,
feature-detection, flag-validator, generate-feature-yaml, git-state-helper,
gk, gki, graphiti-check, graphiti-context-loader, graphiti-diagnose,
greenfield-qa-session, guardkit, guardkit-init, library-context,
library-detector, micro-task-detector, micro-task-workflow,
modification-applier, modification-persistence, modification-session,
pager-display, phase-execution, phase-gate-validator, plan-audit,
plan-markdown-parser, plan-markdown-renderer, plan-modifier,
plan-persistence, qa-manager, refinement-handler, review-mode-executor,
review-modes, review-report-generator, review-router, spec-drift-detector,
split-models, task-breakdown, task-completion-helper,
task-review-orchestrator, task-split-advisor, task-utils,
template-create-orchestrator, template-merger, template-packager,
template-qa-display, template-qa-persistence, template-qa-questions,
template-qa-session, template-qa-validator, template-versioning,
user-interaction, version-manager, visualization, worktree-cleanup
```

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 2 "Root cause of silent rot" and Section 5 recommendation #3
- Install script section: `installer/scripts/install.sh` lines 1797–1910
- Hard dependency: **TASK-FIX-CF8D** must be merged first (Wave 2 → Wave 3 sequential)
- Related: once this ships, the maintenance burden of the entire `commands/lib/` directory drops — adding a new
  file no longer silently promotes it to a global command.
