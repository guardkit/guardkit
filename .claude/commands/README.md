# `.claude/commands/` — retired repo-local fork (tombstone)

**Canonical command specifications live in [`installer/core/commands/`](../../installer/core/commands/).**
Do not re-add command markdowns here.

This directory once held a repo-local *fork* of the command specs. Session C's
mode-registry / template-loader
(`specialist-agent/docs/design/ws1-session-c-mode-registry-and-template-loader-2026-07-07.md`)
already **refuses** this directory as a source and resolves specs from the
**installed** guardkit distribution by content hash — so nothing headless ever
consumed these files. But they were still loaded by attended Claude Code
sessions, producing duplicate skill registration and, worse, stale mechanism.

The fork was dispositioned and removed by **PB-2** (guardkit modernization
review 2026-07-08 §5 DIM4-F1 CONFIRMED + §4 DIM3-F2 CONFIRMED). Disposition
detail: [`docs/decisions/DEC-claude-commands-fork-disposition.md`](../../docs/decisions/DEC-claude-commands-fork-disposition.md).

What was removed:

- **7 stale shadows** of installer specs (each verified DIFFER + stale by
  `git log`): `context-switch`, `feature-spec`, `system-plan`, `task-complete`,
  `task-create`, `task-status`, `task-work`. Notably `task-work.md` was 421 lines
  vs 4,480 canonical; `feature-spec.md` (856 lines) predated the pinned output
  contract — it still mandated Graphiti queries removed by FEAT-MEM-09 and lacked
  the single-physical-line Gherkin invariant (whose absence causes a downstream
  `CompositeParserException`).
- **2 retired commands** deleted from the installer (`ce914f7c` / `71becc51`) yet
  still invocable here: `impact-analysis`, `system-overview`. `impact-analysis.md`
  instructed `from guardkit.knowledge.graphiti_client import get_graphiti` — a
  module **physically removed** by FEAT-MEM-09 WS-2c — so an attended invocation
  loaded a spec whose implementation stack no longer exists.
- **6 never-canonical require-kit-era orphans** (frozen at `77f865f07`):
  `execute-tests`, `formalize-ears`, `gather-requirements`, `generate-bdd`,
  `task-work-specification`, `update-state`. These belong to
  [require-kit](https://github.com/requirekit/require-kit), never to guardkit.

**Retained:** `shared/agent_validation.py` is **kept** — it is a live consumer,
not an orphan: `tests/lib/agent_enhancement/test_validation.py` imports it (via a
`sys.path.insert` onto this `shared/` dir) and it backs the live
`agent-content-enhancer` agent (`installer/core/agents/agent-content-enhancer.md`).
It is a Python helper, not a command markdown, so it legitimately coexists with
this tombstone. Re-homing it to a canonical location is a separate follow-up (see
the DEC note).

To refresh this machine's *installed* command surface (which may still carry
retired names under `~/.claude` / `~/.agentecflow`), re-run
`installer/scripts/install.sh`. Install-time pruning of retired names arrives
with the PB-3 provenance manifest.
