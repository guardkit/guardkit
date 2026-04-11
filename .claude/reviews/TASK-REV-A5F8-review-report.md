# Review Report: TASK-REV-A5F8

**Title**: Analyse TASK-REV-D0C1 follow-ups — scaffolding model and Exemplar references
**Mode**: Architectural review (decision analysis)
**Depth**: Standard
**Completed**: 2026-04-11
**Revised**: 2026-04-11 (post-[R]evise — Software Factory reframing)

## Executive Summary

> **Revision note**: The first draft of this review framed GuardKit as a "lightweight task workflow system" and concluded the scaffold `.template` files under each template's `templates/` subdirectory were best treated as reference material for agent `-ext.md` cross-references. That framing was stale. GuardKit is becoming a **Software Factory** (Ideation → Product Owner → Architect → GuardKit Factory → Build Agent), and the scaffold files are **build-time patterns intended to be consumed by the AutoBuild Player** during feature implementation. This revision updates the recommendations accordingly. See revision summary at the end of this section.

The two TASK-REV-D0C1 follow-ups are independent in scope but share a common root cause: GuardKit templates contain **two distinct layers** and only one of them has a live consumer today.

1. **Config layer** (`.claude/`, `agents/`, `manifest.json`, `settings.json`, `CLAUDE.md`, `README.md`) — consumed by `guardkit init`. Working as designed.
2. **Pattern layer** (`templates/*.template` — stack-specific scaffold patterns produced by `/template-create`) — **has no active consumer**. TASK-INST-010 (2026-03-02) severed the previous consumer (`agentic_init`) as part of an init reconciliation and never replaced it. Six weeks later, `/template-create` is still emitting these files and **nothing reads them**. They are not dead — the intended consumer is the AutoBuild Player, and that wire is missing.

