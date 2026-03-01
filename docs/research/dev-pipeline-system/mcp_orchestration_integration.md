# MCP Server Integration for Agent Orchestration

## Overview

This document describes the MCP (Model Context Protocol) server that provides a standardized interface for AI agents to participate in the Ship's Computer orchestration system. 

The MCP server acts as a **gateway** between Claude-based agents (or any MCP-compatible client) and your NATS message bus infrastructure.

## Architecture Position

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NATS Message Bus (JetStream)                         │
└─────────────────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Twitter    │ │   LinkedIn   │ │   Research   │ │    GCSE      │
│    Agent     │ │    Agent     │ │    Agent     │ │    Tutor     │
│              │ │              │ │              │ │              │
│  (FastStream)│ │  (FastStream)│ │ (MCP Client) │ │  (FastStream)│
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                         │
        ┌────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Orchestration Server                       │
│                                                                   │
│  Tools:                          Resources:                       │
│  • publish_status               • orchestration://system/status   │
│  • request_approval             • orchestration://approvals/*     │
│  • check_commands               • orchestration://agents/{id}     │
│  • publish_result                                                 │
│  • get_agent_statuses                                             │
│  • get_pending_approvals                                          │
│  • send_command                                                   │
│  • broadcast_message                                              │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Clients                                    │
│                                                                   │
│  • Claude Desktop           • Claude Code                         │
│  • Custom Python scripts    • Other MCP-compatible agents         │
└──────────────────────────────────────────────────────────────────┘
```

## When to Use MCP vs Direct Python

| Use Case | Approach | Reasoning |
|----------|----------|-----------|
| Long-running monitors (Twitter, LinkedIn) | Direct FastStream | Performance, continuous operation |
| Reachy orchestrator | Direct FastStream | Sub-millisecond latency for voice |
| Claude-based research tasks | **MCP Server** | Natural integration with Claude |
| Ad-hoc Claude tasks via API | **MCP Server** | Easy participation in system |
| Dashboard backend | Direct FastStream | WebSocket performance |
| Prototyping new agents | **MCP Server** | Faster iteration |

## Installation

### Prerequisites

```bash
# NATS server running with JetStream
docker run -d --name nats -p 4222:4222 -p 8222:8222 nats:latest -js

# Or install locally
brew install nats-server  # macOS
nats-server -js
```

### Python Dependencies

```bash
pip install mcp nats-py pydantic
```

### Running the Server

```bash
# Set NATS URL if not localhost
export NATS_URL="nats://localhost:4222"

# Run the server
python mcp_orchestration_server.py
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "orchestration": {
      "command": "python",
      "args": ["/path/to/mcp_orchestration_server.py"],
      "env": {
        "NATS_URL": "nats://localhost:4222"
      }
    }
  }
}
```

## Available Tools

### publish_status

Report your agent's current state to the system.

```
Tool: publish_status
Arguments:
  - agent_id: "research-agent-v1"
  - state: "running"  # running | idle | awaiting_approval | error | paused
  - task_description: "Analyzing LangGraph documentation"
  - progress_percent: 45
```

### request_approval

Request human approval before taking significant actions.

```
Tool: request_approval
Arguments:
  - agent_id: "research-agent-v1"
  - summary: "Found 3 relevant papers to summarize"
  - priority: "normal"  # high | normal | low
  - items:
    - id: "paper-1"
      type: "document_summary"
      description: "LangGraph vs CrewAI comparison paper"
    - id: "paper-2"
      type: "document_summary"
      description: "Multi-agent orchestration patterns"
  - expires_minutes: 60
```

### check_commands

Poll for commands directed at your agent.

```
Tool: check_commands
Arguments:
  - agent_id: "research-agent-v1"
  - wait_seconds: 5  # 0 for immediate, max 30
```

Returns any pending commands (approve, reject, pause, resume, etc.)

### publish_result

Report task completion with outputs.

```
Tool: publish_result
Arguments:
  - agent_id: "research-agent-v1"
  - task_id: "task-12345"
  - status: "completed"  # completed | failed | partial
  - summary: "Completed analysis of 3 papers on agent orchestration"
  - outputs:
    - type: "document"
      title: "Agent Orchestration Analysis"
      location: "/outputs/research/orchestration-analysis.md"
