---
title: /system-arch scope — Pattern-layer rendering architecture for GuardKit
status: scope-doc (input to `/system-arch`)
created: 2026-04-18
supersedes_task: TASK-REV-R4CD (cancelled; see `tasks/cancelled/`)
derived_from:
  - .claude/reviews/TASK-REV-A925-review-report.md (R4, R2)
  - .claude/reviews/TASK-REV-A5F8-review-report.md (config-layer split)
  - tasks/design_approved/TASK-INST-010-reconcile-init-paths.md (skip code scaffolds decision)
  - tasks/backlog/template-pattern-layer/TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md
  - tests/integration/test_template_render_import.py (LCL-003 prototype)
---

# /system-arch Scope — Pattern-layer rendering architecture for GuardKit

## Purpose of this document

This is an **input brief** for a `/system-arch` session. It is not a design.
The ask is for the Architect agent to propose a complete architecture for
pattern-layer rendering in GuardKit, covering:

1. A shared rendering primitive (library API)
2. A manifest schema extension declaring each template's pattern layer
3. Two consumer surfaces — explicit one-shot rendering (CLI) and
   AutoBuild Player build-time context — both reading from the same primitive
   and the same manifest contract
4. A migration path from LCL-003's prototype (`_render_template`,
   `_resolve_target`, per-template Python layout dicts) to the production
   architecture
5. An interaction boundary with FEAT-1A5E (pattern-layer → AutoBuild Player)
   that makes the two efforts complementary, not overlapping

**Stop condition for this session**: the Architect produces an architecture
document with (a) library API signatures, (b) manifest schema, (c) command
surface(s) and CLI flag shapes, (d) migration/sequencing plan, (e) interaction
contract with FEAT-1A5E. **No code is written in this session.** Implementation
is filed as subsequent feature-plan / task-work work once the architecture is
approved.

---

## 1 — The problem, stated cleanly

Every new repo initialised from the Software Factory — today Forge, tomorrow
every specialist role, domain-specific agent, or consumer product built through
the pipeline — hits a **scaffold-rendering toll** that has no automated answer.

The toll today:

1. Find the template source in the installed `guardkit` package
2. Read each `.template` file under `installer/core/templates/<name>/templates/`
3. Substitute `{{ProjectName}}` / `{{Namespace}}` / etc. by hand
4. Write to the consumer repo, deciding per-file where in the tree it belongs
5. Audit-trail nothing

Estimated human cost: 30–60 minutes per new repo, mechanical, error-prone
(easy to miss a placeholder), zero auditability.

**Forge is the first repo to feel this at full strength** because Forge is the
first consequential project initialised from a post-LES1 hardened template.
Every subsequent factory-built repo will hit the same toll.

**This is not a bug in `guardkit init`.** `guardkit init` is a config-layer
installer by explicit architectural decision (TASK-INST-010, 2026-03-02;
reaffirmed TASK-REV-A5F8, 2026-04-11). The issue is that the **pattern layer**
— the `templates/` subtree inside each template — has no first-class consumer.
All 10 builtin templates ship a pattern layer; nothing reads it at runtime today.

---

## 2 — Current state of the art

### 2.1 The two-layer template model (already settled)

| Layer | Source | Consumer today | Notes |
|-------|--------|---------------|-------|
| **Config layer** | `.claude/agents/`, `.claude/rules/`, `CLAUDE.md`, `manifest.json` | `guardkit init` (copies to target repo) | Settled by TASK-INST-010. Allow-list copy, 4 paths walked. |
| **Pattern layer** | `templates/**/*.template` and `templates/**/*.j2` | **None in production today.** Prototyped in LCL-003's test-only `_render_template`. | Architectural hole. FEAT-1A5E scopes one consumer (AutoBuild Player); R4 of A925 scopes a second (one-shot CLI). |

