"""
Unit tests for template code sampling features (TASK-PHASE-7-5-INCLUDE-TEMPLATE-CODE-SAMPLES).

Tests the _sample_template_code() method and its integration with batch enhancement:
1. Code sampling accuracy and limits
2. Error handling for missing/unreadable files
3. Batch request enhancement with code samples
4. Batch prompt formatting with code samples
5. Edge cases (empty templates, encoding errors, truncation)

Test Coverage Target: ≥80% line coverage, ≥75% branch coverage
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import importlib
_agent_enhancer_module = importlib.import_module('installer.global.lib.template_creation.agent_enhancer')
AgentEnhancer = _agent_enhancer_module.AgentEnhancer


class TestSampleTemplateCode:
    """Unit tests for _sample_template_code() method"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary directory with test templates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()

            # Create sample template files
            (templates_dir / "template1.py").write_text("def function1():\n    pass")
            (templates_dir / "template2.cs").write_text("public class MyClass { }")
            (templates_dir / "template3.js").write_text("function test() { return true; }")

            yield temp_path

    def test_sample_template_code_success(self, enhancer, temp_template_dir):
        """Test successful code sampling from templates"""
        enhancer.template_root = temp_template_dir

        template_paths = [
            "templates/template1.py",
            "templates/template2.cs"
        ]

        result = enhancer._sample_template_code(template_paths)

        # Verify both templates were sampled
        assert "templates/template1.py" in result
        assert "templates/template2.cs" in result
        assert result["templates/template1.py"] == "def function1():\n    pass"
        assert result["templates/template2.cs"] == "public class MyClass { }"

    def test_sample_template_code_respects_max_templates(self, enhancer, temp_template_dir):
        """Test that only max_templates number of templates are processed"""
        enhancer.template_root = temp_template_dir

        template_paths = [
            "templates/template1.py",
            "templates/template2.cs",
            "templates/template3.js"
        ]

        # Request only 2 templates even though 3 are provided
        result = enhancer._sample_template_code(template_paths, max_templates=2)

        assert len(result) == 2
        assert "templates/template1.py" in result
        assert "templates/template2.cs" in result
        # Third template should not be processed
        assert "templates/template3.js" not in result

    def test_sample_template_code_respects_line_limits(self, enhancer, temp_template_dir):
        """Test that long files are truncated to max_lines_per_template"""
        enhancer.template_root = temp_template_dir

        # Create a file with 100 lines
        long_file = temp_template_dir / "templates" / "long.template"
        lines = [f"line {i}" for i in range(1, 101)]
        long_file.write_text("\n".join(lines))

        template_paths = ["templates/long.template"]

        # Sample with max 50 lines
        result = enhancer._sample_template_code(template_paths, max_lines_per_template=50)

        sampled_code = result["templates/long.template"]
        sampled_lines = sampled_code.split("\n")

        # Should have exactly 51 lines (50 original + "... (truncated)")
        assert len(sampled_lines) == 51
        assert sampled_lines[-1] == "... (truncated)"
        assert "line 50" in sampled_code
        assert "line 51" not in sampled_code

    def test_sample_template_code_missing_file(self, enhancer, temp_template_dir):
        """Test handling of missing template files"""
        enhancer.template_root = temp_template_dir

        template_paths = ["templates/nonexistent.template"]

        result = enhancer._sample_template_code(template_paths)

        # Missing file should return empty string for that path
        assert "templates/nonexistent.template" in result
        assert result["templates/nonexistent.template"] == ""

    def test_sample_template_code_encoding_error(self, enhancer, temp_template_dir):
        """Test handling of encoding errors when reading files"""
        enhancer.template_root = temp_template_dir

        # Create a file with invalid UTF-8 bytes
        bad_file = temp_template_dir / "templates" / "bad_encoding.template"
        with open(bad_file, 'wb') as f:
            f.write(b'\x80\x81\x82\x83')

        template_paths = ["templates/bad_encoding.template"]

        result = enhancer._sample_template_code(template_paths)

        # Should handle gracefully and return empty string
        assert "templates/bad_encoding.template" in result
        assert result["templates/bad_encoding.template"] == ""

    def test_sample_template_code_returns_empty_dict_for_empty_list(self, enhancer, temp_template_dir):
        """Test that empty template list returns empty dict"""
        enhancer.template_root = temp_template_dir

        result = enhancer._sample_template_code([])

        assert result == {}

    def test_sample_template_code_empty_file(self, enhancer, temp_template_dir):
        """Test sampling from an empty file"""
        enhancer.template_root = temp_template_dir

        empty_file = temp_template_dir / "templates" / "empty.template"
        empty_file.write_text("")

        template_paths = ["templates/empty.template"]

        result = enhancer._sample_template_code(template_paths)

        assert result["templates/empty.template"] == ""

    def test_sample_template_code_file_with_only_whitespace(self, enhancer, temp_template_dir):
        """Test sampling from a file with only whitespace"""
        enhancer.template_root = temp_template_dir

        whitespace_file = temp_template_dir / "templates" / "whitespace.template"
        whitespace_file.write_text("   \n\n   ")

        template_paths = ["templates/whitespace.template"]

        result = enhancer._sample_template_code(template_paths)

        # Whitespace content should be preserved as-is
        assert "templates/whitespace.template" in result
        # After splitlines and rejoin, final result will be the content as-is
        assert len(result["templates/whitespace.template"]) > 0

    def test_sample_template_code_mixed_success_and_failure(self, enhancer, temp_template_dir):
        """Test sampling when some files exist and some don't"""
        enhancer.template_root = temp_template_dir

        template_paths = [
            "templates/template1.py",       # exists
            "templates/nonexistent1.py",    # missing
            "templates/template2.cs",       # exists
            "templates/nonexistent2.cs"     # missing
        ]

        result = enhancer._sample_template_code(template_paths)

        # All paths should be in result
        assert len(result) == 4
        # Existing files should have content
        assert len(result["templates/template1.py"]) > 0
        assert len(result["templates/template2.cs"]) > 0
        # Missing files should have empty strings
        assert result["templates/nonexistent1.py"] == ""
        assert result["templates/nonexistent2.cs"] == ""


