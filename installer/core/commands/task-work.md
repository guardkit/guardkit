---
format_version: 1
description: Unified implementation command — full quality-gated workflow from task load to finalization.
---

# Task Work - Unified Implementation Command

## ⚠️ Working Directory Requirement

Run from YOUR PROJECT ROOT (where `tasks/`, `src/`, `.claude/` live) — NEVER from
the RequireKit/GuardKit framework directories. Task files belong to your project;
running from a framework directory reads and writes the wrong `tasks/` tree.
Quick check: `ls` should show your project's files. Full directory guide +
RequireKit integration: `task-work-reference-ext.md` § Working Directory Requirement.

## Command Syntax

```bash
/task-work TASK-XXX [--mode=standard|tdd|bdd] [--intensity=minimal|light|standard|strict] [--design-only | --implement-only] [--docs=minimal|standard|comprehensive] [--no-questions | --with-questions | --defaults | --answers="1:Y 2:N 3:JWT"] [--autobuild-mode] [--complete | --pause] [other-flags...]
```

## Available Flags

The single normative flag-definition site (PB-9). Values, defaults, composite
expansion, and conflicts are defined HERE; other sections and slices point back.

| Flag | Values / Default | Effect | Conflicts |
|------|------------------|--------|-----------|
| `--mode=standard\|tdd\|bdd` | default `standard` | Development mode; `bdd` requires RequireKit (marker check in Step 0) | invalid value → error + mode help |
| `--intensity=minimal\|light\|standard\|strict` | default auto-detected | Ceremony level (phase gating, review depth); invalid value → warn + auto-detect | `--design-only`, `--implement-only` |
| `--micro` | off | Alias for `--intensity=minimal` (streamlined micro-task phase set) | `--design-only`, `--implement-only` |
| `--design-only` | off | Stop at Phase 2.8 checkpoint, save approved plan | `--implement-only`, `--micro` |
| `--implement-only` | off | Start at Phase 3 from a previously approved plan | `--design-only`, `--micro` |
| `--docs=minimal\|standard\|comprehensive` | default `minimal` (hierarchy in Step 2.5) | Documentation verbosity | — |
| `--no-questions` | off | Skip Phase 1.6 clarification | wins over all other clarification flags |
| `--with-questions` | off | Force Phase 1.6 even at complexity 1-2 | overridden by `--no-questions` |
| `--defaults` | off | Use clarification defaults without prompting | `--answers` wins per-question |
| `--answers="1:Y 2:N …"` | — | Inline clarification answers (automation) | overrides `--defaults` |
| `--reclarify` | off | Re-run clarification, ignoring saved decisions | — |
| `--no-library-context` | off | Skip Phase 2.1 Context7 library docs | — |
| `--autobuild-mode` | off | Composite: expands to `--no-questions --skip-arch-review --auto-approve-checkpoint --docs=minimal`; individual sub-flags ignored while set | Phase 6 never auto-completes in this mode |
| `--auto-approve-checkpoint` | off | Auto-approve Phase 2.8 checkpoint (no human present) | — |
| `--skip-arch-review` | off | Skip Phase 2.5B architectural review | — |
| `--complete` | off | Run Phase 6 Finalize on green evidence (DF-018; requires the shared completion routine — until that build lands, report it missing) | never in `--autobuild-mode` or for `operator_handoff` tasks |
| `--pause` (alias `--no-complete`) | off | Force the Amber pause at IN_REVIEW even when Phase 6 is enabled | — |

Per-flag guides (intensity levels, micro mode, design-first, clarification,
docs levels, autobuild, Context7): `task-work-flags-ext.md`.

## Phase & Step Sequence

The execution protocol runs Steps 0–8, then Phase 6. Step 4 invokes these
phases via the Task tool (gates below; full bodies in the named slice —
plan = `task-work-phases-plan-ext.md`, build = `task-work-phases-build-ext.md`):

