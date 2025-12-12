"""
Tests for RulesStructureGenerator.

TASK-CRS-002: Test suite for modular .claude/rules/ structure generation.
"""

import pytest
from pathlib import Path
from datetime import datetime

from installer.core.lib.template_generator.rules_structure_generator import (
    RulesStructureGenerator,
    RuleFile
)
from installer.core.lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    ConfidenceScore,
    ConfidenceLevel,
    LayerInfo,
    ExampleFile
)


class MockAgent:
    """Mock agent for testing."""
    def __init__(self, name, capabilities=None):
        self.name = name
        self.purpose = f"Agent for {name}"
        self.capabilities = capabilities or []


@pytest.fixture
def sample_analysis():
    """Create sample CodebaseAnalysis for testing."""
    return CodebaseAnalysis(
        codebase_path="/test/project",
        technology=TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI", "SQLAlchemy"],
            testing_frameworks=["pytest"],
            build_tools=["pip"],
            databases=["PostgreSQL"],
            infrastructure=["Docker"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0,
                reasoning="Clear technology stack"
            )
        ),
        architecture=ArchitectureInfo(
            patterns=["Repository Pattern", "Service Layer"],
            architectural_style="Clean Architecture",
            layers=[
                LayerInfo(
                    name="Domain",
                    description="Core business logic",
                    typical_files=["entities", "value_objects"],
                    dependencies=[]
                )
            ],
            key_abstractions=["User", "Product"],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
                reasoning="Well-structured architecture"
            )
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=88.0,
            dry_compliance=82.0,
            yagni_compliance=90.0,
            test_coverage=78.0,
            code_smells=["Some duplicate code"],
            strengths=["Good separation of concerns"],
            improvements=["Increase test coverage"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=85.0,
                reasoning="Good quality metrics"
            )
        ),
        example_files=[
            ExampleFile(
                path="src/domain/user.py",
                purpose="User entity",
                layer="Domain",
                patterns_used=["Repository Pattern"],
                key_concepts=["Entity", "Aggregate"]
            )
        ]
    )


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        MockAgent("repository-specialist", ["repositories", "data-access"]),
        MockAgent("api-specialist", ["endpoints", "routing"]),
        MockAgent("testing-specialist", ["unit-tests", "integration-tests"])
    ]


class TestRuleFile:
    """Test RuleFile dataclass."""

    def test_rule_file_creation(self):
        """Test RuleFile can be created."""
        rule = RuleFile(
            path="rules/code-style.md",
            content="# Code Style",
            paths_filter="**/*.py"
        )
        assert rule.path == "rules/code-style.md"
        assert rule.content == "# Code Style"
        assert rule.paths_filter == "**/*.py"

    def test_rule_file_optional_paths(self):
        """Test RuleFile with no paths filter."""
        rule = RuleFile(
            path="rules/general.md",
            content="# General"
        )
        assert rule.paths_filter is None


class TestRulesStructureGenerator:
    """Test RulesStructureGenerator class."""

    def test_init(self, sample_analysis, sample_agents):
        """Test generator initialization."""
        output_path = Path("/test/output")
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=output_path
        )
        assert generator.analysis == sample_analysis
        assert generator.agents == sample_agents
        assert generator.output_path == output_path

    def test_generate_returns_dict(self, sample_analysis, sample_agents):
        """Test generate() returns a dictionary."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        assert isinstance(rules, dict)
        assert len(rules) > 0

    def test_generate_includes_core_claudemd(self, sample_analysis, sample_agents):
        """Test generate() includes CLAUDE.md."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        assert "CLAUDE.md" in rules
        assert len(rules["CLAUDE.md"]) > 0
        # Should be minimal (target ~5KB)
        assert len(rules["CLAUDE.md"]) < 6000

    def test_generate_includes_code_style_rules(self, sample_analysis, sample_agents):
        """Test generate() includes code-style.md."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        assert "rules/code-style.md" in rules
        content = rules["rules/code-style.md"]
        assert "paths:" in content  # Should have frontmatter
        assert "**/*.py" in content  # Python extension

    def test_generate_includes_testing_rules(self, sample_analysis, sample_agents):
        """Test generate() includes testing.md."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        assert "rules/testing.md" in rules
        content = rules["rules/testing.md"]
        assert "paths:" in content
        assert "test" in content.lower()

    def test_generate_includes_pattern_rules(self, sample_analysis, sample_agents):
        """Test generate() includes pattern-specific rules."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        # Should have rules for each pattern
        assert "rules/patterns/repository-pattern.md" in rules
        assert "rules/patterns/service-layer.md" in rules

    def test_generate_includes_agent_rules(self, sample_analysis, sample_agents):
        """Test generate() includes agent-specific rules."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        rules = generator.generate()
        # Should have rules for each agent
        assert "rules/guidance/repository-specialist.md" in rules
        assert "rules/guidance/api-specialist.md" in rules
        assert "rules/guidance/testing-specialist.md" in rules


