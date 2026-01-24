# AutoBuild Workflow Guide

**Version**: 1.0.0
**Last Updated**: 2026-01-24
**Compatibility**: GuardKit v1.0+, Claude Agent SDK v0.1.0+
**Document Type**: Comprehensive Architecture and Usage Guide

---

## Table of Contents

### Part 1: Overview & Quick Start
- [What is AutoBuild?](#what-is-autobuild)
- [Key Concepts](#key-concepts)
- [Quick Start Examples](#quick-start-examples)

### Part 2: Architecture Deep-Dive
- [Player-Coach Adversarial Cooperation](#player-coach-adversarial-cooperation)
- [Comparison with Ralph Wiggum Loop](#comparison-with-ralph-wiggum-loop)
- [Key Techniques from Anthropic Research](#key-techniques-from-anthropic-research)
- [Quality Gate Delegation](#quality-gate-delegation)

### Part 3: Using AutoBuild
- [From Claude Code (Slash Command)](#from-claude-code-slash-command)
- [From Shell (Python CLI)](#from-shell-python-cli)
- [CLI Reference](#cli-reference)
- [Configuration Options](#configuration-options)

### Part 4: Advanced Topics
- [Feature Orchestration](#feature-orchestration)
- [Pre-Loop Design Phase](#pre-loop-design-phase)
- [Resume and State Management](#resume-and-state-management)
- [Troubleshooting](#troubleshooting)

---

# Part 1: OVERVIEW & QUICK START

## What is AutoBuild?

**AutoBuild** is GuardKit's autonomous task implementation system that uses a Player-Coach adversarial cooperation workflow to generate production-quality code with minimal human intervention.

### Core Philosophy

AutoBuild operates on the principle of **adversarial cooperation** - two agents with different roles work together through a dialectical process:

- **Player Agent**: Implements code, writes tests, and produces deliverables
- **Coach Agent**: Validates implementation against acceptance criteria and quality gates

This separation ensures independent verification - the same agent that writes the code cannot approve it.

### Why AutoBuild?

| Traditional `/task-work` | AutoBuild `/feature-build` |
|--------------------------|---------------------------|
| Human-driven execution | Autonomous execution |
| Interactive checkpoints | Automatic approval based on quality gates |
| Single pass implementation | Iterative improvement (up to N turns) |
| Manual quality verification | Independent Coach validation |
| Good for exploratory work | Good for well-defined requirements |

### When to Use AutoBuild

**Use AutoBuild when:**
- Requirements are clear and well-defined
- Acceptance criteria can be objectively verified
- Standard implementation patterns apply
- You want autonomous iteration without manual intervention
- Implementing a feature with multiple related tasks

**Use manual `/task-work` instead when:**
- Requirements are exploratory or unclear
- Complex architectural decisions needed
- High-risk changes requiring human judgment
- Novel or unusual requirements

---

## Key Concepts

### 1. Dialectical Loop

```
┌─────────────────────────────────────────────────────────────┐
│                     DIALECTICAL LOOP                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                    ┌──────────────┐      │
│  │   PLAYER     │                    │    COACH     │      │
│  │   Agent      │───────────────────▶│    Agent     │      │
│  └──────────────┘   Implementation   └──────────────┘      │
│        │            Report                  │               │
│        │                                    │               │
│        │            Feedback                │               │
│        │◀───────────────────────────────────│               │
│        │            or Approval             │               │
│        │                                    │               │
│  Capabilities:                       Capabilities:          │
│  - Full file system access           - Read-only access     │
│  - Code implementation               - Test execution       │
│  - Test creation                     - Quality validation   │
│  - task-work delegation              - Criteria verification│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Worktree Isolation

All AutoBuild work happens in isolated git worktrees:
- **Location**: `.guardkit/worktrees/TASK-XXX/` or `.guardkit/worktrees/FEAT-XXX/`
- **Branch**: `autobuild/TASK-XXX` or `autobuild/FEAT-XXX`
- **Isolation**: Changes don't affect main branch until manually merged
- **Preservation**: Worktrees are never auto-deleted (human review required)

### 3. Quality Gate Delegation

AutoBuild **delegates** to `/task-work --implement-only` rather than implementing directly. This provides:
- **100% code reuse** with proven task-work quality gates
- **Stack-specific subagents** (python-api-specialist, react-specialist, etc.)
- **Phase 4.5 test enforcement** (auto-fix up to 3 attempts)
- **Code review** by dedicated code-reviewer agent

---

## Quick Start Examples

### Example 1: Single Task

```bash
# From Claude Code
/feature-build TASK-AUTH-001

# From shell
guardkit autobuild task TASK-AUTH-001
```

### Example 2: Entire Feature

```bash
# From Claude Code
/feature-build FEAT-A1B2

# From shell
guardkit autobuild feature FEAT-A1B2
```

### Example 3: With Options

```bash
# More iterations for complex tasks
guardkit autobuild task TASK-AUTH-001 --max-turns 10

# Verbose output with debug logging
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-AUTH-001 --verbose

# Resume interrupted execution
guardkit autobuild feature FEAT-A1B2 --resume
```

---

# Part 2: ARCHITECTURE DEEP-DIVE

## Player-Coach Adversarial Cooperation

### The Adversarial Cooperation Pattern

> **Research Foundation**: AutoBuild's adversarial cooperation pattern is based on
> [Block AI's "Adversarial Cooperation in Code Synthesis" research](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf)
> (December 2025), which introduces **dialectical autocoding** - a framework for AI agents
> to write code autonomously through a structured coach-player feedback loop.

Unlike traditional single-agent systems, AutoBuild uses **two distinct agents** with different roles and capabilities:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AUTOBUILD ORCHESTRATION FLOW                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PreLoopQualityGates (optional)                                            │
│       │                                                                     │
│       ▼                                                                     │
│  task-work --design-only (if enable_pre_loop=True)                         │
│       │                                                                     │
│       ▼ (returns plan, complexity)                                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│  ADVERSARIAL LOOP (max_turns iterations)                                    │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  PLAYER TURN:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ task-work --implement-only --mode=tdd                               │    │
│  │     │                                                               │    │
│  │     ├── Phase 3: Implementation (stack-specific agent)             │    │
│  │     ├── Phase 4: Testing (test-orchestrator)                       │    │
│  │     ├── Phase 4.5: Fix Loop (auto-fix, 3 attempts)                 │    │
│  │     └── Phase 5: Code Review (code-reviewer)                       │    │
│  │                                                                     │    │
│  │ Output: Implementation complete, tests passing, code reviewed       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  COACH TURN:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ CoachValidator                                                      │    │
│  │     │                                                               │    │
│  │     ├── Quality gate profile selection (by task_type)              │    │
│  │     ├── Test result verification                                   │    │
│  │     ├── Coverage threshold check                                   │    │
│  │     ├── Plan audit validation                                      │    │
│  │     └── Decision: APPROVE or FEEDBACK                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  (repeat until approved or max_turns)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Adversarial Cooperation Works

1. **Independent Verification**: The agent that writes code cannot approve it
2. **Discard Self-Reports**: Coach ignores Player's success claims and verifies independently (key insight from Block research)
3. **Different Capabilities**: Player has full access, Coach has read-only (can only run tests)
4. **Iterative Improvement**: Feedback loops drive convergence to acceptance criteria
5. **Quality Enforcement**: Coach validates against objective quality gates

### The Core Insight from Block's Research

Block's research identified a critical failure mode in single-agent systems: **premature success declaration**. When an agent is allowed to assess its own work, it tends to "drift from specs" and "declare success prematurely" through circular verification.

The solution is **adversarial cooperation**:

> "Discard the player's self-report of success. Have the coach perform independent evaluation."
> — Block AI Research, "Adversarial Cooperation in Code Synthesis"

In GuardKit's implementation:
- **Player** implements and claims completion
- **Coach** re-reads original requirements and verifies independently
- Coach **ignores** what Player says it did
- Coach runs tests and validates output directly

### Architectural Benefits (from Block Research)

| Problem | Single Agent | Coach-Player (Adversarial) |
|---------|-------------|---------------------------|
| **Anchoring** | Drifts from specs | Requirements anchor every turn |
| **Context Pollution** | Accumulates noise | Fresh context per phase |
| **Completion** | Open-ended, premature claims | Explicit approval gates |
| **Verification** | Circular (self-assessment) | Independent (coach verifies) |

---

## Comparison with Ralph Wiggum Loop

AutoBuild was influenced by the **Ralph Wiggum** plugin from Anthropic's Claude Code research. Here's how they compare:

### Architecture Comparison

| Aspect | Ralph Wiggum | AutoBuild Player-Coach |
|--------|--------------|------------------------|
| **Agent Count** | Single (self-referential) | Dual (Player + Coach) |
| **Loop Mechanism** | Stop hook blocks exit | Orchestrator-driven loop |
| **Completion Detection** | Promise tag exact match (`<promise>COMPLETE</promise>`) | Coach decision (approve/feedback) |
| **Context Preservation** | Files + git history | Feedback summary + task state |
| **Quality Gates** | Tests embedded in prompt | Delegated to task-work (Phase 4-5.5) |
| **Exit Strategy** | Escape hatch with max iterations | Max turns + blocked report |

### Ralph Wiggum Loop Pattern

```
┌──────────────────────────────────────────────────────────────────────┐
│                    RALPH WIGGUM LOOP PATTERN                          │
│                                                                       │
│   User runs /ralph-loop              Claude works                    │
│        ▼                                  ▼                          │
│   ┌─────────────┐                   ┌─────────────┐                  │
│   │ Initialize  │                   │ Implement   │                  │
│   │ loop state  │──────────────────▶│ + test      │                  │
│   └─────────────┘                   └──────┬──────┘                  │
│                                            │                          │
│                                     Claude tries exit                 │
│                                            │                          │
│   ┌─────────────┐                   ┌──────▼──────┐                  │
│   │ Stop Hook   │◀──────────────────│ stop-hook.sh│                  │
│   │ intercepts  │                   └─────────────┘                  │
│   └──────┬──────┘                                                    │
│          │                                                            │
│   ┌──────▼──────┐     NO        ┌─────────────┐                      │
│   │ Promise     │──────────────▶│ Block exit  │                      │
│   │ fulfilled?  │               │ Inject same │──────┐               │
│   └──────┬──────┘               │ prompt      │      │               │
│          │ YES                  └─────────────┘      │               │
│   ┌──────▼──────┐                     ▲              │               │
│   │ Allow exit  │                     └──────────────┘               │
│   │ Loop done   │               (iteration++)                        │
│   └─────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Differences

**Ralph Wiggum** uses a single agent that iterates on itself:
- Same prompt re-injected each iteration
- File system preserves previous work
- Exit blocked until promise fulfilled

**AutoBuild Player-Coach** uses dual agents:
- Player implements, Coach validates (separation of concerns)
- Coach provides specific feedback for next iteration
- Quality gates provide objective approval criteria

---

## Key Techniques from Anthropic Research

AutoBuild incorporates several techniques identified in the Ralph Wiggum architectural review:

### 1. Promise-Based Completion (IMPLEMENTED)

**Concept**: Explicit, verifiable completion criteria that agents must satisfy.

**Ralph Implementation**: `<promise>COMPLETE</promise>` tag must match exactly.

**AutoBuild Implementation**: Coach validates against acceptance criteria and quality gate results:

```python
class CoachDecision:
    decision: Literal["approve", "feedback", "blocked"]
    criteria_verified: List[CriterionVerification]
    quality_gates_passed: bool
    evidence: str
```

### 2. Escape Hatch Pattern (IMPLEMENTED)

**Concept**: Define explicit fallback behavior when maximum iterations are reached.

**Ralph Implementation**: Prompt includes instructions for documenting blocking issues after N iterations.

**AutoBuild Implementation**:
- Max turns with structured blocked report
- Worktree preserved for debugging
- Clear documentation of what was attempted

```python
# When turn >= max_turns - 2 and completion not possible:
blocked_report = {
    "blocking_issues": ["External mock unavailable"],
    "attempts_made": ["Turn 1: HTTP mock", "Turn 2: httpretty"],
    "suggested_alternatives": ["Manual mock server setup"]
}
```

### 3. Honesty Verification (IMPLEMENTED)

**Concept**: Prevent false success claims through independent verification.

**Ralph Philosophy**: "The design enforces intellectual honesty: users cannot fabricate false promises to escape."

**Block Research Insight**: In ablation studies, when coach feedback was withheld, "the player went 4 rounds of implementations with missing feedback. On each iteration it spontaneously found things to improve, however the final implementation was non-functional." This demonstrates why independent verification is essential.

**AutoBuild Implementation**: Coach independently verifies Player claims:
- Runs tests independently (doesn't trust Player's test results)
- Re-reads original requirements (doesn't rely on Player's interpretation)
- Cross-references claimed files with actual file system
- Validates coverage meets thresholds
- Outputs structured verification checklists marking each requirement

### 4. task-work Delegation (ENHANCED BEYOND RALPH)

**Concept**: Reuse proven implementation infrastructure instead of reimplementing.

**AutoBuild Advantage**: Unlike Ralph's prompt-only approach, AutoBuild delegates to `task-work`:
- Stack-specific subagents (python-api-specialist, react-specialist, etc.)
- Phase 4.5 test enforcement loop (3 auto-fix attempts)
- Architectural review (SOLID/DRY/YAGNI scoring)
- Code review by dedicated code-reviewer agent

This provides **100% code reuse** with the proven task-work quality gate system.

---

## Quality Gate Delegation

AutoBuild's Player doesn't implement directly - it delegates to `task-work --implement-only`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ task-work --implement-only --mode=tdd DELEGATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 3: Implementation ──────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "{selected_implementation_agent}"        │ SUBAGENT│
│       │    - python-api-specialist                                 │ USAGE   │
│       │    - react-specialist                                      │        │
│       │    - dotnet-api-specialist                                 │        │
│       │    - (or task-manager fallback)                            │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 4: Testing ─────────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "{selected_testing_agent}"               │ SUBAGENT│
│       │    - test-orchestrator                                     │ USAGE   │
│       │    - qa-tester                                             │        │
│       │                                                            │        │
│       │  Compilation check (mandatory)                             │        │
│       │  Test execution                                            │        │
│       │  Coverage analysis (80%/75% thresholds)                    │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 4.5: Fix Loop ──────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  WHILE tests fail AND attempt <= 3:                        │ ✅      │
│       │    Fix compilation errors                                  │ AUTO-FIX│
│       │    Fix test failures                                       │        │
│       │    Re-run tests                                            │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 5: Code Review ─────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "code-reviewer"                          │ SUBAGENT│
│       │  Quality assessment                                        │ USAGE   │
│       │  Error handling review                                     │        │
│       │  Documentation check                                       │        │
│       └────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Benefits of Delegation

1. **Stack-Specific Quality**: Python tasks get `python-api-specialist`, React gets `react-specialist`
2. **TDD Enforcement**: Structural enforcement (RED→GREEN→REFACTOR), not just prompt-based
3. **Quality Gates Included**: Phase 4.5 auto-fix, coverage thresholds, code review
4. **Single System to Maintain**: All task-work improvements automatically benefit AutoBuild
5. **Agent Discovery**: Metadata-based matching, template overrides work

---

# Part 3: USING AUTOBUILD

## From Claude Code (Slash Command)

### Basic Usage

```bash
# Single task
/feature-build TASK-AUTH-001

# Entire feature
/feature-build FEAT-A1B2
```

### With Options

```bash
# More iterations
/feature-build TASK-AUTH-001 --max-turns 10

# Verbose output
/feature-build TASK-AUTH-001 --verbose

# Resume interrupted session
/feature-build TASK-AUTH-001 --resume

# Use different model
/feature-build TASK-AUTH-001 --model claude-opus-4-5-20251101
```

### Advantages of Claude Code

| Advantage | Description |
|-----------|-------------|
| **Interactive** | See real-time progress in your IDE |
| **Integrated** | Part of your normal Claude Code workflow |
| **Contextual** | Claude Code has full codebase context |
| **Familiar** | Same slash command interface as other commands |

---

## From Shell (Python CLI)

### Basic Usage

```bash
# Single task
guardkit autobuild task TASK-AUTH-001

# Entire feature
guardkit autobuild feature FEAT-A1B2

# Check status
guardkit autobuild status TASK-AUTH-001
```

### With Debug Logging

```bash
# Debug level shows detailed execution
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-AUTH-001

# Verbose flag shows turn-by-turn progress
guardkit autobuild task TASK-AUTH-001 --verbose

# Both together for maximum visibility
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-AUTH-001 --verbose
```

### Real-World Example

```bash
# Full feature execution with monitoring
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-A96D --max-turns 5

# Output shows:
# - Wave-by-wave execution
# - Task state transitions
# - SDK invocation details
# - Coach validation results
# - Quality gate evaluations
```

### Advantages of Shell CLI

| Advantage | Description |
|-----------|-------------|
| **Scriptable** | Can be integrated into CI/CD pipelines |
| **Background Execution** | Run in terminal while doing other work |
| **Environment Variables** | Fine-grained control via `GUARDKIT_LOG_LEVEL` |
| **Direct SDK Access** | Closer to the metal for debugging |
| **Parallel Execution** | Run multiple features in different terminals |

---

## CLI Reference

### Command: `guardkit autobuild task`

Execute AutoBuild orchestration for a single task.

```bash
guardkit autobuild task TASK-XXX [OPTIONS]
```

**Arguments:**
- `TASK_ID`: Task identifier (e.g., `TASK-AUTH-001`)

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--max-turns N` | 5 | Maximum adversarial turns |
| `--model MODEL` | claude-sonnet-4-5-20250929 | Claude model to use |
| `--verbose` | false | Show detailed turn-by-turn output |
| `--resume` | false | Resume from last saved state |
| `--mode MODE` | tdd | Development mode: standard, tdd, or bdd |
| `--sdk-timeout N` | 900 | SDK timeout in seconds (60-3600) |
| `--no-pre-loop` | false | Skip design phase (Phases 1.6-2.8) |
| `--skip-arch-review` | false | Skip architectural review quality gate |

**Exit Codes:**
- `0`: Success (Coach approved)
- `1`: Task file not found or SDK not available
- `2`: Orchestration error
- `3`: Invalid arguments

**Examples:**

```bash
# Basic execution
guardkit autobuild task TASK-AUTH-001

# Complex task with more iterations
guardkit autobuild task TASK-AUTH-001 --max-turns 10 --verbose

# Use Opus model for higher quality
guardkit autobuild task TASK-AUTH-001 --model claude-opus-4-5-20251101

# Skip design phase for simple bug fixes
guardkit autobuild task TASK-FIX-001 --no-pre-loop

# Extended timeout for large implementations
guardkit autobuild task TASK-REFACTOR-001 --sdk-timeout 1800
```

---

### Command: `guardkit autobuild feature`

Execute AutoBuild for all tasks in a feature with dependency ordering.

```bash
guardkit autobuild feature FEAT-XXX [OPTIONS]
```

**Arguments:**
- `FEATURE_ID`: Feature identifier (e.g., `FEAT-A1B2`)

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--max-turns N` | 5 | Maximum turns per task |
| `--stop-on-failure/--no-stop-on-failure` | true | Stop on first task failure |
| `--resume` | false | Resume from last saved state |
| `--fresh` | false | Start fresh, ignoring saved state |
| `--task TASK-ID` | - | Run specific task within feature |
| `--verbose` | false | Show detailed output |
| `--sdk-timeout N` | 900 | SDK timeout in seconds |
| `--enable-pre-loop/--no-pre-loop` | auto | Enable/disable design phase |

**Exit Codes:**
- `0`: Success (all tasks completed)
- `1`: Feature file not found or SDK not available
- `2`: Orchestration error
- `3`: Validation error

**Examples:**

```bash
# Execute entire feature
guardkit autobuild feature FEAT-A1B2

# Continue even if tasks fail
guardkit autobuild feature FEAT-A1B2 --no-stop-on-failure

# Run specific task within feature context
guardkit autobuild feature FEAT-A1B2 --task TASK-AUTH-002

# Resume after interruption
guardkit autobuild feature FEAT-A1B2 --resume

# Start fresh (discard previous state)
guardkit autobuild feature FEAT-A1B2 --fresh
```

---

### Command: `guardkit autobuild status`

Show AutoBuild status for a task.

```bash
guardkit autobuild status TASK-XXX [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--verbose` | false | Show detailed worktree information |

**Examples:**

```bash
# Basic status
guardkit autobuild status TASK-AUTH-001

# Detailed status
guardkit autobuild status TASK-AUTH-001 --verbose
```

---

### Command: `guardkit autobuild complete`

Complete all tasks in a feature and archive it.

```bash
guardkit autobuild complete FEAT-XXX [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | false | Simulate without making changes |
| `--force` | false | Force completion even if tasks incomplete |

**Examples:**

```bash
# Normal completion
guardkit autobuild complete FEAT-A1B2

# Preview what would happen
guardkit autobuild complete FEAT-A1B2 --dry-run

# Force complete partial feature
guardkit autobuild complete FEAT-A1B2 --force
```

---

## Configuration Options

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GUARDKIT_LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ANTHROPIC_API_KEY` | API key for Claude | (required for SDK) |

### Task Frontmatter Configuration

Configure AutoBuild behavior in task frontmatter:

```yaml
---
id: TASK-AUTH-001
title: "Implement OAuth2 authentication"
status: backlog
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
  sdk_timeout: 900
  skip_arch_review: false
---
```

### Feature YAML Configuration

Configure feature-level behavior:

```yaml
# .guardkit/features/FEAT-A1B2.yaml
id: FEAT-A1B2
name: "User Authentication"
autobuild:
  sdk_timeout: 1200
  enable_pre_loop: false
```

---

# Part 4: ADVANCED TOPICS

## Feature Orchestration

### Wave-Based Execution

Features execute tasks in **waves** based on dependencies:

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE ORCHESTRATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 Load Feature File                                           │
│     .guardkit/features/FEAT-XXX.yaml                            │
│                                                                 │
│  📋 Parse Tasks + Dependencies                                  │
│     ├── TASK-001 (complexity: 3, deps: [])                      │
│     ├── TASK-002 (complexity: 5, deps: [TASK-001])              │
│     ├── TASK-003 (complexity: 5, deps: [TASK-001])              │
│     └── TASK-004 (complexity: 4, deps: [TASK-002, TASK-003])    │
│                                                                 │
│  🔀 Execute by Parallel Groups                                  │
│     Wave 1: [TASK-001]           ──► Player-Coach Loop          │
│     Wave 2: [TASK-002, TASK-003] ──► Player-Coach Loop (×2)     │
│     Wave 3: [TASK-004]           ──► Player-Coach Loop          │
│                                                                 │
│  📊 Track Progress                                              │
│     Update FEAT-XXX.yaml status after each task                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Shared Worktree

Features use a **single shared worktree** for all tasks:
- Location: `.guardkit/worktrees/FEAT-XXX/`
- All task changes accumulate in the same worktree
- Enables tasks to build on each other's work

### Feature File Schema

```yaml
id: FEAT-A1B2
name: "User Authentication"
description: "OAuth2 authentication flow"
created: 2025-12-24T10:00:00
status: planned  # planned → in_progress → completed/failed

tasks:
  - id: TASK-001
    name: "Create auth service interface"
    file_path: "tasks/backlog/oauth/TASK-001.md"
    complexity: 3
    dependencies: []
    status: pending
    implementation_mode: direct
    estimated_minutes: 45

  - id: TASK-002
    name: "Implement Google OAuth"
    file_path: "tasks/backlog/oauth/TASK-002.md"
    complexity: 5
    dependencies: [TASK-001]
    status: pending
    implementation_mode: task-work
    estimated_minutes: 90

orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002, TASK-003]
    - [TASK-004]
  estimated_duration_minutes: 285
  recommended_parallel: 2
```

---

## Pre-Loop Design Phase

### What is Pre-Loop?

Pre-loop runs `task-work --design-only` before the Player-Coach loop to:
- Execute clarification questions (Phase 1.6)
- Generate implementation plan (Phase 2)
- Run architectural review (Phase 2.5B)
- Evaluate complexity (Phase 2.7)
- Get human approval if needed (Phase 2.8)

### When to Use Pre-Loop

```
Starting AutoBuild?
│
├─► Using feature-build (from /feature-plan)?
│   │
│   └─► Tasks already have detailed specs
│       └─► Pre-loop NOT needed (default: disabled)
│
└─► Using task-build (standalone task)?
    │
    ├─► Task has detailed requirements?
    │   └─► Pre-loop runs by default
    │
    └─► Simple bug fix or documentation?
        └─► Consider --no-pre-loop for speed
```

### Pre-Loop Decision Guide

| Scenario | Command | Pre-Loop? | Time Impact |
|----------|---------|-----------|-------------|
| Feature from /feature-plan | `guardkit autobuild feature FEAT-XXX` | No | 15-25 min/task |
| Feature needing design | `guardkit autobuild feature FEAT-XXX --enable-pre-loop` | Yes | +60-90 min/task |
| Standalone task | `guardkit autobuild task TASK-XXX` | Yes | 75-105 min total |
| Simple bug fix | `guardkit autobuild task TASK-XXX --no-pre-loop` | No | 15-25 min |

---

## Resume and State Management

### Automatic State Persistence

AutoBuild saves state after each turn:

```yaml
# In task frontmatter
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: .guardkit/worktrees/TASK-AUTH-001
  started_at: '2025-12-24T10:00:00'
  last_updated: '2025-12-24T10:10:00'
  turns:
    - turn: 1
      decision: feedback
      feedback: "Missing token refresh edge case"
      timestamp: '2025-12-24T10:05:00'
    - turn: 2
      decision: approve
      timestamp: '2025-12-24T10:10:00'
```

### Resume Behavior

**For Tasks:**
```bash
# Resume interrupted task
guardkit autobuild task TASK-AUTH-001 --resume
```

**For Features:**
```bash
# Resume - continues from last task
guardkit autobuild feature FEAT-A1B2 --resume

# Fresh - starts over, ignores saved state
guardkit autobuild feature FEAT-A1B2 --fresh
```

If neither `--resume` nor `--fresh` is specified and incomplete state exists, the CLI prompts:

```
Incomplete state detected for FEAT-A1B2:
  Tasks completed: 2/5
  Last task: TASK-002 (in_progress)

Options:
  [R]esume - Continue from last task
  [F]resh  - Start over from scratch
  [C]ancel - Exit without changes

Your choice [R/F/C]:
```

---

## Troubleshooting

### "Claude Agent SDK not installed"

```bash
# Install AutoBuild dependencies
pip install guardkit-py[autobuild]
# OR
pip install claude-agent-sdk
```

### "Task not found"

```bash
# Verify task file exists
ls tasks/backlog/TASK-XXX*.md
ls tasks/in_progress/TASK-XXX*.md

# Check task ID format
guardkit autobuild task TASK-AUTH-001  # Correct
guardkit autobuild task AUTH-001       # Wrong - missing TASK- prefix
```

### "Max turns reached without approval"

1. Review Coach feedback from last turn
2. Check if requirements are too broad
3. Consider splitting into smaller tasks
4. Use `--max-turns 10` for complex tasks
5. Fall back to `/task-work` for manual implementation

### "Worktree already exists"

```bash
# Clean up existing worktree
guardkit worktree cleanup TASK-XXX

# Or manually
rm -rf .guardkit/worktrees/TASK-XXX
git worktree prune

# Then retry
guardkit autobuild task TASK-XXX
```

### Debug Logging

```bash
# Full debug output
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-XXX --verbose

# Log to file
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-XXX 2>&1 | tee autobuild.log
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| SDK timeout | Task too complex | Increase `--sdk-timeout` |
| Tests always fail | Test setup issues | Check test infrastructure in worktree |
| Coach never approves | Acceptance criteria too strict | Review task requirements |
| Worktree conflicts | Previous run artifacts | Use `--fresh` flag |

---

## Further Reading

### Research Papers

- **[Block AI: Adversarial Cooperation in Code Synthesis](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf)** (December 2025) - The foundational research paper introducing **dialectical autocoding** and the coach-player adversarial pattern. Key concepts:
  - "Discard the player's self-report of success. Have the coach perform independent evaluation."
  - Ablation studies showing single-agent failures without independent verification
  - g3 implementation demonstrating autonomous coding through adversarial cooperation

### Related Projects

- **[Hegelion](https://github.com/Hmbown/Hegelion)** - An open-source implementation of the player-coach dialectical loop based on Block's g3 agent research

### GuardKit Documentation

- [AutoBuild Architecture Deep-Dive](../deep-dives/autobuild-architecture.md) - Technical implementation details
- [CLI vs Claude Code Comparison](cli-vs-claude-code.md) - Choosing your interface

---

## See Also

- [GuardKit Workflow Guide](guardkit-workflow.md) - Complete workflow documentation
- [Task Review Workflow](../workflows/task-review-workflow.md) - Review task patterns
- [Design-First Workflow](../workflows/design-first-workflow.md) - Complex task patterns
- [Quality Gates Workflow](../workflows/quality-gates-workflow.md) - Quality enforcement details

---

**Version**: 1.0.0 | **License**: MIT | **Repository**: https://github.com/guardkit/guardkit
