## Summarized at 2026-07-04T21:04:32.444533+00:00

AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 1000, 'offset': 1000}, 'id': 'cWXZjfHBEZyO1FbyYmgiKzYwD3bqpLiO', 'type': 'tool_call'}]
Tool:   1001	            tool_args: Tool arguments dictionary containing file_path
  1002	        """
  1003	        # TASK-FIX-PIPELINE: Try multiple key names for file path (Fix 1)
  1004	        # Claude Code SDK tools may use different key names
  1005	        file_path = (
  1006	            tool_args.get("file_path")
  1007	            or tool_args.get("path")
  1008	            or tool_args.get("file")
  1009	            or tool_args.get("filePath")
  1010	        )
  1011	        if not file_path or not isinstance(file_path, str):
  1012	            logger.debug(
  1013	                f"Tool {tool_name} call has no recognizable file path key. "
  1014	                f"Available keys: {list(tool_args.keys())}"
  1015	            )
  1016	            return
  1017	
  1018	        if tool_name == "Write":
  1019	            self._files_created.add(file_path)
  1020	            self._files_authored.add(file_path)
  1021	            logger.debug(f"Tool call tracked - file created: {file_path}")
  1022	            # Track test files separately
  1023	            if self._is_test_file(file_path):
  1024	                self._test_files_created.add(file_path)
  1025	                logger.debug(f"Test file tracked: {file_path}")
  1026	        elif tool_name == "Edit":
  1027	            self._files_modified.add(file_path)
  1028	            self._files_authored.add(file_path)
  1029	            logger.debug(f"Tool call tracked - file modified: {file_path}")
  1030	
  1031	    def _parse_tool_invocations(self, message: str) -> None:
  1032	        """Parse tool invocations from message and track file operations.
  1033	
  1034	        Detects Write and Edit tool calls in the message text and extracts
  1035	        file paths to track. Handles both XML-style tool invocations and
  1036	        tool result messages.
  1037	
  1038	        Args:
  1039	            message: Stream message that may contain tool invocations
  1040	        """
  1041	        # Track XML-style tool invocations: <invoke name="Write">...<parameter name="file_path">
  1042	        tool_match = self._match_pattern(self.TOOL_INVOKE_PATTERN, message)
  1043	        if tool_match:
  1044	            tool_name = tool_match.group(1)
  1045	            file_path_match = self._match_pattern(self.TOOL_FILE_PATH_PATTERN, message)
  1046	            if file_path_match:
  1047	                file_path = file_path_match.group(1).strip()
  1048	                self._track_tool_call(tool_name, {"file_path": file_path})
  1049	
  1050	        # Track tool result messages (e.g., "File created successfully at: /path")
  1051	        for result_match in self.TOOL_RESULT_CREATED_PATTERN.finditer(message):
  1052	            file_path = result_match.group(1).strip()
  1053	            if file_path and self._is_valid_file_path(file_path):
  1054	                self._files_created.add(file_path)
  1055	                logger.debug(f"Tool result tracked - file created: {file_path}")
  1056	
  1057	        for result_match in self.TOOL_RESULT_MODIFIED_PATTERN.finditer(message):
  1058	            file_path = result_match.group(1).strip()
  1059	            if file_path and self._is_valid_file_path(file_path):
  1060	                self._files_modified.add(file_path)
  1061	                logger.debug(f"Tool result tracked - file modified: {file_path}")
  1062	
  1063	    def parse_message(self, message: str) -> None:
  1064	        """Parse a single stream message and accumulate results.
  1065	
  1066	        This method extracts quality gate information from a stream message
  1067	        and updates the internal state. It handles:
  1068	        - Phase markers and completion indicators
  1069	        - Test pass/fail counts
  1070	        - Coverage percentage
  1071	        - Quality gate status
  1072	        - File modification lists
  1073	        - Tool invocations (Write/Edit) for file tracking
  1074	
  1075	        Args:
  1076	            message: Single message from the task-work SDK stream
  1077	
  1078	        Note:
  1079	            Unrecognized patterns are logged at debug level but do not
  1080	            cause errors (graceful degradation).
  1081	        """
  1082	        if not message:
  1083	            return
  1084	
  1085	        # Tool invocation tracking (Write/Edit operations)
  1086	        self._parse_tool_invocations(message)
  1087	
  1088	        # Phase detection
  1089	        phase_match = self._match_pattern(self.PHASE_MARKER_PATTERN, message)
  1090	        if phase_match:
  1091	            phase_num = phase_match.group(1)
  1092	            phase_text = phase_match.group(2)[:100]  # Truncate long descriptions
  1093	            self._phases[f"phase_{phase_num}"] = {
  1094	                "detected": True,
  1095	                "text": phase_text,
  1096	                "completed": False,
  1097	            }
  1098	            logger.debug(f"Detected phase {phase_num}: {phase_text}")
  1099	
  1100	        # Phase completion
  1101	        complete_match = self._match_pattern(self.PHASE_COMPLETE_PATTERN, message)
  1102	        if complete_match:
  1103	            phase_num = complete_match.group(1)
  1104	            phase_key = f"phase_{phase_num}"
  1105	            if phase_key in self._phases:
  1106	                self._phases[phase_key]["completed"] = True
  1107	            else:
  1108	                self._phases[phase_key] = {"detected": True, "completed": True}
  1109	            logger.debug(f"Phase {phase_num} completed")
  1110	
  1111	        # Test results - try individual patterns first
  1112	        tests_passed_match = self._match_pattern(self.TESTS_PASSED_PATTERN, message)
  1113	        if tests_passed_match:
  1114	            self._tests_passed = int(tests_passed_match.group(1))
  1115	            logger.debug(f"Tests passed: {self._tests_passed}")
  1116	
  1117	        tests_failed_match = self._match_pattern(self.TESTS_FAILED_PATTERN, message)
  1118	        if tests_failed_match:
  1119	            self._tests_failed = int(tests_failed_match.group(1))
  1120	            logger.debug(f"Tests failed: {self._tests_failed}")
  1121	
  1122	        # Parse pytest summary output (e.g., "===== 5 passed, 2 failed in 0.23s =====")
  1123	        pytest_summary_match = self._match_pattern(self.PYTEST_SUMMARY_PATTERN, message)
  1124	        if pytest_summary_match:
  1125	            if pytest_summary_match.group(1):
  1126	                passed_count = int(pytest_summary_match.group(1))
  1127	                if self._tests_passed is None or passed_count > self._tests_passed:
  1128	                    self._tests_passed = passed_count
  1129	                    logger.debug(f"Pytest summary - tests passed: {self._tests_passed}")
  1130	            if pytest_summary_match.group(2):
  1131	                failed_count = int(pytest_summary_match.group(2))
  1132	                if self._tests_failed is None or failed_count > self._tests_failed:
  1133	                    self._tests_failed = failed_count
  1134	                    logger.debug(f"Pytest summary - tests failed: {self._tests_failed}")
  1135	            # TASK-AB-SKIPVIS01: advisory skip count, derived from an
  1136	            # INDEPENDENT token search over the matched summary line — never
  1137	            # from the positional group(3), which only matches in
  1138	            # passed-then-failed adjacency and so misses the skip token on
  1139	            # every failing-run summary (pytest orders failed before passed:
  1140	            # "2 failed, 3 passed, 1 skipped"). Tri-state contract: None =
  1141	            # no parseable summary ever seen (unknown stays unknown, never
  1142	            # 0-coerced); 0 = a summary matched cleanly and carries no
  1143	            # 'skipped' token; N = N skipped.
  1144	            skipped_token_match = self.PYTEST_SKIPPED_TOKEN_PATTERN.search(
  1145	                pytest_summary_match.group(0)
  1146	            )
  1147	            if skipped_token_match:
  1148	                skipped_count = int(skipped_token_match.group(1))
  1149	                if self._tests_skipped is None or skipped_count > self._tests_skipped:
  1150	                    self._tests_skipped = skipped_count
  1151	                    logger.debug(f"Pytest summary - tests skipped: {self._tests_skipped}")
  1152	            elif pytest_summary_match.group(1) or pytest_summary_match.group(2):
  1153	                # A cleanly parsed summary (it carried a passed/failed count)
  1154	                # with no skip token is positively zero skips (0).
  1155	                if self._tests_skipped is None:
  1156	                    self._tests_skipped = 0
  1157	
  1158	        # Also try simpler pytest pattern (e.g., "5 passed in 0.23s")
  1159	        if self._tests_passed is None:
  1160	            simple_match = self._match_pattern(self.PYTEST_SIMPLE_PATTERN, message)
  1161	            if simple_match:
  1162	                self._tests_passed = int(simple_match.group(1))
  1163	                logger.debug(f"Pytest simple - tests passed: {self._tests_passed}")
  1164	
  1165	        # Coverage
  1166	        coverage_match = self._match_pattern(self.COVERAGE_PATTERN, message)
  1167	        if coverage_match:
  1168	            self._coverage = float(coverage_match.group(1))
  1169	            logger.debug(f"Coverage: {self._coverage}%")
  1170	
  1171	        # Quality gates
  1172	        if self._match_pattern(self.QUALITY_GATES_PASSED_PATTERN, message):
  1173	            self._quality_gates_passed = True
  1174	            logger.debug("Quality gates: PASSED")
  1175	        elif self._match_pattern(self.QUALITY_GATES_FAILED_PATTERN, message):
  1176	            self._quality_gates_passed = False
  1177	            logger.debug("Quality gates: FAILED")
  1178	
  1179	        # File modifications (use sets to avoid duplicates)
  1180	        for file_match in self.FILES_MODIFIED_PATTERN.finditer(message):
  1181	            file_path = file_match.group(1)
  1182	            if self._is_valid_file_path(file_path):
  1183	                self._files_modified.add(file_path)
  1184	                logger.debug(f"File modified: {file_path}")
  1185	
  1186	        for file_match in self.FILES_CREATED_PATTERN.finditer(message):
  1187	            file_path = file_match.group(1)
  1188	            if self._is_valid_file_path(file_path):
  1189	                self._files_created.add(file_path)
  1190	                logger.debug(f"File created: {file_path}")
  1191	
  1192	        # Architectural review scores
  1193	        arch_score_match = self._match_pattern(self.ARCH_SCORE_PATTERN, message)
  1194	        if arch_score_match:
  1195	            try:
  1196	                self._arch_score = int(arch_score_match.group(1))
  1197	                logger.debug(f"Architectural review score: {self._arch_score}")
  1198	            except ValueError:
  1199	                logger.warning(f"Invalid arch score format: {arch_score_match.group(1)}")
  1200	
  1201	        subscores_match = self._match_pattern(self.ARCH_SUBSCORES_PATTERN, message)
  1202	        if subscores_match:
  1203	            try:
  1204	                self._solid_score = int(subscores_match.group(1))
  1205	                self._dry_score = int(subscores_match.group(2))
  1206	                self._yagni_score = int(subscores_match.group(3))
  1207	                logger.debug(f"SOLID: {self._solid_score}, DRY: {self._dry_score}, YAGNI: {self._yagni_score}")
  1208	            except ValueError:
  1209	                logger.warning(f"Invalid subscore format in: {message}")
  1210	
  1211	    def to_result(self) -> Dict[str, Any]:
  1212	        """Convert accumulated state to a result dictionary.
  1213	
  1214	        Returns:
  1215	            Dictionary containing all parsed quality gate information:
  1216	            - phases: Dict of detected phases with completion status
  1217	            - tests_passed: Number of tests that passed (or None)
  1218	            - tests_failed: Number of tests that failed (or None)
  1219	            - tests_skipped: Advisory skip count (omitted when no parseable
  1220	              pytest summary was seen — unknown stays unknown; TASK-AB-SKIPVIS01)
  1221	            - coverage: Coverage percentage (or None)
  1222	            - quality_gates_passed: Boolean or None if not detected
  1223	            - files_modified: List of modified file paths
  1224	            - files_created: List of created file paths
  1225	            - test_files_created: List of test file paths created
  1226	            - architectural_review: Dict with score and optional SOLID/DRY/YAGNI
  1227	              subscores (or absent if no arch review score found)
  1228	        """
  1229	        result: Dict[str, Any] = {}
  1230	
  1231	        if self._phases:
  1232	            result["phases"] = self._phases
  1233	
  1234	        if self._tests_passed is not None:
  1235	            result["tests_passed"] = self._tests_passed
  1236	
  1237	        if self._tests_failed is not None:
  1238	            result["tests_failed"] = self._tests_failed
  1239	
  1240	        # TASK-AB-SKIPVIS01: advisory only. Omitted when None (no parseable
  1241	        # pytest summary) — mirrors tests_passed/tests_failed absence handling.
  1242	        if self._tests_skipped is not None:
  1243	            result["tests_skipped"] = self._tests_skipped
  1244	
  1245	        if self._coverage is not None:
  1246	            result["coverage"] = self._coverage
  1247	
  1248	        if self._quality_gates_passed is not None:
  1249	            result["quality_gates_passed"] = self._quality_gates_passed
  1250	
  1251	        if self._files_modified:
  1252	            result["files_modified"] = sorted(list(self._files_modified))
  1253	
  1254	        if self._files_created:
  1255	            result["files_created"] = sorted(list(self._files_created))
  1256	
  1257	        # TASK-FIX-CC-COND: emit files_authored only when non-empty
  1258	        # (parity with files_modified/files_created). The downstream
  1259	        # producer ``_write_task_work_results`` always persists the field
  1260	        # to disk (even as []) so Coach gets a positive presence signal
  1261	        # for the new contention-detection path.
  1262	        if self._files_authored:
  1263	            result["files_authored"] = sorted(list(self._files_authored))
  1264	
  1265	        if self._test_files_created:
  1266	            result["test_files_created"] = sorted(list(self._test_files_created))
  1267	
  1268	        if self._arch_score is not None:
  1269	            arch_review: Dict[str, Any] = {"score": self._arch_score}
  1270	            if self._solid_score is not None:
  1271	                arch_review["solid"] = self._solid_score
  1272	            if self._dry_score is not None:
  1273	                arch_review["dry"] = self._dry_score
  1274	            if self._yagni_score is not None:
  1275	                arch_review["yagni"] = self._yagni_score
  1276	            result["architectural_review"] = arch_review
  1277	
  1278	        return result
  1279	
  1280	    def reset(self) -> None:
  1281	        """Reset parser state for reuse.
  1282	
  1283	        Clears all accumulated state, allowing the parser to be reused
  1284	        for a new stream.
  1285	        """
  1286	        self._phases = {}
  1287	        self._tests_passed = None
  1288	        self._tests_failed = None
  1289	        self._tests_skipped = None
  1290	        self._coverage = None
  1291	        self._quality_gates_passed = None
  1292	        self._files_modified = set()
  1293	        self._files_created = set()
  1294	        self._files_authored = set()
  1295	        self._test_files_created = set()
  1296	        self._arch_score = None
  1297	        self._solid_score = None
  1298	        self._dry_score = None
  1299	        self._yagni_score = None
  1300	
  1301	
  1302	@dataclass
  1303	class AgentInvocationResult:
  1304	    """Result of an agent invocation.
  1305	
  1306	    Attributes:
  1307	        task_id: Task identifier (e.g., "TASK-001")
  1308	        turn: Turn number (1-based)
  1309	        agent_type: "player" or "coach"
  1310	        success: True if invocation succeeded
  1311	        report: Parsed JSON from agent
  1312	        duration_seconds: Time taken for invocation
  1313	        error: Error message if failed
  1314	    """
  1315	
  1316	    task_id: str
  1317	    turn: int
  1318	    agent_type: str  # "player" or "coach"
  1319	    success: bool
  1320	    report: Dict[str, Any]
  1321	    duration_seconds: float
  1322	    error: Optional[str] = None
  1323	    sdk_turns_used: Optional[int] = None      # TASK-VPR-003: Actual SDK turns from ResultMessage
  1324	    sdk_max_turns: Optional[int] = None        # TASK-VPR-003: Effective SDK turn ceiling
  1325	    sdk_ceiling_hit: bool = False              # TASK-VPR-003: Whether ceiling was hit
  1326	    session_id: Optional[str] = None           # TASK-RFX-B20B: SDK session ID for resumption
  1327	
  1328	
  1329	class AgentInvoker:
  1330	    """Handles Claude Agents SDK invocation for Player and Coach agents.
  1331	
  1332	    This class is the bridge between the orchestration layer and AI agents,
  1333	    managing agent sessions, context preparation, and response handling.
  1334	
  1335	    Key Responsibilities:
  1336	    - Invoke Player and Coach agents via Claude Agents SDK
  1337	    - Manage fresh context per turn (no context pollution)
  1338	    - Handle SDK integration with appropriate permissions per agent type
  1339	    - Parse and validate agent responses (JSON reports)
  1340	    - Provide error handling and timeout management
  1341	    - Support async/await pattern for concurrent operations
  1342	
  1343	    Example:
  1344	        >>> invoker = AgentInvoker(
  1345	        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
  1346	        ...     max_turns_per_agent=30,
  1347	        ... )
  1348	        >>> result = await invoker.invoke_player(
  1349	        ...     task_id="TASK-001",
  1350	        ...     turn=1,
  1351	        ...     requirements="Implement OAuth2 authentication",
  1352	        ... )
  1353	        >>> assert result.success
  1354	        >>> assert result.report["tests_passed"]
  1355	    """
  1356	
  1357	    # Class-level lock to serialise git operations across parallel tasks (TASK-FIX-VL04)
  1358	    _git_lock = threading.RLock()
  1359	
  1360	    def __init__(
  1361	        self,
  1362	        worktree_path: Path,
  1363	        max_turns_per_agent: int = 30,
  1364	        sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT,
  1365	        use_task_work_delegation: Optional[bool] = None,
  1366	        development_mode: str = "tdd",
  1367	        cancellation_event: Optional[threading.Event] = None,
  1368	        timeout_multiplier: Optional[float] = None,
  1369	        emitter: Optional[Any] = None,
  1370	        venv_python: Optional[str] = None,
  1371	        model_name: Optional[str] = None,  # TASK-FIX-MODELPLUMB
  1372	        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
  1373	        evidence_repos: Optional[List["EvidenceRepo"]] = None,  # TASK-AB-XREPOEV01
  1374	    ):
  1375	        """Initialize AgentInvoker.
  1376	
  1377	        Model selection strategy: Both Player and Coach models are delegated
  1378	        to the bundled Claude CLI default. The CLI default (currently
  1379	        claude-sonnet-4-6) must match the vLLM SERVED_MODEL_NAME when using
  1380	        local inference. See docs/guides/simple-local-autobuild.md for details.
  1381	
  1382	        Args:
  1383	            worktree_path: Path to the isolated git worktree
  1384	            max_turns_per_agent: Maximum turns per agent invocation (default: 30)
  1385	            sdk_timeout_seconds: Timeout for SDK invocations (default: 1200s)
  1386	            use_task_work_delegation: If True, delegate Player to task-work instead of
  1387	                direct SDK. Defaults to USE_TASK_WORK_DELEGATION env var.
  1388	            development_mode: Development mode for implementation (default: "tdd").
  1389	                Valid values: "standard", "tdd", "bdd"
  1390	            cancellation_event: Cooperative cancellation signal from FeatureOrchestrator
  1391	                (default: None). When set, _invoke_with_role() monitors the event and
  1392	                terminates the SDK subprocess if cancellation is requested.
  1393	                (TASK-FIX-ASPF-004)
  1394	            timeout_multiplier: Multiplier for all timeout values (default: auto-detect).
  1395	                When None, auto-detects from ANTHROPIC_BASE_URL (4.0 for localhost).
  1396	                (TASK-FIX-VL05)
  1397	            emitter: Optional EventEmitter for instrumentation telemetry.
  1398	                Defaults to NullEmitter() when not provided (zero behaviour change
  1399	                for existing callers). (TASK-INST-005b)
  1400	            venv_python: Optional path to the Python interpreter Coach should
  1401	                use when invoking pytest. Typically
  1402	                ``BootstrapResult.venv_python`` threaded from the feature
  1403	                orchestrator. When None, CoachVerifier falls back to
  1404	                filesystem discovery and then PATH pytest. (TASK-FIX-7A05)
  1405	            evidence_repos: Resolved sibling repos whose writes count as task
  1406	                evidence (TASK-AB-XREPOEV01). Default None -> empty -> zero
  1407	                behaviour change; the evidence boundary stays scoped to the
  1408	                worktree. When populated, the post-turn diff merges per-repo
  1409	                git changes into the Player report as repo-qualified paths
  1410	                (``<repo>:<path>``) and CoachVerifier resolves those claims
  1411	                against the right repo root.
  1412	        """
  1413	        self.worktree_path = Path(worktree_path)
  1414	        self._venv_python: Optional[str] = venv_python
  1415	        self.max_turns_per_agent = max_turns_per_agent
  1416	        self.sdk_timeout_seconds = sdk_timeout_seconds
  1417	        self._sdk_timeout_is_override = sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT
  1418	        self.timeout_multiplier = (
  1419	            timeout_multiplier if timeout_multiplier is not None
  1420	            else detect_timeout_multiplier()
  1421	        )
  1422	        self.use_task_work_delegation = (
  1423	            use_task_work_delegation if use_task_work_delegation is not None
  1424	            else USE_TASK_WORK_DELEGATION
  1425	        )
  1426	        self.development_mode = development_mode
  1427	        self._cancellation_event: Optional[threading.Event] = cancellation_event
  1428	        # TASK-FIX-SPECHANG2: monotonic timestamp of the most recent
  1429	        # model-stream event observed inside ``_invoke_with_role``. Read by
  1430	        # the specialist no-model-activity watchdog
  1431	        # (``specialist_invocations.py``) to distinguish a genuine agent hang
  1432	        # (zero ``/v1/responses`` traffic for N seconds) from a slow-but-
  1433	        # progressing run. ``0.0`` until the first invocation resets it.
  1434	        self._last_activity_monotonic: float = 0.0
  1435	        self._baseline_commit: Optional[str] = None
  1436	        # TASK-AB-XREPOEV01: declared sibling repos whose writes count as task
  1437	        # evidence (default empty -> undeclared sibling-repo writes stay
  1438	        # invisible, AC-003). Per-repo HEAD baselines are recorded alongside
  1439	        # the worktree baseline so the post-turn diff attributes only this
  1440	        # task's sibling-repo writes.
  1441	        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
  1442	        self._evidence_baselines: Dict[str, Optional[str]] = {}
  1443	        # TASK-FIX-OBS2: Per-task progress logger for parallel execution diagnostics
  1444	        self._progress_logger: Optional["TaskProgressLogger"] = None
  1445	        # TASK-CRV-1540: Partial data extracted from response_messages on CancelledError
  1446	        self._last_partial_report: Optional[Dict[str, Any]] = None
  1447	        # TASK-RFX-B20B: Last captured session_id from ResultMessage for resume
  1448	        self._last_session_id: Optional[str] = None
  1449	        # TASK-INST-005b: EventEmitter for instrumentation telemetry
  1450	        self._emitter = emitter if emitter is not None else NullEmitter()
  1451	        # TASK-FIX-MODELPLUMB: default model identifier for invocations that
  1452	        # don't specify one. Threaded from the CLI --model flag through
  1453	        # AutoBuildOrchestrator. Used as a fallback inside _invoke_with_role
  1454	        # when the per-call model kwarg is None — load-bearing for the
  1455	        # LangGraph harness (DeepAgents.create_deep_agent fails with
  1456	        # "'function' object has no attribute 'name'" when model=None);
  1457	        # decorative-but-harmless for the SDK path (routes via
  1458	        # ANTHROPIC_BASE_URL).
  1459	        self._model_name: Optional[str] = model_name
  1460	        # TASK-FIX-COACHBUDG01 (2026-06-06): optional per-role override for
  1461	        # Coach. When non-None, `_invoke_with_role` uses this for role='coach'
  1462	        # and role='coach_test' invocations; Player and specialist roles stay
  1463	        # on `_model_name`. None preserves pre-COACHBUDG01 behaviour (Coach
  1464	        # shares Player's model). Sibling pattern to LGFM3 which threaded the
  1465	        # model_name kwarg through CoachValidator's SDK test-exec path; the
  1466	        # difference here is that LGFM3 unified model selection across all
  1467	        # roles while COACHBUDG01 allows per-role divergence (the load-bearing
  1468	        # mechanic for swapping Coach to gemma4:26b while Player stays on
  1469	        # qwen36-workhorse — TASK-HMIG-013).
  1470	        self._coach_model_name: Optional[str] = coach_model_name
  1471	
  1472	        if self.timeout_multiplier != 1.0:
  1473	            logger.info(
  1474	                f"Timeout multiplier: {self.timeout_multiplier}x "
  1475	                f"(sdk_timeout base={self.sdk_timeout_seconds}s → "
  1476	                f"effective max={int(MAX_SDK_TIMEOUT * self.timeout_multiplier)}s)"
  1477	            )
  1478	
  1479	        # TASK-FIX-7718: Auto-reduce SDK max turns for local backends.
  1480	        # TASK-ABSR-MAXT: This field is now used only by the legacy direct-mode
  1481	        # path (`_invoke_player_direct`). The task-work invocation path uses the
  1482	        # per-task complexity-scaled value from `_calculate_sdk_max_turns(task_id)`
  1483	        # instead, so each task gets a turn budget proportional to its complexity.
  1484	        if not _SDK_MAX_TURNS_IS_OVERRIDE and self.timeout_multiplier > 1.0:
  1485	            self._effective_sdk_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 100)
  1486	            logger.info(
  1487	                "SDK max turns reduced to %d for local backend "
  1488	                "(timeout_multiplier=%.1f)",
  1489	                self._effective_sdk_max_turns,
  1490	                self.timeout_multiplier,
  1491	            )
  1492	        else:
  1493	            self._effective_sdk_max_turns = TASK_WORK_SDK_MAX_TURNS
  1494	
  1495	    # =========================================================================
  1496	    # Per-Task Progress Logging (TASK-FIX-OBS2)
  1497	    # =========================================================================
  1498	
  1499	    def set_progress_logger(self, progress_logger: Optional[Any]) -> None:
  1500	        """Set the per-task progress logger for parallel execution diagnostics.
  1501	
  1502	        Parameters
  1503	        ----------
  1504	        progress_logger : Optional[TaskProgressLogger]
  1505	            Progress logger instance, or None to disable.
  1506	        """
  1507	        self._progress_logger = progress_logger
  1508	
  1509	    def _track_tool_use(self, event: "ToolUseEvent") -> None:
  1510	        """Track a single tool-use event for progress logging.
  1511	
  1512	        TASK-HMIG-006.2 migration: the previous signature accepted the SDK
  1513	        ``AssistantMessage`` and walked its content blocks for
  1514	        ``ToolUseBlock`` instances. Both harnesses now yield a
  1515	        :class:`ToolUseEvent` per tool call, so this helper consumes one
  1516	        typed event per call and the AssistantMessage content walk is gone.
  1517	
  1518	        Parameters
  1519	        ----------
  1520	        event : ToolUseEvent
  1521	            Typed tool-use event yielded by the active harness.
  1522	        """
  1523	        if not self._progress_logger:
  1524	            return
  1525	        try:
  1526	            name = event.name
  1527	            self._progress_logger._last_tool = name
  1528	            if name in ("Write", "Edit"):
  1529	                self._progress_logger._files_changed += 1
  1530	        except Exception:
  1531	            pass  # Never crash orchestration for progress tracking
  1532	
  1533	    # =========================================================================
  1534	    # Path Resolution Helpers (TASK-FIX-VL01)
  1535	    # =========================================================================
  1536	
  1537	    def _resolve_repo_root(self) -> Optional[Path]:
  1538	        """Resolve the main repository root from the worktree path.
  1539	
  1540	        In a git worktree setup, worktrees are located at:
  1541	            {repo_root}/.guardkit/worktrees/{task_or_feature_id}/
  1542	
  1543	        If the current worktree_path follows this convention, the repo root
  1544	        is derived by stripping the ``.guardkit/worktrees/...`` suffix.
  1545	
  1546	        Returns ``None`` when worktree_path IS the repo root (no fallback
  1547	        needed) or when the path doesn't match the worktree convention.
  1548	        """
  1549	        worktree_str = str(self.worktree_path)
  1550	        marker = os.sep + ".guardkit" + os.sep + "worktrees" + os.sep
  1551	        idx = worktree_str.find(marker)
  1552	        if idx >= 0:
  1553	            return Path(worktree_str[:idx])
  1554	        return None
  1555	
  1556	    # =========================================================================
  1557	    # Session Resume Support (TASK-RFX-B20B)
  1558	    # =========================================================================
  1559	
  1560	    def set_player_resume_session(self, session_id: Optional[str]) -> None:
  1561	        """Set session ID for the next Player invocation to resume from.
  1562	
  1563	        Called by the orchestrator between turns to enable session continuity.
  1564	        Pass None to start a fresh session (no resume).
  1565	
  1566	        Args:
  1567	            session_id: SDK session ID from a previous ResultMessage, or None.
  1568	        """
  1569	        self._last_session_id = session_id
  1570	
  1571	    # =========================================================================
  1572	    # Cancellation Support (TASK-FIX-ASPF-004)
  1573	    # =========================================================================
  1574	
  1575	    def cancel(self) -> None:
  1576	        """Cancel any in-progress SDK invocation.
  1577	
  1578	        Sets the cancellation event (if present) and terminates any child
  1579	        ``claude`` processes spawned by the SDK. This bridges the gap between
  1580	        asyncio cancellation (which only cancels the wrapper) and the actual
  1581	        OS subprocess that the SDK spawns.
  1582	
  1583	        Safe to call from any thread.
  1584	        """
  1585	        if self._cancellation_event:
  1586	            self._cancellation_event.set()
  1587	        self._kill_child_claude_processes()
  1588	
  1589	    def _kill_child_claude_processes(self) -> None:
  1590	        """Find and SIGTERM child ``claude`` CLI processes.
  1591	
  1592	        Uses ``/proc/{pid}/status`` on Linux to walk the process tree from
  1593	        the current PID, looking for children whose ``Name:`` field contains
  1594	        ``claude`` or ``node`` (the Claude CLI runs as a Node.js process).
  1595	
  1596	        Handles:
  1597	        - ``ProcessLookupError`` for processes that exit between enumeration
  1598	          and signal delivery.
  1599	        - ``PermissionError`` for processes we cannot signal.
  1600	        - Non-Linux platforms where ``/proc`` is unavailable (logs warning).
  1601	        """
  1602	        my_pid = os.getpid()
  1603	        proc_path = Path("/proc")
  1604	
  1605	        if not proc_path.exists():
  1606	            self._kill_child_processes_fallback(my_pid)
  1607	            return
  1608	
  1609	        killed = []
  1610	        try:
  1611	            for entry in proc_path.iterdir():
  1612	                if not entry.name.isdigit():
  1613	                    continue
  1614	                pid = int(entry.name)
  1615	                if pid == my_pid:
  1616	                    continue
  1617	
  1618	                status_file = entry / "status"
  1619	                try:
  1620	                    status_text = status_file.read_text()
  1621	                except (OSError, PermissionError):
  1622	                    continue
  1623	
  1624	                # Check if this process is a child of our process tree
  1625	                ppid_line = None
  1626	                name_line = None
  1627	                for line in status_text.splitlines():
  1628	                    if line.startswith("PPid:"):
  1629	                        ppid_line = line.split(":", 1)[1].strip()
  1630	                    if line.startswith("Name:"):
  1631	                        name_line = line.split(":", 1)[1].strip()
  1632	
  1633	                if ppid_line is None or name_line is None:
  1634	                    continue
  1635	
  1636	                # Walk up the process tree to see if this is a descendant
  1637	                # of our process. Check both direct children and grandchildren
  1638	                # (SDK spawns node which spawns claude).
  1639	                if not self._is_descendant_of(pid, my_pid):
  1640	                    continue
  1641	
  1642	                # Match claude or node processes (Claude CLI runs as node)
  1643	                if "claude" in name_line.lower() or "node" in name_line.lower():
  1644	                    try:
  1645	                        os.kill(pid, signal.SIGTERM)
  1646	                        killed.append((pid, name_line))
  1647	                        logger.info(
  1648	                            f"TASK-FIX-ASPF-004: Sent SIGTERM to child process "
  1649	                            f"pid={pid} name={name_line}"
  1650	                        )
  1651	                    except ProcessLookupError:
  1652	                        logger.debug(
  1653	                            f"TASK-FIX-ASPF-004: Process pid={pid} already exited"
  1654	                        )
  1655	                    except PermissionError:
  1656	                        logger.warning(
  1657	                            f"TASK-FIX-ASPF-004: Permission denied sending SIGTERM "
  1658	                            f"to pid={pid} name={name_line}"
  1659	                        )
  1660	        except OSError as e:
  1661	            logger.warning(f"TASK-FIX-ASPF-004: Error scanning /proc: {e}")
  1662	
  1663	        if killed:
  1664	            logger.info(
  1665	                f"TASK-FIX-ASPF-004: Terminated {len(killed)} child process(es): "
  1666	                f"{[(pid, name) for pid, name in killed]}"
  1667	            )
  1668	        else:
  1669	            logger.debug("TASK-FIX-ASPF-004: No child claude processes found to kill")
  1670	
  1671	    @staticmethod
  1672	    def _is_descendant_of(pid: int, ancestor_pid: int, max_depth: int = 10) -> bool:
  1673	        """Check if ``pid`` is a descendant of ``ancestor_pid`` via /proc.
  1674	
  1675	        Walks the PPid chain up to ``max_depth`` levels to avoid infinite
  1676	        loops from corrupted /proc data.
  1677	
  1678	        Args:
  1679	            pid: Process ID to check.
  1680	            ancestor_pid: Potential ancestor process ID.
  1681	            max_depth: Maximum depth to walk up the tree (default: 10).
  1682	
  1683	        Returns:
  1684	            True if ``pid`` is a descendant of ``ancestor_pid``.
  1685	        """
  1686	        current = pid
  1687	        for _ in range(max_depth):
  1688	            try:
  1689	                status_text = Path(f"/proc/{current}/status").read_text()
  1690	            except (OSError, PermissionError):
  1691	                return False
  1692	            for line in status_text.splitlines():
  1693	                if line.startswith("PPid:"):
  1694	                    ppid = int(line.split(":", 1)[1].strip())
  1695	                    if ppid == ancestor_pid:
  1696	                        return True
  1697	                    if ppid <= 1:
  1698	                        return False  # Reached init/systemd
  1699	                    current = ppid
  1700	                    break
  1701	            else:
  1702	                return False  # No PPid line found
  1703	        return False
  1704	
  1705	    def _kill_child_processes_fallback(self, my_pid: int) -> None:
  1706	        """Kill child claude processes on non-Linux platforms.
  1707	
  1708	        Tries ``psutil`` first (optional dependency), then falls back to
  1709	        ``pgrep`` + ``ps`` which are available on macOS and most BSDs.
  1710	        """
  1711	        try:
  1712	            import psutil
  1713	            self._kill_child_processes_psutil(my_pid, psutil)
  1714	        except ImportError:
  1715	            logger.debug(
  1716	                "TASK-FIX-DFCB: psutil not available, falling back to pgrep"
  1717	            )
  1718	            self._kill_child_processes_pgrep(my_pid)
  1719	
  1720	    def _kill_child_processes_psutil(self, my_pid: int, psutil_mod: Any) -> None:
  1721	        """Kill child claude/node processes using psutil.
  1722	
  1723	        Args:
  1724	            my_pid: Current process ID.
  1725	            psutil_mod: The ``psutil`` module (passed to avoid top-level import).
  1726	        """
  1727	        killed: list = []
  1728	        try:
  1729	            parent = psutil_mod.Process(my_pid)
  1730	            for child in parent.children(recursive=True):
  1731	                try:
  1732	                    name = child.name().lower()
  1733	                    if "claude" not in name and "node" not in name:
  1734	                        continue
  1735	                    child.terminate()
  1736	                    killed.append((child.pid, child.name()))
  1737	                    logger.info(
  1738	                        f"TASK-FIX-DFCB: Sent SIGTERM to child process "
  1739	                        f"pid={child.pid} name={child.name()} (via psutil)"
  1740	                    )
  1741	                except (psutil_mod.NoSuchProcess, psutil_mod.AccessDenied) as exc:
  1742	                    logger.debug(
  1743	                        f"TASK-FIX-DFCB: Could not signal process: {exc}"
  1744	                    )
  1745	        except (psutil_mod.NoSuchProcess, psutil_mod.AccessDenied) as exc:
  1746	            logger.warning(
  1747	                f"TASK-FIX-DFCB: Error accessing process tree via psutil: {exc}"
  1748	            )
  1749	
  1750	        if killed:
  1751	            logger.info(
  1752	                f"TASK-FIX-DFCB: Terminated {len(killed)} child process(es) "
  1753	                f"via psutil: {killed}"
  1754	            )
  1755	        else:
  1756	            logger.debug(
  1757	                "TASK-FIX-DFCB: No child claude processes found (psutil)"
  1758	            )
  1759	
  1760	    def _kill_child_processes_pgrep(self, my_pid: int) -> None:
  1761	        """Kill child claude/node processes using ``pgrep`` and ``ps``.
  1762	
  1763	        Fallback for macOS/BSD when ``psutil`` is not installed.
  1764	        Uses ``pgrep -P <pid>`` to find children and grandchildren,
  1765	        then ``ps -p <pid> -o comm=`` to check process names.
  1766	        """
  1767	        import subprocess as sp
  1768	
  1769	        killed: list = []
  1770	        try:
  1771	            # Find direct children
  1772	            result = sp.run(
  1773	                ["pgrep", "-P", str(my_pid)],
  1774	                capture_output=True, text=True, timeout=5,
  1775	            )
  1776	            if result.returncode != 0:
  1777	                logger.debug(
  1778	                    "TASK-FIX-DFCB: pgrep found no child processes"
  1779	                )
  1780	                return
  1781	
  1782	            child_pids = [
  1783	                int(p) for p in result.stdout.strip().splitlines() if p.strip()
  1784	            ]
  1785	
  1786	            # Also collect grandchildren (SDK -> node -> claude)
  1787	            all_pids: set = set(child_pids)
  1788	            for cpid in child_pids:
  1789	                gc_result = sp.run(
  1790	                    ["pgrep", "-P", str(cpid)],
  1791	                    capture_output=True, text=True, timeout=5,
  1792	                )
  1793	                if gc_result.returncode == 0:
  1794	                    for line in gc_result.stdout.strip().splitlines():
  1795	                        if line.strip():
  1796	                            all_pids.add(int(line.strip()))
  1797	
  1798	            # Check each process name and kill claude/node matches
  1799	            for pid in all_pids:
  1800	                try:
  1801	                    ps_result = sp.run(
  1802	                        ["ps", "-p", str(pid), "-o", "comm="],
  1803	                        capture_output=True, text=True, timeout=5,
  1804	                    )
  1805	                    if ps_result.returncode != 0:
  1806	                        continue
  1807	                    name = ps_result.stdout.strip().lower()
  1808	                    if "claude" not in name and "node" not in name:
  1809	                        continue
  1810	                    os.kill(pid, signal.SIGTERM)
  1811	                    killed.append((pid, name))
  1812	                    logger.info(
  1813	                        f"TASK-FIX-DFCB: Sent SIGTERM to child process "
  1814	                        f"pid={pid} name={name} (via pgrep)"
  1815	                    )
  1816	                except ProcessLookupError:
  1817	                    logger.debug(
  1818	                        f"TASK-FIX-DFCB: Process pid={pid} already exited"
  1819	                    )
  1820	                except PermissionError:
  1821	                    logger.warning(
  1822	                        f"TASK-FIX-DFCB: Permission denied sending SIGTERM "
  1823	                        f"to pid={pid}"
  1824	                    )
  1825	        except FileNotFoundError:
  1826	            logger.warning(
  1827	                "TASK-FIX-DFCB: pgrep not found on this platform, "
  1828	                "cannot kill child claude processes"
  1829	            )
  1830	        except sp.TimeoutExpired:
  1831	            logger.warning("TASK-FIX-DFCB: pgrep timed out")
  1832	        except OSError as exc:
  1833	            logger.warning(f"TASK-FIX-DFCB: Error running pgrep: {exc}")
  1834	
  1835	        if killed:
  1836	            logger.info(
  1837	                f"TASK-FIX-DFCB: Terminated {len(killed)} child process(es) "
  1838	                f"via pgrep: {killed}"
  1839	            )
  1840	        else:
  1841	            logger.debug(
  1842	                "TASK-FIX-DFCB: No child claude processes found (pgrep)"
  1843	            )
  1844	
  1845	    async def invoke_player(
  1846	        self,
  1847	        task_id: str,
  1848	        turn: int,
  1849	        requirements: str,
  1850	        feedback: Optional[Union[str, Dict[str, Any]]] = None,
  1851	        mode: Optional[str] = None,
  1852	        max_turns: int = 5,
  1853	        documentation_level: str = "minimal",
  1854	        context: str = "",
  1855	        remaining_budget: Optional[float] = None,
  1856	    ) -> AgentInvocationResult:
  1857	        """Invoke Player agent via task-work delegation or Claude Agents SDK.
  1858	
  1859	        When task-work delegation is enabled (use_task_work_delegation=True),
  1860	        the Player delegates to `guardkit task-work --implement-only` which
  1861	        leverages the full subagent infrastructure.
  1862	
  1863	        When delegation is disabled (legacy mode), uses direct SDK invocation.
  1864	
  1865	        The Player agent:
  1866	        - Has full file system access (Read, Write, Edit, Bash)
  1867	        - Works in isolated worktree
  1868	        - Implements code and writes tests
  1869	        - Creates JSON report at .guardkit/autobuild/{task_id}/player_turn_{turn}.json
  1870	
  1871	        Args:
  1872	            task_id: Task identifier (e.g., "TASK-001")
  1873	            turn: Current turn number (1-based)
  1874	            requirements: Task requirements (from task markdown)
  1875	            feedback: Optional Coach feedback from previous turn (string or Coach decision dict)
  1876	            mode: Development mode ("standard", "tdd", or "bdd"), passed to task-work.
  1877	                If not provided, uses the instance's development_mode.
  1878	            max_turns: Maximum turns allowed for this orchestration (default: 5).
  1879	                Used to calculate approaching_limit flag for escape hatch pattern.
  1880	            documentation_level: Documentation level for file count constraint validation
  1881	                ("minimal", "standard", or "comprehensive"). Default: "minimal" for AutoBuild.
  1882	            context: Job-specific context from the memory backend (role constraints, quality gates,
  1883	                turn states). Included in Player prompt but kept separate from requirements.
  1884	                Default: "" (empty string, no context).
  1885	            remaining_budget: Optional remaining wall-clock budget in seconds.
  1886	                When provided, sdk_timeout_seconds is capped at this value for
  1887	                this invocation then restored. Used to honour per-turn budgets
  1888	                and prevent Player from starting turns it cannot finish. (TASK-VRF-003)
  1889	
  1890	        Returns:
  1891	            AgentInvocationResult with Player's report
  1892	
  1893	        Raises:
  1894	            AgentInvocationError: If invocation fails
  1895	            PlayerReportNotFoundError: If Player doesn't create report
  1896	            PlayerReportInvalidError: If report JSON is malformed
  1897	            SDKTimeoutError: If invocation exceeds timeout
  1898	        """
  1899	        start_time = time.time()
  1900	
  1901	        # TASK-FIX-CAUD-PREFLIGHT-C3B0: Pre-turn-1 git check-ignore fail-fast
  1902	        # gate. Walks the task's planned target list through ``git
  1903	        # check-ignore`` in the worktree before any SDK turn runs. If a
  1904	        # planned target IS ignored, raises ``AgentInvocationError`` with
  1905	        # the exact matched rule so the operator can either rebase the
  1906	        # worktree (if the rule is from project-root .gitignore) or pick
  1907	        # a non-ignored target. Skipped when no plan or frontmatter list
  1908	        # is available (identical to the no-plan branch in plan-audit).
  1909	        if turn == 1:
  1910	            self._run_preflight_ignore_gate(task_id)
  1911	
  1912	        # TASK-FIX-VL06: Record baseline commit before SDK invocation
  1913	        # to prevent cross-task file attribution in parallel waves
  1914	        if self._baseline_commit is None:
  1915	            self._record_baseline()
  1916	
  1917	        # TASK-ASF-008: Calculate dynamic SDK timeout based on task characteristics
  1918	        # TASK-VRF-003: Cap SDK timeout at remaining budget (mirrors invoke_coach pattern)
  1919	        effective_timeout = self._calculate_sdk_timeout(task_id, remaining_budget=remaining_budget)
  1920	        original_timeout = self.sdk_timeout_seconds
  1921	        self.sdk_timeout_seconds = effective_timeout
  1922	
  1923	        # Use instance development_mode if mode not provided
  1924	        effective_mode = mode if mode is not None else self.development_mode
  1925	
  1926	        # Calculate if we're approaching the turn limit (escape hatch trigger)
  1927	        approaching_limit = turn >= max_turns - 1  # True when 2 or fewer turns remain
  1928	
  1929	        try:
  1930	            # Write turn context for Player to read (includes approaching_limit)
  1931	            self._write_turn_context(task_id, turn, max_turns, approaching_limit)
  1932	
  1933	            # Write Coach feedback for task-work to read (if present and not turn 1)
  1934	            if feedback and turn > 1:
  1935	                self._write_coach_feedback(task_id, turn, feedback)
  1936	
  1937	            # Route based on implementation_mode from task frontmatter
  1938	            # Direct mode tasks bypass task-work delegation (no plan required)
  1939	            impl_mode = self._get_implementation_mode(task_id)
  1940	            if impl_mode == "direct":
  1941	                logger.info(
  1942	                    f"Routing to direct Player path for {task_id} (implementation_mode=direct)"
  1943	                )
  1944	                return await self._invoke_player_direct(
  1945	                    task_id=task_id,
  1946	                    turn=turn,
  1947	                    requirements=requirements,
  1948	                    feedback=feedback,
  1949	                    max_turns=max_turns,
  1950	                    context=context,
  1951	                )
  1952	
  1953	            # Choose invocation method based on feature flag (task-work or legacy modes)
  1954	            if self.use_task_work_delegation:
  1955	                logger.info(
  1956	                    f"Invoking Player via task-work delegation for {task_id} (turn {turn})"
  1957	                )
  1958	
  1959	                # Ensure task is in design_approved state before delegation
  1960	                # This bridges AutoBuild state with task-work --implement-only requirements
  1961	                self._ensure_design_approved_state(task_id)
  1962	
  1963	                result = await self._invoke_task_work_implement(
  1964	                    task_id=task_id,
  1965	                    mode=effective_mode,
  1966	                    documentation_level=documentation_level,
  1967	                    turn=turn,
  1968	                    requirements=requirements,
  1969	                    feedback=feedback,
  1970	                    max_turns=max_turns,
  1971	                    context=context,
  1972	                )
  1973	
  1974	                duration = time.time() - start_time
  1975	
  1976	                if result.success:
  1977	                    # Create Player report from task-work results
  1978	                    # AgentInvoker._invoke_task_work_implement() writes task_work_results.json
  1979	                    # after parsing task-work output. This method transforms it to
  1980	                    # player_turn_{turn}.json format expected by the orchestrator.
  1981	                    self._create_player_report_from_task_work(task_id, turn, result)
  1982	
  1983	                    # Load the Player report from file (now exists)
  1984	                    report = self._load_agent_report(task_id, turn, "player")
  1985	                    self._validate_player_report(report)
  1986	
  1987	                    # TASK-VPR-003: Extract SDK turn data from TaskWorkResult
  1988	                    from guardkit.orchestrator.sdk_ceiling import detect_ceiling_hit
  1989	                    _sdk_turns_used = result.sdk_turns_used
  1990	                    _sdk_max_turns = result.sdk_max_turns
  1991	                    _sdk_ceiling_hit = detect_ceiling_hit(_sdk_turns_used, _sdk_max_turns)
  1992	
  1993	                    # TASK-VOPT-002: Per-turn timing instrumentation
  1994	                    logger.info(
  1995	                        "[%s] SDK invocation complete: %.1fs, %d SDK turns (%.1fs/turn avg)",
  1996	                        task_id, duration, _sdk_turns_used or 0,
  1997	                        duration / max(_sdk_turns_used or 0, 1),
  1998	                    )
  1999	
  2000	                    return AgentInvocationResult(
AI: [{'name': 'glob', 'args': {'pattern': '**/coach_validator.py'}, 'id': '5tZjz8n9ZwsGE7Tls6BQIjKVgooWLpWh', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 3500}, 'id': '6at5lVqt5ZEkd1LX0rfui5UgFHV77GIK', 'type': 'tool_call'}]
Tool:   3501	        # absent (ran=False) signal, not a pass.
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 3000}, 'id': 'NresegsApFYEP6sIKmIOxVKHll64S6gX', 'type': 'tool_call'}]
Tool:   3001	            contain ``task_type``, ``requires_infrastructure``,
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
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Implement behavioural_oracle discovery and execution in CoachValidator.gather_evidence', 'status': 'in_progress'}, {'content': 'Implement independence check for behavioural_oracle in CoachValidator.gather_evidence', 'status': 'pending'}, {'content': 'Verify AgentInvoker enforces hard gate for behavioural_oracle ran-and-failed outcomes using tests/orchestrator/test_behavioural_oracle_guard.py', 'status': 'pending'}]}, 'id': 'e50srXWSsvbCOEFbOTNgDG6xuzWgHEc6', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Implement behavioural_oracle discovery and execution in CoachValidator.gather_evidence', 'status': 'in_progress'}, {'content': 'Implement independence check for behavioural_oracle in CoachValidator.gather_evidence', 'status': 'pending'}, {'content': 'Verify AgentInvoker enforces hard gate for behavioural_oracle ran-and-failed outcomes using tests/orchestrator/test_behavioural_oracle_guard.py', 'status': 'pending'}]
AI: [{'name': 'grep', 'args': {'pattern': 'class CoachEvidenceBundle'}, 'id': 'pFz7SqKxo4pA9mcg649ejuOPaDSdnOHA', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_219e8132.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_a0a29240.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/state/TASK-HMIG-008R/implementation_plan.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 200}, 'id': 'BwiYhLNeUtnDxM3uGntLolLHSbZu6xkG', 'type': 'tool_call'}]
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
   101	    timed_out : bool
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 200, 'offset': 180}, 'id': 'CY6BRvVBJFxH9IwUOkLbNKgDaD4FuQEs', 'type': 'tool_call'}]
Tool:    181	    ----------
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
AI: [{'name': 'grep', 'args': {'pattern': 'behavioural_oracle'}, 'id': 'QN8tr7AopPHIhltK4SS9gwedqHVIw6si', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-002/coach_evidence_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-004/player_turn_1.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-004/task_work_results.json
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/features/FEAT-10AC.yaml
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.pytest_cache/v/cache/nodeids
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_219e8132.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_7899e677.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_a0a29240.md
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 3500}, 'id': 'HzWV2OzHNI2r84OVYMlIAcFbbrpe7l0f', 'type': 'tool_call'}]
Tool:   3501	        # absent (ran=False) signal, not a pass.
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 1800}, 'id': '6ttn8VP02PAOTyaIANzMbBmNSLrKX4nB', 'type': 'tool_call'}]
Tool:   1801	                    ps_result = sp.run(
  1802	                        ["ps", "-p", str(pid), "-o", "comm="],
  1803	                        capture_output=True, text=True, timeout=5,
  1804	                    )
  1805	                    if ps_result.returncode != 0:
  1806	                        continue
  1807	                    name = ps_result.stdout.strip().lower()
  1808	                    if "claude" not in name and "node" not in name:
  1809	                        continue
  1810	                    os.kill(pid, signal.SIGTERM)
  1811	                    killed.append((pid, name))
  1812	                    logger.info(
  1813	                        f"TASK-FIX-DFCB: Sent SIGTERM to child process "
  1814	                        f"pid={pid} name={name} (via pgrep)"
  1815	                    )
  1816	                except ProcessLookupError:
  1817	                    logger.debug(
  1818	                        f"TASK-FIX-DFCB: Process pid={pid} already exited"
  1819	                    )
  1820	                except PermissionError:
  1821	                    logger.warning(
  1822	                        f"TASK-FIX-DFCB: Permission denied sending SIGTERM "
  1823	                        f"to pid={pid}"
  1824	                    )
  1825	        except FileNotFoundError:
  1826	            logger.warning(
  1827	                "TASK-FIX-DFCB: pgrep not found on this platform, "
  1828	                "cannot kill child claude processes"
  1829	            )
  1830	        except sp.TimeoutExpired:
  1831	            logger.warning("TASK-FIX-DFCB: pgrep timed out")
  1832	        except OSError as exc:
  1833	            logger.warning(f"TASK-FIX-DFCB: Error running pgrep: {exc}")
  1834	
  1835	        if killed:
  1836	            logger.info(
  1837	                f"TASK-FIX-DFCB: Terminated {len(killed)} child process(es) "
  1838	                f"via pgrep: {killed}"
  1839	            )
  1840	        else:
  1841	            logger.debug(
  1842	                "TASK-FIX-DFCB: No child claude processes found (pgrep)"
  1843	            )
  1844	
  1845	    async def invoke_player(
  1846	        self,
  1847	        task_id: str,
  1848	        turn: int,
  1849	        requirements: str,
  1850	        feedback: Optional[Union[str, Dict[str, Any]]] = None,
  1851	        mode: Optional[str] = None,
  1852	        max_turns: int = 5,
  1853	        documentation_level: str = "minimal",
  1854	        context: str = "",
  1855	        remaining_budget: Optional[float] = None,
  1856	    ) -> AgentInvocationResult:
  1857	        """Invoke Player agent via task-work delegation or Claude Agents SDK.
  1858	
  1859	        When task-work delegation is enabled (use_task_work_delegation=True),
  1860	        the Player delegates to `guardkit task-work --implement-only` which
  1861	        leverages the full subagent infrastructure.
  1862	
  1863	        When delegation is disabled (legacy mode), uses direct SDK invocation.
  1864	
  1865	        The Player agent:
  1866	        - Has full file system access (Read, Write, Edit, Bash)
  1867	        - Works in isolated worktree
  1868	        - Implements code and writes tests
  1869	        - Creates JSON report at .guardkit/autobuild/{task_id}/player_turn_{turn}.json
  1870	
  1871	        Args:
  1872	            task_id: Task identifier (e.g., "TASK-001")
  1873	            turn: Current turn number (1-based)
  1874	            requirements: Task requirements (from task markdown)
  1875	            feedback: Optional Coach feedback from previous turn (string or Coach decision dict)
  1876	            mode: Development mode ("standard", "tdd", or "bdd"), passed to task-work.
  1877	                If not provided, uses the instance's development_mode.
  1878	            max_turns: Maximum turns allowed for this orchestration (default: 5).
  1879	                Used to calculate approaching_limit flag for escape hatch pattern.
  1880	            documentation_level: Documentation level for file count constraint validation
  1881	                ("minimal", "standard", or "comprehensive"). Default: "minimal" for AutoBuild.
  1882	            context: Job-specific context from the memory backend (role constraints, quality gates,
  1883	                turn states). Included in Player prompt but kept separate from requirements.
  1884	                Default: "" (empty string, no context).
  1885	            remaining_budget: Optional remaining wall-clock budget in seconds.
  1886	                When provided, sdk_timeout_seconds is capped at this value for
  1887	                this invocation then restored. Used to honour per-turn budgets
  1888	                and prevent Player from starting turns it cannot finish. (TASK-VRF-003)
  1889	
  1890	        Returns:
  1891	            AgentInvocationResult with Player's report
  1892	
  1893	        Raises:
  1894	            AgentInvocationError: If invocation fails
  1895	            PlayerReportNotFoundError: If Player doesn't create report
  1896	            PlayerReportInvalidError: If report JSON is malformed
  1897	            SDKTimeoutError: If invocation exceeds timeout
  1898	        """
  1899	        start_time = time.time()
  1900	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 2000}, 'id': 'bLmsAIhQYV5mxNBb8ZLOWDNvgGrGJnGT', 'type': 'tool_call'}]
Tool:   2001	                        task_id=task_id,
  2002	                        turn=turn,
  2003	                        agent_type="player",
  2004	                        success=True,
  2005	                        report=report,
  2006	                        duration_seconds=duration,
  2007	                        sdk_turns_used=_sdk_turns_used,
  2008	                        sdk_max_turns=_sdk_max_turns,
  2009	                        sdk_ceiling_hit=_sdk_ceiling_hit,
  2010	                        session_id=result.session_id,  # TASK-RFX-B20B
  2011	                    )
  2012	                else:
  2013	                    return AgentInvocationResult(
  2014	                        task_id=task_id,
  2015	                        turn=turn,
  2016	                        agent_type="player",
  2017	                        success=False,
  2018	                        report={},
  2019	                        duration_seconds=duration,
  2020	                        error=result.error,
  2021	                        session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
  2022	                    )
  2023	            else:
  2024	                # Legacy direct SDK invocation
  2025	                logger.info(
  2026	                    f"Invoking Player via direct SDK for {task_id} (turn {turn})"
  2027	                )
  2028	                # Build prompt for Player
  2029	                prompt = self._build_player_prompt(
  2030	                    task_id, turn, requirements, feedback, context=context
  2031	                )
  2032	
  2033	                # Invoke SDK with Player permissions (Read, Write, Edit, Bash)
  2034	                # Model selection delegated to CLI default
  2035	                # TASK-RFX-B20B: Pass resume_session_id for session continuity
  2036	                await self._invoke_with_role(
  2037	                    prompt=prompt,
  2038	                    agent_type="player",
  2039	                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
  2040	                    permission_mode="acceptEdits",
  2041	                    resume_session_id=self._last_session_id,
  2042	                    task_id=task_id,
  2043	                    turn=turn,
  2044	                )
  2045	
  2046	                # Load and validate Player report
  2047	                report = self._load_agent_report(task_id, turn, "player")
  2048	                self._validate_player_report(report)
  2049	
  2050	                duration = time.time() - start_time
  2051	
  2052	                # TASK-VOPT-002: Per-turn timing instrumentation (legacy path)
  2053	                logger.info(
  2054	                    "[%s] SDK invocation complete: %.1fs (legacy direct mode)",
  2055	                    task_id, duration,
  2056	                )
  2057	
  2058	                return AgentInvocationResult(
  2059	                    task_id=task_id,
  2060	                    turn=turn,
  2061	                    agent_type="player",
  2062	                    success=True,
  2063	                    report=report,
  2064	                    duration_seconds=duration,
  2065	                    session_id=self._last_session_id,  # TASK-RFX-B20B
  2066	                )
  2067	
  2068	        except (PlayerReportNotFoundError, PlayerReportInvalidError) as e:
  2069	            duration = time.time() - start_time
  2070	            return AgentInvocationResult(
  2071	                task_id=task_id,
  2072	                turn=turn,
  2073	                agent_type="player",
  2074	                success=False,
  2075	                report={},
  2076	                duration_seconds=duration,
  2077	                error=str(e),
  2078	                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
  2079	            )
  2080	        except SDKTimeoutError as e:
  2081	            duration = time.time() - start_time
  2082	            return AgentInvocationResult(
  2083	                task_id=task_id,
  2084	                turn=turn,
  2085	                agent_type="player",
  2086	                success=False,
  2087	                report={},
  2088	                duration_seconds=duration,
  2089	                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
  2090	                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
  2091	            )
  2092	        except (Exception, asyncio.CancelledError) as e:
  2093	            duration = time.time() - start_time
  2094	            if isinstance(e, asyncio.CancelledError):
  2095	                logger.debug(f"CancelledError caught for {task_id}: {e}")
  2096	                error_msg = f"Cancelled: {str(e)}"
  2097	            else:
  2098	                error_msg = f"Unexpected error: {str(e)}"
  2099	            return AgentInvocationResult(
  2100	                task_id=task_id,
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 2100}, 'id': 'yt8dlwNZl7nB4sX9wS5UNcP5hNR5bqzA', 'type': 'tool_call'}]
Tool:   2101	                turn=turn,
  2102	                agent_type="player",
  2103	                success=False,
  2104	                report={},
  2105	                duration_seconds=duration,
  2106	                error=error_msg,
  2107	                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
  2108	            )
  2109	        finally:
  2110	            # TASK-ASF-008: Restore original timeout after invocation
  2111	            self.sdk_timeout_seconds = original_timeout
  2112	
  2113	    async def invoke_coach(
  2114	        self,
  2115	        task_id: str,
  2116	        turn: int,
  2117	        requirements: str,
  2118	        player_report: Dict[str, Any],
  2119	        remaining_budget: Optional[float] = None,
  2120	        evidence_bundle: Optional["CoachEvidenceBundle"] = None,
  2121	        coach_context: Optional[str] = None,
  2122	        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
  2123	    ) -> AgentInvocationResult:
  2124	        """Invoke Coach agent via Claude Agents SDK with honesty verification.
  2125	
  2126	        The Coach agent:
  2127	        - Has read-only access (Read, Bash only)
  2128	        - Works in same worktree as Player
  2129	        - Validates implementation independently
  2130	        - Receives honesty verification context for Player claims
  2131	        - Creates JSON decision at .guardkit/autobuild/{task_id}/coach_turn_{turn}.json
  2132	
  2133	        Args:
  2134	            task_id: Task identifier
  2135	            turn: Current turn number
  2136	            requirements: Original task requirements
  2137	            player_report: Player's report from current turn
  2138	            remaining_budget: Optional remaining wall-clock budget in seconds.
  2139	                When provided, sdk_timeout_seconds is capped at this value for
  2140	                this invocation then restored. Used to honour per-turn budgets
  2141	                and Coach grace periods. (TASK-ABFIX-004)
  2142	            evidence_bundle: Optional ``CoachEvidenceBundle`` produced by
  2143	                ``CoachValidator.gather_evidence`` upstream (TASK-HMIG-008R Part B).
  2144	                When provided, the bundle's pre-computed ``HonestyVerification``
  2145	                is used as the canonical honesty channel — ``_verify_player_claims``
  2146	                is NOT re-run. This avoids duplicate honesty verification and
  2147	                preserves Layer-1 ``resolved_paths`` annotations that
  2148	                ``gather_evidence`` produced via state_bridge identity resolution
  2149	                (TASK-FIX-1B4A). The bundle is also rendered into the Coach
  2150	                prompt as structured evidence so the LLM Coach can read
  2151	                deterministic gate outputs (coverage, plan_audit, bdd,
  2152	                arch_review, tests) without re-deriving them.
  2153	            coach_context: Optional memory / coach context string. Passed
  2154	                through to ``_build_coach_prompt`` for inclusion in the prompt.
  2155	            acceptance_criteria: Optional structured ACs (``[{"id","text"}]``)
  2156	                threaded into the Coach prompt so the synthesis verdict can
  2157	                carry a populated ``criteria_verification`` per AC
  2158	                (TASK-ARCH-COACHBFULL AC-4 — the run-19 empty-array fix) and so
  2159	                the B-full Phase-A gather (TASK-ARCH-COACHBFULL AC-1) has the
  2160	                explicit per-AC checklist to investigate against. When ``None``
  2161	                the prompt omits the per-criterion section (pre-COACHBFULL
  2162	                behaviour).
  2163	
  2164	        Returns:
  2165	            AgentInvocationResult with Coach's decision
  2166	
  2167	        Raises:
  2168	            AgentInvocationError: If invocation fails
  2169	            CoachDecisionNotFoundError: If Coach doesn't create decision
  2170	            CoachDecisionInvalidError: If decision JSON is malformed
  2171	            SDKTimeoutError: If invocation exceeds timeout
  2172	        """
  2173	        start_time = time.time()
  2174	
  2175	        # TASK-ABFIX-004: Cap SDK timeout at remaining budget (mirrors invoke_player pattern)
  2176	        effective_timeout = self._calculate_sdk_timeout(task_id, remaining_budget=remaining_budget)
  2177	        original_timeout = self.sdk_timeout_seconds
  2178	        self.sdk_timeout_seconds = effective_timeout
  2179	
  2180	        try:
  2181	            # TASK-HMIG-008R Part C: honesty channel unification.
  2182	            # When evidence_bundle is provided (autobuild primary path),
  2183	            # use the bundle's pre-computed HonestyVerification — it was
  2184	            # generated by CoachValidator.gather_evidence with state_bridge
  2185	            # identity resolution (Layer 1 / TASK-FIX-1B4A) and is richer
  2186	            # than what _verify_player_claims would produce here.
  2187	            # When evidence_bundle is None (legacy callers, GUARDKIT_COACH_LEGACY=1
  2188	            # fallback path), compute honesty internally as before.
  2189	            if evidence_bundle is not None:
  2190	                honesty_verification = evidence_bundle.honesty
  2191	            else:
  2192	                honesty_verification = self._verify_player_claims(player_report)
  2193	
  2194	            # TASK-ARCH-COACHSPLIT (D-3): default to TOOLLESS, grammar-enforced
  2195	            # verdict synthesis over the deterministic evidence bundle. The
  2196	            # bundle (gather_evidence) already carries the test/coverage/
  2197	            # honesty/plan_audit/bdd/arch_review signal the legacy tool-using
  2198	            # Coach would investigate, so the Coach can synthesise its verdict
  2199	            # without tools — which (a) lets the GBNF grammar enforce the
  2200	            # verdict schema (llama.cpp hard-rejects grammar+tools) and (b)
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 2200}, 'id': 'HZKODisHtd0bOaYrxOuPPyItxaURoqAn', 'type': 'tool_call'}]
Tool:   2201	            # eliminates the run-18 tool-parse HTTP 500. GUARDKIT_COACH_SYNTHESIS=0
  2202	            # restores the legacy tool-using Coach.
  2203	            #
  2204	            # Synthesis is gated on the bundle ACTUALLY existing: a toolless
  2205	            # "synthesise over the evidence bundle" prompt is incoherent (and an
  2206	            # absence-of-failure false-green hazard — the prompt would assert a
  2207	            # bundle that was never rendered and the structured guards would be
  2208	            # dropped) when no bundle was gathered. Callers without a bundle —
  2209	            # the GUARDKIT_COACH_LEGACY=1 fallback after a CoachValidator
  2210	            # exception (autobuild.py `_invoke_coach_legacy`), or any direct
  2211	            # invoke_coach caller — keep the tool-using Coach so it can
  2212	            # investigate with Read/Bash/Grep/Glob in place of the absent
  2213	            # deterministic evidence. The autobuild PRIMARY path always passes a
  2214	            # bundle (gather_evidence), so it always synthesises.
  2215	            synthesis_enabled = (
  2216	                _coach_synthesis_enabled() and evidence_bundle is not None
  2217	            )
  2218	
  2219	            # TASK-ARCH-COACHBFULL (B-full): optional tool-using Phase-A gather
  2220	            # BEFORE the toolless Phase-B synthesis. When enabled (opt-in), the
  2221	            # Coach investigates with Read/Bash/Grep/Glob and produces findings
  2222	            # TEXT (not a verdict); those findings are threaded into the
  2223	            # synthesis prompt below. The gather is gated on synthesis being
  2224	            # active (a B-full gather only makes sense ahead of the toolless
  2225	            # grammar verdict) and on the opt-in flag. Any failure inside
  2226	            # _invoke_coach_gather returns None → degrade to B-min (strict
  2227	            # dominance, AC-2). A genuine cancellation (CancelledError) is NOT
  2228	            # swallowed there and propagates to the except blocks below (AC-5).
  2229	            gather_findings: Optional[str] = None
  2230	            if synthesis_enabled and _coach_gather_enabled():
  2231	                # effective_timeout is currently in self.sdk_timeout_seconds;
  2232	                # cap Phase A at a fraction of it, floored, never above it.
  2233	                gather_timeout = min(
  2234	                    effective_timeout,
  2235	                    max(
  2236	                        _COACH_GATHER_BUDGET_MIN_S,
  2237	                        int(effective_timeout * _COACH_GATHER_BUDGET_FRACTION),
  2238	                    ),
  2239	                )
  2240	                gather_findings = await self._invoke_coach_gather(
  2241	                    task_id=task_id,
  2242	                    turn=turn,
  2243	                    requirements=requirements,
  2244	                    player_report=player_report,
  2245	                    honesty_verification=honesty_verification,
  2246	                    evidence_bundle=evidence_bundle,
  2247	                    acceptance_criteria=acceptance_criteria,
  2248	                    gather_timeout=gather_timeout,
  2249	                )
  2250	
  2251	            # Build prompt for Coach with verification context.
  2252	            prompt = self._build_coach_prompt(
  2253	                task_id, turn, requirements, player_report, honesty_verification,
  2254	                acceptance_criteria=acceptance_criteria,
  2255	                evidence_bundle=evidence_bundle,
  2256	                coach_context=coach_context,
  2257	                synthesis=synthesis_enabled,
  2258	                gather_findings=gather_findings,
  2259	            )
  2260	
  2261	            # Invoke the Coach. In both paths return_events=True so the typed
  2262	            # HarnessEvent stream comes back for coach_output_parser
  2263	            # (TASK-FIX-COACHOUT01 Shape A) — the verdict is parsed from the
  2264	            # response text and the orchestrator writes coach_turn_N.json
  2265	            # itself; Coach never writes (ADR FB-004, read-only invariant).
  2266	            if synthesis_enabled:
  2267	                # Load the GBNF verdict grammar; degrade to prompt-only (still
  2268	                # toolless) if the packaged grammar can't be read so a
  2269	                # packaging glitch never hard-fails the Coach.
  2270	                grammar: Optional[str] = None
  2271	                try:
  2272	                    from guardkit.orchestrator.coach_grammar import (
  2273	                        load_coach_verdict_grammar,
  2274	                    )
  2275	
  2276	                    grammar = load_coach_verdict_grammar()
  2277	                except Exception as exc:  # noqa: BLE001 — degrade, never hard-fail
  2278	                    logger.warning(
  2279	                        "TASK-ARCH-COACHSPLIT: failed to load Coach verdict "
  2280	                        "grammar (%s); running TOOLLESS synthesis WITHOUT a "
  2281	                        "grammar constraint (prompt-only). The verdict schema "
  2282	                        "is then only prompt-enforced, not grammar-guaranteed.",
  2283	                        exc,
  2284	                    )
  2285	
  2286	                # allowed_tools=[] makes the harness toolless on EVERY
  2287	                # substrate (the SDK harness reads its tool surface from the
  2288	                # constructor allowed_tools, which select_harness threads from
  2289	                # here). synthesis=True dispatches through invoke_synthesis.
  2290	                result_tuple = await self._invoke_with_role(
  2291	                    prompt=prompt,
  2292	                    agent_type="coach",
  2293	                    allowed_tools=[],
  2294	                    permission_mode="bypassPermissions",
  2295	                    task_id=task_id,
  2296	                    turn=turn,
  2297	                    return_events=True,
  2298	                    synthesis=True,
  2299	                    grammar=grammar,
  2300	                )
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 2300}, 'id': 'wnFu01HRVEYWFoZwbBho7eC52Mn2pilr', 'type': 'tool_call'}]
Tool:   2301	            else:
  2302	                # Legacy tool-using Coach (GUARDKIT_COACH_SYNTHESIS disabled).
  2303	                # Read-only tools; verdict still parsed from response text.
  2304	                result_tuple = await self._invoke_with_role(
  2305	                    prompt=prompt,
  2306	                    agent_type="coach",
  2307	                    allowed_tools=["Read", "Bash", "Grep", "Glob"],
  2308	                    permission_mode="bypassPermissions",
  2309	                    task_id=task_id,
  2310	                    turn=turn,
  2311	                    return_events=True,
  2312	                )
  2313	            assert result_tuple is not None, (
  2314	                "_invoke_with_role(return_events=True) must return a tuple "
  2315	                "on success; got None"
  2316	            )
  2317	            _, harness_events = result_tuple
  2318	
  2319	            # TASK-FIX-COACHOUT01 Shape A: extract the structured verdict from
  2320	            # Coach's response text and persist coach_turn_N.json from the
  2321	            # orchestrator side. The parser raises CoachDecisionNotFoundError
  2322	            # / CoachDecisionInvalidError with messages COACHSF01 greps for
  2323	            # (autobuild.py:5676-5678) on every failure path — the exceptions
  2324	            # propagate to the existing except block at the bottom of this
  2325	            # method, which converts them to AgentInvocationResult(
  2326	            # success=False, error=str(e)). COACHSF01 then fires the
  2327	            # synthetic-feedback safety net unchanged.
  2328	            from guardkit.orchestrator.coach_output_parser import (
  2329	                extract_and_write as _coach_extract_and_write,
  2330	            )
  2331	            coach_output_path = self._get_report_path(task_id, turn, "coach")
  2332	            _coach_extract_and_write(
  2333	                harness_events=harness_events,
  2334	                task_id=task_id,
  2335	                turn=turn,
  2336	                output_path=coach_output_path,
  2337	            )
  2338	
  2339	            # Load and validate Coach decision — the file on disk was just
  2340	            # written by the parser, so this re-read keeps the existing
  2341	            # consumer contract intact. _validate_coach_decision still owns
  2342	            # the deep schema check (criteria_verification, severity values,
  2343	            # decision-specific field presence) the parser doesn't replicate.
  2344	            decision = self._load_agent_report(task_id, turn, "coach")
  2345	            self._validate_coach_decision(decision)
  2346	
  2347	            # TASK-AB-NULLEVID01: deterministic fail-closed backstop for the
  2348	            # absence-of-failure guard #5 (the GATHERING-STATUS GUARD in
  2349	            # _build_coach_prompt). When gather_evidence aborts early (e.g.
  2350	            # partial_honesty_abort) the bundle has everything downstream None
  2351	            # and signal_absent is never set, so the guard-#6 backstop below
  2352	            # no-ops — leaving guard #5 as prompt text only. This override
  2353	            # makes guard #5 load-bearing CODE. Ordering is deliberate: it
  2354	            # runs FIRST among the verdict-override guards because incomplete
  2355	            # gathering is upstream of every leg-specific signal — on an
  2356	            # aborted gather the legs the guards below read (independent_tests,
  2357	            # spec_gap, runtime_parity, classification) are all None, so they
  2358	            # would no-op anyway; firing first means the feedback names the
  2359	            # root cause (the aborted gathering stage), not a downstream
  2360	            # symptom. Contract: only `approve` verdicts are ever FLIPPED to
  2361	            # feedback; guard #6 (_reconcile_absent_independent_test_signal)
  2362	            # additionally ANNOTATES feedback verdicts with the
  2363	            # verifier-infrastructure marker (idempotent, re-persisted to
  2364	            # disk — TASK-AB-ZEROTESTLOUD01) without touching the decision.
  2365	            # Ordering still guarantees the flip happens before the
  2366	            # annotation-capable guards run.
  2367	            self._reconcile_incomplete_evidence_gathering(
  2368	                decision=decision,
  2369	                evidence_bundle=evidence_bundle,
  2370	                task_id=task_id,
  2371	                turn=turn,
  2372	                coach_output_path=coach_output_path,
  2373	            )
  2374	
  2375	            # TASK-FIX-COACHFG01: deterministic fail-closed backstop for the
  2376	            # absence-of-failure guard #6 (the INDEPENDENT-TEST ABSENT GUARD in
  2377	            # _build_coach_prompt). The toolless-synthesis Coach is *told* not
  2378	            # to approve when the independent-test oracle produced no signal,
  2379	            # but that instruction is advisory — run-19 showed the local model
  2380	            # emit `approve` anyway after its own trust-but-verify pytest run
  2381	            # timed out (300s). This override makes guard #6 load-bearing CODE,
  2382	            # not a prompt the model may ignore. It fires after the verdict is
  2383	            # loaded + schema-validated and before the AgentInvocationResult is
  2384	            # returned (the natural seam). Narrow: only an `approve` over an
  2385	            # `independent_tests.signal_absent` bundle is overridden.
  2386	            self._reconcile_absent_independent_test_signal(
  2387	                decision=decision,
  2388	                evidence_bundle=evidence_bundle,
  2389	                task_id=task_id,
  2390	                turn=turn,
  2391	                coach_output_path=coach_output_path,
  2392	            )
  2393	
  2394	            # TASK-QAWE-004: SPEC_GAP whole-file deselection hard-gate.
  2395	            # Modelled on _reconcile_absent_independent_test_signal; fires
  2396	            # when spec_gap.whole_file_deselection is True (ground truth > 0,
  2397	            # scenarios_attempted present and zero). AC-013.
  2398	            self._apply_spec_gap_absent_guard(
  2399	                decision=decision,
  2400	                evidence_bundle=evidence_bundle,

