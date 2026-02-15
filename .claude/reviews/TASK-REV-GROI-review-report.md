# Review Report: TASK-REV-GROI — Graphiti ROI Assessment

## Executive Summary

GuardKit's Graphiti integration spans 65+ files across 10 consumption paths. After evidence-based analysis of the actual codebase, the verdict is mixed: **4 paths have untapped potential, 4 are low-value overhead, 1 is dead code, and 1 is not a Graphiti path**. The critical finding is that the system is **80% built with three specific disconnections** preventing value delivery — Coach context is retrieved then discarded, outcome writes happen but reads are never called, and turn continuation context exists but isn't wired in.

**Revised strategy (after [R]evise): Connect the 3 disconnected read paths (1-2 days), measure with 3-5 comparative AutoBuild runs, then decide whether to invest further or deprecate. This is strictly better than premature deprecation — it costs minimal effort and produces evidence.**

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Deep
- **Duration**: Comprehensive codebase analysis
- **Scope**: All 10 consumption paths + 4 hypotheses

---

## Path-by-Path Assessment

### PATH 1: Coach Context Injection

**File**: `guardkit/planning/coach_context_builder.py`
**Category**: POTENTIAL

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Yes — clean code, graceful degradation, 9+ unit tests |
| Provides unique value? | Uncertain — untested hypothesis |
| Actually used? | Only when Graphiti available AND complexity >= 4 |

**Evidence**:
- Token budgets verified: 0/1000/2000/3000 by complexity band (lines 62-66)
- Graceful degradation at 3 levels: budget=0, sp._available=False, exception catch-all (lines 92, 100, 147)
- `coach_validator.py:547-571` calls `build_coach_context()` but injects result as `arch_context` that **isn't consumed by the sync `validate()` method** (comment at line 572-574)
- Impact analysis only fires for complexity >= 7 with > 400 remaining tokens

**Verdict**: The infrastructure is solid but the value proposition is **untested**. Nobody has compared Coach validation quality with vs without Graphiti context. The architecture context is assembled but may not influence Coach decisions. Token budgets (1000 for complexity 4-6) seem too low for meaningful context.

**Action**: Test H1 (Coach context improves quality). If no measurable improvement, deprecate.

---

### PATH 2: AutoBuild Outcome & Turn State Capture

**File**: `guardkit/orchestrator/autobuild.py:1516, 2275-2456`
**Category**: POTENTIAL (writes active, reads disconnected)

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Writes work (1-5 episodes per run). Reads infrastructure exists but is NOT called. |
| Provides unique value? | Could enable cross-task learning — but read path is disconnected |
| Actually used? | Writes: yes. Reads: no. |

**Evidence**:
- `_capture_turn_state()` called at line 1516 for every turn — confirmed working
- `TurnStateEntity` captures: turn number, player/coach decisions, files modified, test metrics, blockers
- `TaskOutcome` entity and `capture_task_outcome()` exist in `outcome_manager.py`
- `find_similar_task_outcomes()` in `outcome_queries.py` — fully implemented, searches `task_outcomes` group
- **CRITICAL**: `find_similar_task_outcomes()` is NOT called from `autobuild.py` directly
- `load_turn_continuation_context()` in `turn_state_operations.py` — defined but NOT called from autobuild
- `JobContextRetriever` queries `task_outcomes` group (25% budget allocation) — but only fires when `JobContextRetriever` is actively used

**Verdict**: Classic write-heavy/read-light pattern. The system diligently captures every turn state but never uses that data to improve future runs. The "similar outcomes" retrieval exists in code but isn't wired into the AutoBuild loop. This means every write is waste until the read path is connected.

**Action**: Either wire `find_similar_task_outcomes()` into Coach context (making outcomes inform future tasks) or stop capturing. Test H2 first.

---

### PATH 3: Feature-Plan Context Assembly

