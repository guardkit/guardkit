"""
Unit Tests for Extended Validator (TASK-043)

Tests extended validation functionality beyond Phase 5.5 completeness checks.
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import using importlib to bypass 'global' keyword issue
import importlib
extended_validator_module = importlib.import_module('installer.global.lib.template_generator.extended_validator')
models_module = importlib.import_module('installer.global.lib.template_generator.models')

# Extract classes
ExtendedValidator = extended_validator_module.ExtendedValidator
ExtendedValidationReport = extended_validator_module.ExtendedValidationReport
SpotCheckResult = extended_validator_module.SpotCheckResult
TemplateCollection = models_module.TemplateCollection
CodeTemplate = models_module.CodeTemplate
ValidationReport = models_module.ValidationReport


# ===== Fixtures =====

@pytest.fixture
def sample_template():
    """Create a sample template for testing"""
    return CodeTemplate(
        name="GetProducts.cs.template",
        original_path="src/Domain/Products/GetProducts.cs",
        template_path="templates/Domain/Products/GetProducts.template",
        content="""namespace {{ProjectName}}.Domain.{{EntityNamePlural}};

public class Get{{EntityNamePlural}}
{
    private readonly IRepository<{{EntityName}}> _repository;

    public Get{{EntityNamePlural}}(IRepository<{{EntityName}}> repository)
    {
        _repository = repository;
    }

    public async Task<Result<List<{{EntityName}}>>> Execute()
    {
        var entities = await _repository.GetAllAsync();
        return Result.Success(entities);
    }
}""",
        placeholders=["ProjectName", "EntityNamePlural", "EntityName"],
        file_type="domain_operation",
        language="C#",
        purpose="Domain operation for querying entities",
        quality_score=8.5,
        patterns=["Repository pattern", "Result type pattern"]
    )


@pytest.fixture
def sample_templates(sample_template):
    """Create a collection of sample templates"""
    templates = [sample_template]

    # Add more templates with different characteristics
    for i in range(4):
        template = CodeTemplate(
            name=f"Template{i}.cs.template",
            original_path=f"src/Domain/Template{i}.cs",
            template_path=f"templates/Domain/Template{i}.template",
            content=f"namespace {{{{ProjectName}}}}.Domain; public class Template{i} {{ }}",
            placeholders=["ProjectName"],
            file_type="domain_operation",
            language="C#",
            quality_score=7.0 + i,
            patterns=["Repository pattern"]
        )
        templates.append(template)

    return TemplateCollection(
        templates=templates,
        total_count=len(templates),
        by_type={"domain_operation": len(templates)}
    )


@pytest.fixture
def sample_manifest():
    """Create a sample manifest"""
    return {
        'name': 'test-template',
        'language': 'C#',
        'architecture': 'Clean Architecture',
        'placeholders': ['ProjectName', 'EntityName', 'EntityNamePlural'],
        'patterns': ['Repository pattern', 'Result type pattern'],
        'complexity': 5
    }


@pytest.fixture
def sample_settings():
    """Create sample settings"""
    return {
        'naming_conventions': [
            {'pattern': 'PascalCase', 'applies_to': 'classes'}
        ],
        'layer_mappings': [
            {'layer': 'Domain', 'path': 'src/Domain'}
        ]
    }


@pytest.fixture
def sample_claude_md(tmp_path):
    """Create a sample CLAUDE.md file"""
    claude_path = tmp_path / "CLAUDE.md"
    claude_path.write_text("""# Architecture Overview

This template follows Clean Architecture principles.

## Technology Stack

- C# 12
- .NET 8
- Repository Pattern
- Result Type Pattern

## Code Examples

```csharp
public class GetProducts
{
    // Example implementation
}
```

## Quality Standards

All code must follow SOLID principles.

## Agents

Use the domain-operations-specialist agent for domain logic.
""", encoding='utf-8')
    return claude_path


@pytest.fixture
def sample_agents(tmp_path):
    """Create sample agent files"""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    agent_path = agents_dir / "domain-operations-specialist.md"
    agent_path.write_text("""---
name: domain-operations-specialist
purpose: Create domain operations
---

# Domain Operations Specialist

