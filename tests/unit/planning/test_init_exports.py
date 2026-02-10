"""Tests for guardkit.planning.__init__.py exports.

TDD RED phase tests for TASK-SC-010. These tests verify that all required
functions are properly exported from the planning module.

Coverage Target: >=85%
Test Count: 6 tests

Key patterns verified:
- All system_overview functions are importable
- All impact_analysis functions are importable
- All context_switch functions are importable
- GuardKitConfig class is importable
- All exports are included in __all__
"""

import pytest


# =========================================================================
# IMPORT TESTS
# =========================================================================


def test_system_overview_exports():
    """Test that system_overview functions are exported."""
    from guardkit.planning import (
        get_system_overview,
        condense_for_injection,
        format_overview_display,
    )

    # Verify functions are callable
    assert callable(get_system_overview)
    assert callable(condense_for_injection)
    assert callable(format_overview_display)


def test_impact_analysis_exports():
    """Test that impact_analysis functions are exported."""
    from guardkit.planning import (
        run_impact_analysis,
        condense_impact_for_injection,
        format_impact_display,
    )

    # Verify functions are callable
    assert callable(run_impact_analysis)
    assert callable(condense_impact_for_injection)
    assert callable(format_impact_display)


def test_context_switch_exports():
    """Test that context_switch functions are exported."""
    from guardkit.planning import (
        execute_context_switch,
        format_context_switch_display,
    )

    # Verify functions are callable
    assert callable(execute_context_switch)
    assert callable(format_context_switch_display)


def test_guardkit_config_export():
    """Test that GuardKitConfig class is exported."""
    from guardkit.planning import GuardKitConfig

    # Verify class is available and can be instantiated
    assert GuardKitConfig is not None


def test_all_list_includes_exports():
    """Test that __all__ includes all exported items."""
    import guardkit.planning as planning

    # Check __all__ exists
    assert hasattr(planning, '__all__')

    # Verify all required exports are in __all__
    required_exports = [
        # system_overview
        'get_system_overview',
        'condense_for_injection',
        'format_overview_display',
        # impact_analysis
        'run_impact_analysis',
        'condense_impact_for_injection',
        'format_impact_display',
        # context_switch
        'GuardKitConfig',
        'execute_context_switch',
        'format_context_switch_display',
    ]

    for export in required_exports:
        assert export in planning.__all__, f"{export} not in __all__"


def test_existing_exports_still_work():
    """Test that existing exports are not broken."""
    from guardkit.planning import (
        ARCHITECTURE_CONTEXT_THRESHOLD,
        ARCH_TOKEN_BUDGETS,
        get_arch_token_budget,
        SystemPlanGraphiti,
        mode_detector,
        build_coach_context,
    )

    # Verify existing exports are still available
    assert ARCHITECTURE_CONTEXT_THRESHOLD is not None
    assert ARCH_TOKEN_BUDGETS is not None
    assert callable(get_arch_token_budget)
    assert SystemPlanGraphiti is not None
    assert mode_detector is not None
    assert callable(build_coach_context)
