"""
Tests for template extends mechanism in guardkit init.

Tests the inheritance chain resolution, manifest merging, base-first
overlay installation, and --base-only flag.

Coverage Target: >=85%
Test Count: 15+ tests
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.cli.init import (
    _load_manifest,
    _merge_manifests,
    _resolve_extends_chain,
    apply_template,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def templates_dir(tmp_path):
    """Create a temporary templates directory with base and extension templates."""
    base_dir = tmp_path / "templates" / "base-template"
    ext_dir = tmp_path / "templates" / "ext-template"
    base_dir.mkdir(parents=True)
    ext_dir.mkdir(parents=True)

    # Base template manifest
    base_manifest = {
        "schema_version": "1.0.0",
        "name": "base-template",
        "display_name": "Base Template",
        "version": "1.0.0",
        "language": "Python",
        "frameworks": [{"name": "pytest", "purpose": "testing"}],
        "tags": ["python", "base"],
        "placeholders": {
            "ProjectName": {"name": "{{ProjectName}}", "required": True},
        },
    }
    (base_dir / "manifest.json").write_text(json.dumps(base_manifest, indent=2))

    # Base template agents
    base_agents = base_dir / "agents"
    base_agents.mkdir()
    (base_agents / "base-specialist.md").write_text("# Base Specialist\nBase agent content.")

    # Base template rules
    base_rules = base_dir / ".claude" / "rules"
    base_rules.mkdir(parents=True)
    (base_rules / "code-style.md").write_text("# Code Style\nBase code style.")
    patterns_dir = base_rules / "patterns"
    patterns_dir.mkdir()
    (patterns_dir / "factory.md").write_text("# Factory Pattern\nBase factory pattern.")

    # Base template CLAUDE.md
    base_claude = base_dir / ".claude"
    (base_claude / "CLAUDE.md").write_text("# Base Template\nBase documentation.")

    # Extension template manifest
    ext_manifest = {
        "schema_version": "1.0.0",
        "name": "ext-template",
        "display_name": "Extension Template",
        "extends": "base-template",
        "version": "2.0.0",
        "language": "Python",
        "frameworks": [
            {"name": "pytest", "purpose": "testing"},
            {"name": "pydantic", "purpose": "data"},
        ],
        "tags": ["python", "extension"],
        "placeholders": {
            "ProjectName": {"name": "{{ProjectName}}", "required": True},
            "DomainName": {"name": "{{DomainName}}", "required": True},
        },
        "requires": ["template:base-template"],
    }
    (ext_dir / "manifest.json").write_text(json.dumps(ext_manifest, indent=2))

    # Extension agents (one new, one override)
    ext_agents = ext_dir / "agents"
    ext_agents.mkdir()
    (ext_agents / "base-specialist.md").write_text("# Base Specialist\nOverridden by extension.")
    (ext_agents / "ext-specialist.md").write_text("# Extension Specialist\nNew agent.")

    # Extension rules (override code-style, add new rule)
    ext_rules = ext_dir / ".claude" / "rules"
    ext_rules.mkdir(parents=True)
    (ext_rules / "code-style.md").write_text("# Code Style\nExtension code style.")
    (ext_rules / "weighted-eval.md").write_text("# Weighted Evaluation\nNew rule.")

    # Extension CLAUDE.md (overrides base)
    ext_claude = ext_dir / ".claude"
    (ext_claude / "CLAUDE.md").write_text("# Extension Template\nExtension documentation.")

    return tmp_path / "templates"


@pytest.fixture
def mock_resolve(templates_dir):
    """Patch _resolve_template_source_dir to use temporary templates."""
    def resolver(name):
        candidate = templates_dir / name
        return candidate if candidate.is_dir() else None

    with patch("guardkit.cli.init._resolve_template_source_dir", side_effect=resolver):
        yield resolver


# ============================================================================
# 1. _load_manifest Tests
# ============================================================================


class TestLoadManifest:
    """Test manifest loading from template directories."""

    def test_loads_valid_manifest(self, templates_dir):
        manifest = _load_manifest(templates_dir / "base-template")
        assert manifest is not None
        assert manifest["name"] == "base-template"

    def test_returns_none_for_missing_manifest(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert _load_manifest(empty_dir) is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "manifest.json").write_text("not valid json {{{")
        assert _load_manifest(bad_dir) is None


# ============================================================================
# 2. _resolve_extends_chain Tests
# ============================================================================


class TestResolveExtendsChain:
    """Test template inheritance chain resolution."""

    def test_no_extends_returns_single(self, mock_resolve):
        chain = _resolve_extends_chain("base-template")
        assert chain == ["base-template"]

    def test_single_extends(self, mock_resolve):
        chain = _resolve_extends_chain("ext-template")
        assert chain == ["base-template", "ext-template"]

    def test_unknown_template(self, mock_resolve):
        chain = _resolve_extends_chain("nonexistent")
        assert chain == ["nonexistent"]

    def test_circular_reference_protection(self, templates_dir, mock_resolve):
        """Ensure circular extends chains don't infinite loop."""
        # Make base-template extend ext-template (circular)
        base_manifest = json.loads(
            (templates_dir / "base-template" / "manifest.json").read_text()
        )
        base_manifest["extends"] = "ext-template"
        (templates_dir / "base-template" / "manifest.json").write_text(
            json.dumps(base_manifest)
        )

        chain = _resolve_extends_chain("ext-template")
        # Should terminate without infinite loop
        assert "ext-template" in chain
        assert "base-template" in chain

    def test_multi_level_chain(self, templates_dir, mock_resolve):
        """Test 3-level inheritance: grandbase → base → ext."""
        grandbase = templates_dir / "grandbase-template"
        grandbase.mkdir()
        (grandbase / "manifest.json").write_text(json.dumps({
            "name": "grandbase-template",
            "version": "0.1.0",
        }))

        # Make base extend grandbase
        base_manifest = json.loads(
            (templates_dir / "base-template" / "manifest.json").read_text()
        )
        base_manifest["extends"] = "grandbase-template"
        (templates_dir / "base-template" / "manifest.json").write_text(
            json.dumps(base_manifest)
        )

        chain = _resolve_extends_chain("ext-template")
        assert chain == ["grandbase-template", "base-template", "ext-template"]