```

### get_agent_statuses

Query the status of all agents or a specific agent.

```
Tool: get_agent_statuses
Arguments:
  - agent_id: "twitter-engagement-v1"  # optional, omit for all
```

### get_pending_approvals

Get all approval requests awaiting human review.

```
Tool: get_pending_approvals
Arguments:
  - agent_id: "twitter-engagement-v1"  # optional filter
```

### send_command

Send commands to other agents (for orchestration).

```
Tool: send_command
Arguments:
  - target_agent_id: "twitter-engagement-v1"
  - command: "approve"  # approve | reject | pause | resume | configure | terminate
  - parameters:
      request_id: "req-12345"
      approved_items: ["item-1", "item-2"]
  - reason: "Approved via Claude research agent"
```

### broadcast_message

Send a message to a topic for all listeners.

```
Tool: broadcast_message
Arguments:
  - topic: "system.announcements"
  - message: "System maintenance in 30 minutes"
  - data: {"maintenance_duration": 15}
```

## Available Resources

Resources provide read-only access to system state:

| URI | Description |
|-----|-------------|
| `orchestration://system/status` | Full system overview |
| `orchestration://approvals/pending` | All pending approval requests |
| `orchestration://agents/{agent_id}` | Status of specific agent |

## Usage Example: Claude Research Agent

Here's how Claude could participate as a research agent in your system:

### Session Start
```
1. Claude reads resource: orchestration://system/status
   → Sees current system state, other agents

2. Claude calls: publish_status
   → agent_id: "claude-research-v1"
   → state: "running"
   → task_description: "Starting research on LangGraph"
```

### During Work
```
3. Claude finds interesting papers, calls: request_approval
   → summary: "Found 5 papers worth deep-diving"
   → items: [list of papers with descriptions]

4. Claude calls: check_commands (with wait_seconds: 10)
   → Receives: {"command": "approve", "approved_items": ["paper-1", "paper-3"]}

5. Claude proceeds with approved items only
```

### Task Completion
```
6. Claude calls: publish_result
   → task_id: "research-langgraph-001"
   → summary: "Completed analysis of approved papers"
   → outputs: [document locations]
```

## Integration with Reachy Orchestrator

The MCP server and Reachy orchestrator both connect to the same NATS bus, so:

1. **MCP agent publishes status** → Reachy sees it in status updates
2. **MCP agent requests approval** → Reachy announces it verbally
3. **User approves via voice** → Reachy publishes command → MCP agent receives it via `check_commands`
4. **MCP agent completes task** → Reachy can announce completion

This creates seamless interaction between Claude-based agents and the embodied interface.

## Security Considerations

### Agent Identity

The MCP server currently trusts `agent_id` provided by clients. For production:

```python
# Add authentication layer
@self.server.call_tool()
async def call_tool(name: str, arguments: dict, auth_token: str) -> list[TextContent]:
    # Verify token maps to claimed agent_id
    if not verify_agent_token(auth_token, arguments.get("agent_id")):
        raise PermissionError("Agent ID mismatch")
```

### Command Authorization

Consider adding role-based access:

```python
# Only certain agents can send commands
ORCHESTRATOR_AGENTS = ["reachy-orchestrator", "dashboard-api"]

async def _tool_send_command(self, args: dict, caller_id: str) -> list[TextContent]:
    if caller_id not in ORCHESTRATOR_AGENTS:
        return [TextContent(type="text", text="Unauthorized: only orchestrators can send commands")]
```

## Monitoring

The NATS monitoring endpoint provides insight into message flow:

```bash
# View server stats
curl http://localhost:8222/varz

# View JetStream streams
nats stream ls
nats stream info AGENTS
```

## Troubleshooting

### "No commands pending" but expected approval response

Check that the Reachy orchestrator or dashboard is publishing to the correct topic:
```bash
nats sub "agents.commands.>" --verbose
```

### Agent state not appearing in get_agent_statuses

The MCP server caches state from subscriptions. If it started after agents, request agents broadcast status:
```bash
nats pub agents.commands.broadcast '{"command": "report_status"}'
```

### Connection refused to NATS

Verify NATS is running and NATS_URL is correct:
```bash
nats server ping
```

---

*MCP Integration Guide for Ship's Computer Project*
*January 2026*
