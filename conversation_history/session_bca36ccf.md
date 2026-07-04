## Summarized at 2026-07-04T22:24:03.791770+00:00

AI: [{'name': 'grep', 'args': {'pattern': 'tests/acceptance/*_roundtrip.py'}, 'id': 'pJlufTrPUXi4Vup84lr2R01yAaI3Tbw8', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.guardkit/autobuild/TASK-QAV-006/player_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/.guardkit/autobuild/TASK-QAV-006/task_work_results.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/conversation_history/session_f5b16fc7.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/features/qav-behavioural-gates/qav-behavioural-gates_assumptions.yaml
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/agent_invoker.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tasks/backlog/qav-behavioural-gates/TASK-QAV-004-behavioural-roundtrip-oracle.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tasks/backlog/qav-l4-producer/TASK-QAV-006-wire-behavioural-oracle-producer.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tasks/design_approved/TASK-QAV-006-wire-behavioural-oracle-producer.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/tests/orchestrator/test_behavioural_oracle_producer.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': '358qCBVtSuw4dQC0ydzzPxOfqj7gzZom', 'type': 'tool_call'}]
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 100}, 'id': 'eUAVbrpAsCoVHhPeHn95EB1WOR64U855', 'type': 'tool_call'}]
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 600}, 'id': 'MgkEbEakPfutH1pSFz8tkFIAMvVmwGyd', 'type': 'tool_call'}]
Tool:    601	    _WIRING_FACTORY_AVAILABLE = True
   602	except ImportError:
   603	    analyze_stub_scan = None  # type: ignore[misc,assignment]
   604	    analyze_wiring = None  # type: ignore[misc,assignment]
   605	    _WIRING_FACTORY_AVAILABLE = False
   606	
   607	def _is_wiring_factory_available() -> bool:
   608	    """Return True when the guardkitfactory wiring analyzer is importable.
   609	
   610	    A plain module-level check (the import happens once at module load);
   611	    kept as a function so tests can patch availability.
   612	    """
   613	    return _WIRING_FACTORY_AVAILABLE and analyze_wiring is not None
   614	
   615	
   616	def _reset_wiring_factory_cache() -> None:
   617	    """Kept for call-site compatibility; availability is no longer cached."""
   618	    return None
   619	
   620	
   621	def _compute_authored_set(
   622	    task_work_results: Dict[str, Any],
   623	) -> List[str]:
   624	    """Compute the set of source files authored by the Player this turn.
   625	
   626	    Uses the presence-based fallback from the task-work results:
   627	    ``files_authored`` when present, else ``files_created ∪ files_modified``.
   628	
   629	    This is NOT the git-enriched ``files_modified`` (which can be
   630	    peer-contaminated in parallel-wave execution).
   631	
   632	    Parameters
   633	    ----------
   634	    task_work_results : Dict[str, Any]
   635	        The task-work results dict from ``read_quality_gate_results``.
   636	
   637	    Returns
   638	    -------
   639	    List[str]
   640	        List of authored file paths (relative to worktree root).
   641	    """
   642	    if "files_authored" in task_work_results and isinstance(
   643	        task_work_results["files_authored"], list
   644	    ):
   645	        # Presence-based: an explicit empty list is authoritative (the
   646	        # Player authored nothing), NOT a trigger for the fallback union.
   647	        return [str(f) for f in task_work_results["files_authored"]]
   648	
   649	    # Fallback: files_created ∪ files_modified
   650	    created = task_work_results.get("files_created") or []
   651	    modified = task_work_results.get("files_modified") or []
   652	    authored: List[str] = []
   653	    seen: set = set()
   654	    for f in list(created) + list(modified):
   655	        fs = str(f)
   656	        if fs not in seen:
   657	            seen.add(fs)
   658	            authored.append(fs)
   659	    return authored
   660	
   661	
   662	def _compute_spec_gap(
   663	    bdd_dict: Optional[Dict[str, Any]],
   664	    worktree_path: Path,
   665	    task_id: str,
   666	) -> Dict[str, Any]:
   667	    """Compute the SPEC_GAP evidence for the given BDD run result.
   668	
   669	    Detects a ``@task:<TASK-ID>``-tagged Gherkin scenario that is ground truth
   670	    (declared in a ``features/**/*.feature`` file) but has no executed binding.
   671	
   672	    AC-011: Per-scenario gap — a named tagged scenario absent from the executed
   673	    set produces one advisory ``spec_gap`` finding.
   674	
   675	    AC-012: When ``scenarios_attempted`` is **absent** from the BDD dict,
   676	    ``whole_file_deselection`` is ``False`` and the hard gate does NOT fire.
   677	    Absent = UNKNOWN, never coerced to 0.
   678	
   679	    AC-013: When ``scenarios_attempted`` is present and zero while
   680	    ``ground_truth_count > 0``, ``whole_file_deselection`` is ``True``.
   681	
   682	    AC-022: When ``bdd.discover(stack)`` returns ``None`` (unsupported stack),
   683	    ``status`` is ``"unsupported_stack"`` and the guard does not fire.
   684	
   685	    Parameters
   686	    ----------
   687	    bdd_dict : Optional[Dict[str, Any]]
   688	        The ``bundle.bdd``-shaped dict (from factory or player-reported).
   689	        ``None`` means no BDD evidence at all.
   690	    worktree_path : Path
   691	        Root of the worktree (for scanning feature files).
   692	    task_id : str
   693	        The task identifier (e.g. ``"TASK-QAWE-004"``) used to match
   694	        ``@task:<TASK-ID>`` tags in feature files.
   695	
   696	    Returns
   697	    -------
   698	    Dict[str, Any]
   699	        A spec_gap dict with keys: ``status``, ``ground_truth_count``,
   700	        ``executed_count``, ``pending_count``, ``findings``,
   701	        ``whole_file_deselection``, ``bdd_plugin_name``,
   702	        ``executed_evidence``.
   703	    """
   704	    # --- Ground truth: scan feature files for @task:<TASK-ID> tags ---
   705	    ground_truth_count = 0
   706	    # (feature_file, scenario_name) tuples — tuples, not joined strings, so
   707	    # scenario names containing ":" never mis-split downstream.
   708	    ground_truth_scenarios: List[tuple] = []
   709	
   710	    features_dir = worktree_path / "features"
   711	    if features_dir.is_dir():
   712	        for feature_file in features_dir.rglob("*.feature"):
   713	            try:
   714	                content = feature_file.read_text(encoding="utf-8")
   715	            except OSError:
   716	                continue
   717	
   718	            # Track tag block context: tags accumulate until a Scenario line.
   719	            # After a Scenario line, reset so the next tag block is captured.
   720	            tag_block: List[str] = []
   721	
   722	            for line in content.splitlines():
   723	                stripped = line.strip()
   724	
   725	                # Tag lines start with @
   726	                if stripped.startswith("@"):
   727	                    tag_block.append(stripped)
   728	                    continue
   729	
   730	                # Scenario line ends the tag block
   731	                if re.match(r"^\s*(Scenario:|Scenario Outline:)", line):
   732	                    # Ground truth is THIS task's scenarios ONLY: an exact
   733	                    # @task:<TASK-ID> token match. Counting other tasks'
   734	                    # @task: tags would inflate ground_truth_count and
   735	                    # false-fire the whole-file hard gate for a task that
   736	                    # legitimately owns zero scenarios (parallel-wave
   737	                    # features). Tag lines may carry multiple tags
   738	                    # ("@task:X @smoke"), so match TOKENS, not whole lines.
   739	                    task_tag = f"@task:{task_id}"
   740	                    tag_tokens = {
   741	                        token
   742	                        for tag_line in tag_block
   743	                        for token in tag_line.split()
   744	                    }
   745	                    if task_tag in tag_tokens:
   746	                        match = re.search(
   747	                            r"(Scenario Outline:|Scenario:)\s+(.+)", line
   748	                        )
   749	                        if match:
   750	                            scenario_name = match.group(2).strip()
   751	                            ground_truth_count += 1
   752	                            ground_truth_scenarios.append((
   753	                                str(feature_file.relative_to(worktree_path)),
   754	                                scenario_name,
   755	                            ))
   756	                    tag_block = []
   757	                    continue
   758	
   759	                # Any other non-empty line ends the tag block
   760	                if stripped and not stripped.startswith("#"):
   761	                    tag_block = []
   762	
   763	    # --- Executed evidence: consume from BDDRunResult ---
   764	    executed_count = 0
   765	    pending_count = 0
   766	    whole_file_deselection = False
   767	    status = "complete"
   768	    executed_evidence: str = "counts_only"
   769	    bdd_plugin_name: Optional[str] = None
   770	
   771	    if bdd_dict is not None and isinstance(bdd_dict, dict):
   772	        # AC-012: Check if scenarios_attempted key is PRESENT (not absent)
   773	        # Use "in" check, NOT .get(..., 0) — absent = UNKNOWN
   774	        if "scenarios_attempted" in bdd_dict:
   775	            executed_count = bdd_dict.get("scenarios_attempted", 0) or 0
   776	            pending_count = bdd_dict.get("scenarios_pending", 0) or 0
   777	
   778	            # AC-013: whole-file deselection when ground_truth > 0 and
   779	            # scenarios_attempted is present and zero
   780	            if ground_truth_count > 0 and executed_count == 0:
   781	                whole_file_deselection = True
   782	
   783	        # Determine executed_evidence level
   784	        if "executed_scenarios" in bdd_dict:
   785	            executed_evidence = "full"
   786	        elif "scenarios_attempted" in bdd_dict:
   787	            executed_evidence = "counts_only"
   788	        else:
   789	            executed_evidence = "partial"
   790	
   791	        bdd_plugin_name = bdd_dict.get("bdd_plugin_name")
   792	    else:
   793	        # No BDD evidence at all — unsupported_stack status
   794	        status = "unsupported_stack"
   795	        executed_evidence = "counts_only"
   796	
   797	    # --- Per-scenario findings (AC-011) ---
   798	    # When executed_evidence is "full", we can compare per-scenario
   799	    findings: List[Dict[str, Any]] = []
   800	    if executed_evidence == "full" and ground_truth_scenarios:
   801	        executed_names = set(
   802	            s.get("name", "")
   803	            for s in bdd_dict.get("executed_scenarios", [])  # type: ignore[union-attr]
   804	            if isinstance(s, dict)
   805	        )
   806	        for gt_file, scenario_name in ground_truth_scenarios:
   807	            # Substring match: name-matching carries FP risk, hence advisory.
   808	            if not any(scenario_name in en for en in executed_names):
   809	                findings.append({
   810	                    "feature_file": gt_file,
   811	                    "symbol": scenario_name,
   812	                    "severity": "warning",
   813	                    "pattern": "SPEC_GAP",
   814	                    "why": f"Tagged scenario '{scenario_name}' declared in ground truth but not found in executed set",
   815	                })
   816	
   817	    return {
   818	        "status": status,
   819	        "ground_truth_count": ground_truth_count,
   820	        "executed_count": executed_count,
   821	        "pending_count": pending_count,
   822	        "findings": findings,
   823	        "whole_file_deselection": whole_file_deselection,
   824	        "bdd_plugin_name": bdd_plugin_name,
   825	        "executed_evidence": executed_evidence,
   826	    }
   827	
   828	
   829	def _run_wiring_analysis(
   830	    worktree_path: Path,
   831	    authored_files: List[str],
   832	    task_type: str,
   833	    stack_template: Optional[str],
   834	    bdd_dict: Optional[Dict[str, Any]] = None,
   835	    task_id: str = "",
   836	) -> Optional[Dict[str, Any]]:
   837	    """Run the wiring analysis for the authored files.
   838	
   839	    Returns a dict with ``wiring``, ``mocked_seam``, and ``spec_gap`` keys
   840	    (some may be ``None``). Returns ``None`` when the task type gates out
   841	    (SCAFFOLDING/DOCUMENTATION) or there are no authored source targets.
   842	
   843	    For the MOCKED_SEAM probe specifically:
   844	    - When authored files exist but no acceptance files are present,
   845	      returns a dict with ``mocked_seam`` set to ``ran: false`` + ``skip_reason``.
   846	    - When acceptance files are present, the factory runs the scan.
   847	
   848	    Parameters
   849	    ----------
   850	    worktree_path : Path
   851	        Root of the worktree.
   852	    authored_files : List[str]
   853	        Source files authored this turn.
   854	    task_type : str
   855	        Resolved task type (e.g. ``"feature"``, ``"scaffolding"``).
   856	    stack_template : Optional[str]
   857	        Detected stack template (e.g. ``"python"``, ``"fastapi-python"``).
   858	    bdd_dict : Optional[Dict[str, Any]]
   859	        The ``bundle.bdd``-shaped dict for SPEC_GAP computation.
   860	    task_id : str
   861	        Task identifier for SPEC_GAP tag matching.
   862	
   863	    Returns
   864	    -------
   865	    Optional[Dict[str, Any]]
   866	        Dict with ``wiring``, ``mocked_seam``, ``spec_gap`` keys, or ``None``
   867	        when the probe legitimately did not run.
   868	    """
   869	    # Positive task-type gate (scope §4): only FEATURE / REFACTOR /
   870	    # INTEGRATION are analyzed. Everything else (scaffolding, documentation,
   871	    # testing, infrastructure, …) legitimately produces un-wired stubs →
   872	    # all three fields None. Case-insensitive: frontmatter uses lowercase.
   873	    if (task_type or "").upper() not in ("FEATURE", "REFACTOR", "INTEGRATION"):
   874	        logger.debug(
   875	            "wiring analysis: task_type=%s gates out; "
   876	            "all three fields left as None.",
   877	            task_type,
   878	        )
   879	        return None
   880	
   881	    # Zero-authored-targets gate → None (probe legitimately did not run).
   882	    if not authored_files:
   883	        logger.debug(
   884	            "wiring analysis: no authored source targets; "
   885	            "all three fields left as None.",
   886	        )
   887	        return None
   888	
   889	    # Factory unavailable → all fields None (graceful import absence,
   890	    # AC-017). Checked before any other work so factory-absent behaviour
   891	    # is uniform regardless of authored-file composition.
   892	    if not _is_wiring_factory_available() or analyze_wiring is None:
   893	        logger.debug(
   894	            "wiring analysis: guardkitfactory.wiring not available; "
   895	            "all three fields left as None.",
   896	        )
   897	        return None
   898	
   899	    # Resolve the stack hint. analyze_wiring reads ``stack.language``
   900	    # (scope §5.5: StackProfile | None) — a bare string would be silently
   901	    # dropped, so wrap it in a namespace object.
   902	    stack_language = (
   903	        _STACK_PROFILE_MAP.get(stack_template) if stack_template else None
   904	    )
   905	    stack_obj = (
   906	        SimpleNamespace(language=stack_language) if stack_language else None
   907	    )
   908	
   909	    try:
   910	        result = analyze_wiring(
   911	            authored_files=authored_files,
   912	            worktree_path=worktree_path,
   913	            task_type=task_type,
   914	            stack=stack_obj,
   915	        )
   916	        # analyze_wiring returns None (probe didn't run), or the §5.1
   917	        # wiring shape FLAT at top level with the MOCKED_SEAM result
   918	        # nested under "mocked_seam" (acceptance-file selection, skip
   919	        # statuses, and the UNWIRED/MOCKED probe independence all live
   920	        # in the factory — guardkit does not re-implement them).
   921	        if result is None:
   922	            return None
   923	        if not isinstance(result, dict):
   924	            logger.warning(
   925	                "wiring analysis returned unexpected type %s; "
   926	                "all three fields left as None.",
   927	                type(result).__name__,
   928	            )
   929	            return None
   930	        # Normalize into the three-field envelope gather_evidence consumes.
   931	        # pop() keeps bundle.wiring free of the nested mocked_seam copy.
   932	        mocked_seam = result.pop("mocked_seam", None)
   933	        if isinstance(mocked_seam, dict) and "external_mocks_ignored" not in mocked_seam:
   934	            # TASK-QAWE-003 AC-006: the field is always present downstream.
   935	            mocked_seam["external_mocks_ignored"] = []
   936	        # Wave-3 (TASK-QAWE-004): compute spec_gap from BDDRunResult.
   937	        spec_gap_dict = _compute_spec_gap(
   938	            bdd_dict=bdd_dict,
   939	            worktree_path=worktree_path,
   940	            task_id=task_id,
   941	        )
   942	        return {
   943	            "wiring": result,
   944	            "mocked_seam": mocked_seam,
   945	            "spec_gap": spec_gap_dict,
   946	        }
   947	    except Exception as exc:  # noqa: BLE001 — analyzer errors must not break gathering
   948	        logger.warning(
   949	            "wiring analysis raised %s; all three fields left as None.",
   950	            exc.__class__.__name__,
   951	        )
   952	        return None
   953	
   954	
   955	def _compute_stub_scan(
   956	    worktree_path: Path,
   957	    authored_files: List[str],
   958	    task_type: str,
   959	) -> Optional[Dict[str, Any]]:
   960	    """Run the L2 anti-stub scan for the authored files.
   961	
   962	    Returns a dict with ``status``, ``findings``, and ``symbols_examined`` keys
   963	    (some may be ``None``). Returns ``None`` when the task type gates out
   964	    (SCAFFOLDING/DOCUMENTATION) or there are no authored source targets.
   965	
   966	    Uses the same lazy-import seam as the wiring analysis: when
   967	    ``guardkitfactory.wiring.analyze_stub_scan`` is unavailable, all three
   968	    fields (``stub_scan``, ``coverage``, ``behavioural_oracle``) stay ``None``.
   969	
   970	    Parameters
   971	    ----------
   972	    worktree_path : Path
   973	        Root of the worktree.
   974	    authored_files : List[str]
   975	        Source files authored this turn.
   976	    task_type : str
   977	        Resolved task type (e.g. ``"feature"``, ``"scaffolding"``).
   978	
   979	    Returns
   980	    -------
   981	    Optional[Dict[str, Any]]
   982	        Dict with ``status``, ``findings``, ``symbols_examined`` keys, or
   983	        ``None`` when the probe legitimately did not run.
   984	    """
   985	    # Positive task-type gate (same as wiring): only FEATURE / REFACTOR /
   986	    # INTEGRATION are scanned. Everything else produces None.
   987	    if (task_type or "").upper() not in ("FEATURE", "REFACTOR", "INTEGRATION"):
   988	        logger.debug(
   989	            "stub_scan: task_type=%s gates out; "
   990	            "all three fields left as None.",
   991	            task_type,
   992	        )
   993	        return None
   994	
   995	    # Zero-authored-targets gate → None.
   996	    if not authored_files:
   997	        logger.debug(
   998	            "stub_scan: no authored source targets; "
   999	            "all three fields left as None.",
  1000	        )
  1001	        return None
  1002	
  1003	    # Factory unavailable → None (graceful import absence).
  1004	    if not _is_wiring_factory_available() or analyze_stub_scan is None:
  1005	        logger.debug(
  1006	            "stub_scan: guardkitfactory.wiring not available; "
  1007	            "all three fields left as None.",
  1008	        )
  1009	        return None
  1010	
  1011	    try:
  1012	        result = analyze_stub_scan(
  1013	            authored_files=authored_files,
  1014	            worktree_path=worktree_path,
  1015	            task_type=task_type,
  1016	        )
  1017	        if result is None:
  1018	            return None
  1019	        if not isinstance(result, dict):
  1020	            logger.warning(
  1021	                "stub_scan returned unexpected type %s; "
  1022	                "all three fields left as None.",
  1023	                type(result).__name__,
  1024	            )
  1025	            return None
  1026	        return result
  1027	    except Exception as exc:  # noqa: BLE001 — analyzer errors must not break gathering
  1028	        logger.warning(
  1029	            "stub_scan raised %s; all three fields left as None.",
  1030	            exc.__class__.__name__,
  1031	        )
  1032	        return None
  1033	
  1034	
  1035	# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
  1036	# description. Filename-based detection (the soft gate at
  1037	# ``_check_seam_test_recommendation``) tolerates "integration" too, but the
  1038	# blocking gate requires explicit marker decoration so a plain integration test
  1039	# can't silently satisfy a contract obligation. Match the established marker
  1040	# precedent: `seam`, `contract`, `boundary`.
  1041	_SEAM_PYTEST_MARKERS = ("seam", "contract", "boundary")
  1042	
  1043	# Header pattern: any markdown header level (`#` to `######`) whose title is
  1044	# exactly "Seam Tests" (case-insensitive, trailing whitespace allowed). The
  1045	# closing `$` plus `re.MULTILINE` matches the header line in isolation so we
  1046	# don't false-trigger on prose like "## Seam Tests are useful because…".
  1047	_SEAM_TESTS_HEADER_RE = re.compile(
  1048	    r"^\s*#{1,6}\s+seam\s+tests\s*$",
  1049	    re.IGNORECASE | re.MULTILINE,
  1050	)
  1051	
  1052	
  1053	def _extract_seam_tests_section(description: Optional[str]) -> Optional[str]:
  1054	    """Extract the body of a ``## Seam Tests`` markdown section.
  1055	
  1056	    Returns the section body (everything between the ``## Seam Tests`` header
  1057	    and the next sibling-or-higher header, or EOF) when the section exists
  1058	    AND has non-whitespace content. Returns ``None`` for any of:
  1059	
  1060	    * ``description`` is empty / None
  1061	    * No ``Seam Tests`` header is present
  1062	    * The header exists but the body is whitespace-only (empty stub block)
  1063	
  1064	    The "non-empty body" rule is what TASK-FIX-A7B4 AC-001 calls "precise"
  1065	    detection: a developer who wants to acknowledge "no seam tests for this
  1066	    task" can leave the section empty (or omit it) without tripping the gate.
  1067	    """
  1068	    if not description:
  1069	        return None
  1070	    match = _SEAM_TESTS_HEADER_RE.search(description)
  1071	    if not match:
  1072	        return None
  1073	    # Find the level of the matched header so we know what closes the section.
  1074	    header_line = match.group(0)
  1075	    header_level = len(header_line.lstrip().split(" ", 1)[0])  # count of '#'
  1076	
  1077	    # Body starts after the header line.
  1078	    body_start = match.end()
  1079	    rest = description[body_start:]
  1080	    # The section closes at the next header of equal-or-higher level.
  1081	    closing_re = re.compile(
  1082	        rf"^\s*#{{1,{header_level}}}\s+\S",
  1083	        re.MULTILINE,
  1084	    )
  1085	    close_match = closing_re.search(rest)
  1086	    body = rest[: close_match.start()] if close_match else rest
  1087	    if not body.strip():
  1088	        return None
  1089	    return body
  1090	
  1091	
  1092	# Stopwords for keyword extraction in fuzzy text matching
  1093	STOPWORDS = {
  1094	    "the", "and", "is", "or", "a", "an", "for", "with", "to", "in", "of",
  1095	    "from", "by", "on", "at", "that", "this", "are", "be", "do", "have",
  1096	    "has", "as", "if", "can", "will", "would", "could", "should", "may",
  1097	    "must", "was", "were", "been", "but", "not", "no", "all", "some",
  1098	    "any", "more", "most", "only", "than", "then", "there", "their",
  1099	    "who", "which", "when", "where", "how",
  1100	}
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 1100}, 'id': 'qSBOzcd5UT3yjRNVuFs5ysq6iCZlJuJz', 'type': 'tool_call'}]
Tool:   1101	
  1102	# ============================================================================
  1103	# Data Models
  1104	# ============================================================================
  1105	
  1106	
  1107	@dataclass
  1108	class QualityGateStatus:
  1109	    """
  1110	    Status of individual quality gates from task-work execution.
  1111	
  1112	    Attributes
  1113	    ----------
  1114	    tests_passed : bool
  1115	        Whether all tests passed in Phase 4.5
  1116	    coverage_met : bool
  1117	        Whether coverage threshold was met
  1118	    arch_review_passed : bool
  1119	        Whether architectural review passed (score >= 60)
  1120	    plan_audit_passed : bool
  1121	        Whether plan audit had zero violations
  1122	    all_gates_passed : bool
  1123	        True only if ALL gates passed (computed)
  1124	    tests_required : bool
  1125	        Whether tests were required by task type profile
  1126	    coverage_required : bool
  1127	        Whether coverage was required by task type profile
  1128	    arch_review_required : bool
  1129	        Whether architectural review was required by task type profile
  1130	    plan_audit_required : bool
  1131	        Whether plan audit was required by task type profile
  1132	    """
  1133	
  1134	    # TASK-ABFIX-010 (W1): ``tests_passed`` is tri-state. ``True``/``False`` are
  1135	    # a ran-and-passed / ran-and-failed verdict; ``None`` (UNKNOWN) is an ABSENT
  1136	    # oracle signal (Coach test run timed out / produced no verdict). ``None``
  1137	    # is APPENDED to ``required_gates`` in ``__post_init__`` (not skipped), so
  1138	    # ``all([None, ...])`` is ``False`` and the gate does NOT auto-approve on an
  1139	    # absent signal; the checkpoint pollution tally reads ``None`` separately
  1140	    # (via to_dict) and does NOT count it as a failure. Skipping ``None`` would
  1141	    # let the OTHER gates approve despite absent tests — a gate-level
  1142	    # false-green. See ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
  1143	    tests_passed: Optional[bool]
  1144	    coverage_met: bool
  1145	    arch_review_passed: bool
  1146	    plan_audit_passed: bool
  1147	    tests_required: bool = True
  1148	    coverage_required: bool = True
  1149	    arch_review_required: bool = True
  1150	    plan_audit_required: bool = True
  1151	    all_gates_passed: bool = field(init=False)
  1152	
  1153	    def __post_init__(self):
  1154	        """Compute all_gates_passed from individual gate results and requirements."""
  1155	        # Only check gates that are required
  1156	        required_gates = []
  1157	        if self.tests_required:
  1158	            required_gates.append(self.tests_passed)
  1159	        if self.coverage_required:
  1160	            required_gates.append(self.coverage_met)
  1161	        if self.arch_review_required:
  1162	            required_gates.append(self.arch_review_passed)
  1163	        if self.plan_audit_required:
  1164	            required_gates.append(self.plan_audit_passed)
  1165	
  1166	        # All required gates must pass
  1167	        self.all_gates_passed = all(required_gates) if required_gates else True
  1168	
  1169	
  1170	# TASK-AB-SKIPVIS01: pytest per-outcome summary tokens, used ONLY to derive
  1171	# the advisory ``tests_skipped`` count. ``skipped`` stays excluded from any
  1172	# tests_run / tests_failed arithmetic — a skipped test executed no assertions
  1173	# (an ABSENT verdict, never a pass and never a failure).
  1174	_PYTEST_OUTCOME_TOKEN_RE = re.compile(
  1175	    r"(\d+)\s+(passed|failed|errors?|xpassed|xfailed|skipped)\b",
  1176	    re.IGNORECASE,
  1177	)
  1178	
  1179	
  1180	def _parse_tests_skipped(output: Optional[str]) -> Optional[int]:
  1181	    """Parse the advisory pytest ``skipped`` count from stdout/stderr.
  1182	
  1183	    TASK-AB-SKIPVIS01. Tri-state, absence-preserving
  1184	    (``.claude/rules/absence-must-survive-every-reconciliation-layer.md``):
  1185	
  1186	    * ``None`` — no recognisable pytest outcome token in ``output`` (empty,
  1187	      garbage, non-pytest runner): the skip count is UNKNOWN, never coerced
  1188	      to ``0``.
  1189	    * ``0`` — a summary parsed cleanly (>=1 outcome token) with no ``skipped``
  1190	      token: positively zero skips.
  1191	    * ``N`` — the summary reported ``N skipped``. ``max`` across matches
  1192	      tolerates pytest reprinting the summary.
  1193	
  1194	    Advisory only: no gate or verdict logic may read this value.
  1195	    """
  1196	    if not output:
  1197	        return None
  1198	    skipped: Optional[int] = None
  1199	    saw_outcome_token = False
  1200	    for match in _PYTEST_OUTCOME_TOKEN_RE.finditer(output):
  1201	        saw_outcome_token = True
  1202	        if match.group(2).lower() == "skipped":
  1203	            count = int(match.group(1))
  1204	            skipped = count if skipped is None else max(skipped, count)
  1205	    if skipped is not None:
  1206	        return skipped
  1207	    return 0 if saw_outcome_token else None
  1208	
  1209	
  1210	def _combined_output_tail(
  1211	    stdout: Optional[str], stderr: Optional[str], bound: int = 2000
  1212	) -> Optional[str]:
  1213	    """Combined stdout+stderr tail for ``RuntimeParityResult.output_tail``.
  1214	
  1215	    2026-07-04 code review (runtime-parity stdout gap): pytest writes its
  1216	    ``FAILED <nodeid>`` short-summary lines to STDOUT, so a stderr-only tail
  1217	    hides the failing-test names from the per-task parity guard's evidence
  1218	    extraction. Joins stdout first, then stderr (mirroring
  1219	    ``feature_orchestrator._build_smoke_feedback``'s combined_output), each
  1220	    stream bounded to its last *bound* chars. Returns ``None`` when neither
  1221	    stream produced output — consumers then fall back to ``stderr_tail``.
  1222	    """
  1223	    parts = [
  1224	        part.rstrip()[-bound:]
  1225	        for part in (stdout, stderr)
  1226	        if part and part.rstrip()
  1227	    ]
  1228	    return "\n".join(parts) or None
  1229	
  1230	
  1231	@dataclass
  1232	class IndependentTestResult:
  1233	    """
  1234	    Result of independent test verification.
  1235	
  1236	    Attributes
  1237	    ----------
  1238	    tests_passed : bool
  1239	        Whether tests passed when run independently
  1240	    test_command : str
  1241	        Command used to run tests
  1242	    test_output_summary : str
  1243	        Summary of test output
  1244	    duration_seconds : float
  1245	        Time taken to run tests
  1246	    raw_output : Optional[str]
  1247	        Full stdout+stderr from test execution, used for failure classification
  1248	    signal_absent : bool
  1249	        ``True`` when the independent-test oracle did NOT produce a verdict —
  1250	        the run timed out or failed at the transport layer (SDK timeout, SDK
  1251	        API error, subprocess/isolated-test timeout, or generic execution
  1252	        error) before pytest could report a pass/fail. This is distinct from
  1253	        "ran and failed" (``tests_passed=False`` with ``signal_absent=False``):
  1254	        an absent signal means the trust-but-verify leg never completed.
  1255	        ``tests_passed`` is always ``False`` when ``signal_absent`` is ``True``
  1256	        so the result can never read as a pass. The Coach's
  1257	        absence-of-failure guard (TASK-FIX-COACHTESTTO) treats an absent
  1258	        independent-test signal as ABSENT — surfaced as feedback, never
  1259	        approved on the Player's self-reported tests. See
  1260	        ``.claude/rules/absence-of-failure-is-not-success.md``.
  1261	    tests_skipped : Optional[int]
  1262	        Advisory pytest ``skipped`` count from the independent run. Tri-state:
  1263	        ``None`` = not parsed / unknown (never coerced to ``0``), ``0`` = the
  1264	        summary parsed cleanly with zero skips, ``N`` = N tests skipped. A
  1265	        skipped test is an ABSENT verdict, not a pass — a nonzero count may
  1266	        indicate missing optional extras in the worktree venv silently
  1267	        under-testing the deliverable. Advisory ONLY: no gate or verdict
  1268	        branch reads this field; it is surfaced to the Coach (evidence
  1269	        bundle / prompt) and the operator (``coach_turn_N.json``) for
  1270	        visibility.
  1271	    resolved_interpreter : Optional[str]
  1272	        The Python interpreter the independent pytest run was actually pinned
  1273	        to (``_pytest_interpreter()`` — the bootstrap venv when resolved,
  1274	        else ``sys.executable``). ``None`` when no interpreter-pinned run
  1275	        happened (non-pytest command, SDK/PATH execution, skipped run).
  1276	        Forensic evidence ONLY (TASK-AB-RESUMEVENV01 AC-003): no gate or
  1277	        verdict branch reads it — it makes the "which interpreter did the
  1278	        verifier actually run?" post-mortem a one-grep answer instead of a
  1279	        reproduction session (FEAT-ABL-005 run 4).
  1280	    """
  1281	
  1282	    tests_passed: bool
  1283	    test_command: str
  1284	    test_output_summary: str
  1285	    duration_seconds: float
  1286	    raw_output: Optional[str] = None
  1287	    signal_absent: bool = False
  1288	    # TASK-AB-SKIPVIS01: advisory skip-count visibility. None = unknown, never
  1289	    # 0-coerced; never joins any verdict / turn-rejecting / stall logic.
  1290	    tests_skipped: Optional[int] = None
  1291	    # TASK-AB-RESUMEVENV01: forensic interpreter evidence. None = no pinned
  1292	    # run; never read by any verdict / gate / stall logic.
  1293	    resolved_interpreter: Optional[str] = None
  1294	
  1295	
  1296	@dataclass
  1297	class CriterionResult:
  1298	    """
  1299	    Structured result for a single acceptance criterion.
  1300	
  1301	    Attributes
  1302	    ----------
  1303	    criterion_id : str
  1304	        Unique identifier (e.g., "AC-001")
  1305	    criterion_text : str
  1306	        Full text of the acceptance criterion
  1307	    result : str
  1308	        Verification result: "verified", "rejected", or "pending"
  1309	    status : str
  1310	        Alias for result, used by _count_criteria_passed consumer
  1311	    evidence : str
  1312	        Summary of what was checked to determine the result
  1313	    """
  1314	
  1315	    criterion_id: str
  1316	    criterion_text: str
  1317	    result: str  # "verified" | "rejected" | "pending"
  1318	    status: str  # same as result, for _count_criteria_passed compatibility
  1319	    evidence: str
  1320	
  1321	    def to_dict(self) -> Dict[str, Any]:
  1322	        """Convert to dictionary for JSON serialization."""
  1323	        return {
  1324	            "criterion_id": self.criterion_id,
  1325	            "criterion_text": self.criterion_text,
  1326	            "result": self.result,
  1327	            "status": self.status,
  1328	            "evidence": self.evidence,
  1329	            "notes": self.evidence,  # alias for _display_criteria_progress
  1330	        }
  1331	
  1332	
  1333	@dataclass
  1334	class RequirementsValidation:
  1335	    """
  1336	    Result of requirements satisfaction validation.
  1337	
  1338	    Attributes
  1339	    ----------
  1340	    criteria_total : int
  1341	        Total acceptance criteria count
  1342	    criteria_met : int
  1343	        Number of criteria met
  1344	    all_criteria_met : bool
  1345	        True if all criteria are met
  1346	    missing : List[str]
  1347	        List of missing/unmet criteria
  1348	    criteria_results : List[CriterionResult]
  1349	        Per-criterion structured verification results
  1350	    """
  1351	
  1352	    criteria_total: int
  1353	    criteria_met: int
  1354	    all_criteria_met: bool
  1355	    missing: List[str] = field(default_factory=list)
  1356	    criteria_results: List[CriterionResult] = field(default_factory=list)
  1357	
  1358	
  1359	@dataclass
  1360	class CoachValidationResult:
  1361	    """
  1362	    Complete result from Coach validation.
  1363	
  1364	    Attributes
  1365	    ----------
  1366	    task_id : str
  1367	        Task identifier
  1368	    turn : int
  1369	        Turn number
  1370	    decision : Literal["approve", "feedback"]
  1371	        Coach's decision
  1372	    quality_gates : Optional[QualityGateStatus]
  1373	        Quality gate status (None if results not found)
  1374	    independent_tests : Optional[IndependentTestResult]
  1375	        Independent test verification result
  1376	    requirements : Optional[RequirementsValidation]
  1377	        Requirements validation result
  1378	    issues : List[Dict[str, Any]]
  1379	        List of issues if feedback
  1380	    rationale : str
  1381	        Explanation of decision
  1382	    """
  1383	
  1384	    task_id: str
  1385	    turn: int
  1386	    decision: Literal["approve", "feedback", "deferred"]
  1387	    quality_gates: Optional[QualityGateStatus] = None
  1388	    independent_tests: Optional[IndependentTestResult] = None
  1389	    requirements: Optional[RequirementsValidation] = None
  1390	    issues: List[Dict[str, Any]] = field(default_factory=list)
  1391	    rationale: str = ""
  1392	    context_used: Optional[str] = None
  1393	    approved_without_independent_tests: bool = False
  1394	    is_configuration_error: bool = False
  1395	    environment_conditional_approval: bool = False
  1396	    # TASK-AB-FIX-INVAB1 AC-003: surface honesty verification result for
  1397	    # observability in coach_turn_N.json. None when verification was not
  1398	    # invoked (e.g. operator-handoff short-circuit, missing-results path).
  1399	    honesty_verification: Optional[HonestyVerification] = None
  1400	
  1401	    def to_dict(self) -> Dict[str, Any]:
  1402	        """
  1403	        Convert result to dictionary for JSON serialization.
  1404	
  1405	        Includes ``criteria_verification`` and ``acceptance_criteria_verification``
  1406	        fields consumed by ``_display_criteria_progress`` and ``_count_criteria_passed``
  1407	        in the AutoBuild orchestrator.
  1408	
  1409	        Returns
  1410	        -------
  1411	        Dict[str, Any]
  1412	            Dictionary representation suitable for JSON
  1413	        """
  1414	        # Build per-criterion results from requirements validation
  1415	        criteria_verification: List[Dict[str, Any]] = []
  1416	        acceptance_criteria_results: List[Dict[str, Any]] = []
  1417	        if self.requirements and self.requirements.criteria_results:
  1418	            criteria_verification = [
  1419	                cr.to_dict() for cr in self.requirements.criteria_results
  1420	            ]
  1421	            acceptance_criteria_results = [
  1422	                cr.to_dict() for cr in self.requirements.criteria_results
  1423	            ]
  1424	
  1425	        return {
  1426	            "task_id": self.task_id,
  1427	            "turn": self.turn,
  1428	            "decision": self.decision,
  1429	            "validation_results": {
  1430	                "quality_gates": {
  1431	                    "tests_passed": self.quality_gates.tests_passed,
  1432	                    "coverage_met": self.quality_gates.coverage_met,
  1433	                    "arch_review_passed": self.quality_gates.arch_review_passed,
  1434	                    "plan_audit_passed": self.quality_gates.plan_audit_passed,
  1435	                    "all_gates_passed": self.quality_gates.all_gates_passed,
  1436	                } if self.quality_gates else None,
  1437	                "independent_tests": {
  1438	                    "tests_passed": self.independent_tests.tests_passed,
  1439	                    "test_command": self.independent_tests.test_command,
  1440	                    "test_output_summary": self.independent_tests.test_output_summary,
  1441	                    "duration_seconds": self.independent_tests.duration_seconds,
  1442	                    # TASK-ABFIX-010 (W2): serialize signal_absent so the
  1443	                    # checkpoint's _extract_tests_passed (autobuild.py) can read
  1444	                    # an absent Coach-run signal and return None (UNKNOWN) rather
  1445	                    # than counting it as a failure. Without this the
  1446	                    # ``independent.get("signal_absent") is True`` guard there is
  1447	                    # dead on arrival for the Coach's own run.
  1448	                    "signal_absent": self.independent_tests.signal_absent,
  1449	                    # TASK-AB-SKIPVIS01: advisory skip count. Serialized even
  1450	                    # when None (unknown stays unknown — the ABFIX-010 lesson:
  1451	                    # a flag omitted from to_dict makes downstream reads dead).
  1452	                    "tests_skipped": self.independent_tests.tests_skipped,
  1453	                    # TASK-AB-RESUMEVENV01 (AC-003): forensic interpreter
  1454	                    # evidence. Serialized even when None (same ABFIX-010
  1455	                    # lesson — an omitted key makes downstream reads dead).
  1456	                    "resolved_interpreter": (
  1457	                        self.independent_tests.resolved_interpreter
  1458	                    ),
  1459	                } if self.independent_tests else None,
  1460	                "requirements": {
  1461	                    "criteria_total": self.requirements.criteria_total,
  1462	                    "criteria_met": self.requirements.criteria_met,
  1463	                    "all_criteria_met": self.requirements.all_criteria_met,
  1464	                    "missing": self.requirements.missing,
  1465	                } if self.requirements else None,
  1466	            },
  1467	            # For _display_criteria_progress (autobuild.py:2555)
  1468	            "criteria_verification": criteria_verification,
  1469	            # For _count_criteria_passed (autobuild.py:2254)
  1470	            "acceptance_criteria_verification": {
  1471	                "criteria_results": acceptance_criteria_results,
  1472	            },
  1473	            "issues": self.issues,
  1474	            "rationale": self.rationale,
  1475	            "context_used": self.context_used,
  1476	            "approved_without_independent_tests": self.approved_without_independent_tests,
  1477	            "is_configuration_error": self.is_configuration_error,
  1478	            "environment_conditional_approval": self.environment_conditional_approval,
  1479	            # TASK-AB-FIX-INVAB1 AC-003: mirror the LLM Coach honesty schema
  1480	            # (verified, honesty_score, discrepancy_count) — see
  1481	            # installer/core/agents/autobuild-coach.md:165-184.
  1482	            "honesty_verification": (
  1483	                {
  1484	                    "verified": self.honesty_verification.verified,
  1485	                    "honesty_score": self.honesty_verification.honesty_score,
  1486	                    "discrepancy_count": len(
  1487	                        self.honesty_verification.discrepancies
  1488	                    ),
  1489	                    # TASK-FIX-1B4A (Layer 1): expose state_bridge identity
  1490	                    # resolutions for audit. Empty list when no resolutions
  1491	                    # occurred (typical case) or wiring was absent.
  1492	                    "resolved_paths": [
  1493	                        {
  1494	                            "claimed": rp.claimed,
  1495	                            "resolved_to": rp.resolved_to,
  1496	                            "task_id": rp.task_id,
  1497	                        }
  1498	                        for rp in self.honesty_verification.resolved_paths
  1499	                    ],
  1500	                }
  1501	                if self.honesty_verification is not None
  1502	                else None
  1503	            ),
  1504	        }
  1505	
  1506	
  1507	# ============================================================================
  1508	# Coach Validator
  1509	# ============================================================================
  1510	
  1511	
  1512	class CoachValidator:
  1513	    """
  1514	    Lightweight Coach that validates task-work results.
  1515	
  1516	    This class does NOT reimplement quality gates - it reads task-work outputs
  1517	    and performs independent verification before making approve/feedback decision.
  1518	
  1519	    Validation Flow
  1520	    ---------------
  1521	    1. Read task-work results from JSON file
  1522	    2. Verify all quality gates passed
  1523	    3. Run independent test verification (trust but verify)
  1524	    4. Validate requirements satisfaction
  1525	    5. Return approve if all checks pass, feedback otherwise
  1526	
  1527	    Attributes
  1528	    ----------
  1529	    worktree_path : Path
  1530	        Path to the git worktree
  1531	    test_command : Optional[str]
  1532	        Command to run tests (auto-detected or specified)
  1533	    test_timeout : int
  1534	        Timeout for test execution in seconds
  1535	
  1536	    Example
  1537	    -------
  1538	    >>> validator = CoachValidator("/path/to/worktree")
  1539	    >>> result = validator.validate("TASK-001", 1, {"acceptance_criteria": [...]})
  1540	    >>> print(f"Decision: {result.decision}")
  1541	    """
  1542	
  1543	    # Quality gate thresholds (match task-work)
  1544	    ARCH_REVIEW_THRESHOLD = 60
  1545	    # Default profile for backward compatibility
  1546	    DEFAULT_PROFILE = get_profile(TaskType.FEATURE)
  1547	
  1548	    # High-confidence infrastructure patterns (safe for conditional approval)
  1549	    _INFRA_HIGH_CONFIDENCE: List[str] = [
  1550	        # Connection/network errors
  1551	        "ConnectionRefusedError",
  1552	        "ConnectionError",
  1553	        "Connection refused",
  1554	        "could not connect to server",
  1555	        # Database drivers
  1556	        "OperationalError",
  1557	        "psycopg2",
  1558	        "psycopg",
  1559	        "asyncpg",
  1560	        "sqlalchemy.exc.OperationalError",
  1561	        "django.db.utils.OperationalError",
  1562	        "pymongo.errors.ServerSelectionTimeoutError",
  1563	        "redis.exceptions.ConnectionError",
  1564	    ]
  1565	
  1566	    # SDK API error patterns — the LLM backend rejected the request (wrong model
  1567	    # name, invalid parameters, rate limits, etc.).  These are NOT code defects.
  1568	    _SDK_API_ERROR_PATTERNS: List[str] = [
  1569	        "SDK API error",
  1570	        "invalid_request",
  1571	        "invalid_request_error",
  1572	        "AssistantMessage.error",
  1573	    ]
  1574	
  1575	    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
  1576	    _INFRA_AMBIGUOUS: List[str] = [
  1577	        "ModuleNotFoundError",
  1578	        "ImportError",
  1579	        "No module named",
  1580	    ]
  1581	
  1582	    # Known service-client libraries whose absence indicates a missing dependency
  1583	    # install (not a code defect). ModuleNotFoundError for these is promoted to
  1584	    # high confidence.
  1585	    # NOTE: psycopg2 is intentionally excluded — projects using asyncpg may
  1586	    # accidentally import psycopg2, which is a Player code-choice error, not an
  1587	    # infrastructure failure.  Classifying it as ("infrastructure", "high") gave
  1588	    # the Player wrong advice (mock fixtures / SQLite) instead of telling them to
  1589	    # remove the wrong import.
  1590	    _KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
  1591	        "asyncpg",
  1592	        "pymongo",
  1593	        "redis",
  1594	        "psycopg",
  1595	        "sqlalchemy",
  1596	        "motor",
  1597	        "aioredis",
  1598	        "cassandra",
  1599	    ]
  1600	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 1600}, 'id': 'VgjYW860Hjs16Kbn1XEi1TskLNTd0a14', 'type': 'tool_call'}]
