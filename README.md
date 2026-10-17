# GuardKit

GuardKit supports planned AI-assisted development with explicit task records and
verification. Use it inside a coding harness, run its bounded AutoBuild engine from
a shell, or invoke AutoBuild through the Software Factory.

[Documentation](https://guardkit.ai/) · [Quickstart](docs/guides/GETTING-STARTED.md) ·
[Factory architecture](docs/software-factory/architecture.md) ·
[Evidence and limitations](docs/software-factory/evidence-and-limits.md)

## Choose a workflow

| Workflow | Who coordinates it? | Start here |
|---|---|---|
| Interactive planning and implementation | You and your coding agent | [GuardKit in a coding harness](docs/harness/index.md) |
| Standalone Player/Coach build | GuardKit's Python orchestrator | [AutoBuild architecture](docs/deep-dives/autobuild-architecture.md) |
| Request-to-delivery factory | Forge, with Jarvis presenting decisions | [Using the Software Factory](docs/software-factory/using-the-factory.md) |

GuardKit AutoBuild is one part of the factory. The `guardkitfactory` Python package
supplies the execution harness; it is not the entire service deployment. Installing
GuardKit does not install Forge, Jarvis or the factory's publication infrastructure.

## Get started

Follow the [source-verified installation guide](docs/guides/GETTING-STARTED.md), which
pins the revisions described by the documentation and explains the Python environment,
command installer and project initialization. The package entrypoint is `guardkit-py`;
the installer also supplies the `guardkit` wrapper.

Then, in your **application repository**, use the installed Claude Code commands:

```text
/task-create "Reject an empty display name with a useful validation message"
/task-work TASK-<returned-id>
```

Review the changes and executed evidence before completing the task. For a larger
feature, use `/feature-spec` to curate behaviour and `/feature-plan` to decompose work.
Pi has an explicit adapter; equivalent native command support for other coding
harnesses should not be assumed. See the [support details](docs/harness/index.md).

## Current AutoBuild architecture

The documented source snapshot is **17 October 2026**. AutoBuild defaults to the
LangGraph harness, with a deepagents-code Player and a Deep Agents Coach. The Claude
Agent SDK path is an explicit alternative. Memory uses fleet-memory; older Graphiti
and SDK-only descriptions are historical.

AutoBuild preserves a candidate for review. Building, merging and recording completion
are distinct operations. Project declarations and task profiles determine the checks
that run; tests and model review reduce specific risks rather than guaranteeing correct
or production-ready code.

Read the [current architecture and commands](docs/deep-dives/autobuild-architecture.md)
before running a build. It describes model configuration, independent evidence, resume,
permission limits and the distinction between a Git worktree and an OS sandbox.

## Understand the Software Factory

- [Overview](docs/software-factory/index.md) and [C4 architecture](docs/software-factory/architecture.md)
- [Delivery sequences](docs/software-factory/delivery-flow.md) and [project readiness](docs/software-factory/project-readiness.md)
- [Implementation sources](docs/software-factory/sources.md) and [recorded evidence](docs/software-factory/evidence-and-limits.md)

The factory has recorded working delivery and preview flows, with remaining planning,
recovery, reporting and onboarding limitations. Private repository and prototype
intake are work in progress at this snapshot.

## Learn and teach

- [Engineering lessons](docs/learning/lessons.md)
- [Other software factories: primary-source comparison](docs/learning/industry-comparison.md)
- [AI-native development pathfinder](docs/learning/pathfinder-playbook.md)
- [Reusable records and handovers](docs/learning/field-kit.md)
- [Presentation and video kit](docs/learning/presentation-kit.md)

## Build the documentation

```bash
python -m pip install -r docs/requirements.txt
mkdocs build
mkdocs serve
```

Older reference pages retain their URLs and carry a notice when their examples have
not been revalidated. The harness, factory and learning sections are the refreshed
entrypoints. See [documentation maintenance](docs/software-factory/sources.md#keep-the-site-current).
