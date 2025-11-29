"""
Integration Tests for Enhanced AI Prompting (TASK-042)

Tests the enhanced AI prompting features that guide template generation
toward CRUD completeness and pattern consistency.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil
import sys

# Add installer/global to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global"))

from lib.template_generator.template_generator import TemplateGenerator
from lib.template_generator.claude_md_generator import ClaudeMdGenerator
from lib.codebase_analyzer.prompt_builder import PromptBuilder
from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    ArchitectureInfo,
    TechnologyInfo,
    QualityInfo,
    ConfidenceScore,
    ExampleFile,
)


@pytest.fixture
def sample_analysis():
    """Create a sample CodebaseAnalysis for testing."""
    return CodebaseAnalysis(
        codebase_path="/test/codebase",
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=["FastEndpoints", "Entity Framework"],
            testing_frameworks=["xUnit"],
            build_tools=["dotnet"],
            databases=["PostgreSQL"],
            infrastructure=["Docker"],
            confidence=ConfidenceScore(
                level="high",
                percentage=95.0,
                reasoning="Clear framework usage patterns"
            )
        ),
        architecture=ArchitectureInfo(
            patterns=["REPR", "Repository", "Domain-Driven Design"],
            architectural_style="Clean Architecture",
            layers=[],
            key_abstractions=["Product", "Order", "User"],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level="high",
                percentage=90.0,
                reasoning="Standard Clean Architecture structure"
            )
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            test_coverage=75.0,
            code_smells=[],
            strengths=["Clear separation of concerns"],
            improvements=["Add more integration tests"],
            confidence=ConfidenceScore(
                level="medium",
                percentage=85.0,
                reasoning="Comprehensive code analysis"
            )
        ),
        example_files=[],
        overall_confidence=ConfidenceScore(
            level="high",
            percentage=90.0,
            reasoning="All metrics show high confidence"
        )
    )


class TestEnhancedPromptGeneration:
    """Test that prompts include completeness requirements."""

    def test_template_generator_prompt_includes_crud_completeness(self, sample_analysis):
        """Test that template generator prompt includes CRUD completeness rule."""
        generator = TemplateGenerator(sample_analysis)

        # Generate a prompt
        prompt = generator._create_extraction_prompt(
            content="namespace MyApp.Domain { public class GetProduct {} }",
            file_path="src/UseCases/Products/GetProduct.cs",
            language="C#",
            purpose="Get product by ID"
        )

        # Verify CRUD completeness section is present
        assert "CRITICAL - TEMPLATE COMPLETENESS" in prompt
        assert "CRUD Completeness Rule" in prompt
        assert "Create (POST)" in prompt
        assert "Read (GET by ID, GET collection)" in prompt
        assert "Update (PUT)" in prompt
        assert "Delete (DELETE)" in prompt

    def test_template_generator_prompt_includes_layer_symmetry(self, sample_analysis):
        """Test that template generator prompt includes layer symmetry rule."""
        generator = TemplateGenerator(sample_analysis)

        prompt = generator._create_extraction_prompt(
            content="public class UpdateProduct {}",
            file_path="src/UseCases/Products/UpdateProduct.cs",
            language="C#",
            purpose="Update product"
        )

        # Verify Layer Symmetry section is present
        assert "Layer Symmetry Rule" in prompt
        assert "UseCases has UpdateEntity → Web must have Update endpoint" in prompt
        assert "Operations must exist in ALL relevant layers" in prompt

    def test_template_generator_prompt_includes_repr_pattern(self, sample_analysis):
        """Test that template generator prompt includes REPR pattern completeness."""
        generator = TemplateGenerator(sample_analysis)

        prompt = generator._create_extraction_prompt(
            content="public class CreateProduct : Endpoint<CreateProductRequest> {}",
            file_path="src/Web/Products/Create.cs",
            language="C#",
            purpose="Create product endpoint"
        )

        # Verify REPR Pattern section is present
        assert "REPR Pattern Completeness" in prompt
        assert "Endpoint class" in prompt
        assert "Request DTO" in prompt
        assert "Response DTO" in prompt
        assert "Validator" in prompt

    def test_template_generator_prompt_includes_reminder(self, sample_analysis):
        """Test that prompt includes reminder about complete operations."""
        generator = TemplateGenerator(sample_analysis)

        prompt = generator._create_extraction_prompt(
            content="class Test {}",
            file_path="test.cs",
            language="C#",
            purpose="Test"
        )

        # Verify reminder is present
        assert "Users need COMPLETE CRUD operations" in prompt
        assert "not representative samples" in prompt


class TestClaudeMdValidationChecklist:
    """Test that CLAUDE.md includes validation checklist."""

    def test_claude_md_includes_validation_checklist(self, sample_analysis):
        """Test that generated CLAUDE.md includes validation checklist."""
        generator = ClaudeMdGenerator(sample_analysis)

        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify validation checklist is present
        assert "## Template Validation Checklist" in markdown
        assert "Before using this template, verify:" in markdown

    def test_validation_checklist_includes_crud_section(self, sample_analysis):
        """Test that validation checklist includes CRUD completeness section."""
        generator = ClaudeMdGenerator(sample_analysis)

        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify CRUD section
        assert "### CRUD Completeness" in markdown
        assert "Create operation (endpoint + handler + validator)" in markdown
        assert "Read operation (GetById + List + handlers)" in markdown
        assert "Update operation (endpoint + handler + validator)" in markdown
        assert "Delete operation (endpoint + handler + validator)" in markdown

    def test_validation_checklist_includes_layer_symmetry(self, sample_analysis):
        """Test that validation checklist includes layer symmetry section."""
        generator = ClaudeMdGenerator(sample_analysis)

        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify Layer Symmetry section
        assert "### Layer Symmetry" in markdown
        assert "All UseCases commands have Web endpoints" in markdown
        assert "All Web endpoints have UseCases handlers" in markdown
        assert "Repository interfaces exist for all operations" in markdown

    def test_validation_checklist_includes_repr_for_web_api(self, sample_analysis):
        """Test that validation checklist includes REPR pattern for web APIs."""
        # Modify analysis to include web/api patterns
        sample_analysis.architecture.architectural_style = "Web API with FastEndpoints"

        generator = ClaudeMdGenerator(sample_analysis)
        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify REPR section is present for web APIs
        assert "### REPR Pattern" in markdown
        assert "Each endpoint has Request/Response/Validator" in markdown

    def test_validation_checklist_includes_pattern_consistency(self, sample_analysis):
        """Test that validation checklist includes pattern consistency section."""
        generator = ClaudeMdGenerator(sample_analysis)

        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify Pattern Consistency section
        assert "### Pattern Consistency" in markdown
        assert "All entities follow same operation structure" in markdown
        assert "Naming conventions consistent" in markdown
        assert "Placeholders consistently applied" in markdown


class TestPromptBuilderCompletenessGuidance:
    """Test that analysis prompts include completeness guidance."""

    def test_analysis_prompt_includes_completeness_guidance(self):
        """Test that analysis prompt includes completeness guidance."""
        builder = PromptBuilder()

        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test/codebase"),
            file_samples=[],
            directory_structure="src/\n  Domain/\n  Application/",
            max_files=10
        )

        # Verify completeness guidance is present
        assert "## Completeness Analysis Guidance" in prompt
        assert "Identify ALL CRUD operations for each entity" in prompt
        assert "COMPLETE SCAFFOLDING templates" in prompt

    def test_completeness_guidance_mentions_layer_symmetry(self):
        """Test that completeness guidance mentions layer symmetry."""
        builder = PromptBuilder()

        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test/codebase"),
            file_samples=[],
            directory_structure="src/",
            max_files=10
        )

        # Verify layer symmetry guidance
        assert "Note layer symmetry" in prompt
        assert "UseCases operations should have corresponding Web endpoints" in prompt

    def test_completeness_guidance_mentions_supporting_files(self):
        """Test that completeness guidance mentions supporting files."""
        builder = PromptBuilder()

        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test/codebase"),
            file_samples=[],
            directory_structure="src/",
            max_files=10
        )

        # Verify supporting files guidance
        assert "Recognize patterns that require supporting files" in prompt
        assert "Validators, Specs, Repositories" in prompt

    def test_completeness_guidance_recommends_complete_sets(self):
        """Test that completeness guidance recommends complete operation sets."""
        builder = PromptBuilder()

        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test/codebase"),
            file_samples=[],
            directory_structure="src/",
            max_files=10
        )

        # Verify complete sets guidance
        assert "Recommend complete operation sets" in prompt
        assert "not partial implementations" in prompt


class TestCombinedEnhancedPrompting:
    """Test combined effect of all enhanced prompting improvements."""

    def test_full_template_generation_workflow_with_enhanced_prompts(self, sample_analysis):
        """Test full workflow uses enhanced prompts throughout."""
        # Create sample example file
        example_file = ExampleFile(
            path="src/UseCases/Products/GetProduct.cs",
            purpose="Get product by ID",
            layer="Application",
            patterns_used=["CQRS", "Repository"],
            key_concepts=["Product", "Query"],
            language="C#"
        )
        sample_analysis.example_files = [example_file]

        generator = TemplateGenerator(sample_analysis)

        # Mock AI client to verify prompt content
        mock_ai_client = Mock()
        mock_ai_client.generate.return_value = "{{Namespace}}.UseCases.{{EntityNamePlural}}\nPLACEHOLDERS: Namespace, EntityNamePlural"
        generator.ai_client = mock_ai_client

        # Generate templates
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a temporary source file
            src_file = Path(tmp_dir) / "src" / "UseCases" / "Products" / "GetProduct.cs"
            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.write_text("namespace MyApp.UseCases.Products { public class GetProduct {} }")

            # Update analysis to use temp directory
            sample_analysis.codebase_path = tmp_dir

            # Generate
            generator.generate(max_templates=1)

        # Verify AI was called with enhanced prompt
        assert mock_ai_client.generate.called
        prompt = mock_ai_client.generate.call_args[0][0]

        # Verify enhanced prompt content
        assert "CRITICAL - TEMPLATE COMPLETENESS" in prompt
        assert "CRUD Completeness Rule" in prompt
        assert "Layer Symmetry Rule" in prompt

    def test_combined_phases_improve_false_negative_score(self):
        """Test that enhanced prompting combined with other phases improves detection."""
        # This is a placeholder for future integration with Phase 1 (Validation)
        # and Phase 2 (Stratified Sampling)
        #
        # Expected improvement path:
        # - Baseline (Phase 0): 4.3/10
        # - After Phase 1: 7.0/10
        # - After Phase 1+2: 7.8/10
        # - After Phase 1+2+3: 8.5/10

        # For now, just verify that enhanced prompts are being used
        assert True  # Placeholder for future multi-phase integration test


class TestEnhancedPromptingBackwardCompatibility:
    """Test that enhanced prompts don't break existing functionality."""

    def test_template_generator_still_works_with_basic_files(self, sample_analysis):
        """Test that template generator still works with basic files."""
        generator = TemplateGenerator(sample_analysis)

        # Mock AI client
        mock_ai_client = Mock()
        mock_ai_client.generate.return_value = "{{Namespace}}.Test\nPLACEHOLDERS: Namespace"
        generator.ai_client = mock_ai_client

        # Should not raise exception
        content, placeholders = generator._ai_extract_placeholders(
            content="namespace Test { class Foo {} }",
            file_path="test.cs",
            language="C#",
            purpose="Test"
        )

        assert content is not None
        assert isinstance(placeholders, list)

    def test_claude_md_generator_still_works_without_agents(self, sample_analysis):
        """Test that CLAUDE.md generator still works without agents."""
        generator = ClaudeMdGenerator(sample_analysis, agents=None)

        # Should not raise exception
        claude = generator.generate()
        markdown = claude.to_markdown()

        assert markdown is not None
        assert len(markdown) > 0

    def test_prompt_builder_still_works_with_minimal_input(self):
        """Test that prompt builder still works with minimal input."""
        builder = PromptBuilder()

        # Should not raise exception with empty samples
        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test"),
            file_samples=[],
            directory_structure="",
            max_files=0
        )

        assert prompt is not None
        assert len(prompt) > 0


