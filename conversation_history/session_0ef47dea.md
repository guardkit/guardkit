## Summarized at 2026-07-04T22:21:54.062102+00:00

Human: You are the code-reviewer specialist for task TASK-QAV-006.

Task context (from the task markdown):
## Description
FEAT-10AC delivered the L4 **guard** (`_apply_behavioural_oracle_guard`,
`agent_invoker.py` ~L6510, wired at the verdict seam ~L2441, fully unit
tested) but NOT the **producer**: `CoachValidator.gather_evidence` hardcodes
`behavioural_oracle=None` (`coach_validator.py` ~L3581, comment "Wave-4"),
so the guard no-ops forever and the L4 hard gate can never fire. The
TASK-QAV-005 dogfood test was soft-pedaled to match ("documents the L4 field
as None until Wave-4 is wired") — a runner-without-producer instance caught
at merge review, on the very feature built to catch that class.

This task wires the producer, honouring the FEAT-10AC spec exactly
(TASK-QAV-004's original ACs, `features/qav-behavioural-gates/` scenarios
tagged @task:TASK-QAV-004):

1. **Discovery by artefact presence**: oracle file(s) at
   `tests/acceptance/*_roundtrip.py` in the worktree; no opt-in flag
   (`.claude/rules/activate-by-artefact-not-opt-in-flag.md`).
2. **Independence check**: the oracle file must NOT be in the turn's
   authored set (`files_authored` when present, else `files_created ∪
   files_modified`; never the git-enriched set). Player-auth
[...truncated]

Phase 4 summary (test-orchestrator outcome):
- tests_run: 13
- tests_failed: 0
- coverage_pct: 0.0
- quality_gates_passed: True
- output_summary: Result:
============================== 13 passed in 4.91s ==============================

Your job:
1. Review the implementation in the worktree against the task's acceptance criteria using Read/Search/Grep.
2. Apply the review checklist from your agent definition (build, requirements, code quality, testing, security, performance, documentation).
3. Report findings via your normal response stream — the orchestrator records the review outcome in specialist_results.json.
Do NOT modify source files: the Write tool is intentionally withheld from this invocation.
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/'}, 'id': 'MspFUuMziMlNrFfnt7guWMAu78LjsPk9', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.clarification_execution.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.claude/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.coverage', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.env.example', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.git', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.github/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.gitignore', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.mcp.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.pytest_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.tmp_clarification_context_sensitive_coach.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.venv/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CHANGELOG.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CLARIFICATION_EXECUTION_TASK-FBSDK-020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CLARIFICATION_QUICK_REFERENCE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CLARIFICATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CLAUDE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CNAME', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/CONTRIBUTING.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/DESIGN-DELIVERY-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/FEAT-AOF-verify/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/FastApi_feature_plans.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/IMPLEMENTATION-SUMMARY-TASK-AB-584A.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/IMPLEMENTATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/LICENSE', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/README.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TASK-DM-008-IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TASK-FBSDK-020-CODE-REVIEW.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TASK-FBSDK-020-COMPLETION-REPORT.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TASK-FBSDK-020-EXECUTION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TASK_FBSDK_002_IMPLEMENTATION.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TEST_RESULTS_FBSDK_020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/TEST_RESULTS_TASK_BRF_001.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/_scratch/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/autobuild_local_vllm.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/backups/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/conftest.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/conversation_history/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/coverage.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/docker/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/docs/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/examples/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/execute_clarification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/features/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit.sln', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/ia03_ai_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/ia03_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/ia03_final_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/installer/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/lib/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/logitech_gb10.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/main.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/measurements/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/minimax-backup-setup.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/mkdocs.yml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/node_modules/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/package-lock.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/package.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/phase_4_test_results.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/pyproject.toml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/pytest.ini', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/requirements.txt', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/run_adr_tests.sh', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/scratch_notes.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/scripts/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tasks/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/templates/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/test_api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tests/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tsconfig.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/uv.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/vitest.config.ts']
AI: [{'name': 'glob', 'args': {'pattern': '**/coach_validator.py'}, 'id': 'kOy4DxMPhwNocd8V2sFZncMtE2SZo0MQ', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': 'fFPNzECKtVd8tMXRRFJcxAQVwMJ7buNe', 'type': 'tool_call'}]
Tool:      1	"""
     2	Coach validator for lightweight task-work result validation.
     3	
     4	This module provides the CoachValidator class that validates Player's
     5	implementation by reading task-work quality gate results rather than
     6	reimplementing the quality gates inside Coach.
     7	
     8	Architecture:
     9	    Implements Option D (per TASK-REV-0414): 100% code reuse by reading
    10	    task-work quality gate outputs instead of reimplementing validation.
    11	
    12	    Validation Flow:
    13	    1. Read task-work results from .guardkit/autobuild/{task_id}/task_work_results.json
    14	    2. Verify quality gates passed (tests, coverage, arch review, plan audit)
    15	    3. Run independent test verification (trust but verify)
    16	    4. Validate requirements satisfaction
    17	    5. Return approve/feedback decision
    18	
    19	Example:
    20	    >>> from guardkit.orchestrator.quality_gates import CoachValidator
    21	    >>>
    22	    >>> validator = CoachValidator("/path/to/worktree")
    23	    >>> result = validator.validate(
    24	    ...     task_id="TASK-001",
    25	    ...     turn=1,
    26	    ...     task={"acceptance_criteria": ["OAuth2 flow", "Token refresh"]}
    27	    ... )
    28	    >>>
    29	    >>> if result.decision == "approve":
    30	    ...     print("Coach approved implementation")
    31	"""
    32	
    33	import ast
    34	import fnmatch
    35	import json
    36	import logging
    37	import os
    38	import re
    39	import subprocess
    40	import sys
    41	import time
    42	from contextlib import aclosing
    43	from dataclasses import dataclass, field
    44	from pathlib import Path
    45	from types import SimpleNamespace
    46	from typing import Any, Dict, List, Literal, Optional, Tuple
    47	
    48	from guardkit.lib.pytest_argv import isolated_basetemp
    49	from guardkit.orchestrator.coach_verification import (
    50	    CoachVerifier,
    51	    HonestyVerification,
    52	    _resolve_venv_python,
    53	)
    54	from guardkit.orchestrator import evidence_repos as evidence_repos_lib
    55	from guardkit.orchestrator.evidence_repos import EvidenceRepo, EvidenceTestResult
    56	from guardkit.orchestrator.quality_gates.stack_test_execution import (
    57	    StackTestProfile,
    58	    classify_absent_for_stack,
    59	    detect_stack_profile,
    60	)
    61	from guardkit.orchestrator.quality_gates.coach_evidence import (
    62	    CoachEvidenceBundle,
    63	    IndependentTestClassification,
    64	    RuntimeParityResult,
    65	)
    66	from guardkit.orchestrator.docker_fixtures import (
    67	    get_container_name,
    68	    get_env_exports,
    69	    get_start_commands,
    70	    is_known_service,
    71	)
    72	from guardkit.orchestrator.paths import TaskArtifactPaths
    73	from guardkit.orchestrator.phase_specialists import (
    74	    PHASE_DESCRIPTIONS,
    75	    detect_stack_template,
    76	    render_missing_phase_list,
    77	)
    78	from guardkit.orchestrator.schemas import STATUS_ALIASES
    79	from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
    80	
    81	# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
    82	# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
    83	# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
    84	# module top matches the Player path convention in
    85	# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
    86	# target for tests under ``coach_validator.select_harness``.
    87	from guardkit.orchestrator.exceptions import AgentInvocationError
    88	from guardkit.orchestrator.harness import (
    89	    AssistantMessageEvent,
    90	    ResultMessageEvent,
    91	    ToolResultEvent,
    92	    select_harness,
    93	)
    94	from guardkit.orchestrator.harness.selector import DEFAULT_HARNESS
    95	from guardkit.orchestrator.sdk_utils import check_assistant_message_error
    96	
    97	# Coach architecture-context integration (TASK-SC-009) was retired in the
    98	# fleet-memory cutover (FEAT-MEM-09): build_coach_context was never invoked and
    99	# was built on the now-removed graphiti planning stack.
   100	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 3500}, 'id': 'R1TV0C3s3JzgnsuxgzT7cCk7mpQ3SCbX', 'type': 'tool_call'}]
