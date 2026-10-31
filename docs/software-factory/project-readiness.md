# Prepare a project for the factory

A factory can automate a delivery process only when the project makes that process explicit. Start by making the repository buildable, testable and understandable without knowledge held only by its original author.

*Reviewed 17 October 2026. This page separates the current registration contract from recommendations for a team adopting the approach. Use the [pathfinder playbook](../learning/pathfinder-playbook.md) for rollout and measurement.*

## What current registration checks

`forge register-repo` reads the project's committed default branch and checks three essentials: a declared memory project, a test command and any declared binding documents. It prepares the factory's configuration and sandbox clone. It does not author missing product files for you.

An illustrative `.guardkit/config.yaml` is:

```yaml
memory:
  project: notes_app

toolchain:
  test: "./scripts/test.sh"

autobuild:
  player:
    required_documents:
      - docs/product-contract.md
      - docs/architecture.md
      - docs/testing.md
```

The names and command are examples. Every declared file must exist as an ordinary committed file, and the test command must be the command your project actually supports. A memory project name uses letters, digits and underscores; inventing a name does not set up a separate security boundary.

The implementation and refusal messages are in [repository registration](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/cli/register_repo.py). For richer toolchain declarations, use the project's supported GuardKit configuration rather than assuming this minimal illustration describes every language or build system.

GuardKit runs only declared commands; a project of several parts declares each one (`components:` or `parts:` patterns, see [AutoBuild verification](../deep-dives/autobuild-architecture.md#what-the-executable-evidence-proves)). The `toolchain.test` command is verdict-bearing by default. Merely listing `lint`,
`typecheck` or `build` does not enforce those commands as gates; bind them through
the supported conformance checks. See [AutoBuild verification](../deep-dives/autobuild-architecture.md#what-the-executable-evidence-proves).

## Make the build reproducible first

Before registering, prove that a clean checkout can install dependencies, run the declared tests and start any required supporting services. Commit lockfiles where the toolchain expects them. State required runtime versions, environment variable names and external service dependencies.

Do not make a passing check depend on a developer's untracked file, pre-existing database, globally installed package or active login. Such assumptions become expensive when the factory creates a fresh worktree or verifies an integration result in another folder.

Test reporting should distinguish passed, failed, skipped and not run. “No tests collected” is not equivalent to “all behaviour verified.” For a web project, a backend unit suite alone does not establish that a signed-in browser journey works.

## Write a small binding contract

The best input is a compact, maintained account of decisions that a builder must preserve. Useful documents answer:

| Topic | Example information |
| --- | --- |
| Product behaviour | User roles, outcomes, exclusions and concrete examples |
| Architecture | Component boundaries, data ownership, external interfaces and important ADRs |
| Testing | Test commands, fixtures, critical journeys and expected failure behaviour |
| Security assumptions | Where authentication and authorisation happen; what data must stay private |
| Operations | Startup, deployment, health checks, rollback expectations and configuration names |

Keep the instructions close to the code and review changes to them deliberately. A task should not redefine a product invariant merely because doing so makes its test pass.

Forge reads declared documents at the recorded start commit. Its document reader has a total context budget; the Player has its own required-document limits and read enforcement. Listing an entire documentation tree does not ensure that every role receives every word. See [project document loading](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/planning/project_documents.py) and [Player configuration](https://github.com/guardkit/guardkitfactory/blob/40615a7e0ff6952b5a5492ada0d3a66dc10c8533/src/guardkitfactory/harness/player_config.py).

A practical pattern is a concise contract that links to detail. Check which linked files the relevant route actually loads; a Markdown link is not automatically retrieval.

## Declare environment needs without committing secrets

Where the project needs additional launch settings, declarations name them. Values come from the launching environment under the factory's rules:

```yaml
launch:
  settings:
    - APP_ENV
```

The declaration is not permission to export arbitrary control-service credentials into the builder. Reserved names and malformed declarations are refused. In the current deployment, factory model and memory credentials stay outside the product sandbox behind restricted access routes. Project-owned application secrets need their own deliberate handling.

The [declaration reader](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/planning/declared_memory.py) reads names and project settings at the admitted commit, rather than trusting whatever a working copy contains later.

## Add delivery evidence that matches the product

A deployable project needs a project-specific deployment profile and meaningful live checks. A web project can also supply a preview profile, browser journey, screenshots, recording and report locations. The factory coordinates those capabilities; it cannot infer every application's correct startup or authentication flow.

Evidence should demonstrate the requested behaviour and its relevant boundaries. For example, a note-count change needs the zero state, creation/deletion updates and preservation of user permissions. A single screenshot of a number is weaker evidence than an exercised journey with an identified source tree.

Keep control over the commands used to judge a change. The current delivery machinery has protections around specification and approval changes, and its merge checks account for changes to judge files. These controls are reasons to define trusted checks explicitly, not reasons to assume arbitrary generated tests are independent verification.

## Registration is an operator action

On a configured factory installation, an operator can inspect readiness using:

```bash
forge register-repo example-org/notes-app \
  --github https://github.com/example-org/notes-app.git \
  --dry-run
```

The repository is illustrative and must be replaced. The command needs the estate configuration and tools expected by that deployment; running it in a product's ordinary development environment is not sufficient.

Without `--dry-run`, registration prepares staged configuration and the factory clone, and prints the activation sequence. It does not restart the running services itself. Adding a publisher route and its credential is a separate explicit operator choice.

The current deployed admission policy requires a registered sandbox route for product builds. Forge's compatibility defaults can permit other execution paths in other installations, so confirm the effective policy rather than treating a code-level default as a safety guarantee. See [build admission](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/config/build_admission.py).

## Private projects and prototype inputs

As of 17 October, private repository reading and signed-off prototype intake are accepted design work with implementation in progress. They are not a completed onboarding path documented by this page.

The intended prototype model is useful as a design principle: keep the prototype and production repositories separate; record the exact version that a client approved; give builders an immutable reference; treat later approved changes as new feature work. Prototype code can convey layout and interaction, but mock data or pretend authentication must not become production behaviour by accident.

The unresolved confidentiality requirement is broader: a shared sandbox and shared memory service can allow content to cross project boundaries. A project-tagged memory namespace is not sufficient proof of tenant isolation. Follow [evidence and limits](evidence-and-limits.md) before adopting this deployment for confidential client work.

## A pathfinder team's first readiness review

Use a small real feature to establish evidence in five areas:

1. **Intent:** a reviewer can explain the approved behaviour and its non-goals.
2. **Reproduction:** a fresh environment can run the declared build and tests.
3. **Verification:** a check independent of the implementation's narrative can catch a realistic failure.
4. **Authority:** the team can name who may change requirements, approve publication and release the runtime.
5. **Learning:** the run records its source, result, intervention and failure modes in a form another team can reuse.

These are recommended adoption criteria, not claims that passing registration proves all five. Keep the pilot narrow enough that a human can inspect the outcome and compare it with an ordinary delivery baseline. Expand autonomy when repeated evidence supports it.

Use the [lessons](../learning/lessons.md) to turn surprises into revised checks and documentation. That is how the pathfinder becomes a knowledge-transfer programme instead of a one-off demonstration.
