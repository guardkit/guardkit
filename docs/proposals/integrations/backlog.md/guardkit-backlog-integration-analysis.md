# GuardKit + Backlog.md Integration Analysis

**Date:** December 6, 2025  
**Status:** Architectural Review  
**Domain:** guardkit.ai (standalone) + optional Backlog.md integration

---

## Executive Summary

GuardKit (formerly TaskWright) and Backlog.md are complementary tools that address different aspects of AI-assisted development. This analysis recommends a **plugin architecture** where Backlog.md serves as an optional task management backend while GuardKit maintains full standalone functionality.

**Key Insight:** GuardKit focuses on *how* to build quality software (specifications, quality gates, agent orchestration), while Backlog.md focuses on *what* and *when* (task visualization, project management, Kanban boards). These concerns are orthogonal and naturally composable.

---

## Tool Comparison

| Aspect | GuardKit | Backlog.md |
|--------|----------|------------|
| **Primary Purpose** | Specification-driven development methodology | Task management & visualization |
| **Core Value** | Quality gates, EARS/BDD, agent orchestration | Kanban boards, task lifecycle, search |
| **Task Storage** | Local markdown (project-specific) | `/backlog` folder (Git-integrated) |
| **MCP Support** | Planned | Native (v1.26+) |
| **AI Integration** | Agent-based workflow orchestration | Task assignment to AI agents |
| **Web UI** | None (CLI-focused) | Full Kanban board + task management |
| **License** | MIT (planned) | MIT |
| **Maturity** | Pre-release | 4.1k stars, v1.26, 145 releases |

---

## Integration Architecture

### Design Principle: Standalone-First with Optional Enhancement

```
┌─────────────────────────────────────────────────────────────────┐
│                        GuardKit Core                            │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ Specification │  │    Quality    │  │      Agent        │   │
│  │   Engine      │  │    Gates      │  │   Orchestration   │   │
│  │  (EARS/BDD)   │  │  (Test/Lint)  │  │  (task-work)      │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │      Task Storage Interface   │                  │
│              └───────────────┬───────────────┘                  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   Native    │    │ Backlog.md  │    │   Future    │
    │  (Default)  │    │  (Plugin)   │    │  (Linear,   │
    │  Markdown   │    │   via MCP   │    │   Jira...)  │
    └─────────────┘    └─────────────┘    └─────────────┘
```

### Mode Selection

```yaml
# guardkit.yaml (project config)
task_backend:
  provider: native  # Default: uses local .guardkit/tasks/
  
# OR with Backlog.md integration:
task_backend:
  provider: backlog.md
  mcp_server: backlog
  sync_mode: bidirectional  # native → backlog.md on create/update
```

---

## Standalone Mode (Default)

When GuardKit operates standalone, it uses its own minimal task storage:

```
project/
├── .guardkit/
│   ├── tasks/
│   │   ├── TASK-001.md          # Minimal task file
│   │   ├── TASK-002.md
│   │   └── ...
│   ├── specs/
│   │   ├── feature-auth.ears    # EARS specifications
│   │   └── feature-auth.gherkin # BDD scenarios
│   └── state.json               # Workflow state
├── .claude/
│   ├── agents/
│   └── commands/
└── GUARDKIT.md                  # Project context
```

### Native Task Format (Minimal)

```markdown
---
id: TASK-001
title: Implement OAuth2 Authentication
status: In Progress
created: 2025-12-06T10:00:00Z
spec_ref: specs/feature-auth.ears
---

## Description
Implement OAuth2 authentication flow with Google and GitHub providers.

## EARS Reference
See: specs/feature-auth.ears#REQ-AUTH-001

## BDD Scenarios
See: specs/feature-auth.gherkin

## Quality Gates
- [ ] Unit tests passing (90%+ coverage)
- [ ] Integration tests passing
- [ ] Code review approved
```

**Rationale:** GuardKit's native format is deliberately minimal because the real value is in the specification files (EARS, BDD), not the task metadata. The task file primarily serves as a pointer to specifications.

---

## Backlog.md Integration Mode

When enabled, GuardKit delegates task management to Backlog.md while retaining full control over:
- Specification generation and validation
- Quality gate enforcement
- Agent orchestration
- Workflow state

### Integration Points

#### 1. Task Creation (`guardkit task-create`)

```python
# When Backlog.md integration is enabled:

async def create_task(spec: EARSSpecification) -> Task:
    # 1. Generate task from specification (GuardKit's value)
    task_data = await generate_task_from_spec(spec)
    
    # 2. Delegate to Backlog.md via MCP
    backlog_task = await mcp_client.call(
        server="backlog",
        method="task_create",
        params={
            "title": task_data.title,
            "description": format_for_backlog(task_data),
            "labels": ["guardkit", spec.category],
            "priority": spec.priority,
            "acceptance_criteria": spec.acceptance_criteria,
            "notes": f"EARS: {spec.id}\nBDD: {spec.gherkin_file}"
        }
    )
    
    # 3. Store cross-reference locally
    store_task_mapping(guardkit_id=task_data.id, backlog_id=backlog_task.id)
    
    return task_data
```

