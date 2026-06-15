"""Cross-repo BDD-contract seam test for the guardkit↔guardkitfactory seam.

TASK-INFRA-BDDSEAM01 (recurrence-prevention follow-up to TASK-FIX-BDDFW01).
This module is the **CI enforcement** for the migrated-contract-boundary
meta-rule documented in ``.claude/rules/namespace-hygiene.md`` and the
absent-signal family (``.claude/rules/absence-of-failure-is-not-success.md``,
``.claude/rules/evidence-boundary-narrower-than-write-surface.md``): a local
decision (the Coach's BDD bridge) that depends on an externally-defined
contract (``guardkitfactory.bdd``) across the repo split needs that contract
audited against the **real installed** package by a fast CI guard.

It is the direct analogue of the harness ``cancel()`` seam test in the sibling
module ``test_xrepo_contract_seam.py`` (TASK-INFRA-XREPOCONTRACT) — same idiom,
same merge-gating ``.github/workflows/seam-tests.yml`` job, different boundary.

Why this test exists
--------------------

TASK-FIX-BDDFW01 (commit ``0e4b7912``, 2026-06-15) found the Coach BDD-factory
bridge had been **silently dead for days**: production
(``guardkit/orchestrator/quality_gates/coach_validator.py``) targeted a STALE
``guardkitfactory`` contract — a one-arg ``discover(stack)`` /
``plugin.run(worktree)`` shape and an abandoned ``BDDRunResult`` field set.
Every call on the live path raised ``TypeError``/``AttributeError``, which the
production ``except Exception`` swallowed, degrading to the legacy
Player-reported fallback. The autobuild loop never visibly failed — a textbook
absent-signal false-green (a *dead* bridge reads identically to a *fallback*
bridge from outside).

Worse, a per-component diagnosis of BDDFW01 missed a **4th** mismatch
(``plugin.run`` arity); it was only caught by hand-verifying against the real
installed package. There was **no executable guard** that asserts the
orchestrator's actual calls into ``guardkitfactory.bdd`` agree with the real
installed signatures. A future ``BDDRunResult`` field rename, a
``discover``/``run`` arity change, or a ``StackProfile`` field change would
silently re-break the bridge with zero visible failure. This module is that
guard.

The four contracts pinned here (each is a real production call site):

1. ``discover(stack, worktree)`` — 2 positional params.
   Production: ``coach_validator.py`` ``_run_factory_bdd`` →
   ``plugin = discover(stack_profile, worktree_path)``.
2. ``BDDPlugin.run(self, scenarios, task_id, worktree, *, timeout_seconds=...)``.
   Production: ``result = plugin.run([], task_id, worktree_path)``.
3. ``BDDRunResult`` exposes every field ``map_bdd_run_result`` reads:
   ``scenarios_attempted``/``passed``/``failed``/``skipped``/``errored``,
   ``duration_seconds``, ``raw_report_path``, ``discoveries``, ``errors``.
4. ``StackProfile`` exposes every field ``_detect_stack_profile`` constructs:
   ``language``, ``test_framework``, ``package_manager``, ``project_root``,
   ``extras``.

Scope and execution
-------------------

* Marked ``@pytest.mark.seam`` (technology-boundary integration). The CI job
  ``.github/workflows/seam-tests.yml`` checks out the sibling guardkitfactory
  repo, installs both packages, and runs the seam-test modules by explicit
  path (a whole-tree ``-m seam`` sweep aborts on SDK-dependent modules that
  ``import claude_agent_sdk`` at collection time, e.g. ``test_sdk_harness.py``).
* ``pytest.importorskip("guardkitfactory.bdd")`` at module load makes the
  whole module **skip cleanly** in a bare guardkit dev venv that has not
  installed the ``[autobuild]`` extra. This is the "skippable locally"
  contract — opt-in for the CI job that has the real cross-repo stack, never a
  hard failure for a contributor working on an unrelated part of guardkit.
* ``inspect`` / ``dataclasses`` only. No subprocess, no live BDD run, no LLM.
  Runs in milliseconds. Exercising a live BDD run is TASK-HMIG-BDDWIRE's remit,
  not this contract guard's.

A note on subset vs exact field-set semantics
---------------------------------------------

The ``BDDRunResult`` / ``StackProfile`` assertions check that every field the
orchestrator *reads/constructs* is **present** (a subset relation), not that
the dataclass has *exactly* those fields. This is deliberate: the drift that
breaks production is a field being **removed or renamed** (the mapper's
attribute access raises ``AttributeError``) — a subset check catches that and
goes red. An *additive* field on the factory side does not break the mapper, so
failing on it would be a false-red in a merge-gating job (cf.
``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` on avoiding
false-reds). The harness seam test uses the same subset idiom
(``missing = expected - params``).
"""