Tool:   3501	        # absent (ran=False) signal, not a pass.
  3502	        # ------------------------------------------------------------------
  3503	        runtime_parity = self._gather_runtime_parity()
  3504	
  3505	        # ------------------------------------------------------------------
  3506	        # 8. L4 behavioural-oracle producer (TASK-QAV-006).
  3507	        # Populates behavioural_oracle at the complete-path return only.
  3508	        # Partial returns (honesty_abort, gate_abort, exception) keep None.
  3509	        # ------------------------------------------------------------------
  3510	        behavioural_oracle_dict: Optional[Dict[str, Any]] = None
  3511	
  3512	        try:
  3513	            behavioural_oracle_dict = self._produce_behavioural_oracle(
  3514	                authored_files=authored if 'authored' in locals() else [],
  3515	            )
  3516	            if behavioural_oracle_dict is not None:
  3517	                logger.info(
  3518	                    "gather_evidence: behavioural-oracle complete "
  3519	                    "(status=%s, passed=%s, oracle=%s).",
  3520	                    behavioural_oracle_dict.get("status"),
  3521	                    behavioural_oracle_dict.get("passed"),
  3522	                    behavioural_oracle_dict.get("oracle_path"),
  3523	                )
  3524	        except Exception as exc:  # noqa: BLE001 — oracle errors must not break gathering
  3525	            logger.warning(
  3526	                "gather_evidence: behavioural-oracle raised %s; "
  3527	                "behavioural_oracle field left as None.",
  3528	                exc.__class__.__name__,
  3529	            )
  3530	
  3531	        # ------------------------------------------------------------------
  3532	        # 7. Independent-test substrate-vs-code classification (TASK-ABFIX-012).
  3533	        # The live gather_evidence path carries NO failure classification on the
  3534	        # bundle today (the legacy validate() path's _classify_test_failure is
  3535	        # not on this path), so a genuine independent CODE failure has no
  3536	        # deterministic blocking guard — the FMDR-004 false-approval. Compute the
  3537	        # verdict HERE (the single place where the classifier + wave-context
  3538	        # is_parallel/wave_size + task_type converge) and carry it on the bundle
  3539	        # for AgentInvoker._apply_independent_test_code_failure_guard.
  3540	        #
  3541	        # Computed ONLY for a RAN-AND-FAILED run (tests_passed False AND
  3542	        # signal_absent False). An ABSENT signal (signal_absent True — e.g. a
  3543	        # host-substrate gap) is owned by the absent guard and must NEVER
  3544	        # manufacture a code verdict (absence-of-failure-is-not-success). A
  3545	        # passing / skipped run leaves it None.
  3546	        independent_test_classification: Optional[IndependentTestClassification] = None
  3547	        if (
  3548	            test_result.tests_passed is False
  3549	            and test_result.signal_absent is False
  3550	        ):
  3551	            fc, conf = self._classify_test_failure(
  3552	                test_result.raw_output,
  3553	                requires_infrastructure=(
  3554	                    task.get("requires_infrastructure") if task else None
  3555	                ),
  3556	                task_type=task_type.value,
  3557	            )
  3558	            # TASK-ABFIX-012: for a TESTING task the parallel-wave
  3559	            # parallel_contention amnesty must not cover the task's OWN failures.
  3560	            # A recognised own-code exception token is already ('code','high').
  3561	            # A NON-token failure (e.g. ValueError / KeyError / a custom
  3562	            # exception) in a parallel wave classifies parallel_contention here;
  3563	            # reclassify it to ('code','high') so the guard blocks it — UNLESS
  3564	            # there is genuine cross-task source-file contention (this task's
  3565	            # authored files overlap a peer's edits in the same wave), the one
  3566	            # case the amnesty must keep (constraint 3). The original ABFIX-005
  3567	            # contention (import / collection races) is caught earlier in the
  3568	            # classifier and never reaches here, so this only reclassifies real
  3569	            # own-code test failures, never a genuine race. Single-task waves
  3570	            # never produce parallel_contention, so this is a no-op there.
  3571	            if task_type == TaskType.TESTING and fc == "parallel_contention":
  3572	                if not self._detect_source_file_contention(task_work_results):
  3573	                    logger.info(
  3574	                        "gather_evidence: TESTING parallel failure with no peer "
  3575	                        "source-file overlap reclassified parallel_contention -> "
  3576	                        "('code','high') for %s (own-code failure, not contention).",
  3577	                        task_id,
  3578	                    )
  3579	                    fc, conf = "code", "high"
  3580	            independent_test_classification = IndependentTestClassification(
  3581	                failure_class=fc,
  3582	                confidence=conf,
  3583	                raw_output_excerpt=(test_result.raw_output or "")[-500:],
  3584	            )
  3585	
  3586	        return CoachEvidenceBundle(
  3587	            honesty=honesty,
  3588	            gathering_status="complete",
  3589	            quality_gates=gates,
  3590	            coverage_details=coverage_details,
  3591	            plan_audit=plan_audit_dict,
  3592	            bdd=bdd_dict,
  3593	            arch_review=arch_review_dict,
  3594	            tests=tests_dict,
  3595	            independent_tests=test_result,
  3596	            independent_test_classification=independent_test_classification,
  3597	            requirements=requirements,
  3598	            severity_recommendations=severity_recommendations,
  3599	            advisory_issues=advisory_issues,
  3600	            task_type=task_type.value,
  3601	            profile_name=profile_name,
  3602	            wiring=wiring_dict,
  3603	            mocked_seam=mocked_seam_dict,
  3604	            spec_gap=spec_gap_dict,
  3605	            stub_scan=stub_scan_dict,
  3606	            coverage=coverage_dict,     # Wave-3 (TASK-QAV-003)
  3607	            behavioural_oracle=behavioural_oracle_dict,  # Wave-4 (TASK-QAV-006)
  3608	            runtime_parity=runtime_parity,
  3609	        )
  3610	
  3611	    def _gather_runtime_parity(self) -> Optional["RuntimeParityResult"]:
  3612	        """Run the deliverable's runtime entry point (TASK-AB-COACHRUNPARITY01, arm b).
  3613	
  3614	        Returns ``None`` when no smoke command was threaded (older callers /
  3615	        feature with no smoke gate). Returns a ``RuntimeParityResult`` with
  3616	        ``ran=False`` (and a ``skipped_reason``) when the check is intentionally
  3617	        skipped (parallel wave) or the runner itself errors — an ABSENT signal
  3618	        that never blocks and never counts as a pass
  3619	        (``absence-of-failure-is-not-success.md``). Returns ``ran=True`` with
  3620	        ``passed`` reflecting a clean (exit 0) standalone run otherwise.
  3621	
  3622	        Guard: runs only on a single-task wave (``wave_size == 1``). On a
  3623	        multi-task wave the deliverable may not run standalone until peers
  3624	        finish, so a per-task smoke run would false-fail; those waves rely on
  3625	        the feature-level post-wave smoke gate instead.
  3626	        """
  3627	        if not self.smoke_command:
  3628	            return None
  3629	
  3630	        command = self.smoke_command
  3631	        if self.wave_size > 1:
  3632	            return RuntimeParityResult(
  3633	                ran=False,
  3634	                passed=False,
  3635	                command=command,
  3636	                skipped_reason="parallel_wave",
  3637	            )
  3638	
  3639	        # PATH-prepend the bootstrap venv so a bare ``python`` / ``pytest`` in
  3640	        # the smoke command resolves to the right interpreter (mirrors
  3641	        # smoke_gates.run_smoke_gate's venv handling).
  3642	        env: Optional[dict] = None
  3643	        if self._venv_python is not None:
  3644	            env = os.environ.copy()
  3645	            env["PATH"] = (
  3646	                str(Path(self._venv_python).parent)
  3647	                + os.pathsep
  3648	                + env.get("PATH", "")
  3649	            )
  3650	
  3651	        try:
  3652	            proc = subprocess.run(
  3653	                command,
  3654	                shell=True,
  3655	                cwd=str(self.worktree_path),
  3656	                capture_output=True,
  3657	                text=True,
  3658	                timeout=self.test_timeout,
  3659	                env=env,
  3660	            )
  3661	        except subprocess.TimeoutExpired as exc:
  3662	            timeout_stderr = (
  3663	                exc.stderr.decode() if isinstance(exc.stderr, bytes)
  3664	                else exc.stderr
  3665	            ) or ""
  3666	            timeout_stdout = (
  3667	                exc.stdout.decode() if isinstance(exc.stdout, bytes)
  3668	                else exc.stdout
  3669	            ) or ""
  3670	            stderr_tail = "\n".join(
  3671	                timeout_stderr.rstrip().splitlines()[-40:]
  3672	            )
  3673	            logger.warning(
  3674	                "Runtime-parity check timed out after %ss: %s",
  3675	                self.test_timeout, command,
  3676	            )
  3677	            # NOTE: ran=True on timeout is operator-pinned
  3678	            # (TASK-AB-COACHRUNPARITY01: a smoke entry point that starts and
  3679	            # hangs is a real deliverable defect). output_tail is additive
  3680	            # evidence only — verdict/timeout semantics unchanged.
  3681	            return RuntimeParityResult(
  3682	                ran=True,
  3683	                passed=False,
  3684	                command=command,
  3685	                exit_code=None,
  3686	                expected_exit=self.smoke_expected_exit,
  3687	                timed_out=True,
  3688	                stderr_tail=stderr_tail,
  3689	                output_tail=_combined_output_tail(timeout_stdout, timeout_stderr),
  3690	            )
  3691	        except Exception as exc:  # noqa: BLE001 — runner errors are ABSENT, not fail
  3692	            logger.warning(
  3693	                "Runtime-parity check runner error for %s: %s", command, exc,
  3694	            )
  3695	            return RuntimeParityResult(
  3696	                ran=False,
  3697	                passed=False,
  3698	                command=command,
  3699	                skipped_reason=f"runner_error: {exc}",
  3700	            )
  3701	
  3702	        stderr_tail = "\n".join(
  3703	            (proc.stderr or "").rstrip().splitlines()[-40:]
  3704	        )
  3705	        passed = proc.returncode == self.smoke_expected_exit
  3706	        if passed:
  3707	            logger.info("Runtime-parity check passed: %s", command)
  3708	        else:
  3709	            logger.warning(
  3710	                "Runtime-parity check FAILED (exit=%d, expected=%d): %s\n"
  3711	                "stderr (tail):\n%s",
  3712	                proc.returncode, self.smoke_expected_exit, command,
  3713	                stderr_tail or "(empty)",
  3714	            )
  3715	        return RuntimeParityResult(
  3716	            ran=True,
  3717	            passed=passed,
  3718	            command=command,
  3719	            exit_code=proc.returncode,
  3720	            expected_exit=self.smoke_expected_exit,
  3721	            timed_out=False,
  3722	            stderr_tail=stderr_tail,
  3723	            # 2026-07-04 code review: pytest FAILED summaries live on stdout;
  3724	            # carry the combined tail so the parity guard can name the failing
  3725	            # tests (stderr_tail semantics untouched — additive only).
  3726	            output_tail=_combined_output_tail(proc.stdout, proc.stderr),
  3727	        )
  3728	
  3729	    # ------------------------------------------------------------------
  3730	    # L4 behavioural-oracle producer (TASK-QAV-006)
  3731	    # ------------------------------------------------------------------
  3732	
  3733	    def _produce_behavioural_oracle(
  3734	        self,
  3735	        authored_files: List[str],
  3736	    ) -> Optional[Dict[str, Any]]:
  3737	        """Produce the L4 behavioural-oracle result for the bundle.
  3738	
  3739	        Discovery by artefact presence: looks for files matching
  3740	        ``tests/acceptance/*_roundtrip.py`` under the worktree root.
  3741	        No opt-in flag — presence of the artefact activates the gate.
  3742	
  3743	        Independence check: the oracle file must NOT be in the turn's
  3744	        authored set (``files_authored`` when present, else
  3745	        ``files_created ∪ files_modified``). A Player-authored oracle
  3746	        yields ``{"status": "not_independent", ...}`` with a
  3747	        ``should_fix`` warning — never trusted, never blocks.
  3748	
  3749	        Execution: runs the oracle via the worktree venv interpreter
  3750	        (``<venv_python> -m pytest <oracle_path>``) with a bounded
  3751	        timeout (default 300s, overridable via ``GUARDKIT_ORACLE_TIMEOUT``
  3752	        env var).
  3753	
  3754	        Outcome policy:
  3755	          * ran-and-failed → ``{"status": "ran", "passed": False, ...}``
  3756	            (the guard fires)
  3757	          * started-then-timed-out → ran-and-failed (COACHRUNPARITY01
  3758	            semantics)
  3759	          * failed-to-start / no oracle discovered → ``None`` (absent,
  3760	            guard no-ops)
  3761	
  3762	        Args:
  3763	            authored_files: List of source files authored by the Player
  3764	                this turn (relative to worktree root).
  3765	
  3766	        Returns:
  3767	            A dict matching the guard's consumed shape, or ``None`` when
  3768	            no oracle file was discovered.
  3769	        """
  3770	        oracle_files = sorted(
  3771	            self.worktree_path.glob("tests/acceptance/*_roundtrip.py")
  3772	        )
  3773	        if not oracle_files:
  3774	            logger.info(
  3775	                "gather_evidence: no behavioural-oracle artefact found "
  3776	                "(no tests/acceptance/*_roundtrip.py); leaving behavioural_oracle absent."
  3777	            )
  3778	            return None
  3779	
  3780	        # Use the first discovered oracle file (convention: one per worktree).
  3781	        oracle_path = oracle_files[0]
  3782	        logger.info(
  3783	            "gather_evidence: discovered behavioural-oracle artefact at %s",
  3784	            oracle_path,
  3785	        )
  3786	
  3787	        # Independence check: the oracle file must NOT be in the authored set.
  3788	        oracle_rel = str(oracle_path.relative_to(self.worktree_path))
  3789	        if oracle_rel in authored_files:
  3790	            logger.warning(
  3791	                "gather_evidence: behavioural-oracle at %s is in the "
  3792	                "Player-authored set — marking not_independent.",
  3793	                oracle_rel,
  3794	            )
  3795	            return {
  3796	                "status": "not_independent",
  3797	                "oracle_path": oracle_rel,
  3798	                "provenance": "player_authored",
  3799	            }
  3800	
  3801	        # Resolve timeout: env override or default 300s.
  3802	        timeout_seconds = float(
  3803	            os.environ.get("GUARDKIT_ORACLE_TIMEOUT", "300")
  3804	        )
  3805	
  3806	        # Build the pytest command, pinned to the worktree venv interpreter.
  3807	        interpreter = self._pytest_interpreter()
  3808	        cmd = [interpreter, "-m", "pytest", str(oracle_path)]
  3809	        env: Optional[dict] = None
  3810	        if self._venv_python is not None:
  3811	            env = os.environ.copy()
  3812	            env["PATH"] = (
  3813	                str(Path(self._venv_python).parent)
  3814	                + os.pathsep
  3815	                + env.get("PATH", "")
  3816	            )
  3817	
  3818	        start_time = time.time()
  3819	        try:
  3820	            proc = subprocess.run(
  3821	                cmd,
  3822	                cwd=str(self.worktree_path),
  3823	                capture_output=True,
  3824	                text=True,
  3825	                timeout=timeout_seconds,
  3826	                env=env,
  3827	            )
  3828	        except subprocess.TimeoutExpired as exc:
  3829	            duration = time.time() - start_time
  3830	            stdout = (
  3831	                exc.stdout.decode() if isinstance(exc.stdout, bytes)
  3832	                else (exc.stdout or "")
  3833	            ) or ""
  3834	            stderr = (
  3835	                exc.stderr.decode() if isinstance(exc.stderr, bytes)
  3836	                else (exc.stderr or "")
  3837	            ) or ""
  3838	            output_tail = _combined_output_tail(stdout, stderr)
  3839	            logger.warning(
  3840	                "gather_evidence: behavioural-oracle timed out after %.1fs "
  3841	                "(oracle: %s). Treating as ran-and-failed.",
  3842	                duration, oracle_rel,
  3843	            )
  3844	            return {
  3845	                "status": "ran",
  3846	                "passed": False,
  3847	                "oracle_path": oracle_rel,
  3848	                "exit_code": None,
  3849	                "duration": duration,
  3850	                "timed_out": True,
  3851	                "output_tail": output_tail,
  3852	                "provenance": "independent",
  3853	            }
  3854	        except Exception as exc:
  3855	            # Failed to start — absent signal.
  3856	            logger.warning(
  3857	                "gather_evidence: behavioural-oracle failed to start "
  3858	                "(oracle: %s): %s. Treating as absent.",
  3859	                oracle_rel, exc,
  3860	            )
  3861	            return None
  3862	
  3863	        duration = time.time() - start_time
  3864	        passed = proc.returncode == 0
  3865	        output_tail = _combined_output_tail(proc.stdout, proc.stderr)
  3866	
  3867	        if passed:
  3868	            logger.info(
  3869	                "gather_evidence: behavioural-oracle passed (oracle: %s, "
  3870	                "duration=%.1fs).",
  3871	                oracle_rel, duration,
  3872	            )
  3873	        else:
  3874	            logger.warning(
  3875	                "gather_evidence: behavioural-oracle FAILED (oracle: %s, "
  3876	                "exit_code=%d, duration=%.1fs).",
  3877	                oracle_rel, proc.returncode, duration,
  3878	            )
  3879	
  3880	        return {
  3881	            "status": "ran",
  3882	            "passed": passed,
  3883	            "oracle_path": oracle_rel,
  3884	            "exit_code": proc.returncode,
  3885	            "duration": duration,
  3886	            "timed_out": False,
  3887	            "output_tail": output_tail,
  3888	            "provenance": "independent",
  3889	        }
  3890	
  3891	    def _compute_agent_invocations_advisory(
  3892	        self, task_work_results: Dict[str, Any],
  3893	    ) -> Optional[Dict[str, Any]]:
  3894	        """Compute the non-blocking agent-invocations advisory issue.
  3895	
  3896	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  3897	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  3898	        Part A). Returns ``None`` when no advisory is needed.
  3899	
  3900	        The logic mirrors the inline computation in ``validate()``: a
  3901	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  3902	        produces a ``severity == "warning"`` advisory naming the missing
  3903	        phases and recommending stack-specific specialists. ``"passed"``,
  3904	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  3905	        on — they ride through without comment.
  3906	        """
  3907	        agent_invocations_validation = task_work_results.get(
  3908	            "agent_invocations_validation"
  3909	        )
  3910	        if not (
  3911	            isinstance(agent_invocations_validation, dict)
  3912	            and agent_invocations_validation.get("status") == "violation"
  3913	        ):
  3914	            return None
  3915	
  3916	        raw_missing = agent_invocations_validation.get("missing_phases") or []
  3917	        missing_phases: List[str] = []
  3918	        if raw_missing and isinstance(raw_missing[0], dict):
  3919	            missing_phases = [
  3920	                str(m.get("phase", ""))
  3921	                for m in raw_missing
  3922	                if m.get("phase")
  3923	            ]
  3924	        else:
  3925	            missing_phases = [str(m) for m in raw_missing]
  3926	        missing_phases_sorted = sorted(missing_phases)
  3927	        missing_phases_with_names = ", ".join(
  3928	            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  3929	            for p in missing_phases_sorted
  3930	        ) if missing_phases_sorted else "unknown"
  3931	
  3932	        stack_template = detect_stack_template(self.worktree_path)
  3933	        specialist_lines = render_missing_phase_list(
  3934	            missing_phases_sorted,
  3935	            stack_template=stack_template,
  3936	            workspace_root=self.worktree_path,
  3937	        )
  3938	        specialist_block = "\n".join(
  3939	            f"- {line}" for line in specialist_lines
  3940	        )
  3941	
  3942	        expected_phases_val = agent_invocations_validation.get("expected_phases")
  3943	        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
  3944	        expected_str = (
  3945	            str(expected_phases_val) if expected_phases_val is not None else "?"
  3946	        )
  3947	        actual_str = (
  3948	            str(actual_invocations_val)
  3949	            if actual_invocations_val is not None
  3950	            else "?"
  3951	        )
  3952	
  3953	        return {
  3954	            "severity": "warning",
  3955	            "category": "agent_invocations_advisory",
  3956	            "description": (
  3957	                f"Advisory (non-blocking): task-work produced a report with "
  3958	                f"{actual_str} of {expected_str} expected agent invocations. "
  3959	                f"Missing phases: {missing_phases_with_names}. "
  3960	                f"Consider invoking these agents via the Task tool to "
  3961	                f"strengthen stack-specific quality:\n{specialist_block}"
  3962	            ),
  3963	            "details": {
  3964	                "missing_phases": missing_phases_sorted,
  3965	                "expected_phases": expected_phases_val,
  3966	                "actual_invocations": actual_invocations_val,
  3967	            },
  3968	        }
  3969	
  3970	    def _compute_specialist_failure_advisories(
  3971	        self, task_work_results: Dict[str, Any],
  3972	    ) -> List[Dict[str, Any]]:
  3973	        """Surface orchestrator-injected specialist failures as advisories.
  3974	
  3975	        TASK-FIX-SPECVIOL01 AC-002. When an orchestrator-invoked specialist
  3976	        (Phase 4 test-orchestrator, Phase 5 code-reviewer) hangs or crashes,
  3977	        ``AgentInvoker._inject_specialist_records_into_task_work_results``
  3978	        writes a ``source: "orchestrator"`` record with ``status`` failed/
  3979	        skipped and an ``error`` into ``agent_invocations``. That is a
  3980	        SUBSTRATE failure — the Player never controlled it — so it must
  3981	        surface as an attributed, non-blocking advisory naming the
  3982	        specialist and the error, never as a Player honesty discrepancy
  3983	        (the path-string-mismatch-is-not-dishonesty meta-class) and never
  3984	        silently dropped (absence of evidence stays absent-signal, per
  3985	        absence-of-failure-is-not-success).
  3986	
  3987	        Only ``status == "failed"`` records advise. ``"skipped"`` records
  3988	        are also synthesized benignly (e.g. direct-mode tasks where
  3989	        ``specialist_results.json`` legitimately never exists) and the
  3990	        phase-absence signal is already carried by the agent-invocations
  3991	        advisory — advising on them would be per-turn noise.
  3992	
  3993	        Returns an empty list when no orchestrator-sourced failure records
  3994	        are present (the overwhelmingly common case).
  3995	        """
  3996	        advisories: List[Dict[str, Any]] = []
  3997	        invocations = task_work_results.get("agent_invocations")
  3998	        if not isinstance(invocations, list):
  3999	            return advisories
  4000	        for inv in invocations:
AI: [{'name': 'grep', 'args': {'pattern': '_produce_behavioural_oracle'}, 'id': 'g24mIng44jesBqcMApl6XJzM18bHjLsN', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.guardkit/autobuild/TASK-QAV-006/player_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.guardkit/autobuild/TASK-QAV-006/task_work_results.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/conversation_history/session_f5b16fc7.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tests/orchestrator/test_behavioural_oracle_producer.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 1000, 'offset': 2500}, 'id': 'wuUXdTpjBoqwIijK0xitdU3efEJNa8vI', 'type': 'tool_call'}]
Tool:   2501	            # ambiguous infrastructure failures (ImportError /
  2502	            # ModuleNotFoundError without service-client context) when the
  2503	            # worktree's bootstrap install is observably broken and all
  2504	            # Player gates passed. Pairs with the bootstrap_failure_mode
  2505	            # smart default from TASK-ABSR-A1B2: when a user opts into
  2506	            # ``warn`` mode and ships on a half-installed venv, this clause
  2507	            # prevents the feedback-stall trapdoor from firing on what is
  2508	            # purely an environment problem.
  2509	            environment_conditional_approval = (
  2510	                failure_class == "infrastructure"
  2511	                and failure_confidence == "ambiguous"
  2512	                and gates_status.all_gates_passed
  2513	                and not requires_infra
  2514	                # TASK-AB-ZEROTESTLOUD01 (AC-004): an ABSENT independent-test
  2515	                # signal must never become an approval input. The amnesty is
  2516	                # for a RAN-AND-FAILED environment-class failure on a
  2517	                # known-broken bootstrap; "the oracle never produced a
  2518	                # verdict" (signal_absent — e.g. zero collected tests via the
  2519	                # verifier-infrastructure defect) is owned by the absent
  2520	                # guard (#6) and stays feedback.
  2521	                and not test_result.signal_absent
  2522	                and self._bootstrap_likely_broken(task)
  2523	            )
  2524	
  2525	            # TASK-FIX-A7B2: Detect source-file contention with peer wave tasks.
  2526	            # The TASK-ABFIX-005 conditional approval for parallel_contention /
  2527	            # parallel-code failures assumes the contention is transient
  2528	            # infrastructure (e.g. partial __init__.py write race) that a retry
  2529	            # in isolation can clear. When two parallel tasks edit the SAME
  2530	            # source file (e.g. shared BDD glue), the contention is real
  2531	            # source-level damage — both tasks committed inconsistent state to
  2532	            # the shared branch BEFORE either snapshot was taken, so the
  2533	            # isolation snapshot captures the already-corrupted file. Granting
  2534	            # conditional approval in that case masks the corruption and the
  2535	            # failure surfaces only at wave-2 verification.
  2536	            #
  2537	            # When overlap is detected, fall through to feedback so the
  2538	            # existing Player-Coach retry machinery serialises the next
  2539	            # attempt — by which point peers have completed and the wave is
  2540	            # effectively single-tasked, eliminating the contention.
  2541	            source_file_contention_overlaps: Dict[str, frozenset] = {}
  2542	            is_parallel_contention_class = (
  2543	                failure_class == "parallel_contention"
  2544	                or (failure_class == "code" and self.is_parallel)
  2545	            )
  2546	            if is_parallel_contention_class and self._peer_changed_files:
  2547	                source_file_contention_overlaps = (
  2548	                    self._detect_source_file_contention(task_work_results)
  2549	                )
  2550	
  2551	            # TASK-AB-ZEROTESTLOUD01 (AC-004), extended 2026-07-04 code review:
  2552	            # an ABSENT independent-test signal must never become an approval
  2553	            # input for ANY conditional-approval clause — not only the
  2554	            # environment amnesty above. Every amnesty below exists for a
  2555	            # RAN-AND-FAILED failure explained away as infrastructure /
  2556	            # collection / contention; "the oracle never produced a verdict"
  2557	            # (signal_absent=True — e.g. TimeoutExpired, or raw_output=None
  2558	            # which _classify_test_failure maps to parallel_contention in
  2559	            # parallel waves) is owned by the absent guard (#6) and stays
  2560	            # feedback (absence-of-failure-is-not-success.md). Hoisted here as
  2561	            # a single precondition so a future clause cannot forget it.
  2562	            conditional_approval = not test_result.signal_absent and (
  2563	                (
  2564	                    failure_class == "infrastructure"
  2565	                    and failure_confidence == "high"
  2566	                    and bool(requires_infra)
  2567	                    and not docker_available
  2568	                    and gates_status.all_gates_passed
  2569	                ) or (
  2570	                    failure_class == "collection_error"
  2571	                    and gates_status.all_gates_passed
  2572	                ) or (
  2573	                    # TASK-ABFIX-005: Grant conditional approval for contention-related
  2574	                    # failures in a parallel wave when all Player quality gates passed.
  2575	                    # "parallel_contention" is set by _classify_test_failure() when
  2576	                    # wave_size > 1 and the failure looks like it could be contention.
  2577	                    # TASK-FIX-A7B2: Only when no source-file overlap with peers.
  2578	                    failure_class == "parallel_contention"
  2579	                    and gates_status.all_gates_passed
  2580	                    and not source_file_contention_overlaps
  2581	                ) or (
  2582	                    # TASK-ABFIX-005: Also grant conditional approval for any "code"
  2583	                    # failure in a parallel wave (recommendation 3b from TASK-REV-A17A).
  2584	                    # The failure might be a false positive caused by concurrent mutations.
  2585	                    # TASK-FIX-A7B2: Only when no source-file overlap with peers.
  2586	                    failure_class == "code"
  2587	                    and self.is_parallel
  2588	                    and gates_status.all_gates_passed
  2589	                    and not source_file_contention_overlaps
  2590	                ) or environment_conditional_approval
  2591	            )
  2592	
  2593	            if conditional_approval:
  2594	                if environment_conditional_approval:
  2595	                    logger.warning(
  2596	                        f"Conditional approval for {task_id}: environment-class "
  2597	                        f"infrastructure failure ({failure_class}/{failure_confidence}) "
  2598	                        f"on a known-broken bootstrap; all Player gates passed. "
  2599	                        f"Marking approved with environment flag."
  2600	                    )
  2601	                elif failure_class == "collection_error":
  2602	                    logger.warning(
  2603	                        f"Conditional approval for {task_id}: test collection errors in "
  2604	                        f"independent verification, all Player gates passed. "
  2605	                        f"Continuing to requirements check."
  2606	                    )
  2607	                elif failure_class == "parallel_contention":
  2608	                    logger.warning(
  2609	                        f"Conditional approval for {task_id}: parallel contention failure "
  2610	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  2611	                        f"Continuing to requirements check."
  2612	                    )
  2613	                elif failure_class == "code" and self.is_parallel:
  2614	                    logger.warning(
  2615	                        f"Conditional approval for {task_id}: code failure in parallel wave "
  2616	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  2617	                        f"Continuing to requirements check."
  2618	                    )
  2619	                else:
  2620	                    logger.warning(
  2621	                        f"Conditional approval for {task_id}: infrastructure failure "
  2622	                        f"with declared deps {requires_infra}, Docker unavailable. "
  2623	                        f"Continuing to requirements check."
  2624	                    )
  2625	                # Fall through to requirements check with conditional flag set
  2626	            else:
  2627	                # Check for psycopg2/asyncpg mismatch before falling back to
  2628	                # generic infrastructure feedback (TASK-FIX-4415).
  2629	                if self._is_psycopg2_asyncpg_mismatch(test_result.raw_output, task):
  2630	                    description = (
  2631	                        "ModuleNotFoundError for 'psycopg2' — this project uses "
  2632	                        "asyncpg. Remove `import psycopg2` from your code and use "
  2633	                        "asyncpg-compatible database patterns instead."
  2634	                    )
  2635	                    rationale = (
  2636	                        "Tests failed because psycopg2 was imported in an asyncpg "
  2637	                        "project"
  2638	                    )
  2639	                elif (
  2640	                    is_parallel_contention_class
  2641	                    and source_file_contention_overlaps
  2642	                ):
  2643	                    # TASK-FIX-A7B2: Source-file contention with at least one
  2644	                    # peer in the same wave. Name the overlapping files so the
  2645	                    # Player can resolve the conflict on retry. The retry will
  2646	                    # be naturally serialised — by the time the Player runs
  2647	                    # its next turn, peers have completed and the wave is
  2648	                    # effectively single-tasked.
  2649	                    error_output = (test_result.test_output_summary or "").strip()
  2650	                    if len(error_output) > 500:
  2651	                        error_output = error_output[:497] + "..."
  2652	                    overlap_lines = []
  2653	                    for peer_id in sorted(source_file_contention_overlaps):
  2654	                        files = sorted(source_file_contention_overlaps[peer_id])
  2655	                        overlap_lines.append(
  2656	                            f"  - {peer_id}: {', '.join(files)}"
  2657	                        )
  2658	                    overlap_block = "\n".join(overlap_lines)
  2659	                    base = (
  2660	                        f"Tests failed due to source-file contention with peer "
  2661	                        f"task(s) in this parallel wave (wave_size={self.wave_size}). "
  2662	                        f"Both this task and the peer(s) below edited the same "
  2663	                        f"source file(s); the resulting shared-branch state is "
  2664	                        f"inconsistent and an isolation-snapshot retry cannot "
  2665	                        f"recover it. Resolve the conflict on the next turn — "
  2666	                        f"by then the peer(s) will have completed and the wave "
  2667	                        f"is effectively serialised.\n"
  2668	                        f"Overlapping files by peer:\n{overlap_block}\n"
  2669	                        f"Test command: {test_result.test_command}."
  2670	                    )
  2671	                    description = (
  2672	                        f"{base} Error detail: {error_output}"
  2673	                        if error_output
  2674	                        else base
  2675	                    )
  2676	                    rationale = (
  2677	                        "Tests failed due to source-file contention with peer "
  2678	                        "wave tasks (real correctness damage, not transient "
  2679	                        "infra contention) — see TASK-FIX-A7B2"
  2680	                    )
  2681	                elif failure_class == "parallel_contention":
  2682	                    error_output = (test_result.test_output_summary or "").strip()
  2683	                    if len(error_output) > 500:
  2684	                        error_output = error_output[:497] + "..."
  2685	                    base = (
  2686	                        f"Tests failed due to likely parallel wave contention "
  2687	                        f"(wave_size={self.wave_size}). Another task may have "
  2688	                        f"concurrently modified shared files (e.g. __init__.py) "
  2689	                        f"during Coach independent verification. "
  2690	                        f"Test command: {test_result.test_command}."
  2691	                    )
  2692	                    description = (
  2693	                        f"{base} Error detail: {error_output}"
  2694	                        if error_output
  2695	                        else base
  2696	                    )
  2697	                    rationale = (
  2698	                        "Tests failed due to likely parallel wave contention, "
  2699	                        "not code defects"
  2700	                    )
  2701	                elif failure_class in ("infrastructure", "collection_error"):
  2702	                    error_output = (test_result.test_output_summary or "").strip()
  2703	                    if len(error_output) > 500:
  2704	                        error_output = error_output[:497] + "..."
  2705	                    base = (
  2706	                        "Tests failed due to infrastructure/environment issues "
  2707	                        f"(not code defects). Test command: {test_result.test_command}. "
  2708	                        "Remediation options: "
  2709	                        "(1) Add mock fixtures for external services, "
  2710	                        "(2) Use SQLite for test database, "
  2711	                        "(3) Mark integration tests with @pytest.mark.integration "
  2712	                        "and exclude via -m 'not integration'."
  2713	                    )
  2714	                    description = (
  2715	                        f"{base} Error detail: {error_output}"
  2716	                        if error_output
  2717	                        else base
  2718	                    )
  2719	                    rationale = (
  2720	                        "Tests failed due to infrastructure/environment issues, "
  2721	                        "not code defects"
  2722	                    )
  2723	                else:
  2724	                    description = "Independent test verification failed"
  2725	                    rationale = (
  2726	                        "Tests passed according to task-work but failed on "
  2727	                        "independent verification"
  2728	                    )
  2729	
  2730	                test_verification_issue: Dict[str, Any] = {
  2731	                    "severity": "must_fix",
  2732	                    "category": "test_verification",
  2733	                    "description": description,
  2734	                    "test_output": test_result.test_output_summary,
  2735	                    "failure_classification": failure_class,
  2736	                    "failure_confidence": failure_confidence,
  2737	                }
  2738	                if source_file_contention_overlaps:
  2739	                    # TASK-AB-STALLTAX01: additive machine-readable contention
  2740	                    # marker. The TASK-FIX-A7B2 overlap branch can record
  2741	                    # failure_class == "code" (a code failure in a parallel
  2742	                    # wave), which would otherwise lose the contention signal
  2743	                    # before the terminal stall label. Serialize the
  2744	                    # peer-overlap map (peer_task_id -> sorted overlapping
  2745	                    # files) onto the issue so the parallel-interference stall
  2746	                    # classifier keys on structured fields only. Verdict
  2747	                    # behaviour is unchanged — overlap still forces feedback.
  2748	                    test_verification_issue["contention_peers"] = {
  2749	                        peer_id: sorted(files)
  2750	                        for peer_id, files in (
  2751	                            source_file_contention_overlaps.items()
  2752	                        )
  2753	                    }
  2754	                return self._feedback_result(
  2755	                    task_id=task_id,
  2756	                    turn=turn,
  2757	                    quality_gates=gates_status,
  2758	                    independent_tests=test_result,
  2759	                    issues=advisory_issues + [test_verification_issue],
  2760	                    rationale=rationale,
  2761	                    context_used=context,
  2762	                    honesty_verification=honesty_verification,
  2763	                )
  2764	
  2765	        # 4. Validate requirements satisfaction (already hoisted above —
  2766	        # see TASK-GK-CR-001).
  2767	        if not requirements.all_criteria_met:
  2768	            logger.info(f"Requirements not met for {task_id}: missing {requirements.missing}")
  2769	            return self._feedback_result(
  2770	                task_id=task_id,
  2771	                turn=turn,
  2772	                quality_gates=gates_status,
  2773	                independent_tests=test_result,
  2774	                requirements=requirements,
  2775	                issues=advisory_issues + [{
  2776	                    "severity": "must_fix",
  2777	                    "category": "missing_requirement",
  2778	                    "description": "Not all acceptance criteria met",
  2779	                    "missing_criteria": requirements.missing,
  2780	                }],
  2781	                rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
  2782	                context_used=context,
  2783	                honesty_verification=honesty_verification,
  2784	            )
  2785	
  2786	        # 5. Check for blocking zero-test anomaly before approval
  2787	        zero_test_issues = self._check_zero_test_anomaly(
  2788	            task_work_results, profile, independent_tests=test_result,
  2789	            task_id=task_id,
  2790	        )
  2791	        has_blocking_zero_test = any(
  2792	            issue.get("severity") == "error" for issue in zero_test_issues
  2793	        )
  2794	
  2795	        if has_blocking_zero_test:
  2796	            logger.info(f"Coach rejected {task_id} turn {turn}: zero-test anomaly (blocking)")
  2797	            return self._feedback_result(
  2798	                task_id=task_id,
  2799	                turn=turn,
  2800	                quality_gates=gates_status,
  2801	                independent_tests=test_result,
  2802	                requirements=requirements,
  2803	                issues=advisory_issues + zero_test_issues,
  2804	                rationale=(
  2805	                    "Zero-test anomaly detected: quality gates reported as passed but "
  2806	                    "no tests were executed. Tests are required for this task type. "
  2807	                    "Please write and run tests before resubmitting."
  2808	                ),
  2809	                context_used=context,
  2810	                honesty_verification=honesty_verification,
  2811	            )
  2812	
  2813	        # 5.5. Check for seam test recommendations (soft gate, non-blocking)
  2814	        seam_test_issues = self._check_seam_test_recommendation(
  2815	            task_work_results, profile
  2816	        )
  2817	
  2818	        # 5.6. Validate consumer_context format constraints (soft gate, non-blocking)
  2819	        consumer_context_issues = self._validate_consumer_context(
  2820	            task, task_work_results
  2821	        )
  2822	
  2823	        # 5.65. Unconfirmed low-confidence assumptions (TASK-FIX-RWOP1.4a).
  2824	        # Warn-mode gate: feature-spec.md:337 says Coach verifies
  2825	        # low-confidence assumptions before accepting a spec. The producer
  2826	        # (AgentInvoker._write_task_work_results) writes the block;
  2827	        # here we surface it as a non-blocking warning so the human
  2828	        # reviewing the merge sees it. Escalation to block-mode is a
  2829	        # separate task driven by evidence that warn-mode is being ignored.
  2830	        assumption_issues = self._check_unconfirmed_assumptions(
  2831	            task_work_results
  2832	        )
  2833	
  2834	        # 5.7. BDD oracle gate (TASK-BDD-E8954): when present in task_work_results,
  2835	        # scenarios_failed > 0 blocks approval. scenarios_pending is informational
  2836	        # and surfaces in feedback without blocking — see bdd_runner module docstring
  2837	        # for the three-state model and rationale for not collapsing pending into
  2838	        # failed.
  2839	        bdd_blocking, bdd_non_blocking = self._check_bdd_results(task_work_results)
  2840	        if bdd_blocking:
  2841	            logger.info(
  2842	                f"Coach rejected {task_id} turn {turn}: bdd_results.scenarios_failed > 0"
  2843	            )
  2844	            return self._feedback_result(
  2845	                task_id=task_id,
  2846	                turn=turn,
  2847	                quality_gates=gates_status,
  2848	                independent_tests=test_result,
  2849	                requirements=requirements,
  2850	                issues=advisory_issues + bdd_blocking + bdd_non_blocking,
  2851	                rationale=(
  2852	                    "BDD scenarios failed: "
  2853	                    f"{task_work_results.get('bdd_results', {}).get('scenarios_failed', 0)} "
  2854	                    "scenario(s) reported assertion failure during pytest-bdd execution."
  2855	                ),
  2856	                context_used=context,
  2857	                honesty_verification=honesty_verification,
  2858	            )
  2859	
  2860	        # 5.8. Seam tests blocking gate (TASK-FIX-A7B4).
  2861	        # Distinct from the soft `_check_seam_test_recommendation` above:
  2862	        # this gate fires only when the task description itself contains a
  2863	        # non-empty `## Seam Tests` section AND the Player wrote zero tests
  2864	        # carrying @pytest.mark.{seam,contract,boundary}. Detected before
  2865	        # approval, after the BDD blocker, so the rest of this turn's gates
  2866	        # have already filtered out lower-quality failure modes.
  2867	        seam_blocking = self._check_seam_tests_implemented(task, task_work_results)
  2868	        if seam_blocking:
  2869	            logger.info(
  2870	                f"Coach rejected {task_id} turn {turn}: "
  2871	                "task description specifies seam tests but Player wrote none"
  2872	            )
  2873	            return self._feedback_result(
  2874	                task_id=task_id,
  2875	                turn=turn,
  2876	                quality_gates=gates_status,
  2877	                independent_tests=test_result,
  2878	                requirements=requirements,
  2879	                issues=advisory_issues + seam_blocking,
  2880	                rationale=(
  2881	                    "Seam tests gate: task description specifies a "
  2882	                    "non-empty `## Seam Tests` section but no "
  2883	                    "@pytest.mark.{seam,contract,boundary} tests were "
  2884	                    "written. Implement the seam test stub before "
  2885	                    "resubmitting."
  2886	                ),
  2887	                context_used=context,
  2888	                honesty_verification=honesty_verification,
  2889	            )
  2890	
  2891	        # Combine all non-blocking issues. The agent_invocations advisory
  2892	        # (F3c) rides along here on the approval path so the Player still
  2893	        # sees the process observation even when outcome gates approve.
  2894	        all_issues = (
  2895	            advisory_issues
  2896	            + zero_test_issues
  2897	            + seam_test_issues
  2898	            + consumer_context_issues
  2899	            + assumption_issues
  2900	            + bdd_non_blocking
  2901	        )
  2902	
  2903	        # 6. All checks passed - approve
  2904	        if conditional_approval:
  2905	            if failure_class == "collection_error":
  2906	                logger.warning(
  2907	                    f"Coach conditionally approved {task_id} turn {turn}: "
  2908	                    f"test collection errors in independent verification, all gates passed"
  2909	                )
  2910	            else:
  2911	                logger.warning(
  2912	                    f"Coach conditionally approved {task_id} turn {turn}: "
  2913	                    f"infrastructure-dependent, independent tests skipped"
  2914	                )
  2915	        else:
  2916	            logger.info(f"Coach approved {task_id} turn {turn}")
  2917	
  2918	        # Build accurate rationale based on actual verification status
  2919	        rationale = self._build_approval_rationale(
  2920	            test_result=test_result,
  2921	            gates_status=gates_status,
  2922	            task_work_results=task_work_results,
  2923	            profile=profile,
  2924	            context=context,
  2925	            conditional_approval=conditional_approval,
  2926	            failure_class=failure_class,
  2927	            environment_conditional_approval=environment_conditional_approval,
  2928	        )
  2929	
  2930	        return CoachValidationResult(
  2931	            task_id=task_id,
  2932	            turn=turn,
  2933	            decision="approve",
  2934	            quality_gates=gates_status,
  2935	            independent_tests=test_result,
  2936	            requirements=requirements,
  2937	            issues=all_issues,
  2938	            rationale=rationale,
  2939	            context_used=context,
  2940	            approved_without_independent_tests=conditional_approval,
  2941	            environment_conditional_approval=environment_conditional_approval,
  2942	            honesty_verification=honesty_verification,
  2943	        )
  2944	
  2945	    def gather_evidence(
  2946	        self,
  2947	        task_id: str,
  2948	        turn: int,
  2949	        task: Dict[str, Any],
  2950	        skip_arch_review: bool = False,
  2951	        context: Optional[str] = None,
  2952	    ) -> CoachEvidenceBundle:
  2953	        """Gather structured evidence for the LLM Coach (TASK-HMIG-008R Part A).
  2954	
  2955	        Runs the same deterministic gathering pipeline the legacy
  2956	        ``validate()`` method uses internally, but packages the results into a
  2957	        :class:`CoachEvidenceBundle` instead of applying decision logic. The
  2958	        LLM Coach reads this bundle (rendered as JSON into the Coach prompt by
  2959	        ``_build_coach_prompt``) plus the honesty result and makes the final
  2960	        approve/feedback decision per the Block adversarial-cooperation paper.
  2961	
  2962	        The pipeline aborts early under three conditions, leaving downstream
  2963	        fields as ``None`` and setting ``bundle.gathering_status`` so the
  2964	        Coach's absence-of-failure guards know to treat the ``None`` fields
  2965	        as ABSENT SIGNAL:
  2966	
  2967	        * Pre-evidence error (invalid task type, missing task_work_results,
  2968	          or an unexpected exception in a gathering helper) →
  2969	          ``"partial_exception"`` with a human-readable cause in
  2970	          ``bundle.gathering_error``.
  2971	        * Honesty verification produced ``must_fix`` discrepancies →
  2972	          ``"partial_honesty_abort"``. Gates and independent tests are not
  2973	          run because the legacy decision tree would have short-circuited
  2974	          here too — the LLM Coach reaches the same conclusion by reading
  2975	          ``bundle.honesty.discrepancies``.
  2976	        * Quality gates failed → ``"partial_gate_abort"``. Independent
  2977	          tests / requirements validation are not run. The LLM Coach
  2978	          reaches a feedback decision by reading ``bundle.quality_gates``.
  2979	
  2980	        Per the Phase 2.5 architectural review and §3 "Exception handling
  2981	        for gather_evidence" in the implementation plan, this method MUST
  2982	        NOT raise to its caller. Wrapping inner helper exceptions in a
  2983	        ``partial_exception`` bundle prevents an exception fallback to
  2984	        ``validate()`` from re-activating the primary decision path that
  2985	        falsifier #1 ("CoachValidator.validate() for the decision is GONE")
  2986	        requires to be gone. ``GUARDKIT_COACH_LEGACY=1`` remains the sole
  2987	        operator-controlled mechanism for re-activating ``validate()``.
  2988	
  2989	        Parameters
  2990	        ----------
  2991	        task_id : str
  2992	            Task identifier (e.g., ``"TASK-001"``). Used to read
  2993	            ``task_work_results.json`` from the standard autobuild path and
  2994	            to wire state-bridge identity resolution into the honesty
  2995	            verifier (TASK-FIX-1B4A Layer 1).
  2996	        turn : int
  2997	            Current turn number (1-based). Passed to
  2998	            ``validate_requirements`` and ``run_independent_tests``.
  2999	        task : Dict[str, Any]
  3000	            Task data dict. Must contain ``acceptance_criteria`` and may
  3001	            contain ``task_type``, ``requires_infrastructure``,
  3002	            ``_docker_available``, ``consumer_context``, ``description``.
  3003	        skip_arch_review : bool, optional
  3004	            If ``True``, the architectural-review gate is skipped regardless
  3005	            of the profile setting. Used for ``--implement-only`` mode where
  3006	            Phase 2.5B did not run. Default: ``False``.
  3007	        context : Optional[str], optional
  3008	            Optional memory / coach context string. Not currently consumed
  3009	            by gather_evidence itself; threaded through for symmetry with
  3010	            ``validate()``'s signature so the legacy shim (when AC-003 is
  3011	            completed in a follow-up) can pass it forward.
  3012	
  3013	        Returns
  3014	        -------
  3015	        CoachEvidenceBundle
  3016	            Populated evidence bundle. Always returned; never raises.
  3017	        """
  3018	        default_honest = HonestyVerification(verified=True)
  3019	
  3020	        # ------------------------------------------------------------------
  3021	        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
  3022	        # ------------------------------------------------------------------
  3023	        try:
  3024	            task_type = self._resolve_task_type(task)
  3025	        except ValueError as exc:
  3026	            logger.error(
  3027	                "gather_evidence: failed to resolve task type: %s", exc
  3028	            )
  3029	            return CoachEvidenceBundle(
  3030	                honesty=default_honest,
  3031	                gathering_status="partial_exception",
  3032	                gathering_error=f"invalid_task_type: {exc}",
  3033	            )
  3034	
  3035	        try:
  3036	            profile = get_profile(task_type)
  3037	        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
  3038	            logger.error(
  3039	                "gather_evidence: failed to load profile for %s: %s",
  3040	                task_type, exc,
  3041	            )
  3042	            return CoachEvidenceBundle(
  3043	                honesty=default_honest,
  3044	                gathering_status="partial_exception",
  3045	                gathering_error=f"missing_profile: {exc}",
  3046	                task_type=task_type.value,
  3047	            )
  3048	
  3049	        profile_name = getattr(profile, "name", None) or task_type.value
  3050	
  3051	        # OPERATOR_HANDOFF: no evidence to gather. The legacy validate() returns
  3052	        # decision="deferred" here; gather_evidence reports a clean status so
  3053	        # the LLM Coach prompt sees an empty bundle with the task_type marker.
  3054	        # The Part B / Part C wiring is responsible for short-circuiting the
  3055	        # Coach invocation for operator-handoff tasks at the autobuild layer
  3056	        # (the same place the legacy validate() returned deferred).
  3057	        if task_type == TaskType.OPERATOR_HANDOFF:
  3058	            logger.info(
  3059	                "gather_evidence: skipping evidence collection for "
  3060	                "operator_handoff task %s (runtime verification deferred to "
  3061	                "operator)", task_id,
  3062	            )
  3063	            return CoachEvidenceBundle(
  3064	                honesty=default_honest,
  3065	                gathering_status="complete",
  3066	                task_type=task_type.value,
  3067	                profile_name=profile_name,
  3068	            )
  3069	
  3070	        # ------------------------------------------------------------------
  3071	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  3072	        # ------------------------------------------------------------------
  3073	        task_work_results = self.read_quality_gate_results(task_id)
  3074	        if "error" in task_work_results:
  3075	            logger.warning(
  3076	                "gather_evidence: task-work results missing for %s: %s",
  3077	                task_id, task_work_results.get("error", "unknown"),
  3078	            )
  3079	            return CoachEvidenceBundle(
  3080	                honesty=default_honest,
  3081	                gathering_status="partial_exception",
  3082	                gathering_error=(
  3083	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  3084	                ),
  3085	                task_type=task_type.value,
  3086	                profile_name=profile_name,
  3087	            )
  3088	
  3089	        # ------------------------------------------------------------------
  3090	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  3091	        # ------------------------------------------------------------------
  3092	        try:
  3093	            honesty = self._verify_honesty(task_work_results)
  3094	        except Exception as exc:  # noqa: BLE001
  3095	            logger.error(
  3096	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  3097	            )
  3098	            return CoachEvidenceBundle(
  3099	                honesty=default_honest,
  3100	                gathering_status="partial_exception",
  3101	                gathering_error=f"honesty_exception: {exc}",
  3102	                task_type=task_type.value,
  3103	                profile_name=profile_name,
  3104	            )
  3105	
  3106	        honesty_issues = self._honesty_issues_from(honesty)
  3107	        honesty_must_fix = [
  3108	            i for i in honesty_issues if i["severity"] == "must_fix"
  3109	        ]
  3110	        honesty_should_fix = [
  3111	            i for i in honesty_issues if i["severity"] == "should_fix"
  3112	        ]
  3113	
  3114	        # Layer-2 demotion hint for the LLM Coach. Mirrors the structural
  3115	        # condition inside _honesty_issues_from (lines 5456-5460): a single
  3116	        # critical file_existence discrepancy that was Layer-1-resolved (via
  3117	        # state_bridge.canonical_path_for) is demoted from must_fix to
  3118	        # should_fix. Surface that hint structurally so the LLM Coach can
  3119	        # apply absence-of-failure guard #4 without re-deriving the demotion.
  3120	        severity_recommendations: List[Dict[str, str]] = []
  3121	        critical_discrepancies = [
  3122	            d for d in honesty.discrepancies if d.severity == "critical"
  3123	        ]
  3124	        non_audit_critical = [
  3125	            d for d in critical_discrepancies
  3126	            if d.claim_type != "claim_audit"
  3127	        ]
  3128	        if (
  3129	            len(non_audit_critical) == 1
  3130	            and non_audit_critical[0].claim_type == "file_existence"
  3131	        ):
  3132	            severity_recommendations.append({
  3133	                "recommendation": (
  3134	                    "A single file_existence discrepancy was suppressed by "
  3135	                    "Layer-1 identity resolution (state_bridge "
  3136	                    "canonical_path_for). Treat as should_fix, not must_fix. "
  3137	                    "Continue AC evaluation."
  3138	                ),
  3139	                "rule": (
  3140	                    "path-string-mismatch-is-not-dishonesty "
  3141	                    "(Layer 2 demotion)"
  3142	                ),
  3143	            })
  3144	
  3145	        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
  3146	        # should_fix issues. Both ride along with the final decision (approve
  3147	        # or feedback) and are surfaced to the Player so process observations
  3148	        # remain visible. Pre-computed here so the LLM Coach can read them
  3149	        # without re-deriving from raw fields.
  3150	        advisory_issues: List[Dict[str, Any]] = []
  3151	        agent_invocations_advisory = (
  3152	            self._compute_agent_invocations_advisory(task_work_results)
  3153	        )
  3154	        if agent_invocations_advisory is not None:
  3155	            advisory_issues.append(agent_invocations_advisory)
  3156	        # TASK-FIX-SPECVIOL01 AC-002: orchestrator-injected specialist
  3157	        # failures (hang/crash) ride along as attributed advisories so the
  3158	        # substrate failure is never silently dropped — and never read as
  3159	        # a Player honesty issue.
  3160	        advisory_issues.extend(
  3161	            self._compute_specialist_failure_advisories(task_work_results)
  3162	        )
  3163	        advisory_issues.extend(honesty_should_fix)
  3164	
  3165	        # Honesty short-circuit: don't run downstream gathering. Legacy
  3166	        # validate() also short-circuits here.
  3167	        if honesty_must_fix:
  3168	            logger.warning(
  3169	                "gather_evidence: honesty produced %d must_fix issue(s) "
  3170	                "for %s; downstream gathering skipped.",
  3171	                len(honesty_must_fix), task_id,
  3172	            )
  3173	            return CoachEvidenceBundle(
  3174	                honesty=honesty,
  3175	                gathering_status="partial_honesty_abort",
  3176	                severity_recommendations=severity_recommendations,
  3177	                advisory_issues=advisory_issues,
  3178	                task_type=task_type.value,
  3179	                profile_name=profile_name,
  3180	            )
  3181	
  3182	        # ------------------------------------------------------------------
  3183	        # 2. Quality gates. Mirrors validate() lines 1130-1132.
  3184	        # ------------------------------------------------------------------
  3185	        try:
  3186	            gates = self.verify_quality_gates(
  3187	                task_work_results,
  3188	                profile=profile,
  3189	                skip_arch_review=skip_arch_review,
  3190	            )
  3191	        except Exception as exc:  # noqa: BLE001
  3192	            logger.error(
  3193	                "gather_evidence: verify_quality_gates raised: %s", exc,
  3194	            )
  3195	            return CoachEvidenceBundle(
  3196	                honesty=honesty,
  3197	                gathering_status="partial_exception",
  3198	                gathering_error=f"quality_gates_exception: {exc}",
  3199	                severity_recommendations=severity_recommendations,
  3200	                advisory_issues=advisory_issues,
  3201	                task_type=task_type.value,
  3202	                profile_name=profile_name,
  3203	            )
  3204	
  3205	        # Build the evidence dict slices the LLM Coach reads.
  3206	        quality_gates_raw = task_work_results.get("quality_gates")
  3207	        if not isinstance(quality_gates_raw, dict):
  3208	            quality_gates_raw = {}
  3209	
  3210	        coverage_details: Dict[str, Any] = {
  3211	            "coverage_met": quality_gates_raw.get("coverage_met"),
  3212	            "line_coverage": quality_gates_raw.get("line_coverage"),
  3213	            "branch_coverage": quality_gates_raw.get("branch_coverage"),
  3214	            "line_threshold": quality_gates_raw.get("line_threshold"),
  3215	            "branch_threshold": quality_gates_raw.get("branch_threshold"),
  3216	            "coverage_required": gates.coverage_required,
  3217	        }
  3218	
  3219	        tests_dict: Dict[str, Any] = {
  3220	            "tests_passed": gates.tests_passed,
  3221	            "tests_required": gates.tests_required,
  3222	            "tests_run": quality_gates_raw.get("tests_run"),
  3223	            "tests_failed": quality_gates_raw.get("tests_failed"),
  3224	            "all_passed": quality_gates_raw.get("all_passed"),
  3225	            "requires_infrastructure": task.get("requires_infrastructure"),
  3226	        }
  3227	
  3228	        plan_audit_raw = task_work_results.get("plan_audit")
  3229	        plan_audit_dict: Optional[Dict[str, Any]] = (
  3230	            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
  3231	        )
  3232	
  3233	        code_review_raw = task_work_results.get("code_review")
  3234	        arch_review_dict: Optional[Dict[str, Any]] = None
  3235	        if isinstance(code_review_raw, dict):
  3236	            arch_review_dict = {
  3237	                "score": code_review_raw.get("score"),
  3238	                "threshold": getattr(profile, "arch_review_threshold", 60),
  3239	                "passed": gates.arch_review_passed,
  3240	                "required": gates.arch_review_required,
  3241	            }
  3242	            # Surface any sub-scores the producer wrote (solid/dry/yagni).
  3243	            for sub in ("solid_score", "dry_score", "yagni_score"):
  3244	                if sub in code_review_raw:
  3245	                    arch_review_dict[sub] = code_review_raw[sub]
  3246	
  3247	        # ------------------------------------------------------------------
  3248	        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
  3249	        # into the Coach evidence path.
  3250	        #
  3251	        # Priority:
  3252	        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
  3253	        #      and stack profile is known, run the BDD plugin and map the
  3254	        #      result into bundle.bdd shape.
  3255	        #   2. Player-reported bdd_results — legacy fallback when the factory
  3256	        #      is unavailable, the stack is unknown, or discovery fails.
  3257	        # ------------------------------------------------------------------
  3258	        _reset_factory_cache()
  3259	        _reset_wiring_factory_cache()
  3260	
  3261	        bdd_raw = task_work_results.get("bdd_results")
  3262	        bdd_dict: Optional[Dict[str, Any]] = None
  3263	
  3264	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  3265	            # Player already produced BDD results — use them as-is.
  3266	            bdd_dict = bdd_raw
  3267	        elif _is_factory_available():
  3268	            # Factory is available but Player didn't produce results.
  3269	            # Attempt independent discovery via the factory plugin.
  3270	            stack_profile = _detect_stack_profile(self.worktree_path)
  3271	            factory_result = _run_factory_bdd(
  3272	                self.worktree_path, stack_profile, task_id
  3273	            )
  3274	            if factory_result is not None:
  3275	                bdd_dict = factory_result
  3276	                logger.info(
  3277	                    "gather_evidence: BDD evidence from factory plugin "
  3278	                    "(stack=%s, scenarios_attempted=%s).",
  3279	                    stack_profile,
  3280	                    factory_result.get("scenarios_attempted"),
  3281	                )
  3282	            else:
  3283	                logger.debug(
  3284	                    "gather_evidence: factory BDD discovery returned None; "
  3285	                    "bdd field left as absent signal.",
  3286	                )
  3287	        else:
  3288	            # Factory unavailable — bdd_dict stays None (absent signal).
  3289	            logger.debug(
  3290	                "gather_evidence: guardkitfactory not available; "
  3291	                "Player-reported bdd_results were empty; "
  3292	                "bdd field left as absent signal.",
  3293	            )
  3294	
  3295	        # Quality-gate-failure short-circuit. Legacy validate() also
  3296	        # short-circuits here via _feedback_from_gates.
  3297	        if not gates.all_gates_passed:
  3298	            logger.info(
  3299	                "gather_evidence: quality gates failed for %s; downstream "
  3300	                "(requirements, independent tests) skipped.", task_id,
  3301	            )
  3302	            return CoachEvidenceBundle(
  3303	                honesty=honesty,
  3304	                gathering_status="partial_gate_abort",
  3305	                quality_gates=gates,
  3306	                coverage_details=coverage_details,
  3307	                plan_audit=plan_audit_dict,
  3308	                bdd=bdd_dict,
  3309	                arch_review=arch_review_dict,
  3310	                tests=tests_dict,
  3311	                severity_recommendations=severity_recommendations,
  3312	                advisory_issues=advisory_issues,
  3313	                task_type=task_type.value,
  3314	                profile_name=profile_name,
  3315	            )
  3316	
  3317	        # ------------------------------------------------------------------
  3318	        # 3. Requirements validation. Mirrors validate() line 1139.
  3319	        # Hoisted ahead of independent-test in the legacy path; preserved
  3320	        # here for the same reason — cheaper, idempotent.
  3321	        # ------------------------------------------------------------------
  3322	        try:
  3323	            requirements = self.validate_requirements(
  3324	                task, task_work_results, turn=turn
  3325	            )
  3326	        except Exception as exc:  # noqa: BLE001
  3327	            logger.error(
  3328	                "gather_evidence: validate_requirements raised: %s", exc,
  3329	            )
  3330	            return CoachEvidenceBundle(
  3331	                honesty=honesty,
  3332	                gathering_status="partial_exception",
  3333	                gathering_error=f"requirements_exception: {exc}",
  3334	                quality_gates=gates,
  3335	                coverage_details=coverage_details,
  3336	                plan_audit=plan_audit_dict,
  3337	                bdd=bdd_dict,
  3338	                arch_review=arch_review_dict,
  3339	                tests=tests_dict,
  3340	                severity_recommendations=severity_recommendations,
  3341	                advisory_issues=advisory_issues,
  3342	                task_type=task_type.value,
  3343	                profile_name=profile_name,
  3344	            )
  3345	
  3346	        # ------------------------------------------------------------------
  3347	        # 4. Independent tests. Mirrors validate() lines 1156-1175.
  3348	        # ------------------------------------------------------------------
  3349	        if not profile.tests_required:
  3350	            test_result: IndependentTestResult = IndependentTestResult(
  3351	                tests_passed=True,
  3352	                test_command="skipped",
  3353	                test_output_summary=(
  3354	                    f"Independent test verification skipped "
  3355	                    f"(tests not required for {task_type.value} tasks)"
  3356	                ),
  3357	                duration_seconds=0.0,
  3358	            )
  3359	            logger.info(
  3360	                "gather_evidence: independent test verification skipped for "
  3361	                "%s (tests not required for %s tasks)",
  3362	                task_id, task_type.value,
  3363	            )
  3364	        else:
  3365	            try:
  3366	                test_result = self.run_independent_tests(
  3367	                    task_work_results=task_work_results,
  3368	                    task=task,
  3369	                    turn=turn,
  3370	                )
  3371	            except Exception as exc:  # noqa: BLE001
  3372	                logger.error(
  3373	                    "gather_evidence: run_independent_tests raised: %s", exc,
  3374	                )
  3375	                return CoachEvidenceBundle(
  3376	                    honesty=honesty,
  3377	                    gathering_status="partial_exception",
  3378	                    gathering_error=f"independent_tests_exception: {exc}",
  3379	                    quality_gates=gates,
  3380	                    coverage_details=coverage_details,
  3381	                    plan_audit=plan_audit_dict,
  3382	                    bdd=bdd_dict,
  3383	                    arch_review=arch_review_dict,
  3384	                    tests=tests_dict,
  3385	                    requirements=requirements,
  3386	                    severity_recommendations=severity_recommendations,
  3387	                    advisory_issues=advisory_issues,
  3388	                    task_type=task_type.value,
  3389	                    profile_name=profile_name,
  3390	                )
  3391	
  3392	        # ------------------------------------------------------------------
  3393	        # 5. Wiring analysis (Wave-1, TASK-QAWE-002).
  3394	        # Populates wiring / mocked_seam / spec_gap at the complete-path
  3395	        # return only. Partial returns (honesty_abort, gate_abort,
  3396	        # exception) leave all three None.
  3397	        # ------------------------------------------------------------------
  3398	        wiring_dict: Optional[Dict[str, Any]] = None
  3399	        mocked_seam_dict: Optional[Dict[str, Any]] = None
  3400	        spec_gap_dict: Optional[Dict[str, Any]] = None
  3401	
  3402	        try:
  3403	            stack_template = detect_stack_template(self.worktree_path)
  3404	            authored = _compute_authored_set(task_work_results)
  3405	            wiring_result = _run_wiring_analysis(
  3406	                worktree_path=self.worktree_path,
  3407	                authored_files=authored,
  3408	                task_type=task_type.value,
  3409	                stack_template=stack_template,
  3410	                bdd_dict=bdd_dict,
  3411	                task_id=task_id,
  3412	            )
  3413	            if wiring_result is not None:
  3414	                wiring_dict = wiring_result.get("wiring")
  3415	                mocked_seam_dict = wiring_result.get("mocked_seam")
  3416	                spec_gap_dict = wiring_result.get("spec_gap")
  3417	                logger.info(
  3418	                    "gather_evidence: wiring analysis complete "
  3419	                    "(wiring_findings=%d, mocked_seam_findings=%d, "
  3420	                    "spec_gap_findings=%d).",
  3421	                    len(wiring_dict.get("findings", [])) if wiring_dict else 0,
  3422	                    len(mocked_seam_dict.get("findings", [])) if mocked_seam_dict else 0,
  3423	                    len(spec_gap_dict.get("findings", [])) if spec_gap_dict else 0,
  3424	                )
  3425	        except Exception as exc:  # noqa: BLE001 — wiring errors must not break gathering
  3426	            logger.warning(
  3427	                "gather_evidence: wiring analysis raised %s; "
  3428	                "all three fields left as None.",
  3429	                exc.__class__.__name__,
  3430	            )
  3431	
  3432	        # ------------------------------------------------------------------
  3433	        # 6. Stub scan (Wave-2, TASK-QAV-002).
  3434	        # Populates stub_scan at the complete-path return only. Partial
  3435	        # returns (honesty_abort, gate_abort, exception) leave it None.
  3436	        # Uses the same authored_files set as wiring analysis.
  3437	        # ------------------------------------------------------------------
  3438	        stub_scan_dict: Optional[Dict[str, Any]] = None
  3439	
  3440	        try:
  3441	            stub_scan_dict = _compute_stub_scan(
  3442	                worktree_path=self.worktree_path,
  3443	                authored_files=authored if 'authored' in locals() else [],
  3444	                task_type=task_type.value,
  3445	            )
  3446	            if stub_scan_dict is not None:
  3447	                logger.info(
  3448	                    "gather_evidence: stub_scan complete "
  3449	                    "(findings=%d).",
  3450	                    len(stub_scan_dict.get("findings", [])),
  3451	                )
  3452	        except Exception as exc:  # noqa: BLE001 — stub scan errors must not break gathering
  3453	            logger.warning(
  3454	                "gather_evidence: stub_scan raised %s; "
  3455	                "stub_scan field left as None.",
  3456	                exc.__class__.__name__,
  3457	            )
  3458	
  3459	        # ------------------------------------------------------------------
  3460	        # 7. Coverage gate (Wave-3, TASK-QAV-003).
  3461	        # Populates coverage at the complete-path return only. Partial
  3462	        # returns (honesty_abort, gate_abort, exception) leave it None.
  3463	        # Uses the same authored_files set as wiring analysis.
  3464	        # Runs pytest under coverage measurement and flags authored public
  3465	        # symbols with zero real execution.
  3466	        # ------------------------------------------------------------------
  3467	        coverage_dict: Optional[Dict[str, Any]] = None
  3468	
  3469	        try:
  3470	            from guardkit.orchestrator.quality_gates.coverage_gate import (
  3471	                run_coverage_gate_for_bundle,
  3472	            )
  3473	
  3474	            coverage_dict = run_coverage_gate_for_bundle(
  3475	                worktree_path=self.worktree_path,
  3476	                authored_files=authored if 'authored' in locals() else [],
  3477	                task_type=task_type.value,
  3478	                timeout=self.test_timeout,
  3479	            )
  3480	            if coverage_dict is not None:
  3481	                logger.info(
  3482	                    "gather_evidence: coverage gate complete "
  3483	                    "(status=%s, findings=%d).",
  3484	                    coverage_dict.get("status"),
  3485	                    len(coverage_dict.get("findings", [])),
  3486	                )
  3487	        except Exception as exc:  # noqa: BLE001 — coverage gate errors must not break gathering
  3488	            logger.warning(
  3489	                "gather_evidence: coverage gate raised %s; "
  3490	                "coverage field left as None.",
  3491	                exc.__class__.__name__,
  3492	            )
  3493	
  3494	        # ------------------------------------------------------------------
  3495	        # 8. Runtime parity (TASK-AB-COACHRUNPARITY01, arm b). Run the
  3496	        # deliverable's declared runtime entry point (the feature smoke
  3497	        # command) before approving, so a "passes pytest but does not run"
  3498	        # deliverable is caught pre-approval. Guarded to single-task waves
  3499	        # (the multi-task-wave caveat: a deliverable may not run standalone
  3500	        # until peers finish). Never breaks gathering; a runner error is an
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 1000, 'offset': 3730}, 'id': 'B36r9U7KyWfNnWveV8L93ejyvxVLQlDZ', 'type': 'tool_call'}]
Tool:   3731	    # ------------------------------------------------------------------
  3732	
  3733	    def _produce_behavioural_oracle(
  3734	        self,
  3735	        authored_files: List[str],
  3736	    ) -> Optional[Dict[str, Any]]:
  3737	        """Produce the L4 behavioural-oracle result for the bundle.
  3738	
  3739	        Discovery by artefact presence: looks for files matching
  3740	        ``tests/acceptance/*_roundtrip.py`` under the worktree root.
  3741	        No opt-in flag — presence of the artefact activates the gate.
  3742	
  3743	        Independence check: the oracle file must NOT be in the turn's
  3744	        authored set (``files_authored`` when present, else
  3745	        ``files_created ∪ files_modified``). A Player-authored oracle
  3746	        yields ``{"status": "not_independent", ...}`` with a
  3747	        ``should_fix`` warning — never trusted, never blocks.
  3748	
  3749	        Execution: runs the oracle via the worktree venv interpreter
  3750	        (``<venv_python> -m pytest <oracle_path>``) with a bounded
  3751	        timeout (default 300s, overridable via ``GUARDKIT_ORACLE_TIMEOUT``
  3752	        env var).
  3753	
  3754	        Outcome policy:
  3755	          * ran-and-failed → ``{"status": "ran", "passed": False, ...}``
  3756	            (the guard fires)
  3757	          * started-then-timed-out → ran-and-failed (COACHRUNPARITY01
  3758	            semantics)
  3759	          * failed-to-start / no oracle discovered → ``None`` (absent,
  3760	            guard no-ops)
  3761	
  3762	        Args:
  3763	            authored_files: List of source files authored by the Player
  3764	                this turn (relative to worktree root).
  3765	
  3766	        Returns:
  3767	            A dict matching the guard's consumed shape, or ``None`` when
  3768	            no oracle file was discovered.
  3769	        """
  3770	        oracle_files = sorted(
  3771	            self.worktree_path.glob("tests/acceptance/*_roundtrip.py")
  3772	        )
  3773	        if not oracle_files:
  3774	            logger.info(
  3775	                "gather_evidence: no behavioural-oracle artefact found "
  3776	                "(no tests/acceptance/*_roundtrip.py); leaving behavioural_oracle absent."
  3777	            )
  3778	            return None
  3779	
  3780	        # Use the first discovered oracle file (convention: one per worktree).
  3781	        oracle_path = oracle_files[0]
  3782	        logger.info(
  3783	            "gather_evidence: discovered behavioural-oracle artefact at %s",
  3784	            oracle_path,
  3785	        )
  3786	
  3787	        # Independence check: the oracle file must NOT be in the authored set.
  3788	        oracle_rel = str(oracle_path.relative_to(self.worktree_path))
  3789	        if oracle_rel in authored_files:
  3790	            logger.warning(
  3791	                "gather_evidence: behavioural-oracle at %s is in the "
  3792	                "Player-authored set — marking not_independent.",
  3793	                oracle_rel,
  3794	            )
  3795	            return {
  3796	                "status": "not_independent",
  3797	                "oracle_path": oracle_rel,
  3798	                "provenance": "player_authored",
  3799	            }
  3800	
  3801	        # Resolve timeout: env override or default 300s.
  3802	        timeout_seconds = float(
  3803	            os.environ.get("GUARDKIT_ORACLE_TIMEOUT", "300")
  3804	        )
  3805	
  3806	        # Build the pytest command, pinned to the worktree venv interpreter.
  3807	        interpreter = self._pytest_interpreter()
  3808	        cmd = [interpreter, "-m", "pytest", str(oracle_path)]
  3809	        env: Optional[dict] = None
  3810	        if self._venv_python is not None:
  3811	            env = os.environ.copy()
  3812	            env["PATH"] = (
  3813	                str(Path(self._venv_python).parent)
  3814	                + os.pathsep
  3815	                + env.get("PATH", "")
  3816	            )
  3817	
  3818	        start_time = time.time()
  3819	        try:
  3820	            proc = subprocess.run(
  3821	                cmd,
  3822	                cwd=str(self.worktree_path),
  3823	                capture_output=True,
  3824	                text=True,
  3825	                timeout=timeout_seconds,
  3826	                env=env,
  3827	            )
  3828	        except subprocess.TimeoutExpired as exc:
  3829	            duration = time.time() - start_time
  3830	            stdout = (
  3831	                exc.stdout.decode() if isinstance(exc.stdout, bytes)
  3832	                else (exc.stdout or "")
  3833	            ) or ""
  3834	            stderr = (
  3835	                exc.stderr.decode() if isinstance(exc.stderr, bytes)
  3836	                else (exc.stderr or "")
  3837	            ) or ""
  3838	            output_tail = _combined_output_tail(stdout, stderr)
  3839	            logger.warning(
  3840	                "gather_evidence: behavioural-oracle timed out after %.1fs "
  3841	                "(oracle: %s). Treating as ran-and-failed.",
  3842	                duration, oracle_rel,
  3843	            )
  3844	            return {
  3845	                "status": "ran",
  3846	                "passed": False,
  3847	                "oracle_path": oracle_rel,
  3848	                "exit_code": None,
  3849	                "duration": duration,
  3850	                "timed_out": True,
  3851	                "output_tail": output_tail,
  3852	                "provenance": "independent",
  3853	            }
  3854	        except Exception as exc:
  3855	            # Failed to start — absent signal.
  3856	            logger.warning(
  3857	                "gather_evidence: behavioural-oracle failed to start "
  3858	                "(oracle: %s): %s. Treating as absent.",
  3859	                oracle_rel, exc,
  3860	            )
  3861	            return None
  3862	
  3863	        duration = time.time() - start_time
  3864	        passed = proc.returncode == 0
  3865	        output_tail = _combined_output_tail(proc.stdout, proc.stderr)
  3866	
  3867	        if passed:
  3868	            logger.info(
  3869	                "gather_evidence: behavioural-oracle passed (oracle: %s, "
  3870	                "duration=%.1fs).",
  3871	                oracle_rel, duration,
  3872	            )
  3873	        else:
  3874	            logger.warning(
  3875	                "gather_evidence: behavioural-oracle FAILED (oracle: %s, "
  3876	                "exit_code=%d, duration=%.1fs).",
  3877	                oracle_rel, proc.returncode, duration,
  3878	            )
  3879	
  3880	        return {
  3881	            "status": "ran",
  3882	            "passed": passed,
  3883	            "oracle_path": oracle_rel,
  3884	            "exit_code": proc.returncode,
  3885	            "duration": duration,
  3886	            "timed_out": False,
  3887	            "output_tail": output_tail,
  3888	            "provenance": "independent",
  3889	        }
  3890	
  3891	    def _compute_agent_invocations_advisory(
  3892	        self, task_work_results: Dict[str, Any],
  3893	    ) -> Optional[Dict[str, Any]]:
  3894	        """Compute the non-blocking agent-invocations advisory issue.
  3895	
  3896	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  3897	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  3898	        Part A). Returns ``None`` when no advisory is needed.
  3899	
  3900	        The logic mirrors the inline computation in ``validate()``: a
  3901	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  3902	        produces a ``severity == "warning"`` advisory naming the missing
  3903	        phases and recommending stack-specific specialists. ``"passed"``,
  3904	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  3905	        on — they ride through without comment.
  3906	        """
  3907	        agent_invocations_validation = task_work_results.get(
  3908	            "agent_invocations_validation"
  3909	        )
  3910	        if not (
  3911	            isinstance(agent_invocations_validation, dict)
  3912	            and agent_invocations_validation.get("status") == "violation"
  3913	        ):
  3914	            return None
  3915	
  3916	        raw_missing = agent_invocations_validation.get("missing_phases") or []
  3917	        missing_phases: List[str] = []
  3918	        if raw_missing and isinstance(raw_missing[0], dict):
  3919	            missing_phases = [
  3920	                str(m.get("phase", ""))
  3921	                for m in raw_missing
  3922	                if m.get("phase")
  3923	            ]
  3924	        else:
  3925	            missing_phases = [str(m) for m in raw_missing]
  3926	        missing_phases_sorted = sorted(missing_phases)
  3927	        missing_phases_with_names = ", ".join(
  3928	            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  3929	            for p in missing_phases_sorted
  3930	        ) if missing_phases_sorted else "unknown"
  3931	
  3932	        stack_template = detect_stack_template(self.worktree_path)
  3933	        specialist_lines = render_missing_phase_list(
  3934	            missing_phases_sorted,
  3935	            stack_template=stack_template,
  3936	            workspace_root=self.worktree_path,
  3937	        )
  3938	        specialist_block = "\n".join(
  3939	            f"- {line}" for line in specialist_lines
  3940	        )
  3941	
  3942	        expected_phases_val = agent_invocations_validation.get("expected_phases")
  3943	        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
  3944	        expected_str = (
  3945	            str(expected_phases_val) if expected_phases_val is not None else "?"
  3946	        )
  3947	        actual_str = (
  3948	            str(actual_invocations_val)
  3949	            if actual_invocations_val is not None
  3950	            else "?"
  3951	        )
  3952	
  3953	        return {
  3954	            "severity": "warning",
  3955	            "category": "agent_invocations_advisory",
  3956	            "description": (
  3957	                f"Advisory (non-blocking): task-work produced a report with "
  3958	                f"{actual_str} of {expected_str} expected agent invocations. "
  3959	                f"Missing phases: {missing_phases_with_names}. "
  3960	                f"Consider invoking these agents via the Task tool to "
  3961	                f"strengthen stack-specific quality:\n{specialist_block}"
  3962	            ),
  3963	            "details": {
  3964	                "missing_phases": missing_phases_sorted,
  3965	                "expected_phases": expected_phases_val,
  3966	                "actual_invocations": actual_invocations_val,
  3967	            },
  3968	        }
  3969	
  3970	    def _compute_specialist_failure_advisories(
  3971	        self, task_work_results: Dict[str, Any],
  3972	    ) -> List[Dict[str, Any]]:
  3973	        """Surface orchestrator-injected specialist failures as advisories.
  3974	
  3975	        TASK-FIX-SPECVIOL01 AC-002. When an orchestrator-invoked specialist
  3976	        (Phase 4 test-orchestrator, Phase 5 code-reviewer) hangs or crashes,
  3977	        ``AgentInvoker._inject_specialist_records_into_task_work_results``
  3978	        writes a ``source: "orchestrator"`` record with ``status`` failed/
  3979	        skipped and an ``error`` into ``agent_invocations``. That is a
  3980	        SUBSTRATE failure — the Player never controlled it — so it must
  3981	        surface as an attributed, non-blocking advisory naming the
  3982	        specialist and the error, never as a Player honesty discrepancy
  3983	        (the path-string-mismatch-is-not-dishonesty meta-class) and never
  3984	        silently dropped (absence of evidence stays absent-signal, per
  3985	        absence-of-failure-is-not-success).
  3986	
  3987	        Only ``status == "failed"`` records advise. ``"skipped"`` records
  3988	        are also synthesized benignly (e.g. direct-mode tasks where
  3989	        ``specialist_results.json`` legitimately never exists) and the
  3990	        phase-absence signal is already carried by the agent-invocations
  3991	        advisory — advising on them would be per-turn noise.
  3992	
  3993	        Returns an empty list when no orchestrator-sourced failure records
  3994	        are present (the overwhelmingly common case).
  3995	        """
  3996	        advisories: List[Dict[str, Any]] = []
  3997	        invocations = task_work_results.get("agent_invocations")
  3998	        if not isinstance(invocations, list):
  3999	            return advisories
  4000	        for inv in invocations:
  4001	            if not isinstance(inv, dict):
  4002	                continue
  4003	            if inv.get("source") != "orchestrator":
  4004	                continue
  4005	            if inv.get("status") != "failed":
  4006	                continue
  4007	            error = inv.get("error")
  4008	            if not error:
  4009	                continue
  4010	            agent = inv.get("agent", "unknown-specialist")
  4011	            phase = inv.get("phase", "?")
  4012	            advisories.append({
  4013	                "severity": "should_fix",
  4014	                "category": "specialist_substrate",
  4015	                "description": (
  4016	                    f"Orchestrator-invoked specialist '{agent}' "
  4017	                    f"(Phase {phase}) did not produce evidence: {error}. "
  4018	                    f"This is a substrate failure attributed to the "
  4019	                    f"orchestrator, not a Player honesty issue — the "
  4020	                    f"phase's evidence is ABSENT, not failed."
  4021	                ),
  4022	                "details": {
  4023	                    "phase": phase,
  4024	                    "agent": agent,
  4025	                    "status": inv.get("status"),
  4026	                    "error": str(error),
  4027	                },
  4028	            })
  4029	        return advisories
  4030	
  4031	    def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
  4032	        """
  4033	        Read quality gate results from task-work execution.
  4034	
  4035	        Looks for results in the standard location:
  4036	        `.guardkit/autobuild/{task_id}/task_work_results.json`
  4037	
  4038	        Parameters
  4039	        ----------
  4040	        task_id : str
  4041	            Task identifier
  4042	
  4043	        Returns
  4044	        -------
  4045	        Dict[str, Any]
  4046	            Task-work results, or dict with "error" key if not found
  4047	        """
  4048	        results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
  4049	        logger.debug(f"Looking for task_work_results at: {results_path}")
  4050	
  4051	        if not results_path.exists():
  4052	            logger.warning(f"task_work_results.json not found at {results_path}")
  4053	            logger.debug(f"Worktree path: {self.worktree_path}")
  4054	            logger.debug(f"Task ID: {task_id}")
  4055	            return {"error": f"Task-work results not found at {results_path}"}
  4056	
  4057	        try:
  4058	            with open(results_path) as f:
  4059	                results = json.load(f)
  4060	            logger.debug(f"Successfully loaded task_work_results from {results_path}")
  4061	            return results
  4062	        except json.JSONDecodeError as e:
  4063	            logger.error(f"Failed to parse task-work results: {e}")
  4064	            return {"error": f"Failed to parse task-work results: {e}"}
  4065	        except Exception as e:
  4066	            logger.error(f"Failed to read task-work results: {e}")
  4067	            return {"error": f"Failed to read task-work results: {e}"}
  4068	
  4069	    def run_evidence_repo_tests(self) -> List[EvidenceTestResult]:
  4070	        """Run independent tests in every declared sibling repo (AC-002).
  4071	
  4072	        Trust-but-verify for sibling-repo deliverables: each declared repo's
  4073	        ``test_command`` runs in that repo's root under the same interpreter
  4074	        Coach pins for worktree tests. Returns one
  4075	        :class:`EvidenceTestResult` per declared repo (empty list when no
  4076	        sibling repos are declared). The orchestrator attaches these to the
  4077	        evidence bundle and blocks the turn on a failed/unrunnable suite via
  4078	        :func:`evidence_repos.evidence_repo_tests_blocking_reason`.
  4079	        """
  4080	        if not self._evidence_repos:
  4081	            return []
  4082	        venv = str(self._venv_python) if self._venv_python is not None else None
  4083	        results = evidence_repos_lib.run_all_repo_tests(
  4084	            self._evidence_repos,
  4085	            venv_python=venv,
  4086	            timeout=self.test_timeout,
  4087	        )
  4088	        for r in results:
  4089	            logger.info(
  4090	                "Evidence-repo tests for %s: ran=%s passed=%s rc=%s",
  4091	                r.repo_name,
  4092	                r.ran,
  4093	                r.passed,
  4094	                r.returncode,
  4095	            )
  4096	        return results
  4097	
  4098	    def verify_quality_gates(
  4099	        self,
  4100	        task_work_results: Dict[str, Any],
  4101	        profile: Optional[QualityGateProfile] = None,
  4102	        skip_arch_review: bool = False,
  4103	    ) -> QualityGateStatus:
  4104	        """
  4105	        Verify task-work quality gates passed.
  4106	
  4107	        Checks the following gates from task-work results, respecting the quality
  4108	        gate profile which determines which gates are required for the task type:
  4109	        - tests_passed: From Phase 4.5 test results
  4110	        - coverage_met: From Phase 4.5 coverage check
  4111	        - arch_review_passed: From Phase 5 code review (score >= threshold)
  4112	        - plan_audit_passed: From Phase 5.5 plan audit (0 violations)
  4113	
  4114	        Parameters
  4115	        ----------
  4116	        task_work_results : Dict[str, Any]
  4117	            Results from task-work execution
  4118	        profile : Optional[QualityGateProfile]
  4119	            Quality gate profile for task type. If None, uses FEATURE profile
  4120	            (backward compatible with existing calls without profile parameter).
  4121	        skip_arch_review : bool
  4122	            If True, skip architectural review gate regardless of profile setting.
  4123	            Used for --implement-only mode where Phase 2.5B doesn't run.
  4124	            Default: False (enforce arch review per profile).
  4125	
  4126	        Returns
  4127	        -------
  4128	        QualityGateStatus
  4129	            Status of all quality gates with requirement flags
  4130	        """
  4131	        # Use default profile for backward compatibility
  4132	        if profile is None:
  4133	            profile = self.DEFAULT_PROFILE
  4134	        # Log input structure and profile for debugging
  4135	        logger.debug(f"task_work_results keys: {list(task_work_results.keys())}")
  4136	        logger.debug(f"quality_gates content: {task_work_results.get('quality_gates', 'NOT_FOUND')}")
  4137	        logger.debug(f"code_review content: {task_work_results.get('code_review', 'NOT_FOUND')}")
  4138	        logger.debug(f"plan_audit content: {task_work_results.get('plan_audit', 'NOT_FOUND')}")
  4139	        logger.debug(
  4140	            f"Profile requirements: tests={profile.tests_required}, "
  4141	            f"coverage={profile.coverage_required}, "
  4142	            f"arch_review={profile.arch_review_required}, "
  4143	            f"plan_audit={profile.plan_audit_required}"
  4144	        )
  4145	
  4146	        # Read from quality_gates object (what writer actually creates)
  4147	        quality_gates = task_work_results.get("quality_gates", {})
  4148	
  4149	        # Test results - use all_passed if present, otherwise check tests_failed
  4150	        # If tests not required by profile, default to True (skip gate)
  4151	        if not profile.tests_required:
  4152	            tests_passed = True
  4153	            logger.debug("Tests not required per task type profile, skipping")
  4154	        elif quality_gates.get("reconciled_absent"):
  4155	            # TASK-ABFIX-010 (W1): the upstream reconciliation flagged an ABSENT
  4156	            # test oracle (Coach isolated pytest timed out / no verdict). This is
  4157	            # UNKNOWN, not a verdict: propagate ``None`` (NOT False, NOT the
  4158	            # ``tests_failed == 0 → True`` fallback below, which would be a
  4159	            # false-GREEN). ``None`` flows through QualityGateStatus → to_dict →
  4160	            # the checkpoint pollution tally, which treats it as absent (not a
  4161	            # counted failure); ``all_gates_passed`` stays falsy so the Coach
  4162	            # does not approve and feeds back instead. Checked BEFORE the
  4163	            # ``all_passed`` / ``tests_failed`` logic so neither can override it.
  4164	            # See ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
  4165	            tests_passed = None
  4166	            logger.debug(
  4167	                "reconciled_absent set → tests_passed=None (UNKNOWN, not counted "
  4168	                "as failure, not approved)"
  4169	            )
  4170	        elif "all_passed" in quality_gates:
  4171	            all_passed_value = quality_gates["all_passed"]
  4172	            if all_passed_value is None:
  4173	                # Player session didn't reach quality gate evaluation (e.g. exhausted SDK turns)
  4174	                # Fall through to tests_failed check for partial data
  4175	                if "tests_failed" in quality_gates:
  4176	                    tests_failed_count = quality_gates["tests_failed"]
  4177	                    tests_passed = tests_failed_count == 0
  4178	                    logger.debug(
  4179	                        f"all_passed is null, falling back to tests_failed={tests_failed_count}, "
  4180	                        f"tests_passed={tests_passed}"
  4181	                    )
  4182	                else:
  4183	                    tests_passed = False
  4184	                    logger.debug("all_passed is null and no tests_failed data, defaulting to False")
  4185	            else:
  4186	                tests_passed = all_passed_value
  4187	                logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.all_passed")
  4188	        elif "tests_failed" in quality_gates:
  4189	            # If we have test counts, check if any failed
  4190	            tests_failed = quality_gates["tests_failed"]
  4191	            tests_passed = tests_failed == 0
  4192	            logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.tests_failed={tests_failed}")
  4193	        else:
  4194	            # No quality_gates data at all - assume failure
  4195	            tests_passed = False
  4196	            logger.debug("No tests_passed or tests_failed found in quality_gates, defaulting to False")
  4197	
  4198	        # Coverage - read from quality_gates.coverage_met
  4199	        # If coverage not required by profile, default to True (skip gate)
  4200	        if not profile.coverage_required:
  4201	            coverage_met = True
  4202	            logger.debug("Coverage not required per task type profile, skipping")
  4203	        else:
  4204	            # Handle None explicitly: treat as "not measured" = pass (same as coverage not required)
  4205	            coverage_met_value = quality_gates.get("coverage_met")
  4206	            coverage_met = coverage_met_value if coverage_met_value is not None else True
  4207	            logger.debug(f"Extracted coverage_met={coverage_met} from quality_gates.coverage_met (raw={coverage_met_value})")
  4208	
  4209	        # Architectural review - may be in separate code_review field or not present
  4210	        # If arch review not required by profile OR skip_arch_review=True, default to True (skip gate)
  4211	        if skip_arch_review:
  4212	            arch_review_passed = True
  4213	            logger.debug("Architectural review skipped (skip_arch_review=True, implement-only mode)")
  4214	        elif not profile.arch_review_required:
  4215	            arch_review_passed = True
  4216	            logger.debug("Architectural review not required per task type profile, skipping")
  4217	        else:
  4218	            code_review = task_work_results.get("code_review", {})
  4219	            arch_score = code_review.get("score", 0)  # Default to 0 if not present
  4220	            arch_review_passed = arch_score >= profile.arch_review_threshold
  4221	            logger.debug(
  4222	                f"Extracted arch_review_passed={arch_review_passed} "
  4223	                f"(score={arch_score}, threshold={profile.arch_review_threshold})"
  4224	            )
  4225	
  4226	        # Plan audit - separate field
  4227	        # If plan audit not required by profile, default to True (skip gate)
  4228	        if not profile.plan_audit_required:
  4229	            plan_audit_passed = True
  4230	            logger.debug("Plan audit not required per task type profile, skipping")
  4231	        else:
  4232	            plan_audit = task_work_results.get("plan_audit", {})
  4233	            # TASK-FIX-RWOP1.3.2: the producer writes a status-typed block
  4234	            # (passed | violation | skipped | auditor_error). "skipped"
  4235	            # means no plan on disk — don't fail the gate on absent data.
  4236	            # "auditor_error" means the deterministic auditor itself crashed;
  4237	            # non-blocking for the same reason validator_error is
  4238	            # non-blocking on the agent_invocations gate — a gate failing
  4239	            # to run is not evidence of a task failing. severity == "high"
  4240	            # is the new authoritative block signal; the legacy violations
  4241	            # count is preserved as a back-compat OR-gate for fixtures and
  4242	            # older Player reports that don't emit severity.
  4243	            plan_audit_status = plan_audit.get("status")
  4244	            severity = plan_audit.get("severity")
  4245	            violations = plan_audit.get("violations", 0)
  4246	
  4247	            if plan_audit_status in ("skipped", "auditor_error"):
  4248	                plan_audit_passed = True
  4249	                logger.debug(
  4250	                    f"Plan audit status={plan_audit_status} — treated as pass "
  4251	                    f"(non-blocking informational status)"
  4252	                )
  4253	            elif severity == "high":
  4254	                plan_audit_passed = False
  4255	                logger.debug(
  4256	                    f"Plan audit rejected: severity=high "
  4257	                    f"(violations={violations}, status={plan_audit_status})"
  4258	                )
  4259	            else:
  4260	                plan_audit_passed = violations == 0
  4261	                logger.debug(
  4262	                    f"Extracted plan_audit_passed={plan_audit_passed} "
  4263	                    f"(violations={violations}, severity={severity}, "
  4264	                    f"status={plan_audit_status})"
  4265	                )
  4266	
  4267	        # Determine effective arch_review_required (False if skip_arch_review=True)
  4268	        effective_arch_review_required = profile.arch_review_required and not skip_arch_review
  4269	
  4270	        status = QualityGateStatus(
  4271	            tests_passed=tests_passed,
  4272	            coverage_met=coverage_met,
  4273	            arch_review_passed=arch_review_passed,
  4274	            plan_audit_passed=plan_audit_passed,
  4275	            tests_required=profile.tests_required,
  4276	            coverage_required=profile.coverage_required,
  4277	            arch_review_required=effective_arch_review_required,
  4278	            plan_audit_required=profile.plan_audit_required,
  4279	        )
  4280	
  4281	        # Log final decision at INFO level for visibility
  4282	        logger.info(
  4283	            f"Quality gate evaluation complete: "
  4284	            f"tests={status.tests_passed} (required={status.tests_required}), "
  4285	            f"coverage={status.coverage_met} (required={status.coverage_required}), "
  4286	            f"arch={status.arch_review_passed} (required={status.arch_review_required}), "
  4287	            f"audit={status.plan_audit_passed} (required={status.plan_audit_required}), "
  4288	            f"ALL_PASSED={status.all_gates_passed}"
  4289	        )
  4290	
  4291	        return status
  4292	
  4293	    @staticmethod
  4294	    def _extract_content_text(content) -> str:
  4295	        """Extract text from ToolResultBlock.content (str | list[dict] | None)."""
  4296	        if content is None:
  4297	            return ""
  4298	        if isinstance(content, str):
  4299	            return content
  4300	        if isinstance(content, list):
  4301	            parts = []
  4302	            for item in content:
  4303	                if isinstance(item, dict):
  4304	                    parts.append(item.get("text", str(item)))
  4305	                else:
  4306	                    parts.append(str(item))
  4307	            return "\n".join(parts)
  4308	        return str(content)
  4309	
  4310	    # TASK-FIX-COACHTRES01 (heuristic precision): the pytest result summary
  4311	    # line, e.g. ``==== 15 passed in 2.75s ====`` /
  4312	    # ``==== 1 failed, 14 passed in 0.3s ====`` / ``==== 2 errors in 1.0s ====``.
  4313	    # Wrapped in ``=`` runs and ending in ``in <float>s``; the body carries the
  4314	    # real per-outcome counts.
  4315	    _PYTEST_SUMMARY_RE = re.compile(
  4316	        r"^=+\s+(?P<body>.*?\b(?:passed|failed|error|errors|skipped|xfailed|"
  4317	        r"xpassed|no tests ran)\b.*?)\s+in\s+[\d.]+\s*s\b.*?=*\s*$",
  4318	        re.IGNORECASE | re.MULTILINE,
  4319	    )
  4320	
  4321	    @classmethod
  4322	    def _verdict_from_pytest_summary(cls, output_text: str) -> Optional[bool]:
  4323	        """Derive pass/fail from the pytest summary line, not substring scan.
  4324	
  4325	        TASK-FIX-COACHTRES01. The capture fix surfaces the *real* pytest output
  4326	        to the SDK-path determination — but the legacy heuristic scanned the
  4327	        WHOLE output for the substrings ``"error"`` / ``"failed"`` /
  4328	        ``"failure"``, which false-positives on a *passing* run whose verbose
  4329	        test names or ``--cov`` file paths contain those words (e.g. a passing
  4330	        ``test_..._displays_error`` or a covered ``*_error_messages.py``). That
  4331	        is the FEAT-HARV TASK-HARV-006 false-block: ``15 passed in 2.75s`` read
  4332	        as a failure because two unrelated ``"error"`` substrings appeared.
  4333	
  4334	        The pytest *summary line* carries only the real counts, so parse that.
  4335	
  4336	        Returns
  4337	        -------
  4338	        Optional[bool]
  4339	            ``True``  — a passing summary (>=1 passed, zero failed/errored).
  4340	            ``False`` — a failing summary (>=1 failed or errored).
  4341	            ``None``  — no pytest summary line found (e.g. narration-only or a
  4342	                        truncated capture), so the caller falls back to the
  4343	                        legacy substring heuristic / absent handling.
  4344	        """
  4345	        if not output_text:
  4346	            return None
  4347	        matches = list(cls._PYTEST_SUMMARY_RE.finditer(output_text))
  4348	        if not matches:
  4349	            return None
  4350	        body = matches[-1].group("body").lower()
  4351	        # Any non-zero failed/errored count is a fail, regardless of passes.
  4352	        if re.search(r"\b[1-9]\d*\s+(?:failed|error|errors)\b", body):
  4353	            return False
  4354	        if re.search(r"\b[1-9]\d*\s+passed\b", body):
  4355	            return True
  4356	        # Only skipped / xfailed / "no tests ran" — not a clear pass; defer.
  4357	        return None
  4358	
  4359	    async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
  4360	        """Run tests via the harness substrate seam (TASK-HMIG-006.3).
  4361	
  4362	        Dispatches through :func:`select_harness` so ``GUARDKIT_HARNESS``
  4363	        routes Coach's independent verification through the SDK or
  4364	        LangGraph substrate consistently with the Player path migrated
  4365	        in TASK-HMIG-006/006.2. Coach-specific orchestrator concerns
  4366	        (``allowed_tools=["Bash"]``, ``max_turns=1``,
  4367	        ``permission_mode="bypassPermissions"``, ``self.test_timeout``)
  4368	        remain orchestrator-side per AC-002.
  4369	
  4370	        The method name retains the historical ``_via_sdk`` suffix so
  4371	        callers (``run_independent_tests`` at line ~2867) need no
  4372	        change; the dispatch is now harness-agnostic.
  4373	
  4374	        Parameters
  4375	        ----------
  4376	        test_cmd : str
  4377	            Shell command to run tests
  4378	
  4379	        Returns
  4380	        -------
  4381	        IndependentTestResult
  4382	            Result of test execution via the substrate seam.
  4383	        """
  4384	        import asyncio
  4385	        import time
  4386	        from contextlib import contextmanager
  4387	
  4388	        # ``select_harness``, harness event types, ``AgentInvocationError``,
  4389	        # and ``check_assistant_message_error`` are imported at module top
  4390	        # (TASK-HMIG-006.3) so ``coach_validator.select_harness`` is a
  4391	        # stable patch target. ``asyncio`` / ``time`` / ``contextmanager``
  4392	        # remain method-local to preserve the historic lazy-import shape
  4393	        # for the rest of the method body.
  4394	
  4395	        @contextmanager
  4396	        def _patched_pythonpath(prepend: str):
  4397	            """Scope PYTHONPATH mutation to harness.invoke() (Step D).
  4398	
  4399	            ``ClaudeSDKHarness`` does not accept an ``env=`` kwarg
  4400	            (sdk_harness.py:130-158); adding one would widen the
  4401	            harness interface for a Coach-only concern (ISP). Mutating
  4402	            ``os.environ`` in a tight scope lets the SDK subprocess
  4403	            inherit PYTHONPATH naturally. The single-coach-turn-per-
  4404	            worktree invariant makes this process-global side effect
  4405	            acceptable; do not lift this helper to a module-level
  4406	            utility without reconsidering thread-safety.
  4407	            """
  4408	            original = os.environ.get("PYTHONPATH")
  4409	            current = os.environ.get("PYTHONPATH", "")
  4410	            new = f"{prepend}:{current}" if current else prepend
  4411	            os.environ["PYTHONPATH"] = new
  4412	            try:
  4413	                yield
  4414	            finally:
  4415	                if original is None:
  4416	                    os.environ.pop("PYTHONPATH", None)
  4417	                else:
  4418	                    os.environ["PYTHONPATH"] = original
  4419	
  4420	        @contextmanager
  4421	        def _patched_path(venv_bin: Optional[str]):
  4422	            """Scope a venv-bin PATH prepend to harness.invoke (TASK-FIX-COACHPYENV).
  4423	
  4424	            Defence-in-depth companion to the ``-m pytest`` interpreter pin: the
  4425	            SDK harness spawns a Bash subprocess that inherits ``os.environ``, so
  4426	            prepending the bootstrap venv ``bin`` here means even a bare
  4427	            ``pytest``/``python`` the tests shell out to resolves inside the
  4428	            bootstrap environment, not the host Python 3.14 framework. No-op when
  4429	            no venv is resolved. Same single-coach-turn-per-worktree invariant as
  4430	            ``_patched_pythonpath`` makes this process-global mutation acceptable.
  4431	            """
  4432	            if not venv_bin:
  4433	                yield
  4434	                return
  4435	            original = os.environ.get("PATH")
  4436	            current = os.environ.get("PATH", "")
  4437	            os.environ["PATH"] = (
  4438	                f"{venv_bin}{os.pathsep}{current}" if current else venv_bin
  4439	            )
  4440	            try:
  4441	                yield
  4442	            finally:
  4443	                if original is None:
  4444	                    os.environ.pop("PATH", None)
  4445	                else:
  4446	                    os.environ["PATH"] = original
  4447	
  4448	        start_time = time.time()
  4449	        # TASK-FIX-COACHPYENV: pin the interpreter in the command the Bash tool
  4450	        # runs so it cannot resolve a stray PATH ``pytest`` (the run-9 Python
  4451	        # 3.14 framework-pytest mismatch). No-op when no venv is resolved.
  4452	        sdk_test_cmd = self._pin_pytest_command(test_cmd)
  4453	        if sdk_test_cmd != test_cmd:
  4454	            logger.info(
  4455	                "Coach SDK test command pinned to bootstrap interpreter: %s",
  4456	                sdk_test_cmd,
  4457	            )
  4458	        # 2026-07-04 code review: record the pinned interpreter as forensic
  4459	        # evidence on the SDK-path results too (the subprocess/isolated runners
  4460	        # already do — TASK-AB-RESUMEVENV01 AC-003). Only when the pin actually
  4461	        # fired: an unpinned SDK run resolves ``pytest`` via the Bash tool's
  4462	        # PATH, so the probe interpreter would not match the run — honest
  4463	        # ``None`` there.
  4464	        sdk_resolved_interpreter = (
  4465	            self._resolved_interpreter_for(test_cmd)
  4466	            if sdk_test_cmd != test_cmd
  4467	            else None
  4468	        )
  4469	        prompt = (
  4470	            f"Run the following test command and report the output:\n\n"
  4471	            f"```bash\n{sdk_test_cmd}\n```\n\nProvide the full test output."
  4472	        )
  4473	
  4474	        # TASK-HMIG-006.5: Restore sdk_debug preservation for the Coach
  4475	        # test path. Pre-migration (TASK-DIAG-F4A2), the SDK call site
  4476	        # invoked ``_sdk_preserve_prompt`` / ``_sdk_preserve_event``
  4477	        # under ``GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`` so incident
  4478	        # analysis of coach test-run failures had a quoted artefact
  4479	        # trail under ``sdk_debug/turn_<n>/coach/test_run/``. The
  4480	        # HMIG-006.3 migration dropped those calls because the harness
  4481	        # substrate seam owns the message stream and no harness-level
  4482	        # hook existed. The preservation is re-introduced here against
  4483	        # the synthesised options-shaped snapshot below so the
  4484	        # diagnostic surface mirrors the pre-migration shape; the
  4485	        # harness dispatch boundary itself (AC-001/AC-002 of HMIG-006.3)
  4486	        # is untouched. Zero overhead when the env var is unset
  4487	        # (``preserve_prompt`` short-circuits and ``preserve_event``
  4488	        # becomes a no-op against ``debug_dir=None``).
  4489	        from guardkit.orchestrator.sdk_debug import (
  4490	            preserve_prompt as _sdk_preserve_prompt,
  4491	            preserve_event as _sdk_preserve_event,
  4492	        )
  4493	
  4494	        try:
  4495	            # Use GUARDKIT_COACH_TEST_MODEL env var if set, otherwise CLI default
  4496	            model = self._get_coach_test_model()
  4497	            worktree_str = str(self.worktree_path)
  4498	            logger.debug(f"Coach harness PYTHONPATH prepend: {worktree_str}")
  4499	
  4500	            # Synthesise the diagnostic options snapshot the
  4501	            # pre-migration ``ClaudeAgentOptions`` would have produced.
  4502	            # The post-migration harness owns its own option assembly;
  4503	            # this record captures Coach's intent (what the substrate
  4504	            # was asked to run with) rather than the substrate's
  4505	            # realisation. ``GUARDKIT_HARNESS`` is included so the
  4506	            # post-mortem can distinguish SDK vs. LangGraph runs.
  4507	            _sdk_options_snapshot = {
  4508	                "cwd": str(self.worktree_path),
  4509	                "allowed_tools": ["Bash"],
  4510	                "permission_mode": "bypassPermissions",
  4511	                "max_turns": 1,
  4512	                "model": model,
  4513	                "harness": os.environ.get("GUARDKIT_HARNESS", DEFAULT_HARNESS),
  4514	                "pythonpath_prepend": worktree_str,
  4515	                "sdk_timeout_seconds": self.test_timeout,
  4516	            }
  4517	            _sdk_debug_dir = _sdk_preserve_prompt(
  4518	                workspace_root=self.worktree_path,
  4519	                task_id=self.task_id or "unknown",
  4520	                turn=self._turn,
  4521	                role="coach_test",
  4522	                prompt=prompt,
  4523	                options=_sdk_options_snapshot,
  4524	            )
  4525	
  4526	            collected_text: List[str] = []
  4527	            bash_output: Optional[str] = None
  4528	            bash_is_error: Optional[bool] = None
  4529	            api_error: Optional[str] = None
  4530	
  4531	            venv_bin = (
  4532	                str(self._venv_python.parent)
  4533	                if self._venv_python is not None
  4534	                else None
  4535	            )
  4536	            with _patched_pythonpath(worktree_str), _patched_path(venv_bin):
  4537	                harness = select_harness(
  4538	                    sdk_timeout_seconds=self.test_timeout,
  4539	                    allowed_tools=["Bash"],
  4540	                    permission_mode="bypassPermissions",
  4541	                    max_turns=1,
  4542	                    model=model,
  4543	                    cwd=self.worktree_path,
  4544	                )
  4545	
  4546	                async with asyncio.timeout(self.test_timeout):
  4547	                    # TASK-FIX-LGACLOSE: finalise the harness async generator on
  4548	                    # every exit (incl. timeout/cancel) via aclosing() so no
  4549	                    # orphaned async_generator_athrow survives interpreter shutdown.
  4550	                    async with aclosing(
  4551	                        harness.invoke(
  4552	                            prompt=prompt,
  4553	                            role="coach_test",
  4554	                            tools=["Bash"],
  4555	                            cwd=self.worktree_path,
  4556	                            timeout_seconds=self.test_timeout,
  4557	                        )
  4558	                    ) as _harness_stream:
  4559	                        async for event in _harness_stream:
  4560	                            # TASK-HMIG-006.5: record every harness event
  4561	                            # the loop consumes. ``preserve_event`` is a
  4562	                            # no-op when ``_sdk_debug_dir`` is None
  4563	                            # (env var unset), so this is zero-cost in
  4564	                            # production.
  4565	                            _sdk_preserve_event(_sdk_debug_dir, event)
  4566	                            if isinstance(event, AssistantMessageEvent):
  4567	                                # API-error short-circuit mirrors the Player
  4568	                                # dispatch in agent_invoker._invoke_with_role.
  4569	                                # Only the SDK harness sets ``event.raw``;
  4570	                                # other substrates have raw=None and this
  4571	                                # check is a no-op there.
  4572	                                if event.raw is not None:
  4573	                                    err = check_assistant_message_error(event.raw)
  4574	                                    if err:
  4575	                                        api_error = err
  4576	                                        break
  4577	                                collected_text.append(event.text)
  4578	                            elif isinstance(event, ToolResultEvent):
  4579	                                # NOTE (TASK-HMIG-006.3, Architectural review
  4580	                                # Concern 4): the current SDK harness does NOT
  4581	                                # yield ToolResultEvent — sdk_harness.py only
  4582	                                # handles AssistantMessage / ResultMessage /
  4583	                                # ToolUseEvent. On the SDK path bash_is_error
  4584	                                # therefore stays None and the heuristic
  4585	                                # branch below is the effective pass/fail
  4586	                                # determination. This branch is live for any
  4587	                                # future harness that yields ToolResultEvent
  4588	                                # (e.g. a variant that walks UserMessage
  4589	                                # content) and preserves the pre-migration
  4590	                                # tri-state contract:
  4591	                                #   is_error=True  -> bash_is_error=True (tool errored)
  4592	                                #   is_error=False -> bash_is_error=None (heuristic)
  4593	                                # The False->None mapping is intentional:
  4594	                                # is_error=False means "tool ran cleanly" not
  4595	                                # "tests passed", so we let the heuristic
  4596	                                # branch decide from the output text.
  4597	                                content = event.content
  4598	                                if isinstance(content, str):
  4599	                                    bash_output = content
  4600	                                else:
  4601	                                    bash_output = self._extract_content_text(content)
  4602	                                bash_is_error = True if event.is_error else None
  4603	                            elif isinstance(event, ResultMessageEvent):
  4604	                                break
  4605	
  4606	            duration = time.time() - start_time
  4607	
  4608	            if api_error is not None:
  4609	                logger.error(f"SDK API error during coach test execution: {api_error}")
  4610	                return IndependentTestResult(
  4611	                    tests_passed=False,
  4612	                    test_command=test_cmd,
  4613	                    test_output_summary=f"SDK API error: {api_error}",
  4614	                    duration_seconds=duration,
  4615	                    raw_output=f"SDK API error: {api_error}",
  4616	                    # TASK-FIX-COACHTESTTO: transport-layer failure — the
  4617	                    # oracle never produced a verdict. ABSENT, not a fail.
  4618	                    signal_absent=True,
  4619	                )
  4620	
  4621	            # Determine pass/fail from bash_is_error and output. Branches
  4622	            # below are unchanged from pre-migration: output assembly is
  4623	            # substrate-agnostic; only the source of bash_is_error /
  4624	            # bash_output / collected_text changed.
  4625	            if bash_is_error is True:
  4626	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4627	                summary = self._summarize_test_output(output_text)
  4628	                logger.debug(
  4629	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4630	                )
  4631	                # TASK-ABFIX-012: a missing host tool ("command not found") makes
  4632	                # this an ABSENT signal (the oracle could not run), not a Player
  4633	                # test failure. No subprocess return code is available on the SDK
  4634	                # path, so match the explicit shell strings.
  4635	                substrate_absent = self._is_host_substrate_gap(None, output_text)
  4636	                if substrate_absent:
  4637	                    logger.warning(
  4638	                        "[TASK-ABFIX-012] SDK independent test oracle hit a "
  4639	                        "host-substrate gap (missing host tool) — absent signal, "
  4640	                        "not a test failure. cmd=%s",
  4641	                        test_cmd,
  4642	                    )
  4643	                return IndependentTestResult(
  4644	                    tests_passed=False,
  4645	                    test_command=test_cmd,
  4646	                    test_output_summary=summary,
  4647	                    duration_seconds=duration,
  4648	                    raw_output=output_text,
  4649	                    signal_absent=substrate_absent,
  4650	                    tests_skipped=_parse_tests_skipped(output_text),
  4651	                    resolved_interpreter=sdk_resolved_interpreter,
  4652	                )
  4653	            elif bash_is_error is False:
  4654	                # NOTE (TASK-HMIG-006.3 code-review nit): this branch is
  4655	                # unreachable in the current implementation because the
  4656	                # ToolResultEvent handler above maps ``is_error=False``
  4657	                # to ``bash_is_error=None`` (heuristic path). Retained
  4658	                # unchanged from pre-migration per the implementation
  4659	                # plan; it activates only if a future harness yields
  4660	                # tri-state ``is_error`` semantics (e.g. by emitting
  4661	                # ``bash_is_error = False`` directly here from a custom
  4662	                # branch). Removing it would silently break that future
  4663	                # extension, so the branch stays live but documented.
  4664	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4665	                summary = self._summarize_test_output(output_text)
  4666	                logger.debug(
  4667	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4668	                )
  4669	                return IndependentTestResult(
  4670	                    tests_passed=True,
  4671	                    test_command=test_cmd,
  4672	                    test_output_summary=summary,
  4673	                    duration_seconds=duration,
  4674	                    raw_output=output_text,
  4675	                    tests_skipped=_parse_tests_skipped(output_text),
  4676	                    resolved_interpreter=sdk_resolved_interpreter,
  4677	                )
  4678	            else:
  4679	                # GAP-FIX #7: is_error is None — parse output text
  4680	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4681	                summary = self._summarize_test_output(output_text)
  4682	                logger.debug(
  4683	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4684	                )
  4685	                # TASK-ABFIX-012: a host-substrate gap ("command not found") is an
  4686	                # ABSENT signal — short-circuit before the pass/fail heuristic so a
  4687	                # missing host tool is never read as a Player test failure or pass.
  4688	                if self._is_host_substrate_gap(None, output_text):
  4689	                    logger.warning(
  4690	                        "[TASK-ABFIX-012] SDK independent test oracle (heuristic "
  4691	                        "branch) hit a host-substrate gap — absent signal, not a "
  4692	                        "test failure. cmd=%s",
  4693	                        test_cmd,
  4694	                    )
  4695	                    return IndependentTestResult(
  4696	                        tests_passed=False,
  4697	                        test_command=test_cmd,
  4698	                        test_output_summary=summary,
  4699	                        duration_seconds=duration,
  4700	                        raw_output=output_text,
  4701	                        signal_absent=True,
  4702	                    )
  4703	                # TASK-FIX-COACHTRES01: prefer the pytest summary line (real
  4704	                # counts) over the substring scan, which false-positives on a
  4705	                # passing run whose verbose test names / --cov file paths
  4706	                # contain "error"/"failed" (the FEAT-HARV TASK-HARV-006
  4707	                # false-block: "15 passed" mis-read as a failure because a
  4708	                # passing test_..._displays_error and a covered
  4709	                # *_error_messages.py path matched). Only fall back to the
  4710	                # legacy substring heuristic when no summary line is present.
  4711	                summary_verdict = self._verdict_from_pytest_summary(output_text)
  4712	                if summary_verdict is not None:
  4713	                    return IndependentTestResult(
  4714	                        tests_passed=summary_verdict,
  4715	                        test_command=test_cmd,
  4716	                        test_output_summary=summary,
  4717	                        duration_seconds=duration,
  4718	                        raw_output=output_text,
  4719	                        tests_skipped=_parse_tests_skipped(output_text),
  4720	                        resolved_interpreter=sdk_resolved_interpreter,
  4721	                    )
  4722	                # Heuristic fallback: check for failure indicators in output
  4723	                lower = output_text.lower()
  4724	                has_failure = any(
  4725	                    indicator in lower
  4726	                    for indicator in ["failed", "error", "errors", "failure"]
  4727	                )
  4728	                has_success = any(
  4729	                    indicator in lower
  4730	                    for indicator in ["passed", "ok", "success"]

