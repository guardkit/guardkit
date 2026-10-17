# What other software factories teach us

Research checked **17 October 2026**. This is a comparison of published approaches and the evidence behind them, not a ranking of products. Internal GuardKit and Factory claims belong in [Evidence and limits](../software-factory/evidence-and-limits.md); this page provides the external reference points.

The useful question is: **which controls make an agent's work easier to specify, verify, operate and transfer to another team?** A system that writes more code, uses more agents or removes more human review is not automatically better at delivering a dependable product.

## Compare the same layer

For this documentation, distinguish three layers:

| Layer | Responsibility | What to compare |
| --- | --- | --- |
| Coding harness | Runs the model, tools and development interaction | Context, tool access, editing, tests and session continuity |
| Build orchestration | Coordinates a specified unit of work across runs | Task state, workspace isolation, retries, validation and evidence |
| Delivery operating system | Connects demand, teams, repositories and release decisions | Ownership, prioritisation, approvals, rollout, operational outcomes and learning |

These are working definitions, not an industry standard. A coding assistant, a background PR producer and a factory for a portfolio of services solve overlapping but different problems. Keep that distinction when comparing GuardKit in an interactive harness with AutoBuild invoked by the Software Factory.

## Published approaches

### Stripe Minions: unattended implementation with human review

Stripe describes a run that starts from a request, works in an isolated development environment and produces a PR for human review. Its February 2026 account emphasises reuse of existing developer tooling, contextual repository rules and curated tools. This is a useful example of separating the person specifying work from the agent doing the implementation. [Stripe, 9 February 2026](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents).

Its follow-up describes **blueprints**: workflows combining deterministic operations with agent decisions. Linting and publishing steps need not depend on model discretion. Feedback is bounded rather than retried indefinitely. Stripe reports more than 1,300 fully minion-produced PRs merged each week, explicitly **human reviewed**. That is a reported production volume, not a published success rate or proof of autonomous merging. [Stripe, 19 February 2026](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2).

**What to learn:** make mandatory steps executable, budget retries, and distinguish implementation authority from merge authority. The transferable idea is the control structure; another team does not need Stripe's infrastructure scale to apply it.

### StrongDM: behaviour-based acceptance and simulated dependencies

StrongDM's AI team describes non-interactive development driven by specifications and scenarios, with no human-written or human-reviewed code. It places some scenarios outside the implementation repository and uses behavioural replicas of external services to exercise interactions at scale. Its acceptance concept includes empirical user satisfaction across scenario runs. [StrongDM, 6 February 2026](https://factory.strongdm.ai/).

This is a stronger published emphasis on independent behavioural acceptance than a green unit-test suite alone. It is an author-reported method, however, not an independent comparison of defect rates, total cost or suitability for every enterprise. The article does not establish that removing code review is generally optimal, or that a simulated service captures every live-system behaviour.

**What to learn:** protect acceptance criteria from the implementation loop and test important external behaviours reproducibly. Begin with one difficult integration; a complete digital-twin environment is an investment to justify, not a prerequisite for calling a system a factory.

### Spotify Honk: platform integration and explicit verification

Spotify describes independent verifiers that return focused feedback and must pass before a PR is opened. A further model judge checks the proposed diff against the request. In the December 2025 account, Spotify explicitly says it had not yet invested in formal evaluations of that judge. A second model's opinion is therefore a useful check, but its existence alone does not establish measured reviewer accuracy. [Spotify, 9 December 2025](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3).

The April 2026 migration case is especially instructive: uneven conventions made one framework too difficult to automate in that project; incomplete context produced wrong mappings; absent build-time tests meant owners still needed to validate manually. The team reported 240 migration PRs. This is evidence of both capability and limits, rather than a claim that all migrations became autonomous. [Spotify, 22 April 2026](https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4).

A later account describes Kubernetes execution, CI builds across operating systems and fleet-level progress tracking. It also reports 76% more PRs to review. Its 2.5 million automated maintenance PRs refer to the broader Fleet Management history, **not all to Honk or LLM-generated changes**. [Spotify, 3 June 2026](https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint).

**What to learn:** platform consistency, validation and review capacity can constrain adoption more than code generation. Compare the integration and verification mechanisms, and retain the failures when teaching the story.