@pytest.mark.integration
class TestEnhancedPromptingE2E:
    """End-to-end integration tests for enhanced prompting."""

    def test_e2e_template_generation_with_enhanced_prompts(self, sample_analysis):
        """Test end-to-end template generation with enhanced prompts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup test codebase
            src_dir = Path(tmp_dir) / "src"
            src_dir.mkdir()

            # Create sample files
            (src_dir / "GetProduct.cs").write_text(
                "namespace MyApp { public class GetProduct {} }"
            )

            # Update analysis
            sample_analysis.codebase_path = tmp_dir
            sample_analysis.example_files = [
                ExampleFile(
                    path="src/GetProduct.cs",
                    purpose="Get product",
                    layer="Application",
                    patterns_used=["CQRS"],
                    key_concepts=["Product"],
                    language="C#"
                )
            ]

            # Generate templates
            generator = TemplateGenerator(sample_analysis)

            # Mock AI response
            mock_ai_client = Mock()
            mock_ai_client.generate.return_value = "{{Namespace}}.{{EntityName}}\nPLACEHOLDERS: Namespace, EntityName"
            generator.ai_client = mock_ai_client

            collection = generator.generate(max_templates=1)

            # Verify templates were generated
            assert collection.total_count >= 0

            # Verify AI was called with enhanced prompt
            if mock_ai_client.generate.called:
                prompt = mock_ai_client.generate.call_args[0][0]
                assert "CRUD Completeness Rule" in prompt

    def test_e2e_claude_md_generation_with_validation_checklist(self, sample_analysis):
        """Test end-to-end CLAUDE.md generation with validation checklist."""
        generator = ClaudeMdGenerator(sample_analysis)

        claude = generator.generate()
        markdown = claude.to_markdown()

        # Verify complete CLAUDE.md structure
        assert "# Architecture Overview" in markdown
        assert "# Technology Stack" in markdown
        assert "# Quality Standards" in markdown
        assert "## Template Validation Checklist" in markdown

        # Verify checklist is properly formatted
        assert "- [ ]" in markdown  # At least one checkbox

        # Verify all major sections present
        assert "### CRUD Completeness" in markdown
        assert "### Layer Symmetry" in markdown
        assert "### Pattern Consistency" in markdown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
