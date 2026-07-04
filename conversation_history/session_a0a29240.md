## Summarized at 2026-07-04T20:57:46.492854+00:00

Human: You are the code-reviewer specialist for task TASK-QAV-004.

Task context (from the task markdown):
## Description
Populate the `behavioural_oracle` bundle field and add the ONE deterministic
hard gate of this feature: an oracle **the Player did not author** (A2), run
against the live dependency, whose **ran-and-failed** outcome overrides an
approving Coach verdict to feedback — the direct fix for the fs-01 class
(FEAT-MEM-04 false green).

**Discovery is by artefact presence**
(`.claude/rules/activate-by-artefact-not-opt-in-flag.md`): an oracle file at
the convention path `tests/acceptance/*_roundtrip.py` in the worktree, or —
for non-file oracles only — a `behavioural_oracle.command` declared in the
feature YAML (genuine operator policy with no artefact proxy). No frontmatter
opt-in flag.

**Independence check** (ASSUM-004): the oracle file must NOT be in the turn's
authored set (`files_authored` when present, else `files_created ∪
files_modified`). A Player-authored oracle degrades to absent + a warning —
it is never trusted as independent evidence.

**Outcome policy** (consolidation §2 + ASSUM-005/006): ran-and-failed → hard
RED; started-then-timed-out → ran-and-failed (a deliverable that hangs is a
real defect, COACHRUNPARITY01 sem
[...truncated]

Phase 4 summary (test-orchestrator outcome):
- tests_run: 12
- tests_failed: 0
- coverage_pct: 0.0
- quality_gates_passed: True
- output_summary: Result:
============================== 12 passed in 2.44s ==============================

Your job:
1. Review the implementation in the worktree against the task's acceptance criteria using Read/Search/Grep.
2. Apply the review checklist from your agent definition (build, requirements, code quality, testing, security, performance, documentation).
3. Report findings via your normal response stream — the orchestrator records the review outcome in specialist_results.json.
Do NOT modify source files: the Write tool is intentionally withheld from this invocation.
AI: [{'name': 'ls', 'args': {'path': '/'}, 'id': 's0X0Ww5S5SOs9JNxMF9OfkUR12eHjaOJ', 'type': 'tool_call'}]
Tool: ['/bin.usr-is-merged/', '/bin/', '/boot/', '/cdrom/', '/dev/', '/etc/', '/home/', '/lib.usr-is-merged/', '/lib/', '/lost+found/', '/media/', '/mnt/', '/opt/', '/proc/', '/raid/', '/root/', '/run/', '/sbin.usr-is-merged/', '/sbin/', '/snap/', '/srv/', '/swap.img', '/sys/', '/tmp/', '/usr/', '/var/']
AI: [{'name': 'execute', 'args': {'command': 'pwd'}, 'id': 'Sx105i3HpDsZK2zRnKltiyqMuvxukgtA', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC

[Command succeeded with exit code 0]
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC'}, 'id': 'iBIZi4NJdroOUCkwAc1oakKbk2uOE29z', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.agentecflow/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.clarification_execution.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.coverage', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.env.example', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.git', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.github/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.gitignore', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit-git.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.mcp.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.pytest_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.tmp_clarification_context_sensitive_coach.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.venv/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CHANGELOG.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CLARIFICATION_EXECUTION_TASK-FBSDK-020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CLARIFICATION_QUICK_REFERENCE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CLARIFICATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CLAUDE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CNAME', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/CONTRIBUTING.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/DESIGN-DELIVERY-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/FEAT-AOF-verify/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/FastApi_feature_plans.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/IMPLEMENTATION-SUMMARY-TASK-AB-584A.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/IMPLEMENTATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/LICENSE', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/README.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TASK-DM-008-IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TASK-FBSDK-020-CODE-REVIEW.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TASK-FBSDK-020-COMPLETION-REPORT.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TASK-FBSDK-020-EXECUTION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TASK_FBSDK_002_IMPLEMENTATION.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TEST_RESULTS_FBSDK_020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/TEST_RESULTS_TASK_BRF_001.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/_scratch/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/autobuild_local_vllm.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/backups/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conftest.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/coverage.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docker/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/examples/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/execute_clarification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/features/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit.sln', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/ia03_ai_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/ia03_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/ia03_final_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/installer/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/large_tool_results/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/lib/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/logitech_gb10.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/main.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/measurements/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/minimax-backup-setup.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/mkdocs.yml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/node_modules/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/package-lock.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/package.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/phase_4_test_results.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/player_turn_1.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/pyproject.toml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/pytest.ini', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/requirements.txt', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/run_adr_tests.sh', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/scratch_notes.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/scripts/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/templates/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/test_api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tsconfig.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/uv.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/vitest.config.ts']
AI: [{'name': 'grep', 'args': {'pattern': 'behavioural_oracle'}, 'id': '5d0mqQcRCqYk6vF0w0Tq2FauY4VjvBqx', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-002/coach_evidence_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-004/player_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-004/task_work_results.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/features/FEAT-10AC.yaml
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.pytest_cache/v/cache/nodeids
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_219e8132.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_e1671105.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/retro/qa-verifier-state-consolidation-2026-07-04.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/features/qav-behavioural-gates/qav-behavioural-gates.feature
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/features/qav-behavioural-gates/qav-behavioural-gates_summary.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/player_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/IMPLEMENTATION-GUIDE.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-004-behavioural-roundtrip-oracle.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-004-behavioural-roundtrip-oracle.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_behavioural_oracle_guard.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_qav002_stub_scan_fields.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': 'N3Zh0X9KllxqijhlStPSyYxgXvjwyIED', 'type': 'tool_call'}]
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py'}, 'id': 'aEWveopAv4FIShMlpkm1T1Xv8f60WLo6', 'type': 'tool_call'}]
Tool:      1	"""CoachEvidenceBundle — structured evidence supplied by CoachValidator.
     2	
     3	TASK-HMIG-008R Part A (Revision 3, operator-approved 2026-05-20). Restores the
     4	LLM Coach as the primary decision-maker per the Block adversarial-cooperation
     5	paper, demoting CoachValidator from primary decision path to evidence supplier.
     6	
     7	The bundle is produced by ``CoachValidator.gather_evidence(...)`` and consumed
     8	by ``AgentInvoker.invoke_coach(...)`` which renders it into the Coach prompt
     9	via ``_build_coach_prompt(...)``. Every field corresponds to an intermediate
    10	value that the legacy ``CoachValidator.validate()`` method previously consumed
    11	internally to reach approve/feedback decisions. Under the new architecture
    12	those intermediates become read-only evidence the LLM Coach reasons about.
    13	
    14	Design rules (see ``.claude/rules/patterns/dataclasses.md``):
    15	
    16	* Internal value object — no external API boundary, no field-level validation
    17	  constraints, serialised via ``dataclasses.asdict`` + ``json.dumps``.
    18	* All evidence fields are ``Optional[...]`` so the bundle can be returned even
    19	  when one of the gathering stages aborted early.
    20	* ``gathering_status`` disambiguates "field is None because gathering aborted"
    21	  from "field is None because no signal was reported". The absence-of-failure
    22	  guards in the Coach prompt (TASK-HMIG-008R §4) instruct the Coach to treat
    23	  any ``None`` field as ABSENT SIGNAL when ``gathering_status != "complete"``.
    24	
    25	Cross-references:
    26	
    27	* ``.claude/rules/absence-of-failure-is-not-success.md`` — the structural
    28	  rule the LLM-layer guards mirror. Pair-with-attempted-count semantics map
    29	  directly onto the bundle's ``bdd.scenarios_attempted`` / ``tests.tests_run``
    30	  fields.
    31	* ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` — Layer-1
    32	  identity resolution lives in ``honesty.resolved_paths``; Layer-2 demotion
    33	  hint surfaces in ``severity_recommendations``.
    34	* TASK-REV-HMIG §14.9 (the architectural correction).
    35	"""
    36	
    37	from __future__ import annotations
    38	
    39	from dataclasses import dataclass, field
    40	from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
    41	
    42	if TYPE_CHECKING:  # pragma: no cover — annotation-only imports
    43	    # Imported under TYPE_CHECKING to avoid the circular dependency
    44	    # coach_validator.py -> coach_evidence.py -> coach_validator.py.
    45	    # Runtime values are duck-typed; the annotations document intent.
    46	    from guardkit.orchestrator.coach_verification import HonestyVerification
    47	    from guardkit.orchestrator.quality_gates.coach_validator import (
    48	        IndependentTestResult,
    49	        QualityGateStatus,
    50	    )
    51	
    52	
    53	GatheringStatus = Literal[
    54	    "complete",
    55	    "partial_honesty_abort",
    56	    "partial_gate_abort",
    57	    "partial_exception",
    58	]
    59	"""Status of the evidence-gathering pipeline.
    60	
    61	* ``complete`` — all gathering stages ran successfully and populated their fields.
    62	* ``partial_honesty_abort`` — honesty verification produced ``must_fix``
    63	  discrepancies; downstream gathering (gates, independent tests, requirements)
    64	  was skipped because the legacy decision tree would have short-circuited here.
    65	  Fields downstream of honesty are ``None``.
    66	* ``partial_gate_abort`` — quality gates failed; downstream gathering
    67	  (independent tests, requirements) was skipped. ``quality_gates`` is populated;
    68	  ``independent_tests`` and ``requirements_*`` fields are ``None``.
    69	* ``partial_exception`` — pre-evidence error (invalid task type, missing
    70	  task_work_results, or unexpected exception in a gathering helper). Inspect
    71	  ``gathering_error`` for the cause.
    72	"""
    73	
    74	
    75	@dataclass
    76	class RuntimeParityResult:
    77	    """Outcome of the per-task Coach runtime-parity check (TASK-AB-COACHRUNPARITY01, arm b).
    78	
    79	    The per-task Coach runs the feature's declared smoke command — the
    80	    deliverable's REAL runtime entry point — before approving, so a "passes
    81	    pytest but does not run" deliverable is caught pre-approval rather than
    82	    only by the post-wave smoke gate. Honours
    83	    ``absence-of-failure-is-not-success.md``: a ran-and-FAILED result blocks
    84	    approval; an ABSENT result (``ran=False`` — no command, parallel wave, or
    85	    runner error) never blocks and never counts as a pass.
    86	
    87	    Attributes
    88	    ----------
    89	    ran : bool
    90	        ``True`` only when the smoke command actually executed and produced an
    91	        exit code. ``False`` for every skip/absent case (``skipped_reason`` set).
    92	    passed : bool
    93	        ``True`` when ``ran`` and the observed exit code equals ``expected_exit``.
    94	        Always ``False`` when ``ran`` is ``False`` (absent != pass).
    95	    command : str
    96	        The smoke command that was (or would have been) run.
    97	    exit_code : Optional[int]
    98	        Observed exit code; ``None`` when the command did not run (or timed out).
    99	    expected_exit : int
   100	        The exit code that counts as success (the feature's configured value).
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 300, 'offset': 100}, 'id': 'agll1JJtkpnTEeRRIzxDbnOJWsnfV4hA', 'type': 'tool_call'}]
Tool:    101	    timed_out : bool
   102	        ``True`` when the command exceeded its timeout before completing.
   103	    stderr_tail : str
   104	        Last lines of captured stderr (for Player-facing feedback). Empty when
   105	        ``ran`` is ``False``.
   106	    skipped_reason : Optional[str]
   107	        Why the check did not run (``"no_smoke_command"``, ``"parallel_wave"``,
   108	        ``"runner_error: ..."``). ``None`` when the check ran.
   109	    output_tail : Optional[str]
   110	        Combined stdout+stderr tail (stdout first, each stream bounded to its
   111	        last 2000 chars). Additive field (2026-07-04 code review): pytest
   112	        writes its ``FAILED <nodeid>`` short-summary lines to STDOUT, so a
   113	        stderr-only tail hides the failing-test names from
   114	        ``AgentInvoker._apply_runtime_parity_guard``'s evidence extraction —
   115	        the same stdout+stderr join ``feature_orchestrator._build_smoke_feedback``
   116	        already performs post-wave. ``None`` on older records / when the run
   117	        produced no output; consumers fall back to ``stderr_tail``.
   118	    """
   119	
   120	    ran: bool
   121	    passed: bool
   122	    command: str
   123	    exit_code: Optional[int] = None
   124	    expected_exit: int = 0
   125	    timed_out: bool = False
   126	    stderr_tail: str = ""
   127	    skipped_reason: Optional[str] = None
   128	    output_tail: Optional[str] = None
   129	
   130	
   131	@dataclass
   132	class IndependentTestClassification:
   133	    """Substrate-vs-code classification of a ran-and-failed independent test run.
   134	
   135	    TASK-ABFIX-012. Computed by ``CoachValidator.gather_evidence`` ONLY when the
   136	    Coach's own independent test run RAN and FAILED (``tests_passed is False`` AND
   137	    ``signal_absent is False``) — never for a passing run and never for an ABSENT
   138	    signal (an absent signal must never manufacture a code verdict;
   139	    ``absence-of-failure-is-not-success.md``). ``None`` on the bundle otherwise.
   140	
   141	    A ``failure_class == "code"`` result for a TESTING task deterministically
   142	    blocks the turn via
   143	    ``AgentInvoker._apply_independent_test_code_failure_guard`` — the deterministic
   144	    backstop the LLM Coach lacked when it false-approved FEAT-FMDR-004 (a 5/9-red
   145	    TESTING task whose real code bugs were reasoned away as "substrate, absent").
   146	
   147	    Attributes
   148	    ----------
   149	    failure_class : str
   150	        One of ``"code"`` / ``"infrastructure"`` / ``"parallel_contention"`` /
   151	        ``"collection_error"`` / ``"sdk_api_error"`` (see
   152	        ``CoachValidator._classify_test_failure``). Only ``"code"`` blocks; a
   153	        substrate gap classifies ``"infrastructure"`` and genuine cross-task
   154	        contention classifies ``"parallel_contention"`` — neither reaches the
   155	        blocking guard, preserving the parallel-contention amnesty for non-code
   156	        failures.
   157	    confidence : str
   158	        ``"high"`` / ``"ambiguous"`` / ``"n/a"``. The guard blocks on any
   159	        confidence (a single-wave failure with no recognised exception token is
   160	        still ``("code", "n/a")`` and IS a real failure for a TESTING task).
   161	    raw_output_excerpt : str
   162	        Last 500 chars of the independent-test raw output, for the Player-facing
   163	        feedback. Bounded so ``coach_turn_N.json`` stays small.
   164	    """
   165	
   166	    failure_class: str
   167	    confidence: str
   168	    raw_output_excerpt: str = ""
   169	
   170	
   171	@dataclass
   172	class CoachEvidenceBundle:
   173	    """Structured evidence gathered by CoachValidator for the LLM Coach.
   174	
   175	    Each field maps to an intermediate value the legacy ``validate()`` method
   176	    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
   177	    (rendered as JSON into the Coach prompt) plus the honesty result and makes
   178	    the final approve/feedback decision.
   179	
   180	    Attributes
   181	    ----------
   182	    honesty
   183	        ``HonestyVerification`` from ``CoachVerifier``. Carries
   184	        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
   185	        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
   186	        gather path. The Coach reads this field unconditionally.
   187	    gathering_status
   188	        Pipeline status; see :data:`GatheringStatus` for the meaning of each
   189	        value. Used by the Coach to decide whether ``None`` evidence fields
   190	        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
   191	        (status == "complete").
   192	    gathering_error
   193	        Optional human-readable description of what went wrong when
   194	        ``gathering_status == "partial_exception"``. ``None`` on every other
   195	        status. Surfaced verbatim in the synthetic feedback rationale when the
   196	        primary ``_invoke_coach`` path catches an exception around evidence
   197	        gathering.
   198	    quality_gates
   199	        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
   200	        plan_audit). ``None`` when gathering aborted before the gates ran or
   201	        when the task type opts out of all gates.
   202	    coverage_details
   203	        Raw coverage dict slice from ``task_work_results['test_results']``
   204	        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
   205	        coverage was not reported.
   206	    plan_audit
   207	        Plan-audit findings dict from ``task_work_results['plan_audit']``.
   208	        ``None`` when the producer wrote no plan_audit block (e.g.
   209	        ``--implement-only`` without a saved plan).
   210	    bdd
   211	        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
   212	        scenarios_failed, scenarios_passed, scenarios_pending, failures,
   213	        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
   214	        applies the Pattern-2 absence-of-failure guard against
   215	        ``bdd['scenarios_attempted']``.
   216	    arch_review
   217	        Architectural review dict slice (``{"score": int, ...}``). ``None``
   218	        when no Phase 2.5B output was produced.
   219	    tests
   220	        Aggregate test result dict (tests_passed / tests_run /
   221	        line_coverage_met / branch_coverage_met / requires_infrastructure).
   222	        ``None`` when no test_results block was produced. The Coach applies
   223	        the absence-of-failure guard against ``tests['tests_run']``.
   224	    independent_tests
   225	        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
   226	        gathering aborted before independent tests or when the task type's
   227	        profile opts out of independent verification.
   228	    independent_test_classification
   229	        ``IndependentTestClassification`` (TASK-ABFIX-012) — substrate-vs-code
   230	        verdict for a RAN-AND-FAILED independent test run. Populated only when
   231	        ``independent_tests`` ran and failed (``tests_passed`` False AND
   232	        ``signal_absent`` False); ``None`` for passing / absent / skipped runs.
   233	        A ``("code", ...)`` result for a TESTING task deterministically blocks
   234	        the turn via ``AgentInvoker._apply_independent_test_code_failure_guard``.
   235	    requirements
   236	        ``RequirementsValidation`` from ``validate_requirements``. ``None``
   237	        when gathering aborted before requirements validation.
   238	    severity_recommendations
   239	        Structured hints derived from ``_honesty_issues_from`` demotion logic
   240	        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
   241	        Coach reads these to know when to demote ``file_existence``
   242	        discrepancies from ``must_fix`` to ``should_fix``.
   243	    task_type
   244	        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
   245	        ``"scaffolding"``). ``None`` when task type could not be resolved
   246	        (``partial_exception`` with invalid_task_type cause).
   247	    profile_name
   248	        Quality-gate profile name string. ``None`` on the same paths as
   249	        ``task_type``.
   250	    advisory_issues
   251	        Non-blocking issues that ride along with the final decision regardless
   252	        of approve/feedback outcome. Currently sourced from:
   253	
   254	        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
   255	          ``severity == "warning"``.
   256	        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
   257	          ``severity == "should_fix"``.
   258	
   259	        Pre-populated so the LLM Coach can read them without re-computing the
   260	        Layer-2 demotion.
   261	    wiring
   262	        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
   263	        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
   264	        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
   265	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   266	        authored source targets, or the factory is unavailable.
   267	    mocked_seam
   268	        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
   269	        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
   270	        the task type gates out, there are no authored acceptance files, or
   271	        the factory is unavailable.
   272	    spec_gap
   273	        SPEC_GAP analysis result (dict). Contains ``status``,
   274	        ``ground_truth_count``, ``executed_count``, ``findings``,
   275	        ``whole_file_deselection``. ``None`` when the task type gates out,
   276	        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
   277	        implemented.
   278	    stub_scan
   279	        L2 anti-stub scan result (dict) from ``guardkitfactory.wiring``.
   280	        Contains ``status``, ``findings``, ``symbols_scanned``. ``None`` when
   281	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   282	        authored source targets, or the factory is unavailable. Populated by
   283	        Wave-2 (TASK-QAV-002).
   284	    coverage
   285	        L3 coverage analysis result (dict). Contains ``status``,
   286	        ``coverage_percentage``, ``files_below_threshold``. ``None`` when the
   287	        factory is unavailable or coverage analysis did not run. Populated by
   288	        Wave-3 (TASK-QAV-003).
   289	    behavioural_oracle
   290	        L4 behavioural oracle result (dict). Contains ``status``,
   291	        ``scenarios_verified``, ``oracles_passed``. ``None`` when the factory
   292	        is unavailable or the oracle did not run. Populated by Wave-4
   293	        (TASK-QAV-004).
   294	    """
   295	
   296	    honesty: "HonestyVerification"
   297	    gathering_status: GatheringStatus = "complete"
   298	    gathering_error: Optional[str] = None
   299	
   300	    quality_gates: Optional["QualityGateStatus"] = None
   301	    coverage_details: Optional[Dict[str, Any]] = None
   302	    plan_audit: Optional[Dict[str, Any]] = None
   303	    bdd: Optional[Dict[str, Any]] = None
   304	    arch_review: Optional[Dict[str, Any]] = None
   305	    tests: Optional[Dict[str, Any]] = None
   306	
   307	    # Wave-1 wiring evidence fields (TASK-QAWE-002).
   308	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   309	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   310	    # or when guardkitfactory.wiring is unavailable (ImportError).
   311	    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
   312	    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
   313	    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)
   314	
   315	    # Wave-2+ anti-stub / coverage / behavioural-oracle fields (TASK-QAV-002/003/004).
   316	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   317	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   318	    # or when guardkitfactory.wiring is unavailable (ImportError).
   319	    stub_scan: Optional[Dict[str, Any]] = None      # L2 anti-stub scan (Wave-2)
   320	    coverage: Optional[Dict[str, Any]] = None       # L3 coverage analysis (Wave-3)
   321	    behavioural_oracle: Optional[Dict[str, Any]] = None  # L4 behavioural oracle (Wave-4)
   322	
   323	    independent_tests: Optional["IndependentTestResult"] = None
   324	    # TASK-ABFIX-012: substrate-vs-code classification of a ran-and-failed
   325	    # independent test run. Populated by gather_evidence ONLY when independent
   326	    # tests RAN and FAILED (tests_passed False AND signal_absent False). A
   327	    # ("code", ...) result for a TESTING task deterministically blocks via
   328	    # AgentInvoker._apply_independent_test_code_failure_guard. ``None`` for
   329	    # passing / absent / skipped runs — an absent signal never manufactures a
   330	    # code verdict (absence-of-failure-is-not-success). Serialised automatically
   331	    # by ``to_dict``/``asdict`` (it is a dataclass), so the verdict reaches
   332	    # coach_turn_N.json with no to_dict change (the ABFIX-010 serialization
   333	    # invariant).
   334	    independent_test_classification: Optional["IndependentTestClassification"] = None
   335	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   336	
   337	    # TASK-AB-COACHRUNPARITY01 (arm b): per-task runtime-parity check. The
   338	    # Coach runs the deliverable's declared runtime entry point (the feature
   339	    # smoke command) before approving, on single-task waves only. ``None`` when
   340	    # no check was attempted (no smoke command threaded / older callers).
   341	    # ``ran=False`` records an attempted-but-skipped check (parallel wave /
   342	    # runner error). A ``ran=True, passed=False`` result deterministically
   343	    # blocks the turn via ``AgentInvoker._apply_runtime_parity_guard``.
   344	    runtime_parity: Optional["RuntimeParityResult"] = None
   345	
   346	    # TASK-AB-XREPOEV01 (AC-002): Coach's independent test runs in declared
   347	    # sibling repos (``evidence_repos``). Each entry is an
   348	    # ``EvidenceTestResult.to_dict()``. Empty when no sibling repos are
   349	    # declared. These results reach ``coach_turn_N.json`` (this bundle is
   350	    # serialised verbatim) and the Coach prompt, and a ran-and-failed suite
   351	    # deterministically blocks the turn in the orchestrator.
   352	    evidence_repo_tests: List[Dict[str, Any]] = field(default_factory=list)
   353	
   354	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   355	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   356	
   357	    task_type: Optional[str] = None
   358	    profile_name: Optional[str] = None
   359	
   360	    def to_dict(self) -> Dict[str, Any]:
   361	        """Serialise the bundle to a JSON-compatible dict.
   362	
   363	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   364	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   365	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   366	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   367	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   368	        """
   369	        from dataclasses import asdict
   370	
   371	        return asdict(self)
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 100}, 'id': 'gl9XM73MMFQUk2xr4jGiCXXc0tCdPtDv', 'type': 'tool_call'}]
Tool:    101	logger = logging.getLogger(__name__)
   102	
   103	# TASK-ABFIX-011: default per-test pytest-timeout (seconds) the Coach injects
   104	# into its isolated pytest run so a single hanging test is marked FAILED while
   105	# the others still run, instead of consuming the whole subprocess budget and
   106	# yielding ``tests_run=0``. Generous by design — the Coach runs focused
   107	# per-task suites, so a test exceeding 60s is almost certainly hung, not slow.
   108	# Operator-tunable via ``GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS``; injection is
   109	# triple-gated (operator flag, Python stack, plugin-resolvable). See
   110	# ``.claude/rules/stack-plugin-architecture.md`` and
   111	# ``.claude/rules/absence-of-failure-is-not-success.md``.
   112	_DEFAULT_COACH_PER_TEST_TIMEOUT_S = 60
   113	
   114	# TASK-AB-COACHSUBPROC01 (2026-07-04): single source of truth for the Coach's
   115	# independent test-execution default — flipped "sdk" -> "subprocess". The SDK
   116	# "environment parity" path failed with the opaque exit-1 "Fatal error in
   117	# message reader" on essentially 100% of invocations across every repo,
   118	# machine and vintage in the 2026 retro corpus (2026-07-04 xref §5 item 15);
   119	# every verdict actually came from the subprocess fallback, so each Coach turn
   120	# paid one doomed SDK attempt. The SDK path stays in-repo as an explicit
   121	# opt-in (config `autobuild.coach.test_execution: sdk` or env
   122	# `GUARDKIT_COACH_TEST_EXECUTION=sdk`) for the open diagnosis tasks
   123	# (TASK-REV-COSE, TASK-FIX-A7B7). Mirrors the ``selector.py::DEFAULT_HARNESS``
   124	# cutover shape: permanent rollback = change this one constant back to "sdk".
   125	DEFAULT_COACH_TEST_EXECUTION = "subprocess"
   126	
   127	# Env override for the Coach test-execution mode. Precedence mirrors the
   128	# TASK-AB-PERTASKFG01 ``GUARDKIT_PHASE4_TEST_EXECUTION`` pattern:
   129	# env > config (``autobuild.coach.test_execution``) > default.
   130	COACH_TEST_EXECUTION_ENV = "GUARDKIT_COACH_TEST_EXECUTION"
   131	
   132	_VALID_COACH_TEST_EXECUTION_MODES = ("subprocess", "sdk")
   133	
   134	
   135	def resolve_coach_test_execution(config_value: Optional[str] = None) -> str:
   136	    """Resolve the Coach independent test-execution mode.
   137	
   138	    Precedence: ``GUARDKIT_COACH_TEST_EXECUTION`` env var > *config_value*
   139	    (``.guardkit/config.yaml`` ``autobuild.coach.test_execution``) >
   140	    :data:`DEFAULT_COACH_TEST_EXECUTION`. Read at call time (not import time)
   141	    so tests and operators can flip it per-invocation. An unrecognised value
   142	    at either tier logs a WARNING and that tier is ignored (falls through to
   143	    the next tier), so an invalid value can never select a mode by accident.
   144	
   145	    Logs the active mode and its provenance (env/config/default) at INFO —
   146	    called once per :class:`CoachValidator` init, so operators can see which
   147	    execution path the Coach will use and where the decision came from
   148	    (display-must-derive-from-enforcement-source: the logged value IS the
   149	    value the validator consumes, not a proxy).
   150	
   151	    Parameters
   152	    ----------
   153	    config_value : Optional[str]
   154	        The raw ``autobuild.coach.test_execution`` value from
   155	        ``.guardkit/config.yaml``, or None when unset.
   156	
   157	    Returns
   158	    -------
   159	    str
   160	        ``"subprocess"`` or ``"sdk"``.
   161	    """
   162	    mode: Optional[str] = None
   163	    source = "default"
   164	
   165	    env_raw = os.environ.get(COACH_TEST_EXECUTION_ENV)
   166	    if env_raw is not None and env_raw.strip():
   167	        candidate = env_raw.strip().lower()
   168	        if candidate in _VALID_COACH_TEST_EXECUTION_MODES:
   169	            mode, source = candidate, "env"
   170	        else:
   171	            logger.warning(
   172	                "Invalid %s=%r (expected one of %s); ignoring env override.",
   173	                COACH_TEST_EXECUTION_ENV,
   174	                env_raw,
   175	                _VALID_COACH_TEST_EXECUTION_MODES,
   176	            )
   177	
   178	    if mode is None and config_value is not None and str(config_value).strip():
   179	        candidate = str(config_value).strip().lower()
   180	        if candidate in _VALID_COACH_TEST_EXECUTION_MODES:
   181	            mode, source = candidate, "config"
   182	        else:
   183	            logger.warning(
   184	                "Invalid autobuild.coach.test_execution=%r in "
   185	                ".guardkit/config.yaml (expected one of %s); "
   186	                "falling back to default %r.",
   187	                config_value,
   188	                _VALID_COACH_TEST_EXECUTION_MODES,
   189	                DEFAULT_COACH_TEST_EXECUTION,
   190	            )
   191	
   192	    if mode is None:
   193	        mode = DEFAULT_COACH_TEST_EXECUTION
   194	
   195	    logger.info(
   196	        "Coach test execution mode: %s (source: %s; "
   197	        "%s > autobuild.coach.test_execution > default %r) "
   198	        "[TASK-AB-COACHSUBPROC01]",
   199	        mode,
   200	        source,
   201	        COACH_TEST_EXECUTION_ENV,
   202	        DEFAULT_COACH_TEST_EXECUTION,
   203	    )
   204	    return mode
   205	
   206	
   207	# ============================================================================
   208	# BDD Factory Bridge — wire guardkitfactory.bdd into the Coach evidence path
   209	# ============================================================================
   210	#
   211	# TASK-BDDW-001: Replace the legacy pytest-hardcoded bdd_runner.py path in the
   212	# Coach evidence path with guardkitfactory's plugin-discovery subsystem.
   213	#
   214	# The bridge uses a lazy import (try/except ImportError) so that
   215	# ``pip install guardkit-py`` without the ``[autobuild]`` extra still works.
   216	# When guardkitfactory is unavailable, the Coach falls back to the Player's
   217	# self-reported ``bdd_results`` (legacy behaviour).
   218	#
   219	# Mapping: BDDRunResult (factory) → bundle.bdd dict (legacy shape)
   220	#
   221	#   BDDRunResult.scenarios_attempted          → bundle.bdd["scenarios_attempted"]
   222	#   BDDRunResult.scenarios_passed             → bundle.bdd["scenarios_passed"]
   223	#   BDDRunResult.scenarios_failed             → bundle.bdd["scenarios_failed"]
   224	#   BDDRunResult.scenarios_skipped            → bundle.bdd["scenarios_pending"]
   225	#   BDDRunResult.scenarios_errored            → bundle.bdd["scenarios_errored"]
   226	#   BDDRunResult.duration_seconds             → bundle.bdd["duration_seconds"]
   227	#   BDDRunResult.raw_report_path              → bundle.bdd["raw_report_path"] (str|None)
   228	#   BDDRunResult.discoveries[*]["feature_file"] → bundle.bdd["feature_files"]
   229	#   BDDRunResult.errors[*]                    → bundle.bdd["failures"][*]["error"]
   230	#   (bundle.bdd["pending"] is always [] — the real contract carries no
   231	#    per-scenario pending list; the pending COUNT derives from scenarios_skipped.)
   232	#
   233	# TASK-FIX-BDDFW01: the bridge originally targeted an ABANDONED BDDRunResult
   234	# contract (``.failures``/``.pending``/``.scenarios_pending``/``.feature_files``)
   235	# and a one-arg ``discover``/``plugin.run`` shape. Every call on the live path
   236	# raised AttributeError/TypeError, was swallowed by the broad ``except`` below,
   237	# and degraded to the Player-reported fallback — so the bridge was SILENTLY
   238	# DEAD. The mapping above now reflects the REAL guardkitfactory contract
   239	# (``guardkitfactory/src/guardkitfactory/bdd/plugin.py``).
   240	#
   241	# Key contract: ``scenarios_attempted`` is non-Optional on BDDRunResult and
   242	# must be preserved verbatim for the absence-of-failure gate. A value of 0
   243	# means "no scenarios ran" (ABSENT SIGNAL), NOT "zero failures = pass".
   244	
   245	# StackProfile values consumed by guardkitfactory.bdd.discover().
   246	# Mapped from the worktree's project.template string.
   247	_STACK_PROFILE_MAP: Dict[str, str] = {
   248	    "python": "python",
   249	    "fastapi-python": "python",
   250	    "django-python": "python",
   251	    "flask-python": "python",
   252	    ".net": "dotnet",
   253	    "aspnet-core": "dotnet",
   254	    "csharp": "dotnet",
   255	    "node-js": "javascript",
   256	    "javascript": "javascript",
   257	    "typescript": "javascript",
   258	}
   259	"""Mapping from ``project.template`` to a stack profile-key."""
   260	
   261	
   262	# Translate a profile-key (the value side of ``_STACK_PROFILE_MAP``, also
   263	# produced by the filesystem-marker fallback below) into the real
   264	# guardkitfactory ``StackProfile`` field-set. Only ``PytestBDDPlugin.discover``
   265	# matches on ``test_framework`` (it requires ``"pytest"``);
   266	# ``ReqnrollPlugin``/``CucumberJSPlugin`` match on ``language`` alone, so the
   267	# dotnet/javascript ``test_framework`` strings are advisory.
   268	_PROFILE_KEY_TO_STACK: Dict[str, Tuple[str, str, str]] = {
   269	    # profile_key: (language, test_framework, package_manager)
   270	    "python": ("python", "pytest", "pip"),
   271	    "dotnet": ("csharp", "dotnet-test", "nuget"),
   272	    "javascript": ("typescript", "vitest", "npm"),
   273	}
   274	
   275	
   276	def _detect_profile_key(workspace_root: Path) -> Optional[str]:
   277	    """Return a stack profile-key for the worktree, or ``None`` when unknown.
   278	
   279	    Resolution order:
   280	      1. ``.claude/settings.json`` → ``project.template`` (mapped via
   281	         ``_STACK_PROFILE_MAP``) — authoritative when present.
   282	      2. Filesystem markers (worktrees created without a ``settings.json``):
   283	         ``pyproject.toml``/``requirements.txt`` → python,
   284	         ``*.csproj``/``*.sln`` → dotnet, ``package.json`` → javascript.
   285	    """
   286	    template = detect_stack_template(workspace_root)
   287	    if template is not None:
   288	        key = _STACK_PROFILE_MAP.get(template)
   289	        if key is not None:
   290	            return key
   291	
   292	    if (workspace_root / "pyproject.toml").exists() or (
   293	        workspace_root / "requirements.txt"
   294	    ).exists():
   295	        return "python"
   296	    if any(workspace_root.glob("*.csproj")) or any(workspace_root.glob("*.sln")):
   297	        return "dotnet"
   298	    if (workspace_root / "package.json").exists():
   299	        return "javascript"
   300	    return None
   301	
   302	
   303	def _detect_stack_profile(
   304	    workspace_root: Optional[Path],
   305	) -> Optional["StackProfile"]:
   306	    """Detect a guardkitfactory ``StackProfile`` for the worktree.
   307	
   308	    Returns a real ``StackProfile`` dataclass — the type that
   309	    ``guardkitfactory.bdd.discover`` requires — or ``None`` when the worktree
   310	    is missing, the stack is unknown, or guardkitfactory is unavailable.
   311	
   312	    TASK-FIX-BDDFW01: previously annotated ``-> Optional[str]`` and returned a
   313	    bare profile string, which ``discover`` cannot consume — the live factory
   314	    path raised ``TypeError`` and was silently swallowed.
   315	
   316	    Parameters
   317	    ----------
   318	    workspace_root : Optional[Path]
   319	        Root of the worktree.
   320	
   321	    Returns
   322	    -------
   323	    Optional[StackProfile]
   324	        A populated ``StackProfile`` (``language``/``test_framework``/
   325	        ``package_manager``/``project_root``/``extras``) or ``None``.
   326	    """
   327	    if workspace_root is None:
   328	        return None
   329	    root = Path(workspace_root)
   330	    if not root.exists():
   331	        return None
   332	    # StackProfile is the lazily-imported factory dataclass; None when the
   333	    # factory is unavailable. The live path only calls this when the factory
   334	    # IS available, but guard defensively.
   335	    if StackProfile is None:
   336	        return None
   337	    key = _detect_profile_key(root)
   338	    if key is None:
   339	        return None
   340	    language, test_framework, package_manager = _PROFILE_KEY_TO_STACK[key]
   341	    return StackProfile(
   342	        language=language,
   343	        test_framework=test_framework,
   344	        package_manager=package_manager,
   345	        project_root=root,
   346	        extras={},
   347	    )
   348	
   349	
   350	def map_bdd_run_result(
   351	    run_result: "BDDRunResult",
   352	) -> Dict[str, Any]:
   353	    """Map a guardkitfactory ``BDDRunResult`` into the legacy ``bundle.bdd`` dict.
   354	
   355	    Reads ONLY real ``BDDRunResult`` fields (see
   356	    ``guardkitfactory/src/guardkitfactory/bdd/plugin.py``):
   357	    ``scenarios_attempted``/``passed``/``failed``/``skipped``/``errored``,
   358	    ``duration_seconds``, ``raw_report_path``, ``discoveries``, ``errors``.
   359	
   360	    Preserves ``scenarios_attempted`` verbatim — never coerces a missing key
   361	    to 0. This is critical for the absence-of-failure gate: when
   362	    ``scenarios_attempted == 0``, the Coach must treat it as ABSENT SIGNAL,
   363	    not as a silent pass
   364	    (``.claude/rules/absence-of-failure-is-not-success.md``).
   365	
   366	    Parameters
   367	    ----------
   368	    run_result : BDDRunResult
   369	        Result from the factory BDD plugin.
   370	
   371	    Returns
   372	    -------
   373	    Dict[str, Any]
   374	        A ``bundle.bdd``-shaped dict with keys: ``scenarios_attempted``,
   375	        ``scenarios_passed``, ``scenarios_failed``, ``scenarios_pending``
   376	        (from ``scenarios_skipped``), ``scenarios_errored``,
   377	        ``duration_seconds``, ``raw_report_path`` (str|None), ``feature_files``
   378	        (from ``discoveries``), ``failures`` (from ``errors``), and ``pending``
   379	        (always ``[]`` — the real contract carries no per-scenario pending list).
   380	    """
   381	    # feature_files: derive from discoveries[*]["feature_file"].
   382	    feature_files: List[str] = []
   383	    for disc in run_result.discoveries:
   384	        if isinstance(disc, dict):
   385	            feature_file = disc.get("feature_file")
   386	            if feature_file:
   387	                feature_files.append(str(feature_file))
   388	
   389	    # failures: one dict per error string. Carry the error text under both
   390	    # "error" (factory-native) and "reason" (so the legacy
   391	    # ``_check_bdd_results`` consumer surfaces it in Player feedback).
   392	    failure_dicts: List[Dict[str, Any]] = [
   393	        {"error": err, "reason": err} for err in run_result.errors
   394	    ]
   395	
   396	    raw_report_path = (
   397	        str(run_result.raw_report_path)
   398	        if run_result.raw_report_path is not None
   399	        else None
   400	    )
   401	
   402	    return {
   403	        "scenarios_attempted": run_result.scenarios_attempted,
   404	        "scenarios_passed": run_result.scenarios_passed,
   405	        "scenarios_failed": run_result.scenarios_failed,
   406	        "scenarios_pending": run_result.scenarios_skipped,
   407	        "scenarios_errored": run_result.scenarios_errored,
   408	        "duration_seconds": run_result.duration_seconds,
   409	        "raw_report_path": raw_report_path,
   410	        "feature_files": feature_files,
   411	        "failures": failure_dicts,
   412	        "pending": [],
   413	    }
   414	
   415	
   416	# Backward-compatible alias: TASK-BDDW-001 shipped this function privately as
   417	# ``_map_bdd_run_result_to_bundle``; ``map_bdd_run_result`` is the public name
   418	# the wiring test (TASK-FIX-BDDFW01) imports. Both refer to ONE corrected
   419	# implementation so producer and consumer cannot drift.
   420	_map_bdd_run_result_to_bundle = map_bdd_run_result
   421	
   422	
   423	# Lazy import of guardkitfactory BDD plugin subsystem.
   424	# The import is guarded so that ``pip install guardkit-py`` without
   425	# ``[autobuild]`` still works — Coach falls back to Player-reported
   426	# bdd_results when the factory is unavailable.
   427	try:
   428	    from guardkitfactory.bdd import (
   429	        BDDRunResult,
   430	        discover,
   431	    )
   432	    from guardkitfactory.bdd.plugin import StackProfile
   433	
   434	    _FACTORY_AVAILABLE = True
   435	except ImportError:
   436	    BDDRunResult = None  # type: ignore[misc,assignment]
   437	    discover = None  # type: ignore[misc,assignment]
   438	    StackProfile = None  # type: ignore[misc,assignment]
   439	    _FACTORY_AVAILABLE = False
   440	
   441	# Module-level cache for the factory import status.
   442	# Re-checked at runtime for each Coach invocation so that a late-installed
   443	# guardkitfactory (e.g. via a post-gather pip install) is picked up.
   444	_factory_available_cache: Optional[bool] = None
   445	
   446	
   447	def _is_factory_available() -> bool:
   448	    """Return True when the guardkitfactory BDD plugin subsystem is importable.
   449	
   450	    Uses a module-level cache that is invalidated on each call to
   451	    ``gather_evidence`` (see the ``_reset_factory_cache`` helper).
   452	    """
   453	    global _factory_available_cache
   454	    if _factory_available_cache is not None:
   455	        return _factory_available_cache
   456	    _factory_available_cache = _FACTORY_AVAILABLE
   457	    return _FACTORY_AVAILABLE
   458	
   459	
   460	def _reset_factory_cache() -> None:
   461	    """Invalidate the factory availability cache.
   462	
   463	    Called at the start of each ``gather_evidence`` invocation so that
   464	    a late-installed guardkitfactory is picked up on subsequent runs.
   465	    """
   466	    global _factory_available_cache
   467	    _factory_available_cache = None
   468	
   469	
   470	def _run_factory_bdd(
   471	    worktree_path: Path,
   472	    stack_profile: Optional["StackProfile"],
   473	    task_id: Optional[str] = None,
   474	) -> Optional[Dict[str, Any]]:
   475	    """Discover and run the BDD plugin for the given stack profile.
   476	
   477	    Drives the real guardkitfactory plugin lifecycle:
   478	    ``discover(stack, worktree)`` → ``preflight(task_id, worktree)`` →
   479	    ``run(scenarios, task_id, worktree)`` → :func:`map_bdd_run_result`.
   480	
   481	    TASK-FIX-BDDFW01: the original implementation targeted an ABANDONED
   482	    contract — it called ``discover(stack_profile)`` (one positional ``str``)
   483	    and ``plugin.run(worktree_path)``. Both raised ``TypeError`` against the
   484	    real guardkitfactory signatures and were silently swallowed, leaving the
   485	    bridge dead on the live path. This version uses the real two-arg
   486	    ``discover(stack: StackProfile, worktree: Path)`` and the real
   487	    ``run(scenarios, task_id, worktree)`` signature.
   488	
   489	    Parameters
   490	    ----------
   491	    worktree_path : Path
   492	        Root of the worktree containing the BDD scenarios.
   493	    stack_profile : Optional[StackProfile]
   494	        Detected stack profile from :func:`_detect_stack_profile`.
   495	    task_id : Optional[str]
   496	        Active task identity. Required to honour the per-task glue contract
   497	        (``GUARDKIT_BDD_TASK_ID`` / ``-m task_<id>``); without it the per-task
   498	        oracle cannot run and the bridge returns ABSENT SIGNAL.
   499	
   500	    Returns
   501	    -------
   502	    Optional[Dict[str, Any]]
   503	        A ``bundle.bdd``-shaped dict, or ``None`` when the factory is
   504	        unavailable, the stack profile is unknown, preflight fails, or
   505	        discovery/execution fails. ``None`` is ABSENT SIGNAL — never a silent
   506	        pass (``.claude/rules/absence-of-failure-is-not-success.md``).
   507	    """
   508	    if not _is_factory_available():
   509	        logger.debug(
   510	            "BDD factory bridge: guardkitfactory not available; "
   511	            "falling back to Player-reported bdd_results.",
   512	        )
   513	        return None
   514	
   515	    if stack_profile is None:
   516	        logger.debug(
   517	            "BDD factory bridge: no stack profile detected; "
   518	            "falling back to Player-reported bdd_results.",
   519	        )
   520	        return None
   521	
   522	    # Guard against discover/StackProfile being None (factory not importable).
   523	    if discover is None or StackProfile is None:
   524	        return None
   525	
   526	    if not task_id:
   527	        logger.debug(
   528	            "BDD factory bridge: no task_id in scope; the per-task BDD oracle "
   529	            "cannot run. Returning ABSENT SIGNAL.",
   530	        )
   531	        return None
   532	
   533	    try:
   534	        plugin = discover(stack_profile, worktree_path)
   535	        if plugin is None:
   536	            logger.debug(
   537	                "BDD factory bridge: no plugin discovered for stack %s; "
   538	                "falling back to Player-reported bdd_results.",
   539	                stack_profile,
   540	            )
   541	            return None
   542	
   543	        # Lifecycle: preflight before run. A failed preflight means the
   544	        # per-task glue convention is not satisfied (no bound scenarios), so a
   545	        # blind ``-m task_<id>`` run would deselect everything — surface ABSENT
   546	        # SIGNAL rather than subprocessing a guaranteed-zero run.
   547	        preflight = getattr(plugin, "preflight", None)
   548	        if callable(preflight) and not preflight(task_id, worktree_path):
   549	            logger.debug(
   550	                "BDD factory bridge: preflight failed for task %s on stack %s; "
   551	                "ABSENT SIGNAL (per-task glue not configured).",
   552	                task_id,
   553	                stack_profile,
   554	            )
   555	            return None
   556	
   557	        # scenarios=[] — pytest-bdd re-discovers from features/ internally
   558	        # (Contract C4). Pre-discovering Scenario objects for every stack is
   559	        # the remit of TASK-HMIG-BDDWIRE, not this contract fix.
   560	        result = plugin.run([], task_id, worktree_path)
   561	
   562	        if result is None:
   563	            logger.debug(
   564	                "BDD factory bridge: plugin returned None for stack %s; "
   565	                "falling back to Player-reported bdd_results.",
   566	                stack_profile,
   567	            )
   568	            return None
   569	
   570	        # Map BDDRunResult → bundle.bdd shape.
   571	        return map_bdd_run_result(result)
   572	
   573	    except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering
   574	        logger.warning(
   575	            "BDD factory bridge raised %s for stack %s; "
   576	            "falling back to Player-reported bdd_results.",
   577	            exc.__class__.__name__,
   578	            stack_profile,
   579	        )
   580	        return None
   581	
   582	
   583	# ============================================================================
   584	# Wiring Factory Bridge — wire guardkitfactory.wiring into the Coach evidence
   585	# ============================================================================
   586	#
   587	# TASK-QAWE-002 (Wave-1): Lazy import of the UNWIRED_PATH / MOCKED_SEAM
   588	# analyzer. The import is guarded so that ``pip install guardkit-py`` without
   589	# the ``[autobuild]`` extra still works — Coach leaves all three wiring
   590	# fields as ``None`` when the factory is unavailable.
   591	#
   592	# The seam returns a dict (never the dataclass) so coach_evidence.py keeps
   593	# zero guardkitfactory import.
   594	
   595	try:
   596	    from guardkitfactory.wiring import (  # type: ignore[attr-defined,no-redef]
   597	        analyze_stub_scan,
   598	        analyze_wiring,
   599	    )
   600	
