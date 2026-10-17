# Sources and documentation maintenance

The refreshed harness, factory and learning pages describe a **17 October 2026**
snapshot. Implementation claims are tied to committed source. Operational observations
are identified separately, and external comparisons link directly to their publishers.

## Source revisions inspected

| Repository | Revision | What was checked |
|---|---|---|
| [GuardKit](https://github.com/guardkit/guardkit/tree/23d99208598706f81f43a21628f5dcfb89d92a55) | `23d99208` | Installer, commands, CLI, harness selection, AutoBuild and project verification |
| [Forge](https://github.com/guardkit/forge/tree/bec134d36a247008a3c64503c865d67268651a88) | `bec134d3` | Intake, planning, approvals, prepared admission, sandbox, previews, merge and publisher |
| [Jarvis](https://github.com/guardkit/jarvis/tree/2da5153e7c1cbc802f6d9c4d2f39c18a8245275e) | `2da5153e` | Deterministic Slack intake and approval/evidence presentation |
| [guardkitfactory](https://github.com/guardkit/guardkitfactory/tree/40615a7e0ff6952b5a5492ada0d3a66dc10c8533) | `40615a7e` | Player/Coach harness implementation and execution boundaries |

Planning-service source was also inspected. That repository is private, so this site
describes its role and the public Forge integration rather than publishing private
source or inaccessible code links. Local uncommitted changes and concurrent feature
branches are not evidence for this snapshot.

## Where to verify a claim

| Question | Primary implementation reference |
|---|---|
| Which harness does AutoBuild select? | [GuardKit harness selector](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/orchestrator/harness/selector.py) |
| What CLI operations exist? | [AutoBuild CLI](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/autobuild.py) and [command specifications](https://github.com/guardkit/guardkit/tree/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/commands) |
| Does Jarvis reason about routine factory intake? | [Slack planning intake](https://github.com/guardkit/jarvis/blob/2da5153e7c1cbc802f6d9c4d2f39c18a8245275e/src/jarvis/infrastructure/slack_planning_intake.py) |
| How is already-planned work admitted? | [Prepared admission](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/pipeline/prepared_admission.py) |
| How are project documents bound to a revision? | [Planning project documents](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/planning/project_documents.py) |
| What enforces project registration? | [Register-repo command](https://github.com/guardkit/forge/blob/bec134d36a247008a3c64503c865d67268651a88/src/forge/cli/register_repo.py) |
| Where do the delivery and publisher controls live? | [Forge pipeline](https://github.com/guardkit/forge/tree/bec134d36a247008a3c64503c865d67268651a88/src/forge/pipeline) and [publisher](https://github.com/guardkit/forge/tree/bec134d36a247008a3c64503c865d67268651a88/src/forge/publisher) |
| How are service and credential boundaries deployed? | [Estate deployment](https://github.com/guardkit/forge/tree/bec134d36a247008a3c64503c865d67268651a88/deploy/estate) |
| Which Player implementation runs? | [guardkitfactory harness](https://github.com/guardkit/guardkitfactory/tree/40615a7e0ff6952b5a5492ada0d3a66dc10c8533/src/guardkitfactory/harness) |

More specific references appear beside the relevant explanations. Code availability
does not imply a service is deployed, a switch is enabled or an integration has passed
a live test.

## Operational records

The public [evidence page](evidence-and-limits.md) summarises the operator's dated
factory operating record, the 16 October local-model trial results and the 17 October
dashboard evaluation. Those records include private environment details and are not
linked from the public site. Treat their summaries as **operator-reported observations**,
not independently reproduced results. The documentation refresh did not run deployments
or issue factory approvals.

The successful six-request trial and later 5/8 follow-up are different runs. The latter
has an inconsistent heading date; the documented event occurred on 16 October. Keeping
that correction visible prevents a later presentation from treating the heading as a
second independent experiment.

## External research and diagram conventions

The [industry comparison](../learning/industry-comparison.md) records source publication
or update dates, access date and evidence strength. Its sources include company
engineering accounts, vendor documentation and research. Their reported outcomes are
not a benchmark against this factory.

Architecture uses the [C4 model's context and container levels](https://c4model.com/diagrams)
with explicit boundaries, responsibilities and technologies. C4 does not require a
particular drawing syntax; Mermaid is used to keep diagrams editable in the repository.
Sequence diagrams provide supporting dynamic views. They are not labelled C4 level 3
merely because they contain more boxes.

Rendering uses Material for MkDocs' [native Mermaid support](https://squidfunk.github.io/mkdocs-material/reference/diagrams/).
Avoid adding a second Mermaid loader: it can conflict with Material's page navigation.

## Keep the site current

When a command, responsibility or delivery boundary changes:

1. Update the owning harness or factory page and its source revision.
2. Change the evidence page only to the strength supported by the new result: source,
   configured service, observed run or broader evaluation.
3. Check diagrams, commands, incoming links and presentation claims affected by it.
4. Build the site, run the existing navigation checks and open the changed diagrams in
   a browser. A successful Markdown build alone does not validate Mermaid rendering.

From a checkout with the documentation dependencies installed:

```bash
python -m pip install -r docs/requirements.txt
mkdocs build
mkdocs serve
```

The repository's documentation workflow publishes the site when relevant changes reach
the main branch. Review
the diff before integration. Keep credentials, access-bearing preview URLs, raw model
transcripts and private customer material out of the public site.

Older reference pages are retained at their existing URLs and marked where they have
not been revalidated. They are useful historical detail, not evidence that an old SDK,
memory backend or command example still describes today's factory. The refreshed
entrypoints are [the harness guide](../harness/index.md),
[AutoBuild architecture](../deep-dives/autobuild-architecture.md) and
[the factory guide](index.md).
