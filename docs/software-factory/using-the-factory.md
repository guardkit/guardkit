# Using the factory

Use the factory when you want a registered repository's feature to proceed through planning, building and a human merge decision. Use [GuardKit in a coding harness](../harness/index.md) when you want to drive that work interactively.

*Reviewed 17 October 2026. The examples describe the existing Slack intake and prepared-build contracts. They assume an operator has configured the factory and your account is authorised for its planning channel. This is not a one-command installation guide.*

## Before you send work

You need an exact registered repository key, a clear feature request or committed plan, and someone who owns the decisions. The repository needs a working test command and the [project declarations](project-readiness.md) the factory uses.

The factory currently demonstrates public-project execution. Private repository reading and prototype intake were still being implemented at this review date. An ability to access a repository from your laptop does not imply that the factory's sandbox can access it.

The current production workflow can be driven through Slack or an operator's automation. Both ultimately reach Forge. A local `guardkit autobuild` invocation is a separate route: it does not automatically create a factory intake, approval cards or publication record.

## Send one feature as a sentence

In the configured planning channel, an authorised user can post a top-level message such as:

```text
target: example-org/notes-app
Show the total number of notes above the list, including zero when there are
no notes. Update the number after creating or deleting a note, without a
page reload. Preserve the existing sign-in and note permissions.
```

Replace `example-org/notes-app` with the exact key your operator registered. The example is illustrative; it is not a bundled demo project.

The first `target:` line selects the repository. Jarvis strips that line and forwards the request with its correlation information. Forge resolves the name and refuses an unknown repository. Jarvis does not decide whether your request is a good idea and does not generate the plan on this route. The syntax and routing are implemented in [Slack planning intake](https://github.com/guardkit/jarvis/blob/2da5153e7c1cbc802f6d9c4d2f39c18a8245275e/src/jarvis/infrastructure/slack_planning_intake.py).

A useful request names the behaviour, an observable example, important failure cases and constraints. Avoid prescribing a file to create unless that is itself the requirement. Let the planner inspect the existing structure; duplicating an existing module is not a useful feature.

For a larger idea, split the work into independently assessable features. The current sentence route turns one request into one feature. It is not evidence of automatic portfolio planning or dependable decomposition of an entire application.

## Read the specification card

Check whether the digest says what you meant. Pay attention to assumptions, examples, exclusions and any unanswered sign-in or environment question. An example should describe behaviour a test or a person can actually observe.

If the specification is wrong, ask for a revision in the card's supported response. Do this before the task plan becomes build input. “The agent understood my sentence” is not a useful substitute for reading the behaviour it proposed.

Approve when the result is specific enough to assess. The specification approval records product intent; it does not certify implementation quality.

## Authorise the build

After planning, the factory asks before starting the build. The current pre-dispatch gate is deliberately human: the implementation returns mandatory human approval because there is no automatic score at that stage. Retrieved prior outcomes can provide context without making the decision automatic. See the [gate implementation](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/gating/degraded.py).

The factory then runs GuardKit AutoBuild in its configured execution environment. You can follow progress, but a progress message is not a delivery receipt. Keep the feature and build identifiers when reporting a problem.

## Review the merge offer

Read the result, test evidence and any limitations. If the project supplies a web preview, try the behaviour you requested. Check whether the preview is ready or expired; an old screenshot is not proof that the currently offered application is running.

Approving the card authorises the described merge. The factory still checks the integrated result and can refuse the action if its identity or evidence no longer holds. Publication and deployment are separate outcomes, and the final report should say which occurred.

The normal factory surface uses a merge card. A code label such as `pull-request-review` in older material does not mean that this route opens a GitHub pull request. See [delivery flow](delivery-flow.md) for the exact distinction.

## Send an already-planned feature

You can plan in a coding harness and hand the resulting bundle to the factory. Commit and push all of its required files on a branch first. The current Slack grammar is:

```text
target: example-org/notes-app
build: FEAT-1234 from feature/note-count
```

This syntax is present in the inspected Jarvis and Forge source. Its availability still depends on the versions your operator deployed; consult the [source register](sources.md) rather than an older handoff that calls it planned work.

Prepared admission fetches the branch, records its exact commit, and checks the supplied feature bundle without asking a model to replan it. The branch name is a way to locate the source at admission; it is not a moving promise to build whatever appears on that branch later.

The bundle includes the feature plan under `.guardkit/features/`, task files, referenced specification files, the implementation guide, applicable QA files and binding project documents. Missing committed inputs are refused. Relative document links must resolve to ordinary committed files; a file that exists only in your working directory is not part of the bundle. See [prepared admission](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/pipeline/prepared_admission.py).

Prepared intake skips factory replanning, not factory controls. It still needs repository admission, the build-start decision, checks and the human merge decision.

## Operator automation and card policies

An operator may drive a run using the project's factory-feature-build workflow. That workflow wraps the ordinary intake and card path; it is not a second implementation engine.

| Policy | What the driver may answer | Appropriate use |
| --- | --- | --- |
| `stop-at-merge` | Planning and build-start cards for this feature; leaves merge and repair decisions to the owner | Normal product work with final review |
| `decline-merge` | Planning/build-start cards, then rejects this run's merge and repair cards | Evaluation runs that must not publish |
| `full` | All authorised decisions for this specific run, including merge | Only when the owner has explicitly delegated that delivery |

These are automation policies, not a relaxation of the publisher's checks. A driver answering a human gate must have actual authority for that answer; an unattended flag is not authority by itself.

Deployment-specific driver commands and secret-loading procedures belong in the operator runbook. They are deliberately not reproduced as a portable public quickstart: copying them would hide the registration and runtime prerequisites.

## When the result is not a delivery

| Outcome | What to do |
| --- | --- |
| Unknown repository or missing declaration | Correct registration or the committed project contract |
| Specification does not match the request | Revise at the specification checkpoint |
| Planning cannot produce an acceptable plan | Preserve the failure reason; refine the request or repair the planner |
| Build fails | Read the failure evidence and any bounded repair offer |
| Preview expired or unavailable | Use the supported rebuild action and reassess readiness |
| Merge refused because the target moved | Obtain evidence for the new integrated result; do not assume the old approval carries over |
| Publication succeeds but deployment fails | Report both facts and investigate the deployment stage |
| “Nothing to build” | Review the cited proof; this is an existing-behaviour outcome, not a newly delivered feature |

The last outcome is configuration-dependent. The factory must be able to substantiate it against existing code and tests; feature text resembling existing code is not sufficient by itself.

## Keep a useful run record

Record the original request, repository, admitted revision, feature/build IDs, decisions, test evidence, candidate identity and actual publication/deployment outcome. Also record intervention time and what went wrong. That produces stronger [teaching material](../learning/presentation-kit.md) than a successful terminal screenshot alone.
