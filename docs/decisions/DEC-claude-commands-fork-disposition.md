# DEC — Disposition of the repo-local `.claude/commands/` command fork

**Date:** 2026-07-08
**Status:** ACCEPTED (executed)
**Source:** PB-2 (guardkit modernization review 2026-07-08 §5 DIM4-F1 CONFIRMED,
§4 DIM3-F2 CONFIRMED). Executed by the O2 repo-hygiene Opus session.
**Scope:** repo-local `guardkit/.claude/commands/` only. Installer specs
(`installer/core/commands/`) are canonical and were **not** touched.

## Context

`guardkit/.claude/commands/` held a repo-local fork of the command markdowns. It
was a stale **third** fork (alongside the installed `~/.claude` / `~/.agentecflow`
surfaces). Session C's mode-registry / template-loader already refuses this
directory as a source and resolves specs from the *installed* distribution by
sha256 content hash — so nothing headless consumed it — but attended Claude Code
sessions still loaded it, producing live **duplicate skill registration** and, in
two cases, mechanism whose implementation stack has been deleted.

Each file was classified by `diff` against the installer counterpart and by
`git log` on the repo-local path before disposition (no file was assumed stale).

## Decision

Delete the fork. Leave a tombstone `README.md` naming `installer/core/commands/`
as canonical. Refresh installed surfaces by re-running `install.sh`.

### (a) Stale shadows — DELETED (7)

Verified DIFFER from the installer spec and stale by `git log`:

| file | repo lines | installer lines | last repo touch |
|---|---|---|---|
| `context-switch.md` | 541 | 536 | 2026-02-10 |
| `feature-spec.md` | 856 | 937 | 2026-02-22 |
| `system-plan.md` | 1262 | 1003 | 2026-02-15 |
| `task-complete.md` | 231 | 438 | 2025-10-28 |
| `task-create.md` | 499 | 1117 | 2025-10-28 |
| `task-status.md` | 387 | 352 | 2026-06-13 |
| `task-work.md` | 421 | 4480 | 2026-02-15 |

`feature-spec.md` (856 lines) predated the pinned output contract: it still
mandated Graphiti queries removed by FEAT-MEM-09 and lacked the single-physical-
line Gherkin invariant (its absence causes a downstream `CompositeParserException`).
`task-status.md`'s one recent touch (`79630e56`, 2026-06-13) was an incidental
`export:json`→`--json` patch to the *shadow*; the canonical installer spec already
carries `--json` and no `export:json` orphan, so no fix is lost. None of the seven
was a deliberate divergence-by-intent override.

### (b) Retired commands — DELETED (2)

Deleted from the installer (`ce914f7c` / `71becc51`) yet still invocable here:

- `impact-analysis.md` — instructed `from guardkit.knowledge.graphiti_client
  import get_graphiti`, a module **physically removed** by FEAT-MEM-09 WS-2c.
- `system-overview.md`.

### (c) Never-canonical require-kit-era orphans — DELETED (6)

Frozen at `77f865f07` (initial clone), never canonical in guardkit:
`execute-tests`, `formalize-ears`, `gather-requirements`, `generate-bdd`,
`task-work-specification`, `update-state`.

**Disposition:** these belong to
[require-kit](https://github.com/requirekit/require-kit), not guardkit. No live
guardkit or installer consumer references them (`git grep` clean outside the fork
itself and gitignored worktree copies). Deleted rather than moved — require-kit
owns its own canonical copies; re-homing stale guardkit forks into it would just
create a fourth fork. If a future integration needs them, pull from require-kit.

### (d) `shared/agent_validation.py` — RETAINED (live consumer)

**Kept.** Initially mis-classified as an orphan (a reversed-word-order grep,
`from agent_validation import`, missed the consumer). It is a **live** dependency:
`tests/lib/agent_enhancement/test_validation.py` imports it via an explicit
`sys.path.insert(0, .claude/commands/shared)` (17 tests), and it backs the live
`agent-content-enhancer` agent (`installer/core/agents/agent-content-enhancer.md`
+ `-ext`). A pre-push pytest-collection guard caught the deletion before it landed
on the remote. It is a Python helper, not a command markdown, so it coexists with
the tombstone. **Follow-up (out of scope for PB-2):** re-home it to a canonical
location (e.g. `installer/core/commands/lib/` or the test tree) and drop the
`sys.path.insert`, so the last live artifact leaves the tombstoned fork dir.

> **LANDED 2026-07-09 (PB-2 residue):** `agent_validation.py` was `git mv`d to
> `installer/core/commands/lib/agent_validation.py`;
> `tests/lib/agent_enhancement/test_validation.py` now does a structural
> `from installer.core.commands.lib.agent_validation import ...` (the editable
> install puts the repo root on `sys.path`) — the `sys.path.insert` is gone. The
> now-empty `.claude/commands/shared/` directory was removed; the
> `.claude/commands/README.md` tombstone stays. The `agent-content-enhancer`
> agent def carries no baked path to the module (verified). 17 tests green.

## Consequences

- **Frozen items:** none touched. Installer specs, the pinned templates, and the
  FEAT-SPL-007/008 output contracts are untouched.
- **Headless:** zero impact — Session C's loader already refused this directory.
- **Attended:** the duplicate skill registrations (`context-switch`,
  `feature-spec`, `impact-analysis`, `system-overview`, `system-plan`,
  `task-complete`, `task-create`, `task-status`, `task-work`) clear once a fresh
  session loads only `installer/core/commands/`.
- **Installed surfaces** (`~/.claude`, `~/.agentecflow`) are unversioned and may
  still carry retired names; re-run `installer/scripts/install.sh` to refresh.
  Install-time pruning of retired names is PB-3 (provenance manifest).
- **Acceptance:** for shared names, `installer/core/commands/` is the sole source;
  a fresh session's skill list carries no duplicate or retired command entries.
