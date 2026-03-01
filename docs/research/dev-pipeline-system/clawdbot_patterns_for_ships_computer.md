# Clawdbot Patterns for Ship's Computer

## Lessons from the Viral Open-Source Personal AI Assistant

**Date:** January 2026  
**Purpose:** Extract actionable patterns from Clawdbot's architecture for Ship's Computer implementation  
**Related:** distributed_agent_orchestration_architecture.md

---

## Executive Summary

Clawdbot has achieved remarkable viral adoption (18.5K+ GitHub stars in ~3 weeks) by solving many of the same problems Ship's Computer aims to address: persistent AI assistants, multi-channel communication, extensibility, and human-in-the-loop safety. While the projects have different architectures (Clawdbot's gateway-centric vs Ship's Computer's distributed NATS pub/sub), several Clawdbot patterns are directly applicable and battle-tested by a rapidly growing community.

This document extracts the most valuable patterns for Ship's Computer, with implementation guidance tailored to our Python/NATS architecture.

---

## Pattern 1: Skills Architecture (SKILL.md + Registry)

### What Clawdbot Does

Clawdbot uses a simple, elegant skills system:

- **SKILL.md files**: Plain markdown files that describe capabilities, with optional supporting code
- **Three skill tiers**: Bundled (ships with Clawdbot), Managed (from ClawdHub registry), Workspace (user-created)
- **Install gating**: Skills can declare requirements (env vars, config, permissions)
- **Self-discovery**: The assistant can search ClawdHub and install skills during conversation
- **Self-authoring**: The assistant can write and install its own skills

### Example SKILL.md Structure

```markdown
---
name: whoop-fitness
description: Fetch WHOOP fitness data and provide health insights
metadata:
  clawdbot:
    config:
      requiredEnv: ["WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET"]
      stateDirs: [".config/whoop"]
    cliHelp: "whoop --help\nUsage: whoop [command]\n..."
---

# WHOOP Fitness Skill

## Capabilities
- Fetch daily recovery scores
- Get sleep performance data
- Track strain and HRV trends

## Usage
Ask me about your WHOOP data:
- "How did I sleep last night?"
- "What's my recovery score?"
- "Show my HRV trend this week"

## Implementation
[Code or CLI wrapper details...]
```

### Why This Matters for Ship's Computer

Ship's Computer agents need extensible capabilities without rebuilding the core system. A skills-like pattern enables:

1. **Community contributions**: Others can create and share agent capabilities
2. **Domain specialisation**: GCSE Tutor skills, social media skills, research skills
3. **Runtime extension**: Add capabilities without restarting the orchestration layer
4. **Self-improvement**: Agents can request or create new skills as needed

### Implementation for Ship's Computer

**Proposed AGENT_SKILL.md Format:**

```markdown
---
name: twitter-engagement
version: 1.0.0
agent_types: [engagement, social]
description: Monitor Twitter for relevant content and draft responses
author: rich
metadata:
  ships_computer:
    requires:
      env: ["TWITTER_API_KEY", "TWITTER_API_SECRET"]
      tools: ["web_search", "llm_inference"]
    message_topics:
      subscribes: ["agents.commands.twitter-*", "system.config"]
      publishes: ["agents.status.*", "agents.approval.requests", "agents.results.*"]
    approval_required: true
---

# Twitter Engagement Skill

## Purpose
Monitors Twitter for content matching configured topics and generates
engagement opportunities for human approval.

## Behaviour
1. Periodically searches Twitter for configured keywords
2. Filters results by toxicity score and relevance
3. Generates draft responses using local LLM
4. Publishes approval requests to message bus
5. Executes approved engagements

## Configuration
```yaml
topics:
  - "Claude MCP"
  - "agentic AI"
  - "LangChain"
toxicity_threshold: 0.3
search_interval_minutes: 30
```

## NATS Message Examples
[Include sample message schemas for this skill...]
```

**Registry Structure:**

```
/skills
├── registry.json           # Index of all available skills
├── bundled/               # Ships with Ship's Computer
│   ├── status-reporter/
│   └── health-check/
├── managed/               # From central registry
│   ├── twitter-engagement/
│   └── research-agent/
└── workspace/             # User-created
    └── gcse-tutor/
```

