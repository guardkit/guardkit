# Claude Agent SDK: Fast Path to TaskWright Workflow Automation

## Executive Summary

The Claude Agent SDK provides a **dramatically faster path** to TaskWright workflow automation than the LangGraph reimplementation approach. The SDK can directly invoke existing TaskWright slash commands (`/task-work`, `/task-create`, etc.) without requiring any reimplementation of workflow logic.

### Terminology Note

This document uses "orchestration" in some places, but the more accurate term is **workflow automation**. 
TaskWright automates a developer's manual workflow - it's not multi-agent orchestration like swarm systems.
See [TaskWright vs Swarm Systems](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md#taskwright-vs-swarm-systems) for details.

**Key Finding**: The Claude Agent SDK reads and executes custom commands from `.claude/commands/` directories automatically. This means TaskWright's existing command files work immediately with the SDK.

**Revised Effort Estimate**: ~1 week for a working workflow runner (vs 3-4 weeks for LangGraph reimplementation)

**Trade-off**: Vendor lock-in to Anthropic (acceptable for initial release, with LangGraph as future multi-LLM path)

---

## How the Claude Agent SDK Works

The Claude Agent SDK is the programmatic interface to Claude Code's agent harness. It provides:

- **Direct slash command execution** - Your `.claude/commands/*.md` files work automatically
- **Subagent auto-detection** - Loads agents from `.claude/agents/` directories
- **Streaming responses** - Real-time message handling for checkpoints
- **Tool permissions** - Fine-grained control over what Claude can do
- **MCP integration** - Connect to external services via Model Context Protocol
- **Custom hooks** - Intercept and modify tool calls programmatically

### Installation

```bash
pip install claude-agent-sdk
```

Prerequisites:
- Python 3.10+
- Node.js (for Claude Code CLI)
- Claude Code 2.0.0+: `npm install -g @anthropic-ai/claude-code`

---

## Direct Invocation of TaskWright Commands

The SDK can invoke TaskWright's existing slash commands with zero modifications:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_task_work(task_id: str, project_path: str):
    """Execute /task-work command via Claude Agent SDK."""
    
    options = ClaudeAgentOptions(
        cwd=project_path,  # Where .claude/commands/ lives
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",  # Auto-approve file edits
        max_turns=50  # Allow multi-turn workflow
    )
    
    # This DIRECTLY invokes your /task-work command!
    async for message in query(
        prompt=f"/task-work {task_id}",
        options=options
    ):
        if message.type == "assistant":
            print(extract_text(message))
        elif message.type == "result":
            print(f"Task completed: {message.result}")
```

**That's it.** The SDK reads your `.claude/commands/task-work.md` file and executes it exactly as Claude Code does interactively.

### What Gets Used Automatically

| TaskWright Component | SDK Behavior |
|---------------------|--------------|
| `.claude/commands/task-work.md` | Invoked via `query(prompt="/task-work ...")` |
| `.claude/commands/task-create.md` | Invoked via `query(prompt="/task-create ...")` |
| `.claude/agents/*.md` | Auto-detected and available to the workflow |
| `.claude/tasks/*.md` | Read/written by the commands as normal |
| `CLAUDE.md` | Loaded if `setting_sources=["project"]` is set |

---

## Architecture with Claude Agent SDK

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TASKWRIGHT ORCHESTRATOR (NEW)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐                                                       │
│   │ Python CLI      │  taskwright plan TASK-XXX --design-only               │
│   │ (Click)         │  taskwright implement TASK-XXX                        │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐                                                       │
│   │ Orchestrator    │  • Track workflow state (SQLite)                      │
│   │ Layer           │  • Human checkpoint handling                          │
│   │ (Python)        │  • Progress display                                   │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐                                                       │
│   │ Claude Agent    │  query(prompt="/task-work TASK-XXX")                  │
│   │ SDK             │  query(prompt="/task-create ...")                     │
│   │ (Python)        │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                     EXISTING TASKWRIGHT                          │       │
│   │  .claude/commands/     .claude/agents/     .claude/tasks/       │       │
│   │  ├── task-work.md      ├── task-manager.md  ├── TASK-XXX.md     │       │
│   │  ├── task-create.md    ├── architect.md     └── ...             │       │
│   │  └── ...               └── ...                                  │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Human Checkpoints via Message Parsing

The SDK streams messages in real-time, allowing checkpoint interception:

```python
async def run_with_checkpoints(task_id: str, project_path: str):
    """Execute task-work with human checkpoint handling."""
    
    options = ClaudeAgentOptions(
        cwd=project_path,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",
        max_turns=100
    )
    
    async for message in query(prompt=f"/task-work {task_id}", options=options):
        if message.type == "assistant":
            text = extract_text(message)
            
            # Detect checkpoint patterns (defined in task-work.md)
            if "CHECKPOINT: Design Review Required" in text:
                print("\n" + "="*60)
                print("📋 DESIGN REVIEW CHECKPOINT")
                print("="*60)
                print(text)
                
                approval = input("\nApprove design? (y/n/feedback): ").strip()
                
                if approval.lower() == 'n':
                    print("❌ Design rejected. Workflow paused.")
                    save_checkpoint_state(task_id, "design_rejected")
                    return
                elif approval.lower() != 'y':
                    # User provided feedback - could send follow-up query
                    print(f"📝 Feedback recorded: {approval}")
                    
            elif "CHECKPOINT: Implementation Complete" in text:
                print("\n✅ Implementation phase complete")
                save_checkpoint_state(task_id, "implementation_complete")
                
        elif message.type == "result":
            print(f"\n🎉 Task completed: {message.result}")
            save_checkpoint_state(task_id, "completed")


def extract_text(message) -> str:
    """Extract text content from assistant message."""
    from claude_agent_sdk import TextBlock
    
    texts = []
    for block in message.content:
        if isinstance(block, TextBlock):
            texts.append(block.text)
    return "\n".join(texts)
```

---

## Design-First Workflow with State Persistence

Implement `--design-only` and `--implement-only` flags:

```python
import sqlite3
from pathlib import Path
from datetime import datetime

class TaskWrightOrchestrator:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.db_path = self.project_path / ".taskwright" / "state.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite state database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_state (
                    task_id TEXT PRIMARY KEY,
                    status TEXT,
                    design_approved INTEGER DEFAULT 0,
                    design_approved_at TEXT,
                    implementation_started_at TEXT,
                    completed_at TEXT,
                    last_checkpoint TEXT,
                    metadata TEXT
                )
            """)
    
    async def plan(self, task_id: str, design_only: bool = False):
        """Run planning phases, optionally stopping after design approval."""
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=50
        )
        
        async for message in query(prompt=f"/task-work {task_id}", options=options):
            if message.type == "assistant":
                text = extract_text(message)
                print(text)
                
                # Check for design checkpoint
                if "CHECKPOINT: Design Review Required" in text:
                    approval = input("\nApprove design? (y/n): ").strip()
                    
                    if approval.lower() == 'y':
                        self._save_design_approved(task_id)
                        
                        if design_only:
                            print("\n📋 Design approved and saved.")
                            print("Run with --implement-only to continue.")
                            return
                    else:
                        print("❌ Design not approved.")
                        return
    
    async def implement(self, task_id: str):
        """Resume implementation from approved design."""
        
        # Check design was approved
        if not self._is_design_approved(task_id):
            raise ValueError(f"Design not approved for {task_id}. Run plan first.")
        
        print(f"▶️ Resuming implementation for {task_id}...")
        
        options = ClaudeAgentOptions(
            cwd=str(self.project_path),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=100
        )
        
        # Continue from implementation phase
        # The task file should have the approved design already
        async for message in query(
            prompt=f"/task-work {task_id} --phase implementation",
            options=options
        ):
            if message.type == "assistant":
                print(extract_text(message))
            elif message.type == "result":
                self._mark_completed(task_id)
                print(f"\n🎉 Task {task_id} completed!")
    
    def _save_design_approved(self, task_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO task_state 
                (task_id, status, design_approved, design_approved_at)
                VALUES (?, 'design_approved', 1, ?)
            """, (task_id, datetime.now().isoformat()))
    
    def _is_design_approved(self, task_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT design_approved FROM task_state WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            return result and result[0] == 1
    
    def _mark_completed(self, task_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_state 
                SET status = 'completed', completed_at = ?
                WHERE task_id = ?
            """, (datetime.now().isoformat(), task_id))
```

---

## CLI Interface

```python
import click
import anyio
from taskwright_orchestrator import TaskWrightOrchestrator

@click.group()
def cli():
    """TaskWright - AI-powered development workflow orchestrator."""
    pass

@cli.command()
@click.argument('task_id')
@click.option('--design-only', is_flag=True, help='Stop after design approval')
@click.option('--project', '-p', default='.', help='Project path')
def plan(task_id: str, design_only: bool, project: str):
    """Plan a task, optionally stopping after design phase."""
    orchestrator = TaskWrightOrchestrator(project)
    anyio.run(orchestrator.plan, task_id, design_only)

@cli.command()
@click.argument('task_id')
@click.option('--project', '-p', default='.', help='Project path')
def implement(task_id: str, project: str):
    """Implement an approved design."""
    orchestrator = TaskWrightOrchestrator(project)
    anyio.run(orchestrator.implement, task_id)

@cli.command()
@click.option('--project', '-p', default='.', help='Project path')
def status(project: str):
    """Show status of all tasks."""
    orchestrator = TaskWrightOrchestrator(project)
    orchestrator.show_status()

if __name__ == '__main__':
    cli()
```

---

## Custom Hooks for Safety and Monitoring

The SDK supports hooks to intercept tool calls:

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def block_dangerous_commands(input_data, tool_use_id, context):
    """Block potentially dangerous bash commands."""
    if input_data["tool_name"] != "Bash":
        return {}
    
    command = input_data["tool_input"].get("command", "")
    
    dangerous_patterns = [
        "rm -rf /",
        "rm -rf ~",
        "DROP TABLE",
        "DELETE FROM",
        "> /dev/sda",
    ]
    
    for pattern in dangerous_patterns:
        if pattern in command:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Blocked dangerous command: {pattern}",
                }
            }
    
    return {}

async def log_all_tool_calls(input_data, tool_use_id, context):
    """Log all tool calls for audit trail."""
    print(f"🔧 Tool: {input_data['tool_name']}")
    print(f"   Input: {input_data['tool_input']}")
    return {}

# Use hooks in orchestrator
options = ClaudeAgentOptions(
    cwd=project_path,
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[block_dangerous_commands]),
            HookMatcher(matcher="*", hooks=[log_all_tool_calls]),
        ],
    }
)
```

---

## Comparison: Claude Agent SDK vs LangGraph Reimplementation

| Aspect | LangGraph (Reimplementation) | Claude Agent SDK |
|--------|------------------------------|------------------|
| **Effort** | 3-4 weeks | ~1 week |
| **Uses existing commands** | ❌ No (must reimplement) | ✅ Yes (direct invocation) |
| **Uses existing agents** | ❌ No (must reimplement) | ✅ Yes (auto-detected) |
| **Vendor lock-in** | ❌ No (any LLM) | ⚠️ Yes (Anthropic only) |
| **Human checkpoints** | Native `interrupt()` | Message parsing |
| **State persistence** | Built-in checkpointer | DIY (SQLite - simple) |
| **Multi-LLM future** | ✅ Ready | ❌ Anthropic only |
| **Production maturity** | High (LangGraph Platform) | Medium (newer SDK) |
| **Code reuse** | Low | High |
| **Maintenance** | Two codebases | One codebase |

---

## Recommended Strategy: Phased Approach

### Phase 1: Quick Win with Claude Agent SDK (~1 week)
- Build Python CLI that wraps `/task-work`, `/task-create`, etc.
- Add basic state tracking (SQLite)
- Add human checkpoint handling via message parsing
- **Deliverable**: Working orchestrator using existing commands

### Phase 2: Enhance and Polish (~2 weeks)
- Add progress streaming and better terminal UI
- Implement `--design-only` / `--implement-only` fully
- Add retry logic for failed API calls
- Add hooks for safety and logging
- Write documentation and examples

### Phase 3: RequireKit Integration (~1 week)
- Build orchestrator commands for requirements workflow
- `taskwright requirements gather`
- `taskwright requirements formalize`
- Connect to TaskWright task creation

### Phase 4: Consider LangGraph for Multi-LLM (Future)
- If you need to support non-Anthropic models (Gemini, GPT-4)
- If you need LangGraph Platform enterprise features
- The workflow knowledge from Phases 1-3 directly transfers
- Could run both paths in parallel during transition

---

## Migration Path to LangGraph (If Needed Later)

The Claude Agent SDK approach doesn't prevent future LangGraph adoption:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MIGRATION PATH                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   NOW: Claude Agent SDK                                                      │
│   ─────────────────────                                                      │
│   • Uses existing TaskWright commands directly                               │
│   • ~1 week to working orchestrator                                          │
│   • Validates workflow patterns in production                                │
│                                                                              │
│   LATER (IF NEEDED): LangGraph                                               │
│   ────────────────────────────                                               │
│   • Extract workflow patterns learned from SDK usage                         │
│   • Reimplement as LangGraph StateGraph                                      │
│   • Add multi-LLM support (OpenAI, Gemini, etc.)                            │
│   • The orchestrator CLI remains the same - just swap backend                │
│                                                                              │
│   Key Insight: The Claude Agent SDK phase is NOT wasted work.               │
│   It validates the orchestration patterns before committing to              │
│   a full reimplementation.                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What TaskWright Commands Need (Minor Updates)

To work optimally with the orchestrator, TaskWright commands may benefit from:

1. **Explicit checkpoint markers** in output:
   ```markdown
   <!-- In task-work.md -->
   When design is complete, output:
   "CHECKPOINT: Design Review Required"
   followed by the design summary.
   ```

2. **Phase flags** (optional):
   ```markdown
   <!-- Support --phase argument -->
   If $ARGUMENTS contains "--phase implementation":
     Skip to Phase 3 (Implementation)
   ```

3. **Structured output** for state tracking:
   ```markdown
   At the end of each phase, output:
   "PHASE_COMPLETE: [phase_name]"
   ```

These are minor additions to existing commands, not rewrites.

---

## Conclusion

The Claude Agent SDK provides the **fastest path to TaskWright orchestration**:

1. **Direct command invocation** - No reimplementation needed
2. **Existing agents work** - Auto-detected from `.claude/agents/`
3. **~1 week effort** - vs 3-4 weeks for LangGraph
4. **Production validation** - Learn orchestration patterns before committing to reimplementation
5. **Clear upgrade path** - LangGraph remains an option for multi-LLM future

The vendor lock-in trade-off is acceptable because:
- Anthropic models are currently best for coding tasks
- The orchestrator layer is thin - easy to swap later
- You validate patterns before investing in reimplementation

**Recommended next step**: Create a proof-of-concept that invokes `/task-work` via the SDK and handles one checkpoint.

---

## Related Documents

- [Claude Agent SDK: Two-Command Feature Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md) ⭐ RECOMMENDED - Two-command workflow with manual override
- [Claude Agent SDK: True End-to-End Orchestrator](./Claude_Agent_SDK_True_End_to_End_Orchestrator.md) - Full automation specification (superseded)
- [TaskWright LangGraph Orchestration: Build Strategy](./TaskWright_LangGraph_Orchestration_Build_Strategy.md)
- [LangGraph-Native Orchestration for TaskWright: Technical Architecture](./LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md)
- [AgenticFlow MCP vs LangGraph Orchestrator: Integration Analysis](./AgenticFlow_MCP_vs_LangGraph_Orchestrator_Analysis.md)

---

## References

- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Python GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Slash Commands in the SDK](https://platform.claude.com/docs/en/agent-sdk/slash-commands)
- [Subagents in the SDK](https://platform.claude.com/docs/en/agent-sdk/subagents)
- [Building Agents with the Claude Agent SDK (Anthropic Blog)](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

---

*Generated: December 2025*
*Context: Evaluating Claude Agent SDK as a faster path to TaskWright orchestration*
