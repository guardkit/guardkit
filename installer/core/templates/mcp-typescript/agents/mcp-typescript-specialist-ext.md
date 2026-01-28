# mcp-typescript-specialist - Extended Reference

This file contains detailed documentation for the `mcp-typescript-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/mcp-typescript-specialist-ext.md
```


## Code Patterns

### Minimal Server Setup
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new McpServer({
    name: 'my-server',
    version: '1.0.0'
});

// Register tools BEFORE connect
server.registerTool('hello', { ... }, async () => { ... });

const transport = new StdioServerTransport();
await server.connect(transport);

console.error('Server started successfully');
```

### Tool Registration with Zod
```typescript
import * as z from 'zod';

server.registerTool(
    'search-patterns',
    {
        title: 'Search Patterns',
        description: 'Search for design patterns by query',
        inputSchema: {
            query: z.string().describe('Search query'),
            limit: z.number().default(5).describe('Maximum results')
        },
        outputSchema: {
            patterns: z.array(z.object({
                name: z.string(),
                category: z.string(),
                score: z.number()
            }))
        }
    },
    async ({ query, limit }) => {
        console.error(`Searching for: ${query}, limit: ${limit}`);

        const patterns = await searchPatterns(query, limit);

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({ patterns }, null, 2)
            }],
            structuredContent: { patterns }
        };
    }
);
```

### Resource Registration
```typescript
import { ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';

// Static resource
server.registerResource(
    'config',
    'config://app',
    { title: 'Application Configuration' },
    async () => ({
        contents: [{
            uri: 'config://app',
            text: JSON.stringify(appConfig, null, 2)
        }]
    })
);

// Dynamic resource with template
server.registerResource(
    'user-profile',
    new ResourceTemplate('users://{userId}/profile', {
        list: undefined,
        complete: {
            userId: (value) =>
                getUserIds().filter(id => id.startsWith(value))
        }
    }),
    { title: 'User Profile' },
    async (uri, { userId }) => ({
        contents: [{
            uri: uri.href,
            text: JSON.stringify(await getUser(userId))
        }]
    })
);
```

### Prompt Registration
```typescript
import { completable } from '@modelcontextprotocol/sdk/server/completable.js';
import * as z from 'zod';

server.registerPrompt(
    'code-review',
    {
        title: 'Code Review',
        description: 'Review code for best practices',
        argsSchema: {
            language: completable(
                z.string(),
                (value) => ['typescript', 'python', 'rust', 'go']
                    .filter(l => l.startsWith(value))
            ),
            focus: z.enum(['security', 'performance', 'style']).default('style')
        }
    },
    ({ language, focus }) => ({
        messages: [{
            role: 'user',
            content: {
                type: 'text',
                text: `Review the following ${language} code with focus on ${focus}:`
            }
        }]
    })
);
```

### Streaming Two-Layer Architecture
```typescript
// Layer 1: Implementation (pure async generator)
async function* streamingImpl(data: { param: string }): AsyncGenerator<Event> {
    yield { event: 'start', timestamp: new Date().toISOString() };

    for (const item of await processData(data)) {
        yield { event: 'progress', item };
    }

    yield { event: 'done', timestamp: new Date().toISOString() };
}

// Layer 2: MCP Wrapper (collects generator output)
server.registerTool(
    'streaming-tool',
    {
        inputSchema: { param: z.string() },
        outputSchema: { events: z.array(z.any()) }
    },
    async ({ param }) => {
        const events: Event[] = [];

        for await (const event of streamingImpl({ param })) {
            events.push(event);
            console.error(`Event: ${event.event}`);
        }

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({ events })
            }],
            structuredContent: { events }
        };
    }
);
```

### Error Handling Patterns
```typescript
// In streaming implementation
async function* streamingImpl(): AsyncGenerator<Event> {
    try {
        yield { event: 'start' };

        const result = await riskyOperation();
        yield { event: 'success', result };

    } catch (error) {
        console.error('Operation failed:', error);
        yield { event: 'error', error: String(error) };
        throw error; // Re-throw for proper async semantics

    } finally {
        console.error('Cleanup complete');
    }
}

