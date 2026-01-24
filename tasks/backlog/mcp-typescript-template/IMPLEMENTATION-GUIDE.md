# Implementation Guide: MCP TypeScript Template

## Overview

This guide provides wave-by-wave execution strategy for implementing the `mcp-typescript` GuardKit template.

**Total Subtasks**: 11
**Estimated Effort**: 8-12 hours
**Parallel Execution**: Waves 1-3 support Conductor workspaces

---

## Wave Breakdown

### Wave 1: Foundation (Parallel)

**Tasks**: 3 | **Estimated**: 2-3 hours | **Dependencies**: None

These tasks can run in parallel using Conductor workspaces.

| Task | Title | Workspace | Mode |
|------|-------|-----------|------|
| MTS-001 | Create manifest.json | mcp-ts-wave1-1 | task-work |
| MTS-002 | Create settings.json | mcp-ts-wave1-2 | task-work |
| MTS-003 | Create mcp-typescript-specialist agent | mcp-ts-wave1-3 | task-work |

**Execution**:
```bash
# Option 1: Sequential
/task-work TASK-MTS-001
/task-work TASK-MTS-002
/task-work TASK-MTS-003

# Option 2: Parallel (Conductor)
conductor create mcp-ts-wave1-1 && cd .conductor/mcp-ts-wave1-1 && /task-work TASK-MTS-001
conductor create mcp-ts-wave1-2 && cd .conductor/mcp-ts-wave1-2 && /task-work TASK-MTS-002
conductor create mcp-ts-wave1-3 && cd .conductor/mcp-ts-wave1-3 && /task-work TASK-MTS-003
```

**Wave 1 Completion Criteria**:
- [ ] manifest.json created at `installer/core/templates/mcp-typescript/manifest.json`
- [ ] settings.json created at `installer/core/templates/mcp-typescript/settings.json`
- [ ] Core agent created at `installer/core/templates/mcp-typescript/agents/mcp-typescript-specialist.md`

---

### Wave 2: Templates (Parallel)

**Tasks**: 3 | **Estimated**: 3-4 hours | **Dependencies**: MTS-001

These tasks can run in parallel after Wave 1 completes.

| Task | Title | Workspace | Mode |
|------|-------|-----------|------|
| MTS-004 | Create server/index.ts.template | mcp-ts-wave2-1 | task-work |
| MTS-005 | Create tools/tool.ts.template | mcp-ts-wave2-2 | task-work |
| MTS-006 | Create config templates | mcp-ts-wave2-3 | task-work |

**Execution**:
```bash
# After Wave 1 complete
/task-work TASK-MTS-004
/task-work TASK-MTS-005
/task-work TASK-MTS-006
```

**Wave 2 Completion Criteria**:
- [ ] Server entry point template created
- [ ] Tool implementation template created
- [ ] Config templates created (package.json, tsconfig.json, claude-desktop.json)

---

### Wave 3: Testing & Rules (Parallel)

**Tasks**: 3 | **Estimated**: 2-3 hours | **Dependencies**: MTS-003, MTS-005

| Task | Title | Workspace | Mode |
|------|-------|-----------|------|
| MTS-007 | Create mcp-testing-specialist agent | mcp-ts-wave3-1 | task-work |
| MTS-008 | Create .claude/rules/ files | mcp-ts-wave3-2 | task-work |
| MTS-009 | Create test templates | mcp-ts-wave3-3 | task-work |

**Execution**:
```bash
# After Wave 2 complete
/task-work TASK-MTS-007
/task-work TASK-MTS-008
/task-work TASK-MTS-009
```

**Wave 3 Completion Criteria**:
- [ ] Testing specialist agent created
- [ ] Rules files created (mcp-patterns.md, testing.md, transport.md, configuration.md)
- [ ] Test templates created (tool.test.ts.template, protocol.sh.template)

---

### Wave 4: Documentation (Sequential)

**Tasks**: 2 | **Estimated**: 1-2 hours | **Dependencies**: All previous

These tasks must run sequentially after all other waves complete.

| Task | Title | Mode |
|------|-------|------|
| MTS-010 | Create CLAUDE.md files | task-work |
| MTS-011 | Validate template | task-work |

**Execution**:
```bash
# After Wave 3 complete
/task-work TASK-MTS-010
/task-work TASK-MTS-011
```

