"""
Pattern Matcher for Template Completeness Validation

Provides pattern matching utilities to identify CRUD operations, layers,
and entities from template file paths and names.

TASK-040: Phase 1 - Completeness Validation Layer
"""

import re
import importlib
from typing import Dict, Set, Optional, List
from pathlib import Path

# Import models using importlib to bypass 'global' keyword issue
_models = importlib.import_module('installer.global.lib.template_generator.models')
CodeTemplate = _models.CodeTemplate
TemplateCollection = _models.TemplateCollection


# CRUD Operation Patterns (case-insensitive)
CRUD_PATTERNS = {
    'Create': ['Create', 'Add', 'Insert', 'New', 'Post'],
    'Read': ['Get', 'Query', 'List', 'Find', 'Fetch', 'Read', 'Retrieve'],
    'Update': ['Update', 'Edit', 'Modify', 'Put', 'Patch'],
    'Delete': ['Delete', 'Remove', 'Destroy'],
    'List': ['List', 'GetAll', 'Query', 'Search']  # Special case of Read
}

# Layer Detection Patterns
LAYER_PATTERNS = {
    'Domain': ['/Core/', '/Domain/', 'Domain.', '.Core.', 'core/', 'domain/'],
    'UseCases': ['/UseCases/', '/Application/', 'UseCases.', 'Application.', 'usecases/', 'application/'],
    'Web': ['/Web/', '/Api/', '/Endpoints/', 'Web.', 'Api.', 'Endpoints.', 'web/', 'api/', 'endpoints/'],
    'Infrastructure': ['/Infrastructure/', '/Persistence/', 'Infrastructure.', 'Persistence.', 'infrastructure/', 'persistence/']
}


class CRUDPatternMatcher:
    """
    Identifies CRUD operations, layers, and entities from template paths/names.

    Provides static methods for pattern matching without requiring state.
    """

    @staticmethod
    def identify_crud_operation(template: CodeTemplate) -> Optional[str]:
        """
        Identify CRUD operation from template file path or name.

        Args:
            template: CodeTemplate to analyze

        Returns:
            Operation name ('Create', 'Read', 'Update', 'Delete', 'List') or None

        Examples:
            - 'CreateProduct.cs' → 'Create'
            - 'GetProduct.cs' → 'Read'
            - 'UpdateProduct.cs' → 'Update'
            - 'DeleteProduct.cs' → 'Delete'
            - 'ListProducts.cs' → 'List'
        """
        # Combine file name and path for matching
        search_text = f"{template.name} {template.template_path} {template.original_path}"
        search_text_lower = search_text.lower()

        filename_lower = template.name.lower()

        # Special case: Check 'List' first before other Read operations
        # because 'List' is also in Read patterns
        if filename_lower.startswith('list'):
            return 'List'

        # Check each CRUD operation pattern
        for operation, patterns in CRUD_PATTERNS.items():
            # Skip List since we already handled it
            if operation == 'List':
                continue

            for pattern in patterns:
                # Check if pattern appears at the start of filename (case-insensitive)
                # Example: 'Create' matches 'CreateProduct.cs' or 'create_product.py'
                # But not 'MyCreateHandler.cs' (Create not at start)
                pattern_lower = pattern.lower()

                if filename_lower.startswith(pattern_lower):
                    return operation

                # Also check in path for cases like '/Create/' or '/create-'
                if f'/{pattern_lower}' in search_text_lower or f'-{pattern_lower}' in search_text_lower or f'_{pattern_lower}' in search_text_lower:
                    return operation

        return None

    @staticmethod
    def identify_layer(template: CodeTemplate) -> Optional[str]:
        """
        Identify architectural layer from template file path.

        Args:
            template: CodeTemplate to analyze

        Returns:
            Layer name ('Domain', 'UseCases', 'Web', 'Infrastructure') or None

        Examples:
            - 'src/UseCases/Products/CreateProduct.cs' → 'UseCases'
            - 'src/Web/Endpoints/ProductEndpoints.cs' → 'Web'
            - 'src/Domain/Products/Product.cs' → 'Domain'
        """
        # Check template_path and original_path
        search_paths = [template.template_path, template.original_path]

        for layer, patterns in LAYER_PATTERNS.items():
            for pattern in patterns:
                for path in search_paths:
                    if pattern in path:
                        return layer

        return None

    @staticmethod
    def identify_entity(template: CodeTemplate) -> Optional[str]:
        """
        Extract entity name from template file path or name.

        Uses heuristics to identify the entity being operated on.

        Args:
            template: CodeTemplate to analyze

        Returns:
            Entity name (singular form) or None

        Examples:
            - 'CreateProduct.cs' → 'Product'
            - 'GetUsers.cs' → 'User'
            - 'UpdateOrderValidator.cs' → 'Order'

        Strategy:
            1. Remove operation prefix (Create, Get, Update, Delete)
            2. Remove common suffixes (Request, Response, Validator, Handler, Query, Command)
            3. Singularize plural forms if possible
            4. Return remaining token
        """
        # Start with the file name (without extension)
        name = Path(template.name).stem

        # Remove operation prefixes
        for operation, patterns in CRUD_PATTERNS.items():
            for pattern in patterns:
                if name.startswith(pattern):
                    name = name[len(pattern):]
                    break

        # Remove common suffixes
        suffixes = ['Request', 'Response', 'Validator', 'Handler', 'Query', 'Command',
                   'Dto', 'ViewModel', 'Model', 'Endpoint', 'Controller', 'Service']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break

        # Attempt to singularize (simple heuristic)
        if name.endswith('ies'):
            # Categories → Category
            name = name[:-3] + 'y'
        elif name.endswith('s') and not name.endswith('ss'):
            # Products → Product (but not Address → Addres)
            name = name[:-1]

        # Return None if we couldn't extract a meaningful entity name
        if len(name) < 2:
            return None

        return name