**Python Skill Loader:**

```python
from pathlib import Path
import yaml
import frontmatter

class SkillRegistry:
    def __init__(self, skills_path: Path):
        self.skills_path = skills_path
        self.loaded_skills = {}
    
    def discover_skills(self) -> list[dict]:
        """Scan all skill directories and parse AGENT_SKILL.md files."""
        skills = []
        for skill_dir in self.skills_path.glob("**/AGENT_SKILL.md"):
            skill = frontmatter.load(skill_dir)
            skills.append({
                "name": skill.metadata.get("name"),
                "path": skill_dir.parent,
                "metadata": skill.metadata,
                "content": skill.content
            })
        return skills
    
    def validate_requirements(self, skill: dict) -> tuple[bool, list[str]]:
        """Check if skill requirements are satisfied."""
        missing = []
        reqs = skill["metadata"].get("ships_computer", {}).get("requires", {})
        
        for env_var in reqs.get("env", []):
            if not os.getenv(env_var):
                missing.append(f"Missing env: {env_var}")
        
        return len(missing) == 0, missing
    
    def install_skill(self, skill_name: str, source: str = "managed"):
        """Install a skill from registry."""
        # Fetch from registry, validate, install
        pass
```

---

## Pattern 2: Heartbeats & Proactive Behaviour

### What Clawdbot Does

Clawdbot implements "heartbeats" - periodic check-ins where the assistant proactively reaches out:

- **Scheduled heartbeats**: Configurable intervals (e.g., every few hours)
- **Context-aware**: Reviews recent activity, pending tasks, system state
- **Proactive suggestions**: Offers help based on observed patterns
- **Background monitoring**: Can watch for conditions and alert when triggered

User testimonials highlight this as a standout feature:
> "Apparently @clawdbot checks in during heartbeats!? A kinda awesome surprise! Love the proactive reaching out." - @HixVAC

### Why This Matters for Ship's Computer

Ship's Computer with Reachy Mini needs to feel like an active participant, not just a passive responder. Heartbeats enable:

1. **Ambient awareness**: Reachy can proactively notify about completed tasks, pending approvals
2. **Continuity**: The system feels "alive" even when not directly addressed
3. **Anticipation**: Can prepare summaries, suggestions before being asked
4. **Monitoring**: Background agents can surface important changes

### Implementation for Ship's Computer

**Heartbeat Service:**

```python
import asyncio
from datetime import datetime, timedelta
from faststream.nats import NatsBroker

class HeartbeatService:
    def __init__(self, broker: NatsBroker, config: dict):
        self.broker = broker
        self.interval = config.get("heartbeat_interval_minutes", 60)
        self.quiet_hours = config.get("quiet_hours", {"start": 22, "end": 7})
        self.last_heartbeat = None
        
    async def start(self):
        """Begin heartbeat loop."""
        while True:
            if self._should_heartbeat():
                await self._perform_heartbeat()
            await asyncio.sleep(60)  # Check every minute
    
    def _should_heartbeat(self) -> bool:
        """Determine if we should send a heartbeat now."""
        now = datetime.now()
        
        # Respect quiet hours
        hour = now.hour
        if self.quiet_hours["start"] <= hour or hour < self.quiet_hours["end"]:
            return False
        
        # Check interval
        if self.last_heartbeat:
            elapsed = now - self.last_heartbeat
            if elapsed < timedelta(minutes=self.interval):
                return False
        
        return True
    
    async def _perform_heartbeat(self):
        """Execute heartbeat check and potentially notify user."""
        self.last_heartbeat = datetime.now()
        
        # Gather system state
        context = await self._gather_context()
        
        # Determine if there's anything worth mentioning
        notification = await self._evaluate_for_notification(context)
        
        if notification:
            await self.broker.publish(
                {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "notification": notification,
                    "context": context
                },
                "system.heartbeat"
            )
    
    async def _gather_context(self) -> dict:
        """Collect current system state for heartbeat evaluation."""
        return {
            "pending_approvals": await self._get_pending_approvals(),
            "recent_completions": await self._get_recent_completions(),
            "agent_states": await self._get_agent_states(),
            "error_count": await self._get_recent_errors()
        }
    
    async def _evaluate_for_notification(self, context: dict) -> str | None:
        """Use LLM to determine if context warrants proactive notification."""
        # Only notify if there's something meaningful
        if context["pending_approvals"]:
            return f"You have {len(context['pending_approvals'])} pending approvals."
        
        if context["error_count"] > 0:
            return f"Heads up: {context['error_count']} agent errors in the last hour."
        
        if context["recent_completions"]:
            # Summarise completed work
            return self._summarise_completions(context["recent_completions"])
        
        return None
```

