"""
Unit Tests for Completeness Validator

Tests CRUD completeness detection, layer symmetry, and auto-generation.

TASK-040: Phase 1 - Completeness Validation Layer
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import using importlib to bypass 'global' keyword issue
import importlib
models_module = importlib.import_module('installer.global.lib.template_generator.models')
validator_module = importlib.import_module('installer.global.lib.template_generator.completeness_validator')

CodeTemplate = models_module.CodeTemplate
TemplateCollection = models_module.TemplateCollection
CompletenessIssue = models_module.CompletenessIssue
TemplateRecommendation = models_module.TemplateRecommendation
ValidationReport = models_module.ValidationReport
CompletenessValidator = validator_module.CompletenessValidator


class TestCompletenessValidator:
    """Test completeness validation"""

    @pytest.fixture
    def incomplete_crud_templates(self):
        """Create template collection with incomplete CRUD (missing Update, Delete)"""
        templates = [
            CodeTemplate(
                name="CreateProduct.cs",
                original_path="src/UseCases/Products/CreateProduct.cs",
                template_path="templates/UseCases/Products/CreateProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class CreateProduct { }",
                placeholders=["ProjectName"]
            ),
            CodeTemplate(
                name="GetProduct.cs",
                original_path="src/UseCases/Products/GetProduct.cs",
                template_path="templates/UseCases/Products/GetProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class GetProduct { }",
                placeholders=["ProjectName"]
            )
        ]

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type={}
        )

    @pytest.fixture
    def complete_crud_templates(self):
        """Create template collection with complete CRUD"""
        templates = [
            CodeTemplate(
                name="CreateProduct.cs",
                original_path="src/UseCases/Products/CreateProduct.cs",
                template_path="templates/UseCases/Products/CreateProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class CreateProduct { }"
            ),
            CodeTemplate(
                name="GetProduct.cs",
                original_path="src/UseCases/Products/GetProduct.cs",
                template_path="templates/UseCases/Products/GetProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class GetProduct { }"
            ),
            CodeTemplate(
                name="UpdateProduct.cs",
                original_path="src/UseCases/Products/UpdateProduct.cs",
                template_path="templates/UseCases/Products/UpdateProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class UpdateProduct { }"
            ),
            CodeTemplate(
                name="DeleteProduct.cs",
                original_path="src/UseCases/Products/DeleteProduct.cs",
                template_path="templates/UseCases/Products/DeleteProduct.template",
                content="namespace {{ProjectName}}.UseCases.Products;\n\npublic class DeleteProduct { }"
            )
        ]

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type={}
        )

    @pytest.fixture
    def layer_asymmetry_templates(self):
        """Create templates with layer asymmetry (UseCases has Update, Web doesn't)"""
        templates = [
            CodeTemplate(
                name="CreateProduct.cs",
                original_path="src/UseCases/Products/CreateProduct.cs",
                template_path="templates/UseCases/Products/CreateProduct.template",
                content=""
            ),
            CodeTemplate(
                name="UpdateProduct.cs",
                original_path="src/UseCases/Products/UpdateProduct.cs",
                template_path="templates/UseCases/Products/UpdateProduct.template",
                content=""
            ),
            CodeTemplate(
                name="CreateEndpoint.cs",
                original_path="src/Web/Endpoints/CreateEndpoint.cs",
                template_path="templates/Web/Endpoints/CreateEndpoint.template",
                content=""
            )
            # Missing: UpdateEndpoint in Web layer
        ]

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type={}
        )

    def test_validate_incomplete_crud(self, incomplete_crud_templates):
        """Test detection of incomplete CRUD operations"""
        validator = CompletenessValidator()
        report = validator.validate(incomplete_crud_templates)

        assert not report.is_complete
        assert len(report.issues) > 0

        # Should detect missing Update and Delete
        issue_operations = [issue.operation for issue in report.issues if issue.type == 'incomplete_crud']
        assert 'Update' in issue_operations
        assert 'Delete' in issue_operations

    def test_validate_complete_crud(self, complete_crud_templates):
        """Test validation of complete CRUD operations"""
        validator = CompletenessValidator()
        report = validator.validate(complete_crud_templates)

        # Should have no incomplete_crud issues (may have layer_asymmetry)
        incomplete_crud_issues = [
            issue for issue in report.issues
            if issue.type == 'incomplete_crud'
        ]
        assert len(incomplete_crud_issues) == 0

    def test_validate_layer_asymmetry(self, layer_asymmetry_templates):
        """Test detection of layer asymmetry"""
        validator = CompletenessValidator()
        report = validator.validate(layer_asymmetry_templates)

        assert not report.is_complete
        assert len(report.issues) > 0

        # Should detect Update in UseCases but not Web
        layer_issues = [issue for issue in report.issues if issue.type == 'layer_asymmetry']
        assert len(layer_issues) > 0

        update_issue = next(
            (issue for issue in layer_issues if issue.operation == 'Update'),
            None
        )
        assert update_issue is not None
        assert update_issue.layer == 'Web'  # Missing layer

    def test_false_negative_score_calculation(self):
        """Test False Negative score calculation"""
        validator = CompletenessValidator()

        # Perfect score (all templates present)
        score = validator._calculate_false_negative_score(
            templates_generated=10,
            templates_expected=10
        )
        assert score == 10.0

        # 80% score
        score = validator._calculate_false_negative_score(
            templates_generated=8,
            templates_expected=10
        )
        assert score == 8.0

        # 50% score
        score = validator._calculate_false_negative_score(
            templates_generated=5,
            templates_expected=10
        )
        assert score == 5.0

        # 0% score (no templates)
        score = validator._calculate_false_negative_score(
            templates_generated=0,
            templates_expected=10
        )
        assert score == 0.0

        # Edge case: no templates expected
        score = validator._calculate_false_negative_score(
            templates_generated=0,
            templates_expected=0
        )
        assert score == 10.0

    def test_generate_recommendations(self, incomplete_crud_templates):
        """Test recommendation generation for missing templates"""
        validator = CompletenessValidator()
        report = validator.validate(incomplete_crud_templates)

        assert len(report.recommended_templates) > 0

        # Should recommend Update and Delete templates
        recommended_operations = []
        for rec in report.recommended_templates:
            if 'Update' in rec.file_path:
                recommended_operations.append('Update')
            if 'Delete' in rec.file_path:
                recommended_operations.append('Delete')

        assert 'Update' in recommended_operations
        assert 'Delete' in recommended_operations

    def test_generate_missing_templates(self, incomplete_crud_templates):
        """Test auto-generation of missing templates"""
        validator = CompletenessValidator()
        report = validator.validate(incomplete_crud_templates)

        # Auto-generate missing templates
        new_templates = validator.generate_missing_templates(
            recommendations=report.recommended_templates,
            existing_templates=incomplete_crud_templates
        )

        assert len(new_templates) > 0

        # Check that generated templates have correct structure
        for template in new_templates:
            assert template.name is not None
            assert template.template_path is not None
            assert template.content is not None
            assert len(template.placeholders) > 0  # Should preserve placeholders

    def test_clone_and_adapt_template(self, complete_crud_templates):
        """Test template cloning and adaptation"""
        validator = CompletenessValidator()

        # Use CreateProduct as reference to generate UpdateProduct
        reference = complete_crud_templates.templates[0]  # CreateProduct

        new_template = validator._clone_and_adapt_template(
            reference=reference,
            target_path="templates/UseCases/Products/UpdateProduct.template"
        )

        assert new_template is not None
        assert 'Update' in new_template.name
        assert 'Update' in new_template.content or 'update' in new_template.content
        assert 'Create' not in new_template.content or new_template.content.count('Create') < reference.content.count('Create')

    def test_replace_operation_in_content(self):
        """Test operation name replacement in content"""
        validator = CompletenessValidator()

        content = """
        namespace MyApp.UseCases.Products;

        public class CreateProduct
        {
            public Result Create(CreateProductRequest request)
            {
                // Create logic
                return Result.Success();
            }
        }
        """

        updated = validator._replace_operation_in_content(
            content=content,
            old_operation='Create',
            new_operation='Update'
        )

        assert 'UpdateProduct' in updated
        assert 'Update(UpdateProductRequest' in updated or 'Update(CreateProductRequest' in updated
        assert 'CreateProduct' not in updated or updated.count('CreateProduct') < content.count('CreateProduct')

    def test_find_reference_template(self, complete_crud_templates):
        """Test finding reference template for entity"""
        validator = CompletenessValidator()

        # Find reference for Product entity, Update operation
        reference = validator._find_reference_template(
            entity='Product',
            operation='Update',
            templates=complete_crud_templates
        )

        assert reference is not None
        # Should find Create as preferred reference for Update
        assert 'Product' in reference.name

    def test_validation_report_properties(self, incomplete_crud_templates):
        """Test ValidationReport properties"""
        validator = CompletenessValidator()
        report = validator.validate(incomplete_crud_templates)

        # Test has_high_severity_issues property
        if any(issue.severity in ['critical', 'high'] for issue in report.issues):
            assert report.has_high_severity_issues

        # Test to_dict serialization
        report_dict = report.to_dict()
        assert 'is_complete' in report_dict
        assert 'issues' in report_dict
        assert 'recommended_templates' in report_dict
        assert 'false_negative_score' in report_dict

    def test_empty_template_collection(self):
        """Test validation of empty template collection"""
        validator = CompletenessValidator()

        empty_collection = TemplateCollection(
            templates=[],
            total_count=0,
            by_type={}
        )

        report = validator.validate(empty_collection)

        assert report.is_complete  # No entities, so complete
        assert len(report.issues) == 0
        assert report.false_negative_score == 10.0

    def test_single_template_collection(self):
        """Test validation of single template (incomplete entity)"""
        validator = CompletenessValidator()

        single_template = TemplateCollection(
            templates=[
                CodeTemplate(
                    name="CreateProduct.cs",
                    original_path="src/UseCases/Products/CreateProduct.cs",
                    template_path="templates/UseCases/Products/CreateProduct.template",
                    content=""
                )
            ],
            total_count=1,
            by_type={}
        )

        report = validator.validate(single_template)

        assert not report.is_complete
        # Should recommend Read, Update, Delete
        assert len(report.issues) >= 3


