## Summarized at 2026-07-04T19:45:58.840588+00:00

AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'def analyze_stub_scan'}, 'id': 'KaD1FvPMOJnpGqAdz1pPd3Bxn6XXUmVd', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_b9edd33d.md:
  691:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  692: AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'def analyze_stub_scan'}, 'id': 'L5kgZgJo9afegxxUg2UOgMIvC1axgj1e', 'type': 'tool_call'}]
  694:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  695: AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'def analyze_stub_scan'}, 'id': 'OwE5OrX0CfcN7kziYN6xeeitf6jkMaLI', 'type': 'tool_call'}]
  697:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  739:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/unit/test_coach_verification_promises.py:
  243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
AI: [{'name': 'glob', 'args': {'pattern': '**/wiring/*.py'}, 'id': 'N7BXmwJ2znaJRGTyfnrDhWUpPbjv2fs1', 'type': 'tool_call'}]
Tool: []
AI: [{'name': 'glob', 'args': {'pattern': '**/wiring/**/*.py'}, 'id': '2RVKqcwg0CYK1D36ByFyzXsfF2VgzXxf', 'type': 'tool_call'}]
Tool: []
AI: [{'name': 'glob', 'args': {'pattern': '**/wiring/*.py', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/'}, 'id': 'NGJFzXAuJUJ9hMiWvJjDKVUXAq2vkqpT', 'type': 'tool_call'}]
Tool: []
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/lib/'}, 'id': 'jfZfrl4lBXCmwaLGmY1n7trNtgt7c6j6', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/lib/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/lib/pytest_argv.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/lib/task_type_detector.py']
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/'}, 'id': 'zHnqP605Vtx3hOsAyFup7BZ3JLPOf8CV', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/autobuild.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/browser_verifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/coach_grammar.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/coach_narrative_reconciler.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/coach_output_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/docker_fixtures.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/environment_bootstrap.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/evidence_repos.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/exceptions.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/feature_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/feature_complete.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/feature_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/feature_orchestrator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/feature_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/gpu_monitor.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/grammars/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/harness/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/instrumentation/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/intensity_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/mcp_design_extractor.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/parallel_strategy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/paths.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/phase_specialists.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/preflight.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/preflight_ignore_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/progress.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/progress_logger.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/prohibition_checklist.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/prompts/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/protocol.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/review_summary.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/schemas.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/sdk_ceiling.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/sdk_debug.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/sdk_utils.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/security_config.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/smoke_gates.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/specialist_invocations.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/stale_test_attribution.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/state_detection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/state_tracker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/synthetic_report.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/visual_comparator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/worktree_checkpoints.py']
AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'analyze_stub_scan'}, 'id': 'wfmuY1Yc3Luu5Z02swVW1xZqwF5Z9FdP', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-001/player_turn_1.json:
  76:       "criterion_text": "Task-type gating + public API: analyze_stub_scan returns None for SCAFFOLDING/DOCUMENTATION/TESTING and zero targets; result exposes .to_dict()",
  86:       "criterion_text": "End-to-end round-trip: analyze_stub_scan over mini fixture project produces JSON-serializable dict matching documented shape with correct findings",
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-001/player_turn_2.json:
  68:       "evidence": "TestAC4StatusDiscriminator has 2 tests. test_unsupported_language writes a .rb file (Ruby, no stub_body_query dialect) and asserts result is None (absent-signal, probe didn't run). test_parse_degraded writes syntactically broken Python and asserts findings == [] with degraded_files recorded. The _analyze_stub_scan_impl sets status='parse_degraded' when degraded files exist, and returns None when no dialect has stub_body_query for the file extension.",
  76:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING / DOCUMENTATION / TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  87:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test (not colocated with the unit fixtures) runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-001/player_turn_3.json:
  77:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING/DOCUMENTATION/TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  79:       "evidence": "8 tests in TestAC5TaskTypeGating pass: 5 non-analyzed task types return None (parametrized), zero authored targets returns None, StubScanResult.to_dict() returns valid dict, analyze_stub_scan has correct public API signature.",
  88:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-001/task_work_results.json:
  103:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING/DOCUMENTATION/TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  105:       "evidence": "8 tests in TestAC5TaskTypeGating pass: 5 non-analyzed task types return None (parametrized), zero authored targets returns None, StubScanResult.to_dict() returns valid dict, analyze_stub_scan has correct public API signature.",
  114:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/conversation_history/session_b9edd33d.md:
  119:     52	  `analyze_stub_scan(authored_files, worktree_path, task_type, ...)` sibling of
  124:     57	  (not colocated with the unit fixtures) runs `analyze_stub_scan` end-to-end
  641: AI: [{'name': 'grep', 'args': {'pattern': 'analyze_stub_scan'}, 'id': 'cMGkfA5Aa5McdATh5XuvBUpCMySSi168', 'type': 'tool_call'}]
  650: AI: [{'name': 'grep', 'args': {'pattern': 'analyze_stub_scan', 'output_mode': 'content'}, 'id': '7ZpLWzCy4QkdCck92YpPChGRGJUfjshR', 'type': 'tool_call'}]
  652:   76:       "criterion_text": "Task-type gating + public API: analyze_stub_scan returns None for SCAFFOLDING/DOCUMENTATION/TESTING and zero targets; result exposes .to_dict()",
  653:   86:       "criterion_text": "End-to-end round-trip: analyze_stub_scan over mini fixture project produces JSON-serializable dict matching documented shape with correct findings",
  655:   68:       "evidence": "TestAC4StatusDiscriminator has 2 tests. test_unsupported_language writes a .rb file (Ruby, no stub_body_query dialect) and asserts result is None (absent-signal, probe didn't run). test_parse_degraded writes syntactically broken Python and asserts findings == [] with degraded_files recorded. The _analyze_stub_scan_impl sets status='parse_degraded' when degraded files exist, and returns None when no dialect has stub_body_query for the file extension.",
  656:   76:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING / DOCUMENTATION / TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  657:   87:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test (not colocated with the unit fixtures) runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
  659:   93:       "evidence": "TestAC4StatusDiscriminator has 2 tests. test_unsupported_language writes a .rb file (Ruby, no stub_body_query dialect) and asserts result is None (absent-signal, probe didn't run). test_parse_degraded writes syntactically broken Python and asserts findings == [] with degraded_files recorded. The _analyze_stub_scan_impl sets status='parse_degraded' when degraded files exist, and returns None when no dialect has stub_body_query for the file extension.",
  660:   101:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING / DOCUMENTATION / TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  661:   112:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test (not colocated with the unit fixtures) runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
  663:   15:     consumes: analyze_stub_scan
  664:   54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  665:   62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  666:   79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  667:   86: @pytest.mark.integration_contract("analyze_stub_scan")
  668:   87: def test_analyze_stub_scan_contract():
  669:   88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  670:   93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  671:   96:     params = inspect.signature(analyze_stub_scan).parameters
  673:   18:         W1["analyze_stub_scan()\n(guardkitfactory.wiring, T-001)"]
  674:   61:     CV->>GF: analyze_stub_scan(authored, worktree, task_type)
  675:   94: ### Contract: analyze_stub_scan
  676:   97: - **Artifact type:** Python API (`guardkitfactory.wiring.analyze_stub_scan`)
  678:   15:     consumes: analyze_stub_scan
  679:   54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  680:   62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  681:   79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  682:   86: @pytest.mark.integration_contract("analyze_stub_scan")
  683:   87: def test_analyze_stub_scan_contract():
  684:   88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  685:   93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  686:   96:     params = inspect.signature(analyze_stub_scan).parameters
  688:   52:   `analyze_stub_scan(authored_files, worktree_path, task_type, ...)` sibling of
  689:   57:   (not colocated with the unit fixtures) runs `analyze_stub_scan` end-to-end
  691:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  692: AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'def analyze_stub_scan'}, 'id': 'L5kgZgJo9afegxxUg2UOgMIvC1axgj1e', 'type': 'tool_call'}]
  694:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  695: AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'def analyze_stub_scan'}, 'id': 'OwE5OrX0CfcN7kziYN6xeeitf6jkMaLI', 'type': 'tool_call'}]
  697:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
  698: AI: [{'name': 'grep', 'args': {'output_mode': 'content', 'pattern': 'analyze_stub_scan'}, 'id': 'DnfqdEZP73dj2kplaiAyQraMjmla2aFG', 'type': 'tool_call'}]
  700:   76:       "criterion_text": "Task-type gating + public API: analyze_stub_scan returns None for SCAFFOLDING/DOCUMENTATION/TESTING and zero targets; result exposes .to_dict()",
  701:   86:       "criterion_text": "End-to-end round-trip: analyze_stub_scan over mini fixture project produces JSON-serializable dict matching documented shape with correct findings",
  703:   68:       "evidence": "TestAC4StatusDiscriminator has 2 tests. test_unsupported_language writes a .rb file (Ruby, no stub_body_query dialect) and asserts result is None (absent-signal, probe didn't run). test_parse_degraded writes syntactically broken Python and asserts findings == [] with degraded_files recorded. The _analyze_stub_scan_impl sets status='parse_degraded' when degraded files exist, and returns None when no dialect has stub_body_query for the file extension.",
  704:   76:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING / DOCUMENTATION / TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  705:   87:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test (not colocated with the unit fixtures) runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
  707:   93:       "evidence": "TestAC4StatusDiscriminator has 2 tests. test_unsupported_language writes a .rb file (Ruby, no stub_body_query dialect) and asserts result is None (absent-signal, probe didn't run). test_parse_degraded writes syntactically broken Python and asserts findings == [] with degraded_files recorded. The _analyze_stub_scan_impl sets status='parse_degraded' when degraded files exist, and returns None when no dialect has stub_body_query for the file extension.",
  708:   101:       "criterion_text": "Task-type gating + public API: a public analyze_stub_scan(authored_files, worktree_path, task_type, ...) sibling of analyze_wiring returns None for SCAFFOLDING / DOCUMENTATION / TESTING task types and for zero authored targets; result exposes .to_dict() so the guardkit side stores a plain dict.",
  709:   112:       "criterion_text": "Behavioural check (dogfood): an independent round-trip test (not colocated with the unit fixtures) runs analyze_stub_scan end-to-end over a mini fixture project on disk and asserts the emitted dict is JSON-serialisable and matches the documented shape.",
  711:   15:     consumes: analyze_stub_scan
  712:   54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  713:   62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  714:   79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  715:   86: @pytest.mark.integration_contract("analyze_stub_scan")
  716:   87: def test_analyze_stub_scan_contract():
  717:   88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  718:   93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  719:   96:     params = inspect.signature(analyze_stub_scan).parameters
  721:   18:         W1["analyze_stub_scan()\n(guardkitfactory.wiring, T-001)"]
  722:   61:     CV->>GF: analyze_stub_scan(authored, worktree, task_type)
  723:   94: ### Contract: analyze_stub_scan
  724:   97: - **Artifact type:** Python API (`guardkitfactory.wiring.analyze_stub_scan`)
  726:   15:     consumes: analyze_stub_scan
  727:   54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  728:   62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  729:   79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  730:   86: @pytest.mark.integration_contract("analyze_stub_scan")
  731:   87: def test_analyze_stub_scan_contract():
  732:   88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  733:   93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  734:   96:     params = inspect.signature(analyze_stub_scan).parameters
  736:   52:   `analyze_stub_scan(authored_files, worktree_path, task_type, ...)` sibling of
  737:   57:   (not colocated with the unit fixtures) runs `analyze_stub_scan` end-to-end
  739:   243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md:
  15:     consumes: analyze_stub_scan
  54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  86: @pytest.mark.integration_contract("analyze_stub_scan")
  87: def test_analyze_stub_scan_contract():
  88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  96:     params = inspect.signature(analyze_stub_scan).parameters
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/IMPLEMENTATION-GUIDE.md:
  18:         W1["analyze_stub_scan()\n(guardkitfactory.wiring, T-001)"]
  61:     CV->>GF: analyze_stub_scan(authored, worktree, task_type)
  94: ### Contract: analyze_stub_scan
  97: - **Artifact type:** Python API (`guardkitfactory.wiring.analyze_stub_scan`)
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md:
  15:     consumes: analyze_stub_scan
  54:   populated from `analyze_stub_scan` on the complete path for FEATURE /
  62:   installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  79: """Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
  86: @pytest.mark.integration_contract("analyze_stub_scan")
  87: def test_analyze_stub_scan_contract():
  88:     """Verify analyze_stub_scan exists and returns the documented dict shape.
  93:     from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
  96:     params = inspect.signature(analyze_stub_scan).parameters
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-001-anti-stub-scan-factory-core.md:
  52:   `analyze_stub_scan(authored_files, worktree_path, task_type, ...)` sibling of
  57:   (not colocated with the unit fixtures) runs `analyze_stub_scan` end-to-end
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/unit/test_coach_verification_promises.py:
  243:         (target / "analyzer.py").write_text("def analyze_stub_scan(): ...\n")
