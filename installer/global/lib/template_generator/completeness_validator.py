"""
Completeness Validator for Template Generation

Validates CRUD operation completeness, layer symmetry, and pattern consistency
in generated template collections. Provides auto-fix recommendations and
template generation capabilities.

TASK-040: Phase 1 - Completeness Validation Layer
"""

from datetime import datetime
from typing import List, Dict, Set, Optional
import logging
import importlib

# Import modules using importlib to bypass 'global' keyword issue
_models = importlib.import_module('installer.global.lib.template_generator.models')
_pattern_matcher = importlib.import_module('installer.global.lib.template_generator.pattern_matcher')

CodeTemplate = _models.CodeTemplate
TemplateCollection = _models.TemplateCollection
CompletenessIssue = _models.CompletenessIssue
TemplateRecommendation = _models.TemplateRecommendation
ValidationReport = _models.ValidationReport
CRUDPatternMatcher = _pattern_matcher.CRUDPatternMatcher
OperationExtractor = _pattern_matcher.OperationExtractor


logger = logging.getLogger(__name__)


# Expected CRUD operations for complete entity
EXPECTED_CRUD_OPERATIONS = {'Create', 'Read', 'Update', 'Delete'}

# Operations that should have layer symmetry (UseCases ↔ Web)
SYMMETRIC_OPERATIONS = {'Create', 'Read', 'Update', 'Delete', 'List'}


