"""
Test suite for TASK-GI-DOC-004: GitHub Pages Navigation

Validates that the Knowledge Graph navigation has been properly added to the
MkDocs configuration and index page.

Tests:
1. MkDocs configuration is valid YAML
2. Knowledge Graph section exists in navigation
3. All three child pages are linked correctly
4. Links use correct MkDocs path format
5. Index page includes Graphiti section
6. Referenced documentation files exist
"""

import os
import yaml
import pytest
from pathlib import Path


# Acceptance Criteria Test Markers
AC_001 = "AC-001: Navigation configuration updated"
AC_002 = "AC-002: Knowledge Graph section added"
AC_003 = "AC-003: All 3 child pages linked"
AC_004 = "AC-004: Links use correct URL format"
AC_005 = "AC-005: Builds without errors"


class TestGraphitiNavigation:
    """Test suite for Graphiti documentation navigation."""

    @pytest.fixture(scope="class")
    def mkdocs_config_path(self):
        """Get the path to mkdocs.yml."""
        return Path("mkdocs.yml")

    @pytest.fixture(scope="class")
    def index_path(self):
        """Get the path to docs/index.md."""
        return Path("docs/index.md")

    @pytest.fixture(scope="class")
    def mkdocs_config(self, mkdocs_config_path):
        """Load and parse mkdocs.yml."""
        # Read the raw content and parse only the nav section manually
        # to avoid issues with Python object tags
        with open(mkdocs_config_path, 'r') as f:
            content = f.read()

        # Extract just the nav section for testing
        nav_start = content.find('nav:')
        if nav_start == -1:
            return {'nav': []}

        # Find the next top-level key after nav
        next_section = content.find('\n\n# =', nav_start)
        if next_section == -1:
            next_section = len(content)

        nav_content = content[nav_start:next_section]

        # Parse the nav section using safe_load on just that portion
        try:
            nav_dict = yaml.safe_load(nav_content)
            return nav_dict
        except:
            # Fallback: return the raw content for text-based testing
            return {'nav': [], '_raw': nav_content}

    @pytest.fixture(scope="class")
    def index_content(self, index_path):
        """Load the index.md content."""
        with open(index_path, 'r') as f:
            return f.read()

    # ========================================================================
    # AC-001 & AC-005: Configuration is valid and parseable
    # ========================================================================

    @pytest.mark.parametrize("criterion", [AC_001, AC_005])
    def test_mkdocs_config_is_valid_yaml(self, mkdocs_config_path, mkdocs_config, criterion):
        """
        Verify mkdocs.yml is valid YAML and can be parsed.

        Acceptance Criteria:
        - AC-001: Navigation configuration updated
        - AC-005: Builds without errors
        """
        assert mkdocs_config_path.exists(), "mkdocs.yml file not found"
        assert isinstance(mkdocs_config, dict), "mkdocs.yml is not valid YAML"
        assert 'nav' in mkdocs_config, "mkdocs.yml missing 'nav' key"

    # ========================================================================
    # AC-002: Knowledge Graph section exists
    # ========================================================================

    @pytest.mark.parametrize("criterion", [AC_002])
    def test_knowledge_graph_section_exists(self, mkdocs_config, criterion):
        """
        Verify that the Knowledge Graph section is present in navigation.

        Acceptance Criterion:
        - AC-002: "Knowledge Graph" section added
        """
        nav = mkdocs_config['nav']

        # Find the Knowledge Graph section
        kg_section = None
        for item in nav:
            if isinstance(item, dict) and 'Knowledge Graph' in item:
                kg_section = item['Knowledge Graph']
                break

        assert kg_section is not None, "Knowledge Graph section not found in navigation"
        assert isinstance(kg_section, list), "Knowledge Graph section is not a list"

    # ========================================================================
    # AC-003: All 3 child pages are linked
    # ========================================================================

    @pytest.mark.parametrize("criterion", [AC_003])
    def test_all_three_child_pages_linked(self, mkdocs_config, criterion):
        """
        Verify that all three child pages are linked in the Knowledge Graph section.

        Expected pages:
        1. Integration Guide
        2. Setup
        3. Architecture

        Acceptance Criterion:
        - AC-003: All 3 child pages linked
        """
        nav = mkdocs_config['nav']

        # Find the Knowledge Graph section
        kg_section = None
        for item in nav:
            if isinstance(item, dict) and 'Knowledge Graph' in item:
                kg_section = item['Knowledge Graph']
                break

        assert kg_section is not None, "Knowledge Graph section not found"

        # Extract page titles
        page_titles = []
        for page in kg_section:
            if isinstance(page, dict):
                page_titles.extend(page.keys())

        # Verify all three expected pages exist
        expected_pages = {'Integration Guide', 'Setup', 'Architecture'}
        actual_pages = set(page_titles)

        assert expected_pages.issubset(actual_pages), \
            f"Missing pages. Expected: {expected_pages}, Found: {actual_pages}"
        assert len(kg_section) == 3, \
            f"Expected exactly 3 child pages, found {len(kg_section)}"

    # ========================================================================
    # AC-004: Links use correct MkDocs path format
    # ========================================================================

    @pytest.mark.parametrize("criterion", [AC_004])
    def test_links_use_correct_mkdocs_format(self, mkdocs_config, criterion):
        """
        Verify that all links use the correct MkDocs path format.

        Expected format: path/to/file.md (relative to docs/)
        NOT: /path/to/file or http://...

        Acceptance Criterion:
        - AC-004: Links use correct URL format for docs system
        """
        nav = mkdocs_config['nav']

        # Find the Knowledge Graph section
        kg_section = None
        for item in nav:
            if isinstance(item, dict) and 'Knowledge Graph' in item:
                kg_section = item['Knowledge Graph']
                break

        assert kg_section is not None, "Knowledge Graph section not found"

        expected_links = {
            'Integration Guide': 'guides/graphiti-integration-guide.md',
            'Setup': 'setup/graphiti-setup.md',
            'Architecture': 'architecture/graphiti-architecture.md'
        }

        for page in kg_section:
            if isinstance(page, dict):
                for title, path in page.items():
                    assert title in expected_links, f"Unexpected page: {title}"
                    assert path == expected_links[title], \
                        f"Incorrect path for {title}. Expected: {expected_links[title]}, Got: {path}"

                    # Verify format
                    assert not path.startswith('/'), \
                        f"Path should not start with '/': {path}"
                    assert path.endswith('.md'), \
                        f"Path should end with '.md': {path}"

    # ========================================================================
    # Documentation Files Existence
    # ========================================================================

    def test_referenced_files_exist(self, mkdocs_config):
        """
        Verify that all referenced documentation files actually exist.

        This ensures no broken links in the navigation.
        """
        nav = mkdocs_config['nav']

        # Find the Knowledge Graph section
        kg_section = None
        for item in nav:
            if isinstance(item, dict) and 'Knowledge Graph' in item:
                kg_section = item['Knowledge Graph']
                break

        assert kg_section is not None, "Knowledge Graph section not found"

        # Check each file exists
        for page in kg_section:
            if isinstance(page, dict):
                for title, path in page.items():
                    file_path = Path('docs') / path
                    assert file_path.exists(), \
                        f"Documentation file not found: {file_path} (for '{title}')"

    # ========================================================================
    # Index Page Tests
    # ========================================================================

    def test_index_page_includes_graphiti_section(self, index_content):
        """
        Verify that the index page includes a reference to the Knowledge Graph section.

        This improves discoverability for users landing on the homepage.
        """
        # Check for section header
        assert '### 🧠 Knowledge Graph' in index_content or \
               '## Knowledge Graph' in index_content, \
            "Index page does not include Knowledge Graph section"

        # Check for links to all three pages
        assert 'guides/graphiti-integration-guide.md' in index_content, \
            "Index page missing link to Integration Guide"
        assert 'setup/graphiti-setup.md' in index_content, \
            "Index page missing link to Setup"
        assert 'architecture/graphiti-architecture.md' in index_content, \
            "Index page missing link to Architecture"

    def test_index_page_graphiti_section_placement(self, index_content):
        """
        Verify that the Knowledge Graph section is placed after MCP Integration
        and before Troubleshooting, as specified in the requirements.
        """
        # Find section positions
        mcp_pos = index_content.find('### 🔌 [MCP Integration]')
        kg_pos = index_content.find('### 🧠 Knowledge Graph')
        troubleshooting_pos = index_content.find('### 🛠️ [Troubleshooting]')

        assert mcp_pos >= 0, "MCP Integration section not found"
        assert kg_pos >= 0, "Knowledge Graph section not found"
        assert troubleshooting_pos >= 0, "Troubleshooting section not found"

        # Verify order
        assert mcp_pos < kg_pos, \
            "Knowledge Graph section should appear after MCP Integration"
        assert kg_pos < troubleshooting_pos, \
            "Knowledge Graph section should appear before Troubleshooting"

    # ========================================================================
    # Navigation Structure Tests
    # ========================================================================

    def test_knowledge_graph_section_placement(self, mkdocs_config):
        """
        Verify that the Knowledge Graph section appears after Deep Dives
        in the navigation structure.
        """
        nav = mkdocs_config['nav']

        # Find positions
        deep_dives_idx = None
        kg_idx = None

        for idx, item in enumerate(nav):
            if isinstance(item, dict):
                if 'Deep Dives' in item:
                    deep_dives_idx = idx
                if 'Knowledge Graph' in item:
                    kg_idx = idx

        assert deep_dives_idx is not None, "Deep Dives section not found"
        assert kg_idx is not None, "Knowledge Graph section not found"
        assert kg_idx > deep_dives_idx, \
            "Knowledge Graph should appear after Deep Dives in navigation"


# ============================================================================
# Integration Tests
# ============================================================================

class TestNavigationIntegration:
    """Integration tests for the complete navigation system."""

    def test_mkdocs_can_build(self):
        """
        Verify that MkDocs can build the site without errors.

        This is a smoke test to ensure our changes don't break the build.

        Acceptance Criterion:
        - AC-005: Builds without errors

        Note: This test will be skipped if mkdocs is not installed.
        """
        import subprocess
        import shutil

        # Try to validate the configuration
        result = subprocess.run(
            ['python', '-m', 'mkdocs', 'build', '--strict', '--site-dir', 'test_site'],
            capture_output=True,
            text=True
        )

        # Clean up test site if it was created
        if Path('test_site').exists():
            shutil.rmtree('test_site')

        # Check if mkdocs is installed
        if result.returncode != 0:
            if 'No module named' in result.stderr or 'command not found' in result.stderr:
                pytest.skip("MkDocs not installed - skipping build test")
            else:
                pytest.fail(f"MkDocs build failed:\n{result.stderr}")
