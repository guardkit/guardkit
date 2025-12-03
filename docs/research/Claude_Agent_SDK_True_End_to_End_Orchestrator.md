# Claude Agent SDK: Full Automation Specification (Superseded)

> **Note**: This document describes a single-command full automation approach. 
> The recommended approach is now the **[Two-Command Feature Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md)** 
> which provides better human control points and manual override capability.
>
> This document is retained for reference on the technical implementation details
> of parallel execution, git worktrees, and SDK integration.

## What This Document Describes

This specification covers a **single-command workflow automation** approach:

```bash
taskwright implement "dark mode for settings page"
```

### Important Terminology Clarification

This document originally used the term "orchestrator" but that's misleading. 
What we're building is **workflow automation**, not multi-agent orchestration:

| This Document Says | More Accurate Term |
|-------------------|--------------------|
| "Orchestrator" | Workflow Runner |
| "Orchestration" | Workflow Automation |
| "FeatureOrchestrator" | FeatureWorkflow |

See [TaskWright vs Swarm Systems](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md#taskwright-vs-swarm-systems) 
for a detailed comparison with true multi-agent orchestration systems like Claude-Flow.

---

## Executive Summary

This document specifies a **true end-to-end orchestrator** that automates the complete feature implementation workflow using the Claude Agent SDK. Unlike partial automation approaches, this orchestrator handles everything from initial investigation through to final merge, with only a single human checkpoint before merging to main.

**Key Insight**: The Claude Agent SDK can run multiple parallel `query()` calls with different working directories, effectively replacing Conductor's git worktree management with native Python async orchestration.

**Single Command Goal**:
```bash
taskwright implement "dark mode for settings page"
```

This runs the entire workflow automatically, only pausing for human approval at the final merge.

---

## Current Manual Workflow Analysis

### Rich's Evolved Workflow (Current State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT MANUAL WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. INVESTIGATION PHASE (Manual)                                           │
│   ────────────────────────────────                                          │
│   /task-create "Create a review task to investigate how to implement xxx"   │
│   + explicit analysis requirements                                          │
│   + ultrathink + subagents                                                  │
│   + minimal scope guidance                                                   │
│                                                                              │
│   2. REVIEW & DECOMPOSITION PHASE (Manual)                                  │
│   ─────────────────────────────────────────                                 │
│   /task-review → Claude analyzes investigation results                      │
│   └─► [R]evise if needed, then [I]mplement                                  │
│   └─► Creates decomposed implementation tasks                               │
│                                                                              │
│   3. ORGANIZATION PHASE (Manual)                                            │
│   ─────────────────────────────────                                         │
│   Ask Claude to:                                                            │
│   • Move tasks to tasks/backlog/{feature-name}/                             │
│   • Create implementation-guide.md                                          │
│   • Specify /task-work vs direct implementation                             │
│   • Identify parallel-safe tasks for Conductor                              │
│                                                                              │
│   4. IMPLEMENTATION PHASE (Conductor - Manual)                              │
│   ────────────────────────────────────────────                              │
│   • Read implementation guide                                               │
│   • Use Conductor workspaces (git worktrees)                                │
│   • /task-complete on each task                                             │
│   • Commit and merge to main                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pain Points with Current Workflow

1. **Multiple manual steps** - Each phase requires human intervention
2. **Context switching** - Moving between Claude Code, Conductor, git
3. **Repetitive prompts** - Same investigation prompt structure every time
4. **Manual checkpoint decisions** - Almost always approve anyway
5. **Conductor coordination** - Managing worktrees, merging back

---

## Why Claude Agent SDK Enables True Automation

### Key SDK Capabilities

The Claude Agent SDK provides:

1. **Async `query()` function** - Can run multiple sessions in parallel
2. **Configurable `cwd`** - Each query can operate in a different directory
3. **Full tool access** - Read, Write, Edit, Bash, Agent, etc.
4. **Streaming responses** - Monitor progress in real-time
5. **Permission modes** - Auto-accept edits for unattended operation

### Critical Discovery: Parallel Execution

```python
from claude_agent_sdk import query, ClaudeAgentOptions
import asyncio

async def parallel_tasks():
    """The SDK can run multiple Claude sessions in parallel."""
    
    options_ws1 = ClaudeAgentOptions(cwd="/project/worktree-1")
    options_ws2 = ClaudeAgentOptions(cwd="/project/worktree-2")
    options_ws3 = ClaudeAgentOptions(cwd="/project/worktree-3")
    
    # Run three tasks simultaneously in different worktrees
    await asyncio.gather(
        query(prompt="/task-work TASK-001", options=options_ws1),
        query(prompt="/task-work TASK-002", options=options_ws2),
        query(prompt="/task-work TASK-003", options=options_ws3),
    )
```

**This means the Claude Agent SDK can replace Conductor** for parallel task execution using git worktrees.

---

## True End-to-End Orchestrator Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRUE ORCHESTRATOR: taskwright implement                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CLI: taskwright implement "dark mode for settings page"                   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PHASE 1: Investigation (Automated)                                   │   │
│   │ • Create and execute investigation task                              │   │
│   │ • AI Reviewer subagent approves or flags for human                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PHASE 2: Decomposition (Automated)                                   │   │
│   │ • Break into atomic tasks                                            │   │
│   │ • Identify parallel groups (no file conflicts)                       │   │
│   │ • AI Reviewer validates decomposition                                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PHASE 3: Parallel Implementation (Automated)                         │   │
│   │                                                                      │   │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│   │   │ Worktree 1   │  │ Worktree 2   │  │ Worktree 3   │              │   │
│   │   │ TASK-001     │  │ TASK-002     │  │ TASK-003     │              │   │
│   │   │ query()      │  │ query()      │  │ query()      │              │   │
│   │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   │
│   │          │                 │                 │                       │   │
│   │          └────────────┬────┴────────────────┘                       │   │
│   │                       ▼                                              │   │
│   │              Wait for all to complete                                │   │
│   │              Merge worktrees to feature branch                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PHASE 4: Sequential Dependencies (Automated)                         │   │
│   │ • Run tasks that depend on Phase 3 outputs                           │   │
│   │ • One at a time, in dependency order                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PHASE 5: Integration & Merge (Automated)                             │   │
│   │ • Merge worktrees back to feature branch                             │   │
│   │ • Run integration tests                                              │   │
│   │ • AI Reviewer checks for conflicts/issues                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 🛑 SINGLE CHECKPOINT: Final Merge to Main                            │   │
│   │ • Human reviews complete feature                                     │   │
│   │ • [M]erge to main / [R]eject / [I]nspect                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## AI Reviewer Subagent

Since human checkpoints almost always result in approval, we use an AI Reviewer subagent that:

1. **Auto-approves** reasonable outputs
2. **Requests revision** for minor issues
3. **Escalates to human** only for critical problems

### AI Reviewer Implementation

```python
class AIReviewer:
    """
    Subagent that reviews checkpoints and auto-approves or escalates.
    
    Philosophy: Be lenient - only reject or escalate if there's a real problem.
    This matches the observed behavior where humans almost always approve.
    """
    
    REVIEW_PROMPT = """You are a senior engineering reviewer. Analyze this output and decide:

## Review Criteria
1. **Completeness**: Does it address all requirements?
2. **Quality**: Is the analysis/code reasonable?
3. **Scope**: Is it appropriately scoped (not too broad)?
4. **Red Flags**: Any obvious problems, security issues, or regressions?

## Decision Rules
- APPROVED: Output is acceptable, no significant issues
- NEEDS_REVISION: Minor issues that can be fixed with specific feedback
- ESCALATE: Critical issues requiring human judgment

## Output Format
Respond with exactly one of:
- APPROVED
- NEEDS_REVISION: <specific feedback for revision>
- ESCALATE: <reason human review is needed>

Be lenient - only reject or escalate if there's a real problem.
Most outputs should be APPROVED if they reasonably address the task.
"""

    async def review(self, content: str, context: str) -> tuple[str, str]:
        """
        Review content and return (decision, reason).
        
        Args:
            content: The output to review
            context: Description of what this output represents
            
        Returns:
            Tuple of (decision, reason) where decision is one of:
            - "approved": Continue workflow
            - "revise": Re-run with feedback
            - "escalate": Pause for human review
        """
        
        options = ClaudeAgentOptions(
            max_turns=1,
            system_prompt=self.REVIEW_PROMPT
        )
        
        response = ""
        async for message in query(
            prompt=f"Context: {context}\n\nContent to review:\n{content}",
            options=options
        ):
            response += self._extract_text(message)
        
        if "APPROVED" in response:
            return ("approved", "AI reviewer approved")
        elif "NEEDS_REVISION" in response:
            feedback = response.split("NEEDS_REVISION:")[-1].strip()
            return ("revise", feedback)
        else:  # ESCALATE
            reason = response.split("ESCALATE:")[-1].strip()
            return ("escalate", reason)
    
    def _extract_text(self, message) -> str:
        if hasattr(message, 'content'):
            return "".join(
                block.text for block in message.content 
                if hasattr(block, 'text')
            )
        return ""
```

### Review Points in Workflow

| Checkpoint | What's Reviewed | Typical Outcome |
|------------|-----------------|-----------------|
| Investigation complete | Analysis quality, scope | APPROVED (95%) |
| Decomposition complete | Task structure, dependencies | APPROVED (90%) |
| Integration tests | Test results, conflicts | APPROVED (85%) |
| Pre-merge | Overall feature quality | ESCALATE to human |

---

## Core Data Structures

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    """Represents an atomic implementation task."""
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    parallel_group: Optional[int] = None  # None = must be sequential
    files: list[str] = field(default_factory=list)  # Files this task modifies
    complexity: int = 5  # 1-10 scale
    worktree: Optional[str] = None  # Path when running in worktree
    status: TaskStatus = TaskStatus.PENDING

@dataclass 
class FeatureWorkflow:
    """Tracks state of an entire feature implementation."""
    feature_description: str
    feature_slug: str
    feature_branch: str
    investigation_task_id: Optional[str] = None
    investigation_result: Optional[str] = None
    tasks: list[Task] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
```

---

## Full Orchestrator Implementation

```python
import asyncio
import subprocess
import re
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from claude_agent_sdk import query, ClaudeAgentOptions


class FeatureOrchestrator:
    """
    True end-to-end orchestrator for feature implementation.
    
    Automates the complete workflow from feature description to merged code,
    with only a single human checkpoint before final merge to main.
    
    Usage:
        orchestrator = FeatureOrchestrator("/path/to/project")
        await orchestrator.implement("dark mode for settings page")
    """
    
    def __init__(self, project_path: str, max_parallel: int = 3):
        """
        Initialize the orchestrator.
        
        Args:
            project_path: Path to the project root
            max_parallel: Maximum number of parallel tasks (worktrees)
        """
        self.project_path = Path(project_path)
        self.max_parallel = max_parallel
        self.reviewer = AIReviewer()
        self.worktrees_dir = self.project_path / ".worktrees"
        
    async def implement(self, feature_description: str) -> bool:
        """
        Implement a feature end-to-end.
        
        This is the main entry point. It runs the complete workflow:
        1. Investigation
        2. Decomposition
        3. Parallel implementation
        4. Sequential dependencies
        5. Integration testing
        6. Final human approval
        7. Merge to main
        
        Args:
            feature_description: Natural language description of the feature
            
        Returns:
            True if feature was successfully implemented and merged
        """
        
        # Initialize workflow
        workflow = FeatureWorkflow(
            feature_description=feature_description,
            feature_slug=self._slugify(feature_description),
            feature_branch=f"feature/{self._slugify(feature_description)}",
            started_at=datetime.now().isoformat()
        )
        
        print(f"🚀 Starting feature implementation: {feature_description}")
        print(f"   Branch: {workflow.feature_branch}")
        print(f"   Started: {workflow.started_at}")
        
        # Create feature branch from main
        self._git_checkout("main")
        self._git_pull()
        self._create_feature_branch(workflow.feature_branch)
        
        try:
            # ─────────────────────────────────────────────────────────────
            # Phase 1: Investigation
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("📋 PHASE 1: Investigation")
            print("═"*60)
            
            workflow.investigation_result = await self._run_investigation(workflow)
            
            decision, reason = await self.reviewer.review(
                workflow.investigation_result, 
                "Feature investigation analysis"
            )
            
            if decision == "escalate":
                print(f"⚠️  AI Reviewer escalated: {reason}")
                if not self._human_approve("Investigation", workflow.investigation_result):
                    return self._abort_workflow(workflow, "Investigation rejected")
            elif decision == "revise":
                print(f"🔄 AI Reviewer requested revision: {reason}")
                workflow.investigation_result = await self._revise_investigation(
                    workflow, reason
                )
            else:
                print("✅ AI Reviewer approved investigation")
            
            # ─────────────────────────────────────────────────────────────
            # Phase 2: Decomposition
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("🔨 PHASE 2: Task Decomposition")
            print("═"*60)
            
            workflow.tasks = await self._decompose_tasks(workflow)
            
            print(f"   Created {len(workflow.tasks)} tasks")
            parallel_count = len([t for t in workflow.tasks if t.parallel_group is not None])
            sequential_count = len(workflow.tasks) - parallel_count
            print(f"   Parallel: {parallel_count}, Sequential: {sequential_count}")
            
            decision, reason = await self.reviewer.review(
                self._format_tasks(workflow.tasks),
                "Task decomposition for feature implementation"
            )
            
            if decision == "escalate":
                print(f"⚠️  AI Reviewer escalated: {reason}")
                if not self._human_approve("Decomposition", self._format_tasks(workflow.tasks)):
                    return self._abort_workflow(workflow, "Decomposition rejected")
            elif decision == "revise":
                print(f"🔄 Revising decomposition: {reason}")
                workflow.tasks = await self._revise_decomposition(workflow, reason)
            else:
                print("✅ AI Reviewer approved decomposition")
            
            # ─────────────────────────────────────────────────────────────
            # Phase 3: Parallel Implementation
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("⚡ PHASE 3: Parallel Implementation")
            print("═"*60)
            
            await self._run_parallel_implementation(workflow)
            
            # ─────────────────────────────────────────────────────────────
            # Phase 4: Sequential Dependencies
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("📦 PHASE 4: Sequential Tasks")
            print("═"*60)
            
            await self._run_sequential_tasks(workflow)
            
            # ─────────────────────────────────────────────────────────────
            # Phase 5: Integration
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("🔗 PHASE 5: Integration & Testing")
            print("═"*60)
            
            integration_passed = await self._integrate_and_test(workflow)
            
            if not integration_passed:
                print("❌ Integration tests failed")
                decision, reason = await self.reviewer.review(
                    "Integration tests failed",
                    "Decide whether to abort or attempt fixes"
                )
                if decision == "escalate":
                    if not self._human_approve("Integration Failed", "Attempt to fix?"):
                        return self._abort_workflow(workflow, "Integration failed")
                    # Human approved - attempt fixes
                    await self._attempt_integration_fixes(workflow)
            
            # ─────────────────────────────────────────────────────────────
            # Final Checkpoint: Human Approval for Merge
            # ─────────────────────────────────────────────────────────────
            print("\n" + "═"*60)
            print("🛑 FINAL CHECKPOINT: Merge to Main")
            print("═"*60)
            
            self._show_feature_summary(workflow)
            
            approval = input("\n[M]erge to main / [R]eject / [I]nspect: ").strip().lower()
            
            if approval == 'm':
                self._merge_to_main(workflow.feature_branch)
                workflow.status = "completed"
                workflow.completed_at = datetime.now().isoformat()
                print(f"\n✅ Feature '{feature_description}' merged to main!")
                return True
                
            elif approval == 'i':
                print(f"\nInspect the changes:")
                print(f"  cd {self.project_path}")
                print(f"  git diff main..{workflow.feature_branch}")
                input("\nPress Enter when ready to decide...")
                
                final = input("[M]erge / [R]eject: ").strip().lower()
                if final == 'm':
                    self._merge_to_main(workflow.feature_branch)
                    workflow.status = "completed"
                    workflow.completed_at = datetime.now().isoformat()
                    print(f"\n✅ Feature merged to main!")
                    return True
                    
            print("❌ Feature rejected")
            return self._abort_workflow(workflow, "Rejected at final review")
                
        except Exception as e:
            print(f"❌ Error during implementation: {e}")
            self._cleanup_worktrees(workflow)
            workflow.status = "failed"
            raise
            
        finally:
            self._cleanup_worktrees(workflow)
    
    # ═══════════════════════════════════════════════════════════════════════
    # Phase 1: Investigation
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _run_investigation(self, workflow: FeatureWorkflow) -> str:
        """Create and execute investigation task."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent"],
            permission_mode="acceptEdits",
            max_turns=50
        )
        
        # This prompt mirrors Rich's evolved workflow
        prompt = f"""Create and execute an investigation task for: {workflow.feature_description}

## Investigation Requirements

Please be very explicit about:
1. **Analysis findings** - What did you discover about the codebase?
2. **Recommended approach** - How should this be implemented?
3. **Code snippets** - Show specific code changes needed
4. **Scope constraints** - Keep changes minimal to avoid regressions

## Execution Instructions

1. Use ultrathink for deep analysis
2. Invoke appropriate subagents (architect, code-reviewer, etc.)
3. Create a comprehensive specification of the work required

## Required Output

When investigation is complete, provide:
- Summary of findings
- Recommended implementation approach  
- List of files that will need changes
- Estimated complexity (1-10)
- Whether tasks can be parallelized (which files conflict?)

Format the file list as:
```
FILES_TO_MODIFY:
- path/to/file1.py
- path/to/file2.tsx
```
"""

        result_text = []
        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                result_text.append(text)
                print(".", end="", flush=True)
        
        print()  # Newline after progress dots
        return "\n".join(result_text)
    
    async def _revise_investigation(self, workflow: FeatureWorkflow, feedback: str) -> str:
        """Revise investigation based on AI reviewer feedback."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30
        )
        
        prompt = f"""Revise the investigation for: {workflow.feature_description}

## Previous Investigation
{workflow.investigation_result[:3000]}...

## Feedback from Reviewer
{feedback}

Please address this feedback and provide an updated analysis."""

        result_text = []
        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                result_text.append(text)
        
        return "\n".join(result_text)
    
    # ═══════════════════════════════════════════════════════════════════════
    # Phase 2: Decomposition
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _decompose_tasks(self, workflow: FeatureWorkflow) -> list[Task]:
        """Decompose investigation into implementation tasks."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30
        )
        
        prompt = f"""Based on this investigation, decompose into implementation tasks:

