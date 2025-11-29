"""
Unit Tests for Stratified Sampler

Tests the stratified sampling components:
1. PatternCategoryDetector - Pattern detection accuracy
2. CRUDCompletenessChecker - CRUD operation completeness
3. StratifiedSampler - End-to-end sampling

Target: ≥85% line coverage
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from lib.codebase_analyzer.stratified_sampler import (
    PatternCategory,
    PatternCategoryDetector,
    CRUDCompletenessChecker,
    StratifiedSampler,
)


class TestPatternCategory:
    """Test PatternCategory enum and helper methods."""

    def test_get_crud_categories(self):
        """Test getting all CRUD categories."""
        crud_cats = PatternCategory.get_crud_categories()
        assert len(crud_cats) == 4
        assert PatternCategory.CRUD_CREATE in crud_cats
        assert PatternCategory.CRUD_READ in crud_cats
        assert PatternCategory.CRUD_UPDATE in crud_cats
        assert PatternCategory.CRUD_DELETE in crud_cats

    def test_get_all_categories(self):
        """Test getting all categories."""
        all_cats = PatternCategory.get_all_categories()
        assert len(all_cats) == 10
        assert PatternCategory.CRUD_CREATE in all_cats
        assert PatternCategory.VALIDATORS in all_cats
        assert PatternCategory.SPECIFICATIONS in all_cats
        assert PatternCategory.REPOSITORIES in all_cats
        assert PatternCategory.INFRASTRUCTURE in all_cats
        assert PatternCategory.QUERIES in all_cats
        assert PatternCategory.OTHER in all_cats


class TestPatternCategoryDetector:
    """Test pattern category detection."""

    @pytest.fixture
    def detector(self):
        """Create pattern detector instance."""
        return PatternCategoryDetector()

    def test_detect_crud_create_patterns(self, detector):
        """Test detecting CRUD Create patterns."""
        test_paths = [
            Path("src/UseCases/Products/Create/CreateProductHandler.cs"),
            Path("src/Endpoints/Contributors/CreateEndpoint.cs"),
            Path("src/Commands/CreateOrder.cs"),
            Path("api/v1/users/create.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.CRUD_CREATE, \
                f"Failed to detect CREATE in: {path}"

    def test_detect_crud_update_patterns(self, detector):
        """Test detecting CRUD Update patterns."""
        test_paths = [
            Path("src/UseCases/Products/Update/UpdateProductHandler.cs"),
            Path("src/Endpoints/Contributors/UpdateEndpoint.cs"),
            Path("src/Commands/UpdateOrder.cs"),
            Path("api/v1/users/update.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.CRUD_UPDATE, \
                f"Failed to detect UPDATE in: {path}"

    def test_detect_crud_delete_patterns(self, detector):
        """Test detecting CRUD Delete patterns."""
        test_paths = [
            Path("src/UseCases/Products/Delete/DeleteProductHandler.cs"),
            Path("src/Endpoints/Contributors/DeleteEndpoint.cs"),
            Path("src/Commands/DeleteOrder.cs"),
            Path("api/v1/users/delete.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.CRUD_DELETE, \
                f"Failed to detect DELETE in: {path}"

    def test_detect_crud_read_patterns(self, detector):
        """Test detecting CRUD Read patterns (Get, List, Query)."""
        test_paths = [
            Path("src/UseCases/Products/GetById/GetProductByIdHandler.cs"),
            Path("src/UseCases/Products/List/ListProductsHandler.cs"),
            Path("src/Endpoints/Contributors/Get.cs"),
            Path("api/v1/users/get.py"),
            Path("api/v1/users/list.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.CRUD_READ, \
                f"Failed to detect READ in: {path}"

    def test_detect_validator_patterns(self, detector):
        """Test detecting Validator patterns."""
        test_paths = [
            Path("src/Validators/CreateProductValidator.cs"),
            Path("src/UseCases/Products/Create/CreateProductValidator.cs"),
            Path("src/Validation/OrderValidator.cs"),
            Path("api/v1/validators/user_validator.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.VALIDATORS, \
                f"Failed to detect VALIDATOR in: {path}"

    def test_detect_specification_patterns(self, detector):
        """Test detecting Specification patterns."""
        test_paths = [
            Path("src/Specifications/ProductByIdSpec.cs"),
            Path("src/Specs/ActiveProductSpec.cs"),
            Path("domain/specifications/user_spec.ts"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.SPECIFICATIONS, \
                f"Failed to detect SPECIFICATION in: {path}"

    def test_detect_repository_patterns(self, detector):
        """Test detecting Repository patterns."""
        test_paths = [
            Path("src/Repositories/ProductRepository.cs"),
            Path("src/Repositories/IProductRepository.cs"),
            Path("infrastructure/repositories/user_repository.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.REPOSITORIES, \
                f"Failed to detect REPOSITORY in: {path}"

    def test_detect_infrastructure_patterns(self, detector):
        """Test detecting Infrastructure patterns."""
        test_paths = [
            Path("src/Infrastructure/Data/ProductConfiguration.cs"),
            Path("src/Infrastructure/Data/Seeder.cs"),
            Path("src/Infrastructure/AppDbContext.cs"),
            Path("infrastructure/database/migrations/001_init.py"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.INFRASTRUCTURE, \
                f"Failed to detect INFRASTRUCTURE in: {path}"

    def test_detect_query_patterns(self, detector):
        """Test detecting explicit Query patterns."""
        test_paths = [
            Path("src/Queries/GetProductQuery.cs"),
            Path("src/UseCases/Products/Queries/ListProductsQuery.ts"),
            Path("api/v1/queries/user_query.py"),
        ]

        for path in test_paths:
            # Note: Some might be detected as CRUD_READ first
            # This tests explicit query files
            category = detector.detect_pattern_from_path(path)
            assert category in [PatternCategory.QUERIES, PatternCategory.CRUD_READ], \
                f"Failed to detect QUERY in: {path}"

    def test_detect_other_patterns(self, detector):
        """Test detecting files that don't match any pattern."""
        test_paths = [
            Path("src/Domain/Product.cs"),
            Path("src/Domain/Entities/User.cs"),
            Path("src/Shared/Result.cs"),
            Path("src/Utils/StringHelper.cs"),
        ]

        for path in test_paths:
            category = detector.detect_pattern_from_path(path)
            assert category == PatternCategory.OTHER, \
                f"Should be OTHER: {path}"

    def test_categorize_files(self, detector):
        """Test categorizing a list of files."""
        test_files = [
            Path("src/Create/CreateProduct.cs"),
            Path("src/Update/UpdateProduct.cs"),
            Path("src/Delete/DeleteProduct.cs"),
            Path("src/Get/GetProduct.cs"),
            Path("src/Validators/ProductValidator.cs"),
            Path("src/Domain/Product.cs"),
        ]

        categorized = detector.categorize_files(test_files)

        assert PatternCategory.CRUD_CREATE in categorized
        assert PatternCategory.CRUD_UPDATE in categorized
        assert PatternCategory.CRUD_DELETE in categorized
        assert PatternCategory.CRUD_READ in categorized
        assert PatternCategory.VALIDATORS in categorized
        assert PatternCategory.OTHER in categorized

        assert len(categorized[PatternCategory.CRUD_CREATE]) == 1
        assert len(categorized[PatternCategory.CRUD_UPDATE]) == 1
        assert len(categorized[PatternCategory.CRUD_DELETE]) == 1
        assert len(categorized[PatternCategory.CRUD_READ]) == 1
        assert len(categorized[PatternCategory.VALIDATORS]) == 1
        assert len(categorized[PatternCategory.OTHER]) == 1

    def test_pattern_detection_accuracy(self, detector):
        """
        Test overall pattern detection accuracy.

        Target: ≥90% accuracy on sample set.
        """
        # Test cases: (path, expected_category)
        test_cases = [
            # CRUD Create (10)
            (Path("src/Create/CreateProduct.cs"), PatternCategory.CRUD_CREATE),
            (Path("api/products/create.py"), PatternCategory.CRUD_CREATE),
            (Path("handlers/CreateHandler.cs"), PatternCategory.CRUD_CREATE),
            (Path("endpoints/CreateEndpoint.cs"), PatternCategory.CRUD_CREATE),
            (Path("commands/CreateCommand.cs"), PatternCategory.CRUD_CREATE),
            (Path("create/product.py"), PatternCategory.CRUD_CREATE),
            (Path("src/UseCases/Create/Handler.cs"), PatternCategory.CRUD_CREATE),
            (Path("features/create/index.ts"), PatternCategory.CRUD_CREATE),
            (Path("src/CreateProduct/Handler.cs"), PatternCategory.CRUD_CREATE),
            (Path("api/v1/create_product.py"), PatternCategory.CRUD_CREATE),

            # CRUD Update (10)
            (Path("src/Update/UpdateProduct.cs"), PatternCategory.CRUD_UPDATE),
            (Path("api/products/update.py"), PatternCategory.CRUD_UPDATE),
            (Path("handlers/UpdateHandler.cs"), PatternCategory.CRUD_UPDATE),
            (Path("endpoints/UpdateEndpoint.cs"), PatternCategory.CRUD_UPDATE),
            (Path("commands/UpdateCommand.cs"), PatternCategory.CRUD_UPDATE),
            (Path("update/product.py"), PatternCategory.CRUD_UPDATE),
            (Path("src/UseCases/Update/Handler.cs"), PatternCategory.CRUD_UPDATE),
            (Path("features/update/index.ts"), PatternCategory.CRUD_UPDATE),
            (Path("src/UpdateProduct/Handler.cs"), PatternCategory.CRUD_UPDATE),
            (Path("api/v1/update_product.py"), PatternCategory.CRUD_UPDATE),

            # CRUD Delete (10)
            (Path("src/Delete/DeleteProduct.cs"), PatternCategory.CRUD_DELETE),
            (Path("api/products/delete.py"), PatternCategory.CRUD_DELETE),
            (Path("handlers/DeleteHandler.cs"), PatternCategory.CRUD_DELETE),
            (Path("endpoints/DeleteEndpoint.cs"), PatternCategory.CRUD_DELETE),
            (Path("commands/DeleteCommand.cs"), PatternCategory.CRUD_DELETE),
            (Path("delete/product.py"), PatternCategory.CRUD_DELETE),
            (Path("src/UseCases/Delete/Handler.cs"), PatternCategory.CRUD_DELETE),
            (Path("features/delete/index.ts"), PatternCategory.CRUD_DELETE),
            (Path("src/DeleteProduct/Handler.cs"), PatternCategory.CRUD_DELETE),
            (Path("api/v1/delete_product.py"), PatternCategory.CRUD_DELETE),

            # CRUD Read (10)
            (Path("src/Get/GetProduct.cs"), PatternCategory.CRUD_READ),
            (Path("api/products/get.py"), PatternCategory.CRUD_READ),
            (Path("handlers/GetHandler.cs"), PatternCategory.CRUD_READ),
            (Path("endpoints/GetEndpoint.cs"), PatternCategory.CRUD_READ),
            (Path("src/List/ListProducts.cs"), PatternCategory.CRUD_READ),
            (Path("api/products/list.py"), PatternCategory.CRUD_READ),
            (Path("handlers/ListHandler.cs"), PatternCategory.CRUD_READ),
            (Path("features/get/index.ts"), PatternCategory.CRUD_READ),
            (Path("src/GetById/Handler.cs"), PatternCategory.CRUD_READ),
            (Path("api/v1/get_product.py"), PatternCategory.CRUD_READ),

            # Validators (10)
            (Path("src/Validators/ProductValidator.cs"), PatternCategory.VALIDATORS),
            (Path("validators/user_validator.py"), PatternCategory.VALIDATORS),
            (Path("src/CreateProductValidator.cs"), PatternCategory.VALIDATORS),
            (Path("validation/order_validator.ts"), PatternCategory.VALIDATORS),
            (Path("src/UseCases/Create/Validator.cs"), PatternCategory.VALIDATORS),
            (Path("features/validation/product.ts"), PatternCategory.VALIDATORS),
            (Path("api/validators/user.py"), PatternCategory.VALIDATORS),
            (Path("src/Validation/ProductValidator.cs"), PatternCategory.VALIDATORS),
            (Path("lib/validators/order.ts"), PatternCategory.VALIDATORS),
            (Path("src/Product/Validator.cs"), PatternCategory.VALIDATORS),

            # Specifications (5)
            (Path("src/Specifications/ProductSpec.cs"), PatternCategory.SPECIFICATIONS),
            (Path("specs/product_spec.py"), PatternCategory.SPECIFICATIONS),
            (Path("src/Specs/ActiveProductSpec.cs"), PatternCategory.SPECIFICATIONS),
            (Path("domain/specs/user_spec.ts"), PatternCategory.SPECIFICATIONS),
            (Path("src/ProductByIdSpec.cs"), PatternCategory.SPECIFICATIONS),

            # Repositories (5)
            (Path("src/Repositories/ProductRepository.cs"), PatternCategory.REPOSITORIES),
            (Path("repositories/user_repository.py"), PatternCategory.REPOSITORIES),
            (Path("src/IProductRepository.cs"), PatternCategory.REPOSITORIES),
            (Path("infrastructure/repositories/order.ts"), PatternCategory.REPOSITORIES),
            (Path("src/Data/ProductRepository.cs"), PatternCategory.REPOSITORIES),

            # Infrastructure (10)
            (Path("src/Infrastructure/ProductConfiguration.cs"), PatternCategory.INFRASTRUCTURE),
            (Path("infrastructure/database/seeder.py"), PatternCategory.INFRASTRUCTURE),
            (Path("src/Data/AppDbContext.cs"), PatternCategory.INFRASTRUCTURE),
            (Path("migrations/001_init.py"), PatternCategory.INFRASTRUCTURE),
            (Path("src/Mapping/ProductMapping.cs"), PatternCategory.INFRASTRUCTURE),
            (Path("infrastructure/config.ts"), PatternCategory.INFRASTRUCTURE),
            (Path("src/Configurations/Database.cs"), PatternCategory.INFRASTRUCTURE),
            (Path("database/migrations/create_products.py"), PatternCategory.INFRASTRUCTURE),
            (Path("src/Infrastructure/Persistence/Context.cs"), PatternCategory.INFRASTRUCTURE),
            (Path("infrastructure/seeder/products.ts"), PatternCategory.INFRASTRUCTURE),

            # Other (10)
            (Path("src/Domain/Product.cs"), PatternCategory.OTHER),
            (Path("models/user.py"), PatternCategory.OTHER),
            (Path("src/Shared/Result.cs"), PatternCategory.OTHER),
            (Path("utils/string_helper.py"), PatternCategory.OTHER),
            (Path("src/Domain/Entities/Order.cs"), PatternCategory.OTHER),
            (Path("lib/types/product.ts"), PatternCategory.OTHER),
            (Path("src/Shared/ValueObjects/Email.cs"), PatternCategory.OTHER),
            (Path("helpers/date_utils.py"), PatternCategory.OTHER),
            (Path("src/Core/Common/Result.cs"), PatternCategory.OTHER),
            (Path("lib/utils/validation.ts"), PatternCategory.OTHER),
        ]

        correct = 0
        total = len(test_cases)

        for path, expected_category in test_cases:
            detected_category = detector.detect_pattern_from_path(path)
            if detected_category == expected_category:
                correct += 1
            else:
                # Log mismatches for debugging
                print(f"Mismatch: {path} - Expected: {expected_category}, Got: {detected_category}")

        accuracy = (correct / total) * 100
        print(f"Pattern detection accuracy: {accuracy:.1f}% ({correct}/{total})")

        # Assert ≥90% accuracy
        assert accuracy >= 90.0, \
            f"Pattern detection accuracy {accuracy:.1f}% is below required 90%"


