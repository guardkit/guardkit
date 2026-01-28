---
paths: ["config/**/*.json", "*.json", "package.json", "tsconfig.json"]
---

# MCP Server Configuration

## Claude Desktop Configuration

Configure your MCP server in Claude Desktop's config file:

**Location**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration**:
```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### CRITICAL: Absolute Paths Required

**Always use ABSOLUTE paths** in Claude Desktop config:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": [
        "/Users/username/projects/my-mcp-server/dist/index.js"
      ]
    }
  }
}
```

**Wrong** (relative paths will fail):
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["./dist/index.js"]  // FAILS!
    }
  }
}
```

**Why**: Claude Desktop runs from its own working directory, not your project directory.

## Environment Variables

Pass configuration via environment variables:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"],
      "env": {
        "API_KEY": "sk-...",
        "API_BASE_URL": "https://api.example.com",
        "LOG_LEVEL": "debug",
        "MAX_RETRIES": "3"
      }
    }
  }
}
```

Access in your server:
```typescript
const API_KEY = process.env.API_KEY;
const LOG_LEVEL = process.env.LOG_LEVEL || "info";
const MAX_RETRIES = parseInt(process.env.MAX_RETRIES || "3");

if (!API_KEY) {
  console.error("[Config] Error: API_KEY is required");
  process.exit(1);
}
```

## package.json Scripts

Define standard npm scripts:

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc && node -e \"require('fs').chmodSync('dist/index.js',0o755)\"",
    "start": "node dist/index.js",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "inspector": "npx @modelcontextprotocol/inspector node dist/index.js"
  },
  "bin": {
    "my-mcp-server": "./dist/index.js"
  }
}
```

### Script Purposes

- **dev**: Run in development with hot reload (tsx watch)
- **build**: Compile TypeScript and make executable
- **start**: Run production build
- **test**: Run unit tests with Vitest
- **test:coverage**: Generate coverage report
- **inspector**: Launch MCP Inspector for debugging

## tsconfig.json for ESM

Configure TypeScript for ES Modules:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### Key Settings

- **module**: "Node16" for native ESM support
- **moduleResolution**: "Node16" for proper .js imports
- **target**: "ES2022" for modern JavaScript
- **strict**: true for maximum type safety

## Multiple Server Configurations

Run multiple MCP servers in Claude Desktop:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["/path/to/filesystem-server/dist/index.js"]
    },
    "weather": {
      "command": "node",
      "args": ["/path/to/weather-server/dist/index.js"],
      "env": {
        "WEATHER_API_KEY": "..."
      }
    },
    "database": {
      "command": "node",
      "args": ["/path/to/db-server/dist/index.js"],
      "env": {
        "DB_CONNECTION_STRING": "postgresql://..."
      }
    }
  }
}
```

## Server Naming Convention

Use clear, descriptive server names:

```json
{
  "mcpServers": {
    "acme-api": {  // Company-specific
      "command": "node",
      "args": ["/path/to/acme-api-server/dist/index.js"]
    },
    "github-tools": {  // Service-specific
      "command": "node",
      "args": ["/path/to/github-server/dist/index.js"]
    },
    "local-files": {  // Function-specific
      "command": "node",
      "args": ["/path/to/filesystem-server/dist/index.js"]
    }
  }
}
```

## Configuration Validation

Validate configuration at server startup:

```typescript
interface ServerConfig {
  apiKey: string;
  apiBaseUrl: string;
  logLevel: "debug" | "info" | "warn" | "error";
  maxRetries: number;
}

function validateConfig(): ServerConfig {
  const apiKey = process.env.API_KEY;
  const apiBaseUrl = process.env.API_BASE_URL || "https://api.example.com";
  const logLevel = process.env.LOG_LEVEL as ServerConfig["logLevel"] || "info";
  const maxRetries = parseInt(process.env.MAX_RETRIES || "3");

  if (!apiKey) {
    throw new Error("API_KEY environment variable is required");
  }

  if (!["debug", "info", "warn", "error"].includes(logLevel)) {
    throw new Error(`Invalid LOG_LEVEL: ${logLevel}`);
  }

  if (maxRetries < 0 || maxRetries > 10) {
    throw new Error(`MAX_RETRIES must be between 0 and 10, got ${maxRetries}`);
  }

  return { apiKey, apiBaseUrl, logLevel, maxRetries };
}

// At server startup
const config = validateConfig();
console.error("[Config] Loaded configuration:", {
  apiBaseUrl: config.apiBaseUrl,
  logLevel: config.logLevel,
  maxRetries: config.maxRetries
});
```

## Secrets Management

Never commit secrets to version control:

```typescript
// Use environment variables
const API_KEY = process.env.API_KEY;

// OR load from secure file (gitignored)
import { readFileSync } from "fs";
const secrets = JSON.parse(
  readFileSync("/secure/path/secrets.json", "utf-8")
);
```

**.gitignore**:
```
.env
.env.*
secrets.json
config/local.json
claude_desktop_config.json
```

## Development vs Production Config

Use different configs for dev/prod:

```typescript
const isDev = process.env.NODE_ENV !== "production";

const config = {
  logLevel: isDev ? "debug" : "info",
  apiBaseUrl: isDev
    ? "http://localhost:3000"
    : "https://api.production.com",
  maxRetries: isDev ? 1 : 3
};
```

## HTTP Server Configuration (Production)

For HTTP/SSE transport:

```typescript
const PORT = parseInt(process.env.PORT || "3000");
const HOST = process.env.HOST || "0.0.0.0";
const CORS_ORIGIN = process.env.CORS_ORIGIN || "*";

const app = express();

app.use(cors({ origin: CORS_ORIGIN }));

app.listen(PORT, HOST, () => {
  console.error(`[Server] HTTP server running on ${HOST}:${PORT}`);
});
```
