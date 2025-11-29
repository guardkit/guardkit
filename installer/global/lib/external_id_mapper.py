"""
External ID Mapper for PM Tools Integration

This module provides bidirectional mapping between Taskwright's internal
hash-based task IDs and external sequential IDs used by PM tools.

Supported PM Tools:
- JIRA: {PROJECT_KEY}-{number} (e.g., PROJ-456)
- Azure DevOps: {number} (e.g., 1234)
- Linear: {TEAM_KEY}-{number} (e.g., TEAM-789)
- GitHub: {number} (e.g., 234, displayed as #234)

Thread Safety:
All counter operations are protected by threading.Lock() to ensure
atomic increments during concurrent task creation.

Usage:
    mapper = ExternalIDMapper()

    # Create mapping
    jira_id = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
    # Returns: "PROJ-456"

    # Reverse lookup
    internal_id = mapper.get_internal_id("PROJ-456", "jira")
    # Returns: "TASK-E01-b2c4"

    # Get all mappings for a task
    all_ids = mapper.get_all_mappings("TASK-E01-b2c4")
    # Returns: {"jira": "PROJ-456", "azure_devops": "1234", ...}
"""

import threading
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from external_id_persistence import ExternalIDPersistence


class ExternalIDMapper:
    """
    Manages bidirectional mapping between internal hash IDs and external
    sequential IDs for PM tools.

    Attributes:
        mappings (Dict): Internal ID -> {tool: external_id}
        counters (Dict): Tool -> counter value (or {key: value} for keyed tools)
        _counter_lock (threading.Lock): Ensures atomic counter operations
    """

    # Supported PM tools
    SUPPORTED_TOOLS = {"jira", "azure_devops", "linear", "github"}

    # Tools requiring project/team keys
    KEYED_TOOLS = {"jira", "linear"}

    def __init__(self, persistence: Optional['ExternalIDPersistence'] = None):
        """
        Initialize mapper with persistence support.

        Args:
            persistence: Optional persistence layer. If None, uses in-memory only.
        """
        self.persistence = persistence

        # Load from persistence if available
        if self.persistence:
            self.mappings = self.persistence.load_mappings()
            self.counters = self.persistence.load_counters()
        else:
            # In-memory only mode
            self.mappings: Dict[str, Dict[str, str]] = {}
            self.counters: Dict[str, any] = {
                "jira": {},        # {project_key: counter}
                "azure_devops": 0,  # Global counter
                "linear": {},       # {team_key: counter}
                "github": 0         # Global counter
            }

        self._counter_lock = threading.Lock()

    def map_to_external(
        self,
        internal_id: str,
        tool: str,
        project_key: str = "PROJ"
    ) -> str:
        """
        Map internal hash ID to external sequential ID.

        Creates a new mapping if one doesn't exist, or returns existing mapping.
        Automatically increments counter for new mappings.

        Args:
            internal_id: Internal task ID (e.g., "TASK-E01-b2c4")
            tool: PM tool name (jira|azure_devops|linear|github)
            project_key: Project/team key for JIRA/Linear (default: "PROJ")

        Returns:
            External ID string in tool-specific format

        Raises:
            ValueError: If tool not supported or internal_id invalid

        Examples:
            >>> mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
            'PROJ-1'
            >>> mapper.map_to_external("TASK-E01-b2c4", "azure_devops")
            '1'
        """
        self._validate_tool(tool)
        self._validate_internal_id(internal_id)

        # Check if mapping already exists
        if internal_id in self.mappings and tool in self.mappings[internal_id]:
            return self.mappings[internal_id][tool]

        # Create new mapping
        if tool in self.KEYED_TOOLS:
            if not project_key:
                raise ValueError(f"Tool '{tool}' requires a project/team key")
            # Normalize project_key to uppercase for consistent counter management
            normalized_key = project_key.upper()
            counter = self.increment_counter(tool, normalized_key)
        else:
            counter = self.increment_counter(tool)

        # Format external ID (formatting function also normalizes key)
        external_id = self._format_external_id(tool, counter, project_key)

        # Store mapping
        if internal_id not in self.mappings:
            self.mappings[internal_id] = {}
        self.mappings[internal_id][tool] = external_id

        # Persist mapping to disk
        if self.persistence:
            self.persistence.save_mappings(self.mappings)

        return external_id

    def get_internal_id(
        self,
        external_id: str,
        tool: str
    ) -> Optional[str]:
        """
        Reverse lookup: Get internal ID from external ID.

        Args:
            external_id: External ID in tool format (e.g., "PROJ-456")
            tool: PM tool name

        Returns:
            Internal hash ID or None if mapping doesn't exist

        Examples:
            >>> mapper.get_internal_id("PROJ-456", "jira")
            'TASK-E01-b2c4'
            >>> mapper.get_internal_id("UNKNOWN-999", "jira")
            None
        """
        self._validate_tool(tool)

        # Search through all mappings
        for internal_id, tool_mappings in self.mappings.items():
            if tool in tool_mappings and tool_mappings[tool] == external_id:
                return internal_id

        return None

    def get_all_mappings(
        self,
        internal_id: str
    ) -> Dict[str, str]:
        """
        Get all external IDs for an internal ID.

        Args:
            internal_id: Internal task ID

        Returns:
            Dictionary of {tool: external_id} or empty dict if no mappings

        Examples:
            >>> mapper.get_all_mappings("TASK-E01-b2c4")
            {'jira': 'PROJ-456', 'azure_devops': '1234', 'github': '234'}
        """
        return self.mappings.get(internal_id, {}).copy()

    def increment_counter(
        self,
        tool: str,
        key: str = None
    ) -> int:
        """
        Thread-safe counter increment.

        Args:
            tool: PM tool name
            key: Project/team key for JIRA/Linear (required for keyed tools)

        Returns:
            Next sequential number

        Raises:
            ValueError: If tool not supported or key missing for keyed tools

        Examples:
            >>> mapper.increment_counter("jira", "PROJ")
            1
            >>> mapper.increment_counter("jira", "PROJ")
            2
            >>> mapper.increment_counter("azure_devops")
            1
        """
        self._validate_tool(tool)

        with self._counter_lock:
            if tool in self.KEYED_TOOLS:
                if not key:
                    raise ValueError(f"Tool '{tool}' requires a key for counter")

                # Initialize key counter if needed
                if key not in self.counters[tool]:
                    self.counters[tool][key] = 0

                # Increment and return
                self.counters[tool][key] += 1
                counter_value = self.counters[tool][key]

                # Persist counters to disk
                if self.persistence:
                    self.persistence.save_counters(self.counters)

                return counter_value
            else:
                # Global counter for Azure DevOps/GitHub
                self.counters[tool] += 1
                counter_value = self.counters[tool]

                # Persist counters to disk
                if self.persistence:
                    self.persistence.save_counters(self.counters)

                return counter_value

    def _format_external_id(
        self,
        tool: str,
        number: int,
        key: str = None
    ) -> str:
        """
        Format external ID based on tool specifications.

        Args:
            tool: PM tool name
            number: Sequential number
            key: Project/team key for JIRA/Linear

        Returns:
            Formatted external ID
        """
        if tool == "jira":
            return self._format_jira_id(key, number)
        elif tool == "azure_devops":
            return self._format_azure_id(number)
        elif tool == "linear":
            return self._format_linear_id(key, number)
        elif tool == "github":
            return self._format_github_id(number)
        else:
            raise ValueError(f"Unsupported tool: {tool}")

    def _format_keyed_id(self, key: str, number: int) -> str:
        """
        Shared format handler for JIRA/Linear.

        Args:
            key: Project/team key
            number: Sequential number

        Returns:
            Formatted ID: {KEY}-{number}
        """
        return f"{key.upper()}-{number}"

    def _format_jira_id(self, project_key: str, number: int) -> str:
        """Format JIRA ID: PROJECT-123"""
        return self._format_keyed_id(project_key, number)

    def _format_azure_id(self, number: int) -> str:
        """Format Azure DevOps ID: 1234"""
        return str(number)

    def _format_linear_id(self, team_key: str, number: int) -> str:
        """Format Linear ID: TEAM-456"""
        return self._format_keyed_id(team_key, number)

    def _format_github_id(self, number: int) -> str:
        """Format GitHub ID: 789 (displayed as #789 in UI)"""
        return str(number)

    def _validate_tool(self, tool: str):
        """
        Validate tool name is supported.

        Raises:
            ValueError: If tool not in SUPPORTED_TOOLS
        """
        if tool not in self.SUPPORTED_TOOLS:
            raise ValueError(
                f"Unsupported tool: '{tool}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_TOOLS))}"
            )

    def _validate_internal_id(self, internal_id: str):
        """
        Validate internal ID format.

        Expected format: TASK-XXX-hash or EPIC-XXX-hash

        Raises:
            ValueError: If format is invalid
        """
        if not internal_id:
            raise ValueError("Internal ID cannot be empty")

        parts = internal_id.split("-")
        if len(parts) < 3:
            raise ValueError(
                f"Invalid internal ID format: '{internal_id}'. "
                f"Expected: TASK-XXX-hash or EPIC-XXX-hash"
            )

        prefix = parts[0]
        if prefix not in {"TASK", "EPIC", "FEAT", "DOC"}:
            raise ValueError(
                f"Invalid internal ID prefix: '{prefix}'. "
                f"Expected: TASK, EPIC, FEAT, or DOC"
            )

    def get_counter_status(self) -> Dict:
        """
        Get current counter state for all tools (debugging/testing).

        Returns:
            Dictionary of counter states
        """
        return {
            "jira": dict(self.counters["jira"]),
            "azure_devops": self.counters["azure_devops"],
            "linear": dict(self.counters["linear"]),
            "github": self.counters["github"]
        }

    def reset_counters(self):
        """
        Reset all counters to initial state (testing only).

        Warning: This will cause ID collisions if used in production!
        """
        self.counters = {
            "jira": {},
            "azure_devops": 0,
            "linear": {},
            "github": 0
        }

    def clear_mappings(self):
        """
        Clear all mappings (testing only).

        Warning: This will lose all mapping data!
        """
        self.mappings = {}


# Singleton instance for global use
_mapper_instance = None
_instance_lock = threading.Lock()


def get_mapper(persistence: Optional['ExternalIDPersistence'] = None) -> ExternalIDMapper:
    """
    Get singleton mapper instance with persistence support (thread-safe).

    Args:
        persistence: Optional persistence layer. If provided, used for singleton.
                     If None and mapper doesn't exist, uses default persistence.

    Returns:
        Global ExternalIDMapper instance

    Example:
        >>> from lib.external_id_mapper import get_mapper
        >>> mapper = get_mapper()  # Uses default persistence
        >>> external_id = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
    """
    global _mapper_instance

    if _mapper_instance is None:
        with _instance_lock:
            # Double-check pattern
            if _mapper_instance is None:
                # Use provided persistence or create default
                if persistence is None:
                    from external_id_persistence import ExternalIDPersistence
                    persistence = ExternalIDPersistence()
                _mapper_instance = ExternalIDMapper(persistence)

    return _mapper_instance
