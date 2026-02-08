"""MCP Design Extractor Facade

Facade class that hides MCP complexity from downstream agents.
The orchestrator handles all MCP calls; Player and Coach never call MCP tools directly.

Supports both Figma and Zeplin MCP servers with caching and token budget management.

Architecture:
    Task → DesignExtractor → MCP Tools → DesignData → Agent Context

Example:
    >>> from guardkit.orchestrator.mcp_design_extractor import DesignExtractor, DesignData
    >>>
    >>> extractor = DesignExtractor()
    >>>
    >>> # Check MCP availability before extraction (fail-fast)
    >>> if extractor.verify_mcp_availability("figma"):
    ...     design_data = await extractor.extract_figma("abc123", "2:2")
    ...     summary = extractor.summarize_design_data(design_data)
    ...     print(f"Design context: {len(summary)} chars")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

# ============================================================================
# Exceptions
# ============================================================================


class DesignExtractionError(Exception):
    """Base exception for design extraction errors."""

    pass


class MCPUnavailableError(DesignExtractionError):
    """Raised when required MCP tools are not available.

    Attributes:
        source: Design source (figma or zeplin)
        missing_tools: List of MCP tools that are missing
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        missing_tools: Optional[List[str]] = None,
    ):
        self.source = source
        self.missing_tools = missing_tools or []
        super().__init__(message)


class TokenBudgetExceededError(DesignExtractionError):
    """Raised when MCP response exceeds token budget.

    Attributes:
        limit: Maximum allowed tokens
        actual: Actual token count
    """

    def __init__(self, message: str, limit: int = 0, actual: int = 0):
        self.limit = limit
        self.actual = actual
        full_message = f"{message} (limit: {limit}, actual: {actual})"
        super().__init__(full_message)


