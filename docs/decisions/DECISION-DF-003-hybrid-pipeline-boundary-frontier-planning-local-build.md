# DECISION-DF-003 — Hybrid Pipeline Boundary: Frontier Planning, Local Build

**Status:** PROPOSED — preferred direction; challenge only with new evidence
**Date:** 2026-06-10
**Author:** Rich (worked through with Claude in Claude Desktop)
**Companions:** DECISION-DF-001 (stands unchanged — governs the unattended critical path) · DECISION-DF-002 (ledger-based tool selection — the same boundary applied to the commercial ledger)
**Scope:** The GuardKit software-factory pipeline — which stages run attended on frontier models and which run unattended on local inference; and, by direct consequence, the scope of the Forge.
**Related:** `ai-transition/docs/workstream-a-dark-factory-consolidation-scope.md` · `forge/docs/research/ideas/fleet-master-index.md` (superseded framing) · `guardkit/docs/research/autobuild-harness-migration.md` (FEAT-HMIG) · specialist-agent architect-model evals (May 2026) · DDD SouthWest deck, slides 7 & 12

---

## Summary

**The software-factory pipeline is split at a fixed boundary. Ideation, system architecture, design, and feature planning run *attended* on frontier models. Implementation — AutoBuild and its review loops — runs *unattended* on local inference. The Forge orchestrates the local build half only. Full pipeline autonomy (the original "domain goal in, built solution out" Forge premise) is formally deferred, with explicit revisit conditions.**

This is not a rowback of the dark-factory thesis. It is the only configuration that simultaneously satisfies DECISION-DF-001, the quality economics of the planning stages, and the vendor pricing boundary — and it was already the position stated publicly in the DDD SouthWest talk (slide 7's Claude Desktop → Claude Code → Runbooks daily reality; slide 12's "SLMs for operations, LLMs for strategy").

## 1. Context

### 1.1 How the question arose

During March–May 2026 the AutoBuild pipeline matured to the point where a full lifecycle (ideation → `/system-arch` → `/system-design` → `/feature-spec` → `/feature-plan` → AutoBuild) ran with near-zero human intervention — defaults accepted throughout, one correction across seven features. The natural inference was that an agent (the Forge) could drive the entire pipeline autonomously, planning included. The fleet-master-index (April 2026) and the Forge pipeline-orchestrator documents captured that vision: Ideation Agent → Product Owner Agent → Architect Agent → Forge → GuardKit commands as one autonomous, locally-served flow.

Three subsequent developments forced the question to be answered properly rather than by drift.

### 1.2 The three converging lines

**(a) DF-001 entails the boundary.** DF-001 forbids cloud APIs on any unattended path. An autonomous planning stage would therefore have to run on *local* models. The May 2026 analysis (architect-agent integration session, 30 May) showed why that is the worst available trade: `/system-arch` and `/system-design` run once per system — trivial token volume, maximum blast radius. Localising the lowest-volume, highest-stakes reasoning in the pipeline saves almost nothing and concentrates quality risk precisely where it is least affordable. The volume argument that justified going local for ingestion and builds points the *other way* at the planning apex.

**(b) The two-model asymmetry is a quality gate, not an accident.** The current shape — frontier plans, local builds — means an underspecified spec fails *visibly*, because the weaker implementation model has less room for creative gap-filling. That visible failure is the mechanism by which specification gaps surface. Collapsing both seats into the same local capability class loses not just a planner but a diagnostic.

**(c) The vendor's pricing fence draws the same line.** The June 2026 Anthropic enforcement (API keys required for programmatic access from 15 June) meters *unattended* volume while leaving *interactive* use on flat subscriptions. Attended frontier work is cheap; unattended frontier volume is where costs explode — the same 10–100× class that triggered DF-001. The economically rational boundary and the vendor-imposed boundary coincide.

### 1.3 Supporting evidence

- **The architect fine-tune validates a reviewer, not an author.** The May 2026 eval showed the fine-tuned Gemma 4 26B-A4B architect model comparable to the GPT-5.5 baseline in 3 of 4 sessions — but exclusively in `architect_align` (judgment) mode. There is no evidence yet for `architect_greenfield` (origination), which is what autonomous `/system-arch` would require. The local fallback can judge; it cannot yet originate.
- **External validation.** NVIDIA Research (arXiv:2506.02153): heterogeneous systems — SLMs for operations, LLMs for strategy — already cited on slide 12 of the talk.
- **The market ran the inverse experiment.** Kiro autonomous, Devin, Codex Cloud, Jules all run the token-heavy *implementation* half on metered frontier models — the most expensive possible configuration (~5–10× per-task cost of attended tools). The factory inverts it: frontier only where leverage-per-token is highest (planning, low volume), local where volume explodes (implementation).

## 2. Decision

### 2.1 The pipeline boundary

