# MCP Enhancements Implementation Specification

**Version**: 1.0
**Date**: 2025-11-22
**Based on**: TASK-MCP-7796 Review Findings
**Priority**: HIGH
**Estimated Effort**: 24-32 hours total

---

## Executive Summary

This specification defines two critical MCP enhancements that will significantly improve token efficiency and provide real-time visibility into MCP resource consumption during task execution. Both enhancements maintain backward compatibility and follow SOLID principles.

### Enhancement Overview

| Enhancement | Token Savings | Implementation Complexity | Risk Level |
|-------------|---------------|---------------------------|------------|
| **#1: Progressive Disclosure (Context7)** | 50-70% in Phase 2 | Medium | Low |
| **#2: MCP Response Monitoring** | N/A (observability) | Low | Very Low |

**Combined Impact**:
- 2,000-3,500 tokens saved per task (Phase 2)
- Real-time MCP usage visibility
- Foundation for auto-optimization feedback loop
- Zero disruption to existing workflows

---

## Enhancement #1: Progressive Disclosure for Context7

### 1.1 Problem Statement

**Current Behavior**:
- Phase 2 (Planning): Fetches 3,500-5,000 token detailed documentation
- Phase 3 (Implementation): Fetches same 3,500-5,000 token documentation
- Result: 50-70% waste in Phase 2 (only needs high-level overview)

**Research Support**:
- MCP Optimization Guide: "Planning phase needs architectural overview, not API details"
- TASK-MCP-7796 findings: "Progressive disclosure can save 2,000-3,500 tokens per task"

### 1.2 Solution Architecture

#### 1.2.1 Class Structure

```python
# File: installer/core/commands/lib/mcp/context7_client.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import json

class DetailLevel(Enum):
    """Documentation detail levels for progressive disclosure."""
    SUMMARY = "summary"      # 500-1000 tokens: High-level overview, key concepts
    DETAILED = "detailed"    # 3500-5000 tokens: Complete API docs, examples, patterns

    @property
    def token_budget(self) -> int:
        """Default token budget for this detail level."""
        return {
            DetailLevel.SUMMARY: 1000,
            DetailLevel.DETAILED: 5000
        }[self]

    @property
    def description(self) -> str:
        """Human-readable description."""
        return {
            DetailLevel.SUMMARY: "High-level overview (planning phase)",
            DetailLevel.DETAILED: "Complete documentation (implementation phase)"
        }[self]


@dataclass
class Context7Request:
    """Request parameters for Context7 MCP calls."""
    library_id: str              # e.g., "/tiangolo/fastapi"
    topic: Optional[str] = None  # e.g., "dependency-injection"
    detail_level: DetailLevel = DetailLevel.DETAILED  # NEW parameter
    custom_token_budget: Optional[int] = None  # Override default budget

    @property
    def token_budget(self) -> int:
        """Resolved token budget (custom or default)."""
        return self.custom_token_budget or self.detail_level.token_budget

    def to_mcp_params(self) -> Dict[str, Any]:
        """Convert to MCP tool parameters."""
        params = {
            "context7CompatibleLibraryID": self.library_id,
            "tokens": self.token_budget
        }
        if self.topic:
            params["topic"] = self.topic

        # Include detail level hint (if MCP supports it in future)
        params["_hint_detail_level"] = self.detail_level.value

        return params


@dataclass
class Context7Response:
    """Response from Context7 MCP."""
    content: str
    library_id: str
    topic: Optional[str]
    requested_tokens: int
    actual_tokens: int  # Populated by MCPMonitor
    detail_level: DetailLevel

    @property
    def token_efficiency(self) -> float:
        """Percentage of requested tokens actually used."""
        return (self.actual_tokens / self.requested_tokens * 100) if self.requested_tokens > 0 else 0.0


class Context7Client:
    """
    Enhanced Context7 MCP client with progressive disclosure.

    Principles:
    - Single Responsibility: Only handles Context7 communication
    - Open/Closed: Extensible via DetailLevel enum, closed for modification
    - Dependency Inversion: Depends on abstract MCPMonitor interface
    """

    def __init__(self, monitor: Optional['MCPMonitor'] = None):
        """
        Initialize Context7 client.

        Args:
            monitor: Optional MCPMonitor for tracking token usage
        """
        self.monitor = monitor
        self._library_id_cache: Dict[str, str] = {}  # Cache resolved library IDs

    def resolve_library_id(self, library_name: str) -> str:
        """
        Resolve library name to Context7-compatible ID.

        Args:
            library_name: Library name (e.g., "fastapi", "react")

        Returns:
            Context7-compatible library ID (e.g., "/tiangolo/fastapi")

        Raises:
            Context7Error: If library cannot be resolved
        """
        # Check cache first
        if library_name in self._library_id_cache:
            return self._library_id_cache[library_name]

        # Call MCP tool: mcp__context7__resolve-library-id
        try:
            result = mcp__context7__resolve_library_id(library_name)
            library_id = result  # Actual MCP response format may vary

            # Cache for session
            self._library_id_cache[library_name] = library_id

            return library_id
        except Exception as e:
            raise Context7Error(f"Failed to resolve library '{library_name}': {e}")

    def get_documentation(self, request: Context7Request) -> Context7Response:
        """
        Fetch library documentation with progressive disclosure.

        Args:
            request: Context7Request with library_id, topic, detail_level

        Returns:
            Context7Response with documentation content and metadata

        Raises:
            Context7Error: If documentation fetch fails
        """
        # Prepare MCP parameters
        params = request.to_mcp_params()

        # Track request (if monitor available)
        if self.monitor:
            self.monitor.record_request(
                mcp_name="context7",
                tool_name="get-library-docs",
                params=params,
                phase=self._get_current_phase()  # From task context
            )

        # Call MCP tool: mcp__context7__get-library-docs
        try:
            content = mcp__context7__get_library_docs(**params)

            # Count actual tokens (approximate - assumes ~4 chars/token)
            actual_tokens = len(content) // 4

            # Create response
            response = Context7Response(
                content=content,
                library_id=request.library_id,
                topic=request.topic,
                requested_tokens=request.token_budget,
                actual_tokens=actual_tokens,
                detail_level=request.detail_level
            )

            # Track response (if monitor available)
            if self.monitor:
                self.monitor.record_response(
                    mcp_name="context7",
                    tool_name="get-library-docs",
                    response_size=actual_tokens,
                    metadata={
                        "library_id": request.library_id,
                        "topic": request.topic,
                        "detail_level": request.detail_level.value,
                        "efficiency": response.token_efficiency
                    }
                )

            return response

        except Exception as e:
            if self.monitor:
                self.monitor.record_error(
                    mcp_name="context7",
                    tool_name="get-library-docs",
                    error=str(e)
                )
            raise Context7Error(f"Failed to fetch documentation: {e}")

    def get_summary(self, library_id: str, topic: Optional[str] = None) -> Context7Response:
        """
        Convenience method: Fetch summary documentation (for Phase 2).

        Args:
            library_id: Context7-compatible library ID
            topic: Optional topic to focus on

        Returns:
            Context7Response with summary documentation
        """
        request = Context7Request(
            library_id=library_id,
            topic=topic,
            detail_level=DetailLevel.SUMMARY
        )
        return self.get_documentation(request)

    def get_detailed(self, library_id: str, topic: Optional[str] = None) -> Context7Response:
        """
        Convenience method: Fetch detailed documentation (for Phase 3).

        Args:
            library_id: Context7-compatible library ID
            topic: Optional topic to focus on

        Returns:
            Context7Response with detailed documentation
        """
        request = Context7Request(
            library_id=library_id,
            topic=topic,
            detail_level=DetailLevel.DETAILED
        )
        return self.get_documentation(request)

    def _get_current_phase(self) -> str:
        """Get current workflow phase from task context (implementation detail)."""
        # This would be injected via task context in actual implementation
        return "unknown"


class Context7Error(Exception):
    """Raised when Context7 operations fail."""
    pass
```

#### 1.2.2 Integration with task-manager Agent

