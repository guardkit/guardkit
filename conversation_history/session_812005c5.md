## Summarized at 2026-06-12T16:44:42.796391+00:00

AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/agent_invoker.py', 'limit': 500, 'offset': 3000}, 'id': 'cJQNuYx03ONdXaCT71ShYDnjzFeww465', 'type': 'tool_call'}]
Tool:   3001	
  3002	```json
  3003	{{
  3004	  "task_id": "{task_id}",
  3005	  "turn": {turn},
  3006	  "decision": "approve" | "feedback",
  3007	  ...fields as specified below...
  3008	}}
  3009	```
  3010	
  3011	For APPROVAL, the JSON block must contain:
  3012	```json
  3013	{{
  3014	  "task_id": "{task_id}",
  3015	  "turn": {turn},
  3016	  "decision": "approve",
  3017	  "validation_results": {{
  3018	    "requirements_met": ["list", "of", "verified", "requirements"],
  3019	    "tests_run": true,
  3020	    "tests_passed": true,
  3021	    "test_command": "command you ran",
  3022	    "test_output_summary": "summary of test results",
  3023	    "code_quality": "assessment",
  3024	    "edge_cases_covered": ["list", "of", "edge", "cases"]
  3025	  }},{verification_example}
  3026	  "rationale": "Why you approved"
  3027	}}
  3028	```
  3029	
  3030	For FEEDBACK, the JSON block must contain:
  3031	```json
  3032	{{
  3033	  "task_id": "{task_id}",
  3034	  "turn": {turn},
  3035	  "decision": "feedback",
  3036	  "issues": [
  3037	    {{
  3038	      "type": "missing_requirement" | "test_failure" | "code_quality" | "edge_case",
  3039	      "severity": "critical" | "major" | "minor",
  3040	      "description": "Specific issue with file paths and line numbers",
  3041	      "requirement": "Which requirement is affected",
  3042	      "suggestion": "How to fix it"
  3043	    }}
  3044	  ],{verification_example}
  3045	  "rationale": "Why you're providing feedback"
  3046	}}
  3047	```
  3048	
  3049	**IMPORTANT**: For each acceptance criterion, create a criteria_verification with:
  3050	- criterion_id: The ID (e.g., "AC-001") matching the Player's completion_promise
  3051	- result: "verified" if criterion is satisfied, "rejected" if not
  3052	- notes: Your reasoning - what you checked and found
  3053	
  3054	**CRITICAL**: The fenced ```json block MUST be the last thing in your response.
  3055	Do not write any prose after the closing ``` fence. If you emit exploratory JSON
  3056	blocks earlier in your response (e.g. while sketching alternatives), the
  3057	orchestrator takes only the **last** fenced block.
  3058	"""
  3059	        return prompt
  3060	
  3061	    # ------------------------------------------------------------------
  3062	    # TASK-HMIG-008R Part C — Coach prompt rendering helpers.
  3063	    # ------------------------------------------------------------------
  3064	
  3065	    # Token-budget truncation thresholds (plan §4 "Token budget"):
  3066	    _COACH_BDD_DISCOVERIES_LIMIT = 20
  3067	    _COACH_BDD_ERRORS_LIMIT = 10
  3068	    _COACH_HONESTY_DISCREPANCIES_LIMIT = 20
  3069	    # Wave-1 (TASK-QAWE-002): wiring / mocked_seam / spec_gap findings limit.
  3070	    _COACH_WIRING_FINDINGS_LIMIT = 20
  3071	
  3072	    # TASK-PERF-COACHSYNTH (AC-4 / Lever C): cap the Phase-A gather findings
  3073	    # text rendered into the Phase-B synthesis prompt. The gather is already
  3074	    # bounded at the source (recursion_limit + per-tool-result truncation),
  3075	    # but the findings the model *produces* can still be large; this is the
  3076	    # final belt so the synthesis prompt size does not grow unbounded with
  3077	    # gather volume (the run-20 latency creep). Truncation is MARKED, never
  3078	    # silent — respecting absence-of-failure-is-not-success.md: a silently
  3079	    # dropped tail would let the synthesis treat a partial checklist as
  3080	    # complete. ~16 k chars ≈ ~4 k tokens of findings.
  3081	    _COACH_GATHER_FINDINGS_LIMIT_CHARS = int(
  3082	        os.environ.get("GUARDKIT_COACH_GATHER_FINDINGS_LIMIT_CHARS", "16000")
  3083	    )
  3084	
  3085	    @classmethod
  3086	    def _truncate_gather_findings(cls, findings: str) -> str:
  3087	        """Cap findings at the char budget with a visible truncation marker."""
  3088	        limit = cls._COACH_GATHER_FINDINGS_LIMIT_CHARS
  3089	        if limit <= 0 or len(findings) <= limit:
  3090	            return findings
  3091	        elided = len(findings) - limit
  3092	        return (
  3093	            findings[:limit]
  3094	            + f"\n\n... [Phase-A findings truncated for synthesis-prompt "
  3095	            f"budget: {elided} more chars elided. Any acceptance criterion "
  3096	            f"NOT explicitly marked PASS above is unverified — treat as "
  3097	            f"FAIL/UNSURE, never an assumed pass.] ..."
  3098	        )
  3099	
  3100	    @classmethod
  3101	    def _truncate_findings(
  3102	        cls,
  3103	        findings_container: Optional[Dict[str, Any]],
  3104	        limit: int,
  3105	    ) -> None:
  3106	        """Truncate the ``findings`` list inside a wiring result dict.
  3107	
  3108	        Keeps the first ``limit`` entries and appends a ``"... and N more"``
  3109	        marker when the list exceeds the limit. Mirrors the
  3110	        ``bdd.discoveries`` truncation pattern. Wave-1, TASK-QAWE-002.
  3111	
  3112	        Parameters
  3113	        ----------
  3114	        findings_container : Optional[Dict[str, Any]]
  3115	            A dict with a ``"findings"`` key (e.g. wiring / mocked_seam /
  3116	            spec_gap result). May be ``None``.
  3117	        limit : int
  3118	            Maximum number of findings to keep.
  3119	        """
  3120	        if not isinstance(findings_container, dict):
  3121	            return
  3122	        findings = findings_container.get("findings")
  3123	        if isinstance(findings, list) and len(findings) > limit:
  3124	            remainder = len(findings) - limit
  3125	            findings_container["findings"] = (
  3126	                findings[:limit]
  3127	                + [f"... and {remainder} more (truncated for token budget)"]
  3128	            )
  3129	
  3130	    def _render_evidence_bundle_section(
  3131	        self,
  3132	        evidence_bundle: "CoachEvidenceBundle",
  3133	    ) -> str:
  3134	        """Render the CoachEvidenceBundle as a structured prompt section.
  3135	
  3136	        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
  3137	        XML-like tags so the LLM Coach can locate it deterministically and
  3138	        apply the absence-of-failure guards against specific fields.
  3139	
  3140	        Truncation rules (plan §4):
  3141	
  3142	        * ``evidence_bundle.bdd.discoveries`` — keep first 20 entries.
  3143	        * ``evidence_bundle.bdd.errors``     — keep first 10 entries.
  3144	        * ``evidence_bundle.honesty.discrepancies`` — keep first 20 entries.
  3145	        * ``evidence_bundle.wiring.findings`` — keep first 20 entries.
  3146	        * ``evidence_bundle.mocked_seam.findings`` — keep first 20 entries.
  3147	        * ``evidence_bundle.spec_gap.findings`` — keep first 20 entries.
  3148	
  3149	        Each truncation appends a ``"... and N more"`` marker so the Coach
  3150	        knows the list was bounded. Non-list fields are bounded by gate
  3151	        computation and pass through unchanged.
  3152	
  3153	        The bundle's honesty channel is NOT duplicated here — it lives in
  3154	        the separate ``<honesty_verification>`` section emitted by
  3155	        :py:meth:`_render_bundle_honesty_section`. Both sections read from
  3156	        the same bundle.honesty value, but rendering them separately lets
  3157	        the absence-of-failure guards reference each by tag.
  3158	        """
  3159	        try:
  3160	            bundle_dict = evidence_bundle.to_dict()
  3161	        except Exception as exc:  # noqa: BLE001 — never block prompt build
  3162	            logger.error(
  3163	                "Failed to serialise evidence_bundle for Coach prompt: %s. "
  3164	                "Emitting empty bundle section so the Coach prompt still "
  3165	                "carries the absence-of-failure guards.",
  3166	                exc,
  3167	            )
  3168	            bundle_dict = {
  3169	                "gathering_status": "partial_exception",
  3170	                "gathering_error": f"bundle_serialisation_failed: {exc}",
  3171	            }
  3172	
  3173	        # Truncate bdd.discoveries / bdd.errors.
  3174	        bdd = bundle_dict.get("bdd")
  3175	        if isinstance(bdd, dict):
  3176	            discoveries = bdd.get("discoveries")
  3177	            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
  3178	                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
  3179	                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
  3180	                    f"... and {remainder} more (truncated for token budget)"
  3181	                ]
  3182	            errors = bdd.get("errors")
  3183	            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
  3184	                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
  3185	                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
  3186	                    f"... and {remainder} more (truncated for token budget)"
  3187	                ]
  3188	
  3189	        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
  3190	        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
  3191	        # evidence-bundle JSON the Coach sees is internally consistent.
  3192	        honesty = bundle_dict.get("honesty")
  3193	        if isinstance(honesty, dict):
  3194	            discrepancies = honesty.get("discrepancies")
  3195	            if (
  3196	                isinstance(discrepancies, list)
  3197	                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3198	            ):
  3199	                remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3200	                honesty["discrepancies"] = discrepancies[
  3201	                    : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3202	                ] + [{
  3203	                    "truncated": True,
  3204	                    "remainder": remainder,
  3205	                    "note": (
  3206	                        f"... and {remainder} more discrepancies (truncated "
  3207	                        f"for token budget). See full honesty_verification "
  3208	                        f"in coach_turn_N.json."
  3209	                    ),
  3210	                }]
  3211	
  3212	        # Truncate wiring / mocked_seam / spec_gap findings.
  3213	        # Mirrors the bdd.discoveries truncation pattern (keep first 20 +
  3214	        # "... and N more" marker). Wave-1, TASK-QAWE-002.
  3215	        self._truncate_findings(bundle_dict.get("wiring"), self._COACH_WIRING_FINDINGS_LIMIT)
  3216	        self._truncate_findings(bundle_dict.get("mocked_seam"), self._COACH_WIRING_FINDINGS_LIMIT)
  3217	        self._truncate_findings(bundle_dict.get("spec_gap"), self._COACH_WIRING_FINDINGS_LIMIT)
  3218	
  3219	        try:
  3220	            payload = json.dumps(bundle_dict, indent=2, default=str)
  3221	        except Exception as exc:  # noqa: BLE001
  3222	            logger.error(
  3223	                "Failed to JSON-encode truncated evidence_bundle: %s", exc,
  3224	            )
  3225	            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'
  3226	
  3227	        return f"""
  3228	## Deterministic Evidence Bundle
  3229	
  3230	<evidence_bundle>
  3231	{payload}
  3232	</evidence_bundle>
  3233	"""
  3234	
  3235	    def _render_bundle_honesty_section(
  3236	        self,
  3237	        honesty_verification: HonestyVerification,
  3238	    ) -> str:
  3239	        """Render the bundle's HonestyVerification as a structured prompt section.
  3240	
  3241	        Sourced from ``evidence_bundle.honesty`` (channel unification per
  3242	        plan §4). Emits a JSON-structured section inside
  3243	        ``<honesty_verification>...</honesty_verification>`` tags so the
  3244	        absence-of-failure guards can reference specific fields:
  3245	
  3246	        * ``honesty.discrepancies[*].claim_type``
  3247	        * ``honesty.discrepancies[*].severity``
  3248	        * ``honesty.resolved_paths`` — Layer-1 (TASK-FIX-1B4A) suppressions.
  3249	
  3250	        Truncation rule: keep first 20 discrepancies (plan §4 token budget).
  3251	        """
  3252	        from dataclasses import asdict
  3253	
  3254	        try:
  3255	            honesty_dict: Dict[str, Any] = asdict(honesty_verification)
  3256	        except Exception as exc:  # noqa: BLE001
  3257	            logger.error(
  3258	                "Failed to serialise honesty_verification for Coach prompt: %s",
  3259	                exc,
  3260	            )
  3261	            honesty_dict = {
  3262	                "verified": True,
  3263	                "discrepancies": [],
  3264	                "honesty_score": 1.0,
  3265	                "resolved_paths": [],
  3266	                "should_fix_count": 0,
  3267	                "serialisation_error": str(exc),
  3268	            }
  3269	
  3270	        discrepancies = honesty_dict.get("discrepancies")
  3271	        if (
  3272	            isinstance(discrepancies, list)
  3273	            and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3274	        ):
  3275	            remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3276	            honesty_dict["discrepancies"] = discrepancies[
  3277	                : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3278	            ] + [{
  3279	                "truncated": True,
  3280	                "remainder": remainder,
  3281	                "note": (
  3282	                    f"... and {remainder} more discrepancies (truncated "
  3283	                    f"for token budget). See full list in coach_turn_N.json."
  3284	                ),
  3285	            }]
  3286	
  3287	        try:
  3288	            payload = json.dumps(honesty_dict, indent=2, default=str)
  3289	        except Exception as exc:  # noqa: BLE001
  3290	            logger.error(
  3291	                "Failed to JSON-encode honesty_verification: %s", exc,
  3292	            )
  3293	            payload = '{"verified": true, "discrepancies": [], "honesty_score": 1.0}'
  3294	
  3295	        return f"""
  3296	## Honesty Verification
  3297	
  3298	<honesty_verification>
  3299	{payload}
  3300	</honesty_verification>
  3301	"""
  3302	
  3303	    def _render_absence_of_failure_guards(self) -> str:
  3304	        """Render the six absence-of-failure guard sentences (AC-009 + #5 + #6).
  3305	
  3306	        The four guards from the TASK-HMIG-008R task spec (AC-009 points 1-4),
  3307	        the fifth guard added per Phase 2.5 review finding #2
  3308	        (gathering_status guard), and the sixth guard added by
  3309	        TASK-FIX-COACHTESTTO (independent-test absent guard — treat a
  3310	        timed-out / transport-errored independent-test oracle as ABSENT rather
  3311	        than approving on the Player's self-reported tests). The sentences are
  3312	        emitted verbatim inside
  3313	        an ``<absence_of_failure_guards>`` block so the Coach can locate
  3314	        them deterministically. Wording mirrors
  3315	        ``.claude/rules/absence-of-failure-is-not-success.md`` and
  3316	        ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` to
  3317	        preserve the rule citation chain.
  3318	        """
  3319	        return """
  3320	<absence_of_failure_guards>
  3321	CRITICAL READING RULES — apply these BEFORE any approval decision:
  3322	
  3323	1. ZERO-CARDINALITY BDD GUARD.
  3324	   If evidence_bundle.bdd is not null AND evidence_bundle.bdd.scenarios_attempted == 0:
  3325	   treat as ABSENT SIGNAL — do NOT approve based on absence of failure.
  3326	   Surface as feedback: "BDD oracle ran zero scenarios — no evidence of
  3327	   passing behaviour." Rule: .claude/rules/absence-of-failure-is-not-success.md.
  3328	
  3329	2. ZERO-CARDINALITY TEST GUARD.
  3330	   If evidence_bundle.tests is not null AND evidence_bundle.tests.tests_run == 0:
  3331	   treat as ABSENT SIGNAL — do NOT approve. Surface as feedback:
  3332	   "No tests ran — cannot verify correctness." Rule:
  3333	   .claude/rules/absence-of-failure-is-not-success.md.
  3334	
  3335	3. SOPHISTICATED-LIE GUARD.
  3336	   If honesty_verification.discrepancies contains entries with
  3337	   severity == "critical" AND claim_type != "file_existence" AND
  3338	   claim_type != "claim_audit": you MUST reject the turn. These are
  3339	   sophisticated lies (test_result, test_count, promise_file_existence
  3340	   fabrications). Structural rejection is mandatory — do not evaluate
  3341	   ACs further. Surface a "feedback" decision naming each discrepancy.
  3342	
  3343	4. LAYER-1 PATH DEMOTION GUARD.
  3344	   If honesty_verification.discrepancies contains exactly ONE entry with
  3345	   claim_type == "file_existence" AND honesty_verification.resolved_paths
  3346	   is non-empty: this discrepancy was Layer-1-resolved by state_bridge
  3347	   identity lookup (the orchestrator moved the task file, not Player
  3348	   dishonesty). Demote to should_fix and continue AC evaluation. Rule:
  3349	   .claude/rules/path-string-mismatch-is-not-dishonesty.md (Layer 2).
  3350	   Cross-check evidence_bundle.severity_recommendations for the
  3351	   structured hint — if present, it confirms this demotion applies.
  3352	
  3353	5. GATHERING-STATUS GUARD.
  3354	   If evidence_bundle.gathering_status != "complete": evidence collection
  3355	   aborted before all fields were populated. Treat any null/None field as
  3356	   ABSENT SIGNAL — do NOT approve. Surface as feedback with the
  3357	   gathering_status value verbatim in the rationale so operators can
  3358	   diagnose which stage failed (e.g. "partial_honesty_abort",
  3359	   "partial_gate_abort", "partial_exception"). When status is
  3360	   "partial_exception", also surface evidence_bundle.gathering_error.
  3361	
  3362	6. INDEPENDENT-TEST ABSENT GUARD.
  3363	   If evidence_bundle.independent_tests is not null AND
  3364	   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
  3365	   trust-but-verify pytest run did NOT complete (it timed out or failed at
  3366	   the transport layer before producing a verdict). This is ABSENT SIGNAL,
  3367	   NOT a passing or failing test result — do NOT approve on the basis of the
  3368	   Player's self-reported tests plus the other gates. Surface as feedback:
  3369	   "Independent test verification did not complete (signal absent) — cannot
  3370	   independently confirm the Player's reported tests." Quote
  3371	   independent_tests.test_output_summary verbatim in the rationale so
  3372	   operators can see whether it timed out or errored. Rule:
  3373	   .claude/rules/absence-of-failure-is-not-success.md.
  3374	
  3375	7. WIRING-EVIDENCE ADVISORY GUARD.
  3376	   If evidence_bundle.wiring, evidence_bundle.mocked_seam, or
  3377	   evidence_bundle.spec_gap is not null AND any of these fields has a
  3378	   non-empty findings list for a FEATURE / REFACTOR / INTEGRATION task:
  3379	   treat the named symbols as candidate dead code (UNWIRED_PATH), suspect
  3380	   acceptance evidence (MOCKED_SEAM), or unexecuted scenarios (SPEC_GAP).
  3381	   Require evidence of registration / real-seam execution before approving.
  3382	   Surface as feedback unless the Player demonstrates the wiring path.
  3383	   Advisory only — does not override on its own; combines with other
  3384	   guards for the final decision. Rule:
  3385	   .claude/rules/absence-of-failure-is-not-success.md.
  3386	</absence_of_failure_guards>
  3387	"""
  3388	
  3389	    def _verify_player_claims(
  3390	        self,
  3391	        player_report: Dict[str, Any],
  3392	    ) -> HonestyVerification:
  3393	        """Verify Player's self-reported claims against reality.
  3394	
  3395	        This method uses CoachVerifier to cross-reference Player claims:
  3396	        - Test results vs actual test execution
  3397	        - Claimed files vs filesystem state
  3398	        - Test counts vs parsed output
  3399	
  3400	        Args:
  3401	            player_report: Player's report from current turn
  3402	
  3403	        Returns:
  3404	            HonestyVerification with verification results and honesty score
  3405	
  3406	        Note:
  3407	            Returns a default verification result if verification fails,
  3408	            allowing the workflow to continue while logging the issue.
  3409	        """
  3410	        try:
  3411	            verifier = CoachVerifier(
  3412	                self.worktree_path, venv_python=self._venv_python
  3413	            )
  3414	            verification = verifier.verify_player_report(player_report)
  3415	
  3416	            if verification.discrepancies:
  3417	                logger.warning(
  3418	                    f"Player honesty verification found {len(verification.discrepancies)} "
  3419	                    f"discrepancies (score: {verification.honesty_score:.2f})"
  3420	                )
  3421	                for disc in verification.discrepancies:
  3422	                    logger.warning(
  3423	                        f"  [{disc.severity}] {disc.claim_type}: "
  3424	                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
  3425	                    )
  3426	            else:
  3427	                logger.info(
  3428	                    f"Player claims verified successfully (score: {verification.honesty_score:.2f})"
  3429	                )
  3430	
  3431	            return verification
  3432	
  3433	        except Exception as e:
  3434	            logger.warning(f"Failed to verify Player claims: {e}")
  3435	            # Return default verification (assume honest) to not block workflow
  3436	            return HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0)
  3437	
  3438	    async def _invoke_with_role(
  3439	        self,
  3440	        prompt: str,
  3441	        agent_type: Literal["player", "coach"],
  3442	        allowed_tools: list[str],
  3443	        permission_mode: Literal["acceptEdits", "bypassPermissions"],
  3444	        model: Optional[str] = None,
  3445	        resume_session_id: Optional[str] = None,
  3446	        task_id: Optional[str] = None,
  3447	        turn: Optional[int] = None,
  3448	        heartbeat_label_override: Optional[str] = None,
  3449	        return_events: bool = False,
  3450	        synthesis: bool = False,
  3451	        grammar: Optional[str] = None,
  3452	        recursion_limit: Optional[int] = None,
  3453	        max_tool_result_chars: Optional[int] = None,
  3454	    ) -> Optional[Tuple[None, List[HarnessEvent]]]:
  3455	        """Low-level SDK invocation with role-based permissions.
  3456	
  3457	        This method handles the actual Claude Agent SDK invocation with
  3458	        appropriate permissions and timeout handling. Emits an ``llm.call``
  3459	        event for every invocation via the injected EventEmitter
  3460	        (TASK-INST-005b).
  3461	
  3462	        Args:
  3463	            prompt: Formatted prompt for agent
  3464	            agent_type: "player" or "coach"
  3465	            allowed_tools: List of allowed SDK tools
  3466	            permission_mode: "acceptEdits" (Player) or "bypassPermissions" (Coach)
  3467	            model: Model identifier, or None to use CLI default
  3468	            resume_session_id: Optional SDK session ID to resume from.
  3469	                If provided, passed as ``resume`` kwarg to ClaudeAgentOptions.
  3470	                If None, starts a fresh session. (TASK-RFX-B20B)
  3471	            heartbeat_label_override: Optional explicit phase label for
  3472	                ``async_heartbeat``. When provided, replaces the default
  3473	                ``f"{agent_type.capitalize()} invocation"`` label. Used by
  3474	                :func:`run_specialist` so orchestrator-invoked specialists
  3475	                surface as ``"specialist:{name} invocation"`` instead of
  3476	                masquerading as Player/Coach invocations (TASK-ABSR-DIAG).
  3477	            return_events: When ``True``, return ``(None, harness_events)``
  3478	                instead of ``None`` so callers can inspect the typed event
  3479	                stream the harness emitted. Used by the Coach call site
  3480	                (``invoke_coach``) to feed ``coach_output_parser`` the
  3481	                substrate-agnostic ``AssistantMessageEvent`` list it needs
  3482	                to extract the structured verdict (TASK-FIX-COACHOUT01
  3483	                Shape A). Player and specialist call sites leave this
  3484	                ``False`` and continue to receive ``None``.
  3485	
  3486	                The parameter-based mechanism (rather than an instance
  3487	                attribute like ``self._last_harness_events``) was chosen by
  3488	                the Phase 2.5B architectural review (Gap 1) to avoid the
  3489	                hidden stale-state risk a future concurrent-invocation
  3490	                refactor would silently activate.
  3491	            synthesis: When ``True``, dispatch through
  3492	                ``harness.invoke_synthesis(...)`` instead of
  3493	                ``harness.invoke(...)`` — a TOOLLESS call (no ``tools`` in
  3494	                the substrate request) optionally constrained by ``grammar``.
  3495	                Used by the Coach verdict-synthesis path
  3496	                (TASK-ARCH-COACHSPLIT D-3). The caller MUST also pass
  3497	                ``allowed_tools=[]`` so the harness is constructed toolless
  3498	                on every substrate (the SDK harness reads its tool surface
  3499	                from the constructor ``allowed_tools``, not from the invoke
  3500	                call). All other orchestrator-side concerns (cancel monitor,
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 500, 'offset': 0}, 'id': 'PwyDfHFVpedDjK67PEyqx4ZTN129uehp', 'type': 'tool_call'}]
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
    76	class CoachEvidenceBundle:
    77	    """Structured evidence gathered by CoachValidator for the LLM Coach.
    78	
    79	    Each field maps to an intermediate value the legacy ``validate()`` method
    80	    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
    81	    (rendered as JSON into the Coach prompt) plus the honesty result and makes
    82	    the final approve/feedback decision.
    83	
    84	    Attributes
    85	    ----------
    86	    honesty
    87	        ``HonestyVerification`` from ``CoachVerifier``. Carries
    88	        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
    89	        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
    90	        gather path. The Coach reads this field unconditionally.
    91	    gathering_status
    92	        Pipeline status; see :data:`GatheringStatus` for the meaning of each
    93	        value. Used by the Coach to decide whether ``None`` evidence fields
    94	        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
    95	        (status == "complete").
    96	    gathering_error
    97	        Optional human-readable description of what went wrong when
    98	        ``gathering_status == "partial_exception"``. ``None`` on every other
    99	        status. Surfaced verbatim in the synthetic feedback rationale when the
   100	        primary ``_invoke_coach`` path catches an exception around evidence
   101	        gathering.
   102	    quality_gates
   103	        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
   104	        plan_audit). ``None`` when gathering aborted before the gates ran or
   105	        when the task type opts out of all gates.
   106	    coverage_details
   107	        Raw coverage dict slice from ``task_work_results['test_results']``
   108	        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
   109	        coverage was not reported.
   110	    plan_audit
   111	        Plan-audit findings dict from ``task_work_results['plan_audit']``.
   112	        ``None`` when the producer wrote no plan_audit block (e.g.
   113	        ``--implement-only`` without a saved plan).
   114	    bdd
   115	        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
   116	        scenarios_failed, scenarios_passed, scenarios_pending, failures,
   117	        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
   118	        applies the Pattern-2 absence-of-failure guard against
   119	        ``bdd['scenarios_attempted']``.
   120	    arch_review
   121	        Architectural review dict slice (``{"score": int, ...}``). ``None``
   122	        when no Phase 2.5B output was produced.
   123	    tests
   124	        Aggregate test result dict (tests_passed / tests_run /
   125	        line_coverage_met / branch_coverage_met / requires_infrastructure).
   126	        ``None`` when no test_results block was produced. The Coach applies
   127	        the absence-of-failure guard against ``tests['tests_run']``.
   128	    independent_tests
   129	        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
   130	        gathering aborted before independent tests or when the task type's
   131	        profile opts out of independent verification.
   132	    requirements
   133	        ``RequirementsValidation`` from ``validate_requirements``. ``None``
   134	        when gathering aborted before requirements validation.
   135	    severity_recommendations
   136	        Structured hints derived from ``_honesty_issues_from`` demotion logic
   137	        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
   138	        Coach reads these to know when to demote ``file_existence``
   139	        discrepancies from ``must_fix`` to ``should_fix``.
   140	    task_type
   141	        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
   142	        ``"scaffolding"``). ``None`` when task type could not be resolved
   143	        (``partial_exception`` with invalid_task_type cause).
   144	    profile_name
   145	        Quality-gate profile name string. ``None`` on the same paths as
   146	        ``task_type``.
   147	    advisory_issues
   148	        Non-blocking issues that ride along with the final decision regardless
   149	        of approve/feedback outcome. Currently sourced from:
   150	
   151	        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
   152	          ``severity == "warning"``.
   153	        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
   154	          ``severity == "should_fix"``.
   155	
   156	        Pre-populated so the LLM Coach can read them without re-computing the
   157	        Layer-2 demotion.
   158	    wiring
   159	        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
   160	        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
   161	        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
   162	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   163	        authored source targets, or the factory is unavailable.
   164	    mocked_seam
   165	        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
   166	        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
   167	        the task type gates out, there are no authored acceptance files, or
   168	        the factory is unavailable.
   169	    spec_gap
   170	        SPEC_GAP analysis result (dict). Contains ``status``,
   171	        ``ground_truth_count``, ``executed_count``, ``findings``,
   172	        ``whole_file_deselection``. ``None`` when the task type gates out,
   173	        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
   174	        implemented.
   175	    """
   176	
   177	    honesty: "HonestyVerification"
   178	    gathering_status: GatheringStatus = "complete"
   179	    gathering_error: Optional[str] = None
   180	
   181	    quality_gates: Optional["QualityGateStatus"] = None
   182	    coverage_details: Optional[Dict[str, Any]] = None
   183	    plan_audit: Optional[Dict[str, Any]] = None
   184	    bdd: Optional[Dict[str, Any]] = None
   185	    arch_review: Optional[Dict[str, Any]] = None
   186	    tests: Optional[Dict[str, Any]] = None
   187	
   188	    # Wave-1 wiring evidence fields (TASK-QAWE-002).
   189	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   190	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   191	    # or when guardkitfactory.wiring is unavailable (ImportError).
   192	    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
   193	    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
   194	    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)
   195	
   196	    independent_tests: Optional["IndependentTestResult"] = None
   197	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   198	
   199	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   200	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   201	
   202	    task_type: Optional[str] = None
   203	    profile_name: Optional[str] = None
   204	
   205	    def to_dict(self) -> Dict[str, Any]:
   206	        """Serialise the bundle to a JSON-compatible dict.
   207	
   208	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   209	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   210	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   211	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   212	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   213	        """
   214	        from dataclasses import asdict
   215	
   216	        return asdict(self)
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 1000, 'offset': 0}, 'id': 'JhWucI7OcB9oMAR00jvjalktMDdQejiy', 'type': 'tool_call'}]
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
    45	from typing import Any, Dict, List, Literal, Optional, Tuple
    46	
    47	from guardkit.orchestrator.coach_verification import (
    48	    CoachVerifier,
    49	    HonestyVerification,
    50	    _resolve_venv_python,
    51	)
    52	from guardkit.orchestrator.quality_gates.coach_evidence import (
    53	    CoachEvidenceBundle,
    54	)
    55	from guardkit.orchestrator.docker_fixtures import (
    56	    get_container_name,
    57	    get_env_exports,
    58	    get_start_commands,
    59	    is_known_service,
    60	)
    61	from guardkit.orchestrator.paths import TaskArtifactPaths
    62	from guardkit.orchestrator.phase_specialists import (
    63	    PHASE_DESCRIPTIONS,
    64	    detect_stack_template,
    65	    render_missing_phase_list,
    66	)
    67	from guardkit.orchestrator.schemas import STATUS_ALIASES
    68	from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
    69	
    70	# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
    71	# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
    72	# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
    73	# module top matches the Player path convention in
    74	# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
    75	# target for tests under ``coach_validator.select_harness``.
    76	from guardkit.orchestrator.exceptions import AgentInvocationError
    77	from guardkit.orchestrator.harness import (
    78	    AssistantMessageEvent,
    79	    ResultMessageEvent,
    80	    ToolResultEvent,
    81	    select_harness,
    82	)
    83	from guardkit.orchestrator.sdk_utils import check_assistant_message_error
    84	
    85	# Optional coach context integration (TASK-SC-009)
    86	try:
    87	    from guardkit.planning.coach_context_builder import build_coach_context
    88	    from guardkit.knowledge.graphiti_client import get_graphiti
    89	    ARCH_CONTEXT_AVAILABLE = True
    90	except ImportError:
    91	    ARCH_CONTEXT_AVAILABLE = False
    92	    build_coach_context = None
    93	    get_graphiti = None
    94	
    95	logger = logging.getLogger(__name__)
    96	
    97	# ============================================================================
    98	# BDD Factory Bridge — wire guardkitfactory.bdd into the Coach evidence path
    99	# ============================================================================
   100	#
   101	# TASK-BDDW-001: Replace the legacy pytest-hardcoded bdd_runner.py path in the
   102	# Coach evidence path with guardkitfactory's plugin-discovery subsystem.
   103	#
   104	# The bridge uses a lazy import (try/except ImportError) so that
   105	# ``pip install guardkit-py`` without the ``[autobuild]`` extra still works.
   106	# When guardkitfactory is unavailable, the Coach falls back to the Player's
   107	# self-reported ``bdd_results`` (legacy behaviour).
   108	#
   109	# Mapping: BDDRunResult (factory) → bundle.bdd dict (legacy shape)
   110	#
   111	#   BDDRunResult.scenarios_attempted  → bundle.bdd["scenarios_attempted"]
   112	#   BDDRunResult.scenarios_passed     → bundle.bdd["scenarios_passed"]
   113	#   BDDRunResult.scenarios_failed     → bundle.bdd["scenarios_failed"]
   114	#   BDDRunResult.scenarios_pending    → bundle.bdd["scenarios_pending"]
   115	#   BDDRunResult.failures             → bundle.bdd["failures"]
   116	#   BDDRunResult.pending              → bundle.bdd["pending"]
   117	#   BDDRunResult.feature_files        → bundle.bdd["feature_files"]
   118	#
   119	# Key contract: ``scenarios_attempted`` is non-Optional on BDDRunResult and
   120	# must be preserved verbatim for the absence-of-failure gate. A value of 0
   121	# means "no scenarios ran" (ABSENT SIGNAL), NOT "zero failures = pass".
   122	
   123	# StackProfile values consumed by guardkitfactory.bdd.discover().
   124	# Mapped from the worktree's project.template string.
   125	_STACK_PROFILE_MAP: Dict[str, str] = {
   126	    "python": "python",
   127	    "fastapi-python": "python",
   128	    "django-python": "python",
   129	    "flask-python": "python",
   130	    ".net": "dotnet",
   131	    "aspnet-core": "dotnet",
   132	    "csharp": "dotnet",
   133	    "node-js": "javascript",
   134	    "javascript": "javascript",
   135	    "typescript": "javascript",
   136	}
   137	"""Mapping from ``project.template`` to ``StackProfile`` string."""
   138	
   139	
   140	def _detect_stack_profile(workspace_root: Optional[Path]) -> Optional[str]:
   141	    """Detect the stack profile from the worktree's template string.
   142	
   143	    Parameters
   144	    ----------
   145	    workspace_root : Optional[Path]
   146	        Root of the worktree. Used to find ``.claude/settings.json``.
   147	
   148	    Returns
   149	    -------
   150	    Optional[str]
   151	        A ``StackProfile``-compatible string (``"python"``, ``"dotnet"``,
   152	        ``"javascript"``) or ``None`` when the template is unknown.
   153	    """
   154	    template = detect_stack_template(workspace_root)
   155	    if template is None:
   156	        return None
   157	    return _STACK_PROFILE_MAP.get(template)
   158	
   159	
   160	def _map_bdd_run_result_to_bundle(
   161	    run_result: "BDDRunResult",
   162	) -> Dict[str, Any]:
   163	    """Map a ``BDDRunResult`` into the legacy ``bundle.bdd`` dict shape.
   164	
   165	    Preserves ``scenarios_attempted`` verbatim — never coerces a missing key
   166	    to 0. This is critical for the absence-of-failure gate: when
   167	    ``scenarios_attempted == 0``, the Coach must treat it as ABSENT SIGNAL,
   168	    not as a silent pass.
   169	
   170	    Parameters
   171	    ----------
   172	    run_result : BDDRunResult
   173	        Result from the factory BDD plugin.
   174	
   175	    Returns
   176	    -------
   177	    Dict[str, Any]
   178	        A dict with keys: ``scenarios_attempted``, ``scenarios_passed``,
   179	        ``scenarios_failed``, ``scenarios_pending``, ``failures``,
   180	        ``pending``, ``feature_files``.
   181	    """
   182	    # Import here to avoid circular import at module level.
   183	    # BDDRunResult is imported lazily from guardkitfactory.
   184	    from dataclasses import asdict
   185	
   186	    failures = run_result.failures
   187	    pending = run_result.pending
   188	
   189	    # Convert FailureDetail/PendingDetail to dicts if they are dataclass instances.
   190	    failure_dicts: List[Dict[str, Any]] = []
   191	    for f in failures:
   192	        if hasattr(f, "asdict") or hasattr(f, "_asdict"):
   193	            failure_dicts.append(asdict(f))
   194	        elif isinstance(f, dict):
   195	            failure_dicts.append(f)
   196	        else:
   197	            failure_dicts.append({
   198	                "scenario_name": getattr(f, "scenario_name", "<unknown>"),
   199	                "failing_step": getattr(f, "failing_step", ""),
   200	                "reason": getattr(f, "reason", ""),
   201	            })
   202	
   203	    pending_dicts: List[Dict[str, Any]] = []
   204	    for p in pending:
   205	        if hasattr(p, "asdict") or hasattr(p, "_asdict"):
   206	            pending_dicts.append(asdict(p))
   207	        elif isinstance(p, dict):
   208	            pending_dicts.append(p)
   209	        else:
   210	            pending_dicts.append({
   211	                "scenario_name": getattr(p, "scenario_name", "<unknown>"),
   212	                "pending_step": getattr(p, "pending_step", ""),
   213	            })
   214	
   215	    return {
   216	        "scenarios_attempted": run_result.scenarios_attempted,
   217	        "scenarios_passed": run_result.scenarios_passed,
   218	        "scenarios_failed": run_result.scenarios_failed,
   219	        "scenarios_pending": run_result.scenarios_pending,
   220	        "failures": failure_dicts,
   221	        "pending": pending_dicts,
   222	        "feature_files": list(run_result.feature_files),
   223	    }
   224	
   225	
   226	# Lazy import of guardkitfactory BDD plugin subsystem.
   227	# The import is guarded so that ``pip install guardkit-py`` without
   228	# ``[autobuild]`` still works — Coach falls back to Player-reported
   229	# bdd_results when the factory is unavailable.
   230	try:
   231	    from guardkitfactory.bdd import (
   232	        BDDRunResult,
   233	        discover,
   234	    )
   235	    from guardkitfactory.bdd.plugin import StackProfile
   236	
   237	    _FACTORY_AVAILABLE = True
   238	except ImportError:
   239	    BDDRunResult = None  # type: ignore[misc,assignment]
   240	    discover = None  # type: ignore[misc,assignment]
   241	    StackProfile = None  # type: ignore[misc,assignment]
   242	    _FACTORY_AVAILABLE = False
   243	
   244	# Module-level cache for the factory import status.
   245	# Re-checked at runtime for each Coach invocation so that a late-installed
   246	# guardkitfactory (e.g. via a post-gather pip install) is picked up.
   247	_factory_available_cache: Optional[bool] = None
   248	
   249	
   250	def _is_factory_available() -> bool:
   251	    """Return True when the guardkitfactory BDD plugin subsystem is importable.
   252	
   253	    Uses a module-level cache that is invalidated on each call to
   254	    ``gather_evidence`` (see the ``_reset_factory_cache`` helper).
   255	    """
   256	    global _factory_available_cache
   257	    if _factory_available_cache is not None:
   258	        return _factory_available_cache
   259	    _factory_available_cache = _FACTORY_AVAILABLE
   260	    return _FACTORY_AVAILABLE
   261	
   262	
   263	def _reset_factory_cache() -> None:
   264	    """Invalidate the factory availability cache.
   265	
   266	    Called at the start of each ``gather_evidence`` invocation so that
   267	    a late-installed guardkitfactory is picked up on subsequent runs.
   268	    """
   269	    global _factory_available_cache
   270	    _factory_available_cache = None
   271	
   272	
   273	def _run_factory_bdd(
   274	    worktree_path: Path,
   275	    stack_profile: Optional[str],
   276	) -> Optional[Dict[str, Any]]:
   277	    """Discover and run the BDD plugin for the given stack profile.
   278	
   279	    Uses ``guardkitfactory.bdd.discover(stack_profile)`` to find the plugin,
   280	    invokes it to get a ``BDDRunResult``, and maps the result into the legacy
   281	    ``bundle.bdd`` dict shape.
   282	
   283	    Parameters
   284	    ----------
   285	    worktree_path : Path
   286	        Root of the worktree containing the BDD scenarios.
   287	    stack_profile : Optional[str]
   288	        Detected stack profile (``"python"``, ``"dotnet"``, ``"javascript"``).
   289	
   290	    Returns
   291	    -------
   292	    Optional[Dict[str, Any]]
   293	        A ``bundle.bdd``-shaped dict, or ``None`` when the factory is
   294	        unavailable, the stack profile is unknown, or discovery fails.
   295	    """
   296	    if not _is_factory_available():
   297	        logger.debug(
   298	            "BDD factory bridge: guardkitfactory not available; "
   299	            "falling back to Player-reported bdd_results.",
   300	        )
   301	        return None
   302	
   303	    if stack_profile is None:
   304	        logger.debug(
   305	            "BDD factory bridge: no stack profile detected; "
   306	            "falling back to Player-reported bdd_results.",
   307	        )
   308	        return None
   309	
   310	    # Guard against StackProfile being None (factory not importable).
   311	    if StackProfile is None:
   312	        return None
   313	
   314	    try:
   315	        plugin = discover(stack_profile)
   316	        if plugin is None:
   317	            logger.debug(
   318	                "BDD factory bridge: no plugin discovered for stack %s; "
   319	                "falling back to Player-reported bdd_results.",
   320	                stack_profile,
   321	            )
   322	            return None
   323	
   324	        # Invoke the plugin to get BDDRunResult.
   325	        # The plugin is responsible for running the scenarios and returning
   326	        # a BDDRunResult with the counts-only contract.
   327	        result = plugin.run(worktree_path)
   328	
   329	        if result is None:
   330	            logger.debug(
   331	                "BDD factory bridge: plugin returned None for stack %s; "
   332	                "falling back to Player-reported bdd_results.",
   333	                stack_profile,
   334	            )
   335	            return None
   336	
   337	        # Map BDDRunResult → bundle.bdd shape.
   338	        return _map_bdd_run_result_to_bundle(result)
   339	
   340	    except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering
   341	        logger.warning(
   342	            "BDD factory bridge raised %s for stack %s; "
   343	            "falling back to Player-reported bdd_results.",
   344	            exc.__class__.__name__,
   345	            stack_profile,
   346	        )
   347	        return None
   348	
   349	
   350	# ============================================================================
   351	# Wiring Factory Bridge — wire guardkitfactory.wiring into the Coach evidence
   352	# ============================================================================
   353	#
   354	# TASK-QAWE-002 (Wave-1): Lazy import of the UNWIRED_PATH / MOCKED_SEAM
   355	# analyzer. The import is guarded so that ``pip install guardkit-py`` without
   356	# the ``[autobuild]`` extra still works — Coach leaves all three wiring
   357	# fields as ``None`` when the factory is unavailable.
   358	#
   359	# The seam returns a dict (never the dataclass) so coach_evidence.py keeps
   360	# zero guardkitfactory import.
   361	
   362	try:
   363	    from guardkitfactory.wiring import (  # type: ignore[attr-defined,no-redef]
   364	        analyze_wiring,
   365	    )
   366	
   367	    _WIRING_FACTORY_AVAILABLE = True
   368	except ImportError:
   369	    analyze_wiring = None  # type: ignore[misc,assignment]
   370	    _WIRING_FACTORY_AVAILABLE = False
   371	
   372	_wiring_factory_available_cache: Optional[bool] = None
   373	
   374	
   375	def _is_wiring_factory_available() -> bool:
   376	    """Return True when the guardkitfactory wiring analyzer is importable."""
   377	    global _wiring_factory_available_cache
   378	    if _wiring_factory_available_cache is not None:
   379	        return _wiring_factory_available_cache
   380	    _wiring_factory_available_cache = _WIRING_FACTORY_AVAILABLE
   381	    return _WIRING_FACTORY_AVAILABLE
   382	
   383	
   384	def _reset_wiring_factory_cache() -> None:
   385	    """Invalidate the wiring factory availability cache."""
   386	    global _wiring_factory_available_cache
   387	    _wiring_factory_available_cache = None
   388	
   389	
   390	def _compute_authored_set(
   391	    task_work_results: Dict[str, Any],
   392	) -> List[str]:
   393	    """Compute the set of source files authored by the Player this turn.
   394	
   395	    Uses the presence-based fallback from the task-work results:
   396	    ``files_authored`` when present, else ``files_created ∪ files_modified``.
   397	
   398	    This is NOT the git-enriched ``files_modified`` (which can be
   399	    peer-contaminated in parallel-wave execution).
   400	
   401	    Parameters
   402	    ----------
   403	    task_work_results : Dict[str, Any]
   404	        The task-work results dict from ``read_quality_gate_results``.
   405	
   406	    Returns
   407	    -------
   408	    List[str]
   409	        List of authored file paths (relative to worktree root).
   410	    """
   411	    files_authored = task_work_results.get("files_authored")
   412	    if files_authored and isinstance(files_authored, list):
   413	        return [str(f) for f in files_authored]
   414	
   415	    # Fallback: files_created ∪ files_modified
   416	    created = task_work_results.get("files_created") or []
   417	    modified = task_work_results.get("files_modified") or []
   418	    authored: List[str] = []
   419	    seen: set = set()
   420	    for f in list(created) + list(modified):
   421	        fs = str(f)
   422	        if fs not in seen:
   423	            seen.add(fs)
   424	            authored.append(fs)
   425	    return authored
   426	
   427	
   428	def _run_wiring_analysis(
   429	    worktree_path: Path,
   430	    authored_files: List[str],
   431	    task_type: str,
   432	    stack_template: Optional[str],
   433	) -> Optional[Dict[str, Any]]:
   434	    """Run the wiring analysis for the authored files.
   435	
   436	    Returns a dict with ``wiring``, ``mocked_seam``, and ``spec_gap`` keys
   437	    (some may be ``None``). Returns ``None`` when the task type gates out
   438	    (SCAFFOLDING/DOCUMENTATION) or there are no authored source targets.
   439	
   440	    Parameters
   441	    ----------
   442	    worktree_path : Path
   443	        Root of the worktree.
   444	    authored_files : List[str]
   445	        Source files authored this turn.
   446	    task_type : str
   447	        Resolved task type (e.g. ``"feature"``, ``"scaffolding"``).
   448	    stack_template : Optional[str]
   449	        Detected stack template (e.g. ``"python"``, ``"fastapi-python"``).
   450	
   451	    Returns
   452	    -------
   453	    Optional[Dict[str, Any]]
   454	        Dict with ``wiring``, ``mocked_seam``, ``spec_gap`` keys, or ``None``
   455	        when the probe legitimately did not run.
   456	    """
   457	    # Task-type gate: SCAFFOLDING / DOCUMENTATION → all fields None.
   458	    if task_type in ("scaffolding", "documention", "documentation", "testing"):
   459	        logger.debug(
   460	            "wiring analysis: task_type=%s gates out; "
   461	            "all three fields left as None.",
   462	            task_type,
   463	        )
   464	        return None
   465	
   466	    # Zero-authored-targets gate → None (probe legitimately did not run).
   467	    if not authored_files:
   468	        logger.debug(
   469	            "wiring analysis: no authored source targets; "
   470	            "all three fields left as None.",
   471	        )
   472	        return None
   473	
   474	    # Factory unavailable → all fields None (graceful import absence).
   475	    if not _is_wiring_factory_available() or analyze_wiring is None:
   476	        logger.debug(
   477	            "wiring analysis: guardkitfactory.wiring not available; "
   478	            "all three fields left as None.",
   479	        )
   480	        return None
   481	
   482	    # Resolve stack profile for the factory call.
   483	    stack_profile = _STACK_PROFILE_MAP.get(stack_template) if stack_template else None
   484	
   485	    try:
   486	        result = analyze_wiring(
   487	            authored_files=authored_files,
   488	            worktree_path=worktree_path,
   489	            task_type=task_type,
   490	            stack=stack_profile,
   491	        )
   492	        # analyze_wiring returns a dict with wiring/mocked_seam/spec_gap keys.
   493	        # If it returns None (task-type gate or zero targets inside the
   494	        # factory), all three fields stay None.
   495	        if result is None:
   496	            return None
   497	        return result
   498	    except Exception as exc:  # noqa: BLE001 — analyzer errors must not break gathering
   499	        logger.warning(
   500	            "wiring analysis raised %s; all three fields left as None.",
   501	            exc.__class__.__name__,
   502	        )
   503	        return None
   504	
   505	
   506	# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
   507	# description. Filename-based detection (the soft gate at
   508	# ``_check_seam_test_recommendation``) tolerates "integration" too, but the
   509	# blocking gate requires explicit marker decoration so a plain integration test
   510	# can't silently satisfy a contract obligation. Match the established marker
   511	# precedent: `seam`, `contract`, `boundary`.
   512	_SEAM_PYTEST_MARKERS = ("seam", "contract", "boundary")
   513	
   514	# Header pattern: any markdown header level (`#` to `######`) whose title is
   515	# exactly "Seam Tests" (case-insensitive, trailing whitespace allowed). The
   516	# closing `$` plus `re.MULTILINE` matches the header line in isolation so we
   517	# don't false-trigger on prose like "## Seam Tests are useful because…".
   518	_SEAM_TESTS_HEADER_RE = re.compile(
   519	    r"^\s*#{1,6}\s+seam\s+tests\s*$",
   520	    re.IGNORECASE | re.MULTILINE,
   521	)
   522	
   523	
   524	def _extract_seam_tests_section(description: Optional[str]) -> Optional[str]:
   525	    """Extract the body of a ``## Seam Tests`` markdown section.
   526	
   527	    Returns the section body (everything between the ``## Seam Tests`` header
   528	    and the next sibling-or-higher header, or EOF) when the section exists
   529	    AND has non-whitespace content. Returns ``None`` for any of:
   530	
   531	    * ``description`` is empty / None
   532	    * No ``Seam Tests`` header is present
   533	    * The header exists but the body is whitespace-only (empty stub block)
   534	
   535	    The "non-empty body" rule is what TASK-FIX-A7B4 AC-001 calls "precise"
   536	    detection: a developer who wants to acknowledge "no seam tests for this
   537	    task" can leave the section empty (or omit it) without tripping the gate.
   538	    """
   539	    if not description:
   540	        return None
   541	    match = _SEAM_TESTS_HEADER_RE.search(description)
   542	    if not match:
   543	        return None
   544	    # Find the level of the matched header so we know what closes the section.
   545	    header_line = match.group(0)
   546	    header_level = len(header_line.lstrip().split(" ", 1)[0])  # count of '#'
   547	
   548	    # Body starts after the header line.
   549	    body_start = match.end()
   550	    rest = description[body_start:]
   551	    # The section closes at the next header of equal-or-higher level.
   552	    closing_re = re.compile(
   553	        rf"^\s*#{{1,{header_level}}}\s+\S",
   554	        re.MULTILINE,
   555	    )
   556	    close_match = closing_re.search(rest)
   557	    body = rest[: close_match.start()] if close_match else rest
   558	    if not body.strip():
   559	        return None
   560	    return body
   561	
   562	
   563	# Stopwords for keyword extraction in fuzzy text matching
   564	STOPWORDS = {
   565	    "the", "and", "is", "or", "a", "an", "for", "with", "to", "in", "of",
   566	    "from", "by", "on", "at", "that", "this", "are", "be", "do", "have",
   567	    "has", "as", "if", "can", "will", "would", "could", "should", "may",
   568	    "must", "was", "were", "been", "but", "not", "no", "all", "some",
   569	    "any", "more", "most", "only", "than", "then", "there", "their",
   570	    "who", "which", "when", "where", "how",
   571	}
   572	
   573	# ============================================================================
   574	# Data Models
   575	# ============================================================================
   576	
   577	
   578	@dataclass
   579	class QualityGateStatus:
   580	    """
   581	    Status of individual quality gates from task-work execution.
   582	
   583	    Attributes
   584	    ----------
   585	    tests_passed : bool
   586	        Whether all tests passed in Phase 4.5
   587	    coverage_met : bool
   588	        Whether coverage threshold was met
   589	    arch_review_passed : bool
   590	        Whether architectural review passed (score >= 60)
   591	    plan_audit_passed : bool
   592	        Whether plan audit had zero violations
   593	    all_gates_passed : bool
   594	        True only if ALL gates passed (computed)
   595	    tests_required : bool
   596	        Whether tests were required by task type profile
   597	    coverage_required : bool
   598	        Whether coverage was required by task type profile
   599	    arch_review_required : bool
   600	        Whether architectural review was required by task type profile
   601	    plan_audit_required : bool
   602	        Whether plan audit was required by task type profile
   603	    """
   604	
   605	    tests_passed: bool
   606	    coverage_met: bool
   607	    arch_review_passed: bool
   608	    plan_audit_passed: bool
   609	    tests_required: bool = True
   610	    coverage_required: bool = True
   611	    arch_review_required: bool = True
   612	    plan_audit_required: bool = True
   613	    all_gates_passed: bool = field(init=False)
   614	
   615	    def __post_init__(self):
   616	        """Compute all_gates_passed from individual gate results and requirements."""
   617	        # Only check gates that are required
   618	        required_gates = []
   619	        if self.tests_required:
   620	            required_gates.append(self.tests_passed)
   621	        if self.coverage_required:
   622	            required_gates.append(self.coverage_met)
   623	        if self.arch_review_required:
   624	            required_gates.append(self.arch_review_passed)
   625	        if self.plan_audit_required:
   626	            required_gates.append(self.plan_audit_passed)
   627	
   628	        # All required gates must pass
   629	        self.all_gates_passed = all(required_gates) if required_gates else True
   630	
   631	
   632	@dataclass
   633	class IndependentTestResult:
   634	    """
   635	    Result of independent test verification.
   636	
   637	    Attributes
   638	    ----------
   639	    tests_passed : bool
   640	        Whether tests passed when run independently
   641	    test_command : str
   642	        Command used to run tests
   643	    test_output_summary : str
   644	        Summary of test output
   645	    duration_seconds : float
   646	        Time taken to run tests
   647	    raw_output : Optional[str]
   648	        Full stdout+stderr from test execution, used for failure classification
   649	    signal_absent : bool
   650	        ``True`` when the independent-test oracle did NOT produce a verdict —
   651	        the run timed out or failed at the transport layer (SDK timeout, SDK
   652	        API error, subprocess/isolated-test timeout, or generic execution
   653	        error) before pytest could report a pass/fail. This is distinct from
   654	        "ran and failed" (``tests_passed=False`` with ``signal_absent=False``):
   655	        an absent signal means the trust-but-verify leg never completed.
   656	        ``tests_passed`` is always ``False`` when ``signal_absent`` is ``True``
   657	        so the result can never read as a pass. The Coach's
   658	        absence-of-failure guard (TASK-FIX-COACHTESTTO) treats an absent
   659	        independent-test signal as ABSENT — surfaced as feedback, never
   660	        approved on the Player's self-reported tests. See
   661	        ``.claude/rules/absence-of-failure-is-not-success.md``.
   662	    """
   663	
   664	    tests_passed: bool
   665	    test_command: str
   666	    test_output_summary: str
   667	    duration_seconds: float
   668	    raw_output: Optional[str] = None
   669	    signal_absent: bool = False
   670	
   671	
   672	@dataclass
   673	class CriterionResult:
   674	    """
   675	    Structured result for a single acceptance criterion.
   676	
   677	    Attributes
   678	    ----------
   679	    criterion_id : str
   680	        Unique identifier (e.g., "AC-001")
   681	    criterion_text : str
   682	        Full text of the acceptance criterion
   683	    result : str
   684	        Verification result: "verified", "rejected", or "pending"
   685	    status : str
   686	        Alias for result, used by _count_criteria_passed consumer
   687	    evidence : str
   688	        Summary of what was checked to determine the result
   689	    """
   690	
   691	    criterion_id: str
   692	    criterion_text: str
   693	    result: str  # "verified" | "rejected" | "pending"
   694	    status: str  # same as result, for _count_criteria_passed compatibility
   695	    evidence: str
   696	
   697	    def to_dict(self) -> Dict[str, Any]:
   698	        """Convert to dictionary for JSON serialization."""
   699	        return {
   700	            "criterion_id": self.criterion_id,
   701	            "criterion_text": self.criterion_text,
   702	            "result": self.result,
   703	            "status": self.status,
   704	            "evidence": self.evidence,
   705	            "notes": self.evidence,  # alias for _display_criteria_progress
   706	        }
   707	
   708	
   709	@dataclass
   710	class RequirementsValidation:
   711	    """
   712	    Result of requirements satisfaction validation.
   713	
   714	    Attributes
   715	    ----------
   716	    criteria_total : int
   717	        Total acceptance criteria count
   718	    criteria_met : int
   719	        Number of criteria met
   720	    all_criteria_met : bool
   721	        True if all criteria are met
   722	    missing : List[str]
   723	        List of missing/unmet criteria
   724	    criteria_results : List[CriterionResult]
   725	        Per-criterion structured verification results
   726	    """
   727	
   728	    criteria_total: int
   729	    criteria_met: int
   730	    all_criteria_met: bool
   731	    missing: List[str] = field(default_factory=list)
   732	    criteria_results: List[CriterionResult] = field(default_factory=list)
   733	
   734	
   735	@dataclass
   736	class CoachValidationResult:
   737	    """
   738	    Complete result from Coach validation.
   739	
   740	    Attributes
   741	    ----------
   742	    task_id : str
   743	        Task identifier
   744	    turn : int
   745	        Turn number
   746	    decision : Literal["approve", "feedback"]
   747	        Coach's decision
   748	    quality_gates : Optional[QualityGateStatus]
   749	        Quality gate status (None if results not found)
   750	    independent_tests : Optional[IndependentTestResult]
   751	        Independent test verification result
   752	    requirements : Optional[RequirementsValidation]
   753	        Requirements validation result
   754	    issues : List[Dict[str, Any]]
   755	        List of issues if feedback
   756	    rationale : str
   757	        Explanation of decision
   758	    """
   759	
   760	    task_id: str
   761	    turn: int
   762	    decision: Literal["approve", "feedback", "deferred"]
   763	    quality_gates: Optional[QualityGateStatus] = None
   764	    independent_tests: Optional[IndependentTestResult] = None
   765	    requirements: Optional[RequirementsValidation] = None
   766	    issues: List[Dict[str, Any]] = field(default_factory=list)
   767	    rationale: str = ""
   768	    context_used: Optional[str] = None
   769	    approved_without_independent_tests: bool = False
   770	    is_configuration_error: bool = False
   771	    environment_conditional_approval: bool = False
   772	    # TASK-AB-FIX-INVAB1 AC-003: surface honesty verification result for
   773	    # observability in coach_turn_N.json. None when verification was not
   774	    # invoked (e.g. operator-handoff short-circuit, missing-results path).
   775	    honesty_verification: Optional[HonestyVerification] = None
   776	
   777	    def to_dict(self) -> Dict[str, Any]:
   778	        """
   779	        Convert result to dictionary for JSON serialization.
   780	
   781	        Includes ``criteria_verification`` and ``acceptance_criteria_verification``
   782	        fields consumed by ``_display_criteria_progress`` and ``_count_criteria_passed``
   783	        in the AutoBuild orchestrator.
   784	
   785	        Returns
   786	        -------
   787	        Dict[str, Any]
   788	            Dictionary representation suitable for JSON
   789	        """
   790	        # Build per-criterion results from requirements validation
   791	        criteria_verification: List[Dict[str, Any]] = []
   792	        acceptance_criteria_results: List[Dict[str, Any]] = []
   793	        if self.requirements and self.requirements.criteria_results:
   794	            criteria_verification = [
   795	                cr.to_dict() for cr in self.requirements.criteria_results
   796	            ]
   797	            acceptance_criteria_results = [
   798	                cr.to_dict() for cr in self.requirements.criteria_results
   799	            ]
   800	
   801	        return {
   802	            "task_id": self.task_id,
   803	            "turn": self.turn,
   804	            "decision": self.decision,
   805	            "validation_results": {
   806	                "quality_gates": {
   807	                    "tests_passed": self.quality_gates.tests_passed,
   808	                    "coverage_met": self.quality_gates.coverage_met,
   809	                    "arch_review_passed": self.quality_gates.arch_review_passed,
   810	                    "plan_audit_passed": self.quality_gates.plan_audit_passed,
   811	                    "all_gates_passed": self.quality_gates.all_gates_passed,
   812	                } if self.quality_gates else None,
   813	                "independent_tests": {
   814	                    "tests_passed": self.independent_tests.tests_passed,
   815	                    "test_command": self.independent_tests.test_command,
   816	                    "test_output_summary": self.independent_tests.test_output_summary,
   817	                    "duration_seconds": self.independent_tests.duration_seconds,
   818	                } if self.independent_tests else None,
   819	                "requirements": {
   820	                    "criteria_total": self.requirements.criteria_total,
   821	                    "criteria_met": self.requirements.criteria_met,
   822	                    "all_criteria_met": self.requirements.all_criteria_met,
   823	                    "missing": self.requirements.missing,
   824	                } if self.requirements else None,
   825	            },
   826	            # For _display_criteria_progress (autobuild.py:2555)
   827	            "criteria_verification": criteria_verification,
   828	            # For _count_criteria_passed (autobuild.py:2254)
   829	            "acceptance_criteria_verification": {
   830	                "criteria_results": acceptance_criteria_results,
   831	            },
   832	            "issues": self.issues,
   833	            "rationale": self.rationale,
   834	            "context_used": self.context_used,
   835	            "approved_without_independent_tests": self.approved_without_independent_tests,
   836	            "is_configuration_error": self.is_configuration_error,
   837	            "environment_conditional_approval": self.environment_conditional_approval,
   838	            # TASK-AB-FIX-INVAB1 AC-003: mirror the LLM Coach honesty schema
   839	            # (verified, honesty_score, discrepancy_count) — see
   840	            # installer/core/agents/autobuild-coach.md:165-184.
   841	            "honesty_verification": (
   842	                {
   843	                    "verified": self.honesty_verification.verified,
   844	                    "honesty_score": self.honesty_verification.honesty_score,
   845	                    "discrepancy_count": len(
   846	                        self.honesty_verification.discrepancies
   847	                    ),
   848	                    # TASK-FIX-1B4A (Layer 1): expose state_bridge identity
   849	                    # resolutions for audit. Empty list when no resolutions
   850	                    # occurred (typical case) or wiring was absent.
   851	                    "resolved_paths": [
   852	                        {
   853	                            "claimed": rp.claimed,
   854	                            "resolved_to": rp.resolved_to,
   855	                            "task_id": rp.task_id,
   856	                        }
   857	                        for rp in self.honesty_verification.resolved_paths
   858	                    ],
   859	                }
   860	                if self.honesty_verification is not None
   861	                else None
   862	            ),
   863	        }
   864	
   865	
   866	# ============================================================================
   867	# Coach Validator
   868	# ============================================================================
   869	
   870	
   871	class CoachValidator:
   872	    """
   873	    Lightweight Coach that validates task-work results.
   874	
   875	    This class does NOT reimplement quality gates - it reads task-work outputs
   876	    and performs independent verification before making approve/feedback decision.
   877	
   878	    Validation Flow
   879	    ---------------
   880	    1. Read task-work results from JSON file
   881	    2. Verify all quality gates passed
   882	    3. Run independent test verification (trust but verify)
   883	    4. Validate requirements satisfaction
   884	    5. Return approve if all checks pass, feedback otherwise
   885	
   886	    Attributes
   887	    ----------
   888	    worktree_path : Path
   889	        Path to the git worktree
   890	    test_command : Optional[str]
   891	        Command to run tests (auto-detected or specified)
   892	    test_timeout : int
   893	        Timeout for test execution in seconds
   894	
   895	    Example
   896	    -------
   897	    >>> validator = CoachValidator("/path/to/worktree")
   898	    >>> result = validator.validate("TASK-001", 1, {"acceptance_criteria": [...]})
   899	    >>> print(f"Decision: {result.decision}")
   900	    """
   901	
   902	    # Quality gate thresholds (match task-work)
   903	    ARCH_REVIEW_THRESHOLD = 60
   904	    # Default profile for backward compatibility
   905	    DEFAULT_PROFILE = get_profile(TaskType.FEATURE)
   906	
   907	    # High-confidence infrastructure patterns (safe for conditional approval)
   908	    _INFRA_HIGH_CONFIDENCE: List[str] = [
   909	        # Connection/network errors
   910	        "ConnectionRefusedError",
   911	        "ConnectionError",
   912	        "Connection refused",
   913	        "could not connect to server",
   914	        # Database drivers
   915	        "OperationalError",
   916	        "psycopg2",
   917	        "psycopg",
   918	        "asyncpg",
   919	        "sqlalchemy.exc.OperationalError",
   920	        "django.db.utils.OperationalError",
   921	        "pymongo.errors.ServerSelectionTimeoutError",
   922	        "redis.exceptions.ConnectionError",
   923	    ]
   924	
   925	    # SDK API error patterns — the LLM backend rejected the request (wrong model
   926	    # name, invalid parameters, rate limits, etc.).  These are NOT code defects.
   927	    _SDK_API_ERROR_PATTERNS: List[str] = [
   928	        "SDK API error",
   929	        "invalid_request",
   930	        "invalid_request_error",
   931	        "AssistantMessage.error",
   932	    ]
   933	
   934	    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
   935	    _INFRA_AMBIGUOUS: List[str] = [
   936	        "ModuleNotFoundError",
   937	        "ImportError",
   938	        "No module named",
   939	    ]
   940	
   941	    # Known service-client libraries whose absence indicates a missing dependency
   942	    # install (not a code defect). ModuleNotFoundError for these is promoted to
   943	    # high confidence.
   944	    # NOTE: psycopg2 is intentionally excluded — projects using asyncpg may
   945	    # accidentally import psycopg2, which is a Player code-choice error, not an
   946	    # infrastructure failure.  Classifying it as ("infrastructure", "high") gave
   947	    # the Player wrong advice (mock fixtures / SQLite) instead of telling them to
   948	    # remove the wrong import.
   949	    _KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
   950	        "asyncpg",
   951	        "pymongo",
   952	        "redis",
   953	        "psycopg",
   954	        "sqlalchemy",
   955	        "motor",
   956	        "aioredis",
   957	        "cassandra",
   958	    ]
   959	
   960	    def __init__(
   961	        self,
   962	        worktree_path: str,
   963	        test_command: Optional[str] = None,
   964	        test_timeout: int = 300,
   965	        task_id: Optional[str] = None,
   966	        coach_test_execution: str = "sdk",
   967	        matching_strategy: str = "auto",
   968	        wave_size: int = 1,
   969	        turn: int = 1,
   970	        peer_changed_files: Optional[Dict[str, Any]] = None,
   971	        model_name: Optional[str] = None,
   972	        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
   973	        venv_python: Optional[str] = None,  # TASK-FIX-COACHPYENV
   974	    ):
   975	        """
   976	        Initialize CoachValidator.
   977	
   978	        Parameters
   979	        ----------
   980	        worktree_path : str
   981	            Path to the git worktree where validation should execute
   982	        test_command : Optional[str]
   983	            Command to run tests. If None, auto-detects based on project.
   984	        test_timeout : int
   985	            Timeout for test execution in seconds (default: 300s)
   986	        task_id : Optional[str]
   987	            Task identifier for task-specific test filtering in shared worktrees.
   988	            When provided, test detection will first look for task-specific test
   989	            files before falling back to running the full test suite.
   990	        coach_test_execution : str
   991	            Test execution mode: "sdk" (default) uses Claude Agent SDK via Bash
   992	            tool for environment parity; "subprocess" uses subprocess.run() directly.
   993	        matching_strategy : str
   994	            Text matching strategy for acceptance criteria verification.
   995	            ``"text"``: strict Jaccard threshold (70%), ``"semantic"``: lower
   996	            threshold (50%) with fuzzy keyword prefix matching for local/vLLM
   997	            backends, ``"auto"`` (default): resolves to ``"semantic"`` when
   998	            ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint, otherwise
   999	            ``"text"``.  Can also be set via ``GUARDKIT_MATCHING_STRATEGY`` env var.
  1000	        wave_size : int
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 1000, 'offset': 1000}, 'id': 'BFT1n1PPIky0I0fg8myehs4OeqIMYLUC', 'type': 'tool_call'}]
Tool:   1001	            Number of tasks executing in parallel in the current wave (default: 1).
  1002	            When >1, the Coach runs independent tests in an isolated temp directory
  1003	            to prevent spurious failures from concurrent worktree mutations, and
  1004	            applies more lenient failure classification for contention-related errors.
  1005	        peer_changed_files : Optional[Dict[str, Iterable[str]]]
  1006	            Snapshot of files edited by other in-flight tasks in the same parallel
  1007	            wave, keyed by peer task id. When this Coach classifies a failure as
  1008	            ``parallel_contention`` (or as ``code`` in a parallel wave), it checks
  1009	            whether this task's own edits overlap with any peer's edits. Overlap
  1010	            means the failure is real source-file contention, not transient infra
  1011	            contention, so the conditional approval rule from TASK-ABFIX-005 must
  1012	            NOT fire — instead Coach returns feedback and the existing
  1013	            Player-Coach loop retries on the next turn (by which point peers have
  1014	            completed and the wave is naturally serialised). See TASK-FIX-A7B2.
  1015	        model_name : Optional[str]
  1016	            Orchestrator-configured model name to thread through to the harness
  1017	            for SDK-based Coach test execution. Used as a fallback when the
  1018	            ``GUARDKIT_COACH_TEST_MODEL`` env var is not set. Mirrors the model
  1019	            threading precedent set by TASK-FIX-LGFM2 / TASK-FIX-MODELPLUMB in
  1020	            ``AgentInvoker``. Without this, the LangGraph harness receives
  1021	            ``model=None`` for ``role='coach_test'`` and falls back to subprocess
  1022	            (TASK-FIX-LGFM3 / F12).
  1023	        venv_python : Optional[str]
  1024	            Path to the bootstrap venv Python interpreter Coach should run its
  1025	            independent tests under (typically ``BootstrapResult.venv_python``
  1026	            threaded from the feature orchestrator). When set, the SDK and
  1027	            subprocess test paths pin pytest to this interpreter instead of the
  1028	            host ``which pytest`` / ``sys.executable``. Resolution follows
  1029	            :func:`guardkit.orchestrator.coach_verification._resolve_venv_python`.
  1030	            Without it, Coach could validate against the wrong interpreter
  1031	            (TASK-FIX-COACHPYENV — sibling of the TASK-FIX-7A05 CoachVerifier fix).
  1032	        """
  1033	        self.worktree_path = Path(worktree_path)
  1034	        self.test_command = test_command
  1035	        self.test_timeout = test_timeout
  1036	        self.task_id = task_id
  1037	        self._coach_test_execution = coach_test_execution
  1038	        # TASK-FIX-COACHPYENV: resolve the interpreter Coach runs independent
  1039	        # tests under. Prefers the explicit bootstrap venv, then a filesystem
  1040	        # ``<worktree>/.guardkit/venv/bin/python`` recovery, else None (PATH
  1041	        # pytest / sys.executable for non-Python projects). Reuses the helper
  1042	        # already battle-tested for CoachVerifier (TASK-FIX-7A05) so the two
  1043	        # Coach verification surfaces resolve interpreters identically.
  1044	        self._configured_venv_python: Optional[str] = venv_python
  1045	        self._venv_python: Optional[Path] = _resolve_venv_python(
  1046	            self.worktree_path, venv_python
  1047	        )
  1048	        if venv_python and (
  1049	            self._venv_python is None
  1050	            or str(self._venv_python) != str(Path(venv_python))
  1051	        ):
  1052	            # AC-4 mismatch guard: a bootstrap interpreter was configured but
  1053	            # the resolved interpreter differs (stale path / disappeared venv).
  1054	            # Loud WARNING — Coach is about to verify against a DIFFERENT
  1055	            # interpreter than the bootstrap installed packages into, which is
  1056	            # exactly the run-9 spurious-failure shape.
  1057	            logger.warning(
  1058	                "Coach test interpreter MISMATCH: configured bootstrap venv "
  1059	                "%s but resolved to %s. Independent tests may run under the "
  1060	                "wrong interpreter (TASK-FIX-COACHPYENV).",
  1061	                venv_python,
  1062	                self._venv_python if self._venv_python is not None else
  1063	                "PATH pytest / sys.executable",
  1064	            )
  1065	        elif self._venv_python is not None:
  1066	            logger.info(
  1067	                "CoachValidator pinning independent-test interpreter to %s",
  1068	                self._venv_python,
  1069	            )
  1070	        # TASK-FIX-LGFM3: orchestrator model threaded through for SDK test
  1071	        # execution path; falls back to None when caller didn't supply one.
  1072	        self._model_name: Optional[str] = model_name
  1073	        # TASK-FIX-COACHBUDG01 (2026-06-06): per-role Coach override. When
  1074	        # non-None, takes precedence over _model_name for the coach_test
  1075	        # path (consumed by _get_coach_test_model). Lets the operator
  1076	        # route Coach SDK test execution to the same Coach-specific model
  1077	        # (gemma4:26b) the Player↔Coach loop uses.
  1078	        self._coach_model_name: Optional[str] = coach_model_name
  1079	        self.wave_size = max(1, int(wave_size))
  1080	        # TASK-DIAG-F4A2: Turn number for sdk_debug preservation paths.
  1081	        # Default 1 keeps backwards-compat for callers that don't pass it.
  1082	        self._turn = max(1, int(turn))
  1083	        # TASK-FIX-A7B2: Wave-peer file-edit snapshot for source-file contention
  1084	        # detection. Normalised to ``Dict[str, frozenset[str]]`` so the overlap
  1085	        # check is a cheap set intersection.
  1086	        self._peer_changed_files: Dict[str, frozenset] = {}
  1087	        if peer_changed_files:
  1088	            for peer_id, files in peer_changed_files.items():
  1089	                if not peer_id or peer_id == self.task_id:
  1090	                    continue
  1091	                if not files:
  1092	                    continue
  1093	                self._peer_changed_files[peer_id] = frozenset(
  1094	                    str(f) for f in files if f
  1095	                )
  1096	        # Resolve matching strategy: constructor arg > env var > "auto"
  1097	        _VALID_STRATEGIES = ("auto", "text", "semantic")
  1098	        env_strategy = os.environ.get("GUARDKIT_MATCHING_STRATEGY", "").lower()
  1099	        if matching_strategy not in _VALID_STRATEGIES:
  1100	            logger.warning(
  1101	                "Unrecognised matching_strategy %r, falling back to 'auto'",
  1102	                matching_strategy,
  1103	            )
  1104	            matching_strategy = "auto"
  1105	        if matching_strategy != "auto":
  1106	            self._matching_strategy = matching_strategy
  1107	        elif env_strategy in ("text", "semantic"):
  1108	            self._matching_strategy = env_strategy
  1109	        else:
  1110	            self._matching_strategy = "auto"
  1111	
  1112	        logger.debug(
  1113	            f"CoachValidator initialized for worktree: {worktree_path}, "
  1114	            f"task_id: {task_id}, wave_size: {self.wave_size}"
  1115	        )
  1116	
  1117	    @property
  1118	    def is_parallel(self) -> bool:
  1119	        """Return True when this Coach is running in a parallel wave (wave_size > 1)."""
  1120	        return self.wave_size > 1
  1121	
  1122	    def _detect_source_file_contention(
  1123	        self,
  1124	        task_work_results: Dict[str, Any],
  1125	    ) -> Dict[str, frozenset]:
  1126	        """Detect source-file contention with in-flight peer tasks (TASK-FIX-A7B2).
  1127	
  1128	        Returns a mapping ``peer_task_id -> frozenset[overlapping_file]`` for
  1129	        every peer that edited at least one file this task also edited within
  1130	        the same parallel wave. An empty mapping means there is no source-file
  1131	        contention — the failure is either genuinely transient (e.g. infra
  1132	        flakiness, partial __init__.py write race) or unrelated to peer edits,
  1133	        so the existing TASK-ABFIX-005 conditional approval path remains safe.
  1134	
  1135	        A non-empty mapping means the parallel_contention is real source-file
  1136	        contention (e.g. two tasks writing conflicting step definitions to a
  1137	        shared BDD glue file). The TASK-ABFIX-005 isolation snapshot cannot
  1138	        defend against this case because the snapshot captures the
  1139	        already-corrupted shared file. Conditional approval would mask real
  1140	        correctness damage, so the caller must fall through to feedback and
  1141	        let the existing Player-Coach retry machinery serialise the next
  1142	        attempt (by which point peers have completed and the wave is
  1143	        effectively single-tasked).
  1144	
  1145	        Parameters
  1146	        ----------
  1147	        task_work_results : Dict[str, Any]
  1148	            Player's task_work_results.json payload. Reads ``files_authored``
  1149	            (Player's explicit Write/Edit tool calls — TASK-FIX-CC-COND) when
  1150	            present, otherwise falls back to ``files_created`` /
  1151	            ``files_modified`` for compatibility with pre-files_authored
  1152	            artefacts.
  1153	
  1154	        Returns
  1155	        -------
  1156	        Dict[str, frozenset[str]]
  1157	            Map from peer task id to set of overlapping file paths. Empty when
  1158	            no peer edits overlap, when this task has no recorded edits, or
  1159	            when no peer snapshot was supplied.
  1160	
  1161	        Notes
  1162	        -----
  1163	        TASK-FIX-CC-COND: ``files_modified`` / ``files_created`` are
  1164	        unioned with worktree-wide ``git diff`` output by ``agent_invoker``
  1165	        before they reach this validator, so in shared-worktree parallel
  1166	        waves they include peer-task edits this task never authored. Using
  1167	        them as the contention input produced false-positive
  1168	        ``parallel_contention`` verdicts that blocked the conditional
  1169	        approval path the design relies on (see TASK-REV-CC40 finding F-3,
  1170	        FEAT-39E1 turn-2 evidence). ``files_authored`` is captured at the
  1171	        SDK Write/Edit boundary and is *not* enriched with git output, so
  1172	        it remains authoritative. The fallback is presence-based, not
  1173	        truthy-based: ``files_authored = []`` correctly means "this task
  1174	        authored nothing" and yields no contention, even when
  1175	        ``files_modified`` is contaminated.
  1176	        """
  1177	        if not self._peer_changed_files:
  1178	            return {}
  1179	
  1180	        # TASK-FIX-CC-COND: prefer the Player's authored set when present.
  1181	        # Presence-based fallback: distinguish "field absent" (legacy
  1182	        # task_work_results.json from before files_authored existed) from
  1183	        # "field present, empty" (this task's Player did no Write/Edit).
  1184	        if "files_authored" in task_work_results:
  1185	            authored_raw = task_work_results.get("files_authored") or []
  1186	            own = {str(f) for f in authored_raw if f}
  1187	            source = "files_authored"
  1188	        else:
  1189	            legacy = set(task_work_results.get("files_created", []) or [])
  1190	            legacy.update(task_work_results.get("files_modified", []) or [])
  1191	            own = {str(f) for f in legacy if f}
  1192	            source = "legacy_files_modified"
  1193	
  1194	        if not own:
  1195	            return {}
  1196	
  1197	        overlaps: Dict[str, frozenset] = {}
  1198	        for peer_id, peer_files in self._peer_changed_files.items():
  1199	            shared = peer_files & own
  1200	            if shared:
  1201	                overlaps[peer_id] = frozenset(shared)
  1202	
  1203	        if overlaps:
  1204	            # TASK-FIX-CC-COND bonus: structured-log line so future
  1205	            # false positives are diagnosable from logs alone. Records
  1206	            # both the authored set and the (possibly contaminated)
  1207	            # files_modified set so a reviewer can see at a glance
  1208	            # whether the overlap reflects real intent or legacy
  1209	            # fallback noise.
  1210	            logger.info(
  1211	                "Source-file contention detected (source=%s, overlaps=%s, "
  1212	                "files_authored=%s, files_modified=%s, files_created=%s)",
  1213	                source,
  1214	                {peer: sorted(files) for peer, files in overlaps.items()},
  1215	                sorted(task_work_results.get("files_authored", []) or []),
  1216	                sorted(task_work_results.get("files_modified", []) or []),
  1217	                sorted(task_work_results.get("files_created", []) or []),
  1218	            )
  1219	        return overlaps
  1220	
  1221	    def _get_coach_test_model(self) -> Optional[str]:
  1222	        """Return the model for Coach SDK test invocations, or None to use CLI default.
  1223	
  1224	        Resolution order:
  1225	        1. ``GUARDKIT_COACH_TEST_MODEL`` env var (operator override — e.g.
  1226	           claude-haiku-4-5-20251001 for cost reduction on the real Anthropic API).
  1227	        2. Orchestrator-supplied ``coach_model_name`` (TASK-FIX-COACHBUDG01):
  1228	           per-role Coach override (e.g. ``gemma4:26b`` while Player stays on
  1229	           ``qwen36-workhorse`` — TASK-HMIG-013). Takes precedence over the
  1230	           generic ``model_name`` for this Coach-specific path.
  1231	        3. Orchestrator-supplied ``model_name`` (TASK-FIX-LGFM3): same value
  1232	           threaded into ``AgentInvoker.select_harness`` calls. Without this
  1233	           fallback, the LangGraph harness receives ``model=None`` for
  1234	           ``role='coach_test'`` and the SDK path errors out (F12).
  1235	        4. ``None`` (harness uses CLI default).
  1236	        """
  1237	        import os
  1238	        env_model = os.environ.get("GUARDKIT_COACH_TEST_MODEL") or None
  1239	        if env_model is not None:
  1240	            return env_model
  1241	        if self._coach_model_name is not None:
  1242	            return self._coach_model_name
  1243	        return self._model_name
  1244	
  1245	    def _resolve_task_type(self, task: Dict[str, Any]) -> TaskType:
  1246	        """
  1247	        Resolve task type from task metadata with alias support and fallback to default.
  1248	
  1249	        Supports legacy task_type values through TASK_TYPE_ALIASES mapping.
  1250	        Logs info message when alias is used for transparency.
  1251	
  1252	        Parameters
  1253	        ----------
  1254	        task : Dict[str, Any]
  1255	            Task data including optional task_type field
  1256	
  1257	        Returns
  1258	        -------
  1259	        TaskType
  1260	            Resolved task type
  1261	
  1262	        Raises
  1263	        ------
  1264	        ValueError
  1265	            If task_type is specified but invalid (not in enum or aliases)
  1266	        """
  1267	        task_type_str = task.get("task_type")
  1268	
  1269	        if task_type_str is None:
  1270	            # No task_type specified - use default (feature)
  1271	            logger.debug("No task_type specified, defaulting to FEATURE profile")
  1272	            return TaskType.FEATURE
  1273	
  1274	        # Try to parse as valid TaskType enum first
  1275	        try:
  1276	            task_type = TaskType(task_type_str)
  1277	            logger.debug(f"Resolved task_type from metadata: {task_type.value}")
  1278	            return task_type
  1279	        except ValueError:
  1280	            # Check aliases before raising error
  1281	            if task_type_str in TASK_TYPE_ALIASES:
  1282	                aliased_type = TASK_TYPE_ALIASES[task_type_str]
  1283	                logger.info(
  1284	                    f"Using task_type alias: '{task_type_str}' → '{aliased_type.value}' "
  1285	                    f"(update task frontmatter to use '{aliased_type.value}' directly)"
  1286	                )
  1287	                return aliased_type
  1288	
  1289	            # Not a valid enum value or alias - raise error
  1290	            logger.error(f"Invalid task_type value: {task_type_str}")
  1291	            raise ValueError(
  1292	                f"Invalid task_type value: {task_type_str}. "
  1293	                f"Must be one of: {', '.join(t.value for t in TaskType)} "
  1294	                f"or valid alias: {', '.join(TASK_TYPE_ALIASES.keys())}"
  1295	            ) from None
  1296	
  1297	    def validate(
  1298	        self,
  1299	        task_id: str,
  1300	        turn: int,
  1301	        task: Dict[str, Any],
  1302	        skip_arch_review: bool = False,
  1303	        context: Optional[str] = None,
  1304	    ) -> CoachValidationResult:
  1305	        """
  1306	        Main validation entry point.
  1307	
  1308	        Validates Player's implementation by:
  1309	        1. Reading task-work quality gate results
  1310	        2. Verifying all gates passed
  1311	        3. Running independent test verification
  1312	        4. Checking requirements satisfaction
  1313	
  1314	        Parameters
  1315	        ----------
  1316	        task_id : str
  1317	            Task identifier (e.g., "TASK-001")
  1318	        turn : int
  1319	            Current turn number (1-based)
  1320	        task : Dict[str, Any]
  1321	            Task data including acceptance_criteria
  1322	        skip_arch_review : bool
  1323	            If True, skip architectural review gate regardless of profile setting.
  1324	            Used for --implement-only mode where Phase 2.5B doesn't run.
  1325	            Default: False (enforce arch review per profile).
  1326	
  1327	        Returns
  1328	        -------
  1329	        CoachValidationResult
  1330	            Complete validation result with decision
  1331	        """
  1332	        logger.info(f"Starting Coach validation for {task_id} turn {turn}")
  1333	
  1334	        # Log context if provided
  1335	        if context:
  1336	            logger.debug(f"[Graphiti] Coach context provided: {len(context)} chars")
  1337	
  1338	        # Resolve task type and get quality gate profile
  1339	        try:
  1340	            task_type = self._resolve_task_type(task)
  1341	        except ValueError as e:
  1342	            logger.error(f"Failed to resolve task type: {e}")
  1343	            # honesty_verification omitted (defaults to None): _verify_honesty
  1344	            # has not yet been called on this short-circuit path (TASK-FIX-7E3F).
  1345	            return self._feedback_result(
  1346	                task_id=task_id,
  1347	                turn=turn,
  1348	                issues=[{
  1349	                    "severity": "must_fix",
  1350	                    "category": "invalid_task_type",
  1351	                    "description": str(e),
  1352	                }],
  1353	                rationale=f"Invalid task type: {e}",
  1354	                context_used=context,
  1355	                is_configuration_error=True,
  1356	            )
  1357	
  1358	        # Operator handoff: defensive skip branch (TASK-FPTC-004 AC-01).
  1359	        # Operator-handoff tasks have runtime-shaped acceptance criteria
  1360	        # that no automated check can verify (e.g. "operator runs X
  1361	        # against the deployed service and inspects Y"). The feature
  1362	        # orchestrator (TASK-FPTC-003) is responsible for short-circuiting
  1363	        # dispatch BEFORE Coach is invoked — this branch is a paranoid
  1364	        # second line of defence that exits cleanly without exercising
  1365	        # any AC-matching machinery if the orchestrator-level skip is
  1366	        # bypassed for any reason. The "deferred" outcome shape mirrors
  1367	        # what feature_orchestrator records, so TASK-FPTC-005's
  1368	        # feature-complete summary sees consistent records.
  1369	        if task_type == TaskType.OPERATOR_HANDOFF:
  1370	            logger.info(
  1371	                f"Coach skipping operator_handoff task {task_id} turn {turn}: "
  1372	                f"runtime verification deferred to operator."
  1373	            )
  1374	            # honesty_verification omitted (defaults to None): _verify_honesty
  1375	            # has not yet been called on this operator-handoff short-circuit
  1376	            # path (TASK-FIX-7E3F).
  1377	            return CoachValidationResult(
  1378	                task_id=task_id,
  1379	                turn=turn,
  1380	                decision="deferred",
  1381	                quality_gates=None,
  1382	                independent_tests=None,
  1383	                requirements=None,
  1384	                issues=[],
  1385	                rationale="operator follow-up — runtime verification required",
  1386	                context_used=context,
  1387	            )
  1388	
  1389	        profile = get_profile(task_type)
  1390	        logger.info(f"Using quality gate profile for task type: {task_type.value}")
  1391	
  1392	        # 1. Read task-work quality gate results
  1393	        task_work_results = self.read_quality_gate_results(task_id)
  1394	
  1395	        if "error" in task_work_results:
  1396	            logger.warning(
  1397	                f"Task-work results for {task_id} contain error: "
  1398	                f"{task_work_results.get('error', 'unknown')}"
  1399	            )
  1400	            # honesty_verification omitted (defaults to None): _verify_honesty
  1401	            # has not yet been called on this missing-results short-circuit
  1402	            # path (TASK-FIX-7E3F).
  1403	            return self._feedback_result(
  1404	                task_id=task_id,
  1405	                turn=turn,
  1406	                issues=[{
  1407	                    "severity": "must_fix",
  1408	                    "category": "missing_results",
  1409	                    "description": task_work_results["error"],
  1410	                }],
  1411	                rationale="Task-work quality gate results not found",
  1412	                context_used=context,
  1413	            )
  1414	
  1415	        # 1.4. Adversarial honesty verification (TASK-AB-FIX-INVAB1 AC-002).
  1416	        #
  1417	        # Restores the original Player–Coach adversarial property on the
  1418	        # deterministic Coach path. Option D (TASK-REV-0414) introduced
  1419	        # CoachValidator as the primary Coach but did not wire in
  1420	        # CoachVerifier — the existing-but-disconnected honesty verifier
  1421	        # documented in installer/core/agents/autobuild-coach.md:141-203.
  1422	        #
  1423	        # The verifier checks Player claims against worktree state:
  1424	        # - files_created / files_modified / tests_written exist on disk
  1425	        # - completion_promises[*].implementation_files exist when status=complete
  1426	        #
  1427	        # When critical discrepancies exist, gates are not consulted at all
  1428	        # — Player feedback names the specific claim/actual disagreement so
  1429	        # the next turn can correct course. Honest reports produce zero
  1430	        # discrepancies (no behavioural change for compliant Players).
  1431	        #
  1432	        # Test verification (CoachVerifier._verify_test_results) is
  1433	        # deliberately skipped here because run_independent_tests below
  1434	        # already runs an authoritative independent pytest pass — running
  1435	        # it twice would double the Coach's wall-clock cost.
  1436	        honesty_verification = self._verify_honesty(task_work_results)
  1437	        honesty_issues = self._honesty_issues_from(honesty_verification)
  1438	        # TASK-FIX-1B4B Layer 2: only ``must_fix`` honesty issues
  1439	        # short-circuit gate evaluation. ``should_fix`` issues (a single
  1440	        # path-only ``file_existence`` discrepancy demoted by
  1441	        # ``_honesty_issues_from``) ride along to the final result so
  1442	        # the Player still sees them in feedback while the rest of the
  1443	        # gates run.
  1444	        honesty_must_fix = [
  1445	            i for i in honesty_issues if i["severity"] == "must_fix"
  1446	        ]
  1447	        honesty_should_fix = [
  1448	            i for i in honesty_issues if i["severity"] == "should_fix"
  1449	        ]
  1450	        if honesty_must_fix:
  1451	            logger.warning(
  1452	                f"Honesty verification produced {len(honesty_must_fix)} "
  1453	                f"critical issue(s) for {task_id}; short-circuiting "
  1454	                f"gate evaluation."
  1455	            )
  1456	            return CoachValidationResult(
  1457	                task_id=task_id,
  1458	                turn=turn,
  1459	                decision="feedback",
  1460	                quality_gates=None,
  1461	                independent_tests=None,
  1462	                requirements=None,
  1463	                issues=honesty_must_fix,
  1464	                rationale=(
  1465	                    f"{len(honesty_must_fix)} honesty discrepancy/discrepancies. "
  1466	                    f"Adversarial verification overrode gate evaluation."
  1467	                ),
  1468	                context_used=context,
  1469	                honesty_verification=honesty_verification,
  1470	            )
  1471	
  1472	        # 1.45. AC-cited missing test files (TASK-AB-FIX-INVAB1 AC-006).
  1473	        #
  1474	        # If an acceptance criterion names a specific test file (e.g.
  1475	        # ``tests/test_login.py``) and that file does not exist on disk,
  1476	        # the independent-test gate would silently fall back to the
  1477	        # existing-test set and report green. Surface the gap as a
  1478	        # ``must_fix`` issue so the Coach short-circuits with feedback
  1479	        # rather than running a smaller-scope pytest invocation that can
  1480	        # only return false-greens.
  1481	        ac_missing_tests = self._detect_ac_cited_missing_test_files(
  1482	            task.get("acceptance_criteria", [])
  1483	        )
  1484	        if ac_missing_tests:
  1485	            logger.warning(
  1486	                f"AC-cited missing test files for {task_id}: "
  1487	                f"{ac_missing_tests}. Short-circuiting before "
  1488	                f"run_independent_tests."
  1489	            )
  1490	            return CoachValidationResult(
  1491	                task_id=task_id,
  1492	                turn=turn,
  1493	                decision="feedback",
  1494	                quality_gates=None,
  1495	                independent_tests=None,
  1496	                requirements=None,
  1497	                issues=honesty_should_fix + [{
  1498	                    "severity": "must_fix",
  1499	                    "category": "acceptance_criteria",
  1500	                    "description": (
  1501	                        f"AC names test file(s) that don't exist on disk: "
  1502	                        f"{', '.join(ac_missing_tests)}. The independent-"
  1503	                        f"test gate cannot run honestly while AC-cited "
  1504	                        f"tests are absent."
  1505	                    ),
  1506	                    "details": {"missing_test_files": ac_missing_tests},
  1507	                }],
  1508	                rationale=(
  1509	                    f"{len(ac_missing_tests)} AC-cited test file(s) "
  1510	                    f"missing on disk; gate cannot run honestly."
  1511	                ),
  1512	                context_used=context,
  1513	                honesty_verification=honesty_verification,
  1514	            )
  1515	
  1516	        # 1.5. Agent-invocations gate (TASK-FIX-RWOP1.3.1, TASK-REV-F6E1 F3c).
  1517	        #
  1518	        # AgentInvoker._write_task_work_results folds
  1519	        # validate_agent_invocations into the producer path and persists the
  1520	        # verdict under "agent_invocations_validation".
  1521	        #
  1522	        # Pre-F3c (RWOP1.3.1 → forge-run-6): a "violation" status caused this
  1523	        # method to early-return with feedback, short-circuiting positions
  1524	        # 2–4 (quality_gates, independent_tests, AC verification). The
  1525	        # consequence — observed across forge-run-3/4/5/6 — was that the
  1526	        # Coach never once ran AC verification when the gate fired, so
  1527	        # the recent BDD-AC bridge work could not actually deliver its
  1528	        # quality signal.
  1529	        #
  1530	        # Post-F3c: a "violation" is captured as a non-blocking advisory
  1531	        # (severity=warning, category=agent_invocations_advisory) and
  1532	        # threaded into the issues list of whatever decision the
  1533	        # outcome-based gates produce. The Player still sees the process
  1534	        # observation ("you should invoke X via Task tool") so structural
  1535	        # drift toward Player-inline implementation stays visible — but
  1536	        # the gate no longer prevents the outcome-checks from running.
  1537	        #
  1538	        # Stall classifiers that match `category == "agent_invocations_violation"`
  1539	        # (autobuild stall sub-typing) intentionally no longer trigger:
  1540	        # this gate stops being a stall driver. Promote back to blocker
  1541	        # only after evidence shows the advisory-mode signal is being
  1542	        # systematically ignored AND that absence correlates with quality
  1543	        # drops in AC verification. See
  1544	        # docs/reviews/forge-run-6-fix-or-revert/TASK-REV-F6E1-decision-report.md
  1545	        # § Revision 3 for the diagnostic and rationale.
  1546	        agent_invocations_advisory: Optional[Dict[str, Any]] = None
  1547	        agent_invocations_validation = task_work_results.get(
  1548	            "agent_invocations_validation"
  1549	        )
  1550	        if (
  1551	            isinstance(agent_invocations_validation, dict)
  1552	            and agent_invocations_validation.get("status") == "violation"
  1553	        ):
  1554	            raw_missing = agent_invocations_validation.get("missing_phases") or []
  1555	            # The validator may emit missing_phases either as a list of phase
  1556	            # IDs or as a list of {"phase": "...", "description": "..."} dicts.
  1557	            # Normalise to a flat list of phase IDs for downstream formatting.
  1558	            missing_phases: List[str] = []
  1559	            if raw_missing and isinstance(raw_missing[0], dict):
  1560	                missing_phases = [
  1561	                    str(m.get("phase", ""))
  1562	                    for m in raw_missing
  1563	                    if m.get("phase")
  1564	                ]
  1565	            else:
  1566	                missing_phases = [str(m) for m in raw_missing]
  1567	            missing_phases_sorted = sorted(missing_phases)
  1568	            missing_phases_str = (
  1569	                ", ".join(missing_phases_sorted)
  1570	                if missing_phases_sorted
  1571	                else "unknown"
  1572	            )
  1573	            # TASK-FIX-7A07 AC-3: Build a phase-with-description rendering and
  1574	            # resolve the stack-specific Phase-3 specialist name so the
  1575	            # Player's next turn has actionable guidance on *which*
  1576	            # sub-agent to invoke via the Task tool.
  1577	            missing_phases_with_names = ", ".join(
  1578	                f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  1579	                for p in missing_phases_sorted
  1580	            ) if missing_phases_sorted else "unknown"
  1581	            stack_template = detect_stack_template(self.worktree_path)
  1582	            # TASK-GK-PROF-001: thread the worktree root so Phase-3 resolution
  1583	            # consults the *installed* specialist set, not the legacy
  1584	            # stack→specialist map. When the stack's profile-default isn't
  1585	            # installed (e.g. langchain-deepagents-orchestrator ships
  1586	            # langchain-tool-decorator-specialist, not python-api-specialist),
  1587	            # this downgrades the advisory to informational instead of naming
  1588	            # an agent the operator doesn't have.
  1589	            specialist_lines = render_missing_phase_list(
  1590	                missing_phases_sorted,
  1591	                stack_template=stack_template,
  1592	                workspace_root=self.worktree_path,
  1593	            )
  1594	            specialist_block = "\n".join(f"- {line}" for line in specialist_lines)
  1595	            expected_phases_val = agent_invocations_validation.get(
  1596	                "expected_phases"
  1597	            )
  1598	            actual_invocations_val = agent_invocations_validation.get(
  1599	                "actual_invocations"
  1600	            )
  1601	            expected_str = (
  1602	                str(expected_phases_val)
  1603	                if expected_phases_val is not None
  1604	                else "?"
  1605	            )
  1606	            actual_str = (
  1607	                str(actual_invocations_val)
  1608	                if actual_invocations_val is not None
  1609	                else "?"
  1610	            )
  1611	            logger.info(
  1612	                f"Agent-invocations advisory for {task_id}: "
  1613	                f"missing phases {missing_phases_str} "
  1614	                f"(non-blocking; outcome gates will run)"
  1615	            )
  1616	            advisory_description = (
  1617	                f"Advisory (non-blocking): task-work produced a report with "
  1618	                f"{actual_str} of {expected_str} expected agent invocations. "
  1619	                f"Missing phases: {missing_phases_with_names}. "
  1620	                f"Consider invoking these agents via the Task tool to "
  1621	                f"strengthen stack-specific quality:\n{specialist_block}"
  1622	            )
  1623	            agent_invocations_advisory = {
  1624	                "severity": "warning",
  1625	                "category": "agent_invocations_advisory",
  1626	                "description": advisory_description,
  1627	                "details": {
  1628	                    "missing_phases": missing_phases_sorted,
  1629	                    "expected_phases": expected_phases_val,
  1630	                    "actual_invocations": actual_invocations_val,
  1631	                },
  1632	            }
  1633	
  1634	        # F3c helper: prepend the advisory to any issues list so process
  1635	        # observations ride along with whatever outcome-based decision
  1636	        # downstream gates produce. ``honesty_should_fix`` rides the
  1637	        # same channel (TASK-FIX-1B4B Layer 2): a single demoted
  1638	        # path-only honesty discrepancy surfaces in feedback while the
  1639	        # rest of the gates evaluate normally.
  1640	        advisory_issues: List[Dict[str, Any]] = (
  1641	            [agent_invocations_advisory]
  1642	            if agent_invocations_advisory is not None
  1643	            else []
  1644	        )
  1645	        advisory_issues.extend(honesty_should_fix)
  1646	
  1647	        # 2. Verify quality gates passed with profile
  1648	        gates_status = self.verify_quality_gates(
  1649	            task_work_results, profile=profile, skip_arch_review=skip_arch_review
  1650	        )
  1651	
  1652	        # Validate requirements ahead of the gate-fail short-circuit so
  1653	        # gate-failure results carry criteria_met (TASK-GK-CR-001). This
  1654	        # is a pure read over task / task_work_results / the player report
  1655	        # — no side effects, idempotent. The same value is reused on the
  1656	        # all-gates-passed path below, so the call happens exactly once.
  1657	        requirements = self.validate_requirements(task, task_work_results, turn=turn)
  1658	
  1659	        if not gates_status.all_gates_passed:
  1660	            logger.info(f"Quality gates failed for {task_id}: {gates_status}")
  1661	            return self._feedback_from_gates(
  1662	                task_id=task_id,
  1663	                turn=turn,
  1664	                gates=gates_status,
  1665	                task_work_results=task_work_results,
  1666	                context_used=context,
  1667	                extra_issues=advisory_issues,
  1668	                honesty_verification=honesty_verification,
  1669	                requirements=requirements,
  1670	            )
  1671	
  1672	        # 3. Independent test verification (trust but verify)
  1673	        # Skip independent tests for task types that don't require tests (e.g., scaffolding)
  1674	        if not profile.tests_required:
  1675	            test_result = IndependentTestResult(
  1676	                tests_passed=True,
  1677	                test_command="skipped",
  1678	                test_output_summary=(
  1679	                    f"Independent test verification skipped "
  1680	                    f"(tests not required for {task_type.value} tasks)"
  1681	                ),
  1682	                duration_seconds=0.0,
  1683	            )
  1684	            logger.info(
  1685	                f"Independent test verification skipped for {task_id} "
  1686	                f"(tests not required for {task_type.value} tasks)"
  1687	            )
  1688	        else:
  1689	            test_result = self.run_independent_tests(
  1690	                task_work_results=task_work_results,
  1691	                task=task,
  1692	                turn=turn,
  1693	            )
  1694	
  1695	        conditional_approval = False
  1696	        environment_conditional_approval = False
  1697	        failure_class = None
  1698	        if not test_result.tests_passed:
  1699	            failure_class, failure_confidence = self._classify_test_failure(
  1700	                test_result.raw_output,
  1701	                requires_infrastructure=task.get("requires_infrastructure") if task else None,
  1702	            )
  1703	            logger.warning(
  1704	                f"Independent test verification failed for {task_id} "
  1705	                f"(classification={failure_class}, confidence={failure_confidence})"
  1706	            )
  1707	
  1708	            # Conditional approval for high-confidence infrastructure failures
  1709	            # when task declares requires_infrastructure and Docker is unavailable
  1710	            requires_infra = task.get("requires_infrastructure", [])
  1711	            docker_available = task.get("_docker_available", True)
  1712	
  1713	            logger.info(
  1714	                "conditional_approval check: failure_class=%s, confidence=%s, "
  1715	                "requires_infra=%s, docker_available=%s, all_gates_passed=%s, "
  1716	                "wave_size=%s",
  1717	                failure_class,
  1718	                failure_confidence,
  1719	                requires_infra,
  1720	                docker_available,
  1721	                gates_status.all_gates_passed,
  1722	                self.wave_size,
  1723	            )
  1724	
  1725	            # TASK-ABSR-2468: belt-and-braces clause for environment-class
  1726	            # ambiguous infrastructure failures (ImportError /
  1727	            # ModuleNotFoundError without service-client context) when the
  1728	            # worktree's bootstrap install is observably broken and all
  1729	            # Player gates passed. Pairs with the bootstrap_failure_mode
  1730	            # smart default from TASK-ABSR-A1B2: when a user opts into
  1731	            # ``warn`` mode and ships on a half-installed venv, this clause
  1732	            # prevents the feedback-stall trapdoor from firing on what is
  1733	            # purely an environment problem.
  1734	            environment_conditional_approval = (
  1735	                failure_class == "infrastructure"
  1736	                and failure_confidence == "ambiguous"
  1737	                and gates_status.all_gates_passed
  1738	                and not requires_infra
  1739	                and self._bootstrap_likely_broken(task)
  1740	            )
  1741	
  1742	            # TASK-FIX-A7B2: Detect source-file contention with peer wave tasks.
  1743	            # The TASK-ABFIX-005 conditional approval for parallel_contention /
  1744	            # parallel-code failures assumes the contention is transient
  1745	            # infrastructure (e.g. partial __init__.py write race) that a retry
  1746	            # in isolation can clear. When two parallel tasks edit the SAME
  1747	            # source file (e.g. shared BDD glue), the contention is real
  1748	            # source-level damage — both tasks committed inconsistent state to
  1749	            # the shared branch BEFORE either snapshot was taken, so the
  1750	            # isolation snapshot captures the already-corrupted file. Granting
  1751	            # conditional approval in that case masks the corruption and the
  1752	            # failure surfaces only at wave-2 verification.
  1753	            #
  1754	            # When overlap is detected, fall through to feedback so the
  1755	            # existing Player-Coach retry machinery serialises the next
  1756	            # attempt — by which point peers have completed and the wave is
  1757	            # effectively single-tasked, eliminating the contention.
  1758	            source_file_contention_overlaps: Dict[str, frozenset] = {}
  1759	            is_parallel_contention_class = (
  1760	                failure_class == "parallel_contention"
  1761	                or (failure_class == "code" and self.is_parallel)
  1762	            )
  1763	            if is_parallel_contention_class and self._peer_changed_files:
  1764	                source_file_contention_overlaps = (
  1765	                    self._detect_source_file_contention(task_work_results)
  1766	                )
  1767	
  1768	            conditional_approval = (
  1769	                failure_class == "infrastructure"
  1770	                and failure_confidence == "high"
  1771	                and bool(requires_infra)
  1772	                and not docker_available
  1773	                and gates_status.all_gates_passed
  1774	            ) or (
  1775	                failure_class == "collection_error"
  1776	                and gates_status.all_gates_passed
  1777	            ) or (
  1778	                # TASK-ABFIX-005: Grant conditional approval for contention-related
  1779	                # failures in a parallel wave when all Player quality gates passed.
  1780	                # "parallel_contention" is set by _classify_test_failure() when
  1781	                # wave_size > 1 and the failure looks like it could be contention.
  1782	                # TASK-FIX-A7B2: Only when no source-file overlap with peers.
  1783	                failure_class == "parallel_contention"
  1784	                and gates_status.all_gates_passed
  1785	                and not source_file_contention_overlaps
  1786	            ) or (
  1787	                # TASK-ABFIX-005: Also grant conditional approval for any "code"
  1788	                # failure in a parallel wave (recommendation 3b from TASK-REV-A17A).
  1789	                # The failure might be a false positive caused by concurrent mutations.
  1790	                # TASK-FIX-A7B2: Only when no source-file overlap with peers.
  1791	                failure_class == "code"
  1792	                and self.is_parallel
  1793	                and gates_status.all_gates_passed
  1794	                and not source_file_contention_overlaps
  1795	            ) or environment_conditional_approval
  1796	
  1797	            if conditional_approval:
  1798	                if environment_conditional_approval:
  1799	                    logger.warning(
  1800	                        f"Conditional approval for {task_id}: environment-class "
  1801	                        f"infrastructure failure ({failure_class}/{failure_confidence}) "
  1802	                        f"on a known-broken bootstrap; all Player gates passed. "
  1803	                        f"Marking approved with environment flag."
  1804	                    )
  1805	                elif failure_class == "collection_error":
  1806	                    logger.warning(
  1807	                        f"Conditional approval for {task_id}: test collection errors in "
  1808	                        f"independent verification, all Player gates passed. "
  1809	                        f"Continuing to requirements check."
  1810	                    )
  1811	                elif failure_class == "parallel_contention":
  1812	                    logger.warning(
  1813	                        f"Conditional approval for {task_id}: parallel contention failure "
  1814	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  1815	                        f"Continuing to requirements check."
  1816	                    )
  1817	                elif failure_class == "code" and self.is_parallel:
  1818	                    logger.warning(
  1819	                        f"Conditional approval for {task_id}: code failure in parallel wave "
  1820	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  1821	                        f"Continuing to requirements check."
  1822	                    )
  1823	                else:
  1824	                    logger.warning(
  1825	                        f"Conditional approval for {task_id}: infrastructure failure "
  1826	                        f"with declared deps {requires_infra}, Docker unavailable. "
  1827	                        f"Continuing to requirements check."
  1828	                    )
  1829	                # Fall through to requirements check with conditional flag set
  1830	            else:
  1831	                # Check for psycopg2/asyncpg mismatch before falling back to
  1832	                # generic infrastructure feedback (TASK-FIX-4415).
  1833	                if self._is_psycopg2_asyncpg_mismatch(test_result.raw_output, task):
  1834	                    description = (
  1835	                        "ModuleNotFoundError for 'psycopg2' — this project uses "
  1836	                        "asyncpg. Remove `import psycopg2` from your code and use "
  1837	                        "asyncpg-compatible database patterns instead."
  1838	                    )
  1839	                    rationale = (
  1840	                        "Tests failed because psycopg2 was imported in an asyncpg "
  1841	                        "project"
  1842	                    )
  1843	                elif (
  1844	                    is_parallel_contention_class
  1845	                    and source_file_contention_overlaps
  1846	                ):
  1847	                    # TASK-FIX-A7B2: Source-file contention with at least one
  1848	                    # peer in the same wave. Name the overlapping files so the
  1849	                    # Player can resolve the conflict on retry. The retry will
  1850	                    # be naturally serialised — by the time the Player runs
  1851	                    # its next turn, peers have completed and the wave is
  1852	                    # effectively single-tasked.
  1853	                    error_output = (test_result.test_output_summary or "").strip()
  1854	                    if len(error_output) > 500:
  1855	                        error_output = error_output[:497] + "..."
  1856	                    overlap_lines = []
  1857	                    for peer_id in sorted(source_file_contention_overlaps):
  1858	                        files = sorted(source_file_contention_overlaps[peer_id])
  1859	                        overlap_lines.append(
  1860	                            f"  - {peer_id}: {', '.join(files)}"
  1861	                        )
  1862	                    overlap_block = "\n".join(overlap_lines)
  1863	                    base = (
  1864	                        f"Tests failed due to source-file contention with peer "
  1865	                        f"task(s) in this parallel wave (wave_size={self.wave_size}). "
  1866	                        f"Both this task and the peer(s) below edited the same "
  1867	                        f"source file(s); the resulting shared-branch state is "
  1868	                        f"inconsistent and an isolation-snapshot retry cannot "
  1869	                        f"recover it. Resolve the conflict on the next turn — "
  1870	                        f"by then the peer(s) will have completed and the wave "
  1871	                        f"is effectively serialised.\n"
  1872	                        f"Overlapping files by peer:\n{overlap_block}\n"
  1873	                        f"Test command: {test_result.test_command}."
  1874	                    )
  1875	                    description = (
  1876	                        f"{base} Error detail: {error_output}"
  1877	                        if error_output
  1878	                        else base
  1879	                    )
  1880	                    rationale = (
  1881	                        "Tests failed due to source-file contention with peer "
  1882	                        "wave tasks (real correctness damage, not transient "
  1883	                        "infra contention) — see TASK-FIX-A7B2"
  1884	                    )
  1885	                elif failure_class == "parallel_contention":
  1886	                    error_output = (test_result.test_output_summary or "").strip()
  1887	                    if len(error_output) > 500:
  1888	                        error_output = error_output[:497] + "..."
  1889	                    base = (
  1890	                        f"Tests failed due to likely parallel wave contention "
  1891	                        f"(wave_size={self.wave_size}). Another task may have "
  1892	                        f"concurrently modified shared files (e.g. __init__.py) "
  1893	                        f"during Coach independent verification. "
  1894	                        f"Test command: {test_result.test_command}."
  1895	                    )
  1896	                    description = (
  1897	                        f"{base} Error detail: {error_output}"
  1898	                        if error_output
  1899	                        else base
  1900	                    )
  1901	                    rationale = (
  1902	                        "Tests failed due to likely parallel wave contention, "
  1903	                        "not code defects"
  1904	                    )
  1905	                elif failure_class in ("infrastructure", "collection_error"):
  1906	                    error_output = (test_result.test_output_summary or "").strip()
  1907	                    if len(error_output) > 500:
  1908	                        error_output = error_output[:497] + "..."
  1909	                    base = (
  1910	                        "Tests failed due to infrastructure/environment issues "
  1911	                        f"(not code defects). Test command: {test_result.test_command}. "
  1912	                        "Remediation options: "
  1913	                        "(1) Add mock fixtures for external services, "
  1914	                        "(2) Use SQLite for test database, "
  1915	                        "(3) Mark integration tests with @pytest.mark.integration "
  1916	                        "and exclude via -m 'not integration'."
  1917	                    )
  1918	                    description = (
  1919	                        f"{base} Error detail: {error_output}"
  1920	                        if error_output
  1921	                        else base
  1922	                    )
  1923	                    rationale = (
  1924	                        "Tests failed due to infrastructure/environment issues, "
  1925	                        "not code defects"
  1926	                    )
  1927	                else:
  1928	                    description = "Independent test verification failed"
  1929	                    rationale = (
  1930	                        "Tests passed according to task-work but failed on "
  1931	                        "independent verification"
  1932	                    )
  1933	
  1934	                return self._feedback_result(
  1935	                    task_id=task_id,
  1936	                    turn=turn,
  1937	                    quality_gates=gates_status,
  1938	                    independent_tests=test_result,
  1939	                    issues=advisory_issues + [{
  1940	                        "severity": "must_fix",
  1941	                        "category": "test_verification",
  1942	                        "description": description,
  1943	                        "test_output": test_result.test_output_summary,
  1944	                        "failure_classification": failure_class,
  1945	                        "failure_confidence": failure_confidence,
  1946	                    }],
  1947	                    rationale=rationale,
  1948	                    context_used=context,
  1949	                    honesty_verification=honesty_verification,
  1950	                )
  1951	
  1952	        # 4. Validate requirements satisfaction (already hoisted above —
  1953	        # see TASK-GK-CR-001).
  1954	        if not requirements.all_criteria_met:
  1955	            logger.info(f"Requirements not met for {task_id}: missing {requirements.missing}")
  1956	            return self._feedback_result(
  1957	                task_id=task_id,
  1958	                turn=turn,
  1959	                quality_gates=gates_status,
  1960	                independent_tests=test_result,
  1961	                requirements=requirements,
  1962	                issues=advisory_issues + [{
  1963	                    "severity": "must_fix",
  1964	                    "category": "missing_requirement",
  1965	                    "description": f"Not all acceptance criteria met",
  1966	                    "missing_criteria": requirements.missing,
  1967	                }],
  1968	                rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
  1969	                context_used=context,
  1970	                honesty_verification=honesty_verification,
  1971	            )
  1972	
  1973	        # 5. Check for blocking zero-test anomaly before approval
  1974	        zero_test_issues = self._check_zero_test_anomaly(
  1975	            task_work_results, profile, independent_tests=test_result,
  1976	            task_id=task_id,
  1977	        )
  1978	        has_blocking_zero_test = any(
  1979	            issue.get("severity") == "error" for issue in zero_test_issues
  1980	        )
  1981	
  1982	        if has_blocking_zero_test:
  1983	            logger.info(f"Coach rejected {task_id} turn {turn}: zero-test anomaly (blocking)")
  1984	            return self._feedback_result(
  1985	                task_id=task_id,
  1986	                turn=turn,
  1987	                quality_gates=gates_status,
  1988	                independent_tests=test_result,
  1989	                requirements=requirements,
  1990	                issues=advisory_issues + zero_test_issues,
  1991	                rationale=(
  1992	                    "Zero-test anomaly detected: quality gates reported as passed but "
  1993	                    "no tests were executed. Tests are required for this task type. "
  1994	                    "Please write and run tests before resubmitting."
  1995	                ),
  1996	                context_used=context,
  1997	                honesty_verification=honesty_verification,
  1998	            )
  1999	
  2000	        # 5.5. Check for seam test recommendations (soft gate, non-blocking)

