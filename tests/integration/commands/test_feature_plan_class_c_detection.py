"""End-to-end detector tests against the FEAT-FD32 reproducer ACs.

This module hard-gates the operator_handoff detector (TASK-FPTC-001) against
the two real-world incidents that motivated the Class C workstream:

- ``AC_SEED_01`` — verbatim AC-SEED-01 from study-tutor TASK-GR-SEED.
- ``AC_DEMO_01`` — verbatim AC-DEMO-01 from study-tutor TASK-GR-DEMO.

Both reproducer ACs MUST trigger the detector. Three benign ACs MUST NOT
trigger (false-positive guard). The matcher under test
(``_detector_matcher.detect_operator_handoff``) is a contract mirror of the
strong/weak/pairing rules in ``installer/core/commands/feature-plan.md`` —
see the module docstring on ``_detector_matcher`` for why this Python
helper exists alongside the prompt-side detector.

ACs covered: AC-FPTC-006-01 through AC-FPTC-006-05.
"""

from __future__ import annotations

import pytest

from ._detector_matcher import detect_operator_handoff


# ---------------------------------------------------------------------------
# Reproducer fixtures (AC-FPTC-006-02, AC-FPTC-006-03)
# ---------------------------------------------------------------------------
#
# These strings are reproduced verbatim from the parent review and the
# original study-tutor task files so the prompt and the contract-mirror
# matcher are gated against the same text the real plan once produced.

AC_SEED_01 = (
    "`python scripts/seed_student_model.py` runs successfully against live "
    "FalkorDB at whitestocks:6379 ... All 25 entity writes succeed without "
    "401s, timeouts, or GroupIdValidationError failures."
)

AC_DEMO_01 = (
    "A live MCP tutor session is conducted from Claude Desktop with the user "
    "as the human-in-the-loop. Sequence: 5–7 × tutor_turn(...) "
    "exchanges with at least one Coach revision ..."
)


# ---------------------------------------------------------------------------
# Benign fixtures that must NOT trigger (AC-FPTC-006-04)
# ---------------------------------------------------------------------------
#
# Each of these is an autobuild-suitable AC that looks superficially close
# to the reproducers (mentions "tests", "FALKORDB", parses a YAML stream) but
# does not contain any strong signal — the false-positive guard from
# feature-plan.md must keep them inert.

BENIGN_PYTEST = "All unit tests pass with `pytest tests/ -v`."
BENIGN_FALKORDB_CONFIG = (
    "`SettingsClass.from_env()` reads `FALKORDB_HOST` from environment and "
    "constructs a valid client config."
)
BENIGN_PARSE_YAML = (
    "Calling `parse_yaml(s)` returns the expected dict with key `version=1`."
)


# ---------------------------------------------------------------------------
# AC-FPTC-006-02 — AC_SEED_01 fixture matches strong-signal rules
# ---------------------------------------------------------------------------


def test_ac_seed_01_contains_strong_signal_markers() -> None:
    """The verbatim seed-script AC must contain the markers the rules call out
    so the prompt-side detector and the contract mirror are gated against the
    same surface text.
    """
    assert "FalkorDB" in AC_SEED_01
    assert "live" in AC_SEED_01
    assert "whitestocks" in AC_SEED_01, (
        "AC_SEED_01 must contain the project hostname pattern that the rules "
        "table in feature-plan.md flags as live infrastructure."
    )


def test_ac_seed_01_triggers_detector() -> None:
    """The seed-script reproducer must trigger the detector via the live
    infrastructure category.
    """
    result = detect_operator_handoff(AC_SEED_01)
    assert result.triggered is True
    assert "live_infrastructure" in result.strong_categories


# ---------------------------------------------------------------------------
# AC-FPTC-006-03 — AC_DEMO_01 fixture matches strong-signal rules
# ---------------------------------------------------------------------------


def test_ac_demo_01_contains_strong_signal_markers() -> None:
    """The verbatim demo AC must contain ``live``, ``human-in-the-loop``, and
    ``Claude Desktop`` as called out by AC-FPTC-006-03.
    """
    assert "live" in AC_DEMO_01
    assert "human-in-the-loop" in AC_DEMO_01
    assert "Claude Desktop" in AC_DEMO_01


def test_ac_demo_01_triggers_detector() -> None:
    """The MCP-tutor reproducer must trigger via the human-verbs category
    (and incidentally several others — but human verbs is the load-bearing
    one for this AC).
    """
    result = detect_operator_handoff(AC_DEMO_01)
    assert result.triggered is True
    assert "human_verbs" in result.strong_categories


# ---------------------------------------------------------------------------
# AC-FPTC-006-04 — three benign fixtures must NOT trigger
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ac_text",
    [
        pytest.param(BENIGN_PYTEST, id="pytest_passes"),
        pytest.param(BENIGN_FALKORDB_CONFIG, id="falkordb_host_env_var"),
        pytest.param(BENIGN_PARSE_YAML, id="parse_yaml_returns_dict"),
    ],
)
def test_benign_acs_do_not_trigger_detector(ac_text: str) -> None:
    """The false-positive guard must keep autobuild-suitable ACs inert even
    when they superficially resemble the reproducers (e.g. ``FALKORDB_HOST``
    as a config string vs ``FalkorDB at <host>`` as a live target).
    """
    result = detect_operator_handoff(ac_text)
    assert result.triggered is False, (
        f"Benign AC unexpectedly flagged: strong_categories="
        f"{result.strong_categories!r}, weak_count={result.weak_count}"
    )
    assert result.strong_categories == ()


# ---------------------------------------------------------------------------
# AC-FPTC-006-05 — pairing rule (weak alone does NOT trigger)
# ---------------------------------------------------------------------------
#
# These tests exercise the contract-mirror matcher's pairing rule so the
# false-positive guard ("weak signal alone does NOT trigger") from
# feature-plan.md is mechanically enforced.


def test_weak_signal_alone_does_not_trigger() -> None:
    """A weak signal in isolation must not flip ``triggered``."""
    weak_only = "Verify the parser handles trailing whitespace correctly."
    result = detect_operator_handoff(weak_only)
    assert result.weak_count >= 1, "fixture should contain a weak signal"
    assert result.triggered is False
    assert result.strong_categories == ()


def test_strong_plus_weak_still_triggers() -> None:
    """1 strong + N weak must trigger — strong always wins per the rules."""
    mixed = (
        "Verify that the seed script runs against live FalkorDB at "
        "whitestocks:6379."
    )
    result = detect_operator_handoff(mixed)
    assert result.triggered is True
    assert "live_infrastructure" in result.strong_categories
    assert result.weak_count >= 1
