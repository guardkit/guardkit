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

from lib.codebase_analyzer.models import CodebaseAnalysis, AnalysisError


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
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            return output_path

        except (OSError, IOError) as e:
            raise AnalysisError(f"Failed to save analysis to {output_path}: {e}") from e
        except Exception as e:
            raise AnalysisError(f"Unexpected error saving analysis: {e}") from e

    def load(self, filepath: Path) -> CodebaseAnalysis:
        """
        Load analysis from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Loaded CodebaseAnalysis object

        Raises:
            AnalysisError: If load fails or validation fails
        """
        if not filepath.exists():
            raise AnalysisError(f"Analysis file not found: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse datetime fields
            if 'analyzed_at' in data and isinstance(data['analyzed_at'], str):
                data['analyzed_at'] = datetime.fromisoformat(data['analyzed_at'])

            # Construct analysis from data
            analysis = CodebaseAnalysis(**data)
            return analysis

        except json.JSONDecodeError as e:
            raise AnalysisError(f"Invalid JSON in {filepath}: {e}") from e
        except Exception as e:
            raise AnalysisError(f"Failed to load analysis from {filepath}: {e}") from e

    def find_latest(self, codebase_name: Optional[str] = None) -> Optional[Path]:
        """
        Find the most recent analysis file.

        Args:
            codebase_name: Optional codebase name to filter by

        Returns:
            Path to most recent analysis file, or None if none found
        """
        pattern = f"{codebase_name}_*.json" if codebase_name else "*.json"
        files = list(self.cache_dir.glob(pattern))

        if not files:
            return None

        # Sort by modification time, most recent first
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]

    def list_analyses(self, codebase_name: Optional[str] = None) -> list[Path]:
        """
        List all available analysis files.

        Args:
            codebase_name: Optional codebase name to filter by

        Returns:
            List of paths to analysis files, sorted by modification time (newest first)
        """
        pattern = f"{codebase_name}_*.json" if codebase_name else "*.json"
        files = list(self.cache_dir.glob(pattern))

        # Sort by modification time, most recent first
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def delete(self, filepath: Path) -> bool:
        """
        Delete an analysis file.

        Args:
            filepath: Path to file to delete

        Returns:
            True if deleted, False if file didn't exist

        Raises:
            AnalysisError: If deletion fails
        """
        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            return True
        except OSError as e:
            raise AnalysisError(f"Failed to delete {filepath}: {e}") from e

    def get_summary(self, filepath: Path) -> dict:
        """
        Get summary information about an analysis file without loading the entire file.

        Args:
            filepath: Path to analysis file

        Returns:
            Dictionary with summary info: codebase_path, analyzed_at, language, etc.

        Raises:
            AnalysisError: If file cannot be read
        """
        if not filepath.exists():
            raise AnalysisError(f"Analysis file not found: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                "codebase_path": data.get("codebase_path", "Unknown"),
                "analyzed_at": data.get("analyzed_at", "Unknown"),
                "primary_language": data.get("technology", {}).get("primary_language", "Unknown"),
                "architectural_style": data.get("architecture", {}).get("architectural_style", "Unknown"),
                "overall_score": data.get("quality", {}).get("overall_score", 0),
                "agent_used": data.get("agent_used", False),
                "file_size": filepath.stat().st_size,
                "filepath": str(filepath)
            }

        except json.JSONDecodeError as e:
            raise AnalysisError(f"Invalid JSON in {filepath}: {e}") from e
        except Exception as e:
            raise AnalysisError(f"Failed to read summary from {filepath}: {e}") from e

    def export_markdown(self, analysis: CodebaseAnalysis, output_path: Path) -> Path:
        """
        Export analysis as a markdown report.

        Args:
            analysis: CodebaseAnalysis to export
            output_path: Path to output markdown file

        Returns:
            Path to created markdown file

        Raises:
            AnalysisError: If export fails
        """
        try:
            # Build markdown content
            markdown = self._build_markdown_report(analysis)

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)

            return output_path

        except (OSError, IOError) as e:
            raise AnalysisError(f"Failed to export markdown to {output_path}: {e}") from e

    def _build_markdown_report(self, analysis: CodebaseAnalysis) -> str:
        """Build markdown report from analysis."""
        lines = [
            f"# Codebase Analysis Report",
            "",
            f"**Codebase**: `{analysis.codebase_path}`",
            f"**Analyzed**: {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Analysis Version**: {analysis.analysis_version}",
            "",
            "---",
            "",
            "## Technology Stack",
            "",
            f"**Primary Language**: {analysis.technology.primary_language}",
            "",
        ]

        if analysis.technology.frameworks:
            lines.append(f"**Frameworks**: {', '.join(analysis.technology.frameworks)}")
        if analysis.technology.testing_frameworks:
            lines.append(f"**Testing**: {', '.join(analysis.technology.testing_frameworks)}")
        if analysis.technology.build_tools:
            lines.append(f"**Build Tools**: {', '.join(analysis.technology.build_tools)}")

        lines.extend([
            "",
            f"**Confidence**: {analysis.technology.confidence.level.value} "
            f"({analysis.technology.confidence.percentage}%)",
            "",
            "## Architecture",
            "",
            f"**Style**: {analysis.architecture.architectural_style}",
            "",
        ])

        if analysis.architecture.patterns:
            lines.append(f"**Patterns**: {', '.join(analysis.architecture.patterns)}")
            lines.append("")

        if analysis.architecture.layers:
            lines.append("**Layers**:")
            lines.append("")
            for layer in analysis.architecture.layers:
                lines.append(f"- **{layer.name}**: {layer.description}")
            lines.append("")

        lines.extend([
            f"**Dependency Flow**: {analysis.architecture.dependency_flow}",
            "",
            f"**Confidence**: {analysis.architecture.confidence.level.value} "
            f"({analysis.architecture.confidence.percentage}%)",
            "",
            "## Quality Assessment",
            "",
            f"**Overall Score**: {analysis.quality.overall_score}/100",
            f"**SOLID Compliance**: {analysis.quality.solid_compliance}/100",
            f"**DRY Compliance**: {analysis.quality.dry_compliance}/100",
            f"**YAGNI Compliance**: {analysis.quality.yagni_compliance}/100",
            "",
        ])

        if analysis.quality.test_coverage is not None:
            lines.append(f"**Test Coverage**: {analysis.quality.test_coverage}%")
            lines.append("")

        if analysis.quality.strengths:
            lines.append("**Strengths**:")
            lines.append("")
            for strength in analysis.quality.strengths:
                lines.append(f"- {strength}")
            lines.append("")

        if analysis.quality.improvements:
            lines.append("**Suggested Improvements**:")
            lines.append("")
            for improvement in analysis.quality.improvements:
                lines.append(f"- {improvement}")
            lines.append("")

        if analysis.quality.code_smells:
            lines.append("**Code Smells**:")
            lines.append("")
            for smell in analysis.quality.code_smells:
                lines.append(f"- {smell}")
            lines.append("")

        lines.extend([
            f"**Confidence**: {analysis.quality.confidence.level.value} "
            f"({analysis.quality.confidence.percentage}%)",
            "",
        ])

        if analysis.example_files:
            lines.extend([
                "## Example Files",
                "",
            ])
            for example in analysis.example_files:
                lines.append(f"### `{example.path}`")
                lines.append("")
                lines.append(f"**Purpose**: {example.purpose}")
                if example.layer:
                    lines.append(f"**Layer**: {example.layer}")
                if example.patterns_used:
                    lines.append(f"**Patterns**: {', '.join(example.patterns_used)}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## Analysis Details",
            "",
            f"**Agent Used**: {'Yes' if analysis.agent_used else 'No'}",
        ])

        if analysis.fallback_reason:
            lines.append(f"**Fallback Reason**: {analysis.fallback_reason}")

        overall = analysis.overall_confidence
        lines.extend([
            "",
            f"**Overall Confidence**: {overall.level.value} ({overall.percentage}%)",
            "",
            f"*{overall.reasoning}*",
        ])

        return "\n".join(lines)