class TestCoreCLAUDEGeneration:
    """Test core CLAUDE.md generation."""

    def test_core_claudemd_includes_project_name(self, sample_analysis, sample_agents):
        """Test CLAUDE.md includes project name."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_core_claudemd()
        assert "project" in content.lower()

    def test_core_claudemd_includes_language(self, sample_analysis, sample_agents):
        """Test CLAUDE.md includes primary language."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_core_claudemd()
        assert "Python" in content

    def test_core_claudemd_includes_frameworks(self, sample_analysis, sample_agents):
        """Test CLAUDE.md includes frameworks."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_core_claudemd()
        assert "FastAPI" in content

    def test_core_claudemd_includes_architecture(self, sample_analysis, sample_agents):
        """Test CLAUDE.md includes architecture style."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_core_claudemd()
        assert "Clean Architecture" in content

    def test_core_claudemd_includes_quick_start(self, sample_analysis, sample_agents):
        """Test CLAUDE.md includes quick start commands."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_core_claudemd()
        assert "Quick Start" in content
        assert "pip install" in content or "# Install" in content


class TestCodeStyleRulesGeneration:
    """Test code style rules generation."""

    def test_code_style_has_frontmatter(self, sample_analysis, sample_agents):
        """Test code style rules include paths frontmatter."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_code_style_rules()
        assert "---" in content
        assert "paths:" in content

    def test_code_style_has_correct_paths(self, sample_analysis, sample_agents):
        """Test code style rules have correct path patterns."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_code_style_rules()
        assert "**/*.py" in content  # Python files

    def test_code_style_includes_naming_conventions(self, sample_analysis, sample_agents):
        """Test code style rules include naming conventions."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_code_style_rules()
        assert "Naming" in content or "naming" in content


class TestTestingRulesGeneration:
    """Test testing rules generation."""

    def test_testing_rules_have_frontmatter(self, sample_analysis, sample_agents):
        """Test testing rules include paths frontmatter."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_testing_rules()
        assert "---" in content
        assert "paths:" in content

    def test_testing_rules_have_test_paths(self, sample_analysis, sample_agents):
        """Test testing rules target test files."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_testing_rules()
        assert "test" in content.lower()

    def test_testing_rules_include_coverage(self, sample_analysis, sample_agents):
        """Test testing rules mention coverage requirements."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_testing_rules()
        assert "coverage" in content.lower()


class TestPatternRulesGeneration:
    """Test pattern-specific rules generation."""

    def test_pattern_rules_include_pattern_name(self, sample_analysis, sample_agents):
        """Test pattern rules include pattern name."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_pattern_rules("Repository Pattern")
        assert "Repository" in content

    def test_pattern_rules_include_description(self, sample_analysis, sample_agents):
        """Test pattern rules include description."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        content = generator._generate_pattern_rules("Repository Pattern")
        assert "Overview" in content or "description" in content.lower()


class TestAgentRulesGeneration:
    """Test agent-specific rules generation."""

    def test_agent_rules_include_agent_name(self, sample_analysis, sample_agents):
        """Test agent rules include agent name."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        agent = sample_agents[0]
        content = generator._generate_guidance_rules(agent)
        assert agent.name in content

    def test_agent_rules_with_path_inference(self, sample_analysis, sample_agents):
        """Test agent rules include inferred paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        # Repository specialist should have repository paths
        agent = MockAgent("repository-specialist")
        content = generator._generate_guidance_rules(agent)
        if "---" in content:  # Has frontmatter
            assert "paths:" in content

    def test_agent_rules_without_path_inference(self, sample_analysis, sample_agents):
        """Test agent rules without path inference (always load)."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        # Generic agent should not have paths frontmatter
        agent = MockAgent("general-agent")
        content = generator._generate_guidance_rules(agent)
        # Should not start with frontmatter
        assert not content.startswith("---\npaths:")