// In tool handler
server.registerTool(
    'safe-tool',
    { inputSchema: { data: z.string() } },
    async ({ data }) => {
        try {
            const result = await processData(data);
            return {
                content: [{ type: 'text', text: JSON.stringify(result) }]
            };
        } catch (error) {
            console.error('Tool error:', error);
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        error: true,
                        message: error instanceof Error ? error.message : String(error)
                    })
                }],
                isError: true
            };
        }
    }
);
```


## Anti-Patterns to Avoid

1. **Using console.log() for logging**
   ```typescript
   // BAD - corrupts MCP protocol
   console.log('Processing request');

   // GOOD - uses stderr
   console.error('Processing request');
   ```

2. **Registering tools after connect()**
   ```typescript
   // BAD - tools won't be discoverable
   await server.connect(transport);
   server.registerTool('my-tool', ...);

   // GOOD - register before connect
   server.registerTool('my-tool', ...);
   await server.connect(transport);
   ```

3. **Using raw Server class**
   ```typescript
   // BAD - low-level, error-prone
   import { Server } from '@modelcontextprotocol/sdk/server/index.js';

   // GOOD - high-level API
   import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
   ```

4. **Skipping Zod validation**
   ```typescript
   // BAD - no type safety
   async ({ param }) => {
       const count = parseInt(param); // param might not be a string!
   }

   // GOOD - Zod handles coercion
   inputSchema: { count: z.number().default(10) }
   ```

5. **Using relative paths in config**
   ```json
   // BAD - won't work from different directories
   {
       "command": "npx",
       "args": ["tsx", "./src/index.ts"]
   }

   // GOOD - works everywhere
   {
       "command": "/absolute/path/to/node",
       "args": ["--import", "tsx", "/absolute/path/to/src/index.ts"]
   }
   ```

6. **Forgetting structuredContent**
   ```typescript
   // BAD - no machine-readable output
   return {
       content: [{ type: 'text', text: JSON.stringify(result) }]
   };

   // GOOD - includes structured data
   return {
       content: [{ type: 'text', text: JSON.stringify(result) }],
       structuredContent: result
   };
   ```

7. **Not testing with JSON-RPC commands**
   ```bash
   # BAD - only unit tests (miss protocol issues)
   npm test

   # GOOD - verify protocol compliance
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize",...}' | npx tsx src/index.ts
   ```


## Technology Stack Context
- @modelcontextprotocol/sdk: Official MCP SDK (Anthropic)
- Zod 3.25+: Schema validation with TypeScript inference
- TypeScript 5.0+: Strict mode recommended
- Node.js 20+: Native ESM support
- tsx 4.0+: Fast TypeScript execution for development
- esbuild 0.20+: Production bundling


## Template Best Practices

### Server Initialization
- Always set both `name` and `version` in McpServer constructor
- Use descriptive server names (kebab-case)
- Log server startup to stderr for debugging
- Handle SIGINT/SIGTERM for graceful shutdown

### Tool Design
- Use descriptive tool names (kebab-case)
- Provide meaningful descriptions for tools and parameters
- Set sensible defaults using Zod `.default()`
- Include both human-readable `content` and machine-readable `structuredContent`

### Schema Design
- Use Zod's `.describe()` for parameter documentation
- Prefer specific types over `z.any()`
- Use `.optional()` and `.default()` appropriately
- Document enum values with descriptions

### Error Handling
- Log errors to stderr with context
- Return `isError: true` for tool errors
- Include meaningful error messages in content
- Never throw unhandled exceptions from handlers

### Configuration
- Use absolute paths in claude_desktop_config.json
- Set `NODE_ENV=production` for deployed servers
- Configure appropriate timeouts for long operations


## Template Anti-Patterns

### DON'T: Mix stdout and stderr
```typescript
// Stdout is RESERVED for JSON-RPC protocol
// Any stdout output breaks MCP communication
console.log('Debug info');  // WRONG
console.error('Debug info');  // CORRECT
```

### DON'T: Forget to validate environment
```typescript
// WRONG - crashes with unclear error
const apiKey = process.env.API_KEY;
callApi(apiKey);

// CORRECT - validate early with clear message
const apiKey = process.env.API_KEY;
if (!apiKey) {
    console.error('ERROR: API_KEY environment variable required');
    process.exit(1);
}
```

### DON'T: Block the event loop
```typescript
// WRONG - blocks all requests
server.registerTool('cpu-heavy', ..., async () => {
    const result = heavyComputation();  // Synchronous!
    return { content: [...] };
});

// CORRECT - use async patterns
server.registerTool('cpu-heavy', ..., async () => {
    const result = await runInWorker(heavyComputation);
    return { content: [...] };
});
```

### DON'T: Hardcode configuration
```typescript
// WRONG - not portable
const config = {
    apiUrl: 'http://localhost:3000'
};

// CORRECT - use environment
const config = {
    apiUrl: process.env.API_URL || 'http://localhost:3000'
};
```


## Related Templates

This specialist works with the following MCP TypeScript templates:

### Server Templates
- **templates/server/index.ts.template** - Entry point with STDIO transport
- **templates/server/http-server.ts.template** - HTTP transport for production

### Tool Templates
- **templates/tools/tool.ts.template** - Basic tool with Zod validation
- **templates/tools/streaming-tool.ts.template** - Two-layer streaming pattern

### Resource Templates
- **templates/resources/static-resource.ts.template** - Static resource provider
- **templates/resources/dynamic-resource.ts.template** - Template-based resources

### Prompt Templates
- **templates/prompts/prompt.ts.template** - Basic prompt with arguments
- **templates/prompts/completable-prompt.ts.template** - Prompt with argument completion

### Configuration Templates
- **templates/config/package.json.template** - Package configuration
- **templates/config/tsconfig.json.template** - TypeScript configuration
- **templates/config/claude-desktop.json.template** - Claude Desktop integration

### Testing Templates
- **templates/testing/tool.test.ts.template** - Vitest unit tests
- **templates/testing/protocol.sh.template** - JSON-RPC protocol tests

### Docker Templates
- **templates/docker/Dockerfile.template** - Multi-stage production build
- **templates/docker/docker-compose.yml.template** - Development compose

---


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat mcp-typescript-specialist-ext.md
```

Or in Claude Code:
```
Please read mcp-typescript-specialist-ext.md for detailed examples.
```
