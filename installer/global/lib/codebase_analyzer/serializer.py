"""
Analysis Serializer

Handles saving and loading CodebaseAnalysis results to/from JSON files.
Provides caching and persistence for analysis results.

Following architectural review recommendations:
- Shared serialization logic (DRY)
- Single responsibility (serialization only)
- Clear error handling
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('lib.codebase_analyzer.models')

CodebaseAnalysis = _models_module.CodebaseAnalysis
AnalysisError = _models_module.AnalysisError


class AnalysisSerializer:
    """
    Serializes and deserializes CodebaseAnalysis objects.

    Handles JSON conversion with proper datetime handling and validation.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize serializer.

        Args:
            cache_dir: Directory for caching analysis results.
                      Defaults to .claude/state/codebase_analysis/
        """
        if cache_dir is None:
            self.cache_dir = Path.home() / ".agentecflow" / "state" / "codebase_analysis"
        else:
            self.cache_dir = Path(cache_dir)

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, analysis: CodebaseAnalysis, filename: Optional[str] = None) -> Path:
        """
        Save analysis to JSON file.

        Args:
            analysis: CodebaseAnalysis to save
            filename: Optional filename (default: auto-generated from codebase path)

        Returns:
            Path to saved file

        Raises:
            AnalysisError: If save fails
        """
        if filename is None:
            # Generate filename from codebase path
            codebase_name = Path(analysis.codebase_path).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{codebase_name}_{timestamp}.json"

        output_path = self.cache_dir / filename

        try:
            # Convert to dict
            data = analysis.model_dump(mode='json')

            # Write to file with pretty printing
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)

            return output_path

        except Exception as e:
            raise AnalysisError(f"Failed to save analysis: {e}") from e

    def load(self, filepath: Path) -> CodebaseAnalysis:
        """
        Load analysis from JSON file.

        Args:
            filepath: Path to analysis JSON file

        Returns:
            CodebaseAnalysis object

        Raises:
            AnalysisError: If file not found or invalid
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise AnalysisError(f"Analysis file not found: {filepath}")

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Reconstruct CodebaseAnalysis from dict
            analysis = CodebaseAnalysis(**data)
            return analysis

        except json.JSONDecodeError as e:
            raise AnalysisError(f"Invalid JSON in analysis file: {e}") from e
        except Exception as e:
            raise AnalysisError(f"Failed to load analysis: {e}") from e

    def find_latest(self, codebase_name: Optional[str] = None) -> Optional[Path]:
        """
        Find the most recent analysis file.

        Args:
            codebase_name: Optional filter by codebase name

        Returns:
            Path to latest analysis file or None if no analyses found
        """
        if not self.cache_dir.exists():
            return None

        json_files = list(self.cache_dir.glob("*.json"))

        if not json_files:
            return None

        if codebase_name:
            json_files = [f for f in json_files if codebase_name in f.name]

        if not json_files:
            return None

        # Return newest file (by modification time)
        return max(json_files, key=lambda p: p.stat().st_mtime)

    def export_markdown(self, analysis: CodebaseAnalysis, filepath: Optional[Path] = None) -> Path:
        """
        Export analysis as human-readable markdown.

        Args:
            analysis: CodebaseAnalysis to export
            filepath: Optional output filepath (default: auto-generated)

        Returns:
            Path to exported markdown file

        Raises:
            AnalysisError: If export fails
        """
        if filepath is None:
            codebase_name = Path(analysis.codebase_path).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{codebase_name}_{timestamp}_analysis.md"
            filepath = self.cache_dir / filename
        else:
            filepath = Path(filepath)

        try:
            # Generate markdown content
            content = self._generate_markdown(analysis)

            # Write to file
            with open(filepath, 'w') as f:
                f.write(content)

            return filepath

        except Exception as e:
            raise AnalysisError(f"Failed to export markdown: {e}") from e

    def list_analyses(self) -> list[Path]:
        """
        List all cached analysis files.

        Returns:
            List of analysis file paths
        """
        if not self.cache_dir.exists():
            return []

        return sorted(
            self.cache_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    def delete(self, filepath: Path) -> bool:
        """
        Delete an analysis file.

        Args:
            filepath: Path to analysis file

        Returns:
            True if deleted, False if not found

        Raises:
            AnalysisError: If deletion fails
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            return True
        except Exception as e:
            raise AnalysisError(f"Failed to delete analysis: {e}") from e

    def get_summary(self, filepath: Path) -> dict:
        """
        Get a summary of an analysis file as a dictionary.

        Args:
            filepath: Path to analysis file

        Returns:
            Dictionary with summary info

        Raises:
            AnalysisError: If file not found or invalid
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise AnalysisError(f"Analysis file not found: {filepath}")

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Extract summary info
            return {
                "filepath": str(filepath),
                "codebase_path": data.get('codebase_path'),
                "primary_language": data.get('technology', {}).get('primary_language'),
                "frameworks": data.get('technology', {}).get('frameworks', []),
                "overall_score": data.get('quality', {}).get('overall_score'),
                "analyzed_at": data.get('analyzed_at'),
            }

        except json.JSONDecodeError as e:
            raise AnalysisError(f"Invalid JSON in analysis file: {e}") from e
        except Exception as e:
            raise AnalysisError(f"Failed to read summary: {e}") from e

    @staticmethod
    def _generate_markdown(analysis: CodebaseAnalysis) -> str:
        """
        Generate markdown representation of analysis.

        Args:
            analysis: CodebaseAnalysis to convert

        Returns:
            Markdown string
        """
        lines = [
            "# Codebase Analysis Report",
            "",
            f"**Codebase Path:** {analysis.codebase_path}",
            f"**Analyzed:** {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Agent Used:** {'Yes' if analysis.agent_used else 'No'}",
            "",
            "## Technology Stack",
            "",
            f"**Primary Language:** {analysis.technology.primary_language}",
            f"**Frameworks:** {', '.join(analysis.technology.frameworks) if analysis.technology.frameworks else 'None'}",
            f"**Testing Frameworks:** {', '.join(analysis.technology.testing_frameworks) if analysis.technology.testing_frameworks else 'None'}",
            f"**Build Tools:** {', '.join(analysis.technology.build_tools) if analysis.technology.build_tools else 'None'}",
            f"**Confidence:** {analysis.technology.confidence.level.value} ({analysis.technology.confidence.percentage}%)",
            "",
            "## Architecture",
            "",
            f"**Architectural Style:** {analysis.architecture.architectural_style}",
            f"**Patterns:** {', '.join(analysis.architecture.patterns) if analysis.architecture.patterns else 'None'}",
            f"**Layers:** {', '.join([l.name for l in analysis.architecture.layers]) if analysis.architecture.layers else 'None'}",
            f"**Confidence:** {analysis.architecture.confidence.level.value} ({analysis.architecture.confidence.percentage}%)",
            "",
            "## Quality Metrics",
            "",
            f"**Overall Score:** {analysis.quality.overall_score}/100",
            f"**SOLID Compliance:** {analysis.quality.solid_compliance}%",
            f"**DRY Compliance:** {analysis.quality.dry_compliance}%",
            f"**YAGNI Compliance:** {analysis.quality.yagni_compliance}%",
            f"**Test Coverage:** {analysis.quality.test_coverage if analysis.quality.test_coverage is not None else 'N/A'}%",
            f"**Confidence:** {analysis.quality.confidence.level.value} ({analysis.quality.confidence.percentage}%)",
            "",
        ]

        return "\n".join(lines)
