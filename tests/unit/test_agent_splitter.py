"""
Unit tests for agent content splitter.

Tests the progressive disclosure pattern implementation for agent files.
"""

import pytest
from pathlib import Path


# Sample agent content for testing
SAMPLE_FULL_AGENT = """---
name: api-specialist
description: FastAPI endpoint specialist
tools: [Read, Write, Edit, Grep, Bash]
tags: [python, fastapi, api]
stack: python
phase: implementation
capabilities: [api-design, async-patterns, pydantic]
keywords: [endpoint, router, fastapi]
priority: 9
---

# API Specialist

## Overview

This agent specializes in creating FastAPI endpoints following best practices.

## Purpose

Helps developers implement RESTful APIs with proper structure and error handling.

## Boundaries

### ALWAYS
- ✅ Use async/await for database operations (prevents thread blocking)
- ✅ Validate input with Pydantic models (type safety)
- ✅ Return proper HTTP status codes (REST compliance)
- ✅ Implement error handling (robust APIs)
- ✅ Use dependency injection (testability)

### NEVER
- ❌ Never use synchronous database calls (blocks event loop)
- ❌ Never skip input validation (security risk)
- ❌ Never return 200 for errors (misleading clients)
- ❌ Never hardcode credentials (security violation)
- ❌ Never ignore exceptions (silent failures)

### ASK
- ⚠️ Pagination needed for large datasets: Ask about page size limits
- ⚠️ Authentication required: Ask about auth method (JWT/OAuth/API key)
- ⚠️ Rate limiting needed: Ask about limits and strategy

## Quick Start

### Example 1: Basic GET endpoint
```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

### Example 2: POST with validation
```python
@router.post("/users")
async def create_user(user: UserCreate):
    return {"id": 1, "name": user.name}
```

### Example 3: Async database query
```python
@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    users = await db.query(User).all()
    return users
```

## Capabilities

- REST API design
- Async/await patterns
- Input validation
- Error handling
- Dependency injection

## Phase Integration

Used in Phase 3 (Implementation) for creating API endpoints.

## Loading Extended Content

For detailed examples and best practices, see `api-specialist-ext.md`.

## Detailed Examples

### Example 4: Complex validation
```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    age: int

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

### Example 5: Error handling
```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    try:
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Example 6: Pagination
```python
@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    users = await db.query(User).offset(skip).limit(limit).all()
    return users
```

### Example 7: Authentication
```python
@router.get("/users/me")
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
```

### Example 8: File upload
```python
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}
```

## Best Practices

### 1. Always use type hints
Type hints improve code clarity and enable IDE autocompletion.

### 2. Validate all inputs
Use Pydantic models to validate request bodies and query parameters.

### 3. Use dependency injection
Inject database sessions and other dependencies rather than creating them in routes.

### 4. Return appropriate status codes
Use 200 for success, 201 for creation, 404 for not found, etc.

### 5. Handle errors gracefully
Catch exceptions and return meaningful error messages to clients.

## Anti-Patterns

### 1. Synchronous database calls
```python
# ❌ BAD
@router.get("/users")
def list_users():
    users = db.query(User).all()  # Blocks event loop
    return users

# ✅ GOOD
@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    users = await db.query(User).all()
    return users
```

### 2. Missing error handling
```python
# ❌ BAD
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return await db.get(user_id)  # No null check

# ✅ GOOD
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await db.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user
```

### 3. Hardcoded credentials
```python
# ❌ BAD
DATABASE_URL = "postgresql://user:password@localhost/db"

# ✅ GOOD
DATABASE_URL = os.getenv("DATABASE_URL")
```

## Technology-Specific Guidance

### FastAPI specifics
- Use `async def` for async operations
- Leverage automatic OpenAPI docs
- Use `Depends()` for dependency injection

### Pydantic models
- Create separate models for request/response
- Use validators for complex validation
- Enable ORM mode for database models

## Troubleshooting

### Issue: Async database calls failing
**Solution**: Ensure you're using an async database driver (asyncpg, motor, etc.)

### Issue: Validation errors not showing
**Solution**: Enable debug mode and check Pydantic model configuration.

### Issue: CORS errors
**Solution**: Add CORSMiddleware with appropriate origins.
"""