`guardkit init` explicitly skips `templates/`; see
[guardkit/cli/init.py:56](../../../guardkit/cli/init.py#L56) (`_SKIP_DIRS` — a
documentation-only constant never referenced by copy logic, because the copy
logic is allow-list) and [guardkit/cli/init.py:920-1146](../../../guardkit/cli/init.py#L920)
(`_apply_single_template` + `apply_template`).

### 2.2 The LCL-003 prototype (what exists and works)

[tests/integration/test_template_render_import.py](../../../tests/integration/test_template_render_import.py)
contains a working renderer, intentionally marked as a shim:

- **`_render_text(source, placeholders)`** — literal `{{Key}} → value`
  substitution. Does NOT evaluate Jinja expressions
  ([test_template_render_import.py:390](../../../tests/integration/test_template_render_import.py#L390))
- **`_resolve_target(src_rel, layout)`** — longest-prefix-match mapping from
  source paths under `templates/` to target paths in the rendered tree
  ([test_template_render_import.py:398](../../../tests/integration/test_template_render_import.py#L398))
- **`_render_template(template_root, case, output_root)`** — walks `*.template`
  and `*.j2`, resolves targets, substitutes, writes. Contains
  `_RENDER_IMPL = "local"` sentinel flagged for future promotion
  ([test_template_render_import.py:444](../../../tests/integration/test_template_render_import.py#L444))

**Per-template layout maps already exist** as Python dicts in the test file:

- `_LCD_LAYOUT` — `langchain-deepagents` (flattened `scratch/` package model)
- `_LCDO_LAYOUT` — `langchain-deepagents-orchestrator` (root-package `agents/`,
  `prompts/`, `tools/`, `lib/` — different from base)
- `_LCDWE_LAYOUT` — `langchain-deepagents-weighted-evaluation` (`.j2` suffix,
  partial rendering — some files contain real Jinja and are skipped)

These dicts are precisely the contract that needs to move out of test code and
into a template-declared manifest.

### 2.3 The Jinja boundary (critical)

LCL-003 deliberately does **literal `{{Key}}`** substitution, not Jinja
evaluation. Files that contain real Jinja expressions (`{% for %}`, filters,
`| default(...)`) are skipped via the layout's `None` target — see
[test_template_render_import.py:246-253](../../../tests/integration/test_template_render_import.py#L246).

The Architect must decide whether the production renderer:
- Stays literal `{{Key}}` only (and `.j2` files with real Jinja are rendered by
  something else / out of scope)
- Adopts full Jinja2 (risks template authors using features that break literal
  fallbacks elsewhere)
- Splits: `.template` = literal, `.j2` = Jinja — formalises the existing suffix
  convention as the contract

### 2.4 FEAT-1A5E — the in-flight consumer

[tasks/backlog/template-pattern-layer/TASK-PAT-1A5E](../../../tasks/backlog/template-pattern-layer/TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md)
scopes the Player-context consumer. Key points for the Architect:

- Player currently enters feature implementation with **zero stack-specific
  pattern context**. Worktree setup prunes `.claude/rules/` to 4 essentials
  (`AUTOBUILD_ESSENTIAL_RULES`, ~11.5K tokens saved/turn).
- FEAT-1A5E proposes injecting patterns into `.guardkit/patterns/` or
  `.claude/patterns/` inside the worktree, ephemerally, per Player turn.
- Scope discussion includes v1 (copy whole `templates/` tree — flat token cost)
  vs v2 (task-scoped selection by layer — scales with need).
- Status: `needs_feature_plan: true`. Has not been designed yet.

**FEAT-1A5E is not this session's subject**, but this session's architecture
MUST define the boundary cleanly so FEAT-1A5E can proceed in parallel.

---

## 3 — The design space (four options)

These are the candidate shapes. The Architect should evaluate, combine, or
reject as appropriate — they are NOT a menu to pick one from.

### Option A — `guardkit render <template>` standalone CLI

One-shot rendering command, separate from `init`. Explicit user intent.
Preserves config-layer-only boundary of `init`.

**Pro**: clear UX, explicit, audit-trail via CLI invocation, dry-run friendly.
**Con**: commits to a CLI surface before we have evidence from real usage;
encodes layout contract independently from any other consumer unless backed
by manifest.

### Option B — `guardkit init <template> --with-scaffold` integrated flag

Opt-in flag extending `init` to render pattern layer.

**Pro**: single command for bootstrap; less surface area.
**Con**: re-litigates TASK-INST-010 and TASK-REV-A5F8 — the config-layer split
is a settled decision. This option should be rejected outright unless the
Architect has strong new evidence. Flagged here for completeness only.

### Option C — Pattern layer → AutoBuild Player context

FEAT-1A5E. Player receives `.template` files as reference patterns during
AutoBuild, alongside Graphiti context. Render happens inside the Player turn.

**Pro**: architecturally correct destination for factory-built features; matches
"build-time patterns, not init-time scaffolds" spirit of A5F8.
**Con**: doesn't solve the one-off bootstrap case (Forge today, new repos
tomorrow). AutoBuild is overkill for a hand-bootstrap.

### Option D — Thin rendering library, defer command decision

Extract `guardkit.rendering.render_template_file(src, dst, variables)` (and
friends) as a library with:
- Placeholder resolution (strict `{{Key}}` today, Jinja escape hatch TBD)
- File walker + conflict detection (what if target exists?)
- Dry-run mode
- Full test coverage

**Do NOT wire to a CLI yet.** Use it today via ad-hoc Python invocation for
Forge; use it later as the engine for A and/or C.

**Pro**: cheapest path that actually fixes the immediate pain; zero lock-in on
command surface; shared primitive for A and C means neither reinvents
placeholder resolution or layout resolution.
**Con**: no end-user CLI deliverable on day one. Mitigated by hand-scaffold
path (see §5 sequencing).

### Why A and C are complementary, not alternatives

Different use cases:

- **C (Player context)** — factory-built features. The user never manually
  renders anything. AutoBuild pulls from pattern layer during `/feature-build`.
- **A (explicit CLI)** — one-off operations. Bootstrapping a new repo,
  regenerating a scaffold from an updated template, diff-mode for
  "what changed?" against a live repo. Situations where AutoBuild is wrong
  or overkill.

Software Factory thinking says **you need both, not one**. The question the
Architect should answer is the sequencing and the shared foundation.

---

## 4 — The manifest-schema question (the real architectural move)

Right now, each template's pattern layer lives in an internal directory
convention (`templates/other/other/*.template`, `templates/other/prompts/*.template`,
etc.). The layout maps in LCL-003 are Python dicts that encode
directory-to-target mappings per template. That means:

- The rendering logic is coupled to each template's internal directory structure
- Users have no way to introspect "what will `render` do?" without running it
- `init` has no way to enumerate the pattern layer for diagnostic output
  (R2 from A925 is blocked on this)
- Adding a new template requires writing a new Python layout dict (or
  inheriting a brittle convention)

### Proposed: `manifest.json` pattern_layer section

Each template declares its pattern layer explicitly:

```json
{
  "name": "langchain-deepagents-orchestrator",
  "version": "1.0.0",
  "config_layer": { "...": "existing init-time paths" },
  "pattern_layer": {
    "placeholders": {
      "ProjectName": { "required": true, "default": null, "pattern": "^[a-z][a-z0-9_]*$" },
      "Namespace":   { "required": true, "default": null }
    },
    "files": [
      { "source": "templates/other/other/pyproject.toml.template",
        "target": "pyproject.toml" },
      { "source": "templates/other/other/AGENTS.md.template",
        "target": "AGENTS.md" },
      { "source": "templates/other/other/agent.py.template",
        "target": "src/{{ProjectName}}/agent.py" },
      { "source": "templates/other/other/langgraph.json.template",
        "target": "langgraph.json" }
    ],
    "directories": [
      { "source": "templates/other/agents/",  "target": "agents/" },
      { "source": "templates/other/prompts/", "target": "prompts/" },
      { "source": "templates/other/tools/",   "target": "tools/" },
      { "source": "templates/other/lib/",     "target": "lib/" }
    ],
    "skip": [ "templates/testing/", "templates/goal.md.j2" ]
  }
}
```

**Advantages**:

1. **Pattern layer becomes explicit and introspectable.** `guardkit render`
   (whenever it lands) can enumerate what will be written before writing.
2. **`guardkit init` can list the pattern layer in its summary output** —
   R2 from A925 closes as a side effect, with zero rendering logic added to
   `init`.
3. **Removes the internal-directory convention as contract.** The manifest is
   the contract; the directory structure is implementation.
4. **Unblocks A and C simultaneously.** Both consumers read the same manifest.
5. **Template authors own their layout.** No Python code required in guardkit
   to add a new template.

### Open questions for the Architect

- **Schema validation**: Pydantic model? JSON Schema file? Runtime-checked at
  what point (template install, render invocation, both)?
- **Placeholder constraint language**: regex pattern? enum? computed defaults
  (e.g. `Namespace` defaults to `ProjectName`)?
- **Target templating**: the `{{ProjectName}}` in target paths above — literal
  string replace, same Jinja/literal decision as file contents?
- **Skip semantics**: `skip` list vs `None` target (per LCL-003)? Glob patterns?
- **Inheritance**: extension templates (e.g. `langchain-deepagents-weighted-evaluation`
  `extends: langchain-deepagents`) — does the manifest merge?
- **Migration path**: can existing templates keep their current directory
  layout and just gain a manifest section? Or does something need to rename?
  (TASK-REN-B9F2 in FEAT-1A5E proposes renaming `templates/` → `patterns/` —
  is that orthogonal or entangled?)

---

## 5 — Sequencing proposal (for the Architect to validate or revise)

The following sequencing ships standalone value at every step and does not
commit to a command surface before evidence exists:

### Today (hand-scaffold unblock)

- Hand-scaffold Forge via manual copy + placeholder substitution. Filed as
  a one-shot task in the Forge repo (TASK-FORGE-SCAFFOLD or similar).
- Capture observations: which placeholders appear, what goes wrong, where the
  mental friction is. Evidence feeds library design.

### This sprint (foundation)

- **Option D**: extract `guardkit.rendering` library
  (`render_template_file`, `render_template_tree`, conflict detection, dry-run).
  ~4 hours of focused work + tests.
- **Manifest schema extension**: `pattern_layer` section in `manifest.json`,
  Pydantic model, JSON Schema, validation. Port `_LCD_LAYOUT`, `_LCDO_LAYOUT`,
  `_LCDWE_LAYOUT` to manifest form in the three langchain-deepagents templates
  as proof-of-concept.
- **LCL-003 migration**: swap `_render_template` shim for
  `guardkit.rendering.render_template_tree`, delete the Python layout dicts.
  The `_RENDER_IMPL = "local"` sentinel becomes `_RENDER_IMPL = "library"`.
- **R2 from A925 closure**: `init` reads `pattern_layer.files` + `directories`
  from manifest, reports count in summary. No rendering added to `init`.

### Next sprint (consumers)

- **Option A lands**: `guardkit render <template> [--output-dir] [--dry-run]
  [--diff] [--force]`. Reads manifest, calls library, writes to cwd or
  `--output-dir`. Conflict handling per flag.
- **Option C lands (FEAT-1A5E)**: AutoBuild worktree-setup path reads manifest,
  calls library, writes patterns to `.guardkit/patterns/` inside worktree.
  v1 = copy all, v2 = task-scoped selection (open design question in FEAT-1A5E).

### Confidence test

- Re-scaffold Forge via `guardkit render langchain-deepagents-orchestrator
  --diff-only` and verify output matches the hand-scaffold from day one. That
  is the test that says the automated path produces the same result as the
  manual one.

---

## 6 — What the Architect must decide

Deliverables from the `/system-arch` session:

### 6.1 Library API

Proposed signatures, error modes, conflict-handling semantics. Minimum:
- Single-file render function
- Tree render function (walks + resolves + renders + writes)
- Dry-run mode (returns plan without writing)
- Placeholder validation (strict? fail-on-unknown?)

### 6.2 Manifest schema

- Complete Pydantic model for the `pattern_layer` section
- JSON Schema export for template-author validation
- Resolution rules (placeholder defaults, target-path templating, skip semantics,
  extension inheritance)
- Versioning strategy (`schema_version` vs `pattern_layer_version`)

### 6.3 Command surface(s)

- `guardkit render` — full flag design (`--output-dir`, `--dry-run`, `--diff`,
  `--force`, `--placeholder key=value`)
- Explicit non-surfaces: `init --with-scaffold` is rejected unless the
  Architect has strong evidence to re-open TASK-INST-010. State the
  rationale either way.
- Interaction with `init`: none (separate command) — but `init` reads the
  manifest for its diagnostic summary. Confirm this boundary.

### 6.4 FEAT-1A5E interaction contract

- Explicit statement that FEAT-1A5E's Player-context injection uses the same
  `guardkit.rendering` library + same manifest contract — no divergent
  layout resolution
- Open questions FEAT-1A5E still owns (v1 vs v2 task-scoped pattern selection,
  rule-prune reconsideration, prompt wording for Player)
- Sequence: does FEAT-1A5E wait for the library + manifest, or run in parallel?

### 6.5 Migration plan

- LCL-003's shim → library (straightforward swap once library ships)
- Three langchain-deepagents templates → manifest form (concrete task list)
- Remaining 7 builtin templates → manifest form (dotnet-railway-fastendpoints,
  fastapi-python, etc.) — bulk backfill plan
- Backwards compatibility: do templates without a `pattern_layer` section
  work? (Probably yes — render silently does nothing. But state it explicitly.)

### 6.6 Scope boundaries (what this architecture does NOT own)

State clearly to prevent scope creep:

- Jinja2 evaluation for `.j2` files with real Jinja expressions — out of scope
  unless the Architect argues it belongs here
- Renaming `templates/` → `patterns/` directory (TASK-REN-B9F2) — decide
  whether this is entangled or orthogonal
- Placeholder inference / interactive Q&A (`guardkit init --interactive`) —
  out of scope; `render` takes placeholders as args
- Template creation tooling (`/template-create`) — it produces pattern-layer
  files today; it does NOT need to change unless the manifest schema requires
  producers to emit the manifest section

---

## 7 — Evidence pointers for the Architect

| Claim / context | File | Lines |
|-----------------|------|-------|
| `_SKIP_DIRS` is doc-only | [guardkit/cli/init.py](../../../guardkit/cli/init.py) | 56 |
| `apply_template` allow-list walks 4 paths | [guardkit/cli/init.py](../../../guardkit/cli/init.py) | 920-1146 |
| `init` summary does not mention pattern layer | [guardkit/cli/init.py](../../../guardkit/cli/init.py) | 1592-1626 |
| Config-layer-only decision | [tasks/design_approved/TASK-INST-010-reconcile-init-paths.md](../../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md) | 56 |
| Config-layer reaffirmation | [.claude/reviews/TASK-REV-A5F8-review-report.md](../../../.claude/reviews/TASK-REV-A5F8-review-report.md) | §0, §1 |
| R4 source (this effort's origin) | [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md) | §R4, §R2 |
| LCL-003 prototype `_render_template` | [tests/integration/test_template_render_import.py](../../../tests/integration/test_template_render_import.py) | 390-485 |
| `_RENDER_IMPL` sentinel | [tests/integration/test_template_render_import.py](../../../tests/integration/test_template_render_import.py) | 458 |
| Per-template layouts (`_LCD_LAYOUT`, `_LCDO_LAYOUT`, `_LCDWE_LAYOUT`) | [tests/integration/test_template_render_import.py](../../../tests/integration/test_template_render_import.py) | 153-253 |
| FEAT-1A5E scope | [tasks/backlog/template-pattern-layer/TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md](../../../tasks/backlog/template-pattern-layer/TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md) | full |
| Directory-rename proposal | [tasks/backlog/template-pattern-layer/TASK-REN-B9F2-rename-templates-to-patterns.md](../../../tasks/backlog/template-pattern-layer/TASK-REN-B9F2-rename-templates-to-patterns.md) | full |

---

## 8 — Invocation

Run the session with:

```bash
/system-arch --context docs/research/pattern-layer-rendering/SCOPE-system-arch-pattern-layer-rendering.md
```

Expected outputs written to `docs/architecture/` (or wherever the Architect
writes, per project convention):
- `DESIGN-PAT-RENDER-001-architecture.md` — the architecture document
- `ADR-PAT-RENDER-001-library-first-sequencing.md` — the sequencing decision
  record
- `ADR-PAT-RENDER-002-manifest-schema.md` — manifest schema decision record
- (optionally) `DESIGN-PAT-RENDER-001-visual-architecture.md` — diagrams

Once those are in hand, the implementation work is filed as one or more
`/feature-plan` sessions, each scoped to a distinct deliverable from §5:

- `/feature-plan "extract guardkit.rendering library from LCL-003 prototype"`
- `/feature-plan "pattern_layer manifest schema + migration of langchain-deepagents templates"`
- `/feature-plan "guardkit render CLI command"`
- FEAT-1A5E remains the Player-context feature on its own track

---

## 9 — What this document deliberately does NOT do

- **Does not pick an option.** The Architect picks or combines.
- **Does not write library code.** That is implementation, after architecture.
- **Does not design the manifest schema in final form.** §4 is a straw man.
- **Does not commit to the `guardkit render` flag shape.** §5 names flags only
  as the ask to the Architect.
- **Does not resolve TASK-REN-B9F2.** The rename is orthogonal to the rendering
  architecture and is called out as a scope question, not a decision.

This is the honest path: use `/system-arch` to design the rendering
architecture, review the output, then file implementation features from it.
Exemplar-before-template — don't design the pattern, produce an architecture,
harvest the pattern from what actually ships.
