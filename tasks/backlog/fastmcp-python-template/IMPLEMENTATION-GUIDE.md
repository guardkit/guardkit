# Implementation Guide: FastMCP Python Template

## Wave Breakdown

### Wave 1: Foundation (Parallel - 2 tasks)

Foundation files that other tasks depend on.

| Task | Title | Mode | Workspace | Dependencies |
|------|-------|------|-----------|--------------|
| TASK-FMT-001 | Create manifest.json | task-work | fastmcp-wave1-1 | None |
| TASK-FMT-002 | Create settings.json | task-work | fastmcp-wave1-2 | None |

**Rationale**: manifest.json and settings.json are independent and can be created in parallel. They define the template's identity and conventions.

---

### Wave 2: Core Content (Parallel - 4 tasks)

Main template content that uses Wave 1 conventions.

| Task | Title | Mode | Workspace | Dependencies |
|------|-------|------|-----------|--------------|
| TASK-FMT-003 | Create fastmcp-specialist agent | task-work | fastmcp-wave2-1 | TASK-FMT-002 |
| TASK-FMT-004 | Create fastmcp-testing-specialist agent | task-work | fastmcp-wave2-2 | TASK-FMT-002 |
| TASK-FMT-005 | Create code templates | task-work | fastmcp-wave2-3 | TASK-FMT-002 |
| TASK-FMT-006 | Create .claude/rules | task-work | fastmcp-wave2-4 | TASK-FMT-002 |

**Rationale**: All Wave 2 tasks depend on settings.json (Wave 1) for naming conventions but are independent of each other. Maximum parallelization.

---

### Wave 3: Integration (Sequential - 2 tasks)

Final integration and validation.

| Task | Title | Mode | Workspace | Dependencies |
|------|-------|------|-----------|--------------|
| TASK-FMT-007 | Create CLAUDE.md files | direct | N/A | TASK-FMT-003, FMT-004, FMT-005, FMT-006 |
| TASK-FMT-008 | Validate template | direct | N/A | TASK-FMT-007 |

**Rationale**: CLAUDE.md files summarize agent capabilities (need Wave 2). Validation runs after everything is complete.

---

## Execution Strategy

### Conductor Parallel Execution

**Wave 1** (2 parallel workspaces):
```bash
# In separate terminals or Conductor sessions
conductor create fastmcp-wave1-1
/task-work TASK-FMT-001

conductor create fastmcp-wave1-2
/task-work TASK-FMT-002
```

**Wave 2** (4 parallel workspaces):
```bash
# After Wave 1 completes
conductor create fastmcp-wave2-1
/task-work TASK-FMT-003

conductor create fastmcp-wave2-2
/task-work TASK-FMT-004

conductor create fastmcp-wave2-3
/task-work TASK-FMT-005

conductor create fastmcp-wave2-4
/task-work TASK-FMT-006
```

**Wave 3** (sequential, direct implementation):
```bash
# After Wave 2 completes
# Direct implementation without /task-work
# Create CLAUDE.md files
# Run /template-validate
```

---

## File Structure Target

```
installer/core/templates/fastmcp-python/
├── .claude/
│   ├── CLAUDE.md                              # Wave 3
│   └── rules/
│       ├── mcp-patterns.md                    # Wave 2 (FMT-006)
│       ├── testing.md                         # Wave 2 (FMT-006)
│       ├── docker.md                          # Wave 2 (FMT-006)
│       └── config.md                          # Wave 2 (FMT-006)
├── agents/
│   ├── fastmcp-specialist.md                  # Wave 2 (FMT-003)
│   ├── fastmcp-specialist-ext.md              # Wave 2 (FMT-003)
│   ├── fastmcp-testing-specialist.md          # Wave 2 (FMT-004)
│   └── fastmcp-testing-specialist-ext.md      # Wave 2 (FMT-004)
├── templates/
│   ├── server/
│   │   ├── __main__.py.template               # Wave 2 (FMT-005)
│   │   └── server.py.template                 # Wave 2 (FMT-005)
│   ├── tools/
│   │   └── tool.py.template                   # Wave 2 (FMT-005)
│   ├── resources/
│   │   └── resource.py.template               # Wave 2 (FMT-005)
│   ├── config/
│   │   ├── pyproject.toml.template            # Wave 2 (FMT-005)
│   │   └── Dockerfile.template                # Wave 2 (FMT-005)
│   └── testing/
│       ├── conftest.py.template               # Wave 2 (FMT-005)
│       └── test_tool.py.template              # Wave 2 (FMT-005)
├── manifest.json                              # Wave 1 (FMT-001)
├── settings.json                              # Wave 1 (FMT-002)
├── CLAUDE.md                                  # Wave 3 (FMT-007)
└── README.md                                  # Wave 3 (FMT-007)
```

