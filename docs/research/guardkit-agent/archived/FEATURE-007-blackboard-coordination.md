# Feature 7: Blackboard Coordination Infrastructure

> **Feature ID**: FEATURE-007
> **Priority**: P0 (Critical for debugging and observability)
> **Estimated Effort**: 2-3 days
> **Dependencies**: FEATURE-002 (Agent SDK Infrastructure)
> **Inspired By**: claude-flow's coordination patterns (10.6k ⭐)

---

## Summary

Implement a blackboard-based coordination system where Player and Coach agents communicate through shared state rather than direct message passing. This provides observability, debuggability, and resume capability that's essential for the hybrid Claude Code + Python architecture.

---

## Why Blackboard Pattern?

### The Problem We're Solving

From our testing strategy discussion, bugs in hybrid architectures live at **integration seams**:

```
Slash Command → Claude Code (black box) → Agent Selection → Agent Instructions → Python call?
                    ↑                         ↑                    ↑
              Integration seam          Integration seam    Integration seam
```

When something breaks, we need to answer:
- What did the Player actually report?
- What did the Coach actually see?
- What feedback was actually passed back?

**Direct state passing makes this invisible.** With blackboard, everything is observable.

### Claude-Flow's Proven Architecture

```
Claude Code ──(MCP)──> Orchestration
     |                      |
     v                      v
 pre/post hooks      memory.db (SQLite)
                        ├─ shared_state  (blackboard)
                        ├─ events        (audit trail)
                        ├─ consensus     (approval gates)
                        └─ checkpoints   (resume state)
```

**Key Insight**: Agents write hints to `shared_state` and append actions to `events`. They don't communicate directly—they communicate via the blackboard.

---

## Architecture

### Blackboard Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BLACKBOARD                                     │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  coordination   │  │    feedback     │  │   consensus     │         │
│  │   namespace     │  │   namespace     │  │   namespace     │         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ player/turn_1   │  │ coach/turn_1    │  │ gate/turn_1     │         │
│  │ player/turn_2   │  │ coach/turn_2    │  │ gate/turn_2     │         │
│  │ ...             │  │ ...             │  │ ...             │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │     events      │  ← Append-only audit trail                        │
│  │   namespace     │                                                   │
│  ├─────────────────┤                                                   │
│  │ evt_001: player_start                                               │
│  │ evt_002: player_report                                              │
│  │ evt_003: coach_validate                                             │
│  │ evt_004: coach_decision                                             │
│  │ ...                                                                 │
│  └─────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │  Player │          │  Coach  │          │Orchestr │
    │  Agent  │          │  Agent  │          │  ator   │
    └─────────┘          └─────────┘          └─────────┘
    
    Writes:               Reads:                Reads:
    - player/turn_N       - player/turn_N       - All namespaces
    - events              Writes:               Writes:
                          - coach/turn_N        - checkpoints
                          - consensus/turn_N    - events
                          - events
```

### Communication Flow

```
Turn 1:
  Player WRITES → blackboard["coordination"]["player/turn_1/report"]
  Coach READS  ← blackboard["coordination"]["player/turn_1/report"]
  Coach WRITES → blackboard["feedback"]["coach/turn_1/feedback"]
  Coach WRITES → blackboard["consensus"]["gate/turn_1"]

Turn 2 (if feedback):
  Player READS ← blackboard["feedback"]["coach/turn_1/feedback"]
  Player WRITES → blackboard["coordination"]["player/turn_2/report"]
  ... and so on
```

---

## Components

### 7.1 Blackboard Class

```python
# guardkit/coordination/blackboard.py
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import json

@dataclass
class BlackboardEntry:
    """A single entry in the blackboard."""
    key: str
    namespace: str
    value: Dict[str, Any]
    created_at: str
    expires_at: Optional[str] = None
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.utcnow()

