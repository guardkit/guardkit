---
format_version: 1
description: Structured review and analysis workflow for tasks needing assessment or decisions rather than implementation.
---

# Task Review - Structured Analysis and Decision-Making

Execute structured review and analysis workflows for tasks that require assessment, evaluation, or decision-making rather than implementation.

## Command Syntax

```bash
# ID form — review an existing task
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]

# Description form (ad-hoc) — self-creates the review task, then reviews it
/task-review "free-text description of what to review" [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]
```

**Argument detection**: if the first argument matches the task-id pattern
`^TASK(-[A-Z0-9]{2,4})?-[A-Fa-f0-9]{4,6}$` it is treated as a task reference (ID form);
anything else is treated as a description (ad-hoc form, see Phase 0). An argument that
matches the id pattern but has no matching task file on disk is an error, exactly as today —
there is NO silent fallback from a missing ID to description mode.

## Available Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Review mode (architectural, code-quality, decision, technical-debt, security) |
| `--depth=DEPTH` | Review depth (quick, standard, comprehensive) |
| `--output=FORMAT` | Output format (markdown, json, both) |
| `--no-questions` | Skip review scope clarification |
| `--with-questions` | Force clarification even for simple reviews |
| `--defaults` | Use clarification defaults without prompting |
| `--capture-knowledge` | Trigger knowledge capture session after review completion (3-5 context-specific questions) |

## Overview

The `/task-review` command provides a dedicated workflow for analysis and decision-making tasks, separate from the implementation-focused `/task-work` command.

**Use `/task-review` for**:
- Architectural reviews and assessments
- Code quality evaluations
- Technical decision analysis
- Technical debt assessment
- Security audits
- Root cause analysis

**Use `/task-work` for**:
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

## Ad-Hoc Review (Description Form)

Passing a free-text description instead of a task ID removes the two-step friction of
`/task-create "..." task_type:review` → wait → copy the TASK-REV id → `/task-review TASK-REV-XXXX`.
The command self-creates the review task (Phase 0) and proceeds directly into the review.

```bash
/task-review "auth redirect loops after logout" --mode=code-quality
```

Properties of the ad-hoc form:

- **Same durable record**: a real `TASK-REV-{hash}` task file is created in `tasks/backlog/`
  BEFORE analysis starts, so provenance, fleet-memory writes, and downstream joins on
  TASK-REV ids are identical to the two-step flow. Nothing about the report, frontmatter,
  or decision checkpoint changes.
- **Deterministic creation**: Phase 0 shells out to `guardkit task create "{description}"
  --prefix REV --task-type review` (guardkit/cli/task.py) — the same collision-checked
  hash-ID machinery, not ad-hoc file writing.
- **All flags apply unchanged**: `--mode`, `--depth`, `--output`, clarification flags, and
  `--capture-knowledge` behave exactly as in the ID form.
- **The two-step flow remains valid**: `/task-create ... task_type:review` followed by
  `/task-review TASK-REV-XXXX` is unchanged (it is what `/feature-plan` uses internally).

## Workflow Phases

The `/task-review` command executes these phases automatically:

### Phase 0: Ad-Hoc Task Creation (Description Form Only)

Runs ONLY when the first argument is a description (does not match the task-id pattern
`^TASK(-[A-Z0-9]{2,4})?-[A-Fa-f0-9]{4,6}$`). ID-form invocations skip straight to Phase 1.

**GUARD**: if the argument DOES match the id pattern but no task file exists in any
`tasks/{state}/` directory, fail with the standard "Task TASK-XXX not found" error.
Never reinterpret a missing ID as a description.

**EXECUTE** (Bash):
```bash
guardkit task create "{description}" --prefix REV --task-type review
```

**BINARY FALLBACK**: the installed `guardkit` shell wrapper may not dispatch the `task`
subcommand ("Unknown command: task") — the subcommand lives in the Python CLI. If the first
form fails that way, retry with the Python entry point: `guardkit-py task create ...`, or the
repo venv's `.venv/bin/guardkit-py` when working inside the guardkit repo itself.

**PARSE** the created task id and path from the command output
(`Created task: TASK-REV-{hash}-{slug}.md` / `Location: {path}`). The created file carries
`task_type: review` frontmatter and a `## Review Scope` section seeded with the description,
so it satisfies this command's Execution Protocol prerequisites without editing.

**ON FAILURE** (non-zero exit after the binary fallback, or unparseable output): STOP with
the error and suggest the two-step fallback (`/task-create "..." task_type:review` then
`/task-review TASK-REV-XXXX`). Do NOT hand-write a task file.

**DISPLAY**:
```
Phase 0: Ad-hoc review task created
  Task: {task_id} — {description}
  File: tasks/backlog/{filename}
  Proceeding to review (mode: {mode}, depth: {depth})
```

**Continue to Phase 1 with {task_id}** — from this point the ad-hoc form is
indistinguishable from the ID form.


**Phase sequence** (full bodies: `task-review-ext.md` § Workflow Phases — Full Bodies):

