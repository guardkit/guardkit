## Summarized at 2026-07-04T22:26:30.107407+00:00

AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2600}, 'id': '6X2aOFXYV9r8zKKQf0pXoUKQYIKe29bW', 'type': 'tool_call'}]
Tool:   2601	                elif failure_class == "collection_error":
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 1000}, 'id': 'XK2eTh1JoARpMhYEmhcRacnOr5Q7DVII', 'type': 'tool_call'}]
Tool:   1001	        return None
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
  1101	
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 0}, 'id': 'rj7Xb4YE9tixZ9yZNHF1d0E8uZMJT4yg', 'type': 'tool_call'}]
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
   101	logger = logging.getLogger(__name__)
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
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Complete detailed review of _produce_behavioural_oracle implementation against ACs (Discovery, Independence, Execution, Outcome Policy).', 'status': 'in_progress'}, {'content': 'Evaluate implementation using specialist review checklist (build, requirements, code quality, testing, security, performance, documentation).', 'status': 'pending'}, {'content': 'Report findings.', 'status': 'pending'}]}, 'id': 'yz5KpW1UQt6YLr85UT1AeKoy6tBVzroa', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Complete detailed review of _produce_behavioural_oracle implementation against ACs (Discovery, Independence, Execution, Outcome Policy).', 'status': 'in_progress'}, {'content': 'Evaluate implementation using specialist review checklist (build, requirements, code quality, testing, security, performance, documentation).', 'status': 'pending'}, {'content': 'Report findings.', 'status': 'pending'}]
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 500}, 'id': 'tXZS6zIksVOcqguhKEAWUkc2RoBh0DWN', 'type': 'tool_call'}]
Tool:    501	    -------
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
   601	    _WIRING_FACTORY_AVAILABLE = True
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2500}, 'id': 'vT7ldgSwafVB4blaBjtU5UmtQVYdfoV7', 'type': 'tool_call'}]
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

