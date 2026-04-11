# commands-lib-cleanup

Cleanup sprint for `installer/core/commands/lib/`, scoped from the audit in
[TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md).

## Why

`/task-review TASK-REV-C1B4` audited `installer/core/commands/lib/` after
[TASK-FIX-E841](../../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md) deleted a dead CLI shim
(`template_validate_cli.py`) and its equally-dead integration test. The review asked: *are there other silent
rotters in this directory, and what structural problem let them accumulate?*

**The answer**:
- **One more dead shim** — `upfront_complexity_cli.py` + `upfront_complexity_adapter.py`, residue of abandoned
  TASK-005 design, never wired into `/impact-analysis`.
- **One dangling symlink** — E841's cleanup was incomplete: `~/.agentecflow/bin/template-validate-cli` still
  points at the deleted file.
- **Directory hygiene problems** — 15 orphaned `test_*.py` files pytest doesn't collect; 4 demo scripts mixed in
  with production code; 8 README/docs markdown files at the same level as Python modules; 3 versioned
  `graphiti_diagnose*.py` debug scripts, two of which hardcode infrastructure hosts.
- **One root cause** — `install.sh` blindly symlinks every `.py` file in `commands/lib/` into
  `~/.agentecflow/bin/`, promoting dead code and demo scripts to global shell commands. This is the structural
  reason silent rot happens here. Fix the root cause and the directory stays clean.

See the [review report](../../../.claude/reviews/TASK-REV-C1B4-review-report.md) for full evidence.

## What's in this folder

- **[IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)** — wave breakdown, dependency graph, execution strategy
- **7 subtask files** — one per recommendation

## Subtasks

### Wave 1 — Parallel-friendly cleanup (5 tasks, no deps)

| Task | Priority | Summary |
|---|---|---|
| [TASK-FIX-7A3E](TASK-FIX-7A3E-delete-dead-upfront-complexity-cli.md) | medium | Delete dead `upfront_complexity_cli.py` + adapter + unit test |
| [TASK-FIX-8B4F](TASK-FIX-8B4F-delete-graphiti-diagnose-v2-v3.md) | low | Delete hardcoded-host `graphiti_diagnose_v2.py` / `_v3.py` |
| [TASK-REF-9C5A](TASK-REF-9C5A-relocate-demo-scripts.md) | low | Move 4 `demo_*.py` + `verify_*.sh` to `examples/` |
| [TASK-REF-AD6B](TASK-REF-AD6B-relocate-markdown-docs.md) | low | Move 8 `.md` files to `docs/internals/commands-lib/` (mind the `graphiti-preamble.md` cross-ref) |
| [TASK-TSE-BE7C](TASK-TSE-BE7C-audit-orphaned-test-files.md) | low | Per-file audit of 15 orphaned `test_*.py` files |

### Wave 2 — Cleanup + prune pass (1 task, after Wave 1)

| Task | Priority | Summary |
|---|---|---|
| [TASK-FIX-CF8D](TASK-FIX-CF8D-prune-stale-bin-symlinks.md) | medium | Clean dangling `~/.agentecflow/bin/` symlinks + add `prune_stale_bin_symlinks()` to `install.sh` |

### Wave 3 — Root-cause fix (1 task, after Wave 2)

| Task | Priority | Summary |
|---|---|---|
| [TASK-ISH-D09E](TASK-ISH-D09E-replace-blind-walk-with-manifest.md) | medium | Replace `install.sh` blind walk with explicit `bin-entries.txt` manifest |

## How to run

Sequential is fine (and probably simpler than Conductor for this cleanup):

```bash
# Wave 1 — any order, each task is independent
/task-work TASK-FIX-8B4F
/task-work TASK-FIX-7A3E
/task-work TASK-REF-9C5A
/task-work TASK-REF-AD6B
/task-work TASK-TSE-BE7C

# Wave 2 — after Wave 1 is merged
/task-work TASK-FIX-CF8D

# Wave 3 — after Wave 2 is merged
/task-work TASK-ISH-D09E
```

Or spawn Wave 1 in parallel via Conductor; workspace names are pre-assigned in each subtask's frontmatter.

## Out of scope

- Refactoring the 63 legitimate command-library files (they are the directory's intended content)
- Moving the 7 subpackages (`agent_validator/`, `clarification/`, etc. — internally structured, out of scope)
- Auditing `installer/core/lib/` or `installer/core/agents/` (scope is `commands/lib/` only)
- Evaluating individual orchestrator correctness (concern is alive-or-dead, not quality)

## Provenance

- **Parent review**: TASK-REV-C1B4 (2026-04-11)
- **Grandparent fix**: TASK-FIX-E841 (deleted the first dead shim + its dead test)
- **Grandparent reviews** that originally surfaced the side note:
  [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md),
  [TASK-REV-D0C1](../../in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md)
