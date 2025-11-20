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
            return self._ai_enhancement(agent_metadata, templates, template_dir)
        elif self.strategy == "static":
            return self._static_enhancement(agent_metadata, templates)
        elif self.strategy == "hybrid":
            # Try AI, fallback to static
            try:
                return self._ai_enhancement(agent_metadata, templates, template_dir)
            except Exception as e:
                logger.warning(f"AI enhancement failed, falling back to static: {e}")
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
        AI-powered enhancement.

        Uses agent-content-enhancer agent via direct Task tool invocation.
        Synchronous call with 300-second timeout.
        """
        # Build prompt using shared prompt builder
        prompt = self.prompt_builder.build(
            agent_metadata,
            templates,
            template_dir
        )

        # TODO: Implement actual AI invocation via Task tool
        # For now, return placeholder response
        logger.warning("AI enhancement not yet fully implemented - using placeholder")

        # Placeholder implementation
        return {
            "sections": ["related_templates", "examples"],
            "related_templates": "## Related Templates\n\n" + "\n".join([
                f"- {t.relative_to(template_dir)}" for t in templates[:5]
            ]),
            "examples": "## Code Examples\n\n(AI-generated examples would go here)",
            "best_practices": ""
        }

    def _static_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path]
    ) -> dict:
        """Static keyword-based enhancement (Option C from TASK-09E9)."""
        # Simple keyword matching
        agent_name = agent_metadata.get("name", "unknown")
        keywords = agent_name.lower().split('-')

        related_templates = []
        for template in templates:
            # Check if any keyword appears in template name
            template_name = template.stem.lower()
            if any(kw in template_name for kw in keywords):
                related_templates.append(str(template))

        return {
            "sections": ["related_templates"],
            "related_templates": "\n\n## Related Templates\n\n" + "\n".join([
                f"- {t}" for t in related_templates
            ]) if related_templates else "\n\n## Related Templates\n\nNo matching templates found.",
            "examples": [],
            "best_practices": ""
        }

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