**Wave 4 Completion Criteria**:
- [ ] Top-level CLAUDE.md created
- [ ] Nested .claude/CLAUDE.md created
- [ ] Template validation passes (`/template-validate`)

---

## Template File Structure

```
installer/core/templates/mcp-typescript/
├── manifest.json                        # MTS-001
├── settings.json                        # MTS-002
├── CLAUDE.md                            # MTS-010
├── README.md                            # MTS-010
│
├── .claude/
│   ├── CLAUDE.md                        # MTS-010
│   └── rules/
│       ├── mcp-patterns.md              # MTS-008
│       ├── testing.md                   # MTS-008
│       ├── transport.md                 # MTS-008
│       └── configuration.md             # MTS-008
│
├── agents/
│   ├── mcp-typescript-specialist.md     # MTS-003
│   ├── mcp-typescript-specialist-ext.md # MTS-003
│   ├── mcp-testing-specialist.md        # MTS-007
│   └── mcp-testing-specialist-ext.md    # MTS-007
│
└── templates/
    ├── server/
    │   └── index.ts.template            # MTS-004
    ├── tools/
    │   └── tool.ts.template             # MTS-005
    ├── resources/
    │   └── resource.ts.template         # MTS-005
    ├── prompts/
    │   └── prompt.ts.template           # MTS-005
    ├── config/
    │   ├── package.json.template        # MTS-006
    │   ├── tsconfig.json.template       # MTS-006
    │   └── claude-desktop.json.template # MTS-006
    ├── testing/
    │   ├── tool.test.ts.template        # MTS-009
    │   └── protocol.sh.template         # MTS-009
    └── docker/
        ├── Dockerfile.template          # MTS-006
        └── docker-compose.yml.template  # MTS-006
```

---

## Reference Materials

### Pattern Mapping (From Review Report)

| Python Pattern | TypeScript Equivalent |
|---------------|----------------------|
| FastMCP() | McpServer() |
| @mcp.tool() decorator | server.registerTool() |
| logging to stderr | console.error() |
| Pydantic validation | Zod schema validation |
| __main__.py entry | src/index.ts entry |
| asyncio patterns | async/await with Promises |

### Key Code Patterns

**Server Entry Point**:
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import * as z from 'zod';

const server = new McpServer({
    name: '{{ServerName}}',
    version: '1.0.0'
});

// Register tools BEFORE connect
server.registerTool('{{toolName}}', {
    title: '{{ToolTitle}}',
    description: '{{Description}}',
    inputSchema: { param: z.string() }
}, async ({ param }) => ({
    content: [{ type: 'text', text: JSON.stringify({ result: param }) }]
}));

const transport = new StdioServerTransport();
await server.connect(transport);
console.error('{{ServerName}} started'); // stderr only!
```

**Tool Template**:
```typescript
import * as z from 'zod';

export const {{toolName}}Schema = {
    param: z.string().describe('{{ParamDescription}}')
};

export async function {{toolName}}Impl({ param }: { param: string }) {
    // Implementation here
    return { result: param };
}
```

---

## Quality Gates

Each task must pass:
1. **Compilation**: TypeScript compiles without errors
2. **Validation**: JSON files are valid
3. **Pattern Compliance**: Follows 10 critical MCP patterns
4. **Template Standards**: Follows GuardKit template conventions

Final validation (MTS-011):
```bash
/template-validate installer/core/templates/mcp-typescript
```

---

## Troubleshooting

### Common Issues

1. **Tool not discovered by Claude Code**
   - Check: Tool registered BEFORE `server.connect()`
   - Check: Using McpServer, not raw Server class

2. **MCP protocol corruption**
   - Check: No `console.log()` statements
   - Check: All logging uses `console.error()`

3. **Type errors**
   - Check: Zod schema matches function signature
   - Check: Proper type inference from inputSchema

4. **Claude Desktop won't connect**
   - Check: Absolute paths in config
   - Check: Node.js version compatible (20+)

---

## Post-Implementation

After all waves complete:

1. **Integration Test**: Create sample MCP server using template
2. **Documentation Review**: Ensure README accurate
3. **Cross-Reference**: Update TASK-REV-4371 with completion status
4. **Announcement**: Template available for `guardkit init mcp-typescript`
