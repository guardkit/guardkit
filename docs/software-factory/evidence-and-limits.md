# Evidence and current limitations

**Snapshot: 17 October 2026.** The factory has useful working mechanisms and recorded
deliveries. It is still developing. This page distinguishes source inspection from
operator-reported runs and future work, so a demonstration does not become an
unsupported claim of general reliability.

The [source register](sources.md) identifies the revisions and evidence classes. This
documentation refresh inspected source and existing records; it did not rerun the
factory or independently reproduce the historical trials.

## What each result establishes

| Result | What it establishes | What it does not establish |
|---|---|---|
| Source implementation | A mechanism exists at a named revision | It is enabled, configured or working in a particular deployment |
| Passing component tests | The tested component met those checks | The real caller supplies the right input or the product works end to end |
| AutoBuild completion | The build loop reached its completion condition | Human acceptance, publication or deployment |
| Review-ready candidate | A specific change and available evidence can be reviewed | That it remains valid after the target branch moves |
| Approved merge decision | The authorised reviewer accepted that proposal | The merge, publish and deploy operations subsequently succeeded |
| Published and running | The delivery path recorded publication and runtime success | Long-term reliability, comprehensive security or every user journey |
| Declined-merge trial | The run reached its defined pre-merge endpoint | Any deployed product outcome |

## Implemented mechanisms

At the inspected revisions, the factory includes deterministic Slack intake, persistent
planning/build state, specification and build decisions, prepared-feature admission,
bounded AutoBuild, independent evidence gathering, candidate review previews, merge
verification and a separate publisher. These mechanisms are explained in
[architecture](architecture.md) and [delivery flow](delivery-flow.md), with source links.

The build environment and publisher have different authority. Model and memory access
go through narrow service boundaries. This is more than a prompt asking the agent to
behave, but it is not proof of complete isolation between every workload.

## Recorded operational evidence

These are **operator-reported observations** from the maintained operating record and
trial results, summarised for public teaching. The underlying runtime logs and private
infrastructure details are not published here. They are not independently reproduced
benchmarks. See the [operational source note](sources.md#operational-records).

| Observation date | Recorded result | Scope and limit |
|---|---|---|
| 15 October 2026 | A web-fixture fix reached a preview card, was approved, verified with the target's judge file, published and reported running | One connected fixture delivery; cleanup defects were found afterwards and repaired |
| 15 October 2026 | Two non-overlapping changes could merge cleanly in Git, but the second approval was refused because the joined tree differed from its preview | Exercises stale-preview refusal separately from an ordinary merge conflict |
| 16 October 2026 | A Slack preview expired, the card updated, the operator rebuilt the same candidate and approved it; preview, candidate and merged tree matched | One live lifecycle proof; environment configuration was repaired during the session |
| 16 October 2026 | A six-request local-model trial built 6/6; merges were declined; at most four builds ran simultaneously | Small fixture cohort, not six simultaneous completed builds or deployed outcomes |
| 16 October 2026, later follow-up | With the configured build limit raised to six, an eight-request run built 5/8 and observed at most four builds at once | Two planning output-format failures and one verification-only-task refusal; planning constrained progress |
| 17 October 2026 | Dashboard evaluation found a live ledger feed alongside sample pages, incorrect delivery labels and missing cost reporting | A live data connection does not make the dashboard's metrics trustworthy |

The follow-up must stay beside the successful six-request trial when teaching the
capacity story. These observations do not establish a stable success rate, a fair
model ranking or an accepted-feature throughput benchmark. The capacity record has
a heading dated 17 October but describes a run on 16 October; the table uses the event
date supported by its body.

## Current gaps

| Area | Current position at this snapshot | What would close the evidence gap? |
|---|---|---|
| Private-repository intake | The inspected sandbox fetch path supports public HTTPS repositories without credentials; a private Git access design is being implemented | A complete private-repository build and publication proof with the chosen authority boundary |
| Approved prototype handover | Versioned prototype references and change-to-feature intake are being developed | Trace one approved reference through planning, implementation and acceptance without treating mock behaviour as production |
| Isolation between clients/projects | Shared sandbox and memory boundaries are not evidence of tenant isolation; gate-prior retrieval uses a static configured project scope | Deliberate cross-project access tests and a documented isolation model |
| Shell isolation | The Player's file-tool confinement is not an OS sandbox; standalone shell execution requires an appropriate surrounding environment | Verify process, filesystem, network and credential boundaries in the actual deployment |
| Language and stack breadth | Generic project declarations and multiple templates exist; recent connected readiness proof is a React/Go web fixture | Equivalent runtime and delivery evidence for other stacks; Rust template availability alone does not prove factory runtime support |
| Planning reliability | Malformed output and task-admission refusals still occurred in recent trials | Representative task cohorts, recorded failures and repeatable admission/planning outcomes |
| Reviewer reliability | Separate roles and deterministic checks are useful controls; this snapshot supplies no calibrated general false-accept/false-reject rate | A labelled good/bad candidate set, repeated trials and analysis of reviewer errors |
| Recovery | Durable state and preview lifecycle handling exist; the preview implementation documents a restart window during preparation that can leave no merge card | A demonstrated supported recovery for that window; do not edit the ledger to simulate success |
| Operations and metrics | Dashboard data reconciliation, cost attribution and useful stage timing remain incomplete | Reconcile reports against source records, include failures and define time/cost denominators |
| Portable onboarding | Factory operation depends on several services, project declarations and environment configuration | A fresh receiving team reproduces setup, one successful task and one failure/recovery case |

These are priorities for improvement, not arguments for discarding the working
controls. The [industry comparison](../learning/industry-comparison.md) identifies
stronger published practices in acceptance, platform integration, evaluation and
operations, without claiming a controlled head-to-head result.

## How to make a fair public claim

Keep the revision, environment, task scope, denominator and stopping point with the
result. Say “built 6 of 6 fixture requests, with merges declined” rather than “delivered
six production features”. Say “the configured limit is six” separately from the
observed active-build count. A proposed workflow belongs under future work until its
real caller and consumer have been exercised.

Use the [presentation evidence card](../learning/field-kit.md#a-presentation-evidence-card)
and the [pathfinder measurement plan](../learning/pathfinder-playbook.md#measure-outcomes-with-fair-denominators)
to carry these distinctions into talks and team adoption.
