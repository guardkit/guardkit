# Review Report: TASK-REV-A925

**Title**: Orchestrator template scaffold files not rendered by `guardkit-init`
**Mode**: Architectural review + root-cause investigation
**Depth**: Standard
**Completed**: 2026-04-18
**Source brief**: [docs/reviews/deepagents-templates/TASK-REV-FORGE-INIT-orchestrator-template-scaffold-rendering-gap.md](../../docs/reviews/deepagents-templates/TASK-REV-FORGE-INIT-orchestrator-template-scaffold-rendering-gap.md)

---

## Executive Summary

**The filed task's framing is incorrect.** This is **not a resolver bug** in `guardkit init`,
**not a manifest-declaration gap**, **not a Jinja rendering failure**, and **not a LCL-003
regression**. The scaffold files under `installer/core/templates/<name>/templates/other/other/`
are **never rendered by `guardkit init` for any template** — that is deliberate,
architected, documented behaviour, landed on 2026-03-02 by
[TASK-INST-010](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md), confirmed
by the previous architectural review
[TASK-REV-A5F8](./TASK-REV-A5F8-review-report.md) on 2026-04-11, and acknowledged in
the LCL-003 smoke test's module docstring as an explicit non-goal.

The actual architectural situation, discovered during this review:

1. **`guardkit init` is a config-layer installer only.** It copies `.claude/agents`,
   `.claude/rules`, `CLAUDE.md` variants, and `manifest.json`. It does **not** render
   `.template` files from *any* template under `templates/other/**`. This is
   the two-layer template model (config layer + pattern layer) established
   by TASK-INST-010 and re-affirmed by TASK-REV-A5F8.

2. **All 10 builtin templates ship a `templates/` pattern layer with no
   runtime consumer today.** This is a known architectural hole already being
   addressed by feature **FEAT-1A5E** (Template Pattern Layer for AutoBuild) in
   [tasks/backlog/template-pattern-layer/](../../tasks/backlog/template-pattern-layer/).
   The Forge is blocked on the same hole every other consumer sits in; it is
   not a new or orchestrator-specific defect.

3. **LCL-003 landed and is working as designed.** It renders templates via its own
   `_render_template` shim (not via `guardkit init`) and explicitly documents
   that non-coverage. Its documented scope limitation — coverage of `langchain-deepagents`
   only, deferring `-orchestrator` and `-weighted-evaluation` as "mechanical
   extension" — is a real open gap, but unrelated to the BLOCKER framing in the
   filed task.

4. **Severity is MEDIUM, not BLOCKER.** The Forge is not blocked by a broken
   CLI; it is blocked by a missing-capability gap that affects every consumer
   of every template. Three short-horizon remediations are available without
   waiting on FEAT-1A5E.

### Score (Architectural Assessment)

| Dimension | Score | Notes |
|-----------|-------|-------|
| SOLID Compliance | 8/10 | `guardkit init` has a clean single responsibility (config layer). The open follow-through is a missing component, not a violation. |
| DRY Adherence | 6/10 | Every template ships a pattern layer with no consumer — write-only output from `/template-create`. Not duplication, but redundant production. |
| YAGNI Compliance | 5/10 | The pattern layer has been produced for ~6 weeks with no runtime reader. Either the consumer (FEAT-1A5E) lands or the layer is deferred. |
| Diagnostic trail | 4/10 | `guardkit init` reports success without listing what was **not** copied. Users discover the two-layer split by failing in a consumer repo, as happened here. |
| Regression prevention | 7/10 | LCL-003 prevents `.template` render-time import regressions. It does not (and was never intended to) catch "init doesn't render" misunderstandings. |
| Docs/code co-evolution | 4/10 | The two-layer model is not documented outside review reports. No user-facing text explains `guardkit init` is config-only. |
| **Overall** | **72/100** | Sound architecture with a known, filed architectural hole and a legitimate diagnostic-trail gap. |

---

## Findings

### F1 — The filed hypothesis (resolver has incomplete `templates/other/<category>/` mapping) is **wrong**