## Investigation Results
{workflow.investigation_result}

## Decomposition Requirements

For each task:
1. Make it atomic and independently testable
2. Define clear acceptance criteria
3. List specific files that will be modified
4. Estimate complexity (1-10)

## CRITICAL: Parallel Execution Analysis

Identify which tasks can run IN PARALLEL (no file conflicts).
Tasks modifying the same files MUST be in different parallel groups or sequential.

## Output Format

Use exactly this YAML structure:
```yaml
tasks:
  - id: TASK-001
    description: "Brief description of what this task does"
    files: 
      - src/components/Button.tsx
      - src/styles/button.css
    dependencies: []
    parallel_group: 1  # Same number = can run together
    complexity: 3
    
  - id: TASK-002
    description: "Another task"
    files:
      - src/pages/Settings.tsx
    dependencies: []
    parallel_group: 1  # Can run with TASK-001 (different files)
    complexity: 4
    
  - id: TASK-003
    description: "Task that depends on others"
    files:
      - src/components/Button.tsx  # Same as TASK-001
    dependencies: [TASK-001]
    parallel_group: null  # Must be sequential
    complexity: 2
```

Rules:
- parallel_group: number means it can run in parallel with same-numbered tasks
- parallel_group: null means it must run sequentially
- Tasks with file conflicts CANNOT have the same parallel_group
- dependencies: list task IDs that must complete first
"""

        result_text = []
        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                result_text.append(text)
        
        return self._parse_tasks("\n".join(result_text))
    
    async def _revise_decomposition(self, workflow: FeatureWorkflow, feedback: str) -> list[Task]:
        """Revise task decomposition based on feedback."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Grep"],
            permission_mode="acceptEdits",
            max_turns=20
        )
        
        prompt = f"""Revise the task decomposition.

## Current Tasks
{self._format_tasks(workflow.tasks)}

## Feedback
{feedback}

Please provide revised YAML task list addressing this feedback."""

        result_text = []
        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                result_text.append(text)
        
        return self._parse_tasks("\n".join(result_text))
    
    # ═══════════════════════════════════════════════════════════════════════
    # Phase 3: Parallel Implementation
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _run_parallel_implementation(self, workflow: FeatureWorkflow):
        """Run parallel tasks using git worktrees."""
        
        # Group tasks by parallel_group
        parallel_groups: dict[int, list[Task]] = {}
        for task in workflow.tasks:
            if task.parallel_group is not None:
                if task.parallel_group not in parallel_groups:
                    parallel_groups[task.parallel_group] = []
                parallel_groups[task.parallel_group].append(task)
        
        if not parallel_groups:
            print("   No parallel tasks identified")
            return
        
        # Process each parallel group in order
        for group_num in sorted(parallel_groups.keys()):
            group_tasks = parallel_groups[group_num]
            
            # Limit concurrent tasks
            for batch_start in range(0, len(group_tasks), self.max_parallel):
                batch = group_tasks[batch_start:batch_start + self.max_parallel]
                
                print(f"\n   Running parallel group {group_num}, batch: {[t.id for t in batch]}")
                
                # Create worktrees for this batch
                for task in batch:
                    worktree_path = self._create_worktree(
                        workflow.feature_branch,
                        f"{workflow.feature_slug}-{task.id}"
                    )
                    task.worktree = worktree_path
                
                # Run all tasks in batch simultaneously
                results = await asyncio.gather(*[
                    self._run_single_task(task) for task in batch
                ], return_exceptions=True)
                
                # Check for failures
                for task, result in zip(batch, results):
                    if isinstance(result, Exception):
                        print(f"   ❌ {task.id} failed: {result}")
                        task.status = TaskStatus.FAILED
                    else:
                        # Merge worktree back to feature branch
                        self._merge_worktree(task.worktree, workflow.feature_branch)
                        task.status = TaskStatus.COMPLETED
                        print(f"   ✅ {task.id} completed and merged")
    
    async def _run_single_task(self, task: Task):
        """Run a single task in its worktree."""
        
        task.status = TaskStatus.IN_PROGRESS
        
        options = ClaudeAgentOptions(
            cwd=task.worktree,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent"],
            permission_mode="acceptEdits",
            max_turns=50
        )
        
        prompt = f"""Implement this task completely:

## Task: {task.id}
{task.description}

## Files to Modify
{chr(10).join(f'- {f}' for f in task.files)}

## Instructions
1. Implement the changes described
2. Write or update tests as needed
3. Run tests to verify (use appropriate test command)
4. Commit changes with descriptive message: "feat({task.id}): {task.description[:50]}"

## Important
- Stay focused on this specific task only
- Don't modify files outside the listed scope unless necessary
- Ensure tests pass before completing
"""

        async for message in query(prompt=prompt, options=options):
            # Consume the stream, letting Claude do the work
            text = self._extract_text(message)
            if text and "error" in text.lower():
                print(f"   ⚠️  {task.id}: {text[:100]}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Phase 4: Sequential Tasks
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _run_sequential_tasks(self, workflow: FeatureWorkflow):
        """Run sequential tasks (those with dependencies or no parallel group)."""
        
        sequential_tasks = [
            t for t in workflow.tasks 
            if t.parallel_group is None and t.status == TaskStatus.PENDING
        ]
        
        if not sequential_tasks:
            print("   No sequential tasks remaining")
            return
        
        # Sort by dependencies (topological sort)
        sorted_tasks = self._topological_sort(sequential_tasks, workflow)
        
        for task in sorted_tasks:
            # Check dependencies are complete
            for dep_id in task.dependencies:
                dep_task = next((t for t in workflow.tasks if t.id == dep_id), None)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    print(f"   ⏳ {task.id} waiting for {dep_id}")
                    # In a real implementation, we'd wait or handle this better
            
            print(f"\n   Running sequential task: {task.id}")
            task.status = TaskStatus.IN_PROGRESS
            
            options = ClaudeAgentOptions(
                cwd=str(self.project_path),
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent"],
                permission_mode="acceptEdits",
                max_turns=50
            )
            
            prompt = f"""Implement this task:

## Task: {task.id}
{task.description}

## Files to Modify
{chr(10).join(f'- {f}' for f in task.files)}

## Dependencies Completed
{', '.join(task.dependencies) if task.dependencies else 'None'}

## Instructions
1. Implement the changes
2. Run tests to verify
3. Commit with message: "feat({task.id}): {task.description[:50]}"
"""

            async for message in query(prompt=prompt, options=options):
                pass
            
            task.status = TaskStatus.COMPLETED
            print(f"   ✅ {task.id} completed")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Phase 5: Integration
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _integrate_and_test(self, workflow: FeatureWorkflow) -> bool:
        """Run integration tests and final checks."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Bash", "Grep"],
            permission_mode="acceptEdits",
            max_turns=20
        )
        
        prompt = """Run integration tests and verify the feature implementation:

## Checks to Perform
1. Run the full test suite (detect test framework automatically)
2. Check for TypeScript/linting errors if applicable
3. Verify no obvious regressions
4. Check that all new code has test coverage

## Output Format
Respond with exactly one of:
- INTEGRATION_PASSED: All tests pass, no issues found
- INTEGRATION_FAILED: <specific issues found>
"""

        result = ""
        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                result += text
                print(f"   {text[:100]}")
        
        if "INTEGRATION_PASSED" in result:
            print("   ✅ Integration tests passed")
            return True
        else:
            print(f"   ❌ Integration issues: {result}")
            return False
    
    async def _attempt_integration_fixes(self, workflow: FeatureWorkflow):
        """Attempt to fix integration test failures."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30
        )
        
        prompt = """Integration tests are failing. Please:

1. Identify the specific failures
2. Fix the issues
3. Re-run tests to verify
4. Commit fixes with message: "fix: resolve integration test failures"
"""

        async for message in query(prompt=prompt, options=options):
            text = self._extract_text(message)
            if text:
                print(f"   {text[:100]}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Git Operations
    # ═══════════════════════════════════════════════════════════════════════
    
    def _git_checkout(self, branch: str):
        """Checkout a branch."""
        subprocess.run(
            ["git", "checkout", branch],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
    
    def _git_pull(self):
        """Pull latest changes."""
        subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=self.project_path,
            check=False,  # May fail if no remote
            capture_output=True
        )
    
    def _create_feature_branch(self, branch_name: str):
        """Create and checkout feature branch."""
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
        print(f"   Created branch: {branch_name}")
    
    def _create_worktree(self, base_branch: str, name: str) -> str:
        """Create a git worktree for parallel work."""
        worktree_path = self.worktrees_dir / name
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove existing worktree if present
        if worktree_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.project_path,
                check=False,
                capture_output=True
            )
        
        # Create new worktree with a branch
        worktree_branch = f"wt-{name}"
        subprocess.run(
            ["git", "worktree", "add", "-b", worktree_branch, str(worktree_path), base_branch],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
        
        return str(worktree_path)
    
    def _merge_worktree(self, worktree_path: str, target_branch: str):
        """Merge worktree changes back to target branch."""
        worktree_name = Path(worktree_path).name
        worktree_branch = f"wt-{worktree_name}"
        
        # Commit any uncommitted changes in worktree
        subprocess.run(["git", "add", "-A"], cwd=worktree_path, check=False, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Complete task in {worktree_name}", "--allow-empty"],
            cwd=worktree_path,
            check=False,
            capture_output=True
        )
        
        # Switch to target branch and merge
        subprocess.run(
            ["git", "checkout", target_branch],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "merge", worktree_branch, "--no-edit"],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
    
    def _merge_to_main(self, feature_branch: str):
        """Merge feature branch to main."""
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "merge", feature_branch, "--no-edit"],
            cwd=self.project_path,
            check=True,
            capture_output=True
        )
        print(f"   Merged {feature_branch} to main")
    
    def _cleanup_worktrees(self, workflow: FeatureWorkflow):
        """Remove all worktrees created for this workflow."""
        if not self.worktrees_dir.exists():
            return
            
        for worktree in self.worktrees_dir.iterdir():
            if worktree.is_dir() and workflow.feature_slug in worktree.name:
                subprocess.run(
                    ["git", "worktree", "remove", str(worktree), "--force"],
                    cwd=self.project_path,
                    check=False,
                    capture_output=True
                )
                # Also remove the worktree branch
                branch_name = f"wt-{worktree.name}"
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=self.project_path,
                    check=False,
                    capture_output=True
                )
    
    # ═══════════════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════════════
    
    def _abort_workflow(self, workflow: FeatureWorkflow, reason: str) -> bool:
        """Abort the workflow and cleanup."""
        print(f"\n❌ Workflow aborted: {reason}")
        workflow.status = "failed"
        self._cleanup_worktrees(workflow)
        # Optionally delete feature branch
        return False
    
    def _human_approve(self, phase: str, content: str) -> bool:
        """Fallback to human approval when AI escalates."""
        print(f"\n{'─'*60}")
        print(f"Human Review Required: {phase}")
        print("─"*60)
        
        # Show truncated content
        if len(content) > 2000:
            print(content[:1000])
            print(f"\n... ({len(content) - 2000} characters omitted) ...\n")
            print(content[-1000:])
        else:
            print(content)
        
        approval = input("\n[A]pprove / [R]eject: ").strip().lower()
        return approval == 'a'
    
    def _show_feature_summary(self, workflow: FeatureWorkflow):
        """Show summary of completed feature."""
        completed = len([t for t in workflow.tasks if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in workflow.tasks if t.status == TaskStatus.FAILED])
        
        print(f"\n{'─'*60}")
        print(f"Feature: {workflow.feature_description}")
        print(f"Branch:  {workflow.feature_branch}")
        print(f"Tasks:   {completed} completed, {failed} failed")
        print(f"{'─'*60}")
        
        print("\nCompleted tasks:")
        for task in workflow.tasks:
            status_icon = "✅" if task.status == TaskStatus.COMPLETED else "❌"
            print(f"  {status_icon} {task.id}: {task.description[:50]}")
        
        print(f"\nTo inspect changes:")
        print(f"  git diff main..{workflow.feature_branch}")
        print(f"  git log main..{workflow.feature_branch} --oneline")
    
    def _extract_text(self, message) -> str:
        """Extract text content from SDK message."""
        if hasattr(message, 'content'):
            return "".join(
                block.text for block in message.content 
                if hasattr(block, 'text')
            )
        return ""
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL/branch-safe slug."""
        slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
        return slug.strip('-')[:40]
    
    def _parse_tasks(self, output: str) -> list[Task]:
        """Parse YAML task output into Task objects."""
        # Extract YAML block from output
        match = re.search(r'```yaml\n(.*?)```', output, re.DOTALL)
        if not match:
            # Try without code fence
            match = re.search(r'tasks:\n(.*?)(?:\n\n|$)', output, re.DOTALL)
            if match:
                yaml_content = "tasks:\n" + match.group(1)
            else:
                print("   ⚠️ Could not parse task YAML")
                return []
        else:
            yaml_content = match.group(1)
        
        try:
            data = yaml.safe_load(yaml_content)
            tasks = []
            
            for t in data.get('tasks', []):
                tasks.append(Task(
                    id=t.get('id', f"TASK-{len(tasks)+1:03d}"),
                    description=t.get('description', ''),
                    files=t.get('files', []),
                    dependencies=t.get('dependencies', []),
                    parallel_group=t.get('parallel_group'),
                    complexity=t.get('complexity', 5)
                ))
            
            return tasks
            
        except yaml.YAMLError as e:
            print(f"   ⚠️ YAML parse error: {e}")
            return []
    
    def _format_tasks(self, tasks: list[Task]) -> str:
        """Format tasks for display/review."""
        lines = [f"Tasks ({len(tasks)} total):"]
        
        # Group by parallel group
        parallel = [t for t in tasks if t.parallel_group is not None]
        sequential = [t for t in tasks if t.parallel_group is None]
        
        if parallel:
            lines.append("\nParallel tasks:")
            for t in sorted(parallel, key=lambda x: (x.parallel_group, x.id)):
                lines.append(f"  [{t.parallel_group}] {t.id}: {t.description}")
                lines.append(f"      Files: {', '.join(t.files[:3])}")
        
        if sequential:
            lines.append("\nSequential tasks:")
            for t in sequential:
                deps = f" (after: {', '.join(t.dependencies)})" if t.dependencies else ""
                lines.append(f"  {t.id}: {t.description}{deps}")
                lines.append(f"      Files: {', '.join(t.files[:3])}")
        
        return "\n".join(lines)
    
    def _topological_sort(self, tasks: list[Task], workflow: FeatureWorkflow) -> list[Task]:
        """Sort tasks by dependencies using topological sort."""
        completed_ids = {t.id for t in workflow.tasks if t.status == TaskStatus.COMPLETED}
        sorted_tasks = []
        remaining = tasks.copy()
        
        while remaining:
            # Find tasks with all dependencies satisfied
            ready = [
                t for t in remaining
                if all(dep in completed_ids or dep in [s.id for s in sorted_tasks] 
                       for dep in t.dependencies)
            ]
            
            if not ready:
                # No tasks ready - circular dependency or missing dependency
                print(f"   ⚠️ Could not resolve dependencies, adding remaining tasks")
                sorted_tasks.extend(remaining)
                break
            
            # Add first ready task
            task = ready[0]
            sorted_tasks.append(task)
            remaining.remove(task)
        
        return sorted_tasks


# ═══════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════

import click
import anyio

@click.command()
@click.argument('description')
@click.option('--project', '-p', default='.', help='Project path')
@click.option('--max-parallel', '-j', default=3, help='Max parallel tasks')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def implement(description: str, project: str, max_parallel: int, dry_run: bool):
    """
    Implement a feature end-to-end.
    
    Example:
        taskwright implement "dark mode for settings page"
        taskwright implement "add user authentication" -j 4
    """
    if dry_run:
        click.echo(f"Would implement: {description}")
        click.echo(f"Project: {project}")
        click.echo(f"Max parallel: {max_parallel}")
        return
    
    orchestrator = FeatureOrchestrator(project, max_parallel)
    success = anyio.run(orchestrator.implement, description)
    
    if success:
        click.echo("\n🎉 Feature successfully implemented and merged!")
    else:
        click.echo("\n❌ Feature implementation was not completed")
        raise SystemExit(1)


if __name__ == '__main__':
    implement()
```

---

## What Gets Automated

| Step | Before (Manual) | After (Orchestrator) |
|------|-----------------|----------------------|
| Create investigation task | Type `/task-create` + prompt | Automated |
| Run investigation | Wait, read output | Automated |
| Review investigation | Read, decide [A/R] | AI Reviewer auto-approves |
| Decompose into tasks | Ask Claude, review | Automated + AI review |
| Identify parallel groups | Manual analysis | Automated via file analysis |
| Create worktrees | Conductor UI / manual | Automated git worktree |
| Run parallel tasks | Conductor sessions | `asyncio.gather()` with SDK |
| Run sequential tasks | One at a time manually | Automated with dependency ordering |
| Merge worktrees | Manual git commands | Automated merge |
| Run integration tests | Manual | Automated |
| Final merge to main | Manual | **Single human checkpoint** |

---

## The Single Remaining Checkpoint

```
═══════════════════════════════════════════════════════════════
🛑 FINAL CHECKPOINT: Merge to Main
═══════════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────────
Feature: dark mode for settings page
Branch:  feature/dark-mode-for-settings-page
Tasks:   5 completed, 0 failed
──────────────────────────────────────────────────────────────

Completed tasks:
  ✅ TASK-001: Add dark mode CSS variables
  ✅ TASK-002: Update Settings component theme toggle
  ✅ TASK-003: Persist theme preference to localStorage
  ✅ TASK-004: Add dark mode styles to navigation
  ✅ TASK-005: Update tests for theme switching

To inspect changes:
  git diff main..feature/dark-mode-for-settings-page
  git log main..feature/dark-mode-for-settings-page --oneline

[M]erge to main / [R]eject / [I]nspect: 
```

---

## Configuration Options

### Environment Variables

```bash
# API Configuration
export ANTHROPIC_API_KEY="sk-..."

# Orchestrator defaults
export TASKWRIGHT_MAX_PARALLEL=3
export TASKWRIGHT_PROJECT_PATH="."
export TASKWRIGHT_AUTO_APPROVE_THRESHOLD=0.8  # AI confidence threshold
```

### Project Configuration

```yaml
# .taskwright/config.yaml
orchestrator:
  max_parallel: 3
  worktrees_dir: .worktrees
  
  # AI Reviewer settings
  reviewer:
    auto_approve: true
    escalate_on_security: true
    escalate_on_breaking_changes: true
  
  # Test configuration
  tests:
    command: npm test
    timeout: 300
    
  # Git settings
  git:
    main_branch: main
    feature_prefix: feature/
    commit_style: conventional  # feat, fix, etc.
```

---

## Error Handling and Recovery

### Failure Scenarios

| Scenario | Handling |
|----------|----------|
| Investigation fails | AI Reviewer escalates, human decides |
| Task execution fails | Mark task failed, continue others, report at end |
| Merge conflict | Attempt auto-resolve, escalate if complex |
| Integration tests fail | Attempt fixes, escalate if persistent |
| API rate limit | Exponential backoff with retry |
| Network failure | Save state, allow resume |

### Resume Capability

```bash
# If workflow is interrupted, resume from last checkpoint
taskwright resume --workflow-id abc123

# Or re-run failed tasks only
taskwright retry --workflow-id abc123 --failed-only
```

---

## Comparison with Alternatives

| Aspect | Manual Workflow | Conductor | SDK Orchestrator |
|--------|-----------------|-----------|------------------|
| **Human steps** | ~10 | ~5 | 1 |
| **Parallel execution** | ❌ | ✅ | ✅ |
| **Automated checkpoints** | ❌ | ❌ | ✅ (AI Reviewer) |
| **Single command** | ❌ | ❌ | ✅ |
| **Git worktree management** | Manual | Built-in | Automated |
| **Integration testing** | Manual | Manual | Automated |
| **State persistence** | None | UI state | SQLite |
| **Resume capability** | ❌ | Partial | ✅ |

---

## Implementation Roadmap

### Phase 1: Core Orchestrator (1 week)
- [ ] Basic `FeatureOrchestrator` class
- [ ] Investigation and decomposition phases
- [ ] Single-threaded task execution
- [ ] Final human checkpoint

### Phase 2: Parallel Execution (3-4 days)
- [ ] Git worktree creation/cleanup
- [ ] Async parallel task execution
- [ ] Worktree merge handling
- [ ] Conflict detection

### Phase 3: AI Reviewer (2-3 days)
- [ ] `AIReviewer` subagent implementation
- [ ] Checkpoint auto-approval logic
- [ ] Escalation to human when needed
- [ ] Configurable review thresholds

### Phase 4: Polish and Testing (3-4 days)
- [ ] CLI interface (`taskwright implement`)
- [ ] Configuration file support
- [ ] Error handling and recovery
- [ ] Resume capability
- [ ] Documentation and examples

**Total Estimated Effort**: 2-3 weeks

---

## Related Documents

- [Claude Agent SDK: Two-Command Feature Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md) ⭐ SUCCESSOR - Refined two-command approach with manual override
- [Claude Agent SDK: Fast Path to TaskWright Orchestration](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md) - Initial SDK analysis
- [TaskWright LangGraph Orchestration: Build Strategy](./TaskWright_LangGraph_Orchestration_Build_Strategy.md) - LangGraph alternative
- [LangGraph-Native Orchestration for TaskWright](./LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md) - Technical architecture

---

## References

- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Python GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Git Worktrees Documentation](https://git-scm.com/docs/git-worktree)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

*Generated: December 2025*
*Context: Designing true end-to-end feature orchestration using Claude Agent SDK*
*Status: Research and specification phase*
