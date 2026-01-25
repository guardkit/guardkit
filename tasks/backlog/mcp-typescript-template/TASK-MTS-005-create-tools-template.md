---
id: TASK-MTS-005
title: Create tools/tool.ts.template and related templates
status: backlog
task_type: feature
created: 2026-01-24T16:45:00Z
updated: 2026-01-24T16:45:00Z
priority: high
tags: [template, mcp, typescript, tools, resources, prompts]
complexity: 4
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 2
parallel_group: wave2
implementation_mode: task-work
conductor_workspace: mcp-ts-wave2-2
dependencies:
  - TASK-MTS-001  # manifest.json for placeholders
---

# Task: Create tools/tool.ts.template and related templates

## Description

Create code templates for MCP primitives: tools, resources, and prompts. These templates provide scaffolding for the three core MCP capabilities.

## Reference

Use `.claude/reviews/TASK-REV-4371-review-report.md` Sections 3 and 6 for patterns.
Use Context7 TypeScript SDK documentation for API signatures.

## Deliverables

### 1. tools/tool.ts.template

```typescript
/**
 * {{ToolName}} - MCP Tool
 * {{Description}}
 */

import * as z from 'zod';

// Input schema with Zod validation
export const {{toolName}}Schema = {
    {{paramName}}: z.string().describe('{{ParamDescription}}')
};

// Output type (optional, for structuredContent)
export interface {{ToolName}}Output {
    result: string;
    // Add more fields as needed
}

// Implementation function (testable independently)
export async function {{toolName}}Impl(
    params: z.infer<typeof {{toolName}}Schema>
): Promise<{{ToolName}}Output> {
    const { {{paramName}} } = params;

    // TODO: Implement tool logic
    return {
        result: `Processed: ${{{paramName}}}`
    };
}

// Tool registration helper (use in index.ts)
export function register{{ToolName}}(server: McpServer) {
    server.registerTool(
        '{{tool-name}}',
        {
            title: '{{ToolTitle}}',
            description: '{{Description}}',
            inputSchema: {{toolName}}Schema,
            outputSchema: {
                result: z.string()
            }
        },
        async (params) => {
            const output = await {{toolName}}Impl(params);
            return {
                content: [{ type: 'text', text: JSON.stringify(output) }],
                structuredContent: output
            };
        }
    );
}
```

### 2. resources/resource.ts.template

```typescript
/**
 * {{ResourceName}} - MCP Resource
 * {{Description}}
 */

import { ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';

// Static resource registration
export function registerStatic{{ResourceName}}(server: McpServer) {
    server.registerResource(
        '{{resource-name}}',
        '{{protocol}}://{{path}}',
        {
            title: '{{ResourceTitle}}',
            description: '{{Description}}',
            mimeType: 'application/json'
        },
        async (uri) => ({
            contents: [{
                uri: uri.href,
                text: JSON.stringify({
                    // Resource data here
                })
            }]
        })
    );
}

// Dynamic resource with URI template
export function registerDynamic{{ResourceName}}(server: McpServer) {
    server.registerResource(
        '{{resource-name}}',
        new ResourceTemplate('{{protocol}}://{id}/{{path}}', {
            list: undefined
        }),
        {
            title: '{{ResourceTitle}}',
            description: '{{Description}}'
        },
        async (uri, { id }) => ({
            contents: [{
                uri: uri.href,
                mimeType: 'application/json',
                text: JSON.stringify({ id, data: '...' })
            }]
        })
    );
}
```

### 3. prompts/prompt.ts.template

```typescript
/**
 * {{PromptName}} - MCP Prompt
 * {{Description}}
 */

import * as z from 'zod';
import { completable } from '@modelcontextprotocol/sdk/server/completable.js';

// Prompt registration
export function register{{PromptName}}(server: McpServer) {
    server.registerPrompt(
        '{{prompt-name}}',
        {
            title: '{{PromptTitle}}',
            description: '{{Description}}',
            argsSchema: {
                {{argName}}: z.string().describe('{{ArgDescription}}')
            }
        },
        ({ {{argName}} }) => ({
            messages: [{
                role: 'user',
                content: {
                    type: 'text',
                    text: `{{PromptTemplate}}\n\n${{{argName}}}`
                }
            }]
        })
    );
}

// Prompt with argument completion
export function register{{PromptName}}WithCompletion(server: McpServer) {
    server.registerPrompt(
        '{{prompt-name}}',
        {
            title: '{{PromptTitle}}',
            description: '{{Description}}',
            argsSchema: {
                {{argName}}: completable(
                    z.string().describe('{{ArgDescription}}'),
                    (value) => {
                        // Return completion suggestions
                        return ['option1', 'option2'].filter(o => o.startsWith(value));
                    }
                )
            }
        },
        ({ {{argName}} }) => ({
            messages: [{
                role: 'user',
                content: { type: 'text', text: `Process: ${{{argName}}}` }
            }]
        })
    );
}
```

## Acceptance Criteria

- [ ] tools/tool.ts.template created with Zod schema and registration helper
- [ ] resources/resource.ts.template created with static and dynamic patterns
- [ ] prompts/prompt.ts.template created with completion support
- [ ] All templates use proper placeholders from manifest.json
- [ ] All templates include TypeScript types
- [ ] All templates demonstrate best practices

## Test Execution Log

[Automatically populated by /task-work]