class TestCompletenessIssue:
    """Test CompletenessIssue model"""

    def test_create_issue(self):
        """Test issue creation"""
        issue = CompletenessIssue(
            severity='high',
            type='incomplete_crud',
            message='Product entity missing Update operation',
            entity='Product',
            operation='Update',
            layer='UseCases',
            missing_files=['UpdateProduct.cs']
        )

        assert issue.severity == 'high'
        assert issue.type == 'incomplete_crud'
        assert issue.entity == 'Product'
        assert issue.operation == 'Update'

    def test_issue_serialization(self):
        """Test issue to_dict conversion"""
        issue = CompletenessIssue(
            severity='high',
            type='incomplete_crud',
            message='Product entity missing Update operation',
            entity='Product',
            operation='Update'
        )

        issue_dict = issue.to_dict()

        assert issue_dict['severity'] == 'high'
        assert issue_dict['type'] == 'incomplete_crud'
        assert issue_dict['entity'] == 'Product'


class TestTemplateRecommendation:
    """Test TemplateRecommendation model"""

    def test_create_recommendation(self):
        """Test recommendation creation"""
        rec = TemplateRecommendation(
            file_path='templates/UseCases/Products/UpdateProduct.template',
            reason='Update operation missing for Product entity',
            can_auto_generate=True,
            reference_template='templates/UseCases/Products/CreateProduct.template',
            estimated_confidence=0.85
        )

        assert rec.can_auto_generate
        assert rec.estimated_confidence == 0.85

    def test_recommendation_serialization(self):
        """Test recommendation to_dict conversion"""
        rec = TemplateRecommendation(
            file_path='templates/UseCases/Products/UpdateProduct.template',
            reason='Update operation missing',
            can_auto_generate=True
        )

        rec_dict = rec.to_dict()

        assert rec_dict['file_path'] == 'templates/UseCases/Products/UpdateProduct.template'
        assert rec_dict['can_auto_generate'] is True
