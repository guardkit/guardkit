## Summarized at 2026-07-04T21:00:51.635840+00:00

AI: [{'name': 'grep', 'args': {'pattern': 'behavioural_oracle', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': '1bY8kZ7b2zfo2NK5eejxcrZ1wJ3h9Ezl', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py
AI: [{'name': 'grep', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/', 'pattern': 'behavioural_oracle'}, 'id': 'jGIJaCpCfsfBLptg1FdNkUgN5xJz72pC', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 3600, 'offset': 3500}, 'id': 'IX56gFi0JBC7wmFl2Dfc43pVsfjSARwk', 'type': 'tool_call'}]
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
  3941	            Status of all quality gates with requirement flags
  3942	        """
  3943	        # Use default profile for backward compatibility
  3944	        if profile is None:
  3945	            profile = self.DEFAULT_PROFILE
  3946	        # Log input structure and profile for debugging
  3947	        logger.debug(f"task_work_results keys: {list(task_work_results.keys())}")
  3948	        logger.debug(f"quality_gates content: {task_work_results.get('quality_gates', 'NOT_FOUND')}")
  3949	        logger.debug(f"code_review content: {task_work_results.get('code_review', 'NOT_FOUND')}")
  3950	        logger.debug(f"plan_audit content: {task_work_results.get('plan_audit', 'NOT_FOUND')}")
  3951	        logger.debug(
  3952	            f"Profile requirements: tests={profile.tests_required}, "
  3953	            f"coverage={profile.coverage_required}, "
  3954	            f"arch_review={profile.arch_review_required}, "
  3955	            f"plan_audit={profile.plan_audit_required}"
  3956	        )
  3957	
  3958	        # Read from quality_gates object (what writer actually creates)
  3959	        quality_gates = task_work_results.get("quality_gates", {})
  3960	
  3961	        # Test results - use all_passed if present, otherwise check tests_failed
  3962	        # If tests not required by profile, default to True (skip gate)
  3963	        if not profile.tests_required:
  3964	            tests_passed = True
  3965	            logger.debug("Tests not required per task type profile, skipping")
  3966	        elif quality_gates.get("reconciled_absent"):
  3967	            # TASK-ABFIX-010 (W1): the upstream reconciliation flagged an ABSENT
  3968	            # test oracle (Coach isolated pytest timed out / no verdict). This is
  3969	            # UNKNOWN, not a verdict: propagate ``None`` (NOT False, NOT the
  3970	            # ``tests_failed == 0 → True`` fallback below, which would be a
  3971	            # false-GREEN). ``None`` flows through QualityGateStatus → to_dict →
  3972	            # the checkpoint pollution tally, which treats it as absent (not a
  3973	            # counted failure); ``all_gates_passed`` stays falsy so the Coach
  3974	            # does not approve and feeds back instead. Checked BEFORE the
  3975	            # ``all_passed`` / ``tests_failed`` logic so neither can override it.
  3976	            # See ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
  3977	            tests_passed = None
  3978	            logger.debug(
  3979	                "reconciled_absent set → tests_passed=None (UNKNOWN, not counted "
  3980	                "as failure, not approved)"
  3981	            )
  3982	        elif "all_passed" in quality_gates:
  3983	            all_passed_value = quality_gates["all_passed"]
  3984	            if all_passed_value is None:
  3985	                # Player session didn't reach quality gate evaluation (e.g. exhausted SDK turns)
  3986	                # Fall through to tests_failed check for partial data
  3987	                if "tests_failed" in quality_gates:
  3988	                    tests_failed_count = quality_gates["tests_failed"]
  3989	                    tests_passed = tests_failed_count == 0
  3990	                    logger.debug(
  3991	                        f"all_passed is null, falling back to tests_failed={tests_failed_count}, "
  3992	                        f"tests_passed={tests_passed}"
  3993	                    )
  3994	                else:
  3995	                    tests_passed = False
  3996	                    logger.debug("all_passed is null and no tests_failed data, defaulting to False")
  3997	            else:
  3998	                tests_passed = all_passed_value
  3999	                logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.all_passed")
  4000	        elif "tests_failed" in quality_gates:
  4001	            # If we have test counts, check if any failed
  4002	            tests_failed = quality_gates["tests_failed"]
  4003	            tests_passed = tests_failed == 0
  4004	            logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.tests_failed={tests_failed}")
  4005	        else:
  4006	            # No quality_gates data at all - assume failure
  4007	            tests_passed = False
  4008	            logger.debug("No tests_passed or tests_failed found in quality_gates, defaulting to False")
  4009	
  4010	        # Coverage - read from quality_gates.coverage_met
  4011	        # If coverage not required by profile, default to True (skip gate)
  4012	        if not profile.coverage_required:
  4013	            coverage_met = True
  4014	            logger.debug("Coverage not required per task type profile, skipping")
  4015	        else:
  4016	            # Handle None explicitly: treat as "not measured" = pass (same as coverage not required)
  4017	            coverage_met_value = quality_gates.get("coverage_met")
  4018	            coverage_met = coverage_met_value if coverage_met_value is not None else True
  4019	            logger.debug(f"Extracted coverage_met={coverage_met} from quality_gates.coverage_met (raw={coverage_met_value})")
  4020	
  4021	        # Architectural review - may be in separate code_review field or not present
  4022	        # If arch review not required by profile OR skip_arch_review=True, default to True (skip gate)
  4023	        if skip_arch_review:
  4024	            arch_review_passed = True
  4025	            logger.debug("Architectural review skipped (skip_arch_review=True, implement-only mode)")
  4026	        elif not profile.arch_review_required:
  4027	            arch_review_passed = True
  4028	            logger.debug("Architectural review not required per task type profile, skipping")
  4029	        else:
  4030	            code_review = task_work_results.get("code_review", {})
  4031	            arch_score = code_review.get("score", 0)  # Default to 0 if not present
  4032	            arch_review_passed = arch_score >= profile.arch_review_threshold
  4033	            logger.debug(
  4034	                f"Extracted arch_review_passed={arch_review_passed} "
  4035	                f"(score={arch_score}, threshold={profile.arch_review_threshold})"
  4036	            )
  4037	
  4038	        # Plan audit - separate field
  4039	        # If plan audit not required by profile, default to True (skip gate)
  4040	        if not profile.plan_audit_required:
  4041	            plan_audit_passed = True
  4042	            logger.debug("Plan audit not required per task type profile, skipping")
  4043	        else:
  4044	            plan_audit = task_work_results.get("plan_audit", {})
  4045	            # TASK-FIX-RWOP1.3.2: the producer writes a status-typed block
  4046	            # (passed | violation | skipped | auditor_error). "skipped"
  4047	            # means no plan on disk — don't fail the gate on absent data.
  4048	            # "auditor_error" means the deterministic auditor itself crashed;
  4049	            # non-blocking for the same reason validator_error is
  4050	            # non-blocking on the agent_invocations gate — a gate failing
  4051	            # to run is not evidence of a task failing. severity == "high"
  4052	            # is the new authoritative block signal; the legacy violations
  4053	            # count is preserved as a back-compat OR-gate for fixtures and
  4054	            # older Player reports that don't emit severity.
  4055	            plan_audit_status = plan_audit.get("status")
  4056	            severity = plan_audit.get("severity")
  4057	            violations = plan_audit.get("violations", 0)
  4058	
  4059	            if plan_audit_status in ("skipped", "auditor_error"):
  4060	                plan_audit_passed = True
  4061	                logger.debug(
  4062	                    f"Plan audit status={plan_audit_status} — treated as pass "
  4063	                    f"(non-blocking informational status)"
  4064	                )
  4065	            elif severity == "high":
  4066	                plan_audit_passed = False
  4067	                logger.debug(
  4068	                    f"Plan audit rejected: severity=high "
  4069	                    f"(violations={violations}, status={plan_audit_status})"
  4070	                )
  4071	            else:
  4072	                plan_audit_passed = violations == 0
  4073	                logger.debug(
  4074	                    f"Extracted plan_audit_passed={plan_audit_passed} "
  4075	                    f"(violations={violations}, severity={severity}, "
  4076	                    f"status={plan_audit_status})"
  4077	                )
  4078	
  4079	        # Determine effective arch_review_required (False if skip_arch_review=True)
  4080	        effective_arch_review_required = profile.arch_review_required and not skip_arch_review
  4081	
  4082	        status = QualityGateStatus(
  4083	            tests_passed=tests_passed,
  4084	            coverage_met=coverage_met,
  4085	            arch_review_passed=arch_review_passed,
  4086	            plan_audit_passed=plan_audit_passed,
  4087	            tests_required=profile.tests_required,
  4088	            coverage_required=profile.coverage_required,
  4089	            arch_review_required=effective_arch_review_required,
  4090	            plan_audit_required=profile.plan_audit_required,
  4091	        )
  4092	
  4093	        # Log final decision at INFO level for visibility
  4094	        logger.info(
  4095	            f"Quality gate evaluation complete: "
  4096	            f"tests={status.tests_passed} (required={status.tests_required}), "
  4097	            f"coverage={status.coverage_met} (required={status.coverage_required}), "
  4098	            f"arch={status.arch_review_passed} (required={status.arch_review_required}), "
  4099	            f"audit={status.plan_audit_passed} (required={status.plan_audit_required}), "
  4100	            f"ALL_PASSED={status.all_gates_passed}"
  4101	        )
  4102	
  4103	        return status
  4104	
  4105	    @staticmethod
  4106	    def _extract_content_text(content) -> str:
  4107	        """Extract text from ToolResultBlock.content (str | list[dict] | None)."""
  4108	        if content is None:
  4109	            return ""
  4110	        if isinstance(content, str):
  4111	            return content
  4112	        if isinstance(content, list):
  4113	            parts = []
  4114	            for item in content:
  4115	                if isinstance(item, dict):
  4116	                    parts.append(item.get("text", str(item)))
  4117	                else:
  4118	                    parts.append(str(item))
  4119	            return "\n".join(parts)
  4120	        return str(content)
  4121	
  4122	    # TASK-FIX-COACHTRES01 (heuristic precision): the pytest result summary
  4123	    # line, e.g. ``==== 15 passed in 2.75s ====`` /
  4124	    # ``==== 1 failed, 14 passed in 0.3s ====`` / ``==== 2 errors in 1.0s ====``.
  4125	    # Wrapped in ``=`` runs and ending in ``in <float>s``; the body carries the
  4126	    # real per-outcome counts.
  4127	    _PYTEST_SUMMARY_RE = re.compile(
  4128	        r"^=+\s+(?P<body>.*?\b(?:passed|failed|error|errors|skipped|xfailed|"
  4129	        r"xpassed|no tests ran)\b.*?)\s+in\s+[\d.]+\s*s\b.*?=*\s*$",
  4130	        re.IGNORECASE | re.MULTILINE,
  4131	    )
  4132	
  4133	    @classmethod
  4134	    def _verdict_from_pytest_summary(cls, output_text: str) -> Optional[bool]:
  4135	        """Derive pass/fail from the pytest summary line, not substring scan.
  4136	
  4137	        TASK-FIX-COACHTRES01. The capture fix surfaces the *real* pytest output
  4138	        to the SDK-path determination — but the legacy heuristic scanned the
  4139	        WHOLE output for the substrings ``"error"`` / ``"failed"`` /
  4140	        ``"failure"``, which false-positives on a *passing* run whose verbose
  4141	        test names or ``--cov`` file paths contain those words (e.g. a passing
  4142	        ``test_..._displays_error`` or a covered ``*_error_messages.py``). That
  4143	        is the FEAT-HARV TASK-HARV-006 false-block: ``15 passed in 2.75s`` read
  4144	        as a failure because two unrelated ``"error"`` substrings appeared.
  4145	
  4146	        The pytest *summary line* carries only the real counts, so parse that.
  4147	
  4148	        Returns
  4149	        -------
  4150	        Optional[bool]
  4151	            ``True``  — a passing summary (>=1 passed, zero failed/errored).
  4152	            ``False`` — a failing summary (>=1 failed or errored).
  4153	            ``None``  — no pytest summary line found (e.g. narration-only or a
  4154	                        truncated capture), so the caller falls back to the
  4155	                        legacy substring heuristic / absent handling.
  4156	        """
  4157	        if not output_text:
  4158	            return None
  4159	        matches = list(cls._PYTEST_SUMMARY_RE.finditer(output_text))
  4160	        if not matches:
  4161	            return None
  4162	        body = matches[-1].group("body").lower()
  4163	        # Any non-zero failed/errored count is a fail, regardless of passes.
  4164	        if re.search(r"\b[1-9]\d*\s+(?:failed|error|errors)\b", body):
  4165	            return False
  4166	        if re.search(r"\b[1-9]\d*\s+passed\b", body):
  4167	            return True
  4168	        # Only skipped / xfailed / "no tests ran" — not a clear pass; defer.
  4169	        return None
  4170	
  4171	    async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
  4172	        """Run tests via the harness substrate seam (TASK-HMIG-006.3).
  4173	
  4174	        Dispatches through :func:`select_harness` so ``GUARDKIT_HARNESS``
  4175	        routes Coach's independent verification through the SDK or
  4176	        LangGraph substrate consistently with the Player path migrated
  4177	        in TASK-HMIG-006/006.2. Coach-specific orchestrator concerns
  4178	        (``allowed_tools=["Bash"]``, ``max_turns=1``,
  4179	        ``permission_mode="bypassPermissions"``, ``self.test_timeout``)
  4180	        remain orchestrator-side per AC-002.
  4181	
  4182	        The method name retains the historical ``_via_sdk`` suffix so
  4183	        callers (``run_independent_tests`` at line ~2867) need no
  4184	        change; the dispatch is now harness-agnostic.
  4185	
  4186	        Parameters
  4187	        ----------
  4188	        test_cmd : str
  4189	            Shell command to run tests
  4190	
  4191	        Returns
  4192	        -------
  4193	        IndependentTestResult
  4194	            Result of test execution via the substrate seam.
  4195	        """
  4196	        import asyncio
  4197	        import time
  4198	        from contextlib import contextmanager
  4199	
  4200	        # ``select_harness``, harness event types, ``AgentInvocationError``,
  4201	        # and ``check_assistant_message_error`` are imported at module top
  4202	        # (TASK-HMIG-006.3) so ``coach_validator.select_harness`` is a
  4203	        # stable patch target. ``asyncio`` / ``time`` / ``contextmanager``
  4204	        # remain method-local to preserve the historic lazy-import shape
  4205	        # for the rest of the method body.
  4206	
  4207	        @contextmanager
  4208	        def _patched_pythonpath(prepend: str):
  4209	            """Scope PYTHONPATH mutation to harness.invoke() (Step D).
  4210	
  4211	            ``ClaudeSDKHarness`` does not accept an ``env=`` kwarg
  4212	            (sdk_harness.py:130-158); adding one would widen the
  4213	            harness interface for a Coach-only concern (ISP). Mutating
  4214	            ``os.environ`` in a tight scope lets the SDK subprocess
  4215	            inherit PYTHONPATH naturally. The single-coach-turn-per-
  4216	            worktree invariant makes this process-global side effect
  4217	            acceptable; do not lift this helper to a module-level
  4218	            utility without reconsidering thread-safety.
  4219	            """
  4220	            original = os.environ.get("PYTHONPATH")
  4221	            current = os.environ.get("PYTHONPATH", "")
  4222	            new = f"{prepend}:{current}" if current else prepend
  4223	            os.environ["PYTHONPATH"] = new
  4224	            try:
  4225	                yield
  4226	            finally:
  4227	                if original is None:
  4228	                    os.environ.pop("PYTHONPATH", None)
  4229	                else:
  4230	                    os.environ["PYTHONPATH"] = original
  4231	
  4232	        @contextmanager
  4233	        def _patched_path(venv_bin: Optional[str]):
  4234	            """Scope a venv-bin PATH prepend to harness.invoke (TASK-FIX-COACHPYENV).
  4235	
  4236	            Defence-in-depth companion to the ``-m pytest`` interpreter pin: the
  4237	            SDK harness spawns a Bash subprocess that inherits ``os.environ``, so
  4238	            prepending the bootstrap venv ``bin`` here means even a bare
  4239	            ``pytest``/``python`` the tests shell out to resolves inside the
  4240	            bootstrap environment, not the host Python 3.14 framework. No-op when
  4241	            no venv is resolved. Same single-coach-turn-per-worktree invariant as
  4242	            ``_patched_pythonpath`` makes this process-global mutation acceptable.
  4243	            """
  4244	            if not venv_bin:
  4245	                yield
  4246	                return
  4247	            original = os.environ.get("PATH")
  4248	            current = os.environ.get("PATH", "")
  4249	            os.environ["PATH"] = (
  4250	                f"{venv_bin}{os.pathsep}{current}" if current else venv_bin
  4251	            )
  4252	            try:
  4253	                yield
  4254	            finally:
  4255	                if original is None:
  4256	                    os.environ.pop("PATH", None)
  4257	                else:
  4258	                    os.environ["PATH"] = original
  4259	
  4260	        start_time = time.time()
  4261	        # TASK-FIX-COACHPYENV: pin the interpreter in the command the Bash tool
  4262	        # runs so it cannot resolve a stray PATH ``pytest`` (the run-9 Python
  4263	        # 3.14 framework-pytest mismatch). No-op when no venv is resolved.
  4264	        sdk_test_cmd = self._pin_pytest_command(test_cmd)
  4265	        if sdk_test_cmd != test_cmd:
  4266	            logger.info(
  4267	                "Coach SDK test command pinned to bootstrap interpreter: %s",
  4268	                sdk_test_cmd,
  4269	            )
  4270	        # 2026-07-04 code review: record the pinned interpreter as forensic
  4271	        # evidence on the SDK-path results too (the subprocess/isolated runners
  4272	        # already do — TASK-AB-RESUMEVENV01 AC-003). Only when the pin actually
  4273	        # fired: an unpinned SDK run resolves ``pytest`` via the Bash tool's
  4274	        # PATH, so the probe interpreter would not match the run — honest
  4275	        # ``None`` there.
  4276	        sdk_resolved_interpreter = (
  4277	            self._resolved_interpreter_for(test_cmd)
  4278	            if sdk_test_cmd != test_cmd
  4279	            else None
  4280	        )
  4281	        prompt = (
  4282	            f"Run the following test command and report the output:\n\n"
  4283	            f"```bash\n{sdk_test_cmd}\n```\n\nProvide the full test output."
  4284	        )
  4285	
  4286	        # TASK-HMIG-006.5: Restore sdk_debug preservation for the Coach
  4287	        # test path. Pre-migration (TASK-DIAG-F4A2), the SDK call site
  4288	        # invoked ``_sdk_preserve_prompt`` / ``_sdk_preserve_event``
  4289	        # under ``GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`` so incident
  4290	        # analysis of coach test-run failures had a quoted artefact
  4291	        # trail under ``sdk_debug/turn_<n>/coach/test_run/``. The
  4292	        # HMIG-006.3 migration dropped those calls because the harness
  4293	        # substrate seam owns the message stream and no harness-level
  4294	        # hook existed. The preservation is re-introduced here against
  4295	        # the synthesised options-shaped snapshot below so the
  4296	        # diagnostic surface mirrors the pre-migration shape; the
  4297	        # harness dispatch boundary itself (AC-001/AC-002 of HMIG-006.3)
  4298	        # is untouched. Zero overhead when the env var is unset
  4299	        # (``preserve_prompt`` short-circuits and ``preserve_event``
  4300	        # becomes a no-op against ``debug_dir=None``).
  4301	        from guardkit.orchestrator.sdk_debug import (
  4302	            preserve_prompt as _sdk_preserve_prompt,
  4303	            preserve_event as _sdk_preserve_event,
  4304	        )
  4305	
  4306	        try:
  4307	            # Use GUARDKIT_COACH_TEST_MODEL env var if set, otherwise CLI default
  4308	            model = self._get_coach_test_model()
  4309	            worktree_str = str(self.worktree_path)
  4310	            logger.debug(f"Coach harness PYTHONPATH prepend: {worktree_str}")
  4311	
  4312	            # Synthesise the diagnostic options snapshot the
  4313	            # pre-migration ``ClaudeAgentOptions`` would have produced.
  4314	            # The post-migration harness owns its own option assembly;
  4315	            # this record captures Coach's intent (what the substrate
  4316	            # was asked to run with) rather than the substrate's
  4317	            # realisation. ``GUARDKIT_HARNESS`` is included so the
  4318	            # post-mortem can distinguish SDK vs. LangGraph runs.
  4319	            _sdk_options_snapshot = {
  4320	                "cwd": str(self.worktree_path),
  4321	                "allowed_tools": ["Bash"],
  4322	                "permission_mode": "bypassPermissions",
  4323	                "max_turns": 1,
  4324	                "model": model,
  4325	                "harness": os.environ.get("GUARDKIT_HARNESS", DEFAULT_HARNESS),
  4326	                "pythonpath_prepend": worktree_str,
  4327	                "sdk_timeout_seconds": self.test_timeout,
  4328	            }
  4329	            _sdk_debug_dir = _sdk_preserve_prompt(
  4330	                workspace_root=self.worktree_path,
  4331	                task_id=self.task_id or "unknown",
  4332	                turn=self._turn,
  4333	                role="coach_test",
  4334	                prompt=prompt,
  4335	                options=_sdk_options_snapshot,
  4336	            )
  4337	
  4338	            collected_text: List[str] = []
  4339	            bash_output: Optional[str] = None
  4340	            bash_is_error: Optional[bool] = None
  4341	            api_error: Optional[str] = None
  4342	
  4343	            venv_bin = (
  4344	                str(self._venv_python.parent)
  4345	                if self._venv_python is not None
  4346	                else None
  4347	            )
  4348	            with _patched_pythonpath(worktree_str), _patched_path(venv_bin):
  4349	                harness = select_harness(
  4350	                    sdk_timeout_seconds=self.test_timeout,
  4351	                    allowed_tools=["Bash"],
  4352	                    permission_mode="bypassPermissions",
  4353	                    max_turns=1,
  4354	                    model=model,
  4355	                    cwd=self.worktree_path,
  4356	                )
  4357	
  4358	                async with asyncio.timeout(self.test_timeout):
  4359	                    # TASK-FIX-LGACLOSE: finalise the harness async generator on
  4360	                    # every exit (incl. timeout/cancel) via aclosing() so no
  4361	                    # orphaned async_generator_athrow survives interpreter shutdown.
  4362	                    async with aclosing(
  4363	                        harness.invoke(
  4364	                            prompt=prompt,
  4365	                            role="coach_test",
  4366	                            tools=["Bash"],
  4367	                            cwd=self.worktree_path,
  4368	                            timeout_seconds=self.test_timeout,
  4369	                        )
  4370	                    ) as _harness_stream:
  4371	                        async for event in _harness_stream:
  4372	                            # TASK-HMIG-006.5: record every harness event
  4373	                            # the loop consumes. ``preserve_event`` is a
  4374	                            # no-op when ``_sdk_debug_dir`` is None
  4375	                            # (env var unset), so this is zero-cost in
  4376	                            # production.
  4377	                            _sdk_preserve_event(_sdk_debug_dir, event)
  4378	                            if isinstance(event, AssistantMessageEvent):
  4379	                                # API-error short-circuit mirrors the Player
  4380	                                # dispatch in agent_invoker._invoke_with_role.
  4381	                                # Only the SDK harness sets ``event.raw``;
  4382	                                # other substrates have raw=None and this
  4383	                                # check is a no-op there.
  4384	                                if event.raw is not None:
  4385	                                    err = check_assistant_message_error(event.raw)
  4386	                                    if err:
  4387	                                        api_error = err
  4388	                                        break
  4389	                                collected_text.append(event.text)
  4390	                            elif isinstance(event, ToolResultEvent):
  4391	                                # NOTE (TASK-HMIG-006.3, Architectural review
  4392	                                # Concern 4): the current SDK harness does NOT
  4393	                                # yield ToolResultEvent — sdk_harness.py only
  4394	                                # handles AssistantMessage / ResultMessage /
  4395	                                # ToolUseEvent. On the SDK path bash_is_error
  4396	                                # therefore stays None and the heuristic
  4397	                                # branch below is the effective pass/fail
  4398	                                # determination. This branch is live for any
  4399	                                # future harness that yields ToolResultEvent
  4400	                                # (e.g. a variant that walks UserMessage
  4401	                                # content) and preserves the pre-migration
  4402	                                # tri-state contract:
  4403	                                #   is_error=True  -> bash_is_error=True (tool errored)
  4404	                                #   is_error=False -> bash_is_error=None (heuristic)
  4405	                                # The False->None mapping is intentional:
  4406	                                # is_error=False means "tool ran cleanly" not
  4407	                                # "tests passed", so we let the heuristic
  4408	                                # branch decide from the output text.
  4409	                                content = event.content
  4410	                                if isinstance(content, str):
  4411	                                    bash_output = content
  4412	                                else:
  4413	                                    bash_output = self._extract_content_text(content)
  4414	                                bash_is_error = True if event.is_error else None
  4415	                            elif isinstance(event, ResultMessageEvent):
  4416	                                break
  4417	
  4418	            duration = time.time() - start_time
  4419	
  4420	            if api_error is not None:
  4421	                logger.error(f"SDK API error during coach test execution: {api_error}")
  4422	                return IndependentTestResult(
  4423	                    tests_passed=False,
  4424	                    test_command=test_cmd,
  4425	                    test_output_summary=f"SDK API error: {api_error}",
  4426	                    duration_seconds=duration,
  4427	                    raw_output=f"SDK API error: {api_error}",
  4428	                    # TASK-FIX-COACHTESTTO: transport-layer failure — the
  4429	                    # oracle never produced a verdict. ABSENT, not a fail.
  4430	                    signal_absent=True,
  4431	                )
  4432	
  4433	            # Determine pass/fail from bash_is_error and output. Branches
  4434	            # below are unchanged from pre-migration: output assembly is
  4435	            # substrate-agnostic; only the source of bash_is_error /
  4436	            # bash_output / collected_text changed.
  4437	            if bash_is_error is True:
  4438	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4439	                summary = self._summarize_test_output(output_text)
  4440	                logger.debug(
  4441	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4442	                )
  4443	                # TASK-ABFIX-012: a missing host tool ("command not found") makes
  4444	                # this an ABSENT signal (the oracle could not run), not a Player
  4445	                # test failure. No subprocess return code is available on the SDK
  4446	                # path, so match the explicit shell strings.
  4447	                substrate_absent = self._is_host_substrate_gap(None, output_text)
  4448	                if substrate_absent:
  4449	                    logger.warning(
  4450	                        "[TASK-ABFIX-012] SDK independent test oracle hit a "
  4451	                        "host-substrate gap (missing host tool) — absent signal, "
  4452	                        "not a test failure. cmd=%s",
  4453	                        test_cmd,
  4454	                    )
  4455	                return IndependentTestResult(
  4456	                    tests_passed=False,
  4457	                    test_command=test_cmd,
  4458	                    test_output_summary=summary,
  4459	                    duration_seconds=duration,
  4460	                    raw_output=output_text,
  4461	                    signal_absent=substrate_absent,
  4462	                    tests_skipped=_parse_tests_skipped(output_text),
  4463	                    resolved_interpreter=sdk_resolved_interpreter,
  4464	                )
  4465	            elif bash_is_error is False:
  4466	                # NOTE (TASK-HMIG-006.3 code-review nit): this branch is
  4467	                # unreachable in the current implementation because the
  4468	                # ToolResultEvent handler above maps ``is_error=False``
  4469	                # to ``bash_is_error=None`` (heuristic path). Retained
  4470	                # unchanged from pre-migration per the implementation
  4471	                # plan; it activates only if a future harness yields
  4472	                # tri-state ``is_error`` semantics (e.g. by emitting
  4473	                # ``bash_is_error = False`` directly here from a custom
  4474	                # branch). Removing it would silently break that future
  4475	                # extension, so the branch stays live but documented.
  4476	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4477	                summary = self._summarize_test_output(output_text)
  4478	                logger.debug(
  4479	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4480	                )
  4481	                return IndependentTestResult(
  4482	                    tests_passed=True,
  4483	                    test_command=test_cmd,
  4484	                    test_output_summary=summary,
  4485	                    duration_seconds=duration,
  4486	                    raw_output=output_text,
  4487	                    tests_skipped=_parse_tests_skipped(output_text),
  4488	                    resolved_interpreter=sdk_resolved_interpreter,
  4489	                )
  4490	            else:
  4491	                # GAP-FIX #7: is_error is None — parse output text
  4492	                output_text = bash_output or "\n".join(collected_text) or "No output"
  4493	                summary = self._summarize_test_output(output_text)
  4494	                logger.debug(
  4495	                    f"[{self.task_id}] _run_tests_via_sdk raw output (first 2000 chars): {output_text[:2000]}"
  4496	                )
  4497	                # TASK-ABFIX-012: a host-substrate gap ("command not found") is an
  4498	                # ABSENT signal — short-circuit before the pass/fail heuristic so a
  4499	                # missing host tool is never read as a Player test failure or pass.
  4500	                if self._is_host_substrate_gap(None, output_text):
  4501	                    logger.warning(
  4502	                        "[TASK-ABFIX-012] SDK independent test oracle (heuristic "
  4503	                        "branch) hit a host-substrate gap — absent signal, not a "
  4504	                        "test failure. cmd=%s",
  4505	                        test_cmd,
  4506	                    )
  4507	                    return IndependentTestResult(
  4508	                        tests_passed=False,
  4509	                        test_command=test_cmd,
  4510	                        test_output_summary=summary,
  4511	                        duration_seconds=duration,
  4512	                        raw_output=output_text,
  4513	                        signal_absent=True,
  4514	                    )
  4515	                # TASK-FIX-COACHTRES01: prefer the pytest summary line (real
  4516	                # counts) over the substring scan, which false-positives on a
  4517	                # passing run whose verbose test names / --cov file paths
  4518	                # contain "error"/"failed" (the FEAT-HARV TASK-HARV-006
  4519	                # false-block: "15 passed" mis-read as a failure because a
  4520	                # passing test_..._displays_error and a covered
  4521	                # *_error_messages.py path matched). Only fall back to the
  4522	                # legacy substring heuristic when no summary line is present.
  4523	                summary_verdict = self._verdict_from_pytest_summary(output_text)
  4524	                if summary_verdict is not None:
  4525	                    return IndependentTestResult(
  4526	                        tests_passed=summary_verdict,
  4527	                        test_command=test_cmd,
  4528	                        test_output_summary=summary,
  4529	                        duration_seconds=duration,
  4530	                        raw_output=output_text,
  4531	                        tests_skipped=_parse_tests_skipped(output_text),
  4532	                        resolved_interpreter=sdk_resolved_interpreter,
  4533	                    )
  4534	                # Heuristic fallback: check for failure indicators in output
  4535	                lower = output_text.lower()
  4536	                has_failure = any(
  4537	                    indicator in lower
  4538	                    for indicator in ["failed", "error", "errors", "failure"]
  4539	                )
  4540	                has_success = any(
  4541	                    indicator in lower
  4542	                    for indicator in ["passed", "ok", "success"]
  4543	                )
  4544	                tests_passed = has_success and not has_failure
  4545	                return IndependentTestResult(
  4546	                    tests_passed=tests_passed,
  4547	                    test_command=test_cmd,
  4548	                    test_output_summary=summary,
  4549	                    duration_seconds=duration,
  4550	                    raw_output=output_text,
  4551	                    tests_skipped=_parse_tests_skipped(output_text),
  4552	                    resolved_interpreter=sdk_resolved_interpreter,
  4553	                )
  4554	
  4555	        except asyncio.TimeoutError:
  4556	            duration = time.time() - start_time
  4557	            logger.error(f"SDK coach test execution timed out after {self.test_timeout}s")
  4558	            return IndependentTestResult(
  4559	                tests_passed=False,
  4560	                test_command=test_cmd,
  4561	                test_output_summary=f"SDK test execution timed out after {self.test_timeout}s",
  4562	                duration_seconds=duration,
  4563	                raw_output=f"Timeout after {self.test_timeout}s",
  4564	                # TASK-FIX-COACHTESTTO: the oracle did not complete — ABSENT,
  4565	                # not a real pass/fail verdict.
  4566	                signal_absent=True,
  4567	            )
  4568	        except AgentInvocationError as e:
  4569	            # TASK-HMIG-006.3 D-4: the harness normalises
  4570	            # CLINotFoundError / ProcessError / CLIJSONDecodeError /
  4571	            # MessageParseError into a single AgentInvocationError
  4572	            # (sdk_harness.py). The diagnostic info (exit_code, stderr,
  4573	            # error_class) is preserved inside the exception message
  4574	            # string. ``run_independent_tests``'s generic catch reads
  4575	            # type(e).__name__ for log formatting and falls back to
  4576	            # subprocess, so behavioural parity is preserved; the only
  4577	            # observable change is the logged error_class value.
  4578	            logger.error(
  4579	                f"SDK coach test execution failed "
  4580	                f"(error_class=AgentInvocationError): {e}"
  4581	            )
  4582	            raise
  4583	        except Exception as e:
  4584	            # Catch-all retained for non-harness failures (e.g.
  4585	            # context-manager errors restoring PYTHONPATH). Preserves
  4586	            # the pre-migration log shape.
  4587	            logger.error(
  4588	                f"SDK coach test execution failed "
  4589	                f"(error_class={type(e).__name__}): {e}"
  4590	            )
  4591	            raise
  4592	
  4593	    def _is_custom_api_base(self) -> bool:
  4594	        """Return True when ANTHROPIC_BASE_URL points to a non-Anthropic endpoint (e.g. vLLM)."""
  4595	        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
  4596	        return bool(base_url) and "api.anthropic.com" not in base_url
  4597	
  4598	    def _is_langgraph_harness(self) -> bool:
  4599	        """Return True when ``GUARDKIT_HARNESS`` selects the LangGraph substrate.
  4600	
  4601	        TASK-FIX-COACHTESTTO. Under the LangGraph harness the SDK-path
  4602	        independent-test run (``_run_tests_via_sdk``) is dispatched as a
  4603	        one-turn LLM agent invocation: the (typically local) coach-test model
  4604	        is asked to call the ``Bash`` tool, run pytest, and report. That whole
  4605	        turn is bounded by ``self.test_timeout`` (300s). With a slow local
  4606	        model the turn never completes within budget and the trust-but-verify
  4607	        leg times out on every task (run-19, FEAT-AOF). The deterministic
  4608	        subprocess path runs the *same* pinned interpreter in the *same*
  4609	        worktree in seconds with no model in the loop, so under LangGraph we
  4610	        force subprocess.
  4611	
  4612	        This is the LangGraph-substrate complement to ``_is_custom_api_base``:
  4613	        the latter disables the SDK path when ``ANTHROPIC_BASE_URL`` points at
  4614	        a non-Anthropic endpoint, but the LangGraph harness configures its
  4615	        model endpoint through the LangGraph/OpenAI-compatible channel rather
  4616	        than ``ANTHROPIC_BASE_URL``, so ``_is_custom_api_base`` does not catch
  4617	        it. See ``docs/state/TASK-FIX-COACHTESTTO/diagnosis.md``.
  4618	        """
  4619	        return (
  4620	            os.environ.get("GUARDKIT_HARNESS", DEFAULT_HARNESS).strip().lower()
  4621	            == "langgraph"
  4622	        )
  4623	
  4624	    def _resolve_matching_strategy(self) -> str:
  4625	        """Resolve effective matching strategy to ``'text'`` or ``'semantic'``.
  4626	
  4627	        When configured as ``'auto'``, returns ``'semantic'`` if
  4628	        ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint (e.g. vLLM),
  4629	        otherwise ``'text'``.
  4630	        """
  4631	        if self._matching_strategy == "auto":
  4632	            is_custom = self._is_custom_api_base()
  4633	            effective = "semantic" if is_custom else "text"
  4634	            logger.info(
  4635	                "Matching strategy auto-resolved to '%s' (custom_api=%s)",
  4636	                effective,
  4637	                is_custom,
  4638	            )
  4639	            return effective
  4640	        return self._matching_strategy
  4641	
  4642	    # Directories to skip when copying worktree for isolated test execution.
  4643	    _ISOLATION_SKIP_DIRS: set = {
  4644	        ".git", "__pycache__", ".guardkit", ".venv", "venv", "node_modules",
  4645	        ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", "*.egg-info",
  4646	    }
  4647	
  4648	    def _pytest_interpreter(self) -> str:
  4649	        """Return the interpreter Coach should run pytest under.
  4650	
  4651	        TASK-FIX-COACHPYENV: prefer the resolved bootstrap venv interpreter so
  4652	        independent tests run in the same environment the Player's packages were
  4653	        installed into. Falls back to ``sys.executable`` (the orchestrator
  4654	        interpreter) for non-Python projects / no-venv recovery — never bare
  4655	        ``pytest`` from PATH, which is what produced the run-9 Python-3.14
  4656	        framework-pytest mismatch.
  4657	        """
  4658	        return str(self._venv_python) if self._venv_python is not None else sys.executable
  4659	
  4660	    def _resolved_interpreter_for(self, test_cmd: str) -> Optional[str]:
  4661	        """The interpreter an interpreter-pinned run of ``test_cmd`` uses.
  4662	
  4663	        TASK-AB-RESUMEVENV01 (AC-003): recorded on
  4664	        :class:`IndependentTestResult.resolved_interpreter` as forensic
  4665	        evidence. Only pytest-shaped commands are pinned to
  4666	        ``_pytest_interpreter()`` by the subprocess/isolated runners; a
  4667	        non-pytest command runs via ``shell=True`` with no interpreter pin,
  4668	        so ``None`` (unknown) is the honest value there.
  4669	        """
  4670	        if test_cmd.startswith("pytest"):
  4671	            return self._pytest_interpreter()
  4672	        return None
  4673	
  4674	    def _pin_pytest_command(self, test_cmd: str) -> str:
  4675	        """Rewrite a bare ``pytest …`` command to pin the bootstrap interpreter.
  4676	
  4677	        TASK-FIX-COACHPYENV: the SDK test path hands ``test_cmd`` to a Bash tool,
  4678	        which resolves ``pytest`` via PATH. Rewriting to
  4679	        ``<venv_python> -m pytest …`` makes the Bash subprocess invoke the exact
  4680	        interpreter regardless of PATH ordering. No-op when no venv is resolved
  4681	        or the command is not a bare ``pytest`` invocation.
  4682	        """
  4683	        if self._venv_python is None:
  4684	            # No pinned venv: the Bash tool resolves ``pytest`` via PATH, so the
  4685	            # probe interpreter (sys.executable) would not match the run
  4686	            # interpreter — skip both the pin and the --timeout injection here.
  4687	            return test_cmd
  4688	        # TASK-ABFIX-011: append a gated per-test --timeout to the pinned string.
  4689	        # Only the venv-pinned branches reach here, so the probe interpreter
  4690	        # (self._pytest_interpreter()) matches the interpreter that runs.
  4691	        timeout_suffix = ""
  4692	        timeout_argv = self._pytest_timeout_argv()
  4693	        if timeout_argv:
  4694	            timeout_suffix = " " + " ".join(timeout_argv)
  4695	        if test_cmd.startswith("pytest "):
  4696	            return f"{self._pytest_interpreter()} -m {test_cmd}{timeout_suffix}"
  4697	        if test_cmd == "pytest":
  4698	            return f"{self._pytest_interpreter()} -m pytest{timeout_suffix}"
  4699	        return test_cmd
  4700	
  4701	    def _pytest_env(self) -> Dict[str, str]:
  4702	        """Environment for subprocess pytest runs, with venv bin on PATH.
  4703	
  4704	        TASK-FIX-COACHPYENV: pinning ``argv[0]`` to the venv interpreter is the
  4705	        load-bearing fix; prepending the venv ``bin`` to PATH is defence-in-depth
  4706	        so any nested ``python``/console-script the tests shell out to also
  4707	        resolves inside the bootstrap environment. Falls back to the parent
  4708	        environment when no venv exists.
  4709	        """
  4710	        from guardkit.orchestrator.quality_gates.command_models import (
  4711	            build_venv_env,
  4712	        )
  4713	
  4714	        return build_venv_env(self.worktree_path) or dict(os.environ)
  4715	
  4716	    # ------------------------------------------------------------------
  4717	    # TASK-ABFIX-011: gated per-test pytest-timeout injection
  4718	    # ------------------------------------------------------------------
  4719	    # A single hanging test otherwise consumes the whole Coach subprocess budget
  4720	    # and yields ``tests_run=0`` (no per-test attribution). Injecting
  4721	    # ``--timeout N --timeout-method signal`` marks the *specific* hung test
  4722	    # FAILED while the others still run (``signal`` lets the session continue;
  4723	    # ``thread`` would ``os._exit``-kill it). Injection is TRIPLE-gated so it can
  4724	    # never become the harness-wide false-fail an *unconditional* ``--timeout``
  4725	    # would be (returncode-4 ``unrecognized arguments`` on any project lacking the
  4726	    # plugin — the already-reverted FEAT-FMDR-003 regression, replayed
  4727	    # harness-wide). Defence-in-depth: a mis-fired injection (plugin vanished
  4728	    # between probe and run) degrades to ``signal_absent=True`` via
  4729	    # ``_is_pytest_timeout_usage_error``, which ABFIX-010 carries as ``None``
  4730	    # (fed back), never a counted Player failure. Fail toward feedback.
  4731	
  4732	    @staticmethod
  4733	    def _is_pytest_timeout_usage_error(returncode: int, combined_output: str) -> bool:
  4734	        """True iff a pytest run failed because ``--timeout`` was unrecognised.
  4735	
  4736	        pytest exits ``4`` (usage error) with ``unrecognized arguments:
  4737	        --timeout`` when the plugin is absent. That means our gated injection
  4738	        mis-fired — the oracle produced NO verdict on the Player's code, so it is
  4739	        an ABSENT signal, not a Player test failure (constraint 3,
  4740	        ``.claude/rules/absence-of-failure-is-not-success.md``). The match is
  4741	        deliberately narrow so it can never mask a genuine exit-1 failure, which
  4742	        reports a test summary and never ``unrecognized arguments``.
  4743	        """
  4744	        return (
  4745	            returncode == 4
  4746	            and "unrecognized arguments" in combined_output
  4747	            and "--timeout" in combined_output
  4748	        )
  4749	
  4750	    def _pytest_timeout_injection_enabled(self) -> bool:
  4751	        """Master gate for per-test ``--timeout`` injection (all three must hold).
  4752	
  4753	        1. operator flag — ``GUARDKIT_COACH_PYTEST_TIMEOUT`` not in
  4754	           ``{0, false, off, no}`` (escape hatch; default enabled);
  4755	        2. Python stack — ``self._active_stack_profile is None`` (a non-Python
  4756	           profile means a non-pytest ``whole_suite_command``; never inject a
  4757	           Python-only arg — ``.claude/rules/stack-plugin-architecture.md``);
  4758	        3. plugin resolvable in the pinned interpreter (cached probe).
  4759	        """
  4760	        flag = os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT", "").strip().lower()
  4761	        if flag in ("0", "false", "off", "no"):
  4762	            return False
  4763	        if self._active_stack_profile is not None:
  4764	            return False
  4765	        return self._pytest_timeout_available()
  4766	
  4767	    def _pytest_timeout_available(self) -> bool:
  4768	        """Cached: is ``pytest-timeout`` importable in the pinned interpreter?"""
  4769	        if self._pytest_timeout_available_cache is None:
  4770	            self._pytest_timeout_available_cache = self._probe_pytest_timeout()
  4771	        return self._pytest_timeout_available_cache
  4772	
  4773	    def _probe_pytest_timeout(self) -> bool:
  4774	        """Probe whether ``pytest_timeout`` is importable where Coach runs pytest.
  4775	
  4776	        When the pinned interpreter is the orchestrator's own
  4777	        (``self._venv_python is None`` → ``sys.executable``) the check is
  4778	        in-process (``importlib.util.find_spec`` — no subprocess, so it does not
  4779	        perturb the many tests that patch ``subprocess.run``). When a distinct
  4780	        bootstrap venv is pinned, the plugin must be probed *in that interpreter*,
  4781	        so a tiny out-of-process ``find_spec`` is run. Any failure (non-zero exit,
  4782	        timeout, OSError) returns ``False`` — fail toward NO injection, never a
  4783	        spurious ``--timeout``.
  4784	        """
  4785	        import importlib.util
  4786	
  4787	        interpreter = self._pytest_interpreter()
  4788	        if interpreter == sys.executable:
  4789	            return importlib.util.find_spec("pytest_timeout") is not None
  4790	        try:
  4791	            proc = subprocess.run(
  4792	                [
  4793	                    interpreter,
  4794	                    "-c",
  4795	                    "import importlib.util, sys; "
  4796	                    "sys.exit(0 if importlib.util.find_spec('pytest_timeout') "
  4797	                    "else 1)",
  4798	                ],
  4799	                capture_output=True,
  4800	                text=True,
  4801	                timeout=15,
  4802	            )
  4803	            return proc.returncode == 0
  4804	        except Exception as exc:  # subprocess error / timeout / OSError
  4805	            logger.debug(
  4806	                "pytest-timeout probe failed for %s (%s); not injecting --timeout",
  4807	                interpreter,
  4808	                exc,
  4809	            )
  4810	            return False
  4811	
  4812	    def _per_test_timeout_seconds(self) -> int:
  4813	        """Per-test timeout (seconds). Env override, else the module default."""
  4814	        raw = os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS")
  4815	        if raw:
  4816	            try:
  4817	                value = int(raw)
  4818	                if value > 0:
  4819	                    return value
  4820	                logger.warning(
  4821	                    "GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS=%r is not positive; "
  4822	                    "using default %ss",
  4823	                    raw,
  4824	                    _DEFAULT_COACH_PER_TEST_TIMEOUT_S,
  4825	                )
  4826	            except ValueError:
  4827	                logger.warning(
  4828	                    "GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS=%r is not an int; "
  4829	                    "using default %ss",
  4830	                    raw,
  4831	                    _DEFAULT_COACH_PER_TEST_TIMEOUT_S,
  4832	                )
  4833	        return _DEFAULT_COACH_PER_TEST_TIMEOUT_S
  4834	
  4835	    def _pytest_timeout_method(self) -> str:
  4836	        """``--timeout-method``: ``signal`` (default) or ``thread``.
  4837	
  4838	        ``signal`` raises inside the hung test and lets the session CONTINUE, so
  4839	        the other tests still run and report verdicts — the per-test attribution
  4840	        the AC requires. ``thread`` dumps tracebacks then ``os._exit``-kills the
  4841	        session (the others never report), so it is not the default. The alarm
  4842	        fires only once a test exceeds the deadline, so a healthy asyncio test
  4843	        (event loop on the main thread) is never spuriously interrupted (empirically
  4844	        validated, constraint 5). Operator override:
  4845	        ``GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD``.
  4846	        """
  4847	        method = (
  4848	            os.environ.get("GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD", "")
  4849	            .strip()
  4850	            .lower()
  4851	        )
  4852	        if method in ("signal", "thread"):
  4853	            return method
  4854	        return "signal"
  4855	
  4856	    def _pytest_timeout_argv(self) -> List[str]:
  4857	        """argv fragment injecting a gated per-test ``--timeout``, or ``[]``.
  4858	
  4859	        Shared by all three pytest construction sites (SDK pin, isolated/parallel
  4860	        subprocess, standard subprocess) so the gate logic cannot drift between
  4861	        them — the recurring "Nth-injection-site" lesson of the absence-of-failure
  4862	        rule family.
  4863	        """
  4864	        if not self._pytest_timeout_injection_enabled():
  4865	            return []
  4866	        return [
  4867	            "--timeout",
  4868	            str(self._per_test_timeout_seconds()),
  4869	            "--timeout-method",
  4870	            self._pytest_timeout_method(),
  4871	        ]
  4872	
  4873	    def _basetemp_run_context(self, default_label: str) -> str:
  4874	        """Attribution label for the per-run pytest ``--basetemp`` dir.
  4875	
  4876	        TASK-AB-BASETEMP01: composes ``<task_id>-<label>`` so a leaked dir
  4877	        under system tmp is attributable to its task and call site. A
  4878	        caller-supplied ``basetemp_context`` (e.g. ``"phase4"`` from the
  4879	        deterministic Phase-4 runner) overrides the per-path default.
  4880	        """
  4881	        label = self._basetemp_context or default_label
  4882	        if self.task_id:
  4883	            return f"{self.task_id}-{label}"
  4884	        return label
  4885	
  4886	    def _run_isolated_tests(self, test_cmd: str) -> "IndependentTestResult":
  4887	        """
  4888	        Run tests in an isolated temporary directory (Option B: tempdir copy).
  4889	
  4890	        Copies the worktree to a temp directory, excluding large/irrelevant
  4891	        directories, and runs tests there.  This prevents spurious failures
  4892	        caused by concurrent mutations from other tasks running in the same
  4893	        parallel wave.
  4894	
  4895	        Parameters
  4896	        ----------
  4897	        test_cmd : str
  4898	            Test command to run (e.g. ``"pytest tests/test_foo.py -v --tb=short"``)
  4899	
  4900	        Returns
  4901	        -------
  4902	        IndependentTestResult
  4903	            Result of isolated test execution
  4904	        """
  4905	        import shutil
  4906	        import tempfile
  4907	
  4908	        start_time = time.time()
  4909	        logger.info(
  4910	            f"[TASK-ABFIX-005] Running isolated tests (wave_size={self.wave_size}): {test_cmd}"
  4911	        )
  4912	
  4913	        try:
  4914	            with tempfile.TemporaryDirectory(prefix="guardkit-coach-iso-") as tmpdir:
  4915	                tmpdir_path = Path(tmpdir)
  4916	
  4917	                # Copy worktree snapshot, skipping large/irrelevant directories
  4918	                for item in self.worktree_path.iterdir():
  4919	                    dest = tmpdir_path / item.name
  4920	                    if item.name in self._ISOLATION_SKIP_DIRS or item.name.endswith(".egg-info"):
  4921	                        continue
  4922	                    try:
  4923	                        if item.is_dir():
  4924	                            shutil.copytree(
  4925	                                str(item),
  4926	                                str(dest),
  4927	                                ignore=shutil.ignore_patterns(
  4928	                                    "__pycache__", "*.pyc", "*.pyo",
  4929	                                    ".pytest_cache", ".mypy_cache",
  4930	                                ),
  4931	                            )
  4932	                        else:
  4933	                        

[Output was truncated due to size limits. The file content is very large. Consider reformatting the file to make it easier to navigate. For example, if this is JSON, use execute(command='jq . /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py') to pretty-print it with line breaks. For other formats, you can use appropriate formatting tools to split long lines.]
AI: [{'name': 'grep', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'pattern': 'async def gather_evidence'}, 'id': '6xHuJ5cY1atAI2jByVxcmxXCAlJphwO8', 'type': 'tool_call'}]
Tool: No matches found
AI: [{'name': 'grep', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'pattern': 'def gather_evidence'}, 'id': 'fszRT2YP8KwMxlhgZ722CslvIEHqqVr3', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 3400}, 'id': 'pO5XGEet7k3XNSOQBmVujSIEmLrJF9tg', 'type': 'tool_call'}]
Tool:   3401	
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 3000}, 'id': 'fjRZ5c9XDa01RF7uIBZZrLt9JoJYY2an', 'type': 'tool_call'}]
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
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Implement behavioural oracle discovery and execution in CoachValidator.gather_evidence', 'status': 'in_progress'}, {'content': "Implement independence check for behavioural oracle (ensure it's not in authored set)", 'status': 'pending'}, {'content': "Verify AgentInvoker correctly applies the hard gate for behavioural_oracle 'ran-and-failed' outcome", 'status': 'pending'}]}, 'id': 'aVhi7u5kxfiRoCaPeONixoZTYafQavot', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Implement behavioural oracle discovery and execution in CoachValidator.gather_evidence', 'status': 'in_progress'}, {'content': "Implement independence check for behavioural oracle (ensure it's not in authored set)", 'status': 'pending'}, {'content': "Verify AgentInvoker correctly applies the hard gate for behavioural_oracle 'ran-and-failed' outcome", 'status': 'pending'}]
AI: [{'name': 'grep', 'args': {'pattern': 'behavioural_oracle.command'}, 'id': 'yO5bqbSrvxwWroXevBO1a3bs7VSt9rXv', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_a0a29240.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-004-behavioural-roundtrip-oracle.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-004-behavioural-roundtrip-oracle.md
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_behavioural_oracle_guard.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_behavioural_oracle_guard.py'}, 'id': 'txb5C7LP4fq4Ee4RFK6sQU2mFlP3Nsi2', 'type': 'tool_call'}]
Tool:      1	"""TASK-QAV-004 — L4 behavioural round-trip oracle guard.
     2	
     3	Deterministic backstop: when the Coach's ``behavioural_oracle`` bundle reports
     4	``ran-and-failed``, an approving Coach verdict is overridden to ``feedback``
     5	with a ``must_fix`` issue naming the oracle and its failure output.
     6	
     7	Tests model the guard verbatim on the
     8	``_reconcile_absent_independent_test_signal`` archetype (wired at the same
     9	post-verdict seam, beside the COACHFG01 and spec-gap guards).
    10	
    11	Tests exercise every outcome branch:
    12	  - ran-and-failed → hard RED override (AC-1)
    13	  - timeout → ran-and-failed (AC-6)
    14	  - failed-to-start → absent WARN (AC-6)
    15	  - None bundle → no-op (AC-3)
    16	  - None oracle field → no-op (AC-3)
    17	  - passing oracle → no override (AC-4)
    18	  - not_independent → no override, warning recorded (AC-5)
    19	  - absent → no override (AC-7)
    20	  - dogfood end-to-end with real failing oracle (AC-8)
    21	
    22	Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
    23	matching the convention in ``test_coach_synthesis_split.py``.
    24	"""
    25	
    26	from __future__ import annotations
    27	
    28	import asyncio
    29	import json
    30	import textwrap
    31	from pathlib import Path
    32	from typing import Any, Dict, Optional
    33	from unittest.mock import AsyncMock, MagicMock, patch
    34	
    35	import pytest
    36	import yaml
    37	
    38	from guardkit.orchestrator.agent_invoker import AgentInvoker
    39	from guardkit.orchestrator.coach_verification import HonestyVerification
    40	from guardkit.orchestrator.harness import (
    41	    AssistantMessageEvent,
    42	    ResultMessageEvent,
    43	)
    44	from guardkit.orchestrator.quality_gates.coach_evidence import (
    45	    CoachEvidenceBundle,
    46	)
    47	
    48	
    49	# ---------------------------------------------------------------------------
    50	# helpers
    51	# ---------------------------------------------------------------------------
    52	
    53	
    54	def _make_invoker(worktree: Path) -> AgentInvoker:
    55	    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    56	    path (mirrors ``_make_invoker_for_routing`` in test_coach_synthesis_split)."""
    57	    invoker = AgentInvoker.__new__(AgentInvoker)
    58	    invoker.worktree_path = worktree
    59	    invoker.sdk_timeout_seconds = 600
    60	    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    61	    invoker._venv_python = None
    62	    return invoker
    63	
    64	
    65	def _bundle(
    66	    behavioural_oracle: Optional[Dict[str, Any]] = None,
    67	) -> CoachEvidenceBundle:
    68	    """A minimal bundle whose behavioural_oracle leg is whatever the test supplies."""
    69	    return CoachEvidenceBundle(
    70	        honesty=HonestyVerification(
    71	            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
    72	        ),
    73	        gathering_status="complete",
    74	        behavioural_oracle=behavioural_oracle,
    75	    )
    76	
    77	
    78	def _approve_events(task_id: str, turn: int) -> list:
    79	    """Harness events carrying a fenced ``approve`` verdict."""
    80	    verdict: Dict[str, Any] = {
    81	        "task_id": task_id,
    82	        "turn": turn,
    83	        "decision": "approve",
    84	        "rationale": "All Player-reported gates pass; tests look green.",
    85	        "criteria_verification": [],
    86	    }
    87	    text = "```json\n" + json.dumps(verdict) + "\n```"
    88	    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]
    89	
    90	
    91	def _run_coach(
    92	    invoker: AgentInvoker,
    93	    *,
    94	    task_id: str,
    95	    turn: int,
    96	    bundle: CoachEvidenceBundle,
    97	    player_report: Optional[Dict[str, Any]] = None,
    98	):
    99	    """Invoke the Coach with ``_invoke_with_role`` mocked to return the
   100	    approve-verdict harness events. Everything else runs for real."""
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py'}, 'id': 'nfJEZRgCKXsX2dVicLK17GDRMdtc2s4Z', 'type': 'tool_call'}]
Tool:      1	"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""
     2	
     3	import asyncio
     4	import json
     5	import logging
     6	import os
     7	import re
     8	import signal
     9	import threading
    10	import time
    11	from contextlib import aclosing, asynccontextmanager, suppress
    12	from dataclasses import dataclass
    13	from datetime import datetime
    14	from pathlib import Path
    15	from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Literal, Optional, Set, Tuple, Union
    16	
    17	if TYPE_CHECKING:
    18	    from guardkit.orchestrator.autobuild import DesignContext
    19	    # TASK-HMIG-008R Part C: bundle reference avoids the circular import that
    20	    # would result from a runtime import of
    21	    # guardkit.orchestrator.quality_gates.coach_evidence — the quality_gates
    22	    # package __init__ transitively imports agent_invoker via pre_loop →
    23	    # task_work_interface. Runtime values are duck-typed.
    24	    from guardkit.orchestrator.quality_gates.coach_evidence import (
    25	        CoachEvidenceBundle,
    26	    )
    27	
    28	from guardkit.orchestrator.exceptions import (
    29	    AgentInvocationError,
    30	    CoachDecisionInvalidError,
    31	    CoachDecisionNotFoundError,
    32	    PlanNotFoundError,
    33	    PlayerReportInvalidError,
    34	    PlayerReportNotFoundError,
    35	    RateLimitExceededError,
    36	    SDKTimeoutError,
    37	    TaskStateError,
    38	    TaskWorkResult,
    39	)
    40	from guardkit.orchestrator.instrumentation.emitter import NullEmitter
    41	from guardkit.orchestrator.instrumentation.llm_instrumentation import (
    42	    classify_error,
    43	    detect_provider,
    44	    extract_token_usage,
    45	    measure_latency,
    46	    sanitise_tool_name,
    47	)
    48	from guardkit.orchestrator.instrumentation.redaction import SecretRedactor
    49	from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent, ToolExecEvent
    50	from guardkit.orchestrator.paths import TaskArtifactPaths
    51	from guardkit.orchestrator.prompts import load_protocol
    52	from guardkit.orchestrator.coach_verification import (
    53	    CoachVerifier,
    54	    HonestyVerification,
    55	    format_verification_context,
    56	)
    57	from guardkit.orchestrator import evidence_repos as evidence_repos_lib
    58	from guardkit.orchestrator.evidence_repos import EvidenceRepo
    59	from guardkit.orchestrator.schemas import (
    60	    CompletionPromise,
    61	    CriterionVerification,
    62	)
    63	from guardkit.orchestrator.stale_test_attribution import (
    64	    extract_failing_test_lines,
    65	    is_test_runner_command,
    66	    stale_test_notes,
    67	)
    68	
    69	# TASK-HMIG-006 Phase 3b: HarnessAdapter substrate seam.
    70	# Pure-Python, SDK-free imports — the concrete ClaudeSDKHarness lazily
    71	# imports claude_agent_sdk inside its own invoke() (matches existing
    72	# test-fixture behaviour at tests/orchestrator/instrumentation/
    73	# test_llm_call_events.py which patches sys.modules["claude_agent_sdk"]).
    74	# See Design Decision D-3: orchestrator-side concerns (heartbeat,
    75	# cancel monitor, sdk_debug, llm.call event) stay inline.
    76	from guardkit.orchestrator.harness import (
    77	    AssistantMessageEvent,
    78	    HarnessEvent,
    79	    ResultMessageEvent,
    80	    ToolResultEvent,
    81	    ToolUseEvent,
    82	    select_harness,
    83	)
    84	
    85	# TASK-FIX-RWOP1.3.1: Agent-invocations validation on the producer path.
    86	# task-work.md Step 6.5 declares validate_agent_invocations as "the ONLY
    87	# checkpoint that prevents false reporting". Folding it into
    88	# _write_task_work_results is the producer-runs-gate pattern from
    89	# TASK-FIX-3C9D: without this wiring the Player can emit a results file
    90	# claiming any phases were completed and no deterministic check catches it
    91	# before Coach reads the file.
    92	from installer.core.commands.lib import (
    93	    AgentInvocationTracker,
    94	    validate_agent_invocations,
    95	    ValidationError as AgentInvocationValidationError,
    96	)
    97	from installer.core.commands.lib.agent_invocation_validator import (
    98	    get_expected_phases,
    99	    identify_missing_phases,
   100	)

