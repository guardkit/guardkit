"""
Integration tests for quality gates workflow.

This module provides integration tests for the AutoBuild quality gates system,
covering pre-loop quality gates, Player-Coach validation, and failure scenarios.

Test Structure:
    - test_simple_scenarios.py: Complexity 1-3 (auto-proceed, single turn)
    - test_medium_scenarios.py: Complexity 4-6 (feedback loop, 2 turns)
    - test_complex_scenarios.py: Complexity 7+ (human checkpoint, 3+ turns)
    - test_failure_scenarios.py: Auto-fix, scope creep, architectural blocks

Coverage Target: >=85%
Test Count: 40+ integration tests
"""

__all__ = []