class Blackboard:
    """
    SQLite-backed shared state for agent coordination.
    
    Namespaces:
    - coordination: Player reports, current phase, hints
    - feedback: Coach feedback for Player iterations
    - consensus: Approval/rejection decisions with votes
    - events: Append-only audit trail
    - checkpoints: Workflow state for resume
    """
    
    NAMESPACES = ["coordination", "feedback", "consensus", "events", "checkpoints"]
    
    def __init__(self, db_path: str = ".guardkit/blackboard.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blackboard (
                    key TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    PRIMARY KEY (key, namespace)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_namespace 
                ON blackboard(namespace)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON blackboard(expires_at)
            """)
            # Enable WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
    
    def write(
        self,
        key: str,
        value: Dict[str, Any],
        namespace: str = "coordination",
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Write a value to the blackboard.
        
        Args:
            key: Unique key within namespace (e.g., "player/turn_1/report")
            value: Dictionary to store (will be JSON serialized)
            namespace: One of the defined namespaces
            ttl_seconds: Optional time-to-live in seconds
        """
        if namespace not in self.NAMESPACES:
            raise ValueError(f"Invalid namespace: {namespace}. Must be one of {self.NAMESPACES}")
        
        now = datetime.utcnow()
        expires_at = None
        if ttl_seconds:
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO blackboard 
                (key, namespace, value, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                key,
                namespace,
                json.dumps(value),
                now.isoformat(),
                expires_at
            ))
    
    def read(
        self,
        key: str,
        namespace: str = "coordination"
    ) -> Optional[Dict[str, Any]]:
        """
        Read a value from the blackboard.
        
        Returns None if key doesn't exist or is expired.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT value, expires_at FROM blackboard
                WHERE key = ? AND namespace = ?
            """, (key, namespace)).fetchone()
        
        if row is None:
            return None
        
        # Check expiration
        if row["expires_at"]:
            if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
                return None
        
        return json.loads(row["value"])
    
    def search(
        self,
        pattern: str,
        namespace: str = "coordination",
        include_expired: bool = False
    ) -> List[BlackboardEntry]:
        """
        Search blackboard by key pattern (SQL LIKE).
        
        Pattern uses SQL wildcards: % for any chars, _ for single char.
        Example: "player/turn_%/report" matches all player reports.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT key, namespace, value, created_at, expires_at 
                FROM blackboard
                WHERE key LIKE ? AND namespace = ?
            """
            
            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > ?)"
                rows = conn.execute(query, (
                    pattern, namespace, datetime.utcnow().isoformat()
                )).fetchall()
            else:
                rows = conn.execute(query, (pattern, namespace)).fetchall()
        
        return [
            BlackboardEntry(
                key=row["key"],
                namespace=row["namespace"],
                value=json.loads(row["value"]),
                created_at=row["created_at"],
                expires_at=row["expires_at"]
            )
            for row in rows
        ]
    
    def delete(self, key: str, namespace: str = "coordination") -> bool:
        """Delete a specific key. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM blackboard WHERE key = ? AND namespace = ?
            """, (key, namespace))
        return cursor.rowcount > 0
    
    def sweep_expired(self) -> int:
        """
        Remove all expired entries.
        
        Call this in a maintenance job or before operations.
        Returns number of entries removed.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM blackboard 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (datetime.utcnow().isoformat(),))
        return cursor.rowcount
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all entries in a namespace. Returns count deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM blackboard WHERE namespace = ?
            """, (namespace,))
        return cursor.rowcount
    
    def clear_task(self, task_id: str) -> int:
        """Clear all entries for a specific task across all namespaces."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM blackboard WHERE key LIKE ?
            """, (f"%{task_id}%",))
        return cursor.rowcount
    
    def get_stats(self) -> Dict[str, int]:
        """Get entry counts per namespace."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT namespace, COUNT(*) as count 
                FROM blackboard 
                GROUP BY namespace
            """).fetchall()
        return {row[0]: row[1] for row in rows}
```

### 7.2 Event Log

```python
# guardkit/coordination/events.py
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import uuid

@dataclass
class WorkflowEvent:
    """An immutable event in the workflow audit trail."""
    event_id: str
    task_id: str
    event_type: str
    actor: str
    data: dict
    timestamp: str = None
    transition: Optional[str] = None  # "phase_a → phase_b"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())[:8]

