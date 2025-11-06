"""
Settings Generator

Generates template settings from AI-powered codebase analysis.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from lib.codebase_analyzer.models import CodebaseAnalysis, LayerInfo
from lib.settings_generator.models import (
    CaseStyle,
    TestLocation,
    NamingConvention,
    FileOrganization,
    LayerMapping,
    CodeStyle,
    TemplateSettings,
    GenerationError
)


class SettingsGenerator:
    """Generate settings.json from CodebaseAnalysis.

    Example:
        analysis = CodebaseAnalysis(...)
        generator = SettingsGenerator(analysis)
        settings = generator.generate()
        generator.save(settings, Path("template/settings.json"))
    """

    def __init__(self, analysis: CodebaseAnalysis):
        """Initialize generator with codebase analysis.

        Args:
            analysis: CodebaseAnalysis from TASK-002
        """
        self.analysis = analysis

    def generate(self) -> TemplateSettings:
        """Generate complete settings from analysis.

        Returns:
            TemplateSettings with all fields populated

        Raises:
            GenerationError: If generation fails
        """
        try:
            return TemplateSettings(
                schema_version="1.0.0",
                naming_conventions=self._extract_naming_conventions(),
                file_organization=self._infer_file_organization(),
                layer_mappings=self._create_layer_mappings(),
                code_style=self._infer_code_style(),
                generation_options=self._create_generation_options()
            )
        except Exception as e:
            raise GenerationError(f"Failed to generate settings: {str(e)}") from e

    def _extract_naming_conventions(self) -> Dict[str, NamingConvention]:
        """Extract naming conventions from analysis.

        The CodebaseAnalysis doesn't have explicit naming_conventions field,
        so we'll infer them from the architecture and example files.
        """
        conventions = {}

        # Infer from architecture patterns and primary language
        lang = self.analysis.technology.primary_language.lower()

        if lang in ["c#", "csharp"]:
            conventions.update(self._infer_csharp_conventions())
        elif lang in ["python"]:
            conventions.update(self._infer_python_conventions())
        elif lang in ["typescript", "javascript"]:
            conventions.update(self._infer_typescript_conventions())
        elif lang in ["java", "kotlin"]:
            conventions.update(self._infer_java_conventions())

        # Enhance with examples from codebase
        self._enhance_with_examples(conventions)

        return conventions

    def _infer_csharp_conventions(self) -> Dict[str, NamingConvention]:
        """Infer C# naming conventions."""
        return {
            "class": NamingConvention(
                element_type="class",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".cs",
                examples=[]
            ),
            "interface": NamingConvention(
                element_type="interface",
                pattern="I{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                prefix="I",
                suffix=".cs",
                examples=[]
            ),
            "method": NamingConvention(
                element_type="method",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                examples=[]
            ),
            "property": NamingConvention(
                element_type="property",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                examples=[]
            ),
            "field": NamingConvention(
                element_type="field",
                pattern="_{{name}}",
                case_style=CaseStyle.CAMEL_CASE,
                prefix="_",
                examples=[]
            ),
        }

    def _infer_python_conventions(self) -> Dict[str, NamingConvention]:
        """Infer Python naming conventions."""
        return {
            "class": NamingConvention(
                element_type="class",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".py",
                examples=[]
            ),
            "function": NamingConvention(
                element_type="function",
                pattern="{{name}}",
                case_style=CaseStyle.SNAKE_CASE,
                examples=[]
            ),
            "module": NamingConvention(
                element_type="module",
                pattern="{{name}}",
                case_style=CaseStyle.SNAKE_CASE,
                suffix=".py",
                examples=[]
            ),
            "constant": NamingConvention(
                element_type="constant",
                pattern="{{NAME}}",
                case_style=CaseStyle.SCREAMING_SNAKE_CASE,
                examples=[]
            ),
        }

    def _infer_typescript_conventions(self) -> Dict[str, NamingConvention]:
        """Infer TypeScript naming conventions."""
        return {
            "class": NamingConvention(
                element_type="class",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".ts",
                examples=[]
            ),
            "interface": NamingConvention(
                element_type="interface",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".ts",
                examples=[]
            ),
            "function": NamingConvention(
                element_type="function",
                pattern="{{name}}",
                case_style=CaseStyle.CAMEL_CASE,
                examples=[]
            ),
            "constant": NamingConvention(
                element_type="constant",
                pattern="{{NAME}}",
                case_style=CaseStyle.SCREAMING_SNAKE_CASE,
                examples=[]
            ),
        }

    def _infer_java_conventions(self) -> Dict[str, NamingConvention]:
        """Infer Java naming conventions."""
        return {
            "class": NamingConvention(
                element_type="class",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".java",
                examples=[]
            ),
            "interface": NamingConvention(
                element_type="interface",
                pattern="{{Name}}",
                case_style=CaseStyle.PASCAL_CASE,
                suffix=".java",
                examples=[]
            ),
            "method": NamingConvention(
                element_type="method",
                pattern="{{name}}",
                case_style=CaseStyle.CAMEL_CASE,
                examples=[]
            ),
            "constant": NamingConvention(
                element_type="constant",
                pattern="{{NAME}}",
                case_style=CaseStyle.SCREAMING_SNAKE_CASE,
                examples=[]
            ),
        }

    def _enhance_with_examples(self, conventions: Dict[str, NamingConvention]) -> None:
        """Enhance conventions with examples from analyzed files."""
        for example_file in self.analysis.example_files[:5]:  # Use up to 5 examples
            file_name = Path(example_file.path).stem

            # Try to match to conventions
            for conv in conventions.values():
                if self._matches_pattern(file_name, conv):
                    if file_name not in conv.examples:
                        conv.examples.append(file_name)
                    if len(conv.examples) >= 3:  # Max 3 examples per convention
                        break

    def _matches_pattern(self, name: str, convention: NamingConvention) -> bool:
        """Check if a name matches a naming convention pattern."""
        # Simple heuristic based on case style
        if convention.case_style == CaseStyle.PASCAL_CASE:
            return name[0].isupper() and "_" not in name and "-" not in name
        elif convention.case_style == CaseStyle.CAMEL_CASE:
            return name[0].islower() and "_" not in name and "-" not in name
        elif convention.case_style == CaseStyle.SNAKE_CASE:
            return "_" in name or name.islower()
        elif convention.case_style == CaseStyle.KEBAB_CASE:
            return "-" in name
        elif convention.case_style == CaseStyle.SCREAMING_SNAKE_CASE:
            return name.isupper() and "_" in name
        return False

    def _infer_file_organization(self) -> FileOrganization:
        """Infer file organization preferences from architecture."""
        # Check if we have multiple layers
        by_layer = len(self.analysis.architecture.layers) > 1

        # Check architectural style for by-feature hint
        by_feature = "vertical" in self.analysis.architecture.architectural_style.lower() or \
                     "feature" in self.analysis.architecture.architectural_style.lower()

        # Infer test location from example files
        test_location = self._infer_test_location()

        return FileOrganization(
            by_layer=by_layer,
            by_feature=by_feature,
            test_location=test_location,
            max_files_per_directory=50  # Reasonable default
        )

    def _infer_test_location(self) -> TestLocation:
        """Infer where tests are located."""
        # Check if there's a test-specific layer
        for layer in self.analysis.architecture.layers:
            if "test" in layer.name.lower():
                return TestLocation.SEPARATE

        # Check example files for test patterns
        for example_file in self.analysis.example_files:
            path_lower = example_file.path.lower()
            if "/tests/" in path_lower or "\\tests\\" in path_lower:
                return TestLocation.SEPARATE
            elif "test" in Path(example_file.path).name.lower():
                # Test file exists, check if it's adjacent or separate
                if "/tests/" not in path_lower:
                    return TestLocation.ADJACENT

        # Default to separate
        return TestLocation.SEPARATE

    def _create_layer_mappings(self) -> Dict[str, LayerMapping]:
        """Create layer mappings from analysis."""
        mappings = {}

        for layer in self.analysis.architecture.layers:
            mappings[layer.name] = LayerMapping(
                name=layer.name,
                directory=self._infer_layer_directory(layer),
                namespace_pattern=self._infer_namespace_pattern(layer),
                file_patterns=self._infer_file_patterns(layer)
            )

        return mappings

    def _infer_layer_directory(self, layer: LayerInfo) -> str:
        """Infer directory path for a layer."""
        # Use description as hint for path
        # Common patterns: src/{LayerName}, {LayerName}, etc.
        layer_name = layer.name

        # Most modern projects use src/ prefix
        return f"src/{layer_name}"

    def _infer_namespace_pattern(self, layer: LayerInfo) -> Optional[str]:
        """Infer namespace pattern for layer."""
        lang = self.analysis.technology.primary_language.lower()

        if lang in ["c#", "csharp", "java", "kotlin"]:
            # Namespace-based languages
            return f"{{{{ProjectName}}}}.{layer.name}.{{{{SubPath}}}}"
        elif lang in ["typescript", "javascript"]:
            # Module-based (no explicit namespace pattern needed)
            return None
        elif lang == "python":
            # Package-based
            return f"{{{{project_name}}}}.{layer.name.lower()}"

        return None

    def _infer_file_patterns(self, layer: LayerInfo) -> List[str]:
        """Infer file patterns for layer."""
        lang = self.analysis.technology.primary_language.lower()

        # Language-specific patterns with test exclusions
        if lang in ["c#", "csharp"]:
            return ["*.cs", "!*Test.cs", "!*Tests.cs"]
        elif lang in ["typescript"]:
            return ["*.ts", "*.tsx", "!*.test.ts", "!*.spec.ts"]
        elif lang in ["javascript"]:
            return ["*.js", "*.jsx", "!*.test.js", "!*.spec.js"]
        elif lang == "python":
            return ["*.py", "!*_test.py", "!test_*.py"]
        elif lang in ["java"]:
            return ["*.java", "!*Test.java", "!*Tests.java"]
        elif lang in ["kotlin"]:
            return ["*.kt", "!*Test.kt", "!*Tests.kt"]
        else:
            return ["*"]

    def _infer_code_style(self) -> CodeStyle:
        """Infer code style from language and frameworks."""
        lang = self.analysis.technology.primary_language.lower()

        # Language-specific defaults
        if lang == "python":
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=88,  # Black default
                trailing_commas=True
            )
        elif lang in ["typescript", "javascript"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=2,
                line_length=100,
                trailing_commas=True
            )
        elif lang in ["c#", "csharp"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=120,
                trailing_commas=False
            )
        elif lang in ["java", "kotlin"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=120,
                trailing_commas=False
            )
        else:
            # Generic defaults
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=None,
                trailing_commas=False
            )

    def _create_generation_options(self) -> Dict[str, any]:
        """Create generation options."""
        return {
            "preserve_comments": True,
            "preserve_whitespace": True,
            "auto_format": True
        }

    def to_json(self, settings: TemplateSettings) -> str:
        """Convert settings to JSON string.

        Args:
            settings: TemplateSettings to serialize

        Returns:
            JSON string
        """
        return json.dumps(settings.to_dict(), indent=2)

    def save(self, settings: TemplateSettings, output_path: Path) -> None:
        """Save settings to file.

        Args:
            settings: TemplateSettings to save
            output_path: Path to output file

        Raises:
            GenerationError: If save fails
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(self.to_json(settings))
        except Exception as e:
            raise GenerationError(f"Failed to save settings to {output_path}: {str(e)}") from e