**Reachy Integration:**

```python
@broker.subscriber("system.heartbeat")
async def handle_heartbeat(msg):
    """React to heartbeat notifications via Reachy."""
    notification = msg.body.get("notification")
    
    if notification:
        # Gentle attention animation
        await reachy.animate_attention_soft()
        
        # Optional audio cue (configurable)
        if config.get("heartbeat_sound_enabled"):
            await play_soft_chime()
        
        # If user is detected (via camera), speak
        if await reachy.detect_user_present():
            await reachy.speak(notification)
```

---

## Pattern 3: Self-Extension & Skill Authoring

### What Clawdbot Does

One of Clawdbot's most powerful features is self-modification:

- **Skill authoring during conversation**: Users can ask Clawdbot to create new skills
- **Hot-reload**: New skills are loaded without restarting
- **Prompt self-editing**: Can modify its own system prompt
- **Tool chaining**: Combines existing tools in unexpected ways to solve problems

User examples:
> "It's the fact that clawd can just keep building upon itself just by talking to it in discord is crazy." - @jonahships_
> "I asked it to take picture of the sky whenever it's pretty. It designed a skill and took a pic!" - @signalgaining
> "Wanted a way for it to have access to my courses/assignments at uni. Asked it to build a skill - it did and started using it on its own." - @pranavkarthik__

### Why This Matters for Ship's Computer

Self-extension enables:

1. **Rapid iteration**: New capabilities without developer intervention
2. **Personalisation**: System adapts to user's specific needs
3. **Problem-solving**: Agents can create tools to overcome obstacles
4. **Reduced friction**: No need to wait for "official" skill implementations

### Implementation for Ship's Computer

**Skill Authoring Agent:**

```python
class SkillAuthorAgent:
    """Agent that can create new skills on demand."""
    
    SKILL_TEMPLATE = '''---
name: {name}
version: 1.0.0
description: {description}
author: auto-generated
metadata:
  ships_computer:
    requires:
      env: {env_vars}
      tools: {tools}
    approval_required: {approval_required}
---

# {title}

## Purpose
{purpose}

## Implementation

```python
{implementation}
```
'''
    
    async def create_skill(
        self,
        user_request: str,
        available_tools: list[str]
    ) -> dict:
        """Generate a new skill based on user request."""
        
        # Use LLM to design the skill
        design_prompt = f"""
        User wants a new skill: "{user_request}"
        
        Available tools: {available_tools}
        
        Design a skill that accomplishes this. Output:
        1. Skill name (snake_case)
        2. Description (one line)
        3. Required environment variables (if any)
        4. Required tools from available list
        5. Whether human approval should be required
        6. Python implementation
        
        Format as JSON.
        """
        
        design = await self.llm.generate(design_prompt)
        
        # Generate AGENT_SKILL.md
        skill_content = self.SKILL_TEMPLATE.format(
            name=design["name"],
            description=design["description"],
            env_vars=design.get("env_vars", []),
            tools=design.get("tools", []),
            approval_required=design.get("approval_required", True),
            title=design["name"].replace("_", " ").title(),
            purpose=design["description"],
            implementation=design["implementation"]
        )
        
        return {
            "name": design["name"],
            "content": skill_content,
            "path": f"workspace/{design['name']}"
        }
    
    async def install_authored_skill(self, skill: dict) -> bool:
        """Install a newly authored skill with safety checks."""
        
        # Validate the generated code
        validation = await self._validate_skill_code(skill)
        if not validation["safe"]:
            return False, validation["issues"]
        
        # Write to workspace directory
        skill_path = Path(self.skills_dir) / skill["path"]
        skill_path.mkdir(parents=True, exist_ok=True)
        
        (skill_path / "AGENT_SKILL.md").write_text(skill["content"])
        
        # Hot-reload into registry
        await self.skill_registry.reload()
        
        return True, None
    
    async def _validate_skill_code(self, skill: dict) -> dict:
        """Safety validation for auto-generated skill code."""
        issues = []
        
        # Check for dangerous patterns
        dangerous_patterns = [
            "subprocess.call",
            "os.system",
            "eval(",
            "exec(",
            "__import__",
            "open(",  # File access needs approval
        ]
        
        code = skill["content"]
        for pattern in dangerous_patterns:
            if pattern in code:
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues
        }
```

