# Review Report: TASK-REV-acbc (Revised)

## Executive Summary

The `guardkit graphiti seed` command wastes ~45% of its 263-minute runtime seeding templates the project doesn't use. But the **real problem is bigger**: the seed function is only half the story. AutoBuild performance on local LLMs (Qwen/DeepSeek on Dell GB10) is primarily degraded by **~100-115 KB of static markdown context injected into every Player/Coach turn**, not just by slow seeding. The seeding waste and the context bloat are two sides of the same problem — both stem from a lack of template-awareness.

### Three-Layer Problem

| Layer | Problem | Impact on Local LLM |
|-------|---------|---------------------|
| **1. Seed Duration** | Seeds all 7 templates (~263 min) | Hours wasted on initial setup |
| **2. Static Context Per Turn** | ~100-115 KB injected via SDK every turn | Degrades Qwen/DeepSeek inference quality and speed |
| **3. Seeding vs Static Gap** | Seeding into Graphiti doesn't reduce static loading | Both systems run in parallel, not replacing each other |

**Recommendation**: A two-phase fix targeting both seeding efficiency and static context reduction.

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Comprehensive (revised with broader scope)
- **Task ID**: TASK-REV-acbc
- **Goal**: Improve AutoBuild performance on local Dell GB10 with Qwen/DeepSeek

---

## Finding 1: Static Context Per AutoBuild Turn Is ~100-115 KB

Every Player turn loads:

| Component | Size | Loaded By | Every Turn? |
|-----------|:----:|:---------:|:-----------:|
| Execution protocol (embedded) | 18.0 KB | Python code | Yes (Player) |
| Coach agent definition | 18.4 KB | SDK | Yes (Coach) |
| Player agent definition | 8.1 KB | SDK | Yes (Player) |
| CLAUDE.md (root) | 7.5 KB | SDK | Yes |
| .claude/CLAUDE.md | 1.0 KB | SDK | Yes |
| .claude/rules/ (ALL files) | 63.2 KB | SDK | Yes |
| **Total static baseline** | **~116 KB** | | **Every turn** |

On top of this, per-turn dynamic content adds 4-15 KB (task requirements, coach feedback, Graphiti context).

**For a local 32B model with 32K context window, ~116 KB of static context is devastating.** That's ~29K tokens (at ~4 chars/token) leaving almost no room for the actual task and model reasoning.

### Rules Breakdown (63.2 KB loaded every turn)