class CompletenessValidator:
    """
    Validates template collection completeness and provides auto-fix recommendations.

    Phase 5.5 validation layer that ensures generated templates include complete
    CRUD operations, symmetric layer coverage, and consistent patterns.
    """

    # TASK-FIX-6855 Issue 6: Template suffix constant (DRY principle)
    TEMPLATE_SUFFIX = '.template'

    def __init__(
        self,
        pattern_matcher: CRUDPatternMatcher = None,
        operation_extractor: OperationExtractor = None
    ):
        """
        Initialize completeness validator.

        Args:
            pattern_matcher: Pattern matcher instance (defaults to CRUDPatternMatcher)
            operation_extractor: Operation extractor instance (defaults to OperationExtractor)
        """
        self.pattern_matcher = pattern_matcher or CRUDPatternMatcher()
        self.operation_extractor = operation_extractor or OperationExtractor(self.pattern_matcher)

    def validate(
        self,
        templates: TemplateCollection,
        analysis: any = None
    ) -> ValidationReport:
        """
        Validate completeness of template collection.

        Performs three types of validation:
        1. CRUD completeness (all operations present for each entity)
        2. Layer symmetry (UseCases ↔ Web consistency)
        3. Pattern consistency (naming, structure)

        Args:
            templates: TemplateCollection to validate
            analysis: CodebaseAnalysis for context (optional)

        Returns:
            ValidationReport with issues, recommendations, and False Negative score
        """
        logger.info(f"Validating template collection ({templates.total_count} templates)")

        issues = []

        # Validation 1: Check CRUD completeness
        crud_issues = self._check_crud_completeness(templates)
        issues.extend(crud_issues)
        logger.debug(f"CRUD completeness check: {len(crud_issues)} issues found")

        # Validation 2: Check layer symmetry
        symmetry_issues = self._check_layer_symmetry(templates)
        issues.extend(symmetry_issues)
        logger.debug(f"Layer symmetry check: {len(symmetry_issues)} issues found")

        # Generate recommendations for missing templates
        recommendations = self._generate_recommendations(issues, templates)
        logger.debug(f"Generated {len(recommendations)} recommendations")

        # Calculate False Negative score
        templates_expected = templates.total_count + len(recommendations)
        fn_score = self._calculate_false_negative_score(
            templates_generated=templates.total_count,
            templates_expected=templates_expected
        )

        # Build validation report
        report = ValidationReport(
            is_complete=len(issues) == 0,
            issues=issues,
            recommended_templates=recommendations,
            false_negative_score=fn_score,
            templates_generated=templates.total_count,
            templates_expected=templates_expected,
            validation_timestamp=datetime.now().isoformat()
        )

        logger.info(
            f"Validation complete: {len(issues)} issues, "
            f"{len(recommendations)} recommendations, "
            f"FN score: {fn_score:.2f}/10"
        )

        return report

    def _check_crud_completeness(self, templates: TemplateCollection) -> List[CompletenessIssue]:
        """
        Check if all CRUD operations are present for each entity.

        Expected operations: Create, Read, Update, Delete

        Args:
            templates: TemplateCollection to check

        Returns:
            List of CompletenessIssue for missing operations
        """
        issues = []

        # Group templates by entity
        entity_groups = self.operation_extractor.group_by_entity(templates)

        for entity, operations_dict in entity_groups.items():
            present_operations = set(operations_dict.keys())
            missing_operations = EXPECTED_CRUD_OPERATIONS - present_operations

            for operation in missing_operations:
                issue = CompletenessIssue(
                    severity='high',
                    type='incomplete_crud',
                    message=f"{entity} entity missing {operation} operation",
                    entity=entity,
                    operation=operation,
                    layer=None,  # Will be determined in recommendations
                    missing_files=[]  # Will be populated in recommendations
                )
                issues.append(issue)
                logger.debug(f"Incomplete CRUD: {entity} missing {operation}")

        return issues

    def _check_layer_symmetry(self, templates: TemplateCollection) -> List[CompletenessIssue]:
        """
        Check if operations exist in both UseCases and Web layers.

        Example issue: UpdateProduct.cs exists in UseCases but not in Web

        Args:
            templates: TemplateCollection to check

        Returns:
            List of CompletenessIssue for layer asymmetry
        """
        issues = []

        # Extract operations by layer
        layer_operations = self.operation_extractor.extract_operations_by_layer(templates)

        # Get operations in UseCases and Web
        usecases_ops = layer_operations.get('UseCases', set())
        web_ops = layer_operations.get('Web', set())

        # Check for asymmetry: operations in UseCases but not Web
        usecases_only = usecases_ops - web_ops
        for operation in usecases_only:
            if operation in SYMMETRIC_OPERATIONS:
                issue = CompletenessIssue(
                    severity='high',
                    type='layer_asymmetry',
                    message=f"{operation} operation exists in UseCases but not in Web layer",
                    entity=None,  # Not entity-specific
                    operation=operation,
                    layer='Web',  # Missing layer
                    missing_files=[]
                )
                issues.append(issue)
                logger.debug(f"Layer asymmetry: {operation} in UseCases but not Web")

        # Check for asymmetry: operations in Web but not UseCases
        web_only = web_ops - usecases_ops
        for operation in web_only:
            if operation in SYMMETRIC_OPERATIONS:
                issue = CompletenessIssue(
                    severity='medium',
                    type='layer_asymmetry',
                    message=f"{operation} operation exists in Web but not in UseCases layer",
                    entity=None,
                    operation=operation,
                    layer='UseCases',  # Missing layer
                    missing_files=[]
                )
                issues.append(issue)
                logger.debug(f"Layer asymmetry: {operation} in Web but not UseCases")

        return issues

    def _generate_recommendations(
        self,
        issues: List[CompletenessIssue],
        templates: TemplateCollection
    ) -> List[TemplateRecommendation]:
        """
        Generate recommendations for fixing completeness issues.

        Args:
            issues: List of completeness issues
            templates: TemplateCollection for context

        Returns:
            List of TemplateRecommendation with auto-generation details
        """
        recommendations = []

        for issue in issues:
            recommendation = self._create_recommendation_for_issue(issue, templates)
            if recommendation:
                recommendations.append(recommendation)

        return recommendations

    def _create_recommendation_for_issue(
        self,
        issue: CompletenessIssue,
        templates: TemplateCollection
    ) -> Optional[TemplateRecommendation]:
        """
        Create a recommendation for a specific issue.

        Args:
            issue: CompletenessIssue to address
            templates: TemplateCollection for context

        Returns:
            TemplateRecommendation or None if cannot recommend
        """
        if issue.type == 'incomplete_crud' and issue.entity and issue.operation:
            # Find reference template for this entity (prefer same operation type)
            reference = self._find_reference_template(
                entity=issue.entity,
                operation=issue.operation,
                templates=templates
            )

            if reference:
                # Estimate file path for missing template
                estimated_path = self._estimate_file_path(
                    entity=issue.entity,
                    operation=issue.operation,
                    reference=reference
                )

                return TemplateRecommendation(
                    file_path=estimated_path,
                    reason=f"Missing {issue.operation} operation for {issue.entity} entity",
                    can_auto_generate=True,
                    reference_template=reference.template_path,
                    estimated_confidence=0.85
                )

        elif issue.type == 'layer_asymmetry' and issue.operation and issue.layer:
            # For layer asymmetry, recommend adding to missing layer
            # This is more complex and may require analysis of existing patterns
            # For now, return a recommendation but mark as cannot auto-generate
            return TemplateRecommendation(
                file_path=f"{issue.layer}/{issue.operation}Endpoint.cs",
                reason=f"Add {issue.operation} endpoint to {issue.layer} layer for symmetry",
                can_auto_generate=False,  # Layer asymmetry is complex
                reference_template=None,
                estimated_confidence=0.60
            )

        return None

    def _find_reference_template(
        self,
        entity: str,
        operation: str,
        templates: TemplateCollection
    ) -> Optional[CodeTemplate]:
        """
        Find a reference template for auto-generation.

        Strategy:
        1. Find template for same entity with different operation
        2. Prefer similar operations (Create ↔ Update, Read ↔ Delete)

        Args:
            entity: Entity name
            operation: Target operation
            templates: TemplateCollection to search

        Returns:
            CodeTemplate to use as reference or None
        """
        # Preference order for reference operations
        operation_preferences = {
            'Create': ['Update', 'Read', 'Delete'],
            'Update': ['Create', 'Read', 'Delete'],
            'Read': ['Create', 'Update', 'Delete'],
            'Delete': ['Update', 'Create', 'Read']
        }

        preferred_ops = operation_preferences.get(operation, ['Create', 'Read', 'Update', 'Delete'])

        # Try to find template with preferred operations
        for pref_op in preferred_ops:
            for template in templates.templates:
                template_entity = self.pattern_matcher.identify_entity(template)
                template_operation = self.pattern_matcher.identify_crud_operation(template)

                if template_entity == entity and template_operation == pref_op:
                    return template

        # Fallback: return any template for this entity
        for template in templates.templates:
            template_entity = self.pattern_matcher.identify_entity(template)
            if template_entity == entity:
                return template

        return None

    def _separate_template_suffix(self, filename: str) -> tuple:
        """Separate .template suffix from actual filename.

        TASK-FIX-6855 Issue 6: Correctly handle template suffix (DRY principle).

        Args:
            filename: Filename to process

        Returns:
            Tuple of (actual_filename, template_suffix)

        Examples:
            - 'file.js.template' → ('file.js', '.template')
            - 'file.py' → ('file.py', '')
        """
        if filename.endswith(self.TEMPLATE_SUFFIX):
            actual = filename[:-len(self.TEMPLATE_SUFFIX)]
            return actual, self.TEMPLATE_SUFFIX
        return filename, ''

    def _estimate_file_path(
        self,
        entity: str,
        operation: str,
        reference: CodeTemplate
    ) -> str:
        """
        Estimate file path for missing template based on reference.

        TASK-FIX-6855 Issue 6: Rewritten to correctly handle template suffix using helper.

        Preserves full compound extensions (e.g., .js.template, .ts.template)
        and follows the naming pattern from the reference file.

        Args:
            entity: Entity name
            operation: Operation name
            reference: Reference template

        Returns:
            Estimated file path with correct extension and naming pattern
        """
        from pathlib import Path
        ref_path = Path(reference.template_path)
        directory = ref_path.parent

        # TASK-FIX-6855 Issue 6: Use helper to separate template suffix
        ref_name = ref_path.name
        actual_filename, template_suffix = self._separate_template_suffix(ref_name)

        # Now work with the actual filename (without .template)
        actual_path = Path(actual_filename)

        # Get the file extension(s) from actual filename
        # For 'file.js' → '.js', for 'file.test.ts' → '.test.ts'
        file_suffixes = ''.join(actual_path.suffixes)

        # Get base name without any extensions
        base_name = actual_path.name
        if file_suffixes:
            base_name = base_name[:-len(file_suffixes)]

        # Extract the entity part from reference to understand the pattern
        ref_operation = self.pattern_matcher.identify_crud_operation(reference)

        # Find the actual prefix used in the reference file
        actual_prefix = None
        if ref_operation:
            # Get CRUD_PATTERNS to find the actual prefix used
            patterns_for_operation = _pattern_matcher.CRUD_PATTERNS.get(ref_operation, [ref_operation])
            for pattern in patterns_for_operation:
                if base_name.startswith(pattern):
                    actual_prefix = pattern
                    break

        if actual_prefix:
            # Get the separator used (if any) between operation and entity
            remainder = base_name[len(actual_prefix):]
            if remainder.startswith('-'):
                # Hyphenated pattern: "Get-user" -> "Update-user"
                entity_part = remainder[1:]  # Remove the hyphen
                new_base = f"{operation}-{entity_part}"
            elif remainder.startswith('_'):
                # Underscore pattern: "Get_user" -> "Update_user"
                entity_part = remainder[1:]
                new_base = f"{operation}_{entity_part}"
            else:
                # No separator or PascalCase: "GetUser" -> "UpdateUser"
                new_base = f"{operation}{entity}"
        else:
            # Fallback: use operation + entity
            new_base = f"{operation}{entity}"

        # Reconstruct full filename: base + file_suffixes + template_suffix
        new_filename = f"{new_base}{file_suffixes}{template_suffix}"

        return str(directory / new_filename)

    def _calculate_false_negative_score(
        self,
        templates_generated: int,
        templates_expected: int
    ) -> float:
        """
        Calculate False Negative score: (generated / expected) × 10

        Target: ≥8.0/10

        Args:
            templates_generated: Number of templates actually generated
            templates_expected: Number of templates that should have been generated

        Returns:
            Score from 0-10
        """
        if templates_expected == 0:
            return 10.0

        score = (templates_generated / templates_expected) * 10.0
        return min(10.0, max(0.0, score))  # Clamp to 0-10 range

    def generate_missing_templates(
        self,
        recommendations: List[TemplateRecommendation],
        existing_templates: TemplateCollection
    ) -> List[CodeTemplate]:
        """
        Auto-generate missing templates by cloning reference templates.

        Strategy:
        1. Find reference template (e.g., Create.cs for Update.cs)
        2. Clone template content
        3. Replace operation names
        4. Update HTTP methods/routes (if applicable)
        5. Preserve entity placeholders

        Args:
            recommendations: List of template recommendations
            existing_templates: Existing template collection for reference

        Returns:
            List of newly generated CodeTemplate objects
        """
        generated_templates = []

        for recommendation in recommendations:
            if not recommendation.can_auto_generate or not recommendation.reference_template:
                logger.debug(f"Skipping auto-generation for {recommendation.file_path} (not auto-generable)")
                continue

            # Find reference template
            reference = self._find_template_by_path(
                path=recommendation.reference_template,
                templates=existing_templates
            )

            if not reference:
                logger.warning(f"Reference template not found: {recommendation.reference_template}")
                continue

            # Generate new template
            new_template = self._clone_and_adapt_template(
                reference=reference,
                target_path=recommendation.file_path
            )

            if new_template:
                generated_templates.append(new_template)
                logger.info(f"Auto-generated template: {new_template.template_path}")

        logger.info(f"Auto-generated {len(generated_templates)} templates")
        return generated_templates

    def _find_template_by_path(
        self,
        path: str,
        templates: TemplateCollection
    ) -> Optional[CodeTemplate]:
        """
        Find template by path in collection.

        Args:
            path: Template path to find
            templates: TemplateCollection to search

        Returns:
            CodeTemplate if found, None otherwise
        """
        for template in templates.templates:
            if template.template_path == path or template.original_path == path:
                return template
        return None

    def _clone_and_adapt_template(
        self,
        reference: CodeTemplate,
        target_path: str
    ) -> Optional[CodeTemplate]:
        """
        Clone reference template and adapt for target operation.

        Args:
            reference: Reference template to clone
            target_path: Target file path for new template

        Returns:
            New CodeTemplate or None if generation fails
        """
        from pathlib import Path

        # Extract operation names from paths
        ref_operation = self.pattern_matcher.identify_crud_operation(reference)
        target_filename = Path(target_path).name
        target_operation = self._extract_operation_from_filename(target_filename)

        if not ref_operation or not target_operation:
            logger.warning(f"Could not extract operations for cloning: {target_path}")
            return None

        # Clone content and replace operation names
        new_content = self._replace_operation_in_content(
            content=reference.content,
            old_operation=ref_operation,
            new_operation=target_operation
        )

        # Create new template
        new_template = CodeTemplate(
            schema_version=reference.schema_version,
            name=target_filename,
            original_path=target_path,  # Not a real original path (generated)
            template_path=target_path,
            content=new_content,
            placeholders=reference.placeholders,  # Preserve placeholders
            file_type=reference.file_type,
            language=reference.language,
            purpose=f"Auto-generated {target_operation} operation template",
            quality_score=reference.quality_score * 0.9 if reference.quality_score else None,  # Slightly lower quality
            patterns=reference.patterns
        )

        return new_template

    def _extract_operation_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract operation name from filename.

        Args:
            filename: File name to parse

        Returns:
            Operation name or None
        """
        from pathlib import Path

        # Remove extension
        name = Path(filename).stem

        # Check against known operations
        for operation, patterns in {
            'Create': ['Create', 'Add', 'Insert'],
            'Read': ['Get', 'Query', 'Find'],
            'Update': ['Update', 'Edit', 'Modify'],
            'Delete': ['Delete', 'Remove']
        }.items():
            for pattern in patterns:
                if name.startswith(pattern):
                    return operation

        return None

    def _replace_operation_in_content(
        self,
        content: str,
        old_operation: str,
        new_operation: str
    ) -> str:
        """
        Replace operation names in template content.

        Handles case variations:
        - PascalCase: Create → Update
        - camelCase: create → update
        - lowercase: create → update
        - UPPERCASE: CREATE → UPDATE

        Args:
            content: Template content
            old_operation: Operation to replace
            new_operation: New operation name

        Returns:
            Updated content
        """
        import re

        # Replace various case styles
        replacements = [
            (old_operation, new_operation),  # PascalCase
            (old_operation.lower(), new_operation.lower()),  # lowercase
            (old_operation.upper(), new_operation.upper()),  # UPPERCASE
            (old_operation[0].lower() + old_operation[1:], new_operation[0].lower() + new_operation[1:])  # camelCase
        ]

        result = content
        for old, new in replacements:
            result = result.replace(old, new)

        return result
