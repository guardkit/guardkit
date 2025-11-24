# Agent Response Format Specification

**Version**: 1.0
**Task**: TASK-FIX-267C
**Last Updated**: 2025-11-24

## Overview

This document specifies the correct format for `.agent-response.json` files used in the checkpoint-resume pattern for agent invocations.

## Critical Requirements

### 1. Field Name: `response` (NOT `result`)

❌ **WRONG**:
```json
{
  "result": { ... }
}
```

✅ **CORRECT**:
```json
{
  "response": "..."
}
```

### 2. Data Type: JSON String (NOT Object)

❌ **WRONG**:
```json
{
  "response": {
    "sections": [...]
  }
}
```

✅ **CORRECT**:
```json
{
  "response": "{\"sections\": [...]}"
}
```

### 3. All Required Fields Must Be Present

The following fields are **required** in every response:

- `request_id` (string)
- `version` (string)
- `status` (string)
- `response` (string or null)
- `error_message` (string or null)
- `error_type` (string or null)
- `created_at` (string, ISO 8601)
- `duration_seconds` (number)
- `metadata` (object)

## Complete Schema

```json
{
  "request_id": "string (UUID from request file)",
  "version": "string (use '1.0')",
  "status": "string ('success' | 'error' | 'timeout')",
  "response": "string (JSON-encoded agent output) or null",
  "error_message": "string (error description) or null",
  "error_type": "string (error type) or null",
  "created_at": "string (ISO 8601 timestamp)",
  "duration_seconds": "number (seconds as float)",
  "metadata": "object (can be empty {})"
}
```

## Field Specifications

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `request_id` | string | ✅ | UUID from `.agent-request.json` | `"32ecfadc-2b66-4daa-a7c0-a03c449fcea5"` |
| `version` | string | ✅ | Protocol version | `"1.0"` |
| `status` | string | ✅ | Response status | `"success"` or `"error"` or `"timeout"` |
| `response` | string or null | ✅ | JSON-encoded agent output | `"{\"sections\": [...]}"` |
| `error_message` | string or null | ✅ | Error description (null for success) | `null` or `"Timeout after 120s"` |
| `error_type` | string or null | ✅ | Error type (null for success) | `null` or `"timeout"` |
| `created_at` | string | ✅ | ISO 8601 timestamp with timezone | `"2025-11-24T14:22:45.123456+00:00"` |
| `duration_seconds` | number | ✅ | Execution time in seconds | `1.0` or `120.5` |
| `metadata` | object | ✅ | Additional metadata (can be empty) | `{}` or `{"model": "sonnet-4"}` |

## Valid Examples

### Success Response

```json
{
  "request_id": "32ecfadc-2b66-4daa-a7c0-a03c449fcea5",
  "version": "1.0",
  "status": "success",
  "response": "{\"sections\": [\"related_templates\", \"examples\", \"boundaries\"], \"related_templates\": \"## Related Templates\\n\\n- template1\", \"examples\": \"## Examples\\n\\n### Example 1\", \"boundaries\": \"## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1\"}",
  "error_message": null,
  "error_type": null,
  "created_at": "2025-11-24T14:22:45.123456+00:00",
  "duration_seconds": 1.0,
  "metadata": {}
}
```

### Error Response

```json
{
  "request_id": "32ecfadc-2b66-4daa-a7c0-a03c449fcea5",
  "version": "1.0",
  "status": "error",
  "response": null,
  "error_message": "Agent execution timeout after 120 seconds",
  "error_type": "timeout",
  "created_at": "2025-11-24T14:24:45.123456+00:00",
  "duration_seconds": 120.0,
  "metadata": {}
}
```

## Generation Algorithm

### Python Implementation

```python
import json
from datetime import datetime, timezone

# Step 1: Create agent output as Python dict
agent_output = {
    "sections": ["related_templates", "examples", "boundaries"],
    "related_templates": "## Related Templates\n\n- template1",
    "examples": "## Code Examples\n\n### Example 1\n```code```",
    "boundaries": "## Boundaries\n\n### ALWAYS\n- ✅ Rule 1"
}

# Step 2: Read request file to get request_id
with open(".agent-request.json", "r") as f:
    request = json.load(f)
    request_id = request["request_id"]

# Step 3: Create response envelope with correct format
response_data = {
    "request_id": request_id,
    "version": "1.0",
    "status": "success",
    "response": json.dumps(agent_output),  # ← JSON-encode the output
    "error_message": None,
    "error_type": None,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "duration_seconds": 1.0,
    "metadata": {}
}

# Step 4: Write to file with proper formatting
with open(".agent-response.json", "w", encoding="utf-8") as f:
    json.dump(response_data, f, indent=2, ensure_ascii=False)
```

