# FastMCP Python Server Template

## Project Context

This is a **production-ready FastMCP server template** for building MCP (Model Context Protocol) servers using the FastMCP framework. The template embeds 10 critical production patterns that prevent common MCP failures and ensure protocol compliance.

## Core Principles

1. **Protocol-First**: stdout reserved for MCP protocol, all logging to stderr
2. **Async Architecture**: Leverage FastMCP's async capabilities for I/O operations
3. **Type Safety**: Comprehensive Pydantic validation for tool parameters
4. **Test Coverage**: Full MCP protocol compliance testing
5. **Production Ready**: Error handling, resource management, idempotent operations

## Architecture Overview

### Flat MCP Structure

```
{{ProjectName}}/
├── src/
│   ├── __main__.py              # Server entry point (CRITICAL: module-level tool registration)
│   ├── tools/                   # MCP tool implementations
│   │   ├── basic_tool.py
│   │   ├── streaming_tool.py
│   │   └── paginated_tool.py
│   ├── resources/               # MCP resource implementations
│   │   └── resource_handler.py
│   └── models/                  # Pydantic models
│       ├── tool_params.py
│       └── responses.py
│
├── tests/                       # MCP protocol compliance tests
│   ├── test_tools.py
│   ├── test_resources.py
│   ├── test_protocol.py
│   └── conftest.py
│
├── pyproject.toml               # Package metadata and dependencies
├── Dockerfile                   # Container for MCP server
└── .env                         # Configuration (never in MCP stdout)
```

## The 10 Critical Patterns

These patterns prevent common MCP failures and ensure protocol compliance. Each pattern is essential for production-ready MCP servers.

| # | Pattern | Critical Rule | Details |
|---|---------|--------------|---------|
| 1 | Tool Registration | Register at module level in `__main__.py` (never in functions) | See `.claude/rules/mcp-patterns.md` |
| 2 | Logging to stderr | ALL logging to `stream=sys.stderr` (stdout breaks protocol) | See `.claude/rules/mcp-patterns.md` |
| 3 | Streaming Two-Layer | Inner `_impl()` generator + outer tool wrapper | See `.claude/rules/mcp-patterns.md` |
| 4 | CancelledError Handling | Always catch, log, and re-raise `asyncio.CancelledError` | See `.claude/rules/mcp-patterns.md` |
| 5 | String Parameter Conversion | MCP sends all params as strings - convert explicitly | See `.claude/rules/mcp-patterns.md` |
| 6 | DateTime with UTC | Use `datetime.now(timezone.utc)` not deprecated `utcnow()` | See `.claude/rules/mcp-patterns.md` |
| 7 | FastMCP Not Custom | Use `FastMCP()` framework, never custom `Server()` classes | See `.claude/rules/mcp-patterns.md` |
| 8 | Error Propagation Boundaries | Catch at tool boundary, return structured error dict | See `.claude/rules/mcp-patterns.md` |
| 9 | Resource URI Patterns | Use `@mcp.resource()` with proper URI schemes (`data://`, `config://`) | See `.claude/rules/mcp-patterns.md` |
| 10 | Async Context Injection | Use `@asynccontextmanager` for resource lifespan management | See `.claude/rules/mcp-patterns.md` |

**Quick Reference**: The patterns file (`.claude/rules/mcp-patterns.md`) contains complete code examples, anti-patterns, and detailed explanations for each of these critical patterns.

## Detailed Pattern Documentation

For complete implementation details of all 10 critical patterns:

- **MCP Patterns**: See `.claude/rules/mcp-patterns.md` for exhaustive examples
- **Testing Patterns**: See `.claude/rules/testing.md` for MCP protocol compliance tests
- **Configuration**: See `.claude/rules/config.md` for environment setup
- **Security**: See `.claude/rules/security.md` for input validation and resource limits
- **Docker**: See `.claude/rules/docker.md` for containerization

## Technology Stack

