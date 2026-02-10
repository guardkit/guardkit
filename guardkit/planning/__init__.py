"""
Planning module for GuardKit.

Provides complexity gating, planning utilities, and Graphiti architecture operations.
"""

from guardkit.planning.complexity_gating import (
    ARCHITECTURE_CONTEXT_THRESHOLD,
    ARCH_TOKEN_BUDGETS,
    get_arch_token_budget,
)

from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.planning import mode_detector
from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
    format_overview_display,
)
from guardkit.planning.coach_context_builder import (
    build_coach_context,
)
from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    condense_impact_for_injection,
    format_impact_display,
)
from guardkit.planning.context_switch import (
    GuardKitConfig,
    execute_context_switch,
    format_context_switch_display,
)

__all__ = [
    'ARCHITECTURE_CONTEXT_THRESHOLD',
    'ARCH_TOKEN_BUDGETS',
    'get_arch_token_budget',
    'SystemPlanGraphiti',
    'mode_detector',
    'get_system_overview',
    'condense_for_injection',
    'format_overview_display',
    'build_coach_context',
    'run_impact_analysis',
    'condense_impact_for_injection',
    'format_impact_display',
    'GuardKitConfig',
    'execute_context_switch',
    'format_context_switch_display',
]
