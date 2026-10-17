# July modernisation: commands, skills and migration

The July 2026 modernisation removed obsolete commands, cleared duplicate command
definitions and simplified review and completion. If you are returning from an older
GuardKit installation or video, use this page to translate that workflow.

**Verified 17 October 2026** against GuardKit `23d99208`. The tables distinguish
implemented changes from accepted plans. They describe the interactive coding harness;
the [Software Factory](../software-factory/index.md) has its own execution and delivery
lifecycle.

## Retired commands and what to use instead

The current [distribution manifest][manifest] records six retired command filenames.
These commands are removed, rather than deprecated commands that still work.

| Old command | Removed | Current guidance |
|---|---|---|
| `/impact-analysis` | 2 July | Its Graphiti implementation was removed. Ask `/task-review "Assess the impact of …"` to review the actual repository and record findings. This is a review workflow, not a replacement graph-query API. |
| `/system-overview` | 2 July | Read the repository's architecture and context documents; use `/system-plan "…"` for a focused architecture planning question. There is no same-name replacement command. |
| `/task-refine` | 9 July | Re-run `/task-work TASK-<id>` with the requested changes, or use `/task-review`'s **[I]mplement** flow for review findings. The claimed `refinement_handler.py` implementation never existed. |
| `/figma-to-react` | 10 July | The stack-specific command was removed. The retirement decision points toward the orchestrator's `design_url` path; see the integration limit below. |
| `/zeplin-to-maui` | 10 July | Removed with the same design-tool consolidation. There is no supported same-name replacement. |
| `/mcp-zeplin` | 10 July | Removed; its documented Zeplin integration was not implemented. |

Sources: [memory-related retirements][memory-retirement], [architecture command
rewrite][architecture-retirement], [task-refine decision][refine-decision] and
[design-tool retirement decision][design-decision].

**Design integration limit:** the retirement decision does not establish a working
`/task-create design:` → `/task-work` integration. Its non-goals explicitly say that
command-level feature was not delivered by the retirement. The inspected
[design extractor][extractor] also leaves its Figma and Zeplin MCP call methods as
`NotImplementedError`. Treat `design_url` as the documented integration direction,
not a ready-to-run substitute or a verified design-to-code demonstration.

For an existing task needing changes, the normal interactive route is:

```text
/task-work TASK-<id>
```

For a review that should create its own durable record:

```text
/task-review "Assess the validation changes and recommend any fixes" --mode=code-quality
```

Choose **[I]mplement** if you want the resulting findings turned into implementation
work. Neither route needs `/task-refine`.

## Changed, retained and still planned

| Area | What is implemented in the inspected source |
|---|---|
| Review entry | `/task-review "description"` creates a `TASK-REV-*` record before reviewing. You can still pass an existing task ID. The preliminary `/task-create` step is optional. |
| Completion | `/task-complete` remains installed as a wrapper around `guardkit task complete`. The shared routine owns completion instead of each caller implementing its own file move. |
| Completion during work | `/task-work … --complete` opts into Phase 6. It is **off by default**; ordinary green work ends at `IN_REVIEW`. `--pause` preserves that checkpoint. AutoBuild mode and `operator_handoff` tasks do not use this automatic completion path. |
| Final retirement of `/task-complete` | Planned as the last consolidation phase; **not implemented**. Do not remove it from current command guidance. |
| Smaller command instructions | `/task-work` has core instructions plus phase/reference files. `/task-review`, `/agent-validate` and `/template-create` also have extended reference files loaded as needed. This is progressive disclosure, not retirement of those commands. |
| Architecture/design consolidation | The proposed reduction from five commands to at most three has **not shipped**: `/arch-refine`, `/design-refine`, `/system-arch`, `/system-design` and `/system-plan` remain in the manifest. |
| Template creation | `/template-create` remains. No `/create-template-task` command was added. The accepted simplification direction does not mean the checkpoint/resume agent bridge was removed; it remains in the inspected command. |
| Command distribution | Command content ships with the Python package. A manifest records provenance and retired names; the installer and doctor use it to detect drift and obsolete installed copies. |
| Memory | The July Graphiti removal moved the current memory surface to fleet-memory and `guardkit memory` commands. Old Graphiti setup instructions no longer describe the active backend. |

