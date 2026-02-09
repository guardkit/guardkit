"""
Complexity gating for architecture context token budget allocation.

This module provides functions to determine how much architecture context
to include based on task complexity. Lower complexity tasks don't need
architecture context, while higher complexity tasks benefit from more.
"""

# Complexity threshold below which no architecture context is needed
ARCHITECTURE_CONTEXT_THRESHOLD = 4

# Token budgets for each complexity tier
ARCH_TOKEN_BUDGETS = {
    'low': 0,       # Complexity 1-3: no architecture context
    'medium': 1000, # Complexity 4-6: limited context
    'high': 2000,   # Complexity 7-8: more context
    'critical': 3000,  # Complexity 9-10: maximum context
}


def get_arch_token_budget(complexity: int) -> int:
    """
    Get the architecture context token budget based on task complexity.

    Args:
        complexity: Task complexity score (expected range 1-10)

    Returns:
        Token budget as an integer:
        - 0 for complexity 1-3 (below threshold, or invalid/negative)
        - 1000 for complexity 4-6 (medium tier)
        - 2000 for complexity 7-8 (high tier)
        - 3000 for complexity 9-10+ (critical tier, clamped for >10)
    """
    # Handle invalid inputs: negative or zero complexity returns 0
    if complexity <= 0:
        return 0

    # Below threshold: no architecture context
    if complexity < ARCHITECTURE_CONTEXT_THRESHOLD:
        return ARCH_TOKEN_BUDGETS['low']

    # Medium tier: complexity 4-6
    if complexity <= 6:
        return ARCH_TOKEN_BUDGETS['medium']

    # High tier: complexity 7-8
    if complexity <= 8:
        return ARCH_TOKEN_BUDGETS['high']

    # Critical tier: complexity 9-10 (and any value above 10 clamps here)
    return ARCH_TOKEN_BUDGETS['critical']
