"""
FalkorDB workarounds for graphiti-core.

Contains two monkey-patches:

1. handle_multiple_group_ids decorator fix (PR #1170)
   Fixes a bug where single-group-id searches use the wrong FalkorDB database.
   Bug: graphiti-core decorators.py checks `len(group_ids) > 1`, which skips
   driver cloning for single group_id searches.
   Fix: Change to `len(group_ids) >= 1`.

   Upstream references:
       - Issue: https://github.com/getzep/graphiti/issues/1161
       - PR: https://github.com/getzep/graphiti/pull/1170

2. build_fulltext_query underscore escaping fix
   FalkorDB's RediSearch treats underscores as token separators. Group IDs
   like 'product_knowledge' produce queries `(@group_id:product_knowledge)`
   which RediSearch parses as two tokens, causing syntax errors.
   Fix: Escape underscores in group_id values with backslash before building
   the RediSearch query (e.g. product_knowledge becomes product backslash-underscore knowledge).

   This affects ALL GuardKit group_ids since they use underscore naming.

Usage:
    Call apply_falkordb_workaround() once at startup, before creating any
    Graphiti clients. It is safe to call multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)

_workaround_applied = False
_original_decorator = None


def apply_falkordb_workaround() -> bool:
    """Apply the FalkorDB single-group-id decorator workaround.

    Monkey-patches graphiti_core.decorators.handle_multiple_group_ids to use
    `>= 1` instead of `> 1` for the group_ids length check.

    Returns:
        True if workaround was applied (or already applied).
        False if graphiti-core is not installed or patch failed.
    """
    global _workaround_applied

    if _workaround_applied:
        return True

    try:
        import graphiti_core.decorators as decorators_module
        from graphiti_core.decorators import get_parameter_position
        from graphiti_core.driver.driver import GraphProvider
        from graphiti_core.helpers import semaphore_gather
        from graphiti_core.search.search_config import SearchResults
    except ImportError:
        logger.debug("[Graphiti] graphiti-core not installed, skipping FalkorDB workaround")
        return False

    # Check if the bug still exists by inspecting the source
    import inspect
    import functools
    from collections.abc import Awaitable, Callable
    from typing import Any, TypeVar

    original_source = inspect.getsource(decorators_module.handle_multiple_group_ids)
    if "len(group_ids) >= 1" in original_source:
        logger.info("[Graphiti] FalkorDB decorator already fixed upstream, skipping workaround")
        _workaround_applied = True
        return True

    if "len(group_ids) > 1" not in original_source:
        logger.warning(
            "[Graphiti] FalkorDB decorator source changed unexpectedly, "
            "skipping workaround (manual review needed)"
        )
        return False

    F = TypeVar('F', bound=Callable[..., Awaitable[Any]])

    def handle_multiple_group_ids_fixed(func: F) -> F:
        """Fixed decorator: clones FalkorDB driver for single AND multiple group_ids."""

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            group_ids_func_pos = get_parameter_position(func, 'group_ids')
            group_ids_pos = (
                group_ids_func_pos - 1 if group_ids_func_pos is not None else None
            )
            group_ids = kwargs.get('group_ids')

            if group_ids is None and group_ids_pos is not None and len(args) > group_ids_pos:
                group_ids = args[group_ids_pos]

            # FIX: >= 1 instead of > 1
            if (
                hasattr(self, 'clients')
                and hasattr(self.clients, 'driver')
                and self.clients.driver.provider == GraphProvider.FALKORDB
                and group_ids
                and len(group_ids) >= 1
            ):
                driver = self.clients.driver

                async def execute_for_group(gid: str):
                    filtered_args = list(args)
                    if group_ids_pos is not None and len(args) > group_ids_pos:
                        filtered_args.pop(group_ids_pos)

                    return await func(
                        self,
                        *filtered_args,
                        **{**kwargs, 'group_ids': [gid], 'driver': driver.clone(database=gid)},
                    )

                results = await semaphore_gather(
                    *[execute_for_group(gid) for gid in group_ids],
                    max_coroutines=getattr(self, 'max_coroutines', None),
                )

                if isinstance(results[0], SearchResults):
                    return SearchResults.merge(results)
                elif isinstance(results[0], list):
                    return [item for result in results for item in result]
                elif isinstance(results[0], tuple):
                    merged_tuple = []
                    for i in range(len(results[0])):
                        component_results = [result[i] for result in results]
                        if isinstance(component_results[0], list):
                            merged_tuple.append(
                                [item for component in component_results for item in component]
                            )
                        else:
                            merged_tuple.append(component_results)
                    return tuple(merged_tuple)
                else:
                    return results

            return await func(self, *args, **kwargs)

        return wrapper  # type: ignore

    # Save original and apply the monkey-patch
    global _original_decorator
    _original_decorator = decorators_module.handle_multiple_group_ids
    decorators_module.handle_multiple_group_ids = handle_multiple_group_ids_fixed

    # Re-decorate already-bound methods on the Graphiti class.
    # The decorator is applied at class definition time (import), so patching
    # the module attribute alone doesn't fix methods already decorated with the
    # old version. We use __wrapped__ (set by functools.wraps) to get the
    # original unwrapped function and re-apply the fixed decorator.
    _redecorate_graphiti_methods(handle_multiple_group_ids_fixed)

    _workaround_applied = True
    logger.info(
        "[Graphiti] Applied FalkorDB workaround: "
        "handle_multiple_group_ids patched for single group_id support "
        "(upstream PR #1170)"
    )

    # Also apply the fulltext query workaround for underscore escaping
    apply_fulltext_query_workaround()

    return True


# Methods on Graphiti class that use @handle_multiple_group_ids
_DECORATED_METHODS = ("retrieve_episodes", "build_communities", "search", "search_")
_original_methods: dict = {}


def _redecorate_graphiti_methods(fixed_decorator) -> None:
    """Re-decorate already-bound Graphiti methods with the fixed decorator.

    At import time, graphiti_core defines the Graphiti class and applies
    @handle_multiple_group_ids to several methods. By the time our patch runs,
    those methods already have the buggy wrapper. This function extracts the
    original unwrapped function via __wrapped__ and re-applies the fixed
    decorator.
    """
    try:
        from graphiti_core import Graphiti
    except ImportError:
        return

    for method_name in _DECORATED_METHODS:
        method = getattr(Graphiti, method_name, None)
        if method is None:
            continue

        # Save original decorated method for restore in remove_workaround()
        _original_methods[method_name] = method

        # Get the unwrapped original function
        unwrapped = getattr(method, "__wrapped__", None)
        if unwrapped is None:
            logger.debug(
                f"[Graphiti] Method {method_name} has no __wrapped__, skipping re-decoration"
            )
            continue

        # Re-decorate with the fixed version
        setattr(Graphiti, method_name, fixed_decorator(unwrapped))
        logger.debug(f"[Graphiti] Re-decorated Graphiti.{method_name} with fixed decorator")


def is_workaround_applied() -> bool:
    """Check if the FalkorDB workaround has been applied."""
    return _workaround_applied


# =============================================================================
# Workaround 2: build_fulltext_query underscore escaping
# =============================================================================

_fulltext_workaround_applied = False
_original_build_fulltext_query = None


def _escape_group_id_for_redisearch(group_id: str) -> str:
    """Escape RediSearch separator characters in a group_id value.

    FalkorDB's RediSearch treats these characters as token separators:
        , . < > { } [ ] " ' : ; ! @ # $ % ^ & * ( ) - + = ~ _

    Group IDs commonly contain underscores (product_knowledge) and
    double underscores (guardkit__project_overview). These must be
    escaped with backslash for exact matching in RediSearch queries.

    Args:
        group_id: The raw group_id value.

    Returns:
        Escaped group_id safe for RediSearch query syntax.
    """
    # Escape characters that RediSearch treats as separators.
    # Order matters: backslash must be escaped first to avoid double-escaping.
    # We only escape the chars likely to appear in group_ids:
    #   _ (underscore) - most common, e.g. product_knowledge
    #   - (hyphen) - possible in normalized project IDs
    result = group_id
    result = result.replace('_', r'\_')
    result = result.replace('-', r'\-')
    return result


def apply_fulltext_query_workaround() -> bool:
    """Patch FalkorDriver.build_fulltext_query to escape underscores in group_ids.

    Without this patch, queries like (@group_id:product_knowledge) fail with:
        RediSearch: Syntax error at offset 31 near product_knowledge

    Returns:
        True if patch applied (or already applied), False if FalkorDB driver unavailable.
    """
    global _fulltext_workaround_applied, _original_build_fulltext_query

    if _fulltext_workaround_applied:
        return True

    try:
        from graphiti_core.driver.falkordb_driver import FalkorDriver
    except ImportError:
        logger.debug("[Graphiti] FalkorDB driver not available, skipping fulltext workaround")
        return False

    _original_build_fulltext_query = FalkorDriver.build_fulltext_query

    def build_fulltext_query_fixed(
        self, query: str, group_ids: list | None = None, max_query_length: int = 128
    ) -> str:
        """Fixed build_fulltext_query that escapes underscores in group_ids."""
        if group_ids is not None:
            group_ids = [_escape_group_id_for_redisearch(gid) for gid in group_ids]
        return _original_build_fulltext_query(self, query, group_ids, max_query_length)

    FalkorDriver.build_fulltext_query = build_fulltext_query_fixed

    _fulltext_workaround_applied = True
    logger.info(
        "[Graphiti] Applied FalkorDB workaround: "
        "build_fulltext_query patched to escape underscores in group_ids"
    )
    return True


def is_fulltext_workaround_applied() -> bool:
    """Check if the fulltext query workaround has been applied."""
    return _fulltext_workaround_applied


def remove_fulltext_workaround() -> None:
    """Restore original build_fulltext_query (for testing only)."""
    global _fulltext_workaround_applied, _original_build_fulltext_query
    if _original_build_fulltext_query is not None:
        try:
            from graphiti_core.driver.falkordb_driver import FalkorDriver
            FalkorDriver.build_fulltext_query = _original_build_fulltext_query
        except ImportError:
            pass
    _fulltext_workaround_applied = False
    _original_build_fulltext_query = None


def remove_workaround() -> None:
    """Reset all workaround states and restore originals (for testing only)."""
    global _workaround_applied, _original_decorator
    if _original_decorator is not None:
        try:
            import graphiti_core.decorators as decorators_module
            decorators_module.handle_multiple_group_ids = _original_decorator
        except ImportError:
            pass

    # Restore original decorated methods on Graphiti class
    if _original_methods:
        try:
            from graphiti_core import Graphiti
            for method_name, original_method in _original_methods.items():
                setattr(Graphiti, method_name, original_method)
            _original_methods.clear()
        except ImportError:
            pass

    _workaround_applied = False
    _original_decorator = None

    # Also remove the fulltext workaround
    remove_fulltext_workaround()