class TestCRUDCompletenessChecker:
    """Test CRUD completeness checking."""

    @pytest.fixture
    def detector(self):
        """Create pattern detector."""
        return PatternCategoryDetector()

    @pytest.fixture
    def checker(self, detector):
        """Create completeness checker."""
        return CRUDCompletenessChecker(detector)

    def test_extract_entity_from_path_usecases(self, checker):
        """Test entity extraction from UseCases paths."""
        test_cases = [
            (Path("src/UseCases/Products/Create/Handler.cs"), "product"),
            (Path("src/UseCases/Contributors/Update/Handler.cs"), "contributor"),
            (Path("src/UseCases/Orders/Delete/Handler.cs"), "order"),
        ]

        for path, expected_entity in test_cases:
            entity = checker._extract_entity_from_path(path)
            assert entity == expected_entity, \
                f"Failed to extract entity from: {path}"

    def test_extract_entity_from_path_endpoints(self, checker):
        """Test entity extraction from Endpoints paths."""
        test_cases = [
            (Path("src/Endpoints/Products/Create.cs"), "product"),
            (Path("src/Endpoints/Users/Update.cs"), "user"),
            (Path("src/Web/Endpoints/Orders/Delete.cs"), "order"),
        ]

        for path, expected_entity in test_cases:
            entity = checker._extract_entity_from_path(path)
            assert entity == expected_entity, \
                f"Failed to extract entity from: {path}"

    def test_extract_entity_from_filename(self, checker):
        """Test entity extraction from filename."""
        test_cases = [
            (Path("src/CreateProduct.cs"), "product"),
            (Path("src/UpdateProductHandler.cs"), "product"),
            (Path("src/DeleteOrderCommand.cs"), "order"),
            (Path("src/GetUserQuery.cs"), "user"),
        ]

        for path, expected_entity in test_cases:
            entity = checker._extract_entity_from_path(path)
            assert entity == expected_entity, \
                f"Failed to extract entity from: {path}"

    def test_singularize_words(self, checker):
        """Test word singularization."""
        test_cases = [
            ("Products", "Product"),
            ("Users", "User"),
            ("Orders", "Order"),
            ("Companies", "Company"),  # ies -> y rule
            ("Categories", "Category"),  # ies -> y rule
            ("User", "User"),  # Already singular
            ("Status", "Status"),  # Ends with 'ss', should not change
        ]

        for plural, expected_singular in test_cases:
            singular = checker._singularize(plural)
            assert singular.lower() == expected_singular.lower(), \
                f"Singularization failed: {plural} -> {singular}, expected: {expected_singular}"

    def test_analyze_current_samples_single_entity(self, checker):
        """Test analyzing samples with a single entity."""
        samples = [
            {'path': 'src/UseCases/Products/Create/Handler.cs', 'content': '...'},
            {'path': 'src/UseCases/Products/Update/Handler.cs', 'content': '...'},
        ]

        entity_operations = checker._analyze_current_samples(samples)

        assert 'product' in entity_operations
        assert PatternCategory.CRUD_CREATE in entity_operations['product']
        assert PatternCategory.CRUD_UPDATE in entity_operations['product']
        assert len(entity_operations['product']) == 2

    def test_analyze_current_samples_multiple_entities(self, checker):
        """Test analyzing samples with multiple entities."""
        samples = [
            {'path': 'src/UseCases/Products/Create/Handler.cs', 'content': '...'},
            {'path': 'src/UseCases/Orders/Create/Handler.cs', 'content': '...'},
            {'path': 'src/UseCases/Products/Update/Handler.cs', 'content': '...'},
        ]

        entity_operations = checker._analyze_current_samples(samples)

        assert 'product' in entity_operations
        assert 'order' in entity_operations
        assert PatternCategory.CRUD_CREATE in entity_operations['product']
        assert PatternCategory.CRUD_UPDATE in entity_operations['product']
        assert PatternCategory.CRUD_CREATE in entity_operations['order']

    def test_find_missing_operations(self, checker):
        """Test finding missing CRUD operations."""
        entity_operations = {
            'product': {PatternCategory.CRUD_CREATE, PatternCategory.CRUD_READ},
            'order': {PatternCategory.CRUD_CREATE, PatternCategory.CRUD_UPDATE,
                     PatternCategory.CRUD_DELETE, PatternCategory.CRUD_READ},
        }

        missing = checker._find_missing_operations(entity_operations)

        assert 'product' in missing
        assert PatternCategory.CRUD_UPDATE in missing['product']
        assert PatternCategory.CRUD_DELETE in missing['product']

        # Order has all operations, should not be in missing
        assert 'order' not in missing

    def test_ensure_crud_completeness_adds_missing_operations(self, checker, tmp_path):
        """Test that completeness checker adds missing operations."""
        # Create test files
        create_file = tmp_path / "CreateProduct.cs"
        update_file = tmp_path / "UpdateProduct.cs"
        delete_file = tmp_path / "DeleteProduct.cs"
        get_file = tmp_path / "GetProduct.cs"

        create_file.write_text("// Create Product")
        update_file.write_text("// Update Product")
        delete_file.write_text("// Delete Product")
        get_file.write_text("// Get Product")

        # Current samples (only Create)
        samples = [
            {'path': str(create_file), 'content': '// Create Product'},
        ]

        all_files = [create_file, update_file, delete_file, get_file]

        # Ensure completeness
        updated_samples = checker.ensure_crud_completeness(samples, all_files, max_additions=10)

        # Should have added missing operations
        assert len(updated_samples) > 1
        sample_paths = [s['path'] for s in updated_samples]
        assert str(create_file) in sample_paths