# ============================================================================
# 3. _merge_manifests Tests
# ============================================================================


class TestMergeManifests:
    """Test manifest merging logic."""

    def test_scalar_override(self):
        base = {"name": "base", "version": "1.0.0"}
        ext = {"name": "ext", "version": "2.0.0"}
        merged = _merge_manifests(base, ext)
        assert merged["name"] == "ext"
        assert merged["version"] == "2.0.0"

    def test_dict_shallow_merge(self):
        base = {"placeholders": {"A": {"required": True}, "B": {"required": False}}}
        ext = {"placeholders": {"B": {"required": True}, "C": {"required": True}}}
        merged = _merge_manifests(base, ext)
        assert "A" in merged["placeholders"]
        assert merged["placeholders"]["B"]["required"] is True  # ext wins
        assert "C" in merged["placeholders"]

    def test_list_concatenation_with_dedup(self):
        base = {"tags": ["python", "base"]}
        ext = {"tags": ["python", "extension"]}
        merged = _merge_manifests(base, ext)
        assert merged["tags"] == ["python", "base", "extension"]

    def test_list_with_dict_items_dedup(self):
        base = {"frameworks": [{"name": "pytest", "purpose": "testing"}]}
        ext = {"frameworks": [
            {"name": "pytest", "purpose": "testing"},
            {"name": "pydantic", "purpose": "data"},
        ]}
        merged = _merge_manifests(base, ext)
        assert len(merged["frameworks"]) == 2
        names = [f["name"] for f in merged["frameworks"]]
        assert "pytest" in names
        assert "pydantic" in names

    def test_extension_adds_new_keys(self):
        base = {"name": "base"}
        ext = {"name": "ext", "new_field": "value"}
        merged = _merge_manifests(base, ext)
        assert merged["new_field"] == "value"

    def test_base_only_keys_preserved(self):
        base = {"name": "base", "base_only": True}
        ext = {"name": "ext"}
        merged = _merge_manifests(base, ext)
        assert merged["base_only"] is True


# ============================================================================
# 4. apply_template with extends Tests
# ============================================================================


