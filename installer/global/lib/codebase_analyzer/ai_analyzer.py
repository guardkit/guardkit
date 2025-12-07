"""
AI-Powered Codebase Analyzer

Main orchestrator for codebase analysis using architectural-reviewer agent.
Coordinates file collection, prompt building, agent invocation, response parsing,
and result serialization.

Following architectural review recommendations:
- Orchestrator pattern for coordination (not doing the work itself)
- Dependency injection for testability
- Graceful fallback when agent unavailable
- Clear error handling and logging
"""

from __future__ import annotations  # Enable Python 3.10+ type syntax in Python 3.9

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('lib.codebase_analyzer.models')
_agent_invoker_module = importlib.import_module('lib.codebase_analyzer.agent_invoker')
_prompt_builder_module = importlib.import_module('lib.codebase_analyzer.prompt_builder')
_response_parser_module = importlib.import_module('lib.codebase_analyzer.response_parser')
_serializer_module = importlib.import_module('lib.codebase_analyzer.serializer')

CodebaseAnalysis = _models_module.CodebaseAnalysis
AgentInvocationError = _models_module.AgentInvocationError
ParseError = _models_module.ParseError
ArchitecturalReviewerInvoker = _agent_invoker_module.ArchitecturalReviewerInvoker
HeuristicAnalyzer = _agent_invoker_module.HeuristicAnalyzer
PromptBuilder = _prompt_builder_module.PromptBuilder
FileCollector = _prompt_builder_module.FileCollector
ResponseParser = _response_parser_module.ResponseParser
FallbackResponseBuilder = _response_parser_module.FallbackResponseBuilder
AnalysisSerializer = _serializer_module.AnalysisSerializer


logger = logging.getLogger(__name__)


