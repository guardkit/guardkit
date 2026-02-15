"""
Interface for invoking task-work design phases from feature-build.

This module provides a clean interface for executing design phases (1.5-2.8)
from the AutoBuild feature-build workflow, enabling quality gate reuse.

Architecture:
    TASK-POF-003: Uses an inline execution protocol sent directly to the
    Claude Agent SDK, replacing the previous /task-work --design-only skill
    invocation. This eliminates ~840KB of unnecessary context loading per
    session by using setting_sources=["project"] instead of ["user", "project"].

    The inline protocol instructs the SDK agent to execute Phases 1.5
    (task loading), 2 (planning), 2.5B (arch review), 2.7 (complexity),
    and 2.8 (checkpoint) directly.

    Subprocess fallback still uses the guardkit CLI with --design-only flag.

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface
    >>>
    >>> interface = TaskWorkInterface(Path("/path/to/worktree"))
    >>> result = await interface.execute_design_phase("TASK-001", {"no_questions": True})
    >>>
    >>> print(f"Plan: {result.implementation_plan}")
    >>> print(f"Complexity: {result.complexity.get('score')}")
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardkit.orchestrator.agent_invoker import async_heartbeat
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.exceptions import (
    DesignPhaseError,
    QualityGateBlocked,
)

logger = logging.getLogger(__name__)

# SDK timeout in seconds (default: 1200s/20min, can be overridden via env var or constructor)
# Complexity-6+ tasks with full Phase 3-5 pipeline (implementation, testing, code review)
# need ~900-1200s. 1200s provides adequate headroom for most tasks.
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1200"))


@dataclass
class DesignPhaseResult:
    """
    Result from task-work --design-only execution.

    Attributes
    ----------
    implementation_plan : Dict[str, Any]
        The generated implementation plan
    plan_path : Optional[str]
        Path to the saved plan file
    complexity : Dict[str, Any]
        Complexity evaluation results including score
    checkpoint_result : str
        Human checkpoint decision ("approved", "rejected", "skipped")
    architectural_review : Dict[str, Any]
        SOLID/DRY/YAGNI scores from architectural review
    clarifications : Dict[str, Any]
        User clarification decisions from Phase 1.6
    """

    implementation_plan: Dict[str, Any]
    plan_path: Optional[str]
    complexity: Dict[str, Any]
    checkpoint_result: str
    architectural_review: Dict[str, Any]
    clarifications: Dict[str, Any]


class TaskWorkInterface:
    """
    Interface to execute design phases from feature-build.

    Enables feature-build to reuse task-work quality gates via an inline
    execution protocol sent to the Claude Agent SDK.

    TASK-POF-003: Uses inline protocol instead of /task-work skill invocation.
    This reduces context loading from ~840KB to ~78KB per session by using
    setting_sources=["project"] and eliminating user command loading.

    Design phases executed:
        - Phase 1.5: Task Loading
        - Phase 2: Implementation Planning
        - Phase 2.5B: Architectural Review (optional)
        - Phase 2.7: Complexity Evaluation
        - Phase 2.8: Design Checkpoint (auto-approved)

    Attributes
    ----------
    worktree_path : Path
        Path to the worktree where task-work should execute
    sdk_timeout_seconds : int
        Timeout for SDK invocations (default from DEFAULT_SDK_TIMEOUT)

    Example
    -------
    >>> interface = TaskWorkInterface(Path("/path/to/worktree"))
    >>> result = await interface.execute_design_phase("TASK-001", {})
    >>> print(result.implementation_plan)
    """

    def __init__(
        self,
        worktree_path: Path,
        sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT,
    ):
        """
        Initialize TaskWorkInterface.

        Parameters
        ----------
        worktree_path : Path
            Path to the git worktree where task-work should execute
        sdk_timeout_seconds : int
            Timeout for SDK invocations in seconds (default: 600)
        """
        self.worktree_path = Path(worktree_path)
        self.sdk_timeout_seconds = sdk_timeout_seconds
        logger.debug(
            f"TaskWorkInterface initialized with worktree: {worktree_path}, "
            f"sdk_timeout: {sdk_timeout_seconds}s"
        )

    async def execute_design_phase(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> DesignPhaseResult:
        """
        Execute design phases via Claude Agent SDK with inline protocol.

        Sends an inline execution protocol to the SDK that instructs the
        agent to execute Phases 1.5-2.8 directly (TASK-POF-003):
        - Phase 1.5: Task Loading
        - Phase 2: Implementation Planning
        - Phase 2.5B: Architectural Review (optional)
        - Phase 2.7: Complexity Evaluation
        - Phase 2.8: Design Checkpoint (auto-approved)

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        options : Dict[str, Any]
            Options to pass through to task-work:
            - no_questions: Skip Phase 1.6 clarification
            - with_questions: Force Phase 1.6 clarification
            - answers: Inline answers for automation
            - docs: Documentation level
            - defaults: Use default answers

        Returns
        -------
        DesignPhaseResult
            Result containing plan, complexity, and checkpoint decision

        Raises
        ------
        DesignPhaseError
            If task-work --design-only fails or SDK is unavailable
        QualityGateBlocked
            If architectural review score is too low
        """
        logger.info(f"Executing design phase for {task_id} in {self.worktree_path}")

        # TASK-ACO-003: Use protocol-based prompt builder
        prompt = self._build_autobuild_design_prompt(task_id, options)
        logger.debug(f"SDK prompt length: {len(prompt)} chars")

        try:
            # Execute via Claude Agent SDK
            raw_result = await self._execute_via_sdk(prompt)
            return self._parse_design_result(raw_result)

        except ImportError as e:
            # SDK not available - try subprocess fallback
            logger.warning(f"SDK import failed: {e}, trying subprocess fallback")
            args = self._build_task_work_args(task_id, options)
            raw_result = self._execute_via_subprocess(args)
            return self._parse_design_result(raw_result)

    def _build_task_work_args(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> List[str]:
        """
        Build task-work command arguments.

        Parameters
        ----------
        task_id : str
            Task identifier
        options : Dict[str, Any]
            Options to pass through

        Returns
        -------
        List[str]
            Command arguments for task-work
        """
        args = [task_id, "--design-only"]

        # Composite flag: --autobuild-mode bundles autonomous execution optimizations
        if options.get("autobuild_mode"):
            args.append("--autobuild-mode")
        else:
            # Pass through individual flags when not using composite mode
            if options.get("no_questions"):
                args.append("--no-questions")
            if options.get("with_questions"):
                args.append("--with-questions")
            if answers := options.get("answers"):
                args.extend(["--answers", answers])
            if docs := options.get("docs"):
                args.append(f"--docs={docs}")
            if options.get("defaults"):
                args.append("--defaults")
            if options.get("skip_arch_review"):
                args.append("--skip-arch-review")

        return args

    def _build_design_prompt(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> str:
        """
        Build inline design phase execution protocol for SDK invocation.

        Instead of invoking /task-work --design-only (which requires loading
        all user commands ~839KB), this returns a self-contained inline protocol
        (~15KB) that instructs the SDK agent to execute Phases 1.5-2.8 directly.

        TASK-POF-003: Replaced skill invocation with inline protocol to eliminate
        ~840KB of unnecessary context loading per session.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        options : Dict[str, Any]
            Options to pass through:
            - autobuild_mode: Use autonomous optimizations
            - skip_arch_review: Skip Phase 2.5B for simple tasks
            - docs: Documentation level (minimal/standard/comprehensive)
            - no_questions: Skip clarification (implicit in inline protocol)
            - with_questions: Force clarification (not used in inline protocol)
            - answers: Inline answers (not used in inline protocol)
            - defaults: Use defaults (not used in inline protocol)

        Returns
        -------
        str
            Complete inline protocol string for SDK invocation
        """
        from guardkit.orchestrator.quality_gates.design_protocol import (
            build_inline_design_protocol,
        )

        return build_inline_design_protocol(task_id, options, self.worktree_path)

    def _build_autobuild_design_prompt(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> str:
        """
        Build AutoBuild design prompt from extracted protocol file.

        Loads the design protocol from ``autobuild_design_protocol.md`` via
        :func:`load_protocol` and prepends task-specific context. This replaces
        the previous approach of invoking ``/task-work --design-only`` as an
        SDK skill, eliminating ~840KB of unnecessary context loading.

        TASK-ACO-003: Uses extracted protocol files from TASK-ACO-001 instead
        of constructing the protocol inline in Python code.

        Phase skipping encoded directly in prompt:

        ========== ============ =========================================
        Phase      AutoBuild    Rationale
        ========== ============ =========================================
        1.6        **Skip**     No human present
        2          Yes          Essential
        2.1        **Skip**     Adds 30-60s, marginal value
        2.5A       **Skip**     Pattern suggestions add latency
        2.5B       **Lightweight** Inline check, no subagent
        2.7        Yes          Needed for orchestration decisions
        2.8        **Auto-approve** Already implemented
        ========== ============ =========================================

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        options : Dict[str, Any]
            Execution options:
            - skip_arch_review: Omit Phase 2.5B architectural review
            - docs: Documentation level (minimal/standard/comprehensive)

        Returns
        -------
        str
            Complete prompt for SDK invocation, consisting of task context
            header plus the loaded design protocol with task_id substituted.
        """
        from guardkit.orchestrator.prompts import load_protocol

        # Load the extracted design protocol (from TASK-ACO-001)
        protocol_content = load_protocol("autobuild_design_protocol")

        # Substitute {task_id} placeholders in the protocol
        protocol_content = protocol_content.replace("{task_id}", task_id)

        docs_level = options.get("docs", "minimal")
        skip_arch_review = options.get("skip_arch_review", False)

        # Build task context header
        header = (
            f"You are executing the AutoBuild design phase for task {task_id}.\n"
            f"\n"
            f"Documentation Level: {docs_level}\n"
            f"Working Directory: {self.worktree_path}\n"
        )

        # Add phase-skipping instructions
        header += (
            "\n"
            "## AutoBuild Phase Decisions\n"
            "\n"
            "The following phases are SKIPPED in AutoBuild mode:\n"
            "- Phase 1.6 (Clarifying Questions): SKIP — no human present\n"
            "- Phase 2.1 (Library Context Gathering): SKIP — Context7 not available in SDK\n"
            "- Phase 2.5A (Pattern Suggestion): SKIP — Design Patterns MCP not available in SDK\n"
        )

        if skip_arch_review:
            header += "- Phase 2.5B (Architectural Review): SKIP — skip_arch_review flag set\n"
        else:
            header += (
                "- Phase 2.5B (Architectural Review): LIGHTWEIGHT — "
                "inline self-assessment only, do NOT invoke a subagent\n"
            )

        header += (
            "- Phase 2.8 (Design Checkpoint): AUTO-APPROVE — no human present\n"
            "\n"
            "Execute ONLY the phases listed in the protocol below that are not skipped.\n"
            "\n"
            "---\n"
            "\n"
        )

        # If arch review is skipped, strip that section from the protocol
        if skip_arch_review:
            protocol_content = self._strip_arch_review_section(protocol_content)

        return header + protocol_content

    @staticmethod
    def _strip_arch_review_section(protocol: str) -> str:
        """Remove Phase 2.5B section from protocol content.

        Parameters
        ----------
        protocol : str
            Full protocol content

        Returns
        -------
        str
            Protocol with Phase 2.5B section removed
        """
        lines = protocol.split("\n")
        result: List[str] = []
        skip = False

        for line in lines:
            # Start skipping at Phase 2.5B heading
            if line.startswith("## Phase 2.5B"):
                skip = True
                continue
            # Stop skipping at the next ## heading
            if skip and line.startswith("## "):
                skip = False
            if not skip:
                result.append(line)

        return "\n".join(result)

    async def _execute_via_sdk(self, prompt: str) -> Dict[str, Any]:
        """
        Execute task-work via Claude Agent SDK.

        Invokes the SDK with the constructed prompt and collects the output
        stream. Parses the stream to extract design phase results including
        implementation plan, complexity score, and architectural review.

        Parameters
        ----------
        prompt : str
            The complete prompt (e.g., "/task-work TASK-001 --design-only")

        Returns
        -------
        Dict[str, Any]
            Raw result dictionary containing:
            - implementation_plan: Dict with plan content
            - plan_path: Path to saved plan file
            - complexity: Dict with score
            - checkpoint_result: "approved", "rejected", or "skipped"
            - architectural_review: Dict with SOLID/DRY/YAGNI scores
            - clarifications: Dict with user decisions

        Raises
        ------
        ImportError
            If Claude Agent SDK is not installed
        DesignPhaseError
            If SDK execution fails or times out
        """
        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                CLINotFoundError,
                ProcessError,
                CLIJSONDecodeError,
                AssistantMessage,
                TextBlock,
                ToolUseBlock,
                ToolResultBlock,
                ResultMessage,
            )
        except ImportError as e:
            import sys
            diagnosis = (
                f"Claude Agent SDK import failed.\n"
                f"  Error: {e}\n"
                f"  Python: {sys.executable}\n"
                f"  To fix: pip install claude-agent-sdk or pip install guardkit-py[autobuild]"
            )
            logger.error(diagnosis)
            raise ImportError(diagnosis) from e

        logger.info(f"Executing via SDK: {prompt}")
        logger.info(f"Working directory: {self.worktree_path}")

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                permission_mode="acceptEdits",
                max_turns=25,  # Inline protocol is simpler than full task-work
                # TASK-POF-003: Use project-only context (~78KB) instead of user+project (~840KB)
                # Inline protocol replaces /task-work skill invocation, so user skills not needed
                setting_sources=["project"],
            )

            # Extract task_id from prompt for heartbeat logging
            task_id_match = re.search(r"TASK-[A-Z0-9-]+", prompt)
            heartbeat_task_id = task_id_match.group(0) if task_id_match else "unknown"

            collected_output: List[str] = []
            async with asyncio.timeout(self.sdk_timeout_seconds):
                async with async_heartbeat(heartbeat_task_id, "design phase"):
                    async for message in query(prompt=prompt, options=options):
                        # TASK-FB-FIX-005: Properly iterate ContentBlocks instead of str()
                        # message.content is a list[ContentBlock], not a string
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    collected_output.append(block.text)
                                    # Log progress for debugging
                                    if "Phase" in block.text or "Plan saved" in block.text:
                                        logger.debug(f"SDK progress: {block.text[:100]}...")
                                elif isinstance(block, ToolUseBlock):
                                    logger.debug(f"Tool invoked: {block.name}")
                                elif isinstance(block, ToolResultBlock):
                                    # Extract content from tool results if present
                                    if block.content:
                                        collected_output.append(str(block.content))
                        elif isinstance(message, ResultMessage):
                            logger.info(f"SDK completed: turns={message.num_turns}")

            # Join collected output and parse results
            output_text = "\n".join(collected_output)
            logger.info(f"SDK execution completed for design phase")

            # TASK-FB-FIX-006: Log output length for debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Collected output length: {len(output_text)} chars")
                if len(output_text) < 500:
                    logger.debug(f"Full output: {output_text}")
                else:
                    logger.debug(f"Output preview: {output_text[:500]}...")

            return self._parse_sdk_output(output_text)

        except asyncio.TimeoutError:
            error_msg = f"SDK timeout after {self.sdk_timeout_seconds}s"
            logger.error(error_msg)
            raise DesignPhaseError(phase="design", error=error_msg)

        except CLINotFoundError as e:
            error_msg = (
                "Claude Code CLI not installed. "
                "Run: npm install -g @anthropic-ai/claude-code"
            )
            logger.error(error_msg)
            raise DesignPhaseError(phase="design", error=error_msg) from e

        except ProcessError as e:
            error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
            logger.error(error_msg)
            raise DesignPhaseError(phase="design", error=error_msg) from e

        except CLIJSONDecodeError as e:
            error_msg = f"Failed to parse SDK response: {e}"
            logger.error(error_msg)
            raise DesignPhaseError(phase="design", error=error_msg) from e

        except Exception as e:
            logger.exception(f"Unexpected error executing design phase: {e}")
            raise DesignPhaseError(phase="design", error=str(e)) from e

    def _parse_sdk_output(self, output: str) -> Dict[str, Any]:
        """
        Parse SDK output to extract design phase results.

        Extracts key information from the task-work --design-only output
        including plan path, complexity score, architectural review scores,
        and checkpoint result.

        Parameters
        ----------
        output : str
            Raw output from SDK stream

        Returns
        -------
        Dict[str, Any]
            Parsed result dictionary with design phase data
        """
        result: Dict[str, Any] = {
            "implementation_plan": {},
            "plan_path": None,
            "complexity": {"score": 5},
            "checkpoint_result": "approved",
            "architectural_review": {
                "score": 80,
                "solid": 80,
                "dry": 80,
                "yagni": 80,
            },
            "clarifications": {},
        }

        # Extract plan path - look for "Plan saved to:" or similar patterns
        plan_path_patterns = [
            r"Plan saved to[:\s]+([^\s\n]+)",
            r"Plan saved[:\s]+to[:\s]+([^\s\n]+)",
            r"Implementation plan saved[:\s]+to[:\s]+([^\s\n]+)",
            r"Implementation plan saved[:\s]+([^\s\n]+)",
            r"Created implementation plan[:\s]+([^\s\n]+)",  # Task-work actual output format
            r"plan_path[:\s]+[\"']?([^\s\n\"']+)",
            r"(docs/state/[A-Z0-9-]+/implementation_plan\.(?:md|json))",
            r"(\.claude/task-plans/[A-Z0-9-]+-implementation-plan\.(?:md|json))",
        ]

        for pattern in plan_path_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                plan_path = match.group(1) if match.lastindex else match.group(0)
                result["plan_path"] = plan_path
                logger.debug(f"Extracted plan path: {plan_path}")
                break

        # If no explicit path found, check if plan was created at expected location
        if not result["plan_path"]:
            # Extract task_id from output if possible
            task_id_match = re.search(r"TASK-[A-Z0-9-]+", output)
            if task_id_match:
                task_id = task_id_match.group(0)
                expected_path = self._get_plan_path(task_id)
                if expected_path.exists():
                    result["plan_path"] = str(expected_path)
                    logger.debug(f"Found plan at expected path: {expected_path}")

        # Load implementation plan content if path exists
        if result["plan_path"]:
            plan_path = Path(result["plan_path"])
            if not plan_path.is_absolute():
                plan_path = self.worktree_path / plan_path
            if plan_path.exists():
                try:
                    with open(plan_path) as f:
                        if plan_path.suffix == ".json":
                            result["implementation_plan"] = json.load(f)
                        else:
                            result["implementation_plan"] = {"content": f.read()}
                    logger.debug(f"Loaded implementation plan from {plan_path}")
                except Exception as e:
                    logger.warning(f"Failed to load plan from {plan_path}: {e}")

        # Extract complexity score - look for "Complexity: N/10" or "Score: N"
        complexity_patterns = [
            r"[Cc]omplexity[:\s]+(\d+)/10",
            r"[Cc]omplexity\s+[Ss]core[:\s]+(\d+)",
            r"complexity_score[:\s]+(\d+)",
            r"[Ss]core[:\s]+(\d+)/10",
        ]

        for pattern in complexity_patterns:
            match = re.search(pattern, output)
            if match:
                score = int(match.group(1))
                result["complexity"] = {"score": score}
                logger.debug(f"Extracted complexity score: {score}")
                break

        # Extract architectural review scores - look for SOLID/DRY/YAGNI
        arch_score_match = re.search(
            r"[Aa]rchitectural.*?[Ss]core[:\s]+(\d+)",
            output
        )
        if arch_score_match:
            result["architectural_review"]["score"] = int(arch_score_match.group(1))
            logger.debug(f"Extracted architectural score: {arch_score_match.group(1)}")

        # Look for individual principle scores
        solid_match = re.search(r"SOLID[:\s]+(\d+)", output)
        if solid_match:
            result["architectural_review"]["solid"] = int(solid_match.group(1))

        dry_match = re.search(r"DRY[:\s]+(\d+)", output)
        if dry_match:
            result["architectural_review"]["dry"] = int(dry_match.group(1))

        yagni_match = re.search(r"YAGNI[:\s]+(\d+)", output)
        if yagni_match:
            result["architectural_review"]["yagni"] = int(yagni_match.group(1))

        # Extract checkpoint result
        if re.search(r"checkpoint.*?rejected|rejected.*?checkpoint", output, re.IGNORECASE):
            result["checkpoint_result"] = "rejected"
        elif re.search(r"checkpoint.*?skipped|auto-?proceed", output, re.IGNORECASE):
            result["checkpoint_result"] = "skipped"
        elif re.search(r"checkpoint.*?approved|design.*?approved|DESIGN_APPROVED", output, re.IGNORECASE):
            result["checkpoint_result"] = "approved"

        logger.debug(f"Parsed SDK output result: {result}")
        return result

    def _execute_via_import(
        self,
        task_id: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute task-work via direct Python import.

        This is the preferred method as it avoids subprocess overhead
        and enables better error handling.

        Parameters
        ----------
        task_id : str
            Task identifier
        options : Dict[str, Any]
            Options dictionary

        Returns
        -------
        Dict[str, Any]
            Raw result from task-work executor

        Raises
        ------
        ImportError
            If task-work executor module is not available
        DesignPhaseError
            If execution fails
        """
        # Note: This import path may need adjustment based on actual
        # task-work implementation location
        try:
            from installer.core.commands.lib.plan_persistence import (
                load_plan,
                plan_exists,
            )
        except ImportError as e:
            logger.warning(f"Could not import plan_persistence: {e}")
            raise ImportError("task-work executor not available") from e

        # For now, we'll read the saved plan directly
        # In the future, this could invoke the actual task-work executor

        # Check if plan exists for this task
        plan_path = self._get_plan_path(task_id)
        complexity_path = self._get_complexity_path(task_id)

        result = {
            "success": True,
            "task_id": task_id,
            "implementation_plan": {},
            "plan_path": None,
            "complexity": {"score": 5},  # Default medium complexity
            "checkpoint_result": "approved",  # Default to approved
            "architectural_review": {
                "score": 80,
                "solid": 80,
                "dry": 80,
                "yagni": 80,
            },
            "clarifications": {},
        }

        # Try to load existing plan
        if plan_path.exists():
            try:
                with open(plan_path) as f:
                    if plan_path.suffix == ".json":
                        result["implementation_plan"] = json.load(f)
                    else:
                        # Markdown plan - parse basic structure
                        result["implementation_plan"] = {"content": f.read()}
                result["plan_path"] = str(plan_path)
            except Exception as e:
                logger.warning(f"Could not load plan from {plan_path}: {e}")

        # Try to load complexity score
        if complexity_path.exists():
            try:
                with open(complexity_path) as f:
                    result["complexity"] = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load complexity from {complexity_path}: {e}")

        return result

    def _execute_via_subprocess(self, args: List[str]) -> Dict[str, Any]:
        """
        Execute task-work via subprocess.

        Fallback method when direct import is not available.

        Parameters
        ----------
        args : List[str]
            Command arguments

        Returns
        -------
        Dict[str, Any]
            Raw result from task-work execution

        Raises
        ------
        DesignPhaseError
            If subprocess execution fails
        """
        cmd = ["guardkit", "task-work"] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for design phases
            )

            if result.returncode != 0:
                raise DesignPhaseError(
                    phase="design",
                    error=f"task-work failed: {result.stderr}",
                )

            # Parse JSON output if available
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # Return minimal result if output isn't JSON
                return {
                    "success": True,
                    "output": result.stdout,
                    "implementation_plan": {},
                    "complexity": {"score": 5},
                    "checkpoint_result": "approved",
                    "architectural_review": {"score": 80},
                    "clarifications": {},
                }

        except subprocess.TimeoutExpired:
            raise DesignPhaseError(
                phase="design",
                error="task-work timed out after 10 minutes",
            )
        except FileNotFoundError:
            raise DesignPhaseError(
                phase="design",
                error="guardkit CLI not found - is it installed?",
            )

    def _parse_design_result(self, raw_result: Dict[str, Any]) -> DesignPhaseResult:
        """
        Parse raw task-work result into DesignPhaseResult.

        Parameters
        ----------
        raw_result : Dict[str, Any]
            Raw result from task-work execution

        Returns
        -------
        DesignPhaseResult
            Parsed result object

        Raises
        ------
        QualityGateBlocked
            If architectural review score is below threshold
        """
        # Extract architectural review score
        arch_review = raw_result.get("architectural_review", {})
        arch_score = arch_review.get("score", 80)

        # Check if architectural review blocked
        if arch_score < 60:
            raise QualityGateBlocked(
                reason=f"Architectural review score {arch_score}/100 below threshold (60)",
                gate_name="architectural_review",
                details=arch_review,
            )

        return DesignPhaseResult(
            implementation_plan=raw_result.get("implementation_plan", {}),
            plan_path=raw_result.get("plan_path"),
            complexity=raw_result.get("complexity", {"score": 5}),
            checkpoint_result=raw_result.get("checkpoint_result", "approved"),
            architectural_review=arch_review,
            clarifications=raw_result.get("clarifications", {}),
        )

    def _get_plan_path(self, task_id: str) -> Path:
        """Get path to implementation plan file.

        Uses centralized TaskArtifactPaths for consistent path resolution.
        """
        # Use centralized path resolution that checks all locations
        plan_path = TaskArtifactPaths.find_implementation_plan(task_id, self.worktree_path)
        if plan_path:
            return plan_path

        # Return preferred path even if it doesn't exist
        return TaskArtifactPaths.preferred_plan_path(task_id, self.worktree_path)

    def _get_complexity_path(self, task_id: str) -> Path:
        """Get path to complexity score file.

        Uses centralized TaskArtifactPaths for consistent path resolution.
        """
        return TaskArtifactPaths.complexity_score_path(task_id, self.worktree_path)

    def execute_security_review(
        self,
        task_id: str,
        worktree_path: Optional[Path] = None,
        config: Optional["SecurityConfig"] = None,
    ) -> "SecurityReviewResult":
        """
        Execute security review for Phase 2.5C.

        Runs SecurityReviewer on the worktree and persists results to
        .guardkit/autobuild/{task_id}/security_review.json.

        This method is called during pre-loop Phase 2.5C (after architectural
        review Phase 2.5B). Coach can later verify the results without
        re-running the checks.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree_path : Optional[Path]
            Path to worktree (defaults to self.worktree_path)
        config : Optional[SecurityConfig]
            Security configuration (defaults to SecurityConfig())

        Returns
        -------
        SecurityReviewResult
            Complete security review result with findings and blocking decision

        Example
        -------
        >>> interface = TaskWorkInterface("/path/to/worktree")
        >>> result = interface.execute_security_review("TASK-001")
        >>> if result.blocked:
        ...     print(f"Security blocked: {result.critical_count} critical findings")
        """
        from guardkit.orchestrator.quality_gates.security_review import (
            SecurityReviewer,
            SecurityReviewResult,
            save_security_review,
        )
        from guardkit.orchestrator.security_config import SecurityConfig

        # Use instance worktree_path if not provided
        target_worktree = Path(worktree_path) if worktree_path else self.worktree_path

        # Use default config if not provided
        if config is None:
            config = SecurityConfig()

        logger.info(f"Executing security review for {task_id} (Phase 2.5C)")

        # Run security review
        reviewer = SecurityReviewer(
            worktree_path=target_worktree,
            config=config,
        )
        result = reviewer.run(task_id)

        # Persist result for Coach verification
        save_security_review(result, target_worktree)

        logger.info(
            f"Security review complete for {task_id}: "
            f"critical={result.critical_count}, blocked={result.blocked}"
        )

        return result
