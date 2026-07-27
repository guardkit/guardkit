"""FEAT-SCG-003 — history proofs + the two permanent regression pins.

Two parts, per the buildplan §5:

1. **Would-have-fired proofs.** Three tests that drive the SCG-001 *executor*
   with rules reconstructing each of the 2026-07-26 drifts in its PRE-FIX shape
   and assert each yields the blocking (``status == "failed"``) verdict with an
   actionable detail a local Player could act on:

   * **CV4M** (fix ``041098ad``) — a ``byte_parity`` rule over a fixture pair
     reproducing the fenced-output divergence (authority = the corpus/raw-JSON
     contract, subject = the divergent prompt block that re-taught a ```json
     fence and extra keys).
   * **SBHO** (fix ``4a37bacc``) — an ``assert_command`` rule whose command
     checks path containment and fails for a worktree-INSIDE ``task_private_dir``
     resolution (the pre-fix "rename, not relocation" shape).
   * **CMIR-003** (fix ``33ed5e0a``) — a ``token_coverage`` rule requiring the
     config-tier tokens + ``unique_token`` (max 1) for ``GUARDKIT_COACH_CONTRACT``
     + ``require_test_tokens``, failing against a reconstruction of the pre-fix
     two-env-only-resolvers shape (fixture files, not the real tree).

2. **Permanent regression pins** closing today's still-open live holes:

   * **Provenance pin (CV4M).** The authoritative v4 Decision Format bytes are
     vendored as a guardkit golden with a dated provenance header naming the adf
     source (``tests/fixtures/coach-contract/v4_decision_format.golden.txt``).
     A test asserts the rendered block ``agent_invoker._V4_DECISION_FORMAT_BLOCK``
     is byte-identical to the golden's payload (header excluded via a clear
     delimiter) — so editing the prompt and its fixture together can no longer
     stay green. See ``TestProvenancePin`` for the recorded trailing-newline
     divergence and how it is pinned.
   * **Containment pin (SBHO).** A test builds a worktree-SHAPED root
     (``<tmp>/.guardkit/worktrees/<id>``) and asserts
     ``TaskArtifactPaths.task_private_dir`` resolves OUTSIDE that worktree — the
     invariant the plain-``tmp_path`` tests structurally cannot see.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.quality_gates.spec_conformance import (
    evaluate,
    parse_conformance_block,
)

# Fixtures live under tests/fixtures/coach-contract (three levels up from
# tests/unit/orchestrator/quality_gates/).
_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "coach-contract"
_GOLDEN_FILE = _FIXTURES_DIR / "v4_decision_format.golden.txt"

# The delimiter line separating the provenance header from the verbatim payload
# in the golden. Must match tests/fixtures/coach-contract/v4_decision_format.golden.txt.
_GOLDEN_PAYLOAD_DELIMITER = (
    "=====8<===== PAYLOAD (verbatim adf V4_DECISION_FORMAT bytes) "
    "— do not add or remove bytes below =====8<====="
)


def _golden_payload() -> str:
    """Return the verbatim adf payload from the golden (header excluded).

    Everything strictly after the delimiter line is the payload — byte-for-byte
    the vendored ``V4_DECISION_FORMAT`` string, including its trailing newline.
    """
    raw = _GOLDEN_FILE.read_text(encoding="utf-8")
    _header, payload = raw.split(_GOLDEN_PAYLOAD_DELIMITER + "\n", 1)
    return payload


# ===========================================================================
# 1. Would-have-fired proofs (drive the executor with pre-fix reconstructions)
# ===========================================================================


class TestWouldHaveFired_CV4M:
    """CV4M: the v4 Decision Format block re-taught fenced output + extra keys.

    The Player byte-compared against its OWN divergent fixture (both sides
    editable together). A ``byte_parity`` rule whose authority is captured out
    of reach turns the fence re-teach into a blocking failure with a diff.
    """

    def test_fence_reteach_yields_blocking_diff(self, tmp_path: Path) -> None:
        # Authority (captured pre-build, out of the Player's reach): the raw-JSON
        # contract from the training corpus — no fence, exactly two keys.
        authority = (
            "## Decision Format\n\n"
            "Respond with the verdict as a SINGLE RAW JSON object — no ```json "
            "fence, no code fence of any kind, no prose before or after it.\n\n"
            '{"verdict": "approve" | "reject", "findings": [...]}\n\n'
            "- No other keys: no class, no task_id, no rationale — the two keys "
            "above are the entire contract.\n"
        )
        # Subject (the pre-fix drift): re-teaches a fenced code block and adds
        # the extra keys the fix later removed.
        subject = (
            "## Decision Format\n\n"
            "Respond with the verdict inside a fenced ```json code block so the "
            "orchestrator can parse it.\n\n"
            '```json\n'
            '{"verdict": "approve", "class": "...", "task_id": "...", '
            '"rationale": "...", "findings": [...]}\n'
            '```\n'
        )
        subject_path = tmp_path / "src" / "coach_prompt.txt"
        subject_path.parent.mkdir(parents=True)
        subject_path.write_text(subject)

        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "CV4M",
                        "type": "byte_parity",
                        "authority": "corpus/decision_format.golden.txt",
                        "subject": "src/coach_prompt.txt",
                    }
                ]
            }
        )
        # The snapshot supplies the authority bytes (never the live authority).
        result = evaluate(block, {"CV4M": authority.encode("utf-8")}, tmp_path)

        assert result["status"] == "failed"
        (failure,) = result["failures"]
        assert failure["rule_id"] == "CV4M"
        assert failure["kind"] == "byte_parity"
        detail = failure["detail"]
        # Actionable: a unified diff naming the fence re-teach and the extra keys.
        assert "@@" in detail
        assert "```json" in detail
        assert "rationale" in detail
        # And it tells the Player the authority side is out of reach.
        assert "cannot be changed" in detail


class TestWouldHaveFired_SBHO:
    """SBHO: task_private_dir resolved INSIDE the shared worktree (rename, not
    relocation). The AC test passed a plain ``tmp_path`` root, so broken and
    correct code resolved identically. An ``assert_command`` containment check,
    exercised under a realistic (worktree-shaped) root, turns the pre-fix
    worktree-INSIDE resolution into a blocking failure.
    """

    def test_worktree_inside_resolution_yields_blocking_failure(
        self, tmp_path: Path
    ) -> None:
        task_id = "TASK-SBHO-HIST"
        # A realistic worktree root: <root>/.guardkit/worktrees/<id>.
        worktree = tmp_path / ".guardkit" / "worktrees" / task_id
        worktree.mkdir(parents=True)

        # The command reconstructs the PRE-FIX resolver (private dir INSIDE the
        # worktree — a rename, not a relocation) and asserts the containment
        # invariant. It exits non-zero because the pre-fix shape violates it.
        check = (
            "import os, sys\n"
            "wt = os.path.abspath(os.getcwd())\n"
            f"task = {task_id!r}\n"
            "# pre-fix (buggy) resolution: private dir under the worktree itself\n"
            "private = os.path.join(wt, '.guardkit', 'autobuild-private', task)\n"
            "inside = os.path.commonpath([wt, private]) == wt\n"
            "if inside:\n"
            "    sys.stderr.write(\n"
            "        'CONTAINMENT VIOLATION: task_private_dir resolves INSIDE the '\n"
            "        'shared worktree (' + private + '); it must live outside the '\n"
            "        \"Player's cwd tree.\\n\")\n"
            "    sys.exit(1)\n"
            "sys.exit(0)\n"
        )
        command = f"{sys.executable} -c {_shquote(check)}"

        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "SBHO",
                        "type": "assert_command",
                        "command": command,
                        "expected_exit": 0,
                        "timeout": 60,
                    }
                ]
            }
        )
        result = evaluate(block, {}, worktree)

        assert result["status"] == "failed"
        (failure,) = result["failures"]
        assert failure["rule_id"] == "SBHO"
        assert failure["kind"] == "assert_command"
        detail = failure["detail"]
        assert "exited 1" in detail
        # Actionable: the command's own message reaches the Player.
        assert "CONTAINMENT VIOLATION" in detail
        assert "INSIDE the shared worktree" in detail


class TestWouldHaveFired_CMIR003:
    """CMIR-003: AC-1's config tier never built; two duplicated env-only
    resolvers; a comment claimed otherwise. An OMISSION produces no failing
    test, so the coach graded what was present. A ``token_coverage`` rule
    (required config-tier tokens present · ``GUARDKIT_COACH_CONTRACT`` read at
    most once · the config-tier test exists) turns the omission + the duplicate
    into a blocking failure.
    """

    def _reconstruct_prefix_tree(self, root: Path) -> None:
        """Write the pre-fix shape: two env-only resolvers, no config tier."""
        pkg = root / "guardkit" / "orchestrator"
        pkg.mkdir(parents=True)
        # Resolver A (env-only) with a comment falsely claiming the config tier
        # is handled — the "a comment claimed otherwise" half of CMIR-003. The
        # claim is prose only; neither the config file nor the config key is
        # actually read, so the required config-tier tokens stay absent.
        (pkg / "coach_contract.py").write_text(
            "import os\n\n\n"
            "def resolve_contract():\n"
            "    # Resolves the coach contract from the environment, plus the\n"
            "    # repo config tier per the spec (env > config > default).\n"
            '    return os.environ.get("GUARDKIT_COACH_CONTRACT", "coachsplit")\n'
        )
        # Resolver B: a duplicated env-only resolver in another module.
        (pkg / "agent_invoker.py").write_text(
            "import os\n\n\n"
            "def _coach_contract():\n"
            '    return os.environ.get("GUARDKIT_COACH_CONTRACT", "coachsplit")\n'
        )
        # A test exists, but only for the env tier — the config tier is untested.
        tests_dir = root / "tests" / "orchestrator"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_coach_contract.py").write_text(
            "def test_env_tier():\n"
            "    # exercises the environment variable only\n"
            "    pass\n"
        )

    def test_missing_config_tier_and_duplicate_resolver_fail(
        self, tmp_path: Path
    ) -> None:
        self._reconstruct_prefix_tree(tmp_path)

        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "CMIR-003",
                        "type": "token_coverage",
                        "paths": ["guardkit/orchestrator/**/*.py"],
                        # The config tier that AC-1 required but never built.
                        "require_tokens": [
                            "config.yaml",
                            "autobuild.coach.contract",
                        ],
                        # The env resolver must exist ONCE — the pre-fix shape
                        # has two copies.
                        "unique_token": {
                            "token": "GUARDKIT_COACH_CONTRACT",
                            "max_count": 1,
                            "paths": ["guardkit/orchestrator/**/*.py"],
                        },
                        # The config-tier test the omission left unwritten.
                        "require_test_tokens": {
                            "paths": ["tests/**/*.py"],
                            "tokens": ["config-only tier"],
                        },
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)

        assert result["status"] == "failed"
        (failure,) = result["failures"]
        assert failure["rule_id"] == "CMIR-003"
        assert failure["kind"] == "token_coverage"
        detail = failure["detail"]
        # (a) the config tier simply never built — required tokens absent.
        assert "config.yaml" in detail
        assert "autobuild.coach.contract" in detail
        # (b) the duplicated env-only resolver: read twice, cap is one.
        assert "GUARDKIT_COACH_CONTRACT" in detail
        assert "2 time" in detail
        # (c) the config-tier test was never authored.
        assert "config-only tier" in detail


def _shquote(s: str) -> str:
    """POSIX single-quote a string for a ``sh -c`` command line."""
    return "'" + s.replace("'", "'\\''") + "'"


# ===========================================================================
# 2a. Provenance pin (CV4M) — the rendered block == the vendored golden payload
# ===========================================================================


class TestProvenancePin:
    """Pin ``_V4_DECISION_FORMAT_BLOCK`` to the vendored adf golden payload.

    RECORDED DIVERGENCE (coordinator decision, 2026-07-27): the shipped rendered
    block is byte-identical to the adf ``V4_DECISION_FORMAT`` authority EXCEPT
    for a single trailing newline — the authority string ends ``…contract.\\n``
    (1110 bytes) while ``_V4_DECISION_FORMAT_BLOCK`` ends ``…contract.`` (1109
    bytes). Per the FEAT-SCG fences the prompt/v4 wire contract must NOT be
    changed, so the exact-bytes pin below is marked ``xfail(strict=True)``: it
    documents the divergence verbatim and will FAIL LOUDLY (xpass) the moment
    the block or the golden is edited to close it — without changing shipped
    behavior today. The live content pin that follows catches any *content*
    re-teach (the actual CV4M drift) immediately.
    """

    def test_golden_payload_is_the_verbatim_authority_shape(self) -> None:
        payload = _golden_payload()
        assert payload.startswith("## Decision Format")
        # Verbatim adf bytes end with a trailing newline.
        assert payload.endswith("contract.\n")
        # The two-key raw-JSON contract, no fence taught.
        assert "SINGLE RAW JSON object" in payload
        assert "the two keys above are\n  the entire contract." in payload

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "RECORDED DIVERGENCE: _V4_DECISION_FORMAT_BLOCK omits the trailing "
            "newline present in the adf V4_DECISION_FORMAT authority (1109 vs "
            "1110 bytes). Prompt is fenced off (no v4 wire-contract changes), so "
            "the golden is pinned to the CURRENT adf bytes and this exact-bytes "
            "pin xfails until the block and golden are reconciled."
        ),
    )
    def test_rendered_block_is_byte_identical_to_golden_payload(self) -> None:
        from guardkit.orchestrator.agent_invoker import _V4_DECISION_FORMAT_BLOCK

        assert _V4_DECISION_FORMAT_BLOCK == _golden_payload()

    def test_rendered_block_content_matches_golden_payload(self) -> None:
        """The live half of the pin: block == golden payload once the single
        recorded trailing newline is accounted for. Any CONTENT change to the
        rendered block (a re-taught fence, an extra key) breaks this
        immediately — the prompt and its fixture can no longer drift together.
        """
        from guardkit.orchestrator.agent_invoker import _V4_DECISION_FORMAT_BLOCK

        payload = _golden_payload()
        # Remove exactly the one recorded divergence (the trailing newline).
        payload_body = payload[:-1] if payload.endswith("\n") else payload
        assert _V4_DECISION_FORMAT_BLOCK == payload_body


# ===========================================================================
# 2b. Containment pin (SBHO) — task_private_dir resolves OUTSIDE the worktree
# ===========================================================================


class TestContainmentPin:
    """Pin the SBHO relocation invariant under a REALISTIC (worktree-shaped)
    root — the shape the plain-``tmp_path`` tests cannot see.
    """

    def test_task_private_dir_is_outside_a_worktree_shaped_root(
        self, tmp_path: Path
    ) -> None:
        from guardkit.orchestrator.paths import TaskArtifactPaths

        task_id = "TASK-SBHO-PIN"
        worktree = tmp_path / ".guardkit" / "worktrees" / task_id
        worktree.mkdir(parents=True)

        private = TaskArtifactPaths.task_private_dir(task_id, worktree).resolve()
        wt = worktree.resolve()

        # The invariant: the private dir is NOT a descendant of the worktree.
        assert wt not in private.parents
        assert private != wt
        # It relocates to the MAIN checkout's autobuild-private, beside the
        # .guardkit/worktrees tree rather than inside it.
        expected = (tmp_path / ".guardkit" / "autobuild-private" / task_id).resolve()
        assert private == expected

    def test_plain_tmp_path_root_cannot_expose_the_invariant(
        self, tmp_path: Path
    ) -> None:
        """Why the pin needs a worktree-shaped root: with a bare ``tmp_path``
        root there is no enclosing worktree, so the private dir resolves BESIDE
        the root and a broken (inside-worktree) resolver would look identical.
        This documents the blind spot the containment pin above closes.
        """
        from guardkit.orchestrator.paths import TaskArtifactPaths

        task_id = "TASK-SBHO-PLAIN"
        private = TaskArtifactPaths.task_private_dir(task_id, tmp_path).resolve()
        # Under a plain root the private dir sits inside that root — there is no
        # separate worktree for it to be wrongly nested in, so the test is blind
        # to the relocation. (Contrast with the worktree-shaped test above.)
        assert tmp_path.resolve() in private.parents
