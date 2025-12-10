"""
Unit Tests for Pattern Matcher

Tests CRUD operation detection, layer identification, and entity extraction.

TASK-040: Phase 1 - Completeness Validation Layer
"""

import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import using importlib to bypass 'global' keyword issue
import importlib
models_module = importlib.import_module('installer.core.lib.template_generator.models')
pattern_matcher_module = importlib.import_module('installer.core.lib.template_generator.pattern_matcher')

CodeTemplate = models_module.CodeTemplate
TemplateCollection = models_module.TemplateCollection
CRUDPatternMatcher = pattern_matcher_module.CRUDPatternMatcher
OperationExtractor = pattern_matcher_module.OperationExtractor


class TestCRUDPatternMatcher:
    """Test CRUD operation identification"""

    def test_identify_create_operation(self):
        """Test identification of Create operation"""
        template = CodeTemplate(
            name="CreateProduct.cs",
            original_path="src/UseCases/Products/CreateProduct.cs",
            template_path="templates/UseCases/Products/CreateProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Create'

    def test_identify_read_operation_with_get(self):
        """Test identification of Read operation (Get)"""
        template = CodeTemplate(
            name="GetProduct.cs",
            original_path="src/UseCases/Products/GetProduct.cs",
            template_path="templates/UseCases/Products/GetProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Read'

    def test_identify_read_operation_with_query(self):
        """Test identification of Read operation (Query)"""
        template = CodeTemplate(
            name="QueryProducts.cs",
            original_path="src/UseCases/Products/QueryProducts.cs",
            template_path="templates/UseCases/Products/QueryProducts.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Read'

    def test_identify_update_operation(self):
        """Test identification of Update operation"""
        template = CodeTemplate(
            name="UpdateProduct.cs",
            original_path="src/UseCases/Products/UpdateProduct.cs",
            template_path="templates/UseCases/Products/UpdateProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Update'

    def test_identify_delete_operation(self):
        """Test identification of Delete operation"""
        template = CodeTemplate(
            name="DeleteProduct.cs",
            original_path="src/UseCases/Products/DeleteProduct.cs",
            template_path="templates/UseCases/Products/DeleteProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Delete'

    def test_identify_list_operation(self):
        """Test identification of List operation"""
        template = CodeTemplate(
            name="ListProducts.cs",
            original_path="src/UseCases/Products/ListProducts.cs",
            template_path="templates/UseCases/Products/ListProducts.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'List'

    def test_no_operation_identified(self):
        """Test when no operation can be identified"""
        template = CodeTemplate(
            name="Product.cs",
            original_path="src/Domain/Products/Product.cs",
            template_path="templates/Domain/Products/Product.template",
            content="namespace {{ProjectName}}.Domain.Products;"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation is None

    def test_identify_layer_usecases(self):
        """Test identification of UseCases layer"""
        template = CodeTemplate(
            name="CreateProduct.cs",
            original_path="src/UseCases/Products/CreateProduct.cs",
            template_path="templates/UseCases/Products/CreateProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        layer = matcher.identify_layer(template)

        assert layer == 'UseCases'

    def test_identify_layer_web(self):
        """Test identification of Web layer"""
        template = CodeTemplate(
            name="ProductEndpoints.cs",
            original_path="src/Web/Endpoints/ProductEndpoints.cs",
            template_path="templates/Web/Endpoints/ProductEndpoints.template",
            content="namespace {{ProjectName}}.Web.Endpoints;"
        )

        matcher = CRUDPatternMatcher()
        layer = matcher.identify_layer(template)

        assert layer == 'Web'

    def test_identify_layer_domain(self):
        """Test identification of Domain layer"""
        template = CodeTemplate(
            name="Product.cs",
            original_path="src/Domain/Products/Product.cs",
            template_path="templates/Domain/Products/Product.template",
            content="namespace {{ProjectName}}.Domain.Products;"
        )

        matcher = CRUDPatternMatcher()
        layer = matcher.identify_layer(template)

        assert layer == 'Domain'

    def test_identify_layer_infrastructure(self):
        """Test identification of Infrastructure layer"""
        template = CodeTemplate(
            name="ProductRepository.cs",
            original_path="src/Infrastructure/Persistence/ProductRepository.cs",
            template_path="templates/Infrastructure/Persistence/ProductRepository.template",
            content="namespace {{ProjectName}}.Infrastructure.Persistence;"
        )

        matcher = CRUDPatternMatcher()
        layer = matcher.identify_layer(template)

        assert layer == 'Infrastructure'

    def test_identify_entity_from_create(self):
        """Test entity extraction from Create operation"""
        template = CodeTemplate(
            name="CreateProduct.cs",
            original_path="src/UseCases/Products/CreateProduct.cs",
            template_path="templates/UseCases/Products/CreateProduct.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'Product'

    def test_identify_entity_from_get(self):
        """Test entity extraction from Get operation"""
        template = CodeTemplate(
            name="GetUser.cs",
            original_path="src/UseCases/Users/GetUser.cs",
            template_path="templates/UseCases/Users/GetUser.template",
            content="namespace {{ProjectName}}.UseCases.Users;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'User'

    def test_identify_entity_with_suffix_request(self):
        """Test entity extraction with Request suffix"""
        template = CodeTemplate(
            name="CreateProductRequest.cs",
            original_path="src/UseCases/Products/CreateProductRequest.cs",
            template_path="templates/UseCases/Products/CreateProductRequest.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'Product'

    def test_identify_entity_with_suffix_validator(self):
        """Test entity extraction with Validator suffix"""
        template = CodeTemplate(
            name="UpdateProductValidator.cs",
            original_path="src/UseCases/Products/UpdateProductValidator.cs",
            template_path="templates/UseCases/Products/UpdateProductValidator.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'Product'

    def test_identify_entity_plural_to_singular(self):
        """Test entity singularization from plural"""
        template = CodeTemplate(
            name="GetProducts.cs",
            original_path="src/UseCases/Products/GetProducts.cs",
            template_path="templates/UseCases/Products/GetProducts.template",
            content="namespace {{ProjectName}}.UseCases.Products;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'Product'

    def test_identify_entity_categories_to_category(self):
        """Test entity singularization (ies → y)"""
        template = CodeTemplate(
            name="GetCategories.cs",
            original_path="src/UseCases/Categories/GetCategories.cs",
            template_path="templates/UseCases/Categories/GetCategories.template",
            content="namespace {{ProjectName}}.UseCases.Categories;"
        )

        matcher = CRUDPatternMatcher()
        entity = matcher.identify_entity(template)

        assert entity == 'Category'


class TestOperationExtractor:
    """Test operation extraction and grouping"""

    @pytest.fixture
    def sample_templates(self):
        """Create sample template collection"""
        templates = [
            CodeTemplate(
                name="CreateProduct.cs",
                original_path="src/UseCases/Products/CreateProduct.cs",
                template_path="templates/UseCases/Products/CreateProduct.template",
                content=""
            ),
            CodeTemplate(
                name="GetProduct.cs",
                original_path="src/UseCases/Products/GetProduct.cs",
                template_path="templates/UseCases/Products/GetProduct.template",
                content=""
            ),
            CodeTemplate(
                name="UpdateProduct.cs",
                original_path="src/UseCases/Products/UpdateProduct.cs",
                template_path="templates/UseCases/Products/UpdateProduct.template",
                content=""
            ),
            CodeTemplate(
                name="ProductEndpoint.cs",
                original_path="src/Web/Endpoints/ProductEndpoint.cs",
                template_path="templates/Web/Endpoints/ProductEndpoint.template",
                content=""
            ),
            CodeTemplate(
                name="CreateUser.cs",
                original_path="src/UseCases/Users/CreateUser.cs",
                template_path="templates/UseCases/Users/CreateUser.template",
                content=""
            ),
            CodeTemplate(
                name="GetUser.cs",
                original_path="src/UseCases/Users/GetUser.cs",
                template_path="templates/UseCases/Users/GetUser.template",
                content=""
            )
        ]

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type={}
        )

    def test_extract_operations_by_layer(self, sample_templates):
        """Test extraction of operations grouped by layer"""
        extractor = OperationExtractor()
        layer_operations = extractor.extract_operations_by_layer(sample_templates)

        assert 'UseCases' in layer_operations
        assert 'Create' in layer_operations['UseCases']
        assert 'Read' in layer_operations['UseCases']
        assert 'Update' in layer_operations['UseCases']

    def test_group_by_entity(self, sample_templates):
        """Test grouping templates by entity"""
        extractor = OperationExtractor()
        entity_groups = extractor.group_by_entity(sample_templates)

        assert 'Product' in entity_groups
        assert 'User' in entity_groups

        assert 'Create' in entity_groups['Product']
        assert 'Read' in entity_groups['Product']
        assert 'Update' in entity_groups['Product']

        assert 'Create' in entity_groups['User']
        assert 'Read' in entity_groups['User']

    def test_extract_entities(self, sample_templates):
        """Test extraction of unique entity names"""
        extractor = OperationExtractor()
        entities = extractor.extract_entities(sample_templates)

        assert 'Product' in entities
        assert 'User' in entities
        assert len(entities) == 2

    def test_extract_operations_for_entity(self, sample_templates):
        """Test extraction of operations for specific entity"""
        extractor = OperationExtractor()

        product_ops = extractor.extract_operations_for_entity(sample_templates, 'Product')
        assert 'Create' in product_ops
        assert 'Read' in product_ops
        assert 'Update' in product_ops

        user_ops = extractor.extract_operations_for_entity(sample_templates, 'User')
        assert 'Create' in user_ops
        assert 'Read' in user_ops
        assert 'Update' not in user_ops

    def test_extract_entities_by_layer(self, sample_templates):
        """Test extraction of entities grouped by layer"""
        extractor = OperationExtractor()
        layer_entities = extractor.extract_entities_by_layer(sample_templates)

        assert 'UseCases' in layer_entities
        assert 'Product' in layer_entities['UseCases']
        assert 'User' in layer_entities['UseCases']