This is not a docs gap. It is an **architectural hole** in the Software Factory pipeline. The Player runs in an isolated git worktree and currently receives:
- Task plan, acceptance criteria, task description
- A pruned `.claude/rules/` set of **4 files only** (`autobuild.md`, `anti-stub.md`, `hash-based-ids.md`, `testing.md`) — confirmed at [autobuild.py:1172-1215](../../guardkit/orchestrator/autobuild.py#L1172) and [autobuild.py:210-215](../../guardkit/orchestrator/autobuild.py#L210)
- **Zero stack-specific patterns**. All `patterns/`, `guidance/`, code-style, and testing-stack rules beyond the 4 essentials are aggressively pruned from the worktree to "reduce context size... freeing ~11.5K tokens per Player/Coach turn".
- **Zero scaffold templates**. `.template` files were never copied into the worktree because `_SKIP_DIRS` excludes them at `init` time and the worktree is created from the initialized project, not the source template package.

The Player is therefore walking into feature implementation blind to the stack's canonical patterns. The scaffold `.template` files — `templates/api/router.py.template`, `templates/components/create-entity.tsx.template`, `templates/endpoints/endpoints/CreateCustomer.cs.template`, etc. — are exactly the "do it like this" reference the Player needs, and they already exist. They just need to be wired in.

### Revised decisions

| Follow-up | Recommendation | Priority | Dependency |
|-----------|----------------|----------|------------|
| **NEW: TASK-DRF-PLAYER-PATTERNS** | **Wire template `.template` files into AutoBuild Player context as stack-pattern guidance during feature implementation.** This is the architectural fix and the primary deliverable of this review. | **High** | None — can start after Player context-loading audit |
| TASK-DRF-F4B8 | **Close original; replace with F4B8a** (documentation of the two-layer model reframed as config + pattern, all 10 templates) and **F4B8b** (rename decision, deferred) | Medium | Should land after PLAYER-PATTERNS is scoped so the docs describe the real consumer |
| TASK-DRF-E7A2 | **Proceed as filed; standalone task** — unchanged | Low | Independent |

**Ordering**: PLAYER-PATTERNS is the highest-value work and should be scoped first (feature-plan level; see Section 1 revised). F4B8a docs can start in parallel with PLAYER-PATTERNS scoping but should not ship until the wiring approach is at least design-approved, so the documentation describes the real consumer rather than a future intent. E7A2 is fully independent and can land any time.

**Gating question answered (unchanged)**: The restriction of `guardkit init` to the config layer was **deliberate**, added by TASK-INST-010 on 2026-03-02 with the one-line rationale "code scaffold generation is a separate concern". The historical analysis holds. What changes in this revision is the interpretation of "separate concern": the right consumer is the AutoBuild Player, not `guardkit init`. The TASK-INST-010 author was correct to keep `init` as a config-layer installer; they just did not follow through on the pattern-layer consumer. This review is filing that follow-through.

### Revision summary (what changed between drafts)

| Section | Original framing | Revised framing |
|---------|------------------|-----------------|
| Positioning | "Lightweight, pragmatic task workflow system" | Software Factory (Ideation → PO → Architect → GuardKit Factory → Build Agent) |
| Scaffold file purpose | Reference material for agent `-ext.md` cross-references | Build-time stack patterns for AutoBuild Player |
| Missing consumer | None — files are valuable as docs | **AutoBuild Player context loader** |
| F4B8 option 1 recommendation | Document as reference material | Document as pattern layer; add wire-in follow-up as primary deliverable |
| F4B8 option 2 ("extend init") | Rejected — scope creep into Yeoman territory | **Still rejected — same reason, different framing.** The consumer should be the Player in an isolated worktree, not `init` in the user's working directory. `init` remains config-layer. |
| F4B8 option 3 (delete files) | Rejected — breaks agent `-ext.md` references | **Even more strongly rejected** — deletes the canonical pattern library the Player needs |
| New finding | — | AutoBuild prunes worktree `.claude/rules/` to 4 files (confirmed at [autobuild.py:1172-1215](../../guardkit/orchestrator/autobuild.py#L1172)) — Player has zero stack context today |
| New primary recommendation | — | **TASK-DRF-PLAYER-PATTERNS**: wire scaffold templates into Player context |

---

## Section 0 — Historical Analysis (the gating question)

**Question**: Was restricting `guardkit init` to copying only `.claude/` a deliberate architectural decision, and does the original rationale still apply?

**Answer**: **Yes, deliberate — but the rationale is thin and unreviewed.**

### The commit and the task

The current behavior is enforced by two lines in [guardkit/cli/init.py:50-51](../../guardkit/cli/init.py#L50):

```python
# Directories that should NOT be copied from templates (code scaffold concerns)
_SKIP_DIRS = {"templates", "config", "docker"}
```

`git blame` pins this to commit `e00fda0d3b` (2026-03-02 21:56 UTC), which is an AutoBuild checkpoint commit. The underlying task is **[TASK-INST-010](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md) — Reconcile guardkit init and agentic_init template application paths** (Richard Woollcott, 2026-03-02, 5 weeks ago, part of FEAT-INST, parent review TASK-REV-2FE2).

### What the task says (verbatim)

> **Skip code scaffolds**: Do NOT copy `{template}/templates/`, `{template}/config/`, or `{template}/docker/` directories (code scaffold generation is a separate concern)
>
> — [TASK-INST-010-reconcile-init-paths.md:56](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md#L56)

### Reconstructed timeline

1. **Original state (≤2026-03-01)**: Two divergent init paths existed:
   - `guardkit init <template>` — Python CLI. Created empty directory scaffolds only (`.claude/`, `tasks/`, `.guardkit/`). Copied **nothing** from the template.
   - `agentic_init` (`installer/core/commands/lib/agentic_init/command.py`) — Copied `manifest.json`, `settings.json`, `CLAUDE.md`, agents, **and** code-scaffold templates from `installer/core/templates/{template}/`.

2. **2026-03-02**: TASK-INST-010 reconciled these two paths into `guardkit init` as the single authoritative command. The task added:
   - Agent copying (from both `agents/` and `.claude/agents/`)
   - Rule copying (preserving `.claude/rules/` directory structure)
   - CLAUDE.md copying (both root and `.claude/` variants)
   - manifest.json copying
   - **Explicit exclusion** of `templates/`, `config/`, `docker/` via `_SKIP_DIRS`

3. **2026-03-02 → 2026-04-11 (today)**: `_SKIP_DIRS` has not been touched by any non-checkpoint commit (`git log -S '_SKIP_DIRS' -- guardkit/cli/init.py` returns only the autobuild checkpoint). The "code scaffold generation is a separate concern" carve-out has never been revisited.

4. **Today (2026-04-11)**: TASK-REV-D0C1's smoke test rediscovered the gap.

### Was it deliberate? Was the rationale sound?

**Deliberate: yes.** The task spec explicitly lists skipping scaffolds as a requirement, not an omission. The `_SKIP_DIRS` constant is named to match and has a comment labeled "code scaffold concerns".

**Well-justified: no.** The task gives exactly one phrase of rationale: "code scaffold generation is a separate concern". There is no:
- Design document or ADR justifying the two-layer split
- Decision between "delete scaffold dirs from templates" vs "keep them unused" vs "support them later"
- User-facing documentation explaining that `init` is a config-layer installer
- Backlog task for the deferred "separate concern"

Note also that the predecessor path (`agentic_init`) **had been copying scaffold templates**. So TASK-INST-010 was not preserving existing behavior — it actively removed functionality that had existed. This move was made inside a feature focused on AutoBuild instrumentation (FEAT-INST, parent review TASK-REV-2FE2 which, per `grep`, does not itself mention init or scaffolds), not in a review focused on template architecture. This is consistent with the task author's recollection of "feeling uneasy about it at the time" — it was a subsidiary decision buried in an instrumentation feature, not a reviewed architectural call.

**Does the rationale still apply? (revised)** **Partially yes, partially no.**

- **Yes** on `init` staying config-layer. Extending `init` to materialize scaffold templates into the user's working directory is still the wrong answer — it puts the pattern library in the wrong place (user-editable files, staled instantly, irrelevant to most features), and `init` runs once at project setup while patterns want to be read by an autonomous agent many times during feature builds. TASK-INST-010's decision to keep `init` as a config-layer installer was correct.
- **No** on "separate concern" meaning "unscoped indefinitely". The author's one-line rationale read as a punt, and the task-author of this review (TASK-REV-A5F8) was correct to flag that it felt wrong. The right consumer exists — it is the **AutoBuild Player** — and it has been there the whole time, walking into feature implementation without any stack-specific pattern context. The "separate concern" was never actually picked up as follow-up work, and the pattern layer has been silently producing output for a consumer that was never built.

**Verdict (revised)**: Defend the `init` decision, but **do not** defend the overall framing of "lightweight config installer, scaffolds are separate". The Software Factory pipeline *is* supposed to consume these files — just not at `init` time. Filing TASK-DRF-PLAYER-PATTERNS to wire them into the Player is the architectural close-out that TASK-INST-010 elided.

---

## Section 1 — F4B8: Scaffolding Model Decision

### Current behavior of `guardkit init`

Verified from [guardkit/cli/init.py:50-51](../../guardkit/cli/init.py#L50), [guardkit/cli/init.py:535-672](../../guardkit/cli/init.py#L535) (copy helpers), and [guardkit/cli/init.py:960-1013](../../guardkit/cli/init.py#L960) (apply_template loop).

`init` copies, from a template dir:
- `.claude/CLAUDE.md` **or** root `CLAUDE.md`
- `.claude/rules/**/*.md` (preserving directory structure)
- `agents/*.md` **or** `.claude/agents/*.md`
- `manifest.json` → `.claude/manifest.json`

`init` explicitly skips: `templates/`, `config/`, `docker/` (via `_SKIP_DIRS`).

### Universal pattern discovery — **F4B8 is mis-scoped**

**The task description treats this as a dotnet-railway-fastendpoints oddity. It is not.** Checking all 10 builtin templates:

| Template | `templates/` subdirectory contents |
|----------|------------------------------------|
| `default` | empty |
| `fastapi-python` | api, config, core, crud, db, dependencies, models, schemas, testing |
| `fastmcp-python` | config, resources, server, testing, tools |
| `langchain-deepagents` | other, testing |
| `mcp-typescript` | prompts, resources, server, testing, tools |
| `nats-asyncio-service` | handlers, infrastructure, other, services, testing |
| `nextjs-fullstack` | actions, api, app, components, lib, prisma, tests, + `workflows-ci.yml.template` |
| `python-library` | src |
| `react-fastapi-monorepo` | apps, docker |
| `react-typescript` | api, components, mocks, routes |
| `dotnet-railway-fastendpoints` | 20 `.cs.template` files across 10 layer subdirs |

**Every non-trivial builtin template ships `.template` scaffold files that `init` silently ignores.** This is not a dotnet quirk; it is how `/template-create` emits templates and has been since TASK-INST-010 severed the consumer.

This means F4B8 as filed **understates the scope by 10×**. Any decision must be applied consistently across all templates, or the mismatch will recur every time a new template is registered.

### Producer/consumer mismatch — the missing Player wire

Verified from [installer/core/lib/template_generator/template_generator.py](../../installer/core/lib/template_generator/template_generator.py) that `/template-create`'s `TemplateGenerator` class is what produces `.template` files (via the `generate()` method), writing them into the `templates/` subdirectory of a new template package. The docstring says: "Generates .template files from example code files using AI to intelligently extract placeholders while preserving code structure and patterns."

So the current state is:
- **Producer**: `/template-create` (actively used) → writes `templates/*.template` stack patterns
- **Config-layer consumer**: `guardkit init` → copies `.claude/`, `agents/`, manifest, etc. **Deliberately does NOT copy scaffold templates** (TASK-INST-010). ✅ Correct — config-layer installer, not a scaffolder.
- **Pattern-layer consumer**: ~~`agentic_init`~~ (removed 2026-03-02) → **should be the AutoBuild Player, not replaced yet**
- **Incidental secondary consumer**: `/agent-enhance --hybrid` reads these files when generating agent `-ext.md` guidance examples (confirmed in TASK-REV-D0C1 review: the dotnet agent `-ext.md` files contain explicit cross-references like ``templates/tests (e2e)/factories/ExemplarApiFactory.cs.template``). This is valuable but not the primary consumer.

**What the Player actually gets today** (verified from [autobuild.py:1172-1215](../../guardkit/orchestrator/autobuild.py#L1172)):

```python
AUTOBUILD_ESSENTIAL_RULES: frozenset = frozenset({
    "autobuild.md",
    "anti-stub.md",
    "hash-based-ids.md",
    "testing.md",
})
```

Everything else in `.claude/rules/` is actively deleted from the worktree before the Player turn starts — "~63 KB total → ~17 KB retained — frees ~11.5K tokens per turn". Stack-specific patterns under `.claude/rules/patterns/` and agent guidance under `.claude/rules/guidance/` are both pruned. And `templates/*.template` was never copied in the first place.

**Net**: when the Player starts implementing, say, a new FastEndpoints endpoint in a `dotnet-railway-fastendpoints`-initialized project, it has:
- The task plan and acceptance criteria
- 4 generic rule files (autobuild, anti-stub, hash-based-ids, testing)
- Whatever is in the project's `.claude/CLAUDE.md`
- **No Railway-Oriented Programming pattern reference**
- **No `CreateCustomer.cs.template` to follow as a canonical shape for new endpoints**
- **No `ResultExtensions.cs.template` to show the Result<T> combinator usage**
- **No `ExemplarApiFactory.cs.template` to show Testcontainers wiring for tests**

All of that is sitting in `installer/core/templates/dotnet-railway-fastendpoints/templates/`, and all of it is unreachable. The Player is trying to write idiomatic Railway-Oriented FastEndpoints code from training-data memory of vanilla ASP.NET, not from the codebase's actual canonical shapes. This is a significant quality gap.

Deleting the scaffold files (Option 3) would make this permanent. Documenting them as "reference material" (original Option 1 framing) would accept it. **Wiring them into the Player is the real fix.**

### Evaluation of the original three options (reframed for Software Factory)

#### Option 1 — Document-only (original framing: rejected. Revised framing: partially adopted as F4B8a, reframed)

**Original framing**: Document scaffold files as "reference material for agent `-ext.md` examples".

**Problem with that framing**: It accepts the Player blindness and labels it as the design. It turns a missing wire into a feature. The task author's recollection of "feeling uneasy" about the restriction was correct — the files are not reference material; they are a pattern library waiting for the Player to read them.

**Revised adoption**: Keep the documentation work, but frame the two layers as:
- **Config layer** — consumed by `guardkit init` at project-init time. Installs `.claude/`, `agents/`, manifest, rules.
- **Pattern layer** — consumed by **AutoBuild Player** at feature-build time. Provides stack-specific canonical shapes that inform how the Player writes new code.

With this framing, the documentation is no longer "these files sit unused, here is why". It is "these files are the Player's pattern library, here is how it works", which only becomes true once **TASK-DRF-PLAYER-PATTERNS** (the new primary recommendation) lands or is at least scoped.

**Therefore F4B8a should not ship before PLAYER-PATTERNS is at least at design-approved stage** — shipping docs about a pattern layer that is still not wired would bake in the lie.

#### Option 2 — Extend `guardkit init` to process `templates/*.template` (rejected, unchanged)

**Decision**: Still reject. `init` is the wrong consumer.

**Revised rationale**: Not "out of scope because GuardKit is lightweight" — that framing was stale. Reject because the Player, not `init`, is the right consumer. `init` runs once at project setup in the user's working directory. The Player runs N times per feature in an isolated worktree. Stack patterns want to be read by an autonomous agent during implementation, not materialized as files into the user's working tree where they would be stale, edit-conflict prone, and irrelevant to whatever feature the user is actually working on. `init` remains config-layer as TASK-INST-010 decided. That call was right; it just wasn't the whole picture.

#### Option 3 — Remove the dead scaffold files (rejected, more strongly)

**Decision**: Reject — this would delete the Software Factory's pattern library before it has been wired up.

**Revised rationale**: The first draft argued this would break agent `-ext.md` cross-references (16+ in the dotnet template alone). Still true, but subordinate. The stronger reason is that these files are the **canonical pattern library intended for the Player**. Deleting them means `/template-create` would need to be rebuilt, the entire pattern-extraction pass would have to be re-run across every stack, and the Player would permanently lose access to the ~1,800 lines of enhanced agent guidance that reference specific shapes. This would be throwing away the raw material of the Software Factory's quality fly-wheel right at the moment it was about to be wired up.

#### Option 4 — Restore full-template copying by `init` (considered and rejected, same as draft 1)

Unchanged. Restoring `agentic_init`-style behavior is the wrong direction; the Player, not `init`, is the right consumer.

### **Primary recommendation (NEW): TASK-DRF-PLAYER-PATTERNS**

**Wire template `.template` scaffold files into AutoBuild Player context as stack-pattern guidance during feature implementation.**

This is the architectural fix. It is what the task author's recollection of "something was wrong here" was pointing at. The rest of this review is secondary to getting this task filed, scoped, and planned.

**Scope (indicative, subject to a proper feature plan)**:

1. **Identify the source template** for a given project. Options:
   - Read `.claude/manifest.json` (copied in by `init`) to find the template `name` field
   - Fall back to a `.guardkit/template.yaml` marker, if one exists
   - Fall back to heuristic detection from project files (`pyproject.toml`, `package.json`, `.csproj`)
2. **Resolve the source template's `templates/` subdirectory** from the installed `installer/core/templates/{name}/templates/` path. Use the same `importlib.resources` / `__file__`-relative resolver that `apply_template()` already uses in [guardkit/cli/init.py:460-510](../../guardkit/cli/init.py#L460).
3. **Select the relevant pattern files** for the current task. Naive v1: copy the whole `templates/` tree. Smarter v2: match patterns to the task's expected layer (task mentions "endpoint" → include `endpoints/*.template`; task mentions "repository" → include `infrastructure/repositories/*.template`; etc.). This selection logic can grow incrementally.
4. **Inject into the Player's worktree** at a well-known path, e.g. `.guardkit/patterns/` or `.claude/patterns/`. Do not pollute the user's working tree — the worktree is ephemeral and gets cleaned up per-task. The patterns are for the Player to *read*, not for the user to *maintain*.
5. **Update the Player prompt** (or autobuild.md invariants file) to instruct the Player to consult the pattern library before synthesizing new code: "When implementing against the {{stack}} stack, canonical shapes for this project's layers are in `.guardkit/patterns/`. Read the relevant files before writing new code. Your implementation should match the shapes used in these patterns."
6. **Reconsider the rule-pruning constant** `AUTOBUILD_ESSENTIAL_RULES` at [autobuild.py:210-215](../../guardkit/orchestrator/autobuild.py#L210). The current 4-file essentials list was sized when patterns did not exist. Once patterns are wired, either:
   - Keep the aggressive prune and rely on the `.guardkit/patterns/` injection as the pattern source, OR
   - Relax the prune to also keep `.claude/rules/patterns/` (stack-specific rule files that accompany the `.template` files)

   The token budget concern is real (11.5K tokens per turn) — the right design is probably a **task-scoped selection** of patterns rather than loading them all, so the token cost only grows for tasks that need them.
7. **Measure**: after wiring, instrument Player turns to track whether the pattern files are actually being read (SDK file-access tracking already exists in the instrumentation pipeline per TASK-INST-*). Confirm the patterns are earning their token cost.

**Why this is a feature plan, not a task**: Scoping this properly needs `/feature-plan "Wire template patterns into AutoBuild Player context"`. The indicative scope above touches the Player prompt, worktree setup, instrumentation, and possibly `AUTOBUILD_ESSENTIAL_RULES`. It is not a single file edit.

**Priority**: **High**. This is a correctness/quality gap in the Software Factory pipeline that was obscured by calling it "a separate concern" six weeks ago. Every day it stays unwired, every AutoBuild task is implemented without the stack patterns that the system is designed to provide.

**Dependency on F4B8**: None forward. But F4B8a (docs) should wait for at least a design-approved PLAYER-PATTERNS plan so the docs describe real wiring, not future intent.

### Recommended F4B8 plan (revised)

1. **TASK-DRF-PLAYER-PATTERNS** (NEW, high priority, file as a feature plan or large task)
   - The architectural fix. Wire scaffold templates into Player context.
   - See "Primary recommendation" above for scope.

2. **TASK-DRF-F4B8a — Document the two-layer template model** (medium priority, documentation task)
   - Reframed: config layer (consumed by `init`) + pattern layer (consumed by AutoBuild Player)
   - Update [installer/core/templates/README.md](../../installer/core/templates/README.md) and a `docs/guides/template-layers-guide.md`
   - Add a `templates/README.md` stub to each of the 10 templates explaining the pattern-layer purpose and pointing at PLAYER-PATTERNS
   - Update `/template-create`'s post-generation output to mention that `.template` files feed the Player
   - **Scheduling**: hold until PLAYER-PATTERNS is design-approved, so the docs are truthful

3. **TASK-DRF-F4B8b — Audit and optionally rename `templates/` → `patterns/`** (low priority, deferred)
   - If the name feels misleading, `patterns/` is now the natural target (not `reference/`)
   - Still deferred. Same cross-file coordination cost as before.

4. **Close original TASK-DRF-F4B8** with "superseded by PLAYER-PATTERNS + F4B8a + F4B8b" note.

### On the "broken template_validate_cli.py" side note

The side note in TASK-REV-A5F8 flags that [installer/core/commands/lib/template_validate_cli.py](../../installer/core/commands/lib/template_validate_cli.py) fails with `ModuleNotFoundError: No module named 'global'`. I did not run or fix the CLI (out of scope per the task), but based on the project structure and the existence of `installer/core/commands/template-validate.md` (a Claude Code slash command), the slash-command subagent route is the intended primary path. The Python CLI in `template_validate_cli.py` is likely a legacy artifact from an earlier architecture.

**Recommendation**: file a separate **TASK-FIX-{hash}** to either repair the CLI or formally deprecate/remove it. Not a blocker for anything in this review's scope.

---

## Section 2 — E7A2: Exemplar Reference Cleanup

### Confirmed occurrences

`grep -rn 'Exemplar' installer/core/templates/dotnet-railway-fastendpoints/agents/` returns **27 occurrences across 5 files** (F4B8's filed estimate of "5 files is non-exhaustive" was correct on files, exact on count):

| File | Count |
|------|-------|
| `fastendpoints-endpoint-specialist.md` | 2 |
| `fastendpoints-endpoint-specialist-ext.md` | 9 |
| `xunit-testcontainers-testing-specialist.md` | 5 |
| `xunit-testcontainers-testing-specialist-ext.md` | 8 |
| `keycloak-auth-observability-specialist-ext.md` | 3 |

The scaffold files under `templates/` contain an additional **53 occurrences across 16 files**, but per E7A2's filed "out of scope" clause those are reference material and not touched by init — leave them alone.

### Categorization of the 27 agent-doc occurrences

From sampling the grep results:

| Category | Replacement strategy | Examples |
|----------|---------------------|----------|
| Namespace references (`Exemplar.Core.Functional`, `Exemplar.Core.Errors`, `Exemplar.Orders.Application`, etc.) | Replace with `{{Namespace}}.*` or document neutrally | `using Exemplar.Core.Endpoints;` → `using {{Namespace}}.Core.Endpoints;` |
| File path references (`src/Exemplar.Customers/Endpoints/CreateCustomer.cs`) | Replace with `{{Namespace}}` or generalize | `src/{{Namespace}}.Customers/Endpoints/...` |
| Class name `ExemplarApiFactory` (WebApplicationFactory subclass) | Generalize (`{{ProjectName}}ApiFactory`) or keep as a generic example with a note | `ExemplarApiFactory` → `{{ProjectName}}ApiFactory` (one of the template placeholders) |
| OpenTelemetry service name `"Exemplar.API"` | Replace with `{{ProjectName}}.API` | Line 109 in keycloak-auth-observability-specialist-ext.md |

All 27 occurrences are trivially replaceable. The task is cosmetic but self-contained.

### Is E7A2 worth doing standalone or should it be folded?

**Recommendation: proceed as filed, standalone**. Rationale:
- Complexity 2, truly a one-sitting task
- Independent of F4B8's outcome (see ordering below)
- No other template polish pass is currently planned that it could fold into
- The filed task already has clear acceptance criteria

### Dependency on F4B8 outcome

**None**, given the recommendation to pick F4B8 option 1.

Under option 1 (document), scaffold files stay → E7A2's out-of-scope clause holds as filed → no scope change.

Under the *rejected* option 3 (delete scaffolds), E7A2's scope would shrink because the `templates/` Exemplar references vanish automatically — but that option is not being pursued.

E7A2 can start immediately in parallel with F4B8a.

---

## Section 3 — Cross-Cutting Concerns

### Ordering between follow-ups (revised)

1. **TASK-DRF-PLAYER-PATTERNS** (NEW, high priority) — start here. Needs feature-plan scoping. Everything else about the pattern layer depends on this landing or at least being design-approved.
2. **E7A2 (Exemplar cleanup)** — start immediately, parallel to PLAYER-PATTERNS scoping. Fully independent. No dependency on the pattern-layer architecture. 27 occurrences, 5 files, cosmetic.
3. **F4B8a (documentation, reframed)** — start **after** PLAYER-PATTERNS is design-approved. Reason: the docs should describe real wiring, not future intent. Holding F4B8a for a week or two while PLAYER-PATTERNS is scoped is cheap insurance against shipping a lie in the docs.
4. **F4B8b (rename `templates/` → `patterns/`)** — deferred until bandwidth, same as draft 1. May be worth reconsidering *after* PLAYER-PATTERNS lands — at that point the new name (`patterns/`) is even more naturally justified than the earlier `reference/` candidate.

Partial ordering: PLAYER-PATTERNS design-approved → F4B8a start. E7A2 and PLAYER-PATTERNS scoping are fully parallel.

### Should either follow-up be promoted, deferred, or merged?

- **Promote**: **PLAYER-PATTERNS to high priority** (new task, not F4B8's original scope but surfaced by this review).
- **Re-scope**: **F4B8 → F4B8a (reframed docs) + F4B8b (deferred rename)**.
- **Defer**: F4B8b (rename).
- **Merge**: None.

### New follow-ups surfaced by this analysis

1. **TASK-DRF-PLAYER-PATTERNS** — the primary new deliverable. See Section 1 "Primary recommendation" for indicative scope. Should probably be filed via `/feature-plan` rather than `/task-create` due to its scope.
2. **TASK-FIX-{hash}** — Repair or deprecate `installer/core/commands/lib/template_validate_cli.py` (ModuleNotFoundError: No module named 'global'). Priority: low. Unchanged from draft 1.
3. Verify `TASK-TSE-8A1C-fix-stale-expected-templates-set.md` in backlog is not a duplicate of what this review would otherwise file.
4. Verify `TASK-ISH-3F02-update-legacy-install-sh-template-lists.md` in backlog is not a duplicate of what this review would otherwise file.

---

## Decision Matrix

### F4B8 options (revised)

| Option | Effort | Risk | Software Factory Fit | Recommendation |
|--------|--------|------|----------------------|----------------|
| **NEW: Wire scaffolds into AutoBuild Player** | High (feature plan) | Medium — worktree injection, prompt update, token budget | ✅ **This is the Software Factory's intended pipeline** | ✅ **PRIMARY: TASK-DRF-PLAYER-PATTERNS** |
| 1. Document-only + stub READMEs (original) | Low (~2h docs + 10 stubs) | Low but ships a half-truth if scaffolds remain unwired | ⚠️ Only valid if reframed as "pattern layer" + sequenced after PLAYER-PATTERNS | ✅ **F4B8a (reframed, sequenced after PLAYER-PATTERNS design-approved)** |
| 2. Extend `init` to process scaffold templates | Very High | High — wrong consumer, wrong layer | ❌ `init` is not the Player | ❌ Reject |
| 3. Delete scaffold files | Medium | High — deletes the pattern library the Player needs | ❌ Throws away the Software Factory's raw material | ❌ Reject |
| 4. Restore full-template copying by `init` | High | High — same objections as option 2 | ❌ | ❌ Reject |
| 1b. Rename `templates/` → `patterns/` (was `reference/`) | Medium | Medium — `TemplateGenerator`, `TemplatePathResolver`, agent `-ext.md` cross-refs must be kept in sync | ✅ `patterns/` is even more natural post-PLAYER-PATTERNS | ⏸️ **F4B8b, deferred** |

### E7A2 options

| Option | Effort | Recommendation |
|--------|--------|----------------|
| Proceed standalone | Low (30 min) | ✅ **Recommended** |
| Fold into broader template polish pass | — | ❌ No pass currently planned |
| Defer indefinitely | — | ❌ Already low priority; just do it |

---

## Recommendations (Prioritized)

### Wave 1 — Architectural fix (high priority, start scoping immediately)

1. **TASK-DRF-PLAYER-PATTERNS — Wire template scaffold files into AutoBuild Player context** (NEW primary deliverable)
   - File via `/feature-plan` (scope is feature-sized, not task-sized)
   - Scope: identify source template, resolve `templates/` subdirectory, select task-relevant patterns, inject into worktree at `.guardkit/patterns/` or `.claude/patterns/`, update Player prompt to consult patterns, reconsider `AUTOBUILD_ESSENTIAL_RULES` prune list
   - Primary concerns: token budget (pruning was for ~11.5K/turn savings), task-scoped selection heuristics, measurement
   - Parent review: TASK-REV-A5F8
   - Priority: **high**

### Wave 2 — Cosmetic cleanup (fully independent, start immediately in parallel)

2. **TASK-DRF-E7A2 — Replace Exemplar references in dotnet agent docs** (as filed, unchanged)
   - 27 occurrences in 5 files, all in `installer/core/templates/dotnet-railway-fastendpoints/agents/`
   - Out-of-scope clause for `.cs.template` files holds (scaffold files are now more valuable, not less, under the revised framing — the Player will be reading them)
   - Complexity 2, as filed
   - **Proceed as is**

### Wave 3 — Documentation (medium priority, hold until Wave 1 is design-approved)

3. **TASK-DRF-F4B8a — Document the two-layer template model (config + pattern)**
   - Update [installer/core/templates/README.md](../../installer/core/templates/README.md)
   - Add `docs/guides/template-layers-guide.md` (or equivalent)
   - Add `templates/README.md` stubs in all 10 builtin templates pointing at PLAYER-PATTERNS
   - Update `/template-create` post-generation output
   - **Hold until**: PLAYER-PATTERNS is at least design-approved, so docs describe the real wiring
   - Complexity: 3

4. **TASK-DRF-F4B8-close — Close the original TASK-DRF-F4B8** with "superseded by PLAYER-PATTERNS + F4B8a + F4B8b (deferred)" note. Simple state change.

### Wave 4 — Deferred (low priority, after Wave 1 lands)

5. **TASK-DRF-F4B8b — Rename `templates/` → `patterns/`** (deferred)
   - Requires coordinated edits to `TemplateGenerator`, `TemplatePathResolver`, all 10 templates, agent `-ext.md` cross-references, and the PLAYER-PATTERNS injection code
   - Natural fit post-PLAYER-PATTERNS: the new name matches the new consumer's role
   - Do NOT do this until PLAYER-PATTERNS has landed

### Newly-surfaced (file if not already present)

6. **TASK-FIX-{hash} — Repair or deprecate `template_validate_cli.py`** (priority: low)
7. Verify `TASK-TSE-8A1C` and `TASK-ISH-3F02` are not duplicates of follow-ups from Section 3

---

## Appendix

### Files Referenced

- Gating task (history): [TASK-INST-010-reconcile-init-paths.md](../../tasks/design_approved/TASK-INST-010-reconcile-init-paths.md)
- Parent review of gating task: [.claude/reviews/TASK-REV-2FE2-review-report.md](../../.claude/reviews/TASK-REV-2FE2-review-report.md) — does not discuss init or scaffolds
- Prior init review (context): [.claude/reviews/TASK-REV-INIT-review-report.md](../../.claude/reviews/TASK-REV-INIT-review-report.md) — from 2025-12-11, about the legacy shell-script installer, now superseded
- Parent review (D0C1): [.claude/reviews/TASK-REV-D0C1-review-report.md](../../.claude/reviews/TASK-REV-D0C1-review-report.md)
- Installer CLI: [guardkit/cli/init.py](../../guardkit/cli/init.py) (lines 50-51 for `_SKIP_DIRS`, 535-672 for copy helpers, 960-1013 for apply_template)
- Template generator: [installer/core/lib/template_generator/template_generator.py](../../installer/core/lib/template_generator/template_generator.py)
- Follow-up 1 (F4B8): [tasks/backlog/TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md](../../tasks/backlog/TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md)
- Follow-up 2 (E7A2): [tasks/backlog/TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md](../../tasks/backlog/TASK-DRF-E7A2-replace-exemplar-references-in-agent-docs.md)
- Registered template: [installer/core/templates/dotnet-railway-fastendpoints/](../../installer/core/templates/dotnet-railway-fastendpoints/)

### Evidence: `_SKIP_DIRS` blame

```
e00fda0d3b (Richard Woollcott 2026-03-02 21:56:57 +0000 50) # Directories that should NOT be copied from templates (code scaffold concerns)
e00fda0d3b (Richard Woollcott 2026-03-02 21:56:57 +0000 51) _SKIP_DIRS = {"templates", "config", "docker"}
```

Commit is `[guardkit-checkpoint] Turn 1 complete (tests: pass)` — an AutoBuild checkpoint implementing TASK-INST-010.

### Evidence: no revisions to `_SKIP_DIRS`

`git log --all --oneline -S '_SKIP_DIRS' -- guardkit/cli/init.py | grep -v checkpoint` returns zero non-checkpoint commits. The constant has been untouched since 2026-03-02.

### Evidence: universal `templates/` pattern

All 10 builtin templates under `installer/core/templates/` ship a `templates/` subdirectory with scaffold `.template` files (except `default`, which ships an empty one). Verified by iterating `ls installer/core/templates/{name}/templates/` for each template.

### Corrections to initial exploration

- My first `Glob installer/core/templates/*/templates/` pattern returned "No files found" — this was misleading, not wrong. Glob with a trailing `/` tries to match files, not directories. Subsequent `ls` confirmed 10 templates with `templates/` subdirs. The finding "dotnet is unique" was wrong; corrected in Section 1.
- Initially suspected the TASK-INST-010 "separate concern" rationale would tie back to a parent review recommendation. Grepping [TASK-REV-2FE2-review-report.md](../../.claude/reviews/TASK-REV-2FE2-review-report.md) for `init`, `scaffold`, `reconcile`, `apply_template`, `INST-010` returned zero matches. The parent review did not discuss the init path reconciliation at all — it was a tangential addition inside FEAT-INST. This strengthens the "deliberate but under-justified" verdict.
