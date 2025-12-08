"""
Test Suite for TASK-FIX-6855: Template Create Validation Fixes

Tests for all 6 issues addressed in TASK-FIX-6855:
1. Framework schema - Support both simple strings and FrameworkInfo objects
2. Extended layer patterns - Detect 14 extended layer patterns
3. Entity detection guard clause - Prevent false positives for utility files
4. Template naming fix - Correct suffix handling for compound extensions

Target: 80%+ line coverage, 75%+ branch coverage
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any

# Import modules under test
from lib.codebase_analyzer.models import (
    FrameworkInfo,
    TechnologyInfo,
    ConfidenceScore,
    ConfidenceLevel
)
from lib.codebase_analyzer.agent_invoker import (
    HeuristicAnalyzer,
)
from lib.template_generator.pattern_matcher import (
    CRUDPatternMatcher,
)
from lib.template_generator.completeness_validator import (
    CompletenessValidator,
)
from lib.template_generator.models import (
    CodeTemplate,
)


# =============================================================================
# ISSUE 1: Framework Schema Tests
# =============================================================================

class TestFrameworkInfoSchema:
    """Test FrameworkInfo model and backward compatibility."""

    def test_framework_info_basic(self):
        """Test basic FrameworkInfo creation."""
        fw = FrameworkInfo(name="FastAPI")
        assert fw.name == "FastAPI"
        assert fw.purpose is None
        assert fw.version is None

    def test_framework_info_with_metadata(self):
        """Test FrameworkInfo with full metadata."""
        fw = FrameworkInfo(
            name="React",
            purpose="Frontend UI library",
            version="18.2.0"
        )
        assert fw.name == "React"
        assert fw.purpose == "Frontend UI library"
        assert fw.version == "18.2.0"

    def test_technology_info_simple_strings(self):
        """Test TechnologyInfo with simple string frameworks (backward compatible)."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI", "React"],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.frameworks == ["FastAPI", "React"]
        assert tech.framework_list == ["FastAPI", "React"]

    def test_technology_info_framework_objects(self):
        """Test TechnologyInfo with FrameworkInfo objects."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=[
                FrameworkInfo(name="FastAPI", purpose="Web API"),
                FrameworkInfo(name="React", purpose="Frontend")
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.frameworks) == 2
        assert isinstance(tech.frameworks[0], FrameworkInfo)
        assert tech.framework_list == ["FastAPI", "React"]

    def test_technology_info_mixed_frameworks(self):
        """Test TechnologyInfo with mixed string and FrameworkInfo objects."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=[
                "FastAPI",
                FrameworkInfo(name="React", purpose="Frontend"),
                "PostgreSQL"
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.frameworks) == 3
        assert tech.framework_list == ["FastAPI", "React", "PostgreSQL"]

    def test_framework_list_property_iteration(self):
        """Test that framework_list property supports iteration (backward compatibility)."""
        tech = TechnologyInfo(
            primary_language="TypeScript",
            frameworks=[
                FrameworkInfo(name="Next.js"),
                "TailwindCSS"
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.MEDIUM, percentage=85.0)
        )

        # Iterate over framework_list
        names = []
        for name in tech.framework_list:
            names.append(name)

        assert names == ["Next.js", "TailwindCSS"]

    def test_empty_frameworks_list(self):
        """Test TechnologyInfo with empty frameworks list."""
        tech = TechnologyInfo(
            primary_language="Go",
            frameworks=[],
            confidence=ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)
        )
        assert tech.frameworks == []
        assert tech.framework_list == []


# =============================================================================
# ISSUE 4: Extended Layer Pattern Detection Tests
# =============================================================================