Tool:   1601	    # TASK-ABFIX-012: stack-agnostic HOST-SUBSTRATE gap signals. A test command
  1602	    # that could not run because a host tool is missing (the command itself, or a
  1603	    # tool a test shells out to — e.g. psql/docker/dotnet/npm/node). Routed to
  1604	    # ("infrastructure", "high") in ``_classify_test_failure`` AND to
  1605	    # ``signal_absent=True`` in ``run_independent_tests`` (via
  1606	    # ``_is_host_substrate_gap``), so a substrate-blocked TESTING task surfaces as
  1607	    # ABSENT / feedback (bounded by max_turns) — never a code-class block (the
  1608	    # false-red ABFIX-010 prevents) and never a false pass
  1609	    # (absence-of-failure-is-not-success). Stack-agnostic shell vocabulary, not
  1610	    # Python-specific. NOTE: the bare ": not found" / "no such file or directory"
  1611	    # idioms are intentionally EXCLUDED — they false-match legitimate code
  1612	    # failures ("key: not found", a test asserting FileNotFoundError), which would
  1613	    # mis-route a real bug to infrastructure and re-open a false-green. The
  1614	    # definitive rc-126/127 signal in ``_is_host_substrate_gap`` covers those.
  1615	    _HOST_SUBSTRATE_MISSING_PATTERNS: List[str] = [
  1616	        "command not found",
  1617	        "executable file not found",
  1618	        "is not recognized as an internal or external command",
  1619	    ]
  1620	
  1621	    # TASK-ABFIX-012: high-confidence OWN-CODE-BUG signals. A genuine Python
  1622	    # exception token in a TESTING task's own test output is a deterministic code
  1623	    # defect — a filesystem race (the contention ABFIX-005 amnesties) surfaces as
  1624	    # import / collection errors, not a clean AssertionError/AttributeError. Used
  1625	    # ONLY to neutralise the parallel-wave ``parallel_contention`` amnesty for
  1626	    # TESTING: a token match returns ("code", "high") regardless of wave_size, so a
  1627	    # real assertion failure is rejected in BOTH single and parallel waves. (Single
  1628	    # waves already classify ("code", "n/a") via the natural fallback, which the
  1629	    # guard also blocks.)
  1630	    _CODE_FAILURE_HIGH_CONFIDENCE: List[str] = [
  1631	        "assertionerror",
  1632	        "attributeerror",
  1633	        "has no attribute",
  1634	        "nameerror",
  1635	        "is not defined",
  1636	        "typeerror",
  1637	    ]
  1638	
  1639	    def __init__(
  1640	        self,
  1641	        worktree_path: str,
  1642	        test_command: Optional[str] = None,
  1643	        test_timeout: int = 300,
  1644	        task_id: Optional[str] = None,
  1645	        coach_test_execution: Optional[str] = None,
  1646	        matching_strategy: str = "auto",
  1647	        wave_size: int = 1,
  1648	        turn: int = 1,
  1649	        peer_changed_files: Optional[Dict[str, Any]] = None,
  1650	        model_name: Optional[str] = None,
  1651	        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
  1652	        venv_python: Optional[str] = None,  # TASK-FIX-COACHPYENV
  1653	        evidence_repos: Optional[List["EvidenceRepo"]] = None,  # TASK-AB-XREPOEV01
  1654	        smoke_command: Optional[str] = None,  # TASK-AB-COACHRUNPARITY01 (arm b)
  1655	        smoke_expected_exit: int = 0,  # TASK-AB-COACHRUNPARITY01 (arm b)
  1656	        basetemp_context: Optional[str] = None,  # TASK-AB-BASETEMP01
  1657	    ):
  1658	        """
  1659	        Initialize CoachValidator.
  1660	
  1661	        Parameters
  1662	        ----------
  1663	        worktree_path : str
  1664	            Path to the git worktree where validation should execute
  1665	        test_command : Optional[str]
  1666	            Command to run tests. If None, auto-detects based on project.
  1667	        test_timeout : int
  1668	            Timeout for test execution in seconds (default: 300s)
  1669	        task_id : Optional[str]
  1670	            Task identifier for task-specific test filtering in shared worktrees.
  1671	            When provided, test detection will first look for task-specific test
  1672	            files before falling back to running the full test suite.
  1673	        coach_test_execution : Optional[str]
  1674	            Test execution mode: "subprocess" (default,
  1675	            TASK-AB-COACHSUBPROC01) uses subprocess.run() directly with the
  1676	            venv-pinned interpreter; "sdk" (opt-in — see the open diagnosis
  1677	            tasks TASK-REV-COSE / TASK-FIX-A7B7) runs pytest through the
  1678	            Claude Agent SDK Bash tool for environment parity, with the
  1679	            subprocess path as fallback. None (default) resolves via
  1680	            :func:`resolve_coach_test_execution` (env
  1681	            ``GUARDKIT_COACH_TEST_EXECUTION`` > default). Callers that read
  1682	            ``.guardkit/config.yaml`` resolve
  1683	            ``resolve_coach_test_execution(config_value)`` before
  1684	            constructing. An explicit value is authoritative (validated, but
  1685	            never env-overridden) so pinned callers like the deterministic
  1686	            Phase-4 runner (``specialist_invocations.py``,
  1687	            TASK-AB-PERTASKFG01: never an LLM turn) cannot be flipped by the
  1688	            Coach env lever.
  1689	        matching_strategy : str
  1690	            Text matching strategy for acceptance criteria verification.
  1691	            ``"text"``: strict Jaccard threshold (70%), ``"semantic"``: lower
  1692	            threshold (50%) with fuzzy keyword prefix matching for local/vLLM
  1693	            backends, ``"auto"`` (default): resolves to ``"semantic"`` when
  1694	            ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint, otherwise
  1695	            ``"text"``.  Can also be set via ``GUARDKIT_MATCHING_STRATEGY`` env var.
  1696	        wave_size : int
  1697	            Number of tasks executing in parallel in the current wave (default: 1).
  1698	            When >1, the Coach runs independent tests in an isolated temp directory
  1699	            to prevent spurious failures from concurrent worktree mutations, and
  1700	            applies more lenient failure classification for contention-related errors.
  1701	        peer_changed_files : Optional[Dict[str, Iterable[str]]]
  1702	            Snapshot of files edited by other in-flight tasks in the same parallel
  1703	            wave, keyed by peer task id. When this Coach classifies a failure as
  1704	            ``parallel_contention`` (or as ``code`` in a parallel wave), it checks
  1705	            whether this task's own edits overlap with any peer's edits. Overlap
  1706	            means the failure is real source-file contention, not transient infra
  1707	            contention, so the conditional approval rule from TASK-ABFIX-005 must
  1708	            NOT fire — instead Coach returns feedback and the existing
  1709	            Player-Coach loop retries on the next turn (by which point peers have
  1710	            completed and the wave is naturally serialised). See TASK-FIX-A7B2.
  1711	        model_name : Optional[str]
  1712	            Orchestrator-configured model name to thread through to the harness
  1713	            for SDK-based Coach test execution. Used as a fallback when the
  1714	            ``GUARDKIT_COACH_TEST_MODEL`` env var is not set. Mirrors the model
  1715	            threading precedent set by TASK-FIX-LGFM2 / TASK-FIX-MODELPLUMB in
  1716	            ``AgentInvoker``. Without this, the LangGraph harness receives
  1717	            ``model=None`` for ``role='coach_test'`` and falls back to subprocess
  1718	            (TASK-FIX-LGFM3 / F12).
  1719	        venv_python : Optional[str]
  1720	            Path to the bootstrap venv Python interpreter Coach should run its
  1721	            independent tests under (typically ``BootstrapResult.venv_python``
  1722	            threaded from the feature orchestrator). When set, the SDK and
  1723	            subprocess test paths pin pytest to this interpreter instead of the
  1724	            host ``which pytest`` / ``sys.executable``. Resolution follows
  1725	            :func:`guardkit.orchestrator.coach_verification._resolve_venv_python`.
  1726	            Without it, Coach could validate against the wrong interpreter
  1727	            (TASK-FIX-COACHPYENV — sibling of the TASK-FIX-7A05 CoachVerifier fix).
  1728	        evidence_repos : Optional[List[EvidenceRepo]]
  1729	            Declared sibling repos whose independent tests the Coach runs
  1730	            (TASK-AB-XREPOEV01 AC-002). When a repo carries a ``test_command``,
  1731	            :meth:`run_evidence_repo_tests` executes it in that repo with the
  1732	            pinned interpreter; results reach the evidence bundle and a
  1733	            ran-and-failed (or declared-but-unrunnable) suite blocks the turn.
  1734	            Default None -> no sibling-repo test execution.
  1735	        basetemp_context : Optional[str]
  1736	            Attribution label for the per-run pytest ``--basetemp`` isolation
  1737	            (TASK-AB-BASETEMP01). When set (e.g. ``"phase4"`` from the
  1738	            deterministic Phase-4 runner in ``specialist_invocations.py``),
  1739	            it overrides the per-path defaults (``"coach-independent"`` for
  1740	            the standard subprocess run, ``"coach-isolated"`` for the
  1741	            parallel-wave snapshot run) so a leaked tmp dir names the caller.
  1742	            The label is combined with ``task_id`` in the directory prefix.
  1743	        """
  1744	        self.worktree_path = Path(worktree_path)
  1745	        self.test_command = test_command
  1746	        self.test_timeout = test_timeout
  1747	        self.task_id = task_id
  1748	        # TASK-AB-COACHSUBPROC01: None -> resolve env > default (subprocess);
  1749	        # resolve_coach_test_execution logs the active mode + provenance once
  1750	        # per init. An explicit value is authoritative (validated with safe
  1751	        # degrade, never env-overridden — protects pinned callers like the
  1752	        # deterministic Phase-4 runner).
  1753	        if coach_test_execution is None:
  1754	            coach_test_execution = resolve_coach_test_execution()
  1755	        elif coach_test_execution not in _VALID_COACH_TEST_EXECUTION_MODES:
  1756	            # 2026-07-04 code review: an INVALID explicit value is not a pin —
  1757	            # delegate to the standard env > default resolution instead of
  1758	            # jumping straight to the default, so a valid
  1759	            # GUARDKIT_COACH_TEST_EXECUTION override still applies (mirrors
  1760	            # resolve_coach_test_execution's invalid-tier fall-through). Only
  1761	            # a VALID explicit value stays authoritative over env.
  1762	            logger.warning(
  1763	                "Invalid coach_test_execution=%r (expected one of %s); "
  1764	                "delegating to %s > default resolution.",
  1765	                coach_test_execution,
  1766	                _VALID_COACH_TEST_EXECUTION_MODES,
  1767	                COACH_TEST_EXECUTION_ENV,
  1768	            )
  1769	            coach_test_execution = resolve_coach_test_execution()
  1770	        else:
  1771	            logger.debug(
  1772	                "Coach test execution mode: %s (source: caller)",
  1773	                coach_test_execution,
  1774	            )
  1775	        self._coach_test_execution = coach_test_execution
  1776	        # TASK-FIX-COACHPYENV: resolve the interpreter Coach runs independent
  1777	        # tests under. Prefers the explicit bootstrap venv, then a filesystem
  1778	        # recovery probing ``<worktree>/.venv/bin/python`` (current bootstrap
  1779	        # layout) and legacy ``<worktree>/.guardkit/venv/bin/python``
  1780	        # (TASK-AB-RESUMEVENV01), else None (PATH pytest / sys.executable for
  1781	        # non-Python projects). Reuses the helper already battle-tested for
  1782	        # CoachVerifier (TASK-FIX-7A05) so the two Coach verification surfaces
  1783	        # resolve interpreters identically.
  1784	        self._configured_venv_python: Optional[str] = venv_python
  1785	        self._venv_python: Optional[Path] = _resolve_venv_python(
  1786	            self.worktree_path, venv_python
  1787	        )
  1788	        if venv_python and (
  1789	            self._venv_python is None
  1790	            or str(self._venv_python) != str(Path(venv_python))
  1791	        ):
  1792	            # AC-4 mismatch guard: a bootstrap interpreter was configured but
  1793	            # the resolved interpreter differs (stale path / disappeared venv).
  1794	            # Loud WARNING — Coach is about to verify against a DIFFERENT
  1795	            # interpreter than the bootstrap installed packages into, which is
  1796	            # exactly the run-9 spurious-failure shape.
  1797	            logger.warning(
  1798	                "Coach test interpreter MISMATCH: configured bootstrap venv "
  1799	                "%s but resolved to %s. Independent tests may run under the "
  1800	                "wrong interpreter (TASK-FIX-COACHPYENV).",
  1801	                venv_python,
  1802	                self._venv_python if self._venv_python is not None else
  1803	                "PATH pytest / sys.executable",
  1804	            )
  1805	        elif self._venv_python is not None:
  1806	            logger.info(
  1807	                "CoachValidator pinning independent-test interpreter to %s",
  1808	                self._venv_python,
  1809	            )
  1810	        # TASK-FIX-LGFM3: orchestrator model threaded through for SDK test
  1811	        # execution path; falls back to None when caller didn't supply one.
  1812	        self._model_name: Optional[str] = model_name
  1813	        # TASK-FIX-COACHBUDG01 (2026-06-06): per-role Coach override. When
  1814	        # non-None, takes precedence over _model_name for the coach_test
  1815	        # path (consumed by _get_coach_test_model). Lets the operator
  1816	        # route Coach SDK test execution to the same Coach-specific model
  1817	        # (gemma4:26b) the Player↔Coach loop uses.
  1818	        self._coach_model_name: Optional[str] = coach_model_name
  1819	        # TASK-AB-XREPOEV01 (AC-002): declared sibling repos whose tests the
  1820	        # Coach runs independently. Empty -> no sibling test execution.
  1821	        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
  1822	        # TASK-AB-COACHRUNPARITY01 (arm b): the feature smoke command (the
  1823	        # deliverable's real runtime entry point). When set AND wave_size == 1,
  1824	        # gather_evidence runs it and records a RuntimeParityResult so a
  1825	        # "passes pytest but does not run" deliverable is caught pre-approval.
  1826	        # None -> no per-task runtime-parity check.
  1827	        self.smoke_command: Optional[str] = smoke_command
  1828	        # Exit code that counts as a clean standalone run for the parity check.
  1829	        # Threaded from the feature's smoke_gates.expected_exit so the per-task
  1830	        # check agrees with the post-wave gate (default 0).
  1831	        self.smoke_expected_exit: int = smoke_expected_exit
  1832	        # TASK-AB-BASETEMP01: caller-supplied attribution label for the per-run
  1833	        # pytest --basetemp; None -> per-path defaults (see _basetemp_context).
  1834	        self._basetemp_context: Optional[str] = basetemp_context
  1835	        self.wave_size = max(1, int(wave_size))
  1836	        # TASK-AB-NPDET01: the non-Python stack test-execution profile resolved
  1837	        # by ``_detect_test_command`` for THIS run (None for Python / no match /
  1838	        # parallel-wave deferral). ``run_independent_tests`` reads it to classify
  1839	        # absence stack-awarely (missing toolchain / zero-test => signal_absent).
  1840	        self._active_stack_profile: Optional[StackTestProfile] = None
  1841	        # TASK-ABFIX-011: cached result of the pytest-timeout availability probe
  1842	        # against the pinned interpreter (``None`` = not yet probed). The pinned
  1843	        # interpreter is fixed per validator instance, so one probe per instance
  1844	        # is sufficient and is shared across all three pytest injection sites.
  1845	        self._pytest_timeout_available_cache: Optional[bool] = None
  1846	        # TASK-DIAG-F4A2: Turn number for sdk_debug preservation paths.
  1847	        # Default 1 keeps backwards-compat for callers that don't pass it.
  1848	        self._turn = max(1, int(turn))
  1849	        # TASK-FIX-A7B2: Wave-peer file-edit snapshot for source-file contention
  1850	        # detection. Normalised to ``Dict[str, frozenset[str]]`` so the overlap
  1851	        # check is a cheap set intersection.
  1852	        self._peer_changed_files: Dict[str, frozenset] = {}
  1853	        if peer_changed_files:
  1854	            for peer_id, files in peer_changed_files.items():
  1855	                if not peer_id or peer_id == self.task_id:
  1856	                    continue
  1857	                if not files:
  1858	                    continue
  1859	                self._peer_changed_files[peer_id] = frozenset(
  1860	                    str(f) for f in files if f
  1861	                )
  1862	        # Resolve matching strategy: constructor arg > env var > "auto"
  1863	        _VALID_STRATEGIES = ("auto", "text", "semantic")
  1864	        env_strategy = os.environ.get("GUARDKIT_MATCHING_STRATEGY", "").lower()
  1865	        if matching_strategy not in _VALID_STRATEGIES:
  1866	            logger.warning(
  1867	                "Unrecognised matching_strategy %r, falling back to 'auto'",
  1868	                matching_strategy,
  1869	            )
  1870	            matching_strategy = "auto"
  1871	        if matching_strategy != "auto":
  1872	            self._matching_strategy = matching_strategy
  1873	        elif env_strategy in ("text", "semantic"):
  1874	            self._matching_strategy = env_strategy
  1875	        else:
  1876	            self._matching_strategy = "auto"
  1877	
  1878	        logger.debug(
  1879	            f"CoachValidator initialized for worktree: {worktree_path}, "
  1880	            f"task_id: {task_id}, wave_size: {self.wave_size}"
  1881	        )
  1882	
  1883	    @property
  1884	    def is_parallel(self) -> bool:
  1885	        """Return True when this Coach is running in a parallel wave (wave_size > 1)."""
  1886	        return self.wave_size > 1
  1887	
  1888	    def _detect_source_file_contention(
  1889	        self,
  1890	        task_work_results: Dict[str, Any],
  1891	    ) -> Dict[str, frozenset]:
  1892	        """Detect source-file contention with in-flight peer tasks (TASK-FIX-A7B2).
  1893	
  1894	        Returns a mapping ``peer_task_id -> frozenset[overlapping_file]`` for
  1895	        every peer that edited at least one file this task also edited within
  1896	        the same parallel wave. An empty mapping means there is no source-file
  1897	        contention — the failure is either genuinely transient (e.g. infra
  1898	        flakiness, partial __init__.py write race) or unrelated to peer edits,
  1899	        so the existing TASK-ABFIX-005 conditional approval path remains safe.
  1900	
  1901	        A non-empty mapping means the parallel_contention is real source-file
  1902	        contention (e.g. two tasks writing conflicting step definitions to a
  1903	        shared BDD glue file). The TASK-ABFIX-005 isolation snapshot cannot
  1904	        defend against this case because the snapshot captures the
  1905	        already-corrupted shared file. Conditional approval would mask real
  1906	        correctness damage, so the caller must fall through to feedback and
  1907	        let the existing Player-Coach retry machinery serialise the next
  1908	        attempt (by which point peers have completed and the wave is
  1909	        effectively single-tasked).
  1910	
  1911	        Parameters
  1912	        ----------
  1913	        task_work_results : Dict[str, Any]
  1914	            Player's task_work_results.json payload. Reads ``files_authored``
  1915	            (Player's explicit Write/Edit tool calls — TASK-FIX-CC-COND) when
  1916	            present, otherwise falls back to ``files_created`` /
  1917	            ``files_modified`` for compatibility with pre-files_authored
  1918	            artefacts.
  1919	
  1920	        Returns
  1921	        -------
  1922	        Dict[str, frozenset[str]]
  1923	            Map from peer task id to set of overlapping file paths. Empty when
  1924	            no peer edits overlap, when this task has no recorded edits, or
  1925	            when no peer snapshot was supplied.
  1926	
  1927	        Notes
  1928	        -----
  1929	        TASK-FIX-CC-COND: ``files_modified`` / ``files_created`` are
  1930	        unioned with worktree-wide ``git diff`` output by ``agent_invoker``
  1931	        before they reach this validator, so in shared-worktree parallel
  1932	        waves they include peer-task edits this task never authored. Using
  1933	        them as the contention input produced false-positive
  1934	        ``parallel_contention`` verdicts that blocked the conditional
  1935	        approval path the design relies on (see TASK-REV-CC40 finding F-3,
  1936	        FEAT-39E1 turn-2 evidence). ``files_authored`` is captured at the
  1937	        SDK Write/Edit boundary and is *not* enriched with git output, so
  1938	        it remains authoritative. The fallback is presence-based, not
  1939	        truthy-based: ``files_authored = []`` correctly means "this task
  1940	        authored nothing" and yields no contention, even when
  1941	        ``files_modified`` is contaminated.
  1942	        """
  1943	        if not self._peer_changed_files:
  1944	            return {}
  1945	
  1946	        # TASK-FIX-CC-COND: prefer the Player's authored set when present.
  1947	        # Presence-based fallback: distinguish "field absent" (legacy
  1948	        # task_work_results.json from before files_authored existed) from
  1949	        # "field present, empty" (this task's Player did no Write/Edit).
  1950	        if "files_authored" in task_work_results:
  1951	            authored_raw = task_work_results.get("files_authored") or []
  1952	            own = {str(f) for f in authored_raw if f}
  1953	            source = "files_authored"
  1954	        else:
  1955	            legacy = set(task_work_results.get("files_created", []) or [])
  1956	            legacy.update(task_work_results.get("files_modified", []) or [])
  1957	            own = {str(f) for f in legacy if f}
  1958	            source = "legacy_files_modified"
  1959	
  1960	        if not own:
  1961	            return {}
  1962	
  1963	        overlaps: Dict[str, frozenset] = {}
  1964	        for peer_id, peer_files in self._peer_changed_files.items():
  1965	            shared = peer_files & own
  1966	            if shared:
  1967	                overlaps[peer_id] = frozenset(shared)
  1968	
  1969	        if overlaps:
  1970	            # TASK-FIX-CC-COND bonus: structured-log line so future
  1971	            # false positives are diagnosable from logs alone. Records
  1972	            # both the authored set and the (possibly contaminated)
  1973	            # files_modified set so a reviewer can see at a glance
  1974	            # whether the overlap reflects real intent or legacy
  1975	            # fallback noise.
  1976	            logger.info(
  1977	                "Source-file contention detected (source=%s, overlaps=%s, "
  1978	                "files_authored=%s, files_modified=%s, files_created=%s)",
  1979	                source,
  1980	                {peer: sorted(files) for peer, files in overlaps.items()},
  1981	                sorted(task_work_results.get("files_authored", []) or []),
  1982	                sorted(task_work_results.get("files_modified", []) or []),
  1983	                sorted(task_work_results.get("files_created", []) or []),
  1984	            )
  1985	        return overlaps
  1986	
  1987	    def _get_coach_test_model(self) -> Optional[str]:
  1988	        """Return the model for Coach SDK test invocations, or None to use CLI default.
  1989	
  1990	        Resolution order:
  1991	        1. ``GUARDKIT_COACH_TEST_MODEL`` env var (operator override — e.g.
  1992	           claude-haiku-4-5-20251001 for cost reduction on the real Anthropic API).
  1993	        2. Orchestrator-supplied ``coach_model_name`` (TASK-FIX-COACHBUDG01):
  1994	           per-role Coach override (e.g. ``gemma4:26b`` while Player stays on
  1995	           ``qwen36-workhorse`` — TASK-HMIG-013). Takes precedence over the
  1996	           generic ``model_name`` for this Coach-specific path.
  1997	        3. Orchestrator-supplied ``model_name`` (TASK-FIX-LGFM3): same value
  1998	           threaded into ``AgentInvoker.select_harness`` calls. Without this
  1999	           fallback, the LangGraph harness receives ``model=None`` for
  2000	           ``role='coach_test'`` and the SDK path errors out (F12).
  2001	        4. ``None`` (harness uses CLI default).
  2002	        """
  2003	        import os
  2004	        env_model = os.environ.get("GUARDKIT_COACH_TEST_MODEL") or None
  2005	        if env_model is not None:
  2006	            return env_model
  2007	        if self._coach_model_name is not None:
  2008	            return self._coach_model_name
  2009	        return self._model_name
  2010	
  2011	    def _resolve_task_type(self, task: Dict[str, Any]) -> TaskType:
  2012	        """
  2013	        Resolve task type from task metadata with alias support and fallback to default.
  2014	
  2015	        Supports legacy task_type values through TASK_TYPE_ALIASES mapping.
  2016	        Logs info message when alias is used for transparency.
  2017	
  2018	        Parameters
  2019	        ----------
  2020	        task : Dict[str, Any]
  2021	            Task data including optional task_type field
  2022	
  2023	        Returns
  2024	        -------
  2025	        TaskType
  2026	            Resolved task type
  2027	
  2028	        Raises
  2029	        ------
  2030	        ValueError
  2031	            If task_type is specified but invalid (not in enum or aliases)
  2032	        """
  2033	        task_type_str = task.get("task_type")
  2034	
  2035	        if task_type_str is None:
  2036	            # No task_type specified - use default (feature)
  2037	            logger.debug("No task_type specified, defaulting to FEATURE profile")
  2038	            return TaskType.FEATURE
  2039	
  2040	        # Try to parse as valid TaskType enum first
  2041	        try:
  2042	            task_type = TaskType(task_type_str)
  2043	            logger.debug(f"Resolved task_type from metadata: {task_type.value}")
  2044	            return task_type
  2045	        except ValueError:
  2046	            # Check aliases before raising error
  2047	            if task_type_str in TASK_TYPE_ALIASES:
  2048	                aliased_type = TASK_TYPE_ALIASES[task_type_str]
  2049	                logger.info(
  2050	                    f"Using task_type alias: '{task_type_str}' → '{aliased_type.value}' "
  2051	                    f"(update task frontmatter to use '{aliased_type.value}' directly)"
  2052	                )
  2053	                return aliased_type
  2054	
  2055	            # Not a valid enum value or alias - raise error
  2056	            logger.error(f"Invalid task_type value: {task_type_str}")
  2057	            raise ValueError(
  2058	                f"Invalid task_type value: {task_type_str}. "
  2059	                f"Must be one of: {', '.join(t.value for t in TaskType)} "
  2060	                f"or valid alias: {', '.join(TASK_TYPE_ALIASES.keys())}"
  2061	            ) from None
  2062	
  2063	    def validate(
  2064	        self,
  2065	        task_id: str,
  2066	        turn: int,
  2067	        task: Dict[str, Any],
  2068	        skip_arch_review: bool = False,
  2069	        context: Optional[str] = None,
  2070	    ) -> CoachValidationResult:
  2071	        """
  2072	        Main validation entry point.
  2073	
  2074	        Validates Player's implementation by:
  2075	        1. Reading task-work quality gate results
  2076	        2. Verifying all gates passed
  2077	        3. Running independent test verification
  2078	        4. Checking requirements satisfaction
  2079	
  2080	        Parameters
  2081	        ----------
  2082	        task_id : str
  2083	            Task identifier (e.g., "TASK-001")
  2084	        turn : int
  2085	            Current turn number (1-based)
  2086	        task : Dict[str, Any]
  2087	            Task data including acceptance_criteria
  2088	        skip_arch_review : bool
  2089	            If True, skip architectural review gate regardless of profile setting.
  2090	            Used for --implement-only mode where Phase 2.5B doesn't run.
  2091	            Default: False (enforce arch review per profile).
  2092	
  2093	        Returns
  2094	        -------
  2095	        CoachValidationResult
  2096	            Complete validation result with decision
  2097	        """
  2098	        logger.info(f"Starting Coach validation for {task_id} turn {turn}")
  2099	
  2100	        # Log context if provided
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2100}, 'id': 'oZDstIBs18Agr23Hh4qUFTJ07FmDUBZm', 'type': 'tool_call'}]
Tool:   2101	        if context:
  2102	            logger.debug(f"[Memory] Coach context provided: {len(context)} chars")
  2103	
  2104	        # Resolve task type and get quality gate profile
  2105	        try:
  2106	            task_type = self._resolve_task_type(task)
  2107	        except ValueError as e:
  2108	            logger.error(f"Failed to resolve task type: {e}")
  2109	            # honesty_verification omitted (defaults to None): _verify_honesty
  2110	            # has not yet been called on this short-circuit path (TASK-FIX-7E3F).
  2111	            return self._feedback_result(
  2112	                task_id=task_id,
  2113	                turn=turn,
  2114	                issues=[{
  2115	                    "severity": "must_fix",
  2116	                    "category": "invalid_task_type",
  2117	                    "description": str(e),
  2118	                }],
  2119	                rationale=f"Invalid task type: {e}",
  2120	                context_used=context,
  2121	                is_configuration_error=True,
  2122	            )
  2123	
  2124	        # Operator handoff: defensive skip branch (TASK-FPTC-004 AC-01).
  2125	        # Operator-handoff tasks have runtime-shaped acceptance criteria
  2126	        # that no automated check can verify (e.g. "operator runs X
  2127	        # against the deployed service and inspects Y"). The feature
  2128	        # orchestrator (TASK-FPTC-003) is responsible for short-circuiting
  2129	        # dispatch BEFORE Coach is invoked — this branch is a paranoid
  2130	        # second line of defence that exits cleanly without exercising
  2131	        # any AC-matching machinery if the orchestrator-level skip is
  2132	        # bypassed for any reason. The "deferred" outcome shape mirrors
  2133	        # what feature_orchestrator records, so TASK-FPTC-005's
  2134	        # feature-complete summary sees consistent records.
  2135	        if task_type == TaskType.OPERATOR_HANDOFF:
  2136	            logger.info(
  2137	                f"Coach skipping operator_handoff task {task_id} turn {turn}: "
  2138	                f"runtime verification deferred to operator."
  2139	            )
  2140	            # honesty_verification omitted (defaults to None): _verify_honesty
  2141	            # has not yet been called on this operator-handoff short-circuit
  2142	            # path (TASK-FIX-7E3F).
  2143	            return CoachValidationResult(
  2144	                task_id=task_id,
  2145	                turn=turn,
  2146	                decision="deferred",
  2147	                quality_gates=None,
  2148	                independent_tests=None,
  2149	                requirements=None,
  2150	                issues=[],
  2151	                rationale="operator follow-up — runtime verification required",
  2152	                context_used=context,
  2153	            )
  2154	
  2155	        profile = get_profile(task_type)
  2156	        logger.info(f"Using quality gate profile for task type: {task_type.value}")
  2157	
  2158	        # 1. Read task-work quality gate results
  2159	        task_work_results = self.read_quality_gate_results(task_id)
  2160	
  2161	        if "error" in task_work_results:
  2162	            logger.warning(
  2163	                f"Task-work results for {task_id} contain error: "
  2164	                f"{task_work_results.get('error', 'unknown')}"
  2165	            )
  2166	            # honesty_verification omitted (defaults to None): _verify_honesty
  2167	            # has not yet been called on this missing-results short-circuit
  2168	            # path (TASK-FIX-7E3F).
  2169	            return self._feedback_result(
  2170	                task_id=task_id,
  2171	                turn=turn,
  2172	                issues=[{
  2173	                    "severity": "must_fix",
  2174	                    "category": "missing_results",
  2175	                    "description": task_work_results["error"],
  2176	                }],
  2177	                rationale="Task-work quality gate results not found",
  2178	                context_used=context,
  2179	            )
  2180	
  2181	        # 1.4. Adversarial honesty verification (TASK-AB-FIX-INVAB1 AC-002).
  2182	        #
  2183	        # Restores the original Player–Coach adversarial property on the
  2184	        # deterministic Coach path. Option D (TASK-REV-0414) introduced
  2185	        # CoachValidator as the primary Coach but did not wire in
  2186	        # CoachVerifier — the existing-but-disconnected honesty verifier
  2187	        # documented in installer/core/agents/autobuild-coach.md:141-203.
  2188	        #
  2189	        # The verifier checks Player claims against worktree state:
  2190	        # - files_created / files_modified / tests_written exist on disk
  2191	        # - completion_promises[*].implementation_files exist when status=complete
  2192	        #
  2193	        # When critical discrepancies exist, gates are not consulted at all
  2194	        # — Player feedback names the specific claim/actual disagreement so
  2195	        # the next turn can correct course. Honest reports produce zero
  2196	        # discrepancies (no behavioural change for compliant Players).
  2197	        #
  2198	        # Test verification (CoachVerifier._verify_test_results) is
  2199	        # deliberately skipped here because run_independent_tests below
  2200	        # already runs an authoritative independent pytest pass — running
  2201	        # it twice would double the Coach's wall-clock cost.
  2202	        honesty_verification = self._verify_honesty(task_work_results)
  2203	        honesty_issues = self._honesty_issues_from(honesty_verification)
  2204	        # TASK-FIX-1B4B Layer 2: only ``must_fix`` honesty issues
  2205	        # short-circuit gate evaluation. ``should_fix`` issues (a single
  2206	        # path-only ``file_existence`` discrepancy demoted by
  2207	        # ``_honesty_issues_from``) ride along to the final result so
  2208	        # the Player still sees them in feedback while the rest of the
  2209	        # gates run.
  2210	        honesty_must_fix = [
  2211	            i for i in honesty_issues if i["severity"] == "must_fix"
  2212	        ]
  2213	        honesty_should_fix = [
  2214	            i for i in honesty_issues if i["severity"] == "should_fix"
  2215	        ]
  2216	        if honesty_must_fix:
  2217	            logger.warning(
  2218	                f"Honesty verification produced {len(honesty_must_fix)} "
  2219	                f"critical issue(s) for {task_id}; short-circuiting "
  2220	                f"gate evaluation."
  2221	            )
  2222	            return CoachValidationResult(
  2223	                task_id=task_id,
  2224	                turn=turn,
  2225	                decision="feedback",
  2226	                quality_gates=None,
  2227	                independent_tests=None,
  2228	                requirements=None,
  2229	                issues=honesty_must_fix,
  2230	                rationale=(
  2231	                    f"{len(honesty_must_fix)} honesty discrepancy/discrepancies. "
  2232	                    f"Adversarial verification overrode gate evaluation."
  2233	                ),
  2234	                context_used=context,
  2235	                honesty_verification=honesty_verification,
  2236	            )
  2237	
  2238	        # 1.45. AC-cited missing test files (TASK-AB-FIX-INVAB1 AC-006).
  2239	        #
  2240	        # If an acceptance criterion names a specific test file (e.g.
  2241	        # ``tests/test_login.py``) and that file does not exist on disk,
  2242	        # the independent-test gate would silently fall back to the
  2243	        # existing-test set and report green. Surface the gap as a
  2244	        # ``must_fix`` issue so the Coach short-circuits with feedback
  2245	        # rather than running a smaller-scope pytest invocation that can
  2246	        # only return false-greens.
  2247	        ac_missing_tests = self._detect_ac_cited_missing_test_files(
  2248	            task.get("acceptance_criteria", [])
  2249	        )
  2250	        if ac_missing_tests:
  2251	            logger.warning(
  2252	                f"AC-cited missing test files for {task_id}: "
  2253	                f"{ac_missing_tests}. Short-circuiting before "
  2254	                f"run_independent_tests."
  2255	            )
  2256	            return CoachValidationResult(
  2257	                task_id=task_id,
  2258	                turn=turn,
  2259	                decision="feedback",
  2260	                quality_gates=None,
  2261	                independent_tests=None,
  2262	                requirements=None,
  2263	                issues=honesty_should_fix + [{
  2264	                    "severity": "must_fix",
  2265	                    "category": "acceptance_criteria",
  2266	                    "description": (
  2267	                        f"AC names test file(s) that don't exist on disk: "
  2268	                        f"{', '.join(ac_missing_tests)}. The independent-"
  2269	                        f"test gate cannot run honestly while AC-cited "
  2270	                        f"tests are absent."
  2271	                    ),
  2272	                    "details": {"missing_test_files": ac_missing_tests},
  2273	                }],
  2274	                rationale=(
  2275	                    f"{len(ac_missing_tests)} AC-cited test file(s) "
  2276	                    f"missing on disk; gate cannot run honestly."
  2277	                ),
  2278	                context_used=context,
  2279	                honesty_verification=honesty_verification,
  2280	            )
  2281	
  2282	        # 1.5. Agent-invocations gate (TASK-FIX-RWOP1.3.1, TASK-REV-F6E1 F3c).
  2283	        #
  2284	        # AgentInvoker._write_task_work_results folds
  2285	        # validate_agent_invocations into the producer path and persists the
  2286	        # verdict under "agent_invocations_validation".
  2287	        #
  2288	        # Pre-F3c (RWOP1.3.1 → forge-run-6): a "violation" status caused this
  2289	        # method to early-return with feedback, short-circuiting positions
  2290	        # 2–4 (quality_gates, independent_tests, AC verification). The
  2291	        # consequence — observed across forge-run-3/4/5/6 — was that the
  2292	        # Coach never once ran AC verification when the gate fired, so
  2293	        # the recent BDD-AC bridge work could not actually deliver its
  2294	        # quality signal.
  2295	        #
  2296	        # Post-F3c: a "violation" is captured as a non-blocking advisory
  2297	        # (severity=warning, category=agent_invocations_advisory) and
  2298	        # threaded into the issues list of whatever decision the
  2299	        # outcome-based gates produce. The Player still sees the process
  2300	        # observation ("you should invoke X via Task tool") so structural
  2301	        # drift toward Player-inline implementation stays visible — but
  2302	        # the gate no longer prevents the outcome-checks from running.
  2303	        #
  2304	        # Stall classifiers that match `category == "agent_invocations_violation"`
  2305	        # (autobuild stall sub-typing) intentionally no longer trigger:
  2306	        # this gate stops being a stall driver. Promote back to blocker
  2307	        # only after evidence shows the advisory-mode signal is being
  2308	        # systematically ignored AND that absence correlates with quality
  2309	        # drops in AC verification. See
  2310	        # docs/reviews/forge-run-6-fix-or-revert/TASK-REV-F6E1-decision-report.md
  2311	        # § Revision 3 for the diagnostic and rationale.
  2312	        agent_invocations_advisory: Optional[Dict[str, Any]] = None
  2313	        agent_invocations_validation = task_work_results.get(
  2314	            "agent_invocations_validation"
  2315	        )
  2316	        if (
  2317	            isinstance(agent_invocations_validation, dict)
  2318	            and agent_invocations_validation.get("status") == "violation"
  2319	        ):
  2320	            raw_missing = agent_invocations_validation.get("missing_phases") or []
  2321	            # The validator may emit missing_phases either as a list of phase
  2322	            # IDs or as a list of {"phase": "...", "description": "..."} dicts.
  2323	            # Normalise to a flat list of phase IDs for downstream formatting.
  2324	            missing_phases: List[str] = []
  2325	            if raw_missing and isinstance(raw_missing[0], dict):
  2326	                missing_phases = [
  2327	                    str(m.get("phase", ""))
  2328	                    for m in raw_missing
  2329	                    if m.get("phase")
  2330	                ]
  2331	            else:
  2332	                missing_phases = [str(m) for m in raw_missing]
  2333	            missing_phases_sorted = sorted(missing_phases)
  2334	            missing_phases_str = (
  2335	                ", ".join(missing_phases_sorted)
  2336	                if missing_phases_sorted
  2337	                else "unknown"
  2338	            )
  2339	            # TASK-FIX-7A07 AC-3: Build a phase-with-description rendering and
  2340	            # resolve the stack-specific Phase-3 specialist name so the
  2341	            # Player's next turn has actionable guidance on *which*
  2342	            # sub-agent to invoke via the Task tool.
  2343	            missing_phases_with_names = ", ".join(
  2344	                f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  2345	                for p in missing_phases_sorted
  2346	            ) if missing_phases_sorted else "unknown"
  2347	            stack_template = detect_stack_template(self.worktree_path)
  2348	            # TASK-GK-PROF-001: thread the worktree root so Phase-3 resolution
  2349	            # consults the *installed* specialist set, not the legacy
  2350	            # stack→specialist map. When the stack's profile-default isn't
  2351	            # installed (e.g. langchain-deepagents-orchestrator ships
  2352	            # langchain-tool-decorator-specialist, not python-api-specialist),
  2353	            # this downgrades the advisory to informational instead of naming
  2354	            # an agent the operator doesn't have.
  2355	            specialist_lines = render_missing_phase_list(
  2356	                missing_phases_sorted,
  2357	                stack_template=stack_template,
  2358	                workspace_root=self.worktree_path,
  2359	            )
  2360	            specialist_block = "\n".join(f"- {line}" for line in specialist_lines)
  2361	            expected_phases_val = agent_invocations_validation.get(
  2362	                "expected_phases"
  2363	            )
  2364	            actual_invocations_val = agent_invocations_validation.get(
  2365	                "actual_invocations"
  2366	            )
  2367	            expected_str = (
  2368	                str(expected_phases_val)
  2369	                if expected_phases_val is not None
  2370	                else "?"
  2371	            )
  2372	            actual_str = (
  2373	                str(actual_invocations_val)
  2374	                if actual_invocations_val is not None
  2375	                else "?"
  2376	            )
  2377	            logger.info(
  2378	                f"Agent-invocations advisory for {task_id}: "
  2379	                f"missing phases {missing_phases_str} "
  2380	                f"(non-blocking; outcome gates will run)"
  2381	            )
  2382	            advisory_description = (
  2383	                f"Advisory (non-blocking): task-work produced a report with "
  2384	                f"{actual_str} of {expected_str} expected agent invocations. "
  2385	                f"Missing phases: {missing_phases_with_names}. "
  2386	                f"Consider invoking these agents via the Task tool to "
  2387	                f"strengthen stack-specific quality:\n{specialist_block}"
  2388	            )
  2389	            agent_invocations_advisory = {
  2390	                "severity": "warning",
  2391	                "category": "agent_invocations_advisory",
  2392	                "description": advisory_description,
  2393	                "details": {
  2394	                    "missing_phases": missing_phases_sorted,
  2395	                    "expected_phases": expected_phases_val,
  2396	                    "actual_invocations": actual_invocations_val,
  2397	                },
  2398	            }
  2399	
  2400	        # F3c helper: prepend the advisory to any issues list so process
  2401	        # observations ride along with whatever outcome-based decision
  2402	        # downstream gates produce. ``honesty_should_fix`` rides the
  2403	        # same channel (TASK-FIX-1B4B Layer 2): a single demoted
  2404	        # path-only honesty discrepancy surfaces in feedback while the
  2405	        # rest of the gates evaluate normally.
  2406	        advisory_issues: List[Dict[str, Any]] = (
  2407	            [agent_invocations_advisory]
  2408	            if agent_invocations_advisory is not None
  2409	            else []
  2410	        )
  2411	        # TASK-FIX-SPECVIOL01 AC-002: attributed specialist-substrate
  2412	        # failure advisories ride the same channel (legacy validate() path;
  2413	        # the primary gather_evidence path has the same wire).
  2414	        advisory_issues.extend(
  2415	            self._compute_specialist_failure_advisories(task_work_results)
  2416	        )
  2417	        advisory_issues.extend(honesty_should_fix)
  2418	
  2419	        # 2. Verify quality gates passed with profile
  2420	        gates_status = self.verify_quality_gates(
  2421	            task_work_results, profile=profile, skip_arch_review=skip_arch_review
  2422	        )
  2423	
  2424	        # Validate requirements ahead of the gate-fail short-circuit so
  2425	        # gate-failure results carry criteria_met (TASK-GK-CR-001). This
  2426	        # is a pure read over task / task_work_results / the player report
  2427	        # — no side effects, idempotent. The same value is reused on the
  2428	        # all-gates-passed path below, so the call happens exactly once.
  2429	        requirements = self.validate_requirements(task, task_work_results, turn=turn)
  2430	
  2431	        if not gates_status.all_gates_passed:
  2432	            logger.info(f"Quality gates failed for {task_id}: {gates_status}")
  2433	            return self._feedback_from_gates(
  2434	                task_id=task_id,
  2435	                turn=turn,
  2436	                gates=gates_status,
  2437	                task_work_results=task_work_results,
  2438	                context_used=context,
  2439	                extra_issues=advisory_issues,
  2440	                honesty_verification=honesty_verification,
  2441	                requirements=requirements,
  2442	            )
  2443	
  2444	        # 3. Independent test verification (trust but verify)
  2445	        # Skip independent tests for task types that don't require tests (e.g., scaffolding)
  2446	        if not profile.tests_required:
  2447	            test_result = IndependentTestResult(
  2448	                tests_passed=True,
  2449	                test_command="skipped",
  2450	                test_output_summary=(
  2451	                    f"Independent test verification skipped "
  2452	                    f"(tests not required for {task_type.value} tasks)"
  2453	                ),
  2454	                duration_seconds=0.0,
  2455	            )
  2456	            logger.info(
  2457	                f"Independent test verification skipped for {task_id} "
  2458	                f"(tests not required for {task_type.value} tasks)"
  2459	            )
  2460	        else:
  2461	            test_result = self.run_independent_tests(
  2462	                task_work_results=task_work_results,
  2463	                task=task,
  2464	                turn=turn,
  2465	            )
  2466	
  2467	        conditional_approval = False
  2468	        environment_conditional_approval = False
  2469	        failure_class = None
  2470	        if not test_result.tests_passed:
  2471	            failure_class, failure_confidence = self._classify_test_failure(
  2472	                test_result.raw_output,
  2473	                requires_infrastructure=task.get("requires_infrastructure") if task else None,
  2474	                # TASK-ABFIX-012: thread task_type so the TESTING own-code override
  2475	                # fires on the legacy validate() path too (GUARDKIT_COACH_LEGACY=1).
  2476	                task_type=task.get("task_type") if task else None,
  2477	            )
  2478	            logger.warning(
  2479	                f"Independent test verification failed for {task_id} "
  2480	                f"(classification={failure_class}, confidence={failure_confidence})"
  2481	            )
  2482	
  2483	            # Conditional approval for high-confidence infrastructure failures
  2484	            # when task declares requires_infrastructure and Docker is unavailable
  2485	            requires_infra = task.get("requires_infrastructure", [])
  2486	            docker_available = task.get("_docker_available", True)
  2487	
  2488	            logger.info(
  2489	                "conditional_approval check: failure_class=%s, confidence=%s, "
  2490	                "requires_infra=%s, docker_available=%s, all_gates_passed=%s, "
  2491	                "wave_size=%s",
  2492	                failure_class,
  2493	                failure_confidence,
  2494	                requires_infra,
  2495	                docker_available,
  2496	                gates_status.all_gates_passed,
  2497	                self.wave_size,
  2498	            )
  2499	
  2500	            # TASK-ABSR-2468: belt-and-braces clause for environment-class
  2501	            # ambiguous infrastructure failures (ImportError /
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

