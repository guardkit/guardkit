# TASK-REV-C7EB: Review Report - Graphiti Command Integration Points

**Review Mode:** deep-analysis | **Depth:** comprehensive
**Date:** 2026-02-08
**Reviewer:** Claude (automated)
**Related:** TASK-REV-0E58 (autobuild pipeline), TASK-REV-8BD8 (context retrieval), TASK-FIX-GCW3/4/5 (context wiring)

---

## Executive Summary

This review analyses Graphiti integration points across four core GuardKit commands (`/feature-plan`, `/task-review`, `/task-create`, `/task-work`) comparing specification to implementation. The knowledge module (`guardkit/knowledge/`) is substantial (~30 files, ~8000+ lines) with well-designed building blocks, but command-level integration is uneven.

**Overall Assessment:** The integration is **partially implemented** with significant gaps.

| Command | Spec Coverage | Implementation Status | Graceful Degradation |
|---------|--------------|----------------------|---------------------|
| `/feature-plan` | Extensive | **Partial** (reads only, no seeding) | Yes |
| `/task-review` | Moderate | **Stub** (end-to-end path broken) | Yes |
| `/task-create` | Minimal | **N/A** (Context7, not Graphiti) | N/A |
| `/task-work` (standard) | **Absent from spec** | **NOT wired** (infrastructure exists, not connected) | Yes (in unused bridge) |
| `/task-work` (AutoBuild) | Extensive | **Implemented** (TASK-FIX-GCW3/4/5) | Yes |

**Critical findings:**
1. **`/task-work` standard mode has no Graphiti wiring** despite a complete infrastructure (FEAT-GR-006) designed for it - including an unused bridge module (`graphiti_context_loader.py`) and a "standard" budget allocation strategy in `DynamicBudgetCalculator` that is never invoked
2. `/feature-plan` has meaningful Graphiti integration but is read-only (no seeding)
3. The `/task-review` knowledge capture path terminates at a stub
4. `/task-create` mentions `graphiti-core` as an example library for Context7 resolution, not as a Graphiti knowledge graph integration

---

## Per-Command Analysis

### Command 1: `/feature-plan`

**Spec:** `installer/core/commands/feature-plan.md` (1764 lines)
**Implementation:** `guardkit/knowledge/feature_plan_context.py`, `guardkit/commands/feature_plan_integration.py`

#### What the Spec Says

The FEAT-GR-003 section describes comprehensive Graphiti integration:

1. **Context Retrieval** - Query 8+ group IDs for enrichment:
   - `feature_specs`, `related_features`, `architecture_patterns`, `failed_approaches`
   - `role_constraints`, `quality_gate_configs`, `implementation_modes`, `project_architecture`
2. **Feature Spec Seeding** - Seed the generated feature spec TO the knowledge graph
3. **Token Budget** - ~4000 token allocation with priority weighting (40% spec, 20% arch, etc.)
4. **Log Output** - `[Graphiti]` prefixed status messages during execution
5. **Graceful Degradation** - Continue without Graphiti context when unavailable

#### What Is Implemented

| Spec Feature | Status | Notes |
|-------------|--------|-------|
| Context retrieval from 8 group IDs | **Implemented** | `FeaturePlanContextBuilder.build_context()` queries all 8 via `_safe_search()` |
| Token budget allocation | **Implemented** | `to_prompt_context(budget_tokens=4000)` with priority-based allocation |
| Graceful degradation | **Implemented** | Checks `graphiti_client is None`, `graphiti_client.enabled`, try/except on each query |
| Feature spec seeding | **NOT Implemented** | No `add_episode()` or `upsert_episode()` calls in `feature_plan_context.py` |
| `[Graphiti]` log output | **NOT Implemented** | Zero matches for `[Graphiti]` in entire `guardkit/` codebase |
| CLI `--context` flag wiring | **Partial** | `FeaturePlanIntegration` class exists but no CLI flag in `guardkit/cli/` routes to it |

#### Key Evidence