class TestExtendedLayerPatterns:
    """Test extended layer pattern detection in HeuristicAnalyzer."""

    @pytest.fixture
    def temp_codebase(self, tmp_path):
        """Create temporary codebase with various directory patterns."""
        # Create directories matching EXTENDED_LAYER_PATTERNS
        patterns = [
            "routes/user_routes.py",
            "controllers/auth_controller.py",
            "views/index.html",
            "endpoints/api.py",
            "lib/utils.py",
            "utils/helpers.py",
            "helpers/format.py",
            "upload/file_handler.py",
            "scripts/deploy.sh",
            "src/main.py",
            "components/Button.tsx",
            "stores/user_store.js",
            "services/email_service.py",
            "middleware/auth.py",
        ]

        for pattern in patterns:
            file_path = tmp_path / pattern
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# Sample file")

        return tmp_path

    def test_extended_patterns_constant_has_14_entries(self):
        """Test that EXTENDED_LAYER_PATTERNS has exactly 14 patterns."""
        from lib.codebase_analyzer.agent_invoker import HeuristicAnalyzer

        assert len(HeuristicAnalyzer.EXTENDED_LAYER_PATTERNS) == 14

    def test_detect_extended_patterns_method_exists(self):
        """Test that _detect_extended_patterns method exists."""
        analyzer = HeuristicAnalyzer(Path("/tmp"))
        assert hasattr(analyzer, '_detect_extended_patterns')
        assert callable(getattr(analyzer, '_detect_extended_patterns'))

    def test_detect_presentation_layer_patterns(self, temp_codebase):
        """Test detection of Presentation layer patterns (routes, controllers, views, endpoints, components)."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        extended_layers = analyzer._detect_extended_patterns()

        # Extract layer names
        layer_names = [layer['name'] for layer in extended_layers]

        # Should detect Presentation layer from routes/controllers/views/endpoints/components
        assert 'Presentation' in layer_names

    def test_detect_infrastructure_layer_patterns(self, temp_codebase):
        """Test detection of Infrastructure layer patterns (lib, upload, scripts, middleware)."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        extended_layers = analyzer._detect_extended_patterns()

        layer_names = [layer['name'] for layer in extended_layers]

        # Should detect Infrastructure layer
        assert 'Infrastructure' in layer_names

    def test_detect_shared_layer_patterns(self, temp_codebase):
        """Test detection of Shared layer patterns (utils, helpers)."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        extended_layers = analyzer._detect_extended_patterns()

        layer_names = [layer['name'] for layer in extended_layers]

        # Should detect Shared layer
        assert 'Shared' in layer_names

    def test_detect_application_layer_patterns(self, temp_codebase):
        """Test detection of Application layer patterns (src, stores, services)."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        extended_layers = analyzer._detect_extended_patterns()

        layer_names = [layer['name'] for layer in extended_layers]

        # Should detect Application layer
        assert 'Application' in layer_names

    def test_extended_patterns_no_duplicates(self, temp_codebase):
        """Test that extended patterns don't create duplicate layer entries."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        extended_layers = analyzer._detect_extended_patterns()

        # Extract layer names
        layer_names = [layer['name'] for layer in extended_layers]

        # Check for duplicates
        assert len(layer_names) == len(set(layer_names)), "Duplicate layers detected"

    def test_detect_layers_includes_extended_patterns(self, temp_codebase):
        """Test that _detect_layers integrates extended patterns."""
        analyzer = HeuristicAnalyzer(temp_codebase)
        layers = analyzer._detect_layers()

        # Should include layers from extended patterns
        layer_names = [layer['name'] for layer in layers]

        # At least some extended patterns should be detected
        assert len(layer_names) > 0


# =============================================================================
# ISSUE 5: Entity Detection Guard Clause Tests
# =============================================================================

class TestEntityDetectionGuardClause:
    """Test entity detection guard clause prevents false positives."""

    @pytest.fixture
    def create_template(self):
        """Factory function to create CodeTemplate for testing."""
        def _create(name: str, path: str, original_path: str = None):
            return CodeTemplate(
                schema_version="0.2.0",
                name=name,
                original_path=original_path or path,
                template_path=path,
                content="// Sample content",
                placeholders=[],
                file_type="source",
                language="JavaScript"
            )
        return _create

    def test_query_js_not_crud(self, create_template):
        """Test that 'query.js' is NOT identified as CRUD operation."""
        template = create_template("query.js", "lib/query.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation is None, "query.js should not be identified as CRUD"

    def test_firebase_js_not_crud(self, create_template):
        """Test that 'firebase.js' is NOT identified as CRUD operation."""
        template = create_template("firebase.js", "lib/firebase.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation is None, "firebase.js should not be identified as CRUD"

    def test_session_format_js_not_crud(self, create_template):
        """Test that 'sessionFormat.js' is NOT identified as CRUD operation."""
        template = create_template("sessionFormat.js", "lib/sessionFormat.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation is None, "sessionFormat.js should not be identified as CRUD"

    def test_create_user_js_is_crud(self, create_template):
        """Test that 'CreateUser.js' IS identified as Create operation."""
        template = create_template("CreateUser.js", "usecases/CreateUser.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation == 'Create', "CreateUser.js should be identified as Create"

    def test_query_users_js_is_crud(self, create_template):
        """Test that 'QueryUsers.js' IS identified as Read operation."""
        template = create_template("QueryUsers.js", "usecases/QueryUsers.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation == 'Read', "QueryUsers.js should be identified as Read"

    def test_list_products_is_list(self, create_template):
        """Test that 'ListProducts.js' IS identified as List operation."""
        template = create_template("ListProducts.js", "usecases/ListProducts.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation == 'List', "ListProducts.js should be identified as List"

    def test_update_order_is_crud(self, create_template):
        """Test that 'UpdateOrder.cs' IS identified as Update operation."""
        template = create_template("UpdateOrder.cs", "usecases/UpdateOrder.cs")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation == 'Update', "UpdateOrder.cs should be identified as Update"

    def test_delete_session_is_crud(self, create_template):
        """Test that 'DeleteSession.svelte' IS identified as Delete operation."""
        template = create_template("DeleteSession.svelte", "components/DeleteSession.svelte")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation == 'Delete', "DeleteSession.svelte should be identified as Delete"

    def test_entity_detection_guard_clause(self, create_template):
        """Test that identify_entity returns None for non-CRUD files."""
        matcher = CRUDPatternMatcher()

        # Non-CRUD files should return None for entity
        query_template = create_template("query.js", "lib/query.js")
        firebase_template = create_template("firebase.js", "lib/firebase.js")

        assert matcher.identify_entity(query_template) is None, "query.js should have no entity"
        assert matcher.identify_entity(firebase_template) is None, "firebase.js should have no entity"

    def test_entity_detection_for_crud_files(self, create_template):
        """Test that identify_entity works correctly for CRUD files."""
        matcher = CRUDPatternMatcher()

        # CRUD files should return entity
        create_user = create_template("CreateUser.js", "usecases/CreateUser.js")
        query_users = create_template("QueryUsers.js", "usecases/QueryUsers.js")

        assert matcher.identify_entity(create_user) == 'User', "CreateUser.js should have User entity"
        assert matcher.identify_entity(query_users) == 'User', "QueryUsers.js should have User entity"

    def test_list_alone_not_crud(self, create_template):
        """Test that 'list.js' alone is NOT CRUD (utility file)."""
        template = create_template("list.js", "lib/list.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation is None, "list.js alone should not be CRUD"

    def test_search_alone_not_crud(self, create_template):
        """Test that 'search.js' alone is NOT CRUD (utility file)."""
        template = create_template("search.js", "lib/search.js")
        matcher = CRUDPatternMatcher()

        operation = matcher.identify_crud_operation(template)
        assert operation is None, "search.js alone should not be CRUD"


# =============================================================================
# ISSUE 6: Template Naming Fix Tests
# =============================================================================

class TestTemplateNamingFix:
    """Test template naming fix for compound extensions."""

    @pytest.fixture
    def validator(self):
        """Create CompletenessValidator instance."""
        return CompletenessValidator()

    @pytest.fixture
    def create_template(self):
        """Factory function to create CodeTemplate for testing."""
        def _create(name: str, path: str, content: str = "// Sample", **kwargs):
            return CodeTemplate(
                schema_version="0.2.0",
                name=name,
                original_path=kwargs.get('original_path', path),
                template_path=path,
                content=content,
                placeholders=kwargs.get('placeholders', []),
                file_type=kwargs.get('file_type', 'source'),
                language=kwargs.get('language', 'JavaScript')
            )
        return _create

    def test_separate_template_suffix_with_suffix(self, validator):
        """Test _separate_template_suffix with .template suffix."""
        actual, suffix = validator._separate_template_suffix("file.js.template")
        assert actual == "file.js"
        assert suffix == ".template"

    def test_separate_template_suffix_without_suffix(self, validator):
        """Test _separate_template_suffix without .template suffix."""
        actual, suffix = validator._separate_template_suffix("file.js")
        assert actual == "file.js"
        assert suffix == ""

    def test_separate_template_suffix_compound_extension(self, validator):
        """Test _separate_template_suffix with compound extension."""
        actual, suffix = validator._separate_template_suffix("file.test.ts.template")
        assert actual == "file.test.ts"
        assert suffix == ".template"

    def test_estimate_file_path_svelte_template(self, validator, create_template):
        """Test Session.svelte.template → DeleteSession.svelte.template."""
        reference = create_template(
            "GetSession.svelte.template",
            "components/GetSession.svelte.template"
        )

        estimated = validator._estimate_file_path(
            entity="Session",
            operation="Delete",
            reference=reference
        )

        assert estimated == "components/DeleteSession.svelte.template"

    def test_estimate_file_path_js_template(self, validator, create_template):
        """Test CreateUser.js.template → DeleteUser.js.template."""
        reference = create_template(
            "CreateUser.js.template",
            "usecases/CreateUser.js.template"
        )

        estimated = validator._estimate_file_path(
            entity="User",
            operation="Delete",
            reference=reference
        )

        assert estimated == "usecases/DeleteUser.js.template"

    def test_estimate_file_path_hyphenated(self, validator, create_template):
        """Test hyphenated pattern: Get-user.js.template → Update-user.js.template."""
        reference = create_template(
            "Get-user.js.template",
            "api/Get-user.js.template"
        )

        estimated = validator._estimate_file_path(
            entity="user",
            operation="Update",
            reference=reference
        )

        assert estimated == "api/Update-user.js.template"

    def test_estimate_file_path_underscore(self, validator, create_template):
        """Test underscore pattern preservation: Get_session.py.template → Update_session.py.template."""
        reference = create_template(
            "Get_session.py.template",
            "api/Get_session.py.template"
        )

        estimated = validator._estimate_file_path(
            entity="session",
            operation="Update",
            reference=reference
        )

        assert estimated == "api/Update_session.py.template"

    def test_estimate_file_path_compound_extension(self, validator, create_template):
        """Test compound extension: CreateUser.test.ts.template → DeleteUser.test.ts.template."""
        reference = create_template(
            "CreateUser.test.ts.template",
            "tests/CreateUser.test.ts.template"
        )

        estimated = validator._estimate_file_path(
            entity="User",
            operation="Delete",
            reference=reference
        )

        assert estimated == "tests/DeleteUser.test.ts.template"

    def test_estimate_file_path_without_template_suffix(self, validator, create_template):
        """Test file without .template suffix: CreateUser.cs → DeleteUser.cs."""
        reference = create_template(
            "CreateUser.cs",
            "usecases/CreateUser.cs"
        )

        estimated = validator._estimate_file_path(
            entity="User",
            operation="Delete",
            reference=reference
        )

        assert estimated == "usecases/DeleteUser.cs"

    def test_estimate_file_path_preserves_directory(self, validator, create_template):
        """Test that directory structure is preserved."""
        reference = create_template(
            "GetProduct.js.template",
            "src/api/products/GetProduct.js.template"
        )

        estimated = validator._estimate_file_path(
            entity="Product",
            operation="Update",
            reference=reference
        )

        assert "src/api/products/" in estimated
        assert estimated.endswith("UpdateProduct.js.template")


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_framework_list_iteration(self):
        """Test iteration over empty framework list."""
        tech = TechnologyInfo(
            primary_language="Rust",
            frameworks=[],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
        )

        result = list(tech.framework_list)
        assert result == []

    def test_single_framework_object(self):
        """Test TechnologyInfo with single FrameworkInfo object."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=[FrameworkInfo(name="Django", purpose="Web framework")],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=92.0)
        )

        assert tech.framework_list == ["Django"]

    def test_pattern_matcher_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        template = CodeTemplate(
            schema_version="0.2.0",
            name="createuser.js",  # lowercase
            original_path="api/createuser.js",
            template_path="api/createuser.js",
            content="// content",
            placeholders=[],
            file_type="source",
            language="JavaScript"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        # Should detect Create even with lowercase
        assert operation == 'Create'

    def test_crud_operation_with_special_chars(self):
        """Test CRUD detection with special characters in filename."""
        template = CodeTemplate(
            schema_version="0.2.0",
            name="Create-User-Profile.js",
            original_path="api/Create-User-Profile.js",
            template_path="api/Create-User-Profile.js",
            content="// content",
            placeholders=[],
            file_type="source",
            language="JavaScript"
        )

        matcher = CRUDPatternMatcher()
        operation = matcher.identify_crud_operation(template)

        assert operation == 'Create'


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.fixture
    def sample_codebase(self, tmp_path):
        """Create sample codebase with realistic structure."""
        # Create realistic file structure
        files = [
            "src/main.py",
            "routes/user_routes.py",
            "controllers/auth_controller.py",
            "services/email_service.py",
            "utils/helpers.py",
            "lib/query.js",  # Utility file (not CRUD)
            "lib/firebase.js",  # Utility file (not CRUD)
            "usecases/CreateUser.js",  # CRUD operation
            "usecases/QueryUsers.js",  # CRUD operation
            "components/DeleteSession.svelte",  # CRUD operation
        ]

        for file in files:
            file_path = tmp_path / file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# Sample content")

        return tmp_path

    def test_heuristic_analyzer_with_extended_patterns(self, sample_codebase):
        """Test HeuristicAnalyzer detects extended patterns correctly."""
        analyzer = HeuristicAnalyzer(sample_codebase)
        result = analyzer.analyze()

        # Should have architecture with layers
        assert 'architecture' in result
        assert 'layers' in result['architecture']

        # Should detect at least some extended patterns
        layers = result['architecture']['layers']
        assert len(layers) > 0

    def test_crud_pattern_matcher_filters_utility_files(self):
        """Test that CRUDPatternMatcher correctly filters utility files."""
        matcher = CRUDPatternMatcher()

        # Utility files
        query_template = CodeTemplate(
            schema_version="0.2.0",
            name="query.js",
            original_path="lib/query.js",
            template_path="lib/query.js",
            content="// utility",
            placeholders=[],
            file_type="source",
            language="JavaScript"
        )

        # CRUD file
        create_user = CodeTemplate(
            schema_version="0.2.0",
            name="CreateUser.js",
            original_path="usecases/CreateUser.js",
            template_path="usecases/CreateUser.js",
            content="// CRUD",
            placeholders=[],
            file_type="source",
            language="JavaScript"
        )

        # Utility file should not be detected as CRUD
        assert matcher.identify_crud_operation(query_template) is None
        assert matcher.identify_entity(query_template) is None

        # CRUD file should be detected
        assert matcher.identify_crud_operation(create_user) == 'Create'
        assert matcher.identify_entity(create_user) == 'User'

    def test_completeness_validator_template_naming(self):
        """Test CompletenessValidator handles template naming correctly."""
        validator = CompletenessValidator()

        reference = CodeTemplate(
            schema_version="0.2.0",
            name="GetSession.svelte.template",
            original_path="components/GetSession.svelte.template",
            template_path="components/GetSession.svelte.template",
            content="<script>// Svelte component</script>",
            placeholders=[],
            file_type="component",
            language="Svelte"
        )

        estimated = validator._estimate_file_path(
            entity="Session",
            operation="Delete",
            reference=reference
        )

        # Should preserve compound extension and template suffix
        assert estimated == "components/DeleteSession.svelte.template"
        assert ".svelte.template" in estimated
        assert "Delete" in estimated


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
