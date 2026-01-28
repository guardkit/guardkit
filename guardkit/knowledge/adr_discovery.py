"""
ADR Discovery from Code Analysis.

Discovers implicit Architecture Decision Records (ADRs) from existing codebases
during template-create operations. Analyzes code structure, dependencies, patterns,
and conventions to extract decisions that were made but never formally documented.

Public API:
    DiscoveryCategory: Enum for types of discovered decisions
    DiscoveredDecision: Dataclass representing a discovered decision
    ADRDiscoverer: Main class for discovering ADRs from codebases
    discover_adrs_from_codebase: Convenience function for full discovery
    create_discovered_adrs: Create ADR entities from discoveries

Example:
    from guardkit.knowledge.adr_discovery import discover_adrs_from_codebase

    discoveries = await discover_adrs_from_codebase(Path("./my-project"))
    for d in discoveries:
        print(f"{d.title} (confidence: {d.confidence:.0%})")
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.knowledge.adr_service import ADRService

from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger

logger = logging.getLogger(__name__)


class DiscoveryCategory(Enum):
    """Category of discovered decision.

    Values:
        STRUCTURAL: Directory layout and file organization decisions
        TECHNOLOGY: Technology stack and dependency decisions
        PATTERN: Code patterns and design decisions
        CONVENTION: Naming and coding convention decisions
    """
    STRUCTURAL = "structural"
    TECHNOLOGY = "technology"
    PATTERN = "pattern"
    CONVENTION = "convention"


@dataclass
class DiscoveredDecision:
    """A decision discovered from code analysis.

    Represents an implicit architectural decision found in the codebase
    that was never formally documented.

    Attributes:
        category: Type of decision (structural, technology, pattern, convention)
        title: Brief title describing the decision
        description: Detailed description of what was discovered
        evidence: List of files/patterns supporting this decision
        confidence: Confidence score (0.0 to 1.0)
        exceptions: List of violations or exceptions to the pattern
    """
    category: DiscoveryCategory
    title: str
    description: str
    evidence: List[str]
    confidence: float
    exceptions: List[str] = field(default_factory=list)


class ADRDiscoverer:
    """Discovers implicit ADRs from codebase analysis.

    Analyzes directory structure, dependencies, code patterns, and naming
    conventions to extract decisions that exist in code but were never
    formally documented.

    Attributes:
        source_path: Path to the codebase to analyze
        analysis_results: Optional pre-computed analysis results
        confidence_threshold: Minimum confidence for discoveries

    Example:
        discoverer = ADRDiscoverer(Path("./my-project"))
        structural = discoverer.analyze_directory_structure()
        tech = discoverer.analyze_dependencies()
    """

    # Standard file patterns that indicate feature-based organization
    STANDARD_FILES = {"router.py", "schemas.py", "models.py", "crud.py", "service.py"}

    # Framework indicators in dependencies
    FRAMEWORK_INDICATORS = {
        "fastapi": ("FastAPI", "Async Python web framework"),
        "django": ("Django", "Python web framework"),
        "flask": ("Flask", "Python micro web framework"),
        "sqlalchemy": ("SQLAlchemy", "Python ORM"),
        "pydantic": ("Pydantic", "Python data validation"),
        "redis": ("Redis", "In-memory data store"),
        "celery": ("Celery", "Distributed task queue"),
        "pytest": ("pytest", "Python testing framework"),
        "uvicorn": ("Uvicorn", "ASGI server"),
        "asyncio": ("asyncio", "Async support"),
    }

    # Pattern indicators to look for in code
    PATTERN_INDICATORS = {
        "Depends(": "Dependency Injection",
        "async def": "Async/Await pattern",
        "@router": "Router/Blueprint pattern",
        "@app": "Application routes",
        "Repository": "Repository pattern",
        "BaseModel": "Pydantic models",
        "class.*Service": "Service layer pattern",
    }

    # Naming convention patterns
    NAMING_PATTERNS = {
        r"(\w+)Create": "{Entity}Create",
        r"(\w+)Update": "{Entity}Update",
        r"(\w+)Public": "{Entity}Public",
        r"(\w+)InDB": "{Entity}InDB",
        r"(\w+)Response": "{Entity}Response",
        r"(\w+)Request": "{Entity}Request",
    }

    def __init__(
        self,
        source_path: Path,
        analysis_results: Optional[Dict] = None,
        confidence_threshold: float = 0.7,
    ):
        """Initialize ADRDiscoverer with source path.

        Args:
            source_path: Path to the codebase to analyze
            analysis_results: Optional pre-computed analysis results
            confidence_threshold: Minimum confidence for discoveries (default: 0.7)
        """
        self.source_path = source_path
        self.analysis_results = analysis_results or {}
        self.confidence_threshold = confidence_threshold

    def analyze_directory_structure(self) -> List[DiscoveredDecision]:
        """Analyze directory structure for organizational patterns.

        Looks for feature-based organization, standard file naming,
        and other structural patterns.

        Returns:
            List of discovered structural decisions.
        """
        decisions = []

        # Check for src directory
        src_dir = self.source_path / "src"
        if not src_dir.exists():
            # Try looking in the root
            src_dir = self.source_path
            if not any(src_dir.glob("*/router.py")) and not any(src_dir.glob("*/models.py")):
                return decisions

        # Find feature directories
        feature_dirs = []
        standard_files_count = {}

        try:
            for child in src_dir.iterdir():
                if child.is_dir() and not child.name.startswith((".", "_", "__")):
                    files = {f.name for f in child.glob("*.py") if f.is_file()}

                    # Check for standard files
                    matching_files = files & self.STANDARD_FILES
                    if matching_files:
                        feature_dirs.append(child)
                        standard_files_count[child.name] = len(matching_files)

        except PermissionError:
            logger.warning(f"Permission denied accessing {src_dir}")
            return decisions

        # Calculate feature-based organization confidence
        if feature_dirs:
            total_features = len(feature_dirs)
            avg_standard_files = sum(standard_files_count.values()) / total_features

            # Confidence based on how many features follow the pattern
            confidence = min(avg_standard_files / 4, 1.0)  # 4 is typical max standard files

            if confidence >= 0.5:  # Lower threshold for detection
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.STRUCTURAL,
                    title="Feature-based organization with standard file naming",
                    description="Code is organized by feature/domain with consistent file patterns",
                    evidence=[str(d.relative_to(self.source_path)) for d in feature_dirs[:5]],
                    confidence=confidence,
                    exceptions=[],
                ))

        return decisions

    def analyze_dependencies(self) -> List[DiscoveredDecision]:
        """Analyze dependencies for technology decisions.

        Parses requirements.txt, pyproject.toml, and other dependency
        files to identify technology stack decisions.

        Returns:
            List of discovered technology decisions.
        """
        decisions = []
        detected_frameworks: Dict[str, str] = {}

        # Check requirements.txt
        req_file = self.source_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text()
                for framework, (name, desc) in self.FRAMEWORK_INDICATORS.items():
                    if framework.lower() in content.lower():
                        detected_frameworks[framework] = name
            except (PermissionError, UnicodeDecodeError):
                logger.warning(f"Could not read {req_file}")

        # Check pyproject.toml
        pyproject = self.source_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                for framework, (name, desc) in self.FRAMEWORK_INDICATORS.items():
                    if framework.lower() in content.lower():
                        detected_frameworks[framework] = name
            except (PermissionError, UnicodeDecodeError):
                logger.warning(f"Could not read {pyproject}")

        # Create decisions for detected frameworks
        if detected_frameworks:
            # Primary framework decision
            primary_frameworks = []
            if "fastapi" in detected_frameworks:
                primary_frameworks.append("FastAPI")
            if "django" in detected_frameworks:
                primary_frameworks.append("Django")
            if "flask" in detected_frameworks:
                primary_frameworks.append("Flask")

            if primary_frameworks:
                framework_str = ", ".join(primary_frameworks)
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.TECHNOLOGY,
                    title=f"{framework_str} web framework",
                    description=f"Uses {framework_str} for web API development",
                    evidence=[
                        str(f.relative_to(self.source_path))
                        for f in [req_file, pyproject]
                        if f.exists()
                    ],
                    confidence=1.0,  # Direct evidence
                    exceptions=[],
                ))

            # Database/ORM decision
            if "sqlalchemy" in detected_frameworks:
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.TECHNOLOGY,
                    title="SQLAlchemy ORM for database access",
                    description="Uses SQLAlchemy as the Object-Relational Mapper",
                    evidence=[
                        str(f.relative_to(self.source_path))
                        for f in [req_file, pyproject]
                        if f.exists()
                    ],
                    confidence=1.0,
                    exceptions=[],
                ))

            # Full stack decision if multiple frameworks
            if len(detected_frameworks) >= 3:
                framework_list = ", ".join(sorted(detected_frameworks.values()))
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.TECHNOLOGY,
                    title="Python async web stack",
                    description=f"Technology stack includes: {framework_list}",
                    evidence=[
                        str(f.relative_to(self.source_path))
                        for f in [req_file, pyproject]
                        if f.exists()
                    ],
                    confidence=1.0,
                    exceptions=[],
                ))

        return decisions

    def analyze_code_patterns(self) -> List[DiscoveredDecision]:
        """Analyze code for common patterns.

        Looks for dependency injection, async patterns, repository pattern,
        and other design patterns in the codebase.

        Returns:
            List of discovered pattern decisions.
        """
        decisions = []
        pattern_evidence: Dict[str, List[str]] = {
            pattern: [] for pattern in self.PATTERN_INDICATORS.values()
        }
        pattern_counts: Dict[str, int] = {
            pattern: 0 for pattern in self.PATTERN_INDICATORS.values()
        }

        total_py_files = 0

        # Scan Python files
        try:
            for py_file in self.source_path.rglob("*.py"):
                if any(
                    part.startswith((".", "_", "__", "test", "venv", "env"))
                    for part in py_file.parts
                ):
                    continue

                try:
                    content = py_file.read_text(errors="ignore")
                    total_py_files += 1

                    for indicator, pattern_name in self.PATTERN_INDICATORS.items():
                        # Use regex for patterns with special chars
                        if ".*" in indicator:
                            if re.search(indicator, content):
                                pattern_counts[pattern_name] += content.count(
                                    indicator.replace(".*", "")
                                ) or 1
                                rel_path = str(py_file.relative_to(self.source_path))
                                if rel_path not in pattern_evidence[pattern_name]:
                                    pattern_evidence[pattern_name].append(rel_path)
                        elif indicator in content:
                            count = content.count(indicator)
                            pattern_counts[pattern_name] += count
                            rel_path = str(py_file.relative_to(self.source_path))
                            if rel_path not in pattern_evidence[pattern_name]:
                                pattern_evidence[pattern_name].append(rel_path)

                except (PermissionError, UnicodeDecodeError):
                    continue

        except PermissionError:
            logger.warning(f"Permission denied scanning {self.source_path}")
            return decisions

        # Create decisions for detected patterns
        if total_py_files > 0:
            # Dependency Injection
            di_name = "Dependency Injection"
            if pattern_counts[di_name] >= 3:
                confidence = min(pattern_counts[di_name] / 10, 1.0)
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.PATTERN,
                    title="Dependency Injection pattern",
                    description="Uses FastAPI Depends() for dependency injection",
                    evidence=pattern_evidence[di_name][:10],
                    confidence=confidence,
                    exceptions=[],
                ))

            # Async pattern
            async_name = "Async/Await pattern"
            if pattern_counts[async_name] >= 3:
                confidence = min(pattern_counts[async_name] / 10, 1.0)
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.PATTERN,
                    title="Async/await programming model",
                    description="Uses async/await for non-blocking I/O operations",
                    evidence=pattern_evidence[async_name][:10],
                    confidence=confidence,
                    exceptions=[],
                ))

            # Router pattern
            router_name = "Router/Blueprint pattern"
            if pattern_counts[router_name] >= 2:
                confidence = min(pattern_counts[router_name] / 5, 1.0)
                decisions.append(DiscoveredDecision(
                    category=DiscoveryCategory.PATTERN,
                    title="Router/Blueprint API organization",
                    description="Uses routers/blueprints to organize API endpoints",
                    evidence=pattern_evidence[router_name][:10],
                    confidence=confidence,
                    exceptions=[],
                ))

        return decisions

    def analyze_naming_conventions(self) -> List[DiscoveredDecision]:
        """Analyze naming conventions in code.

        Looks for consistent naming patterns like Pydantic schema naming,
        class naming conventions, and file naming patterns.

        Returns:
            List of discovered convention decisions.
        """
        decisions = []
        naming_matches: Dict[str, List[str]] = {
            pattern: [] for pattern in self.NAMING_PATTERNS.values()
        }

        # Scan Python files for class definitions
        try:
            for py_file in self.source_path.rglob("*.py"):
                if any(
                    part.startswith((".", "_", "__", "test", "venv", "env"))
                    for part in py_file.parts
                ):
                    continue

                try:
                    content = py_file.read_text(errors="ignore")

                    # Find class definitions
                    class_matches = re.findall(r"class\s+(\w+)", content)

                    for class_name in class_matches:
                        for regex, pattern_name in self.NAMING_PATTERNS.items():
                            if re.match(regex, class_name):
                                if class_name not in naming_matches[pattern_name]:
                                    naming_matches[pattern_name].append(class_name)

                except (PermissionError, UnicodeDecodeError):
                    continue

        except PermissionError:
            logger.warning(f"Permission denied scanning {self.source_path}")
            return decisions

        # Check for Pydantic naming convention (UserCreate, UserUpdate, etc.)
        schema_patterns = ["{Entity}Create", "{Entity}Update", "{Entity}Public", "{Entity}InDB"]
        schema_matches = []
        for pattern in schema_patterns:
            schema_matches.extend(naming_matches.get(pattern, []))

        if len(schema_matches) >= 3:
            # Multiple schema classes follow pattern
            confidence = min(len(schema_matches) / 8, 1.0)
            decisions.append(DiscoveredDecision(
                category=DiscoveryCategory.CONVENTION,
                title="Pydantic schema naming convention",
                description="Pydantic schemas follow {Entity}{Operation} naming pattern",
                evidence=schema_matches[:10],
                confidence=confidence,
                exceptions=[],
            ))

        return decisions


async def discover_adrs_from_codebase(
    source_path: Path,
    analysis_results: Optional[Dict] = None,
    confidence_threshold: float = 0.7,
) -> List[DiscoveredDecision]:
    """Discover implicit ADRs from code analysis.

    Main entry point for ADR discovery. Analyzes directory structure,
    dependencies, code patterns, and naming conventions to find
    implicit architectural decisions.

    Args:
        source_path: Path to the codebase to analyze
        analysis_results: Optional pre-computed analysis results
        confidence_threshold: Minimum confidence for discoveries (default: 0.7)

    Returns:
        List of discovered decisions meeting the confidence threshold.

    Example:
        discoveries = await discover_adrs_from_codebase(Path("./project"))
        for d in discoveries:
            print(f"{d.title} ({d.confidence:.0%})")
    """
    discoverer = ADRDiscoverer(
        source_path,
        analysis_results=analysis_results,
        confidence_threshold=confidence_threshold,
    )

    all_discoveries = []

    # 1. Structural decisions
    structural = discoverer.analyze_directory_structure()
    all_discoveries.extend(structural)

    # 2. Technology decisions
    tech = discoverer.analyze_dependencies()
    all_discoveries.extend(tech)

    # 3. Pattern decisions
    patterns = discoverer.analyze_code_patterns()
    all_discoveries.extend(patterns)

    # 4. Convention decisions
    conventions = discoverer.analyze_naming_conventions()
    all_discoveries.extend(conventions)

    # Filter by confidence threshold
    filtered = [d for d in all_discoveries if d.confidence >= confidence_threshold]

    return filtered


async def create_discovered_adrs(
    discoveries: List[DiscoveredDecision],
    template_id: str,
    adr_service: Optional["ADRService"] = None,
    confidence_threshold: float = 0.7,
) -> List[ADREntity]:
    """Create ADR entities from discovered decisions.

    Converts DiscoveredDecision objects into ADREntity objects and
    optionally persists them via the ADRService.

    Args:
        discoveries: List of discovered decisions
        template_id: ID of the template being created
        adr_service: Optional ADRService for persistence
        confidence_threshold: Minimum confidence for ADR creation (default: 0.7)

    Returns:
        List of created ADREntity objects.

    Example:
        discoveries = await discover_adrs_from_codebase(path)
        adrs = await create_discovered_adrs(discoveries, "my-template", service)
    """
    adrs = []

    for discovery in discoveries:
        # Filter by confidence
        if discovery.confidence < confidence_threshold:
            continue

        # Create ADR entity
        adr = ADREntity(
            id="",  # Will be generated
            title=discovery.title,
            status=ADRStatus.ACCEPTED,
            trigger=ADRTrigger.DISCOVERED,
            context=f"Discovered during template-create analysis of {template_id}",
            decision=discovery.description,
            rationale="",  # Unknown for discovered ADRs
            consequences=[f"Evidence: {', '.join(discovery.evidence[:5])}"],
            tags=[discovery.category.value, "discovered", template_id],
            confidence=discovery.confidence,
        )

        # Persist if service available
        if adr_service:
            try:
                adr_id = await adr_service.create_adr(adr)
                if adr_id:
                    adr.id = adr_id
            except Exception as e:
                logger.warning(f"Failed to persist ADR: {e}")

        # Generate ID if not set
        if not adr.id:
            import time
            adr.id = f"ADR-DISC-{int(time.time()) % 10000:04d}"

        adrs.append(adr)

    return adrs
