"""
Response Parser for Agent Responses

Parses and validates JSON responses from the architectural-reviewer agent,
converting them into structured Pydantic models with proper error handling.

Following architectural review recommendations:
- Single responsibility (parsing only)
- Robust error handling with detailed messages
- Schema validation using Pydantic
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import ValidationError
import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('installer.core.lib.codebase_analyzer.models')

CodebaseAnalysis = _models_module.CodebaseAnalysis
TechnologyInfo = _models_module.TechnologyInfo
ArchitectureInfo = _models_module.ArchitectureInfo
QualityInfo = _models_module.QualityInfo
ExampleFile = _models_module.ExampleFile
LayerInfo = _models_module.LayerInfo
ConfidenceScore = _models_module.ConfidenceScore
ParseError = _models_module.ParseError
ConfidenceLevel = _models_module.ConfidenceLevel

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parses architectural-reviewer agent responses into structured models.

    Handles JSON extraction, validation, and error reporting.
    """

    def parse_analysis_response(
        self,
        response: str,
        codebase_path: str,
        template_context: Optional[Dict[str, str]] = None,
        validate_example_files: bool = True,  # TASK-0CE5: Optional validation
        directory_tree: Optional[str] = None  # TASK-FIX-PD03: Directory tree from file discovery
    ) -> CodebaseAnalysis:
        """
        Parse agent response into CodebaseAnalysis model.

        Args:
            response: Raw response from agent (may contain markdown/text)
            codebase_path: Path to analyzed codebase
            template_context: Template context from TASK-001
            validate_example_files: Whether to validate example_files are present (TASK-0CE5)
            directory_tree: Directory tree from file discovery phase (TASK-FIX-PD03)

        Returns:
            Validated CodebaseAnalysis object

        Raises:
            ParseError: If response cannot be parsed or validated
        """
        # Extract JSON from response
        json_data = self._extract_json(response)

        if not json_data:
            raise ParseError("No valid JSON found in agent response")

        # Validate and construct models
        try:
            analysis = self._build_analysis(
                json_data,
                codebase_path,
                template_context,
                validate_example_files=validate_example_files,
                directory_tree=directory_tree  # TASK-FIX-PD03
            )
            return analysis
        except ValidationError as e:
            raise ParseError(f"Invalid response structure: {e}") from e
        except KeyError as e:
            raise ParseError(f"Missing required field: {e}") from e
        except Exception as e:
            raise ParseError(f"Unexpected error parsing response: {e}") from e

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from potentially markdown-formatted response.

        The agent might return JSON wrapped in markdown code blocks:
        ```json
        {...}
        ```

        Args:
            response: Raw response text

        Returns:
            Parsed JSON dict or None if extraction fails
        """
        # Try to find JSON in code blocks first
        json_block_pattern = r"```(?:json)?\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, response, re.DOTALL)

        if matches:
            for match in matches:
                try:
                    json_data = json.loads(match)
                    logger.debug(f"Extracted JSON from code block. Keys: {list(json_data.keys())}")
                    return json_data
                except json.JSONDecodeError:
                    continue

        # Try parsing the entire response as JSON
        try:
            json_data = json.loads(response)
            logger.debug(f"Extracted JSON from raw response. Keys: {list(json_data.keys())}")
            return json_data
        except json.JSONDecodeError:
            pass

        # Try to find JSON object with regex
        json_object_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_object_pattern, response, re.DOTALL)

        for match in matches:
            try:
                json_data = json.loads(match)
                logger.debug(f"Extracted JSON via regex. Keys: {list(json_data.keys())}")
                return json_data
            except json.JSONDecodeError:
                continue

        logger.warning("Failed to extract JSON from agent response")
        return None

    def _build_analysis(
        self,
        data: Dict[str, Any],
        codebase_path: str,
        template_context: Optional[Dict[str, str]],
        validate_example_files: bool = True,  # TASK-0CE5
        directory_tree: Optional[str] = None  # TASK-FIX-PD03
    ) -> CodebaseAnalysis:
        """
        Build CodebaseAnalysis from parsed JSON data.

        Args:
            data: Parsed JSON dictionary
            codebase_path: Path to codebase
            template_context: Template context

        Returns:
            Validated CodebaseAnalysis object
        """
        # Parse technology info
        tech_data = data.get("technology", {})
        technology = TechnologyInfo(
            primary_language=tech_data.get("primary_language", "Unknown"),
            frameworks=tech_data.get("frameworks", []),
            testing_frameworks=tech_data.get("testing_frameworks", []),
            build_tools=tech_data.get("build_tools", []),
            databases=tech_data.get("databases", []),
            infrastructure=tech_data.get("infrastructure", []),
            confidence=self._parse_confidence(tech_data.get("confidence", {}))
        )

        # Parse architecture info
        arch_data = data.get("architecture", {})
        architecture = ArchitectureInfo(
            patterns=arch_data.get("patterns", []),
            architectural_style=arch_data.get("architectural_style", "Unknown"),
            layers=self._parse_layers(arch_data.get("layers", [])),
            key_abstractions=arch_data.get("key_abstractions", []),
            dependency_flow=arch_data.get("dependency_flow", "Not specified"),
            confidence=self._parse_confidence(arch_data.get("confidence", {}))
        )

        # Parse quality info
        quality_data = data.get("quality", {})
        quality = QualityInfo(
            overall_score=quality_data.get("overall_score", 70.0),
            solid_compliance=quality_data.get("solid_compliance", 70.0),
            dry_compliance=quality_data.get("dry_compliance", 70.0),
            yagni_compliance=quality_data.get("yagni_compliance", 70.0),
            test_coverage=quality_data.get("test_coverage"),
            code_smells=quality_data.get("code_smells", []),
            strengths=quality_data.get("strengths", []),
            improvements=quality_data.get("improvements", []),
            confidence=self._parse_confidence(quality_data.get("confidence", {}))
        )

        # Parse example files
        example_files_data = data.get("example_files", [])

        # TASK-0CE5: Log what we received
        logger.debug(f"example_files present in response: {'example_files' in data}")
        if 'example_files' in data:
            logger.debug(f"example_files count: {len(example_files_data)}")
        else:
            logger.warning("AI response missing 'example_files' key - will default to empty list")

        # TASK-0CE5: Validate example_files is not empty (only if validation enabled)
        if validate_example_files and not example_files_data:
            logger.error("AI returned empty example_files - template generation will fail!")
            logger.error("This indicates:")
            logger.error("  1. AI did not follow the prompt instructions")
            logger.error("  2. AI did not understand the example_files requirement")
            logger.error("  3. Prompt may need strengthening")
            raise ParseError(
                "AI analysis returned empty example_files. "
                "Cannot generate templates without example files. "
                "The AI must include 10-20 example_files in the JSON response. "
                "This is a critical requirement for template generation."
            )

        example_files = [self._parse_example_file(f) for f in example_files_data]
        logger.info(f"Successfully parsed {len(example_files)} example files from AI response")

        # Build final analysis
        analysis = CodebaseAnalysis(
            codebase_path=codebase_path,
            technology=technology,
            architecture=architecture,
            quality=quality,
            example_files=example_files,
            template_context=template_context,
            agent_used=True,
            fallback_reason=None,
            project_structure=directory_tree  # TASK-FIX-PD03: Store directory tree
        )

        return analysis

    def _parse_confidence(self, conf_data: Dict[str, Any]) -> ConfidenceScore:
        """Parse confidence score from data."""
        if not conf_data:
            # Default confidence
            return ConfidenceScore(
                level=ConfidenceLevel.MEDIUM,
                percentage=70.0,
                reasoning="No confidence data provided"
            )

        level_str = conf_data.get("level", "medium").lower()
        level_map = {
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW,
            "uncertain": ConfidenceLevel.UNCERTAIN
        }
        level = level_map.get(level_str, ConfidenceLevel.MEDIUM)

        percentage = float(conf_data.get("percentage", 70.0))
        reasoning = conf_data.get("reasoning")

        return ConfidenceScore(
            level=level,
            percentage=percentage,
            reasoning=reasoning
        )

    def _parse_layers(self, layers_data: list) -> list:
        """Parse layer information."""
        layers = []

        for layer_data in layers_data:
            if isinstance(layer_data, dict):
                layer = LayerInfo(
                    name=layer_data.get("name", "Unknown"),
                    description=layer_data.get("description", "No description"),
                    typical_files=layer_data.get("typical_files", []),
                    dependencies=layer_data.get("dependencies", [])
                )
                layers.append(layer)

        return layers

    def _parse_example_file(self, file_data: Dict[str, Any]) -> ExampleFile:
        """Parse example file information."""
        return ExampleFile(
            path=file_data.get("path", ""),
            purpose=file_data.get("purpose", "No purpose specified"),
            layer=file_data.get("layer"),
            patterns_used=file_data.get("patterns_used", []),
            key_concepts=file_data.get("key_concepts", [])
        )

    def validate_analysis(self, analysis: CodebaseAnalysis) -> tuple[bool, list[str]]:
        """
        Validate analysis for completeness and quality.

        Args:
            analysis: CodebaseAnalysis to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check technology info
        if analysis.technology.primary_language == "Unknown":
            issues.append("Primary language not detected")

        if not analysis.technology.frameworks:
            issues.append("No frameworks detected (may be valid for simple projects)")

        # Check architecture info
        if analysis.architecture.architectural_style == "Unknown":
            issues.append("Architectural style not identified")

        if analysis.architecture.confidence.percentage < 50:
            issues.append("Low confidence in architecture analysis")

        # Check quality scores
        if analysis.quality.overall_score < 50:
            issues.append("Low overall quality score - review findings")

        # Check for example files
        if not analysis.example_files:
            issues.append("No example files provided")

        # Overall validation
        is_valid = len(issues) == 0 or all(
            "may be valid" in issue for issue in issues
        )

        return is_valid, issues


class FallbackResponseBuilder:
    """
    Builds analysis responses when agent is unavailable.

    Used to convert heuristic analysis results into proper CodebaseAnalysis
    objects with appropriate confidence scores indicating fallback mode.
    """

    def build_from_heuristics(
        self,
        heuristic_data: Dict[str, Any],
        codebase_path: str,
        template_context: Optional[Dict[str, str]] = None
    ) -> CodebaseAnalysis:
        """
        Build CodebaseAnalysis from heuristic analysis data.

        Args:
            heuristic_data: Data from HeuristicAnalyzer
            codebase_path: Path to codebase
            template_context: Template context

        Returns:
            CodebaseAnalysis with fallback indicators
        """
        parser = ResponseParser()

        # Build analysis from heuristic data
        # TASK-0CE5: Don't validate example_files for fallback (it may be empty initially)
        analysis = parser._build_analysis(
            heuristic_data,
            codebase_path,
            template_context,
            validate_example_files=False
        )

        # Mark as fallback
        analysis.agent_used = False
        analysis.fallback_reason = heuristic_data.get(
            "fallback_reason",
            "Agent unavailable - using heuristic analysis"
        )

        return analysis