class TestApplyTemplateExtends:
    """Test full apply_template with inheritance."""

    def test_extension_installs_base_then_overlay(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        result = apply_template("ext-template", target)
        assert result is True

        # Extension CLAUDE.md should override base
        claude_content = (target / ".claude" / "CLAUDE.md").read_text()
        assert "Extension documentation" in claude_content

        # Base-only rule preserved
        assert (target / ".claude" / "rules" / "patterns" / "factory.md").exists()

        # Extension-only rule added
        assert (target / ".claude" / "rules" / "weighted-eval.md").exists()

        # Extension agent overrides base agent
        specialist = (target / ".claude" / "agents" / "base-specialist.md").read_text()
        assert "Overridden by extension" in specialist

        # Extension-only agent added
        assert (target / ".claude" / "agents" / "ext-specialist.md").exists()

    def test_merged_manifest_written(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        apply_template("ext-template", target)

        manifest_path = target / ".claude" / "manifest.json"
        assert manifest_path.exists()

        merged = json.loads(manifest_path.read_text())
        # Extension name wins
        assert merged["name"] == "ext-template"
        # Extension version wins
        assert merged["version"] == "2.0.0"
        # Tags merged with dedup
        assert "base" in merged["tags"]
        assert "extension" in merged["tags"]
        # Placeholders merged
        assert "ProjectName" in merged["placeholders"]
        assert "DomainName" in merged["placeholders"]

    def test_base_only_flag(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        result = apply_template("ext-template", target, base_only=True)
        assert result is True

        # Should have base CLAUDE.md, not extension
        claude_content = (target / ".claude" / "CLAUDE.md").read_text()
        assert "Base documentation" in claude_content

        # Should NOT have extension-only files
        assert not (target / ".claude" / "rules" / "weighted-eval.md").exists()
        assert not (target / ".claude" / "agents" / "ext-specialist.md").exists()

        # Should have base agent content
        specialist = (target / ".claude" / "agents" / "base-specialist.md").read_text()
        assert "Base agent content" in specialist

    def test_base_template_still_works_independently(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        result = apply_template("base-template", target)
        assert result is True

        # Base content present
        assert (target / ".claude" / "CLAUDE.md").exists()
        assert (target / ".claude" / "agents" / "base-specialist.md").exists()
        assert (target / ".claude" / "rules" / "code-style.md").exists()

        # No extension content
        assert not (target / ".claude" / "agents" / "ext-specialist.md").exists()
        assert not (target / ".claude" / "rules" / "weighted-eval.md").exists()

    def test_nonexistent_template_returns_true(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        result = apply_template("nonexistent", target)
        assert result is True  # Creates scaffold only

    def test_missing_base_in_chain_returns_false(self, templates_dir, tmp_path):
        """If extends references a base that doesn't exist, return False."""
        # Create a template that extends a non-existent base
        broken_dir = templates_dir / "broken-template"
        broken_dir.mkdir()
        (broken_dir / "manifest.json").write_text(json.dumps({
            "name": "broken-template",
            "extends": "nonexistent-base",
        }))

        def resolver(name):
            candidate = templates_dir / name
            return candidate if candidate.is_dir() else None

        with patch("guardkit.cli.init._resolve_template_source_dir", side_effect=resolver):
            target = tmp_path / "project"
            target.mkdir()
            result = apply_template("broken-template", target)
            assert result is False

    def test_directory_structure_created(self, tmp_path, mock_resolve):
        target = tmp_path / "project"
        target.mkdir()

        apply_template("ext-template", target)

        # Verify standard directories created
        assert (target / ".claude").is_dir()
        assert (target / ".claude" / "agents").is_dir()
        assert (target / "tasks" / "backlog").is_dir()
        assert (target / ".guardkit").is_dir()


# ============================================================================
# 5. Real Template Integration Tests
# ============================================================================


class TestRealTemplateExtends:
    """Integration tests using actual templates in installer/core/templates/."""

    @pytest.fixture
    def real_templates_available(self):
        """Skip if real templates are not available."""
        templates_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "installer" / "core" / "templates"
        )
        base = templates_dir / "langchain-deepagents"
        ext = templates_dir / "langchain-deepagents-weighted-evaluation"
        if not base.is_dir() or not ext.is_dir():
            pytest.skip("Real templates not available")
        return templates_dir

    def test_weighted_evaluation_manifest_has_extends(self, real_templates_available):
        manifest_path = (
            real_templates_available
            / "langchain-deepagents-weighted-evaluation"
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text())
        assert manifest.get("extends") == "langchain-deepagents"

    def test_resolve_chain_for_real_templates(self, real_templates_available):
        chain = _resolve_extends_chain("langchain-deepagents-weighted-evaluation")
        assert chain == [
            "langchain-deepagents",
            "langchain-deepagents-weighted-evaluation",
        ]

    def test_base_template_has_no_extends(self, real_templates_available):
        chain = _resolve_extends_chain("langchain-deepagents")
        assert chain == ["langchain-deepagents"]

    def test_apply_weighted_evaluation_end_to_end(
        self, tmp_path, real_templates_available
    ):
        """Full end-to-end test: init with weighted-evaluation template."""
        target = tmp_path / "test-project"
        target.mkdir()

        result = apply_template(
            "langchain-deepagents-weighted-evaluation", target
        )
        assert result is True

        # Extension CLAUDE.md should be present (overrides base)
        claude_path = target / ".claude" / "CLAUDE.md"
        assert claude_path.exists()
        content = claude_path.read_text()
        assert "Weighted Evaluation" in content

        # Merged manifest should exist
        manifest_path = target / ".claude" / "manifest.json"
        assert manifest_path.exists()
        merged = json.loads(manifest_path.read_text())
        assert merged["extends"] == "langchain-deepagents"

        # Base agents should be present
        agents_dir = target / ".claude" / "agents"
        assert agents_dir.is_dir()
