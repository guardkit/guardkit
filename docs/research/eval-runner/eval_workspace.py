"""EvalWorkspace — sandboxed workspace management for eval runs.

Extracted from eval_runner.py into its own module to support
the guardkit_vs_vanilla eval type, which requires two independent
workspaces forked from different templates.

All evals use temp directories on the local filesystem.
Workspaces are cleaned up automatically after the eval completes.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Directory containing workspace templates
EVAL_WORKSPACES_DIR = Path(__file__).parent / "workspaces"


class EvalWorkspace:
    """Manages a sandboxed workspace for a single eval run.

    Creates a temporary directory seeded from a template.
    Cleaned up automatically via teardown() or use as async context manager.

    For guardkit_vs_vanilla evals, use create_forked_pair() instead.
    """

    def __init__(self, eval_id: str, template: str = "blank") -> None:
        self.eval_id = eval_id
        self.template = template
        self._tmpdir: Optional[tempfile.TemporaryDirectory] = None
        self.path: Optional[Path] = None

    async def create(self) -> Path:
        """Provision workspace from template. Returns workspace path."""
        self._tmpdir = tempfile.TemporaryDirectory(prefix=f"eval_{self.eval_id}_")
        self.path = Path(self._tmpdir.name)
        await self._seed(self.path, self.template)
        return self.path

    async def teardown(self) -> None:
        """Remove workspace directory."""
        if self._tmpdir:
            try:
                self._tmpdir.cleanup()
                logger.debug(f"[{self.eval_id}] Workspace cleaned up")
            except Exception as e:
                logger.warning(f"[{self.eval_id}] Workspace cleanup failed: {e}")
            self._tmpdir = None
            self.path = None

    @staticmethod
    async def create_forked_pair(
        eval_id: str,
        guardkit_template: str = "guardkit-project",
        vanilla_template: str = "plain-project",
    ) -> tuple["ForkedWorkspace", "ForkedWorkspace"]:
        """Provision two independent workspaces from different templates.

        The GuardKit workspace has CLAUDE.md and .guardkit/ present.
        The vanilla workspace has the same codebase but no GuardKit config.
        Both start from clean, equivalent snapshots.

        Returns (guardkit_workspace, vanilla_workspace).

        Usage:
            gk_ws, van_ws = await EvalWorkspace.create_forked_pair(eval_id)
            try:
                # run both arms
            finally:
                await gk_ws.teardown()
                await van_ws.teardown()
        """
        gk_ws = ForkedWorkspace(eval_id, "guardkit", guardkit_template)
        van_ws = ForkedWorkspace(eval_id, "vanilla", vanilla_template)

        await gk_ws.create()
        await van_ws.create()

        logger.info(
            f"[{eval_id}] Forked pair created:\n"
            f"  GuardKit arm: {gk_ws.path}\n"
            f"  Vanilla arm:  {van_ws.path}"
        )
        return gk_ws, van_ws

    @staticmethod
    async def _seed(path: Path, template: str) -> None:
        """Seed workspace from template directory."""
        template_path = EVAL_WORKSPACES_DIR / template

        # Create evidence directory for criterion outputs
        (path / ".eval" / "evidence").mkdir(parents=True, exist_ok=True)

        if template_path.exists() and template_path.is_dir():
            shutil.copytree(str(template_path), str(path), dirs_exist_ok=True)
            logger.debug(f"Seeded workspace from template '{template}'")
        else:
            if template not in ("blank", ""):
                logger.warning(
                    f"Template '{template}' not found at {template_path}. "
                    f"Using blank workspace."
                )


class ForkedWorkspace(EvalWorkspace):
    """A workspace that is one arm of a forked pair.

    Identical to EvalWorkspace but carries an arm label for logging
    and result attribution.
    """

    def __init__(self, eval_id: str, arm: str, template: str) -> None:
        super().__init__(eval_id, template)
        self.arm = arm  # "guardkit" or "vanilla"

    async def create(self) -> Path:
        self._tmpdir = tempfile.TemporaryDirectory(
            prefix=f"eval_{self.eval_id}_{self.arm}_"
        )
        self.path = Path(self._tmpdir.name)
        await self._seed(self.path, self.template)
        logger.info(f"[{self.eval_id}] {self.arm} workspace: {self.path}")
        return self.path

    def write_input(self, input_text: str) -> Path:
        """Write resolved input text to input.txt in the workspace.

        Called by InputResolver before agent runs.
        Returns path to input.txt.
        """
        if not self.path:
            raise RuntimeError("Workspace not created yet")
        input_file = self.path / "input.txt"
        input_file.write_text(input_text, encoding="utf-8")
        return input_file