class TestPathInference:
    """Test agent path pattern inference."""

    def test_infer_repository_paths(self, sample_analysis, sample_agents):
        """Test repository agent gets repository paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        paths = generator._infer_agent_paths("repository-specialist")
        assert "repository" in paths.lower() or "repositories" in paths.lower()

    def test_infer_api_paths(self, sample_analysis, sample_agents):
        """Test API agent gets API paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        paths = generator._infer_agent_paths("api-specialist")
        assert "api" in paths.lower() or "Controllers" in paths

    def test_infer_testing_paths(self, sample_analysis, sample_agents):
        """Test testing agent gets test paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        paths = generator._infer_agent_paths("testing-specialist")
        assert "test" in paths.lower()

    def test_infer_database_paths(self, sample_analysis, sample_agents):
        """Test database agent gets database paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        paths = generator._infer_agent_paths("database-specialist")
        assert "models" in paths or "db" in paths

    def test_infer_unknown_agent_returns_empty(self, sample_analysis, sample_agents):
        """Test unknown agent returns empty string (always load)."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        paths = generator._infer_agent_paths("unknown-agent")
        assert paths == ""


class TestFrontmatterGeneration:
    """Test YAML frontmatter generation."""

    def test_frontmatter_with_paths(self, sample_analysis, sample_agents):
        """Test frontmatter generation with paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        frontmatter = generator._generate_frontmatter("**/*.py")
        assert "---" in frontmatter
        assert "paths: **/*.py" in frontmatter

    def test_frontmatter_without_paths(self, sample_analysis, sample_agents):
        """Test frontmatter generation without paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        frontmatter = generator._generate_frontmatter(None)
        assert frontmatter == ""

    def test_frontmatter_with_empty_paths(self, sample_analysis, sample_agents):
        """Test frontmatter generation with empty paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        frontmatter = generator._generate_frontmatter("")
        assert frontmatter == ""


class TestSlugify:
    """Test name slugification."""

    def test_slugify_simple_name(self, sample_analysis, sample_agents):
        """Test slugify with simple name."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        assert generator._slugify("Repository") == "repository"

    def test_slugify_with_spaces(self, sample_analysis, sample_agents):
        """Test slugify with spaces."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        assert generator._slugify("Repository Pattern") == "repository-pattern"

    def test_slugify_with_underscores(self, sample_analysis, sample_agents):
        """Test slugify with underscores."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        assert generator._slugify("API_Specialist") == "api-specialist"

    def test_slugify_mixed_case(self, sample_analysis, sample_agents):
        """Test slugify with mixed case."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        assert generator._slugify("ServiceLayer") == "servicelayer"


class TestHelperMethods:
    """Test helper methods."""

    def test_get_install_command_python(self, sample_analysis, sample_agents):
        """Test install command for Python."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        cmd = generator._get_install_command()
        assert "pip" in cmd

    def test_get_test_command_pytest(self, sample_analysis, sample_agents):
        """Test test command for pytest."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        cmd = generator._get_test_command()
        assert "pytest" in cmd

    def test_get_language_extensions_python(self, sample_analysis, sample_agents):
        """Test Python file extensions."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        extensions = generator._get_language_extensions("Python")
        assert ".py" in extensions

    def test_get_language_extensions_typescript(self, sample_analysis, sample_agents):
        """Test TypeScript file extensions."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=Path("/test/output")
        )
        extensions = generator._get_language_extensions("TypeScript")
        assert ".ts" in extensions
        assert ".tsx" in extensions


