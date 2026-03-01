# Distributed AI Agent Orchestration Architecture

## Project: "Ship's Computer" Multi-Agent System with Reachy Mini

**Version:** 1.0  
**Date:** January 2026  
**Author:** Rich (with Claude AI assistance)

---

## Executive Summary

This document outlines an architecture for orchestrating multiple AI agents through a unified messaging infrastructure, with both a web dashboard UI and an embodied AI interface (Reachy Mini robot) serving as interaction points. The system draws inspiration from science fiction ship computers (Star Trek's Computer, Red Dwarf's Holly, Iron Man's JARVIS) to create a natural, voice-driven command interface for managing distributed AI workflows.

The architecture leverages:
- **Gigabyte AI Top Atom** (NVIDIA GB10) for local LLM inference
- **Reachy Mini** robot for embodied voice interaction
- **NATS/Redis Streams** for cloud-based messaging infrastructure
- **NVIDIA NeMo Agent Toolkit** for agent orchestration
- **Web Dashboard** for visual monitoring and control

This approach was validated at CES 2026 where Jensen Huang demonstrated a similar DGX Spark + Reachy Mini personal assistant system.

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Hardware Components](#hardware-components)
3. [Message Bus Infrastructure](#message-bus-infrastructure)
4. [Message Schema Specification](#message-schema-specification)
5. [Agent Integration Pattern](#agent-integration-pattern)
6. [Reachy Orchestrator](#reachy-orchestrator)
7. [Web Dashboard](#web-dashboard)
8. [Use Cases](#use-cases)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Technology Stack Summary](#technology-stack-summary)

---

## System Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                    Message Bus (NATS / Redis Streams)              │
│                                                                    │
│  Topics:  agents.status    agents.approval    agents.command       │
│           agents.results   notifications      system.health        │
└────────────────────────────────────────────────────────────────────┘
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ LinkedIn │  │ Twitter  │  │ Research │  │  GCSE    │  │  Future  │
│  Agent   │  │  Agent   │  │  Agent   │  │  Tutor   │  │  Agents  │
│ (Cowork) │  │ (Goose?) │  │ (Claude) │  │          │  │          │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
     ☁️            ☁️           💻            💻            ?
   Cloud         Cloud        Local        Local
                                    
        │                              │
        ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   Web Dashboard UI      │    │   Reachy Orchestrator   │
│   (FastAPI + React)     │    │   (NeMo Agent Toolkit)  │
│                         │    │                         │
│   - Agent status grid   │    │   - Voice interface     │
│   - Approval queue      │    │   - Physical presence   │
│   - Action history      │    │   - Intent routing      │
│   - Manual overrides    │    │   - Human-in-the-loop   │
└─────────────────────────┘    └─────────────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           ▼
                  ┌─────────────────┐
                  │  Gigabyte Atom  │
                  │  (Local LLMs)   │
                  └─────────────────┘
```

### Key Design Principles

1. **Loose Coupling**: Agents communicate via message bus, not direct connections
2. **Location Agnostic**: Agents can run anywhere (cloud, local, edge)
3. **Dual Interface**: Both visual (dashboard) and embodied (Reachy) interfaces
4. **Human-in-the-Loop**: Critical actions require human approval
5. **Privacy-Aware**: Sensitive data processed locally on the Atom

---

## Hardware Components

### Gigabyte AI Top Atom (GB10)

The local AI compute backbone, equivalent to NVIDIA DGX Spark.

| Specification | Details |
|---------------|---------|
| Processor | NVIDIA GB10 Grace Blackwell Superchip (20-core Arm) |
| GPU | Blackwell architecture with 6,144 CUDA cores |
| Memory | 128GB unified LPDDR5x (273 GB/s bandwidth) |
| AI Performance | Up to 1 petaFLOP at FP4 precision |
| Fine-tuning Capacity | Models up to 70B parameters |
| Inference Capacity | Models up to 200B parameters |
| Networking | ConnectX-7 with 200Gbps, 10GbE, Wi-Fi 7 |
| Storage | Up to 4TB Gen5 NVMe SSD |
| Price | ~$3,500-4,000 USD |

**Role in Architecture:**
- Runs local LLMs for privacy-sensitive tasks
- Hosts the Reachy orchestrator
- Executes NeMo Agent Toolkit
- Provides intent-based model routing

### Reachy Mini

The embodied AI interface from Pollen Robotics / Hugging Face.

| Specification | Details |
|---------------|---------|
| Dimensions | 28cm height × 16cm width |
| Weight | 1.5 kg |
| Head Movement | 6 degrees of freedom (Stewart platform) |
| Body Rotation | 360 degrees |
| Eyes | Expressive LED display |
| Sensors | Camera, 4 microphones (reSpeaker array), speakers, IMU |
| Compute | Raspberry Pi 4/5 (Wireless version) |
| SDK | Python (reachy_mini package) |
| Price | $299-449 USD |

**Role in Architecture:**
- Voice input/output interface
- Visual presence for notifications
- Camera for visual context
- Expressive feedback (head movements, antenna animations)

---

## Message Bus Infrastructure

### Recommended: NATS with JetStream

For a single developer managing multiple agents, NATS offers the best balance of simplicity and capability.

#### Comparison Matrix

| Factor | Kafka | NATS | Redis Streams |
|--------|-------|------|---------------|
| Complexity | High | Very Low | Low |
| Latency | ~1-5ms | ~0.1-0.4ms | ~0.5-1ms |
| Setup | Multiple services | Single binary | Need Redis |
| Persistence | Built-in | JetStream | Optional |
| Scaling | Excellent | Good | Good |
| Solo dev fit | Overkill | Perfect | Good |
| Cloud options | Confluent, MSK | Synadia Cloud | Redis Cloud |

#### Why NATS?

1. **Single Binary**: No Zookeeper, no complex cluster setup
2. **Sub-millisecond Latency**: Critical for real-time voice interaction
3. **JetStream**: Built-in persistence when needed
4. **Key-Value Store**: Native KV API for agent state
5. **Leaf/Hub Topology**: Easy multi-region if needed later

### NATS Setup

```bash
# Install NATS server
# macOS
brew install nats-server

# Linux
curl -L https://github.com/nats-io/nats-server/releases/download/v2.10.7/nats-server-v2.10.7-linux-amd64.tar.gz -o nats.tar.gz
tar -xzf nats.tar.gz

# Run with JetStream enabled
nats-server -js

# Or with Docker
docker run -d --name nats -p 4222:4222 -p 8222:8222 nats:latest -js
```

### Topic Structure

```
agents/
├── status/
│   ├── {agent_id}           # Individual agent status updates
│   └── all                   # Aggregated status (for dashboard)
├── approval/
│   ├── requests              # Agents requesting human approval
│   └── responses             # Approval/rejection responses
├── commands/
│   ├── {agent_id}           # Commands to specific agents
│   └── broadcast             # Commands to all agents
├── results/
│   └── {agent_id}           # Completed task results
└── system/
    ├── health                # System health checks
    └── config                # Configuration updates
```

---

## Message Schema Specification

### Base Message Format

All messages follow a consistent envelope structure:

```json
{
    "message_id": "uuid-v4",
    "timestamp": "2026-01-22T14:30:00.000Z",
    "version": "1.0",
    "agent_id": "string",
    "event_type": "status | approval_request | command | result | error",
    "payload": {}
}
```

### Status Update Message

Sent by agents to report their current state.

```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-22T14:30:00.000Z",
    "version": "1.0",
    "agent_id": "twitter-engagement-v1",
    "event_type": "status",
    "payload": {
        "state": "running | idle | awaiting_approval | error | paused",
        "task_description": "Monitoring Twitter for AI content",
        "progress": {
            "current_step": 3,
            "total_steps": 5,
            "percentage": 60
        },
        "metrics": {
            "items_processed": 42,
            "items_pending": 3,
            "uptime_seconds": 3600
        },
        "last_activity": "2026-01-22T14:29:55.000Z"
    }
}
```

### Approval Request Message

Sent when an agent needs human authorization.

```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440001",
    "timestamp": "2026-01-22T14:30:00.000Z",
    "version": "1.0",
    "agent_id": "twitter-engagement-v1",
    "event_type": "approval_request",
    "payload": {
        "request_id": "req-12345",
        "priority": "high | normal | low",
        "expires_at": "2026-01-22T15:30:00.000Z",
        "summary": "Found 3 posts about Claude MCP worth engaging with",
        "items": [
            {
                "id": "item-1",
                "type": "tweet_reply",
                "content": {
                    "original_tweet": "Just discovered MCP for Claude...",
                    "author": "@ai_developer",
                    "proposed_response": "Great thread! MCP has transformed...",
                    "engagement_score": 0.85
                }
            },
            {
                "id": "item-2",
                "type": "tweet_reply",
                "content": {
                    "original_tweet": "Anyone using Claude for coding?",
                    "author": "@tech_enthusiast",
                    "proposed_response": "Yes! With the latest features...",
                    "engagement_score": 0.72
                }
            }
        ],
        "context": {
            "search_query": "Claude MCP AI agents",
            "time_window": "last_4_hours",
            "filter_applied": "toxicity < 0.3"
        }
    }
}
```

### Command Message

Sent to agents to control their behavior.

```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440002",
    "timestamp": "2026-01-22T14:31:00.000Z",
    "version": "1.0",
    "agent_id": "twitter-engagement-v1",
    "event_type": "command",
    "payload": {
        "command": "approve | reject | pause | resume | configure | terminate",
        "source": "reachy-voice | dashboard-ui | api",
        "operator": "rich",
        "parameters": {
            "request_id": "req-12345",
            "approved_items": ["item-1", "item-2"],
            "rejected_items": [],
            "modifications": {
                "item-1": {
                    "proposed_response": "Updated response text..."
                }
            }
        },
        "reason": "Approved via voice command"
    }
}
```

### Result Message

Sent when an agent completes a task.

```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440003",
    "timestamp": "2026-01-22T14:35:00.000Z",
    "version": "1.0",
    "agent_id": "research-agent-v1",
    "event_type": "result",
    "payload": {
        "task_id": "task-67890",
        "status": "completed | failed | partial",
        "summary": "Research on LangGraph vs CrewAI completed",
        "outputs": [
            {
                "type": "document",
                "title": "Framework Comparison Report",
                "location": "/outputs/research/langgraph-crewai-comparison.md",
                "size_bytes": 15420
            }
        ],
        "metrics": {
            "duration_seconds": 245,
            "tokens_used": 12500,
            "sources_consulted": 8
        },
        "next_steps": [
            "Review findings",
            "Decide on framework selection"
        ]
    }
}
```

### Error Message

Sent when an agent encounters a problem.

```json
{
    "message_id": "550e8400-e29b-41d4-a716-446655440004",
    "timestamp": "2026-01-22T14:32:00.000Z",
    "version": "1.0",
    "agent_id": "linkedin-engagement-v1",
    "event_type": "error",
    "payload": {
        "error_code": "RATE_LIMIT_EXCEEDED",
        "severity": "warning | error | critical",
        "message": "LinkedIn API rate limit reached",
        "details": {
            "limit": 100,
            "used": 100,
            "reset_at": "2026-01-22T15:00:00.000Z"
        },
        "recovery_action": "auto_retry | manual_intervention | none",
        "retry_at": "2026-01-22T15:00:00.000Z"
    }
}
```

---

## Agent Integration Pattern

### FastStream Framework

FastStream provides a unified API across multiple message brokers. Write once, deploy to NATS, Kafka, Redis, or RabbitMQ.

```bash
pip install faststream[nats]
# or
pip install faststream[redis]
pip install faststream[kafka]
```

### Base Agent Template

```python
"""
base_agent.py - Template for creating message-bus-connected agents
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from faststream import FastStream
from faststream.nats import NatsBroker, NatsMessage

# Configuration
NATS_URL = "nats://localhost:4222"

class AgentConfig(BaseModel):
    agent_id: str
    agent_type: str
    description: str
    version: str = "1.0"

class BaseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.broker = NatsBroker(NATS_URL)
        self.app = FastStream(self.broker)
        self.state = "idle"
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up message handlers for this agent"""
        
        @self.broker.subscriber(f"agents.commands.{self.config.agent_id}")
        async def handle_command(msg: NatsMessage):
            data = msg.body
            command = data.get("payload", {}).get("command")
            
            if command == "pause":
                self.state = "paused"
                await self.publish_status()
            elif command == "resume":
                self.state = "running"
                await self.publish_status()
            elif command == "approve":
                await self.handle_approval(data["payload"])
            elif command == "reject":
                await self.handle_rejection(data["payload"])
    
    async def publish_status(self, task_description: str = None):
        """Publish current agent status"""
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": self.config.agent_id,
            "event_type": "status",
            "payload": {
                "state": self.state,
                "task_description": task_description or self.config.description
            }
        }
        await self.broker.publish(message, "agents.status.all")
    
    async def request_approval(
        self, 
        summary: str, 
        items: list,
        priority: str = "normal"
    ) -> str:
        """Request human approval for actions"""
        request_id = str(uuid.uuid4())
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": self.config.agent_id,
            "event_type": "approval_request",
            "payload": {
                "request_id": request_id,
                "priority": priority,
                "summary": summary,
                "items": items
            }
        }
        
        self.state = "awaiting_approval"
        await self.broker.publish(message, "agents.approval.requests")
        await self.publish_status(f"Awaiting approval: {summary}")
        
        return request_id
    
    async def publish_result(self, task_id: str, summary: str, outputs: list):
        """Publish task completion result"""
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": self.config.agent_id,
            "event_type": "result",
            "payload": {
                "task_id": task_id,
                "status": "completed",
                "summary": summary,
                "outputs": outputs
            }
        }
        await self.broker.publish(message, f"agents.results.{self.config.agent_id}")
    
    async def handle_approval(self, payload: dict):
        """Override in subclass to handle approvals"""
        pass
    
    async def handle_rejection(self, payload: dict):
        """Override in subclass to handle rejections"""
        pass
    
    async def run(self):
        """Start the agent"""
        async with self.broker:
            self.state = "running"
            await self.publish_status()
            await self.main_loop()
    
    async def main_loop(self):
        """Override in subclass with main agent logic"""
        while True:
            if self.state == "running":
                await self.do_work()
            await asyncio.sleep(1)
    
    async def do_work(self):
        """Override in subclass"""
        pass
