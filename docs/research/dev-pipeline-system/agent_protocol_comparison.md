# Agent Communication Protocols: Comparison & Recommendations

## The Current Landscape (January 2026)

The agent communication space has matured significantly. Here's what exists:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent Communication Stack                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │    MCP      │    │    A2A      │    │    ACP      │    │    ANP      │  │
│  │ (Anthropic) │    │  (Google)   │    │   (IBM)     │    │  (Various)  │  │
│  │             │    │             │    │             │    │             │  │
│  │ Agent↔Tool  │    │ Agent↔Agent │    │  Workflow   │    │  Network    │  │
│  │ Agent↔Data  │    │ Collaboration│   │ Orchestration│   │  Discovery  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │         │
│         └──────────────────┴──────────────────┴──────────────────┘         │
│                                    │                                        │
│                         ┌──────────▼──────────┐                            │
│                         │   Your Application   │                            │
│                         └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Protocol Comparison

| Protocol | Purpose | Transport | Key Feature | Maturity |
|----------|---------|-----------|-------------|----------|
| **MCP** | Agent ↔ Tools/Data | JSON-RPC, stdio | Tool standardization | Production-ready |
| **A2A** | Agent ↔ Agent | HTTP, SSE, JSON-RPC | Opaque collaboration | v0.3, Linux Foundation |
| **ACP** | Workflow orchestration | HTTP/REST, SSE | Performatives (inform, request, propose) | Enterprise |
| **ANP** | Network-wide coordination | P2P | Discovery, routing, health | Emerging |
| **FIPA-ACL** | Formal agent semantics | IIOP, HTTP | 20+ performatives, BDI model | Legacy (academic) |
| **NLIP** | Natural language agents | Application-level | No shared ontology needed | New (ECMA Dec 2025) |

## Gas Town's Approach

Gas Town uses a **git-backed persistence model** rather than a wire protocol:

```
┌──────────────────────────────────────────────────────────────────┐
│                    Gas Town Architecture                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Agent Identity = Bead (in Git)                                 │
│   ├── Role pointer                                               │
│   ├── Mail inbox (also Beads)                                    │
│   ├── Hook (persistent work assignment)                          │
│   └── State/history                                              │
│                                                                   │
│   Communication = File-based "mail" + CLI commands               │
│   ├── gt sling <bead-id> <rig>  → assigns work to hook          │
│   ├── gt mail check --inject    → injects pending messages      │
│   ├── gt nudge <agent>          → triggers agent to check hook   │
│   └── Agents discover work via GUPP (Git-backed Universal        │
│       Propulsion Protocol): "If there's work on your hook,       │
│       YOU MUST RUN IT"                                           │
│                                                                   │
│   Persistence = Git worktrees                                    │
│   ├── Survives agent crashes                                     │
│   ├── Full history in version control                            │
│   └── Rollback capability                                        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Key insight from Steve Yegge**: Gas Town adopted "MCP Agent Mail" pattern because 
"coding agents are pros at email-like interfaces, and you can use mail as an 
'agent village' messaging system without needing to train or prompt them."

## Your Architecture vs. Existing Protocols

### What You're Building

```
Your Ship's Computer
├── NATS Message Bus (real-time pub/sub)
├── Custom JSON message schema
├── MCP Server for Claude integration  
├── Reachy voice interface
└── Web dashboard
```

### How It Maps to Standards

| Your Component | Closest Standard | Alignment |
|----------------|------------------|-----------|
| NATS pub/sub | A2A (HTTP/SSE) | Different transport, similar semantics |
| Message schema | A2A Message/Task/Artifact | Very similar concepts |
| Approval workflow | A2A "input-required" state | Direct mapping |
| MCP Server | MCP | You're using this correctly |
| Agent discovery | A2A AgentCard | Could adopt |

## Recommendations

### Option 1: Adopt A2A Protocol ✅ Recommended for Future-Proofing

**Pros:**
- Linux Foundation backing, 150+ organizations
- Designed to complement MCP (which you're already using)
- SDKs in Python, JS, Java, Go, C#
- Built-in concepts for everything you need:
  - AgentCard (discovery)
  - Task lifecycle (submitted → working → input-required → completed)
  - Artifacts (results)
  - Streaming via SSE
  - Push notifications

**Cons:**
- HTTP-based (higher latency than NATS for local agents)
- More overhead for simple local-only scenarios
- Still relatively new (v0.3)

**Hybrid approach**: Use A2A for agent-to-agent semantics, but run over NATS transport locally:

```python
# A2A message format over NATS transport
message = {
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
        "id": "task-123",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Analyze this content"}]
        }
    }
}