**Context retrieval works** (`feature_plan_context.py:356-424`):
```python
if self.graphiti_client is not None and self.graphiti_client.enabled:
    # Queries feature_specs, architecture_patterns, role_constraints, etc.
    context.related_features = await self._safe_search("related features ...")
    context.relevant_patterns = await self._safe_search("architecture patterns ...")
    # ... 6 more queries
```

**Seeding is absent** - grep for `seed`, `add_episode`, `upsert` in `feature_plan_context.py` returns zero matches. The spec says "Seed feature spec to knowledge graph" but the implementation only reads.

#### Gap Assessment

- **Severity: Medium** - The read path works well; missing write path means the knowledge graph doesn't grow from feature planning activity
- **Impact:** Feature specs created by `/feature-plan` are not stored in Graphiti, so subsequent queries for "related features" can only find manually seeded data

---

### Command 2: `/task-review`

**Spec:** `installer/core/commands/task-review.md`
**Implementation:** `guardkit/knowledge/review_knowledge_capture.py`, `guardkit/knowledge/interactive_capture.py`

#### What the Spec Says

1. **`--capture-knowledge` / `-ck` flag** - Optional Phase 4.5 after review completes
2. **`run_review_capture()`** - Entry point for knowledge capture
3. **3-5 context-specific questions** - Generated from review mode and findings
4. **Graceful degradation** - If Graphiti unavailable, skip silently

#### What Is Implemented

| Spec Feature | Status | Notes |
|-------------|--------|-------|
| `ReviewCaptureConfig.from_args()` | **Implemented** | Parses `--capture-knowledge` and `-ck` flags |
| `run_review_capture()` function | **Implemented** | Creates `ReviewKnowledgeCapture`, generates questions, calls `run_abbreviated()` |
| Mode-specific question generation | **Implemented** | 5 review modes, 3 templates each, plus generic questions |
| 3-5 question count | **Implemented** | `generate_review_questions()` enforces 3-5 range with deduplication |
| `InteractiveCaptureSession.run_abbreviated()` | **STUB** | Returns empty result immediately without asking questions or storing |
| CLI flag wiring | **NOT Implemented** | Zero matches for `capture_knowledge` in `guardkit/cli/` |

#### Key Evidence

**The stub** (`interactive_capture.py:432-471`):
```python
async def run_abbreviated(self, questions, task_context=None):
    task_context = task_context or {}
    captured_items: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {
        "captured_items": captured_items,  # Always empty
        "task_id": task_context.get("task_id", ""),
        "review_mode": task_context.get("review_mode", ""),
    }
    return result  # Returns immediately, no questions asked, nothing stored
```

The full `run_session()` method (lines 110-430) is implemented with gap analysis, Q&A loops, and Graphiti storage. But `run_abbreviated()` - the method called by the `/task-review` path - is a stub.

**CLI gap** - `--capture-knowledge` is not wired in any CLI command file under `guardkit/cli/`. The flag parsing exists in `ReviewCaptureConfig.from_args()` but nothing calls it from the CLI layer.

#### Gap Assessment

- **Severity: High** - The entire end-to-end path is broken. Even if the CLI flag were wired, `run_abbreviated()` does nothing.
- **Impact:** `/task-review --capture-knowledge` is non-functional. Knowledge from reviews is never captured to Graphiti.

---

### Command 3: `/task-create`

**Spec:** `installer/core/commands/task-create.md` (1104 lines)
**Implementation:** `installer/core/commands/lib/library_context.py`

#### What the Spec Says

1. **`library_context` frontmatter field** - Manual specification of library dependencies
2. **Phase 1.5: Load Task Context** - Parse `library_context` from task frontmatter
3. **Phase 2.1: Implementation Planning** - Merge manual context with Context7 results
4. **`graphiti-core` as example** - Listed as an example library in the `library_context` field

#### Clarification: This Is Not a Graphiti Integration

The spec uses `graphiti-core` as an **example library name** in the `library_context` field:

```yaml
library_context:
  - name: graphiti-core
    version: ">=0.3"
    focus: "Episode body format, _add_episodes() API"
```