| Phase | Runs when | Slice |
|---|---|---|
| 1 Requirements Analysis | require-kit only (skipped in GuardKit) | plan |
| 1.6 Clarifying Questions | complexity-gated: 1-2 skip unless `--with-questions` · 3-4 quick · 5+ full; skipped by `--no-questions` | plan |
| 1.7 Pre-Implementation Architecture Check | complexity ≥ 7 | plan |
| 1.8 Feature Diagram Review Prompt | feature-linked tasks | plan |
| 2.1 Library Context (Context7 MCP) | unless `--no-library-context` | plan |
| 2 Implementation Planning | always | plan |
| 2.5A Pattern Suggestion | conditional — skipped for simple tasks | plan |
| 2.5B Architectural Review | unless `--skip-arch-review` (autobuild skips ≤5) | plan |
| 2.7 Complexity Evaluation | always (routes review mode) | plan |
| 2.6 Human Checkpoint | when complexity evaluation or critical task triggers it | plan |
| 2.7 Plan Generation & Complexity Evaluation | always | plan |
| 2.8 Human Plan Checkpoint | blocking unless `--auto-approve-checkpoint`; `--design-only` stops here | plan |
| 2.9 Workflow Routing | always — continue into Phase 3 | plan |
| 3-BDD BDD Test Generation | `--mode=bdd` only | build |
| 3 Implementation | always | build |
| 4 Testing | always | build |
| 4.5 Fix Loop | until 100% tests pass (or blocked) | build |
| 5 Code Review | always | build |
| 5.5 Plan Audit | after Phase 5; skipped in `--micro` / when no plan exists | build |
| 6 Finalize | gated — `### Phase 6` below (DF-018) | build |

## 🎯 EXECUTION PROTOCOL - START HERE IMMEDIATELY

When user runs `/task-work TASK-XXX [flags]`, **EXECUTE THIS EXACT SEQUENCE**:

### Step 0: Parse and Validate Flags (ENHANCED - Design-first + Documentation Levels)

**PARSE** every flag from the command line against the `## Available Flags`
table above — it is the single normative definition site (PB-9): values,
defaults, the `--autobuild-mode` composite expansion, and clarification-flag
precedence (`--no-questions` > `--with-questions` > `--answers` > `--defaults`)
are defined there, not re-stated here.

**VALIDATE** BDD mode requirements (TASK-BDD-FIX1):

When `--mode=bdd`, confirm RequireKit is installed by checking for the
presence of `~/.agentecflow/require-kit.marker.json` (preferred) or the
legacy `require-kit.marker`. If neither exists, print the RequireKit
installation instructions (repository: `https://github.com/requirekit/require-kit`,
installer: `cd ~/Projects/require-kit && ./installer/scripts/install.sh`)
and suggest `--mode=tdd` or `--mode=standard` as alternatives, then exit.

**VALIDATE** flag mutual exclusivity:

Reject combinations that don't make sense together:
- `--design-only` with `--implement-only` (pick one workflow mode)
- `--micro` with `--design-only` or `--implement-only` (micro mode has its own phase set)

When a conflict is detected, print which flags conflict and what the user
probably meant, then exit non-zero.

**DISPLAY** active flags (development mode, workflow mode, autobuild, docs
level) — banner formats: `task-work-flags-ext.md` § Step 0 Display Banners.

**PROCEED** to Step 1 with flag context.

### Step 1: Load Task Context (REQUIRED - Multi-phase file resolution)

This step implements robust file resolution supporting descriptive filenames and automatic state detection.