**Key Steps**:
1. Create agent output as Python dict
2. **JSON-encode** it using `json.dumps(agent_output)`
3. Place the JSON string in the `response` field
4. Include all required fields with correct types
5. Write with UTF-8 encoding and pretty formatting

## Why Two-Level JSON Parsing?

The design uses **two-level JSON parsing** for clarity and flexibility:

```
┌─────────────────────────────────────────┐
│ .agent-response.json (file)             │
│ {                                        │
│   "request_id": "...",                   │
│   "response": "{\"sections\": [...]}"    │ ← Outer JSON (envelope)
│ }                                        │
└─────────────────────────────────────────┘
              ↓ json.loads(file)
┌─────────────────────────────────────────┐
│ AgentResponse object                     │
│   request_id: "..."                      │
│   response: "{\"sections\": [...]}"      │ ← JSON string
└─────────────────────────────────────────┘
              ↓ json.loads(response.response)
┌─────────────────────────────────────────┐
│ Agent output (dict)                      │
│ {                                        │
│   "sections": ["boundaries"],            │
│   "boundaries": "..."                    │ ← Actual content
│ }                                        │
└─────────────────────────────────────────┘
```

**Benefits**:
1. **Language-agnostic**: Response can be JSON, Markdown, XML, or plain text
2. **Size handling**: Large responses can be compressed/encoded as strings
3. **Validation separation**: Parse errors caught separately from response errors
4. **Flexibility**: Supports multiple content types without schema changes
5. **Explicit parsing**: Two-level parse makes data flow explicit

## Common Mistakes

### Mistake 1: Using "result" Instead of "response"

```json
// ❌ WRONG
{
  "result": "{...}"
}

// ✅ CORRECT
{
  "response": "{...}"
}
```

**Error**: `TypeError: AgentResponse.__init__() got an unexpected keyword argument 'result'`

### Mistake 2: Response as Object Instead of String

```json
// ❌ WRONG
{
  "response": {"sections": [...]}
}

// ✅ CORRECT
{
  "response": "{\"sections\": [...]}"
}
```

**Error**: `TypeError: Expected str, got dict` (when parsing inner JSON)

### Mistake 3: Missing json.dumps() Encoding

```python
# ❌ WRONG
response_data = {
    "response": agent_output  # Dict instead of JSON string
}

# ✅ CORRECT
response_data = {
    "response": json.dumps(agent_output)  # JSON-encoded string
}
```

### Mistake 4: Missing Required Fields

```json
// ❌ WRONG - Incomplete
{
  "status": "success",
  "response": "{...}"
}

// ✅ CORRECT - All required fields
{
  "request_id": "...",
  "version": "1.0",
  "status": "success",
  "response": "{...}",
  "error_message": null,
  "error_type": null,
  "created_at": "...",
  "duration_seconds": 1.0,
  "metadata": {}
}
```

**Error**: `TypeError: missing required positional arguments`

### Mistake 5: Wrong Type for duration_seconds

```json
// ❌ WRONG
{
  "duration_seconds": "1.0"  // String
}

// ✅ CORRECT
{
  "duration_seconds": 1.0  // Number
}
```

## Validation

### Manual Validation

Use the provided validation script:

```bash
python3 docs/validation/agent-response-format-test.py
```

### Python Code Validation

```python
import json
from installer.global.lib.agent_bridge.invoker import AgentResponse

# Load response file
with open(".agent-response.json", "r") as f:
    response_data = json.load(f)

# Validate structure
try:
    response = AgentResponse(**response_data)
    print("✅ Response structure valid")
except TypeError as e:
    print(f"❌ Invalid structure: {e}")

# Validate inner JSON
try:
    agent_output = json.loads(response.response)
    print("✅ Agent output parsed successfully")
except json.JSONDecodeError as e:
    print(f"❌ Invalid inner JSON: {e}")
```

## Schema Definition

See `installer/global/lib/agent_bridge/invoker.py` for the authoritative `AgentResponse` dataclass definition:

```python
@dataclass
class AgentResponse:
    """Agent invocation response."""
    request_id: str
    version: str
    status: str
    response: Optional[str]
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    created_at: str
    duration_seconds: float
    metadata: dict
```

## Related Tasks

- **TASK-FIX-D4E5**: Checkpoint-resume mechanism (working correctly)
- **TASK-FIX-A7D3**: Python import scoping (unrelated)
- **TASK-FIX-267C**: This format specification (documentation)

## References

- Implementation: `installer/global/lib/agent_bridge/invoker.py`
- Validation: `docs/validation/agent-response-format-test.py`
- Task: `tasks/in_progress/TASK-FIX-267C-fix-claude-code-agent-response-json-format-error.md`