class EventLog:
    """
    Append-only event log for audit and debugging.
    
    Event Types:
    - orchestrator_start: Task begins
    - player_start: Player begins implementation
    - player_report: Player reports progress
    - coach_validate: Coach begins validation
    - coach_decision: Coach approves or provides feedback
    - consensus_recorded: Approval/rejection recorded
    - orchestrator_success: Task completed
    - orchestrator_failure: Task failed
    - orchestrator_escalate: Task escalated to human
    """
    
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
    
    def record(self, event: WorkflowEvent) -> str:
        """
        Record an event. Returns the event_id.
        
        Events are stored in the 'events' namespace with key format:
        "event/{task_id}/{timestamp}_{event_id}"
        """
        key = f"event/{event.task_id}/{event.timestamp}_{event.event_id}"
        
        self.blackboard.write(
            key=key,
            value=asdict(event),
            namespace="events",
            ttl_seconds=2592000  # 30 days retention
        )
        
        return event.event_id
    
    def get_task_events(
        self,
        task_id: str,
        event_type: Optional[str] = None
    ) -> List[WorkflowEvent]:
        """Get all events for a task, optionally filtered by type."""
        entries = self.blackboard.search(
            pattern=f"event/{task_id}/%",
            namespace="events"
        )
        
        events = [WorkflowEvent(**e.value) for e in entries]
        events.sort(key=lambda e: e.timestamp)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events
    
    def get_transitions(self, task_id: str) -> List[str]:
        """Get sequence of phase transitions for a task."""
        events = self.get_task_events(task_id)
        return [e.transition for e in events if e.transition]
    
    def replay(self, task_id: str) -> None:
        """Print event replay for debugging."""
        events = self.get_task_events(task_id)
        
        print(f"\n{'='*60}")
        print(f"EVENT REPLAY: {task_id}")
        print(f"{'='*60}")
        
        for event in events:
            print(f"\n[{event.timestamp}] {event.event_type}")
            print(f"  Actor: {event.actor}")
            if event.transition:
                print(f"  Transition: {event.transition}")
            print(f"  Data: {event.data}")
        
        print(f"\n{'='*60}")
```

### 7.3 Consensus Gate

```python
# guardkit/coordination/consensus.py
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum

class VoteType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"

@dataclass
class Vote:
    """A single vote in a consensus gate."""
    voter: str  # "coach", "human", "linter", "tests"
    vote: VoteType
    rationale: str
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

@dataclass
class ConsensusGate:
    """
    A gate requiring consensus to pass.
    
    Current implementation: Single coach approval.
    Future: Multiple reviewers (human + AI).
    """
    gate_id: str
    task_id: str
    turn: int
    required_approvals: int = 1
    votes: List[Vote] = field(default_factory=list)
    status: Literal["pending", "passed", "blocked"] = "pending"
    created_at: str = None
    resolved_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def add_vote(self, vote: Vote) -> None:
        """Add a vote and update status."""
        self.votes.append(vote)
        self._update_status()
    
    def _update_status(self) -> None:
        """Update gate status based on votes."""
        approvals = sum(1 for v in self.votes if v.vote == VoteType.APPROVE)
        rejections = sum(1 for v in self.votes if v.vote == VoteType.REJECT)
        
        if rejections > 0:
            self.status = "blocked"
            self.resolved_at = datetime.utcnow().isoformat()
        elif approvals >= self.required_approvals:
            self.status = "passed"
            self.resolved_at = datetime.utcnow().isoformat()
    
    @property
    def is_passed(self) -> bool:
        return self.status == "passed"
    
    @property
    def is_blocked(self) -> bool:
        return self.status == "blocked"
    
    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

class ConsensusManager:
    """Manage consensus gates via blackboard."""
    
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
    
    def create_gate(
        self,
        task_id: str,
        turn: int,
        required_approvals: int = 1
    ) -> ConsensusGate:
        """Create a new consensus gate."""
        gate = ConsensusGate(
            gate_id=f"gate/{task_id}/turn_{turn}",
            task_id=task_id,
            turn=turn,
            required_approvals=required_approvals
        )
        
        self.blackboard.write(
            key=gate.gate_id,
            value=asdict(gate),
            namespace="consensus"
        )
        
        return gate
    
    def record_vote(
        self,
        gate_id: str,
        voter: str,
        vote: VoteType,
        rationale: str
    ) -> ConsensusGate:
        """Record a vote on a gate."""
        # Load gate
        data = self.blackboard.read(gate_id, namespace="consensus")
        if data is None:
            raise ValueError(f"Gate not found: {gate_id}")
        
        gate = ConsensusGate(**data)
        gate.votes = [Vote(**v) if isinstance(v, dict) else v for v in gate.votes]
        
        # Add vote
        vote_obj = Vote(voter=voter, vote=vote, rationale=rationale)
        gate.add_vote(vote_obj)
        
        # Save updated gate
        self.blackboard.write(
            key=gate_id,
            value=asdict(gate),
            namespace="consensus"
        )
        
        return gate
    
    def get_gate(self, gate_id: str) -> Optional[ConsensusGate]:
        """Get a consensus gate by ID."""
        data = self.blackboard.read(gate_id, namespace="consensus")
        if data is None:
            return None
        
        gate = ConsensusGate(**data)
        gate.votes = [Vote(**v) if isinstance(v, dict) else v for v in gate.votes]
        return gate
    
    def get_task_gates(self, task_id: str) -> List[ConsensusGate]:
        """Get all gates for a task."""
        entries = self.blackboard.search(
            pattern=f"gate/{task_id}/%",
            namespace="consensus"
        )
        
        gates = []
        for entry in entries:
            gate = ConsensusGate(**entry.value)
            gate.votes = [Vote(**v) if isinstance(v, dict) else v for v in gate.votes]
            gates.append(gate)
        
        return sorted(gates, key=lambda g: g.turn)