- **Phase 1.1 Parse and Validate Task ID** — accept a `TASK-XXX`-style id; invalid shape → error.
- **Phase 1.2 Multi-State File Search** — search every `tasks/{state}/` directory, descriptive filenames included.
- **Phase 1.3 Handle Search Results** — none → error with guidance; multiple → disambiguate; one → proceed.
- **Phase 1.4 Automatic State Transition** — a file found in a non-active state moves to the active directory when the transition rules allow it.
- **Phase 1.5 Load Task Context** — frontmatter, description, acceptance criteria, epic/feature context (+ require-kit fields when installed).
- **Phase 1.7 Fleet-Memory Context Loading** — tiered MCP→CLI availability check; architecture/failure/turn-state queries populate `task_context`.

Full procedure: `task-work-phases-plan-ext.md` § Step 1.

### Step 2: Detect Technology Stack (REQUIRED - 10 seconds)

**READ** `.claude/settings.json` and extract `project.template` value.

If file exists: Use `project.template` value
If file not exists: Set stack to "default"

**DISPLAY**: "🔍 Detected stack: {stack}"

### Step 2.5: Determine Documentation Level (NEW - TASK-036)

**PURPOSE**: Establish documentation verbosity based on configuration hierarchy

**Configuration Hierarchy** (highest to lowest priority):
1. Command-line flag: `--docs=minimal|standard|comprehensive`
2. Force-comprehensive triggers (security, compliance, breaking changes)
3. Settings.json default: `.claude/settings.json` → `documentation.default_level`
4. Default: `minimal` (use `--docs=standard` to lift)

Full load/evaluate/display procedure: `task-work-phases-plan-ext.md` § Step 2.5.

### Step 3: Agent Discovery (Automatic)

**Agent selection is DYNAMIC** based on metadata matching. The system:

1. Analyzes task context (stack, phase, keywords from description)
2. Scans all agent sources (Local > User > Global > Template)
3. Returns best match based on metadata (stack, phase, capabilities, keywords)

**No action required** - Discovery happens automatically during each phase.