class CodebaseAnalyzer:
    """
    Main orchestrator for AI-powered codebase analysis.

    Coordinates the analysis workflow:
    1. Collect file samples from codebase
    2. Build analysis prompt with context
    3. Invoke architectural-reviewer agent (or fallback to heuristics)
    4. Parse and validate response
    5. Return structured CodebaseAnalysis

    Usage:
        analyzer = CodebaseAnalyzer()
        analysis = analyzer.analyze_codebase(
            codebase_path="/path/to/project",
            template_context={"name": "FastAPI", "language": "python"}
        )
    """

    def __init__(
        self,
        agent_invoker: Optional[ArchitecturalReviewerInvoker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        serializer: Optional[AnalysisSerializer] = None,
        max_files: int = 10,  # TASK-PROMPT-SIZE: Reduced from 20 to 10 to keep prompt under 25k tokens
        use_agent: bool = True,
        use_stratified_sampling: bool = True,  # NEW: Enable pattern-aware sampling
        bridge_invoker: Optional[Any] = None  # TASK-769D: Optional agent bridge invoker
    ):
        """
        Initialize codebase analyzer.

        Args:
            agent_invoker: Agent communication layer (DIP - can be injected for testing)
            prompt_builder: Prompt construction layer (DIP)
            response_parser: Response parsing layer (DIP)
            serializer: Result serialization layer (DIP)
            max_files: Maximum number of files to sample (default: 20 for stratified sampling)
            use_agent: Whether to attempt agent invocation (False forces heuristics)
            use_stratified_sampling: Whether to use stratified sampling (default: True)
                                    Set to False to use original random sampling
            bridge_invoker: Optional agent bridge invoker for checkpoint-resume pattern (TASK-769D)
        """
        # TASK-769D: Pass bridge_invoker to ArchitecturalReviewerInvoker so it can use checkpoint-resume
        self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker(bridge_invoker=bridge_invoker)
        self.response_parser = response_parser or ResponseParser()
        self.serializer = serializer or AnalysisSerializer()
        self.max_files = max_files
        self.use_agent = use_agent
        self.use_stratified_sampling = use_stratified_sampling
        self.bridge_invoker = bridge_invoker  # TASK-769D: Store bridge invoker

        # Prompt builder is created per-analysis with template context
        self.prompt_builder_class = prompt_builder.__class__ if prompt_builder else PromptBuilder

    def analyze_codebase(
        self,
        codebase_path: str | Path,
        template_context: Optional[Dict[str, str]] = None,
        save_results: bool = False,
        output_path: Optional[Path] = None
    ) -> CodebaseAnalysis:
        """
        Analyze a codebase and return structured results.

        Args:
            codebase_path: Path to codebase directory
            template_context: Context from template creation (TASK-001)
                             Expected keys: name, language, framework, description
            save_results: Whether to save analysis to JSON
            output_path: Optional custom path for saving results

        Returns:
            CodebaseAnalysis with technology, architecture, and quality info

        Raises:
            ValueError: If codebase_path doesn't exist or isn't a directory
        """
        codebase_path = Path(codebase_path)

        # Validate input
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")
        if not codebase_path.is_dir():
            raise ValueError(f"Codebase path is not a directory: {codebase_path}")

        logger.info(f"Analyzing codebase: {codebase_path}")

        # Step 1: Collect file samples (with stratified sampling option)
        logger.debug("Collecting file samples...")

        if self.use_stratified_sampling:
            try:
                _stratified_sampler_module = importlib.import_module('lib.codebase_analyzer.stratified_sampler')
                StratifiedSampler = _stratified_sampler_module.StratifiedSampler
                logger.info("Using stratified sampling for pattern-aware file selection")

                sampler = StratifiedSampler(codebase_path, max_files=self.max_files)
                file_samples = sampler.collect_stratified_samples()

                # Still need directory tree, use FileCollector for that
                file_collector = FileCollector(codebase_path, max_files=0)
                directory_tree = file_collector.get_directory_tree()

                logger.info(f"Collected {len(file_samples)} stratified samples")
            except Exception as e:
                logger.warning(f"Stratified sampling failed: {e}. Falling back to random sampling.")
                # Fallback to original sampling
                file_collector = FileCollector(codebase_path, max_files=self.max_files)
                file_samples = file_collector.collect_samples()
                directory_tree = file_collector.get_directory_tree()
                logger.info(f"Collected {len(file_samples)} file samples (fallback)")
        else:
            logger.info("Using original random sampling (stratified sampling disabled)")
            file_collector = FileCollector(codebase_path, max_files=self.max_files)
            file_samples = file_collector.collect_samples()
            directory_tree = file_collector.get_directory_tree()
            logger.info(f"Collected {len(file_samples)} file samples")

        # Step 2: Build prompt with template context
        logger.debug("Building analysis prompt...")
        prompt_builder = self.prompt_builder_class(template_context=template_context)
        prompt = prompt_builder.build_analysis_prompt(
            codebase_path=codebase_path,
            file_samples=file_samples,
            directory_structure=directory_tree,
            max_files=self.max_files
        )

        # Step 3: Attempt agent invocation with fallback
        analysis = None

        if self.use_agent and self.agent_invoker.is_available():
            logger.info("Invoking architectural-reviewer agent...")
            try:
                response = self.agent_invoker.invoke_agent(
                    prompt=prompt,
                    agent_name="architectural-reviewer"
                )

                # Step 4: Parse response
                logger.debug("Parsing agent response...")
                analysis = self.response_parser.parse_analysis_response(
                    response=response,
                    codebase_path=str(codebase_path),
                    template_context=template_context,
                    directory_tree=directory_tree  # TASK-FIX-PD03: Pass directory tree
                )

                # TASK-0CE5: Verify example_files were returned
                logger.info(f"Agent analysis completed - received {len(analysis.example_files)} example files")

                # Log each example file for debugging
                for i, example_file in enumerate(analysis.example_files, 1):
                    logger.debug(f"  Example {i}: {example_file.path} ({example_file.layer}) - {example_file.purpose}")

            except AgentInvocationError as e:
                logger.warning(f"Agent invocation failed: {e}. Falling back to heuristics.")
                analysis = None  # Will trigger fallback
            except ParseError as e:
                # TASK-0CE5: If parse error is due to empty example_files, try fallback with file_samples
                if "empty example_files" in str(e).lower():
                    logger.error(f"AI did not return example_files: {e}")
                    logger.info("Attempting fallback: Using file_samples as example_files source")
                    analysis = None  # Will trigger fallback with file_samples
                else:
                    logger.warning(f"Failed to parse agent response: {e}. Falling back to heuristics.")
                    analysis = None  # Will trigger fallback
        else:
            if not self.use_agent:
                logger.info("Agent invocation disabled - using heuristics")
            else:
                logger.info("Agent not available - using heuristics")

        # Fallback to heuristic analysis if needed
        if analysis is None:
            logger.info("Performing heuristic analysis...")
            # TASK-769D: Pass file_samples to fallback analysis
            # TASK-FIX-PD03: Pass directory_tree to fallback analysis
            analysis = self._fallback_analysis(
                codebase_path=codebase_path,
                template_context=template_context,
                file_samples=file_samples,
                directory_tree=directory_tree
            )

        # Step 5: Validate analysis
        is_valid, issues = self.response_parser.validate_analysis(analysis)
        if not is_valid:
            logger.warning(f"Analysis validation issues: {issues}")
        else:
            logger.info("Analysis validation passed")

        # Step 6: Save results if requested
        if save_results:
            if output_path:
                save_path = output_path
            else:
                save_path = self.serializer.save(analysis)
            logger.info(f"Analysis results saved to: {save_path}")

        return analysis

    def _fallback_analysis(
        self,
        codebase_path: Path,
        template_context: Optional[Dict[str, str]],
        file_samples: Optional[list] = None,
        directory_tree: Optional[str] = None  # TASK-FIX-PD03
    ) -> CodebaseAnalysis:
        """
        Perform fallback heuristic analysis when agent is unavailable.

        Args:
            codebase_path: Path to codebase
            template_context: Template context
            file_samples: Optional file samples for analysis (TASK-769D)
            directory_tree: Directory tree from file discovery (TASK-FIX-PD03)

        Returns:
            CodebaseAnalysis from heuristics with appropriate confidence scores
        """
        # Use heuristic analyzer
        # TASK-769D: Pass file_samples to HeuristicAnalyzer
        heuristic_analyzer = HeuristicAnalyzer(codebase_path, file_samples=file_samples)
        heuristic_data = heuristic_analyzer.analyze()

        # Convert to CodebaseAnalysis
        fallback_builder = FallbackResponseBuilder()
        analysis = fallback_builder.build_from_heuristics(
            heuristic_data=heuristic_data,
            codebase_path=str(codebase_path),
            template_context=template_context
        )

        # TASK-FIX-PD03: Set project_structure from directory_tree
        analysis.project_structure = directory_tree

        return analysis

    def quick_analyze(
        self,
        codebase_path: str | Path,
        template_context: Optional[Dict[str, str]] = None
    ) -> CodebaseAnalysis:
        """
        Perform quick analysis without collecting detailed file samples.

        Useful for large codebases or when only high-level info is needed.

        Args:
            codebase_path: Path to codebase
            template_context: Template context

        Returns:
            CodebaseAnalysis with basic information
        """
        codebase_path = Path(codebase_path)

        logger.info(f"Quick analyzing codebase: {codebase_path}")

        # Just get directory structure
        file_collector = FileCollector(codebase_path, max_files=0)
        directory_tree = file_collector.get_directory_tree(max_depth=3)

        # Use heuristic analysis (faster)
        heuristic_analyzer = HeuristicAnalyzer(codebase_path)
        heuristic_data = heuristic_analyzer.analyze()

        # Build analysis
        fallback_builder = FallbackResponseBuilder()
        analysis = fallback_builder.build_from_heuristics(
            heuristic_data=heuristic_data,
            codebase_path=str(codebase_path),
            template_context=template_context
        )

        # Update to indicate this was a quick analysis
        analysis.fallback_reason = "Quick analysis mode - limited detail"

        # TASK-FIX-PD03: Set project_structure from directory_tree
        analysis.project_structure = directory_tree

        return analysis

    def analyze_and_save(
        self,
        codebase_path: str | Path,
        template_context: Optional[Dict[str, str]] = None,
        output_filename: Optional[str] = None
    ) -> tuple[CodebaseAnalysis, Path]:
        """
        Analyze codebase and save results.

        Convenience method combining analyze_codebase() and save().

        Args:
            codebase_path: Path to codebase
            template_context: Template context
            output_filename: Optional custom filename

        Returns:
            Tuple of (analysis, save_path)
        """
        analysis = self.analyze_codebase(
            codebase_path=codebase_path,
            template_context=template_context,
            save_results=False  # We'll save manually
        )

        save_path = self.serializer.save(analysis, filename=output_filename)

        return analysis, save_path

    def load_cached_analysis(
        self,
        codebase_name: Optional[str] = None,
        filepath: Optional[Path] = None
    ) -> Optional[CodebaseAnalysis]:
        """
        Load a previously saved analysis.

        Args:
            codebase_name: Name of codebase (loads most recent)
            filepath: Specific file path to load

        Returns:
            Loaded CodebaseAnalysis or None if not found
        """
        if filepath:
            if filepath.exists():
                return self.serializer.load(filepath)
            return None

        if codebase_name:
            latest = self.serializer.find_latest(codebase_name)
            if latest:
                return self.serializer.load(latest)

        return None

    def export_markdown_report(
        self,
        analysis: CodebaseAnalysis,
        output_path: Path
    ) -> Path:
        """
        Export analysis as markdown report.

        Args:
            analysis: CodebaseAnalysis to export
            output_path: Path to output file

        Returns:
            Path to created markdown file
        """
        return self.serializer.export_markdown(analysis, output_path)

    def get_analysis_summary(self, analysis: CodebaseAnalysis) -> str:
        """
        Get human-readable summary of analysis.

        Args:
            analysis: CodebaseAnalysis to summarize

        Returns:
            Formatted summary string
        """
        return analysis.get_summary()


# Convenience function for quick usage
def analyze_codebase(
    codebase_path: str | Path,
    template_context: Optional[Dict[str, str]] = None,
    save_results: bool = False
) -> CodebaseAnalysis:
    """
    Convenience function for quick codebase analysis.

    Args:
        codebase_path: Path to codebase
        template_context: Template context from TASK-001
        save_results: Whether to save results to JSON

    Returns:
        CodebaseAnalysis object

    Example:
        analysis = analyze_codebase(
            "/path/to/project",
            template_context={"name": "FastAPI", "language": "python"},
            save_results=True
        )
        print(analysis.get_summary())
    """
    analyzer = CodebaseAnalyzer()
    return analyzer.analyze_codebase(
        codebase_path=codebase_path,
        template_context=template_context,
        save_results=save_results
    )
