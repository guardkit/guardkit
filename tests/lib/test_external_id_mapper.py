"""
Comprehensive test suite for ExternalIDMapper

Tests cover:
- Mapping creation for all 4 PM tools
- Reverse lookup functionality
- Counter increment and sequencing
- Thread safety with concurrent operations
- Integration scenarios
- Edge cases and error handling

Target Coverage: ≥85%
"""

import pytest
import threading
import sys
from pathlib import Path
from typing import List

# Add installer/core/lib to path to handle 'global' keyword issue
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "lib"))

from external_id_mapper import (
    ExternalIDMapper,
    get_mapper
)


class TestMappingCreation:
    """Test mapping creation for all PM tools."""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance for each test."""
        return ExternalIDMapper()

    def test_jira_format_first_mapping(self, mapper):
        """Test JIRA format: PROJECT-1"""
        external_id = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        assert external_id == "PROJ-1"

    def test_jira_format_sequential(self, mapper):
        """Test JIRA sequential numbering"""
        id1 = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        id2 = mapper.map_to_external("TASK-E02-c3d5", "jira", "PROJ")
        id3 = mapper.map_to_external("TASK-E03-d4e6", "jira", "PROJ")

        assert id1 == "PROJ-1"
        assert id2 == "PROJ-2"
        assert id3 == "PROJ-3"

    def test_jira_multiple_projects(self, mapper):
        """Test JIRA per-project counters"""
        proj1 = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        test1 = mapper.map_to_external("TASK-E02-c3d5", "jira", "TEST")
        proj2 = mapper.map_to_external("TASK-E03-d4e6", "jira", "PROJ")
        test2 = mapper.map_to_external("TASK-E04-e5f7", "jira", "TEST")

        assert proj1 == "PROJ-1"
        assert test1 == "TEST-1"
        assert proj2 == "PROJ-2"
        assert test2 == "TEST-2"

    def test_azure_devops_format(self, mapper):
        """Test Azure DevOps format: 1234"""
        id1 = mapper.map_to_external("TASK-E01-b2c4", "azure_devops")
        id2 = mapper.map_to_external("TASK-E02-c3d5", "azure_devops")

        assert id1 == "1"
        assert id2 == "2"

    def test_linear_format(self, mapper):
        """Test Linear format: TEAM-789"""
        external_id = mapper.map_to_external("TASK-E01-b2c4", "linear", "TEAM")
        assert external_id == "TEAM-1"

    def test_linear_multiple_teams(self, mapper):
        """Test Linear per-team counters"""
        team1 = mapper.map_to_external("TASK-E01-b2c4", "linear", "TEAM")
        design1 = mapper.map_to_external("TASK-E02-c3d5", "linear", "DESIGN")
        team2 = mapper.map_to_external("TASK-E03-d4e6", "linear", "TEAM")

        assert team1 == "TEAM-1"
        assert design1 == "DESIGN-1"
        assert team2 == "TEAM-2"

    def test_github_format(self, mapper):
        """Test GitHub format: 234"""
        id1 = mapper.map_to_external("TASK-E01-b2c4", "github")
        id2 = mapper.map_to_external("TASK-E02-c3d5", "github")

        assert id1 == "1"
        assert id2 == "2"

    def test_multiple_mappings_per_internal_id(self, mapper):
        """Test mapping one internal ID to multiple PM tools"""
        internal_id = "TASK-E01-b2c4"

        jira_id = mapper.map_to_external(internal_id, "jira", "PROJ")
        azure_id = mapper.map_to_external(internal_id, "azure_devops")
        linear_id = mapper.map_to_external(internal_id, "linear", "TEAM")
        github_id = mapper.map_to_external(internal_id, "github")

        assert jira_id == "PROJ-1"
        assert azure_id == "1"
        assert linear_id == "TEAM-1"
        assert github_id == "1"

    def test_idempotent_mapping(self, mapper):
        """Test mapping same internal ID twice returns same external ID"""
        id1 = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        id2 = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")

        assert id1 == id2 == "PROJ-1"

    def test_case_insensitive_project_keys(self, mapper):
        """Test project keys are normalized to uppercase"""
        lower = mapper.map_to_external("TASK-E01-b2c4", "jira", "proj")
        upper = mapper.map_to_external("TASK-E02-c3d5", "jira", "PROJ")
        mixed = mapper.map_to_external("TASK-E03-d4e6", "jira", "PrOj")

        assert lower == "PROJ-1"
        assert upper == "PROJ-2"
        assert mixed == "PROJ-3"

    def test_invalid_tool_name(self, mapper):
        """Test error on unsupported tool name"""
        with pytest.raises(ValueError, match="Unsupported tool"):
            mapper.map_to_external("TASK-E01-b2c4", "trello", "PROJ")

    def test_missing_project_key_for_keyed_tool(self, mapper):
        """Test error when JIRA/Linear missing project key"""
        with pytest.raises(ValueError, match="requires a project/team key"):
            mapper.map_to_external("TASK-E01-b2c4", "jira", "")

    def test_epic_id_format(self, mapper):
        """Test mapping works with EPIC prefix"""
        external_id = mapper.map_to_external("EPIC-001-a1b2", "jira", "PROJ")
        assert external_id == "PROJ-1"

    def test_feat_id_format(self, mapper):
        """Test mapping works with FEAT prefix"""
        external_id = mapper.map_to_external("FEAT-ABC-x9y8", "jira", "PROJ")
        assert external_id == "PROJ-1"

    def test_doc_id_format(self, mapper):
        """Test mapping works with DOC prefix"""
        external_id = mapper.map_to_external("DOC-XYZ-z7w6", "jira", "PROJ")
        assert external_id == "PROJ-1"


class TestReverseLookup:
    """Test reverse lookup: external → internal"""

    @pytest.fixture
    def mapper_with_data(self):
        """Create mapper with pre-existing mappings"""
        mapper = ExternalIDMapper()
        mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        mapper.map_to_external("TASK-E01-b2c4", "azure_devops")
        mapper.map_to_external("TASK-E02-c3d5", "jira", "PROJ")
        mapper.map_to_external("TASK-E03-d4e6", "linear", "TEAM")
        return mapper

    def test_successful_jira_lookup(self, mapper_with_data):
        """Test successful JIRA reverse lookup"""
        internal_id = mapper_with_data.get_internal_id("PROJ-1", "jira")
        assert internal_id == "TASK-E01-b2c4"

    def test_successful_azure_lookup(self, mapper_with_data):
        """Test successful Azure DevOps reverse lookup"""
        internal_id = mapper_with_data.get_internal_id("1", "azure_devops")
        assert internal_id == "TASK-E01-b2c4"

    def test_successful_linear_lookup(self, mapper_with_data):
        """Test successful Linear reverse lookup"""
        internal_id = mapper_with_data.get_internal_id("TEAM-1", "linear")
        assert internal_id == "TASK-E03-d4e6"

    def test_nonexistent_mapping(self, mapper_with_data):
        """Test lookup returns None for non-existent mapping"""
        internal_id = mapper_with_data.get_internal_id("PROJ-999", "jira")
        assert internal_id is None

    def test_empty_mapper_lookup(self):
        """Test lookup on empty mapper returns None"""
        mapper = ExternalIDMapper()
        internal_id = mapper.get_internal_id("PROJ-1", "jira")
        assert internal_id is None

    def test_invalid_tool_lookup(self, mapper_with_data):
        """Test error on unsupported tool in lookup"""
        with pytest.raises(ValueError, match="Unsupported tool"):
            mapper_with_data.get_internal_id("PROJ-1", "invalid_tool")

    def test_case_sensitivity(self, mapper_with_data):
        """Test external ID lookup is case-sensitive"""
        # Mapping stored as "PROJ-1"
        assert mapper_with_data.get_internal_id("PROJ-1", "jira") is not None
        assert mapper_with_data.get_internal_id("proj-1", "jira") is None


class TestCounterManagement:
    """Test counter increment and sequencing"""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance"""
        return ExternalIDMapper()

    def test_sequential_increment_jira(self, mapper):
        """Test JIRA counter increments sequentially"""
        assert mapper.increment_counter("jira", "PROJ") == 1
        assert mapper.increment_counter("jira", "PROJ") == 2
        assert mapper.increment_counter("jira", "PROJ") == 3

    def test_sequential_increment_azure(self, mapper):
        """Test Azure DevOps global counter"""
        assert mapper.increment_counter("azure_devops") == 1
        assert mapper.increment_counter("azure_devops") == 2
        assert mapper.increment_counter("azure_devops") == 3

    def test_independent_project_counters(self, mapper):
        """Test JIRA counters are independent per project"""
        assert mapper.increment_counter("jira", "PROJ") == 1
        assert mapper.increment_counter("jira", "TEST") == 1
        assert mapper.increment_counter("jira", "PROJ") == 2
        assert mapper.increment_counter("jira", "TEST") == 2

    def test_independent_team_counters(self, mapper):
        """Test Linear counters are independent per team"""
        assert mapper.increment_counter("linear", "TEAM") == 1
        assert mapper.increment_counter("linear", "DESIGN") == 1
        assert mapper.increment_counter("linear", "TEAM") == 2

    def test_independent_tool_counters(self, mapper):
        """Test counters are independent across tools"""
        assert mapper.increment_counter("jira", "PROJ") == 1
        assert mapper.increment_counter("azure_devops") == 1
        assert mapper.increment_counter("linear", "TEAM") == 1
        assert mapper.increment_counter("github") == 1

        assert mapper.increment_counter("jira", "PROJ") == 2
        assert mapper.increment_counter("azure_devops") == 2

    def test_counter_initialization(self, mapper):
        """Test counter starts at 0 and first increment returns 1"""
        counter = mapper.increment_counter("github")
        assert counter == 1

    def test_missing_key_for_keyed_tool(self, mapper):
        """Test error when key missing for JIRA/Linear"""
        with pytest.raises(ValueError, match="requires a key"):
            mapper.increment_counter("jira")

        with pytest.raises(ValueError, match="requires a key"):
            mapper.increment_counter("linear")

    def test_get_counter_status(self, mapper):
        """Test counter status retrieval"""
        mapper.increment_counter("jira", "PROJ")
        mapper.increment_counter("jira", "PROJ")
        mapper.increment_counter("azure_devops")

        status = mapper.get_counter_status()

        assert status["jira"]["PROJ"] == 2
        assert status["azure_devops"] == 1
        assert status["github"] == 0