from __future__ import annotations

import dataclasses
import inspect

import pytest

# Skip the entire module unless the real cross-repo BDD stack is installed.
# ``guardkitfactory.bdd`` does NOT pull in langchain (unlike
# ``guardkitfactory.harness``), so this is a lighter import than the sibling
# harness seam test — but the skip contract is identical: bare guardkit dev venv
# skips, the seam-tests CI job (sibling repo installed) runs.
guardkitfactory_bdd = pytest.importorskip(
    "guardkitfactory.bdd",
    reason=(
        "guardkitfactory not installed; this seam test runs in the seam-tests "
        "CI job (pip install -e ../guardkitfactory). Install the autobuild "
        "extra locally to run it: pip install -e ../guardkitfactory"
    ),
)

pytestmark = [pytest.mark.seam, pytest.mark.integration]

# Public surface the orchestrator imports
# (``from guardkitfactory.bdd import BDDRunResult, discover``;
#  ``from guardkitfactory.bdd.plugin import StackProfile``). Bound from the
# imported module object so a removed/renamed export fails loudly at access.
discover = guardkitfactory_bdd.discover
BDDPlugin = guardkitfactory_bdd.BDDPlugin
BDDRunResult = guardkitfactory_bdd.BDDRunResult
StackProfile = guardkitfactory_bdd.StackProfile

# The exact field set ``map_bdd_run_result`` reads from a ``BDDRunResult``
# (coach_validator.py: ``map_bdd_run_result``). If guardkitfactory drops or
# renames any of these, the mapper's attribute access raises and the bridge
# silently falls back — this set is the contract that keeps it honest.
_BDD_RUN_RESULT_FIELDS_READ_BY_MAPPER = frozenset(
    {
        "scenarios_attempted",
        "scenarios_passed",
        "scenarios_failed",
        "scenarios_skipped",
        "scenarios_errored",
        "duration_seconds",
        "raw_report_path",
        "discoveries",
        "errors",
    }
)

# The exact field set ``_detect_stack_profile`` constructs a ``StackProfile``
# with (coach_validator.py: ``_detect_stack_profile`` →
# ``StackProfile(language=, test_framework=, package_manager=, project_root=,
# extras=)``).
_STACK_PROFILE_FIELDS_CONSTRUCTED = frozenset(
    {
        "language",
        "test_framework",
        "package_manager",
        "project_root",
        "extras",
    }
)


# ----------------------------------------------------------------------
# Contract 1: discover(stack, worktree) — 2 positional params
# ----------------------------------------------------------------------


