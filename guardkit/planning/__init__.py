"""
Planning module for GuardKit.

Provides complexity gating and planning utilities.
"""

from guardkit.planning.complexity_gating import (
    ARCHITECTURE_CONTEXT_THRESHOLD,
    ARCH_TOKEN_BUDGETS,
    get_arch_token_budget,
)

__all__ = [
    'ARCHITECTURE_CONTEXT_THRESHOLD',
    'ARCH_TOKEN_BUDGETS',
    'get_arch_token_budget',
]
