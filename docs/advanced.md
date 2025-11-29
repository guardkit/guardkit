# Advanced Topics

Advanced workflows and features for complex development scenarios.

## 🎨 [Design-First Workflow](workflows/design-first-workflow.md)

Optional design approval checkpoint for complex tasks requiring upfront planning.

**When to Use:**

- Complexity ≥7
- High-risk changes (security, breaking, schema)
- Multi-person teams (architect designs, dev implements)
- Multi-day tasks

**Workflow Flags:**

- `--design-only`: Phases 2-2.8, stops at checkpoint, saves plan
- `--implement-only`: Phases 3-5, requires `design_approved` state
- (default): All phases 2-5.5 in sequence

**Example:**

```bash
# Design phase only
/task-work TASK-002 --design-only

# [Human reviews and approves plan]

# Implementation phase
/task-work TASK-002 --implement-only
```

Learn when and how to use design-first workflow for critical tasks.

## 🖼️ [UX Design Integration](workflows/ux-design-integration-workflow.md)

Convert design system files (Figma, Zeplin) into components with zero scope creep.

> **Note:** These are early experiments. Generic design URL support is planned (Figma, Zeplin, Sketch) via `design:URL` parameter in `/task-create`, enabling automatic design-to-code conversion for any design tool.

**Current Commands:**

- `/figma-to-react`: Figma → TypeScript React + Tailwind + Playwright
- `/zeplin-to-maui`: Zeplin → XAML + C# + platform tests

**6-Phase Saga:**

1. MCP Verification
2. Design Extraction
3. Boundary Documentation (12-category prohibition checklist)
4. Component Generation
5. Visual Regression Testing (>95% similarity)
6. Constraint Validation (zero tolerance)

**Quality Gates:**

- Visual fidelity: >95%
- Constraint violations: 0
- Compilation: 100%

Prevent scope creep during design-to-code conversion.

## 🔄 [Iterative Refinement](guides/taskwright-workflow.md#iterative-refinement)

Lightweight improvements without full re-work using `/task-refine`.

**Use For:**

- Minor code improvements
- Linting fixes
- Renaming/formatting
- Adding comments

**Don't Use For:**

- New features (use `/task-work`)
- Architecture changes
- Major refactoring

**Example:**

```bash
/task-refine TASK-042
# Makes targeted improvements without full workflow
```

Learn when refinement is faster than re-implementation.

## 📝 [Plan Modification](workflows/design-first-workflow.md#modifying-saved-plans)

Edit implementation plans before execution in design-first workflow.

**Process:**

1. Run `/task-work TASK-XXX --design-only`
2. Plan saved to `.claude/task-plans/TASK-XXX-implementation-plan.md`
3. Edit plan file manually (markdown)
4. Run `/task-work TASK-XXX --implement-only`

**Use Cases:**

- Adjust implementation approach
- Add/remove scope
- Change technical decisions
- Incorporate stakeholder feedback

Plans are human-readable markdown for easy editing.

## 🔍 [Task Review Workflow](workflows/task-review-workflow.md)

Analysis and decision-making workflows separate from implementation.

**Review Modes:**

1. **architectural**: SOLID/DRY/YAGNI compliance review
2. **code-quality**: Maintainability and complexity assessment
3. **decision**: Technical decision analysis with options evaluation
4. **technical-debt**: Debt inventory and prioritization
5. **security**: Security audit and vulnerability assessment

**Depth Levels:**

- **quick** (15-30 min): Initial assessment, sanity checks
- **standard** (1-2 hours): Regular reviews, architecture assessments
- **comprehensive** (4-6 hours): Security audits, critical decisions

**Example:**

```bash
/task-create "Review authentication architecture" task_type:review
/task-review TASK-002 --mode=architectural --depth=standard

# Decision checkpoint: [A]ccept / [R]evise / [I]mplement / [C]ancel
```

Use `/task-review` for analysis, `/task-work` for implementation.

## 🏗️ [Conductor Integration](guides/taskwright-workflow.md#conductor-integration)

Parallel development with Conductor.build and git worktrees.

**Setup:**

```bash
./installer/scripts/install.sh  # Creates symlinks automatically
taskwright doctor              # Verify integration
```

**State Persistence:** ✅

- Symlink architecture + auto-commit
- 100% state preservation across worktrees
- Zero manual intervention required

**Workflow:**

```bash
# Create worktrees for parallel tasks
conductor create-worktree task-001 main
conductor create-worktree task-002 main

# Work in parallel (different terminals)
cd task-001 && /task-work TASK-001
cd task-002 && /task-work TASK-002

# Merge back
git merge task-001
git merge task-002
```

Scale your productivity with parallel development.

---

## Next Steps

- **Try Design-First**: [Design-First Workflow Guide](workflows/design-first-workflow.md)
- **Review Code**: [Task Review Workflow Guide](workflows/task-review-workflow.md)
- **Go Parallel**: Set up [Conductor Integration](https://conductor.build)