class TestDiscoverArity:
    """``guardkitfactory.bdd.discover`` keeps the 2-positional shape.

    Production (``coach_validator.py`` ``_run_factory_bdd``) calls
    ``discover(stack_profile, worktree_path)`` positionally. The stale contract
    BDDFW01 fixed was a one-arg ``discover(stack)``; this pins the corrected
    two-arg shape so the regression cannot recur silently.
    """

    def test_discover_takes_stack_and_worktree_positionally(self) -> None:
        params = list(inspect.signature(discover).parameters.values())
        positional = [
            p
            for p in params
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        names = [p.name for p in positional]
        assert names == ["stack", "worktree"], (
            "guardkitfactory.bdd.discover must take exactly 2 positional "
            f"params (stack, worktree); got positional params {names}. "
            "coach_validator._run_factory_bdd calls "
            "discover(stack_profile, worktree_path) positionally — the stale "
            "one-arg discover(stack) shape is the TASK-FIX-BDDFW01 regression."
        )


# ----------------------------------------------------------------------
# Contract 2: BDDPlugin.run(self, scenarios, task_id, worktree, *, timeout_seconds=...)
# ----------------------------------------------------------------------


class TestBDDPluginRunSignature:
    """``BDDPlugin.run`` keeps the ``(scenarios, task_id, worktree, *, timeout_seconds)`` shape.

    Production calls ``plugin.run([], task_id, worktree_path)`` — three
    positional args after ``self``, ``timeout_seconds`` left to its default.
    The 4th mismatch BDDFW01's per-component diagnosis missed was exactly this
    ``run`` arity, so it is pinned explicitly.
    """

    def test_run_leading_positional_params_in_order(self) -> None:
        params = list(inspect.signature(BDDPlugin.run).parameters.values())
        positional = [
            p.name
            for p in params
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        assert positional == ["self", "scenarios", "task_id", "worktree"], (
            "BDDPlugin.run must take positional params "
            "(self, scenarios, task_id, worktree); got "
            f"{positional}. coach_validator._run_factory_bdd calls "
            "plugin.run([], task_id, worktree_path)."
        )

    def test_run_timeout_seconds_is_keyword_only_with_default(self) -> None:
        params = inspect.signature(BDDPlugin.run).parameters
        assert "timeout_seconds" in params, (
            "BDDPlugin.run dropped `timeout_seconds`; production relies on its "
            "default (run is called without it: plugin.run([], task_id, "
            "worktree_path))."
        )
        timeout = params["timeout_seconds"]
        assert timeout.kind is inspect.Parameter.KEYWORD_ONLY, (
            "BDDPlugin.run `timeout_seconds` must be keyword-only "
            f"(after a bare *); got kind={timeout.kind.name}."
        )
        assert timeout.default is not inspect.Parameter.empty, (
            "BDDPlugin.run `timeout_seconds` must have a default; production "
            "calls run() without supplying it."
        )


# ----------------------------------------------------------------------
# Contract 3: BDDRunResult exposes every field the mapper reads
# ----------------------------------------------------------------------


class TestBDDRunResultFields:
    """``BDDRunResult`` exposes every field ``map_bdd_run_result`` reads.

    A removed/renamed field is the drift that broke the bridge in BDDFW01: the
    mapper's attribute access raises ``AttributeError``, the production
    ``except Exception`` swallows it, and the bridge degrades to the legacy
    fallback with no visible failure (absent-signal false-green).
    """

    def test_bdd_run_result_is_a_dataclass(self) -> None:
        assert dataclasses.is_dataclass(BDDRunResult), (
            "BDDRunResult must be a dataclass — map_bdd_run_result and this "
            "guard rely on dataclasses.fields()."
        )

    def test_bdd_run_result_exposes_all_mapper_fields(self) -> None:
        actual = {f.name for f in dataclasses.fields(BDDRunResult)}
        missing = _BDD_RUN_RESULT_FIELDS_READ_BY_MAPPER - actual
        assert not missing, (
            f"BDDRunResult dropped/renamed field(s) {sorted(missing)} that "
            "coach_validator.map_bdd_run_result reads. This is the "
            "TASK-FIX-BDDFW01 class of drift — the mapper's attribute access "
            "would raise AttributeError and the bridge would silently fall "
            f"back. Installed fields: {sorted(actual)}."
        )


# ----------------------------------------------------------------------
# Contract 4: StackProfile exposes every field _detect_stack_profile constructs
# ----------------------------------------------------------------------


class TestStackProfileFields:
    """``StackProfile`` exposes every field ``_detect_stack_profile`` constructs.

    The stale contract returned a bare profile *string*; the corrected bridge
    builds a real ``StackProfile`` dataclass that ``discover`` consumes. A
    removed/renamed field here makes the production ``StackProfile(...)``
    constructor raise ``TypeError``, swallowed into the same silent fallback.
    """

    def test_stack_profile_is_a_dataclass(self) -> None:
        assert dataclasses.is_dataclass(StackProfile), (
            "StackProfile must be a dataclass — _detect_stack_profile "
            "constructs it by keyword and this guard reads dataclasses.fields()."
        )

    def test_stack_profile_exposes_all_constructed_fields(self) -> None:
        actual = {f.name for f in dataclasses.fields(StackProfile)}
        missing = _STACK_PROFILE_FIELDS_CONSTRUCTED - actual
        assert not missing, (
            f"StackProfile dropped/renamed field(s) {sorted(missing)} that "
            "coach_validator._detect_stack_profile constructs by keyword "
            "(StackProfile(language=, test_framework=, package_manager=, "
            "project_root=, extras=)). The production constructor would raise "
            f"TypeError. Installed fields: {sorted(actual)}."
        )
