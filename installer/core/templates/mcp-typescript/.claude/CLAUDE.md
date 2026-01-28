# MCP TypeScript Template Context

## Template Information

| Property | Value |
|----------|-------|
| Template | mcp-typescript |
| SDK | @modelcontextprotocol/sdk |
| Language | TypeScript |
| Runtime | Node.js (>=18) |

## 10 Critical MCP Patterns

1. **Use McpServer** - Not the raw Server class. McpServer provides the high-level API with proper typing and simplified registration.

2. **Register before connect()** - Tool order matters. All `server.tool()`, `server.resource()`, and `server.prompt()` calls must happen before `server.connect(transport)`.

3. **stderr logging** - `console.error()` only. Never use console.log() as it corrupts the JSON-RPC protocol on stdout.

4. **Streaming two-layer** - Implementation + wrapper. For streaming responses, implement the generator and wrap it with the SDK's streaming utilities.

5. **Error handling** - Try/catch in streams. Wrap async generators with proper error handling to avoid silent failures.

6. **Zod validation** - Type-safe schemas. Use Zod for all input validation. The SDK integrates with Zod for automatic schema generation.

7. **Absolute paths** - In all configuration. Claude Desktop and other clients require absolute paths to the server executable.

8. **ISO timestamps** - `new Date().toISOString()`. Use ISO 8601 format for all timestamps in responses.

9. **Protocol testing** - JSON-RPC manual tests. Test the raw protocol with shell scripts to verify correct message formatting.

10. **Docker non-root** - Security best practice. Run MCP servers as non-root users in containers.

## Testing Strategy

### Unit Tests (Vitest)

Test tool logic in isolation:

```typescript
import { describe, it, expect } from 'vitest';
import { myToolHandler } from '../src/tools/my-tool';

describe('myTool', () => {
  it('should process input correctly', async () => {
    const result = await myToolHandler({ input: 'test' });
    expect(result.content[0].text).toContain('test');
  });
});
```

### Protocol Tests

Test JSON-RPC communication:

```bash
# Send initialize request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{}}}' | node dist/index.js
```

## Troubleshooting

### Tools not discovered

**Symptom**: Claude cannot see your tools after connection.

**Cause**: Tools registered after `server.connect()` call.

**Solution**: Ensure all `server.tool()` calls happen before `server.connect(transport)`.

### Protocol corruption

**Symptom**: Server crashes or Claude shows parse errors.

**Cause**: `console.log()` statements in server code.

**Solution**: Remove all console.log statements. Use `console.error()` for logging.

### Type errors with Zod

**Symptom**: TypeScript errors when defining tool schemas.

**Cause**: Incorrect Zod schema structure or missing `.shape` accessor.

**Solution**: Pass the Zod schema's `.shape` property to `server.tool()`:

```typescript
const Schema = z.object({ input: z.string() });
server.tool('name', 'desc', Schema.shape, handler);
```

### Connection timeout

**Symptom**: Server starts but Claude never connects.

**Cause**: Server not calling `server.connect()` or transport misconfiguration.

**Solution**: Verify the server calls `await server.connect(transport)` at startup.

## Extended Rules

For detailed patterns and best practices, see the extended rules in `.claude/rules/`:

- `mcp-patterns.md` - MCP-specific patterns and examples
- `testing.md` - Testing strategies for MCP servers
- `transport.md` - Transport layer configuration
- `configuration.md` - Environment and deployment configuration
