# Specialist-prompt budget + hold-out relocation — scope + buildplan (FEAT-SBHO)
## 2026-07-25 night · the two small guardkit lanes combined per the handoff §3.1 · binding spec

## 1. Why (receipts)

- **Specialist budget:** the FEAT-8AD1 merge (`58bc42b6`) filed this follow-up verbatim:
  *"the code-reviewer specialist prompt is a SEPARATE seam (3 live overflow receipts,
  advisory/non-fatal) — same budget owed, its own small lane."* No task was ever filed —
  this build files and closes it.
- **Hold-out relocation:** ruled by Rich from the verification research
  (ai-transition `docs/verification-deep-dives-dossier-2026-07-25.md` Dive 3): the Player
  can currently read the full Coach evidence dossier out of the shared worktree —
  `coach_evidence_turn_{turn}.json` is written to
  `worktree/.guardkit/autobuild/{task_id}/` (`autobuild.py:6766-6787`) and the Player runs
  with unrestricted Read/Grep/Bash in that worktree (`agent_invoker.py:2077`). Measures M2.

## 2. Fix A — budget the specialist/advisory prompt seams (TASK-SBHO-001)

Mirror the `_trim_synthesis_prompt` pattern (`agent_invoker.py:3402-3665`: env-tunable
char ceiling, protected markers, loud in-prompt truncation notice + WARNING log, degrade
never raise) onto the two unbudgeted seams:

1. `guardkit/qa/review_seat.py::build_seat_messages` (:319-338): the assembled
   system+user payload has NO overall budget today (only the diff is capped at 60k via
   `render_payload_for_seat`; `repo_context` is uncapped). Add
   `GUARDKIT_REVIEW_SEAT_MAX_CHARS` (default 300000) bounding the ASSEMBLED user
   message; trim `repo_context` first, then the diff tail; never trim the instruction
   header or the finding-schema section. Advisory posture unchanged (never raises,
   never blocks — `run_advisory_review` :711-799 contract intact).
2. `guardkit/orchestrator/specialist_invocations.py::_build_code_reviewer_prompt`
   (:886-936): keep the existing ~2000-char seed cap, and add the same env-tunable
   overall bound as a backstop (`GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS`, default 300000)
   applied to the final prompt string for ALL specialist builders in this module
   (code-reviewer, test-orchestrator runner), with the loud-marker convention.

## 3. Fix B — hold-out relocation (TASK-SBHO-002), the Dive-3 named set

1. **(S)** `coach_evidence_turn_{turn}.json` moves OUT of the worktree to an
   orchestrator-private dir: `<repo-root>/.guardkit/autobuild-private/{task_id}/`
   (host-side, sibling of the worktree root, never inside `worktree.path`). Writer:
   `autobuild.py:6766-6787`. All readers (shadow mode, receipts, review summary) follow
   the new path via one accessor in `guardkit/orchestrator/paths.py` — no scattered
   literals.
2. **(M)** `coach_turn_{turn}.json` (the full verdict) moves to the same private dir.
   The worktree keeps ONLY the designed Player-facing feedback file
   (`coach_feedback_*.json`), which already carries the redacted
   issue/location/suggestion view (`_write_coach_feedback`, `agent_invoker.py:7164-7198`).
   `coach_output_parser.extract_and_write` writes to the private dir; the COACHSF01
   safety net and `load_coach_feedback` keep working (update their path resolution via
   the same accessor).
3. **(S)** Oracle-failure feedback names the scenario/AC id, not the oracle file path
   (strip worktree-relative oracle paths from Player-facing feedback text).
4. Player prompt text: remove any references that hand the Player coach-artifact paths
   beyond the feedback file.

**Honest cap (from Dive 3, restated):** this removes the casual read and the path hint,
not a determined process — the Player's Bash is unrestricted at the host. Full
enforcement is a separate sandbox lane. Say so in code comments at the seam.

**Compat law:** backward-compatible READ fallback — if a legacy-located file exists and
the private one doesn't (old runs, replays), readers fall back with a log line. Fresh
writes always go private.

## 4. Done means

- Both lane suites green + zero net-new failures vs main.
- Hermetic tests: (a) an oversized review-seat payload renders under the budget with the
  loud marker and untouched instruction header; (b) a specialist prompt over the ceiling
  is bounded; (c) after a simulated coach turn, `worktree/.guardkit/autobuild/{task}/`
  contains NO `coach_evidence_*` or `coach_turn_*` file, the private dir contains both,
  and the feedback file still round-trips through `load_coach_feedback`; (d) the legacy
  read-fallback fires with its log line.
- Advisory/non-fatal behaviour of the review seat and specialist results is unchanged.

## 5. Fences

Normal topology. No changes to the coach contract surfaces (FEAT-CV4M owns those; this
build must not touch `_build_coach_prompt`, `coach_output_parser` parse logic, or
grammars beyond the file-path seam in §3.2).
