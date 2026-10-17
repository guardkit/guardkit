# Present the harness and the Software Factory

Use this material as a source-backed presentation outline or a small YouTube series.
The diagrams are editable Mermaid blocks in the documentation source. The architecture
pages distinguish C4 structure from sequence views, so a slide can answer either
“what exists?” or “what happens next?” without mixing the two.

The snapshot is **17 October 2026**. Recheck the
[evidence page](../software-factory/evidence-and-limits.md) before reusing a current-state
claim. This is an outline and demonstration plan; it does not imply that recordings
or a finished slide deck have already been produced.

## A 25-minute presentation

| Slide | Main point | Visual or evidence | Speaker note |
|---|---|---|---|
| 1. A coding agent is one part of delivery | The outcome includes accepted, running behaviour | One request and its observable result | Start with the user's need, not the agent names |
| 2. Two ways to use GuardKit | Attended harness and factory orchestration are distinct | [Workflow comparison](../guides/guardkit-workflow.md) | Show which surface receives slash commands and which receives a factory request |
| 3. The system in its environment | People, Git, chat, models and delivery interact | [C4 context](../software-factory/architecture.md) | Explain the system boundary before zooming in |
| 4. Who owns what | Jarvis, Forge and AutoBuild have different jobs | C4 container view on the same page | An agent role is not automatically a separate service |
| 5. One feature through the factory | Approvals and evidence have explicit places | [Delivery sequence](../software-factory/delivery-flow.md) | State that the prepared route skips factory planning |
| 6. Player and Coach | Implementation and assessment are separate roles | [AutoBuild loop](../deep-dives/autobuild-architecture.md) | Independence of role does not guarantee independent errors |
| 7. What “done” means | Build, acceptance, merge and deployment differ | Outcome table in [evidence](../software-factory/evidence-and-limits.md) | A declined-merge trial is not delivered software |
| 8. The preview must match the merge | Approval must apply to the reviewed code | Candidate → preview → joined tree | Use the recorded moved-main refusal, including its limits |
| 9. What still fails | Planning, recovery, metrics and onboarding remain work | Current gaps table | Avoid presenting backlog items as implemented |
| 10. What others teach us | Different factories optimise different parts | [Industry comparison](industry-comparison.md) | Distinguish company-reported practice from independent evaluation |
| 11. Transfer the method | A second team must be able to operate and explain it | [Pathfinder stages](pathfinder-playbook.md) | Start with one useful slice and existing delivery controls |
| 12. The next experiment | Ask a measurable question | [Experiment record](field-kit.md#experiment-record) | End with the next evidence to collect, not an autonomy slogan |

Allow about two minutes per slide, with a short pause for the delivery sequence. For a
10-minute introduction, use slides 1–5, 9 and 11. For an engineering workshop, spend the
extra time tracing a failure through the real verification path.

## Episode briefs

### 1. From coding assistant to Software Factory

**Question:** What changes when a developer stops directing every implementation turn?

Show the same small feature as an attended task and a factory request. Explain ownership,
state, approvals and delivery evidence. Use the C4 context and container views.

**Keep beside the claim:** GuardKit installation alone does not provide the hosted
factory services. The factory remains a developing system, with the limits documented.

### 2. The tests passed, but was the feature delivered?

**Question:** Which evidence does a completion message actually establish?

Trace task checks, a real connected journey, review preview, publication and deployment.
Use a synthetic disconnected-API example for explanation; label it as a demonstration.
Use the recorded web proof only for what was actually observed.

**Keep beside the claim:** Passing the selected checks does not establish complete
correctness, security or reliability across other projects.

### 3. Player and Coach: useful disagreement needs evidence

**Question:** What does a second agent add if both believe the same wrong assumption?

Show the evidence given to the Coach and a deliberately wrong result caught by an
independent check. Explain bounded repair, escalation and project-owned verification.

**Keep beside the claim:** Different roles or model vendors do not by themselves prove
error independence. A known-bad control is stronger evidence than another approval count.

### 4. The approval was valid, but the code had changed

**Question:** What happens when another feature merges while a reviewer is looking?

Use the [recorded moved-main refusal](../software-factory/evidence-and-limits.md#recorded-operational-evidence).
Explain candidate identity with two branches and two different Git trees. Distinguish
the actual stale-preview refusal from an ordinary merge conflict.

**Keep beside the claim:** Refusing delivery preserves safety but can add rework. A
fresh preview or new attempt must follow the supported recovery path.

### 5. Local models improved; the factory still had a bottleneck

**Question:** Why is faster generation not the same as faster accepted delivery?

Show the six-request trial and the later eight-request follow-up together. Separate
configured concurrency, observed active builds, planning failures and merge policy.

**Keep beside the claim:** These are small, operator-reported fixture runs with merges
declined, not a benchmark against other factories or an enterprise reliability rate.

### 6. Take the lessons into a new team

**Question:** What should remain after an AI-native development pathfinder leaves?

Run a short teach-back with the feature contract, failure example and experiment record.
Show the team's own commands and acceptance criteria rather than requiring the same
infrastructure. Use the [pathfinder playbook](pathfinder-playbook.md).

**Keep beside the claim:** This is a proposed adoption approach; evaluate it with the
receiving team before making productivity claims.

## Demonstration checklist

Prepare a clean public fixture, immutable starting commit, bounded request and declared
checks. Decide whether the demonstration stops at review or includes an authorised
release. Record failed attempts and edited footage honestly. Hide credentials, private
repository material and access-bearing preview URLs.

For a repeatable workshop, demonstrate three things: a correct candidate passing, a
known incorrect candidate failing, and a second engineer explaining the difference.
Keep a [presentation evidence card](field-kit.md#a-presentation-evidence-card) for each
factual slide.

## Reuse the diagrams

Download a vector image, a PNG for presentation tools, or editable Mermaid source:

| View | SVG | PNG | Mermaid source |
|---|---|---|---|
| Harness and factory overview | [SVG](../assets/factory-diagrams/workflow-overview.svg) | [PNG](../assets/factory-diagrams/workflow-overview.png) | [Source](../assets/factory-diagrams/workflow-overview.mmd) |
| C4 system context | [SVG](../assets/factory-diagrams/c4-context.svg) | [PNG](../assets/factory-diagrams/c4-context.png) | [Source](../assets/factory-diagrams/c4-context.mmd) |
| C4 collaboration and control | [SVG](../assets/factory-diagrams/c4-coordination.svg) | [PNG](../assets/factory-diagrams/c4-coordination.png) | [Source](../assets/factory-diagrams/c4-coordination.mmd) |
| C4 execution and publication | [SVG](../assets/factory-diagrams/c4-execution.svg) | [PNG](../assets/factory-diagrams/c4-execution.png) | [Source](../assets/factory-diagrams/c4-execution.mmd) |
| C4 AutoBuild components | [SVG](../assets/factory-diagrams/c4-autobuild-components.svg) | [PNG](../assets/factory-diagrams/c4-autobuild-components.png) | [Source](../assets/factory-diagrams/c4-autobuild-components.mmd) |
| Planning sequence | [SVG](../assets/factory-diagrams/planning-sequence.svg) | [PNG](../assets/factory-diagrams/planning-sequence.png) | [Source](../assets/factory-diagrams/planning-sequence.mmd) |
| Build sequence | [SVG](../assets/factory-diagrams/build-sequence.svg) | [PNG](../assets/factory-diagrams/build-sequence.png) | [Source](../assets/factory-diagrams/build-sequence.mmd) |
| Delivery sequence | [SVG](../assets/factory-diagrams/delivery-sequence.svg) | [PNG](../assets/factory-diagrams/delivery-sequence.png) | [Source](../assets/factory-diagrams/delivery-sequence.mmd) |
| Player and Coach sequence | [SVG](../assets/factory-diagrams/player-coach-sequence.svg) | [PNG](../assets/factory-diagrams/player-coach-sequence.png) | [Source](../assets/factory-diagrams/player-coach-sequence.mmd) |

The exports are a snapshot of the diagrams in the pages above. Regenerate them when
those source blocks change. You can also copy a Mermaid block into an editor that
supports Mermaid. Retain the view title, system boundary, technology
labels and arrow descriptions. Put the source revision/date in speaker notes. Avoid
squeezing the entire factory onto one unreadable slide; use context, containers and
the delivery sequence as successive views.