AI: [{'name': 'glob', 'args': {'pattern': '**/wiring/*.py'}, 'id': '4YZEhNEFNatwy9HBE6eo8r5PynfjOJ1v', 'type': 'tool_call'}]
Tool: []
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/'}, 'id': 'xzJ3cIodxKQ0ZOr0X4kuNNsuG8zWWVD2', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.agents/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.claude/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.coverage', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.git/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.github/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.gitignore', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.guardkit-git.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.mcp.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.mypy_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.pytest_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.ruff_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/.venv/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/LICENSE', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/README.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/coverage.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/docs/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/lib/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/pyproject.toml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/scripts/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/skills-lock.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/tasks/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/tests/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/uv.lock']
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/'}, 'id': '0Peyr6IcN1vx4Lw0iEvUlcJt0eLWQCz9', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/bdd/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/harness/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/']
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/'}, 'id': 'STK2ilHTzIkY0PNS2f6ZS9qfddYdgxzW', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/analyzer.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialect.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/parser.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/analyzer.py'}, 'id': 'UiR32BmMbJpghVKkrW1a4EQH0us7er8f', 'type': 'tool_call'}]
Tool:      1	"""WiringAnalyzer: stack-agnostic wiring-analysis engine.
     2	
     3	Operates over tree-sitter Concrete Syntax Trees.  The only stack-specific
     4	input is a declarative ``WiringDialect`` descriptor (DATA).  Adding a
     5	language is **a descriptor entry, not a code plugin change**.
     6	
     7	Fidelity caveat
     8	---------------
     9	tree-sitter yields a **Concrete Syntax Tree, NOT full semantic
    10	resolution**.  Reachability is a **syntactic identifier-match heuristic
    11	across files** — the same fidelity as the prior python-ast plan, now
    12	multi-language.  It cannot resolve aliased imports, dynamic dispatch,
    13	string-keyed registries, reflection-based DI, or entry-points outside
    14	the worktree.  The FP/FN posture deliberately **biases toward WIRED**
    15	(substrings count as referenced; ``__all__`` / manifest names count as
    16	wired; parse-degraded files are skipped, never flagged) so the heuristic
    17	produces accepted false-negatives, never false-red false-positives.
    18	
    19	Result shape (consumed by guardkit's Coach evidence path)
    20	----------------------------------------------------------
    21	``analyze_wiring`` returns ``None`` when the probe legitimately did not
    22	run (task-type gate; zero authored non-test source targets), otherwise a
    23	dict in the ``bundle.wiring`` shape of the scope doc §5.1, with the
    24	MOCKED_SEAM result nested under the ``"mocked_seam"`` key (its own §5.1
    25	shape) so a single CST pass serves both probes::
    26	
    27	    {
    28	      "status": "complete" | "parse_degraded" | "unsupported_stack" | "error",
    29	      "dialect": "<primary>", "language": "<primary>",
    30	      "dialects": [...], "languages": [...],          # polyglot (AC-021)
    31	      "targets_scanned": int, "symbols_examined": int,
    32	      "findings": [ {UNWIRED_PATH finding} ],
    33	      "degraded_files": [...],
    34	      "mocked_seam": {
    35	        "status": "ran" | "skipped_no_acceptance_files",
    36	        "ran": bool, "skip_reason": str | None,
    37	        "dialect": ..., "language": ...,
    38	        "findings": [ {MOCKED_SEAM finding, severity warning|info} ],
    39	        "external_mocks_ignored": [...],
    40	      },
    41	    }
    42	
    43	No status value ever maps to "pass": the only positive verdict is
    44	``complete`` **with** ``findings: []`` (scope §5.6).
    45	"""
    46	
    47	from __future__ import annotations
    48	
    49	import fnmatch
    50	import logging
    51	import os
    52	import re
    53	from dataclasses import dataclass, field
    54	from pathlib import Path
    55	from typing import Any
    56	
    57	from guardkitfactory.wiring.dialect import (
    58	    WiringDialect,
    59	    _find_language,
    60	    get_dialect,
    61	    iter_dialects,
    62	)
    63	from guardkitfactory.wiring.parser import _load_language, parse_bytes
    64	
    65	logger = logging.getLogger(__name__)
    66	
    67	# ---------------------------------------------------------------------------
    68	# Status discriminator
    69	# ---------------------------------------------------------------------------
    70	
    71	WiringStatus = str  # literal type: see status table below
    72	
    73	# Status values (no value maps to "pass" — see scope doc §5.6):
    74	#   complete                    — analyzer ran, classification authoritative
    75	#                                 (empty findings = real positive verdict)
    76	#   unsupported_stack           — no dialect for the detected language
    77	#   parse_degraded              — ≥1 target skipped on CST parse error
    78	#                                 (biased WIRED, recorded in degraded_files)
    79	#   error                       — unexpected exception, caught fail-open
    80	# MOCKED_SEAM sub-result additionally uses:
    81	#   ran / skipped_no_acceptance_files
    82	
    83	_ANALYZED_TASK_TYPES = frozenset({"FEATURE", "REFACTOR", "INTEGRATION"})
    84	
    85	# Source extensions that are real languages we know about but have no
    86	# registered dialect — used to report unsupported_stack (absent-signal)
    87	# instead of None when a stack profile is not supplied.
    88	_KNOWN_UNDIALECTED_EXTENSIONS = {
    89	    ".rb": "ruby",
    90	    ".go": "go",
    91	    ".rs": "rust",
    92	    ".java": "java",
    93	    ".kt": "kotlin",
    94	    ".swift": "swift",
    95	    ".php": "php",
    96	    ".scala": "scala",
    97	    ".ex": "elixir",
    98	    ".erl": "erlang",
    99	}
   100	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/analyzer.py', 'limit': 500, 'offset': 100}, 'id': 'DvDLurBvHxVDSwEd39kC3zp8vDbYwBRQ', 'type': 'tool_call'}]