```

### Example: Twitter Engagement Agent

```python
"""
twitter_engagement_agent.py - Example agent implementation
"""

from base_agent import BaseAgent, AgentConfig

class TwitterEngagementAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(
            agent_id="twitter-engagement-v1",
            agent_type="engagement",
            description="Monitors Twitter for AI content opportunities"
        ))
        self.pending_approvals = {}
    
    async def do_work(self):
        """Main work loop - find engagement opportunities"""
        # Search for relevant tweets
        tweets = await self.search_tweets(
            query="Claude MCP AI agents",
            toxicity_filter=0.3
        )
        
        if tweets:
            # Prepare items for approval
            items = [
                {
                    "id": f"tweet-{t['id']}",
                    "type": "tweet_reply",
                    "content": {
                        "original_tweet": t["text"],
                        "author": t["author"],
                        "proposed_response": await self.generate_response(t),
                        "engagement_score": t["score"]
                    }
                }
                for t in tweets
            ]
            
            # Request approval
            request_id = await self.request_approval(
                summary=f"Found {len(tweets)} posts worth engaging with",
                items=items,
                priority="normal"
            )
            
            self.pending_approvals[request_id] = items
        
        # Wait before next search
        await asyncio.sleep(300)  # 5 minutes
    
    async def handle_approval(self, payload: dict):
        """Execute approved engagements"""
        request_id = payload["parameters"]["request_id"]
        approved_ids = payload["parameters"].get("approved_items", [])
        
        items = self.pending_approvals.get(request_id, [])
        
        for item in items:
            if item["id"] in approved_ids:
                await self.post_reply(
                    tweet_id=item["id"],
                    response=item["content"]["proposed_response"]
                )
        
        del self.pending_approvals[request_id]
        self.state = "running"
        await self.publish_status()
    
    async def search_tweets(self, query: str, toxicity_filter: float):
        """Search Twitter API - implement with your preferred method"""
        # TODO: Implement Twitter API search
        pass
    
    async def generate_response(self, tweet: dict) -> str:
        """Generate response using local LLM"""
        # TODO: Call local LLM on Atom
        pass
    
    async def post_reply(self, tweet_id: str, response: str):
        """Post reply to Twitter"""
        # TODO: Implement Twitter posting
        pass

