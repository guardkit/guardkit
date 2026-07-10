# DEC — Retire the design-tool trio (`/figma-to-react`, `/zeplin-to-maui`, `/mcp-zeplin`)

**Date:** 2026-07-10
**Status:** ACCEPTED (executed)
**Source:** `DECISION-DF-018-attended-command-surface-consolidation.md` §2.4 (PB-17), ACCEPTED
by Rich 2026-07-09 — **Option A, deprecate-then-remove via the PB-3 tombstone path** (Option B
"keep-as-deprecated" and Option C "retain one" both rejected). Grounded in the 2026-07-08
guardkit modernization review (`docs/reviews/guardkit-modernization-review-2026-07-08.md`
§5 DIM4-F4 / §9 ADR-C) and the prior, lapsed `TASK-UX-2DAB` deprecation plan. Executed by the
PB-17 / DF-018 §2.4 retirement session.
**Scope:** `installer/core/commands/figma-to-react.md` (739 lines) +
`installer/core/commands/zeplin-to-maui.md` (778) + `installer/core/commands/mcp-zeplin.md`
(802) = 2,319 lines + their live doc/tooling references. Historical records (docs/archive,
docs/reviews, docs/adr, docs/proposals, docs/state, docs/validation, docs/implementation,
`.claude/task-plans`, `.claude/reviews`, `tasks/archived`, past `tasks/in_review` implementation
records) deliberately untouched.

## Context

The trio documented stack-specific design-to-code (`/figma-to-react` → React, `/zeplin-to-maui`
→ .NET MAUI) plus a Zeplin MCP integration (`/mcp-zeplin`) the orchestrator does not implement.
Evidence from DF-018 §2.4 and the modernization review:

- **Lapsed deprecation already on the books.** `TASK-UX-2DAB` (2025-11-11) planned deprecating
  `/figma-to-react` + `/zeplin-to-maui` in favour of the unified `/task-create design:`
  workflow, with `removal_planned: 2026-06-01` — **a date now lapsed, unexecuted**. `mcp-zeplin`
  was never covered; DF-018 §2.4 extends the disposition to it.
- **No live consumer.** No guardkit/installer code, command, or rule invokes them. The three are
  frozen relics + duplicate skill-registration surface — pure carrying cost.
- **The replacement exists at a different layer.** The live design capability is the `design_url`
  path — `guardkit/orchestrator/mcp_design_extractor.py` + `guardkit/design/` — technology-agnostic
  and integrated with the task/autobuild workflow. The trio's stack-specific command surface is
  superseded by it.

## Decision

Delete the three command markdowns; tombstone all three in
`scripts/generate_command_manifest.py` (PB-3 mechanism: `install.sh` prunes the installed copies
on the next run; `guardkit doctor` reports stragglers). Replacement guidance in live docs: the
unified `design_url` / `/task-create design:` → `/task-work` workflow.

## Executed

- Three specs deleted; manifest regenerated (tombstone count 3 → 6; command count 28 → 25).
- Live references removed/updated: `installer/core/commands/debug.md` (Zeplin-MCP prerequisite
  line), `tests/documentation/test_documentation_audit.py` (known-commands set),
  `docs/guides/claude-code-web-setup.md` (command lists ×2), `docs/guides/guardkit-workflow.md`
  (design-workflow bullets), `tasks/backlog/documentation/TASK-DOC-api-reference.md` (planned
  command list). `docs/shared/design-to-code-common.md` and
  `docs/deep-dives/mcp-integration/mcp-optimization.md` carry dated retirement banners and are
  preserved as historical records (the MCP-optimization doc's lazy-load examples remain as
  pedagogy).
- The lapsed `TASK-UX-2DAB` and its stalled sibling design-url-integration tasks
  (all `backlog`, dated 2025-11-11) are closed to `tasks/completed/2026-07/design-url-integration/`
  with a dated outcome note: the trio is retired here; the design capability shipped separately in
  the orchestrator `design_url` path; the 2025-11 command-integration/deprecation plan is
  superseded. (Tracker-hygiene close per WS3-S8a declared-vs-inferred divergence.)
- Installed-surface prune verified by an `install.sh` re-run (the three names gone from
  `~/.agentecflow/commands` / project `.claude/commands`).
- The live `design_url` path (`guardkit/orchestrator/mcp_design_extractor.py`, `guardkit/design/`)
  is untouched, as are all pinned template bytes.

## Non-goals

The broader design-url-integration *feature build* (a `/task-create design:` command-level
parameter, ui-specialist extensions, pattern docs) is NOT delivered by this note — those folder
tasks are closed as **superseded/obsolete**, not as individually shipped. Any future
technology-agnostic design work runs through the orchestrator `design_url` path, not a revived
stack-specific command.