**Conversation Flow Example:**

```
User: "I need a skill that checks my local git repos for uncommitted changes every morning"

Reachy: "I can create that for you. The skill will:
- Scan directories you specify for git repositories
- Check each for uncommitted changes or unpushed commits  
- Send you a morning summary

Should I require your approval before it sends notifications, or can it notify automatically?"

User: "Automatic is fine for notifications"

Reachy: "Creating the skill now..."

[Agent authors AGENT_SKILL.md + implementation]
[Validates code safety]
[Installs to workspace/git_repo_checker/]

Reachy: "Done! I've created the git-repo-checker skill. It will run at 8am daily. 
You can configure which directories to scan by saying 'configure git checker'."
```

---

## Pattern 4: Session Persistence & Recovery

### What Clawdbot Does

Clawdbot maintains persistent sessions that survive crashes and restarts:

- **State serialisation**: Conversation context, memory, pending tasks stored to disk
- **Graceful recovery**: On restart, sessions resume where they left off
- **Per-sender isolation**: Each user/channel gets isolated session state
- **Pruning policies**: Old sessions are cleaned up to manage storage

### Why This Matters for Ship's Computer

Distributed agents need resilience:

1. **Crash recovery**: Agent restarts shouldn't lose work in progress
2. **Context continuity**: Users shouldn't need to re-explain context
3. **Task durability**: Long-running tasks survive infrastructure changes
4. **Audit trail**: Session history for debugging and compliance

### Implementation for Ship's Computer

**Session State Manager:**

```python
import json
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles

class SessionManager:
    def __init__(self, state_dir: Path, retention_days: int = 30):
        self.state_dir = state_dir
        self.retention_days = retention_days
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_session(self, session_id: str, state: dict):
        """Persist session state to disk."""
        session_file = self.state_dir / f"{session_id}.json"
        
        state["_meta"] = {
            "saved_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        async with aiofiles.open(session_file, "w") as f:
            await f.write(json.dumps(state, indent=2, default=str))
    
    async def load_session(self, session_id: str) -> dict | None:
        """Restore session state from disk."""
        session_file = self.state_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        async with aiofiles.open(session_file, "r") as f:
            content = await f.read()
            return json.loads(content)
    
    async def recover_agent_state(self, agent_id: str) -> dict:
        """Recover full agent state after crash/restart."""
        state = await self.load_session(agent_id)
        
        if state is None:
            return {"status": "fresh_start", "state": {}}
        
        # Check if state is stale
        saved_at = datetime.fromisoformat(state["_meta"]["saved_at"])
        if datetime.utcnow() - saved_at > timedelta(hours=24):
            return {
                "status": "stale_recovery",
                "state": state,
                "stale_hours": (datetime.utcnow() - saved_at).total_seconds() / 3600
            }
        
        return {"status": "recovered", "state": state}
    
    async def checkpoint(self, agent_id: str, state: dict):
        """Create a checkpoint (called periodically during operation)."""
        await self.save_session(agent_id, state)
    
    async def prune_old_sessions(self):
        """Clean up sessions older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        
        for session_file in self.state_dir.glob("*.json"):
            try:
                async with aiofiles.open(session_file, "r") as f:
                    content = await f.read()
                    state = json.loads(content)
                
                saved_at = datetime.fromisoformat(state["_meta"]["saved_at"])
                if saved_at < cutoff:
                    session_file.unlink()
            except Exception:
                pass  # Skip malformed files
```