# Run the agent
if __name__ == "__main__":
    agent = TwitterEngagementAgent()
    asyncio.run(agent.run())
```

---

## Reachy Orchestrator

The Reachy orchestrator serves as the embodied interface to the agent system, built on NVIDIA NeMo Agent Toolkit.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Reachy Orchestrator                         │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │   Voice     │───▶│   Intent     │───▶│  NeMo Agent     │   │
│  │   Input     │    │   Router     │    │  Toolkit        │   │
│  │  (Whisper)  │    │              │    │                 │   │
│  └─────────────┘    └──────────────┘    └────────┬────────┘   │
│                                                   │            │
│  ┌─────────────┐    ┌──────────────┐    ┌────────▼────────┐   │
│  │   Voice     │◀───│   Response   │◀───│  Tool Router    │   │
│  │   Output    │    │   Generator  │    │                 │   │
│  │ (ElevenLabs)│    │              │    │  - Agent Cmds   │   │
│  └─────────────┘    └──────────────┘    │  - Status Query │   │
│                                          │  - Local LLM    │   │
│  ┌─────────────┐                        │  - Web Search   │   │
│  │   Reachy    │◀───────────────────────┴─────────────────┘   │
│  │   Motion    │                                              │
│  │   Control   │                                              │
│  └─────────────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              NATS Message Bus Connection                 │  │
│  │   Subscribe: agents.approval.requests, agents.status.*   │  │
│  │   Publish: agents.commands.*                             │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### NeMo Agent Toolkit Configuration

```yaml
# reachy_orchestrator_config.yml

