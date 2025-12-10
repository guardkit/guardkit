---
id: TASK-REV-GA01
title: Review global agent stack filtering during template initialization
status: completed
created: 2025-12-03T12:00:00Z
updated: 2025-12-04T10:15:00Z
completed: 2025-12-04T10:15:00Z
completed_location: tasks/completed/TASK-REV-GA01/
priority: high
tags: [architecture-review, agents, template-init, user-experience]
task_type: review
decision_required: true
complexity: 6
review_results:
  mode: architectural
  depth: standard (revised)
  findings_count: 4
  recommendations_count: 2
  decision: "Approach E (Refined) - Delete/Move/Archive per agent"
  implementation_complexity: "2-3 hours"
  report_path: .claude/reviews/TASK-REV-GA01-review-report.md
  completed_at: 2025-12-04T10:15:00Z
  implementation_task: TASK-IMP-GA02
organized_files:
  - TASK-REV-GA01.md
  - review-report.md
---

# Task: Review Global Agent Stack Filtering During Template Initialization

## Problem Statement

When running `guardkit init <template>` (e.g., using the kartlog template created from https://github.com/ColinEberhardt/kartlog), **all global agents** are copied to the project's `.claude/agents/` folder, including stack-specific agents that are irrelevant to the project's technology stack.

**Example**: A Swift/iOS project (kartlog) receives:
- `react-state-specialist.md` (React/TypeScript only)
- `python-api-specialist.md` (Python only)
- `dotnet-domain-specialist.md` (.NET only)
- `figma-react-orchestrator.md` (React/Figma only)
- `zeplin-maui-orchestrator.md` (.NET MAUI/Zeplin only)

These agents clutter the project and could confuse the agent discovery system.

## Current Agent Inventory

### Stack-Specific Agents (5 agents)
| Agent | Stack | Should Install For |
|-------|-------|-------------------|
| `react-state-specialist.md` | `[react, typescript]` | React/TypeScript projects |
| `python-api-specialist.md` | `[python]` | Python projects |
| `dotnet-domain-specialist.md` | `[dotnet]` | .NET projects |
| `figma-react-orchestrator.md` | `[react, typescript]` | React + Figma integration |
| `zeplin-maui-orchestrator.md` | `[dotnet, maui]` | .NET MAUI + Zeplin integration |

### Cross-Stack Agents (14 agents) - Always Relevant
| Agent | Phase | Purpose |
|-------|-------|---------|
| `task-manager.md` | orchestration | Workflow management |
| `agent-content-enhancer.md` | cross-stack | Template enhancement |
| `test-verifier.md` | testing | Test execution |
| `security-specialist.md` | review | Security validation |
| `test-orchestrator.md` | testing | Test coordination |
| `devops-specialist.md` | implementation | Infrastructure |
| `git-workflow-manager.md` | cross-stack | Git operations |
| `pattern-advisor.md` | cross-stack | Design patterns |
| `architectural-reviewer.md` | review | SOLID/DRY/YAGNI |
| `build-validator.md` | cross-stack | Build verification |
| `code-reviewer.md` | review | Code quality |
| `complexity-evaluator.md` | orchestration | Complexity scoring |
| `database-specialist.md` | implementation | Data architecture |
| `debugging-specialist.md` | debugging | Root cause analysis |

## Scope of Review

### Questions to Answer

1. **Filtering Strategy**: Should template-init filter agents by stack, or always install all global agents?

2. **Stack Detection**: How should the target project's stack be detected?
   - From template metadata?
   - From file extensions in project?
   - From explicit user flag?
   - From template manifest?

3. **Discovery vs Installation**: Should agents remain global (symlinked) and rely on runtime discovery, or be selectively installed per project?

4. **Cross-Stack Handling**: Are all 14 cross-stack agents truly universal, or could some be filtered?

5. **User Control**: Should users have explicit control over which agents are installed?

## Potential Approaches

### Approach A: Stack-Based Filtering (Recommended Investigation)
- Template manifest declares supported stacks
- Only install agents matching those stacks
- Always install cross-stack agents
- **Pros**: Clean, minimal, relevant agents only
- **Cons**: Requires accurate stack detection

### Approach B: Lazy Discovery (No Installation)
- Don't copy agents to project at all
- Agent discovery uses global agents via symlinks
- Filter at runtime based on project context
- **Pros**: Zero duplication, automatic updates
- **Cons**: Requires symlink architecture

### Approach C: Opt-In Installation
- Install only cross-stack agents by default
- Users explicitly request stack-specific agents
- **Pros**: User control, minimal default
- **Cons**: Additional steps for users

### Approach D: Status Quo + Documentation
- Keep installing all agents
- Document that unused agents are ignored
- Agent discovery handles relevance at runtime
- **Pros**: Simple, no changes needed
- **Cons**: Cluttered project, potential confusion

## Acceptance Criteria

- [ ] Analysis of current template-init agent installation logic
- [ ] Assessment of agent discovery system capabilities
- [ ] Recommendation with pros/cons for each approach
- [ ] Impact assessment on existing workflows
- [ ] Decision recommendation with implementation complexity estimate

## Files to Review

- `installer/scripts/install.sh` - Installation logic
- `installer/core/agents/*.md` - All global agents
- Template manifest structure
- Agent discovery implementation

## Review Mode

Recommended: `architectural` with `standard` depth

## Notes

This review was triggered by real-world usage where a Swift/iOS project (kartlog) received React, Python, and .NET specialists that were clearly irrelevant to the technology stack.
