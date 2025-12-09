"""
Single Agent Enhancer

Enhances individual agent files with template-specific content.

TASK-PHASE-8-INCREMENTAL: Incremental Agent Enhancement Workflow
TASK-PD-003: Enhanced to support split-file output mode
"""

from pathlib import Path
from typing import List, Optional
import json
import logging
import time

# Import shared modules using importlib to avoid module resolution issues
import importlib

# Import EnhancementResult from models (TASK-PD-003)
# Handle both relative and absolute imports for test compatibility
try:
    from .models import EnhancementResult
except ImportError:
    from models import EnhancementResult

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Raised when enhancement data fails validation.

    This exception is raised by _validate_enhancement() when the enhancement
    dict returned by AI or static strategy is malformed or missing required keys.

    See Clarification #4 in Architectural Review Clarifications section.
    """
    pass


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
        template_dir: Path,
        split_output: bool = True
    ) -> EnhancementResult:
        """
        Enhance single agent with template-specific content.

        TASK-PD-003: Enhanced to support split-file output mode.

        Args:
            agent_file: Path to agent file
            template_dir: Path to template directory
            split_output: If True (default), create separate core and extended files.
                         If False, create single file (backward compatible mode).

        Returns:
            Enhancement result with success status and file paths.
            Result includes:
            - core_file: Path to core agent file
            - extended_file: Path to extended file (split mode only, None otherwise)
            - split_output: Whether split mode was used

        Example (split mode):
            >>> result = enhancer.enhance(agent_file, template_dir, split_output=True)
            >>> print(f"Core: {result.core_file}")
            >>> print(f"Extended: {result.extended_file}")

        Example (single-file mode):
            >>> result = enhancer.enhance(agent_file, template_dir, split_output=False)
            >>> print(f"File: {result.core_file}")
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
            core_file = None
            extended_file = None

            if not self.dry_run:
                if split_output:
                    # Split-file mode: Create core + extended files
                    if self.verbose:
                        logger.info(f"Applying enhancement with split output to {agent_file}")

                    # Verify apply_with_split() is available (TASK-PD-001 dependency)
                    if not hasattr(self.applier, 'apply_with_split'):
                        raise RuntimeError(
                            "split_output=True requires TASK-PD-001 completion. "
                            "Method applier.apply_with_split() not available."
                        )

                    split_result = self.applier.apply_with_split(agent_file, enhancement)
                    core_file = split_result.core_path
                    extended_file = split_result.extended_path
                else:
                    # Single-file mode: Backward compatible behavior
                    if self.verbose:
                        logger.info(f"Applying enhancement to {agent_file} (single-file mode)")

                    self.applier.apply(agent_file, enhancement)
                    core_file = agent_file
                    extended_file = None
            else:
                # Dry-run mode: Return paths but don't create files
                core_file = agent_file
                if split_output:
                    # Derive extended file name
                    extended_file = agent_file.parent / f"{agent_file.stem}-ext{agent_file.suffix}"
                else:
                    extended_file = None

            # 6. Generate diff
            diff = self.applier.generate_diff(agent_file, enhancement)

            # TASK-FIX-PD03: Include enhancement_data for debugging/passthrough
            return EnhancementResult(
                success=True,
                agent_name=agent_name,
                sections=enhancement.get("sections", []),
                templates=[str(t) for t in templates],
                examples=enhancement.get("examples", []),
                diff=diff,
                strategy_used=self.strategy,
                core_file=core_file,
                extended_file=extended_file,
                split_output=split_output,
                enhancement_data=enhancement
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
                strategy_used=self.strategy,
                core_file=None,
                extended_file=None,
                split_output=split_output,
                enhancement_data=None
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
            import json  # Local import required - ensures scope covers all exception handlers (line 341)

            # Use AgentBridgeInvoker for Claude Code integration (same pattern as template-create)
            import importlib
            _agent_bridge_module = importlib.import_module('installer.global.lib.agent_bridge.invoker')
            AgentBridgeInvoker = _agent_bridge_module.AgentBridgeInvoker

            invoker = AgentBridgeInvoker(
                phase=8,  # Phase 8: Agent Enhancement
                phase_name="agent_enhancement"
            )

            # Check for existing response from previous invocation (checkpoint-resume pattern)
            if invoker.has_response():
                # Response file exists - load cached response
                result_text = invoker.load_response()
                if self.verbose:
                    logger.info("  ✓ Loaded agent response from checkpoint")
            else:
                # No response yet - invoke agent
                # This will write .agent-request.json and exit with code 42
                # Claude Code will see the exit 42 and invoke the agent-content-enhancer
                # On re-run, has_response() will return True and we'll load the cached response
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

                    # Parse without validation to get partial enhancement (using local json import)
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

            # TASK-FIX-AE01: Extract context around error position for better debugging
            error_pos = e.pos if hasattr(e, 'pos') else 0
            context_start = max(0, error_pos - 50)
            context_end = min(len(result_text), error_pos + 50)
            context_snippet = result_text[context_start:context_end]

            # Build comprehensive error message with actionable suggestions
            logger.error(
                f"AI response parsing failed after {duration:.2f}s\n"
                f"  Error: {e.msg} at position {error_pos}\n"
                f"  Context: ...{context_snippet}...\n"
                f"  Response size: {len(result_text)} chars\n"
                f"  Likely cause: AI response truncated or corrupted\n"
                f"  Suggestion: Re-run with --static for reliable results"
            )
            raise ValidationError(f"Invalid JSON at position {error_pos}: {e.msg}")

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

    def reparse_enhanced_file(self, agent_file: Path) -> dict:
        """
        Re-parse enhanced agent file to extract enhancement data for splitting.

        Used when AI writes monolithic file directly and we need to apply
        split post-hoc. Extracts sections from the enhanced markdown.

        TASK-FIX-DBFA: Added for post-AI split support.

        Args:
            agent_file: Path to enhanced agent file (monolithic)

        Returns:
            Enhancement dict compatible with apply_with_split()

        Raises:
            ValueError: If file cannot be parsed or has insufficient content

        Examples:
            >>> enhancer = SingleAgentEnhancer(strategy='ai')
            >>> agent_file = Path('agents/test-agent.md')
            >>> enhancement = enhancer.reparse_enhanced_file(agent_file)
            >>> enhancement['sections']
            ['frontmatter', 'quick_start', 'boundaries', 'capabilities']
        """
        try:
            content = agent_file.read_text()
        except (OSError, IOError, PermissionError) as e:
            raise ValueError(f"Cannot read enhanced file {agent_file}: {e}")

        # Parse markdown sections
        enhancement = {"sections": []}
        current_section = None
        section_content = []

        lines = content.split('\n')
        in_frontmatter = False
        frontmatter_lines = []
        frontmatter_done = False

        for i, line in enumerate(lines):
            # Handle frontmatter
            if line.strip() == '---':
                if i == 0:
                    in_frontmatter = True
                    frontmatter_lines.append(line)
                    continue
                elif in_frontmatter and not frontmatter_done:
                    in_frontmatter = False
                    frontmatter_done = True
                    frontmatter_lines.append(line)
                    enhancement['frontmatter'] = '\n'.join(frontmatter_lines)
                    enhancement['sections'].append('frontmatter')
                    continue

            if in_frontmatter:
                frontmatter_lines.append(line)
                continue

            # Detect section headers (## Section Name)
            if line.startswith('## '):
                # Save previous section
                if current_section:
                    section_key = self._normalize_section_key(current_section)
                    enhancement[section_key] = '\n'.join(section_content)
                    if section_key not in enhancement['sections']:
                        enhancement['sections'].append(section_key)

                # Start new section
                current_section = line[3:].strip()
                section_content = [line]
            elif current_section:
                section_content.append(line)

        # Save last section
        if current_section:
            section_key = self._normalize_section_key(current_section)
            enhancement[section_key] = '\n'.join(section_content)
            if section_key not in enhancement['sections']:
                enhancement['sections'].append(section_key)

        # Validate the parsed content has required structure
        if 'frontmatter' not in enhancement:
            raise ValueError(f"Enhanced file {agent_file} missing frontmatter (YAML header)")

        if len(enhancement['sections']) < 2:  # frontmatter + at least one section
            raise ValueError(
                f"Enhanced file {agent_file} has insufficient sections: "
                f"{len(enhancement['sections'])} found (minimum 2 required)"
            )

        if self.verbose:
            logger.info(f"Re-parsed {len(enhancement['sections'])} sections from enhanced file")

        return enhancement

    def _normalize_section_key(self, section_name: str) -> str:
        """
        Convert section header to snake_case key.

        Args:
            section_name: Section header text (e.g., "Quick Start")

        Returns:
            Normalized key (e.g., "quick_start")
        """
        return section_name.lower().replace(' ', '_').replace('-', '_')