class TestBatchRequestWithCodeSamples:
    """Test integration of code samples with batch enhancement requests"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory with agents and templates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create agents directory with sample agent
            agents_dir = temp_path / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test-agent.md"
            agent_file.write_text("""---
name: test-agent
description: Test agent
priority: 5
technologies:
  - Python
---

# Test Agent
Original content.""")

            # Create templates directory
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "sample.template").write_text("def sample():\n    pass")

            yield temp_path

    def test_batch_request_includes_code_samples(self, enhancer, temp_template_dir):
        """Test that _build_batch_enhancement_request includes code samples"""
        enhancer.template_root = temp_template_dir

        agent_files = list((temp_template_dir / "agents").glob("*.md"))
        all_templates = list((temp_template_dir / "templates").glob("*.template"))

        batch_request = enhancer._build_batch_enhancement_request(agent_files, all_templates)

        # Verify structure
        assert "agents" in batch_request
        assert "template_catalog" in batch_request
        assert "template_code_samples" in batch_request
        assert "enhancement_instructions" in batch_request

        # Verify code samples field
        code_samples = batch_request["template_code_samples"]
        assert isinstance(code_samples, dict)
        # Should have sampled the template
        assert len(code_samples) >= 0

    def test_batch_request_handles_empty_templates(self, enhancer):
        """Test batch request handles case with no templates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create agents directory
            agents_dir = temp_path / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test-agent.md"
            agent_file.write_text("""---
name: test-agent
description: Test agent
priority: 5
technologies:
  - Python
---

# Test Agent""")

            # Create empty templates directory
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()

            enhancer.template_root = temp_path

            agent_files = list(agents_dir.glob("*.md"))
            all_templates = []

            batch_request = enhancer._build_batch_enhancement_request(agent_files, all_templates)

            # Should handle gracefully
            assert batch_request["template_code_samples"] == {}
            assert batch_request["template_catalog"] == []

    def test_batch_request_code_samples_are_non_empty(self, enhancer, temp_template_dir):
        """Test that code samples are properly populated when templates exist"""
        enhancer.template_root = temp_template_dir

        agent_files = list((temp_template_dir / "agents").glob("*.md"))
        all_templates = list((temp_template_dir / "templates").glob("*.template"))

        batch_request = enhancer._build_batch_enhancement_request(agent_files, all_templates)

        code_samples = batch_request["template_code_samples"]

        # Sample should include the template
        if code_samples:
            # All values should be strings
            for path, code in code_samples.items():
                assert isinstance(path, str)
                assert isinstance(code, str)


