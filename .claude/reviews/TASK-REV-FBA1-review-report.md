# Review Report: TASK-REV-FBA1 (Revised)

## Executive Summary

This investigation re-examines the `/feature-build` UX issues with corrected understanding and a **forward-looking architectural vision** informed by the Reachy PA event-driven orchestration patterns.

**Core Issues Identified**:
1. **Buffered output** - Claude Code Bash tool doesn't stream, user sees nothing during builds
2. **No real-time feedback** - Rich library TTY-dependent features fail silently in non-TTY context
3. **Architectural gap** - No event-driven communication layer for agent orchestration

**Strategic Recommendation**: Implement a **phased event-driven architecture** using NATS with JetStream, providing sub-millisecond progress updates that work across CLI, Claude Code, and future web dashboard/voice interfaces.

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Investigation (Diagnostic Analysis) |
| **Depth** | Comprehensive |
| **Duration** | ~75 minutes |
| **Reviewer** | Comprehensive investigation with architectural analysis |
| **Files Analyzed** | feature-build.md, autobuild.md, autobuild.py, agent_invoker.py, progress.py, finally_success.md, reachy_pa architecture |

---

## Part 1: Immediate Problem Analysis

### User's Actual Environment

- **Shell**: iTerm with zsh (macOS)
- **Invocation**: Running `/feature-build` as a slash command in Claude Code
- **NOT**: Running directly in terminal or VS Code extension timeout issues

### The Core Problem: Buffered Output

When Claude Code invokes a Bash command:
1. The command runs in a subprocess
2. **Output is buffered until completion** (not streamed)
3. User sees nothing during execution
4. Only when command completes does output appear

**Evidence from finally_success.md**:
The terminal output shows rich progress:
```
⠋ Turn 1/5: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%
INFO:guardkit.orchestrator.agent_invoker:[TASK-FHA-003] task-work implementation in progress... (30s elapsed)
...
✓ TASK-FHA-001: approved (1 turns)
```

This is produced by `ProgressDisplay` using Rich library - **none visible when run via Claude Code Bash tool**.

### Current Architecture Limitation

```
Claude Code (user types /feature-build TASK-XXX)
    │
    └── Bash tool invokes: guardkit autobuild task TASK-XXX
            │
            └── AutoBuildOrchestrator
                    │
                    ├── ProgressDisplay (Rich library - TTY-dependent)
                    │
                    ├── AgentInvoker (SDK calls - long-running)
                    │
                    └── Output to stdout (BUFFERED - no streaming)
```

**Problem**: No mechanism for real-time feedback outside terminal context.

---

## Part 2: Big Picture - Event-Driven Agent Orchestration

### Lessons from Reachy PA Architecture

The Reachy PA project demonstrates a superior pattern for agent orchestration using **NATS with JetStream**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     NATS Message Bus                             │
│                                                                  │
│   Topics:                                                        │
│   • agents.status.*       - Agent status updates                │
│   • agents.approval.*     - Human-in-the-loop requests          │
│   • agents.commands.*     - Control messages                    │
│   • agents.results.*      - Task completion                     │
│   • agents.errors.*       - Error notifications                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ CLI Client  │   │ Web Dashboard│   │ Voice (Reachy)│
│ (Subscribe) │   │ (WebSocket)  │   │ (NeMo ASR/TTS)│
└─────────────┘   └─────────────┘   └─────────────┘
```

### Why NATS Over Alternatives

| Option | Why Not |
|--------|---------|
| **tmux** | Process-based, single machine, no structured messages |
| **File polling** | High latency, race conditions, doesn't scale |
| **Redis Streams** | Additional dependency, higher latency than NATS |
| **Kafka** | Overkill for this use case, complex setup |
| **NATS** | Single binary, sub-ms latency, built-in persistence |

### Event-Driven Progress Architecture for GuardKit

```
┌─────────────────────────────────────────────────────────────────┐
│                     NATS Message Bus                             │
│                                                                  │
│   Topics:                                                        │
│   • guardkit.builds.{build_id}.status    - Turn progress        │
│   • guardkit.builds.{build_id}.approval  - Human checkpoint     │
│   • guardkit.builds.{build_id}.result    - Build completion     │
│   • guardkit.errors.*                    - Error propagation    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Claude Code     │ │ Terminal CLI    │ │ Future Dashboard│
│ MCP Bridge      │ │ (guardkit watch)│ │ (React + WS)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Standardized Progress Message Envelope

Following Reachy PA's pattern:

```json
{
  "message_id": "uuid-v4",
  "timestamp": "2025-01-31T15:30:00Z",
  "version": "1.0",
  "build_id": "FEAT-0F4A",
  "event_type": "status",
  "payload": {
    "wave": 1,
    "wave_total": 3,
    "task_id": "TASK-FB-002",
    "task_name": "Implement core configuration",
    "turn": 2,
    "turn_max": 5,
    "phase": "Coach Validation",
    "state": "running",
    "progress": {
      "current_step": 4,
      "total_steps": 10,
      "percentage": 40
    },
    "metrics": {
      "elapsed_seconds": 245,
      "tokens_used": 12500,
      "tests_passed": 3,
      "tests_total": 5
    },
    "last_activity": "2025-01-31T15:29:55Z"
  }
}
```

### Human-in-the-Loop Approval Pattern

For Phase 2.8 checkpoints and Coach decisions:

```json
{
  "message_id": "uuid-v4",
  "timestamp": "2025-01-31T15:30:00Z",
  "version": "1.0",
  "build_id": "FEAT-0F4A",
  "event_type": "approval_request",
  "payload": {
    "task_id": "TASK-FB-002",
    "decision_point": "complexity_checkpoint",
    "complexity_score": 8,
    "priority": "high",
    "options": ["approve", "modify", "simplify", "reject", "postpone"],
    "context": {
      "plan_summary": "Refactor authentication module...",
      "risk_factors": ["High file count", "Database schema changes"]
    },
    "expires_at": "2025-01-31T15:45:00Z"
  }
}
```

---

## Part 3: Phased Implementation Roadmap

### Phase 1: Minimal Working Solution (Now)

**Goal**: Fix immediate UX gap with minimal effort

| Task | Description | Effort |
|------|-------------|--------|
| TASK-FB-001 | TTY detection in ProgressDisplay | Low |
| TASK-FB-002 | Simple text output fallback for non-TTY | Low |
| TASK-FB-003 | Progress file writer (JSON, every 30s) | Low |
| TASK-FB-004 | `/feature-build` polls progress file | Medium |

**Architecture (Phase 1)**:
```
guardkit autobuild
    │
    ├── ProgressDisplay (TTY? Rich : Text)
    │
    └── Progress file: .guardkit/autobuild/{id}/progress.json
            │
            └── Claude Code polls every 30s
```

### Phase 2: Event-Driven Foundation (Q1)

**Goal**: Introduce NATS for real-time event streaming

| Task | Description | Effort |
|------|-------------|--------|
| TASK-FB-010 | Add NATS JetStream integration | Medium |
| TASK-FB-011 | Publish turn status events | Medium |
| TASK-FB-012 | `guardkit watch FEAT-XXX` CLI subscriber | Medium |
| TASK-FB-013 | Approval request/response via NATS | Medium |
| TASK-FB-014 | MCP bridge for Claude Code integration | High |

**Architecture (Phase 2)**:
```
guardkit autobuild
    │
    └── NATS Publisher
            │
            ├── guardkit.builds.{id}.status
            ├── guardkit.builds.{id}.approval
            └── guardkit.builds.{id}.result
                    │
         ┌──────────┴──────────┐
         │                     │
    guardkit watch        MCP Bridge
    (CLI subscriber)      (Claude Code)
```

### Phase 3: Multi-Interface & A2A (Q2)

**Goal**: Full distributed orchestration with industry standards

| Task | Description | Effort |
|------|-------------|--------|
| TASK-FB-020 | Web dashboard (React + WebSocket) | High |
| TASK-FB-021 | Voice notifications (optional Reachy integration) | Medium |
| TASK-FB-022 | Adopt A2A message semantics | Medium |
| TASK-FB-023 | Multi-project build orchestration | High |
| TASK-FB-024 | Priority-based interruption | Medium |

**Architecture (Phase 3)**:
```
┌─────────────────────────────────────────────────────────────────┐
│                     NATS Message Bus (A2A Semantics)             │
└──────────────────────────┬───────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │          │           │           │          │
    ▼          ▼           ▼           ▼          ▼
 CLI       Web UI      Claude      Reachy     Mobile
(watch)   (React)    (MCP Bridge) (Voice)    (Future)
```

---

## Part 4: Comparison with TASK-REV-BAF6

### What to Integrate (After Phase 1)

The scope management recommendations from TASK-REV-BAF6 become **more powerful** with event-driven architecture:

| Original Recommendation | Enhanced with Events |
|------------------------|---------------------|
| Phased [I]mplement | Wave completion → approval event → user decides continue/stop |
| Soft limits with warnings | Publish warning events, dashboard shows alerts |
| `--continue` command | Subscribe to build, send resume command via NATS |
| Wave completion pause | Automatic approval_request at wave boundary |

### Defer Until Phase 2