```

### 7.4 Coordination Manager (Facade)

```python
# guardkit/coordination/__init__.py
from typing import Optional, Dict, Any
from pathlib import Path

from .blackboard import Blackboard, BlackboardEntry
from .events import EventLog, WorkflowEvent
from .consensus import ConsensusManager, ConsensusGate, Vote, VoteType

class CoordinationManager:
    """
    Facade for all coordination components.
    
    Usage:
        coord = CoordinationManager()
        
        # Player writes report
        coord.write_player_report(task_id, turn, report_data)
        
        # Coach reads report
        report = coord.read_player_report(task_id, turn)
        
        # Coach writes feedback and records decision
        coord.write_coach_feedback(task_id, turn, feedback_data)
        gate = coord.record_coach_decision(task_id, turn, "approve", "All requirements met")
    """
    
    def __init__(self, db_path: str = ".guardkit/blackboard.db"):
        self.blackboard = Blackboard(db_path)
        self.events = EventLog(self.blackboard)
        self.consensus = ConsensusManager(self.blackboard)
    
    # === Player Methods ===
    
    def write_player_report(
        self,
        task_id: str,
        turn: int,
        report: Dict[str, Any]
    ) -> str:
        """Write player's implementation report."""
        key = f"player/{task_id}/turn_{turn}/report"
        
        self.blackboard.write(
            key=key,
            value=report,
            namespace="coordination"
        )
        
        # Record event
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="player_report",
            actor="player",
            transition="implementing → validating",
            data={"report_key": key, "turn": turn}
        ))
        
        return key
    
    def read_player_report(
        self,
        task_id: str,
        turn: int
    ) -> Optional[Dict[str, Any]]:
        """Read player's report for a specific turn."""
        key = f"player/{task_id}/turn_{turn}/report"
        return self.blackboard.read(key, namespace="coordination")
    
    # === Coach Methods ===
    
    def write_coach_feedback(
        self,
        task_id: str,
        turn: int,
        feedback: Dict[str, Any]
    ) -> str:
        """Write coach's feedback."""
        key = f"coach/{task_id}/turn_{turn}/feedback"
        
        self.blackboard.write(
            key=key,
            value=feedback,
            namespace="feedback"
        )
        
        return key
    
    def read_coach_feedback(
        self,
        task_id: str,
        turn: int
    ) -> Optional[Dict[str, Any]]:
        """Read coach's feedback for a specific turn."""
        key = f"coach/{task_id}/turn_{turn}/feedback"
        return self.blackboard.read(key, namespace="feedback")
    
    def get_latest_feedback(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent coach feedback for a task."""
        entries = self.blackboard.search(
            pattern=f"coach/{task_id}/%",
            namespace="feedback"
        )
        
        if not entries:
            return None
        
        # Sort by key (which includes turn number) and get latest
        entries.sort(key=lambda e: e.key, reverse=True)
        return entries[0].value
    
    def record_coach_decision(
        self,
        task_id: str,
        turn: int,
        decision: str,  # "approve" or "feedback"
        rationale: str
    ) -> ConsensusGate:
        """Record coach's approval/rejection decision."""
        # Create or get gate
        gate_id = f"gate/{task_id}/turn_{turn}"
        gate = self.consensus.get_gate(gate_id)
        
        if gate is None:
            gate = self.consensus.create_gate(task_id, turn)
        
        # Record vote
        vote_type = VoteType.APPROVE if decision == "approve" else VoteType.REJECT
        gate = self.consensus.record_vote(gate_id, "coach", vote_type, rationale)
        
        # Record event
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="coach_decision",
            actor="coach",
            transition=f"validating → {'complete' if decision == 'approve' else 'implementing'}",
            data={
                "gate_id": gate_id,
                "decision": decision,
                "rationale": rationale,
                "turn": turn
            }
        ))
        
        return gate
    
    # === Orchestrator Methods ===
    
    def record_task_start(self, task_id: str, requirements: Dict[str, Any]) -> None:
        """Record task start event."""
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="orchestrator_start",
            actor="orchestrator",
            transition="idle → implementing",
            data={"requirements_count": len(requirements.get("acceptance_criteria", []))}
        ))
    
    def record_task_success(self, task_id: str, turns: int) -> None:
        """Record successful task completion."""
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="orchestrator_success",
            actor="orchestrator",
            transition="validating → complete",
            data={"total_turns": turns}
        ))
    
    def record_task_failure(self, task_id: str, turns: int, reason: str) -> None:
        """Record task failure."""
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="orchestrator_failure",
            actor="orchestrator",
            transition="validating → failed",
            data={"total_turns": turns, "reason": reason}
        ))
    
    def record_escalation(self, task_id: str, turns: int, reason: str) -> None:
        """Record escalation to human."""
        self.events.record(WorkflowEvent(
            event_id=None,
            task_id=task_id,
            event_type="orchestrator_escalate",
            actor="orchestrator",
            transition="validating → escalated",
            data={"total_turns": turns, "reason": reason}
        ))
    
    # === Checkpoint Methods ===
    
    def save_checkpoint(self, task_id: str, state: Dict[str, Any]) -> None:
        """Save workflow checkpoint for resume."""
        self.blackboard.write(
            key=f"checkpoint/{task_id}",
            value=state,
            namespace="checkpoints"
        )
    
    def load_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow checkpoint."""
        return self.blackboard.read(f"checkpoint/{task_id}", namespace="checkpoints")
    
    def delete_checkpoint(self, task_id: str) -> bool:
        """Delete checkpoint after successful completion."""
        return self.blackboard.delete(f"checkpoint/{task_id}", namespace="checkpoints")
    
    # === Debugging Methods ===
    
    def replay_task(self, task_id: str) -> None:
        """Print event replay for debugging."""
        self.events.replay(task_id)
    
    def inspect_blackboard(self, task_id: str) -> Dict[str, Any]:
        """Get all blackboard state for a task (for debugging)."""
        result = {}
        
        for namespace in Blackboard.NAMESPACES:
            entries = self.blackboard.search(f"%{task_id}%", namespace=namespace)
            if entries:
                result[namespace] = {e.key: e.value for e in entries}
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """Get blackboard statistics."""
        return self.blackboard.get_stats()
```

---

## File Structure

```
guardkit/
├── coordination/
│   ├── __init__.py          # CoordinationManager facade
│   ├── blackboard.py        # Blackboard class
│   ├── events.py            # EventLog, WorkflowEvent
│   └── consensus.py         # ConsensusManager, ConsensusGate, Vote
```

---

## Integration with Orchestrator

### Modified State (References Instead of Data)

```python
# guardkit/orchestrator/state.py
class AutoBuildState(TypedDict):
    task_id: str
    feature_id: Optional[str]
    requirements: dict  # Still passed directly (immutable)
    
    turn_count: int
    max_turns: int
    phase: str
    
    # Blackboard references (not full data)
    player_report_key: Optional[str]   # e.g., "player/TASK-001/turn_3/report"
    coach_feedback_key: Optional[str]  # e.g., "coach/TASK-001/turn_3/feedback"
    consensus_gate_id: Optional[str]   # e.g., "gate/TASK-001/turn_3"
    
    coach_decision: str
    success: Optional[bool]
    failure_reason: Optional[str]
```

### Modified Nodes

```python
# guardkit/orchestrator/nodes.py

# Initialize coordination manager globally
coord = CoordinationManager()

async def initialize_task(state: AutoBuildState) -> dict:
    """Initialize task with coordination."""
    task_id = state["task_id"]
    
    # Load task
    task = load_task(task_id)
    
    # Record start event
    coord.record_task_start(task_id, task.to_dict())
    
    return {
        "requirements": task.to_dict(),
        "turn_count": 0,
        "phase": "implementing",
        "player_report_key": None,
        "coach_feedback_key": None,
        "consensus_gate_id": None
    }

async def execute_player(state: AutoBuildState) -> dict:
    """Execute player with blackboard coordination."""
    task_id = state["task_id"]
    turn = state["turn_count"]
    
    # Read previous feedback from blackboard (if any)
    feedback = None
    if state.get("coach_feedback_key"):
        feedback = coord.read_coach_feedback(task_id, turn - 1)
    
    # Build context and execute
    # ... (same as before)
    
    # Write report to blackboard
    report_key = coord.write_player_report(task_id, turn, parsed_report)
    
    return {
        "player_report_key": report_key,
        "turn_count": turn + 1,
        "phase": "validating"
    }

async def execute_coach(state: AutoBuildState) -> dict:
    """Execute coach with blackboard coordination."""
    task_id = state["task_id"]
    turn = state["turn_count"] - 1  # Player incremented it
    
    # Read player report from blackboard
    player_report = coord.read_player_report(task_id, turn)
    
    # Execute coach validation
    # ... (same as before)
    
    # Write feedback and record decision
    feedback_key = coord.write_coach_feedback(task_id, turn, coach_output)
    gate = coord.record_coach_decision(
        task_id, turn, 
        coach_output["decision"],
        coach_output["rationale"]
    )
    
    return {
        "coach_feedback_key": feedback_key,
        "consensus_gate_id": gate.gate_id,
        "coach_decision": coach_output["decision"],
        "phase": "complete" if gate.is_passed else "implementing"
    }

async def finalize_success(state: AutoBuildState) -> dict:
    """Record success and cleanup."""
    task_id = state["task_id"]
    
    coord.record_task_success(task_id, state["turn_count"])
    coord.delete_checkpoint(task_id)  # Clean up checkpoint
    
    return {"phase": "complete", "success": True}

async def finalize_failure(state: AutoBuildState) -> dict:
    """Record failure."""
    task_id = state["task_id"]
    reason = f"Max turns ({state['max_turns']}) reached"
    
    coord.record_task_failure(task_id, state["turn_count"], reason)
    # Keep checkpoint for debugging
    
    return {"phase": "failed", "success": False, "failure_reason": reason}
```

---

## Debugging Commands

```bash
# View all events for a task
guardkit debug replay TASK-001

# Inspect blackboard state
guardkit debug inspect TASK-001

# View consensus gates
guardkit debug consensus TASK-001

# Get blackboard stats
guardkit debug stats
```

```python
# guardkit/cli/debug.py
import click
from guardkit.coordination import CoordinationManager

@click.group()
def debug():
    """Debugging tools for AutoBuild."""
    pass

@debug.command()
@click.argument("task_id")
def replay(task_id: str):
    """Replay all events for a task."""
    coord = CoordinationManager()
    coord.replay_task(task_id)

@debug.command()
@click.argument("task_id")
def inspect(task_id: str):
    """Inspect blackboard state for a task."""
    coord = CoordinationManager()
    state = coord.inspect_blackboard(task_id)
    
    import json
    click.echo(json.dumps(state, indent=2))

@debug.command()
@click.argument("task_id")
def consensus(task_id: str):
    """View consensus gates for a task."""
    coord = CoordinationManager()
    gates = coord.consensus.get_task_gates(task_id)
    
    for gate in gates:
        click.echo(f"\nGate: {gate.gate_id}")
        click.echo(f"  Status: {gate.status}")
        click.echo(f"  Votes:")
        for vote in gate.votes:
            click.echo(f"    - {vote.voter}: {vote.vote.value}")
            click.echo(f"      Rationale: {vote.rationale}")

@debug.command()
def stats():
    """Show blackboard statistics."""
    coord = CoordinationManager()
    stats = coord.get_stats()
    
    click.echo("\nBlackboard Statistics:")
    for namespace, count in stats.items():
        click.echo(f"  {namespace}: {count} entries")
```

---

## Acceptance Criteria

- [ ] `Blackboard` class implemented with SQLite persistence
- [ ] Namespaces: coordination, feedback, consensus, events, checkpoints
- [ ] TTL support for automatic expiration
- [ ] `EventLog` records all workflow transitions
- [ ] `ConsensusManager` handles approval gates
- [ ] `CoordinationManager` facade provides clean API
- [ ] Orchestrator nodes use blackboard for communication
- [ ] State contains keys/references, not full data
- [ ] Debug commands: replay, inspect, consensus, stats
- [ ] WAL mode enabled for concurrent access
- [ ] 30-day retention for events (configurable)

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_blackboard.py

def test_write_and_read():
    bb = Blackboard(":memory:")
    bb.write("test/key", {"foo": "bar"}, namespace="coordination")
    
    result = bb.read("test/key", namespace="coordination")
    
    assert result == {"foo": "bar"}

def test_ttl_expiration():
    bb = Blackboard(":memory:")
    bb.write("test/key", {"foo": "bar"}, namespace="coordination", ttl_seconds=-1)
    
    result = bb.read("test/key", namespace="coordination")
    
    assert result is None  # Expired

def test_search_pattern():
    bb = Blackboard(":memory:")
    bb.write("player/turn_1/report", {"turn": 1}, namespace="coordination")
    bb.write("player/turn_2/report", {"turn": 2}, namespace="coordination")
    bb.write("coach/turn_1/feedback", {"turn": 1}, namespace="feedback")
    
    results = bb.search("player/%", namespace="coordination")
    
    assert len(results) == 2

def test_namespace_isolation():
    bb = Blackboard(":memory:")
    bb.write("same/key", {"ns": "coord"}, namespace="coordination")
    bb.write("same/key", {"ns": "feedback"}, namespace="feedback")
    
    coord = bb.read("same/key", namespace="coordination")
    feedback = bb.read("same/key", namespace="feedback")
    
    assert coord["ns"] == "coord"
    assert feedback["ns"] == "feedback"
```

### Integration Tests

```python
# tests/integration/test_coordination.py

@pytest.mark.integration
def test_full_turn_cycle():
    coord = CoordinationManager()
    task_id = "TEST-001"
    
    # Player writes report
    report_key = coord.write_player_report(task_id, 1, {
        "files_modified": ["src/test.py"],
        "tests_written": ["test_feature"]
    })
    
    # Coach reads report
    report = coord.read_player_report(task_id, 1)
    assert report["files_modified"] == ["src/test.py"]
    
    # Coach writes feedback and decision
    coord.write_coach_feedback(task_id, 1, {
        "decision": "approve",
        "rationale": "All good"
    })
    gate = coord.record_coach_decision(task_id, 1, "approve", "All good")
    
    assert gate.is_passed
    
    # Verify events recorded
    events = coord.events.get_task_events(task_id)
    assert len(events) == 2  # player_report + coach_decision

@pytest.mark.integration
def test_event_replay():
    coord = CoordinationManager()
    task_id = "TEST-002"
    
    coord.record_task_start(task_id, {"acceptance_criteria": ["a", "b"]})
    coord.write_player_report(task_id, 1, {"files": []})
    coord.record_coach_decision(task_id, 1, "feedback", "Missing tests")
    coord.write_player_report(task_id, 2, {"files": [], "tests": ["test"]})
    coord.record_coach_decision(task_id, 2, "approve", "LGTM")
    coord.record_task_success(task_id, 2)
    
    events = coord.events.get_task_events(task_id)
    
    assert len(events) == 6
    assert events[0].event_type == "orchestrator_start"
    assert events[-1].event_type == "orchestrator_success"
```

---

## Benefits

1. **Observability**: See exactly what each agent saw and wrote
2. **Debugging**: `guardkit debug replay TASK-001` shows full history
3. **Resume**: Checkpoints in blackboard survive crashes
4. **Extensibility**: Add new agents that read/write same blackboard
5. **Audit Trail**: 30-day event retention for analysis
6. **Decoupling**: Agents don't know each other's interfaces

---

## References

- [Claude-Flow Blackboard Pattern](https://gist.github.com/ruvnet/9b066e77dd2980bfdcc5adf3bc082281)
- [Claude-Flow Memory System Wiki](https://github.com/ruvnet/claude-flow/wiki/Memory-System)
- [Blackboard Pattern (Wikipedia)](https://en.wikipedia.org/wiki/Blackboard_(design_pattern))
- AutoBuild Testing Strategy (bugs at integration seams)
