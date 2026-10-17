# Engineering lessons from building the factory

The most transferable work is often the repair of a mistaken assumption. These lessons
combine mechanisms visible in the [source snapshot](../software-factory/sources.md)
with the explicitly labelled operational reports in
[evidence and limitations](../software-factory/evidence-and-limits.md).

## Separate instructions, orchestration and authority

The attended harness, Forge and AutoBuild have different responsibilities. Jarvis
transports routine requests and decisions; it does not need to reason about every
workflow transition. Forge coordinates the delivery; Player and Coach perform bounded
jobs inside it.

**Transfer:** draw the owner of each decision before adding another agent. Make retries,
timeouts and permission checks deterministic where the answer is already known. This
reduces the number of places where a model can reinterpret the process.

## Independent evidence must reach the actual decision

A detector can work in isolation while its production caller gives it an empty file
list. A reviewer can approve a plausible report without observing the behaviour that
matters. The current build architecture gathers evidence outside the Player's prose,
but the usefulness of that evidence still depends on the checks and their inputs.

**Transfer:** introduce a known defect in an isolated fixture and follow it through the
normal caller to the final refusal. A unit test of the detector alone does not show
that the delivery workflow uses it. Record “not run” separately from “ran and passed”.
See [AutoBuild's evidence path](../deep-dives/autobuild-architecture.md).

## A passing task is smaller than a working product

Task-level checks, a buildable application, a connected user journey and a running
deployment establish different things. The factory's web readiness work joins browser,
API, database and identity behaviour, and presents a preview before the merge decision.
The [recorded web proofs](../software-factory/evidence-and-limits.md#recorded-operational-evidence)
are useful precisely because they go beyond a model declaring completion.

**Transfer:** define the user's observable result first. Put component tests underneath
it, then include at least one real connection across the boundaries most likely to
fail. Use project-appropriate checks for agent decisions, APIs, web and mobile clients.

## The reviewer must see the candidate that gets delivered

While one feature waits for approval, another may change the target branch. A clean
Git merge does not mean the resulting tree matches the preview. Forge checks the
relationship between the reviewed candidate, preview and joined result, and the
recorded moved-main trial exercised a refusal without a merge conflict.

**Transfer:** bind review evidence to a revision. Recheck after integration changes that
revision. Never treat an old screenshot or green result as evidence for new code.
See the [delivery sequence](../software-factory/delivery-flow.md).

## Protect the checks used to judge a change

An implementation may legitimately edit test infrastructure. That also gives it a way
to weaken the condition used to accept itself. The factory's merge verification uses
the target's designated judge files for the joined candidate, with the change explained
on the card.

**Transfer:** distinguish product changes from changes to acceptance machinery. Review
the latter explicitly and avoid letting a candidate silently supply a weaker judge.
This does not make the current checks complete; their coverage still needs evaluation.

## Put credentials outside the environment executing product code

The factory separates the build sandbox from the publisher and uses narrow proxy
services for model and memory access. This is an authority boundary: running a test
or installing dependencies should not automatically grant publication credentials.

**Transfer:** enumerate what generated code can read and call, including shared mounts,
service endpoints and caches. Treat Git worktrees as version isolation, not a security
sandbox. The present shared factory is not evidence of tenant isolation; see
[current gaps](../software-factory/evidence-and-limits.md#current-gaps).

## Context must be available to the worker that needs it

A decision in a chat or an operator's private notebook does not constrain an agent
that never receives it. The factory binds selected project documents to the source
revision and supplies them to planning and build roles.

**Transfer:** give every important constraint a home in the target repository, link it
from the task and verify delivery to the relevant role. Keep procedural instructions
small, and detailed evidence discoverable. Memory retrieval can help, but it should
not silently outrank the current project contract.

## Measure the bottleneck rather than the advertised capacity

The October trials improved the model-serving environment, but the follow-up reached
only four simultaneous builds even after the configured limit became six. Planning
and malformed outputs still constrained completed work. Model tokens per second,
concurrent requests and accepted features per hour are different measurements.

**Transfer:** measure queue, planning, execution, review and delivery separately. Keep
failed attempts in the denominator, and check that dashboards reconcile with the
underlying records before using them in a business case.

## Keep operational records out of product history

Conversation transcripts and large tool outputs can be useful evidence without
belonging in the product's Git commits. The current factory excludes these records
from build commits and checks publication inputs.

**Transfer:** decide where source, review evidence and operational logs belong. Test the
actual publication path, including retries and generated files. A `.gitignore` entry
alone does not prove already-tracked or explicitly staged content cannot be published.

## Convert each lesson into a capability another team can use

For a pathfinder, the reusable output is a working example, a failure demonstration,
an owned command and a short explanation of its limits. Use the
[learning record](field-kit.md#learning-record) and ask a receiving engineer to teach
it back. The [industry comparison](industry-comparison.md) provides useful alternatives
where other teams have documented more mature practices.
