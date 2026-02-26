# Review Report: TASK-REV-8A94

## Executive Summary

The vLLM/Qwen3 autobuild failure on FEAT-947C has **one primary root cause** and several contributing factors. The Qwen3 model inconsistently wrote the `player_turn_1.json` report to the **repo root** instead of the **worktree path** for 2 of 4 tasks. This prevented the promise-recovery pipeline from finding the agent's structured output, forcing the Coach to fall back to text matching against an empty `requirements_met` list — guaranteeing 0% criteria verification.

**Bottom line:** This is not a text matching algorithm bug. It is a **path resolution failure** caused by model inconsistency when following the execution protocol in a worktree context.

## Review Details

- **Mode**: Decision Analysis (architectural + code-quality)
- **Depth**: Standard
- **Task**: TASK-REV-8A94 — Analyse vLLM Qwen3 DB feature autobuild failure on GB10
- **Feature**: FEAT-947C — PostgreSQL Database Integration (8 tasks, 4 waves)

---

## Finding 1: Player Report Path Mismatch (Critical — Root Cause)

### Evidence

The `player_turn_1.json` file (written by the agent during task-work) was saved to different paths depending on the task:

| Task | player_turn_1.json Path | Recovery | Result |
|------|------------------------|----------|--------|
| DB-001 | `/.guardkit/worktrees/FEAT-947C/.guardkit/autobuild/TASK-DB-001/` | 10 promises recovered | **10/10 APPROVED** |
| DB-002 | `/.guardkit/autobuild/TASK-DB-002/` (REPO ROOT) | Nothing recovered | **0/9 FAILED** |
| DB-003 | `/.guardkit/worktrees/FEAT-947C/.guardkit/autobuild/TASK-DB-003/` | 7 promises recovered | **7/7 APPROVED** |
| DB-004 | `/.guardkit/autobuild/TASK-DB-004/` (REPO ROOT) | Nothing recovered | **0/7 FAILED** |

**DB-002** and **DB-004** wrote `player_turn_1.json` to the repo root `.guardkit/autobuild/{task_id}/` instead of the worktree `.guardkit/worktrees/FEAT-947C/.guardkit/autobuild/{task_id}/`.

### Impact

The recovery code at `agent_invoker.py:1848` checks `player_report_path.exists()` using the worktree path. When the agent writes to the repo root, the file isn't found, so:

1. `completion_promises` → empty
2. `requirements_addressed` → empty
3. Fix 5 synthetic promises → insufficient (too few files detected by git)
4. Coach falls back to `_match_by_text()` with empty `requirements_met`
5. All criteria rejected → 0% verification → feedback loop → timeout

### Root Cause Analysis

The execution protocol instructs the agent to write to `.guardkit/autobuild/{task_id}/player_turn_N.json`. The working directory is set to the worktree for all tasks. Yet Qwen3 resolved this path to the **repo root** for DB-002/DB-004 (possibly via `.git` traversal or an absolute path embedded in context).

Anthropic's Claude models consistently resolve this path relative to the working directory. Qwen3 is inconsistent — 2/4 correct.

---

## Finding 2: Empty requirements_met Forces Guaranteed Rejection

### Evidence

```
WARNING:coach_validator: Criteria verification 0/9 - diagnostic dump:
WARNING:coach_validator:   requirements_met: []
WARNING:coach_validator:   completion_promises: (not used)
WARNING:coach_validator:   matching_strategy: text
WARNING:coach_validator:   _synthetic: False
```

### The Matching Pipeline

```
1. Promise-based matching (completion_promises from player report)
   └─ FAILED: No promises found (agent wrote to wrong path)

2. Hybrid fallback (requirements_addressed + text matching)
   └─ FAILED: requirements_addressed is empty

3. Text matching (requirements_met with 3 strategies)
   └─ FAILED: requirements_met is [] — nothing to match against

4. Synthetic promises (Fix 5 — file-existence check)
   └─ FAILED: Insufficient file detection via git
```

All four layers failed because the **source data** (agent-written player report) was unreachable.

---

## Finding 3: Timeout Cascade from Rejection Loop

### Evidence

- **Turn 1**: Coach rejects (0% criteria) → sends feedback
- **Turn 2**: Player re-implements, taking 1200s+ (20 min)
- Task timeout: 2400s (40 min) → exceeded → CANCELLED

### Timing Comparison

