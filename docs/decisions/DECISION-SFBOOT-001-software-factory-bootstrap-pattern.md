# DECISION-SFBOOT-001 — Software Factory Bootstrap Pattern

**Status:** Accepted
**Date:** 2026-04-18
**Author:** Rich (pair-programmed with Claude Opus 4.7 in Claude Desktop)
**Scope:** How new repos are bootstrapped within the Software Factory.
**Supersedes:** Draft `/system-arch` session on pattern-layer rendering architecture
(abandoned mid-flight 2026-04-18 after zoom-out)

---

## Summary

**New Software Factory repos are bootstrapped by the AutoBuild Player
producing scaffold files as the natural output of the first feature build,
using pattern-layer `.template` files and — over time — exemplar repos as
reference context.**

The scaffold is not a setup step that precedes feature work. The scaffold
is a side effect of the first feature build. Bootstrap and build are the
same operation.

This supersedes three alternatives considered and rejected:

- **Extending `guardkit init` to render scaffolds** (Option B / "A1" in the
  zoom-out discussion) — violates the config-layer-only boundary settled in
  TASK-INST-010 and re-affirmed in TASK-REV-A5F8. Rejected on architectural
  grounds.
- **Building `guardkit render <template>` as a new rendering command**
  (R4 of TASK-REV-A925 / Option A) — solves a narrower problem than A4,
  requires a manifest schema and a library, duplicates what the pattern
  layer already is, and creates per-template investment inequality.
  Rejected in favour of A4.
- **`guardkit new <template>` as an exemplar-clone command** (Option A3 in
  the zoom-out discussion) — still treats scaffolding as a pre-work setup
  step. Cheaper than the rendering path but locks in a pre-Software-Factory
  mental model. Rejected in favour of A4.

---

## 1. Context

### 1.1 The immediate trigger

On 2026-04-18 while bootstrapping the Forge repo from
`langchain-deepagents-orchestrator`, we observed that `guardkit init` left
the repo without its scaffold files (`pyproject.toml`, `AGENTS.md`,
`agent.py`, `langgraph.json`). Initial diagnosis treated this as a rendering
bug in `guardkit-init`. `/task-review` (TASK-REV-A925) corrected the
diagnosis: `guardkit init` is config-layer-only by design; the
`templates/` tree inside each template package is a **pattern layer** that
has no runtime consumer today.

### 1.2 The wider question that emerged

Closing the gap raised a bigger question: **what IS the bootstrap flow for
a new Software Factory repo?** Four candidate shapes were considered:

- **A1. Rendering layer** — `guardkit init X` or `guardkit render X`
  materialises scaffold files from `.template` sources into the consumer
  repo. Requires a library, manifest schema, and per-template manifest
  authoring. About 4–5 days of work across 10 templates.
- **A2. Manual exemplar copy** — user clones the canonical exemplar, modifies
  by hand. No automation; no audit trail.
- **A3. `guardkit new <template>`** — codifies A2 as a command. Clones
  exemplar, substitutes placeholders, initialises config layer. About
  half a day of work.
- **A4. AutoBuild produces the scaffold as a feature build output** —
  the scaffold is not bootstrapped separately; it emerges from the first
  `/feature-build` execution. FEAT-1A5E (pattern-layer → Player context)
  is the prerequisite. The `/task-review` exemplar-reference pattern
  generalises this into reference-guided generation.

**A4 is the chosen direction.**

### 1.3 Why this decision was nearly missed

The zoom-out that produced A4 nearly didn't happen. The immediate engineering
reflex on hitting the Forge scaffold gap was to propose a rendering layer
(A1) — that's the shape of problem that has clean abstractions. A
`/system-arch` session was commissioned to design it; the Architect was
mid-way through a 7-phase design pass. A zoom-out question from Rich —
"what about the other 7 templates? there will be inequality" — surfaced
A3 as a cheaper path. A further zoom-out — "is this scaffolding question
really the right one?" — surfaced A4 as the architecturally correct path.

The `/system-arch` session was cancelled mid-flight. Captured as a lesson
in §5.

