# Implementation Guide: commands-lib-cleanup

**Feature ID**: FEAT-E1AF
**Parent Review**: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md)
**Review Report**: [.claude/reviews/TASK-REV-C1B4-review-report.md](../../../.claude/reviews/TASK-REV-C1B4-review-report.md)
**Created**: 2026-04-11

---

## Purpose

Execute the 7 follow-up recommendations from TASK-REV-C1B4's audit of `installer/core/commands/lib/`. The review
identified one structurally-healthy-but-functionally-dead CLI shim (same failure mode as E841), one dangling
`~/.agentecflow/bin/` symlink left behind by E841, directory-hygiene issues (15 orphaned test files, 4 demo
scripts, 8 markdown files mixed in with production code, 3 versioned Graphiti debug scripts), and — most
importantly — the **root cause**: `install.sh` blindly symlinks every `.py` file in `commands/lib/` into
`~/.agentecflow/bin/`, promoting dead files and demo scripts to global shell commands.

This feature folder bundles all 7 fixes into a coordinated cleanup. Wave 1 is parallel-friendly tidy-up. Wave 2
and Wave 3 are the two install.sh changes and **must be sequential** because they touch the same file.

## Wave Structure

### Wave 1 — Parallel-friendly cleanup (5 tasks)

All five tasks touch **different** files in `installer/core/commands/lib/` and can be done in parallel workspaces.
Merge order within the wave does not matter. None of these tasks touch `install.sh`, so they will produce
dangling `~/.agentecflow/bin/` symlinks after merge — that is **expected**, Wave 2 cleans them up.