#### 2. Task Work (`guardkit task-work`)

```python
async def work_on_task(task_id: str):
    # 1. Resolve task (check both systems)
    task = await resolve_task(task_id)  # Handles both TASK-001 and task-15
    
    # 2. Update status in Backlog.md
    if backlog_integration_enabled():
        await mcp_client.call(
            server="backlog",
            method="task_edit",
            params={
                "id": task.backlog_id,
                "status": "In Progress",
                "assignee": "@claude"  # Or human assignee
            }
        )
    
    # 3. Execute GuardKit workflow (unchanged)
    await execute_specification_workflow(task)
    await run_quality_gates(task)
    await orchestrate_agents(task)
```

#### 3. Task Completion (`guardkit task-complete`)

```python
async def complete_task(task_id: str, results: WorkResults):
    # 1. Validate quality gates passed
    if not results.all_gates_passed:
        raise QualityGateFailure(results.failures)
    
    # 2. Update Backlog.md
    if backlog_integration_enabled():
        await mcp_client.call(
            server="backlog",
            method="task_edit",
            params={
                "id": task.backlog_id,
                "status": "Done",
                "notes": format_completion_notes(results)
            }
        )
    
    # 3. Archive spec files if configured
    await archive_completed_spec(task.spec_ref)
```

---

## Configuration Options

### Project-Level (guardkit.yaml)

```yaml
# GuardKit project configuration
version: "1.0"

# Task backend selection
task_backend:
  # Options: native | backlog.md | linear | jira
  provider: backlog.md
  
  # Backlog.md specific settings
  backlog:
    # Use MCP (recommended) or CLI
    connection: mcp  # mcp | cli
    
    # Sync behavior
    sync:
      # Create Backlog.md tasks from GuardKit specs
      create_tasks: true
      
      # Update status bidirectionally
      status_sync: true
      
      # Import existing Backlog.md tasks
      import_existing: false
      
    # Task format mapping
    mapping:
      # GuardKit field → Backlog.md field
      spec_ref: notes  # Store spec reference in notes
      quality_gates: acceptance_criteria
      
    # Labels added to all GuardKit-created tasks
    labels: ["guardkit", "spec-driven"]

# Specification settings (unchanged)
specifications:
  ears_enabled: true
  bdd_enabled: true
  
# Quality gates (unchanged)  
quality_gates:
  test_coverage: 90
  lint_enabled: true
```

### Global User Settings (~/.guardkit/config.yaml)

```yaml
# User preferences
defaults:
  task_backend: native  # Default for new projects
  
# Backlog.md global settings (if installed)
backlog:
  # Auto-detect if backlog CLI is available
  auto_detect: true
  
  # Default MCP server name
  mcp_server: backlog
```

---

## Benefits of Integration

### For GuardKit Users

1. **Visual Task Management:** Gain Kanban boards without building one
2. **Team Visibility:** Non-technical stakeholders can track progress
3. **Rich Task Features:** Dependencies, labels, priorities, search
4. **Cross-Branch Tracking:** See tasks across Git branches
5. **Web UI:** Browser-based task management when needed

### For Backlog.md Users

1. **Specification Quality:** Tasks backed by formal EARS/BDD specs
2. **Quality Gates:** Automatic test/lint enforcement
3. **Agent Orchestration:** Structured AI task execution
4. **Human Checkpoints:** Controlled approval workflows
5. **Production-Grade Output:** Proven methodology for quality code

---

## Implementation Phases

### Phase 1: Standalone Refinement (Current Focus)

**Goal:** Ensure GuardKit works perfectly without any external dependencies.

- [ ] Finalize native task storage format
- [ ] Complete `/task-create`, `/task-work`, `/task-complete` commands
- [ ] Implement quality gate enforcement
- [ ] Ship guardkit.ai standalone version

### Phase 2: Task Storage Interface (Week 2)

**Goal:** Abstract task storage behind a clean interface.

```python
# guardkit/storage/interface.py
from abc import ABC, abstractmethod

class TaskStorage(ABC):
    @abstractmethod
    async def create(self, task: Task) -> str: ...
    
    @abstractmethod
    async def get(self, task_id: str) -> Task: ...
    
    @abstractmethod
    async def update(self, task_id: str, updates: TaskUpdate) -> Task: ...
    
    @abstractmethod
    async def list(self, filters: TaskFilters) -> List[Task]: ...
    
    @abstractmethod
    async def archive(self, task_id: str) -> None: ...
```

### Phase 3: Backlog.md Plugin (Week 3-4)

**Goal:** Implement Backlog.md as the first external backend.