---

## 2. Decision

### 2.1 What we're doing

**The scaffold for a new Software Factory repo is produced by the first
AutoBuild run.** The flow is:

1. User creates an empty repo and runs `guardkit init <template>` to lay
   down the config layer (unchanged from today).
2. User populates the standard design-first artefacts: research documents,
   build plan, and the outputs of `/system-arch` → `/system-design`.
3. User runs `/feature-spec` → `/feature-plan` on the first feature.
4. `/feature-build` (AutoBuild) executes. The Player produces the feature
   code AND the supporting scaffold (`pyproject.toml`, `AGENTS.md`,
   package structure, entry points) in a single build pass, guided by
   pattern-layer reference material.

This is enabled by two downstream pieces of work:

- **FEAT-1A5E** — pattern-layer files wired into AutoBuild's Player context.
  The Player has access to `.template` files as reference material during
  a build. Already scoped and in the backlog.
- **Reference-guided generation** (new concept introduced here) — the
  Player can cite and selectively adapt from arbitrary reference sources:
  pattern-layer files, exemplar repos, previously-built sibling repos.
  This is the generalisation of FEAT-1A5E. See §3.

### 2.2 What we're NOT doing

- **Not building a rendering library** (Option A1). The pattern layer
  stays as reference material consumed by the Player, not as source for
  a dedicated renderer.
- **Not building a manifest schema** for the pattern layer today. If a
  future consumer needs declarative rendering, it can be added at that
  point. Speculation costs abstraction.
- **Not building `guardkit render`** as a command. Deferred indefinitely;
  may never be needed if FEAT-1A5E delivers.
- **Not building `guardkit new <template>`** as a command. The exemplar-clone
  flow is still useful as a manual workflow (see §4), but codifying it as
  a command is unnecessary once A4 ships.
- **Not changing `guardkit init`**. Config-layer-only remains the contract.
  The R2 recommendation from TASK-REV-A925 (summary enumerates pattern-layer
  file count) is still worth doing, but it's decoration, not architecture.

### 2.3 Scope of this decision

This decision covers **new-repo bootstrap**. It does not cover:

- Adding new features to an existing Software Factory repo (already handled
  by `/feature-spec` → `/feature-plan` → AutoBuild)
- Modifying an exemplar repo (already handled by direct editing + re-running
  `/template-create` if the template needs updating)
- Template creation itself (`/template-create`, owned separately)

---

## 3. The reference-guided generation pattern

### 3.1 The insight

A human engineer bootstrapping a new project doesn't render a scaffold from
placeholders. They find a reference implementation they trust, read its
structure, and produce analogous structure for their new project — adapted
to the current requirements. The reference is a **source of pattern**, not
a source of files.

The Software Factory's Player should work the same way. Given a feature to
implement and a set of reference sources, the Player should:

1. Read the reference sources to extract relevant patterns
2. Produce new code that applies those patterns to the current feature
3. Cite the reference source in the build output for auditability

### 3.2 Reference sources

Three classes of reference, in ascending order of richness:

- **Pattern-layer `.template` files** — canonical snippets showing "this is
  how a `pyproject.toml` is structured for this stack" or "this is the
  factory guard pattern." Already present in every template. Closest to
  today's state. FEAT-1A5E wires these into Player context.
