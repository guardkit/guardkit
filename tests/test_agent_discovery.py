"""
Unit Tests for Agent Discovery Module.

Task Reference: TASK-HAI-005-7A2E
Epic: haiku-agent-implementation

Tests cover:
- Discovery by phase (required filter)
- Discovery by stack (optional filter)
- Keyword scoring and relevance
- Graceful degradation (missing metadata, invalid files)
- Edge cases (empty results, duplicate handling)
- Validation functions
- Performance requirements
"""

import logging
import os
import pytest
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"))

from agent_discovery import (
    discover_agents,
    get_agent_by_name,
    list_discoverable_agents,
    get_agents_by_stack,
    validate_discovery_metadata,
    VALID_STACKS,
    VALID_PHASES,
    _extract_metadata,
    _matches_criteria,
    _calculate_relevance_score,
    _sort_by_relevance,
    _parse_frontmatter_regex,
    _scan_agent_locations,
    _get_agent_locations,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create a temporary directory with test agent files."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    return agents_dir


@pytest.fixture
def sample_python_agent_content():
    """Sample Python API Specialist agent content."""
    return """---
name: python-api-specialist
description: FastAPI endpoint and Pydantic model implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

# Discovery metadata
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling patterns
  - Dependency injection via Depends()
  - Pydantic schema integration
keywords: [fastapi, async, endpoints, router, dependency-injection, pydantic, python-api, rest, http, validation]

collaborates_with:
  - python-testing-specialist
  - database-specialist
---

# Python API Specialist Agent

You are a Python API implementation specialist.
"""


@pytest.fixture
def sample_react_agent_content():
    """Sample React State Specialist agent content."""
    return """---
name: react-state-specialist
description: React hooks and state management implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

stack: [react, typescript]
phase: implementation
capabilities:
  - React hooks implementation
  - TanStack Query for server state
  - State management patterns
keywords: [react, hooks, state, tanstack-query, zustand, typescript, components]

collaborates_with:
  - react-testing-specialist
---

# React State Specialist
"""


@pytest.fixture
def sample_dotnet_agent_content():
    """Sample .NET Domain Specialist agent content."""
    return """---
name: dotnet-domain-specialist
description: .NET domain model and DDD patterns implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

stack: [dotnet, csharp]
phase: implementation
capabilities:
  - Entity design with encapsulation
  - Value object implementation
  - Domain events and event handlers
keywords: [csharp, dotnet, domain-model, entity, value-object, ddd, aggregate, domain-event, repository, cqrs]
---

# .NET Domain Specialist
"""


@pytest.fixture
def sample_review_agent_content():
    """Sample review phase agent content."""
    return """---
name: code-reviewer
description: Code review specialist
tools: [Read, Grep]
model: sonnet

stack: [cross-stack]
phase: review
capabilities:
  - Code quality assessment
  - Best practices enforcement
keywords: [review, quality, standards, refactoring]
---

# Code Reviewer
"""


@pytest.fixture
def sample_agent_without_metadata():
    """Sample agent without discovery metadata."""
    return """---
name: legacy-agent
description: An old agent without discovery metadata
tools: [Read, Write]
---

# Legacy Agent

This agent has no phase or stack metadata.
"""


@pytest.fixture
def create_test_agents(temp_agent_dir, sample_python_agent_content,
                       sample_react_agent_content, sample_dotnet_agent_content,
                       sample_review_agent_content, sample_agent_without_metadata):
    """Create test agent files and return the directory path."""
    # Write agent files
    (temp_agent_dir / "python-api-specialist.md").write_text(sample_python_agent_content)
    (temp_agent_dir / "react-state-specialist.md").write_text(sample_react_agent_content)
    (temp_agent_dir / "dotnet-domain-specialist.md").write_text(sample_dotnet_agent_content)
    (temp_agent_dir / "code-reviewer.md").write_text(sample_review_agent_content)
    (temp_agent_dir / "legacy-agent.md").write_text(sample_agent_without_metadata)

    return temp_agent_dir


# ============================================================================
# Test: Phase Filtering (Required)
# ============================================================================

class TestPhaseFiltering:
    """Tests for phase-based agent discovery."""

    def test_discover_by_phase_only(self, create_test_agents):
        """Should find all implementation agents."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='implementation')

            assert len(results) >= 3  # Python, React, .NET
            assert all(r['phase'] == 'implementation' for r in results)

    def test_discover_review_phase(self, create_test_agents):
        """Should find review phase agents."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='review')

            assert len(results) >= 1
            assert all(r['phase'] == 'review' for r in results)

    def test_phase_is_required(self, create_test_agents):
        """Phase must be specified - no default."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            # Empty phase should return no results
            results = discover_agents(phase='')
            assert results == []

    def test_phase_case_insensitive(self, create_test_agents):
        """Phase matching should be case insensitive."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results_lower = discover_agents(phase='implementation')
            results_upper = discover_agents(phase='IMPLEMENTATION')
            results_mixed = discover_agents(phase='Implementation')

            assert len(results_lower) == len(results_upper) == len(results_mixed)


# ============================================================================
# Test: Stack Filtering (Optional)
# ============================================================================

class TestStackFiltering:
    """Tests for stack-based agent filtering."""

    def test_discover_by_stack(self, create_test_agents):
        """Should filter by stack."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='implementation', stack=['python'])

            assert len(results) >= 1
            for r in results:
                stacks = r.get('stack', [])
                if isinstance(stacks, str):
                    stacks = [stacks]
                assert 'python' in [s.lower() for s in stacks] or 'cross-stack' in [s.lower() for s in stacks]

    def test_discover_multi_stack(self, create_test_agents):
        """Should handle multi-stack agents."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='implementation', stack=['react', 'typescript'])

            assert len(results) >= 1
            # Find the React agent
            react_agents = [r for r in results if 'react' in [s.lower() for s in r.get('stack', [])]]
            assert len(react_agents) >= 1
            # React agent should also have typescript
            for agent in react_agents:
                stacks_lower = [s.lower() for s in agent.get('stack', [])]
                assert 'typescript' in stacks_lower

    def test_cross_stack_agent(self, create_test_agents):
        """Should find cross-stack agents for any stack query."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            # Cross-stack agents should appear for review phase with any stack
            results = discover_agents(phase='review', stack=['python'])

            cross_stack_agents = [r for r in results if 'cross-stack' in r.get('stack', [])]
            assert len(cross_stack_agents) >= 1

    def test_stack_case_insensitive(self, create_test_agents):
        """Stack matching should be case insensitive."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results_lower = discover_agents(phase='implementation', stack=['python'])
            results_upper = discover_agents(phase='implementation', stack=['PYTHON'])

            assert len(results_lower) == len(results_upper)

    def test_empty_stack_list(self, create_test_agents):
        """Empty stack list should not filter by stack."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            # Should return all implementation agents
            results_no_stack = discover_agents(phase='implementation', stack=[])
            results_none_stack = discover_agents(phase='implementation', stack=None)

            assert len(results_no_stack) == len(results_none_stack)


# ============================================================================
# Test: Keyword Scoring
# ============================================================================

class TestKeywordScoring:
    """Tests for keyword-based relevance scoring."""

    def test_keyword_scoring(self, create_test_agents):
        """Should rank by keyword relevance."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(
                phase='implementation',
                stack=['python'],
                keywords=['fastapi', 'async', 'endpoints']
            )

            assert len(results) >= 1
            # Python agent should have highest score
            assert results[0]['relevance_score'] >= 2

    def test_min_capability_threshold(self, create_test_agents):
        """Should respect min_capability_match parameter."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(
                phase='implementation',
                keywords=['fastapi', 'async'],
                min_capability_match=2
            )

            # All results should have at least 2 matches
            for r in results:
                assert r.get('relevance_score', 0) >= 2

    def test_keyword_case_insensitive(self, create_test_agents):
        """Keyword matching should be case insensitive."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results_lower = discover_agents(
                phase='implementation',
                keywords=['fastapi']
            )
            results_upper = discover_agents(
                phase='implementation',
                keywords=['FASTAPI']
            )

            assert len(results_lower) == len(results_upper)

    def test_keyword_matches_capabilities(self, create_test_agents):
        """Keywords should also match in capabilities text."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            # "Pydantic" appears in capabilities
            results = discover_agents(
                phase='implementation',
                keywords=['pydantic']
            )

            assert len(results) >= 1


# ============================================================================
# Test: Graceful Degradation
# ============================================================================

class TestGracefulDegradation:
    """Tests for graceful handling of edge cases."""

    def test_graceful_degradation_no_metadata(self, create_test_agents):
        """Should skip agents without phase field."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='implementation')

            # Should succeed even with legacy-agent lacking metadata
            assert isinstance(results, list)
            # legacy-agent should not be in results
            agent_names = [r.get('name') for r in results]
            assert 'legacy-agent' not in agent_names

    def test_no_agents_found(self, create_test_agents):
        """Should return empty list if no matches."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = discover_agents(phase='nonexistent-phase')

            assert results == []
            assert isinstance(results, list)

    def test_handles_invalid_paths(self, temp_agent_dir):
        """Should skip agents with read errors."""
        # Create an unreadable file (simulate permission error)
        unreadable = temp_agent_dir / "unreadable.md"
        unreadable.write_text("---\nname: test\n---")

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            # Mock file read to raise an exception
            original_read_text = Path.read_text

            def mock_read_text(self, *args, **kwargs):
                if 'unreadable' in str(self):
                    raise PermissionError("Cannot read file")
                return original_read_text(self, *args, **kwargs)

            with patch.object(Path, 'read_text', mock_read_text):
                # Should not raise an exception
                results = discover_agents(phase='implementation')
                assert isinstance(results, list)

    def test_handles_malformed_frontmatter(self, temp_agent_dir):
        """Should handle malformed YAML frontmatter gracefully."""
        malformed = temp_agent_dir / "malformed.md"
        malformed.write_text("""---