# Publish to NATS instead of HTTP POST
await nats.publish(f"a2a.tasks.{agent_id}", json.dumps(message))
```

### Option 2: Keep Custom Protocol + MCP Bridge ✅ Pragmatic for Now

**Pros:**
- You control the schema
- NATS gives you sub-millisecond latency
- MCP bridge lets Claude participate
- Simpler for your specific use case

**Cons:**
- Not interoperable with A2A ecosystem
- You maintain it yourself

**This is essentially what you've designed**. The MCP server I created acts as the 
bridge between Claude (via MCP tools) and your custom NATS-based system.

### Option 3: Gas Town Style (Git-backed) ❌ Not Recommended for Your Use Case

**Why not:**
- You want real-time voice interaction (Reachy) — git is too slow
- You have cloud agents (Twitter/LinkedIn) — need network messaging
- Gas Town is optimized for coding agents with session persistence, not IoT/voice

## Practical Path Forward

### Phase 1: Current (What You Have)
```
NATS + Custom Schema + MCP Bridge
└── Works now, good for proof-of-concept
```

### Phase 2: A2A Semantics (When Ready)
```
A2A message format + NATS transport + MCP
└── Best of both worlds:
    - A2A semantics for interoperability
    - NATS speed for local agents
    - MCP for Claude/tool integration
```

### Implementation Sketch for Phase 2

```python
from a2a import AgentCard, Task, Message, Artifact
from faststream.nats import NatsBroker

class A2ANatsAdapter:
    """Run A2A protocol semantics over NATS transport."""
    
    def __init__(self, agent_card: AgentCard, broker: NatsBroker):
        self.card = agent_card
        self.broker = broker
        self.tasks: dict[str, Task] = {}
    
    async def send_task(self, target_agent: str, task: Task):
        """A2A tasks/send over NATS."""
        message = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": task.model_dump()
        }
        await self.broker.publish(
            message, 
            f"a2a.{target_agent}.tasks"
        )
    
    async def handle_task(self, msg):
        """Process incoming A2A task."""
        task = Task.model_validate(msg.body["params"])
        
        # Update task state
        task.status.state = "working"
        await self._publish_status(task)
        
        # Do work...
        result = await self.process(task)
        
        # Return artifact
        artifact = Artifact(
            type="text",
            parts=[{"type": "text", "text": result}]
        )
        task.status.state = "completed"
        task.artifacts.append(artifact)
        
        await self._publish_result(task)
```

## Key Takeaways

1. **MCP + A2A are complementary** — MCP for tools, A2A for agent collaboration
2. **Your NATS-based approach is valid** — it's faster than HTTP for local agents
3. **A2A semantics are worth adopting** — even over different transport
4. **Gas Town is a different paradigm** — file/git-based, great for coding agents, not for real-time voice
5. **Your MCP server bridge is the right pattern** — lets Claude participate without rewriting everything

## References

- [A2A Protocol Documentation](https://a2a-protocol.org/latest/)
- [A2A GitHub](https://github.com/a2aproject/A2A)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [Gas Town](https://github.com/steveyegge/gastown)
- [Agent Communication Protocols Survey](https://arxiv.org/html/2505.02279v1)
- [NLIP Standard (ECMA)](https://en.wikipedia.org/wiki/Agent_Communications_Language)

---

*Protocol Comparison for Ship's Computer Project*
*January 2026*