| Rule File | Size | Needed for AutoBuild? |
|-----------|:----:|:---------------------:|
| anti-stub.md | 6.0 KB | Yes (embedded in protocol too) |
| autobuild.md | 5.9 KB | Yes |
| orchestrators.md (pattern) | 11.7 KB | Rarely |
| pydantic-models.md (pattern) | 4.1 KB | Rarely |
| dataclasses.md (pattern) | 3.9 KB | Rarely |
| template.md (pattern) | 3.6 KB | No |
| agent-development.md (guidance) | 4.3 KB | No |
| clarifying-questions.md | 4.1 KB | No (AutoBuild doesn't ask questions) |
| graphiti-knowledge.md | 4.4 KB | No (handled by Python code) |
| task-workflow.md | 4.2 KB | Maybe |
| python-library.md | 3.7 KB | Maybe |
| testing.md | 4.0 KB | Yes |
| hash-based-ids.md | 1.4 KB | Yes |
| feature-build-invariants.md | 1.9 KB | Only for feature-build |
| **Total** | **63.2 KB** | **~17 KB essential** |

**~46 KB of rules are loaded every turn that AutoBuild doesn't need.** That's ~11.5K wasted tokens per turn.

## Finding 2: Seed Function Seeds All 7 Templates (Original Finding — Confirmed)

The 17 categories in `seed_all_system_context()` are hardcoded with no template filtering. For a fastapi-python project, 77 out of 97 template-specific episodes are irrelevant (79% waste).

| Content Type | Total Episodes | Relevant (fastapi-python) | Wasted |
|-------------|:--------------:|:-------------------------:|:------:|
| Templates | 7 | 2 (fastapi + default) | 5 |
| Agents | 18 | 3 | 15 |
| Rules | 72 | 15 | 57 |
| **Total** | **97** | **20** | **77** |

Template-specific content has 3x the timeout rate (39% vs 12%), disproportionately inflating the 263-minute duration.

## Finding 3: Seeding Doesn't Actually Reduce Static Context Loading

This is the critical gap. Even after successful seeding:

1. **SDK still loads all `.claude/rules/`** — seeding rules into Graphiti doesn't prevent the SDK from also loading them from disk
2. **Execution protocol is always embedded** — 18 KB hardcoded in `_build_implementation_prompt_with_protocol()`
3. **Agent definitions always load** — SDK discovers and loads the full agent .md file
4. **CLAUDE.md always loads** — SDK injects it as system context

**The seeding is additive, not substitutive.** Graphiti context (2-8 KB) loads _on top of_ the 116 KB static baseline, making the problem worse when Graphiti is enabled.

## Finding 4: No Cross-Template Dependencies (Original Finding — Confirmed)

Zero cross-template references found. Each template's rules, agents, and manifests are fully self-contained. Selective seeding and selective rule loading are both safe.

## Finding 5: `seed-system` Already Has Template Filtering

The `seed-system` command uses `resolve_template_path()` which:
1. Accepts explicit `--template` flag
2. Auto-detects from `manifest.json` in cwd
3. Falls back to "default"

This pattern can be reused for both the `seed` command and for static context filtering.

---

## Root Cause Analysis

The performance problem on local LLMs has **three root causes**:

### Root Cause 1: SDK Loads All Rules Without Filtering
`setting_sources=["project"]` tells the SDK to load everything in `.claude/rules/`. There is no mechanism to say "only load these rules for this agent type."

### Root Cause 2: Execution Protocol Is Always Fully Embedded
The 18 KB protocol is injected as a string in `_build_implementation_prompt_with_protocol()`. No mode-specific trimming.

### Root Cause 3: Seeding Is Additive, Not Substitutive
Graphiti seeding was designed to make knowledge searchable, not to replace static loading. Both systems run simultaneously, doubling the context for overlapping content.

---

## Option Evaluation

### Option A: Selective Rule Loading for AutoBuild (Highest Impact — Recommended)

**Description**: Create an AutoBuild-specific rules subset. Either:
- (A1) Move non-essential rules to a subdirectory that the SDK doesn't load for AutoBuild worktrees
- (A2) Create a minimal `.claude/rules/` in AutoBuild worktrees with only essential rules

**Implementation**:
- When AutoBuild creates a worktree, copy only essential rules (~17 KB instead of 63 KB)
- Or: restructure rules into `.claude/rules/autobuild/` (always loaded) and `.claude/rules/interactive/` (only for interactive sessions)

| Criterion | Score |
|-----------|:-----:|
| Context reduction | **~46 KB saved per turn** (~11.5K tokens) |
| Effort | Medium (4/10) |
| Risk | Low |
| Compatibility | Full (interactive sessions unchanged) |

### Option B: Template Filtering in `guardkit graphiti seed` (Medium Impact)

**Description**: Add `--template` filter to the `seed` command (original recommendation).

| Criterion | Score |
|-----------|:-----:|
| Seed time reduction | **40-60%** (~108-158 min saved) |
| Effort | Low (3/10) |
| Risk | Low |
| Compatibility | Full |

### Option C: Trim Execution Protocol by Mode (Medium Impact)

**Description**: Create mode-specific protocol variants:
- `autobuild_protocol_standard.md` (~10 KB) — core phases only
- `autobuild_protocol_tdd.md` (~12 KB) — with TDD-specific phases
- `autobuild_protocol_full.md` (18 KB) — current full version

| Criterion | Score |
|-----------|:-----:|
| Context reduction | **6-8 KB saved per turn** (~2K tokens) |
| Effort | Medium (4/10) |
| Risk | Low-Medium (risk of missing guidance) |
| Compatibility | Full |

### Option D: Context-Aware Agent Definitions (Lower Impact)

**Description**: Create slimmed-down agent definitions for local LLM use:
- `autobuild-player-local.md` (~4 KB instead of 8.1 KB)
- `autobuild-coach-local.md` (~9 KB instead of 18.4 KB)

| Criterion | Score |
|-----------|:-----:|
| Context reduction | **~13 KB saved per turn** (~3.3K tokens) |
| Effort | Medium (5/10) |
| Risk | Medium (may lose important guidance) |
| Compatibility | Separate files for local vs cloud |

### Option E: Accept Current Behaviour

| Criterion | Score |
|-----------|:-----:|
| Savings | None |
| Effort | None |
| Risk | None |
| Compatibility | Full |

---

## Decision Matrix

| Option | Context Saved/Turn | Seed Time Saved | Effort | Risk | Priority |
|--------|:-----------------:|:---------------:|:------:|:----:|:--------:|
| **A: Selective Rules** | **46 KB** | — | 4/10 | Low | **1 (Highest)** |
| **B: Seed Template Filter** | — | **108-158 min** | 3/10 | Low | **2** |
| **C: Trim Protocol** | **6-8 KB** | — | 4/10 | Low-Med | **3** |
| **D: Slim Agent Defs** | **13 KB** | — | 5/10 | Medium | **4** |
| E: Accept Status Quo | 0 | 0 | 0 | None | — |

---

## Recommended Approach: A + B Combined

### Phase 1: Selective Rule Loading (Option A) — Biggest Win

**Target**: Reduce rules from 63 KB to ~17 KB per AutoBuild turn.

**Essential rules for AutoBuild** (keep):
- `autobuild.md` (5.9 KB) — workflow guidance
- `anti-stub.md` (6.0 KB) — quality gate
- `hash-based-ids.md` (1.4 KB) — ID format
- `testing.md` (4.0 KB) — test guidance
- **Total: ~17 KB**

**Non-essential for AutoBuild** (exclude from worktree):
- `patterns/` directory (23.3 KB) — code patterns for interactive development
- `guidance/` directory (4.3 KB) — agent development guidance
- `clarifying-questions.md` (4.1 KB) — interactive Q&A
- `graphiti-knowledge.md` (4.4 KB) — handled by Python code
- `feature-build-invariants.md` (1.9 KB) — feature-build only
- `python-library.md` (3.7 KB) — general Python guidance
- `task-workflow.md` (4.2 KB) — task file format (not needed during coding)
- **Total excluded: ~46 KB**

**Implementation approach**:
When creating AutoBuild worktrees, configure `.claude/rules/` with only essential rules. The worktree creation already copies files — this is just filtering which rules get copied.

**Estimated impact**: From ~116 KB to ~70 KB per turn = **40% context reduction**.

### Phase 2: Seed Template Filtering (Option B) — Quick Win

**Target**: Reduce seed time from ~263 min to ~105-155 min.

Add `--template` parameter to `seed_all_system_context()`, using existing `resolve_template_path()` logic. Filter `seed_templates()`, `seed_agents()`, `seed_rules()` to only process the relevant template + default.

**Implementation**: ~50 LOC across 5 files. Complexity 3/10.

### Combined Impact

| Metric | Before | After (Phase 1+2) | Improvement |
|--------|:------:|:-----------------:|:-----------:|
| Static context per turn | ~116 KB | ~70 KB | **40% reduction** |
| Tokens per turn (static) | ~29K | ~17.5K | **11.5K tokens freed** |
| Seed duration | ~263 min | ~105-155 min | **40-60% faster** |
| Wasted episodes | 77 | 0 | **100% eliminated** |

---

## Implementation Complexity

| Phase | Files Changed | LOC | Effort | Risk |
|-------|:------------:|:---:|:------:|:----:|
| Phase 1 (Rules) | 1-2 (worktree setup) | ~30 | 2-3 hours | Low |
| Phase 2 (Seed Filter) | 5 | ~50 | 2-4 hours | Low |
| **Total** | **6-7** | **~80** | **4-7 hours** | **Low** |

---

## Appendix A: Per-Turn Context Budget for Local LLMs

For Qwen 2.5 Coder 32B with 32K context:

| Component | Tokens (est.) | % of Budget |
|-----------|:------------:|:-----------:|
| Static context (current) | ~29K | 91% |
| Task requirements | ~500 | 1.5% |
| Coach feedback | ~1K | 3% |
| Model reasoning | ~1.5K | 4.5% |
| **Total** | **~32K** | **100%** |

After Phase 1 (selective rules):

| Component | Tokens (est.) | % of Budget |
|-----------|:------------:|:-----------:|
| Static context (reduced) | ~17.5K | 55% |
| Task requirements | ~500 | 1.5% |
| Coach feedback | ~1K | 3% |
| Graphiti context | ~2K | 6% |
| **Model reasoning** | **~11K** | **34.5%** |
| **Total** | **~32K** | **100%** |

This frees up **~11K tokens for actual reasoning** — a significant improvement for a 32K context model.

## Appendix B: Seeding Category Classification

| Category | Episodes | Type | Duration Impact |
|----------|:--------:|:----:|:---------------:|
| product_knowledge | 3 | Universal | Low |
| command_workflows | 20 | Universal | Low |
| quality_gate_phases | 12 | Universal | Low |
| technology_stack | 7 | Universal | Low |
| feature_build_architecture | 8 | Universal | Low |
| architecture_decisions | ~5 | Universal | Low |
| failure_patterns | 4 | Universal | Low |
| component_status | 6 | Universal | Low |
| integration_points | 3 | Universal | Low |
| patterns | 5 | Universal | Low |
| project_overview | 3 | Project | Low |
| project_architecture | 3 | Project | Low |
| failed_approaches | ~3 | Project | Low |
| pattern_examples | 7 | Universal | Low |
| **templates** | **7** | **Template** | **Medium** |
| **agents** | **18** | **Template** | **High** |
| **rules** | **72** | **Template** | **Very High** |
