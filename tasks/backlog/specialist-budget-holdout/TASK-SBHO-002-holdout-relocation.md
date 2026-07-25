---
complexity: 5
dependencies: []
feature_id: FEAT-SBHO
id: TASK-SBHO-002
implementation_mode: task-work
status: backlog
task_type: feature
title: Hold-out relocation — coach dossier out of the shared worktree
wave: 1
---

# Hold-out relocation — coach dossier out of the shared worktree

The Player runs with unrestricted Read/Grep/Bash in the shared worktree
(agent_invoker.py:2077) where the orchestrator writes the FULL coach evidence dossier
coach_evidence_turn_{turn}.json (autobuild.py:6766-6787) and the full verdict
coach_turn_{turn}.json (coach_output_parser.py + paths.py:86). That leaks the judge's
evidence to the judged. Relocate per the ruled Dive-3 change set (ai-transition
docs/verification-deep-dives-dossier-2026-07-25.md): both files move to an
orchestrator-private dir OUTSIDE the worktree
(<repo-root>/.guardkit/autobuild-private/{task_id}/); the worktree keeps ONLY the
Player-facing coach_feedback file; oracle-failure feedback names the scenario/AC id not
the oracle file path. One accessor in paths.py owns the private path — no scattered
literals; readers get a backward-compatible legacy-location fallback with a log line.
Binding spec: docs/specialist-budget-and-holdout-scope-and-buildplan.md §3 (including
the honest-cap comment requirement). Do NOT touch _build_coach_prompt content,
coach_output_parser parse logic, or grammars — only file-path seams.

## Acceptance Criteria
- [ ] After a simulated coach turn (hermetic), worktree/.guardkit/autobuild/{task_id}/ contains NO coach_evidence_* and NO coach_turn_* file; the private dir contains both; the coach_feedback file remains in the worktree and round-trips through load_coach_feedback unchanged
- [ ] All readers (shadow mode qav_shadow, COACHSF01 safety net, review summary, replay/resume paths) resolve via the single paths.py accessor; a legacy-located file is still readable via the fallback and logs the fallback line
- [ ] Player-facing feedback text contains no worktree-relative oracle file paths (scenario/AC id instead); the Player prompt hands the Player no coach-artifact path other than the feedback file
- [ ] The honest-cap comment (relocation removes the casual read, not a determined process; full enforcement = the sandbox lane) is present at the write seam; zero net-new failures on the existing suite
