"""Tests for guardkit.planning.__init__.py exports.

Verifies the planning package exports after the fleet-memory cutover
(FEAT-MEM-09), which retired the knowledge-graph planning surface
(system_overview, impact_analysis, coach_context, SystemPlanGraphiti).

Key patterns verified:
- complexity_gating exports are importable
- context_switch functions are importable
- GuardKitConfig class is importable
- mode_detector is importable
- retired symbols are NOT exported
- all live exports are included in __all__
"""

import pytest


# =========================================================================
# IMPORT TESTS
# =========================================================================


def test_complexity_gating_exports():
    """complexity_gating symbols are exported."""
    from guardkit.planning import (
        ARCHITECTURE_CONTEXT_THRESHOLD,
        ARCH_TOKEN_BUDGETS,
        get_arch_token_budget,
    )

    assert ARCHITECTURE_CONTEXT_THRESHOLD is not None
    assert ARCH_TOKEN_BUDGETS is not None
    assert callable(get_arch_token_budget)


def test_context_switch_exports():
    """context_switch functions are exported."""
    from guardkit.planning import (
        execute_context_switch,
        format_context_switch_display,
    )

    assert callable(execute_context_switch)
    assert callable(format_context_switch_display)


def test_guardkit_config_export():
    """GuardKitConfig class is exported."""
    from guardkit.planning import GuardKitConfig

    assert GuardKitConfig is not None


def test_mode_detector_export():
    """mode_detector module is exported."""
    from guardkit.planning import mode_detector

    assert mode_detector is not None


def test_all_list_includes_live_exports():
    """__all__ includes every live export."""
    import guardkit.planning as planning

    assert hasattr(planning, "__all__")

    required_exports = [
        "ARCHITECTURE_CONTEXT_THRESHOLD",
        "ARCH_TOKEN_BUDGETS",
        "get_arch_token_budget",
        "mode_detector",
        "GuardKitConfig",
        "execute_context_switch",
        "format_context_switch_display",
    ]

    for export in required_exports:
        assert export in planning.__all__, f"{export} not in __all__"


def test_retired_graphiti_symbols_not_exported():
    """Knowledge-graph planning symbols retired in FEAT-MEM-09 are gone."""
    import guardkit.planning as planning

    retired = [
        "SystemPlanGraphiti",
        "build_coach_context",
        "get_system_overview",
        "condense_for_injection",
        "format_overview_display",
        "run_impact_analysis",
        "condense_impact_for_injection",
        "format_impact_display",
    ]

    for symbol in retired:
        assert symbol not in planning.__all__, f"{symbol} should be retired from __all__"
        assert not hasattr(planning, symbol), f"{symbol} should not be importable"