| Task | Turn 1 Duration | Turn 2 Duration | Outcome |
|------|----------------|-----------------|---------|
| DB-001 | ~1650s (27.5 min) | N/A | Approved turn 1 |
| DB-002 | ~2160s (36 min) | 1200s+ (cancelled) | TIMEOUT |
| DB-003 | ~2160s (36 min) | N/A | Approved turn 1 |
| DB-004 | ~2160s (36 min) | 450s+ (cancelled) | TIMEOUT |

When the first turn incorrectly rejects, there is almost no time budget remaining for a second attempt at vLLM speeds.

---

## Finding 4: Configuration Differences vs Successful Anthropic Run

| Parameter | vLLM/Qwen3 Run | Anthropic Run |
|-----------|----------------|---------------|
| max_turns | 5 | 10 |
| SDK max_turns | 100 | 50 |
| Feature tasks | 8 (FEAT-947C) | 5 (FEAT-BA28) |
| Turn 1 speed | ~27-36 min/task | ~6.7 min/task |
| Speed ratio | 4x slower | baseline |
| Environment bootstrap | "no dependency install available" | Dependencies installed |
| Matching success | 2/4 tasks | 5/5 tasks |

The Anthropic run also benefited from the TM01-TM04 text matching fixes (commit `2786976e`), but these fixes are irrelevant when `requirements_met` is empty.

---

## Finding 5: Git Detection Discrepancy

For DB-002 Turn 1:
- Agent created 4 files (per documentation constraint warning)
- Git detection found: **0 modified, 2 created**
- Final summary: "6 files created, 1 modified"

The git detection undercount may be due to parallel Wave 2 tasks modifying the same worktree simultaneously, making git diff unreliable for attributing file changes to specific tasks.

---

## Recommendations

### Priority 1: Path-Hardened Player Report Recovery (Quick Win)

**Fix**: In `_create_player_report_from_task_work()` (agent_invoker.py:1848), search for the agent-written player report at **both** the worktree path and the repo root path:

```python
# Current: only checks worktree path
if not report.get("completion_promises") and player_report_path.exists():

# Proposed: check worktree path first, then repo root fallback
candidate_paths = [player_report_path]
if self.worktree_path:
    repo_root_fallback = self.repo_path / ".guardkit" / "autobuild" / task_id / f"player_turn_{turn}.json"
    if repo_root_fallback != player_report_path:
        candidate_paths.append(repo_root_fallback)

for candidate in candidate_paths:
    if candidate.exists():
        # recover from this path
        break
```

**Impact**: Would have fixed DB-002 and DB-004 immediately.
**Effort**: ~30 min. Zero risk of regression.

### Priority 2: Timeout Scaling for Local LLM Backends (Quick Win)

**Fix**: Auto-detect vLLM/local backends (when `ANTHROPIC_BASE_URL` points to localhost) and apply a timeout multiplier:

```python
# In feature_orchestrator or agent_invoker
if "localhost" in os.environ.get("ANTHROPIC_BASE_URL", ""):
    task_timeout *= 3  # Scale for ~4x slower inference
    sdk_timeout *= 2
```

**Impact**: Prevents premature timeout for turn 2 attempts.
**Effort**: ~1 hour.

### Priority 3: Stronger Synthetic Promise Fallback (Medium)