**File**: `guardkit/knowledge/feature_plan_context.py`
**Category**: LOW VALUE

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Yes — clean dataclass with `to_prompt_context()` |
| Provides unique value? | No — same information available from `docs/architecture/ARCHITECTURE.md` (~66 lines) |
| Actually used? | Developed extensively (63 files reference it) but value over file reads is unclear |

**Evidence**:
- `FeaturePlanContext` dataclass with 9 fields: feature_spec, related_features, patterns, similar_implementations, project_architecture, warnings, role_constraints, quality_gate_configs, implementation_modes
- 4000-token budget with priority ordering (40% spec, 20% architecture, remaining for patterns/warnings)
- `docs/architecture/ARCHITECTURE.md` is 66 lines — easily readable by Claude Code directly
- `docs/architecture/components.md`, `crosscutting-concerns.md`, `system-context.md` are each ~60-65 lines
- Total architecture docs: ~400 lines across 6 files — well within Claude Code's read capacity

**Verdict**: The architecture docs that Graphiti would query are small enough to read directly. Claude Code sessions already have access to `CLAUDE.md` (loaded automatically) which contains the essential project context. The 4000-token Graphiti budget adds complexity without a clear win over direct file reads.

**Action**: Compare `/feature-plan` output with Graphiti vs with direct file reads of `docs/architecture/*.md`. If quality is equivalent, deprecate the Graphiti path and use direct reads.

---

### PATH 4: System Overview / Impact Analysis / Context Switch

**File**: `guardkit/cli/system_context.py`
**Category**: POTENTIAL (impact-analysis) / LOW VALUE (overview, context-switch)

| Sub-path | Category | Reasoning |
|----------|----------|-----------|
| `system-overview` | LOW VALUE | Reads the same architecture docs that exist in `docs/architecture/` |
| `impact-analysis` | POTENTIAL | Semantic search across components/ADRs — genuinely can't replicate with grep |
| `context-switch` | LOW VALUE | Multi-project switching — no evidence anyone uses GuardKit across projects |

**Evidence**:
- `system_context.py` obtains GraphitiClient with graceful degradation (returns None if unavailable)
- `NO_CONTEXT_MESSAGE` suggests fallback: "Read CLAUDE.md for project conventions"
- `system-overview` assembles from Graphiti but the authoritative source is `docs/architecture/ARCHITECTURE.md` (per ADR-SP-007)
- `impact-analysis` uses `SystemPlanGraphiti.get_relevant_context_for_topic()` for semantic search — this is the one path where Graphiti's embedding-based search adds genuine value over keyword grep
- `context-switch` for multi-project: no evidence of multi-project usage in task history

**Verdict**: Impact analysis is the most promising use case because it requires semantic understanding of component relationships — you can't replicate "which components are affected by changing authentication?" with a simple `grep`. The other two are redundant with file reads.

**Action**: Invest in impact-analysis reliability. Deprecate system-overview CLI (direct file reads suffice). Defer context-switch until multi-project demand exists.

---

### PATH 5: System-Plan Write Path

