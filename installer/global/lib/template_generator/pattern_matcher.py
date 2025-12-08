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

        TASK-FIX-6855 Issue 5: Enhanced to prevent false positives for standalone utility files.

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
            - 'query.js' → None (TASK-FIX-6855: utility file, not CRUD)
            - 'firebase.js' → None (TASK-FIX-6855: utility file, not CRUD)
        """
        # Combine file name and path for matching
        search_text = f"{template.name} {template.template_path} {template.original_path}"
        search_text_lower = search_text.lower()

        # Get filename without extension for pattern matching
        filename_stem = Path(template.name).stem
        filename_stem_lower = filename_stem.lower()

        # TASK-FIX-6855 Issue 5: Skip standalone utility files
        # Pattern must be followed by something (entity name, separator, etc.)
        # Patterns like 'query', 'list', 'search' alone are utility files, not CRUD operations

        # Special case: Check 'List' first before other Read operations
        # because 'List' is also in Read patterns
        # But must be followed by something (ListUsers, not just List or list)
        if filename_stem_lower.startswith('list') and len(filename_stem_lower) > 4:
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
                pattern_len = len(pattern_lower)

                # TASK-FIX-6855 Issue 5: Pattern must be followed by something
                # 'query' alone is not CRUD, but 'QueryUsers' is
                if filename_stem_lower.startswith(pattern_lower) and len(filename_stem_lower) > pattern_len:
                    # Check what follows the pattern
                    remainder = filename_stem_lower[pattern_len:]
                    # Valid separators: PascalCase (uppercase), hyphen, underscore
                    if remainder[0].isupper() or remainder.startswith('-') or remainder.startswith('_'):
                        return operation
                    # Also accept if it's all lowercase but has something after
                    # This handles cases like 'createuser.js' → Create operation
                    elif remainder and remainder[0].isalpha():
                        return operation

                # TASK-FIX-6855 Issue 5: Skip path matching for short patterns that could be utility files
                # Patterns like 'Query', 'List', 'Search' in paths could be false positives
                # Only check path for longer, less ambiguous patterns like '/Create/' or '/Update/'
                if pattern_len >= 6:  # Only match unambiguous patterns in paths
                    # Also check in path for cases like '/Create/' or '/create-'
                    if f'/{pattern_lower}/' in search_text_lower or f'-{pattern_lower}' in search_text_lower or f'_{pattern_lower}' in search_text_lower:
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

        TASK-FIX-6855 Issue 5: Guard clause to check if this is a CRUD file first.

        Args:
            template: CodeTemplate to analyze

        Returns:
            Entity name (singular form) or None

        Examples:
            - 'CreateProduct.cs' → 'Product'
            - 'GetUsers.cs' → 'User'
            - 'UpdateOrderValidator.cs' → 'Order'

        Strategy:
            1. Check if this is a CRUD file first
            2. Remove operation prefix (Create, Get, Update, Delete)
            3. Remove common suffixes (Request, Response, Validator, Handler, Query, Command)
            4. Singularize plural forms if possible
            5. Return remaining token
        """
        # TASK-FIX-6855 Issue 5: Guard clause - only process CRUD files
        operation = CRUDPatternMatcher.identify_crud_operation(template)
        if operation is None:
            return None  # Not a CRUD file - don't treat as entity

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