**Agent Integration:**

```python
class ResilientAgent(BaseAgent):
    """Agent with built-in session persistence."""
    
    def __init__(self, config: AgentConfig, session_manager: SessionManager):
        super().__init__(config)
        self.session_manager = session_manager
        self.checkpoint_interval = 60  # seconds
        self._state = {}
    
    async def start(self):
        """Start agent with state recovery."""
        recovery = await self.session_manager.recover_agent_state(
            self.config.agent_id
        )
        
        if recovery["status"] == "recovered":
            self._state = recovery["state"]
            await self._resume_pending_work()
        elif recovery["status"] == "stale_recovery":
            # Notify about stale state
            self._state = recovery["state"]
            await self._handle_stale_recovery(recovery["stale_hours"])
        
        # Start checkpoint loop
        asyncio.create_task(self._checkpoint_loop())
        
        await super().start()
    
    async def _checkpoint_loop(self):
        """Periodically save state."""
        while True:
            await asyncio.sleep(self.checkpoint_interval)
            await self.session_manager.checkpoint(
                self.config.agent_id,
                self._state
            )
    
    async def _resume_pending_work(self):
        """Resume any work that was in progress before crash."""
        pending = self._state.get("pending_tasks", [])
        for task in pending:
            if task["status"] == "in_progress":
                await self._resume_task(task)
```

---

## Pattern 5: Approval Workflows with Context

### What Clawdbot Does

Clawdbot implements sophisticated approval gates:

- **Granular permissions**: Different actions require different approval levels
- **Context preservation**: Approval requests include full context for decision-making
- **Batch operations**: Can approve/reject multiple items at once
- **Modification during approval**: Can edit proposed actions before approving
- **Timeout handling**: Pending approvals can expire

### Why This Matters for Ship's Computer

Ship's Computer's human-in-the-loop design requires robust approval flows:

1. **Safety**: Prevent agents from taking harmful actions autonomously
2. **Trust building**: Users gain confidence by reviewing before execution
3. **Flexibility**: Different contexts need different approval thresholds
4. **Efficiency**: Batch approvals for high-volume operations

### Implementation for Ship's Computer

This aligns well with the existing approval flow in the architecture doc, but Clawdbot adds some refinements:

**Enhanced Approval Request:**

```python
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel

class ApprovalLevel(Enum):
    AUTO = "auto"           # No approval needed
    NOTIFY = "notify"       # Notify user, proceed automatically
    APPROVE = "approve"     # Require explicit approval
    ELEVATED = "elevated"   # Require approval + confirmation

class ApprovalItem(BaseModel):
    id: str
    type: str
    summary: str
    details: dict
    proposed_action: str
    modifiable_fields: list[str] = []  # Fields user can edit
    risk_score: float = 0.0  # 0-1, higher = riskier

class ApprovalRequest(BaseModel):
    request_id: str
    agent_id: str
    level: ApprovalLevel
    summary: str
    items: list[ApprovalItem]
    context: dict  # Full context for decision-making
    expires_at: datetime
    batch_allowed: bool = True  # Can approve all at once
    
    @classmethod
    def create(
        cls,
        agent_id: str,
        summary: str,
        items: list[ApprovalItem],
        context: dict,
        ttl_minutes: int = 60
    ):
        # Auto-determine approval level based on risk
        max_risk = max(item.risk_score for item in items) if items else 0
        
        if max_risk < 0.2:
            level = ApprovalLevel.NOTIFY
        elif max_risk < 0.6:
            level = ApprovalLevel.APPROVE
        else:
            level = ApprovalLevel.ELEVATED
        
        return cls(
            request_id=str(uuid.uuid4()),
            agent_id=agent_id,
            level=level,
            summary=summary,
            items=items,
            context=context,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes)
        )

class ApprovalResponse(BaseModel):
    request_id: str
    approved_items: list[str]
    rejected_items: list[str]
    modifications: dict[str, dict]  # item_id -> field modifications
    approved_by: str
    approved_at: datetime
```