class OperationExtractor:
    """
    Extracts and groups operations from a template collection.

    Provides methods to analyze template collections and identify patterns.
    """

    def __init__(self, pattern_matcher: CRUDPatternMatcher = None):
        """
        Initialize operation extractor.

        Args:
            pattern_matcher: Pattern matcher instance (defaults to CRUDPatternMatcher)
        """
        self.pattern_matcher = pattern_matcher or CRUDPatternMatcher()

    def extract_operations_by_layer(self, templates: TemplateCollection) -> Dict[str, Set[str]]:
        """
        Extract operations grouped by layer.

        Args:
            templates: TemplateCollection to analyze

        Returns:
            Dictionary mapping layer name to set of operations

        Example:
            {
                'UseCases': {'Create', 'Read', 'Update'},
                'Web': {'Create', 'Read'},
                'Domain': {'Read'}
            }
        """
        layer_operations = {}

        for template in templates.templates:
            layer = self.pattern_matcher.identify_layer(template)
            operation = self.pattern_matcher.identify_crud_operation(template)

            if layer and operation:
                if layer not in layer_operations:
                    layer_operations[layer] = set()
                layer_operations[layer].add(operation)

        return layer_operations

    def group_by_entity(self, templates: TemplateCollection) -> Dict[str, Dict[str, List[CodeTemplate]]]:
        """
        Group templates by entity and operation.

        Args:
            templates: TemplateCollection to analyze

        Returns:
            Dictionary mapping entity name to operations to templates

        Example:
            {
                'Product': {
                    'Create': [CreateProduct.cs, CreateProductRequest.cs],
                    'Read': [GetProduct.cs, GetProductQuery.cs],
                    'Update': [UpdateProduct.cs]
                },
                'User': {
                    'Create': [CreateUser.cs],
                    'Read': [GetUser.cs]
                }
            }
        """
        entity_groups = {}

        for template in templates.templates:
            entity = self.pattern_matcher.identify_entity(template)
            operation = self.pattern_matcher.identify_crud_operation(template)

            if entity and operation:
                if entity not in entity_groups:
                    entity_groups[entity] = {}

                if operation not in entity_groups[entity]:
                    entity_groups[entity][operation] = []

                entity_groups[entity][operation].append(template)

        return entity_groups

    def extract_entities(self, templates: TemplateCollection) -> Set[str]:
        """
        Extract unique entity names from template collection.

        Args:
            templates: TemplateCollection to analyze

        Returns:
            Set of unique entity names

        Example:
            {'Product', 'User', 'Order', 'Category'}
        """
        entities = set()

        for template in templates.templates:
            entity = self.pattern_matcher.identify_entity(template)
            if entity:
                entities.add(entity)

        return entities

    def extract_operations_for_entity(
        self,
        templates: TemplateCollection,
        entity: str
    ) -> Set[str]:
        """
        Extract operations present for a specific entity.

        Args:
            templates: TemplateCollection to analyze
            entity: Entity name to filter by

        Returns:
            Set of operation names present for this entity

        Example:
            extract_operations_for_entity(templates, 'Product')
            → {'Create', 'Read', 'Update'}
        """
        operations = set()

        for template in templates.templates:
            template_entity = self.pattern_matcher.identify_entity(template)
            operation = self.pattern_matcher.identify_crud_operation(template)

            if template_entity == entity and operation:
                operations.add(operation)

        return operations

    def extract_entities_by_layer(
        self,
        templates: TemplateCollection
    ) -> Dict[str, Set[str]]:
        """
        Extract entities grouped by layer.

        Args:
            templates: TemplateCollection to analyze

        Returns:
            Dictionary mapping layer name to set of entity names

        Example:
            {
                'UseCases': {'Product', 'User', 'Order'},
                'Web': {'Product', 'User'},
                'Domain': {'Product', 'User', 'Order', 'Category'}
            }
        """
        layer_entities = {}

        for template in templates.templates:
            layer = self.pattern_matcher.identify_layer(template)
            entity = self.pattern_matcher.identify_entity(template)

            if layer and entity:
                if layer not in layer_entities:
                    layer_entities[layer] = set()
                layer_entities[layer].add(entity)

        return layer_entities
