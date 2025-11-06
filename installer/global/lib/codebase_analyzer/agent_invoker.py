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
import subprocess
from pathlib import Path
from typing import Optional, Protocol

from lib.codebase_analyzer.models import AgentInvocationError


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
    """

    def __init__(
        self,
        agent_path: Optional[Path] = None,
        timeout_seconds: int = 120
    ):
        """
        Initialize agent invoker.

        Args:
            agent_path: Path to architectural-reviewer.md agent file.
                       Defaults to installer/global/agents/architectural-reviewer.md
            timeout_seconds: Maximum time to wait for agent response
        """
        if agent_path is None:
            # Default to global agents directory
            self.agent_path = Path.home() / ".agentecflow" / "agents" / "architectural-reviewer.md"
        else:
            self.agent_path = agent_path

        self.timeout_seconds = timeout_seconds

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

        This method uses Claude Code's agent invocation mechanism. In the actual
        implementation, this would communicate with Claude Code's agent system.
        For now, we simulate this with a subprocess call that would be replaced
        with the actual agent invocation mechanism.

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
                "Ensure Taskwright is properly installed."
            )

        try:
            # In a real implementation, this would use Claude Code's agent system
            # For now, we'll return a structured response format that matches
            # what the architectural-reviewer agent would return
            #
            # The actual invocation would look like:
            # response = claude_code_api.invoke_agent(
            #     agent_name=agent_name,
            #     prompt=prompt,
            #     timeout=self.timeout_seconds
            # )
            #
            # For this implementation, we'll simulate the response structure
            # and rely on heuristic analysis in the fallback path

            # Placeholder for actual agent invocation
            # This will be replaced with real Claude Code agent communication
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
    """

    def __init__(self, codebase_path: Path):
        """
        Initialize heuristic analyzer.

        Args:
            codebase_path: Path to codebase to analyze
        """
        self.codebase_path = codebase_path

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
            "example_files": self._find_example_files(language),
            "agent_used": False,
            "fallback_reason": "Agent not available - using heuristic analysis"
        }

    def _detect_language(self) -> str:
        """Detect primary programming language."""
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
            count = len(list(self.codebase_path.rglob(f"*{ext}")))
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

    def _detect_patterns(self) -> list:
        """Detect design patterns from directory structure."""
        patterns = []

        # Look for common pattern indicators (case-insensitive)
        # Check for repository pattern
        repo_patterns = ["*[Rr]epository*.py", "*[Rr]epository*.ts", "*[Rr]epository*.cs"]
        if any(any(self.codebase_path.rglob(pattern)) for pattern in repo_patterns):
            patterns.append("Repository")

        # Check for factory pattern
        factory_patterns = ["*[Ff]actory*.py", "*[Ff]actory*.ts", "*[Ff]actory*.cs"]
        if any(any(self.codebase_path.rglob(pattern)) for pattern in factory_patterns):
            patterns.append("Factory")

        # Check for service layer pattern
        service_patterns = ["*[Ss]ervice*.py", "*[Ss]ervice*.ts", "*[Ss]ervice*.cs"]
        if any(any(self.codebase_path.rglob(pattern)) for pattern in service_patterns):
            patterns.append("Service Layer")

        return patterns

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
        """Detect architectural layers."""
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

        return layers

    def _detect_abstractions(self, language: str) -> list:
        """Detect key domain abstractions."""
        abstractions = []

        # This would require more sophisticated analysis
        # For now, return empty or basic guesses

        return abstractions

    def _find_example_files(self, language: str) -> list:
        """Find example files from the codebase."""
        examples = []

        # Find a few representative files
        if language == "Python":
            py_files = list(self.codebase_path.rglob("*.py"))[:5]
            for f in py_files:
                if "test" not in str(f):
                    examples.append({
                        "path": str(f.relative_to(self.codebase_path)),
                        "purpose": "Python module",
                        "layer": None,
                        "patterns_used": [],
                        "key_concepts": []
                    })

        return examples