**File**: `guardkit/planning/graphiti_arch.py`
**Category**: POTENTIAL (if readers exist) / LOW VALUE (if readers don't query it)

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Yes — historical stub bug FIXED. Real `upsert_episode()` operations confirmed |
| Provides unique value? | ADR-SP-007 says "Markdown Authoritative, Graphiti Queryable" — but is Graphiti actually queried? |
| Actually used? | Writes: yes. Read-back: only by paths 1, 3, 4 (themselves of mixed value) |

**Evidence**:
- `SystemPlanGraphiti` class with real upsert methods: `upsert_component()`, `upsert_adr()`, `upsert_system_context()`, `upsert_crosscutting()`
- Uses `upsert_episode()` (NOT `add_episode()`) for idempotent writes — correct
- `_available` check prevents operations on disabled client
- ADR-SP-007 confirmed: "Never duplicate -- if it's authoritative in markdown, Graphiti provides a reference/summary"
- ADR-SP-007 also acknowledges: "Requires re-ingestion when markdown changes" and "Graphiti facts may lag behind markdown edits"

**Verdict**: The write path works correctly now (stub was fixed). But per ADR-SP-007's own acknowledgment, Graphiti facts lag behind markdown edits. Since markdown is the authoritative source and Claude Code reads markdown directly, the write path creates a copy that's often stale. Its value depends entirely on whether paths 1, 3, 4 deliver enough read-side value to justify the writes.

**Action**: Value tied to read-side verdict. If impact-analysis proves valuable, keep writes. Otherwise, let `/system-plan` write only to markdown (which it already does).

---

### PATH 6: Seeding Infrastructure (18 categories, ~140-220 episodes)

**File**: `guardkit/knowledge/seeding.py` (orchestrator) + 15 `seed_*.py` modules
**Category**: LOW VALUE

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Partially — marks seeded even with partial failures (line 181-183) |
| Provides unique value? | No — seeds static content that could be read from files |
| Actually used? | Runs during `guardkit init` and `guardkit graphiti seed` |

**Evidence**:
- 18 seed categories in `seed_all_system_context()` (lines 150-168): product_knowledge, command_workflows, quality_gate_phases, technology_stack, feature_build_architecture, architecture_decisions, failure_patterns, component_status, integration_points, templates, agents, patterns, rules, project_overview, project_architecture, failed_approaches, quality_gate_configs, pattern_examples
- All content is **hardcoded** in Python source files — no auto-generation from docs
- `SEEDING_VERSION = "1.0.0"` — never incremented
- Idempotency: `is_seeded()` checks marker file, but `mark_seeded()` runs even with `had_errors = True`
- Estimated volume: 140-220 episodes, 8-45 seconds, 140-220 network calls
- FalkorDB throttling workaround: `SEMAPHORE_LIMIT=5` + 0.5s delay per episode

**Seed categories with NO identified read path**:
- `seed_component_status` — no active queries found
- `seed_feature_overviews` (if exists) — no active queries found
- `seed_role_constraints` — only used during init, not queried during task execution

**Verdict**: The seeding system copies static knowledge from Python source into Graphiti, creating a maintenance burden with no auto-update mechanism. The same knowledge exists in `CLAUDE.md`, `docs/architecture/*.md`, and `.claude/rules/*.md` — all directly readable. The hardcoded nature means seed content goes stale whenever the product evolves, and version "1.0.0" suggests it has never been refreshed.

**Action**: Eliminate most seed categories. If Coach context (PATH 1) proves valuable, keep only the seed categories it actually queries. Otherwise, remove seeding entirely.

---

### PATH 7: Add-Context CLI (Document Ingestion)

**File**: `guardkit/cli/graphiti.py:483-777`
**Category**: LOW VALUE

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Partially — silent failures on `add_episode()` return None |
| Provides unique value? | No — ingests documents already readable as files |
| Actually used? | Available but no evidence of regular use in workflows |

**Evidence**:
- 5 registered parsers: ADRParser, FeatureSpecParser, ProjectDocParser, ProjectOverviewParser, FullDocParser
- `add_episode()` returns `None` on ANY error — caller tracks `episodes_failed` counter but no reason logged
- `result_uuid is not None` check (graphiti.py) — only way to detect failure
- Error suppression in `graphiti_client.py:776-784`: exception logged at WARNING level, returns None
- No distinction between retryable (network) vs fatal (disabled) errors

**Verdict**: This CLI command ingests markdown files into Graphiti for searchability. But in Claude Code sessions, the same files can be read directly. The parser infrastructure adds complexity without clear benefit over `cat docs/adr/ADR-001.md`. The silent failure mode undermines trust.

**Action**: If semantic search (PATH 4 impact-analysis) proves valuable, fix the error handling to distinguish retryable vs fatal failures. Otherwise, deprecate.

---

### PATH 8: Interactive Capture & Search

**File**: `guardkit/knowledge/interactive_capture.py`, `guardkit/cli/graphiti.py:780-879, 1304-1403`
**Category**: POTENTIAL

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Yes — well-structured with gap analysis and 9 knowledge categories |
| Provides unique value? | Yes — captures tacit knowledge not in files |
| Actually used? | Unknown — no usage telemetry |

**Evidence**:
- `InteractiveCaptureSession` with gap analysis via `KnowledgeGapAnalyzer`
- 9 knowledge categories mapped to Graphiti group IDs
- Search across 17 group IDs with relevance scoring (green/yellow/white)
- Focus categories available: project-overview, architecture, domain, constraints, decisions, goals, role-customization, quality-gates, workflow-preferences

**Verdict**: This is one of the genuinely unique Graphiti capabilities. Interactive capture collects **tacit knowledge** (domain rules, constraints, decisions) that doesn't exist in any file. If this knowledge is then surfaced via search or context injection, it provides value that file reads cannot. However, the value depends on adoption — if nobody runs capture sessions, the knowledge base stays empty.

**Action**: Keep. Promote as the primary knowledge capture workflow. Ensure captured knowledge is surfaced by Coach context and impact-analysis.

---

### PATH 9: MCP Servers (context7, design-patterns)

**File**: `installer/core/lib/mcp/context7_client.py`
**Category**: NOT A GRAPHITI PATH (separate concern)

**Evidence**:
- MCP servers are independent of Graphiti — they query external services (Upstash, local SQLite)
- `CLAUDE.md` states: "All MCPs are optional. Falls back gracefully to training data."
- Graceful degradation confirmed: exception caught, warning printed, error message returned
- Setup: context7 HTTP = 2-5 min; design-patterns = 20-30 min

**Verdict**: MCP servers are orthogonal to Graphiti. They provide library documentation and design patterns from external sources — not from the knowledge graph. Including them in a Graphiti ROI assessment conflates two different systems. They deliver value when available but are correctly treated as optional.

**Action**: Remove from Graphiti ROI scope. Continue treating as independent optional capability.

---

### PATH 10: Quality Gate Config from Graphiti

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py:354-417`
**Category**: DEAD

| Criterion | Assessment |
|-----------|------------|
| Works reliably? | Infrastructure exists but is DISCONNECTED from execution |
| Provides unique value? | No — hardcoded defaults in `task_types.py` always used |
| Actually used? | Never — prepared for "future integration" that never shipped |

**Evidence**:
- `get_graphiti_thresholds()` async method queries `quality_gate_configs` group (line 354-417)
- Falls back to hardcoded `DEFAULT_PROFILES` in `task_types.py` (7 task types with full profiles)
- Comment at line 572-574: "graphiti_profile is currently not used by the sync validate method"
- `validate_with_graphiti_thresholds()` prepares the profile but `validate()` ignores it
- `seed_quality_gate_configs.py` seeds 6 configs that are never read in production

**Verdict**: Dead code. The query infrastructure, seeding, and fallback logic exist but the actual validation path uses hardcoded defaults exclusively. Nobody has ever customized quality gate thresholds via Graphiti — they use `task_types.py` directly.

**Action**: Remove the Graphiti quality gate query path and the `seed_quality_gate_configs` module. Keep the hardcoded `DEFAULT_PROFILES` in `task_types.py` (which work well). If per-project customization is needed later, implement it via a config file, not a knowledge graph.

---

## Assessment Summary

| Path | Category | Evidence | Action |
|------|----------|----------|--------|
| **1: Coach Context** | POTENTIAL | Working code, untested value | Test H1, then decide |
| **2: Outcome Capture** | POTENTIAL | Writes active, reads disconnected | Wire reads or stop writes |
| **3: Feature-Plan Context** | LOW VALUE | Same info available via file reads | Compare with direct reads |
| **4a: Impact Analysis** | POTENTIAL | Semantic search adds genuine value | Invest in reliability |
| **4b: System Overview** | LOW VALUE | Redundant with `docs/architecture/` | Deprecate CLI |
| **4c: Context Switch** | LOW VALUE | No multi-project usage evidence | Defer until demand |
| **5: System-Plan Writes** | CONDITIONAL | Depends on read-side value | Tied to PATH 1,4a verdict |
| **6: Seeding (18 categories)** | LOW VALUE | Hardcoded, stale, largely unqueried | Eliminate most categories |
| **7: Add-Context CLI** | LOW VALUE | Silent failures, files already readable | Deprecate or fix errors |
| **8: Capture & Search** | POTENTIAL | Captures tacit knowledge uniquely | Keep, promote adoption |
| **9: MCP Servers** | N/A | Not a Graphiti path | Remove from scope |
| **10: Quality Gate Config** | DEAD | Infrastructure exists but disconnected | Remove dead code |

---

## Hypothesis Testing

### H1: Coach Context Improves AutoBuild Quality

**Status**: CANNOT TEST (requires controlled experiment)

**Available Evidence**:
- `build_coach_context()` assembles architecture context (confirmed working)
- But `arch_context` is not consumed by `validate()` — the injection point is prepared but not connected
- Even if connected, no baseline data exists to compare quality with/without

**Recommendation**: Before testing H1, fix the injection point so Coach actually reads the context. Then run 5 identical tasks with/without. Currently testing this hypothesis would be meaningless because the context isn't consumed.

### H2: Outcome Capture Enables Cross-Task Learning

**Status**: FALSIFIED (read path disconnected)

**Evidence**:
- `_capture_turn_state()` writes 1-5 episodes per AutoBuild run (**confirmed in code**)
- `find_similar_task_outcomes()` EXISTS but is NOT CALLED from AutoBuild
- `load_turn_continuation_context()` EXISTS but is NOT CALLED from AutoBuild
- `JobContextRetriever` allocates 25% budget to outcomes — but only fires when explicitly used

**Conclusion**: Outcome capture does NOT currently enable learning. Writes happen but reads are disconnected. Every turn state write is wasted effort until the read path is wired in.

### H3: Semantic Search Provides Value Over File Reads

**Status**: PARTIALLY CONFIRMED

**Evidence**:
- `docs/architecture/` contains 6 files totaling ~400 lines — easily greppable
- For queries like "which components affected by auth changes?", keyword grep against component descriptions works surprisingly well on a small codebase
- Where Graphiti DOES add value: embedding-based search can surface **relationship** connections (e.g., "component A depends on component B which uses pattern C") that keyword search misses
- This advantage scales with codebase size — on GuardKit's current scale, the advantage is marginal

**Conclusion**: Semantic search advantage is real but marginal at current scale. Would become more valuable for larger projects with many components and cross-cutting concerns. For GuardKit specifically, `grep` across `docs/architecture/` is nearly equivalent.

### H4: Seeding ROI Is Positive

**Status**: FALSIFIED

**Evidence**:
- Seeding: 18 categories, ~140-220 episodes, 8-45 seconds, 140-220 network calls
- Seeded content: hardcoded in Python source, never auto-updated, version 1.0.0 unchanged
- At least 3 seed categories have no identified read path (component_status, feature_overviews, role_constraints during task execution)
- Same content exists in readable files (CLAUDE.md, docs/architecture/*.md, .claude/rules/*.md)
- Maintenance cost: every product change requires manual seed module update (never done)

**Conclusion**: Seeding ROI is negative. It creates a stale copy of information already available in readable files. The maintenance burden of keeping 18 seed modules in sync with the evolving product is not justified by the read-side value (which is itself uncertain).

---

## Cost Analysis

### Infrastructure Costs

| Item | Cost | Notes |
|------|------|-------|
| FalkorDB Docker | ~$0/month (local) or $20-50/month (cloud) | Required for Graphiti |
| OpenAI Embeddings | ~$0.02 per 1M tokens | text-embedding-3-small for search |
| Seeding per project | 8-45 seconds + ~140-220 API calls | One-time but never refreshed |
| Per-task captures | 1-5 episodes per AutoBuild run | Turn state writes |

### Maintenance Costs

| Item | Effort | Notes |
|------|--------|-------|
| Seed module updates | Never done (stale since v1.0.0) | Should happen on every product change |
| Graphiti client wrapper | ~22 files in knowledge/ | Ongoing maintenance |
| Integration tests | Limited coverage | Seam tests being developed |
| FalkorDB migration | Already completed (from Neo4j) | One-time |

### Value Delivered (Current State)

| Path | Value | Confidence |
|------|-------|------------|
| Coach context injection | Unknown — not consumed | Low |
| Cross-task learning | Zero — reads disconnected | High |
| Feature-plan enrichment | Marginal — files readable directly | Medium |
| Impact analysis | Potentially unique | Medium |
| Interactive capture | Potentially unique | Medium |
| Quality gate config | Zero — dead code | High |

---

## Expansion Opportunities Assessment

| Opportunity | Value | Feasibility | Verdict |
|-------------|-------|-------------|---------|
| Cross-session continuity | Medium — Graphiti could provide "last session" context | High | Worth exploring IF Graphiti is kept |
| Pattern mining from completed tasks | High — requires actual read path for outcomes | Medium | REQUIRES fixing PATH 2 reads first |
| Architecture drift detection | Low — codebase changes faster than Graphiti updates | Low | ADR-SP-007 acknowledges this lag |
| Multi-project knowledge sharing | Unknown — no multi-project users | Low | Defer until demand |
| Embedding-powered code search | Medium — but GitHub Copilot and IDE search already good | Medium | Low priority |

---

## Revised Strategy: Connect, Measure, Then Decide

> **Revision rationale**: The original review (Option A: Simplify Aggressively) recommended mass deprecation before testing whether connecting the disconnected reads delivers value. The revised strategy takes a "connect the last 20%, measure, then decide" approach — recognizing the system is 80% built with three specific disconnections preventing value delivery.

### The Three Disconnections

All three are confirmed in the codebase:

**Disconnection 1: Coach context retrieved but never passed to validator**
- `_invoke_coach_safely()` retrieves `context_prompt` via `thread_loader.get_coach_context()` (autobuild.py:2967)
- `validator.validate()` is called WITHOUT `context=context_prompt` (autobuild.py:3010-3018)
- The `validate()` method signature has no `context` parameter at all
- Result: context assembled, logged, then thrown away

**Disconnection 2: Outcome writes active, reads never called from AutoBuild**
- `_capture_turn_state()` writes 1-5 episodes per run to `"turn_states"` group (confirmed working)
- `capture_task_outcome()` writes to `"task_outcomes"` group (confirmed working)
- `JobContextRetriever` allocates 25% budget to `task_outcomes` and DOES query it — but only fires when explicitly used via `AutoBuildContextLoader`
- `load_turn_continuation_context()` reads from `"turn_states"` — fully implemented but NEVER called from `AutoBuildContextLoader.get_player_context()`
- Result: turn state data written every turn but never used for cross-turn learning

**Disconnection 3: Quality gate config — dead code (PATH 10)**
- `validate_with_graphiti_thresholds()` and `get_graphiti_thresholds()` exist but are never called
- Coach always uses hardcoded `DEFAULT_PROFILES` from `task_types.py`
- This is confirmed dead code, not a disconnection to fix

### Implementation Plan (3 Fixes)

#### Fix 3: Remove Dead Code (PATH 10) — Do First

Remove confirmed dead code to reduce noise:

| File | Action |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Remove `get_graphiti_thresholds()`, `validate_with_graphiti_thresholds()`, `GRAPHITI_AVAILABLE` import block |
| `guardkit/knowledge/quality_gate_queries.py` | **DELETE** |
| `guardkit/knowledge/seed_quality_gate_configs.py` | **DELETE** |
| `guardkit/knowledge/seeding.py` | Remove `quality_gate_configs` from category list |

**Acceptance Criteria**:
- AC-F3-01: `quality_gate_queries.py` deleted
- AC-F3-02: `seed_quality_gate_configs.py` deleted
- AC-F3-03: Dead async methods removed from `coach_validator.py`
- AC-F3-04: `GRAPHITI_AVAILABLE` import block removed
- AC-F3-05: All existing coach_validator tests pass unchanged
- AC-F3-06: Seeding orchestrator no longer includes `quality_gate_configs`

#### Fix 1: Wire Coach Context Into Validation — Do Second

Thread the already-retrieved `context_prompt` into the validator:

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Add optional `context: Optional[str] = None` param to `validate()`. Include in rationale/result for traceability. |
| `guardkit/orchestrator/autobuild.py` | Pass `context=context_prompt` to `validator.validate()` at line 3010-3018 |

**Acceptance Criteria**:
- AC-F1-01: `CoachValidator.validate()` accepts optional `context` parameter
- AC-F1-02: When context is provided, it appears in `CoachValidationResult` (rationale or new `context_used` field)
- AC-F1-03: `_invoke_coach_safely` passes `context_prompt` to `validator.validate()`
- AC-F1-04: `validate(context=None)` works identically to current behavior (backward compat)
- AC-F1-05: Graceful degradation when context retrieval fails

#### Fix 2: Wire Outcome Reads Into AutoBuild Context — Do Third

Connect the cross-turn learning that's already 90% built:

| File | Change |
|------|--------|
| `guardkit/knowledge/autobuild_context_loader.py` | In `get_player_context()`, call `load_turn_continuation_context()` when `turn_number > 1` and append to context |
| `guardkit/knowledge/job_context_retriever.py` | Verify `task_outcomes` query fires (already wired — confirm with test) |

**Group ID Verification** (confirmed consistent):
- Turn states: write `"turn_states"` → read `"turn_states"` via `load_turn_continuation_context()`
- Task outcomes: write `"task_outcomes"` → read `"task_outcomes"` via `JobContextRetriever`

**Acceptance Criteria**:
- AC-F2-01: `AutoBuildContextLoader.get_player_context()` calls `load_turn_continuation_context()` for turn > 1
- AC-F2-02: Turn continuation context included in Player prompt when available
- AC-F2-03: Group IDs consistent between write and read paths (verified)
- AC-F2-04: Graceful degradation when no prior outcomes exist
- AC-F2-05: `JobContextRetriever` queries `task_outcomes` group (already wired — verify with round-trip test)

### Observability: Before/After Measurement

Add structured logging to each fix:

```
[Graphiti] Coach context provided: {len} chars, {categories} categories  (Fix 1)
[Graphiti] Turn continuation loaded: {len} chars for turn {N}            (Fix 2)
[Graphiti] Similar outcomes found: {count} matches                        (Fix 2)
```

**Test Protocol**: Run 3-5 identical AutoBuild tasks before/after. Measure:
- Turns to approval (fewer = better)
- Coach feedback quality (does context reduce false rejections?)
- Cross-turn learning (does turn 2 avoid repeating turn 1 mistakes?)

### Decision Gate

After the 3-5 comparative runs:

- **If measurable improvement** → Keep connected paths, proceed with broader investment in Graphiti
- **If no improvement** → Proceed with original Option A (simplify aggressively), now with confidence that deprecation is justified

### Implementation Order & Effort

1. Fix 3 (dead code removal) — cleanest, no risk — **2-3 hours**
2. Fix 1 (Coach context wiring) — straightforward parameter threading — **3-4 hours**
3. Fix 2 (outcome reads) — verify group_id consistency, wire continuation — **4-6 hours**
4. Observability logging — alongside each fix — **included above**
5. Before/after testing — 3-5 comparative AutoBuild runs — **1 day**

**Total estimated effort**: 1-2 days for all fixes + testing.

### Files Modified Summary

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Add `context` param to `validate()`, remove dead methods + imports |
| `guardkit/orchestrator/autobuild.py` | Pass `context_prompt` to `validator.validate()` |
| `guardkit/knowledge/autobuild_context_loader.py` | Wire `load_turn_continuation_context()` for turn > 1 |
| `guardkit/knowledge/quality_gate_queries.py` | **DELETE** |
| `guardkit/knowledge/seed_quality_gate_configs.py` | **DELETE** |
| `guardkit/knowledge/seeding.py` | Remove `quality_gate_configs` from category list |
| `tests/unit/test_coach_validator.py` | Add context parameter tests |
| `tests/unit/test_autobuild_context_loader.py` | Add turn continuation tests |

---

## Original Options (Preserved for Reference)

### Option A: Simplify Aggressively (Original Recommendation)

**Keep**: Paths 4a (impact-analysis) and 8 (interactive capture/search)
**Fix & Validate**: Path 2 (wire outcome reads into Coach context)
**Deprecate**: Paths 3, 4b, 4c, 6, 7, 10
**Conditional**: Path 1 (if H1 tested positive after fixing injection), Path 5 (if impact-analysis proves valuable)

**Result**: ~65 files reduced to ~20. Lower maintenance burden.

### Option B: Connect, Measure, Then Decide (Revised Recommendation)

**Fix now**: 3 targeted wire-ups (Fix 1, 2, 3) — 1-2 days effort
**Measure**: 3-5 comparative AutoBuild runs with observability
**Decide after**: Option A deprecation OR broader investment based on evidence

**Result**: Minimal effort to test whether 80%-built system delivers value when the last 20% is connected.

### Option C: Full Deprecation

Remove Graphiti entirely. Replace with direct file reads + grep. Estimated effort: 1 week. Risk: lose genuinely unique semantic search and tacit knowledge capture.

### Recommended: Option B

Option B is strictly better than Option A: it costs 1-2 days of effort but gives evidence-based confidence in whatever decision follows. If the wire-ups deliver no value, Option A deprecation proceeds with hard data. If they DO deliver value, we avoided prematurely deprecating a nearly-complete system.

---

## Decision Required

**Primary Decision**: Proceed with Option B (Connect, Measure, Then Decide)?

**If yes**: Create 3 implementation tasks (Fix 1, Fix 2, Fix 3) + observability + test protocol.

---

## Appendix: File Inventory

### Files Modified (Option B — Revised)

```
guardkit/orchestrator/quality_gates/coach_validator.py  # Add context param, remove dead code
guardkit/orchestrator/autobuild.py                      # Pass context_prompt to validator
guardkit/knowledge/autobuild_context_loader.py          # Wire turn continuation for turn > 1
guardkit/knowledge/seeding.py                           # Remove quality_gate_configs category
tests/unit/test_coach_validator.py                      # New context tests
tests/unit/test_autobuild_context_loader.py             # Turn continuation tests
```

### Files Deleted (Option B — Revised)

```
guardkit/knowledge/quality_gate_queries.py               # Dead code (PATH 10)
guardkit/knowledge/seed_quality_gate_configs.py           # Seeds for dead code
```

### Files to Deprecate Later (if measurement shows no value)

```
guardkit/knowledge/seed_*.py (15+ files)     # Seeding modules
guardkit/knowledge/seeding.py                 # Seed orchestrator
guardkit/knowledge/feature_plan_context.py    # Replaced by direct reads
guardkit/integrations/graphiti/parsers/*.py   # Add-context parsers
```