class TestThreadSafety:
    """Test concurrent operations and thread safety"""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance"""
        return ExternalIDMapper()

    def test_concurrent_counter_increments(self, mapper):
        """Test 10 simultaneous counter increments have no collisions"""
        results = []
        threads = []

        def increment_counter():
            counter = mapper.increment_counter("azure_devops")
            results.append(counter)

        # Create and start 10 threads
        for _ in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all counters are unique and sequential
        assert len(results) == 10
        assert sorted(results) == list(range(1, 11))
        assert len(set(results)) == 10  # No duplicates

    def test_concurrent_mappings_different_internal_ids(self, mapper):
        """Test concurrent mappings for different internal IDs"""
        results = []
        threads = []

        def create_mapping(internal_id: str, index: int):
            external_id = mapper.map_to_external(
                internal_id,
                "jira",
                "PROJ"
            )
            results.append((internal_id, external_id, index))

        # Create 10 mappings concurrently
        for i in range(10):
            internal_id = f"TASK-E{i:02d}-test"
            thread = threading.Thread(
                target=create_mapping,
                args=(internal_id, i)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all mappings created
        assert len(results) == 10

        # Verify all external IDs are unique
        external_ids = [r[1] for r in results]
        assert len(set(external_ids)) == 10

        # Verify all are in PROJ-X format
        for _, external_id, _ in results:
            assert external_id.startswith("PROJ-")

    def test_concurrent_same_internal_id_mapping(self, mapper):
        """Test concurrent mapping of same internal ID returns same external ID"""
        results = []
        threads = []
        internal_id = "TASK-E01-b2c4"

        def create_mapping():
            external_id = mapper.map_to_external(
                internal_id,
                "jira",
                "PROJ"
            )
            results.append(external_id)

        # Try to create same mapping 5 times concurrently
        for _ in range(5):
            thread = threading.Thread(target=create_mapping)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should get same external ID
        assert len(set(results)) == 1
        assert results[0] == "PROJ-1"

    def test_performance_10_concurrent_operations(self, mapper):
        """Test 10 concurrent operations complete in <5s"""
        import time

        start_time = time.time()

        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=mapper.map_to_external,
                args=(f"TASK-E{i:02d}-test", "azure_devops")
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time
        assert elapsed < 5.0, f"Concurrent operations took {elapsed:.2f}s (max: 5s)"


class TestGetAllMappings:
    """Test getting all mappings for an internal ID"""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance"""
        return ExternalIDMapper()

    def test_get_all_mappings_single_tool(self, mapper):
        """Test get all mappings with one tool"""
        mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")

        mappings = mapper.get_all_mappings("TASK-E01-b2c4")
        assert mappings == {"jira": "PROJ-1"}

    def test_get_all_mappings_multiple_tools(self, mapper):
        """Test get all mappings with multiple tools"""
        internal_id = "TASK-E01-b2c4"
        mapper.map_to_external(internal_id, "jira", "PROJ")
        mapper.map_to_external(internal_id, "azure_devops")
        mapper.map_to_external(internal_id, "github")

        mappings = mapper.get_all_mappings(internal_id)
        assert mappings == {
            "jira": "PROJ-1",
            "azure_devops": "1",
            "github": "1"
        }

    def test_get_all_mappings_nonexistent_id(self, mapper):
        """Test get all mappings returns empty dict for unknown ID"""
        mappings = mapper.get_all_mappings("TASK-UNKNOWN-x9y8")
        assert mappings == {}

    def test_get_all_mappings_returns_copy(self, mapper):
        """Test returned dict is a copy, not reference"""
        internal_id = "TASK-E01-b2c4"
        mapper.map_to_external(internal_id, "jira", "PROJ")

        mappings1 = mapper.get_all_mappings(internal_id)
        mappings1["azure_devops"] = "999"  # Modify copy

        mappings2 = mapper.get_all_mappings(internal_id)
        assert "azure_devops" not in mappings2  # Original unchanged