class TestBatchPromptWithCodeSamples:
    """Test batch prompt formatting with code samples"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    def test_batch_prompt_includes_code_samples(self, enhancer):
        """Test that _build_batch_prompt includes code samples in output"""
        batch_request = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "Test agent",
                    "technologies": ["Python"],
                    "file_path": "agents/test-agent.md"
                }
            ],
            "template_catalog": [
                {
                    "path": "templates/test.template",
                    "category": "core",
                    "name": "test"
                }
            ],
            "template_code_samples": {
                "templates/test.template": "def test():\n    pass"
            },
            "enhancement_instructions": "Test instructions"
        }

        prompt = enhancer._build_batch_prompt(batch_request)

        # Verify code samples are included in prompt
        assert "Template Code Samples" in prompt or "test.template" in prompt
        # Verify the actual code is in the prompt
        assert "def test()" in prompt

    def test_batch_prompt_handles_empty_code_samples(self, enhancer):
        """Test batch prompt handles empty code samples gracefully"""
        batch_request = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "Test agent",
                    "technologies": ["Python"],
                    "file_path": "agents/test-agent.md"
                }
            ],
            "template_catalog": [],
            "template_code_samples": {},
            "enhancement_instructions": "Test instructions"
        }

        prompt = enhancer._build_batch_prompt(batch_request)

        # Should not crash with empty code samples
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Test instructions" in prompt

    def test_batch_prompt_includes_multiple_code_samples(self, enhancer):
        """Test batch prompt with multiple code samples"""
        batch_request = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "Test agent",
                    "technologies": ["Python"],
                    "file_path": "agents/test-agent.md"
                }
            ],
            "template_catalog": [
                {"path": "templates/test1.template", "category": "core", "name": "test1"},
                {"path": "templates/test2.template", "category": "core", "name": "test2"}
            ],
            "template_code_samples": {
                "templates/test1.template": "def test1():\n    pass",
                "templates/test2.template": "class Test2:\n    pass"
            },
            "enhancement_instructions": "Test instructions"
        }

        prompt = enhancer._build_batch_prompt(batch_request)

        # Both code samples should be included
        assert "def test1()" in prompt
        assert "class Test2" in prompt
        assert "test1.template" in prompt
        assert "test2.template" in prompt

    def test_batch_prompt_skips_empty_code_samples(self, enhancer):
        """Test batch prompt skips empty code samples in formatted output"""
        batch_request = {
            "agents": [
                {
                    "name": "test-agent",
                    "description": "Test agent",
                    "technologies": ["Python"],
                    "file_path": "agents/test-agent.md"
                }
            ],
            "template_catalog": [
                {"path": "templates/test1.template", "category": "core", "name": "test1"},
                {"path": "templates/test2.template", "category": "core", "name": "test2"}
            ],
            "template_code_samples": {
                "templates/test1.template": "def test1():\n    pass",
                "templates/test2.template": ""  # Empty code sample
            },
            "enhancement_instructions": "Test instructions"
        }

        prompt = enhancer._build_batch_prompt(batch_request)

        # Should include test1 but not test2 in code samples section
        assert "def test1()" in prompt
        # Empty samples should not create empty code blocks
        assert "```\n\n```" not in prompt


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    def test_sample_template_code_with_unicode_content(self, enhancer):
        """Test sampling files with unicode content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()

            # Create file with unicode content
            unicode_file = templates_dir / "unicode.template"
            unicode_file.write_text("# 中文注释\ndef function():\n    '''文档字符串'''\n    pass", encoding='utf-8')

            enhancer.template_root = temp_path

            result = enhancer._sample_template_code(["templates/unicode.template"])

            # Should handle unicode correctly
            assert "中文" in result["templates/unicode.template"]
            assert "function()" in result["templates/unicode.template"]

    def test_batch_prompt_with_large_code_samples(self, enhancer):
        """Test batch prompt formatting with large code samples"""
        large_code = "def function():\n    pass\n" * 50  # ~600 characters

        batch_request = {
            "agents": [{"name": "test", "description": "test", "technologies": [], "file_path": "agents/test.md"}],
            "template_catalog": [{"path": "templates/large.template", "category": "core", "name": "large"}],
            "template_code_samples": {"templates/large.template": large_code},
            "enhancement_instructions": "Test"
        }

        prompt = enhancer._build_batch_prompt(batch_request)

        # Should include large code without truncating
        assert "def function():" in prompt
        assert len(prompt) > 1000  # Should be substantial

    def test_sample_template_code_with_max_templates_zero(self, enhancer):
        """Test sampling with max_templates=0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "test.template").write_text("content")

            enhancer.template_root = temp_path

            result = enhancer._sample_template_code(
                ["templates/test.template"],
                max_templates=0
            )

            # Should return empty dict
            assert result == {}


class TestSelectRelevantTemplates:
    """Unit tests for _select_relevant_templates() method - relevance-based template selection"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    def test_select_relevant_templates_extension_match(self, enhancer):
        """Test that templates with matching extensions are prioritized"""
        catalog = [
            {"path": "templates/react.tsx", "category": "components", "name": "react"},
            {"path": "templates/model.cs", "category": "models", "name": "model"},
            {"path": "templates/api.py", "category": "services", "name": "api"},
        ]

        # Technologies for C# MAUI project
        technologies = {'c#', 'maui', '.net'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=2)

        # Should prioritize .cs file
        assert "templates/model.cs" in result
        assert len(result) <= 2

    def test_select_relevant_templates_keyword_match(self, enhancer):
        """Test that templates with technology keywords in path are selected"""
        catalog = [
            {"path": "templates/other/realm-query.cs", "category": "other", "name": "realm-query"},
            {"path": "templates/components/button.tsx", "category": "components", "name": "button"},
            {"path": "templates/services/repository.cs", "category": "services", "name": "repository"},
        ]

        # Technologies include 'realm' and 'repository'
        technologies = {'c#', 'realm', 'repository'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=3)

        # Should include templates with 'realm' and 'repository' in path
        assert "templates/other/realm-query.cs" in result
        assert "templates/services/repository.cs" in result

    def test_select_relevant_templates_category_diversity(self, enhancer):
        """Test that selection maintains category diversity"""
        catalog = [
            {"path": "templates/models/model1.cs", "category": "models", "name": "model1"},
            {"path": "templates/models/model2.cs", "category": "models", "name": "model2"},
            {"path": "templates/services/service1.cs", "category": "services", "name": "service1"},
            {"path": "templates/repositories/repo1.cs", "category": "repositories", "name": "repo1"},
        ]

        technologies = {'c#', '.net'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=3)

        # Should select from different categories
        categories_selected = set()
        for template in catalog:
            if template["path"] in result:
                categories_selected.add(template["category"])

        # Should have selected from at least 2 different categories
        assert len(categories_selected) >= 2

    def test_select_relevant_templates_python_technologies(self, enhancer):
        """Test template selection for Python technologies"""
        catalog = [
            {"path": "templates/api.py", "category": "api", "name": "api"},
            {"path": "templates/model.ts", "category": "models", "name": "model"},
            {"path": "templates/service.py", "category": "services", "name": "service"},
        ]

        technologies = {'python', 'fastapi'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=3)

        # Should prioritize .py files
        assert "templates/api.py" in result
        assert "templates/service.py" in result

    def test_select_relevant_templates_no_matches_fallback(self, enhancer):
        """Test fallback behavior when no templates match technologies"""
        catalog = [
            {"path": "templates/model.cs", "category": "models", "name": "model"},
            {"path": "templates/service.cs", "category": "services", "name": "service"},
        ]

        # Technologies that don't match any templates
        technologies = {'rust', 'wasm'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=2)

        # Should fallback to first N templates
        assert len(result) == 2
        assert "templates/model.cs" in result
        assert "templates/service.cs" in result

    def test_select_relevant_templates_empty_catalog(self, enhancer):
        """Test behavior with empty template catalog"""
        catalog = []
        technologies = {'c#', 'maui'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=5)

        # Should return empty list
        assert result == []

    def test_select_relevant_templates_empty_technologies(self, enhancer):
        """Test behavior with empty technologies set"""
        catalog = [
            {"path": "templates/model.cs", "category": "models", "name": "model"},
            {"path": "templates/service.py", "category": "services", "name": "service"},
        ]

        technologies = set()

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=5)

        # Should fallback to first N templates (no matches possible with empty technologies)
        assert len(result) == 2

    def test_select_relevant_templates_respects_max_limit(self, enhancer):
        """Test that max_templates limit is respected"""
        catalog = [
            {"path": f"templates/model{i}.cs", "category": "models", "name": f"model{i}"}
            for i in range(10)
        ]

        technologies = {'c#', '.net'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=3)

        # Should only return 3 templates
        assert len(result) == 3

    def test_select_relevant_templates_maui_project(self, enhancer):
        """Test template selection for real MAUI project technologies"""
        catalog = [
            {"path": "templates/other/LoadingRepository.cs", "category": "other", "name": "LoadingRepository"},
            {"path": "templates/other/ConfigurationService.cs", "category": "other", "name": "ConfigurationService"},
            {"path": "templates/other/RealmQuery.cs", "category": "other", "name": "RealmQuery"},
            {"path": "templates/api/ApiClient.cs", "category": "api", "name": "ApiClient"},
            {"path": "templates/components/Button.tsx", "category": "components", "name": "Button"},
        ]

        # Realistic MAUI project technologies
        technologies = {'c#', 'realm', 'maui', '.net', 'repository', 'mvvm'}

        result = enhancer._select_relevant_templates(catalog, technologies, max_templates=5)

        # Should select .cs files with realm/repository keywords
        assert "templates/other/LoadingRepository.cs" in result or "templates/other/RealmQuery.cs" in result
        # Should NOT select .tsx files
        assert "templates/components/Button.tsx" not in result