- **Exemplar repos** — full working implementations of a stack or pattern
  (`deepagents-player-coach-exemplar`,
  `deepagents-tutor-exemplar`, fastapi-python's origin project, etc.).
  Already exist as the origin of every template. The Player can read them
  as reference material via a future `--reference <repo>` flag on
  `/feature-build`.
- **Previously-built sibling repos** — once the Software Factory has
  produced N repos, those repos become reference material for subsequent
  builds. The Forge references nats-core's patterns; the next orchestrator-
  style agent references the Forge; and so on. The factory's output
  becomes its own input.

### 3.3 `/task-review` as an introspection primitive

`/task-review --mode=architectural` already inspects a codebase and
extracts patterns. Pointed at an exemplar, it produces exactly the kind
of structured reference the Player would benefit from consuming during a
build. This is a future direction, not a commitment — but it's worth
noting that the primitive exists and has a natural place in the
reference-guided generation architecture.

### 3.4 Implications

- **Equality across templates becomes free.** Every template already has
  pattern-layer files and an exemplar repo. Player-context wiring is a
  one-time investment in AutoBuild, not a per-template investment.
- **Pattern layer becomes more valuable over time, not less.** As the
  factory builds more repos, the reference-source pool grows. Each new
  repo inherits from a richer set of patterns than the last.
- **`/template-create` retains its role** — when a pattern proves itself
  across multiple repos, it gets harvested into a template. Template is
  the stable form; exemplars are the proving ground. Same methodology
  already in use.

---

## 4. Interim workflow (before FEAT-1A5E ships)

FEAT-1A5E hasn't been built yet. Until it ships, new-repo bootstrap uses
a manual version of A4:

1. `guardkit init <template>` — config layer (unchanged).
2. Research and planning phase (unchanged) — `/system-arch`,
   `/system-design`, `/feature-spec`, `/feature-plan`.
3. **Manual hand-scaffold from pattern layer** for the files the first
   feature needs (`pyproject.toml`, `AGENTS.md`, etc.). This is the
   TASK-FORGE-SCAFFOLD path for the Forge specifically. About 30–60
   minutes.
4. `/feature-build` on the first feature — proceeds as normal against the
   hand-scaffolded baseline.

Once FEAT-1A5E ships, step 3 goes away — the Player produces the scaffold
as part of step 4.

---

## 5. Process lesson captured during this decision

This decision document is paired with a lesson capture because the process
of reaching it was itself instructive.

### 5.1 What happened

The Forge scaffold gap surfaced an engineering question: "How do we close
this?" The initial response reached for a **technically interesting solution**
(a rendering library with manifest schema, clean abstractions, obvious
architectural shape). A full `/system-arch` session was commissioned. The
Architect had loaded context and was proposing a 7-phase design flow when
a zoom-out question surfaced A3 as a cheaper alternative, and a further
zoom-out surfaced A4 as the architecturally correct one.

### 5.2 The failure mode

**Engineering reflex pattern-matched on the shape of the problem, not on
whether solving that problem was the right thing to do.** The rendering-
layer shape is clean, familiar, and has obvious abstractions. It reads as
an architecture problem. It isn't — it's a workflow problem that the
Software Factory's own workflow (A4) already addresses.

Claude, pair-programming with Rich, proposed the rendering architecture
and wrote a scope document for it without asking "would the boring solution
work?" or "is the scaffolding question really the right question?" Those
questions came from Rich, not from the engineering side.

### 5.3 The gate that caught it

Rich's zoom-out happened mid-way through the `/system-arch` session, when
the Architect had loaded the scope doc and proposed the 7-phase flow. The
specific prompt: "if we do this for the three langchain-deepagents templates,
what about the other 7? there will be inequality."

That question forced a scope re-examination, which surfaced A3. A follow-on
zoom-out from Rich — "maybe we should use a similar approach to the exemplars"
— surfaced A4. The architecture session was cancelled.

### 5.4 What to do about it

**Add a "boring-solution check" to the start of every `/system-arch` session.**
Before the Architect loads the full flow, it should ask: "What's the simplest
thing that could work? Why isn't that enough?" If the answer is "it's enough
but less architecturally interesting," stop — ship the simple thing.

This applies both to human-driven architecture sessions and to AutoBuild-
generated architecture proposals. It's a specific form of the structural
assumption detection pattern already documented (PHANTOM, UNGROUNDED,
SCOPE_CREEP, MISSING_TRADEOFF): **MISSING_SIMPLE_ALTERNATIVE**. The
Architect is biased toward interesting solutions because that's what
well-formed architectural thinking looks like. The bias needs an explicit
counterweight.

### 5.5 Capture for LES2

This incident is primary evidence for LES2 alongside the TASK-REV-A925
incident:

- **TASK-REV-A925**: Template passed review at source level, install
  succeeded, init reported success, consumer surface was wrong — the
  two-layer model (config-layer `init`, pattern-layer templates) was
  invisible at the init boundary. Category A diagnostic-trail failure.
- **This incident**: Engineering reflex proposed an architectural
  solution to a workflow problem. The `/system-arch` session was
  commissioned before the "is this the right problem?" gate had been
  applied. New category: **MISSING_SIMPLE_ALTERNATIVE**.

Both belong in `cross-agent-lessons-from-forge-build.md` once FEAT-1A5E
ships and the full bootstrap-via-AutoBuild pattern has been proven.

---

## 6. Immediate actions

### 6.1 Today

- **Cancel the `/system-arch` session on pattern-layer rendering.** It was
  about to produce a design for a layer we're no longer building. Tell the
  Architect: "Session cancelled — architectural direction changed. See
  DECISION-SFBOOT-001."
- **Proceed with TASK-FORGE-SCAFFOLD.** The hand-scaffold for the Forge is
  unchanged — it's the interim-workflow §4 step 3 for the Forge specifically.
  30–60 minutes.
- **Accept the guardkit-side implementations from TASK-REV-A925.** R2 (init
  summary enumerates pattern-layer file count), R3 (LCL-003 coverage
  extension to `-orchestrator` and `-weighted-evaluation`), R5 (two-layer
  model documentation). R1 is replaced by TASK-FORGE-SCAFFOLD. R4 is
  superseded by this decision — mark as cancelled with reference to
  DECISION-SFBOOT-001.

### 6.2 Next

- **Revisit FEAT-1A5E priority.** Previously framed as "pattern-layer
  consumer for AutoBuild Player context." Now framed as "the load-bearing
  enabler for all new-repo bootstrap in the Software Factory." Priority
  should reflect this — it's on the critical path for every subsequent
  repo, not just a nice-to-have enrichment for AutoBuild.
- **Capture the reference-guided generation concept** as a design note
  for FEAT-1A5E v2. The v1 implementation wires pattern-layer files into
  Player context; v2 extends to exemplar repos and sibling repos; v3 uses
  `/task-review --mode=architectural` as an introspection primitive. This
  is speculative but worth recording while the concept is fresh.

### 6.3 Open for revisit

- **The pattern layer's file format and conventions.** Once FEAT-1A5E
  ships and the Player is consuming pattern files, observations from real
  builds may reveal that the pattern layer needs restructuring — for
  example, richer metadata on each `.template` file, or a split between
  "copy-as-is" snippets and "here's the pattern, apply to your case"
  examples. Capture observations during FEAT-1A5E implementation and
  early consumer builds; revisit the pattern layer's structure based on
  evidence.
- **The `.template` / `.j2` convention.** Currently undecided. The
  rendering-layer `/system-arch` was going to formalise this. Deferred
  until FEAT-1A5E implementation reveals whether the distinction matters
  in practice.

---

## 7. References

- `guardkit/.claude/reviews/TASK-REV-A925-review-report.md` — immediate
  trigger; establishes that `guardkit init` is config-layer-only by design
- `guardkit/.claude/reviews/TASK-REV-A5F8-review-report.md` — 11 April 2026
  decision to not extend `init` with rendering
- `guardkit/.claude/reviews/TASK-REV-LES1-review-report.md` — LCL-003
  smoke test that proved the renderer works but is in the wrong home
- `guardkit/tasks/backlog/FEAT-1A5E-*` — pattern-layer → Player context
  feature, now on the critical path
- `forge/tasks/backlog/TASK-FORGE-SCAFFOLD-hand-scaffold-from-orchestrator-template.md`
  — interim-workflow execution for the Forge specifically
- `forge/docs/research/ideas/forge-build-plan.md` — the build plan that
  consumes this decision's outcome

---

*Decision accepted: 2026-04-18*
*Scope: All new repos bootstrapped within the Software Factory.*
*"The scaffold isn't a starting point; it's the output of the first feature
build."*
