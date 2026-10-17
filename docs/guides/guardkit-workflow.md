# Choose a GuardKit workflow

GuardKit has an interactive development workflow and a Python AutoBuild engine. The Software Factory orchestrates that engine as one stage of a broader lifecycle. Choose by who owns the next step, rather than treating every route as the same slash command.

**Verified 17 October 2026** against GuardKit `23d99208`.

| Route | You provide | Who advances the work | Review boundary |
| --- | --- | --- | --- |
| Interactive coding harness | A task or feature description and repository context | You and the coding agent | Command checkpoints, diff and test review |
| Standalone AutoBuild | A task or feature plan, configured model and toolchain | GuardKit's bounded Player–Coach loop | Preserved branch/worktree, explicit merge |
| Software Factory | A request or existing committed plan | Factory services and their stage ledger | Stage decisions, build evidence and delivery policy |

## Interactive development

Start with a small task using `/task-create` and `/task-work`, or curate behaviour with `/feature-spec` before `/feature-plan`. The coding agent follows installed command instructions, loads project context and invokes phase agents. This route suits exploration because the user is present to clarify intent.

`/task-work` can split design and implementation with `--design-only` and `--implement-only`. Intensity controls the amount of process. Green work normally ends at `IN_REVIEW`; `--complete` opts into the current completion phase. Neither completing a task nor generating a plan proves that software has been deployed.

Read [GuardKit in a coding harness](../harness/index.md) for support boundaries and [Get started](GETTING-STARTED.md) for installation.

## Standalone AutoBuild

AutoBuild reads task Markdown and feature YAML, prepares an isolated Git worktree and runs the Player–Coach loop. A feature groups dependent tasks into execution waves. Parallel capacity depends on configuration and available serving resources; a wave does not promise simultaneous execution.

The Player implements. The Coach combines independent executable evidence with model review, then approves or gives feedback. Iteration, time and failure bounds stop the loop when it cannot complete. Inspect the artifacts and changes before invoking the separate merge and completion commands. See [AutoBuild architecture](../deep-dives/autobuild-architecture.md).

### Pre-loop decision guide

Feature builds disable the additional design pre-loop by default because `/feature-plan` has already produced task specifications. Enable it when a task still needs that design work. Single-task AutoBuild enables the pre-loop by default; `--no-pre-loop` disables it. These are separate defaults from interactive `/task-work`.

The AutoBuild mode historically named `task-work` injects an implementation protocol into the Player. It does not run the interactive slash command again. [CLI implementation](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/autobuild.py) · [Player invocation](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/orchestrator/agent_invoker.py)

## Factory-managed work

The [Software Factory](../software-factory/index.md) adds request handling, planning stages, dispatch, durable stage records, approval handling and delivery. GuardKit remains the build engine. `guardkitfactory` is the Python harness package used by that engine, not the whole service fleet.

Do not substitute `guardkit task-work` for `/task-work`: the shell command is the headless fix-stage adapter used by the factory pipeline. Its arguments and exit-code contract differ from the interactive command. [Headless adapter](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/task_work.py)

## Evidence to retain in every route

Keep the approved request and assumptions, the plan and exact source revision, the resulting diff, the commands that actually ran and their results, and the review or approval decision. Record missing evidence as missing. This makes a demonstration reproducible and gives a new team something concrete to challenge and improve.
