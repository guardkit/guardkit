"""
MCP Server for Agent Orchestration Messaging
=============================================

This MCP server provides a standardized interface for AI agents (including Claude)
to participate in the Ship's Computer orchestration system.

Features:
- Publish status updates to the message bus
- Request human approval for actions
- Receive and respond to commands
- Query system state (agent statuses, pending approvals)
- Subscribe to notifications

Usage:
    # Run as standalone MCP server
    python mcp_orchestration_server.py
    
    # Or with uvx
    uvx mcp run mcp_orchestration_server.py

Configuration:
    Set NATS_URL environment variable (default: nats://localhost:4222)
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)
from pydantic import BaseModel, Field
import nats
from nats.js.api import StreamConfig, RetentionPolicy


# =============================================================================
# Configuration
# =============================================================================

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
SERVER_NAME = "orchestration-mcp"
SERVER_VERSION = "1.0.0"


# =============================================================================
# Message Models (matching the schema from architecture doc)
# =============================================================================

class StatusPayload(BaseModel):
    state: str = Field(..., description="running | idle | awaiting_approval | error | paused")
    task_description: Optional[str] = None
    progress: Optional[dict] = None
    metrics: Optional[dict] = None

class ApprovalItem(BaseModel):
    id: str
    type: str
    content: dict

class ApprovalRequestPayload(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: str = Field(default="normal", description="high | normal | low")
    summary: str
    items: list[ApprovalItem]
    expires_at: Optional[str] = None
    context: Optional[dict] = None

class CommandPayload(BaseModel):
    command: str = Field(..., description="approve | reject | pause | resume | configure | terminate")
    source: str = Field(default="mcp-client")
    operator: Optional[str] = None
    parameters: Optional[dict] = None
    reason: Optional[str] = None

class ResultPayload(BaseModel):
    task_id: str
    status: str = Field(default="completed", description="completed | failed | partial")
    summary: str
    outputs: Optional[list] = None
    metrics: Optional[dict] = None
    next_steps: Optional[list] = None


# =============================================================================
# MCP Server Implementation
# =============================================================================

class OrchestrationMCPServer:
    """MCP Server that bridges Claude/agents to the NATS message bus."""
    
    def __init__(self):
        self.server = Server(SERVER_NAME)
        self.nc: Optional[nats.NATS] = None
        self.js = None  # JetStream context
        
        # Local state cache (updated via subscriptions)
        self.agent_states: dict[str, dict] = {}
        self.pending_approvals: list[dict] = []
        self.command_queue: dict[str, list] = {}  # agent_id -> commands
        
        # Set up handlers
        self._register_tools()
        self._register_resources()
    
    async def connect(self):
        """Connect to NATS server."""
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()
        
        # Ensure streams exist
        await self._setup_streams()
        
        # Start background subscriptions
        asyncio.create_task(self._subscribe_to_updates())
    
    async def disconnect(self):
        """Disconnect from NATS."""
        if self.nc:
            await self.nc.close()
    
    async def _setup_streams(self):
        """Ensure JetStream streams exist for persistence."""
        try:
            await self.js.add_stream(
                name="AGENTS",
                subjects=["agents.>"],
                retention=RetentionPolicy.LIMITS,
                max_age=86400 * 7,  # 7 days
            )
        except Exception:
            pass  # Stream may already exist
    
    async def _subscribe_to_updates(self):
        """Subscribe to agent updates to maintain local cache."""
        # Subscribe to status updates
        await self.nc.subscribe("agents.status.*", cb=self._handle_status)
        
        # Subscribe to approval requests
        await self.nc.subscribe("agents.approval.requests", cb=self._handle_approval)
        
        # Subscribe to approval responses (to clear pending)
        await self.nc.subscribe("agents.approval.responses", cb=self._handle_approval_response)
    
    async def _handle_status(self, msg):
        """Handle incoming status updates."""
        try:
            data = json.loads(msg.data.decode())
            agent_id = data.get("agent_id")
            if agent_id:
                self.agent_states[agent_id] = {
                    "payload": data.get("payload", {}),
                    "timestamp": data.get("timestamp"),
                }
        except Exception:
            pass
    
    async def _handle_approval(self, msg):
        """Handle incoming approval requests."""
        try:
            data = json.loads(msg.data.decode())
            self.pending_approvals.append(data)
        except Exception:
            pass
    
    async def _handle_approval_response(self, msg):
        """Handle approval responses to clear pending."""
        try:
            data = json.loads(msg.data.decode())
            request_id = data.get("payload", {}).get("parameters", {}).get("request_id")
            if request_id:
                self.pending_approvals = [
                    a for a in self.pending_approvals 
                    if a.get("payload", {}).get("request_id") != request_id
                ]
        except Exception:
            pass

    # =========================================================================
    # Tool Definitions
    # =========================================================================
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="publish_status",
                    description="Publish agent status update to the orchestration bus. Call this periodically to report your current state.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Unique identifier for this agent (e.g., 'research-agent-v1')"
                            },
                            "state": {
                                "type": "string",
                                "enum": ["running", "idle", "awaiting_approval", "error", "paused"],
                                "description": "Current agent state"
                            },
                            "task_description": {
                                "type": "string",
                                "description": "Human-readable description of current task"
                            },
                            "progress_percent": {
                                "type": "number",
                                "description": "Optional progress percentage (0-100)"
                            }
                        },
                        "required": ["agent_id", "state"]
                    }
                ),
                Tool(
                    name="request_approval",
                    description="Request human approval for one or more actions. Use this before taking any significant action that requires human oversight.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Your agent identifier"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Brief summary of what you're asking approval for"
                            },
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "type": {"type": "string"},
                                        "description": {"type": "string"},
                                        "content": {"type": "object"}
                                    },
                                    "required": ["id", "type", "description"]
                                },
                                "description": "List of items requiring approval"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "normal", "low"],
                                "default": "normal"
                            },
                            "expires_minutes": {
                                "type": "number",
                                "description": "Minutes until this request expires (default: 60)"
                            }
                        },
                        "required": ["agent_id", "summary", "items"]
                    }
                ),
                Tool(
                    name="check_commands",
                    description="Check for any commands directed at your agent. Call this periodically to receive instructions from the orchestrator or human operator.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Your agent identifier"
                            },
                            "wait_seconds": {
                                "type": "number",
                                "description": "Seconds to wait for a command (0 for immediate return, max 30)",
                                "default": 0
                            }
                        },
                        "required": ["agent_id"]
                    }
                ),
                Tool(
                    name="publish_result",
                    description="Publish the result of a completed task. Use this when you've finished a significant piece of work.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Your agent identifier"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Identifier for the completed task"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["completed", "failed", "partial"],
                                "default": "completed"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Summary of what was accomplished"
                            },
                            "outputs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"},
                                        "title": {"type": "string"},
                                        "location": {"type": "string"},
                                        "content": {"type": "string"}
                                    }
                                },
                                "description": "List of outputs produced"
                            }
                        },
                        "required": ["agent_id", "task_id", "summary"]
                    }
                ),
                Tool(
                    name="get_agent_statuses",
                    description="Get current status of all agents in the system, or a specific agent.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Optional: specific agent to query (omit for all agents)"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_pending_approvals",
                    description="Get all pending approval requests in the system. Useful for orchestrators or dashboards.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Optional: filter to specific agent's requests"
                            }
                        }
                    }
                ),
                Tool(
                    name="send_command",
                    description="Send a command to another agent. Use this for orchestration or responding to approval requests.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_agent_id": {
                                "type": "string",
                                "description": "Agent to send command to"
                            },
                            "command": {
                                "type": "string",
                                "enum": ["approve", "reject", "pause", "resume", "configure", "terminate"],
                                "description": "Command to send"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Command-specific parameters (e.g., request_id, approved_items for approve command)"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for the command"
                            }
                        },
                        "required": ["target_agent_id", "command"]
                    }
                ),
                Tool(
                    name="broadcast_message",
                    description="Broadcast a message to all agents or a specific topic.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Topic to broadcast to (e.g., 'system.announcements')"
                            },
                            "message": {
                                "type": "string",
                                "description": "Message content"
                            },
                            "data": {
                                "type": "object",
                                "description": "Optional structured data to include"
                            }
                        },
                        "required": ["topic", "message"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Execute a tool call."""
            
            if name == "publish_status":
                return await self._tool_publish_status(arguments)
            elif name == "request_approval":
                return await self._tool_request_approval(arguments)
            elif name == "check_commands":
                return await self._tool_check_commands(arguments)
            elif name == "publish_result":
                return await self._tool_publish_result(arguments)
            elif name == "get_agent_statuses":
                return await self._tool_get_agent_statuses(arguments)
            elif name == "get_pending_approvals":
                return await self._tool_get_pending_approvals(arguments)
            elif name == "send_command":
                return await self._tool_send_command(arguments)
            elif name == "broadcast_message":
                return await self._tool_broadcast_message(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # =========================================================================
    # Tool Implementations
    # =========================================================================
    
    async def _tool_publish_status(self, args: dict) -> list[TextContent]:
        """Publish status update."""
        agent_id = args["agent_id"]
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": agent_id,
            "event_type": "status",
            "payload": {
                "state": args["state"],
                "task_description": args.get("task_description"),
                "progress": {"percentage": args.get("progress_percent")} if args.get("progress_percent") else None,
                "last_activity": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        await self.nc.publish(
            f"agents.status.{agent_id}",
            json.dumps(message).encode()
        )
        
        # Also publish to aggregated topic
        await self.nc.publish(
            "agents.status.all",
            json.dumps(message).encode()
        )
        
        return [TextContent(
            type="text",
            text=f"Status published: {agent_id} is now {args['state']}"
        )]
    
    async def _tool_request_approval(self, args: dict) -> list[TextContent]:
        """Request human approval."""
        agent_id = args["agent_id"]
        request_id = str(uuid.uuid4())
        
        expires_minutes = args.get("expires_minutes", 60)
        expires_at = (datetime.utcnow() + timedelta(minutes=expires_minutes)).isoformat() + "Z"
        
        # Convert items to proper format
        items = []
        for item in args["items"]:
            items.append({
                "id": item.get("id", str(uuid.uuid4())),
                "type": item["type"],
                "content": {
                    "description": item.get("description", ""),
                    **item.get("content", {})
                }
            })
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": agent_id,
            "event_type": "approval_request",
            "payload": {
                "request_id": request_id,
                "priority": args.get("priority", "normal"),
                "expires_at": expires_at,
                "summary": args["summary"],
                "items": items
            }
        }
        
        await self.nc.publish(
            "agents.approval.requests",
            json.dumps(message).encode()
        )
        
        # Update own status
        await self._tool_publish_status({
            "agent_id": agent_id,
            "state": "awaiting_approval",
            "task_description": f"Awaiting approval: {args['summary']}"
        })
        
        return [TextContent(
            type="text",
            text=f"Approval requested (ID: {request_id}). {len(items)} item(s) pending human review. Expires in {expires_minutes} minutes."
        )]
    
    async def _tool_check_commands(self, args: dict) -> list[TextContent]:
        """Check for pending commands."""
        agent_id = args["agent_id"]
        wait_seconds = min(args.get("wait_seconds", 0), 30)
        
        # Set up a temporary subscription for this agent's commands
        commands_received = []
        
        async def command_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                commands_received.append(data)
            except Exception:
                pass
        
        sub = await self.nc.subscribe(
            f"agents.commands.{agent_id}",
            cb=command_handler
        )
        
        # Wait for commands (or timeout)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        else:
            await asyncio.sleep(0.1)  # Brief pause to receive any pending
        
        await sub.unsubscribe()
        
        if commands_received:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "commands_received": len(commands_received),
                    "commands": commands_received
                }, indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text="No commands pending."
            )]
    
    async def _tool_publish_result(self, args: dict) -> list[TextContent]:
        """Publish task result."""
        agent_id = args["agent_id"]
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": agent_id,
            "event_type": "result",
            "payload": {
                "task_id": args["task_id"],
                "status": args.get("status", "completed"),
                "summary": args["summary"],
                "outputs": args.get("outputs", []),
                "metrics": {
                    "completed_at": datetime.utcnow().isoformat() + "Z"
                }
            }
        }
        
        await self.nc.publish(
            f"agents.results.{agent_id}",
            json.dumps(message).encode()
        )
        
        # Update status to idle
        await self._tool_publish_status({
            "agent_id": agent_id,
            "state": "idle",
            "task_description": f"Completed: {args['summary']}"
        })
        
        return [TextContent(
            type="text",
            text=f"Result published for task {args['task_id']}: {args.get('status', 'completed')}"
        )]
    
    async def _tool_get_agent_statuses(self, args: dict) -> list[TextContent]:
        """Get agent statuses from cache."""
        agent_id = args.get("agent_id")
        
        if agent_id:
            if agent_id in self.agent_states:
                return [TextContent(
                    type="text",
                    text=json.dumps({agent_id: self.agent_states[agent_id]}, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"No status found for agent: {agent_id}"
                )]
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "agent_count": len(self.agent_states),
                    "agents": self.agent_states
                }, indent=2)
            )]
    
    async def _tool_get_pending_approvals(self, args: dict) -> list[TextContent]:
        """Get pending approval requests."""
        agent_id = args.get("agent_id")
        
        if agent_id:
            filtered = [a for a in self.pending_approvals if a.get("agent_id") == agent_id]
        else:
            filtered = self.pending_approvals
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "pending_count": len(filtered),
                "approvals": filtered
            }, indent=2)
        )]
    
    async def _tool_send_command(self, args: dict) -> list[TextContent]:
        """Send command to another agent."""
        target_agent_id = args["target_agent_id"]
        
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "agent_id": target_agent_id,
            "event_type": "command",
            "payload": {
                "command": args["command"],
                "source": "mcp-client",
                "parameters": args.get("parameters", {}),
                "reason": args.get("reason")
            }
        }
        
        await self.nc.publish(
            f"agents.commands.{target_agent_id}",
            json.dumps(message).encode()
        )
        
        # If this is an approval response, also publish to approval responses topic
        if args["command"] in ["approve", "reject"]:
            await self.nc.publish(
                "agents.approval.responses",
                json.dumps(message).encode()
            )
        
        return [TextContent(
            type="text",
            text=f"Command '{args['command']}' sent to {target_agent_id}"
        )]
    
    async def _tool_broadcast_message(self, args: dict) -> list[TextContent]:
        """Broadcast message to topic."""
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "event_type": "broadcast",
            "payload": {
                "message": args["message"],
                "data": args.get("data", {})
            }
        }
        
        await self.nc.publish(
            args["topic"],
            json.dumps(message).encode()
        )
        
        return [TextContent(
            type="text",
            text=f"Broadcast sent to {args['topic']}"
        )]

    # =========================================================================
    # Resource Definitions
    # =========================================================================
    
    def _register_resources(self):
        """Register MCP resources for reading state."""
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            resources = [
                Resource(
                    uri="orchestration://system/status",
                    name="System Status",
                    description="Overview of all agents and system health",
                    mimeType="application/json"
                ),
                Resource(
                    uri="orchestration://approvals/pending",
                    name="Pending Approvals",
                    description="All approval requests awaiting human review",
                    mimeType="application/json"
                ),
            ]
            
            # Add dynamic resources for each known agent
            for agent_id in self.agent_states.keys():
                resources.append(Resource(
                    uri=f"orchestration://agents/{agent_id}",
                    name=f"Agent: {agent_id}",
                    description=f"Current status and details for {agent_id}",
                    mimeType="application/json"
                ))
            
            return resources
        
        @self.server.list_resource_templates()
        async def list_resource_templates() -> list[ResourceTemplate]:
            return [
                ResourceTemplate(
                    uriTemplate="orchestration://agents/{agent_id}",
                    name="Agent Status",
                    description="Get status for a specific agent"
                ),
                ResourceTemplate(
                    uriTemplate="orchestration://agents/{agent_id}/history",
                    name="Agent History",
                    description="Get recent activity history for an agent"
                ),
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            if uri == "orchestration://system/status":
                return json.dumps({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "agents": self.agent_states,
                    "pending_approvals": len(self.pending_approvals),
                    "nats_connected": self.nc is not None and self.nc.is_connected
                }, indent=2)
            
            elif uri == "orchestration://approvals/pending":
                return json.dumps({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "count": len(self.pending_approvals),
                    "approvals": self.pending_approvals
                }, indent=2)
            
            elif uri.startswith("orchestration://agents/"):
                agent_id = uri.split("/")[-1]
                if agent_id in self.agent_states:
                    return json.dumps(self.agent_states[agent_id], indent=2)
                else:
                    return json.dumps({"error": f"Agent {agent_id} not found"})
            
            return json.dumps({"error": "Unknown resource"})

    # =========================================================================
    # Server Lifecycle
    # =========================================================================
    
    async def run(self):
        """Run the MCP server."""
        await self.connect()
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.disconnect()


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    server = OrchestrationMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