### GitHub Agentic Workflows: separate proposals from privileged actions

GitHub documents a mechanism in which the agent runs with read-only GitHub permissions and requests structured outputs; separate jobs with controlled permissions perform allowed writes. This makes the boundary between generating a proposal and applying an external effect explicit. The configuration still matters: this is a documented control pattern, not a guarantee that any workflow written with the tool is safe. [GitHub Safe Outputs, living documentation accessed 17 October 2026](https://github.github.io/gh-aw/reference/safe-outputs/).

GitHub's dated announcement records a move to public preview on 11 June 2026. Treat that as the status at that announcement, not an assertion about every account's availability today. [GitHub changelog, 11 June 2026](https://github.blog/changelog/2026-06-11-github-agentic-workflows-is-now-in-public-preview/).

**What to learn:** enforce authority in the system that executes actions. Prompt instructions and an approval screen are insufficient evidence that credentials, branches and external writes are actually constrained.

### Anthropic and OpenAI: the harness and its evidence need engineering

Anthropic's long-running agent example uses an initial setup phase, a feature inventory, incremental implementation, Git history, progress records and end-to-end checks. It is a concrete pattern for continuity across sessions. The authors describe a web-application experiment and acknowledge open questions about generalisation and single-agent versus multi-agent design. [Anthropic, 26 November 2025](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

Anthropic's evaluation guidance distinguishes the agent's transcript from the resulting environment state, recommends repeated trials, and combines deterministic, model and human grading. It argues for calibration rather than taking an evaluator's output at face value. [Anthropic, 9 January 2026](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

OpenAI's workflow cookbook separates goals, plans, execution prompts, phase records and evidence. It explicitly presents the extra files as optional conventions, not product requirements. This is guidance for making work inspectable and repeatable, rather than evidence of enterprise delivery performance. [OpenAI, 3 August 2026](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex).

**What to learn:** durable artefacts matter more than agent names. A reviewer should be able to establish what was requested, what ran, what changed and what was verified without replaying the whole conversation.

## What changed during this research period?

Sources are snapshots. For example, the Spotify December 2025 account lists wider operating-system support as future work; the June 2026 account describes CI verification across operating systems. Do not preserve an old limitation as a present-tense product fact. The two dated accounts above establish the progression, not the completeness of support for every stack.

Spotify's **8 October 2026** announcement brings Portal, Xirp and Confidence together under Spotify Technology and describes a connected context, development and experimentation cycle. This is useful evidence of product direction; the announcement does not by itself establish the performance of that combined system in another organisation. [Spotify Technology announcement](https://engineering.atspotify.com/2026/10/introducing-spotify-technology-proven-at-spotify-now-yours).

## Where GuardKit and the Factory should be challenged

The external examples have more developed public accounts in several areas. The table turns those into concrete evaluation questions. It does not assert that an internal capability is absent merely because it was not found in this research; use the [implementation evidence and limitations](../software-factory/evidence-and-limits.md) to establish the current position.

| Comparison axis | Strong external reference | Evidence to require from GuardKit / a pathfinder |
| --- | --- | --- |
| Repeatable execution environments | Stripe's provisioned devboxes | A clean environment can reproduce the same build; code separation and credential isolation are demonstrated separately |
| Independent acceptance | StrongDM's scenarios and simulated dependencies | Acceptance checks exercise externally visible behaviour and cannot silently change with the implementation |
| Verification infrastructure | Spotify's stack-aware verifiers | Failed builds, failing tests and unsupported stacks produce distinct outcomes; completion is blocked when required evidence is missing |
| Authority boundaries | GitHub's separate write jobs | Only permitted operations execute, against the intended repository and candidate; denials and retries are recorded |
| Reviewer reliability | Anthropic's evaluation guidance | A labelled set of good and bad candidates, false accept/reject analysis, and recorded results after reviewer changes |
| Fleet operations | Spotify's migration tooling | Ownership, dependency scope, rollout progress, failure triage and review backlog remain visible across repositories |
| Session continuity | Anthropic and OpenAI harness examples | Another engineer can resume from durable records and reproduce the evidence without the original operator |

These are meaningful potential gaps: they affect reproducibility, release confidence and transferability. They are more useful than asking whether GuardKit uses the same number of agents or achieves the same PR volume as a much larger organisation.

Do not infer that a different-model reviewer is independent in the statistical sense. Treat that as a hypothesis to evaluate on local defects and acceptance cases. Likewise, a Git worktree proves separate working files; it does not by itself prove process, network or credential isolation.

## Measure value without borrowing someone else's headline

DORA's 2025 research describes AI as amplifying an organisation's existing strengths and weaknesses. Its companion capability model directs attention to the surrounding delivery system. These are useful organisational reference points, not a causal estimate of the benefit this Factory will deliver on a particular project. [DORA 2025 report](https://dora.dev/research/2025/dora-report/), [capability model, updated 25 November 2025](https://dora.dev/ai/capabilities-model/report/).

METR's February 2026 follow-up explains why selection effects and concurrent-agent working made its later developer productivity estimates difficult to interpret. It cautions against treating either its early-2025 slowdown or later raw results as a universal current effect. Its May survey measures **self-reported** productivity, a different form of evidence from observed task performance. [METR, 24 February 2026](https://metr.org/blog/2026-02-24-uplift-update/), [METR, 11 May 2026](https://metr.org/blog/2026-05-11-ai-usage-survey/).

For a pathfinder, use a balanced measurement record. The following is a proposed local evaluation design, not an industry benchmark:

| Measure | Record | Why it matters |
| --- | --- | --- |
| Delivery time | Request-to-accepted-change time, including review and waiting | Faster generation can coexist with a growing review queue |
| Human effort | Specification, intervention, review, repair and release effort | Background execution does not eliminate surrounding work |
| Successful outcomes | Accepted outcomes divided by all attempted tasks, by task class | Include failures and abandoned runs in the denominator |
| Reliability | Escaped defects, rollbacks, reopened work and operational impact | Passing an agent's checks is an intermediate result |
| Cost | Model, compute, platform and human costs per accepted outcome | Token consumption and PR counts alone do not measure value |
| Transferability | Time and help needed for a second team to reproduce a task | A pathfinder should create an organisational capability |
| User value | A task-specific product or operational outcome | More delivered changes need not mean a better product |

Keep model, harness, prompt, policy, repository revision and environment versions with each result. Compare similar task classes; separate migration work from new features. Report sample size and uncertainty. Use medians and a tail measure where useful, and distinguish wall-clock duration from active human effort when agents run concurrently.

## A practical adoption sequence

This sequence is our synthesis of the examples, intended for a team establishing its own evidence:

1. **Choose a bounded problem.** Define the user-visible outcome, allowed scope, owner and acceptance checks before adding orchestration.
2. **Make the repository reproducible.** Establish a known build command, representative test data and clear local conventions.
3. **Establish a baseline.** Capture existing delivery time, quality and review effort on comparable tasks.
4. **Delegate implementation.** Preserve an explicit human release decision while evaluating the system; record every attempted run.
5. **Separate mandatory controls from model judgment.** Enforce identity, validation, budgets and writes through executable mechanisms.
6. **Convert failures into durable knowledge.** Add regression cases, improve context and record the reason for policy changes.
7. **Transfer to another team.** Have someone outside the pathfinder run the workflow and explain its evidence. Use the friction they encounter to improve the package.
8. **Expand autonomy selectively.** Change one boundary at a time after local evidence supports it. More autonomy is a design choice, not a maturity score.

## Using this material in a presentation

A useful narrative is: **a factory makes delegated work observable and governable; it does not make uncertainty disappear.** Show the same feature at three levels: an engineer working in a harness, the Factory dispatching a build, and the organisation deciding whether the result is acceptable.

For comparisons, put the source date and evidence type on the slide. Use one concrete mechanism and one limitation from each example. Avoid presenting reported PR totals as quality scores, product announcements as measured outcomes, or experimental policies as universal best practice.

All linked sources were accessed on **17 October 2026**. Company engineering posts describe their authors' systems; vendor guides explain recommended mechanisms; announcements establish dated product statements; research studies apply within their methods and populations. None of these sources supplies a controlled comparison with GuardKit.
