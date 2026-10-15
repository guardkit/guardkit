---
id: TASK-AB-NOCHANGE01
title: The build says "nothing happened" and stops, instead of running out of turns
status: completed
task_type: bugfix
created: 2026-09-01
completed: 2026-09-01
completed_location: tasks/completed/2026-09/
record_filed: 2026-10-15
record_provenance: reconstructed-after-the-fact
implementing_commits:
  - 28e578fb86484171af4c2c5882fafc640ff69e88
  - dd2fd7a0b0d36ccfdc339cdefc4bb3263356f448
  - 34dd301ea449eeabc6c0b75cbf123e583773b74a
  - f1c90709599fc79435042f81c7e4a55a1ff2749c
tags: [autobuild, stall, no-file-changes, filed-after-the-fact]
---

> **Filed after the fact, on 2026-10-15.** The work shipped on 2026-09-01 in the
> four commits listed above. Comments and log lines in
> `guardkit/orchestrator/autobuild.py` name it `TASK-AB-NOCHANGE01`, but no task
> record was ever written, so the lint
> `tests/rules/test_no_dead_task_id_references.py` failed. This record is
> written from those commits and the code; it is not a plan written in advance.

# The build says "nothing happened" and stops

## What went wrong

Two builds in the 2026-08-30 architecture exam (FEAT-245E and FEAT-B0EF, each on
its second task) changed no files on any turn. In one the task could not be done
as written; in the other the work was already in the file. Each time the
generator claimed edits that git showed had never happened, and the loop ran out
of turns and reported `max_turns_exceeded` after about 25 minutes. That message
named the symptom, not the cause.

## What changed

- The loop measures with git whether a turn changed anything: a snapshot of the
  worktree before the generator runs and another after the generator and the
  orchestrator's own specialists finish. Orchestrator bookkeeping and test-run
  leftovers are ignored; a measurement git could not take stays absent and is
  never read as zero (commit `28e578fb`).
- No files changed for three turns running, with no approval, now ends the task
  as `unrecoverable_stall` with the label `no_file_changes_stall`. The message
  says in plain words that nothing was written, what the reviewer last asked
  for, and the two usual reasons: the work is already there, or the task cannot
  be done as written.
- A second part let a zero-change turn finish the task when the reviewer's own
  test run was green. It was tightened the same day (commit `dd2fd7a0`) and then
  withdrawn (commit `f1c90709`), because it could finish a task the reviewer had
  just refused. The same commit made a same-size edit count as a change. The
  stall itself stands.

## Where the tests are

`tests/unit/test_no_file_changes_stall.py`, plus the simulated generators in
`tests/integration/quality_gates/`, which now write the files they say they
wrote (commit `34dd301e`).