| TASK-REV-BAF6 Item | Reason to Defer |
|--------------------|-----------------|
| Feature YAML default | Infrastructure first |
| Phased [I]mplement | Needs approval event pattern |
| Soft limits | Needs warning event pattern |
| Complexity guidance | Needs metrics event pattern |

---

## Part 5: Technical Decisions

### Why NATS with JetStream

1. **Single binary** - No complex cluster setup
2. **Sub-millisecond latency** - Critical for real-time feedback
3. **Built-in persistence** - JetStream for replay if needed
4. **Leaf/Hub topology** - Scales to multi-region if needed
5. **FastStream compatibility** - Swap to Kafka later if needed

### Why Not tmux/Screen

From investigation of common agent orchestration patterns:

| Approach | Issues |
|----------|--------|
| tmux sessions | Single machine, no structured data, hard to parse |
| Screen sessions | Same limitations as tmux |
| Process managers | No message semantics, polling-based |

**Event streams** provide structured, typed messages that any client can consume.

### MCP Bridge for Claude Code

Following Reachy PA's MCP server pattern:

```python
# GuardKit MCP Server (future)
@mcp_tool
async def get_build_status(build_id: str) -> dict:
    """Get real-time build status."""
    return await nats_client.request(f"guardkit.builds.{build_id}.status")

@mcp_tool
async def approve_checkpoint(build_id: str, decision: str) -> dict:
    """Approve or reject a build checkpoint."""
    return await nats_client.publish(
        f"guardkit.builds.{build_id}.commands",
        {"action": "checkpoint_decision", "decision": decision}
    )
```

---

## Part 6: Success Metrics

### Phase 1 (Immediate)

| Metric | Current | Target |
|--------|---------|--------|
| User sees progress during build | No | Yes (polled) |
| Time to first feedback | >5 min | <60s |
| Non-TTY output quality | Poor | Acceptable |

### Phase 2 (Q1)

| Metric | Current | Target |
|--------|---------|--------|
| Real-time progress updates | No | Yes (<100ms) |
| Multiple interface support | 1 (terminal) | 3 (terminal, Claude, watch) |
| Human checkpoint handling | Manual | Event-driven |

### Phase 3 (Q2)

| Metric | Current | Target |
|--------|---------|--------|
| Web dashboard | No | Yes |
| Multi-project orchestration | No | Yes |
| A2A compatibility | No | Yes |

---

## Recommended Decision

### Implement Phased Approach

**Phase 1 Now** (6 tasks, ~1 week):
- TTY detection + text fallback
- Progress file polling
- Immediate UX improvement

**Phase 2 Q1** (5 tasks, ~2 weeks):
- NATS integration
- Event-driven progress
- MCP bridge foundation

**Phase 3 Q2** (5 tasks, ~3 weeks):
- Web dashboard
- A2A semantics
- Full multi-interface support

### Priority Task Breakdown (Phase 1)

| ID | Task | Mode | Priority |
|----|------|------|----------|
| TASK-FB-001 | TTY detection in ProgressDisplay | direct | 1 |
| TASK-FB-002 | Simple text output fallback | task-work | 1 |
| TASK-FB-003 | Progress file writer | task-work | 2 |
| TASK-FB-004 | /feature-build polling integration | task-work | 2 |
| TASK-FB-005 | Timeout documentation update | direct | 3 |
| TASK-FB-006 | --timeout flag passthrough | direct | 3 |

---

## Appendix: Architecture Alignment with Reachy PA

### Pattern Mapping

| Reachy PA Pattern | GuardKit Application |
|-------------------|---------------------|
| NATS Message Bus | Build progress + approval events |
| State Publishing | Turn-by-turn status updates |
| Standardized Envelope | {build_id, event_type, payload} |
| Approval Loop | Phase 2.8 checkpoints, Coach decisions |
| MCP Bridge | Claude Code tool integration |
| Dual Interface | CLI + Web + Claude Code |
| Local Cache | CLI caches state, subscribes for updates |
| Priority Interrupts | Critical errors halt, warnings queue |
| Structured Metrics | Tokens, tests, coverage per turn |
| A2A Compatibility | Future industry standard adoption |

### Future Integration Points

1. **Reachy Voice Notifications**: "Build FEAT-0F4A Wave 1 complete. 3 tasks passed."
2. **Unified Dashboard**: Single view of all GuardKit builds across projects
3. **Cross-Project Dependencies**: Wait for another build to complete before continuing

---

## Next Steps

1. Review this revised investigation report
2. Choose decision at checkpoint ([A]ccept/[R]evise/[I]mplement/[C]ancel)
3. If [I]mplement: Create Phase 1 tasks (6 immediate, 10+ future)
4. Execute Phase 1 for immediate UX improvement
5. Plan Phase 2 NATS integration for Q1