name: test
stack: [this is not valid yaml
---

Content here
""")

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            # Should not raise an exception
            results = discover_agents(phase='implementation')
            assert isinstance(results, list)

    def test_empty_agent_directory(self, temp_agent_dir):
        """Should handle empty directories gracefully."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            results = discover_agents(phase='implementation')

            assert results == []

    def test_nonexistent_directory(self):
        """Should handle nonexistent directories gracefully."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [Path("/nonexistent/path")]

            results = discover_agents(phase='implementation')

            assert results == []


# ============================================================================
# Test: Duplicate Handling
# ============================================================================

class TestDuplicateHandling:
    """Tests for handling duplicate agents."""

    def test_duplicate_agents_handled(self, temp_agent_dir, sample_python_agent_content):
        """Should handle duplicate agent files across locations."""
        # Create two directories with the same agent
        dir1 = temp_agent_dir / "dir1"
        dir2 = temp_agent_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "python-api-specialist.md").write_text(sample_python_agent_content)
        (dir2 / "python-api-specialist.md").write_text(sample_python_agent_content)

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [dir1, dir2]

            results = discover_agents(phase='implementation', stack=['python'])

            # Should have results (duplicates are acceptable)
            assert len(results) >= 1


# ============================================================================
# Test: Validation Functions
# ============================================================================

class TestValidation:
    """Tests for metadata validation."""

    def test_valid_metadata_passes(self):
        """Valid metadata should pass validation."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation',
            'capabilities': ['API design', 'FastAPI patterns'],
            'keywords': ['fastapi', 'async', 'api']
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert is_valid
        assert len(errors) == 0

    def test_missing_required_field_fails(self):
        """Missing required field should fail validation."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation'
            # Missing capabilities and keywords
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('capabilities' in e for e in errors)
        assert any('keywords' in e for e in errors)

    def test_invalid_stack_fails(self):
        """Invalid stack value should fail validation."""
        metadata = {
            'stack': ['invalid-stack'],
            'phase': 'implementation',
            'capabilities': ['API design'],
            'keywords': ['api', 'test', 'validation']
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('invalid-stack' in e for e in errors)

    def test_invalid_phase_fails(self):
        """Invalid phase value should fail validation."""
        metadata = {
            'stack': ['python'],
            'phase': 'invalid-phase',
            'capabilities': ['API design'],
            'keywords': ['api', 'test', 'validation']
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('phase' in e for e in errors)

    def test_too_many_capabilities_warns(self):
        """More than 10 capabilities should generate error."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation',
            'capabilities': [f'Cap{i}' for i in range(15)],
            'keywords': ['python', 'api', 'test']
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('at most 10' in e for e in errors)

    def test_too_few_keywords_fails(self):
        """Less than 3 keywords should fail."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation',
            'capabilities': ['API design'],
            'keywords': ['api']  # Only 1 keyword
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('at least 3' in e for e in errors)

    def test_too_many_keywords_warns(self):
        """More than 15 keywords should generate error."""
        metadata = {
            'stack': ['python'],
            'phase': 'implementation',
            'capabilities': ['API design'],
            'keywords': [f'kw{i}' for i in range(20)]
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('at most 15' in e for e in errors)

    def test_empty_stack_fails(self):
        """Empty stack array should fail."""
        metadata = {
            'stack': [],
            'phase': 'implementation',
            'capabilities': ['API design'],
            'keywords': ['api', 'test', 'validation']
        }

        is_valid, errors = validate_discovery_metadata(metadata)

        assert not is_valid
        assert any('at least 1' in e for e in errors)


# ============================================================================
# Test: Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Tests for helper/utility functions."""

    def test_get_agent_by_name(self, create_test_agents):
        """Should find agent by name."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            result = get_agent_by_name('python-api-specialist')

            assert result is not None
            assert result['name'] == 'python-api-specialist'

    def test_get_agent_by_name_not_found(self, create_test_agents):
        """Should return None if agent not found."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            result = get_agent_by_name('nonexistent-agent')

            assert result is None

    def test_list_discoverable_agents(self, create_test_agents):
        """Should list all agents with discovery metadata."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = list_discoverable_agents()

            # Should include all agents with phase field
            assert len(results) >= 4  # Python, React, .NET, code-reviewer
            # Should not include legacy-agent (no phase)
            agent_names = [r.get('name') for r in results]
            assert 'legacy-agent' not in agent_names

    def test_get_agents_by_stack(self, create_test_agents):
        """Should get all agents for a stack (any phase)."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            results = get_agents_by_stack('python')

            assert len(results) >= 1
            for r in results:
                stacks = r.get('stack', [])
                if isinstance(stacks, str):
                    stacks = [stacks]
                stacks_lower = [s.lower() for s in stacks]
                assert 'python' in stacks_lower or 'cross-stack' in stacks_lower

    def test_parse_frontmatter_regex(self):
        """Should parse frontmatter using regex fallback."""
        content = """---
name: test-agent
description: A test agent
stack: [python, typescript]
phase: implementation
keywords: [test, agent]
---

# Content
"""
        result = _parse_frontmatter_regex(content)

        assert result['name'] == 'test-agent'
        assert result['description'] == 'A test agent'
        assert 'python' in result['stack']
        assert 'typescript' in result['stack']
        assert result['phase'] == 'implementation'

    def test_calculate_relevance_score(self):
        """Should calculate relevance score correctly."""
        metadata = {
            'stack': ['python'],
            'capabilities': ['API design', 'FastAPI'],
            'relevance_score': 3  # From keyword matching
        }

        score = _calculate_relevance_score(
            metadata,
            stack=['python'],
            keywords=['fastapi']
        )

        # Base score (3) + stack bonus (2) + capabilities bonus
        assert score >= 5

    def test_sort_by_relevance(self):
        """Should sort by relevance score descending."""
        results = [
            {'name': 'low', 'relevance_score': 1},
            {'name': 'high', 'relevance_score': 5},
            {'name': 'medium', 'relevance_score': 3},
        ]

        sorted_results = _sort_by_relevance(results)

        assert sorted_results[0]['name'] == 'high'
        assert sorted_results[1]['name'] == 'medium'
        assert sorted_results[2]['name'] == 'low'


# ============================================================================
# Test: Performance
# ============================================================================

class TestPerformance:
    """Tests for performance requirements."""

    def test_discovery_performance(self, create_test_agents):
        """Should scan agents in reasonable time (<500ms)."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            start = time.time()
            results = discover_agents(phase='implementation')
            duration = time.time() - start

            # Should complete in less than 500ms
            assert duration < 0.5, f"Discovery took {duration:.3f}s (max: 0.5s)"

    def test_repeated_discovery_performance(self, create_test_agents):
        """Multiple discoveries should complete quickly."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            start = time.time()
            for _ in range(10):
                discover_agents(phase='implementation', stack=['python'])
            duration = time.time() - start

            # 10 discoveries should complete in less than 2 seconds
            assert duration < 2.0, f"10 discoveries took {duration:.3f}s (max: 2.0s)"


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and corner cases."""

    def test_agent_with_string_stack(self, temp_agent_dir):
        """Should handle stack as string (not array)."""
        content = """---
name: string-stack-agent
description: Agent with string stack
stack: python
phase: implementation
capabilities: [Test]
keywords: [test, agent, python]
---
"""
        (temp_agent_dir / "string-stack.md").write_text(content)

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            results = discover_agents(phase='implementation', stack=['python'])

            assert len(results) >= 1

    def test_agent_with_string_keywords(self, temp_agent_dir):
        """Should handle keywords as string (not array)."""
        content = """---
name: string-kw-agent
description: Agent with string keywords
stack: [python]
phase: implementation
capabilities: [Test]
keywords: fastapi
---
"""
        (temp_agent_dir / "string-kw.md").write_text(content)

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            results = discover_agents(phase='implementation', keywords=['fastapi'])

            assert len(results) >= 1

    def test_special_characters_in_path(self, tmp_path):
        """Should handle special characters in agent paths."""
        special_dir = tmp_path / "agents with spaces"
        special_dir.mkdir()

        content = """---
name: special-agent
stack: [python]
phase: implementation
capabilities: [Test]
keywords: [test, agent, python]
---
"""
        (special_dir / "agent-name.md").write_text(content)

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [special_dir]

            results = discover_agents(phase='implementation')

            assert len(results) >= 1

    def test_unicode_in_agent_content(self, temp_agent_dir):
        """Should handle unicode characters in agent content."""
        content = """---
name: unicode-agent
description: Agent with unicode ??????
stack: [python]
phase: implementation
capabilities: [API design]
keywords: [test, agent, python]
---

# Agent with Unicode

This agent handles internationalization (i18n).
"""
        (temp_agent_dir / "unicode-agent.md").write_text(content, encoding='utf-8')

        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [temp_agent_dir]

            results = discover_agents(phase='implementation')

            assert len(results) >= 1


# ============================================================================
# Test: Logging
# ============================================================================

class TestLogging:
    """Tests for logging behavior."""

    def test_discovery_logs_results(self, create_test_agents, caplog):
        """Should log discovery results."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            with caplog.at_level(logging.INFO):
                discover_agents(phase='implementation')

            # Check that discovery was logged
            assert any('Discovery' in record.message for record in caplog.records)

    def test_skipped_agents_logged(self, create_test_agents, caplog):
        """Should log skipped agents (without metadata)."""
        with patch('agent_discovery._get_agent_locations') as mock_locations:
            mock_locations.return_value = [create_test_agents]

            with caplog.at_level(logging.DEBUG):
                discover_agents(phase='implementation')

            # Should have debug message about skipping
            log_text = ' '.join(record.message for record in caplog.records)
            # Either skipped message or the count should be present
            assert 'Skip' in log_text or 'skip' in log_text or 'found' in log_text


# ============================================================================
# Test: Valid Constants
# ============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_valid_stacks_defined(self):
        """Should have expected valid stacks."""
        expected = ['python', 'react', 'dotnet', 'typescript', 'javascript',
                   'go', 'rust', 'java', 'ruby', 'php', 'cross-stack']

        for stack in expected:
            assert stack in VALID_STACKS

    def test_valid_phases_defined(self):
        """Should have expected valid phases."""
        expected = ['implementation', 'review', 'testing', 'orchestration']

        assert set(VALID_PHASES) == set(expected)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
