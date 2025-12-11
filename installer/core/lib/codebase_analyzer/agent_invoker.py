"""
Agent Invocation Layer

Handles communication with the architectural-reviewer agent for deep codebase
analysis. Implements proper error handling and graceful fallback when the agent
is unavailable.

Following architectural review recommendations:
- Extract agent invocation to separate class (SRP)
- Use Protocol for dependency injection (DIP)
- Handle errors gracefully with fallback mechanisms
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Protocol, Dict, Any, List

from .models import AgentInvocationError
from .exclusions import get_source_files

logger = logging.getLogger(__name__)


class AgentCommunicator(Protocol):
    """Protocol for agent communication (DIP - Dependency Inversion Principle)."""

    def invoke_agent(self, prompt: str, agent_name: str) -> str:
        """
        Invoke an agent with a prompt.

        Args:
            prompt: The prompt to send to the agent
            agent_name: Name of the agent to invoke

        Returns:
            Agent response as string

        Raises:
            AgentInvocationError: If invocation fails
        """
        ...


class ArchitecturalReviewerInvoker:
    """
    Invokes the architectural-reviewer agent for codebase analysis.

    This class follows SRP by focusing solely on agent communication,
    delegating prompt construction to PromptBuilder and response parsing
    to ResponseParser.

    TASK-769D: Now supports optional bridge_invoker for checkpoint-resume pattern.
    """

    def __init__(
        self,
        agent_path: Optional[Path] = None,
        timeout_seconds: int = 120,
        bridge_invoker: Optional[any] = None  # TASK-769D: Optional bridge invoker
    ):
        """
        Initialize agent invoker.

        Args:
            agent_path: Path to architectural-reviewer.md agent file.
                       Defaults to installer/core/agents/architectural-reviewer.md
            timeout_seconds: Maximum time to wait for agent response
            bridge_invoker: Optional AgentBridgeInvoker for checkpoint-resume (TASK-769D)
        """
        if agent_path is None:
            # Default to global agents directory
            self.agent_path = Path.home() / ".agentecflow" / "agents" / "architectural-reviewer.md"
        else:
            self.agent_path = agent_path

        self.timeout_seconds = timeout_seconds
        self.bridge_invoker = bridge_invoker  # TASK-769D: Store bridge invoker

    def is_available(self) -> bool:
        """
        Check if the architectural-reviewer agent is available.

        Returns:
            True if agent file exists and is accessible
        """
        return self.agent_path.exists() and self.agent_path.is_file()

    def invoke_agent(self, prompt: str, agent_name: str = "architectural-reviewer") -> str:
        """
        Invoke the architectural-reviewer agent with a prompt.

        TASK-769D: Now uses AgentBridgeInvoker if provided, otherwise falls back to error.

        Args:
            prompt: Analysis prompt with codebase context
            agent_name: Name of the agent (default: architectural-reviewer)

        Returns:
            Agent response as JSON string

        Raises:
            AgentInvocationError: If invocation fails or agent unavailable
        """
        if not self.is_available():
            raise AgentInvocationError(
                f"Agent not available at {self.agent_path}. "
                "Ensure GuardKit is properly installed."
            )

        try:
            # TASK-769D: Use bridge invoker if provided
            if self.bridge_invoker is not None:
                logger.info("Using AgentBridgeInvoker for checkpoint-resume pattern")
                response = self.bridge_invoker.invoke(
                    agent_name=agent_name,
                    prompt=prompt,
                    timeout_seconds=self.timeout_seconds
                )
                return response

            # TASK-769D: No bridge invoker - raise error to trigger fallback
            raise AgentInvocationError(
                "Agent invocation not yet implemented. Using fallback heuristics."
            )

        except subprocess.TimeoutExpired as e:
            raise AgentInvocationError(
                f"Agent invocation timed out after {self.timeout_seconds} seconds"
            ) from e
        except subprocess.CalledProcessError as e:
            raise AgentInvocationError(
                f"Agent invocation failed with exit code {e.returncode}: {e.stderr}"
            ) from e
        except Exception as e:
            raise AgentInvocationError(
                f"Unexpected error during agent invocation: {str(e)}"
            ) from e

    def test_connection(self) -> dict:
        """
        Test connection to agent with a simple health check.

        Returns:
            Dictionary with status information:
            {
                "available": bool,
                "agent_path": str,
                "error": Optional[str]
            }
        """
        result = {
            "available": False,
            "agent_path": str(self.agent_path),
            "error": None
        }

        if not self.agent_path.exists():
            result["error"] = "Agent file not found"
            return result

        if not self.agent_path.is_file():
            result["error"] = "Agent path is not a file"
            return result

        try:
            # Try a simple invocation
            test_prompt = "Health check: Respond with OK if you're available."
            # In real implementation, this would call invoke_agent
            # For now, we just check file availability
            result["available"] = True
        except Exception as e:
            result["error"] = str(e)

        return result


class HeuristicAnalyzer:
    """
    Fallback heuristic analyzer when agent is unavailable.

    Provides basic pattern detection and structure analysis using
    file system inspection and simple heuristics. Not as sophisticated
    as the AI agent, but provides reasonable defaults.

    TASK-769D: Now accepts optional file_samples for better context.
    """

    # TASK-FIX-6855 Issue 2: Extended layer patterns dictionary (DIP recommendation)
    EXTENDED_LAYER_PATTERNS = {
        "routes/": ("Presentation", "Route handlers and endpoints", ["Application"]),
        "controllers/": ("Presentation", "API controllers", ["Application"]),
        "views/": ("Presentation", "View templates", ["Application"]),
        "endpoints/": ("Presentation", "API endpoints", ["Application"]),
        "lib/": ("Infrastructure", "Utility libraries", []),
        "utils/": ("Shared", "Utility functions", []),
        "helpers/": ("Shared", "Helper functions", []),
        "upload/": ("Infrastructure", "File upload utilities", []),
        "scripts/": ("Infrastructure", "Automation scripts", []),
        "src/": ("Application", "Source code", ["Domain"]),
        "components/": ("Presentation", "UI components", ["Application"]),
        "stores/": ("Application", "State management", ["Domain"]),
        "services/": ("Application", "Business services", ["Domain"]),
        "middleware/": ("Infrastructure", "Middleware components", ["Application"]),

        # MVVM ViewModels (TASK-FIX-LAYER-D6E0)
        "viewmodels/": ("ViewModels", "MVVM ViewModels", ["Domain", "Services"]),
        "ViewModels/": ("ViewModels", "MVVM ViewModels", ["Domain", "Services"]),

        # Business Logic Engines (TASK-FIX-LAYER-D6E0)
        "engines/": ("Engines", "Business logic orchestration", ["Domain", "Services", "Data-Access"]),
        "Engines/": ("Engines", "Business logic orchestration", ["Domain", "Services", "Data-Access"]),

        # Handlers (CQRS) (TASK-FIX-LAYER-D6E0)
        "handlers/": ("Handlers", "Command/Query handlers", ["Domain", "Services"]),
        "Handlers/": ("Handlers", "Command/Query handlers", ["Domain", "Services"]),

        # Processors (TASK-FIX-LAYER-D6E0)
        "processors/": ("Processors", "Data processors", ["Domain", "Services"]),
        "Processors/": ("Processors", "Data processors", ["Domain", "Services"]),
    }

    def __init__(self, codebase_path: Path, file_samples: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize heuristic analyzer.

        Args:
            codebase_path: Path to codebase to analyze
            file_samples: Optional list of file samples from stratified sampling (TASK-769D)
        """
        self.codebase_path = codebase_path
        self.file_samples = file_samples  # TASK-769D: Store file samples

    def analyze(self) -> dict:
        """
        Perform heuristic analysis of codebase.

        Returns:
            Dictionary with analysis results matching CodebaseAnalysis structure
        """
        # Detect primary language
        language = self._detect_language()

        # Detect frameworks
        frameworks = self._detect_frameworks(language)

        # Detect testing frameworks
        testing_frameworks = self._detect_testing_frameworks(language)

        # Detect patterns
        patterns = self._detect_patterns()

        # Detect architecture style
        arch_style = self._detect_architecture_style()

        return {
            "technology": {
                "primary_language": language,
                "frameworks": frameworks,
                "testing_frameworks": testing_frameworks,
                "build_tools": self._detect_build_tools(language),
                "databases": self._detect_databases(),
                "infrastructure": self._detect_infrastructure(),
                "confidence": {
                    "level": "medium",
                    "percentage": 75.0,
                    "reasoning": "Heuristic detection based on file patterns"
                }
            },
            "architecture": {
                "patterns": patterns,
                "architectural_style": arch_style,
                "layers": self._detect_layers(),
                "key_abstractions": self._detect_abstractions(language),
                "dependency_flow": "Inward toward domain (assumed)",
                "confidence": {
                    "level": "medium",
                    "percentage": 70.0,
                    "reasoning": "Heuristic detection without deep semantic analysis"
                }
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": ["Standard project structure"],
                "improvements": ["Run full architectural review for detailed insights"],
                "confidence": {
                    "level": "low",
                    "percentage": 60.0,
                    "reasoning": "Quality metrics require deep analysis - use agent for accurate results"
                }
            },
            "example_files": self._get_example_files(language),
            "agent_used": False,
            "fallback_reason": "Agent not available - using heuristic analysis"
        }

    def _detect_language(self) -> str:
        """Detect primary programming language, excluding build artifacts."""
        file_counts = {}
        extensions = {
            ".py": "Python",
            ".ts": "TypeScript",
            ".js": "JavaScript",
            ".cs": "C#",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP"
        }

        for ext, lang in extensions.items():
            # Use get_source_files to exclude build artifacts
            source_files = get_source_files(self.codebase_path, extensions=[ext])
            count = len(source_files)
            if count > 0:
                file_counts[lang] = count

        if not file_counts:
            return "Unknown"

        return max(file_counts.items(), key=lambda x: x[1])[0]

    def _detect_frameworks(self, language: str) -> list:
        """Detect web/API frameworks."""
        frameworks = []

        # Python frameworks
        if language == "Python":
            if (self.codebase_path / "requirements.txt").exists():
                requirements = (self.codebase_path / "requirements.txt").read_text()
                if "fastapi" in requirements.lower():
                    frameworks.append("FastAPI")
                if "flask" in requirements.lower():
                    frameworks.append("Flask")
                if "django" in requirements.lower():
                    frameworks.append("Django")

        # TypeScript/JavaScript frameworks
        elif language in ["TypeScript", "JavaScript"]:
            if (self.codebase_path / "package.json").exists():
                try:
                    package_json = json.loads((self.codebase_path / "package.json").read_text())
                    deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}

                    if "next" in deps:
                        frameworks.append("Next.js")
                    if "react" in deps:
                        frameworks.append("React")
                    if "@nestjs/core" in deps:
                        frameworks.append("NestJS")
                    if "express" in deps:
                        frameworks.append("Express")
                except json.JSONDecodeError:
                    pass

        # .NET frameworks
        elif language == "C#":
            if list(self.codebase_path.rglob("*.csproj")):
                frameworks.append(".NET")
                # Check for specific frameworks in csproj files
                for csproj in self.codebase_path.rglob("*.csproj"):
                    content = csproj.read_text()
                    if "Microsoft.NET.Sdk.Web" in content:
                        frameworks.append("ASP.NET Core")
                    if "Maui" in content:
                        frameworks.append(".NET MAUI")

        return frameworks

    def _detect_testing_frameworks(self, language: str) -> list:
        """Detect testing frameworks."""
        frameworks = []

        if language == "Python":
            if (self.codebase_path / "pytest.ini").exists() or \
               any(self.codebase_path.rglob("test_*.py")):
                frameworks.append("pytest")
        elif language in ["TypeScript", "JavaScript"]:
            if (self.codebase_path / "vitest.config.ts").exists():
                frameworks.append("Vitest")
            if (self.codebase_path / "jest.config.js").exists():
                frameworks.append("Jest")
            if (self.codebase_path / "playwright.config.ts").exists():
                frameworks.append("Playwright")
        elif language == "C#":
            frameworks.append("xUnit / NUnit")

        return frameworks

    def _detect_build_tools(self, language: str) -> list:
        """Detect build tools and package managers."""
        tools = []

        if (self.codebase_path / "package.json").exists():
            tools.append("npm")
        if (self.codebase_path / "requirements.txt").exists():
            tools.append("pip")
        if (self.codebase_path / "Pipfile").exists():
            tools.append("pipenv")
        if (self.codebase_path / "pyproject.toml").exists():
            tools.append("poetry")

        return tools

    def _detect_databases(self) -> list:
        """Detect database technologies."""
        databases = []
        # Basic detection - could be enhanced
        return databases

    def _detect_infrastructure(self) -> list:
        """Detect infrastructure tools."""
        infra = []

        if (self.codebase_path / "Dockerfile").exists():
            infra.append("Docker")
        if (self.codebase_path / "docker-compose.yml").exists():
            infra.append("Docker Compose")

        return infra

    # Pattern definitions with file glob patterns
    PATTERN_DETECTION_CONFIG = {
        'Repository': {
            'patterns': ["*[Rr]epository*.py", "*[Rr]epository*.ts", "*[Rr]epository*.cs", "*[Rr]epository*.java"],
            'description': "Data access abstraction layer"
        },
        'Factory': {
            'patterns': ["*[Ff]actory*.py", "*[Ff]actory*.ts", "*[Ff]actory*.cs", "*[Ff]actory*.java"],
            'description': "Object creation patterns"
        },
        'Service Layer': {
            'patterns': ["*[Ss]ervice*.py", "*[Ss]ervice*.ts", "*[Ss]ervice*.cs", "*[Ss]ervice*.java"],
            'description': "Business logic services"
        },
        'Engine': {
            'patterns': ["*[Ee]ngine*.py", "*[Ee]ngine*.ts", "*[Ee]ngine*.cs", "*[Ee]ngine*.java"],
            'description': "Business logic orchestration"
        },
        'MVVM': {
            'patterns': ["*[Vv]iew[Mm]odel*.py", "*[Vv]iew[Mm]odel*.ts", "*[Vv]iew[Mm]odel*.cs", "*[Vv]iew[Mm]odel*.dart"],
            'description': "Model-View-ViewModel pattern"
        },
        'Railway-Oriented Programming': {
            'patterns': ["*[Ee]rror[Oo]r*.cs", "*[Rr]esult*.cs", "*[Rr]ailway*.py", "*[Ee]ither*.ts"],
            'description': "Functional error handling"
        },
        'Entity': {
            'patterns': ["*[Ee]ntity*.py", "*[Ee]ntity*.cs", "*[Ee]ntity*.java"],
            'description': "Domain entities"
        },
        'Model': {
            'patterns': ["*/models/*.py", "*/models/*.ts", "*/model/*.cs"],
            'description': "Data models"
        },
        'Controller': {
            'patterns': ["*[Cc]ontroller*.py", "*[Cc]ontroller*.ts", "*[Cc]ontroller*.cs", "*[Cc]ontroller*.java"],
            'description': "Request handlers (MVC)"
        },
        'Handler': {
            'patterns': ["*[Hh]andler*.py", "*[Hh]andler*.ts", "*[Hh]andler*.cs"],
            'description': "Event/command handlers"
        },
        'Validator': {
            'patterns': ["*[Vv]alidator*.py", "*[Vv]alidator*.ts", "*[Vv]alidator*.cs"],
            'description': "Input validation"
        },
        'Mapper': {
            'patterns': ["*[Mm]apper*.py", "*[Mm]apper*.ts", "*[Mm]apper*.cs"],
            'description': "Object mapping/transformation"
        },
        'Builder': {
            'patterns': ["*[Bb]uilder*.py", "*[Bb]uilder*.ts", "*[Bb]uilder*.cs"],
            'description': "Complex object construction"
        },
        'View': {
            'patterns': ["*/views/*.py", "*/views/*.ts", "*[Vv]iew.cs", "*[Vv]iew.xaml"],
            'description': "UI views/templates"
        }
    }

    def _detect_patterns(self) -> list:
        """
        Detect design patterns from directory structure and file naming.

        Returns:
            List of detected pattern names

        Note:
            This is a heuristic fallback when AI analysis is unavailable.
            It scans the codebase for files matching known pattern conventions.
        """
        detected_patterns = []

        for pattern_name, config in self.PATTERN_DETECTION_CONFIG.items():
            file_patterns = config['patterns']

            # Check if any files match the pattern
            for file_pattern in file_patterns:
                try:
                    matches = list(self.codebase_path.rglob(file_pattern))
                    if matches:
                        detected_patterns.append(pattern_name)
                        logger.debug(f"Detected {pattern_name} pattern: {len(matches)} files")
                        break  # Found pattern, no need to check other file patterns
                except Exception as e:
                    logger.debug(f"Error checking pattern {file_pattern}: {e}")

        return detected_patterns

    def _detect_architecture_style(self) -> str:
        """Detect overall architectural style."""
        # Check for common architecture indicators
        has_domain = any(self.codebase_path.rglob("domain/*")) or \
                     any(self.codebase_path.rglob("Domain/*"))
        has_application = any(self.codebase_path.rglob("application/*")) or \
                         any(self.codebase_path.rglob("Application/*"))
        has_infrastructure = any(self.codebase_path.rglob("infrastructure/*")) or \
                            any(self.codebase_path.rglob("Infrastructure/*"))

        if has_domain and has_application and has_infrastructure:
            return "Clean Architecture / Hexagonal"

        if any(self.codebase_path.rglob("src/*")) and any(self.codebase_path.rglob("tests/*")):
            return "Layered Architecture"

        return "Standard Structure"

    def _detect_layers(self) -> list:
        """Detect architectural layers.

        TASK-FIX-6855 Issue 2: Enhanced with extended patterns support.
        """
        layers = []

        # This is a simplified heuristic
        if any(self.codebase_path.rglob("domain/*")):
            layers.append({
                "name": "Domain",
                "description": "Core business logic",
                "typical_files": ["models", "entities", "value objects"],
                "dependencies": []
            })

        if any(self.codebase_path.rglob("application/*")):
            layers.append({
                "name": "Application",
                "description": "Use cases and application services",
                "typical_files": ["services", "use cases"],
                "dependencies": ["Domain"]
            })

        # TASK-FIX-6855 Issue 2: Add extended patterns detection (SRP recommendation)
        extended_layers = self._detect_extended_patterns()
        layers.extend(extended_layers)

        return layers

    def _detect_extended_patterns(self) -> list:
        """Detect layers from extended patterns.

        TASK-FIX-6855 Issue 2: Separate method for extended pattern detection (SRP).

        Returns:
            List of LayerInfo dictionaries for extended patterns found
        """
        layers = []
        detected_layers = set()  # Track unique layers

        for pattern, (layer_name, description, dependencies) in self.EXTENDED_LAYER_PATTERNS.items():
            # Check if pattern exists in codebase
            pattern_path = pattern.rstrip('/')
            if any(self.codebase_path.rglob(f"{pattern_path}/*")) or \
               any(self.codebase_path.rglob(f"*/{pattern_path}/*")):
                # Only add if we haven't already detected this layer
                if layer_name not in detected_layers:
                    layers.append({
                        "name": layer_name,
                        "description": description,
                        "typical_files": [pattern],
                        "dependencies": dependencies
                    })
                    detected_layers.add(layer_name)
                    logger.debug(f"Detected {layer_name} layer from {pattern} pattern")

        return layers

    def _detect_abstractions(self, language: str) -> list:
        """Detect key domain abstractions."""
        abstractions = []

        # This would require more sophisticated analysis
        # For now, return empty or basic guesses

        return abstractions

    def _get_example_files(self, language: str) -> list:
        """
        Get example files from file_samples if available, otherwise find them.

        TASK-769D: Converts file_samples to example_files format if provided.
        TASK-0CE5: Enhanced to provide richer example file metadata.

        Args:
            language: Primary programming language

        Returns:
            List of example file dicts with path, purpose, layer, patterns, concepts
        """
        # TASK-769D & TASK-0CE5: If file_samples provided, convert to example_files format
        if self.file_samples is not None and len(self.file_samples) > 0:
            logger.info(f"Converting {len(self.file_samples)} file_samples to example_files format (fallback mode)")
            examples = []
            for sample in self.file_samples[:15]:  # Limit to 15 examples (increased from 10)
                # TASK-0CE5: Infer layer from path
                path = sample.get("path", sample.get("relative_path", ""))
                layer = self._infer_layer_from_path(path)

                # TASK-0CE5: Better purpose from category
                category = sample.get("category", "Source file")
                purpose = self._infer_purpose_from_category(category, path)

                # Convert from file_sample format to example_file format
                examples.append({
                    "path": path,
                    "purpose": purpose,
                    "layer": layer,
                    "patterns_used": [],  # Could be inferred from content
                    "key_concepts": []     # Could be inferred from content
                })

            logger.info(f"Converted {len(examples)} example files for template generation")
            return examples

        # Fallback: Use original _find_example_files logic
        logger.warning("No file_samples available - using basic file discovery")
        return self._find_example_files(language)

    def _infer_layer_from_path(self, path: str) -> Optional[str]:
        """
        Infer architectural layer from file path.

        TASK-0CE5: Helper for fallback mode to provide better metadata.
        TASK-FIX-LAYER-D6E0: Added ViewModels, Engines, Handlers, Processors layers.

        Args:
            path: File path

        Returns:
            Layer name or None
        """
        path_lower = path.lower()

        # Check specialized layers first (more specific patterns)
        # ViewModels layer (TASK-FIX-LAYER-D6E0)
        if any(x in path_lower for x in ["viewmodel", "viewmodels", "/vm/"]):
            return "ViewModels"

        # Engines layer (TASK-FIX-LAYER-D6E0)
        if any(x in path_lower for x in ["engine", "engines", "businesslogic"]):
            return "Engines"

        # Handlers layer (TASK-FIX-LAYER-D6E0)
        if any(x in path_lower for x in ["handler", "handlers", "commandhandler", "queryhandler"]):
            return "Handlers"

        # Processors layer (TASK-FIX-LAYER-D6E0)
        if any(x in path_lower for x in ["processor", "processors", "pipeline"]):
            return "Processors"

        # Common layer patterns (existing)
        if any(layer in path_lower for layer in ["domain", "entities", "models"]):
            return "Domain"
        elif any(layer in path_lower for layer in ["application", "usecases", "services"]):
            return "Application"
        elif any(layer in path_lower for layer in ["infrastructure", "data", "repository", "repositories"]):
            return "Infrastructure"
        elif any(layer in path_lower for layer in ["web", "api", "controllers", "routes", "endpoints"]):
            return "Presentation"
        elif any(layer in path_lower for layer in ["test", "tests", "spec", "specs"]):
            return "Testing"
        elif any(layer in path_lower for layer in ["shared", "common", "core"]):
            return "Shared"

        return None

    def _infer_purpose_from_category(self, category: str, path: str) -> str:
        """
        Infer file purpose from category and path.

        TASK-0CE5: Helper for fallback mode to provide better metadata.

        Args:
            category: File category from stratified sampling
            path: File path

        Returns:
            Human-readable purpose string
        """
        # Map categories to purposes
        category_purposes = {
            "crud_create": "Create operation for entity",
            "crud_read": "Read operation for entity",
            "crud_update": "Update operation for entity",
            "crud_delete": "Delete operation for entity",
            "crud_list": "List operation for entity",
            "validators": "Validation logic",
            "repositories": "Data access repository",
            "services": "Business logic service",
            "controllers": "API controller",
            "models": "Domain model or entity",
            "tests": "Test suite",
            "middleware": "Middleware component",
            "configuration": "Configuration settings"
        }

        # Get purpose from category
        purpose = category_purposes.get(category, "Source file")

        # Enhance with filename if available
        if path:
            filename = Path(path).stem
            purpose = f"{purpose} ({filename})"

        return purpose

    def _find_example_files(self, language: str) -> list:
        """Find example files from the codebase."""
        examples = []

        # TASK-0CE5: Enhanced to find more diverse examples
        logger.info(f"Discovering example files for {language} codebase")

        # Find representative files by extension
        extensions_map = {
            "Python": [".py"],
            "TypeScript": [".ts", ".tsx"],
            "JavaScript": [".js", ".jsx"],
            "C#": [".cs"],
            "Java": [".java"],
            "Go": [".go"],
            "Rust": [".rs"],
            "Ruby": [".rb"],
            "PHP": [".php"]
        }

        extensions = extensions_map.get(language, [])

        for ext in extensions:
            # Use get_source_files to exclude build artifacts
            source_files = get_source_files(self.codebase_path, extensions=[ext])

            # Limit to 15 files
            for f in source_files[:15]:
                if "test" not in str(f).lower():
                    path_str = str(f.relative_to(self.codebase_path))
                    examples.append({
                        "path": path_str,
                        "purpose": f"{language} source file",
                        "layer": self._infer_layer_from_path(path_str),
                        "patterns_used": [],
                        "key_concepts": []
                    })

                # Stop if we have enough examples
                if len(examples) >= 15:
                    break

            if len(examples) >= 15:
                break

        logger.info(f"Found {len(examples)} example files")
        return examples