class TestAgentSplitter:
    """Test suite for agent_splitter module."""

    def test_split_agent_basic(self):
        """Test basic agent splitting into core and extended parts."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, extended = split_agent_content(SAMPLE_FULL_AGENT)

        # Core should contain essential sections
        assert "## Boundaries" in core
        assert "## Quick Start" in core
        assert "## Capabilities" in core
        assert "## Phase Integration" in core
        assert "## Loading Extended Content" in core

        # Extended should contain detailed sections
        assert "## Detailed Examples" in extended
        assert "## Best Practices" in extended
        assert "## Anti-Patterns" in extended
        assert "## Technology-Specific Guidance" in extended
        assert "## Troubleshooting" in extended

    def test_core_contains_frontmatter(self):
        """Test that core file retains frontmatter."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, _ = split_agent_content(SAMPLE_FULL_AGENT)

        assert "---" in core
        assert "name: api-specialist" in core
        assert "description: FastAPI endpoint specialist" in core

    def test_core_size_target(self):
        """Test core file meets size target (6-10KB)."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, _ = split_agent_content(SAMPLE_FULL_AGENT)
        core_size = len(core.encode('utf-8'))

        # Warning threshold is 15KB
        assert core_size <= 15 * 1024, f"Core file too large: {core_size / 1024:.1f}KB"

        # Should be substantial enough to be useful
        assert core_size >= 1 * 1024, f"Core file too small: {core_size / 1024:.1f}KB"

    def test_extended_size_target(self):
        """Test extended file has reasonable size."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        _, extended = split_agent_content(SAMPLE_FULL_AGENT)
        extended_size = len(extended.encode('utf-8'))

        # Warning threshold is 30KB
        assert extended_size <= 30 * 1024, f"Extended file too large: {extended_size / 1024:.1f}KB"

    def test_cross_references_added(self):
        """Test cross-references between core and extended files."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, extended = split_agent_content(SAMPLE_FULL_AGENT)

        # Core should reference extended file
        assert "-ext.md" in core

        # Extended should reference core
        assert ("main agent file" in extended.lower() or
                "core file" in extended.lower() or
                "see `" in extended.lower())

    def test_quick_start_limited_examples(self):
        """Test that core Quick Start contains only first 5-10 examples."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, extended = split_agent_content(SAMPLE_FULL_AGENT)

        # Core should have Examples 1-3 (from Quick Start)
        assert "Example 1:" in core
        assert "Example 2:" in core
        assert "Example 3:" in core

        # Extended should have Examples 4+ (from Detailed Examples)
        assert "Example 4:" in extended
        assert "Example 5:" in extended
        assert "Example 6:" in extended

    def test_boundaries_in_core(self):
        """Test that all boundary sections are in core."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, extended = split_agent_content(SAMPLE_FULL_AGENT)

        # All boundaries should be in core
        assert "### ALWAYS" in core
        assert "### NEVER" in core
        assert "### ASK" in core

        # Boundaries should not be duplicated in extended
        assert "### ALWAYS" not in extended
        assert "### NEVER" not in extended
        assert "### ASK" not in extended

    def test_size_validation_warnings(self):
        """Test size validation produces warnings for oversized files."""
        from installer.core.lib.agent_generator.agent_splitter import validate_split_sizes

        # Create oversized content
        core = "x" * (16 * 1024)  # 16KB (over 15KB warning threshold)
        extended = "y" * (31 * 1024)  # 31KB (over 30KB warning threshold)

        warnings = validate_split_sizes(core, extended)

        assert len(warnings) == 2
        assert any("core" in w.lower() for w in warnings)
        assert any("extended" in w.lower() for w in warnings)

    def test_size_validation_no_warnings(self):
        """Test size validation produces no warnings for properly sized files."""
        from installer.core.lib.agent_generator.agent_splitter import validate_split_sizes

        # Create properly sized content
        core = "x" * (8 * 1024)  # 8KB (within 6-10KB target)
        extended = "y" * (20 * 1024)  # 20KB (within 15-25KB target)

        warnings = validate_split_sizes(core, extended)

        assert len(warnings) == 0

    def test_empty_agent_content(self):
        """Test handling of empty agent content."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        with pytest.raises(ValueError, match="Agent content cannot be empty"):
            split_agent_content("")

    def test_minimal_agent_content(self):
        """Test handling of minimal agent (frontmatter only)."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        minimal = """---
name: test-agent
description: Test agent
---

# Test Agent

Basic agent content.
"""

        core, extended = split_agent_content(minimal)

        # Core should have all content when there's not much to split
        assert "# Test Agent" in core

        # Extended should be empty or have minimal content
        assert len(extended) < len(core)

    def test_agent_without_boundaries(self):
        """Test handling of agent missing boundary sections."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        no_boundaries = """---
name: simple-agent
---

# Simple Agent

## Overview
Some overview text.

## Quick Start
Example code here.
"""

        core, extended = split_agent_content(no_boundaries)

        # Should still split, just without boundaries in core
        assert "# Simple Agent" in core
        assert "## Overview" in core

    def test_preserve_code_blocks(self):
        """Test that code blocks are preserved correctly during split."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, extended = split_agent_content(SAMPLE_FULL_AGENT)

        # Code blocks should be preserved with backticks
        assert "```python" in core
        assert "```" in core

        # Extended should also have code blocks
        if "```python" in extended:
            assert "```" in extended

    def test_preserve_frontmatter_formatting(self):
        """Test that frontmatter formatting is preserved."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core, _ = split_agent_content(SAMPLE_FULL_AGENT)

        # Frontmatter should be properly delimited
        lines = core.split('\n')
        assert lines[0] == '---'
        # Find closing delimiter
        closing_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                closing_idx = i
                break

        assert closing_idx is not None, "Frontmatter closing delimiter not found"
        assert closing_idx > 1, "Frontmatter should have content"