- **Phase 1: Load Review Context** — read the task file from `tasks/{state}/`, parse
  metadata (id, title, complexity, mode); unless `--no-questions`, invoke the
  `clarification-questioner` agent with the review_scope context (complexity-gated:
  0-3 skip unless `--with-questions` · 4-6 ask for decision/architectural modes ·
  7+ always); then load review scope, relevant codebase files, and related ADRs.
- **Phase 1.5: Fleet-Memory Review Context** — always after Phase 1 (fast no-op when
  fleet-memory is unavailable; skipped on `--no-context`); tiered MCP→CLI availability
  check; three queries (architecture/project decisions, past failure patterns, similar
  past reviews) populate the knowledge context Phase 2 consumes.
- **Phase 2: Execute Review Analysis** — invoke the mode's primary agent (summary table
  below) with the clarification + knowledge context; produce findings with supporting
  evidence; include a "Context Used" section when memory context informed findings.
- **Phase 3: Synthesize Recommendations** — aggregate findings, generate actionable
  recommendations, identify decision options, prioritize by impact.
- **Phase 4: Generate Review Report** — structured markdown report (executive summary,
  findings with evidence, recommendations with rationale, supporting artifacts) written
  to `.claude/reviews/{task_id}-review-report.md`.
- **Phase 4.5: Knowledge Capture** — only with `--capture-knowledge`: 3-5
  context-specific questions via `run_review_capture`, insights written to fleet-memory.

### Phase 5: Human Decision Checkpoint (with Optional Implementation Preferences)
Present findings to user with decision options:
- **[A]ccept** - Approve findings, mark task as `REVIEW_COMPLETE`
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation task based on recommendation
  - **[NEW]** Presents implementation preferences questions (Context B)
  - Triggered if: user chooses [I]mplement and --no-questions not set
  - Questions help clarify: approach selection, parallelization, testing depth, constraints
- **[C]ancel** - Discard review, return task to backlog

## Review Modes (Summary)

| Mode | Purpose | Primary agent |
|------|---------|---------------|
| `architectural` (default) | System design vs SOLID/DRY/YAGNI | `architectural-reviewer` |
| `code-quality` | Maintainability, complexity, test coverage | `code-reviewer` |
| `decision` | Option evaluation + recommended decision | `software-architect` |
| `technical-debt` | Debt inventory + effort/impact prioritization | `code-reviewer` |
| `security` | Vulnerability assessment (OWASP mapping) | `security-specialist` |

Per-mode agent rosters, output sections, and model/cost selection:
`task-review-ext.md` § Review Modes (Detailed) and § Model Selection Strategy.

## Task States and Transitions

```
BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → Completed/Implemented
              ↓
           BLOCKED
```

**States**:
- `BACKLOG`: Review task not started
- `IN_PROGRESS`: Review in progress
- `REVIEW_COMPLETE`: Review finished, awaiting human decision
- `BLOCKED`: Review cannot proceed (missing context, access issues)

**After Review**:
- Accept findings → Task archived as completed
- Create implementation task → New task in backlog linked to review

## Execution Protocol

### Prerequisites
1. Task must exist in `tasks/` directory (ID form) — the description form satisfies this
   itself via Phase 0's `guardkit task create --task-type review`
2. Task must have `task_type: review` in frontmatter (optional, defaults to review)
3. Review scope must be defined in task description (Phase 0 seeds it from the ad-hoc
   description)

### Validation
- Validates `--mode` against allowed values
- Validates `--depth` against allowed values
- Validates `--output` against allowed values
- Checks task exists and is accessible

### Error Handling

**Common Errors**:

```bash
# Invalid review mode
❌ Error: Invalid review mode 'invalid-mode'
   Allowed: architectural, code-quality, decision, technical-debt, security

# Task not found (an id-shaped argument NEVER falls back to description mode)
❌ Error: Task TASK-XXX not found in any task directory

# Ad-hoc creation failed (description form)
❌ Error: guardkit task create failed — {stderr}
   Fallback: /task-create "..." task_type:review, then /task-review TASK-REV-XXXX

# Missing review scope
❌ Error: Task TASK-XXX missing review scope in description
   Add "Review Scope" section to task description

# Insufficient context
⚠️  Warning: Review scope references non-existent files
   Proceeding with available context
```


## Reference Slices (load on demand)

Extended documentation lives in `task-review-ext.md` (same directory as this file —
K13 core/`-ext` shape). Read the relevant section when needed; do not preload:

| Read when you need | Section in task-review-ext.md |
|---|---|
| Review-task auto-detection criteria + examples | Automatic Review Task Detection |
| Clarification Contexts A/B + complexity gating | Clarification Integration |
| Per-flag behavior detail + flag combinations | Flags |
| Phase 1–4.5 full execution bodies (agent prompts, fleet-memory queries, knowledge capture) | Workflow Phases — Full Bodies |
| Model/cost selection rationale | Model Selection Strategy |
| Per-mode agents + report output sections | Review Modes (Detailed) |
| Review → implementation flow, [I]mplement handler, task state flow | Integration with /task-work |
| Task metadata fields, output files, best practices, implementation notes | Task Metadata … Implementation Notes |