Tool:    101	# ---------------------------------------------------------------------------
   102	# Finding / result types
   103	# ---------------------------------------------------------------------------
   104	
   105	FindingKind = str  # "UNWIRED_PATH" | "MOCKED_SEAM"
   106	
   107	
   108	@dataclass
   109	class Finding:
   110	    """A single wiring evidence finding."""
   111	
   112	    file: str
   113	    symbol: str
   114	    kind: FindingKind
   115	    module: str = ""
   116	    lineno: int = 0
   117	    severity: str = "warning"
   118	    pattern: str = ""
   119	    why: str = ""
   120	    registration_found: bool = False
   121	    searched_refs: int = 0
   122	    mock_kind: str = ""
   123	    authored_this_turn: bool | None = None
   124	    dialect: str = ""
   125	    language: str = ""
   126	
   127	
   128	def _finding_to_dict(f: Finding) -> dict[str, Any]:
   129	    """Convert a Finding to a plain JSON-serializable dict."""
   130	    return {
   131	        "file": f.file,
   132	        "symbol": f.symbol,
   133	        "kind": f.kind,
   134	        "module": f.module,
   135	        "lineno": f.lineno,
   136	        "severity": f.severity,
   137	        "pattern": f.pattern,
   138	        "why": f.why,
   139	        "registration_found": f.registration_found,
   140	        "searched_refs": f.searched_refs,
   141	        "mock_kind": f.mock_kind,
   142	        "authored_this_turn": f.authored_this_turn,
   143	        "dialect": f.dialect,
   144	        "language": f.language,
   145	    }
   146	
   147	
   148	@dataclass
   149	class WiringResult:
   150	    """Result of an UNWIRED_PATH analysis run."""
   151	
   152	    status: WiringStatus
   153	    dialect: str | None = None
   154	    language: str = ""
   155	    dialects: list[str] = field(default_factory=list)
   156	    languages: list[str] = field(default_factory=list)
   157	    targets_scanned: int = 0
   158	    symbols_examined: int = 0
   159	    findings: list[Finding] = field(default_factory=list)
   160	    degraded_files: list[str] = field(default_factory=list)
   161	
   162	    def to_dict(self) -> dict[str, Any]:
   163	        """Convert to a serializable dict (scope §5.1 ``bundle.wiring`` shape)."""
   164	        return {
   165	            "status": self.status,
   166	            "dialect": self.dialect,
   167	            "language": self.language,
   168	            "dialects": self.dialects,
   169	            "languages": self.languages,
   170	            "targets_scanned": self.targets_scanned,
   171	            "symbols_examined": self.symbols_examined,
   172	            "findings": [_finding_to_dict(f) for f in self.findings],
   173	            "degraded_files": self.degraded_files,
   174	        }
   175	
   176	
   177	@dataclass
   178	class MockSeamResult:
   179	    """Result of a MOCKED_SEAM analysis run."""
   180	
   181	    status: WiringStatus = "skipped_no_acceptance_files"
   182	    ran: bool = False
   183	    skip_reason: str | None = "no acceptance files found"
   184	    dialect: str | None = None
   185	    language: str = ""
   186	    findings: list[Finding] = field(default_factory=list)
   187	    external_mocks_ignored: list[Finding] = field(default_factory=list)
   188	
   189	    def to_dict(self) -> dict[str, Any]:
   190	        """Convert to a serializable dict (scope §5.1 ``bundle.mocked_seam`` shape)."""
   191	        return {
   192	            "status": self.status,
   193	            "ran": self.ran,
   194	            "skip_reason": self.skip_reason,
   195	            "dialect": self.dialect,
   196	            "language": self.language,
   197	            "findings": [_finding_to_dict(f) for f in self.findings],
   198	            "external_mocks_ignored": [
   199	                _finding_to_dict(f) for f in self.external_mocks_ignored
   200	            ],
   201	        }
   202	
   203	
   204	@dataclass
   205	class CtorArityResult:
   206	    """Result of a CTOR_ARITY (composition-root constructor-arity) run.
   207	
   208	    Nested under the ``"ctor_arity"`` key of the ``analyze_wiring`` dict, in
   209	    parallel with ``"mocked_seam"``.  ``ran=False`` (no composition root, or
   210	    a dialect with no ctor-arity queries) is an **absent** signal — never a
   211	    pass, never a block (AC#5 / absence-of-failure).
   212	    """
   213	
   214	    status: WiringStatus = "skipped_no_composition_root"
   215	    ran: bool = False
   216	    skip_reason: str | None = "no composition root found"
   217	    dialect: str | None = None
   218	    language: str = ""
   219	    composition_roots_scanned: int = 0
   220	    findings: list[Finding] = field(default_factory=list)
   221	
   222	    def to_dict(self) -> dict[str, Any]:
   223	        """Convert to a serializable dict (``bundle.ctor_arity`` shape)."""
   224	        return {
   225	            "status": self.status,
   226	            "ran": self.ran,
   227	            "skip_reason": self.skip_reason,
   228	            "dialect": self.dialect,
   229	            "language": self.language,
   230	            "composition_roots_scanned": self.composition_roots_scanned,
   231	            "findings": [_finding_to_dict(f) for f in self.findings],
   232	        }
   233	
   234	
   235	# ---------------------------------------------------------------------------
   236	# Anti-stub body scan (TASK-QAV-001)
   237	# ---------------------------------------------------------------------------
   238	
   239	
   240	@dataclass
   241	class StubScanResult:
   242	    """Result of an anti-stub body scan run.
   243	
   244	    Mirrors ``WiringResult``/``MockSeamResult`` / ``CtorArityResult``:
   245	    uses the same ``WiringStatus`` vocabulary and never maps to "pass".
   246	    """
   247	
   248	    status: WiringStatus = "skipped_no_targets"
   249	    ran: bool = False
   250	    skip_reason: str | None = "no targets to scan"
   251	    dialect: str | None = None
   252	    language: str = ""
   253	    symbols_examined: int = 0
   254	    findings: list[Finding] = field(default_factory=list)
   255	    degraded_files: list[str] = field(default_factory=list)
   256	
   257	    def to_dict(self) -> dict[str, Any]:
   258	        """Convert to a serializable dict (``bundle.stub_scan`` shape)."""
   259	        return {
   260	            "status": self.status,
   261	            "ran": self.ran,
   262	            "skip_reason": self.skip_reason,
   263	            "dialect": self.dialect,
   264	            "language": self.language,
   265	            "symbols_examined": self.symbols_examined,
   266	            "findings": [_finding_to_dict(f) for f in self.findings],
   267	            "degraded_files": self.degraded_files,
   268	        }
   269	
   270	
   271	def _classify_stub_body(
   272	    body_node: Any, source: bytes, dialect: WiringDialect
   273	) -> tuple[bool, str]:
   274	    """Classify a function body as a stub.
   275	
   276	    Returns ``(is_stub, stub_kind)`` where *stub_kind* is one of:
   277	    ``"pass"`` | ``"ellipsis"`` | ``"not_implemented"`` |
   278	    ``"return_none"`` | ``"return_empty_list"`` | ``"return_empty_dict"`` |
   279	    ``"empty_block"`` | ``"marker"`` | ``"unknown"``.
   280	
   281	    Classification rules (bias against false positives):
   282	    1. If the body has more than 2 statements → not a stub (real logic).
   283	    2. If the body's child statement types are all in
   284	       ``stub_body_node_types`` → check the actual text to determine kind.
   285	    3. If the body text contains any ``stub_marker_patterns`` → stub.
   286	    4. Decorated functions are skipped (abstract methods, framework
   287	       decorators, etc.) — accepted false-negative (FEAT-C332 posture).
   288	    """
   289	    # Quick check: count top-level statements in the body block.
   290	    # If more than 2, it's almost certainly real logic.
   291	    body_text = _node_text(body_node, source)
   292	    body_type = body_node.type
   293	
   294	    # For Python: body is a (block) node; for TS/JS/C#: body is a
   295	    # (statement_block) or (block).
   296	    # Count direct child statements (excluding comments and docstrings).
   297	    child_statements = [
   298	        c for c in body_node.named_children
   299	        if c.type not in ("comment", "string")
   300	    ]
   301	
   302	    # If body has more than 2 statements, it's not a stub.
   303	    if len(child_statements) > 2:
   304	        return False, ""
   305	
   306	    # If the body type is NOT in stub_body_node_types, check if it's a
   307	    # specific stub pattern by inspecting the text.
   308	    if body_type not in dialect.stub_body_node_types:
   309	        # Check for specific stub patterns in the text.
   310	        stripped = body_text.strip()
   311	        if not stripped:
   312	            return True, "empty_block"
   313	        # Check for raise NotImplementedError / NotImplementedException
   314	        if "NotImplementedError" in stripped or "NotImplementedException" in stripped:
   315	            return True, "not_implemented"
   316	        # Check for return None / return [] / return {} / return null
   317	        if re.search(r"\breturn\s+None\b", stripped):
   318	            return True, "return_none"
   319	        if re.search(r"\breturn\s*\[\s*\]", stripped):
   320	            return True, "return_empty_list"
   321	        if re.search(r"\breturn\s*\{\s*\}", stripped):
   322	            return True, "return_empty_dict"
   323	        if re.search(r"\breturn\s+null\b", stripped):
   324	            return True, "return_none"
   325	        # Check for TODO/FIXME markers
   326	        for marker in dialect.stub_marker_patterns:
   327	            if marker in body_text:
   328	                return True, "marker"
   329	        return False, ""
   330	
   331	    # Body type IS in stub_body_node_types — determine the specific kind.
   332	    if not child_statements:
   333	        # Empty block (e.g. `{}` in TS/JS with only comments)
   334	        return True, "empty_block"
   335	
   336	    # Check each child statement.
   337	    kinds: list[str] = []
   338	    for stmt in child_statements:
   339	        stmt_text = _node_text(stmt, source).strip()
   340	        # Python pass_statement (contains a 'pass' child node)
   341	        if stmt.type == "pass_statement":
   342	            kinds.append("pass")
   343	        elif stmt.type == "pass":
   344	            kinds.append("pass")
   345	        # Python ellipsis (direct child of block)
   346	        elif stmt.type == "ellipsis":
   347	            kinds.append("ellipsis")
   348	        elif stmt.type == "expression_statement":
   349	            expr = _node_text(stmt, source).strip()
   350	            # Python ellipsis: expression_statement containing '...' or 'Ellipsis'
   351	            if expr == "..." or expr == "Ellipsis":
   352	                kinds.append("ellipsis")
   353	            elif "NotImplementedError" in expr:
   354	                kinds.append("not_implemented")
   355	            elif re.search(r"\breturn\s+None\b", expr):
   356	                kinds.append("return_none")
   357	            elif re.search(r"\breturn\s*\[\s*\]", expr):
   358	                kinds.append("return_empty_list")
   359	            elif re.search(r"\breturn\s*\{\s*\}", expr):
   360	                kinds.append("return_empty_dict")
   361	            else:
   362	                return False, ""
   363	        elif stmt.type in ("raise_statement", "raise"):
   364	            if "NotImplementedError" in stmt_text or "NotImplementedException" in stmt_text:
   365	                kinds.append("not_implemented")
   366	            else:
   367	                return False, ""
   368	        elif stmt.type in ("return_statement", "return"):
   369	            if re.search(r"\breturn\s+None\b", stmt_text):
   370	                kinds.append("return_none")
   371	            elif re.search(r"\breturn\s*\[\s*\]", stmt_text):
   372	                kinds.append("return_empty_list")
   373	            elif re.search(r"\breturn\s*\{\s*\}", stmt_text):
   374	                kinds.append("return_empty_dict")
   375	            elif re.search(r"\breturn\s+null\b", stmt_text):
   376	                kinds.append("return_none")
   377	            else:
   378	                return False, ""
   379	        elif stmt.type in ("throw_statement",):
   380	            is_not_impl = (
   381	                "NotImplementedError" in stmt_text
   382	                or "NotImplementedException" in stmt_text
   383	                or "not implemented" in stmt_text.lower()
   384	            )
   385	            if is_not_impl:
   386	                kinds.append("not_implemented")
   387	            else:
   388	                return False, ""
   389	        elif stmt.type in ("statement_block", "braced_statement_list", "block"):
   390	            # Empty block — check if it has no real children
   391	            inner = [c for c in stmt.named_children if c.type not in ("comment",)]
   392	            if not inner:
   393	                kinds.append("empty_block")
   394	            else:
   395	                return False, ""
   396	        else:
   397	            # Unknown statement type — check for markers
   398	            for marker in dialect.stub_marker_patterns:
   399	                if marker in stmt_text:
   400	                    return True, "marker"
   401	            return False, ""
   402	
   403	    if not kinds:
   404	        return True, "empty_block"
   405	
   406	    # All children are stub kinds — determine the dominant kind.
   407	    if "pass" in kinds:
   408	        return True, "pass"
   409	    if "ellipsis" in kinds:
   410	        return True, "ellipsis"
   411	    if "not_implemented" in kinds:
   412	        return True, "not_implemented"
   413	    if "return_empty_list" in kinds:
   414	        return True, "return_empty_list"
   415	    if "return_empty_dict" in kinds:
   416	        return True, "return_empty_dict"
   417	    if "return_none" in kinds:
   418	        return True, "return_none"
   419	
   420	    # Check for markers in the body text.
   421	    for marker in dialect.stub_marker_patterns:
   422	        if marker in body_text:
   423	            return True, "marker"
   424	
   425	    return False, ""
   426	
   427	
   428	def _scan_stub_body_for_dialect(
   429	    targets: list[str],
   430	    worktree: Path,
   431	    dialect: WiringDialect,
   432	) -> StubScanResult:
   433	    """Run the anti-stub body scan for one dialect over authored targets."""
   434	    if not dialect.stub_body_query:
   435	        return StubScanResult(
   436	            status="skipped_no_targets",
   437	            ran=False,
   438	            skip_reason="no stub_body_query for dialect",
   439	        )
   440	
   441	    out = StubScanResult(
   442	        dialect=dialect.language,
   443	        language=dialect.language,
   444	    )
   445	
   446	    for rel_path in targets:
   447	        source = _read_bytes(worktree / rel_path)
   448	        if source is None:
   449	            continue
   450	        out.symbols_examined += 1
   451	        tree = _parse_or_none(source, dialect)
   452	        if tree is None:
   453	            out.degraded_files.append(rel_path)
   454	            continue
   455	
   456	        # Run the stub body query.
   457	        try:
   458	            matches = _run_query_matches(
   459	                dialect.stub_body_query, tree, dialect.ts_language_name
   460	            )
   461	        except Exception as exc:
   462	            logger.warning(
   463	                "stub_body_query failed for '%s': %s", dialect.language, exc
   464	            )
   465	            continue
   466	
   467	        for captures in matches:
   468	            name_nodes = captures.get("name", [])
   469	            body_nodes = captures.get("body", [])
   470	            if not name_nodes or not body_nodes:
   471	                continue
   472	
   473	            # Check if the function is decorated — skip decorated functions
   474	            # to avoid false positives on abstract methods, framework
   475	            # decorators, etc.
   476	            name_node = name_nodes[0]
   477	            parent = getattr(name_node, "parent", None)
   478	            if parent is not None:
   479	                # Check if parent is a decorated_definition
   480	                grandparent = getattr(parent, "parent", None)
   481	                if grandparent is not None and grandparent.type == "decorated_definition":
   482	                    continue  # skip decorated functions (FEAT-C332)
   483	
   484	            body_node = body_nodes[0]
   485	            is_stub, stub_kind = _classify_stub_body(body_node, source, dialect)
   486	            if is_stub:
   487	                sym_name = _node_text(name_nodes[0], source)
   488	                out.findings.append(Finding(
   489	                    file=rel_path,
   490	                    symbol=sym_name,
   491	                    kind="STUB_BODY",
   492	                    module=os.path.basename(rel_path),
   493	                    lineno=name_nodes[0].start_point[0] + 1,
   494	                    severity="warning",
   495	                    pattern="STUB_BODY",
   496	                    why=f"Stub body ({stub_kind}): {sym_name}",
   497	                    dialect=dialect.language,
   498	                    language=dialect.language,
   499	                ))
   500	
   501	    if out.findings:
   502	        out.status = "complete"
   503	        out.ran = True
   504	    else:
   505	        out.status = "complete"
   506	        out.ran = True
   507	        out.skip_reason = "no stubs found"
   508	
   509	    return out
   510	
   511	
   512	def analyze_stub_scan(
   513	    authored_files: list[str],
   514	    worktree_path: str | Path,
   515	    task_type: str,
   516	    stack: Any = None,
   517	) -> dict[str, Any] | None:
   518	    """Analyze authored files for stub bodies.
   519	
   520	    Parameters
   521	    ----------
   522	    authored_files:
   523	        Worktree-relative paths authored this turn.
   524	    worktree_path:
   525	        Path to the worktree root.
   526	    task_type:
   527	        Only ``FEATURE`` / ``REFACTOR`` / ``INTEGRATION`` are analyzed
   528	        (case-insensitive); other task types return ``None``.
   529	        ``SCAFFOLDING``, ``DOCUMENTATION``, ``TESTING`` return ``None``.
   530	    stack:
   531	        Optional object with a ``language`` attribute for dialect dispatch.
   532	
   533	    Returns
   534	    -------
   535	    dict | None
   536	        The stub-scan result dict (see module docstring), or ``None`` when
   537	        the probe legitimately did not run (task-type gate; zero authored
   538	        non-test source targets).
   539	    """
   540	    try:
   541	        return _analyze_stub_scan_impl(
   542	            authored_files, Path(worktree_path), task_type, stack
   543	        )
   544	    except Exception as exc:  # noqa: BLE001 — fail-open by contract
   545	        logger.warning("analyze_stub_scan failed unexpectedly: %s", exc, exc_info=True)
   546	        return {
   547	            "status": "error",
   548	            "error": str(exc),
   549	            "dialect": None,
   550	            "language": "",
   551	            "symbols_examined": 0,
   552	            "findings": [],
   553	            "degraded_files": [],
   554	        }
   555	
   556	
   557	def _analyze_stub_scan_impl(
   558	    authored_files: list[str],
   559	    worktree: Path,
   560	    task_type: str,
   561	    stack: Any,
   562	) -> dict[str, Any] | None:
   563	    # --- Task-type gate (same as analyze_wiring) ---------------------------
   564	    if (task_type or "").upper() not in _ANALYZED_TASK_TYPES:
   565	        return None
   566	
   567	    # --- Select candidate dialects -----------------------------------------
   568	    candidates: list[tuple[WiringDialect, list[str]]] = []
   569	    for dialect in iter_dialects():
   570	        if not dialect.stub_body_query:
   571	            continue  # dialect has no stub scan support
   572	        targets = [
   573	            f
   574	            for f in authored_files
   575	            if _matches_glob(f, dialect.file_globs)
   576	            and not _is_test_file(f, dialect)
   577	            and (worktree / f).is_file()
   578	        ]
   579	        if targets:
   580	            candidates.append((dialect, targets))
   581	
   582	    if not candidates:
   583	        return None  # zero authored source targets → probe didn't run
   584	
   585	    # --- Run every matching dialect ----------------------------------------
   586	    analyses: list[StubScanResult] = [
   587	        _scan_stub_body_for_dialect(targets, worktree, dialect)
   588	        for dialect, targets in candidates
   589	    ]
   590	
   591	    # --- Merge --------------------------------------------------------------
   592	    languages = [a.language for a in analyses]
   593	    primary = languages[0] if languages else ""
   594	
   595	    degraded = [f for a in analyses for f in a.degraded_files]
   596	    all_findings: list[Finding] = []
   597	    for a in analyses:
   598	        all_findings.extend(a.findings)
   599	
   600	    status: WiringStatus = "parse_degraded" if degraded else "complete"
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialect.py'}, 'id': 'qiPmFfqiPGf1KCJ8OW0Rase7kgFz5fcu', 'type': 'tool_call'}]
Tool:      1	"""WiringDialect: frozen dataclass + registry for declarative per-language descriptors.
     2	
     3	A dialect is a frozen dataclass ``WiringDialect``, one record per language,
     4	registered in a per-language module under ``wiring/dialects/``.  Every field
     5	is DATA — tree-sitter S-expression query strings and pattern lists, no
     6	executable plugin code.
     7	
     8	The registry maps a language name (e.g. ``"python"``) to its dialect
     9	descriptor.  Dialects are registered at import time by their respective
    10	``wiring.dialects.<lang>`` modules.
    11	"""
    12	
    13	from __future__ import annotations
    14	
    15	import logging
    16	from dataclasses import dataclass
    17	from typing import TYPE_CHECKING
    18	
    19	if TYPE_CHECKING:
    20	    from collections.abc import Iterator
    21	
    22	logger = logging.getLogger(__name__)
    23	
    24	# ---------------------------------------------------------------------------
    25	# Registry
    26	# ---------------------------------------------------------------------------
    27	
    28	_registry: dict[str, WiringDialect] = {}
    29	
    30	
    31	def register_dialect(dialect: WiringDialect) -> WiringDialect:
    32	    """Register a wiring dialect in the global registry.
    33	
    34	    Returns *dialect* for use as a decorator / return-value.
    35	    """
    36	    _registry[dialect.language] = dialect
    37	    return dialect
    38	
    39	
    40	def get_dialect(language: str) -> WiringDialect | None:
    41	    """Look up a dialect by language name.
    42	
    43	    Returns ``None`` when no dialect is registered for *language*.
    44	    """
    45	    return _registry.get(language)
    46	
    47	
    48	def iter_dialects() -> Iterator[WiringDialect]:
    49	    """Iterate over all registered dialects (insertion order)."""
    50	    yield from _registry.values()
    51	
    52	
    53	# ---------------------------------------------------------------------------
    54	# WiringDialect
    55	# ---------------------------------------------------------------------------
    56	
    57	@dataclass(frozen=True, slots=True)
    58	class WiringDialect:
    59	    """Declarative descriptor for one language's wiring-analysis queries.
    60	
    61	    Parameters
    62	    ----------
    63	    language:
    64	        Human-readable language name used in findings (``"python"``,
    65	        ``"javascript"``, ``"typescript"``, ``"c_sharp"``).
    66	    ts_language_name:
    67	        Canonical key passed to ``tree_sitter_language_pack.get_language()``
    68	        (``"python"``, ``"javascript"``, ``"typescript"``, ``"csharp"`` —
    69	        note ``"csharp"``, NOT ``"c_sharp"``, for the pack key).
    70	    file_globs:
    71	        Glob patterns for source files of this language.
    72	    public_symbols_query:
    73	        tree-sitter S-expression that captures public top-level
    74	        function/class/export declarations plus their ``@name`` capture.
    75	        May also capture ``@visibility`` (e.g. C# modifiers); the analyzer
    76	        pairs ``@visibility`` with ``@name`` per match and applies
    77	        ``public_visibilities``.
    78	    references_query:
    79	        tree-sitter S-expression that captures identifier / member-access
    80	        nodes used for reference detection.
    81	    registration_queries:
    82	        One or more S-expressions that match composition-root binding
    83	        patterns (e.g. ``cli.add_command(X)``, ``AddScoped<X>()``).  The
    84	        registered symbol must be captured as ``@target``.
    85	    mock_call_query:
    86	        S-expression that captures mock/patch primitive calls plus their
    87	        target argument as ``@target``.  Use tree-sitter predicates
    88	        (``#any-of?``/``#eq?``) to restrict to actual mock primitives —
    89	        an unrestricted call query floods MOCKED_SEAM with false targets.
    90	    test_path_markers:
    91	        Path substrings that identify test files (excluded from wiring
    92	        analysis targets and from the reference map).
    93	    acceptance_path_markers:
    94	        Path substrings that identify acceptance/integration test files
    95	        (scanned for MOCKED_SEAM).
    96	    external_mock_allowlist:
    97	        Module names whose mocking is acceptable (e.g. ``"httpx"``,
    98	        ``"requests"``).
    99	    external_mock_path_roots:
   100	        Path substrings indicating external-adapter code whose mocking
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/'}, 'id': '1AaECkweCIGYPYjvCBcjskddXwvuEGUz', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/c_sharp.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/javascript.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/python.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/typescript.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/python.py'}, 'id': 'hwaiz8mCxQfUkySczCdzK3gAG2vpSTEu', 'type': 'tool_call'}]
Tool:      1	"""Python wiring dialect descriptor.
     2	
     3	Registers the ``WiringDialect`` for Python at import time.
     4	"""
     5	
     6	from __future__ import annotations
     7	
     8	from guardkitfactory.wiring.dialect import WiringDialect, register_dialect
     9	
    10	dialect = register_dialect(
    11	    WiringDialect(
    12	        language="python",
    13	        ts_language_name="python",
    14	        file_globs=("**/*.py", "*.py"),
    15	        # Module-level defs/classes, including decorated ones.  Privacy is
    16	        # handled by private_name_prefixes ("_") in the analyzer.
    17	        public_symbols_query="""
    18	            (module
    19	              [
    20	                (function_definition
    21	                  name: (identifier) @name)
    22	                (class_definition
    23	                  name: (identifier) @name)
    24	                (decorated_definition
    25	                  definition: [
    26	                    (function_definition
    27	                      name: (identifier) @name)
    28	                    (class_definition
    29	                      name: (identifier) @name)
    30	                  ])
    31	              ])
    32	        """,
    33	        # ---------------------------------------------------------------------------
    34	        # Anti-stub body scan (TASK-QAV-001)
    35	        # ---------------------------------------------------------------------------
    36	        # Captures module-level function definitions and decorated functions.
    37	        # The analyzer classifies the body as a stub using stub_body_node_types
    38	        # and stub_marker_patterns.  Decorated functions are excluded from
    39	        # stub-flagging to avoid false positives on abstract methods,
    40	        # framework-decorated handlers, etc. (FEAT-C332 bias posture).
    41	        stub_body_query="""
    42	            (function_definition
    43	              name: (identifier) @name
    44	              body: (block) @body)
    45	            (decorated_definition
    46	              definition: (function_definition
    47	                name: (identifier) @name
    48	                body: (block) @body))
    49	        """,
    50	        stub_marker_patterns=(
    51	            "TODO",
    52	            "FIXME",
    53	            "STUB",
    54	            "placeholder",
    55	            "HACK",
    56	            "XXX",
    57	        ),
    58	        stub_body_node_types=(
    59	            "block",
    60	        ),
    61	        # Blanket identifier capture: with the analyzer excluding the
    62	        # defining file and test files from the reference map, any
    63	        # occurrence of the name elsewhere counts as a reference
    64	        # (biased WIRED per the scope's FP/FN posture).
    65	        references_query="""
    66	            (identifier) @name
    67	        """,
    68	        registration_queries=(
    69	            # Click / FastAPI / generic registries:
    70	            #   cli.add_command(X), api.include_router(X), registry.register(X)
    71	            """
    72	            (call
    73	              function: (attribute
    74	                attribute: (identifier) @method)
    75	              arguments: (argument_list
    76	                (identifier) @target)
    77	              (#any-of? @method "add_command" "include_router" "register"))
    78	            """,
    79	            # Decorator-registered commands/routes:
    80	            #   @cli.command() / @app.get("/x") above a def
    81	            """
    82	            (decorated_definition
    83	              (decorator
    84	                (call
    85	                  function: (attribute
    86	                    attribute: (identifier) @method)
    87	                  (#any-of? @method "command" "route" "get" "post" "put" "delete")))
    88	              definition: (function_definition
    89	                name: (identifier) @target))
    90	            """,
    91	        ),
    92	        # Restricted to actual mock primitives via predicate.  Three families:
    93	        #   1. patch("..."), mock.patch("..."), mocker.patch("..."),
    94	        #      monkeypatch.setattr(target, ...), patch.object(Target, ...)
    95	        #   2. spec-mock constructors: AsyncMock(spec=Service),
    96	        #      MagicMock(spec=Service), Mock(spec_set=Service), ... (AC#2)
    97	        #   3. create_autospec(Service)  (AC#2)
    98	        mock_call_query="""
    99	            (call
   100	              function: [
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/typescript.py'}, 'id': 'NuGOVZsUUr5xg32ap7rjZh3uxC51jsVC', 'type': 'tool_call'}]
Tool:      1	"""TypeScript wiring dialect descriptor.
     2	
     3	Registers the ``WiringDialect`` for TypeScript at import time.
     4	Shares query bodies with JavaScript where grammars overlap.
     5	
     6	Note: ``.tsx`` files are parsed with the plain ``typescript`` grammar;
     7	JSX-heavy files will parse-degrade and bias WIRED (recorded in
     8	``degraded_files``), never produce a false UNWIRED.
     9	"""
    10	
    11	from __future__ import annotations
    12	
    13	from guardkitfactory.wiring.dialect import WiringDialect, register_dialect
    14	
    15	dialect = register_dialect(
    16	    WiringDialect(
    17	        language="typescript",
    18	        ts_language_name="typescript",
    19	        file_globs=("**/*.ts", "*.ts", "**/*.tsx", "*.tsx"),
    20	        # Export-wrapped declarations only (scope §3.2).  Class/interface
    21	        # names are (type_identifier) in the TS grammar.
    22	        public_symbols_query="""
    23	            (export_statement
    24	              [
    25	                (function_declaration
    26	                  name: (identifier) @name)
    27	                (class_declaration
    28	                  name: (type_identifier) @name)
    29	                (interface_declaration
    30	                  name: (type_identifier) @name)
    31	                (lexical_declaration
    32	                  (variable_declarator
    33	                    name: (identifier) @name))
    34	              ])
    35	        """,
    36	        # ---------------------------------------------------------------------------
    37	        # Anti-stub body scan (TASK-QAV-001)
    38	        # ---------------------------------------------------------------------------
    39	        # Captures exported function declarations and class methods.
    40	        # The analyzer classifies the body as a stub using stub_body_node_types
    41	        # and stub_marker_patterns.
    42	        stub_body_query="""
    43	            (export_statement
    44	              (function_declaration
    45	                name: (identifier) @name
    46	                body: (statement_block) @body))
    47	            (class_declaration
    48	              body: (class_body
    49	                [
    50	                  (method_definition
    51	                    name: (property_identifier) @name
    52	                    body: (statement_block) @body)
    53	                ]))
    54	        """,
    55	        stub_marker_patterns=(
    56	            "TODO",
    57	            "FIXME",
    58	            "STUB",
    59	            "placeholder",
    60	            "HACK",
    61	            "XXX",
    62	        ),
    63	        stub_body_node_types=(
    64	            "statement_block",   # empty block `{}`
    65	        ),
    66	        # Type positions use (type_identifier); value positions (identifier).
    67	        references_query="""
    68	            [
    69	              (identifier)
    70	              (type_identifier)
    71	            ] @name
    72	        """,
    73	        registration_queries=(
    74	            # Express / routers / generic registries
    75	            """
    76	            (call_expression
    77	              function: (member_expression
    78	                property: (property_identifier) @method)
    79	              arguments: (arguments
    80	                (identifier) @target)
    81	              (#any-of? @method "use" "get" "post" "put" "delete" "register"))
    82	            """,
    83	        ),
    84	        mock_call_query="""
    85	            (call_expression
    86	              function: [
    87	                (identifier) @fn
    88	                (member_expression
    89	                  property: (property_identifier) @fn)
    90	              ]
    91	              arguments: (arguments
    92	                .
    93	                [
    94	                  (string) @target
    95	                  (identifier) @target
    96	                ])
    97	              (#any-of? @fn "mock" "doMock" "stub" "spyOn" "fake"))
    98	        """,
    99	        test_path_markers=(
   100	            "/test_", ".test.", ".spec.", "_test.", "/tests/", "/test/", "__tests__/",
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/dialects/c_sharp.py'}, 'id': 'DxZxVtqsSNFGVUqpKTz0Fj7vuEeaRBa4', 'type': 'tool_call'}]
Tool:      1	"""C# wiring dialect descriptor.
     2	
     3	Registers the ``WiringDialect`` for C# at import time.
     4	
     5	Note the pack key is ``"csharp"`` (NOT ``"c_sharp"``) while the registry
     6	language stays ``"c_sharp"``.
     7	"""
     8	
     9	from __future__ import annotations
    10	
    11	from guardkitfactory.wiring.dialect import WiringDialect, register_dialect
    12	
    13	dialect = register_dialect(
    14	    WiringDialect(
    15	        language="c_sharp",
    16	        ts_language_name="csharp",
    17	        file_globs=("**/*.cs", "*.cs"),
    18	        # Captures @visibility alongside @name; the analyzer pairs them per
    19	        # match and keeps only public/internal (public_visibilities below).
    20	        # Declarations with NO modifier are not captured — invisible symbols
    21	        # bias WIRED, never false-UNWIRED.
    22	        public_symbols_query="""
    23	            [
    24	                (class_declaration
    25	                  (modifier) @visibility
    26	                  name: (identifier) @name)
    27	                (interface_declaration
    28	                  (modifier) @visibility
    29	                  name: (identifier) @name)
    30	                (method_declaration
    31	                  (modifier) @visibility
    32	                  name: (identifier) @name)
    33	            ]
    34	        """,
    35	        # ---------------------------------------------------------------------------
    36	        # Anti-stub body scan (TASK-QAV-001)
    37	        # ---------------------------------------------------------------------------
    38	        # Captures public method declarations with block bodies.
    39	        stub_body_query="""
    40	            (method_declaration
    41	              [
    42	                (modifier) @visibility
    43	              ]
    44	              name: (identifier) @name
    45	              body: (block) @body)
    46	        """,
    47	        stub_marker_patterns=(
    48	            "TODO",
    49	            "FIXME",
    50	            "STUB",
    51	            "placeholder",
    52	            "HACK",
    53	            "XXX",
    54	        ),
    55	        stub_body_node_types=(
    56	            "block",   # empty block `{}`
    57	        ),
    58	        references_query="""
    59	            (identifier) @name
    60	        """,
    61	        registration_queries=(
    62	            # .NET DI: services.AddScoped<X>() / AddSingleton<X>() / AddTransient<X>()
    63	            """
    64	            (invocation_expression
    65	              function: (member_access_expression
    66	                name: (generic_name
    67	                  (identifier) @method
    68	                  (type_argument_list
    69	                    (identifier) @target)))
    70	              (#any-of? @method "AddScoped" "AddSingleton" "AddTransient"))
    71	            """,
    72	            # Minimal API: app.MapGet(..., Handler) / MapPost / MapGroup
    73	            """
    74	            (invocation_expression
    75	              function: (member_access_expression
    76	                name: (identifier) @method)
    77	              arguments: (argument_list
    78	                (argument
    79	                  (identifier) @target))
    80	              (#any-of? @method "MapGet" "MapPost" "MapPut" "MapDelete" "MapGroup"))
    81	            """,
    82	            # FastEndpoints reachable-by-convention: public class X : Endpoint<...>
    83	            """
    84	            (class_declaration
    85	              name: (identifier) @target
    86	              (base_list
    87	                [
    88	                  (identifier) @base
    89	                  (generic_name (identifier) @base)
    90	                ])
    91	              (#match? @base "^Endpoint"))
    92	            """,
    93	        ),
    94	        # Moq: new Mock<T>(); NSubstitute: Substitute.For<T>();
    95	        # FakeItEasy: A.Fake<T>().  @target is the generic TYPE argument.
    96	        mock_call_query="""
    97	            (object_creation_expression
    98	              type: (generic_name
    99	                (identifier) @fn
   100	                (type_argument_list
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Verify implementation of analyze_stub_scan in guardkitfactory/src/guardkitfactory/wiring/analyzer.py', 'status': 'in_progress'}, {'content': 'Verify dialect definitions in guardkitfactory/src/guardkitfactory/wiring/dialects/', 'status': 'pending'}, {'content': 'Review implementation against AC-1 to AC-8', 'status': 'pending'}]}, 'id': 'ILERUN6rCVMtfU8ch0sZiXATAa1acGSm', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Verify implementation of analyze_stub_scan in guardkitfactory/src/guardkitfactory/wiring/analyzer.py', 'status': 'in_progress'}, {'content': 'Verify dialect definitions in guardkitfactory/src/guardkitfactory/wiring/dialects/', 'status': 'pending'}, {'content': 'Review implementation against AC-1 to AC-8', 'status': 'pending'}]
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/analyzer.py', 'limit': 1000, 'offset': 550}, 'id': '7S41TMSvE9O80DeeKU9OYW9OKyXrV7pQ', 'type': 'tool_call'}]
Tool:    551	            "symbols_examined": 0,
   552	            "findings": [],
   553	            "degraded_files": [],
   554	        }
   555	
   556	
   557	def _analyze_stub_scan_impl(
   558	    authored_files: list[str],
   559	    worktree: Path,
   560	    task_type: str,
   561	    stack: Any,
   562	) -> dict[str, Any] | None:
   563	    # --- Task-type gate (same as analyze_wiring) ---------------------------
   564	    if (task_type or "").upper() not in _ANALYZED_TASK_TYPES:
   565	        return None
   566	
   567	    # --- Select candidate dialects -----------------------------------------
   568	    candidates: list[tuple[WiringDialect, list[str]]] = []
   569	    for dialect in iter_dialects():
   570	        if not dialect.stub_body_query:
   571	            continue  # dialect has no stub scan support
   572	        targets = [
   573	            f
   574	            for f in authored_files
   575	            if _matches_glob(f, dialect.file_globs)
   576	            and not _is_test_file(f, dialect)
   577	            and (worktree / f).is_file()
   578	        ]
   579	        if targets:
   580	            candidates.append((dialect, targets))
   581	
   582	    if not candidates:
   583	        return None  # zero authored source targets → probe didn't run
   584	
   585	    # --- Run every matching dialect ----------------------------------------
   586	    analyses: list[StubScanResult] = [
   587	        _scan_stub_body_for_dialect(targets, worktree, dialect)
   588	        for dialect, targets in candidates
   589	    ]
   590	
   591	    # --- Merge --------------------------------------------------------------
   592	    languages = [a.language for a in analyses]
   593	    primary = languages[0] if languages else ""
   594	
   595	    degraded = [f for a in analyses for f in a.degraded_files]
   596	    all_findings: list[Finding] = []
   597	    for a in analyses:
   598	        all_findings.extend(a.findings)
   599	
   600	    status: WiringStatus = "parse_degraded" if degraded else "complete"
   601	    if not all_findings and not degraded:
   602	        status = "complete"
   603	
   604	    result = StubScanResult(
   605	        status=status,
   606	        ran=True,
   607	        skip_reason=None,
   608	        dialect=primary,
   609	        language=primary,
   610	        symbols_examined=sum(a.symbols_examined for a in analyses),
   611	        findings=all_findings,
   612	        degraded_files=degraded,
   613	    )
   614	
   615	    return result.to_dict()
   616	
   617	
   618	# ---------------------------------------------------------------------------
   619	# File-walking helpers
   620	# ---------------------------------------------------------------------------
   621	
   622	_EXCLUSION_DIRS = frozenset({
   623	    "__pycache__",
   624	    "node_modules",
   625	    "bin",
   626	    "obj",
   627	    ".git",
   628	    ".guardkit",
   629	    ".venv",
   630	    "venv",
   631	    ".mypy_cache",
   632	    ".pytest_cache",
   633	    ".ruff_cache",
   634	    "dist",
   635	    "build",
   636	})
   637	
   638	
   639	def _norm_path(path: str) -> str:
   640	    """Normalize a relative path for marker matching: forward slashes and a
   641	    leading "/" so markers like ``"/test_"`` anchor at path-segment starts
   642	    (avoids ``"test_"`` matching ``contest_utils.py``)."""
   643	    return "/" + path.replace(os.sep, "/")
   644	
   645	
   646	def _is_test_file(path: str, dialect: WiringDialect) -> bool:
   647	    """Check if a path matches the dialect's test-file markers."""
   648	    p = _norm_path(path)
   649	    return any(marker in p for marker in dialect.test_path_markers)
   650	
   651	
   652	def _is_acceptance_file(path: str, dialect: WiringDialect) -> bool:
   653	    """Check if a path matches the dialect's acceptance/integration markers."""
   654	    p = _norm_path(path)
   655	    return any(marker in p for marker in dialect.acceptance_path_markers)
   656	
   657	
   658	def _is_composition_root(path: str, dialect: WiringDialect) -> bool:
   659	    """Check if a path matches the dialect's composition-root markers."""
   660	    p = _norm_path(path)
   661	    return any(marker in p for marker in dialect.composition_root_markers)
   662	
   663	
   664	def _matches_glob(path: str, patterns: tuple[str, ...]) -> bool:
   665	    """Check if a path matches any of the glob patterns."""
   666	    return any(fnmatch.fnmatch(path, p) for p in patterns)
   667	
   668	
   669	def _collect_source_files(worktree: Path, dialect: WiringDialect) -> list[str]:
   670	    """Collect worktree-relative source files matching the dialect's globs."""
   671	    files: list[str] = []
   672	    for root, dirs, filenames in os.walk(worktree):
   673	        dirs[:] = [d for d in dirs if d not in _EXCLUSION_DIRS]
   674	        for fname in filenames:
   675	            rel_path = os.path.relpath(os.path.join(root, fname), worktree)
   676	            if _matches_glob(rel_path, dialect.file_globs):
   677	                files.append(rel_path)
   678	    return sorted(files)
   679	
   680	
   681	def _read_bytes(path: Path) -> bytes | None:
   682	    try:
   683	        with open(path, "rb") as f:
   684	            return f.read()
   685	    except OSError:
   686	        return None
   687	
   688	
   689	# ---------------------------------------------------------------------------
   690	# Query helpers
   691	# ---------------------------------------------------------------------------
   692	
   693	
   694	def _node_text(node: Any, source: bytes) -> str:
   695	    """Extract text from a tree-sitter node."""
   696	    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
   697	
   698	
   699	def _run_query_matches(
   700	    query_text: str, tree: Any, language_name: str
   701	) -> list[dict[str, list[Any]]]:
   702	    """Run a query and return per-match capture dicts.
   703	
   704	    Per-match grouping (``matches`` not ``captures``) is required to pair
   705	    ``@visibility`` with its ``@name`` in the same declaration, and to
   706	    apply ``#any-of?``/``#eq?``/``#match?`` predicates reliably.
   707	    """
   708	    from tree_sitter import Query, QueryCursor
   709	
   710	    lang = _load_language(language_name)
   711	    query = Query(lang, query_text)
   712	    cursor = QueryCursor(query)
   713	    return [captures for _pattern_idx, captures in cursor.matches(tree.root_node)]
   714	
   715	
   716	def _run_query_captures(
   717	    query_text: str, tree: Any, language_name: str
   718	) -> dict[str, list[Any]]:
   719	    """Run a query and return the flat capture-name → nodes dict."""
   720	    from tree_sitter import Query, QueryCursor
   721	
   722	    lang = _load_language(language_name)
   723	    query = Query(lang, query_text)
   724	    cursor = QueryCursor(query)
   725	    return cursor.captures(tree.root_node)
   726	
   727	
   728	# ---------------------------------------------------------------------------
   729	# Symbol extraction
   730	# ---------------------------------------------------------------------------
   731	
   732	
   733	def _extract_public_symbols(
   734	    source: bytes, tree: Any, dialect: WiringDialect
   735	) -> list[dict[str, Any]]:
   736	    """Extract public symbols, applying the dialect's is-public predicates.
   737	
   738	    Privacy is DATA-driven: ``private_name_prefixes`` (e.g. ``"_"`` for
   739	    Python) and ``public_visibilities`` (e.g. ``("public", "internal")``
   740	    for C#, paired with the query's ``@visibility`` captures per match).
   741	    """
   742	    try:
   743	        matches = _run_query_matches(
   744	            dialect.public_symbols_query, tree, dialect.ts_language_name
   745	        )
   746	    except Exception as exc:
   747	        logger.warning(
   748	            "public_symbols_query failed for '%s': %s", dialect.language, exc
   749	        )
   750	        return []
   751	
   752	    symbols: list[dict[str, Any]] = []
   753	    for captures in matches:
   754	        name_nodes = captures.get("name", [])
   755	        if not name_nodes:
   756	            continue
   757	        if dialect.public_visibilities:
   758	            vis = {
   759	                _node_text(v, source) for v in captures.get("visibility", [])
   760	            }
   761	            if not (vis & set(dialect.public_visibilities)):
   762	                continue
   763	        for node in name_nodes:
   764	            name = _node_text(node, source)
   765	            if not name:
   766	                continue
   767	            if any(name.startswith(p) for p in dialect.private_name_prefixes):
   768	                continue
   769	            symbols.append({
   770	                "name": name,
   771	                "lineno": node.start_point[0] + 1,
   772	                "kind": _symbol_kind(node),
   773	            })
   774	    return symbols
   775	
   776	
   777	_KIND_BY_DECLARATION = {
   778	    "function_definition": "function",
   779	    "function_declaration": "function",
   780	    "method_declaration": "function",
   781	    "class_definition": "class",
   782	    "class_declaration": "class",
   783	    "interface_declaration": "interface",
   784	    "variable_declarator": "const",
   785	}
   786	
   787	
   788	def _symbol_kind(name_node: Any) -> str:
   789	    """Map a captured name node to its declaration kind (AC-001:
   790	    ``kind:"function"``/``"class"``/...), via the enclosing declaration."""
   791	    parent = getattr(name_node, "parent", None)
   792	    if parent is not None:
   793	        return _KIND_BY_DECLARATION.get(parent.type, "symbol")
   794	    return "symbol"
   795	
   796	
   797	_DUNDER_ALL_RE = re.compile(r"__all__\s*=\s*[\[\(]([^\]\)]*)[\]\)]", re.DOTALL)
   798	_QUOTED_NAME_RE = re.compile(r"""["']([^"']+)["']""")
   799	
   800	
   801	def _dunder_all_names(source: bytes) -> set[str]:
   802	    """Names listed in a Python ``__all__`` literal (count as wired)."""
   803	    text = source.decode("utf-8", errors="replace")
   804	    names: set[str] = set()
   805	    for m in _DUNDER_ALL_RE.finditer(text):
   806	        names.update(_QUOTED_NAME_RE.findall(m.group(1)))
   807	    return names
   808	
   809	
   810	def _extract_references(
   811	    source: bytes, tree: Any, dialect: WiringDialect
   812	) -> set[str]:
   813	    """Extract identifier references from a parsed file."""
   814	    try:
   815	        captures = _run_query_captures(
   816	            dialect.references_query, tree, dialect.ts_language_name
   817	        )
   818	    except Exception as exc:
   819	        logger.warning(
   820	            "references_query failed for '%s': %s", dialect.language, exc
   821	        )
   822	        return set()
   823	    return {
   824	        _node_text(n, source)
   825	        for n in captures.get("name", [])
   826	        if n is not None
   827	    }
   828	
   829	
   830	def _extract_registrations(
   831	    source: bytes, tree: Any, dialect: WiringDialect
   832	) -> set[str]:
   833	    """Extract registered symbol names (``@target`` captures) from a file."""
   834	    registered: set[str] = set()
   835	    for reg_query in dialect.registration_queries:
   836	        try:
   837	            captures = _run_query_captures(
   838	                reg_query, tree, dialect.ts_language_name
   839	            )
   840	        except Exception as exc:
   841	            logger.warning(
   842	                "registration query failed for '%s': %s", dialect.language, exc
   843	            )
   844	            continue
   845	        registered.update(
   846	            _node_text(n, source) for n in captures.get("target", [])
   847	        )
   848	    return registered
   849	
   850	
   851	def _manifest_text(worktree: Path, dialect: WiringDialect) -> str:
   852	    """Concatenated text of all script-manifest files (glob-aware)."""
   853	    chunks: list[str] = []
   854	    for pattern in dialect.script_manifest_files:
   855	        if any(ch in pattern for ch in "*?["):
   856	            paths = list(worktree.glob(pattern))
   857	        else:
   858	            p = worktree / pattern
   859	            paths = [p] if p.is_file() else []
   860	        for path in paths:
   861	            try:
   862	                chunks.append(path.read_text(errors="replace"))
   863	            except OSError:
   864	                continue
   865	    return "\n".join(chunks)
   866	
   867	
   868	def _build_text_corpus(
   869	    worktree: Path, dialect: WiringDialect
   870	) -> list[tuple[str, str]]:
   871	    """Raw text of every non-test file under the worktree, read once.
   872	
   873	    Powers the biased-WIRED substring fallback: deliberately BROADER than
   874	    scope §4.1 step 5's parse-failed-only grep — a raw-text hit anywhere
   875	    (configs, docs, .feature files) counts as referenced.  This widens
   876	    accepted false-negatives and can never produce a false UNWIRED.
   877	    """
   878	    corpus: list[tuple[str, str]] = []
   879	    for root, dirs, filenames in os.walk(worktree):
   880	        dirs[:] = [d for d in dirs if d not in _EXCLUSION_DIRS]
   881	        for fname in filenames:
   882	            full_path = os.path.join(root, fname)
   883	            rel_path = os.path.relpath(full_path, worktree)
   884	            if _is_test_file(rel_path, dialect):
   885	                continue
   886	            try:
   887	                with open(full_path, errors="replace") as f:
   888	                    corpus.append((rel_path, f.read()))
   889	            except OSError:
   890	                continue
   891	    return corpus
   892	
   893	
   894	def _substring_fallback(
   895	    symbol: str, corpus: list[tuple[str, str]], exclude_file: str
   896	) -> bool:
   897	    """Biased-WIRED fallback: symbol appears as a substring in any
   898	    non-test, non-self file's raw text."""
   899	    return any(
   900	        symbol in text for rel_path, text in corpus if rel_path != exclude_file
   901	    )
   902	
   903	
   904	# ---------------------------------------------------------------------------
   905	# Constructor-arity helpers (CTOR_ARITY probe)
   906	# ---------------------------------------------------------------------------
   907	
   908	
   909	@dataclass
   910	class _CtorSig:
   911	    """Extracted constructor signature for a first-party class."""
   912	
   913	    name: str
   914	    required: int          # required positional-or-keyword params (excl. self)
   915	    total: int             # required + defaulted params (excl. self)
   916	    variadic: bool         # has *args / **kwargs → arity unknowable (bias OK)
   917	    lineno: int = 0
   918	
   919	
   920	def _first_identifier_text(node: Any, source: bytes) -> str:
   921	    """Return the text of the first ``identifier`` descendant (the param name).
   922	
   923	    For ``self`` the node IS an identifier; for ``x: int`` / ``x=1`` the param
   924	    name is the first identifier in document order (before the colon/equals).
   925	    """
   926	    if node.type == "identifier":
   927	        return _node_text(node, source)
   928	    for child in node.children:
   929	        if child.type == "identifier":
   930	            return _node_text(child, source)
   931	    return ""
   932	
   933	
   934	def _summarise_params(
   935	    params_node: Any, source: bytes, dialect: WiringDialect
   936	) -> tuple[int, int, bool]:
   937	    """Count (required, total, variadic) for a constructor parameter list.
   938	
   939	    DATA-driven via the dialect's ``param_*`` node-type tuples — no language
   940	    branching here.  ``self``/``cls`` (``param_self_names``) are excluded.
   941	    Any splat parameter makes the signature variadic (arity unknowable).
   942	    """
   943	    required = 0
   944	    total = 0
   945	    variadic = False
   946	    for child in params_node.named_children:
   947	        ctype = child.type
   948	        if ctype in dialect.param_splat_node_types:
   949	            variadic = True
   950	        elif ctype in dialect.param_default_node_types:
   951	            name = _first_identifier_text(child, source)
   952	            if name in dialect.param_self_names:
   953	                continue
   954	            total += 1  # defaulted → optional, counts toward total only
   955	        elif ctype in dialect.param_required_node_types:
   956	            name = _first_identifier_text(child, source)
   957	            if name in dialect.param_self_names:
   958	                continue
   959	            required += 1
   960	            total += 1
   961	        # else: keyword-only separator / comment / anonymous → ignored
   962	    return required, total, variadic
   963	
   964	
   965	def _extract_ctor_signatures(
   966	    source: bytes, tree: Any, dialect: WiringDialect
   967	) -> dict[str, _CtorSig]:
   968	    """Extract ``{class_name: _CtorSig}`` for classes defining a constructor."""
   969	    if not dialect.constructor_signature_query:
   970	        return {}
   971	    try:
   972	        matches = _run_query_matches(
   973	            dialect.constructor_signature_query, tree, dialect.ts_language_name
   974	        )
   975	    except Exception as exc:
   976	        logger.warning(
   977	            "constructor_signature_query failed for '%s': %s",
   978	            dialect.language, exc,
   979	        )
   980	        return {}
   981	    sigs: dict[str, _CtorSig] = {}
   982	    for captures in matches:
   983	        class_nodes = captures.get("class", [])
   984	        params_nodes = captures.get("params", [])
   985	        if not class_nodes or not params_nodes:
   986	            continue
   987	        cls_name = _node_text(class_nodes[0], source)
   988	        if not cls_name:
   989	            continue
   990	        required, total, variadic = _summarise_params(
   991	            params_nodes[0], source, dialect
   992	        )
   993	        sigs[cls_name] = _CtorSig(
   994	            name=cls_name,
   995	            required=required,
   996	            total=total,
   997	            variadic=variadic,
   998	            lineno=class_nodes[0].start_point[0] + 1,
   999	        )
  1000	    return sigs
  1001	
  1002	
  1003	def _summarise_call_args(
  1004	    args_node: Any, source: bytes, dialect: WiringDialect
  1005	) -> tuple[int, int, bool]:
  1006	    """Count (positional, keyword, splat_present) for a constructor call."""
  1007	    positional = 0
  1008	    keyword = 0
  1009	    splat = False
  1010	    for child in args_node.named_children:
  1011	        ctype = child.type
  1012	        if ctype in dialect.arg_splat_node_types:
  1013	            splat = True
  1014	        elif ctype in dialect.arg_keyword_node_types:
  1015	            keyword += 1
  1016	        else:
  1017	            positional += 1
  1018	    return positional, keyword, splat
  1019	
  1020	
  1021	# ---------------------------------------------------------------------------
  1022	# Per-dialect analysis
  1023	# ---------------------------------------------------------------------------
  1024	
  1025	
  1026	@dataclass
  1027	class _DialectAnalysis:
  1028	    """Internal per-dialect analysis output."""
  1029	
  1030	    dialect: WiringDialect
  1031	    targets_scanned: int = 0
  1032	    symbols_examined: int = 0
  1033	    unwired: list[Finding] = field(default_factory=list)
  1034	    degraded_files: list[str] = field(default_factory=list)
  1035	    mocked: list[Finding] = field(default_factory=list)
  1036	    mocks_ignored: list[Finding] = field(default_factory=list)
  1037	    acceptance_files_scanned: int = 0
  1038	    ctor_arity: list[Finding] = field(default_factory=list)
  1039	    composition_roots_scanned: int = 0
  1040	
  1041	
  1042	def _parse_or_none(source: bytes, dialect: WiringDialect) -> Any | None:
  1043	    """Parse source; ``None`` when the CST is unusable (parse degraded).
  1044	
  1045	    tree-sitter is lenient: syntax errors produce a tree with ERROR nodes
  1046	    rather than raising, so ``root_node.has_error`` is the real signal.
  1047	    """
  1048	    tree = parse_bytes(source, dialect.ts_language_name)
  1049	    if tree is None:
  1050	        return None
  1051	    if tree.root_node.has_error:
  1052	        return None
  1053	    return tree
  1054	
  1055	
  1056	def _analyze_dialect(
  1057	    targets: list[str],
  1058	    worktree: Path,
  1059	    dialect: WiringDialect,
  1060	) -> _DialectAnalysis:
  1061	    """Run UNWIRED_PATH + MOCKED_SEAM for one dialect over authored targets."""
  1062	    out = _DialectAnalysis(dialect=dialect)
  1063	
  1064	    # --- Parse authored targets, extract public symbols -------------------
  1065	    # symbol → (defining file, symbol info)
  1066	    candidates: list[tuple[str, dict[str, Any]]] = []
  1067	    wired_by_dunder_all: set[str] = set()
  1068	    authored_seams: set[str] = set()
  1069	    # First-party constructor signatures authored this turn (CTOR_ARITY).
  1070	    ctor_signatures: dict[str, _CtorSig] = {}
  1071	
  1072	    for rel_path in targets:
  1073	        source = _read_bytes(worktree / rel_path)
  1074	        if source is None:
  1075	            continue
  1076	        out.targets_scanned += 1
  1077	        tree = _parse_or_none(source, dialect)
  1078	        if tree is None:
  1079	            # Parse degraded: skip the target — bias WIRED, never a false
  1080	            # UNWIRED (scope §4.1 step 3 / AC-010).
  1081	            out.degraded_files.append(rel_path)
  1082	            continue
  1083	        wired_by_dunder_all |= _dunder_all_names(source)
  1084	        symbols = _extract_public_symbols(source, tree, dialect)
  1085	        out.symbols_examined += len(symbols)
  1086	        for sym in symbols:
  1087	            candidates.append((rel_path, sym))
  1088	            authored_seams.add(sym["name"])
  1089	        ctor_signatures.update(_extract_ctor_signatures(source, tree, dialect))
  1090	
  1091	    # --- Build reference + registration maps over the worktree ------------
  1092	    # Reference map is per-file so a symbol's own defining file and test
  1093	    # files never count as references (the core "referenced only by its
  1094	    # own tests" detection — scope §4.1 step 5).
  1095	    refs_by_file: dict[str, set[str]] = {}
  1096	    registrations: set[str] = set()
  1097	
  1098	    if candidates:
  1099	        for rel_path in _collect_source_files(worktree, dialect):
  1100	            if _is_test_file(rel_path, dialect):
  1101	                continue
  1102	            source = _read_bytes(worktree / rel_path)
  1103	            if source is None:
  1104	                continue
  1105	            tree = _parse_or_none(source, dialect)
  1106	            if tree is None:
  1107	                continue
  1108	            refs_by_file[rel_path] = _extract_references(source, tree, dialect)
  1109	            registrations |= _extract_registrations(source, tree, dialect)
  1110	
  1111	    manifest = _manifest_text(worktree, dialect)
  1112	    corpus = _build_text_corpus(worktree, dialect) if candidates else []
  1113	
  1114	    # --- Classify ----------------------------------------------------------
  1115	    for defining_file, sym in candidates:
  1116	        name = sym["name"]
  1117	        if name in wired_by_dunder_all:
  1118	            continue  # exported via __all__ — counts as wired
  1119	        if name in registrations:
  1120	            continue  # registered into a composition root
  1121	        if manifest and name in manifest:
  1122	            continue  # named in a script/package manifest
  1123	        if any(
  1124	            name in refs
  1125	            for f, refs in refs_by_file.items()
  1126	            if f != defining_file
  1127	        ):
  1128	            continue  # referenced by a non-test, non-self module
  1129	        if _substring_fallback(name, corpus, defining_file):
  1130	            continue  # biased WIRED on raw-text hit
  1131	        searched_refs = sum(1 for f in refs_by_file if f != defining_file)
  1132	        out.unwired.append(Finding(
  1133	            file=defining_file,
  1134	            symbol=name,
  1135	            kind=sym.get("kind", "symbol"),
  1136	            module=os.path.basename(defining_file),
  1137	            lineno=sym["lineno"],
  1138	            severity="warning",
  1139	            pattern="UNWIRED_PATH",
  1140	            why=(
  1141	                f"Public symbol '{name}' has no non-test reference, no "
  1142	                f"registration, and no manifest entry"
  1143	            ),
  1144	            registration_found=False,
  1145	            searched_refs=searched_refs,
  1146	            dialect=dialect.language,
  1147	            language=dialect.language,
  1148	        ))
  1149	
  1150	    # --- MOCKED_SEAM over acceptance files ---------------------------------
  1151	    # Scans ALL acceptance files in the worktree (not just authored ones):
  1152	    # a pre-existing acceptance test that mocks the authored seam hides the
  1153	    # missing wiring just the same.  The SEAM SET stays authored-only, so
  1154	    # attribution precision is preserved.
  1155	    acceptance_files = [
  1156	        f
  1157	        for f in _collect_source_files(worktree, dialect)
  1158	        if _is_acceptance_file(f, dialect)
  1159	    ]
  1160	    for rel_path in acceptance_files:
  1161	        source = _read_bytes(worktree / rel_path)
  1162	        if source is None:
  1163	            continue
  1164	        tree = _parse_or_none(source, dialect)
  1165	        if tree is None:
  1166	            continue
  1167	        out.acceptance_files_scanned += 1
  1168	        try:
  1169	            captures = _run_query_captures(
  1170	                dialect.mock_call_query, tree, dialect.ts_language_name
  1171	            )
  1172	        except Exception as exc:
  1173	            logger.warning(
  1174	                "mock_call_query failed for '%s': %s", dialect.language, exc
  1175	            )
  1176	            continue
  1177	        for node in captures.get("target", []):
  1178	            raw = _node_text(node, source)
  1179	            target = raw.strip("\"'")
  1180	            if not target:
  1181	                continue
  1182	            lineno = node.start_point[0] + 1
  1183	            base = dict(
  1184	                file=rel_path,
  1185	                kind="MOCKED_SEAM",
  1186	                lineno=lineno,
  1187	                pattern="MOCKED_SEAM",
  1188	                mock_kind="mock",
  1189	                dialect=dialect.language,
  1190	                language=dialect.language,
  1191	            )
  1192	            # Authored-seam attribution runs BEFORE the allowlist: an
  1193	            # authored seam whose name merely embeds an allow-listed string
  1194	            # (e.g. my_requests_handler ⊃ "requests") must still warn —
  1195	            # allowlist-first would be a false-green channel.
  1196	            if target in authored_seams or any(
  1197	                seam in target for seam in authored_seams
  1198	            ):
  1199	                out.mocked.append(Finding(
  1200	                    symbol=target,
  1201	                    severity="warning",
  1202	                    why=f"Acceptance test mocks authored seam: {target}",
  1203	                    authored_this_turn=True,
  1204	                    **base,
  1205	                ))
  1206	            elif any(ext in target for ext in dialect.external_mock_allowlist):
  1207	                out.mocks_ignored.append(Finding(
  1208	                    symbol=target,
  1209	                    severity="info",
  1210	                    why=f"External mock (allow-listed): {target}",
  1211	                    authored_this_turn=False,
  1212	                    **base,
  1213	                ))
  1214	            else:
  1215	                # Third-party, not authored, not allow-listed: surfaced as
  1216	                # info, never dropped (scope §4.2).
  1217	                out.mocked.append(Finding(
  1218	                    symbol=target,
  1219	                    severity="info",
  1220	                    why=f"Mock of non-authored target: {target}",
  1221	                    authored_this_turn=False,
  1222	                    **base,
  1223	                ))
  1224	
  1225	    # --- CTOR_ARITY over composition-root files ----------------------------
  1226	    # Scans ALL composition-root files in the worktree (not just authored
  1227	    # ones): a pre-existing main.py / app-factory that constructs an authored
  1228	    # service with the wrong arity is the FEAT-POC-006 defect just the same.
  1229	    # The SIGNATURE SET stays authored-only, so attribution precision is
  1230	    # preserved and only first-party authored services are checked.
  1231	    if (
  1232	        dialect.constructor_call_query
  1233	        and dialect.constructor_signature_query
  1234	        and ctor_signatures
  1235	    ):
  1236	        comp_root_files = [
  1237	            f
  1238	            for f in _collect_source_files(worktree, dialect)
  1239	            if _is_composition_root(f, dialect) and not _is_test_file(f, dialect)
  1240	        ]
  1241	        for rel_path in comp_root_files:
  1242	            source = _read_bytes(worktree / rel_path)
  1243	            if source is None:
  1244	                continue
  1245	            tree = _parse_or_none(source, dialect)
  1246	            if tree is None:
  1247	                continue
  1248	            out.composition_roots_scanned += 1
  1249	            try:
  1250	                matches = _run_query_matches(
  1251	                    dialect.constructor_call_query, tree, dialect.ts_language_name
  1252	                )
  1253	            except Exception as exc:
  1254	                logger.warning(
  1255	                    "constructor_call_query failed for '%s': %s",
  1256	                    dialect.language, exc,
  1257	                )
  1258	                continue
  1259	            for captures in matches:
  1260	                class_nodes = captures.get("class", [])
  1261	                args_nodes = captures.get("args", [])
  1262	                if not class_nodes or not args_nodes:
  1263	                    continue
  1264	                cls_name = _node_text(class_nodes[0], source)
  1265	                sig = ctor_signatures.get(cls_name)
  1266	                if sig is None:
  1267	                    continue  # not a first-party authored service → skip
  1268	                if sig.variadic:
  1269	                    continue  # *args/**kwargs in __init__ → arity unknowable
  1270	                positional, keyword, call_splat = _summarise_call_args(
  1271	                    args_nodes[0], source, dialect
  1272	                )
  1273	                if call_splat:
  1274	                    continue  # *args/**kwargs at call site → bias OK
  1275	                lineno = class_nodes[0].start_point[0] + 1
  1276	                provided = positional + keyword
  1277	                base = dict(
  1278	                    file=rel_path,
  1279	                    symbol=cls_name,
  1280	                    kind="CTOR_ARITY",
  1281	                    module=os.path.basename(rel_path),
  1282	                    lineno=lineno,
  1283	                    severity="warning",
  1284	                    pattern="CTOR_ARITY",
  1285	                    authored_this_turn=True,
  1286	                    dialect=dialect.language,
  1287	                    language=dialect.language,
  1288	                )
  1289	                if provided < sig.required:
  1290	                    out.ctor_arity.append(Finding(
  1291	                        why=(
  1292	                            f"Composition root constructs '{cls_name}' with "
  1293	                            f"{provided} arg(s) ({positional} positional, "
  1294	                            f"{keyword} keyword) but its __init__ requires "
  1295	                            f"{sig.required} (defined at {sig.lineno})"
  1296	                        ),
  1297	                        **base,
  1298	                    ))
  1299	                elif positional > sig.total:
  1300	                    out.ctor_arity.append(Finding(
  1301	                        why=(
  1302	                            f"Composition root constructs '{cls_name}' with "
  1303	                            f"{positional} positional arg(s) but its __init__ "
  1304	                            f"accepts at most {sig.total} (defined at "
  1305	                            f"{sig.lineno})"
  1306	                        ),
  1307	                        **base,
  1308	                    ))
  1309	
  1310	    return out
  1311	
  1312	
  1313	# ---------------------------------------------------------------------------
  1314	# Public API
  1315	# ---------------------------------------------------------------------------
  1316	
  1317	
  1318	def analyze_wiring(
  1319	    authored_files: list[str],
  1320	    worktree_path: str | Path,
  1321	    task_type: str,
  1322	    stack: Any = None,
  1323	) -> dict[str, Any] | None:
  1324	    """Analyze wiring for the files authored this turn.
  1325	
  1326	    Parameters
  1327	    ----------
  1328	    authored_files:
  1329	        Worktree-relative paths authored this turn (the authored set per
  1330	        scope §4: ``files_authored`` else ``files_created ∪ files_modified``).
  1331	    worktree_path:
  1332	        Path to the worktree root.
  1333	    task_type:
  1334	        Only ``FEATURE`` / ``REFACTOR`` / ``INTEGRATION`` are analyzed
  1335	        (case-insensitive); other task types legitimately produce
  1336	        un-wired stubs and return ``None``.
  1337	    stack:
  1338	        Optional object with a ``language`` attribute (e.g. a factory
  1339	        ``StackProfile``); used for dialect dispatch and
  1340	        unsupported-stack detection.  When absent, languages are inferred
  1341	        from authored file extensions — ALL matching dialects run
  1342	        (polyglot, AC-021).
  1343	
  1344	    Returns
  1345	    -------
  1346	    dict | None
  1347	        The §5.1 result dict (see module docstring), or ``None`` when the
  1348	        probe legitimately did not run (task-type gate; zero authored
  1349	        non-test source targets).  Unexpected exceptions are caught and
  1350	        reported as ``status: "error"`` — fail-open to absent-signal,
  1351	        never a crash at the Coach seam.
  1352	    """
  1353	    try:
  1354	        return _analyze_wiring_impl(
  1355	            authored_files, Path(worktree_path), task_type, stack
  1356	        )
  1357	    except Exception as exc:  # noqa: BLE001 — fail-open by contract
  1358	        logger.warning("analyze_wiring failed unexpectedly: %s", exc, exc_info=True)
  1359	        return {
  1360	            "status": "error",
  1361	            "error": str(exc),
  1362	            "dialect": None,
  1363	            "language": "",
  1364	            "dialects": [],
  1365	            "languages": [],
  1366	            "targets_scanned": 0,
  1367	            "symbols_examined": 0,
  1368	            "findings": [],
  1369	            "degraded_files": [],
  1370	            "mocked_seam": MockSeamResult(
  1371	                status="error", ran=False, skip_reason="analyzer error"
  1372	            ).to_dict(),
  1373	            "ctor_arity": CtorArityResult(
  1374	                status="error", ran=False, skip_reason="analyzer error"
  1375	            ).to_dict(),
  1376	        }
  1377	
  1378	
  1379	def _unsupported_stack_dict(language: str) -> dict[str, Any]:
  1380	    """The unsupported-stack absent-signal result (never a pass — AC-009)."""
  1381	    return {
  1382	        "status": "unsupported_stack",
  1383	        "dialect": None,
  1384	        "language": language,
  1385	        "dialects": [],
  1386	        "languages": [language] if language else [],
  1387	        "targets_scanned": 0,
  1388	        "symbols_examined": 0,
  1389	        "findings": [],
  1390	        "degraded_files": [],
  1391	        "mocked_seam": MockSeamResult(
  1392	            status="unsupported_stack",
  1393	            ran=False,
  1394	            skip_reason=f"no dialect for language '{language}'",
  1395	        ).to_dict(),
  1396	        "ctor_arity": CtorArityResult(
  1397	            status="unsupported_stack",
  1398	            ran=False,
  1399	            skip_reason=f"no dialect for language '{language}'",
  1400	        ).to_dict(),
  1401	    }
  1402	
  1403	
  1404	def _analyze_wiring_impl(
  1405	    authored_files: list[str],
  1406	    worktree: Path,
  1407	    task_type: str,
  1408	    stack: Any,
  1409	) -> dict[str, Any] | None:
  1410	    # --- Task-type gate (AC-008) -------------------------------------------
  1411	    if (task_type or "").upper() not in _ANALYZED_TASK_TYPES:
  1412	        return None
  1413	
  1414	    stack_language: str | None = None
  1415	    if stack is not None and getattr(stack, "language", None):
  1416	        stack_language = str(stack.language)
  1417	
  1418	    # --- Select candidate dialects: every registered dialect with ≥1
  1419	    # authored, non-test target (polyglot — AC-021) -------------------------
  1420	    candidates: list[tuple[WiringDialect, list[str]]] = []
  1421	    for dialect in iter_dialects():
  1422	        targets = [
  1423	            f
  1424	            for f in authored_files
  1425	            if _matches_glob(f, dialect.file_globs)
  1426	            and not _is_test_file(f, dialect)
  1427	            and (worktree / f).is_file()
  1428	        ]
  1429	        if targets:
  1430	            candidates.append((dialect, targets))
  1431	
  1432	    if not candidates:
  1433	        # Stack explicitly names a language we have no dialect for →
  1434	        # absent-signal, never a silent pass (AC-009).
  1435	        if stack_language is not None:
  1436	            resolved = _find_language(stack_language)
  1437	            if resolved is None or get_dialect(resolved) is None:
  1438	                return _unsupported_stack_dict(stack_language)
  1439	            return None  # dialect exists; zero authored targets → probe didn't run
  1440	        # No stack: a known-but-undialected source extension is still an
  1441	        # absent-signal, not a silent None.
  1442	        for f in authored_files:
  1443	            ext = os.path.splitext(f)[1].lower()
  1444	            if ext in _KNOWN_UNDIALECTED_EXTENSIONS:
  1445	                return _unsupported_stack_dict(_KNOWN_UNDIALECTED_EXTENSIONS[ext])
  1446	        return None  # zero authored source targets → probe didn't run
  1447	
  1448	    # --- Run every matching dialect ----------------------------------------
  1449	    analyses = [
  1450	        _analyze_dialect(targets, worktree, dialect)
  1451	        for dialect, targets in candidates
  1452	    ]
  1453	
  1454	    # --- Merge --------------------------------------------------------------
  1455	    languages = [a.dialect.language for a in analyses]
  1456	    primary = languages[0]
  1457	    if stack_language is not None:
  1458	        resolved = _find_language(stack_language)
  1459	        if resolved in languages:
  1460	            primary = resolved
  1461	
  1462	    degraded = [f for a in analyses for f in a.degraded_files]
  1463	    status: WiringStatus = "parse_degraded" if degraded else "complete"
  1464	
  1465	    wiring = WiringResult(
  1466	        status=status,
  1467	        dialect=primary,
  1468	        language=primary,
  1469	        dialects=languages,
  1470	        languages=languages,
  1471	        targets_scanned=sum(a.targets_scanned for a in analyses),
  1472	        symbols_examined=sum(a.symbols_examined for a in analyses),
  1473	        findings=[f for a in analyses for f in a.unwired],
  1474	        degraded_files=degraded,
  1475	    )
  1476	
  1477	    acceptance_scanned = sum(a.acceptance_files_scanned for a in analyses)
  1478	    mocked = MockSeamResult(
  1479	        status="ran" if acceptance_scanned else "skipped_no_acceptance_files",
  1480	        ran=bool(acceptance_scanned),
  1481	        skip_reason=None if acceptance_scanned else "no acceptance files found",
  1482	        dialect=primary,
  1483	        language=primary,
  1484	        findings=[f for a in analyses for f in a.mocked],
  1485	        external_mocks_ignored=[f for a in analyses for f in a.mocks_ignored],
  1486	    )
  1487	
  1488	    comp_scanned = sum(a.composition_roots_scanned for a in analyses)
  1489	    ctor = CtorArityResult(
  1490	        status="ran" if comp_scanned else "skipped_no_composition_root",
  1491	        ran=bool(comp_scanned),
  1492	        skip_reason=None if comp_scanned else "no composition root found",
  1493	        dialect=primary,
  1494	        language=primary,
  1495	        composition_roots_scanned=comp_scanned,
  1496	        findings=[f for a in analyses for f in a.ctor_arity],
  1497	    )
  1498	
  1499	    result = wiring.to_dict()
  1500	    result["mocked_seam"] = mocked.to_dict()
  1501	    result["ctor_arity"] = ctor.to_dict()
  1502	    return result