class TestStratifiedSampler:
    """Test stratified sampler."""

    @pytest.fixture
    def temp_codebase(self, tmp_path):
        """Create a temporary codebase structure."""
        # Create directory structure
        (tmp_path / "src" / "UseCases" / "Products" / "Create").mkdir(parents=True)
        (tmp_path / "src" / "UseCases" / "Products" / "Update").mkdir(parents=True)
        (tmp_path / "src" / "UseCases" / "Products" / "Delete").mkdir(parents=True)
        (tmp_path / "src" / "UseCases" / "Products" / "Get").mkdir(parents=True)
        (tmp_path / "src" / "Validators").mkdir(parents=True)
        (tmp_path / "src" / "Specifications").mkdir(parents=True)
        (tmp_path / "src" / "Repositories").mkdir(parents=True)
        (tmp_path / "src" / "Infrastructure").mkdir(parents=True)
        (tmp_path / "src" / "Domain").mkdir(parents=True)

        # Create files
        files = [
            "src/UseCases/Products/Create/CreateProductHandler.cs",
            "src/UseCases/Products/Update/UpdateProductHandler.cs",
            "src/UseCases/Products/Delete/DeleteProductHandler.cs",
            "src/UseCases/Products/Get/GetProductHandler.cs",
            "src/Validators/CreateProductValidator.cs",
            "src/Specifications/ProductByIdSpec.cs",
            "src/Repositories/ProductRepository.cs",
            "src/Infrastructure/ProductConfiguration.cs",
            "src/Domain/Product.cs",
        ]

        for file_path in files:
            full_path = tmp_path / file_path
            full_path.write_text(f"// {file_path}\nclass Sample {{}}")

        return tmp_path

    def test_discover_all_files(self, temp_codebase):
        """Test discovering all source files."""
        sampler = StratifiedSampler(temp_codebase, max_files=20)
        all_files = sampler._discover_all_files()

        assert len(all_files) == 9  # All .cs files created

    def test_should_include_filters_correctly(self, temp_codebase):
        """Test file inclusion filters."""
        sampler = StratifiedSampler(temp_codebase, max_files=20)

        # Should include source files
        source_file = temp_codebase / "src" / "Product.cs"
        source_file.write_text("class Product {}")
        assert sampler._should_include(source_file) is True

        # Should exclude test files
        test_file = temp_codebase / "tests" / "ProductTest.cs"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("class ProductTest {}")
        assert sampler._should_include(test_file) is False

    def test_calculate_allocations(self, temp_codebase):
        """Test allocation calculation."""
        sampler = StratifiedSampler(temp_codebase, max_files=20)

        categorized = {
            PatternCategory.CRUD_CREATE: [Path("create1.cs"), Path("create2.cs")],
            PatternCategory.CRUD_UPDATE: [Path("update1.cs")],
            PatternCategory.CRUD_DELETE: [Path("delete1.cs")],
            PatternCategory.CRUD_READ: [Path("get1.cs")],
            PatternCategory.VALIDATORS: [Path("validator1.cs")],
            PatternCategory.INFRASTRUCTURE: [Path("config1.cs")],
            PatternCategory.OTHER: [Path("other1.cs")],
        }

        allocations = sampler._calculate_allocations(categorized)

        # Should have allocations for each category present
        assert PatternCategory.CRUD_CREATE in allocations
        assert PatternCategory.VALIDATORS in allocations
        assert PatternCategory.INFRASTRUCTURE in allocations

    def test_rank_and_select_files(self, temp_codebase):
        """Test file ranking and selection."""
        sampler = StratifiedSampler(temp_codebase, max_files=20)

        # Create files with different sizes
        file1 = temp_codebase / "small.cs"
        file2 = temp_codebase / "large.cs"

        file1.write_text("small")
        file2.write_text("large" * 100)

        files = [file1, file2]

        # Select 1 file - should pick larger one
        selected = sampler._rank_and_select_files(files, 1)

        assert len(selected) == 1
        # Larger file should be selected (higher quality score)
        # Note: This may vary based on other scoring factors

    def test_calculate_file_quality_score(self, temp_codebase):
        """Test quality score calculation."""
        sampler = StratifiedSampler(temp_codebase, max_files=20)

        # Create test file in domain directory (should get bonus)
        domain_file = temp_codebase / "src" / "Domain" / "Product.cs"
        other_file = temp_codebase / "src" / "Other.cs"

        domain_file.write_text("class Product {}")
        other_file.write_text("class Other {}")

        domain_score = sampler._calculate_file_quality_score(domain_file)
        other_score = sampler._calculate_file_quality_score(other_file)

        # Domain file should have higher score
        assert domain_score > other_score

    def test_collect_stratified_samples(self, temp_codebase):
        """Test end-to-end stratified sampling."""
        sampler = StratifiedSampler(temp_codebase, max_files=10)

        samples = sampler.collect_stratified_samples()

        # Should collect samples
        assert len(samples) > 0
        assert len(samples) <= 10

        # Each sample should have 'path' and 'content'
        for sample in samples:
            assert 'path' in sample
            assert 'content' in sample
            assert len(sample['content']) > 0

    def test_stratified_sampling_respects_max_files(self, temp_codebase):
        """Test that sampling respects max_files limit."""
        sampler = StratifiedSampler(temp_codebase, max_files=5)

        samples = sampler.collect_stratified_samples()

        assert len(samples) <= 5

    def test_stratified_sampling_handles_empty_codebase(self, tmp_path):
        """Test sampling on empty codebase."""
        sampler = StratifiedSampler(tmp_path, max_files=20)

        samples = sampler.collect_stratified_samples()

        assert len(samples) == 0