llms:
  # Fast model for chit-chat and simple queries
  fast_llm:
    _type: nim
    model_name: microsoft/phi-3-mini-128k-instruct
    temperature: 0.7
  
  # Local model on Atom for sensitive tasks
  local_llm:
    _type: openai_compatible
    base_url: http://localhost:8000/v1
    model_name: nemotron-3-nano-30b
    temperature: 0.3
  
  # Routing model
  routing_llm:
    _type: nim
    model_name: microsoft/phi-3-mini-128k-instruct
    temperature: 0.0
  
  # Agent/tool calling model
  agent_llm:
    _type: nim
    model_name: nvidia/nemotron-3-nano-30b-a3b
    temperature: 0.2

functions:
  # Query agent statuses
  get_agent_status:
    _type: custom
    module: tools.agent_tools
    function: get_agent_status
  
  # Send command to agent
  send_agent_command:
    _type: custom
    module: tools.agent_tools
    function: send_agent_command
  
  # Get pending approvals
  get_pending_approvals:
    _type: custom
    module: tools.agent_tools
    function: get_pending_approvals
  
  # Approve/reject items
  process_approval:
    _type: custom
    module: tools.agent_tools
    function: process_approval
  
  # Web search for queries
  web_search:
    _type: web_search
    max_results: 5
  
  # ReAct agent for tool calling
  react_agent:
    _type: react_agent
    llm_name: agent_llm
    verbose: true
    max_tool_calls: 5
    tool_names:
      - get_agent_status
      - send_agent_command
      - get_pending_approvals
      - process_approval
      - web_search

  # Intent router
  router:
    _type: router
    llm_name: routing_llm
    route_config:
      - name: agent_management
        description: Questions about agent status, approvals, commands, or managing AI agents
      - name: chit_chat
        description: Simple conversation, greetings, small talk
      - name: information
        description: Questions requiring web search or factual information
      - name: sensitive
        description: Tasks involving private data, emails, or personal information

