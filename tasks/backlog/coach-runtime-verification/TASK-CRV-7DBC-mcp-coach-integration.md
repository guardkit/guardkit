---
id: TASK-CRV-7DBC
title: MCP tool integration for Coach with server lifecycle management
status: backlog
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: low
tags: [mcp, playwright, coach, verification, server-lifecycle, future]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 4
implementation_mode: task-work
complexity: 8
dependencies: [TASK-CRV-9914]
---

# Task: MCP tool integration for Coach with server lifecycle management

## Description

Enable the Coach validator to use MCP tools (e.g., Playwright for browser testing, custom verification servers) when validating acceptance criteria. The Claude Agent SDK natively supports MCP server configuration via `ClaudeAgentOptions(mcp_servers={...})`.

### Critical Architectural Constraint

**Server lifecycle management must be owned by the orchestrator, NOT the Coach.** The Coach is a pure verifier — it should not be responsible for starting and stopping the thing it's verifying. The autobuild orchestrator should have `pre_verification` and `post_verification` hooks that manage service lifecycle, with cleanup guaranteed even if verification fails hard. This prevents zombie processes and makes the infrastructure reusable across future verification modes.

### Three-Tier Verification Architecture

Verification capabilities decompose into three tiers with increasing complexity:

#### Tier 1: API Backends (Near-term, no MCP needed)

The Coach starts the server as a subprocess in the worktree, waits for the health endpoint, runs HTTP assertions, then terminates. This is a natural extension of the existing `subprocess.run()` infrastructure and does NOT require MCP.

```
Orchestrator                           Coach
    │                                    │
    ├─ pre_verification:                 │
    │   start server subprocess          │
    │   wait for health endpoint         │
    │                                    │
    ├─ invoke Coach ──────────────────>  │
    │                                    ├─ GET /health → 200 ✓
    │                                    ├─ GET /api/v1/ping → 200 ✓
    │                                    ├─ POST /api/v1/data → 201 ✓
    │                                    │
    │  <──────────────── result ─────── │
    │                                    │
    ├─ post_verification:                │
    │   terminate server subprocess      │
    │   cleanup ports                    │
    └────────────────────────────────────┘
```

Acceptance criteria pattern: `GET /health returns 200` — classifiable as `command_execution`.

#### Tier 2: Web Apps (Medium-term, Playwright MCP)

Coach invocation gains a Playwright MCP server for DOM assertions, screenshot comparison, rendered output verification. Server lifecycle (start Next.js/React dev server, wait for port) is orchestrator-owned.

```
Orchestrator                           Coach + Playwright MCP
    │                                    │
    ├─ pre_verification:                 │
    │   npm run dev (port 3000)          │
    │   wait for localhost:3000          │
    │                                    │
    ├─ invoke Coach with MCP ─────────> │
    │                                    ├─ navigate(localhost:3000)
    │                                    ├─ assert(h1 == "Dashboard")
    │                                    ├─ screenshot() → compare
    │                                    │
    │  <──────────────── result ─────── │
    │                                    │
    ├─ post_verification:                │
    │   kill dev server                  │
    │   release port 3000                │
    └────────────────────────────────────┘
```

**Port isolation**: Parallel tasks need unique ports. The orchestrator assigns ports from a pool and passes them via environment variables.

#### Tier 3: Mobile/Desktop Apps (Long-term)

Appium, platform-specific tooling. Out of scope for this task.

## Acceptance Criteria

- [ ] Orchestrator has `pre_verification(task_id, worktree_path)` hook that starts required services
- [ ] Orchestrator has `post_verification(task_id)` hook that terminates services and cleans up
- [ ] Post-verification cleanup is **guaranteed** (runs even if Coach validation throws)
- [ ] Port isolation: orchestrator assigns unique ports from a configurable range for parallel tasks
- [ ] Coach SDK invocation in `agent_invoker.py` accepts optional `mcp_servers` parameter
- [ ] MCP servers configured via `.mcp.json` or autobuild config
- [ ] Playwright MCP server integration working for Tier 2 web app verification
- [ ] Tier 1 API health check verification working without MCP (subprocess + HTTP)
- [ ] Coach agent definition (`autobuild-coach.md`) updated with verification capabilities
- [ ] MCP tools only loaded when relevant criteria types are detected
- [ ] No zombie processes after verification (even on failure)
- [ ] Integration tests with mock server lifecycle

## Implementation Notes

### Orchestrator Lifecycle Hooks

```python
# autobuild.py — verification lifecycle
class VerificationLifecycle:
    """Manages service lifecycle for Coach verification."""

    def __init__(self, worktree_path: Path, port_pool: PortPool):
        self.worktree_path = worktree_path
        self.port_pool = port_pool
        self._processes: List[subprocess.Popen] = []

    async def pre_verification(self, task_id: str, criteria: ClassificationResult) -> dict:
        """Start services needed for verification. Returns env vars for Coach."""
        env = {}
        if criteria.needs_server:
            port = self.port_pool.acquire()
            proc = subprocess.Popen(
                criteria.server_start_command,
                cwd=str(self.worktree_path),
                env={**os.environ, "PORT": str(port)},
            )
            self._processes.append(proc)
            await self._wait_for_health(f"http://localhost:{port}/health", timeout=30)
            env["VERIFY_BASE_URL"] = f"http://localhost:{port}"
        return env

    async def post_verification(self, task_id: str) -> None:
        """Terminate all started services. Always runs."""
        for proc in self._processes:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._processes.clear()
        self.port_pool.release_all()
```

### SDK MCP Configuration

```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Bash", "Grep", "Glob"],
    permission_mode="bypassPermissions",
    mcp_servers={
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest"],
        },
    },
)
```

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (verification lifecycle hooks)
- `guardkit/orchestrator/agent_invoker.py` (add mcp_servers to Coach invocation)
- `installer/core/agents/autobuild-coach.md` (document verification capabilities)
- New: `guardkit/orchestrator/verification_lifecycle.py` (lifecycle management)
- `.mcp.json` (MCP server configuration)