AI: [{'name': 'grep', 'args': {'pattern': 'behavioural_oracle', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': 'NVE7LnLZ0B7XqRxSiikxzWNB1sB7A58z', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py
AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'pattern': 'def gather_evidence'}, 'id': 'Bsf2JxYX8PpJIYjrGutDC6sSGEcX5j2p', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py:
  2945:     def gather_evidence(
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2500}, 'id': 'Aa59DIAOMKHhfvXls8IaCucP8aMJ7trn', 'type': 'tool_call'}]
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2945}, 'id': 'X8c1onDnj1eAXYEW3P54BOlQvIh8FntA', 'type': 'tool_call'}]
Tool:   2946	        self,
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 3440}, 'id': 'YsXAzJY7w8HUy3TZUmNLMiXrvykkZ4Su', 'type': 'tool_call'}]
Tool:   3441	            stub_scan_dict = _compute_stub_scan(
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
  3501	        # absent (ran=False) signal, not a pass.
  3502	        # ------------------------------------------------------------------
  3503	        runtime_parity = self._gather_runtime_parity()
  3504	
  3505	        # ------------------------------------------------------------------
  3506	        # 7. Independent-test substrate-vs-code classification (TASK-ABFIX-012).
  3507	        # The live gather_evidence path carries NO failure classification on the
  3508	        # bundle today (the legacy validate() path's _classify_test_failure is
  3509	        # not on this path), so a genuine independent CODE failure has no
  3510	        # deterministic blocking guard — the FMDR-004 false-approval. Compute the
  3511	        # verdict HERE (the single place where the classifier + wave-context
  3512	        # is_parallel/wave_size + task_type converge) and carry it on the bundle
  3513	        # for AgentInvoker._apply_independent_test_code_failure_guard.
  3514	        #
  3515	        # Computed ONLY for a RAN-AND-FAILED run (tests_passed False AND
  3516	        # signal_absent False). An ABSENT signal (signal_absent True — e.g. a
  3517	        # host-substrate gap) is owned by the absent guard and must NEVER
  3518	        # manufacture a code verdict (absence-of-failure-is-not-success). A
  3519	        # passing / skipped run leaves it None.
  3520	        independent_test_classification: Optional[IndependentTestClassification] = None
  3521	        if (
  3522	            test_result.tests_passed is False
  3523	            and test_result.signal_absent is False
  3524	        ):
  3525	            fc, conf = self._classify_test_failure(
  3526	                test_result.raw_output,
  3527	                requires_infrastructure=(
  3528	                    task.get("requires_infrastructure") if task else None
  3529	                ),
  3530	                task_type=task_type.value,
  3531	            )
  3532	            # TASK-ABFIX-012: for a TESTING task the parallel-wave
  3533	            # parallel_contention amnesty must not cover the task's OWN failures.
  3534	            # A recognised own-code exception token is already ('code','high').
  3535	            # A NON-token failure (e.g. ValueError / KeyError / a custom
  3536	            # exception) in a parallel wave classifies parallel_contention here;
  3537	            # reclassify it to ('code','high') so the guard blocks it — UNLESS
  3538	            # there is genuine cross-task source-file contention (this task's
  3539	            # authored files overlap a peer's edits in the same wave), the one
  3540	            # case the amnesty must keep (constraint 3). The original ABFIX-005
  3541	            # contention (import / collection races) is caught earlier in the
  3542	            # classifier and never reaches here, so this only reclassifies real
  3543	            # own-code test failures, never a genuine race. Single-task waves
  3544	            # never produce parallel_contention, so this is a no-op there.
  3545	            if task_type == TaskType.TESTING and fc == "parallel_contention":
  3546	                if not self._detect_source_file_contention(task_work_results):
  3547	                    logger.info(
  3548	                        "gather_evidence: TESTING parallel failure with no peer "
  3549	                        "source-file overlap reclassified parallel_contention -> "
  3550	                        "('code','high') for %s (own-code failure, not contention).",
  3551	                        task_id,
  3552	                    )
  3553	                    fc, conf = "code", "high"
  3554	            independent_test_classification = IndependentTestClassification(
  3555	                failure_class=fc,
  3556	                confidence=conf,
  3557	                raw_output_excerpt=(test_result.raw_output or "")[-500:],
  3558	            )
  3559	
  3560	        return CoachEvidenceBundle(
  3561	            honesty=honesty,
  3562	            gathering_status="complete",
  3563	            quality_gates=gates,
  3564	            coverage_details=coverage_details,
  3565	            plan_audit=plan_audit_dict,
  3566	            bdd=bdd_dict,
  3567	            arch_review=arch_review_dict,
  3568	            tests=tests_dict,
  3569	            independent_tests=test_result,
  3570	            independent_test_classification=independent_test_classification,
  3571	            requirements=requirements,
  3572	            severity_recommendations=severity_recommendations,
  3573	            advisory_issues=advisory_issues,
  3574	            task_type=task_type.value,
  3575	            profile_name=profile_name,
  3576	            wiring=wiring_dict,
  3577	            mocked_seam=mocked_seam_dict,
  3578	            spec_gap=spec_gap_dict,
  3579	            stub_scan=stub_scan_dict,
  3580	            coverage=coverage_dict,     # Wave-3 (TASK-QAV-003)
  3581	            behavioural_oracle=None,   # Wave-4 (TASK-QAV-004)
  3582	            runtime_parity=runtime_parity,
  3583	        )
  3584	
  3585	    def _gather_runtime_parity(self) -> Optional["RuntimeParityResult"]:
  3586	        """Run the deliverable's runtime entry point (TASK-AB-COACHRUNPARITY01, arm b).
  3587	
  3588	        Returns ``None`` when no smoke command was threaded (older callers /
  3589	        feature with no smoke gate). Returns a ``RuntimeParityResult`` with
  3590	        ``ran=False`` (and a ``skipped_reason``) when the check is intentionally
  3591	        skipped (parallel wave) or the runner itself errors — an ABSENT signal
  3592	        that never blocks and never counts as a pass
  3593	        (``absence-of-failure-is-not-success.md``). Returns ``ran=True`` with
  3594	        ``passed`` reflecting a clean (exit 0) standalone run otherwise.
  3595	
  3596	        Guard: runs only on a single-task wave (``wave_size == 1``). On a
  3597	        multi-task wave the deliverable may not run standalone until peers
  3598	        finish, so a per-task smoke run would false-fail; those waves rely on
  3599	        the feature-level post-wave smoke gate instead.
  3600	        """
  3601	        if not self.smoke_command:
  3602	            return None
  3603	
  3604	        command = self.smoke_command
  3605	        if self.wave_size > 1:
  3606	            return RuntimeParityResult(
  3607	                ran=False,
  3608	                passed=False,
  3609	                command=command,
  3610	                skipped_reason="parallel_wave",
  3611	            )
  3612	
  3613	        # PATH-prepend the bootstrap venv so a bare ``python`` / ``pytest`` in
  3614	        # the smoke command resolves to the right interpreter (mirrors
  3615	        # smoke_gates.run_smoke_gate's venv handling).
  3616	        env: Optional[dict] = None
  3617	        if self._venv_python is not None:
  3618	            env = os.environ.copy()
  3619	            env["PATH"] = (
  3620	                str(Path(self._venv_python).parent)
  3621	                + os.pathsep
  3622	                + env.get("PATH", "")
  3623	            )
  3624	
  3625	        try:
  3626	            proc = subprocess.run(
  3627	                command,
  3628	                shell=True,
  3629	                cwd=str(self.worktree_path),
  3630	                capture_output=True,
  3631	                text=True,
  3632	                timeout=self.test_timeout,
  3633	                env=env,
  3634	            )
  3635	        except subprocess.TimeoutExpired as exc:
  3636	            timeout_stderr = (
  3637	                exc.stderr.decode() if isinstance(exc.stderr, bytes)
  3638	                else exc.stderr
  3639	            ) or ""
  3640	            timeout_stdout = (
  3641	                exc.stdout.decode() if isinstance(exc.stdout, bytes)
  3642	                else exc.stdout
  3643	            ) or ""
  3644	            stderr_tail = "\n".join(
  3645	                timeout_stderr.rstrip().splitlines()[-40:]
  3646	            )
  3647	            logger.warning(
  3648	                "Runtime-parity check timed out after %ss: %s",
  3649	                self.test_timeout, command,
  3650	            )
  3651	            # NOTE: ran=True on timeout is operator-pinned
  3652	            # (TASK-AB-COACHRUNPARITY01: a smoke entry point that starts and
  3653	            # hangs is a real deliverable defect). output_tail is additive
  3654	            # evidence only — verdict/timeout semantics unchanged.
  3655	            return RuntimeParityResult(
  3656	                ran=True,
  3657	                passed=False,
  3658	                command=command,
  3659	                exit_code=None,
  3660	                expected_exit=self.smoke_expected_exit,
  3661	                timed_out=True,
  3662	                stderr_tail=stderr_tail,
  3663	                output_tail=_combined_output_tail(timeout_stdout, timeout_stderr),
  3664	            )
  3665	        except Exception as exc:  # noqa: BLE001 — runner errors are ABSENT, not fail
  3666	            logger.warning(
  3667	                "Runtime-parity check runner error for %s: %s", command, exc,
  3668	            )
  3669	            return RuntimeParityResult(
  3670	                ran=False,
  3671	                passed=False,
  3672	                command=command,
  3673	                skipped_reason=f"runner_error: {exc}",
  3674	            )
  3675	
  3676	        stderr_tail = "\n".join(
  3677	            (proc.stderr or "").rstrip().splitlines()[-40:]
  3678	        )
  3679	        passed = proc.returncode == self.smoke_expected_exit
  3680	        if passed:
  3681	            logger.info("Runtime-parity check passed: %s", command)
  3682	        else:
  3683	            logger.warning(
  3684	                "Runtime-parity check FAILED (exit=%d, expected=%d): %s\n"
  3685	                "stderr (tail):\n%s",
  3686	                proc.returncode, self.smoke_expected_exit, command,
  3687	                stderr_tail or "(empty)",
  3688	            )
  3689	        return RuntimeParityResult(
  3690	            ran=True,
  3691	            passed=passed,
  3692	            command=command,
  3693	            exit_code=proc.returncode,
  3694	            expected_exit=self.smoke_expected_exit,
  3695	            timed_out=False,
  3696	            stderr_tail=stderr_tail,
  3697	            # 2026-07-04 code review: pytest FAILED summaries live on stdout;
  3698	            # carry the combined tail so the parity guard can name the failing
  3699	            # tests (stderr_tail semantics untouched — additive only).
  3700	            output_tail=_combined_output_tail(proc.stdout, proc.stderr),
  3701	        )
  3702	
  3703	    def _compute_agent_invocations_advisory(
  3704	        self, task_work_results: Dict[str, Any],
  3705	    ) -> Optional[Dict[str, Any]]:
  3706	        """Compute the non-blocking agent-invocations advisory issue.
  3707	
  3708	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  3709	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  3710	        Part A). Returns ``None`` when no advisory is needed.
  3711	
  3712	        The logic mirrors the inline computation in ``validate()``: a
  3713	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  3714	        produces a ``severity == "warning"`` advisory naming the missing
  3715	        phases and recommending stack-specific specialists. ``"passed"``,
  3716	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  3717	        on — they ride through without comment.
  3718	        """
  3719	        agent_invocations_validation = task_work_results.get(
  3720	            "agent_invocations_validation"
  3721	        )
  3722	        if not (
  3723	            isinstance(agent_invocations_validation, dict)
  3724	            and agent_invocations_validation.get("status") == "violation"
  3725	        ):
  3726	            return None
  3727	
  3728	        raw_missing = agent_invocations_validation.get("missing_phases") or []
  3729	        missing_phases: List[str] = []
  3730	        if raw_missing and isinstance(raw_missing[0], dict):
  3731	            missing_phases = [
  3732	                str(m.get("phase", ""))
  3733	                for m in raw_missing
  3734	                if m.get("phase")
  3735	            ]
  3736	        else:
  3737	            missing_phases = [str(m) for m in raw_missing]
  3738	        missing_phases_sorted = sorted(missing_phases)
  3739	        missing_phases_with_names = ", ".join(
  3740	            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  3741	            for p in missing_phases_sorted
  3742	        ) if missing_phases_sorted else "unknown"
  3743	
  3744	        stack_template = detect_stack_template(self.worktree_path)
  3745	        specialist_lines = render_missing_phase_list(
  3746	            missing_phases_sorted,
  3747	            stack_template=stack_template,
  3748	            workspace_root=self.worktree_path,
  3749	        )
  3750	        specialist_block = "\n".join(
  3751	            f"- {line}" for line in specialist_lines
  3752	        )
  3753	
  3754	        expected_phases_val = agent_invocations_validation.get("expected_phases")
  3755	        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
  3756	        expected_str = (
  3757	            str(expected_phases_val) if expected_phases_val is not None else "?"
  3758	        )
  3759	        actual_str = (
  3760	            str(actual_invocations_val)
  3761	            if actual_invocations_val is not None
  3762	            else "?"
  3763	        )
  3764	
  3765	        return {
  3766	            "severity": "warning",
  3767	            "category": "agent_invocations_advisory",
  3768	            "description": (
  3769	                f"Advisory (non-blocking): task-work produced a report with "
  3770	                f"{actual_str} of {expected_str} expected agent invocations. "
  3771	                f"Missing phases: {missing_phases_with_names}. "
  3772	                f"Consider invoking these agents via the Task tool to "
  3773	                f"strengthen stack-specific quality:\n{specialist_block}"
  3774	            ),
  3775	            "details": {
  3776	                "missing_phases": missing_phases_sorted,
  3777	                "expected_phases": expected_phases_val,
  3778	                "actual_invocations": actual_invocations_val,
  3779	            },
  3780	        }
  3781	
  3782	    def _compute_specialist_failure_advisories(
  3783	        self, task_work_results: Dict[str, Any],
  3784	    ) -> List[Dict[str, Any]]:
  3785	        """Surface orchestrator-injected specialist failures as advisories.
  3786	
  3787	        TASK-FIX-SPECVIOL01 AC-002. When an orchestrator-invoked specialist
  3788	        (Phase 4 test-orchestrator, Phase 5 code-reviewer) hangs or crashes,
  3789	        ``AgentInvoker._inject_specialist_records_into_task_work_results``
  3790	        writes a ``source: "orchestrator"`` record with ``status`` failed/
  3791	        skipped and an ``error`` into ``agent_invocations``. That is a
  3792	        SUBSTRATE failure — the Player never controlled it — so it must
  3793	        surface as an attributed, non-blocking advisory naming the
  3794	        specialist and the error, never as a Player honesty discrepancy
  3795	        (the path-string-mismatch-is-not-dishonesty meta-class) and never
  3796	        silently dropped (absence of evidence stays absent-signal, per
  3797	        absence-of-failure-is-not-success).
  3798	
  3799	        Only ``status == "failed"`` records advise. ``"skipped"`` records
  3800	        are also synthesized benignly (e.g. direct-mode tasks where
  3801	        ``specialist_results.json`` legitimately never exists) and the
  3802	        phase-absence signal is already carried by the agent-invocations
  3803	        advisory — advising on them would be per-turn noise.
  3804	
  3805	        Returns an empty list when no orchestrator-sourced failure records
  3806	        are present (the overwhelmingly common case).
  3807	        """
  3808	        advisories: List[Dict[str, Any]] = []
  3809	        invocations = task_work_results.get("agent_invocations")
  3810	        if not isinstance(invocations, list):
  3811	            return advisories
  3812	        for inv in invocations:
  3813	            if not isinstance(inv, dict):
  3814	                continue
  3815	            if inv.get("source") != "orchestrator":
  3816	                continue
  3817	            if inv.get("status") != "failed":
  3818	                continue
  3819	            error = inv.get("error")
  3820	            if not error:
  3821	                continue
  3822	            agent = inv.get("agent", "unknown-specialist")
  3823	            phase = inv.get("phase", "?")
  3824	            advisories.append({
  3825	                "severity": "should_fix",
  3826	                "category": "specialist_substrate",
  3827	                "description": (
  3828	                    f"Orchestrator-invoked specialist '{agent}' "
  3829	                    f"(Phase {phase}) did not produce evidence: {error}. "
  3830	                    f"This is a substrate failure attributed to the "
  3831	                    f"orchestrator, not a Player honesty issue — the "
  3832	                    f"phase's evidence is ABSENT, not failed."
  3833	                ),
  3834	                "details": {
  3835	                    "phase": phase,
  3836	                    "agent": agent,
  3837	                    "status": inv.get("status"),
  3838	                    "error": str(error),
  3839	                },
  3840	            })
  3841	        return advisories
  3842	
  3843	    def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
  3844	        """
  3845	        Read quality gate results from task-work execution.
  3846	
  3847	        Looks for results in the standard location:
  3848	        `.guardkit/autobuild/{task_id}/task_work_results.json`
  3849	
  3850	        Parameters
  3851	        ----------
  3852	        task_id : str
  3853	            Task identifier
  3854	
  3855	        Returns
  3856	        -------
  3857	        Dict[str, Any]
  3858	            Task-work results, or dict with "error" key if not found
  3859	        """
  3860	        results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
  3861	        logger.debug(f"Looking for task_work_results at: {results_path}")
  3862	
  3863	        if not results_path.exists():
  3864	            logger.warning(f"task_work_results.json not found at {results_path}")
  3865	            logger.debug(f"Worktree path: {self.worktree_path}")
  3866	            logger.debug(f"Task ID: {task_id}")
  3867	            return {"error": f"Task-work results not found at {results_path}"}
  3868	
  3869	        try:
  3870	            with open(results_path) as f:
  3871	                results = json.load(f)
  3872	            logger.debug(f"Successfully loaded task_work_results from {results_path}")
  3873	            return results
  3874	        except json.JSONDecodeError as e:
  3875	            logger.error(f"Failed to parse task-work results: {e}")
  3876	            return {"error": f"Failed to parse task-work results: {e}"}
  3877	        except Exception as e:
  3878	            logger.error(f"Failed to read task-work results: {e}")
  3879	            return {"error": f"Failed to read task-work results: {e}"}
  3880	
  3881	    def run_evidence_repo_tests(self) -> List[EvidenceTestResult]:
  3882	        """Run independent tests in every declared sibling repo (AC-002).
  3883	
  3884	        Trust-but-verify for sibling-repo deliverables: each declared repo's
  3885	        ``test_command`` runs in that repo's root under the same interpreter
  3886	        Coach pins for worktree tests. Returns one
  3887	        :class:`EvidenceTestResult` per declared repo (empty list when no
  3888	        sibling repos are declared). The orchestrator attaches these to the
  3889	        evidence bundle and blocks the turn on a failed/unrunnable suite via
  3890	        :func:`evidence_repos.evidence_repo_tests_blocking_reason`.
  3891	        """
  3892	        if not self._evidence_repos:
  3893	            return []
  3894	        venv = str(self._venv_python) if self._venv_python is not None else None
  3895	        results = evidence_repos_lib.run_all_repo_tests(
  3896	            self._evidence_repos,
  3897	            venv_python=venv,
  3898	            timeout=self.test_timeout,
  3899	        )
  3900	        for r in results:
  3901	            logger.info(
  3902	                "Evidence-repo tests for %s: ran=%s passed=%s rc=%s",
  3903	                r.repo_name,
  3904	                r.ran,
  3905	                r.passed,
  3906	                r.returncode,
  3907	            )
  3908	        return results
  3909	
  3910	    def verify_quality_gates(
  3911	        self,
  3912	        task_work_results: Dict[str, Any],
  3913	        profile: Optional[QualityGateProfile] = None,
  3914	        skip_arch_review: bool = False,
  3915	    ) -> QualityGateStatus:
  3916	        """
  3917	        Verify task-work quality gates passed.
  3918	
  3919	        Checks the following gates from task-work results, respecting the quality
  3920	        gate profile which determines which gates are required for the task type:
  3921	        - tests_passed: From Phase 4.5 test results
  3922	        - coverage_met: From Phase 4.5 coverage check
  3923	        - arch_review_passed: From Phase 5 code review (score >= threshold)
  3924	        - plan_audit_passed: From Phase 5.5 plan audit (0 violations)
  3925	
  3926	        Parameters
  3927	        ----------
  3928	        task_work_results : Dict[str, Any]
  3929	            Results from task-work execution
  3930	        profile : Optional[QualityGateProfile]
  3931	            Quality gate profile for task type. If None, uses FEATURE profile
  3932	            (backward compatible with existing calls without profile parameter).
  3933	        skip_arch_review : bool
  3934	            If True, skip architectural review gate regardless of profile setting.
  3935	            Used for --implement-only mode where Phase 2.5B doesn't run.
  3936	            Default: False (enforce arch review per profile).
  3937	
  3938	        Returns
  3939	        -------
  3940	        QualityGateStatus