| Task | Priority | Complexity | What | Files touched |
|---|---|---|---|---|
| [TASK-FIX-7A3E](TASK-FIX-7A3E-delete-dead-upfront-complexity-cli.md) | medium | 2 | Delete dead `upfront_complexity_cli.py` + adapter + its unit test | `installer/core/commands/lib/upfront_complexity_cli.py`, `installer/core/commands/lib/upfront_complexity_adapter.py`, `tests/unit/test_upfront_adapter.py` |
| [TASK-FIX-8B4F](TASK-FIX-8B4F-delete-graphiti-diagnose-v2-v3.md) | low | 1 | Delete hardcoded-host `graphiti_diagnose_v2.py` and `_v3.py` | `installer/core/commands/lib/graphiti_diagnose_v2.py`, `installer/core/commands/lib/graphiti_diagnose_v3.py` |
| [TASK-REF-9C5A](TASK-REF-9C5A-relocate-demo-scripts.md) | low | 2 | Move 4 `demo_*.py` + `verify_micro_implementation.sh` to `examples/` | 5 files relocated to `examples/` |
| [TASK-REF-AD6B](TASK-REF-AD6B-relocate-markdown-docs.md) | low | 3 | Move 8 `.md` files to `docs/internals/commands-lib/` + update `/task-review`'s reference to `graphiti-preamble.md` | 8 md files + cross-reference update in `installer/core/commands/task-review.md` |
| [TASK-TSE-BE7C](TASK-TSE-BE7C-audit-orphaned-test-files.md) | low | 5 | Per-file audit of 15 orphaned `test_*.py` files (not bulk-moved — same failure mode as E841's dead test file) | 15 `test_*.py` files, individually moved/deleted |

**Parallel execution**: Up to 5 Conductor workspaces (`commands-lib-cleanup-wave1-1` through `-5`). Or, equivalently,
5 sequential `/task-work` runs on the main branch — the file sets are disjoint, so merge conflicts are only
plausible within `installer/core/commands/lib/` as the directory structure shrinks over time (git handles this fine).

### Wave 2 — Install.sh prune pass (1 task)

**Starts after Wave 1 is merged.** The Wave 1 tasks create dangling symlinks; Wave 2 cleans them up and adds
automatic pruning so future deletions don't recreate the problem.

| Task | Priority | Complexity | What |
|---|---|---|---|
| [TASK-FIX-CF8D](TASK-FIX-CF8D-prune-stale-bin-symlinks.md) | medium | 4 | Remove dangling symlinks under `~/.agentecflow/bin/` + add `prune_stale_bin_symlinks()` function to `install.sh` that runs on every install |

**Verification after Wave 2**: `test -e ~/.agentecflow/bin/template-validate-cli` should fail. All symlinks
created by Wave 1 deletions should be gone.

### Wave 3 — Install.sh manifest refactor (1 task, root-cause fix)

**Starts after Wave 2 is merged.** Same file (`install.sh`), so must be sequential with Wave 2.

| Task | Priority | Complexity | What |
|---|---|---|---|
| [TASK-ISH-D09E](TASK-ISH-D09E-replace-blind-walk-with-manifest.md) | medium | 5 | Replace `find commands/lib/ -name "*.py"` walk with an explicit `bin-entries.txt` manifest. Only files listed in the manifest become shell commands. Unlisted files produce a drift warning. |

**This is the structural fix.** Once it ships, adding a new file to `commands/lib/` does not silently promote
it to a global CLI command — the author must opt in via the manifest. This is the permanent prevention of the
E841 / C1B4 failure mode.

## Execution Strategy

### Recommended: one-at-a-time, main branch

Given the low complexity of most tasks (1–5) and the small file sets involved, **sequential `/task-work` on the
main branch is probably simpler than Conductor parallelization**. The tasks can still run in any Wave 1 order.

Suggested order:
1. `/task-work TASK-FIX-8B4F` — quickest, lowest risk (2 file deletes, no refs)
2. `/task-work TASK-FIX-7A3E` — dead code deletion, one test to verify
3. `/task-work TASK-REF-9C5A` — file moves, straightforward
4. `/task-work TASK-REF-AD6B` — file moves + cross-reference update (the `graphiti-preamble.md` care)
5. `/task-work TASK-TSE-BE7C` — largest task, per-file audit, highest ceremony
6. `/task-work TASK-FIX-CF8D` — **must wait until Wave 1 is merged**; cleans up the dangling symlinks Wave 1 created
7. `/task-work TASK-ISH-D09E` — **must wait until CF8D is merged**; root-cause fix

### Alternative: parallel Wave 1 with Conductor

Spawn 5 workspaces for Wave 1 tasks. After all 5 merge, run Wave 2. After Wave 2 merges, run Wave 3. Workspace
names are pre-assigned in the task frontmatter:

```
commands-lib-cleanup-wave1-1  → TASK-FIX-7A3E
commands-lib-cleanup-wave1-2  → TASK-FIX-8B4F
commands-lib-cleanup-wave1-3  → TASK-REF-9C5A
commands-lib-cleanup-wave1-4  → TASK-REF-AD6B
commands-lib-cleanup-wave1-5  → TASK-TSE-BE7C
commands-lib-cleanup-wave2-1  → TASK-FIX-CF8D
commands-lib-cleanup-wave3-1  → TASK-ISH-D09E
```

## Dependencies

```
Wave 1 (parallel):
  TASK-FIX-7A3E   ←—  no deps
  TASK-FIX-8B4F   ←—  no deps
  TASK-REF-9C5A   ←—  no deps
  TASK-REF-AD6B   ←—  no deps
  TASK-TSE-BE7C   ←—  no deps

Wave 2 (sequential after Wave 1 merges):
  TASK-FIX-CF8D   ←—  cleans up dangling symlinks created by Wave 1 deletions

Wave 3 (sequential after Wave 2 merges):
  TASK-ISH-D09E   ←—  depends_on: TASK-FIX-CF8D  (both touch install.sh)
```

## Acceptance (feature-level)

The feature is complete when, after all 7 tasks have merged, the following all hold:

- [ ] No `*_cli.py` files remain in `installer/core/commands/lib/` except any new ones added post-review.
- [ ] No `test_*.py` files remain in `installer/core/commands/lib/`.
- [ ] No `demo_*.py` or `verify_*.sh` files remain in `installer/core/commands/lib/`.
- [ ] No `*.md` files remain in `installer/core/commands/lib/` (all moved to `docs/internals/commands-lib/`).
- [ ] `graphiti_diagnose.py` remains; `_v2.py` and `_v3.py` are gone.
- [ ] `~/.agentecflow/bin/` contains no dangling symlinks pointing into `installer/core/commands/`.
- [ ] `install.sh` reads from an explicit `bin-entries.txt` (or equivalent) manifest instead of walking `commands/lib/` blindly.
- [ ] `install.sh` prunes stale symlinks on every run.
- [ ] The full pytest suite still passes.
- [ ] `/impact-analysis`, `/task-review`, and other slash commands that touched the affected files still work.
- [ ] `CHANGELOG.md` notes any removed bin commands (from ISH-D09E).

## What is explicitly NOT in this feature

- **Do not refactor the 63 legitimate `command-library` files** in `commands/lib/`. They are the directory's
  intended content. Keep them where they are.
- **Do not move the 7 subpackages** (`agent_validator/`, `clarification/`, `review_modes/`, etc.). They are
  internally structured and out of scope.
- **Do not audit `installer/core/lib/`** (the real library directory) or `installer/core/agents/`. Scope is
  strictly `commands/lib/` top-level.
- **Do not investigate individual orchestrator correctness, complexity, or design quality.** The concern is
  "is this file alive or dead, and does it belong here?" — not "is this file good?".