### Core Framework
- **FastMCP**: Simplified MCP server framework
- **Pydantic** (>=2.0.0): Data validation and settings
- **Python** (>=3.10): Async/await support

### Testing
- **pytest** (>=7.4.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **mcp-client**: MCP protocol testing

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker

## Getting Started

### 1. Initialize Template
```bash
guardkit init fastmcp-python
cd my-mcp-server
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

### 3. Configure Server
Edit `src/__main__.py` to add your tools:

```python
@mcp.tool()
async def my_custom_tool(input: str) -> dict:
    """Description for Claude Code."""
    return {"result": f"Processed: {input}"}
```

### 4. Run Server
```bash
# Run in stdio mode (for MCP clients)
python -m src

# Test with MCP client
mcp-client --server "python -m src"
```

### 5. Run Tests
```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term
```

### 6. Docker Deployment
```bash
docker build -t my-mcp-server .
docker run -i my-mcp-server
```

## Common Commands

```bash
# Development
pip install -e ".[dev]"        # Install with dev dependencies
python -m src                  # Run MCP server

# Testing
pytest tests/ -v               # Run all tests
pytest tests/ --cov=src        # Run with coverage
pytest tests/test_tools.py     # Run specific test

# Quality
ruff check src/ tests/         # Lint code
ruff format src/ tests/        # Format code
mypy src/                      # Type check

# Docker
docker build -t server .       # Build image
docker run -i server           # Run server
```

## Quality Scores

This template achieves the following quality metrics:

- **SOLID Compliance**: 85/100 (Tool isolation, single responsibility)
- **DRY Score**: 85/100 (Minimal code duplication)
- **YAGNI Score**: 90/100 (Essential MCP patterns only)
- **Complexity Rating**: 5/10 (Medium - MCP protocol constraints)

**Key Strengths**:
- ✅ Zero stdout violations (protocol compliance)
- ✅ Full async/await support
- ✅ Comprehensive error handling
- ✅ Idempotent operation support
- ✅ Cursor-based pagination

**Limitations**:
- MCP protocol requires all parameters as strings (explicit conversion needed)
- stdout reserved for protocol (constrains debugging)
- FastMCP framework required (no custom Server classes)

## Naming Conventions

### Tool Names
```python
# Use snake_case
@mcp.tool()
async def search_patterns(query: str) -> dict:
    pass

@mcp.tool()
async def get_pattern_details(id: str) -> dict:
    pass
```

### Server Names
```bash
# Use kebab-case with -server suffix
design-patterns-server
requirements-server
context7-server
```

### Resource Names
```python
# Use snake_case
@mcp.resource("data://patterns_list")
async def get_patterns_list() -> str:
    pass
```

### MCP Parameters
```python
# Use camelCase (MCP protocol convention)
@mcp.tool()
async def search(
    libraryName: str,  # camelCase per MCP spec
    maxResults: str,   # All params are strings
    searchType: str
) -> dict:
    pass
```

## Key Patterns Quick Reference

| Pattern | Location | Example |
|---------|----------|---------|
| Tool Registration | `src/__main__.py` | `@mcp.tool()` at module level |
| Logging Setup | Top of `__main__.py` | `stream=sys.stderr` |
| Parameter Types | Tool signatures | All `str`, convert in body |
| Error Handling | Tool body | Catch, log, return structured error |
| Async Context | Tool body | `async with get_resource()` |
| Resource URIs | Resource decorator | `@mcp.resource("data://{id}")` |
| Pagination | List tools | Cursor-based, limit ≤100 |
| Idempotency | Mutating tools | Accept `request_id` param |
| Testing | `tests/` | Protocol compliance + unit tests |

## Specialized Agents Available

This template works with the following specialized AI agents:

- **fastmcp-specialist**: FastMCP patterns, tool registration, protocol compliance
- **fastmcp-testing-specialist**: MCP protocol testing, async fixtures, client simulation

Use these agents during development for specialized guidance on MCP server implementation.

## Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Servers Collection](https://github.com/modelcontextprotocol/servers)

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