**Reachy Approval Interface:**

```python
class ReachyApprovalHandler:
    """Handle approval requests via Reachy voice/visual interface."""
    
    async def present_approval(self, request: ApprovalRequest):
        """Present approval request to user via Reachy."""
        
        # Visual indicator
        await self.reachy.animate_attention()
        
        # Summarise the request
        if len(request.items) == 1:
            speech = f"{request.agent_id} wants to {request.items[0].summary}. "
        else:
            speech = f"{request.agent_id} has {len(request.items)} items for approval. {request.summary}. "
        
        # Add risk context
        if request.level == ApprovalLevel.ELEVATED:
            speech += "This is a high-risk action requiring confirmation. "
        
        speech += "Would you like to approve, reject, or hear more details?"
        
        await self.reachy.speak(speech)
        
        # Listen for response
        response = await self.reachy.listen_for_response(
            timeout=30,
            expected_intents=["approve", "reject", "details", "skip"]
        )
        
        return await self._process_response(request, response)
    
    async def _process_response(
        self,
        request: ApprovalRequest,
        user_response: dict
    ) -> ApprovalResponse:
        """Process user's spoken response."""
        
        intent = user_response.get("intent")
        
        if intent == "approve":
            # Check for modifications in speech
            modifications = self._extract_modifications(user_response)
            
            return ApprovalResponse(
                request_id=request.request_id,
                approved_items=[item.id for item in request.items],
                rejected_items=[],
                modifications=modifications,
                approved_by="reachy-voice",
                approved_at=datetime.utcnow()
            )
        
        elif intent == "details":
            # Provide more context, then re-ask
            await self._speak_details(request)
            return await self.present_approval(request)
        
        elif intent == "reject":
            return ApprovalResponse(
                request_id=request.request_id,
                approved_items=[],
                rejected_items=[item.id for item in request.items],
                modifications={},
                approved_by="reachy-voice",
                approved_at=datetime.utcnow()
            )
        
        else:  # skip
            return None  # Leave pending
```

---

## Pattern 6: Multi-Agent Routing

### What Clawdbot Does

Clawdbot can route different channels/accounts to isolated agent workspaces:

- **Channel-based routing**: WhatsApp goes to one agent, Discord to another
- **Account-based routing**: Different users get different agent configurations
- **Workspace isolation**: Each agent has its own session, memory, permissions
- **Shared tools**: Common tools available across workspaces

### Why This Matters for Ship's Computer

Ship's Computer explicitly supports multiple agents with different roles:

- Twitter engagement agent
- LinkedIn agent
- Research agent
- GCSE Tutor agent

Routing ensures the right agent handles the right requests.

### Implementation for Ship's Computer

**Agent Router:**

```python
from dataclasses import dataclass
from typing import Callable, Awaitable

@dataclass
class RoutingRule:
    name: str
    condition: Callable[[dict], bool]
    agent_id: str
    priority: int = 0

class AgentRouter:
    def __init__(self):
        self.rules: list[RoutingRule] = []
        self.default_agent: str = "orchestrator"
    
    def add_rule(self, rule: RoutingRule):
        """Add a routing rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def route(self, message: dict) -> str:
        """Determine which agent should handle a message."""
        for rule in self.rules:
            if rule.condition(message):
                return rule.agent_id
        return self.default_agent
    
    @classmethod
    def from_config(cls, config: dict) -> "AgentRouter":
        """Build router from configuration."""
        router = cls()
        
        for rule_config in config.get("routing_rules", []):
            rule = RoutingRule(
                name=rule_config["name"],
                condition=cls._build_condition(rule_config["condition"]),
                agent_id=rule_config["agent_id"],
                priority=rule_config.get("priority", 0)
            )
            router.add_rule(rule)
        
        router.default_agent = config.get("default_agent", "orchestrator")
        return router
    
    @staticmethod
    def _build_condition(condition_config: dict) -> Callable[[dict], bool]:
        """Build a condition function from config."""
        cond_type = condition_config["type"]
        
        if cond_type == "source_channel":
            channels = condition_config["channels"]
            return lambda msg: msg.get("source_channel") in channels
        
        elif cond_type == "keyword":
            keywords = condition_config["keywords"]
            return lambda msg: any(kw in msg.get("content", "").lower() for kw in keywords)
        
        elif cond_type == "intent":
            intents = condition_config["intents"]
            return lambda msg: msg.get("detected_intent") in intents
        
        else:
            return lambda msg: False
```