class TestValidation:
    """Test input validation and error handling"""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance"""
        return ExternalIDMapper()

    def test_empty_internal_id(self, mapper):
        """Test error on empty internal ID"""
        with pytest.raises(ValueError, match="cannot be empty"):
            mapper.map_to_external("", "jira", "PROJ")

    def test_invalid_internal_id_format_too_short(self, mapper):
        """Test error on invalid internal ID format"""
        with pytest.raises(ValueError, match="Invalid internal ID format"):
            mapper.map_to_external("TASK", "jira", "PROJ")

    def test_invalid_internal_id_prefix(self, mapper):
        """Test error on invalid prefix"""
        with pytest.raises(ValueError, match="Invalid internal ID prefix"):
            mapper.map_to_external("INVALID-E01-b2c4", "jira", "PROJ")

    def test_valid_prefixes_accepted(self, mapper):
        """Test all valid prefixes work"""
        valid_prefixes = ["TASK", "EPIC", "FEAT", "DOC"]

        for prefix in valid_prefixes:
            internal_id = f"{prefix}-E01-test"
            external_id = mapper.map_to_external(internal_id, "azure_devops")
            assert external_id  # Should not raise


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    def test_round_trip_internal_to_external_to_internal(self):
        """Test complete round trip mapping"""
        mapper = ExternalIDMapper()
        internal_id = "TASK-E01-b2c4"

        # Forward mapping
        external_id = mapper.map_to_external(internal_id, "jira", "PROJ")
        assert external_id == "PROJ-1"

        # Reverse lookup
        found_internal = mapper.get_internal_id(external_id, "jira")
        assert found_internal == internal_id

    def test_multi_tool_integration(self):
        """Test integrating one internal ID with multiple PM tools"""
        mapper = ExternalIDMapper()
        internal_id = "TASK-E01-b2c4"

        # Map to all 4 tools
        jira_id = mapper.map_to_external(internal_id, "jira", "PROJ")
        azure_id = mapper.map_to_external(internal_id, "azure_devops")
        linear_id = mapper.map_to_external(internal_id, "linear", "TEAM")
        github_id = mapper.map_to_external(internal_id, "github")

        # Verify all reverse lookups work
        assert mapper.get_internal_id(jira_id, "jira") == internal_id
        assert mapper.get_internal_id(azure_id, "azure_devops") == internal_id
        assert mapper.get_internal_id(linear_id, "linear") == internal_id
        assert mapper.get_internal_id(github_id, "github") == internal_id

        # Verify get_all_mappings
        all_mappings = mapper.get_all_mappings(internal_id)
        assert len(all_mappings) == 4
        assert all_mappings["jira"] == jira_id
        assert all_mappings["azure_devops"] == azure_id
        assert all_mappings["linear"] == linear_id
        assert all_mappings["github"] == github_id

    def test_realistic_jira_project_workflow(self):
        """Test realistic JIRA project with multiple tasks"""
        mapper = ExternalIDMapper()

        tasks = [
            ("TASK-E01-b2c4", "Feature: User login"),
            ("TASK-E02-c3d5", "Feature: Password reset"),
            ("TASK-E03-d4e6", "Bug: Login button alignment"),
            ("EPIC-001-a1b2", "Epic: Authentication system"),
        ]

        # Create JIRA mappings
        for internal_id, _ in tasks:
            external_id = mapper.map_to_external(internal_id, "jira", "AUTH")

        # Verify sequential numbering
        assert mapper.get_internal_id("AUTH-1", "jira") == "TASK-E01-b2c4"
        assert mapper.get_internal_id("AUTH-2", "jira") == "TASK-E02-c3d5"
        assert mapper.get_internal_id("AUTH-3", "jira") == "TASK-E03-d4e6"
        assert mapper.get_internal_id("AUTH-4", "jira") == "EPIC-001-a1b2"

    def test_edge_case_special_characters_in_keys(self):
        """Test project keys with underscores and numbers"""
        mapper = ExternalIDMapper()

        # Keys with numbers and underscores
        id1 = mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ_2025")
        id2 = mapper.map_to_external("TASK-E02-c3d5", "linear", "TEAM_UI")

        assert id1 == "PROJ_2025-1"
        assert id2 == "TEAM_UI-1"


class TestSingletonInstance:
    """Test singleton pattern for get_mapper()"""

    def test_get_mapper_returns_instance(self):
        """Test get_mapper returns ExternalIDMapper instance"""
        mapper = get_mapper()
        assert isinstance(mapper, ExternalIDMapper)

    def test_get_mapper_returns_same_instance(self):
        """Test get_mapper returns singleton"""
        mapper1 = get_mapper()
        mapper2 = get_mapper()
        assert mapper1 is mapper2

    def test_singleton_state_persists(self):
        """Test state persists across get_mapper calls"""
        mapper1 = get_mapper()
        mapper1.map_to_external("TASK-E01-b2c4", "jira", "PROJ")

        mapper2 = get_mapper()
        internal_id = mapper2.get_internal_id("PROJ-1", "jira")
        assert internal_id == "TASK-E01-b2c4"

    def test_thread_safe_singleton_creation(self):
        """Test singleton creation is thread-safe"""
        # Reset singleton for this test
        import external_id_mapper as mapper_module
        mapper_module._mapper_instance = None

        results = []

        def get_mapper_id():
            mapper = get_mapper()
            results.append(id(mapper))

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_mapper_id)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get same instance
        assert len(set(results)) == 1


class TestUtilityMethods:
    """Test utility/helper methods"""

    @pytest.fixture
    def mapper(self):
        """Create fresh mapper instance"""
        return ExternalIDMapper()

    def test_reset_counters(self, mapper):
        """Test counter reset functionality"""
        mapper.increment_counter("azure_devops")
        mapper.increment_counter("azure_devops")
        assert mapper.counters["azure_devops"] == 2

        mapper.reset_counters()
        assert mapper.counters["azure_devops"] == 0

    def test_clear_mappings(self, mapper):
        """Test mappings clear functionality"""
        mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
        assert len(mapper.mappings) == 1

        mapper.clear_mappings()
        assert len(mapper.mappings) == 0

    def test_get_counter_status_empty_mapper(self, mapper):
        """Test counter status on fresh mapper"""
        status = mapper.get_counter_status()

        assert status["jira"] == {}
        assert status["azure_devops"] == 0
        assert status["linear"] == {}
        assert status["github"] == 0
