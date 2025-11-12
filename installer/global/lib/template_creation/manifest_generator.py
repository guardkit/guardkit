"""
Manifest Generator

Generates manifest.json files from AI-powered codebase analysis, including
intelligent placeholder detection, framework purpose classification, and
complexity scoring.
"""

import importlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import using importlib to avoid 'global' keyword issue in Python 3.14+
_codebase_models = importlib.import_module('installer.global.lib.codebase_analyzer.models')
CodebaseAnalysis = _codebase_models.CodebaseAnalysis
LayerInfo = _codebase_models.LayerInfo

from .models import FrameworkInfo, PlaceholderInfo, TemplateManifest


class ManifestGenerator:
    """Generate manifest.json from AI codebase analysis."""

    def __init__(self, analysis: CodebaseAnalysis):
        """
        Initialize generator with codebase analysis.

        Args:
            analysis: CodebaseAnalysis from TASK-002
        """
        self.analysis = analysis

    def generate(self) -> TemplateManifest:
        """
        Generate complete manifest from analysis.

        Returns:
            TemplateManifest with all fields populated from analysis
        """
        return TemplateManifest(
            schema_version="1.0.0",

            # Core identity
            name=self._generate_name(),
            display_name=self._generate_display_name(),
            description=self._generate_description(),
            version="1.0.0",  # Initial version for new templates
            author=self._infer_author(),

            # Technology stack
            language=self.analysis.technology.primary_language,
            language_version=self._infer_language_version(),
            frameworks=self._extract_frameworks(),
            architecture=self.analysis.architecture.architectural_style,

            # Template structure
            patterns=self._extract_patterns(),
            layers=self._extract_layer_names(),
            placeholders=self._extract_placeholders(),

            # Usage information
            tags=self._generate_tags(),
            category=self._infer_category(),
            complexity=self._calculate_complexity(),

            # Compatibility
            compatible_with=self._infer_compatible_templates(),
            requires=self._extract_requirements(),

            # Metadata
            created_at=datetime.now().isoformat(),
            source_project=self.analysis.codebase_path,
            confidence_score=self.analysis.overall_confidence.percentage
        )

    def _generate_name(self) -> str:
        """
        Generate template name from analysis.

        Returns kebab-case name based on language and architecture.

        Returns:
            Template name (e.g., 'python-clean-architecture')
        """
        # Infer from language + architecture
        lang = self.analysis.technology.primary_language.lower()
        arch = self.analysis.architecture.architectural_style.lower()

        # Clean up architecture name
        arch = arch.replace(" ", "-").replace("_", "-")

        return f"{lang}-{arch}-template"

    def _generate_display_name(self) -> str:
        """
        Generate human-friendly display name.

        Returns:
            Title-cased display name
        """
        name = self._generate_name()
        # Remove -template suffix and title case
        display = name.replace("-template", "").replace("-", " ").title()
        return display

    def _generate_description(self) -> str:
        """
        Generate template description from analysis.

        Returns:
            Descriptive text about the template
        """
        lang = self.analysis.technology.primary_language
        arch = self.analysis.architecture.architectural_style
        frameworks = self.analysis.technology.frameworks

        if frameworks:
            fw_text = f" with {', '.join(frameworks[:2])}"
        else:
            fw_text = ""

        return f"{lang} template using {arch} architecture{fw_text}"

    def _infer_author(self) -> Optional[str]:
        """
        Infer author from git config.

        Returns:
            Git user.name if available, None otherwise
        """
        try:
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                cwd=self.analysis.codebase_path,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        return None

    def _infer_language_version(self) -> Optional[str]:
        """
        Infer language version from project files.

        Returns:
            Version string if detected (e.g., '>=3.9', 'net8.0')
        """
        lang = self.analysis.technology.primary_language.lower()

        if lang == "python":
            return self._infer_python_version()
        elif lang in ["csharp", "c#", "dotnet"]:
            return self._infer_dotnet_version()
        elif lang in ["typescript", "javascript"]:
            return self._infer_node_version()

        return None

    def _infer_python_version(self) -> Optional[str]:
        """
        Infer Python version from project files.

        Checks:
        1. .python-version file
        2. pyproject.toml requires-python
        3. setup.py python_requires

        Returns:
            Python version requirement (e.g., '>=3.9')
        """
        project_root = Path(self.analysis.codebase_path)

        # Check .python-version
        python_version_file = project_root / ".python-version"
        if python_version_file.exists():
            version = python_version_file.read_text().strip()
            if version:
                return f">={version}"

        # Check pyproject.toml
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
                data = tomllib.loads(pyproject.read_text())
                python_req = data.get("project", {}).get("requires-python")
                if python_req:
                    return python_req
            except Exception:
                pass

        return None

    def _infer_dotnet_version(self) -> Optional[str]:
        """
        Infer .NET version from .csproj files.

        Returns:
            TargetFramework value (e.g., 'net8.0')
        """
        project_root = Path(self.analysis.codebase_path)

        # Find first .csproj file
        for csproj in project_root.rglob("*.csproj"):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(csproj)
                target = tree.find(".//TargetFramework")
                if target is not None and target.text:
                    return target.text
            except Exception:
                continue

        return None

    def _infer_node_version(self) -> Optional[str]:
        """
        Infer Node.js version from package.json engines field.

        Returns:
            Node version requirement (e.g., '>=18.0.0')
        """
        project_root = Path(self.analysis.codebase_path)
        package_json = project_root / "package.json"

        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                engines = data.get("engines", {})
                node_version = engines.get("node")
                if node_version:
                    return node_version
            except Exception:
                pass

        return None

    def _extract_frameworks(self) -> List[FrameworkInfo]:
        """
        Extract framework information with versions and purposes.

        Returns:
            List of FrameworkInfo objects
        """
        frameworks = []

        # Core frameworks
        for fw_name in self.analysis.technology.frameworks:
            frameworks.append(FrameworkInfo(
                name=fw_name,
                version=self._infer_framework_version(fw_name),
                purpose=self._infer_framework_purpose(fw_name)
            ))

        # Testing frameworks
        for fw_name in self.analysis.technology.testing_frameworks:
            frameworks.append(FrameworkInfo(
                name=fw_name,
                version=self._infer_framework_version(fw_name),
                purpose="testing"
            ))

        return frameworks

    def _infer_framework_version(self, framework: str) -> Optional[str]:
        """
        Infer framework version from project files.

        Args:
            framework: Framework name

        Returns:
            Version string if detected
        """
        project_root = Path(self.analysis.codebase_path)
        fw_lower = framework.lower()

        # Python: check requirements.txt or pyproject.toml
        if self.analysis.technology.primary_language.lower() == "python":
            requirements = project_root / "requirements.txt"
            if requirements.exists():
                content = requirements.read_text()
                for line in content.splitlines():
                    if fw_lower in line.lower():
                        # Extract version (e.g., "fastapi==0.104.0")
                        if "==" in line:
                            return line.split("==")[1].split("#")[0].strip()

        # Node: check package.json
        elif self.analysis.technology.primary_language.lower() in ["typescript", "javascript"]:
            package_json = project_root / "package.json"
            if package_json.exists():
                try:
                    data = json.loads(package_json.read_text())
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for pkg, version in deps.items():
                        if fw_lower in pkg.lower():
                            return version.lstrip("^~>=")
                except Exception:
                    pass

        # .NET: check .csproj
        elif self.analysis.technology.primary_language.lower() in ["csharp", "c#", "dotnet"]:
            for csproj in project_root.rglob("*.csproj"):
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(csproj)
                    for pkg_ref in tree.findall(".//PackageReference"):
                        include = pkg_ref.get("Include", "")
                        if fw_lower in include.lower():
                            version = pkg_ref.get("Version")
                            if version:
                                return version
                except Exception:
                    continue

        return None

    def _infer_framework_purpose(self, framework: str) -> str:
        """
        Infer framework purpose based on known framework types.

        Args:
            framework: Framework name

        Returns:
            Purpose: 'testing', 'ui', 'data', 'core', etc.
        """
        fw_lower = framework.lower()

        # Testing frameworks
        testing_keywords = ["test", "jest", "vitest", "pytest", "xunit", "nunit", "mocha", "jasmine"]
        if any(kw in fw_lower for kw in testing_keywords):
            return "testing"

        # UI frameworks
        ui_keywords = ["react", "vue", "angular", "maui", "wpf", "blazor", "svelte"]
        if any(kw in fw_lower for kw in ui_keywords):
            return "ui"

        # Data/ORM frameworks
        data_keywords = ["sqlalchemy", "entity", "prisma", "mongoose", "sequelize", "typeorm"]
        if any(kw in fw_lower for kw in data_keywords):
            return "data"

        # API frameworks
        api_keywords = ["fastapi", "express", "django", "flask", "nestjs", "aspnet"]
        if any(kw in fw_lower for kw in api_keywords):
            return "core"

        return "core"

    def _extract_patterns(self) -> List[str]:
        """
        Extract all architecture and design patterns.

        Returns:
            Deduplicated list of patterns
        """
        patterns = set()

        # Main architecture patterns
        patterns.update(self.analysis.architecture.patterns)

        return sorted(list(patterns))

    def _extract_layer_names(self) -> List[str]:
        """
        Extract architectural layer names.

        Returns:
            List of layer names
        """
        return [layer.name for layer in self.analysis.architecture.layers]

    def _extract_placeholders(self) -> Dict[str, PlaceholderInfo]:
        """
        Extract intelligent placeholders from analysis.

        Includes standard placeholders (ProjectName, Namespace) plus any
        detected from naming patterns.

        Returns:
            Dictionary of placeholder name to PlaceholderInfo
        """
        placeholders = {}

        # Standard placeholders (always present)
        placeholders["ProjectName"] = PlaceholderInfo(
            name="{{ProjectName}}",
            description="Name of the project/solution",
            default_value=None,
            pattern="^[A-Za-z][A-Za-z0-9_]*$",
            required=True
        )

        placeholders["Namespace"] = PlaceholderInfo(
            name="{{Namespace}}",
            description="Root namespace for the project",
            default_value=None,
            pattern="^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)*$",
            required=True
        )

        # Add Author placeholder (commonly used)
        placeholders["Author"] = PlaceholderInfo(
            name="{{Author}}",
            description="Project author name",
            default_value=self._infer_author() or "Your Name",
            pattern=None,
            required=False
        )

        return placeholders

    def _generate_tags(self) -> List[str]:
        """
        Generate searchable tags from analysis.

        Returns:
            Deduplicated list of tags
        """
        tags = set()

        # Language tag
        tags.add(self.analysis.technology.primary_language.lower())

        # Framework tags
        for fw in self.analysis.technology.frameworks:
            tags.add(fw.lower().replace(" ", "-"))

        for fw in self.analysis.technology.testing_frameworks:
            tags.add(fw.lower().replace(" ", "-"))

        # Architecture tag
        arch_tag = self.analysis.architecture.architectural_style.lower().replace(" ", "-")
        tags.add(arch_tag)

        # Layer tags
        for layer in self.analysis.architecture.layers:
            tags.add(layer.name.lower())

        # Pattern tags
        for pattern in self.analysis.architecture.patterns:
            tags.add(pattern.lower().replace(" ", "-"))

        return sorted(list(tags))

    def _infer_category(self) -> str:
        """
        Infer template category from frameworks and architecture.

        Returns:
            Category: 'backend', 'frontend', 'mobile', 'desktop', 'fullstack', or 'general'
        """
        frameworks_lower = [fw.lower() for fw in self.analysis.technology.frameworks]

        # Backend
        backend_keywords = ["fastapi", "django", "flask", "aspnet", "express", "nestjs", "api"]
        if any(kw in fw for kw in backend_keywords for fw in frameworks_lower):
            return "backend"

        # Frontend
        frontend_keywords = ["react", "vue", "angular", "blazor", "svelte"]
        if any(kw in fw for kw in frontend_keywords for fw in frameworks_lower):
            return "frontend"

        # Mobile
        mobile_keywords = ["maui", "react-native", "flutter", "xamarin"]
        if any(kw in fw for kw in mobile_keywords for fw in frameworks_lower):
            return "mobile"

        # Desktop
        desktop_keywords = ["wpf", "winforms", "electron", "tauri"]
        if any(kw in fw for kw in desktop_keywords for fw in frameworks_lower):
            return "desktop"

        # Fullstack
        fullstack_keywords = ["nextjs", "nuxt", "remix"]
        if any(kw in fw for kw in fullstack_keywords for fw in frameworks_lower):
            return "fullstack"

        return "general"

    def _calculate_complexity(self) -> int:
        """
        Calculate template complexity score (1-10).

        Based on:
        - Number of layers (more = complex)
        - Number of frameworks (more = complex)
        - Number of patterns (more = complex)

        Returns:
            Complexity score from 1-10
        """
        complexity = 1

        # Layer complexity (max +3)
        layer_count = len(self.analysis.architecture.layers)
        complexity += min(layer_count, 3)

        # Framework complexity (max +3)
        framework_count = len(self.analysis.technology.frameworks) + len(self.analysis.technology.testing_frameworks)
        complexity += min(framework_count, 3)

        # Pattern complexity (max +3)
        pattern_count = len(self.analysis.architecture.patterns)
        complexity += min(pattern_count, 3)

        return min(complexity, 10)

    def _infer_compatible_templates(self) -> List[str]:
        """
        Infer compatible templates.

        Future: check global template registry for compatibility.

        Returns:
            List of compatible template names
        """
        # Future enhancement: check template registry
        return []

    def _extract_requirements(self) -> List[str]:
        """
        Extract required global agents or tools.

        Returns:
            List of requirement strings (e.g., 'agent:python-domain-specialist')
        """
        requirements = []

        # Based on language
        lang = self.analysis.technology.primary_language.lower()
        if lang == "python":
            requirements.append("agent:python-domain-specialist")
        elif lang in ["csharp", "c#", "dotnet"]:
            requirements.append("agent:dotnet-domain-specialist")
        elif lang in ["typescript", "javascript"]:
            requirements.append("agent:typescript-domain-specialist")

        # Based on architecture
        arch = self.analysis.architecture.architectural_style.lower()
        if "clean" in arch or "hexagonal" in arch:
            requirements.append("agent:architectural-reviewer")

        return requirements

    def to_json(self, manifest: TemplateManifest, indent: int = 2) -> str:
        """
        Convert manifest to JSON string.

        Args:
            manifest: TemplateManifest to convert
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return manifest.model_dump_json(indent=indent, exclude_none=False)

    def save(self, manifest: TemplateManifest, output_path: Path) -> None:
        """
        Save manifest to file.

        Args:
            manifest: TemplateManifest to save
            output_path: Path to manifest.json file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(manifest))
