# GuardKit in a coding harness

GuardKit adds repository instructions, planning commands, task records and quality checks to a coding agent. In the interactive workflow, you work with that agent in your project and answer its questions. The Software Factory adds services that accept work, execute stages and own their approval and delivery lifecycle. You can use the first without operating the second.

**Verified 17 October 2026** against GuardKit source commit `23d99208`. An installed package or command file may be older.

Returning from an older installation? The [July modernisation and migration guide](july-modernisation.md) lists retired commands, their replacements and changes to installed skills. In particular, `/task-refine` was removed; use `/task-work` again or `/task-review`'s **[I]mplement** flow.

## Keep three surfaces separate

| Surface | Where you use it | What executes |
| --- | --- | --- |
| Interactive GuardKit commands | Claude Code; Pi through its adapter | The coding agent reads a command definition, works in your project and delegates phases to agents. |
| Standalone AutoBuild | A shell, or `/feature-build` in the coding agent | GuardKit's Python orchestrator runs a bounded Player–Coach loop in a Git worktree. |
| Software Factory | The factory's front door | Services plan or accept a plan, dispatch AutoBuild, collect evidence and manage approval and delivery. |

There is also an internal meaning of *harness*: the runtime adapter used **inside AutoBuild**. Its default is LangGraph, with a dcode Player and Deep Agents Coach. That is independent of whether you typed your initial request in Claude Code, Pi or a factory interface. [AutoBuild architecture](../deep-dives/autobuild-architecture.md) explains that boundary.

## Installed support

Claude Code is the native interactive integration. The installer places command and agent definitions under `~/.agentecflow/` and connects them to Claude Code. Project initialization adds `.claude/` context, agents and rules from the chosen template.

Pi has an explicit adapter: run the installer with `--pi`, then invoke commands as `/skill:feature-plan`, `/skill:task-work`, and so on. Generated skills read the same installed command definitions. The adapter translates tool names and delegates agent work through separate Pi processes using the current model and the project's saved trust decision.

The audited installer does not provide equivalent native command installation for Codex, Cursor, Windsurf or Gemini. Those agents can read repository instructions and invoke shell commands, but that is not evidence that the Claude-oriented interactive workflow works unchanged. AutoBuild reading `AGENTS.md` is not a Codex slash-command integration. [Installer](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/scripts/install.sh) · [Pi adapter](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/pi/guardkit-on-pi.md)

## An interactive working session

Start with the [installation and first-task guide](../guides/GETTING-STARTED.md). Run these in your coding agent, from the **target project's root**:

```text
/task-create "Reject an empty display name with a useful validation message"
/task-work TASK-<returned-id>
```

The command reads the task and repository context, chooses agents, plans, evaluates complexity, implements, tests and reviews. Intensity changes which phases apply. A required human checkpoint is part of the workflow; it is not a guarantee that every model follows the instructions perfectly. Review the actual changes and test evidence.

For larger work, specify behaviour before decomposing implementation:

```text
/feature-spec "Allow a user to update their display name"
/feature-plan "Allow a user to update their display name" --context path/to/spec-summary.md
```

`/feature-spec` uses propose–review: it proposes scenarios, you curate them, and assumptions remain visible. `--auto` skips that curation and marks inferred assumptions low confidence. `/feature-plan` creates task files, an implementation guide and, by default, a feature YAML under `.guardkit/features/` for AutoBuild.

The Gherkin scenarios remain useful specifications. The old automatic `@task:` tagging and executed-Gherkin oracle are retired. Current planning assigns scenarios to named verification homes, such as an HTTP Hurl check or a named repository test. Enforcement of complete routing is explicit repository policy; writing a scenario alone does not make it executable evidence. [Feature specification command](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/feature-spec.md)

## Completion and review

Interactive `/task-work` normally leaves green work at `IN_REVIEW`. Phase 6 completion is currently **opt-in** with `--complete`; `--pause` keeps the review checkpoint. The completion routine checks required evidence before moving the task to completed. AutoBuild and `operator_handoff` tasks have different completion paths. [Task-work definition](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands/task-work.md)

```text
/task-work TASK-<id> --design-only
/task-work TASK-<id> --implement-only
/task-complete TASK-<id>
```

Use design-only and implement-only when you want to inspect the plan before implementation. For review work, `/task-review "description"` creates its own review task; `/task-review TASK-<id>` reviews an existing one. `/task-complete` remains available: its planned final retirement has not shipped.

## Instructions, templates and memory

Templates supply stack-specific guidance, agents and scaffolding. Current choices extend beyond the original four templates: Python libraries, FastAPI, React, Next.js, monorepos, .NET, MCP, NATS and Deep Agents variants are present. Choose for repository fit; old numerical template ratings are not comparative performance evidence. [Shipped templates](https://github.com/guardkit/guardkit/tree/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/templates)

Memory is optional and uses fleet-memory. The old Graphiti configuration is no longer the current runtime. Standalone use resolves a memory project from `GUARDKIT_MEMORY_PROJECT` or the repository's `.guardkit/config.yaml`; without a name it is off. The backend must also be enabled and configured. Factory launches use the identity handed over from the source commit, avoiding accidental use of a changed working copy's identity. [Memory project resolution](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/knowledge/memory_project.py)

## Moving to AutoBuild or the factory

For a standalone build, inspect the plan and run `guardkit autobuild feature FEAT-<id>` with your configured model. AutoBuild preserves a branch and worktree for review. Building, merging and recording completion are separate actions.

For the service lifecycle, use the [Software Factory](../software-factory/index.md). The shell command `guardkit task-work --task-id ...` is a **headless factory fix-stage adapter**. It is not the shell spelling of interactive `/task-work TASK-...` and does not accept the same workflow contract. [Headless work adapter](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/task_work.py)

For knowledge transfer, demonstrate one task's request, plan, diff, independent checks and review decision. That evidence gives another team more to learn from than a list of agent names or an autonomy claim.