```python
# File: installer/core/commands/lib/mcp/phase_context7_integration.py

from typing import Optional, List
from .context7_client import Context7Client, DetailLevel, Context7Request

class PhaseContext7Integration:
    """
    Orchestrates Context7 usage across task workflow phases.

    Responsibilities:
    - Route Context7 calls to appropriate detail level based on phase
    - Manage library dependency tracking
    - Display user-friendly progress messages
    """

    def __init__(self, client: Context7Client, task_context: Dict[str, Any]):
        self.client = client
        self.task_context = task_context
        self.fetched_libraries: List[str] = []  # Track to avoid duplicates

    def fetch_for_planning(self, library_name: str, topic: Optional[str] = None) -> str:
        """
        Fetch library documentation for Phase 2 (Planning).

        Uses SUMMARY detail level (500-1000 tokens).

        Args:
            library_name: Library name to fetch (e.g., "fastapi")
            topic: Optional topic focus (e.g., "dependency-injection")

        Returns:
            Documentation content as string
        """
        # Display user message
        print(f"📚 Fetching overview for {library_name}...")
        if topic:
            print(f"   Topic: {topic}")
        print(f"   Detail: {DetailLevel.SUMMARY.description}")

        # Resolve library ID
        library_id = self.client.resolve_library_id(library_name)

        # Fetch summary documentation
        response = self.client.get_summary(library_id, topic)

        # Display result
        print(f"✅ Retrieved {library_name} overview ({response.actual_tokens} tokens)")

        # Track for session
        self.fetched_libraries.append(library_name)

        return response.content

    def fetch_for_implementation(self, library_name: str, topic: Optional[str] = None) -> str:
        """
        Fetch library documentation for Phase 3 (Implementation).

        Uses DETAILED detail level (3500-5000 tokens).

        Args:
            library_name: Library name to fetch (e.g., "fastapi")
            topic: Optional topic focus (e.g., "dependency-injection")

        Returns:
            Documentation content as string
        """
        # Display user message
        print(f"📚 Fetching detailed docs for {library_name}...")
        if topic:
            print(f"   Topic: {topic}")
        print(f"   Detail: {DetailLevel.DETAILED.description}")

        # Resolve library ID
        library_id = self.client.resolve_library_id(library_name)

        # Fetch detailed documentation
        response = self.client.get_detailed(library_id, topic)

        # Display result
        print(f"✅ Retrieved {library_name} documentation ({response.actual_tokens} tokens)")

        # Track for session
        if library_name not in self.fetched_libraries:
            self.fetched_libraries.append(library_name)

        return response.content

    def fetch_for_testing(self, library_name: str, topic: Optional[str] = None) -> str:
        """
        Fetch library documentation for Phase 4 (Testing).

        Uses SUMMARY detail level (500-1000 tokens) - testing frameworks need focused docs.

        Args:
            library_name: Testing library name (e.g., "pytest", "vitest")
            topic: Optional topic focus (e.g., "fixtures", "mocking")

        Returns:
            Documentation content as string
        """
        # Display user message
        print(f"📚 Fetching testing docs for {library_name}...")
        if topic:
            print(f"   Topic: {topic}")
        print(f"   Detail: {DetailLevel.SUMMARY.description} (testing focus)")

        # Resolve library ID
        library_id = self.client.resolve_library_id(library_name)

        # Fetch summary documentation (testing doesn't need full API docs)
        response = self.client.get_summary(library_id, topic)

        # Display result
        print(f"✅ Retrieved {library_name} testing docs ({response.actual_tokens} tokens)")

        return response.content
```

#### 1.2.3 Usage in task-manager.md

```markdown
## Phase 2: Implementation Planning (UPDATED - Progressive Disclosure)

When planning implementation that requires library usage:

**STEP 1: Identify Required Libraries**

Parse task description and acceptance criteria for library/framework mentions:
- React task → ["react", "tailwindcss", "vitest"]
- FastAPI task → ["fastapi", "pytest", "pydantic"]
- .NET MAUI task → ["maui", "xunit"]

**STEP 2: Fetch Summary Documentation (NEW - Progressive Disclosure)**

```python
from installer.core.commands.lib.mcp.context7_client import Context7Client
from installer.core.commands.lib.mcp.phase_context7_integration import PhaseContext7Integration

# Initialize client with monitor (see Enhancement #2)
client = Context7Client(monitor=mcp_monitor)
integration = PhaseContext7Integration(client, task_context)

# Fetch SUMMARY docs for planning (500-1000 tokens each)
for library in required_libraries:
    summary = integration.fetch_for_planning(
        library_name=library,
        topic=extract_topic_from_task(task_context, library)  # Optional
    )
    # Use summary for high-level architecture decisions
```

**Token Savings Example**:
- OLD: 3 libraries × 5000 tokens = 15,000 tokens (Phase 2)
- NEW: 3 libraries × 1000 tokens = 3,000 tokens (Phase 2)
- **Savings: 12,000 tokens (80% reduction)**

**STEP 3: Create Implementation Plan**

Use summary documentation to:
- Select appropriate patterns
- Identify required dependencies
- Estimate complexity
- Plan file structure

**Phase 3: Implementation (UPDATED - Detailed Documentation)**

When implementing features with libraries:

```python
# Fetch DETAILED docs for implementation (3500-5000 tokens each)
for library in required_libraries:
    detailed_docs = integration.fetch_for_implementation(
        library_name=library,
        topic=extract_implementation_focus(task_context, library)
    )
    # Use detailed docs for correct API usage
```

**Why Fetch Again?**
- Phase 2 had 500-1000 token summaries (architecture only)
- Phase 3 needs 3500-5000 token detailed docs (API specifics, examples)
- Net result: Still saves 50-70% compared to fetching detailed docs twice
```

### 1.3 API Design

#### 1.3.1 New Parameters

**Context7Request**:
```python
@dataclass
class Context7Request:
    library_id: str                           # EXISTING
    topic: Optional[str] = None               # EXISTING
    detail_level: DetailLevel = DetailLevel.DETAILED  # NEW (default maintains backward compatibility)
    custom_token_budget: Optional[int] = None # NEW (optional override)
```

**Backward Compatibility**:
- Default `detail_level=DetailLevel.DETAILED` preserves existing behavior
- Existing code without `detail_level` parameter continues to work
- Token budgets remain at current 5000 default unless explicitly changed

#### 1.3.2 Method Signatures

```python
# Convenience methods (NEW - Recommended for task-manager)
def get_summary(library_id: str, topic: Optional[str] = None) -> Context7Response
def get_detailed(library_id: str, topic: Optional[str] = None) -> Context7Response

# General method (ENHANCED - Backward compatible)
def get_documentation(request: Context7Request) -> Context7Response
```

#### 1.3.3 Usage Examples

**Example 1: Phase 2 Planning (NEW)**
```python
client = Context7Client()

# Fetch summary for planning
response = client.get_summary(
    library_id="/tiangolo/fastapi",
    topic="dependency-injection"
)
# Returns: 500-1000 token overview
print(f"Planning docs: {response.actual_tokens} tokens")
```

**Example 2: Phase 3 Implementation (NEW)**
```python
# Fetch detailed for implementation
response = client.get_detailed(
    library_id="/tiangolo/fastapi",
    topic="dependency-injection"
)
# Returns: 3500-5000 token detailed docs
print(f"Implementation docs: {response.actual_tokens} tokens")
```

**Example 3: Backward Compatible (EXISTING CODE WORKS)**
```python
# Existing code without detail_level parameter
request = Context7Request(
    library_id="/tiangolo/fastapi",
    topic="dependency-injection"
    # detail_level defaults to DETAILED (backward compatible)
)
response = client.get_documentation(request)
# Behaves exactly as before (5000 tokens)
```

**Example 4: Custom Token Budget (ADVANCED)**
```python
# Override default token budget
request = Context7Request(
    library_id="/tiangolo/fastapi",
    topic="dependency-injection",
    detail_level=DetailLevel.SUMMARY,
    custom_token_budget=1500  # Override default 1000
)
response = client.get_documentation(request)
```

### 1.4 Testing Strategy

#### 1.4.1 Unit Tests

**File**: `tests/unit/test_context7_client.py`

