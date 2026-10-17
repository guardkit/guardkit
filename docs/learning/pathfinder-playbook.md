# Introduce AI-native development through a pathfinder

Start with one useful product journey and leave another engineer able to repeat the
work without its original author. That is a more useful first result than installing
every factory service or reporting how many lines an agent wrote.

This is an adoption proposal informed by the
[implementation lessons](lessons.md) and [external research](industry-comparison.md),
not a claim that GuardKit has already been validated for your organisation.

## Choose the smallest useful starting point

| Starting situation | First experiment | Evidence to retain |
|---|---|---|
| Developers already use assistants, with inconsistent outcomes | One attended harness workflow with explicit acceptance examples | Request, decisions, diff, executed checks, human review time |
| Plans are stable but implementation requires repeated manual steering | A bounded standalone AutoBuild task | All turns, failure reasons, final candidate and independent checks |
| Repeated work has stable project commands and delivery controls | A factory trial on an isolated project | End-to-end request, approvals, candidate identity and delivery result |
| A prototype has been approved | Freeze its version and describe real behaviour, data and identity requirements | Visual reference, product contract and explicit prototype limitations |

The last row is transferable practice. Automated private prototype-to-factory intake
is still in progress in the [current GuardKit snapshot](../software-factory/evidence-and-limits.md).

## Agree the question before selecting the tool

Write one sentence such as: “Can an engineer unfamiliar with this service deliver a
small, reversible change with less review effort and no loss of independently checked
behaviour?” Choose the comparison, observation window and stopping conditions before
running it. Use the [experiment record](field-kit.md#experiment-record).

Choose a slice with an observable result, representative dependencies and a useful
failure case. A browser change that really reaches an API and database teaches more
about delivery than a polished static page, if that connected journey is the team's
actual problem. An agent product needs decision and task-completion checks in addition
to API or browser tests.

## Prepare the repository as a shared working environment

Give humans and agents the same short project map: purpose, architecture, local setup,
supported commands, important constraints and links to detailed decisions. Keep
instructions concise; connect them to checks wherever possible.

Make a clean checkout reproducible. Identify the commands that install dependencies,
build, test, start services, seed synthetic data and clean up. Record existing failures
before the first experiment. Do not let an agent quietly redefine a pre-existing
failure as success, or spend the entire trial repairing unrelated baseline problems.

For each acceptance example, name its verifier and its owner. Explain how failures
reach the final decision. [Project readiness](../software-factory/project-readiness.md)
shows how this maps to the factory, but these practices also work in an ordinary CI
pipeline.

## Work through four stages

These are suggested stages, not mandatory approval ceremonies or fixed calendar weeks.
For a month-long engagement, they can provide a weekly rhythm; adjust to the product
and the organisation's existing delivery process.

| Stage | Work | Leave behind |
|---|---|---|
| Establish the baseline | Observe the current workflow and run one representative change | Current lead time, review effort, failure categories and a reproducible environment |
| Run an attended slice | Pair a developer with the harness; keep assumptions and repairs visible | Feature contract, real checks and a short worked example |
| Repeat and challenge | Have a second engineer repeat it; inject a known defect in an isolated test | Evidence of what the checks catch, what they miss and what still needs judgement |
| Transfer and decide | Receiving team operates the flow and teaches it back | Owned runbook, decision record, measured comparison and next experiment |

The same engineer should not be the only person who can interpret every failure. Keep
an implementation owner, a reviewer and a receiving engineer visible, using existing
team roles. The receiving engineer should run the workflow before the engagement ends.

## Measure outcomes with fair denominators

Track every admitted request, including failures, rejections and cancelled runs.
Separate “build completed”, “independently checked”, “approved”, “published” and
“running”. A deliberate decline at the merge card is useful test evidence but is not
a deployment.

| Measure | Definition to agree | Why it helps |
|---|---|---|
| Acceptance-check completion | Independently accepted results / all eligible attempts | Avoids reporting only successful demonstrations |
| Lead time | Request ready to accepted result, including queues and human waiting | Captures the workflow rather than token speed |
| Human effort | Minutes preparing, steering, reviewing and repairing | Detects work merely moved from coding to supervision |
| First-pass acceptance | Accepted without implementation repair / eligible attempts | Shows rework burden |
| Escaped defects | Issues found after acceptance, over an agreed observation period | Tests the quality of the acceptance process |
| Cost per accepted result | Inference + execution + human cost at a declared rate, divided by accepted results | Avoids equating free local API calls with free delivery |
| Transfer success | A second engineer can run, diagnose and explain a fresh task | Measures knowledge transfer directly |

For a model or harness comparison, hold the starting commit, task, acceptance checks
and resource budget constant. Record changed plans, prior task exposure and tool
differences. With a small sample, report the individual results and uncertainty rather
than implying a stable organisation-wide productivity percentage.

## Transfer knowledge continuously

After each meaningful success or failure, capture one short lesson: trigger, observed
behaviour, cause supported by evidence, change, result and remaining limit. Link the
lesson from the command or runbook the next engineer will actually use.

Use three practical sessions:

1. **Walkthrough:** trace a feature from request to delivered behaviour with the
   [C4 and sequence diagrams](../software-factory/architecture.md).
2. **Failure workshop:** let the receiving engineer diagnose a deliberately wrong
   candidate and explain which evidence stops it.
3. **Teach-back:** let that engineer run a fresh task and explain the method to another
   team without the original facilitator driving the terminal.

Retain reusable ideas in team-owned documentation. Keep client-specific code, data
and decisions in the organisation's systems; use synthetic examples for public
presentations. This makes the method portable without turning a public case study
into the team's operational record.

## Decide what to scale

Scale the part that improved the measured outcome. That may be better project
instructions, a reliable test environment, independent review or automated intake.
It does not have to be the entire factory.

Before extending autonomy, demonstrate bounded execution, a clear authority to merge,
recovery from interruption and evidence for the exact candidate. Reuse the
organisation's existing repository permissions, CI and release process. The
[field kit](field-kit.md) provides compact records for the receiving team to own.
