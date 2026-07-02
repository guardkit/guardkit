"""
Planning module for GuardKit.

Provides complexity gating and planning utilities. Knowledge-graph-backed
architecture planning (system-overview, impact-analysis, coach context,
SystemPlanGraphiti) was retired in the fleet-memory cutover (FEAT-MEM-09).
"""

from guardkit.planning.complexity_gating import (
    ARCHITECTURE_CONTEXT_THRESHOLD,
    ARCH_TOKEN_BUDGETS,
    get_arch_token_budget,
)

from guardkit.planning import mode_detector
from guardkit.planning.context_switch import (
    GuardKitConfig,
    execute_context_switch,
    format_context_switch_display,
)

__all__ = [
    'ARCHITECTURE_CONTEXT_THRESHOLD',
    'ARCH_TOKEN_BUDGETS',
    'get_arch_token_budget',
    'mode_detector',
    'GuardKitConfig',
    'execute_context_switch',
    'format_context_switch_display',
]