**Configuration Example:**

```yaml
routing:
  default_agent: reachy-orchestrator
  
  rules:
    - name: gcse-tutor-activation
      condition:
        type: keyword
        keywords: ["study", "gcse", "english", "macbeth", "essay"]
      agent_id: gcse-tutor-v1
      priority: 10
    
    - name: twitter-mentions
      condition:
        type: source_channel
        channels: ["twitter-dm", "twitter-mention"]
      agent_id: twitter-engagement-v1
      priority: 5
    
    - name: research-requests
      condition:
        type: intent
        intents: ["research", "compare", "analyse", "investigate"]
      agent_id: research-agent-v1
      priority: 5
```

---

## Patterns to Avoid

### Gateway-Centric Architecture

Clawdbot's single-gateway model works for personal assistants but doesn't scale for distributed multi-agent systems:

- **Single point of failure**: Gateway crash affects all channels
- **Scalability limits**: All traffic through one process
- **Deployment constraints**: Can't distribute agents across infrastructure

**Ship's Computer approach**: NATS pub/sub allows truly distributed agents that can run anywhere and communicate asynchronously.

### Chat-First Interface

Clawdbot assumes users interact via messaging apps. Ship's Computer needs:

- **Voice interface**: Reachy Mini as primary interaction point
- **Programmatic interface**: Cloud agents communicating via message bus
- **Dashboard**: Visual monitoring and control

### TypeScript/Node Stack

Clawdbot is TypeScript/Node. Ship's Computer is Python-based for:

- ML/AI ecosystem compatibility (PyTorch, Transformers, etc.)
- NVIDIA tooling (NeMo, TensorRT)
- Existing agent framework familiarity (FastStream, LangChain)

---

## Integration Possibilities

Despite architectural differences, Clawdbot and Ship's Computer could potentially integrate:

1. **Clawdbot as a channel**: Ship's Computer agents could expose capabilities as Clawdbot skills
2. **Shared skill format**: Adopt compatible SKILL.md format for community cross-pollination
3. **MCP bridge**: Both use MCP - could share MCP server implementations
4. **ClawdHub integration**: Ship's Computer skills could be published to ClawdHub for broader reach

---

## Implementation Roadmap

### Phase 1: Skills Foundation (Week 1-2)
- [ ] Define AGENT_SKILL.md format
- [ ] Implement SkillRegistry class
- [ ] Create skill validation and loading
- [ ] Add hot-reload capability

### Phase 2: Persistence & Recovery (Week 2-3)
- [ ] Implement SessionManager
- [ ] Add checkpoint loops to base agent
- [ ] Test crash recovery scenarios
- [ ] Add session pruning

### Phase 3: Heartbeats (Week 3-4)
- [ ] Implement HeartbeatService
- [ ] Integrate with Reachy orchestrator
- [ ] Add quiet hours and user preference config
- [ ] Test proactive notification flows

### Phase 4: Self-Extension (Week 4-5)
- [ ] Implement SkillAuthorAgent
- [ ] Add code safety validation
- [ ] Test skill authoring conversation flows
- [ ] Document skill authoring capabilities

### Phase 5: Enhanced Approvals (Week 5-6)
- [ ] Implement risk-based approval levels
- [ ] Add modification during approval
- [ ] Enhance Reachy approval interface
- [ ] Add batch approval support

---

## References

- [Clawdbot GitHub](https://github.com/clawdbot/clawdbot) - 18.5K+ stars
- [Clawdbot Documentation](https://docs.clawd.bot)
- [ClawdHub Skill Registry](https://clawdhub.com)
- [Awesome Clawdbot Skills](https://github.com/VoltAgent/awesome-clawdbot-skills)
- [Lobster Workflow Engine](https://github.com/clawdbot/lobster)

---

*Document prepared for Ship's Computer project*  
*January 2026*