| Pipeline stage | Mode | Model class | Surface | Orchestration |
|---|---|---|---|---|
| Ideation / conversation starters | Attended | Frontier (subscription) | Claude Desktop | Human |
| `/system-arch` · `/system-design` · `/system-plan` | Attended | Frontier (subscription) | Claude Code / OpenCode | Human |
| `/feature-spec` · `/feature-plan` | Attended | Frontier (subscription) | Claude Code / OpenCode | Human (defaults-acceptance logged as training signal) |
| AutoBuild (Player-Coach) · `/task-work` · `/task-review` loops | **Unattended** | **Local** (llama-swap :9000) | LangGraph/DeepAgents harness (guardkitfactory) | **Forge** |
| Gate evaluation, checkpoint management, re-dispatch | Unattended | Local | Forge | Forge (confidence-gated; human at checkpoints) |

### 2.2 The Forge's scope, restated

The Forge is the **orchestrator and checkpoint manager of the build half**: it sequences AutoBuild waves, evaluates Coach scores against per-stage thresholds, manages confidence-gated checkpoints, and interrupts a human only on specific concerns. It does **not** drive the planning stages. The "domain goal in, built solution out" full-autonomy premise is deferred — keep-warm per Workstream A, not abandoned, with the revisit conditions in §4.

### 2.3 What the specialist planning agents are for (under this boundary)

The fine-tuned architect / product-owner / QA-verifier models remain first-class assets, with three roles that do not require pipeline autonomy:
1. **Config-switchable fallback reviewers** for the planning artefacts (the "tested optionality" posture, 30 May) — a second, adversarial opinion on frontier-authored specs at near-zero cost.
2. **Products of the dataset factory** — the fine-tuned-judgment showcase (Thread 2) and the per-domain delta sold in Offers B/C.
3. **The distillation target** — the frontier planning pipeline doubles as a dataset factory; the teacher funds its own potential replacement, which is exactly what the §4 revisit conditions test for.

### 2.4 Relationship to DF-001 and DF-002

- DF-001 stands unchanged: this decision *applies* it to the pipeline rather than amending it. The attended planning stages were always inside DF-001's interactive carve-out (~5–10 frontier sessions/month).
- DF-002 stands unchanged: its §2.2 tool-selection table is this same boundary expressed on the commercial ledger (attended → frontier as COGS; unattended → local). DF-003 expresses it on the lab/factory ledger, stage by stage.

## 3. Consequences

**Positive:** the dark-factory thesis is preserved where it is true (near-zero marginal cost on the unattended, token-heavy half) and not over-claimed where it is not · planning quality stays at the frontier where blast radius is maximal · the two-model asymmetry is retained as a diagnostic · vendor repricing risk is confined to the attended path, where subscriptions are flat and artefacts (specs, plans, datasets, evals) are portable · the positioning story sharpens — the factory inverts the cost structure of the entire autonomous-coding-agent category.

**Negative / accepted:** frontier dependence remains on the planning path — mitigated by the fallback-reviewer posture (§2.3.1) and artefact portability · the original full-autonomy demo ("watch the factory build from a goal, end to end, untouched") is deferred — accepted, because the hybrid demo (attended planning + dark build) is the honest one and matches what was presented at DDD SouthWest · the Forge's headline ambition shrinks — accepted per Workstream A's keep-warm designation; orchestration is not the moat.

## 4. Revisit conditions (do not reopen without one)

1. **The local planner proves authorship.** A fine-tuned architect/PO model passes `architect_greenfield`-class (origination, not review) evals at an agreed threshold against the frontier baseline, with RAG active. This is the gate the May 2026 eval explicitly did not test.
2. **Frontier interactive terms change materially** — subscription pricing, session limits, or terms that break the attended-path economics (the DF-002 reopen trigger, applied here).
3. **The DF-002 tripwire fires on a planning workload class** — frontier-token COGS on attended planning exceeding ~10–15% of a deliverable's price.
4. **A sold engagement requires fully air-gapped end-to-end delivery** (the sold-privacy class, DF-002 §2.2) — in which case localised planning becomes a priced product feature, not an ideology.

## 5. Principle made explicit

> **Autonomy is bought per stage, not per pipeline. The price of automating a stage is set by its token volume; the risk is set by its blast radius. Automate where volume is high and blast radius is contained (implementation); stay attended where volume is trivial and blast radius is total (architecture). A pipeline that automates its cheapest-to-attend, most-expensive-to-get-wrong stage has optimised the wrong variable.**

## 6. Immediate actions

- ✅ Reframe mission-and-narrative-arc Act 3 and success signal #1 to the hybrid operating loop (2026-06-10, same session as this ADR).
- ✅ Add DF-003 to the Workstream A "decisions carried in" table; name the FEAT-HMIG run-10 cutover as the immediate critical path (2026-06-10).
- ✅ Banner the superseded full-autonomy framing in `forge/docs/research/ideas/fleet-master-index.md` and `forge-pipeline-orchestrator-refresh.md` (2026-06-10).
- Seed this decision into Graphiti (`guardkit-py graphiti add-context` or MCP `add_memory`) so agents retrieve it at context-load and an autonomous session never re-litigates the boundary.
- Carry the boundary into Thread 3 positioning: the one-liner is *"the market runs implementation on metered frontier models; the factory runs frontier only where leverage-per-token is highest."*

---

*Decision proposed: 2026-06-10*
*Scope: pipeline stage → model class → orchestration boundary for the GuardKit software factory.*
*"Autonomy is bought per stage, not per pipeline."*
