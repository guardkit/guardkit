"""Test mkdocs.yml navigation structure and system context guide references."""

import yaml
from pathlib import Path


class MkDocsLoader(yaml.SafeLoader):
    """Custom YAML loader for mkdocs.yml that handles Python tags."""
    pass


# Register the Python name constructor to just return a string representation
def python_name_constructor(loader, node):
    """Constructor for Python name tags."""
    return f"!!python/name:{node.value}"


MkDocsLoader.add_constructor(
    'tag:yaml.org,2002:python/name:pymdownx.superfences.fence_code_format',
    python_name_constructor
)


def load_mkdocs_config():
    """Load mkdocs.yml with custom loader."""
    mkdocs_path = Path("mkdocs.yml")
    with open(mkdocs_path) as f:
        return yaml.load(f, Loader=MkDocsLoader)


def test_mkdocs_yaml_valid():
    """Test that mkdocs.yml is valid YAML."""
    mkdocs_path = Path("mkdocs.yml")
    assert mkdocs_path.exists(), "mkdocs.yml not found"

    config = load_mkdocs_config()

    assert config is not None, "mkdocs.yml is empty or invalid YAML"
    assert "nav" in config, "mkdocs.yml missing 'nav' key"


def test_system_context_guides_in_navigation():
    """Test that system context guides are included in mkdocs navigation."""
    config = load_mkdocs_config()

    # Find the Guides section
    guides_section = None
    for item in config["nav"]:
        if isinstance(item, dict) and "Guides" in item:
            guides_section = item["Guides"]
            break

    assert guides_section is not None, "Guides section not found in navigation"

    # Check for system context guides
    guide_entries = {}
    for entry in guides_section:
        if isinstance(entry, dict):
            guide_entries.update(entry)

    assert "System Overview" in guide_entries, "System Overview guide missing from navigation"
    assert "Impact Analysis" in guide_entries, "Impact Analysis guide missing from navigation"
    assert "Context Switch" in guide_entries, "Context Switch guide missing from navigation"

    # Verify the paths
    assert guide_entries["System Overview"] == "guides/system-overview-guide.md"
    assert guide_entries["Impact Analysis"] == "guides/impact-analysis-guide.md"
    assert guide_entries["Context Switch"] == "guides/context-switch-guide.md"


def test_system_context_guide_files_exist():
    """Test that the system context guide files actually exist."""
    guides = [
        "docs/guides/system-overview-guide.md",
        "docs/guides/impact-analysis-guide.md",
        "docs/guides/context-switch-guide.md",
    ]

    for guide in guides:
        guide_path = Path(guide)
        assert guide_path.exists(), f"Guide file {guide} does not exist"


def test_mkdocs_navigation_structure():
    """Test that mkdocs navigation doesn't exceed max depth of 3."""
    config = load_mkdocs_config()

    def check_depth(items, current_depth=1, max_depth=3):
        """Recursively check navigation depth."""
        if current_depth > max_depth:
            return False

        for item in items:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, list):
                        if not check_depth(value, current_depth + 1, max_depth):
                            return False
        return True

    assert check_depth(config["nav"]), "Navigation depth exceeds maximum of 3 levels"