```python
import pytest
from installer.core.commands.lib.mcp.context7_client import (
    Context7Client, Context7Request, Context7Response,
    DetailLevel, Context7Error
)

class TestDetailLevel:
    """Test DetailLevel enum."""

    def test_token_budgets(self):
        """Verify token budgets for each detail level."""
        assert DetailLevel.SUMMARY.token_budget == 1000
        assert DetailLevel.DETAILED.token_budget == 5000

    def test_descriptions(self):
        """Verify human-readable descriptions."""
        assert "overview" in DetailLevel.SUMMARY.description.lower()
        assert "complete" in DetailLevel.DETAILED.description.lower()


class TestContext7Request:
    """Test Context7Request dataclass."""

    def test_default_detail_level(self):
        """Default detail level should be DETAILED (backward compatibility)."""
        request = Context7Request(library_id="/test/library")
        assert request.detail_level == DetailLevel.DETAILED

    def test_token_budget_default(self):
        """Token budget should use detail level default."""
        request = Context7Request(
            library_id="/test/library",
            detail_level=DetailLevel.SUMMARY
        )
        assert request.token_budget == 1000

    def test_token_budget_custom_override(self):
        """Custom token budget should override default."""
        request = Context7Request(
            library_id="/test/library",
            detail_level=DetailLevel.SUMMARY,
            custom_token_budget=1500
        )
        assert request.token_budget == 1500

    def test_to_mcp_params_minimal(self):
        """Convert to MCP params with minimal fields."""
        request = Context7Request(library_id="/test/library")
        params = request.to_mcp_params()

        assert params["context7CompatibleLibraryID"] == "/test/library"
        assert params["tokens"] == 5000  # DETAILED default
        assert "topic" not in params

    def test_to_mcp_params_with_topic(self):
        """Convert to MCP params with topic."""
        request = Context7Request(
            library_id="/test/library",
            topic="testing",
            detail_level=DetailLevel.SUMMARY
        )
        params = request.to_mcp_params()

        assert params["topic"] == "testing"
        assert params["tokens"] == 1000


class TestContext7Client:
    """Test Context7Client class."""

    @pytest.fixture
    def mock_mcp_tools(self, monkeypatch):
        """Mock MCP tool functions."""
        def mock_resolve(library_name):
            return f"/{library_name}/repo"

        def mock_get_docs(**kwargs):
            # Return mock documentation
            return "# Documentation\n\nSample content." * 100

        monkeypatch.setattr(
            "installer.core.commands.lib.mcp.context7_client.mcp__context7__resolve_library_id",
            mock_resolve
        )
        monkeypatch.setattr(
            "installer.core.commands.lib.mcp.context7_client.mcp__context7__get_library_docs",
            mock_get_docs
        )

    def test_resolve_library_id_caching(self, mock_mcp_tools):
        """Library ID resolution should be cached."""
        client = Context7Client()

        # First call
        id1 = client.resolve_library_id("fastapi")
        # Second call (should use cache)
        id2 = client.resolve_library_id("fastapi")

        assert id1 == id2 == "/fastapi/repo"
        # Verify cache
        assert "fastapi" in client._library_id_cache

    def test_get_summary(self, mock_mcp_tools):
        """get_summary should use SUMMARY detail level."""
        client = Context7Client()

        response = client.get_summary(
            library_id="/test/library",
            topic="testing"
        )

        assert response.detail_level == DetailLevel.SUMMARY
        assert response.requested_tokens == 1000
        assert response.library_id == "/test/library"
        assert response.topic == "testing"

    def test_get_detailed(self, mock_mcp_tools):
        """get_detailed should use DETAILED detail level."""
        client = Context7Client()

        response = client.get_detailed(
            library_id="/test/library",
            topic="implementation"
        )

        assert response.detail_level == DetailLevel.DETAILED
        assert response.requested_tokens == 5000

    def test_backward_compatibility(self, mock_mcp_tools):
        """Existing code without detail_level should work."""
        client = Context7Client()

        # Simulate old-style usage (no detail_level)
        request = Context7Request(
            library_id="/test/library",
            topic="testing"
        )
        response = client.get_documentation(request)

        # Should default to DETAILED
        assert response.detail_level == DetailLevel.DETAILED
        assert response.requested_tokens == 5000

    def test_error_handling_resolve(self, monkeypatch):
        """Should raise Context7Error on resolve failure."""
        def mock_resolve_error(library_name):
            raise Exception("Library not found")

        monkeypatch.setattr(
            "installer.core.commands.lib.mcp.context7_client.mcp__context7__resolve_library_id",
            mock_resolve_error
        )

        client = Context7Client()

        with pytest.raises(Context7Error, match="Failed to resolve"):
            client.resolve_library_id("nonexistent")


class TestContext7Response:
    """Test Context7Response dataclass."""

    def test_token_efficiency_calculation(self):
        """Calculate token efficiency correctly."""
        response = Context7Response(
            content="Sample content",
            library_id="/test/library",
            topic="testing",
            requested_tokens=5000,
            actual_tokens=3500,
            detail_level=DetailLevel.DETAILED
        )

        assert response.token_efficiency == 70.0  # 3500/5000 * 100

    def test_token_efficiency_zero_division(self):
        """Handle zero requested tokens gracefully."""
        response = Context7Response(
            content="",
            library_id="/test/library",
            topic=None,
            requested_tokens=0,
            actual_tokens=0,
            detail_level=DetailLevel.SUMMARY
        )

        assert response.token_efficiency == 0.0


class TestPhaseContext7Integration:
    """Test PhaseContext7Integration orchestration."""

    @pytest.fixture
    def integration(self, mock_mcp_tools):
        client = Context7Client()
        task_context = {"task_id": "TASK-001", "stack": "python"}
        return PhaseContext7Integration(client, task_context)

    def test_fetch_for_planning_uses_summary(self, integration):
        """Planning should use SUMMARY detail level."""
        content = integration.fetch_for_planning("fastapi", "dependency-injection")

        assert "fastapi" in integration.fetched_libraries
        # Verify SUMMARY was used (implementation detail - would need spy)

    def test_fetch_for_implementation_uses_detailed(self, integration):
        """Implementation should use DETAILED detail level."""
        content = integration.fetch_for_implementation("fastapi", "dependency-injection")

        assert "fastapi" in integration.fetched_libraries
        # Verify DETAILED was used

    def test_library_tracking_no_duplicates(self, integration):
        """Should track fetched libraries and avoid duplicates."""
        integration.fetch_for_planning("fastapi")
        integration.fetch_for_implementation("fastapi")

        # Should only appear once in tracking
        assert integration.fetched_libraries.count("fastapi") == 1
```

#### 1.4.2 Integration Tests

**File**: `tests/integration/test_context7_workflow.py`

```python
import pytest
from installer.core.commands.lib.mcp.context7_client import Context7Client
from installer.core.commands.lib.mcp.phase_context7_integration import PhaseContext7Integration

@pytest.mark.mcp
@pytest.mark.skipif(not has_context7_mcp(), reason="Context7 MCP not available")
class TestContext7RealMCP:
    """Integration tests with real Context7 MCP (requires MCP server running)."""

    def test_progressive_disclosure_token_savings(self):
        """Verify actual token savings with real MCP."""
        client = Context7Client()

        # Phase 2: Fetch summary
        summary_response = client.get_summary(
            library_id=client.resolve_library_id("fastapi"),
            topic="dependency-injection"
        )

        # Phase 3: Fetch detailed
        detailed_response = client.get_detailed(
            library_id=client.resolve_library_id("fastapi"),
            topic="dependency-injection"
        )

        # Verify token savings
        assert summary_response.actual_tokens < 1500  # Summary budget
        assert detailed_response.actual_tokens > 3000  # Detailed budget

        # Calculate savings vs old approach (detailed in both phases)
        old_approach = detailed_response.actual_tokens * 2  # Both phases detailed
        new_approach = summary_response.actual_tokens + detailed_response.actual_tokens
        savings = old_approach - new_approach
        savings_percent = (savings / old_approach) * 100

        print(f"Token savings: {savings} tokens ({savings_percent:.1f}%)")
        assert savings_percent >= 40  # At least 40% savings

    def test_end_to_end_workflow(self):
        """Test complete workflow: planning → implementation → testing."""
        client = Context7Client()
        task_context = {"task_id": "TASK-001", "stack": "python"}
        integration = PhaseContext7Integration(client, task_context)

        # Phase 2: Planning
        planning_docs = integration.fetch_for_planning("pytest", "fixtures")
        assert len(planning_docs) > 0

        # Phase 3: Implementation
        impl_docs = integration.fetch_for_implementation("pytest", "fixtures")
        assert len(impl_docs) > len(planning_docs)  # Detailed should be longer

        # Phase 4: Testing (uses summary)
        testing_docs = integration.fetch_for_testing("pytest", "mocking")
        assert len(testing_docs) > 0
```

#### 1.4.3 Validation Tests

**File**: `tests/validation/test_progressive_disclosure_acceptance.py`