**See**: [Agent Discovery System](#agent-discovery-system) for complete details on:
- Discovery sources and precedence
- Metadata requirements
- Template override behavior
- Source indicators (📁 📦 🌐)
- Troubleshooting

**Agent selection results** are shown in the invocation log after task completion.

### Step 3.5: Initialize Invocation Tracker

**INITIALIZE INVOCATION TRACKER**:
```python
from installer.core.commands.lib import AgentInvocationTracker

# Initialize tracker for execution visibility
tracker = AgentInvocationTracker()
```

**Purpose**: Records which agents are invoked, their sources, and execution
status. The post-phase verification happens later via
`validate_agent_invocations` in Step 6.5, not per-phase.

**See**: TASK-ENF2 (invocation tracking), TASK-FIX-RWOP1.3.1 (validator wire
into the autobuild producer path).

### Step 4: INVOKE TASK TOOL FOR EACH PHASE (REQUIRED - DO NOT SKIP)

**⚠️ CRITICAL: YOU MUST USE THE TASK TOOL. DO NOT ATTEMPT TO DO THE WORK YOURSELF.**

Execute the phases from `## Phase & Step Sequence` in order, honoring each
phase's gate. For every phase that runs: READ its full body in the slice the
sequence table names, INVOKE the Task tool with that phase's agent and prompt,
WAIT for completion, record the invocation in the tracker (Step 3.5). Do not
skip phases the gates require; do not run phases the gates skip.

### Step 5: Evaluate Quality Gates (REQUIRED)

**Note**: Phase 4.5 (Fix Loop) already enforces test compilation and passing. This step evaluates final quality metrics.

Based on final results after Phase 4.5, **EVALUATE**:

| Gate | Threshold | Result |
|------|-----------|--------|
| Code compiles | 100% | ✅ or ❌ (Phase 4.5 enforced) |
| All tests passing | 100% | ✅ or ❌ (Phase 4.5 enforced) |
| Line coverage | ≥ 80% | ✅ or ❌ |
| Branch coverage | ≥ 75% | ✅ or ❌ |
| Test execution time | < 30s | ✅ or ⚠️ |

### Step 6: Determine Next State (REQUIRED)

**Task state routing is Coach-driven, not Player-driven.** In autobuild, the Player writes the qualitative summary of Phase 4.5 into `task_work_results.json` (compilation status, test pass/fail counts, coverage). Coach reads that payload, runs its own independent pytest pass in `coach_validator`, and decides the next state. In interactive `/task-work` sessions without Coach, the same routing logic is applied qualitatively by Claude against the same thresholds.

**Routing rules** (applied by Coach in autobuild, applied qualitatively by Claude otherwise):

| Condition observed in results | Next state | Rationale |
|---|---|---|
| Compilation errors remain after fix guidance | `blocked` | Code must build before it can be reviewed. |
| Any test failure remains (pass rate < 100 %) | `blocked` | Zero-tolerance gate; enforced by Coach's own pytest run. |
| Line coverage below 80 % (or branch below 75 %) | `in_progress` — re-invoke testing agent for more tests | Coverage is a reviewable gate, not a terminal one. |
| Clean compile, all tests passing, coverage thresholds met | `in_review` | Only path out of IN_PROGRESS. |

The thresholds above (≥ 80 % line, ≥ 75 % branch) are the same numbers `coach_validator` applies — the Player's self-report and Coach's independent verification are expected to agree; if they disagree, Coach's verdict wins.

**STATE TRANSITION RULES**:

- ✅ **Phase 4.5 SUCCESS (all tests passing) + Coverage ≥ thresholds**:
  → Move task to `tasks/in_review/TASK-XXX.md`
  → All quality gates passed, ready for human review
  → **This is the ONLY path to IN_REVIEW state**

- ⚠️ **Phase 4.5 SUCCESS but coverage below threshold**:
  → Keep task in `tasks/in_progress/TASK-XXX.md`
  → **RE-INVOKE** testing agent to add more tests
  → Do NOT proceed until coverage threshold met
  → Loop back to Phase 4
  → **MUST NOT move to IN_REVIEW**

- ❌ **Phase 4.5 BLOCKED (max fix attempts exhausted with failures)**:
  → Move task to `tasks/blocked/TASK-XXX.md`
  → Include detailed diagnostics in task file:
    - Compilation errors (if any)
    - Test failure details
    - Fix attempts made
    - Recommended next steps
  → Notify that manual intervention required
  → **MUST NOT move to IN_REVIEW**

### Step 6.5: Validate Agent Invocations (CRITICAL - Prevent False Reporting)

**Purpose**: Guarantee that the `agent_invocations` list the Player emits into `task_work_results.json` matches the phases the workflow required. Without this gate the Player can emit any phase set (or none) and Coach will trust it — false reporting becomes a free move.

**This is the ONLY deterministic checkpoint that prevents false reporting.** The framing from earlier spec revisions is still true — what changed is that the check now *actually runs*. It is no longer an in-loop instruction the Claude runtime is asked to execute mid-flight; it is wired into the producer script so it fires on every results-file write.

Producer wire, verdict schema, and failure handling:
`task-work-phases-build-ext.md` § Step 6.5.

### Step 7: Generate Report (REQUIRED)

**OUTPUT** comprehensive report based on outcome:

success report (all tests passing) or blocked report (remaining failures +
diagnostics + fix attempts). Templates: `task-work-phases-build-ext.md`
§ Step 7 — Report Templates.

### Step 8: Commit State Files to Git (REQUIRED for Conductor Support)

**CRITICAL**: After completing all phases and generating the report, commit all state files to git. This ensures that state is preserved across git worktrees (used by Conductor.build for parallel development).

**EXECUTE** the following Python code:

```python
from installer.core.commands.lib.git_state_helper import commit_state_files

# Commit all state files for this task
# This includes:
# - docs/state/{task_id}/implementation_plan.md
# - docs/state/{task_id}/audit_report.json (if Phase 5.5 executed)
# - Any other state files created during workflow

try:
    commit_state_files(
        task_id="{task_id}",
        message=f"Save implementation state for {task_id} (workflow complete)"
    )
    print("✅ State files committed to git")
except Exception as e:
    # Don't fail workflow if git commit fails
    # (may not be in a git repo, or git may not be available)
    print(f"⚠️  Warning: Could not commit state files: {e}")
    print("   (This is non-critical - workflow can continue)")
```

**Why this is needed:**

- **Conductor.build** uses git worktrees for parallel development
- Each worktree has its own working directory but shares the same git repository
- State files in `docs/state/` MUST be committed to be visible across all worktrees
- Without this step, state loss occurs when switching between worktrees

**When to skip:**

- Only skip if not in a git repository (e.g., running in a sandboxed environment)
- Error handling ensures workflow continues even if git commit fails

**What gets committed:**

- All files in `docs/state/{task_id}/` directory
- Commit message includes task ID for traceability
- Does NOT push to remote (that's a separate operation)

---

### Phase 6: Finalize (Completion — DF-018)

Runs AFTER Step 8, and ONLY when ALL of the following hold:

- Step 6 routed the task to `in_review` via Phases 4/4.5/5/5.5 — the only path;
- `--complete` was passed (rollout phase 2 is opt-in; the default flips to
  auto-complete-on-green with `--pause` opt-out only after the demotion scope §6
  metric window — that flip is a later one-line edit here);
- NOT in `--autobuild-mode` — merge-before-complete: feature-build merges first,
  and the autobuild lane completes via feature-complete calling the same shared
  routine post-merge;
- the task is NOT `task_type: operator_handoff` (their completion path is
  feature-complete.md);
- fails CLOSED through `qa.enforce_tier1` when the flag is on (WS2-B2).

Tri-state on the Phase 5.5 checkpoint evidence:

- **Green** (deterministic audit clean + review clean): invoke
  `guardkit task complete TASK-XXX` — the shared atomic completion routine (six
  pre-completion gates → atomic status-flip + file-move → related-file archival →
  rollup/PM sync → fleet-memory capture-outcome → conductor git-state commit) —
  then display the verify-then-record evidence banner;
- **Amber** (any non-clean audit, review concerns, or `--pause`): stop at
  IN_REVIEW with specifics — today's behavior;
- **Red**: BLOCKED.

Banner formats + rollout mechanics: `task-work-phases-build-ext.md`
§ Phase 6 — Finalize Detail.

## ⚠️ CRITICAL REMINDER

**DO NOT ATTEMPT TO IMPLEMENT THE TASK YOURSELF**

This command requires **Task tool invocations for each phase**. Your role is to:
1. ✅ Detect the stack
2. ✅ Select the correct agents
3. ✅ Invoke Task tool for each phase
4. ✅ Aggregate results and generate report

**DO NOT**:
- ❌ Write implementation code directly
- ❌ Write test code directly
- ❌ Skip agent invocations
- ❌ Attempt to do all phases yourself

The agents are specialized and will produce better results than doing it yourself.

## Reference Slices (load on demand)

K13 core/`-ext` shape — four sibling slices in this directory. Read on demand:

| Need | Slice |
|---|---|
| Per-flag guides (intensity, micro, design-first, clarification, docs, autobuild, Context7), Step 0 banners | `task-work-flags-ext.md` |
| Step 1 + Step 2.5 full procedures; Phase 1–2.9 full bodies | `task-work-phases-plan-ext.md` |
| Phase 3–5.5 full bodies; Step 6.5 mechanics; Step 7 report templates; Phase 6 detail | `task-work-phases-build-ext.md` |
| Feature detection, full working-directory guide, additional context (modes narrative, agent discovery, troubleshooting) | `task-work-reference-ext.md` |

Wave-2 fence: the pinned templates (`feature-spec.md`/`feature-plan.md`) are NOT
part of this structure — any change to them rides the DF-019 batched re-pin only.