Compare the [July consolidation decision][consolidation] with the current
[task-work][task-work], [task-review][task-review], [task-complete][task-complete]
and [template-create][template-create] definitions. The decision records intent;
the installed files and runtime establish what shipped.

## Why some skills disappeared or stopped appearing twice

On 8 July, GuardKit removed its own stale `.claude/commands/` fork. Commands such as
`/task-work`, `/feature-spec` and `/context-switch` still exist in the canonical
`installer/core/commands/` source. Removing their repository-local duplicates was
not retirement of the commands themselves.

That cleanup also removed six **never-canonical require-kit copies** from GuardKit's
repository: `execute-tests`, `formalize-ears`, `gather-requirements`, `generate-bdd`,
`task-work-specification` and `update-state`. This is a GuardKit fork cleanup, not a
claim that require-kit retired those capabilities. [Fork disposition][fork-decision]

The later Pi adapter generates `/skill:<command>` entries from the installed command
definitions. It is a separate packaging mechanism, not evidence that July renamed
every Claude command into a universal skill. See [installed harness support](index.md#installed-support).

## Refresh an older installation

Inspect local customisations before refreshing: the installer recopies its managed
command definitions, whereas `init --update` preserves and reports edited command
files unless `--force` is explicitly requested.

1. Update the GuardKit source/package you intend to use. Follow the
   [installation guide](../guides/GETTING-STARTED.md) for the documented source snapshot
   and dependencies. `init --update` does not download a newer package.
2. From that GuardKit source checkout, re-run `./installer/scripts/install.sh`.
   It prunes exact manifest-declared retired names from `~/.agentecflow/commands`.
   For Pi, include `--pi` to regenerate the GuardKit-owned skill directory.
3. From your application repository, run `guardkit-py doctor`. For command files
   reported as stale, run `guardkit init --update`, then inspect the report again.
4. Check any independent project-local `.claude/commands/` copies and custom skill
   wrappers. Remove confirmed obsolete GuardKit copies after reviewing local edits,
   then start a fresh coding-agent session.

**Pruning has a boundary.** The installer does not sweep every project's command
directory. `init --update` refreshes tracked files but does not delete retired names.
Doctor examines recognised command surfaces and can skip a project directory containing
only retired or untracked files. An old command still appearing in your agent can
therefore be a local shadow; it does not establish current support.
[Installer][installer] · [Update implementation][init] · [Doctor][doctor]

`init --update` is a later improvement, added in August. It is included here as
current upgrade guidance, not as a July deliverable.

## Use this in a presentation or team handover

Show three examples: `/task-refine` removed, `/task-review` made easier to start, and
`/task-complete` retained while sharing its implementation. Then show the manifest
and one installed command. The transferable lesson is that fewer entry points,
versioned instructions and explicit migration support reduce ambiguity for both
developers and agents. A design decision alone is not evidence that a migration
finished.

Keep the timeline clear: the automatic Gherkin `@task:` tagging and executed-BDD
oracle retirement happened in **August**, not as part of these July command removals.
The [current harness guide](index.md) describes that later behaviour.

[manifest]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/MANIFEST.json
[memory-retirement]: https://github.com/guardkit/guardkit/commit/ce914f7c
[architecture-retirement]: https://github.com/guardkit/guardkit/commit/71becc51
[refine-decision]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/docs/decisions/DEC-task-refine-retirement.md
[design-decision]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/docs/decisions/DEC-design-tool-trio-retirement.md
[extractor]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/orchestrator/mcp_design_extractor.py
[consolidation]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/docs/decisions/DECISION-DF-018-attended-command-surface-consolidation.md
[task-work]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/task-work.md
[task-review]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/task-review.md
[task-complete]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/task-complete.md
[template-create]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/template-create.md
[fork-decision]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/docs/decisions/DEC-claude-commands-fork-disposition.md
[installer]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/scripts/install.sh
[init]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/init.py
[doctor]: https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/doctor.py
