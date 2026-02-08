"""
Design change detection and state-aware handling module.

This module provides:
- Extraction hash computation and comparison
- Cache TTL validation
- Design change detection logic
- State-aware handling for different task states
- Cache management and invalidation
"""

from guardkit.design.change_detector import (
    compute_extraction_hash,
    is_cache_expired,
    has_design_changed,
    check_design_freshness,
    detect_design_change,
    check_design_before_phase_0,
    update_extraction_metadata,
    apply_state_policy,
)

from guardkit.design.state_handlers import handle_design_change

from guardkit.design.cache_manager import (
    get_cache_path,
    invalidate_cache,
    clean_expired_caches,
    ensure_cache_dir,
    load_cache,
)

__all__ = [
    "compute_extraction_hash",
    "is_cache_expired",
    "has_design_changed",
    "check_design_freshness",
    "detect_design_change",
    "handle_design_change",
    "get_cache_path",
    "invalidate_cache",
    "clean_expired_caches",
    "ensure_cache_dir",
    "load_cache",
    "check_design_before_phase_0",
    "update_extraction_metadata",
    "apply_state_policy",
]