---

## Quality Gates Per Wave

### Wave 1 Quality Gates
- [ ] manifest.json passes JSON schema validation
- [ ] settings.json passes JSON schema validation
- [ ] Both files reference each other correctly

### Wave 2 Quality Gates
- [ ] Agents have proper frontmatter (name, stack, capabilities, keywords)
- [ ] Agents include ALWAYS/NEVER boundaries
- [ ] All 10 critical patterns embedded in agents
- [ ] Templates include placeholders ({{ServerName}}, {{ToolName}}, etc.)
- [ ] Rules reference agents correctly

### Wave 3 Quality Gates
- [ ] `/template-validate` passes with 0 errors
- [ ] Quality score 8+/10
- [ ] All cross-references resolve

---

## Critical Pattern Mapping

| Pattern | Agent Location | Template Location | Rule Location |
|---------|---------------|-------------------|---------------|
| FastMCP not custom | fastmcp-specialist ALWAYS | server.py.template | mcp-patterns.md |
| __main__.py registration | fastmcp-specialist ALWAYS | __main__.py.template | mcp-patterns.md |
| stderr logging | fastmcp-specialist ALWAYS | __main__.py.template | mcp-patterns.md |
| Streaming two-layer | fastmcp-specialist capability | tool.py.template (streaming) | mcp-patterns.md |
| CancelledError handling | fastmcp-specialist ALWAYS | tool.py.template | mcp-patterns.md |
| String param conversion | fastmcp-specialist ALWAYS | tool.py.template | mcp-patterns.md |
| Absolute paths | fastmcp-specialist NEVER | N/A | config.md |
| datetime.now(UTC) | fastmcp-specialist ALWAYS | tool.py.template | mcp-patterns.md |
| Protocol testing | fastmcp-testing-specialist | test_tool.py.template | testing.md |
| Docker patterns | fastmcp-specialist | Dockerfile.template | docker.md |

### Gap Analysis Additions (TASK-REV-A7F9)

| Pattern | Agent Location | Template Location | Rule Location |
|---------|---------------|-------------------|---------------|
| **Idempotent operations** | fastmcp-specialist ALWAYS | N/A | mcp-patterns.md |
| **Pagination cursors** | fastmcp-specialist capability | paginated_tool.py.template | mcp-patterns.md |
| **Structured content** | fastmcp-specialist ALWAYS | tool.py.template | mcp-patterns.md |
| **Health checks** | fastmcp-specialist capability | health_check_tool.py.template | mcp-patterns.md |
| **Circuit breaker** | fastmcp-specialist-ext | N/A | mcp-patterns.md |
| **OAuth 2.1 security** | N/A | N/A | security.md |
| **SSE deprecation** | N/A | N/A | security.md |

---

## Estimated Effort

| Wave | Tasks | Parallel Time | Serial Time |
|------|-------|---------------|-------------|
| Wave 1 | 2 | 30 min | 60 min |
| Wave 2 | 4 | 90 min | 360 min |
| Wave 3 | 2 | 30 min | 60 min |
| **Total** | **8** | **~2.5 hrs** | **~8 hrs** |

**Conductor efficiency gain**: 68% time savings with parallel execution.