class NodeIDFormatError(DesignExtractionError):
    """Raised when Figma node ID format is invalid.

    Attributes:
        node_id: The invalid node ID
        suggested_format: Suggested correct format
    """

    def __init__(
        self, message: str, node_id: Optional[str] = None, suggested_format: Optional[str] = None
    ):
        self.node_id = node_id
        self.suggested_format = suggested_format
        full_message = message
        if suggested_format:
            full_message += f" (suggested: {suggested_format})"
        super().__init__(full_message)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class DesignData:
    """Captured design data from MCP extraction.

    Holds component structure, design tokens, visual reference, and metadata
    from either Figma or Zeplin extraction.

    Attributes:
        source: Design source ('figma' or 'zeplin')
        elements: List of design elements (components, layers, etc.)
        tokens: Design tokens (colors, spacing, typography)
        visual_reference: URL to visual reference image (optional)
        metadata: Additional metadata (file_key, node_id, timestamps, etc.)

    Examples:
        >>> data = DesignData(
        ...     source="figma",
        ...     elements=[{"name": "Button", "type": "component"}],
        ...     tokens={"colors": {"primary": "#3B82F6"}},
        ...     visual_reference="https://figma.com/api/v1/images/...",
        ...     metadata={"file_key": "abc123", "node_id": "2:2"},
        ... )
        >>> data.to_json()
        '{"source": "figma", "elements": [...]}'
    """

    source: str  # 'figma' or 'zeplin'
    elements: List[Dict[str, Any]] = field(default_factory=list)
    tokens: Dict[str, Any] = field(default_factory=dict)
    visual_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation of the design data.
        """
        return json.dumps(
            {
                "source": self.source,
                "elements": self.elements,
                "tokens": self.tokens,
                "visual_reference": self.visual_reference,
                "metadata": self.metadata,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DesignData":
        """Deserialize from JSON string.

        Args:
            json_str: JSON string to parse.

        Returns:
            DesignData instance.
        """
        data = json.loads(json_str)
        return cls(
            source=data.get("source", "unknown"),
            elements=data.get("elements", []),
            tokens=data.get("tokens", {}),
            visual_reference=data.get("visual_reference"),
            metadata=data.get("metadata", {}),
        )

    def estimate_token_count(self) -> int:
        """Estimate token count for this design data.

        Uses a simple heuristic: ~4 characters per token on average.

        Returns:
            Estimated token count.
        """
        json_str = self.to_json()
        # Rough estimate: 4 characters per token
        return len(json_str) // 4


# ============================================================================
# Main Facade Class
# ============================================================================


class DesignExtractor:
    """MCP facade for design extraction.

    Provides a unified interface for extracting design data from Figma and Zeplin
    via their respective MCP servers. Handles caching, retry logic, and token
    budget management.

    The orchestrator uses this class to extract design data before the Player-Coach
    loop starts. Player and Coach agents never call MCP tools directly.

    Attributes:
        cache_dir: Directory for caching MCP responses
        cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        max_retries: Maximum retry attempts for transient failures
        token_budget: Maximum tokens for summarized output

    Example:
        >>> extractor = DesignExtractor()
        >>>
        >>> # Verify MCP availability (fail-fast)
        >>> if extractor.verify_mcp_availability("figma"):
        ...     data = await extractor.extract_figma("abc123", "2:2")
        ...     summary = extractor.summarize_design_data(data)
    """

    # Required MCP tools for each design source
    FIGMA_MCP_TOOLS = [
        "mcp__figma-dev-mode__get_code",
        "mcp__figma-dev-mode__get_image",
        "mcp__figma-dev-mode__get_variable_defs",
    ]

    ZEPLIN_MCP_TOOLS = [
        "mcp__zeplin__get_screen",
        "mcp__zeplin__get_colors",
        "mcp__zeplin__get_text_styles",
    ]

    # Default configuration
    DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TOKEN_BUDGET = 3000

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ):
        """Initialize DesignExtractor.

        Args:
            cache_dir: Directory for caching MCP responses. Defaults to
                       .guardkit/cache/design/ in current directory.
            cache_ttl_seconds: Cache time-to-live in seconds.
            max_retries: Maximum retry attempts for transient failures.
            token_budget: Maximum tokens for summarized output.
        """
        self.cache_dir = cache_dir or Path(".guardkit") / "cache" / "design"
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.max_retries = max_retries
        self.token_budget = token_budget

        # Ensure cache directory exists
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Graceful degradation if cache dir can't be created

    # ========================================================================
    # MCP Availability Verification
    # ========================================================================

    def verify_mcp_availability(self, source: str) -> bool:
        """Verify MCP tools are available for the given design source.

        Args:
            source: Design source ('figma' or 'zeplin').

        Returns:
            True if all required MCP tools are available.

        Raises:
            ValueError: If source is not 'figma' or 'zeplin'.
        """
        if source not in ("figma", "zeplin"):
            raise ValueError(f"Invalid design source: {source}. Must be 'figma' or 'zeplin'.")

        tools = self.FIGMA_MCP_TOOLS if source == "figma" else self.ZEPLIN_MCP_TOOLS

        for tool in tools:
            if not self._check_mcp_tool_exists(tool):
                return False

        return True

    def _check_mcp_tool_exists(self, tool_name: str) -> bool:
        """Check if an MCP tool is available.

        This method should be overridden or mocked in tests.
        In production, it checks the MCP tool registry.

        Args:
            tool_name: Name of the MCP tool.

        Returns:
            True if the tool exists.
        """
        # In production, this would check the actual MCP registry
        # For now, return False (tools must be verified externally)
        return False

    # ========================================================================
    # Node ID Format Validation
    # ========================================================================

    def _validate_node_id_format(self, node_id: str) -> bool:
        """Validate Figma node ID is in colon format.

        Figma URLs use dash format (2-2) but MCP API requires colon format (2:2).

        Args:
            node_id: Node ID to validate.

        Returns:
            True if node ID is in valid colon format.
        """
        # Valid format: digits separated by colons (e.g., "2:2", "1:2:3", "123:456:789")
        pattern = r"^\d+(?::\d+)+$"
        return bool(re.match(pattern, node_id))

    def _convert_node_id_to_colon_format(self, node_id: str) -> str:
        """Convert node ID from dash format to colon format.

        Args:
            node_id: Node ID in dash format (e.g., "2-2").

        Returns:
            Node ID in colon format (e.g., "2:2").
        """
        return node_id.replace("-", ":")

    def _ensure_valid_node_id(self, node_id: str) -> str:
        """Ensure node ID is in valid colon format, converting if necessary.

        Args:
            node_id: Node ID (may be in dash or colon format).

        Returns:
            Node ID in colon format.

        Raises:
            NodeIDFormatError: If node ID cannot be converted to valid format.
        """
        if self._validate_node_id_format(node_id):
            return node_id

        # Try converting from dash format
        converted = self._convert_node_id_to_colon_format(node_id)
        if self._validate_node_id_format(converted):
            return converted

        raise NodeIDFormatError(
            f"Invalid node ID format: {node_id}",
            node_id=node_id,
            suggested_format=converted if ":" in converted else f"{node_id.replace('-', ':')}",
        )

    # ========================================================================
    # Caching
    # ========================================================================

    def _generate_cache_key(self, source: str, *args: str) -> str:
        """Generate cache key from source and arguments.

        Args:
            source: Design source ('figma' or 'zeplin').
            *args: Additional arguments (file_key, node_id, etc.).

        Returns:
            Cache key string.
        """
        return f"{source}:{':'.join(args)}"

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get file path for cache entry.

        Args:
            cache_key: Cache key.

        Returns:
            Path to cache file.
        """
        hash_key = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hash_key}.json"

    def _get_from_cache(self, cache_key: str) -> Optional[DesignData]:
        """Retrieve design data from cache if valid.

        Args:
            cache_key: Cache key.

        Returns:
            DesignData if cache hit and valid, None otherwise.
        """
        self._ensure_cache_dir()

        cache_file = self._get_cache_file_path(cache_key)
        if not cache_file.exists():
            return None

        try:
            cache_data = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
            if datetime.now() - cached_at > self.cache_ttl:
                # Expired
                return None

            return DesignData.from_json(json.dumps(cache_data.get("data", {})))
        except (json.JSONDecodeError, ValueError, KeyError):
            return None

    def _save_to_cache(self, cache_key: str, data: DesignData) -> None:
        """Save design data to cache.

        Args:
            cache_key: Cache key.
            data: DesignData to cache.
        """
        self._ensure_cache_dir()

        cache_file = self._get_cache_file_path(cache_key)
        cache_entry = {
            "cached_at": datetime.now().isoformat(),
            "cache_key": cache_key,
            "data": json.loads(data.to_json()),
        }

        try:
            cache_file.write_text(json.dumps(cache_entry, indent=2))
        except OSError:
            pass  # Graceful degradation if cache write fails

    # ========================================================================
    # Retry Logic with Exponential Backoff
    # ========================================================================

    async def _call_with_retry(
        self,
        func: Callable,
        max_retries: Optional[int] = None,
        retry_on: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError),
        **kwargs: Any,
    ) -> Any:
        """Call function with exponential backoff retry logic.

        Args:
            func: Async function to call.
            max_retries: Maximum retry attempts (defaults to self.max_retries).
            retry_on: Tuple of exception types to retry on.
            **kwargs: Arguments to pass to func.

        Returns:
            Result of func call.

        Raises:
            DesignExtractionError: If all retries exhausted.
        """
        max_retries = max_retries or self.max_retries
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func(**kwargs)
            except retry_on as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, ...
                    delay = 2**attempt
                    await asyncio.sleep(delay)
            except Exception:
                # Non-retryable error
                raise

        raise DesignExtractionError(
            f"Failed after {max_retries} retry attempts: {last_exception}"
        )

    # ========================================================================
    # MCP Tool Calls (to be mocked in tests)
    # ========================================================================

    async def _call_figma_mcp(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Call Figma MCP tool.

        This method should be mocked in tests.

        Args:
            tool_name: MCP tool name.
            **kwargs: Tool arguments.

        Returns:
            Tool response.
        """
        # In production, this would call the actual MCP tool
        # For now, raise NotImplementedError
        raise NotImplementedError("Figma MCP calls must be mocked in tests")

    async def _call_zeplin_mcp(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Call Zeplin MCP tool.

        This method should be mocked in tests.

        Args:
            tool_name: MCP tool name.
            **kwargs: Tool arguments.

        Returns:
            Tool response.
        """
        # In production, this would call the actual MCP tool
        # For now, raise NotImplementedError
        raise NotImplementedError("Zeplin MCP calls must be mocked in tests")

    # ========================================================================
    # Figma Extraction
    # ========================================================================

    async def extract_figma(self, file_key: str, node_id: str) -> DesignData:
        """Extract design data from Figma via MCP.

        Calls three MCP tools:
        - mcp__figma-dev-mode__get_code: Component structure
        - mcp__figma-dev-mode__get_image: Visual reference
        - mcp__figma-dev-mode__get_variable_defs: Design tokens

        Args:
            file_key: Figma file key.
            node_id: Node ID (colon or dash format, will be converted).

        Returns:
            DesignData with extracted design information.

        Raises:
            MCPUnavailableError: If Figma MCP tools are not available.
            NodeIDFormatError: If node ID format is invalid.
            DesignExtractionError: If extraction fails.
        """
        # Verify MCP availability (fail-fast)
        if not self.verify_mcp_availability("figma"):
            raise MCPUnavailableError(
                "Figma MCP tools not available. Enable in claude_desktop_config.json",
                source="figma",
                missing_tools=self.FIGMA_MCP_TOOLS,
            )

        # Validate and convert node ID format
        node_id = self._ensure_valid_node_id(node_id)

        # Check cache
        cache_key = self._generate_cache_key("figma", file_key, node_id)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Call MCP tools with retry logic
        async def call_get_code():
            return await self._call_figma_mcp(
                "mcp__figma-dev-mode__get_code",
                file_key=file_key,
                node_id=node_id,
            )

        async def call_get_image():
            return await self._call_figma_mcp(
                "mcp__figma-dev-mode__get_image",
                file_key=file_key,
                node_id=node_id,
            )

        async def call_get_variables():
            return await self._call_figma_mcp(
                "mcp__figma-dev-mode__get_variable_defs",
                file_key=file_key,
                node_id=node_id,
            )

        try:
            code_response = await self._call_with_retry(call_get_code)
            image_response = await self._call_with_retry(call_get_image)
            tokens_response = await self._call_with_retry(call_get_variables)
        except Exception as e:
            raise DesignExtractionError(f"Failed to extract Figma design: {e}") from e

        # Parse and combine responses
        design_data = self._parse_figma_responses(
            file_key, node_id, code_response, image_response, tokens_response
        )

        # Save to cache
        self._save_to_cache(cache_key, design_data)

        return design_data

    def _parse_figma_responses(
        self,
        file_key: str,
        node_id: str,
        code_response: Dict[str, Any],
        image_response: Dict[str, Any],
        tokens_response: Dict[str, Any],
    ) -> DesignData:
        """Parse Figma MCP responses into DesignData.

        Args:
            file_key: Figma file key.
            node_id: Node ID.
            code_response: Response from get_code.
            image_response: Response from get_image.
            tokens_response: Response from get_variable_defs.

        Returns:
            DesignData with parsed information.
        """
        # Extract component structure from code response
        elements = []
        if "code" in code_response:
            component_structure = code_response["code"].get("component_structure", {})
            if component_structure:
                elements.append(component_structure)

        # Extract design tokens from variables response
        tokens = {}
        if "variables" in tokens_response:
            tokens = tokens_response["variables"]

        # Extract visual reference from image response
        visual_reference = image_response.get("image_url")

        return DesignData(
            source="figma",
            elements=elements,
            tokens=tokens,
            visual_reference=visual_reference,
            metadata={
                "file_key": file_key,
                "node_id": node_id,
                "extracted_at": datetime.now().isoformat(),
            },
        )

    # ========================================================================
    # Zeplin Extraction
    # ========================================================================

    async def extract_zeplin(self, project_id: str, screen_id: str) -> DesignData:
        """Extract design data from Zeplin via MCP.

        Calls MCP tools:
        - mcp__zeplin__get_screen: Screen design data
        - mcp__zeplin__get_colors: Color palette
        - mcp__zeplin__get_text_styles: Typography

        Args:
            project_id: Zeplin project ID.
            screen_id: Screen ID.

        Returns:
            DesignData with extracted design information.

        Raises:
            MCPUnavailableError: If Zeplin MCP tools are not available.
            DesignExtractionError: If extraction fails.
        """
        # Verify MCP availability (fail-fast)
        if not self.verify_mcp_availability("zeplin"):
            raise MCPUnavailableError(
                "Zeplin MCP tools not available. Enable in claude_desktop_config.json",
                source="zeplin",
                missing_tools=self.ZEPLIN_MCP_TOOLS,
            )

        # Check cache
        cache_key = self._generate_cache_key("zeplin", project_id, screen_id)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Call MCP tools with retry logic
        async def call_get_screen():
            return await self._call_zeplin_mcp(
                "mcp__zeplin__get_screen",
                project_id=project_id,
                screen_id=screen_id,
            )

        async def call_get_colors():
            return await self._call_zeplin_mcp(
                "mcp__zeplin__get_colors",
                project_id=project_id,
            )

        async def call_get_text_styles():
            return await self._call_zeplin_mcp(
                "mcp__zeplin__get_text_styles",
                project_id=project_id,
            )

        try:
            screen_response = await self._call_with_retry(call_get_screen)
            colors_response = await self._call_with_retry(call_get_colors)
            text_styles_response = await self._call_with_retry(call_get_text_styles)
        except Exception as e:
            raise DesignExtractionError(f"Failed to extract Zeplin design: {e}") from e

        # Parse and combine responses
        design_data = self._parse_zeplin_responses(
            project_id, screen_id, screen_response, colors_response, text_styles_response
        )

        # Save to cache
        self._save_to_cache(cache_key, design_data)

        return design_data

    def _parse_zeplin_responses(
        self,
        project_id: str,
        screen_id: str,
        screen_response: Dict[str, Any],
        colors_response: Dict[str, Any],
        text_styles_response: Dict[str, Any],
    ) -> DesignData:
        """Parse Zeplin MCP responses into DesignData.

        Args:
            project_id: Zeplin project ID.
            screen_id: Screen ID.
            screen_response: Response from get_screen.
            colors_response: Response from get_colors.
            text_styles_response: Response from get_text_styles.

        Returns:
            DesignData with parsed information.
        """
        # Extract elements from screen response
        elements = []
        if "components" in screen_response:
            elements = screen_response["components"]
        elif screen_response:
            elements = [screen_response]

        # Extract design tokens
        tokens = {}
        if "colors" in colors_response:
            tokens["colors"] = colors_response["colors"]
        if "text_styles" in text_styles_response:
            tokens["typography"] = text_styles_response["text_styles"]

        return DesignData(
            source="zeplin",
            elements=elements,
            tokens=tokens,
            visual_reference=None,  # Zeplin doesn't have direct image URLs
            metadata={
                "project_id": project_id,
                "screen_id": screen_id,
                "extracted_at": datetime.now().isoformat(),
            },
        )

    # ========================================================================
    # Summarization
    # ========================================================================

    def summarize_design_data(self, data: DesignData) -> str:
        """Summarize design data to ~3K tokens for agent context.

        Creates a human-readable summary of the design data suitable for
        including in agent prompts without exceeding token budgets.

        Args:
            data: DesignData to summarize.

        Returns:
            Summarized design context string (~3K tokens).
        """
        lines = []

        # Header
        lines.append(f"# Design Summary ({data.source.title()})")
        lines.append("")

        # Elements
        if data.elements:
            lines.append("## Components/Elements")
            for element in data.elements[:10]:  # Limit to 10 elements
                if isinstance(element, dict):
                    name = element.get("name", "Unknown")
                    elem_type = element.get("type", "component")
                    lines.append(f"- **{name}** ({elem_type})")

                    # Add props if present
                    props = element.get("props", [])
                    if props:
                        prop_names = [
                            p.get("name", str(p)) if isinstance(p, dict) else str(p)
                            for p in props[:5]
                        ]
                        lines.append(f"  - Props: {', '.join(prop_names)}")

                    # Add children if present
                    children = element.get("children", [])
                    if children:
                        child_names = [
                            c.get("name", str(c)) if isinstance(c, dict) else str(c)
                            for c in children[:5]
                        ]
                        lines.append(f"  - Children: {', '.join(child_names)}")
            lines.append("")

        # Design Tokens
        if data.tokens:
            lines.append("## Design Tokens")

            # Colors
            colors = data.tokens.get("colors", {})
            if colors:
                lines.append("### Colors")
                if isinstance(colors, dict):
                    for name, value in list(colors.items())[:10]:
                        lines.append(f"- `{name}`: {value}")
                elif isinstance(colors, list):
                    for color in colors[:10]:
                        if isinstance(color, dict):
                            lines.append(f"- {color.get('name', 'unknown')}: {color.get('value', '')}")

            # Typography
            typography = data.tokens.get("typography", {})
            if typography:
                lines.append("### Typography")
                if isinstance(typography, dict):
                    for name, value in list(typography.items())[:5]:
                        if isinstance(value, dict):
                            lines.append(f"- **{name}**: fontSize={value.get('fontSize', 'N/A')}")
                        else:
                            lines.append(f"- **{name}**: {value}")
                elif isinstance(typography, list):
                    for style in typography[:5]:
                        if isinstance(style, dict):
                            lines.append(f"- **{style.get('name', 'unknown')}**: fontSize={style.get('fontSize', 'N/A')}")

            # Spacing
            spacing = data.tokens.get("spacing", {})
            if spacing:
                lines.append("### Spacing")
                for name, value in list(spacing.items())[:10]:
                    lines.append(f"- `{name}`: {value}")

            lines.append("")

        # Visual Reference
        if data.visual_reference:
            lines.append("## Visual Reference")
            lines.append(f"- Image URL: {data.visual_reference}")
            lines.append("")

        # Metadata
        if data.metadata:
            lines.append("## Metadata")
            for key, value in data.metadata.items():
                lines.append(f"- {key}: {value}")

        summary = "\n".join(lines)

        # Truncate if exceeds token budget (rough: 4 chars/token)
        max_chars = self.token_budget * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n\n[... truncated for token budget ...]"

        return summary


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "DesignData",
    "DesignExtractor",
    "DesignExtractionError",
    "MCPUnavailableError",
    "TokenBudgetExceededError",
    "NodeIDFormatError",
]