workflow:
  _type: reachy_orchestrator_workflow
  router: router
  react_agent: react_agent
  fast_llm: fast_llm
  local_llm: local_llm
```

### Orchestrator Implementation

```python
"""
reachy_orchestrator.py - Main orchestrator connecting Reachy to agent system
"""

import asyncio
from typing import Optional
from datetime import datetime
from faststream.nats import NatsBroker
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
from pipecat.frames.frames import TextFrame, AudioFrame
from nemo_agent_toolkit import Agent

class ReachyOrchestrator:
    def __init__(self, config_path: str = "reachy_orchestrator_config.yml"):
        # Message bus connection
        self.broker = NatsBroker("nats://localhost:4222")
        
        # NeMo Agent Toolkit
        self.agent = Agent(config_file=config_path)
        
        # Reachy connection
        self.reachy: Optional[ReachyMini] = None
        
        # State
        self.pending_notifications = []
        self.agent_states = {}
        self.is_listening = False
    
    async def connect(self):
        """Initialize all connections"""
        # Connect to message bus
        await self.broker.start()
        
        # Connect to Reachy
        self.reachy = ReachyMini()
        await self.reachy.connect()
        
        # Set up message handlers
        await self._setup_handlers()
        
        # Initial status query
        await self._refresh_agent_states()
    
    async def _setup_handlers(self):
        """Subscribe to relevant message bus topics"""
        
        @self.broker.subscriber("agents.approval.requests")
        async def on_approval_request(msg):
            """Agent is requesting approval"""
            await self._handle_approval_request(msg.body)
        
        @self.broker.subscriber("agents.status.*")
        async def on_status_update(msg):
            """Agent status changed"""
            await self._handle_status_update(msg.body)
        
        @self.broker.subscriber("agents.results.*")
        async def on_result(msg):
            """Agent completed a task"""
            await self._handle_result(msg.body)
        
        @self.broker.subscriber("agents.error.*")
        async def on_error(msg):
            """Agent encountered an error"""
            await self._handle_error(msg.body)
    
    async def _handle_approval_request(self, data: dict):
        """Handle incoming approval request from an agent"""
        agent_id = data["agent_id"]
        payload = data["payload"]
        
        # Store for later reference
        self.pending_notifications.append({
            "type": "approval",
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "data": payload
        })
        
        # Alert user via Reachy
        await self._play_notification_sound()
        await self._animate_attention()
        
        # If high priority, speak immediately
        if payload.get("priority") == "high":
            await self._speak(
                f"Attention! {agent_id} needs urgent approval. "
                f"{payload['summary']}"
            )
    
    async def _handle_status_update(self, data: dict):
        """Track agent status changes"""
        agent_id = data["agent_id"]
        self.agent_states[agent_id] = data["payload"]
    
    async def _handle_result(self, data: dict):
        """Handle task completion notification"""
        agent_id = data["agent_id"]
        payload = data["payload"]
        
        self.pending_notifications.append({
            "type": "result",
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "data": payload
        })
        
        # Gentle notification
        await self._play_completion_sound()
        await self._gentle_nod()
    
    async def _handle_error(self, data: dict):
        """Handle agent error"""
        agent_id = data["agent_id"]
        payload = data["payload"]
        
        if payload.get("severity") == "critical":
            await self._play_alert_sound()
            await self._speak(
                f"Warning: {agent_id} has a critical error. "
                f"{payload['message']}"
            )
    
    async def process_voice_input(self, transcript: str):
        """Process user voice command through NeMo Agent Toolkit"""
        
        # Build context with pending notifications
        context = {
            "pending_notifications": self.pending_notifications,
            "agent_states": self.agent_states,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Route through NeMo Agent
        response = await self.agent.process(
            user_input=transcript,
            context=context
        )
        
        # If response includes agent commands, publish them
        if hasattr(response, 'tool_calls'):
            for tool_call in response.tool_calls:
                if tool_call.name == "send_agent_command":
                    await self._publish_command(tool_call.arguments)
                elif tool_call.name == "process_approval":
                    await self._publish_approval_response(tool_call.arguments)
        
        # Speak the response
        await self._speak(response.text)
        
        # Animate based on response sentiment
        await self._animate_response(response)
        
        # Clear processed notifications
        if "approval" in transcript.lower() or "approve" in transcript.lower():
            self.pending_notifications = [
                n for n in self.pending_notifications 
                if n["type"] != "approval"
            ]
    
    async def _publish_command(self, args: dict):
        """Publish command to agent via message bus"""
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": args["agent_id"],
            "event_type": "command",
            "payload": {
                "command": args["command"],
                "source": "reachy-voice",
                "parameters": args.get("parameters", {})
            }
        }
        
        topic = f"agents.commands.{args['agent_id']}"
        await self.broker.publish(message, topic)
    
    async def _publish_approval_response(self, args: dict):
        """Publish approval/rejection response"""
        await self._publish_command({
            "agent_id": args["agent_id"],
            "command": "approve" if args.get("approved") else "reject",
            "parameters": {
                "request_id": args["request_id"],
                "approved_items": args.get("approved_items", []),
                "rejected_items": args.get("rejected_items", [])
            }
        })
    
    # Reachy animation methods
    async def _play_notification_sound(self):
        """Play attention-getting sound"""
        # TODO: Implement sound playback
        pass
    
    async def _play_completion_sound(self):
        """Play gentle completion chime"""
        pass
    
    async def _play_alert_sound(self):
        """Play alert/warning sound"""
        pass
    
    async def _animate_attention(self):
        """Animate Reachy to get attention"""
        if self.reachy:
            # Look up and wiggle antennas
            await self.reachy.goto_target(
                head=create_head_pose(z=15, degrees=True, mm=True),
                duration=0.5
            )
            await asyncio.sleep(0.3)
            await self.reachy.goto_target(
                head=create_head_pose(z=0, degrees=True, mm=True),
                duration=0.3
            )
    
    async def _gentle_nod(self):
        """Small acknowledgment nod"""
        if self.reachy:
            await self.reachy.goto_target(
                head=create_head_pose(y=-5, degrees=True, mm=True),
                duration=0.3
            )
            await asyncio.sleep(0.2)
            await self.reachy.goto_target(
                head=create_head_pose(y=0, degrees=True, mm=True),
                duration=0.3
            )
    
    async def _animate_response(self, response):
        """Animate based on response content"""
        # Could analyze sentiment and animate accordingly
        pass
    
    async def _speak(self, text: str):
        """Output speech via Reachy's speakers"""
        # TODO: Integrate with ElevenLabs or local TTS
        print(f"[Reachy says]: {text}")
    
    async def _refresh_agent_states(self):
        """Query all agents for their current status"""
        # Broadcast status request
        await self.broker.publish(
            {"command": "report_status"},
            "agents.commands.broadcast"
        )