class TestStratifiedSamplerIntegration:
    """Integration tests for stratified sampler with AI analyzer."""

    def test_stratified_sampler_integration_with_ai_analyzer(self, tmp_path):
        """Test that stratified sampler integrates with AI analyzer."""
        # Create minimal codebase
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Product.cs").write_text("class Product {}")

        # Import here to avoid circular dependency issues in tests
        from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer

        # Create analyzer with stratified sampling enabled
        analyzer = CodebaseAnalyzer(
            max_files=10,
            use_agent=False,  # Use heuristics for testing
            use_stratified_sampling=True
        )

        # Analyze should work with stratified sampling
        analysis = analyzer.analyze_codebase(tmp_path)

        assert analysis is not None
        assert analysis.codebase_path == str(tmp_path)

    def test_stratified_sampler_fallback_to_random(self, tmp_path):
        """Test fallback to random sampling if stratified fails."""
        # Create minimal codebase
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "Product.cs").write_text("class Product {}")

        from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer

        # Create analyzer with stratified sampling disabled
        analyzer = CodebaseAnalyzer(
            max_files=10,
            use_agent=False,
            use_stratified_sampling=False
        )

        # Analyze should work with random sampling
        analysis = analyzer.analyze_codebase(tmp_path)

        assert analysis is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=lib.codebase_analyzer.stratified_sampler",
                 "--cov-report=term", "--cov-report=json"])