This agent helps create domain operations.
""", encoding='utf-8')

    return [agent_path]


@pytest.fixture
def validator():
    """Create an ExtendedValidator instance"""
    return ExtendedValidator()


# ===== Placeholder Consistency Tests =====

def test_placeholder_consistency_validation_all_valid(validator, sample_templates):
    """Test placeholder consistency with valid placeholders"""
    score = validator._validate_placeholder_consistency(sample_templates)
    assert score >= 8.0
    assert score <= 10.0


def test_placeholder_consistency_validation_empty_collection(validator):
    """Test placeholder consistency with empty collection"""
    empty_collection = TemplateCollection(templates=[], total_count=0, by_type={})
    score = validator._validate_placeholder_consistency(empty_collection)
    assert score == 10.0  # No templates = no inconsistencies


def test_is_valid_placeholder_casing_pascal_case(validator):
    """Test PascalCase placeholder validation"""
    assert validator._is_valid_placeholder_casing("EntityName") is True
    assert validator._is_valid_placeholder_casing("ProjectName") is True
    assert validator._is_valid_placeholder_casing("EntityNamePlural") is True


def test_is_valid_placeholder_casing_camel_case(validator):
    """Test camelCase placeholder validation"""
    assert validator._is_valid_placeholder_casing("entityName") is True
    assert validator._is_valid_placeholder_casing("projectName") is True


def test_is_valid_placeholder_casing_upper_case(validator):
    """Test UPPER_CASE placeholder validation"""
    assert validator._is_valid_placeholder_casing("MAX_COUNT") is True
    assert validator._is_valid_placeholder_casing("API_KEY") is True


def test_is_valid_placeholder_casing_invalid(validator):
    """Test invalid placeholder casing"""
    assert validator._is_valid_placeholder_casing("entity_name") is False
    assert validator._is_valid_placeholder_casing("Entity-Name") is False
    assert validator._is_valid_placeholder_casing("123Entity") is False


# ===== Pattern Fidelity Tests =====

def test_pattern_fidelity_validation(validator, sample_templates):
    """Test pattern fidelity spot-checks"""
    score, spot_checks = validator._validate_pattern_fidelity(sample_templates)

    assert 0.0 <= score <= 10.0
    assert len(spot_checks) == min(5, sample_templates.total_count)

    # Verify spot check results structure
    for spot_check in spot_checks:
        assert isinstance(spot_check, SpotCheckResult)
        assert hasattr(spot_check, 'template_path')
        assert hasattr(spot_check, 'passed')
        assert hasattr(spot_check, 'checks_performed')
        assert hasattr(spot_check, 'issues_found')
        assert hasattr(spot_check, 'score')


def test_pattern_fidelity_validation_empty_collection(validator):
    """Test pattern fidelity with empty collection"""
    empty_collection = TemplateCollection(templates=[], total_count=0, by_type={})
    score, spot_checks = validator._validate_pattern_fidelity(empty_collection)

    assert score == 10.0
    assert len(spot_checks) == 0


def test_spot_check_template_good_quality(validator, sample_template):
    """Test spot-check on high-quality template"""
    result = validator._spot_check_template(sample_template)

    assert isinstance(result, SpotCheckResult)
    assert result.score >= 7.0  # Good quality template
    assert len(result.checks_performed) > 0


def test_spot_check_template_no_placeholders(validator):
    """Test spot-check on template with no placeholders"""
    template = CodeTemplate(
        name="Empty.cs.template",
        original_path="src/Empty.cs",
        template_path="templates/Empty.template",
        content="public class Empty { }",  # No placeholders
        placeholders=[],
        file_type="class",
        language="C#",
        quality_score=5.0
    )

    result = validator._spot_check_template(template)
    assert result.score < 10.0  # Penalized for no placeholders
    assert any("No placeholders" in issue for issue in result.issues_found)


# ===== Documentation Validation Tests =====

def test_documentation_validation_complete(validator, sample_claude_md, sample_manifest, sample_agents):
    """Test documentation validation with complete CLAUDE.md"""
    score = validator._validate_documentation(sample_claude_md, sample_manifest, sample_agents)
    assert score >= 7.0  # Should score well with complete doc


def test_documentation_validation_missing_file(validator, tmp_path, sample_manifest, sample_agents):
    """Test documentation validation with missing CLAUDE.md"""
    missing_path = tmp_path / "nonexistent.md"
    score = validator._validate_documentation(missing_path, sample_manifest, sample_agents)
    assert score == 0.0


def test_documentation_validation_minimal_content(validator, tmp_path, sample_manifest):
    """Test documentation validation with minimal content"""
    minimal_md = tmp_path / "minimal.md"
    minimal_md.write_text("# Title\n\nMinimal content.", encoding='utf-8')

    score = validator._validate_documentation(minimal_md, sample_manifest, [])
    assert score < 7.0  # Should be penalized for missing sections


# ===== Agent Validation Tests =====

def test_agent_validation_valid_agents(validator, sample_agents, sample_claude_md):
    """Test agent validation with valid agents"""
    score = validator._validate_agents(sample_agents, sample_claude_md)
    assert score >= 7.0  # All agents valid and documented


def test_agent_validation_no_agents(validator, sample_claude_md):
    """Test agent validation with no agents"""
    score = validator._validate_agents([], sample_claude_md)
    assert score == 10.0  # No agents = no issues


def test_agent_validation_missing_frontmatter(validator, tmp_path, sample_claude_md):
    """Test agent validation with agent missing frontmatter"""
    agent_path = tmp_path / "bad-agent.md"
    agent_path.write_text("# Agent\n\nNo frontmatter", encoding='utf-8')

    score = validator._validate_agents([agent_path], sample_claude_md)
    assert score < 10.0  # Penalized for missing frontmatter


# ===== Manifest Validation Tests =====

def test_manifest_validation_complete(validator, sample_manifest, sample_templates):
    """Test manifest validation with complete manifest"""
    score = validator._validate_manifest(sample_manifest, sample_templates)
    assert score >= 8.0


def test_manifest_validation_missing_required_fields(validator, sample_templates):
    """Test manifest validation with missing required fields"""
    incomplete_manifest = {'name': 'test'}  # Missing language, architecture
    score = validator._validate_manifest(incomplete_manifest, sample_templates)
    assert score < 8.0


def test_manifest_validation_invalid_complexity(validator, sample_templates):
    """Test manifest validation with invalid complexity"""
    manifest = {
        'name': 'test',
        'language': 'C#',
        'architecture': 'Clean',
        'complexity': 15  # Invalid (>10)
    }
    score = validator._validate_manifest(manifest, sample_templates)
    assert score < 10.0


# ===== Overall Score Calculation Tests =====

def test_calculate_overall_score_perfect(validator):
    """Test overall score calculation with perfect scores"""
    score = validator._calculate_overall_score(
        completeness_score=10.0,
        placeholder_score=10.0,
        fidelity_score=10.0,
        doc_score=10.0,
        agent_score=10.0,
        manifest_score=10.0
    )
    assert score == 10.0


def test_calculate_overall_score_weighted(validator):
    """Test overall score calculation with weighted scores"""
    # Completeness is 50% weight, others 10% each
    score = validator._calculate_overall_score(
        completeness_score=10.0,  # 50% weight = 5.0
        placeholder_score=0.0,    # 10% weight = 0.0
        fidelity_score=0.0,       # 10% weight = 0.0
        doc_score=0.0,            # 10% weight = 0.0
        agent_score=0.0,          # 10% weight = 0.0
        manifest_score=0.0        # 10% weight = 0.0
    )
    assert score == 5.0  # Only completeness contributes


def test_calculate_overall_score_mixed(validator):
    """Test overall score calculation with mixed scores"""
    score = validator._calculate_overall_score(
        completeness_score=8.0,   # 50% = 4.0
        placeholder_score=9.0,    # 10% = 0.9
        fidelity_score=7.0,       # 10% = 0.7
        doc_score=8.0,            # 10% = 0.8
        agent_score=10.0,         # 10% = 1.0
        manifest_score=6.0        # 10% = 0.6
    )
    # Total: 4.0 + 0.9 + 0.7 + 0.8 + 1.0 + 0.6 = 8.0
    assert score == 8.0


# ===== ExtendedValidationReport Tests =====

def test_extended_validation_report_production_ready():
    """Test production readiness check"""
    report = ExtendedValidationReport(
        overall_score=8.5,
        completeness_score=9.0,
        placeholder_consistency_score=8.0,
        pattern_fidelity_score=8.5,
        documentation_score=8.0,
        agent_validation_score=9.0,
        manifest_accuracy_score=8.0
    )
    assert report.is_production_ready() is True
    assert report.get_exit_code() == 0


def test_extended_validation_report_needs_improvement():
    """Test needs improvement status"""
    report = ExtendedValidationReport(
        overall_score=7.0,
        completeness_score=7.0,
        placeholder_consistency_score=7.0,
        pattern_fidelity_score=7.0,
        documentation_score=7.0,
        agent_validation_score=7.0,
        manifest_accuracy_score=7.0
    )
    assert report.is_production_ready() is False
    assert report.get_exit_code() == 1


def test_extended_validation_report_not_ready():
    """Test not ready status"""
    report = ExtendedValidationReport(
        overall_score=5.0,
        completeness_score=5.0,
        placeholder_consistency_score=5.0,
        pattern_fidelity_score=5.0,
        documentation_score=5.0,
        agent_validation_score=5.0,
        manifest_accuracy_score=5.0
    )
    assert report.is_production_ready() is False
    assert report.get_exit_code() == 2


def test_extended_validation_report_grade_assignment():
    """Test grade assignment"""
    test_cases = [
        (9.7, "A+"),
        (9.2, "A"),
        (8.7, "A-"),
        (8.2, "B+"),
        (7.5, "B"),
        (6.5, "C"),
        (5.0, "F")
    ]

    for score, expected_grade in test_cases:
        report = ExtendedValidationReport(
            overall_score=score,
            completeness_score=score,
            placeholder_consistency_score=score,
            pattern_fidelity_score=score,
            documentation_score=score,
            agent_validation_score=score,
            manifest_accuracy_score=score
        )
        assert report.get_grade() == expected_grade


# ===== Full Validation Tests =====

def test_full_validation_integration(
    validator,
    sample_templates,
    sample_manifest,
    sample_settings,
    sample_claude_md,
    sample_agents
):
    """Test complete validation workflow"""
    report = validator.validate(
        templates=sample_templates,
        manifest=sample_manifest,
        settings=sample_settings,
        claude_md_path=sample_claude_md,
        agents=sample_agents,
        phase_5_5_report=None
    )

    # Verify report structure
    assert isinstance(report, ExtendedValidationReport)
    assert 0.0 <= report.overall_score <= 10.0
    assert 0.0 <= report.completeness_score <= 10.0
    assert 0.0 <= report.placeholder_consistency_score <= 10.0
    assert 0.0 <= report.pattern_fidelity_score <= 10.0
    assert 0.0 <= report.documentation_score <= 10.0
    assert 0.0 <= report.agent_validation_score <= 10.0
    assert 0.0 <= report.manifest_accuracy_score <= 10.0

    # Verify recommendations generated
    assert isinstance(report.recommendations, list)
    assert len(report.recommendations) > 0

    # Verify spot checks performed
    assert len(report.spot_check_results) > 0


# ===== Recommendations Tests =====

def test_generate_recommendations_all_good(validator):
    """Test recommendations with all good scores"""
    recommendations = validator._generate_recommendations(
        completeness_score=9.0,
        placeholder_score=9.0,
        fidelity_score=9.0,
        doc_score=9.0,
        agent_score=9.0,
        manifest_score=9.0
    )
    assert len(recommendations) == 1
    assert "excellent" in recommendations[0].lower()


def test_generate_recommendations_multiple_issues(validator):
    """Test recommendations with multiple low scores"""
    recommendations = validator._generate_recommendations(
        completeness_score=6.0,
        placeholder_score=6.0,
        fidelity_score=6.0,
        doc_score=6.0,
        agent_score=6.0,
        manifest_score=6.0
    )
    assert len(recommendations) == 6  # One for each low score


# ===== Issues Collection Tests =====

def test_collect_issues_none(validator):
    """Test issue collection with no critical issues"""
    issues = validator._collect_issues(
        placeholder_score=8.0,
        fidelity_score=8.0,
        doc_score=8.0,
        agent_score=8.0,
        manifest_score=8.0
    )
    assert len(issues) == 0


def test_collect_issues_critical(validator):
    """Test issue collection with critical issues"""
    issues = validator._collect_issues(
        placeholder_score=5.0,
        fidelity_score=5.0,
        doc_score=5.0,
        agent_score=5.0,
        manifest_score=5.0
    )
    assert len(issues) == 5  # One critical issue per category
    assert all("Critical" in issue for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