This means: "When working on a task that uses graphiti-core, provide its API docs via Context7." It is **not** a Graphiti knowledge graph integration point. The `library_context` field works with any library (React, FastAPI, pytest, etc.).

**Implementation:** `library_context.py` contains `parse_library_context()` and `gather_library_context()` which resolve libraries via Context7 MCP tools (`resolve-library-id`, `query-docs`). No Graphiti client calls exist in this file.

#### Gap Assessment

- **Severity: None** - No gap exists because Graphiti integration was never specified
- **Clarification needed:** The task review scope document lists this as a Graphiti integration point, but analysis shows it is purely Context7

---

### Command 4: `/task-work`

**Spec:** `installer/core/commands/task-work.md` (2000+ lines)
**Implementation:** `installer/core/commands/lib/library_context.py`, `guardkit/knowledge/autobuild_context_loader.py`, `installer/core/commands/lib/graphiti_context_loader.py`

#### What the Spec Says

The task-work spec references Context7 for library documentation (Phase 2.1) but does **not** mention Graphiti knowledge graph queries during Phase 1 (Load Task Context) or Phase 2 (Implementation Planning). This is a spec gap, not a feature gap.

#### The Design Intent vs Reality

FEAT-GR-006 (Job-Specific Context Retrieval) was designed as a **general-purpose context loading pipeline** for any task execution, not just AutoBuild. The infrastructure consists of five components:

| Component | File | Purpose | Used By |
|-----------|------|---------|---------|
| `TaskAnalyzer` | `task_analyzer.py` | Classify task type, complexity, novelty | AutoBuild only |
| `DynamicBudgetCalculator` | `budget_calculator.py` | Calculate token budget per task | AutoBuild only |
| `JobContextRetriever` | `job_context_retriever.py` | Query Graphiti for job-specific context | AutoBuild only |
| `AutoBuildContextLoader` | `autobuild_context_loader.py` | Bridge retriever to Player/Coach | AutoBuild only |
| `GraphitiContextLoader` | `graphiti_context_loader.py` | Bridge retriever to standard task-work | **Not wired** |

The `GraphitiContextLoader` module exists at `installer/core/commands/lib/graphiti_context_loader.py` and provides both async (`load_task_context`) and sync (`load_task_context_sync`) APIs specifically designed for standard `/task-work` integration. It is **imported nowhere** outside its own module.

The `DynamicBudgetCalculator` already has two allocation strategies:
- **Standard allocation:** 6 categories (feature_context, similar_outcomes, relevant_patterns, architecture_context, warnings, domain_knowledge)
- **AutoBuild allocation:** Adds 4 more (role_constraints, quality_gate_configs, turn_states, implementation_modes)

The "standard" allocation strategy was clearly designed for `/task-work` standard mode but is never invoked.

#### What Should Happen During Task-Work

During implementation planning (Phase 2), `/task-work` should query the knowledge graph to understand:
- **How this task fits into the system** - related features, architecture context
- **What similar tasks looked like** - outcomes, patterns that worked/failed
- **What to avoid** - failed approaches, warnings
- **Domain knowledge** - relevant concepts and constraints

This is the core premise of Graphiti integration: the knowledge graph accumulates understanding across sessions, and each task execution benefits from prior context.

#### Gap Assessment

- **Severity: High** - This is the **primary gap** in Graphiti command integration. The entire FEAT-GR-006 infrastructure was built for this use case, and the standard allocation strategy in `DynamicBudgetCalculator` was designed for it. An integration bridge (`GraphitiContextLoader`) was created but never wired.
- **AutoBuild path is covered** - Already reviewed and fixed in TASK-REV-0E58 and TASK-FIX-GCW3/4/5
- **Spec needs updating** - The task-work.md spec should document Graphiti context loading in Phase 1/2, matching how AutoBuild already uses it

---

## Cross-Cutting Concerns

### 1. Consistency of Graphiti Availability Handling

**Pattern:** All implemented integrations use a consistent three-layer check:

```python
# Layer 1: None check
if graphiti is None:
    return default_value

# Layer 2: Enabled check
if not graphiti.enabled:
    return default_value

# Layer 3: Try/except on individual operations
try:
    result = await graphiti.search(query)
except Exception:
    return default_value
```

**Files using this pattern:**
- `context_loader.py` - 4 functions (lines 164, 337, 436, 524)
- `feature_plan_context.py` - `build_context()` and `_safe_search()`
- `autobuild.py` (orchestrator) - lines 598, 2410
- `quality_gate_queries.py` - line 41
- `gap_analyzer.py` - line 338

**Assessment:** Graceful degradation is **consistent and well-implemented** across all files that use Graphiti.

### 2. Knowledge Graph Lifecycle: Read vs Write

| Command | Reads from Graphiti | Writes to Graphiti |
|---------|--------------------|--------------------|
| `/feature-plan` | Yes (8 group IDs) | **No** (spec says yes) |
| `/task-review` | No | **Stub** (spec says yes via capture) |
| `/task-create` | No (Context7 only) | No |
| `/task-work` (standard) | **No** (infrastructure exists, not wired) | No |
| `/task-work` (AutoBuild) | Yes (via `AutoBuildContextLoader`) | Yes (via `capture_turn_state`, `capture_task_outcome`) |
| `guardkit graphiti capture` | Yes (gap analysis) | Yes (interactive session) |
| Seeding (`guardkit graphiti seed`) | N/A | Yes (system context) |

**Assessment:** The knowledge graph lifecycle is **heavily read-biased at the command level**. The only functional write paths are:
1. AutoBuild turn state and outcome capture (implemented)
2. Interactive capture via CLI (`guardkit graphiti capture --interactive`) (implemented)
3. System context seeding (`guardkit graphiti seed`) (implemented)

**Missing read paths:**
1. Standard `/task-work` context loading (FEAT-GR-006 infrastructure unused)

**Missing write paths:**
1. Feature spec seeding from `/feature-plan` (spec says it should happen)
2. Review knowledge capture from `/task-review` (stub)

### 3. Spec vs Reality Summary

| Category | Count | Details |
|----------|-------|---------|
| Fully implemented | 4 | Feature plan context retrieval, token budget, graceful degradation, review question generation |
| Partially implemented | 1 | Feature plan integration (reads but no writes) |
| Infrastructure built but not wired | 1 | `/task-work` standard mode - `GraphitiContextLoader`, standard budget allocation, `JobContextRetriever` all exist but are unused |
| Stub / broken | 1 | `run_abbreviated()` in interactive capture |
| Not implemented (spec says yes) | 3 | Feature spec seeding, `[Graphiti]` logging, `--capture-knowledge` CLI wiring |
| Spec confusion (not actually Graphiti) | 1 | `/task-create` library_context is Context7, not Graphiti |

### 4. Configuration Surface

| Mechanism | Scope | Location |
|-----------|-------|----------|
| `GRAPHITI_ENABLED` env var | Global | `guardkit/knowledge/config.py` |
| `.guardkit/graphiti.yaml` | Project | `guardkit/knowledge/config.py` |
| `--enable-context/--no-context` | CLI (AutoBuild only) | `guardkit/cli/autobuild.py` |
| `--capture-knowledge/-ck` | CLI (task-review) | **Not wired** (only in `ReviewCaptureConfig.from_args()`) |

**Assessment:** Configuration is **inconsistent**. AutoBuild has explicit `--enable-context` flag (added in TASK-FIX-GCW4), but `/feature-plan` and `/task-review` have no CLI flags to control Graphiti behavior. The review `--capture-knowledge` flag exists in spec and parser but has no CLI wiring.

### 5. Error Handling When Neo4j Is Down

| Scenario | Behavior |
|----------|----------|
| Graphiti client not initialized | `get_graphiti()` returns `None` or disabled client |
| Neo4j connection refused | `GraphitiClient.initialize()` catches exception, sets `enabled = False` |
| Individual query fails | Try/except returns empty results |
| Knowledge graph is empty | Returns empty lists, defaults used for performance stats |

