# Code Examples

## General Examples

**File**: `src/lib/query.js`
**Purpose**: Source file (query)

See template files for complete implementation examples.

## Testing Examples

**File**: `test/run_chat.js`
**Purpose**: Source file (run_chat)

See template files for complete implementation examples.

## Infrastructure Examples

**File**: `src/lib/databaseListeners.js`
**Purpose**: Source file (databaseListeners)

See template files for complete implementation examples.


# Naming Conventions

## Other
**Pattern**: `query`
**Examples**:
- `query.js`
- `update-sessions-weather.js`
- `upload-sessions.js`


# Agent Usage

This template includes specialized agents tailored to this project's patterns:

## General Agents

### alasql-in-memory-database-specialist
**Purpose**: AlaSQL in-memory database with Firestore data synchronization, object flattening, and real-time listeners for analytics

**When to Use**: Use this agent when implementing data access layers, working with databases, or creating repository patterns

### complex-form-validation-specialist
**Purpose**: Multi-section forms with conditional validation, recent data loading, and dynamic field requirements

**When to Use**: Use this agent when creating UI components, implementing views, or working with user interfaces

### external-api-integration-specialist
**Purpose**: External weather API integration (Open-Meteo) with historical and forecast data, timezone handling, and error management

**When to Use**: Use this agent when implementing data access layers, working with databases, or creating repository patterns

### firebase-firestore-specialist
**Purpose**: Firebase Firestore CRUD operations with authentication guards, joins, and data transformation for karting equipment and sessions

**When to Use**: Use this agent when creating UI components, implementing views, or working with user interfaces

### openai-chat-specialist
**Purpose**: OpenAI function calling with streaming responses, karting data analysis using SQL queries, and conversation management

**When to Use**: Use this agent when implementing data access layers, working with databases, or creating repository patterns

### pwa-vite-specialist
**Purpose**: Progressive Web App with Vite, service workers, offline caching strategies, and manifest configuration

**When to Use**: Use this agent when working with pwa vite specialist

## Ui Agents

### svelte5-component-specialist
**Purpose**: Svelte 5 components with SMUI Material Design, form validation, and reactive data patterns

**When to Use**: Use this agent when creating UI components, implementing views, or working with user interfaces

## General Guidance

- Use agents when implementing features that match their expertise
- Agents understand this project's specific patterns and conventions
- For tasks outside agent specializations, rely on general Claude capabilities

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
