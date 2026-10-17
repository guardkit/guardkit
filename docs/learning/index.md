# Learn, teach and transfer the approach

Use these routes to explain the system without reading its implementation. The
material separates what GuardKit currently does from practices a new team could adopt.

## A 20-minute introduction

1. Read [the two workflows](../guides/guardkit-workflow.md).
2. Use the C4 context view in [factory architecture](../software-factory/architecture.md)
   to explain the people and systems.
3. Follow one feature through [the delivery flow](../software-factory/delivery-flow.md).
4. Finish with [current limitations](../software-factory/evidence-and-limits.md), so a
   working demonstration is not mistaken for a general reliability claim.

The central idea: a coding agent produces changes; a delivery system must also decide
what to build, check it, preserve review identity and report what happened.

## An engineering walkthrough

Read [AutoBuild](../deep-dives/autobuild-architecture.md),
[project readiness](../software-factory/project-readiness.md) and the
[lessons](lessons.md). Trace one requirement through the task, Player output,
independent check, candidate, approval and publication result. Ask where an incorrect
implementation would be rejected and how to demonstrate that rejection.

## A team pathfinder

Start with the [pathfinder playbook](pathfinder-playbook.md), then copy the
[field kit](field-kit.md) into the team's own repository. Pick one real, bounded
journey and a named receiving engineer. Transfer the method before choosing whether
the organisation needs the same software or deployment topology.

## A presentation or YouTube series

The [presentation kit](presentation-kit.md) contains a slide narrative, episode
briefs, diagram choices and demonstration boundaries. Pair each claim with a source
or a labelled proposal. Use the [industry comparison](industry-comparison.md) to
show where other teams have documented stronger practices.

## Vocabulary for mixed audiences

| Term | Meaning here |
|---|---|
| Coding harness | The environment that gives a model instructions, tools and execution controls |
| Agent | A model-driven role acting through those tools; it need not be a separate service |
| AutoBuild | GuardKit's bounded implementation and review loop |
| Player | The role that changes the product code |
| Coach | The role that assesses the result using supplied and independently gathered evidence |
| Forge | The factory workflow service, including planning and delivery control |
| Jarvis | The conversation interface; routine factory intake follows deterministic routing |
| Candidate | A particular Git revision proposed for review and delivery |
| Gate | A decision that can stop progression; a report that cannot stop it is not a blocking gate |
| Receipt | A recorded result tied to an operation and its source identity |
| Pathfinder | A bounded introduction that leaves another team able to repeat and evaluate the method |

For implementation evidence and revision dates, use the
[source register](../software-factory/sources.md).