class TestEnhancedAgentContent:
    """Test enhanced agent content integration (TASK-RULES-ENHANCE)."""

    def test_uses_enhanced_content_when_available(self, sample_analysis, sample_agents, tmp_path):
        """Test that enhanced agent content is used when file exists."""
        # Create output directory with enhanced agent file
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        enhanced_content = """---
name: repository-specialist
description: Repository pattern specialist
---

# Repository Specialist

## Purpose

Enhanced purpose with boundaries and detailed guidance.

## Boundaries

### ALWAYS
- ✅ Use proper patterns for data access

### NEVER
- ❌ Never expose IQueryable outside repository
"""
        (agents_dir / "repository-specialist.md").write_text(enhanced_content)

        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        agent = MockAgent("repository-specialist")
        content = generator._generate_guidance_rules(agent)

        # Should use enhanced content
        assert "Enhanced purpose with boundaries" in content
        assert "## Boundaries" in content
        assert "### ALWAYS" in content
        assert "### NEVER" in content

    def test_adds_paths_to_enhanced_content_without_paths(self, sample_analysis, sample_agents, tmp_path):
        """Test that paths are added to enhanced content missing paths frontmatter."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        enhanced_content = """---
name: repository-specialist
---

# Repository Specialist

## Purpose

Enhanced content without paths.
"""
        (agents_dir / "repository-specialist.md").write_text(enhanced_content)

        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        agent = MockAgent("repository-specialist")
        content = generator._generate_guidance_rules(agent)

        # Should have paths added to frontmatter
        assert "paths:" in content
        assert "Enhanced content without paths" in content

    def test_preserves_existing_paths_in_enhanced_content(self, sample_analysis, sample_agents, tmp_path):
        """Test that existing paths in enhanced content are preserved."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        enhanced_content = """---
name: repository-specialist
paths: **/custom/path/**
---

# Repository Specialist

Content with custom paths.
"""
        (agents_dir / "repository-specialist.md").write_text(enhanced_content)

        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        agent = MockAgent("repository-specialist")
        content = generator._generate_guidance_rules(agent)

        # Should preserve existing paths
        assert "**/custom/path/**" in content
        assert "Content with custom paths" in content

    def test_falls_back_to_stub_when_no_enhanced_file(self, sample_analysis, sample_agents, tmp_path):
        """Test fallback to stub content when no enhanced file exists."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        agent = MockAgent("nonexistent-agent")
        content = generator._generate_guidance_rules(agent)

        # Should use stub content
        assert "nonexistent-agent" in content
        assert "## Purpose" in content
        assert "## Capabilities" in content

    def test_read_enhanced_agent_content_returns_none_for_missing_file(self, sample_analysis, sample_agents, tmp_path):
        """Test _read_enhanced_agent_content returns None when file doesn't exist."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        result = generator._read_enhanced_agent_content("nonexistent-agent")
        assert result is None

    def test_read_enhanced_agent_content_returns_content_for_existing_file(self, sample_analysis, sample_agents, tmp_path):
        """Test _read_enhanced_agent_content returns content when file exists."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "test-agent.md").write_text("# Test Agent\n\nContent here.")

        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        result = generator._read_enhanced_agent_content("test-agent")
        assert result == "# Test Agent\n\nContent here."

    def test_merge_paths_into_frontmatter_adds_paths_to_no_frontmatter(self, sample_analysis, sample_agents, tmp_path):
        """Test _merge_paths_into_frontmatter adds frontmatter to content without it."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        content = "# Agent\n\nNo frontmatter content."
        result = generator._merge_paths_into_frontmatter(content, "**/test/**")

        assert result.startswith("---\npaths: **/test/**")
        assert "# Agent" in result
        assert "No frontmatter content" in result

    def test_merge_paths_into_frontmatter_preserves_existing_paths(self, sample_analysis, sample_agents, tmp_path):
        """Test _merge_paths_into_frontmatter preserves existing paths."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        content = """---
name: test
paths: **/existing/**
---

# Agent
"""
        result = generator._merge_paths_into_frontmatter(content, "**/new/**")

        # Should keep existing paths, not add new
        assert "**/existing/**" in result
        # New paths should NOT be added when existing paths present
        assert content.count("paths:") == result.count("paths:")

    def test_merge_paths_returns_unchanged_when_no_paths_filter(self, sample_analysis, sample_agents, tmp_path):
        """Test _merge_paths_into_frontmatter returns unchanged content when no paths filter."""
        generator = RulesStructureGenerator(
            analysis=sample_analysis,
            agents=sample_agents,
            output_path=tmp_path
        )

        content = "# Agent\n\nOriginal content."
        result = generator._merge_paths_into_frontmatter(content, "")

        assert result == content
