# Template Two-Layer Model

This guide explains how GuardKit templates are structured and what
`guardkit init` does — and does not do — with them.

It exists because users reliably discover the config/pattern split by
failing in a downstream consumer rather than through documentation. This
is a tactical, user-facing guide; the comprehensive architectural write-up
lives in the
[AutoBuild Instrumentation Guide — Template Pattern Context](autobuild-instrumentation-guide.md#template-pattern-context).

## What `guardkit init` does

`guardkit init <template>` is a **config-layer installer**. Given a
resolved template (optionally following an `extends` chain), it copies
these four paths into your project:

```
.claude/agents/*.md           → .claude/agents/
.claude/rules/**/*.md         → .claude/rules/   (directory structure preserved)
CLAUDE.md, .claude/CLAUDE.md  → target root / .claude/
manifest.json                 → .claude/manifest.json
```

In addition, `init` creates top-level `.claude/`, `tasks/`, and
`.guardkit/` scaffolding, optionally seeds project-level Graphiti
knowledge, and optionally writes `.mcp.json`. The contract is documented
at [guardkit/cli/init.py](../../guardkit/cli/init.py) (`apply_template`
and `_apply_single_template`).

## What `guardkit init` does NOT do

`init` **does not** render files under the template's `templates/`
subdirectory. Specifically, it does not:

- Render `.template` or `.j2` files (no `{{ProjectName}}` /
  `{{Namespace}}` substitution happens at init time).
- Produce language-specific source trees, or project-level artifacts like
  `pyproject.toml`, `AGENTS.md`, `agent.py`, `langgraph.json`, Next.js
  `app/`, .NET `.csproj`, or their equivalents.
- Generate a "runnable project". Use your language's native tooling
  (`poetry init`, `dotnet new`, `pnpm create`, etc.) alongside `init` to
  get a working codebase.

If `init` prints a `Pattern layer: N scaffold file(s) present in
template (not rendered at init time)` line, that is the diagnostic trail
confirming the template ships a pattern layer and that init did not
render it. That is working as designed.

## Why: the two-layer model

GuardKit templates are partitioned into two layers with different
consumers and different lifetimes:

- **Config layer** — the four paths listed above. This is what `init`
  writes into your project. It gives Claude Code and GuardKit the agents,
  rules, CLAUDE.md guidance, and manifest they need to operate in your
  working tree from day one.
- **Pattern layer** — the `templates/` subdirectory inside each template
  (e.g. `installer/core/templates/langchain-deepagents-orchestrator/templates/`).
  It holds `.template` and `.j2` files that are canonical scaffold
  shapes. It is **not** consumed by `init`; it is consumed by the
  AutoBuild Player at feature-build time to give the Player stack-specific
  pattern context.

This split was landed on 2026-03-02 by TASK-INST-010
([tasks/design_approved/TASK-INST-010-reconcile-init-paths.md](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md))
and re-affirmed on 2026-04-11 by
[TASK-REV-A5F8](../../.claude/reviews/TASK-REV-A5F8-review-report.md).
The deliberate non-goal is scaffolding a runnable project out of
`init` — that concern is owned by the pattern layer's consumers, not by
the config-layer installer.

## If you need scaffold files today

If your workflow needs the actual `.template` / `.j2` content
materialised into your project, three options exist, listed fastest to
most architectural:

1. **Hand-copy from the installed template cache.** Locate the files at
   `~/.agentecflow/templates/<template>/templates/` and substitute
   `{{ProjectName}}`, `{{Namespace}}`, and any other placeholders by
   hand. This unblocks you today; it does not close the architectural
   loop.

2. **Use the integration smoke test as a reference renderer.**
   [tests/integration/test_template_render_import.py](../../tests/integration/test_template_render_import.py)
   implements `_render_template` and `_resolve_target` for literal
   `{{Key}} → value` substitution. Its `_RENDER_IMPL` sentinel documents
   the intent to promote this helper to a first-class CLI.

3. **Wait for `guardkit render <template>`.** A design spike is tracked
   as recommendation R4 in
   [.claude/reviews/TASK-REV-A925-review-report.md](../../.claude/reviews/TASK-REV-A925-review-report.md).
   It has not yet been feature-planned at time of writing.

## What the pattern layer is for

The pattern layer is the source of canonical scaffold shapes consumed by
**AutoBuild** and related automated code generation — it is not
user-facing scaffolding at init time. The AutoBuild Player reads from
this layer when it needs stack-specific pattern context during feature
implementation, closing a long-standing architectural hole where the
Player entered every turn with zero stack context.

For the architectural roadmap, including the Player wire-in and the
pattern-selection rules, see
[FEAT-1A5E README](../../tasks/backlog/template-pattern-layer/README.md)
and the
[AutoBuild Instrumentation Guide — Template Pattern Context](autobuild-instrumentation-guide.md#template-pattern-context)
section.

## Further reading

- Architectural analysis that produced this guide:
  [TASK-REV-A925 review report](../../.claude/reviews/TASK-REV-A925-review-report.md)
  (Recommendation R5a).
- Historical context for the config/pattern split:
  [TASK-REV-A5F8 review report](../../.claude/reviews/TASK-REV-A5F8-review-report.md).
- Pattern-layer consumer plan:
  [FEAT-1A5E README](../../tasks/backlog/template-pattern-layer/README.md).
- Comprehensive pattern-layer documentation (delivered by TASK-TPL-007):
  [AutoBuild Instrumentation Guide — Template Pattern Context](autobuild-instrumentation-guide.md#template-pattern-context).
  Originally tracked as
  [TASK-DOC-C3D7](../../tasks/backlog/template-pattern-layer/TASK-DOC-C3D7-document-two-layer-template-model.md).