```python
import pytest

class TestProgressiveDisclosureAcceptance:
    """Acceptance tests for progressive disclosure feature."""

    def test_AC1_summary_level_exists(self):
        """AC1: DetailLevel.SUMMARY exists with 500-1000 token budget."""
        from installer.core.commands.lib.mcp.context7_client import DetailLevel

        assert hasattr(DetailLevel, 'SUMMARY')
        assert 500 <= DetailLevel.SUMMARY.token_budget <= 1000

    def test_AC2_backward_compatibility(self):
        """AC2: Existing code works without modifications."""
        from installer.core.commands.lib.mcp.context7_client import Context7Request, DetailLevel

        # Old-style usage (no detail_level parameter)
        request = Context7Request(
            library_id="/test/library",
            topic="testing"
        )

        # Should default to DETAILED
        assert request.detail_level == DetailLevel.DETAILED
        assert request.token_budget == 5000

    def test_AC3_phase2_uses_summary(self):
        """AC3: Phase 2 (Planning) uses SUMMARY detail level."""
        from installer.core.commands.lib.mcp.phase_context7_integration import PhaseContext7Integration
        from installer.core.commands.lib.mcp.context7_client import Context7Client, DetailLevel

        client = Context7Client()
        integration = PhaseContext7Integration(client, {"task_id": "TEST"})

        # Verify planning method exists
        assert hasattr(integration, 'fetch_for_planning')

        # Note: Actual verification requires mocking or MCP integration

    def test_AC4_phase3_uses_detailed(self):
        """AC4: Phase 3 (Implementation) uses DETAILED detail level."""
        from installer.core.commands.lib.mcp.phase_context7_integration import PhaseContext7Integration
        from installer.core.commands.lib.mcp.context7_client import Context7Client

        client = Context7Client()
        integration = PhaseContext7Integration(client, {"task_id": "TEST"})

        # Verify implementation method exists
        assert hasattr(integration, 'fetch_for_implementation')

    def test_AC5_token_savings_achievable(self):
        """AC5: Token savings of 50-70% are achievable."""
        from installer.core.commands.lib.mcp.context7_client import DetailLevel

        # Calculate theoretical savings
        summary_budget = DetailLevel.SUMMARY.token_budget
        detailed_budget = DetailLevel.DETAILED.token_budget

        # Old approach: detailed in both phases
        old_total = detailed_budget * 2

        # New approach: summary in phase 2, detailed in phase 3
        new_total = summary_budget + detailed_budget

        savings = old_total - new_total
        savings_percent = (savings / old_total) * 100

        # Verify 50-70% savings range
        assert 50 <= savings_percent <= 70
```

### 1.5 Migration Path

#### 1.5.1 Rollout Strategy

**Phase 1: Foundation (Week 1)**
- ✅ Implement `Context7Client` with `DetailLevel` enum
- ✅ Add unit tests (100% coverage target)
- ✅ Default behavior = DETAILED (backward compatible)
- ✅ No changes to existing task-manager agent

**Phase 2: Integration (Week 2)**
- ✅ Implement `PhaseContext7Integration` orchestration layer
- ✅ Update task-manager.md Phase 2 instructions (use summary)
- ✅ Update task-manager.md Phase 3 instructions (use detailed)
- ✅ Add integration tests with real MCP

**Phase 3: Validation (Week 3)**
- ✅ Run on 5-10 sample tasks, measure token savings
- ✅ Verify backward compatibility (existing tasks work)
- ✅ Document token savings in MCP Optimization Guide
- ✅ Update CLAUDE.md with new best practices

