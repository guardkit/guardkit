# AgenticFlow Architecture Analysis: MCP Tools vs Workflow Automation

## Terminology Note

This document uses "orchestration" in places, but the more accurate term is **workflow automation**.
GuardKit automates a developer's manual process - it's not multi-agent swarm coordination.

See [GuardKit vs Swarm Systems](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md#guardkit-vs-swarm-systems) for the distinction.

---

## Executive Summary

This document analyzes the relationship between the original AgenticFlow platform architecture (with Requirements MCP and Engineering MCP servers) and workflow automation approaches. The key finding is that **MCPs and workflow automation serve complementary, not overlapping, roles**: MCPs provide capabilities (tools), while workflow automation provides process control.

---

## Critical Update: Claude Agent SDK Changes the Equation

### NEW: Claude Agent SDK (Fastest Path)

**The Claude Agent SDK can directly invoke GuardKit slash commands** like `/task-work`, `/task-create`, etc. This dramatically changes the effort equation.

See: [Claude Agent SDK: Fast Path to GuardKit Orchestration](./Claude_Agent_SDK_Fast_Path_to_GuardKit_Orchestration.md)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# This DIRECTLY invokes your /task-work command!
async for message in query(
    prompt=f"/task-work {task_id}",
    options=ClaudeAgentOptions(cwd=project_path)
):
    print(message)
```

**Effort**: ~1 week (vs 3-4 weeks for LangGraph reimplementation)

### What LangGraph CANNOT Do (Still True)

**LangGraph cannot directly call Claude Code slash commands** - but the Claude Agent SDK can!

Those slash commands are:
1. **Claude Code UI constructs** - Interpreted by Claude Code's interface
2. **Prompt injections** - Trigger Claude to read `.md` command files
3. **Not CLI commands** - No executable binary exists

**However**, the Claude Agent SDK provides the programmatic bridge we need.

### Updated Recommendation

The original analysis of LangGraph vs MCP remains valid, but add a new option:

1. **Phase 1**: Claude Agent SDK orchestrator (~1 week) - Fastest path
2. **Phase 2**: Validate patterns in production
3. **Phase 3**: LangGraph reimplementation IF multi-LLM support needed
4. **Phase 4**: MCP extraction when team-scale centralization needed

---

## Original AgenticFlow Architecture (4-Stage with MCPs)

The original AgenticFlow design implemented a 4-stage development lifecycle with MCP servers handling each stage:

### Stage 1: Specification → AgenticFlow MCP (Requirements MCP)
- Specification processing
- EARS requirements generation
- Human checkpoint for approval

### Stage 2: Task Definition → AgenticFlow MCP
- Task generation from requirements
- PM tool sync (Jira, Linear, Azure DevOps, GitHub)
- Human checkpoint before engineering

### Stage 3: Engineering → Engineering MCPs (Multiple Specialized)
- Back-end MCP (.NET, C#, Python, Kotlin)
- Front-end MCP (HTML/CSS/JS, React)
- Test MCP (TDD, Playwright)
- DevOps MCP (CI/CD, AWS, Azure)

### Stage 4: Deployment & QA
- Human checkpoint
- Docker/deployment automation

---

## Architectural Layer Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURAL LAYER COMPARISON                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   LAYER 1: ORCHESTRATION (Who controls the workflow?)                       │
│   ─────────────────────────────────────────────────────                     │
│                                                                              │
│   Original Design:        │  LangGraph Approach:                            │
│   ┌──────────────────┐    │  ┌──────────────────┐                          │
│   │ Implicit in MCP  │    │  │ LangGraph        │ ◄── EXPLICIT ORCHESTRATOR│
│   │ server logic     │    │  │ StateGraph       │                          │
│   │ + Human decisions│    │  │ + Checkpointer   │                          │
│   └──────────────────┘    │  └──────────────────┘                          │
│                                                                              │
│   LAYER 2: CAPABILITIES (What can be done?)                                 │
│   ─────────────────────────────────────────────                             │
│                                                                              │
│   Original Design:        │  LangGraph Approach:                            │
│   ┌──────────────────┐    │  ┌──────────────────┐                          │
│   │ Requirements MCP │────┼──│ MCP as TOOLS     │ ◄── MCPs BECOME TOOLS    │
│   │ Engineering MCPs │    │  │ within graph     │                          │
│   │ PM Tool MCPs     │    │  │ nodes            │                          │
│   └──────────────────┘    │  └──────────────────┘                          │
│                                                                              │
│   LAYER 3: STATE (Where is workflow state managed?)                         │
│   ─────────────────────────────────────────────────                         │
│                                                                              │
│   Original Design:        │  LangGraph Approach:                            │
│   ┌──────────────────┐    │  ┌──────────────────┐                          │
│   │ Each MCP manages │    │  │ Centralized      │ ◄── UNIFIED STATE        │
│   │ its own state    │    │  │ StateGraph with  │                          │
│   │ (distributed)    │    │  │ PostgresSaver    │                          │
│   └──────────────────┘    │  └──────────────────┘                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Insight: MCPs Are Tools, LangGraph Is the Conductor

The original AgenticFlow design treated **MCPs as both tools AND implicit orchestrators**. Each MCP had some workflow logic baked in. The transition between stages (Specification → Task Definition → Engineering) was either:
- Manual (human clicks "Proceed")
- Or loosely coupled (one MCP outputs, another inputs)

**With LangGraph as the orchestrator**, MCPs become pure capability providers:

```python
# MCPs become tools that LangGraph nodes call
from langchain_mcp import MCPToolkit

class AgenticFlowGraph:
    def __init__(self):
        # MCPs as tool providers
        self.requirements_mcp = MCPToolkit("requirements-mcp")
        self.engineering_mcp = MCPToolkit("engineering-mcp")
        self.pm_tools_mcp = MCPToolkit("pm-tools-mcp")
        
        # LangGraph manages the orchestration
        self.graph = StateGraph(AgenticFlowState)
        
    def build_graph(self):
        # Stage 1: Specification - calls Requirements MCP tools
        self.graph.add_node("gather_requirements", self.gather_requirements_node)
        self.graph.add_node("formalize_ears", self.formalize_ears_node)
        self.graph.add_node("spec_approval", self.human_checkpoint)  # interrupt()
        
        # Stage 2: Task Definition - calls PM Tools MCP
        self.graph.add_node("generate_tasks", self.generate_tasks_node)
        self.graph.add_node("sync_to_jira", self.sync_pm_tools_node)
        self.graph.add_node("task_approval", self.human_checkpoint)  # interrupt()
        
        # Stage 3: Engineering - calls Engineering MCP tools
        self.graph.add_node("implementation", self.implementation_node)
        self.graph.add_node("testing", self.testing_node)
        self.graph.add_node("review", self.review_node)
        
        # Stage 4: Deployment
        self.graph.add_node("deploy", self.deployment_node)
        self.graph.add_node("deploy_approval", self.human_checkpoint)
```

---

## Practical Comparison

| Concern | Original MCP Design | LangGraph + MCP Design |
|---------|---------------------|------------------------|
| **Workflow control** | Distributed across MCPs | Centralized in StateGraph |
| **State persistence** | Per-MCP (or none) | Unified checkpointer (Postgres/SQLite) |
| **Human checkpoints** | Manual stage transitions | Native `interrupt()` with resume |
| **Tool reuse** | MCPs are monolithic | MCPs are composable tools |
| **Multi-tool support** | Each MCP handles its clients | LangGraph handles clients, MCPs are backend |
| **Complexity routing** | Not inherent | Built into conditional edges |
| **Error recovery** | Per-MCP | Graph-level with time-travel debugging |

---

## Recommended Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED HYBRID ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌───────────────────┐                               │
│                          │   LangGraph       │                               │
│                          │   Orchestrator    │                               │
│                          │   (StateGraph)    │                               │
│                          └─────────┬─────────┘                               │
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                  │
│              │                     │                     │                  │
│              ▼                     ▼                     ▼                  │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│   │ Requirements MCP │  │  PM Tools MCP    │  │ Engineering MCP  │         │
│   │ ────────────────│  │ ────────────────│  │ ────────────────│         │
│   │ • gather_reqs   │  │ • create_epic   │  │ • generate_code │         │
│   │ • formalize_ears│  │ • create_task   │  │ • run_tests     │         │
│   │ • generate_bdd  │  │ • sync_jira     │  │ • review_code   │         │
│   │ • validate_reqs │  │ • sync_linear   │  │ • run_lint      │         │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                              │
│   These MCPs are STATELESS tools - they do one thing and return results     │
│   LangGraph manages ALL workflow state, transitions, and human checkpoints  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **MCPs are stateless capability providers** - They expose tools like `analyze-specification`, `create-task`, `run-tests`
2. **LangGraph is the stateful orchestrator** - It manages workflow state, transitions, and human checkpoints
3. **State is unified** - One checkpointer (PostgresSaver/SqliteSaver), one source of truth
4. **Human checkpoints are native** - Using LangGraph's `interrupt()` function, not manual stage transitions
5. **Multi-client support** - LangGraph can expose via CLI, API, or UI; MCPs stay as backend tools

---

## What Changes from Original Design

1. **MCPs become simpler** - They don't need workflow logic, just capability exposure
2. **Orchestration is explicit** - LangGraph graph definition IS your workflow documentation
3. **State is unified** - One checkpointer, one source of truth
4. **Human checkpoints are native** - `interrupt()` not manual stage transitions
5. **Multi-client support is cleaner** - LangGraph handles clients, MCPs are backend tools

---

## What Stays the Same

1. **MCP tool definitions** - The actual `analyze-specification`, `create-task`, etc. tools
2. **PM tool integrations** - Jira, Linear, Azure DevOps connectors
3. **Stack-specific engineering** - Python, React, .NET specialists
4. **Human checkpoint philosophy** - Humans approve at key gates
5. **4-stage conceptual model** - Specification → Task Definition → Engineering → Deployment

---

## Practical Implication for GuardKit

For the open-source GuardKit orchestration layer, this analysis suggests a clear migration path:

### Phase 1: Build the Orchestrator as Reimplementation (Current Focus)

**Important**: This is a reimplementation, not a wrapper. LangGraph cannot call Claude Code slash commands.

1. Build the **LangGraph orchestrator** that reimplements GuardKit's workflow logic
2. Use the command `.md` files as specifications for what each phase should do
3. Call **Anthropic API directly** for AI-powered operations (planning, code generation, review)
4. The orchestrator reads/writes the same task files as Claude Code version

**Effort estimate**: 3-4 weeks for production-ready implementation

### Phase 2: Extract MCPs When Scale Demands
When you need **team-scale centralization**:

1. Wrap the Python workflow logic in **MCP servers**
2. LangGraph orchestrator calls MCP tools instead of local functions
3. The orchestrator design remains the same - just swap local calls for MCP calls

### Phase 3: Enterprise Features
For commercial AgenticFlow:

1. Add authentication/authorization to MCP servers
2. Deploy MCPs on cloud infrastructure (AWS ECS, Azure Container Apps)
3. Add LangGraph Platform features (RBAC, workspaces, audit trails)

---

## Migration Path Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MIGRATION PATH                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CURRENT STATE                                                              │
│   ─────────────                                                              │
│   Claude Code + GuardKit slash commands (interactive, human-driven)       │
│                                                                              │
│   PHASE 1: LangGraph Orchestrator (Open Source) - REIMPLEMENTATION          │
│   ────────────────────────────────────────────────────────────────          │
│   ┌─────────────────┐                                                       │
│   │ LangGraph       │──► Python functions calling Anthropic API directly    │
│   │ StateGraph      │    (NOT wrapping slash commands - those can't be      │
│   │ + SqliteSaver   │     called programmatically)                          │
│   └─────────────────┘                                                       │
│                                                                              │
│   COEXISTENCE: Both Claude Code and LangGraph versions work with same       │
│                task files in .claude/tasks/                                 │
│                                                                              │
│   PHASE 2: MCP Extraction (Team Scale)                                      │
│   ─────────────────────────────────────                                     │
│   ┌─────────────────┐     ┌──────────────────┐                             │
│   │ LangGraph       │────▶│ Requirements MCP │ (Python logic wrapped)      │
│   │ Orchestrator    │────▶│ Engineering MCP  │ (Python logic wrapped)      │
│   │ + PostgresSaver │────▶│ PM Tools MCP     │ (Jira/Linear/etc)           │
│   └─────────────────┘     └──────────────────┘                             │
│                                                                              │
│   PHASE 3: Enterprise (Commercial AgenticFlow)                              │
│   ─────────────────────────────────────────────                             │
│   ┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│   │ LangGraph       │────▶│ MCP Servers      │────▶│ Cloud Deploy     │    │
│   │ Platform        │     │ + OAuth 2.1      │     │ (ECS/Container   │    │
│   │ (Enterprise)    │     │ + RBAC           │     │  Apps)           │    │
│   └─────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Conclusion

The original AgenticFlow MCP architecture and LangGraph orchestration are **complementary, not competing**:

- **MCPs** = What can be done (capabilities, tools)
- **LangGraph** = How and when things are done (orchestration, state, checkpoints)
- **Claude Agent SDK** = Fastest path to orchestration using existing commands

The cleanest path forward is now:
1. **Claude Agent SDK orchestrator** (~1 week) - Uses existing commands directly
2. Validate orchestration patterns in production
3. **LangGraph reimplementation** IF multi-LLM support needed (3-4 weeks)
4. **MCP extraction** when team-scale centralization is needed

**Key update**: The Claude Agent SDK can invoke Claude Code slash commands programmatically, providing a dramatically faster path to orchestration than LangGraph reimplementation. LangGraph remains valuable for multi-LLM scenarios and enterprise features.

---

## Related Documents

- [Claude Agent SDK: Two-Command Feature Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md) ⭐ RECOMMENDED - Two-command workflow with manual override
- [Claude Agent SDK: True End-to-End Orchestrator](./Claude_Agent_SDK_True_End_to_End_Orchestrator.md) - Full automation specification
- [Claude Agent SDK: Fast Path to GuardKit Orchestration](./Claude_Agent_SDK_Fast_Path_to_GuardKit_Orchestration.md) - Initial SDK analysis
- [LangGraph-Native Orchestration for GuardKit: Technical Architecture](./LangGraph-Native_Orchestration_for_GuardKit_Technical_Architecture.md)
- [GuardKit LangGraph Orchestration: Build Strategy](./GuardKit_LangGraph_Orchestration_Build_Strategy.md)

---

*Generated: December 2025*
*Updated: December 2025 - Added Claude Agent SDK as fastest path option*
*Context: Analyzing the relationship between original AgenticFlow MCP architecture and LangGraph orchestration for GuardKit*