```python
# guardkit/storage/backlog_md.py
from guardkit.storage.interface import TaskStorage
from mcp import MCPClient

class BacklogMdStorage(TaskStorage):
    def __init__(self, mcp_server: str = "backlog"):
        self.mcp = MCPClient(server=mcp_server)
    
    async def create(self, task: Task) -> str:
        result = await self.mcp.call(
            "task_create",
            title=task.title,
            description=self._format_description(task),
            labels=task.labels + ["guardkit"],
            priority=task.priority
        )
        return result["id"]
```

### Phase 4: CLI Integration (Week 5)

**Goal:** Add configuration commands and seamless switching.

```bash
# Initialize with Backlog.md
guardkit init --backend backlog.md

# Switch existing project
guardkit config set task_backend backlog.md

# Check integration status
guardkit status --backend
# Output: Task Backend: backlog.md (connected via MCP)
#         Tasks: 15 total (8 from specs, 7 imported)
```

---

## User Experience

### New Project with Integration

```bash
# User has both tools installed
$ backlog init "my-project"
✓ Backlog.md initialized

$ guardkit init --backend backlog.md
✓ GuardKit initialized with Backlog.md integration
✓ MCP connection verified

$ guardkit task-create "Implement user authentication"
🔍 Gathering requirements...
📝 Generated EARS specification: specs/auth.ears
🧪 Generated BDD scenarios: specs/auth.gherkin
✓ Created task in Backlog.md: task-1 - Implement user authentication

$ backlog board
┌─────────────┬─────────────┬──────────┐
│   To Do     │ In Progress │   Done   │
├─────────────┼─────────────┼──────────┤
│ task-1      │             │          │
│ [guardkit]  │             │          │
│ Auth system │             │          │
└─────────────┴─────────────┴──────────┘
```

### Existing GuardKit Project Adding Backlog.md

```bash
$ guardkit config set task_backend backlog.md
⚠️  Backlog.md not initialized in this directory.
    Run 'backlog init' first, or use --auto-init

$ guardkit config set task_backend backlog.md --auto-init
✓ Initialized Backlog.md
✓ Migrated 5 existing tasks to Backlog.md
✓ Task backend updated
```

---

## Risk Mitigation

### Risk: Backlog.md API Changes

**Mitigation:** Version-lock MCP schema, maintain compatibility layer

```python
class BacklogMdStorage(TaskStorage):
    SUPPORTED_VERSIONS = ["1.25", "1.26"]
    
    async def _check_version(self):
        version = await self.mcp.call("version")
        if version not in self.SUPPORTED_VERSIONS:
            logger.warning(f"Untested Backlog.md version: {version}")
```

### Risk: MCP Connection Failures

**Mitigation:** Graceful fallback to native storage

```python
async def get_storage() -> TaskStorage:
    config = load_config()
    
    if config.task_backend == "backlog.md":
        try:
            storage = BacklogMdStorage()
            await storage.health_check()
            return storage
        except MCPConnectionError:
            logger.warning("Backlog.md unavailable, using native storage")
            return NativeStorage()
    
    return NativeStorage()
```

### Risk: Feature Parity Gaps

**Mitigation:** Document limitations, provide escape hatches

```markdown
## Known Limitations with Backlog.md Integration

1. **Spec References:** Stored in task notes, not dedicated field
2. **Quality Gates:** Not visible in Backlog.md UI (GuardKit enforces)
3. **Agent History:** Not synced to Backlog.md
```

---

## Decision Points

### Recommended Approach

✅ **Do:** Implement as optional plugin with clean separation  
✅ **Do:** Use MCP as primary integration mechanism  
✅ **Do:** Maintain 100% standalone functionality  
✅ **Do:** Store spec references in Backlog.md notes field  

❌ **Don't:** Make Backlog.md a hard dependency  
❌ **Don't:** Duplicate task metadata in both systems  
❌ **Don't:** Try to sync agent orchestration state  
❌ **Don't:** Build a custom Kanban UI when Backlog.md exists  

### Alternative Considered: Deep Integration

We considered a deeper integration where GuardKit would directly read/write Backlog.md's markdown files. This was rejected because:

1. **Coupling:** Changes to Backlog.md file format would break GuardKit
2. **Maintenance:** Two codebases parsing the same files
3. **Conflicts:** Potential for file-level merge conflicts
4. **MCP exists:** The official integration path is MCP, not file parsing

---

## Conclusion

The plugin architecture keeps GuardKit focused on its core value proposition (specification-driven development with quality gates) while allowing users to leverage Backlog.md's excellent task management capabilities when desired.

**Key Principle:** GuardKit should work perfectly at guardkit.ai as a standalone tool. Backlog.md integration is a power-user feature that adds visual task management without compromising the core experience.

**Next Step:** Ship GuardKit standalone first, then add Backlog.md integration in a subsequent release.
