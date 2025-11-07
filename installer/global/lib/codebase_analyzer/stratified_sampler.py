"""
Stratified Sampling for Codebase Analysis

Implements pattern-aware stratified sampling to ensure CRUD completeness
and pattern diversity in file samples. Replaces random sampling (10 files)
with strategic sampling (20 files) that proactively prevents CRUD operation gaps.

Key Components:
1. PatternCategoryDetector - Categorizes files by pattern (CRUD, validators, etc.)
2. CRUDCompletenessChecker - Ensures all CRUD operations sampled per entity
3. StratifiedSampler - Main orchestrator for stratified sampling

Following Phase 2 of TASK-020 implementation plan.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternCategory:
    """Pattern categories for file classification."""
    CRUD_CREATE = "crud_create"
    CRUD_READ = "crud_read"
    CRUD_UPDATE = "crud_update"
    CRUD_DELETE = "crud_delete"
    VALIDATORS = "validators"
    SPECIFICATIONS = "specifications"
    REPOSITORIES = "repositories"
    INFRASTRUCTURE = "infrastructure"
    QUERIES = "queries"
    OTHER = "other"

    @classmethod
    def get_crud_categories(cls) -> List[str]:
        """Get all CRUD-related categories."""
        return [
            cls.CRUD_CREATE,
            cls.CRUD_READ,
            cls.CRUD_UPDATE,
            cls.CRUD_DELETE
        ]

    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get all available categories."""
        return [
            cls.CRUD_CREATE,
            cls.CRUD_READ,
            cls.CRUD_UPDATE,
            cls.CRUD_DELETE,
            cls.VALIDATORS,
            cls.SPECIFICATIONS,
            cls.REPOSITORIES,
            cls.INFRASTRUCTURE,
            cls.QUERIES,
            cls.OTHER
        ]


class PatternCategoryDetector:
    """
    Detects pattern categories from file paths and names.

    Uses heuristic rules to categorize files into patterns like:
    - CRUD operations (Create, Read, Update, Delete)
    - Validators
    - Specifications
    - Repositories
    - Infrastructure
    - Queries
    - Other

    Target: ≥90% categorization accuracy (validated by unit tests)
    """

    def __init__(self):
        """Initialize pattern detector with detection rules."""
        self._initialize_detection_rules()

    def _initialize_detection_rules(self):
        """Define detection rules for each category."""
        # Detection rules: (pattern_strings, pattern_category)
        # Evaluated in order, first match wins
        # IMPORTANT: Put more specific patterns first to avoid false matches
        self.detection_rules = [
            # Validators (must come before CRUD to avoid false Create matches)
            (["validator", "validation"],
             PatternCategory.VALIDATORS),

            # CRUD Create
            (["create", "/create/", "createhandler", "createendpoint", "createcommand"],
             PatternCategory.CRUD_CREATE),

            # CRUD Update
            (["update", "/update/", "updatehandler", "updateendpoint", "updatecommand"],
             PatternCategory.CRUD_UPDATE),

            # CRUD Delete
            (["delete", "/delete/", "deletehandler", "deleteendpoint", "deletecommand"],
             PatternCategory.CRUD_DELETE),

            # CRUD Read (Get, List, Query)
            (["getbyid", "get", "list", "/get/", "/list/", "gethandler", "listhandler",
              "query", "/query/"],
             PatternCategory.CRUD_READ),

            # Specifications
            (["spec.cs", "spec.ts", "specification", "/specs/"],
             PatternCategory.SPECIFICATIONS),

            # Repositories
            (["repository", "irepository", "/repositories/"],
             PatternCategory.REPOSITORIES),

            # Infrastructure
            (["configuration", "seeder", "/infrastructure/", "dbcontext",
              "migration", "mapping"],
             PatternCategory.INFRASTRUCTURE),

            # Queries (explicit query files, not CRUD reads)
            (["query.cs", "query.ts", "/queries/"],
             PatternCategory.QUERIES),
        ]

    def detect_pattern_from_path(self, file_path: Path) -> str:
        """
        Detect pattern category from file path.

        Args:
            file_path: Path to file (absolute or relative)

        Returns:
            Pattern category string (from PatternCategory)
        """
        path_str = str(file_path).lower()
        file_name = file_path.name.lower()

        # Check each detection rule in order
        for patterns, category in self.detection_rules:
            for pattern in patterns:
                if pattern in path_str or pattern in file_name:
                    return category

        # Default to OTHER if no match
        return PatternCategory.OTHER

    def categorize_files(self, files: List[Path]) -> Dict[str, List[Path]]:
        """
        Categorize a list of files by pattern.

        Args:
            files: List of file paths to categorize

        Returns:
            Dictionary mapping category -> list of files
        """
        categorized = defaultdict(list)

        for file_path in files:
            category = self.detect_pattern_from_path(file_path)
            categorized[category].append(file_path)

        # Log category distribution
        logger.info("File categorization:")
        for category in PatternCategory.get_all_categories():
            count = len(categorized.get(category, []))
            if count > 0:
                logger.info(f"  {category}: {count} files")

        return dict(categorized)