**Evidence**: [guardkit/cli/init.py:1007-1146](../../guardkit/cli/init.py#L1007) — the
entire copy loop in `_apply_single_template` + `apply_template` walks exactly four
source paths per template:

```
.claude/agents/*.md           → .claude/agents/
agents/*.md                    → .claude/agents/  (legacy location)
.claude/rules/**/*.md          → .claude/rules/   (preserves structure)
CLAUDE.md / .claude/CLAUDE.md  → target root / .claude/
manifest.json                  → .claude/manifest.json
```

There is **no code path** that walks `templates/`. The `_SKIP_DIRS` constant
at [init.py:56](../../guardkit/cli/init.py#L56) is a documentation-only
statement of intent — grepping the codebase confirms the constant is never
referenced in any copy/walk logic. The copy logic is allow-list, not deny-list:
only the four paths above are read.

**Implication**: There is nothing to fix in the resolver. "Nested `other/other/`
silently skipped" is literally correct but misdiagnosed — *everything* under
`templates/` is skipped, not just the nested bucket. Patching the resolver to
walk `templates/other/other/` would either (a) have no effect (no downstream
write logic) or (b) ship scaffold files to the user's working directory, which
TASK-INST-010 and TASK-REV-A5F8 both rejected as the wrong consumer-side model.

### F2 — `templates/` is the **pattern layer**, a deliberate second tier with a known consumer gap

**Evidence**:
- TASK-INST-010 (2026-03-02, design_approved): explicit task requirement was
  "Skip code scaffolds: Do NOT copy `{template}/templates/`, `{template}/config/`,
  or `{template}/docker/` directories (code scaffold generation is a separate
  concern)".
- [TASK-REV-A5F8 §0](./TASK-REV-A5F8-review-report.md) (2026-04-11) re-reviewed
  this decision, defended the config-layer split, and identified the missing
  consumer as the **AutoBuild Player**, not `guardkit init`.
- [FEAT-1A5E](../../tasks/backlog/template-pattern-layer/README.md) is the
  in-flight feature filed by TASK-REV-A5F8 to close this hole:
  `TASK-PAT-1A5E` (wire pattern layer into Player), `TASK-DOC-C3D7` (document
  two-layer model), `TASK-REN-B9F2` (rename `templates/` → `patterns/`, optional).
- Graphiti `guardkit__project_decisions` contains the validated fact (from
  TASK-DRF-003, 2026-04-11): *"The GuardKit tool's `init` command initializes
  projects by copying specific directories (.claude/, .guardkit/, and tasks/)
  from a template, not generating language-specific source trees."*

**Blast radius confirmation** (all 10 builtin templates ship a pattern layer):

| Template | `templates/` subdirs |
|----------|----------------------|
| `default` | empty |
| `fastapi-python` | api, config, core, crud, db, dependencies, models, schemas, testing |
| `fastmcp-python` | config, resources, server, testing, tools |
| `langchain-deepagents` | other, testing |
| `langchain-deepagents-orchestrator` | other (agents, example-domain, lib, other, prompts, tools) |
| `langchain-deepagents-weighted-evaluation` | goal.md.j2, other |
| `mcp-typescript` | prompts, resources, server, testing, tools |
| `nats-asyncio-service` | handlers, infrastructure, other, services, testing |
| `nextjs-fullstack` | actions, api, app, components, lib, prisma, tests, workflows-ci.yml.template |
| `python-library` | src |
| `react-fastapi-monorepo` | apps, docker |
| `react-typescript` | api, components, mocks, routes |
| `dotnet-railway-fastendpoints` | 20 `.cs.template` files across 10 layer subdirs |

**Every** non-trivial template has this "pattern layer with no init-time
consumer" shape. The Forge failure is not orchestrator-specific.

### F3 — LCL-003 landed and its documented scope limitation is the only real regression-prevention gap

**Evidence**: [tests/integration/test_template_render_import.py](../../tests/integration/test_template_render_import.py)
(375 lines, 14 tests passing + 1 `xfail(strict=True)` gated on LCL-001, currently
in completed/TASK-LCL-003/).

Module docstring lines 11-21 explicitly state:

> **Interface contract**: Consumes the raw `.template` files under
> `installer/core/templates/<name>/`. It does NOT call `guardkit init`
> (that CLI deliberately skips `.template` scaffold files — see
> `guardkit.cli.init.apply_template`). If the installer ever grows a
> first-class `.template` renderer (`guardkit render` or an importable
> `render_template(...)` API), swap the local `_render_template` helper
> for it — see `_RENDER_IMPL` sentinel.

The LES1 §8 argument in the filed task is **misapplied**: LCL-003 is designed
to catch render-time **import-chain** regressions in `.template` files (the class
of bug TASK-LCL-001 introduced). It is architecturally incapable of catching
"the CLI never renders this file" misunderstandings, because in the intended
design there is no render step at `init` time.

The one legitimate LCL-003 gap (acknowledged in its own completion notes):

> **Template coverage**: `langchain-deepagents` (base). The `-orchestrator`
> and `-weighted-evaluation` siblings use different conventions (orchestrator
> uses bare `from prompts import …` imports; weighted-eval uses `.j2` not
> `.template`); adding them is a mechanical extension of `TEMPLATES` in the
> test and is left as a follow-up within FEAT-LTL1.

This is a real, narrow fix; it is unrelated to the filed BLOCKER.

### F4 — The Forge's actual dependency is FEAT-1A5E OR an explicit scaffold-render command

**Evidence**: The Forge (`~/Projects/appmilla_github/forge/`) reports:

```
$ guardkit-init langchain-deepagents-orchestrator
... success ...
$ test -f AGENTS.md && echo Y || echo N  →  N
$ test -f pyproject.toml && echo Y || echo N  →  N
```

Both assertions are consistent with the config-layer-only contract. The Forge's
`/system-arch` workflow expects `pyproject.toml`, `AGENTS.md`, `agent.py`, and
`langgraph.json` at the project root. None of these have ever been produced by
`guardkit init` for any template.

Three remediation paths exist:

- **A. Hand-scaffold in Forge** (fastest, 1-2 hours): copy the four files from
  `~/.agentecflow/templates/langchain-deepagents-orchestrator/templates/other/other/*.template`,
  substitute `{{ProjectName}}` and `{{Namespace}}`, land them in the Forge repo.
  Unblocks `/system-arch` today. Does not close the architectural hole.
- **B. Add `guardkit render <template>` command** (medium, 1-2 days): a
  first-class CLI that applies the layout-matching logic already implemented in
  LCL-003's `_render_template` + `_resolve_target`. This is the long-hinted
  "first-class renderer" referenced in LCL-003's `_RENDER_IMPL` sentinel.
  Uses a per-template layout map (like LCL-003's `_LCD_LAYOUT`) or requires
  templates to carry a `manifest.json` rendering section.
- **C. Complete FEAT-1A5E** (high-value, weeks): wire the pattern layer into
  the AutoBuild Player so it consumes scaffold patterns during feature
  implementation. This is the architectural close-out, not a Forge-unblock.

These are **not mutually exclusive**. A is tactical; B is the missing capability
gap the filed task is actually (indirectly) pointing at; C is the strategic
consumer wire-in.

### F5 — Diagnostic-trail gap in `guardkit init` output is a legitimate, narrow finding

**Evidence**: [guardkit/cli/init.py:1592-1626](../../guardkit/cli/init.py#L1592) —
init's summary block reports:

```
GuardKit initialized successfully!
  Seeded: project knowledge (...)
  Not yet seeded: system knowledge (...)
Next steps:
  1. Create a task: /task-create "Your first task"
```

It does not mention:
- How many files the template contained under `templates/` that were **not**
  copied (i.e. exist in the cache but were intentionally skipped).
- That the template has a pattern layer consumed only by AutoBuild.
- Where to look for the scaffold files if the user expected them.

This is precisely the **Category A (no diagnostic trail)** problem the filed
task calls out — and on that narrow dimension, the filed task is correct.
Fixing this is a small, contained change that does not require resolver work.

---

## Recommendations

Ordered by priority and implementation cost.

### R1 — [HIGH, fast] Unblock the Forge via hand-scaffold (Remediation Path A)

Create a one-shot task to materialise the four scaffold files into the Forge
repo by hand:

- `pyproject.toml` — from `templates/other/other/pyproject.toml.template`
  (substituting `{{ProjectName}}` → `forge`, `{{Namespace}}` → `forge`)
- `AGENTS.md` — from `templates/other/other/AGENTS.md.template`
- `agent.py` — from `templates/other/other/agent.py.template`, placed at
  `src/forge/agent.py` or project root per the template's `langgraph.json`
  mapping
- `langgraph.json` — from `templates/other/other/langgraph.json.template`

**Estimated effort**: 1-2 hours including `pip install .[providers]` + `python -c 'import forge.agent'` smoke.
**Dependencies**: None.
**Owner**: Forge repo task.
**Risk**: Low; the files are already validated by LCL-003 for the base template
and TASK-LCL-004/LCL-005 at source level. Orchestrator variant is
mechanically similar.

### R2 — [HIGH, narrow] Add diagnostic-trail improvements to `guardkit init` summary

Add two lines to the init summary when a template has a non-empty `templates/`
directory:

1. `Pattern layer: {N} scaffold files in template (not rendered at init time)`
2. `  Tip: these are consumed by AutoBuild; see docs/guides/templates.md` (pending R5)

**Implementation**: [guardkit/cli/init.py:1592-1626](../../guardkit/cli/init.py#L1592),
before the "Next steps" block. Count files via
`(_resolve_template_source_dir(template_name) / "templates").rglob("*.template")`
if the `templates/` subdir exists.

**Estimated effort**: 2-3 hours including test coverage.
**Dependencies**: None.
**Fails-loudly clause** (from the filed task's AC): do NOT convert missing
scaffold-file renders into init errors. That would break every consumer.
**Do** make their existence visible. This is the narrow intersection of the
filed AC that is legitimate.

### R3 — [MEDIUM, mechanical] Extend LCL-003 to cover `-orchestrator` and `-weighted-evaluation`

The only real regression-prevention gap. LCL-003's completion notes already
flag this as follow-up work inside FEAT-LTL1.

- Add `TemplateCase` entries for `langchain-deepagents-orchestrator` and
  `langchain-deepagents-weighted-evaluation` to `TEMPLATES` in
  [tests/integration/test_template_render_import.py:170](../../tests/integration/test_template_render_import.py#L170).
- Orchestrator uses different import conventions (`from prompts import …`)
  so the layout map will differ.
- Weighted-eval uses `.j2` not `.template`, so either extend `_render_template`
  to handle both suffixes or declare j2 files out of scope for this smoke test
  (they're Jinja, not string substitution).

**Estimated effort**: 4-6 hours (most cost is figuring out the layout map
for each variant by grep'ing their render-time imports).
**Dependencies**: None.
**Closes**: the only real AC-line in the filed task's "Regression prevention"
section that is currently open.

### R4 — [MEDIUM, capability] Design spike for `guardkit render <template>` (Remediation Path B)

Scope via `/feature-plan` (not `/task-create` directly). The capability exists
in prototype form inside LCL-003 — `_render_template` + `_resolve_target` +
per-template layout maps. Promoting it to a first-class CLI closes the
long-standing producer/consumer loop pointed at by LCL-003's
`_RENDER_IMPL = "local"` sentinel comment.

Key design questions the spike must answer:

- Does layout live in `manifest.json` (declarative), in Python per-template
  plugins, or is it inferred from conventions?
- Does `render` take a `--output-dir` or scaffold in-place?
- What is the placeholder-substitution contract (strict `{{Key}}` vs full Jinja)?
- Does `render` front-run `init` (so `init --render` becomes a convenience)
  or stand alone?
- How does `render` interact with FEAT-1A5E's pattern-layer consumer? (They
  are complementary, not competing: FEAT-1A5E wires patterns into the Player
  worktree; `render` materialises them into a user working directory.)

**Estimated effort**: 1-2 days scoping; 1-2 weeks implementation.
**Dependencies**: None (independent of FEAT-1A5E).
**Defer if**: R1 + R5 together give the Forge and future consumers enough
runway. The narrow deliverable is documented one-shot hand-scaffold + a clear
"here is what init does and does not do" in docs.

### R5 — [MEDIUM, docs] Document the two-layer template model (already filed as TASK-DOC-C3D7)

`TASK-DOC-C3D7` is already in
[tasks/backlog/template-pattern-layer/](../../tasks/backlog/template-pattern-layer/)
pending completion of `TASK-PAT-1A5E` scoping. Consider splitting it:

- **C3D7a (now)**: short user-facing doc explaining that `guardkit init` is a
  config-layer installer; the `templates/` subdirectory is a pattern layer for
  advanced agent workflows; and scaffolding a runnable project requires either
  `guardkit render` (pending R4) or manual copy. Close the *most painful*
  documentation gap today.
- **C3D7b (after FEAT-1A5E)**: comprehensive two-layer architecture doc
  describing the Player consumer wiring. Defer until the wire-in actually
  exists, as originally scoped.

**Estimated effort**: 2-4 hours for C3D7a.
**Dependencies**: None.
**Closes**: the *"Document the `templates/<category>/` convention"* AC from
the filed task, at the narrow-correct scope.

### R6 — [LOW/DEFER] Do NOT pursue the filed "resolver fix" or "manifest-contract enforcement" ACs

The filed task's primary ACs presuppose that `guardkit init` was supposed to
render these files. It was not. Pursuing:

- Extending the resolver to walk `templates/other/other/`: violates
  TASK-INST-010's architectural decision, re-affirmed by TASK-REV-A5F8.
- Adding a manifest-enforced "fail loudly if declared output missing"
  contract: the manifest does not declare init-time outputs, and inventing
  that contract now would be a larger architectural change than warranted.

Both are **rejected** at this review. If the user believes init SHOULD render
scaffolds, that is an architectural pivot that should be filed as a new review
(e.g., `/task-review "Revisit config-layer-only decision in guardkit init"`)
rather than fitted under this task's BLOCKER framing.

---

## Decision Matrix

| Remediation | Effort | Closes Forge block? | Closes LCL-003 gap? | Closes architectural hole? |
|-------------|--------|---------------------|---------------------|---------------------------|
| R1 (hand-scaffold Forge) | 1-2h | ✅ | ❌ | ❌ |
| R2 (init diagnostic trail) | 2-3h | ❌ (but reduces future incidents) | ❌ | Partial (surfaces hole) |
| R3 (extend LCL-003) | 4-6h | ❌ | ✅ | ❌ |
| R4 (`guardkit render` spike) | 1-2d scope, 1-2w build | ✅ (re-run cleanly) | ❌ | Partial |
| R5 (two-layer docs) | 2-4h | ❌ (but prevents misdiagnosis) | ❌ | Partial |
| FEAT-1A5E (already filed, not this review) | weeks | ❌ (wrong consumer) | ❌ | ✅ |

**Recommended sequence**: R1 (unblock today) → R2 + R3 + R5 in parallel (close
the narrow legitimate gaps) → R4 design spike (capability investment) →
FEAT-1A5E proceeds on its own track.

---

## Context Used (from Graphiti knowledge graph)

- **ADR / decision** (`guardkit__project_decisions`, 2026-04-11): *"The
  GuardKit tool's `init` command initializes projects by copying specific
  directories (.claude/, .guardkit/, and tasks/) from a template, not
  generating language-specific source trees."* — validated by TASK-DRF-003
  during the dotnet-railway-fastendpoints integration. Validated against
  the code under review (F1, F2): current behaviour of `guardkit init` still
  matches this ADR.

- **Past failure pattern** (`guardkit__task_outcomes`, TASK-LCL-001):
  un-runnable rendered projects were caused by over-rewriting SDK imports
  to project-local paths. Checked for recurrence (F3): no recurrence —
  this review's finding is a different class (CLI-coverage gap, not
  render-time import bug).

- **Prior review** (TASK-REV-A5F8, 2026-04-11): previously analysed this same
  architectural hole and filed FEAT-1A5E to close it. Applied (F2, F4):
  confirmed the filed task duplicates findings already accepted upstream,
  reaffirmed F4B8a/b/E7A2 recommendations are the accepted architectural
  path forward.

---

## Appendix A — File-level evidence pointers

| Claim | File | Lines |
|-------|------|-------|
| `_SKIP_DIRS` is doc-only, never referenced in copy logic | [guardkit/cli/init.py](../../guardkit/cli/init.py) | 56 (decl), no referenced elsewhere |
| `apply_template` allow-list walks only 4 paths | [guardkit/cli/init.py](../../guardkit/cli/init.py) | 920-1006 (`_apply_single_template`), 1009-1146 (`apply_template`) |
| `init` summary does not mention pattern layer | [guardkit/cli/init.py](../../guardkit/cli/init.py) | 1592-1626 |
| LCL-003 explicitly does not call `guardkit init` | [tests/integration/test_template_render_import.py](../../tests/integration/test_template_render_import.py) | 11-21 (docstring), 274-305 (`_render_template`) |
| LCL-003 only covers `langchain-deepagents` base | [tasks/completed/TASK-LCL-003/TASK-LCL-003.md](../../tasks/completed/TASK-LCL-003/TASK-LCL-003.md) | 74-79 (completion notes) |
| TASK-INST-010 "skip code scaffolds" requirement | [tasks/design_approved/TASK-INST-010-reconcile-init-paths.md](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md) | 56 |
| TASK-REV-A5F8 reaffirmation of config-layer split | [.claude/reviews/TASK-REV-A5F8-review-report.md](./TASK-REV-A5F8-review-report.md) | §0, §1 |
| FEAT-1A5E already scoped | [tasks/backlog/template-pattern-layer/README.md](../../tasks/backlog/template-pattern-layer/README.md) | full |
| Orchestrator template `templates/other/other/` contents | `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/` | 5 `.template` files |

---

## Appendix B — LES2 incident write-up hook (from filed task)

The filed task asks for this incident to be captured as evidence for LES2.
The review-derived write-up is materially different from the filed framing:

- **Category A (no diagnostic trail)**: ✅ legitimate. `guardkit init`
  reports "initialized successfully" without surfacing that a non-trivial
  pattern-layer exists in the template and was not materialised. R2 fixes
  this narrowly.
- **Category C (retry/re-render context lost)**: ✗ misattributed. There is
  no retry, because there is no initial render. This category does not
  apply.
- **LES1 §8 (doc/code co-evolution failure)**: ✗ misattributed. The code
  matches its intent; the code *does not* advertise its intent to users.
  This is a docs-coverage gap (R5), not a docs-drift-from-code gap. LES1 §8
  covers the latter.

The cleaner LES2 lesson is:

> **When an installer is partitioned into layers (config / pattern), users
> will discover the partition in the worst possible place — usually a
> downstream consumer that assumes both layers are present. Surface the
> partition in the installer's own summary output (R2) and document it in
> the user-facing entry point (R5). "Code is correct and does exactly what
> the task description says it does" is necessary but not sufficient; the
> task description's implicit assumptions about user mental model need to
> be laid out in the product's visible surface area.**

This is a narrower, more accurate lesson than the three-category pile-up in
the filed task, and it is one GuardKit can act on inside this review's
recommendations (R2 + R5).

---

## Decision Checkpoint

**Recommendation to user**: Choose `[I]mplement` to create R1, R2, R3, R5 as
fix tasks (R4 should go through `/feature-plan` separately given its design
scope). Reject the original task's R1-framing (resolver fix) and R-framing
of the manifest contract; those ACs are closed at this review as
architecturally incorrect.

**If [A]ccept instead**: document this reframing in the task's completion
notes. FEAT-1A5E proceeds on its existing track. Forge unblocks via manual
hand-scaffold per R1 without a new task.

**If [R]evise**: targeted re-analysis scope would be (a) whether the
config-layer-only decision should be revisited given the Software Factory
direction, and (b) whether `guardkit render` belongs as part of init or as
a separate command. Both are genuinely open design questions.
