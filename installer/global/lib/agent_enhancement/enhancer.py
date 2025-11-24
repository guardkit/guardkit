"""
Single Agent Enhancer

Enhances individual agent files with template-specific content.

TASK-PHASE-8-INCREMENTAL: Incremental Agent Enhancement Workflow
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
import logging
import time

# Import shared modules using importlib to avoid module resolution issues
import importlib

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Raised when enhancement data fails validation.

    This exception is raised by _validate_enhancement() when the enhancement
    dict returned by AI or static strategy is malformed or missing required keys.

    See Clarification #4 in Architectural Review Clarifications section.
    """
    pass


@dataclass
class EnhancementResult:
    """Result of agent enhancement."""
    success: bool
    agent_name: str
    sections: List[str]  # Sections added
    templates: List[str]  # Templates referenced
    examples: List[str]   # Code examples included
    diff: str            # Unified diff
    error: Optional[str] = None
    strategy_used: Optional[str] = None


class SingleAgentEnhancer:
    """Enhances a single agent with template-specific content."""

    def __init__(
        self,
        strategy: str = "ai",
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize enhancer.

        Args:
            strategy: Enhancement strategy (ai|static|hybrid)
            dry_run: If True, don't apply changes
            verbose: If True, show detailed process
        """
        self.strategy = strategy
        self.dry_run = dry_run
        self.verbose = verbose

        # Create supporting components (lazy loading)
        self._prompt_builder = None
        self._parser = None
        self._applier = None

    @property
    def prompt_builder(self):
        """Lazy-load prompt builder"""
        if self._prompt_builder is None:
            _prompt_builder_module = importlib.import_module(
                'installer.global.lib.agent_enhancement.prompt_builder'
            )
            EnhancementPromptBuilder = _prompt_builder_module.EnhancementPromptBuilder
            self._prompt_builder = EnhancementPromptBuilder()
        return self._prompt_builder

    @property
    def parser(self):
        """Lazy-load parser"""
        if self._parser is None:
            _parser_module = importlib.import_module(
                'installer.global.lib.agent_enhancement.parser'
            )
            EnhancementParser = _parser_module.EnhancementParser
            self._parser = EnhancementParser()
        return self._parser

    @property
    def applier(self):
        """Lazy-load applier"""
        if self._applier is None:
            _applier_module = importlib.import_module(
                'installer.global.lib.agent_enhancement.applier'
            )
            EnhancementApplier = _applier_module.EnhancementApplier
            self._applier = EnhancementApplier()
        return self._applier

    def enhance(
        self,
        agent_file: Path,
        template_dir: Path
    ) -> EnhancementResult:
        """
        Enhance single agent with template-specific content.

        Args:
            agent_file: Path to agent file
            template_dir: Path to template directory

        Returns:
            Enhancement result with success status and details
        """
        agent_name = agent_file.stem

        try:
            # 1. Load agent metadata
            if self.verbose:
                logger.info(f"Loading agent metadata from {agent_file}")

            agent_metadata = self._load_agent_metadata(agent_file)

            # 2. Discover relevant templates
            if self.verbose:
                logger.info(f"Discovering relevant templates in {template_dir}")

            templates = self._discover_relevant_templates(
                agent_metadata,
                template_dir
            )

            if self.verbose:
                logger.info(f"Found {len(templates)} relevant templates")

            # 3. Generate enhancement
            if self.verbose:
                logger.info(f"Generating enhancement using '{self.strategy}' strategy")

            enhancement = self._generate_enhancement(
                agent_metadata,
                templates,
                template_dir
            )

            # 4. Validate enhancement
            if self.verbose:
                logger.info("Validating enhancement")

            self._validate_enhancement(enhancement)

            # 5. Apply enhancement (if not dry run)
            if not self.dry_run:
                if self.verbose:
                    logger.info(f"Applying enhancement to {agent_file}")

                self.applier.apply(agent_file, enhancement)

            # 6. Generate diff
            diff = self.applier.generate_diff(agent_file, enhancement)

            return EnhancementResult(
                success=True,
                agent_name=agent_name,
                sections=enhancement.get("sections", []),
                templates=[str(t) for t in templates],
                examples=enhancement.get("examples", []),
                diff=diff,
                strategy_used=self.strategy
            )

        except Exception as e:
            logger.exception(f"Enhancement failed for {agent_name}")
            return EnhancementResult(
                success=False,
                agent_name=agent_name,
                sections=[],
                templates=[],
                examples=[],
                diff="",
                error=str(e),
                strategy_used=self.strategy
            )

    def _generate_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path],
        template_dir: Path
    ) -> dict:
        """Generate enhancement using selected strategy."""

        if self.strategy == "ai":
            return self._ai_enhancement_with_retry(agent_metadata, templates, template_dir)
        elif self.strategy == "static":
            return self._static_enhancement(agent_metadata, templates)
        elif self.strategy == "hybrid":
            # Try AI with retry, fallback to static
            try:
                return self._ai_enhancement_with_retry(agent_metadata, templates, template_dir)
            except Exception as e:
                logger.warning(f"AI enhancement failed after retries, falling back to static: {e}")
                return self._static_enhancement(agent_metadata, templates)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _ai_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path],
        template_dir: Path
    ) -> dict:
        """
        AI-powered enhancement using agent-content-enhancer.

        Uses direct Task tool API (NOT AgentBridgeInvoker) for synchronous invocation.
        Timeout: 300 seconds. Exceptions propagate to hybrid fallback.

        Args:
            agent_metadata: Agent metadata from frontmatter
            templates: List of relevant template files
            template_dir: Template root directory

        Returns:
            Enhancement dict with sections and content

        Raises:
            TimeoutError: If AI invocation exceeds 300s
            ValidationError: If response structure is invalid
            Exception: For other AI failures
        """
        import time

        start_time = time.time()
        agent_name = agent_metadata.get('name', 'unknown')

        # Build prompt using shared prompt builder
        prompt = self.prompt_builder.build(
            agent_metadata,
            templates,
            template_dir
        )

        if self.verbose:
            logger.info(f"AI Enhancement Started:")
            logger.info(f"  Agent: {agent_name}")
            logger.info(f"  Templates: {len(templates)}")
            logger.info(f"  Prompt size: {len(prompt)} chars")

        try:
            # Use AgentBridgeInvoker for Claude Code integration (same pattern as template-create)
            import importlib
            _agent_bridge_module = importlib.import_module('installer.global.lib.agent_bridge.invoker')
            AgentBridgeInvoker = _agent_bridge_module.AgentBridgeInvoker

            invoker = AgentBridgeInvoker(
                phase=8,  # Phase 8: Agent Enhancement
                phase_name="agent_enhancement"
            )

            result_text = invoker.invoke(
                agent_name="agent-content-enhancer",
                prompt=prompt
            )

            duration = time.time() - start_time

            if self.verbose:
                logger.info(f"AI Response Received:")
                logger.info(f"  Duration: {duration:.2f}s")
                logger.info(f"  Response size: {len(result_text)} chars")

            # Parse response using shared parser
            # TASK-BDRY-316A: Parser now enforces boundaries requirement
            # If AI omits boundaries, parser raises ValueError → caught below → workaround triggered
            try:
                enhancement = self.parser.parse(result_text)
            except ValueError as e:
                # Check if this is a boundaries schema violation
                if "missing required 'boundaries' field" in str(e):
                    logger.warning(f"Parser detected missing boundaries (schema violation): {e}")
                    logger.info("Triggering workaround: will add generic boundaries")

                    # Parse without validation to get partial enhancement
                    import json  # noqa: F811 - Required here due to Python scoping rules
                    try:
                        # Extract JSON from response (reuse parser's extraction logic)
                        json_content = self.parser._extract_json_from_markdown(result_text)
                        if json_content:
                            enhancement = json.loads(json_content)
                        else:
                            enhancement = json.loads(result_text)
                    except json.JSONDecodeError:
                        # Can't parse at all, re-raise original error
                        raise e

                    # Manually add boundaries using workaround
                    from .boundary_utils import generate_generic_boundaries
                    agent_name = agent_metadata.get("name", "unknown")
                    agent_description = agent_metadata.get("description", "")
                    boundaries_content = generate_generic_boundaries(agent_name, agent_description)

                    # Add boundaries to enhancement
                    sections = enhancement.get("sections", [])
                    if "boundaries" not in sections:
                        sections.append("boundaries")
                    enhancement["sections"] = sections
                    enhancement["boundaries"] = boundaries_content

                    logger.info(f"Workaround applied: added generic boundaries for {agent_name}")
                else:
                    # Different ValueError, re-raise
                    raise

            # Validate enhancement structure
            self._validate_enhancement(enhancement)

            # TASK-D70B: Ensure boundaries are present (add if missing)
            # TASK-BDRY-316A: This is now a safety net - should rarely trigger
            # since parser validation catches missing boundaries earlier
            enhancement = self._ensure_boundaries(enhancement, agent_metadata)

            if self.verbose:
                sections = enhancement.get('sections', [])
                logger.info(f"Enhancement Validated:")
                logger.info(f"  Sections: {', '.join(sections)}")

            return enhancement

        except TimeoutError as e:
            duration = time.time() - start_time
            logger.warning(f"AI enhancement timed out after {duration:.2f}s: {e}")
            raise  # Propagates to retry logic or hybrid fallback

        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            logger.error(f"AI response parsing failed after {duration:.2f}s: {e}")
            logger.error(f"  Invalid response (first 200 chars): {result_text[:200]}")
            raise ValidationError(f"Invalid JSON response: {e}")

        except ValidationError as e:
            duration = time.time() - start_time
            logger.error(f"AI returned invalid enhancement structure after {duration:.2f}s: {e}")
            raise  # Don't retry validation errors

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"AI enhancement failed after {duration:.2f}s: {e}")
            logger.exception("Full traceback:")
            raise

    def _ai_enhancement_with_retry(
        self,
        agent_metadata: dict,
        templates: List[Path],
        template_dir: Path,
        max_retries: int = 2
    ) -> dict:
        """
        AI enhancement with exponential backoff retry logic.

        Retries on transient failures (TimeoutError, network errors).
        Does NOT retry on ValidationError (permanent failures).

        Args:
            agent_metadata: Agent metadata from frontmatter
            templates: List of relevant template files
            template_dir: Template root directory
            max_retries: Maximum retry attempts (default: 2)

        Returns:
            Enhancement dict from successful attempt

        Raises:
            ValidationError: If AI returns invalid structure (no retry)
            TimeoutError: If all retry attempts timeout
            Exception: If all retry attempts fail
        """
        import time

        agent_name = agent_metadata.get('name', 'unknown')

        for attempt in range(max_retries + 1):  # 0, 1, 2 = 3 total attempts
            try:
                # Log retry attempt
                if attempt > 0:
                    backoff_seconds = 2 ** (attempt - 1)  # 1s (2^0), 2s (2^1)
                    logger.info(f"Retry attempt {attempt}/{max_retries} for {agent_name} after {backoff_seconds}s backoff")
                    time.sleep(backoff_seconds)
                else:
                    logger.info(f"Initial attempt for {agent_name}")

                # Attempt AI enhancement
                return self._ai_enhancement(agent_metadata, templates, template_dir)

            except ValidationError as e:
                # Don't retry validation errors (permanent failures)
                logger.warning(f"Validation error for {agent_name} (no retry): {e}")
                raise

            except TimeoutError as e:
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} timed out for {agent_name}: {e}. Retrying...")
                    continue  # Retry
                else:
                    logger.error(f"All {max_retries + 1} attempts timed out for {agent_name}")
                    raise

            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed for {agent_name}: {e}. Retrying...")
                    continue  # Retry
                else:
                    logger.error(f"All {max_retries + 1} attempts failed for {agent_name}: {e}")
                    raise

    def _static_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path]
    ) -> dict:
        """Static keyword-based enhancement (Option C from TASK-09E9)."""
        # TASK-D70B: Import boundary utilities for static strategy
        from .boundary_utils import generate_generic_boundaries

        # Simple keyword matching
        agent_name = agent_metadata.get("name", "unknown")
        agent_description = agent_metadata.get("description", "")
        keywords = agent_name.lower().split('-')

        related_templates = []
        for template in templates:
            # Check if any keyword appears in template name
            template_name = template.stem.lower()
            if any(kw in template_name for kw in keywords):
                related_templates.append(str(template))

        # TASK-D70B: Generate generic boundaries for static strategy
        boundaries_content = generate_generic_boundaries(agent_name, agent_description)

        return {
            "sections": ["related_templates", "boundaries"],
            "related_templates": "\n\n## Related Templates\n\n" + "\n".join([
                f"- {t}" for t in related_templates
            ]) if related_templates else "\n\n## Related Templates\n\nNo matching templates found.",
            "boundaries": boundaries_content,
            "examples": [],
            "best_practices": ""
        }

    def _ensure_boundaries(self, enhancement: dict, agent_metadata: dict) -> dict:
        """
        Ensure boundaries section is present in enhancement.

        TASK-D70B: If AI omitted boundaries, generate and add them.
        This allows hybrid content: AI-generated examples/best_practices + static boundaries.

        Args:
            enhancement: Enhancement dict from AI (may be missing boundaries)
            agent_metadata: Agent metadata for generating boundaries

        Returns:
            Enhancement dict with boundaries guaranteed
        """
        # Check if boundaries already present
        if "boundaries" in enhancement.get("sections", []) and "boundaries" in enhancement:
            logger.info("Boundaries already present from AI")
            return enhancement

        # TASK-D70B: Import boundary utilities
        from .boundary_utils import generate_generic_boundaries

        # Generate static boundaries
        agent_name = agent_metadata.get("name", "unknown")
        agent_description = agent_metadata.get("description", "")
        boundaries_content = generate_generic_boundaries(agent_name, agent_description)

        # Add boundaries to enhancement
        sections = enhancement.get("sections", [])
        if "boundaries" not in sections:
            sections.append("boundaries")

        enhancement["sections"] = sections
        enhancement["boundaries"] = boundaries_content

        logger.warning(f"AI omitted boundaries - added generic boundaries for {agent_name}")

        return enhancement

    def _load_agent_metadata(self, agent_file: Path) -> dict:
        """
        Load agent metadata from frontmatter.

        Args:
            agent_file: Path to agent markdown file

        Returns:
            Dict with agent metadata (name, description, etc.)
        """
        try:
            import frontmatter
            agent_doc = frontmatter.loads(agent_file.read_text())
            metadata = agent_doc.metadata

            # Ensure 'name' field exists
            if 'name' not in metadata:
                metadata['name'] = agent_file.stem

            return metadata
        except ImportError:
            # Fallback if frontmatter not available
            logger.warning("frontmatter library not available, using basic parsing")
            return {"name": agent_file.stem}
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}, using basic metadata")
            return {"name": agent_file.stem}

    def _discover_relevant_templates(
        self,
        agent_metadata: dict,
        template_dir: Path
    ) -> List[Path]:
        """
        Discover templates relevant to agent.

        Args:
            agent_metadata: Agent metadata from frontmatter
            template_dir: Template root directory

        Returns:
            List of template file paths
        """
        # For now, return all templates
        # Could be enhanced with AI-powered relevance scoring
        templates_subdir = template_dir / "templates"
        if not templates_subdir.exists():
            return []

        return list(templates_subdir.rglob("*.template"))

    def _validate_enhancement(self, enhancement: dict) -> None:
        """
        Validate enhancement structure.

        Args:
            enhancement: Enhancement dict from strategy

        Raises:
            ValidationError: If validation fails
        """
        required_keys = ["sections"]
        for key in required_keys:
            if key not in enhancement:
                raise ValidationError(f"Missing required key: {key}")

        if not isinstance(enhancement["sections"], list):
            raise ValidationError("'sections' must be a list")