class CRUDCompletenessChecker:
    """
    Ensures CRUD completeness in sampled files.

    If any CRUD operation is discovered for an entity, ensures all
    CRUD operations (Create, Read, Update, Delete, List) are included
    in the sample set.

    Entity extraction:
    - From path: src/UseCases/Products/Create/... → "Product"
    - Singularization: "Products" → "Product"
    """

    def __init__(self, pattern_detector: PatternCategoryDetector):
        """
        Initialize completeness checker.

        Args:
            pattern_detector: Detector for identifying operation types
        """
        self.pattern_detector = pattern_detector

    def ensure_crud_completeness(
        self,
        samples: List[Dict[str, str]],
        all_files: List[Path],
        max_additions: int = 10
    ) -> List[Dict[str, str]]:
        """
        Ensure CRUD completeness for all entities in samples.

        Args:
            samples: Current file samples (list of dicts with 'path' and 'content')
            all_files: All available files in codebase
            max_additions: Maximum number of files to add for completeness

        Returns:
            Updated samples list with missing CRUD operations added
        """
        # Extract entities and their operations from current samples
        entity_operations = self._analyze_current_samples(samples)

        if not entity_operations:
            logger.info("No entities with CRUD operations found in samples")
            return samples

        logger.info(f"Found {len(entity_operations)} entities with CRUD operations")

        # Find missing operations for each entity
        missing_operations = self._find_missing_operations(entity_operations)

        if not missing_operations:
            logger.info("All sampled entities have complete CRUD operations")
            return samples

        logger.info(f"Found {len(missing_operations)} missing CRUD operations")

        # Add files for missing operations
        additions_count = 0
        sample_paths = {s['path'] for s in samples}

        for entity, operations in missing_operations.items():
            for operation in operations:
                if additions_count >= max_additions:
                    logger.warning(f"Reached max additions ({max_additions}), stopping")
                    break

                # Find file for this operation
                operation_file = self._find_operation_file(
                    all_files,
                    entity,
                    operation,
                    sample_paths
                )

                if operation_file:
                    content = self._read_file_safely(operation_file)
                    if content:
                        samples.append({
                            'path': str(operation_file),
                            'content': content
                        })
                        sample_paths.add(str(operation_file))
                        additions_count += 1
                        logger.info(f"Added {operation} operation for {entity}: {operation_file.name}")

        logger.info(f"Added {additions_count} files for CRUD completeness")
        return samples

    def _analyze_current_samples(
        self,
        samples: List[Dict[str, str]]
    ) -> Dict[str, Set[str]]:
        """
        Analyze current samples to extract entities and their operations.

        Returns:
            Dictionary mapping entity -> set of operations
        """
        entity_operations = defaultdict(set)

        for sample in samples:
            path = Path(sample['path'])

            # Detect operation type
            category = self.pattern_detector.detect_pattern_from_path(path)

            if category in PatternCategory.get_crud_categories():
                # Extract entity from path
                entity = self._extract_entity_from_path(path)
                if entity:
                    entity_operations[entity].add(category)

        return dict(entity_operations)

    def _extract_entity_from_path(self, file_path: Path) -> Optional[str]:
        """
        Extract entity name from file path.

        Examples:
            src/UseCases/Products/Create/CreateProductHandler.cs → "product"
            src/Web/Endpoints/Contributors/Update.cs → "contributor"

        Returns:
            Entity name (singular, lowercase) or None
        """
        path_parts = file_path.parts
        file_name = file_path.stem

        # Strategy 1: Look for entity name in path hierarchy
        # Common patterns: UseCases/{Entity}/, Endpoints/{Entity}/, Features/{Entity}/
        for i, part in enumerate(path_parts):
            part_lower = part.lower()
            if part_lower in ['usecases', 'endpoints', 'features', 'controllers', 'domain']:
                if i + 1 < len(path_parts):
                    entity_candidate = path_parts[i + 1]
                    return self._singularize(entity_candidate).lower()

        # Strategy 2: Extract from filename
        # Patterns: CreateProductHandler, UpdateContributor, ProductValidator
        for operation in ['create', 'update', 'delete', 'get', 'list']:
            if operation in file_name.lower():
                # Remove operation word and common suffixes
                entity = file_name.lower()
                entity = entity.replace(operation, '')
                entity = entity.replace('handler', '')
                entity = entity.replace('endpoint', '')
                entity = entity.replace('command', '')
                entity = entity.replace('validator', '')
                entity = entity.replace('query', '')

                # Clean up and return
                entity = entity.strip('_-')
                if entity:
                    return self._singularize(entity).lower()

        return None

    def _singularize(self, word: str) -> str:
        """
        Simple singularization (remove trailing 's').

        Note: This is a basic implementation. For production,
        consider using inflect or similar library.
        """
        word_lower = word.lower()

        # Don't change if already ends with 'ss' or 'us'
        if word_lower.endswith('ss') or word_lower.endswith('us'):
            return word

        # Handle 'ies' -> 'y'
        if word.endswith('ies'):
            return word[:-3] + 'y'

        # Remove trailing 's'
        if word.endswith('s'):
            return word[:-1]

        return word

    def _find_missing_operations(
        self,
        entity_operations: Dict[str, Set[str]]
    ) -> Dict[str, List[str]]:
        """
        Find missing CRUD operations for each entity.

        Args:
            entity_operations: Entity -> set of current operations

        Returns:
            Entity -> list of missing operations
        """
        missing = {}
        all_crud_operations = set(PatternCategory.get_crud_categories())

        for entity, operations in entity_operations.items():
            missing_ops = all_crud_operations - operations
            if missing_ops:
                missing[entity] = list(missing_ops)

        return missing

    def _find_operation_file(
        self,
        all_files: List[Path],
        entity: str,
        operation: str,
        exclude_paths: Set[str]
    ) -> Optional[Path]:
        """
        Find a file that implements the given operation for the entity.

        Args:
            all_files: All available files
            entity: Entity name (e.g., "product")
            operation: Operation category (e.g., "crud_create")
            exclude_paths: Paths already in samples (to avoid duplicates)

        Returns:
            Path to file or None
        """
        # Map operation to search keywords
        operation_keywords = {
            PatternCategory.CRUD_CREATE: ['create'],
            PatternCategory.CRUD_READ: ['get', 'list', 'read'],
            PatternCategory.CRUD_UPDATE: ['update'],
            PatternCategory.CRUD_DELETE: ['delete'],
        }

        keywords = operation_keywords.get(operation, [])

        # Search for files matching entity + operation
        for file_path in all_files:
            if str(file_path) in exclude_paths:
                continue

            path_str = str(file_path).lower()
            file_name = file_path.name.lower()

            # Check if entity is in path
            if entity not in path_str:
                continue

            # Check if operation keyword is in path/name
            for keyword in keywords:
                if keyword in path_str or keyword in file_name:
                    return file_path

        return None

    def _read_file_safely(self, file_path: Path, max_lines: int = 100) -> Optional[str]:
        """
        Read file content safely with error handling.

        Args:
            file_path: Path to file
            max_lines: Maximum number of lines to read

        Returns:
            File content or None if read fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("... (truncated)")
                        break
                    lines.append(line.rstrip())
                return "\n".join(lines)
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None


class StratifiedSampler:
    """
    Main stratified sampling orchestrator.

    Replaces random sampling with pattern-aware stratified sampling:
    1. Discover all files and categorize by pattern
    2. Sample proportionally from each category (40% CRUD, 20% queries, etc.)
    3. Ensure CRUD completeness for sampled entities
    4. Fill remaining slots with quality-ranked samples

    Sampling Allocation (20 files total):
    - CRUD operations: 40% (8 files)
    - Query patterns: 20% (4 files)
    - Validators/Specs: 15% (3 files)
    - Infrastructure: 15% (3 files)
    - Other: 10% (2 files)
    """

    # Allocation percentages
    ALLOCATION = {
        'crud': 0.40,  # 40% for all CRUD operations combined
        PatternCategory.QUERIES: 0.20,
        'validators_specs': 0.15,  # Combined validators + specifications
        PatternCategory.INFRASTRUCTURE: 0.15,
        PatternCategory.OTHER: 0.10,
    }

    def __init__(
        self,
        codebase_path: Path,
        max_files: int = 20,
        pattern_detector: Optional[PatternCategoryDetector] = None,
        completeness_checker: Optional[CRUDCompletenessChecker] = None
    ):
        """
        Initialize stratified sampler.

        Args:
            codebase_path: Path to codebase root
            max_files: Maximum number of files to sample (default: 20)
            pattern_detector: Optional custom pattern detector
            completeness_checker: Optional custom completeness checker
        """
        self.codebase_path = Path(codebase_path)
        self.max_files = max_files
        self.pattern_detector = pattern_detector or PatternCategoryDetector()
        self.completeness_checker = completeness_checker or CRUDCompletenessChecker(
            self.pattern_detector
        )

        # Files/directories to ignore (same as FileCollector)
        self.ignore_patterns = {
            ".git", ".svn", "node_modules", "__pycache__", ".pytest_cache",
            "venv", "env", ".venv", "dist", "build", "target", ".idea",
            ".vscode", "*.pyc", "*.pyo", ".DS_Store", "coverage"
        }

    def collect_stratified_samples(self) -> List[Dict[str, str]]:
        """
        Collect stratified file samples from codebase.

        Returns:
            List of dictionaries with 'path' and 'content' keys
        """
        logger.info(f"Starting stratified sampling (max_files={self.max_files})")

        # Step 1: Discover all source files
        all_files = self._discover_all_files()
        logger.info(f"Discovered {len(all_files)} source files")

        if len(all_files) == 0:
            logger.warning("No source files found")
            return []

        # Step 2: Categorize files by pattern
        categorized = self.pattern_detector.categorize_files(all_files)

        # Step 3: Sample proportionally from categories
        samples = self._sample_from_categories(categorized)
        logger.info(f"Collected {len(samples)} proportional samples")

        # Step 4: Ensure CRUD completeness
        samples = self.completeness_checker.ensure_crud_completeness(
            samples,
            all_files,
            max_additions=self.max_files - len(samples)
        )
        logger.info(f"After CRUD completeness: {len(samples)} samples")

        # Step 5: Fill remaining slots with quality-ranked samples
        if len(samples) < self.max_files:
            samples = self._fill_remaining_with_quality(samples, all_files)
            logger.info(f"After quality ranking: {len(samples)} samples")

        # Truncate to max_files if exceeded
        if len(samples) > self.max_files:
            samples = samples[:self.max_files]
            logger.info(f"Truncated to {self.max_files} samples")

        return samples

    def _discover_all_files(self) -> List[Path]:
        """
        Discover all source code files in codebase.

        Returns:
            List of file paths
        """
        all_files = []
        source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".java", ".go", ".rs"}

        for ext in source_extensions:
            for file_path in self.codebase_path.rglob(f"*{ext}"):
                if self._should_include(file_path):
                    all_files.append(file_path)

        return all_files

    def _should_include(self, file_path: Path) -> bool:
        """Check if file should be included in samples."""
        if self._should_ignore(file_path):
            return False

        # Only include source code files
        source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".java", ".go", ".rs"}
        if file_path.suffix not in source_extensions:
            return False

        # Skip test files for now (we want production code examples)
        if "test" in file_path.name.lower():
            return False

        # Skip files that are too large (> 10KB)
        try:
            if file_path.stat().st_size > 10 * 1024:
                return False
        except OSError:
            return False

        return True

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)

        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True

        return False

    def _sample_from_categories(
        self,
        categorized: Dict[str, List[Path]]
    ) -> List[Dict[str, str]]:
        """
        Sample files proportionally from each category.

        Args:
            categorized: Category -> list of files

        Returns:
            List of sampled files with content
        """
        samples = []

        # Calculate allocations
        allocations = self._calculate_allocations(categorized)

        # Sample from each category
        for category, target_count in allocations.items():
            files = categorized.get(category, [])

            if not files:
                continue

            # Sample up to target_count files from this category
            sample_count = min(target_count, len(files))

            # Use quality ranking to select best files
            selected_files = self._rank_and_select_files(files, sample_count)

            for file_path in selected_files:
                content = self._read_file_safely(file_path)
                if content:
                    samples.append({
                        'path': str(file_path.relative_to(self.codebase_path)),
                        'content': content
                    })

        return samples

    def _calculate_allocations(
        self,
        categorized: Dict[str, List[Path]]
    ) -> Dict[str, int]:
        """
        Calculate how many files to sample from each category.

        Args:
            categorized: Category -> list of files

        Returns:
            Category -> target sample count
        """
        allocations = {}

        # Group CRUD categories
        crud_categories = PatternCategory.get_crud_categories()
        crud_files = []
        for cat in crud_categories:
            crud_files.extend(categorized.get(cat, []))

        if crud_files:
            crud_count = int(self.max_files * self.ALLOCATION['crud'])
            # Distribute across CRUD categories
            crud_per_category = max(1, crud_count // len(crud_categories))
            for cat in crud_categories:
                allocations[cat] = crud_per_category

        # Queries
        if categorized.get(PatternCategory.QUERIES):
            allocations[PatternCategory.QUERIES] = int(
                self.max_files * self.ALLOCATION[PatternCategory.QUERIES]
            )

        # Validators + Specifications (combined)
        validators = categorized.get(PatternCategory.VALIDATORS, [])
        specifications = categorized.get(PatternCategory.SPECIFICATIONS, [])
        if validators or specifications:
            combined_count = int(self.max_files * self.ALLOCATION['validators_specs'])
            if validators and specifications:
                allocations[PatternCategory.VALIDATORS] = combined_count // 2
                allocations[PatternCategory.SPECIFICATIONS] = combined_count // 2
            elif validators:
                allocations[PatternCategory.VALIDATORS] = combined_count
            else:
                allocations[PatternCategory.SPECIFICATIONS] = combined_count

        # Infrastructure
        if categorized.get(PatternCategory.INFRASTRUCTURE):
            allocations[PatternCategory.INFRASTRUCTURE] = int(
                self.max_files * self.ALLOCATION[PatternCategory.INFRASTRUCTURE]
            )

        # Other
        if categorized.get(PatternCategory.OTHER):
            allocations[PatternCategory.OTHER] = int(
                self.max_files * self.ALLOCATION[PatternCategory.OTHER]
            )

        return allocations

    def _rank_and_select_files(
        self,
        files: List[Path],
        count: int
    ) -> List[Path]:
        """
        Rank files by quality and select top N.

        Quality criteria (in order):
        1. File size (larger = more patterns)
        2. Complexity indicators (number of classes/methods)
        3. Central importance (in key directories)

        Args:
            files: List of files to rank
            count: Number to select

        Returns:
            Top N files by quality
        """
        if len(files) <= count:
            return files

        # Score each file
        scored_files = []
        for file_path in files:
            score = self._calculate_file_quality_score(file_path)
            scored_files.append((score, file_path))

        # Sort by score (descending) and select top N
        scored_files.sort(reverse=True)
        return [f[1] for f in scored_files[:count]]

    def _calculate_file_quality_score(self, file_path: Path) -> float:
        """
        Calculate quality score for a file.

        Higher score = better quality/more informative

        Returns:
            Quality score (0-100)
        """
        score = 0.0

        # Factor 1: File size (larger files have more content)
        try:
            size_bytes = file_path.stat().st_size
            # Normalize: 0-10KB → 0-30 points
            score += min(30.0, (size_bytes / 10240) * 30)
        except OSError:
            pass

        # Factor 2: Depth in project (deeper = more specific/important)
        depth = len(file_path.parts)
        # Normalize: depth 3-8 → 0-20 points
        score += min(20.0, max(0, (depth - 2) * 4))

        # Factor 3: In key directories (domain, usecases, etc.)
        path_str = str(file_path).lower()
        key_dirs = ['domain', 'usecases', 'core', 'application', 'features']
        for key_dir in key_dirs:
            if key_dir in path_str:
                score += 20.0
                break

        # Factor 4: Has Handler/Service/Repository in name (key components)
        name_lower = file_path.name.lower()
        if any(term in name_lower for term in ['handler', 'service', 'repository', 'controller']):
            score += 15.0

        # Factor 5: Not in generated/auto directories
        if not any(term in path_str for term in ['generated', 'auto', 'migrations']):
            score += 15.0

        return score

    def _fill_remaining_with_quality(
        self,
        samples: List[Dict[str, str]],
        all_files: List[Path]
    ) -> List[Dict[str, str]]:
        """
        Fill remaining sample slots with quality-ranked files.

        Args:
            samples: Current samples
            all_files: All available files

        Returns:
            Updated samples with additional quality-ranked files
        """
        sample_paths = {s['path'] for s in samples}
        remaining_slots = self.max_files - len(samples)

        if remaining_slots <= 0:
            return samples

        # Get files not yet sampled
        unsampled_files = [
            f for f in all_files
            if str(f.relative_to(self.codebase_path)) not in sample_paths
        ]

        # Rank and select top files
        top_files = self._rank_and_select_files(unsampled_files, remaining_slots)

        # Add to samples
        for file_path in top_files:
            content = self._read_file_safely(file_path)
            if content:
                samples.append({
                    'path': str(file_path.relative_to(self.codebase_path)),
                    'content': content
                })

        return samples

    def _read_file_safely(self, file_path: Path, max_lines: int = 100) -> Optional[str]:
        """
        Read file content safely with error handling.

        Args:
            file_path: Path to file
            max_lines: Maximum number of lines to read

        Returns:
            File content or None if read fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("... (truncated)")
                        break
                    lines.append(line.rstrip())
                return "\n".join(lines)
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None