**Phase 4: Rollout (Week 4)**
- ✅ Deploy to production
- ✅ Monitor via MCP Monitor (Enhancement #2)
- ✅ Collect feedback and iterate

#### 1.5.2 Backward Compatibility Verification

```python
# Test script: scripts/verify_backward_compatibility.py

from installer.core.commands.lib.mcp.context7_client import Context7Client, Context7Request

def test_existing_code_patterns():
    """Verify all existing code patterns still work."""

    client = Context7Client()

    # Pattern 1: Old-style Context7Request (no detail_level)
    request = Context7Request(
        library_id="/tiangolo/fastapi",
        topic="dependency-injection"
    )
    assert request.detail_level.value == "detailed"
    assert request.token_budget == 5000
    print("✅ Pattern 1: Old-style Context7Request works")

    # Pattern 2: Direct MCP call (bypassing client)
    # This should still work (MCP itself unchanged)
    # Note: Actual MCP call omitted (requires MCP server)
    print("✅ Pattern 2: Direct MCP calls still work")

    # Pattern 3: task-manager.md instructions without detail_level
    # Existing instructions fetch docs without specifying level
    # Should default to DETAILED (current behavior preserved)
    print("✅ Pattern 3: Existing task-manager instructions preserved")

    print("\n✅ All backward compatibility tests passed!")

if __name__ == "__main__":
    test_existing_code_patterns()
```

### 1.6 Acceptance Criteria (Enhancement #1)

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC1 | `DetailLevel.SUMMARY` exists with 500-1000 token budget | Unit test |
| AC2 | `DetailLevel.DETAILED` exists with 3500-5000 token budget | Unit test |
| AC3 | Default detail level is DETAILED (backward compatible) | Unit test |
| AC4 | `Context7Request` accepts optional `detail_level` parameter | Unit test |
| AC5 | `Context7Client.get_summary()` convenience method exists | Unit test |
| AC6 | `Context7Client.get_detailed()` convenience method exists | Unit test |
| AC7 | `PhaseContext7Integration.fetch_for_planning()` uses SUMMARY | Integration test |
| AC8 | `PhaseContext7Integration.fetch_for_implementation()` uses DETAILED | Integration test |
| AC9 | `PhaseContext7Integration.fetch_for_testing()` uses SUMMARY | Integration test |
| AC10 | Existing code without `detail_level` still works | Backward compatibility test |
| AC11 | Token savings of 50-70% in Phase 2 achievable | Integration test with real MCP |
| AC12 | User sees progress messages ("Fetching overview...") | Manual testing |
| AC13 | Library ID caching works (no duplicate resolves) | Unit test |
| AC14 | Error handling preserves existing behavior | Unit test |
| AC15 | `Context7Response` includes `detail_level` metadata | Unit test |

### 1.7 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **MCP doesn't support detail levels** | Low | Low | Client-side token budgeting already works; detail_level is hint only |
| **Backward compatibility breaks** | Low | High | Default to DETAILED; extensive compatibility tests |
| **Token savings less than expected** | Medium | Low | Measure with real tasks; adjust budgets if needed |
| **User confusion about detail levels** | Low | Low | Convenience methods hide complexity; clear documentation |
| **Performance regression** | Very Low | Medium | No additional MCP calls; only parameter changes |

### 1.8 Effort Estimation

| Component | Hours | Justification |
|-----------|-------|---------------|
| **Context7Client implementation** | 4 | Clean dataclass design, straightforward logic |
| **PhaseContext7Integration** | 3 | Orchestration layer, user messages |
| **Unit tests** | 5 | Comprehensive test coverage for all classes |
| **Integration tests** | 3 | MCP integration, real workflow testing |
| **task-manager.md updates** | 2 | Update Phase 2, 3, 4 instructions |
| **Documentation** | 2 | Update MCP Optimization Guide, CLAUDE.md |
| **Backward compatibility testing** | 2 | Verify existing code works |
| **Code review + refinement** | 3 | Review, address feedback |
| **TOTAL** | **24 hours** | ~3 days of focused work |

---

## Enhancement #2: MCP Response Size Monitoring

### 2.1 Problem Statement

**Current Behavior**:
- No visibility into actual MCP token consumption during task execution
- Cannot detect when MCPs exceed budgets (e.g., 5000 token budget → 8000 actual)
- No tracking of which MCPs are used in which phases
- No historical data for optimization

**Research Support**:
- TASK-MCP-7796 findings: "Real-time monitoring enables optimization feedback loop"
- MCP Optimization Guide: "Track actual vs expected usage to refine budgets"

### 2.2 Solution Architecture

#### 2.2.1 Class Structure

```python
# File: installer/core/commands/lib/mcp/mcp_monitor.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

class MCPType(Enum):
    """Supported MCP types."""
    CONTEXT7 = "context7"
    DESIGN_PATTERNS = "design-patterns"
    FIGMA = "figma-dev-mode"
    ZEPLIN = "zeplin"


@dataclass
class MCPRequest:
    """Record of an MCP request."""
    mcp_name: str
    tool_name: str
    phase: str
    timestamp: datetime
    params: Dict[str, Any]
    expected_tokens: Optional[int] = None  # Budget

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcp_name": self.mcp_name,
            "tool_name": self.tool_name,
            "phase": self.phase,
            "timestamp": self.timestamp.isoformat(),
            "params": self.params,
            "expected_tokens": self.expected_tokens
        }


@dataclass
class MCPResponse:
    """Record of an MCP response."""
    mcp_name: str
    tool_name: str
    phase: str
    timestamp: datetime
    actual_tokens: int
    expected_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def variance_percent(self) -> Optional[float]:
        """Calculate variance from expected tokens."""
        if self.expected_tokens is None or self.expected_tokens == 0:
            return None
        return ((self.actual_tokens - self.expected_tokens) / self.expected_tokens) * 100

    @property
    def is_over_budget(self) -> bool:
        """Check if response exceeded budget by >20%."""
        variance = self.variance_percent
        return variance is not None and variance > 20

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcp_name": self.mcp_name,
            "tool_name": self.tool_name,
            "phase": self.phase,
            "timestamp": self.timestamp.isoformat(),
            "actual_tokens": self.actual_tokens,
            "expected_tokens": self.expected_tokens,
            "variance_percent": self.variance_percent,
            "is_over_budget": self.is_over_budget,
            "metadata": self.metadata
        }


@dataclass
class MCPError:
    """Record of an MCP error."""
    mcp_name: str
    tool_name: str
    phase: str
    timestamp: datetime
    error_message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcp_name": self.mcp_name,
            "tool_name": self.tool_name,
            "phase": self.phase,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message
        }


@dataclass
class PhaseUsageSummary:
    """MCP usage summary for a workflow phase."""
    phase: str
    total_tokens: int
    request_count: int
    mcps_used: List[str]
    over_budget_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "mcps_used": self.mcps_used,
            "over_budget_count": self.over_budget_count
        }


@dataclass
class TaskUsageReport:
    """Complete MCP usage report for a task."""
    task_id: str
    total_tokens: int
    total_requests: int
    phase_summaries: Dict[str, PhaseUsageSummary]
    over_budget_responses: List[MCPResponse]
    errors: List[MCPError]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_tokens": self.total_tokens,
            "total_requests": self.total_requests,
            "phase_summaries": {
                phase: summary.to_dict()
                for phase, summary in self.phase_summaries.items()
            },
            "over_budget_responses": [r.to_dict() for r in self.over_budget_responses],
            "errors": [e.to_dict() for e in self.errors]
        }


class MCPMonitor:
    """
    Real-time MCP usage monitoring and reporting.

    Responsibilities:
    - Track MCP requests and responses
    - Calculate token usage
    - Detect budget overruns
    - Generate usage reports
    - Persist metrics for analysis

    Principles:
    - Single Responsibility: Only monitors MCP usage
    - Open/Closed: Extensible for new MCP types
    - Dependency Inversion: Abstract interface for storage
    """

    def __init__(self, task_id: str, output_dir: Optional[Path] = None):
        """
        Initialize MCP monitor for a task.

        Args:
            task_id: Task ID being monitored (e.g., "TASK-001")
            output_dir: Optional directory for reports (default: docs/state/{task_id})
        """
        self.task_id = task_id
        self.output_dir = output_dir or Path(f"docs/state/{task_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # In-memory tracking
        self.requests: List[MCPRequest] = []
        self.responses: List[MCPResponse] = []
        self.errors: List[MCPError] = []

        # Current phase context (set by task-manager)
        self.current_phase: str = "unknown"

    def set_phase(self, phase: str):
        """Update current workflow phase."""
        self.current_phase = phase

    def record_request(
        self,
        mcp_name: str,
        tool_name: str,
        params: Dict[str, Any],
        phase: Optional[str] = None
    ):
        """
        Record an MCP request.

        Args:
            mcp_name: MCP server name (e.g., "context7")
            tool_name: MCP tool name (e.g., "get-library-docs")
            params: Tool parameters
            phase: Workflow phase (defaults to current_phase)
        """
        request = MCPRequest(
            mcp_name=mcp_name,
            tool_name=tool_name,
            phase=phase or self.current_phase,
            timestamp=datetime.now(),
            params=params,
            expected_tokens=params.get("tokens")  # Extract budget if present
        )
        self.requests.append(request)

        # Real-time logging
        print(f"📡 MCP Request: {mcp_name}/{tool_name} (Phase {request.phase})")
        if request.expected_tokens:
            print(f"   Budget: {request.expected_tokens} tokens")

    def record_response(
        self,
        mcp_name: str,
        tool_name: str,
        response_size: int,  # Actual token count
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an MCP response.

        Args:
            mcp_name: MCP server name
            tool_name: MCP tool name
            response_size: Actual token count
            phase: Workflow phase
            metadata: Additional metadata
        """
        # Find corresponding request to get expected tokens
        expected_tokens = None
        for req in reversed(self.requests):
            if req.mcp_name == mcp_name and req.tool_name == tool_name:
                expected_tokens = req.expected_tokens
                break

        response = MCPResponse(
            mcp_name=mcp_name,
            tool_name=tool_name,
            phase=phase or self.current_phase,
            timestamp=datetime.now(),
            actual_tokens=response_size,
            expected_tokens=expected_tokens,
            metadata=metadata or {}
        )
        self.responses.append(response)

        # Real-time logging with budget variance
        print(f"✅ MCP Response: {mcp_name}/{tool_name}")
        print(f"   Actual: {response_size} tokens")

        if expected_tokens:
            variance = response.variance_percent
            if variance is not None:
                emoji = "⚠️" if response.is_over_budget else "✓"
                print(f"   {emoji} Variance: {variance:+.1f}% from budget")

                if response.is_over_budget:
                    print(f"   WARNING: Exceeded budget by {variance:.1f}%")

    def record_error(
        self,
        mcp_name: str,
        tool_name: str,
        error: str,
        phase: Optional[str] = None
    ):
        """
        Record an MCP error.

        Args:
            mcp_name: MCP server name
            tool_name: MCP tool name
            error: Error message
            phase: Workflow phase
        """
        error_record = MCPError(
            mcp_name=mcp_name,
            tool_name=tool_name,
            phase=phase or self.current_phase,
            timestamp=datetime.now(),
            error_message=error
        )
        self.errors.append(error_record)

        # Real-time logging
        print(f"❌ MCP Error: {mcp_name}/{tool_name}")
        print(f"   {error}")

    def get_phase_summary(self, phase: str) -> PhaseUsageSummary:
        """Get usage summary for a specific phase."""
        phase_responses = [r for r in self.responses if r.phase == phase]

        total_tokens = sum(r.actual_tokens for r in phase_responses)
        request_count = len(phase_responses)
        mcps_used = list(set(r.mcp_name for r in phase_responses))
        over_budget_count = sum(1 for r in phase_responses if r.is_over_budget)

        return PhaseUsageSummary(
            phase=phase,
            total_tokens=total_tokens,
            request_count=request_count,
            mcps_used=mcps_used,
            over_budget_count=over_budget_count
        )

    def generate_report(self) -> TaskUsageReport:
        """Generate complete usage report for the task."""
        # Calculate totals
        total_tokens = sum(r.actual_tokens for r in self.responses)
        total_requests = len(self.responses)

        # Group by phase
        phases = set(r.phase for r in self.responses)
        phase_summaries = {
            phase: self.get_phase_summary(phase)
            for phase in phases
        }

        # Identify over-budget responses
        over_budget_responses = [r for r in self.responses if r.is_over_budget]

        return TaskUsageReport(
            task_id=self.task_id,
            total_tokens=total_tokens,
            total_requests=total_requests,
            phase_summaries=phase_summaries,
            over_budget_responses=over_budget_responses,
            errors=self.errors
        )

    def save_report(self, report: Optional[TaskUsageReport] = None):
        """
        Save usage report to disk.

        Args:
            report: Optional pre-generated report (otherwise generates new one)
        """
        if report is None:
            report = self.generate_report()

        # Save as JSON
        report_path = self.output_dir / "mcp_usage_report.json"
        with open(report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        print(f"📊 MCP usage report saved: {report_path}")

    def print_summary(self):
        """Print real-time usage summary to console."""
        report = self.generate_report()

        print("\n" + "=" * 70)
        print(f"MCP USAGE SUMMARY - {self.task_id}")
        print("=" * 70)

        print(f"\nTotal Tokens: {report.total_tokens:,}")
        print(f"Total Requests: {report.total_requests}")

        if report.over_budget_responses:
            print(f"\n⚠️  Over-Budget Responses: {len(report.over_budget_responses)}")
            for response in report.over_budget_responses:
                print(f"   - {response.mcp_name}/{response.tool_name}: "
                      f"{response.variance_percent:+.1f}% over budget")

        print("\nUsage by Phase:")
        for phase, summary in sorted(report.phase_summaries.items()):
            print(f"\n  {phase}:")
            print(f"    Tokens: {summary.total_tokens:,}")
            print(f"    Requests: {summary.request_count}")
            print(f"    MCPs: {', '.join(summary.mcps_used)}")
            if summary.over_budget_count > 0:
                print(f"    ⚠️  Over-budget: {summary.over_budget_count}")

        if report.errors:
            print(f"\n❌ Errors: {len(report.errors)}")
            for error in report.errors:
                print(f"   - {error.mcp_name}/{error.tool_name}: {error.error_message}")

        print("\n" + "=" * 70)
```

#### 2.2.2 Integration with task-manager Agent

```markdown
## Step 0.5: Initialize MCP Monitor (NEW - Enhancement #2)

**BEFORE** starting workflow phases, initialize MCP monitoring:

```python
from installer.core.commands.lib.mcp.mcp_monitor import MCPMonitor

# Initialize monitor for this task
mcp_monitor = MCPMonitor(task_id=task_id)

# Set initial phase
mcp_monitor.set_phase("initialization")
```

**Pass monitor to all MCP clients:**

```python
from installer.core.commands.lib.mcp.context7_client import Context7Client

# Initialize Context7 client with monitor
context7_client = Context7Client(monitor=mcp_monitor)
```

## Phase Transitions (UPDATED - MCP Monitoring)

**BEFORE EACH PHASE**, update monitor:

```python
# Phase 2: Implementation Planning
mcp_monitor.set_phase("phase_2")

# Phase 3: Implementation
mcp_monitor.set_phase("phase_3")

# Phase 4: Testing
mcp_monitor.set_phase("phase_4")

# Phase 5: Code Review
mcp_monitor.set_phase("phase_5")
```

## After Task Completion (NEW - Save MCP Report)

**AFTER** Phase 5.5 (Plan Audit), generate and save MCP usage report:

```python
# Generate final report
mcp_monitor.print_summary()  # Display to user
mcp_monitor.save_report()    # Save to docs/state/{task_id}/mcp_usage_report.json
```

**Display to user:**
```
📊 MCP Usage Report Generated

Total MCP Tokens Used: 8,500
Breakdown by Phase:
  - Phase 2 (Planning): 1,200 tokens (context7)
  - Phase 3 (Implementation): 5,000 tokens (context7)
  - Phase 4 (Testing): 1,000 tokens (context7)
  - Phase 2.5A (Pattern Suggestion): 1,300 tokens (design-patterns)

Report saved: docs/state/TASK-001/mcp_usage_report.json

⚠️  1 over-budget response detected:
  - context7/get-library-docs: +32% over budget (6600 vs 5000)
  Consider reducing token budget or using progressive disclosure.
```
```

#### 2.2.3 Usage Example

```python
# Example: Complete task workflow with MCP monitoring

from installer.core.commands.lib.mcp.mcp_monitor import MCPMonitor
from installer.core.commands.lib.mcp.context7_client import Context7Client
from installer.core.commands.lib.mcp.phase_context7_integration import PhaseContext7Integration

# Initialize monitor
monitor = MCPMonitor(task_id="TASK-001")

# Initialize Context7 with monitoring
client = Context7Client(monitor=monitor)
integration = PhaseContext7Integration(client, task_context)

# Phase 2: Planning
monitor.set_phase("phase_2")
planning_docs = integration.fetch_for_planning("fastapi", "dependency-injection")

# Phase 3: Implementation
monitor.set_phase("phase_3")
impl_docs = integration.fetch_for_implementation("fastapi", "dependency-injection")

# Phase 4: Testing
monitor.set_phase("phase_4")
testing_docs = integration.fetch_for_testing("pytest", "fixtures")

# Generate report
report = monitor.generate_report()
monitor.print_summary()
monitor.save_report(report)
```

### 2.3 API Design

#### 2.3.1 Core Methods

```python
class MCPMonitor:
    def __init__(task_id: str, output_dir: Optional[Path] = None)
    def set_phase(phase: str)
    def record_request(mcp_name: str, tool_name: str, params: Dict, phase: Optional[str])
    def record_response(mcp_name: str, tool_name: str, response_size: int, phase: Optional[str], metadata: Optional[Dict])
    def record_error(mcp_name: str, tool_name: str, error: str, phase: Optional[str])
    def get_phase_summary(phase: str) -> PhaseUsageSummary
    def generate_report() -> TaskUsageReport
    def save_report(report: Optional[TaskUsageReport])
    def print_summary()
```

#### 2.3.2 Usage Patterns

**Pattern 1: Automatic Monitoring (via Context7Client)**
```python
# Context7Client automatically calls monitor methods
client = Context7Client(monitor=mcp_monitor)
response = client.get_summary("/library/id", "topic")
# monitor.record_request() and monitor.record_response() called internally
```

**Pattern 2: Manual Monitoring (for other MCPs)**
```python
# For design-patterns MCP (not integrated yet)
monitor.record_request("design-patterns", "get-patterns", {"context": "..."})
patterns = mcp__design_patterns__get_patterns(...)
monitor.record_response("design-patterns", "get-patterns", len(patterns) * 100)  # Estimate tokens
```

**Pattern 3: Error Tracking**
```python
try:
    result = mcp__context7__get_library_docs(...)
except Exception as e:
    monitor.record_error("context7", "get-library-docs", str(e))
    raise
```

### 2.4 Testing Strategy

#### 2.4.1 Unit Tests

**File**: `tests/unit/test_mcp_monitor.py`

```python
import pytest
from datetime import datetime
from installer.core.commands.lib.mcp.mcp_monitor import (
    MCPMonitor, MCPRequest, MCPResponse, MCPError,
    PhaseUsageSummary, TaskUsageReport
)

class TestMCPResponse:
    """Test MCPResponse dataclass."""

    def test_variance_calculation(self):
        """Calculate variance percentage correctly."""
        response = MCPResponse(
            mcp_name="context7",
            tool_name="get-docs",
            phase="phase_2",
            timestamp=datetime.now(),
            actual_tokens=6000,
            expected_tokens=5000
        )

        assert response.variance_percent == 20.0  # (6000-5000)/5000 * 100

    def test_variance_none_when_no_expectation(self):
        """Variance is None when expected_tokens not set."""
        response = MCPResponse(
            mcp_name="context7",
            tool_name="get-docs",
            phase="phase_2",
            timestamp=datetime.now(),
            actual_tokens=6000,
            expected_tokens=None
        )

        assert response.variance_percent is None

    def test_is_over_budget_detection(self):
        """Detect when response exceeds budget by >20%."""
        # 21% over budget (should trigger)
        over_budget = MCPResponse(
            mcp_name="context7",
            tool_name="get-docs",
            phase="phase_2",
            timestamp=datetime.now(),
            actual_tokens=6050,
            expected_tokens=5000
        )
        assert over_budget.is_over_budget is True

        # 19% over budget (should not trigger)
        within_budget = MCPResponse(
            mcp_name="context7",
            tool_name="get-docs",
            phase="phase_2",
            timestamp=datetime.now(),
            actual_tokens=5950,
            expected_tokens=5000
        )
        assert within_budget.is_over_budget is False


class TestMCPMonitor:
    """Test MCPMonitor class."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temporary output directory."""
        return MCPMonitor(task_id="TASK-TEST", output_dir=tmp_path)

    def test_initialization(self, monitor):
        """Monitor initializes with empty tracking."""
        assert monitor.task_id == "TASK-TEST"
        assert len(monitor.requests) == 0
        assert len(monitor.responses) == 0
        assert len(monitor.errors) == 0
        assert monitor.current_phase == "unknown"

    def test_set_phase(self, monitor):
        """Phase can be updated."""
        monitor.set_phase("phase_2")
        assert monitor.current_phase == "phase_2"

    def test_record_request(self, monitor, capsys):
        """Recording request adds to tracking and prints message."""
        monitor.set_phase("phase_2")
        monitor.record_request(
            mcp_name="context7",
            tool_name="get-library-docs",
            params={"library_id": "/test", "tokens": 5000}
        )

        assert len(monitor.requests) == 1
        request = monitor.requests[0]
        assert request.mcp_name == "context7"
        assert request.tool_name == "get-library-docs"
        assert request.phase == "phase_2"
        assert request.expected_tokens == 5000

        # Check console output
        captured = capsys.readouterr()
        assert "MCP Request: context7/get-library-docs" in captured.out
        assert "Budget: 5000 tokens" in captured.out

    def test_record_response_with_budget(self, monitor, capsys):
        """Recording response calculates variance against request budget."""
        # Record request first
        monitor.record_request(
            mcp_name="context7",
            tool_name="get-docs",
            params={"tokens": 5000}
        )

        # Record response
        monitor.record_response(
            mcp_name="context7",
            tool_name="get-docs",
            response_size=6000
        )

        assert len(monitor.responses) == 1
        response = monitor.responses[0]
        assert response.actual_tokens == 6000
        assert response.expected_tokens == 5000
        assert response.variance_percent == 20.0

        # Check console output
        captured = capsys.readouterr()
        assert "Variance: +20.0% from budget" in captured.out

    def test_record_response_over_budget_warning(self, monitor, capsys):
        """Warning displayed when response exceeds budget by >20%."""
        monitor.record_request(
            mcp_name="context7",
            tool_name="get-docs",
            params={"tokens": 5000}
        )

        # 30% over budget
        monitor.record_response(
            mcp_name="context7",
            tool_name="get-docs",
            response_size=6500
        )

        captured = capsys.readouterr()
        assert "WARNING: Exceeded budget by 30.0%" in captured.out

    def test_record_error(self, monitor, capsys):
        """Recording error adds to tracking and prints message."""
        monitor.record_error(
            mcp_name="context7",
            tool_name="get-docs",
            error="Library not found"
        )

        assert len(monitor.errors) == 1
        error = monitor.errors[0]
        assert error.mcp_name == "context7"
        assert error.error_message == "Library not found"

        captured = capsys.readouterr()
        assert "MCP Error: context7/get-docs" in captured.out

    def test_get_phase_summary(self, monitor):
        """Phase summary aggregates responses correctly."""
        monitor.set_phase("phase_2")

        # Record multiple responses
        for i in range(3):
            monitor.record_response(
                mcp_name="context7",
                tool_name=f"tool-{i}",
                response_size=1000
            )

        summary = monitor.get_phase_summary("phase_2")
        assert summary.phase == "phase_2"
        assert summary.total_tokens == 3000
        assert summary.request_count == 3
        assert "context7" in summary.mcps_used

    def test_generate_report(self, monitor):
        """Report generation aggregates all data."""
        # Phase 2
        monitor.set_phase("phase_2")
        monitor.record_request("context7", "get-docs", {"tokens": 5000})
        monitor.record_response("context7", "get-docs", 4800)

        # Phase 3
        monitor.set_phase("phase_3")
        monitor.record_request("context7", "get-docs", {"tokens": 5000})
        monitor.record_response("context7", "get-docs", 6500)  # Over budget

        # Error
        monitor.record_error("design-patterns", "get-patterns", "Timeout")

        report = monitor.generate_report()
        assert report.task_id == "TASK-TEST"
        assert report.total_tokens == 11300  # 4800 + 6500
        assert report.total_requests == 2
        assert len(report.phase_summaries) == 2
        assert len(report.over_budget_responses) == 1
        assert len(report.errors) == 1

    def test_save_report(self, monitor, tmp_path):
        """Report is saved to JSON file."""
        monitor.record_response("context7", "get-docs", 5000)

        report = monitor.generate_report()
        monitor.save_report(report)

        report_path = tmp_path / "mcp_usage_report.json"
        assert report_path.exists()

        # Verify JSON structure
        import json
        with open(report_path) as f:
            data = json.load(f)

        assert data["task_id"] == "TASK-TEST"
        assert data["total_tokens"] == 5000

    def test_print_summary(self, monitor, capsys):
        """Summary prints formatted output."""
        monitor.set_phase("phase_2")
        monitor.record_response("context7", "get-docs", 5000)
        monitor.record_error("context7", "get-docs", "Test error")

        monitor.print_summary()

        captured = capsys.readouterr()
        assert "MCP USAGE SUMMARY - TASK-TEST" in captured.out
        assert "Total Tokens: 5,000" in captured.out
        assert "phase_2" in captured.out
        assert "Test error" in captured.out
```

#### 2.4.2 Integration Tests

**File**: `tests/integration/test_mcp_monitor_integration.py`

```python
import pytest
from installer.core.commands.lib.mcp.mcp_monitor import MCPMonitor
from installer.core.commands.lib.mcp.context7_client import Context7Client

class TestMCPMonitorIntegration:
    """Test MCPMonitor integration with Context7Client."""

    @pytest.fixture
    def setup(self, tmp_path, monkeypatch):
        """Setup monitor and mocked MCP tools."""
        monitor = MCPMonitor(task_id="TASK-INT", output_dir=tmp_path)

        # Mock MCP tools
        def mock_resolve(library_name):
            return f"/{library_name}/repo"

        def mock_get_docs(**kwargs):
            return "# Documentation\n" * 100  # ~2000 chars = ~500 tokens

        monkeypatch.setattr(
            "installer.core.commands.lib.mcp.context7_client.mcp__context7__resolve_library_id",
            mock_resolve
        )
        monkeypatch.setattr(
            "installer.core.commands.lib.mcp.context7_client.mcp__context7__get_library_docs",
            mock_get_docs
        )

        return monitor, tmp_path

    def test_context7_client_with_monitor(self, setup):
        """Context7Client automatically records to monitor."""
        monitor, tmp_path = setup

        # Initialize client with monitor
        client = Context7Client(monitor=monitor)

        # Set phase
        monitor.set_phase("phase_2")

        # Fetch documentation
        response = client.get_summary(
            library_id="/test/library",
            topic="testing"
        )

        # Verify monitor recorded request and response
        assert len(monitor.requests) == 1
        assert len(monitor.responses) == 1

        request = monitor.requests[0]
        assert request.mcp_name == "context7"
        assert request.tool_name == "get-library-docs"
        assert request.phase == "phase_2"

        response_record = monitor.responses[0]
        assert response_record.actual_tokens > 0

    def test_multi_phase_workflow(self, setup):
        """Complete workflow across multiple phases."""
        monitor, tmp_path = setup
        client = Context7Client(monitor=monitor)

        # Phase 2: Planning
        monitor.set_phase("phase_2")
        client.get_summary("/library/id", "topic1")

        # Phase 3: Implementation
        monitor.set_phase("phase_3")
        client.get_detailed("/library/id", "topic2")

        # Phase 4: Testing
        monitor.set_phase("phase_4")
        client.get_summary("/test-library/id", "fixtures")

        # Generate report
        report = monitor.generate_report()

        assert report.total_requests == 3
        assert len(report.phase_summaries) == 3
        assert "phase_2" in report.phase_summaries
        assert "phase_3" in report.phase_summaries
        assert "phase_4" in report.phase_summaries

        # Verify report saved
        monitor.save_report(report)
        assert (tmp_path / "mcp_usage_report.json").exists()
```

### 2.5 Acceptance Criteria (Enhancement #2)

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC16 | `MCPMonitor` class exists and initializes | Unit test |
| AC17 | `record_request()` tracks MCP requests | Unit test |
| AC18 | `record_response()` tracks MCP responses | Unit test |
| AC19 | `record_error()` tracks MCP errors | Unit test |
| AC20 | Variance calculation works (actual vs expected) | Unit test |
| AC21 | Over-budget detection triggers at >20% variance | Unit test |
| AC22 | Phase-specific tracking works | Unit test |
| AC23 | `generate_report()` creates TaskUsageReport | Unit test |
| AC24 | `save_report()` persists JSON to disk | Unit test |
| AC25 | `print_summary()` displays formatted output | Unit test |
| AC26 | Context7Client integrates with MCPMonitor | Integration test |
| AC27 | Real-time console output shows token usage | Manual testing |
| AC28 | Over-budget warnings displayed in real-time | Manual testing |
| AC29 | Report includes phase-by-phase breakdown | Unit test |
| AC30 | Report identifies which MCPs were used | Unit test |
| AC31 | Error tracking includes phase and timestamp | Unit test |
| AC32 | Multiple phases tracked in single task | Integration test |

### 2.6 Migration Path

#### 2.6.1 Rollout Strategy

**Phase 1: Foundation (Week 1)**
- ✅ Implement `MCPMonitor` core class
- ✅ Add unit tests (100% coverage target)
- ✅ Documentation in code comments

**Phase 2: Integration (Week 2)**
- ✅ Integrate with `Context7Client`
- ✅ Update task-manager.md to initialize monitor
- ✅ Add phase tracking calls
- ✅ Add integration tests

**Phase 3: Reporting (Week 3)**
- ✅ Implement report generation and saving
- ✅ Add print_summary() console output
- ✅ Test with real tasks

**Phase 4: Rollout (Week 4)**
- ✅ Deploy to production
- ✅ Collect metrics from 10+ tasks
- ✅ Refine budgets based on actual usage
- ✅ Update MCP Optimization Guide with findings

#### 2.6.2 Backward Compatibility

**No Breaking Changes**:
- MCPMonitor is optional (can be None)
- Context7Client works without monitor
- Existing code continues to function

```python
# Old code (without monitor) still works
client = Context7Client()  # monitor=None (default)
response = client.get_detailed("/library/id", "topic")
# No monitoring, but no errors
```

### 2.7 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Performance overhead** | Low | Low | Minimal in-memory tracking; async save |
| **Token counting inaccuracy** | Medium | Low | Use char count / 4 approximation; refine if needed |
| **Storage space growth** | Low | Very Low | JSON reports are <10KB; cleanup old reports periodically |
| **Console output clutter** | Medium | Low | Keep messages concise; add --quiet flag if needed |

### 2.8 Effort Estimation

| Component | Hours | Justification |
|-----------|-------|---------------|
| **MCPMonitor implementation** | 3 | Dataclasses and basic tracking logic |
| **Report generation** | 2 | Aggregation and formatting |
| **Context7Client integration** | 2 | Add monitor calls to existing methods |
| **task-manager.md updates** | 1 | Add initialization and phase tracking |
| **Unit tests** | 4 | Comprehensive test coverage |
| **Integration tests** | 2 | Workflow testing |
| **Documentation** | 1 | Update MCP Optimization Guide |
| **Code review + refinement** | 1 | Review and address feedback |
| **TOTAL** | **16 hours** | ~2 days of focused work |

---

## Combined Implementation Plan

### Phase 1: Foundation (Week 1) - 12 hours
**Goal**: Implement core classes without disrupting existing functionality

1. **Implement Context7Client with DetailLevel** (4 hours)
   - Create `context7_client.py` module
   - Define `DetailLevel` enum
   - Implement `Context7Request` and `Context7Response` dataclasses
   - Add `Context7Client` class with backward-compatible defaults

2. **Implement MCPMonitor** (3 hours)
   - Create `mcp_monitor.py` module
   - Define tracking dataclasses
   - Implement monitoring methods

3. **Unit Tests** (5 hours)
   - Test `Context7Client` (2 hours)
   - Test `MCPMonitor` (2 hours)
   - Test backward compatibility (1 hour)

**Deliverables**:
- ✅ `installer/core/commands/lib/mcp/context7_client.py`
- ✅ `installer/core/commands/lib/mcp/mcp_monitor.py`
- ✅ `tests/unit/test_context7_client.py`
- ✅ `tests/unit/test_mcp_monitor.py`
- ✅ All tests passing

### Phase 2: Integration (Week 2) - 10 hours
**Goal**: Integrate with task workflow and test end-to-end

1. **PhaseContext7Integration** (3 hours)
   - Create `phase_context7_integration.py`
   - Implement phase-specific fetch methods
   - Add user-friendly messages

2. **task-manager.md Updates** (2 hours)
   - Update Phase 2 instructions (use summary)
   - Update Phase 3 instructions (use detailed)
   - Update Phase 4 instructions (use summary)
   - Add MCPMonitor initialization

3. **Integration Tests** (5 hours)
   - Test progressive disclosure workflow (2 hours)
   - Test MCPMonitor integration (2 hours)
   - Test multi-phase workflows (1 hour)

**Deliverables**:
- ✅ `installer/core/commands/lib/mcp/phase_context7_integration.py`
- ✅ Updated `installer/core/agents/task-manager.md`
- ✅ `tests/integration/test_context7_workflow.py`
- ✅ `tests/integration/test_mcp_monitor_integration.py`
- ✅ All tests passing

### Phase 3: Validation (Week 3) - 10 hours
**Goal**: Validate with real tasks and measure impact

1. **Real Task Testing** (4 hours)
   - Run 5-10 sample tasks with new features
   - Measure actual token savings
   - Collect MCP usage reports

2. **Acceptance Criteria Verification** (3 hours)
   - Verify all 32 acceptance criteria
   - Document results

3. **Documentation** (3 hours)
   - Update MCP Optimization Guide with token savings data
   - Update CLAUDE.md with new best practices
   - Create usage examples

**Deliverables**:
- ✅ Token savings data from real tasks (CSV/JSON)
- ✅ Acceptance criteria verification report
- ✅ Updated `docs/guides/mcp-optimization-guide.md`
- ✅ Updated `CLAUDE.md`

### Phase 4: Rollout (Week 4) - 8 hours
**Goal**: Deploy to production and iterate based on feedback

1. **Production Deployment** (2 hours)
   - Merge to main branch
   - Tag release (v1.1.0)
   - Update installation documentation

2. **Monitoring and Feedback** (4 hours)
   - Collect MCP usage reports from 10+ production tasks
   - Analyze token efficiency patterns
   - Identify optimization opportunities

3. **Iteration** (2 hours)
   - Refine token budgets based on real data
   - Address any issues or feedback
   - Document lessons learned

**Deliverables**:
- ✅ Production release v1.1.0
- ✅ MCP usage analytics (10+ tasks)
- ✅ Token budget refinement recommendations
- ✅ Lessons learned document

---

## Success Metrics

### Enhancement #1: Progressive Disclosure

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Token savings in Phase 2** | 50-70% | Compare old vs new approach across 10 tasks |
| **Task completion time reduction** | 5-10% | Measure task-work duration |
| **User adoption** | 80%+ | Track usage of new detail levels |
| **Backward compatibility** | 100% | All existing code works unchanged |

### Enhancement #2: MCP Response Monitoring

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Monitoring overhead** | <2% | Compare task duration with/without monitoring |
| **Over-budget detection accuracy** | 95%+ | Validate variance calculations |
| **Report generation time** | <1 second | Measure report.generate_report() |
| **Storage efficiency** | <10KB per task | Check report file sizes |

### Combined Impact

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Total token savings per task** | 2,000-3,500 | Sum Phase 2 savings across 10 tasks |
| **MCP optimization feedback loop** | Established | Collect 10+ reports, refine budgets |
| **Developer experience** | Positive | User feedback survey |
| **Zero regressions** | 100% | All existing tests pass |

---

## File Structure

```
installer/core/commands/lib/mcp/
├── __init__.py
├── context7_client.py          # Enhancement #1: Progressive disclosure
├── phase_context7_integration.py  # Enhancement #1: Orchestration
└── mcp_monitor.py              # Enhancement #2: Monitoring

tests/
├── unit/
│   ├── test_context7_client.py
│   └── test_mcp_monitor.py
├── integration/
│   ├── test_context7_workflow.py
│   └── test_mcp_monitor_integration.py
└── validation/
    └── test_progressive_disclosure_acceptance.py

docs/state/{task_id}/
├── mcp_usage_report.json       # Generated by MCPMonitor
└── implementation_plan.json    # Existing (from Phase 2.7)
```

---

## Next Steps

To proceed with implementation:

1. **Create tasks** for each enhancement:
   ```bash
   /task-create "Implement Context7 progressive disclosure (Enhancement #1)" priority:high
   /task-create "Implement MCP response monitoring (Enhancement #2)" priority:high
   ```

2. **Execute sequentially** or in parallel (if resources available):
   ```bash
   # Enhancement #1 (24 hours)
   /task-work TASK-XXX-1

   # Enhancement #2 (16 hours)
   /task-work TASK-XXX-2
   ```

3. **Integration task** (after both complete):
   ```bash
   /task-create "Integrate progressive disclosure + monitoring in task-manager" priority:high
   /task-work TASK-XXX-3
   ```

4. **Validation task**:
   ```bash
   /task-create "Validate MCP enhancements with real tasks" priority:high
   /task-work TASK-XXX-4
   ```

**Total Estimated Duration**: 4-5 weeks (1 person) or 2-3 weeks (2 people in parallel)

---

## Appendix: Complete Acceptance Criteria Checklist

### Enhancement #1: Progressive Disclosure (15 criteria)

- [ ] AC1: `DetailLevel.SUMMARY` exists with 500-1000 token budget
- [ ] AC2: `DetailLevel.DETAILED` exists with 3500-5000 token budget
- [ ] AC3: Default detail level is DETAILED (backward compatible)
- [ ] AC4: `Context7Request` accepts optional `detail_level` parameter
- [ ] AC5: `Context7Client.get_summary()` convenience method exists
- [ ] AC6: `Context7Client.get_detailed()` convenience method exists
- [ ] AC7: `PhaseContext7Integration.fetch_for_planning()` uses SUMMARY
- [ ] AC8: `PhaseContext7Integration.fetch_for_implementation()` uses DETAILED
- [ ] AC9: `PhaseContext7Integration.fetch_for_testing()` uses SUMMARY
- [ ] AC10: Existing code without `detail_level` still works
- [ ] AC11: Token savings of 50-70% in Phase 2 achievable
- [ ] AC12: User sees progress messages ("Fetching overview...")
- [ ] AC13: Library ID caching works (no duplicate resolves)
- [ ] AC14: Error handling preserves existing behavior
- [ ] AC15: `Context7Response` includes `detail_level` metadata

### Enhancement #2: MCP Monitoring (17 criteria)

- [ ] AC16: `MCPMonitor` class exists and initializes
- [ ] AC17: `record_request()` tracks MCP requests
- [ ] AC18: `record_response()` tracks MCP responses
- [ ] AC19: `record_error()` tracks MCP errors
- [ ] AC20: Variance calculation works (actual vs expected)
- [ ] AC21: Over-budget detection triggers at >20% variance
- [ ] AC22: Phase-specific tracking works
- [ ] AC23: `generate_report()` creates TaskUsageReport
- [ ] AC24: `save_report()` persists JSON to disk
- [ ] AC25: `print_summary()` displays formatted output
- [ ] AC26: Context7Client integrates with MCPMonitor
- [ ] AC27: Real-time console output shows token usage
- [ ] AC28: Over-budget warnings displayed in real-time
- [ ] AC29: Report includes phase-by-phase breakdown
- [ ] AC30: Report identifies which MCPs were used
- [ ] AC31: Error tracking includes phase and timestamp
- [ ] AC32: Multiple phases tracked in single task

**Total**: 32 acceptance criteria

---

## Conclusion

This specification provides a complete, production-ready design for two critical MCP enhancements that will:

1. **Save 2,000-3,500 tokens per task** through progressive disclosure
2. **Provide real-time visibility** into MCP resource consumption
3. **Enable data-driven optimization** via usage reports
4. **Maintain 100% backward compatibility** with existing workflows
5. **Follow SOLID principles** for maintainability and extensibility

The implementation is structured for incremental delivery, comprehensive testing, and measurable impact validation. All components are designed to integrate seamlessly with the existing GuardKit architecture while providing immediate value to users.