**Assessment:** Error handling is **robust**. The system never crashes due to Graphiti unavailability. All paths degrade gracefully to empty/default results.

---

## Prioritised Recommendations

### Priority 1: Wire Graphiti Context into Standard `/task-work` (High Impact, Medium Effort) - TASK-FIX-GCI1

**Files:** `installer/core/commands/lib/graphiti_context_loader.py` (bridge exists), task-work orchestration, `installer/core/commands/task-work.md` (spec update)

The entire FEAT-GR-006 infrastructure was designed for this. The components exist:
- `GraphitiContextLoader` with `load_task_context()` / `load_task_context_sync()` - **exists, not imported anywhere**
- `DynamicBudgetCalculator` with "standard" allocation strategy - **exists, never invoked**
- `JobContextRetriever` with 6 standard context categories - **exists, only used via AutoBuild path**

What needs to happen:
1. Wire `GraphitiContextLoader.load_task_context()` into Phase 1 (Load Task Context) - inject related features, architecture context, similar outcomes, patterns, warnings
2. Pass retrieved context to Phase 2 (Implementation Planning) prompt
3. Add `--enable-context/--no-context` CLI flag (copy pattern from AutoBuild in `guardkit/cli/autobuild.py`)
4. Update task-work.md spec to document Graphiti context loading

This is the core value proposition of Graphiti: each task benefits from accumulated knowledge. Without this, the knowledge graph is only useful in AutoBuild mode.

### Priority 2: Fix `run_abbreviated()` Stub (High Impact, Low Effort) - TASK-FIX-GCI2

**File:** `guardkit/knowledge/interactive_capture.py:432-471`

The `run_abbreviated()` method should actually ask the provided questions and store answers to Graphiti. The full `run_session()` implementation (lines 110-430) shows how to do this. An abbreviated version should:
1. Iterate through provided questions
2. Collect answers (from AI agent or user input)
3. Store as episodes via `graphiti.add_episode()`

Without this fix, the entire `/task-review --capture-knowledge` feature is non-functional.

### Priority 3: Wire `--capture-knowledge` in CLI (High Impact, Low Effort) - TASK-FIX-GCI3

**Files:** `guardkit/cli/` (task-review command handler)

The `ReviewCaptureConfig.from_args()` parser exists but nothing calls it from the CLI. Wire the flag through the task-review CLI command to `run_review_capture()`.

### Priority 4: Implement Feature Spec Seeding (Medium Impact, Medium Effort) - TASK-FIX-GCI4

**File:** `guardkit/knowledge/feature_plan_context.py`

After `build_context()` completes and the feature spec is generated, seed it to the knowledge graph:
```python
await graphiti_client.add_episode(
    body=feature_spec_text,
    group_id="feature_specs",
    metadata={"feature_id": feature_id, "source": "feature-plan"}
)
```

This closes the read/write lifecycle gap for `/feature-plan`.

### Priority 5: Add `[Graphiti]` Logging (Low Impact, Low Effort) - TASK-FIX-GCI5

**Files:** `feature_plan_context.py`, `autobuild_context_loader.py`, `graphiti_context_loader.py`

Add structured logging with `[Graphiti]` prefix as described in the feature-plan spec. This improves observability without changing functionality.

### Priority 6: Clarify Spec Language for `/task-create` (Low Impact, Low Effort) - TASK-FIX-GCI6

**File:** `installer/core/commands/task-create.md`

The use of `graphiti-core` as an example in `library_context` creates confusion about whether this command has Graphiti knowledge graph integration. Consider:
- Using a different example library (e.g., `pandas`, `fastapi`)
- Adding a note that `library_context` is a Context7 integration, not Graphiti

### Priority 7: Unify Configuration Surface (Medium Impact, Medium Effort) - TASK-FIX-GCI7

Add `--enable-context/--no-context` flags to `/feature-plan` and potentially `/task-review` commands, matching the pattern established in TASK-FIX-GCW4 for AutoBuild.

### Implementation Tasks

All 7 recommendations have been created as tasks at `tasks/backlog/graphiti-command-integration/`:

| Task ID | Recommendation | Wave | Complexity |
|---------|---------------|------|------------|
| TASK-FIX-GCI1 | Wire Graphiti context into standard `/task-work` | 1 | 5 |
| TASK-FIX-GCI2 | Fix `run_abbreviated()` stub | 1 | 4 |
| TASK-FIX-GCI3 | Wire `--capture-knowledge` CLI flag | 2 | 2 |
| TASK-FIX-GCI4 | Feature spec seeding | 2 | 3 |
| TASK-FIX-GCI5 | `[Graphiti]` structured logging | 3 | 2 |
| TASK-FIX-GCI6 | Spec language clarification | 3 | 1 |
| TASK-FIX-GCI7 | Unify `--enable-context` flag | 3 | 3 |

---

## Implementation Status Matrix

| Knowledge Module Component | Implemented | Tested | Wired to CLI | Used by Command |
|---------------------------|-------------|--------|--------------|-----------------|
| `GraphitiClient` | Yes | Yes | Yes (graphiti CLI) | All (when available) |
| `FeaturePlanContextBuilder` | Yes | Partial | No | `/feature-plan` (via spec) |
| `FeaturePlanIntegration` | Yes | No | No | None (wrapper exists) |
| `ReviewKnowledgeCapture` | Yes | Yes | No | None (stub blocks) |
| `ReviewCaptureConfig` | Yes | Yes | No | None (not wired) |
| `InteractiveCaptureSession.run_session()` | Yes | Yes | Yes (graphiti CLI) | `guardkit graphiti capture` |
| `InteractiveCaptureSession.run_abbreviated()` | **Stub** | Yes (tests pass against stub) | No | None |
| `AutoBuildContextLoader` | Yes | Yes | Yes | `/feature-build`, `guardkit autobuild` |
| `GraphitiContextLoader` | Yes | Unknown | **No** | **None** (designed for `/task-work`) |
| `TaskAnalyzer` | Yes | Yes | No | AutoBuild (indirect) |
| `DynamicBudgetCalculator` | Yes | Yes | No | AutoBuild only (standard strategy unused) |
| `JobContextRetriever` | Yes | Yes | No | AutoBuild (indirect) |
| `FeatureDetector` | Yes | Partial | No | `/feature-plan` (indirect) |
| Context7 `library_context` | Yes | No | Yes (via spec) | `/task-work`, `/task-create` |

---

## Conclusion

The Graphiti knowledge module has a **strong foundation** with well-designed building blocks (`GraphitiClient`, `FeaturePlanContextBuilder`, `ReviewKnowledgeCapture`, `AutoBuildContextLoader`, `JobContextRetriever`, `DynamicBudgetCalculator`). Graceful degradation is consistent and robust across all integration points.

However, **command-level integration is incomplete**:

1. **`/task-work` standard mode is the biggest gap** - The entire FEAT-GR-006 job-specific context retrieval pipeline was designed for this use case. A `GraphitiContextLoader` bridge module exists, a "standard" budget allocation strategy exists, but nothing is wired. This means the core premise of Graphiti - that each task benefits from accumulated knowledge during planning - only works in AutoBuild mode.
2. **AutoBuild** is the only command path with full read+write Graphiti integration (fixed in TASK-FIX-GCW3/4/5)
3. **`/feature-plan`** reads from Graphiti but doesn't write back (no seeding)
4. **`/task-review`** has a well-designed capture path that terminates at a stub

The recommendations are prioritised by impact. Wiring Graphiti context into standard `/task-work` (Priority 1) is the highest-value change because it fulfils the original design intent of FEAT-GR-006 and makes the knowledge graph useful during every task execution, not just autonomous builds. Fixing the review capture stub and CLI wiring (Priorities 2-3) would make the `/task-review --capture-knowledge` feature functional, creating a write path that feeds the knowledge graph with review insights.

---

*Review conducted under TASK-REV-C7EB. Files analysed: 15 implementation files, 4 command specifications, 6 Graphiti reference documents.*