# Main entry point
async def main():
    orchestrator = ReachyOrchestrator()
    await orchestrator.connect()
    
    # Keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Voice Command Examples

| User Says | Reachy Response | Action |
|-----------|-----------------|--------|
| "What's up?" | "You have 2 pending approvals. Twitter agent found 3 posts about Claude MCP. LinkedIn agent is idle." | Status summary |
| "Tell me about the Twitter posts" | "The first is from @ai_developer about MCP integration, engagement score 0.85. The second..." | Detail expansion |
| "Approve the first two, skip the third" | "Done. I've approved the first two responses and skipped the third." | Publishes approval command |
| "Status report" | "3 agents running. Twitter: active, LinkedIn: idle, Research: 60% complete." | Full status |
| "Pause the Twitter agent" | "Twitter agent paused." | Publishes pause command |
| "How's my research going?" | "Your research on LangGraph vs CrewAI is 60% complete, about 10 minutes remaining." | Status query |

---

## Web Dashboard

### Technology Stack

- **Backend**: FastAPI + FastStream (shares message bus connection)
- **Frontend**: React + TypeScript + TailwindCSS
- **Real-time**: WebSockets for live updates
- **State**: React Query for server state management

### Dashboard Components

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent Orchestration Dashboard                    🔴 Live      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Twitter    │ │  LinkedIn   │ │  Research   │ │   GCSE    │ │
│  │  ────────   │ │  ────────   │ │  ────────   │ │  ──────   │ │
│  │  🟢 Running │ │  🟡 Idle    │ │  🔵 Working │ │  ⚫ Off   │ │
│  │             │ │             │ │             │ │           │ │
│  │  3 pending  │ │  0 pending  │ │  60%        │ │           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Pending Approvals (3)                              [Approve All]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🐦 Twitter • High Priority • 5 min ago                  │   │
│  │                                                         │   │
│  │ Found 3 posts about Claude MCP worth engaging with      │   │
│  │                                                         │   │
│  │ □ @ai_developer: "Just discovered MCP for Claude..."    │   │
│  │   Response: "Great thread! MCP has transformed..."      │   │
│  │   Score: 0.85  [Edit] [Preview]                        │   │
│  │                                                         │   │
│  │ □ @tech_enthusiast: "Anyone using Claude for coding?"   │   │
│  │   Response: "Yes! With the latest features..."          │   │
│  │   Score: 0.72  [Edit] [Preview]                        │   │
│  │                                                         │   │
│  │              [Approve Selected] [Reject All] [Skip]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Activity Log                                        [Filter ▼] │
├─────────────────────────────────────────────────────────────────┤
│  14:35  Research agent completed "LangGraph comparison"         │
│  14:32  LinkedIn agent rate limited (resets 15:00)              │
│  14:30  Twitter agent requested approval (3 items)              │
│  14:25  Voice command: "approve the first two" via Reachy       │
│  14:20  Twitter agent started monitoring                        │
└─────────────────────────────────────────────────────────────────┘
```

### FastAPI Backend

```python
"""
dashboard_api.py - FastAPI backend for web dashboard
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faststream.nats import NatsBroker
from typing import List
import asyncio
import json

app = FastAPI(title="Agent Orchestration Dashboard")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state
broker = NatsBroker("nats://localhost:4222")
connected_websockets: List[WebSocket] = []
agent_states = {}
pending_approvals = []
activity_log = []

@app.on_event("startup")
async def startup():
    await broker.start()
    
    # Subscribe to all agent messages
    @broker.subscriber("agents.>")
    async def handle_agent_message(msg):
        data = msg.body
        
        # Update state based on message type
        if data["event_type"] == "status":
            agent_states[data["agent_id"]] = data["payload"]
        elif data["event_type"] == "approval_request":
            pending_approvals.append(data)
        elif data["event_type"] == "result":
            activity_log.append({
                "timestamp": data["timestamp"],
                "message": f"{data['agent_id']} completed: {data['payload']['summary']}"
            })
        
        # Broadcast to all connected websockets
        await broadcast_update({
            "type": data["event_type"],
            "data": data
        })

async def broadcast_update(message: dict):
    """Send update to all connected WebSocket clients"""
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
    
    for ws in disconnected:
        connected_websockets.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    
    # Send current state
    await websocket.send_json({
        "type": "initial_state",
        "data": {
            "agents": agent_states,
            "pending_approvals": pending_approvals,
            "activity_log": activity_log[-50:]
        }
    })
    
    try:
        while True:
            # Receive commands from frontend
            data = await websocket.receive_json()
            await handle_frontend_command(data)
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)

async def handle_frontend_command(data: dict):
    """Process command from web frontend"""
    command_type = data.get("type")
    
    if command_type == "approve":
        await broker.publish({
            "event_type": "command",
            "agent_id": data["agent_id"],
            "payload": {
                "command": "approve",
                "source": "dashboard-ui",
                "parameters": data["parameters"]
            }
        }, f"agents.commands.{data['agent_id']}")
    
    elif command_type == "pause":
        await broker.publish({
            "event_type": "command",
            "agent_id": data["agent_id"],
            "payload": {
                "command": "pause",
                "source": "dashboard-ui"
            }
        }, f"agents.commands.{data['agent_id']}")

@app.get("/api/agents")
async def get_agents():
    """Get all agent states"""
    return {"agents": agent_states}

@app.get("/api/approvals")
async def get_pending_approvals():
    """Get pending approval requests"""
    return {"approvals": pending_approvals}

@app.post("/api/agents/{agent_id}/command")
async def send_command(agent_id: str, command: dict):
    """Send command to specific agent"""
    await broker.publish({
        "event_type": "command",
        "agent_id": agent_id,
        "payload": {
            "command": command["command"],
            "source": "dashboard-api",
            "parameters": command.get("parameters", {})
        }
    }, f"agents.commands.{agent_id}")
    
    return {"status": "sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Use Cases

### Use Case 1: Social Media Engagement Workflow

**Scenario**: Twitter agent finds relevant posts about AI topics.

```
1. Twitter agent searches for "Claude MCP AI agents"
2. Finds 3 relevant posts, generates response drafts
3. Publishes approval_request to agents.approval.requests
4. Reachy receives notification, plays sound, animates
5. User (working, not looking at screen): "What's up?"
6. Reachy: "Twitter agent found 3 posts about Claude MCP. 
   First from @ai_developer about MCP integration, score 0.85..."
7. User: "Approve the first two, skip the third"
8. Orchestrator publishes command to agents.commands.twitter-engagement-v1
9. Twitter agent receives approval, posts replies
10. Agent publishes result to agents.results.twitter-engagement-v1
11. Reachy does gentle nod, optionally announces completion
```

### Use Case 2: Research Task Completion

**Scenario**: Deep research agent completes a comparison task.

```
1. User earlier: "Research LangGraph vs CrewAI for my use case"
2. Research agent runs for ~20 minutes
3. Agent publishes periodic status updates (30%, 60%, etc.)
4. Dashboard shows progress bar
5. Agent completes, publishes result with document location
6. Reachy plays completion chime, gentle nod
7. User: "How did the research go?"
8. Reachy: "Completed. LangGraph appears better suited for your 
   human-in-the-loop requirements. The full report is ready."
9. User can view full report in dashboard or ask for details verbally
```

### Use Case 3: Error Handling

**Scenario**: LinkedIn agent hits rate limit.

```
1. LinkedIn agent attempts API call
2. Receives 429 rate limit response
3. Publishes error message with severity "warning"
4. Reachy stores notification but doesn't interrupt
5. Dashboard shows warning indicator on LinkedIn agent card
6. User eventually: "Status report"
7. Reachy: "Twitter running, LinkedIn rate-limited until 3pm, 
   Research 60% complete"
8. Agent automatically retries when limit resets
9. Publishes status update back to "running"
```

### Use Case 4: GCSE Tutor Integration (Future)

**Scenario**: Tutor agent used for daughter's study session.

```
1. User: "Start a study session on Macbeth Act 3"
2. GCSE Tutor agent activates
3. Reachy becomes the tutor interface
4. After session, agent publishes result with session summary
5. Parent can review session transcript in dashboard
6. Agent stores progress for continuity in next session
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up NATS server (local Docker)
- [ ] Implement base agent template with FastStream
- [ ] Create message schema validation (Pydantic models)
- [ ] Test pub/sub with simple mock agent

### Phase 2: First Agent (Weeks 3-4)
- [ ] Port existing Twitter engagement logic to new architecture
- [ ] Implement approval request flow
- [ ] Test end-to-end with command-line interface
- [ ] Add to existing Cowork workflow

### Phase 3: Dashboard MVP (Weeks 5-6)
- [ ] FastAPI backend with WebSocket support
- [ ] React frontend with agent status grid
- [ ] Approval queue interface
- [ ] Activity log

### Phase 4: Reachy Integration (Weeks 7-8)
- [ ] Receive Reachy Mini hardware
- [ ] Set up NeMo Agent Toolkit on Atom
- [ ] Implement voice pipeline (Whisper + ElevenLabs)
- [ ] Connect to message bus
- [ ] Test voice commands for agent control

### Phase 5: Full Integration (Weeks 9-10)
- [ ] LinkedIn agent migration
- [ ] Research agent integration
- [ ] Dashboard ↔ Reachy synchronization
- [ ] Error handling and recovery
- [ ] Documentation and refinement

### Phase 6: GCSE Tutor (Future)
- [ ] Integrate tutor agent to same infrastructure
- [ ] Reachy as tutor interface
- [ ] Session tracking and reporting

---

## Technology Stack Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Message Bus** | NATS + JetStream | Event-driven agent communication |
| **Agent Framework** | FastStream | Unified broker abstraction |
| **Orchestration** | NeMo Agent Toolkit | Intent routing, tool calling |
| **Local LLM** | Nemotron 3 Nano 30B | Privacy-sensitive inference |
| **Hardware** | Gigabyte AI Top Atom | Local compute backbone |
| **Robot** | Reachy Mini | Embodied voice interface |
| **Voice Input** | Whisper (local) | Speech-to-text |
| **Voice Output** | ElevenLabs | Text-to-speech |
| **Dashboard Backend** | FastAPI | REST + WebSocket API |
| **Dashboard Frontend** | React + TypeScript | Web UI |
| **Schema Validation** | Pydantic | Message validation |

---

## References

- [NVIDIA DGX Spark + Reachy Mini Demo (CES 2026)](https://huggingface.co/blog/nvidia-reachy-mini)
- [Reachy Mini Personal Assistant Repository](https://github.com/brevdev/reachy-personal-assistant)
- [NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit)
- [FastStream Documentation](https://faststream.airt.ai/)
- [NATS Documentation](https://docs.nats.io/)
- [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini)
- [Reachy Mini Conversation App](https://github.com/pollen-robotics/reachy_mini_conversation_app)

---

*Document prepared for GCSE English AI Tutor & Distributed Agent Orchestration Project*  
*January 2026*