**Fix**: When no completion_promises are recovered AND the task type is scaffolding:
1. Check file existence directly against acceptance criteria (don't rely solely on git detection)
2. Parse AC text for file path references (e.g., "`alembic.ini` created at project root")
3. Verify referenced files exist in the worktree

**Impact**: Provides a safety net when the agent doesn't produce structured promises.
**Effort**: ~2-4 hours.

### Priority 4: Execution Protocol Path Anchoring (Medium)

**Fix**: In the inline execution protocol sent to the agent, use an **absolute path** for the player report output location instead of a relative path:

```python
# Instead of: "Write to .guardkit/autobuild/{task_id}/player_turn_{turn}.json"
# Use: "Write to {absolute_worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json"
```

**Impact**: Eliminates path ambiguity for all models.
**Effort**: ~1 hour. Requires testing with both Anthropic and vLLM.

### Priority 5: Semantic Matching Configuration (Architecture)

**Fix**: Add a `matching_strategy` configuration option supporting:
- `promises` (default) — current promise-based matching
- `text` — current text matching with TM01-04 fixes
- `semantic` — keyword overlap with lowered Jaccard threshold (e.g., 50% instead of 70%)
- `lenient` — accept scaffolding tasks with >60% file-existence verification

Configurable per-backend or per-model:
```yaml
# .guardkit/autobuild.yaml
matching:
  default_strategy: promises
  fallback_strategy: semantic
  local_model_override:
    strategy: lenient
    jaccard_threshold: 0.50
```

**Impact**: Makes matching resilient to model variation.
**Effort**: ~4-8 hours.

---

## Decision Matrix

| Fix | Effort | Impact | Risk | Priority |
|-----|--------|--------|------|----------|
| Path-hardened recovery | 30 min | HIGH — fixes root cause | Very Low | P1 |
| Timeout scaling | 1 hr | MEDIUM — prevents cascading timeout | Low | P2 |
| Synthetic promise improvement | 2-4 hrs | MEDIUM — safety net for missing promises | Low | P3 |
| Execution protocol path anchoring | 1 hr | HIGH — prevents future path issues | Low | P4 |
| Semantic matching config | 4-8 hrs | MEDIUM — future-proofing | Medium | P5 |

---

## Answers to Key Questions

### 1. Why does text matching succeed for DB-001/DB-003 but fail for DB-002/DB-004?

**It's not a text matching issue.** DB-001/DB-003 succeeded because the Qwen3 model wrote the player report to the **correct worktree path**, allowing the recovery code to extract completion_promises (10 and 7 respectively). DB-002/DB-004 failed because the model wrote to the **repo root path**, preventing recovery. With no promises or requirements_met, text matching had nothing to match against.

### 2. Should semantic matching be enabled as default for vLLM/local models?

**Not as the primary fix.** The path recovery fix (P1) would have resolved this without any matching strategy changes. However, semantic matching as a **fallback** (P5) is recommended for defense-in-depth, since local models are inherently more variable in output formatting.

### 3. Are timeout values appropriate for local vLLM inference speed?

**No.** At 4x slower token generation, a 40-minute task timeout allows only ~10 minutes of "Anthropic-equivalent" work. After one rejection, there's no time budget for a meaningful second attempt. Timeout scaling (P2) is recommended.

### 4. What fixes from the Anthropic debugging journey apply here?

The TM01-04 text matching fixes (commit `2786976e`) are **model-agnostic** and good to have, but they address a different problem (matching accuracy when requirements_met IS populated). They don't help when requirements_met is empty. The cold start fix (commit `0c784975`) and diagnostic logging are universally valuable.

### 5. Is the feature definition (8 tasks) too granular for local models?

**Partially.** More tasks = more parallel pressure on local hardware. With 3 parallel tasks in Wave 2, vLLM was serving 3 concurrent Claude Code agent sessions. This may contribute to increased latency and the path resolution inconsistency (though the latter is more likely a model behavior issue). Consider limiting parallelism to 2 for local backends.

---

## Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Root cause of Coach text matching failure identified | DONE | Path mismatch: agent wrote player report to repo root instead of worktree |
| Comparison of Qwen3 vs Anthropic output format documented | DONE | See Finding 1 (path table) and Finding 4 (config comparison) |
| Recommendations for vLLM/local model autobuild configuration | DONE | P2 (timeout scaling), P5 (semantic matching config) |
| Assessment of text-matching vs semantic-matching strategy | DONE | Text matching is correct; the issue is upstream data absence. Semantic matching is a defense-in-depth enhancement, not the primary fix. |
| Timeout/performance recommendations documented | DONE | P2 with 3x multiplier for localhost backends |
| Actionable fix list prioritised | DONE | P1-P5 with effort/impact/risk matrix |

---

---

## C4 Sequence Diagrams

### Sequence 1: Successful Task (TASK-DB-001) — Full Data Flow

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Feature     │  │  AutoBuild    │  │ AgentInvoker │  │  SDK Agent   │  │ Coach        │
│ Orchestrator │  │ Orchestrator  │  │              │  │ (Qwen3 via   │  │ Validator    │
│              │  │               │  │              │  │  vLLM)       │  │              │
└──────┬───────┘  └──────┬────────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                   │                 │                 │
       │ TaskLoader.load_task("TASK-DB-001") │                 │                 │
       │ ─ parses frontmatter + body ─────── │                 │                 │
       │ ─ AC from markdown body (10 items)  │                 │                 │
       │                 │                   │                 │                 │
       │ orchestrate(    │                   │                 │                 │
       │  acceptance_criteria=[10 items])    │                 │                 │
       │ ────────────────>                   │                 │                 │
       │                 │                   │                 │                 │
       │                 │ invoke_player()   │                 │                 │
       │                 │ ──────────────────>                 │                 │
       │                 │                   │                 │                 │
       │                 │                   │ SDK(cwd=worktree│                 │
       │                 │                   │  protocol: write│to               │
       │                 │                   │  ".guardkit/autobuild/TASK-DB-001 │
       │                 │                   │   /player_turn_1.json")           │
       │                 │                   │ ────────────────>                 │
       │                 │                   │                 │                 │
       │                 │                   │                 │ WRITES player_  │
       │                 │                   │                 │ turn_1.json to: │
       │                 │                   │                 │ {WORKTREE}/     │
       │                 │                   │                 │ .guardkit/      │
       │                 │                   │                 │ autobuild/...   │
       │                 │                   │                 │ (CORRECT PATH)  │
       │                 │                   │                 │                 │
       │                 │                   │ _write_task_work│_results.json    │
       │                 │                   │ (to worktree — │always correct)  │
       │                 │                   │◄────────────────│                 │
       │                 │                   │                 │                 │
       │                 │                   │ _create_player_report_from_task_work()          │
       │                 │                   │                 │                 │
       │                 │                   │ Step 1: Read task_work_results.json              │
       │                 │                   │   files_created=[...from parser...]              │
       │                 │                   │   completion_promises=[] (not in results)        │
       │                 │                   │                 │                 │
       │                 │                   │ Step 2: Git detection                            │
       │                 │                   │   +6 modified, +16 created (merged via union)    │
       │                 │                   │                 │                 │
       │                 │                   │ Step 3: Fix 2 — player_report_path.exists()?     │
       │                 │                   │   YES — agent wrote to correct worktree path     │
       │                 │                   │   → Recovered 10 completion_promises ✓           │
       │                 │                   │   → Recovered 10 requirements_addressed ✓        │
       │                 │                   │                 │                 │
       │                 │                   │ Step 4: Fix 5 — SKIPPED (promises exist)         │
       │                 │                   │                 │                 │
       │                 │                   │ Step 5: Write player_turn_1.json (overwrites)    │
       │                 │                   │                 │                 │
       │                 │                   │ Step 6: Fix 3 — Update task_work_results.json    │
       │                 │                   │   completion_promises propagated ✓               │
       │                 │                   │                 │                 │
       │                 │ coach.validate()  │                 │                 │
       │                 │ ──────────────────────────────────────────────────────>
       │                 │                   │                 │                 │
       │                 │                   │                 │ read_quality_gate_results()
       │                 │                   │                 │ → task_work_results.json
       │                 │                   │                 │   HAS completion_promises ✓
       │                 │                   │                 │                 │
       │                 │                   │                 │ _load_completion_promises()
       │                 │                   │                 │   → 10 promises found
       │                 │                   │                 │                 │
       │                 │                   │                 │ _match_by_promises()
       │                 │                   │                 │   → 10/10 verified ✓
       │                 │                   │                 │                 │
       │                 │                   │                 │ DECISION: APPROVED
       │                 │◄──────────────────────────────────────────────────────│
```

### Sequence 2: Failing Task (TASK-DB-002) — Where Things Go Wrong

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Feature     │  │  AutoBuild    │  │ AgentInvoker │  │  SDK Agent   │  │ Coach        │
│ Orchestrator │  │ Orchestrator  │  │              │  │ (Qwen3 via   │  │ Validator    │
│              │  │               │  │              │  │  vLLM)       │  │              │
└──────┬───────┘  └──────┬────────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                   │                 │                 │
       │ TaskLoader.load_task("TASK-DB-002") │                 │                 │
       │ ─ parses frontmatter + body ─────── │                 │                 │
       │ ─ AC from markdown body (9 items)   │                 │                 │
       │                 │                   │                 │                 │
       │ orchestrate(    │                   │                 │                 │
       │  acceptance_criteria=[9 items])     │                 │                 │
       │ ────────────────>                   │                 │                 │
       │                 │                   │                 │                 │
       │                 │ invoke_player()   │                 │                 │
       │                 │ ──────────────────>                 │                 │
       │                 │                   │                 │                 │
       │                 │                   │ SDK(cwd=worktree│                 │
       │                 │                   │  protocol: write│to               │
       │                 │                   │  ".guardkit/autobuild/TASK-DB-002 │
       │                 │                   │   /player_turn_1.json")           │
       │                 │                   │ ────────────────>                 │
       │                 │                   │                 │                 │
       │                 │                   │                 │ ╔═══════════╗   │
       │                 │                   │                 │ ║ BUG #1    ║   │
       │                 │                   │                 │ ║           ║   │
       │                 │                   │                 │ ║ WRITES    ║   │
       │                 │                   │                 │ ║ player_   ║   │
       │                 │                   │                 │ ║ turn_1 to ║   │
       │                 │                   │                 │ ║ {REPO_ROOT}   │
       │                 │                   │                 │ ║ not worktree  │
       │                 │                   │                 │ ╚═══════════╝   │
       │                 │                   │                 │                 │
       │                 │                   │ _write_task_work│_results.json    │
       │                 │                   │ (to worktree — │always correct)  │
       │                 │                   │◄────────────────│                 │
       │                 │                   │                 │                 │
       │                 │                   │ _create_player_report_from_task_work()          │
       │                 │                   │                 │                 │
       │                 │                   │ Step 1: Read task_work_results.json              │
       │                 │                   │   files_created=[...from parser...]              │
       │                 │                   │   completion_promises=[] (not in results)        │
       │                 │                   │                 │                 │
       │                 │                   │ Step 2: Git detection                            │
       │                 │                   │   +0 modified, +2 created (race condition)       │
       │                 │                   │   Total after merge: 6 created, 1 modified       │
       │                 │                   │                 │                 │
       │                 │                   │ Step 3: Fix 2 — player_report_path.exists()?     │
       │                 │                   │   ╔═══════════════════════════════════════╗       │
       │                 │                   │   ║ NO — agent wrote to REPO ROOT,       ║       │
       │                 │                   │   ║ but we're checking WORKTREE path     ║       │
       │                 │                   │   ║ → 0 completion_promises recovered ✗  ║       │
       │                 │                   │   ║ → 0 requirements_addressed ✗         ║       │
       │                 │                   │   ╚═══════════════════════════════════════╝       │
       │                 │                   │                 │                 │
       │                 │                   │ Step 4: Fix 5 — no promises, try synthetic       │
       │                 │                   │   _find_task_file("TASK-DB-002") → found ✓       │
       │                 │                   │   _load_task_metadata() → YAML frontmatter only  │
       │                 │                   │   ╔═══════════════════════════════════════╗       │
       │                 │                   │   ║ BUG #2: acceptance_criteria = []     ║       │
       │                 │                   │   ║                                      ║       │
       │                 │                   │   ║ _load_task_metadata only reads YAML  ║       │
       │                 │                   │   ║ frontmatter. AC is in markdown body. ║       │
       │                 │                   │   ║ → Fix 5 never generates promises ✗   ║       │
       │                 │                   │   ╚═══════════════════════════════════════╝       │
       │                 │                   │                 │                 │
       │                 │                   │ Step 5: Write player_turn_1.json (no promises)   │
       │                 │                   │                 │                 │
       │                 │                   │ Step 6: Fix 3 — nothing to propagate             │
       │                 │                   │   (report has no completion_promises)             │
       │                 │                   │                 │                 │
       │                 │ coach.validate()  │                 │                 │
       │                 │ ──────────────────────────────────────────────────────>
       │                 │                   │                 │                 │
       │                 │                   │                 │ read_quality_gate_results()
       │                 │                   │                 │ → task_work_results.json
       │                 │                   │                 │   NO completion_promises
       │                 │                   │                 │   NO requirements_met
       │                 │                   │                 │                 │
       │                 │                   │                 │ _load_completion_promises()
       │                 │                   │                 │   → 0 promises
       │                 │                   │                 │                 │
       │                 │                   │                 │ Fallback: _match_by_text()
       │                 │                   │                 │   requirements_met = []
       │                 │                   │                 │   → 0/9 verified ✗
       │                 │                   │                 │                 │
       │                 │                   │                 │ DECISION: FEEDBACK
       │                 │                   │                 │ "0/9 criteria met"
       │                 │◄──────────────────────────────────────────────────────│
       │                 │                   │                 │                 │
       │                 │ Turn 2 starts...  │                 │                 │
       │                 │ (same issues repeat, eventually    │                 │
       │                 │  timeout at 2400s)                  │                 │
```

### Sequence 3: Coach Matching Pipeline (Internal Detail)

```
┌─────────────────────────────────────────────────────────┐
│              Coach Validator: validate_requirements()     │
│                                                          │
│  Input: acceptance_criteria=[9 items] (from TaskLoader)  │
│         task_work_results.json (from worktree)           │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │ Step 1: Check _synthetic flag                    │     │
│  │   _synthetic = False                             │     │
│  │   → Take normal path                            │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────▼────────────────────────┐     │
│  │ Step 2: _load_completion_promises()              │     │
│  │   Check task_work_results["completion_promises"] │     │
│  │   → NOT FOUND (Fix 3 had nothing to propagate)  │     │
│  │                                                  │     │
│  │   Check player_turn_1.json                       │     │
│  │   → READ from worktree path (exists, written by  │     │
│  │     agent_invoker at Step 5, but has NO promises) │     │
│  │                                                  │     │
│  │   Result: completion_promises = []               │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────▼────────────────────────┐     │
│  │ Step 3: Fallback to text matching               │     │
│  │   strategy = "text"                              │     │
│  │   requirements_met = task_work_results.get(      │     │
│  │     "requirements_addressed",                    │     │
│  │     task_work_results.get("requirements_met",[]))│     │
│  │   → requirements_met = []                        │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────▼────────────────────────┐     │
│  │ Step 4: _match_by_text(acceptance_criteria, [])  │     │
│  │                                                  │     │
│  │   For each AC (9 items):                        │     │
│  │     Strategy 1: Exact match vs []  → MISS       │     │
│  │     Strategy 2: Substring vs []    → MISS       │     │
│  │     Strategy 3: Jaccard vs []      → MISS       │     │
│  │     → result = "rejected"                       │     │
│  │                                                  │     │
│  │   Result: 0/9 verified, 9/9 rejected            │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  Diagnostic dump:                                        │
│    requirements_met: []                                  │
│    completion_promises: (not used)                        │
│    matching_strategy: text                                │
│    _synthetic: False                                     │
│                                                          │
│  DECISION: FEEDBACK (not all acceptance criteria met)    │
└─────────────────────────────────────────────────────────┘
```

### C4 Container View: Data Flow Between Components

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Feature Orchestrator                           │
│                                                                       │
│  TaskLoader.load_task() ──── parses FRONTMATTER + MARKDOWN BODY ───  │
│  acceptance_criteria = [9 items from ## Acceptance Criteria section]  │
│                                                                       │
│  Passes acceptance_criteria to AutoBuild via orchestrate() parameter  │
└───────────────────────────┬───────────────────────────────────────────┘
                            │
                    acceptance_criteria=[9 items]
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        AutoBuild Orchestrator                         │
│                                                                       │
│  Stores acceptance_criteria in memory                                 │
│  Passes to Coach via task={"acceptance_criteria": [9 items]}         │
│  Passes to AgentInvoker for player execution                         │
└──────────┬─────────────────────────────┬──────────────────────────────┘
           │                             │
           │                             │ acceptance_criteria=[9 items]
           ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────────────────────┐
│     Agent Invoker        │  │         Coach Validator                   │
│                          │  │                                          │
│  SDK Agent writes:       │  │  Reads: task_work_results.json           │
│  ┌────────────────────┐  │  │    → completion_promises                 │
│  │ task_work_results  │──┼──┼───→ requirements_met/addressed           │
│  │ .json (worktree)   │  │  │                                          │
│  └────────────────────┘  │  │  Gets: acceptance_criteria from task dict │
│                          │  │    → [9 items] (from TaskLoader) ✓       │
│  Agent writes:           │  │                                          │
│  ┌────────────────────┐  │  │  Matches promises/reqs against AC        │
│  │ player_turn_1.json │  │  │  → If promises: _match_by_promises      │
│  │ (REPO ROOT ✗)      │  │  │  → If empty: _match_by_text(AC, [])    │
│  └────────────────────┘  │  │  → Result: 0/9 verified ✗              │
│                          │  └──────────────────────────────────────────┘
│  Fix 2 Recovery:         │
│  ┌────────────────────┐  │
│  │ Checks WORKTREE    │  │
│  │ path — NOT FOUND ✗ │  │
│  └────────────────────┘  │
│                          │
│  Fix 5 Synthetic:        │
│  ┌────────────────────┐  │
│  │ _load_task_metadata │  │
│  │ reads YAML ONLY ✗  │  │
│  │ acceptance_criteria │  │
│  │ = [] (not in YAML) │  │
│  │ Fix 5 never runs ✗ │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

## Deep-Dive A: Execution Protocol Path Analysis

### How the Protocol Works

The execution protocol is loaded from `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` and instructs the agent:

```
After completing implementation, write your report as JSON to:
`.guardkit/autobuild/{task_id}/player_turn_{turn}.json`
```

**Key facts:**
- The path is **RELATIVE** — no absolute paths used in the protocol
- `{task_id}` and `{turn}` are substituted before sending (agent_invoker.py:3321-3325)
- Working directory is set to worktree via `cwd=str(self.worktree_path)` (agent_invoker.py:1587)
- The protocol is **identical** for Wave 1 (solo) and Wave 2 (parallel) tasks
- The orchestrator reads back using **absolute paths** via `TaskArtifactPaths.player_report_path()`

### Why Qwen3 Wrote to Wrong Path

Since the protocol uses relative paths and the cwd is correctly set, the Qwen3 model must have:

1. **Traversed `.git` or parent directories** to find the repo root, then resolved the path there — OR
2. **Used an absolute path** derived from some other context (e.g., log messages showing the repo root path that the model could have seen)

The protocol header shows the working directory in its context:
```
Working directory: /home/.../api_test/.guardkit/worktrees/FEAT-947C
```

But the repo root path (`/home/.../api_test/`) also appears in log messages and error output. A less instruction-following model like Qwen3 may have confused these paths, especially under the cognitive load of parallel tasks.

### Recommendation Update

**P4 (Execution Protocol Path Anchoring)** should be refined to:
- Use **absolute paths** in the protocol: `{worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json`
- Substitute `{worktree_path}` alongside `{task_id}` and `{turn}` in the protocol builder
- This eliminates all path ambiguity regardless of model quality

---

## Deep-Dive B: Synthetic Promises (Fix 5) — CORRECTED Root Cause

### Initial Theory (WRONG)

The initial deep-dive suggested `files_created`/`files_modified` were empty when Fix 5 runs. **This was incorrect.** Code tracing confirms that git detection at lines 1780-1818 DOES populate these fields via union merge BEFORE Fix 5 runs at line 1884. The log confirms "6 files created, 1 modified" for TASK-DB-002 after enrichment.

### Actual Bug (VERIFIED)

Fix 5 fails because `_load_task_metadata()` (`agent_invoker.py:2100-2122`) **only reads YAML frontmatter**, while acceptance criteria are stored in the **markdown body**.

### The Two Parsers Problem

There are **two different task metadata parsers** with different capabilities:

| Parser | Location | Reads Frontmatter | Reads Markdown Body | Used By |
|--------|----------|-------------------|--------------------|---------|
| `TaskLoader._extract_acceptance_criteria()` | `task_loader.py:274-326` | Yes | **Yes** (parses `## Acceptance Criteria` section) | FeatureOrchestrator, AutoBuild, Coach |
| `AgentInvoker._load_task_metadata()` | `agent_invoker.py:2100-2122` | Yes | **No** (regex `r'^---\n(.*?)\n---'` only) | Fix 5 only |

### Code Evidence

**TaskLoader (used by Coach — correct):**
```python
# task_loader.py:274-326
def _extract_acceptance_criteria(metadata, content):
    # Try frontmatter first
    if "acceptance_criteria" in metadata:
        return metadata["acceptance_criteria"]
    # Fall back to content parsing — parses ## Acceptance Criteria section
    for line in content.split("\n"):
        if line.strip().lower() == "## acceptance criteria":
            in_criteria = True
            ...  # extracts bullet points
```

**AgentInvoker (used by Fix 5 — broken):**
```python
# agent_invoker.py:2100-2122
def _load_task_metadata(self, task_file):
    content = task_file.read_text()
    frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        return yaml.safe_load(frontmatter_match.group(1)) or {}
    return {}
    # ↑ NEVER parses markdown body for acceptance_criteria
```

### Traced Flow for TASK-DB-002

```
Fix 5 (agent_invoker.py:1884):
  report.get("completion_promises") → empty ✓ (Fix 2 failed)

  _find_task_file("TASK-DB-002")
    → worktree/tasks/design_approved/TASK-DB-002-setup-alembic-migrations.md ✓

  _load_task_metadata(task_file)
    → reads YAML frontmatter: {id, title, status, complexity, ...}
    → acceptance_criteria NOT in frontmatter (it's in ## Acceptance Criteria body)
    → task_meta.get("acceptance_criteria", []) = []  ✗

  if acceptance_criteria:  → False (empty list)
    # Fix 5 NEVER generates synthetic promises
    # The files_created=[6 files] and worktree_path are both available
    # but never used because we short-circuit on empty AC
```

### Fix Required

Replace `_load_task_metadata()` in Fix 5 with `TaskLoader.load_task()` or extract AC using the same markdown body parsing:

```python
# Option A: Use TaskLoader (preferred — single source of truth)
from guardkit.tasks.task_loader import TaskLoader
task_data = TaskLoader.load_task(task_id, repo_root=self.worktree_path)
acceptance_criteria = task_data.get("acceptance_criteria", [])

# Option B: Add markdown body parsing to _load_task_metadata (more invasive)
```

### Impact

This is an **independent code bug** — even if the path mismatch (Finding 1) is fixed, Fix 5 would still be broken as a safety net. Both bugs need fixing for defence-in-depth.

### Architectural Note

The two-parser divergence is a design debt. `TaskLoader` is the canonical parser used everywhere else. Fix 5's `_load_task_metadata()` was likely written as a quick lightweight parser during the fix pipeline, not realising that feature task ACs live in the markdown body. The fix should consolidate on `TaskLoader`.

---

## Deep-Dive C: Parallel Worktree Race Conditions

### Architecture

Wave 2 tasks (DB-002, DB-003, DB-004) run in parallel using `asyncio.to_thread()` (feature_orchestrator.py:1075-1392). All three share a **single worktree** and the **same git index**.

### Race Condition: Git Detection

`_detect_git_changes()` (agent_invoker.py:1955-1997) runs `git diff HEAD` and `git ls-files --others` **without any locking**:

| Timing | DB-002 | DB-003 | DB-004 |
|--------|--------|--------|--------|
| T+0s | Start writing files | Start writing files | Start writing files |
| T+2100s | | Git detection runs → sees all files from DB-002, DB-003, DB-004 | |
| T+2160s | Git detection runs → sees remaining files (some already counted by DB-003) | Complete | |
| T+2200s | | | Git detection runs → sees remaining uncounted files |

Result: File attribution is **timing-dependent**. DB-002 showing "0 modified, 2 created" while the agent actually created 4+ files is likely because DB-003's git detection ran first and "consumed" the git diff.

### Missing Synchronisation

- **No `threading.Lock()`** for git operations (searched entire codebase)
- **No git commits** between parallel tasks within a wave
- **No per-task baseline commit** to isolate each task's changes
- `threading.Event()` exists only for cancellation, not synchronisation

### Impact

1. **File count underreporting**: Parallel git detection attributes files randomly across tasks
2. **Synthetic promise undergeneration**: If files are attributed to wrong task, Fix 5 generates promises for the wrong task
3. **Non-deterministic behaviour**: Same feature build may produce different results depending on thread scheduling

### Recommendations

| Fix | Effort | Impact |
|-----|--------|--------|
| Record baseline commit hash per task before execution | 1 hr | Accurate per-task git diff |
| Add `threading.RLock()` around git operations | 30 min | Prevents interleaved git commands |
| Git commit after each parallel task completes | 2 hrs | Clean separation of changes |
| Per-task worktrees (architectural) | 1-2 days | Complete isolation |

---

## Updated Recommendation Summary

### Original Findings + Deep-Dive Additions

| # | Fix | Effort | Impact | Category |
|---|-----|--------|--------|----------|
| **P1** | Path-hardened player report recovery (check worktree + repo root) | 30 min | Fixes root cause | Quick Win |
| **P2** | Timeout scaling for localhost/vLLM backends (3x multiplier) | 1 hr | Prevents cascade | Quick Win |
| **P3a** | Fix Fix 5: use TaskLoader instead of _load_task_metadata for AC extraction | 30 min | Enables synthetic fallback | **NEW - Code Bug (two-parser divergence)** |
| **P3b** | Stronger synthetic promise matching (direct file check) | 2-4 hrs | Safety net | Enhancement |
| **P4** | Execution protocol: absolute paths (not relative) | 1 hr | Prevents path ambiguity | Quick Win |
| **P5** | Semantic matching config option | 4-8 hrs | Future-proofing | Architecture |
| **P6** | Per-task baseline commit for git detection | 1 hr | Accurate file attribution | **NEW - Race Condition** |
| **P7** | Threading lock for git operations | 30 min | Prevents interleaved git | **NEW - Race Condition** |

### Recommended Implementation Waves

**Wave 1 (Quick Wins — 2-3 hours total):**
- P1: Path-hardened recovery
- P3a: Fix Fix 5 data transfer bug
- P4: Absolute paths in protocol
- P7: Git operation threading lock

**Wave 2 (Timeout + Git — 2-3 hours):**
- P2: Timeout scaling
- P6: Per-task baseline commit

**Wave 3 (Future-Proofing — 1-2 days):**
- P3b: Enhanced synthetic promises
- P5: Semantic matching config

---

## Appendix: File References

| Component | Location |
|-----------|----------|
| Failing output | `docs/reviews/gb10_local_autobuild/db_feature_1.md` |
| Successful Anthropic run | `docs/reviews/autobuild-fixes/db_finally_succeds.md` |
| Coach validator | `guardkit/orchestrator/quality_gates/coach_validator.py` |
| Agent invoker (recovery code) | `guardkit/orchestrator/agent_invoker.py:1848` |
| Text matching fixes | Commits `2786976e`, `0c784975` |
| Task file | `tasks/backlog/TASK-REV-8A94-analyse-vllm-qwen3-db-autobuild-failure.md` |
