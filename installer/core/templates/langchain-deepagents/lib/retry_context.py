"""Retry input construction and structural context preservation.

Two helpers that keep the Player→Coach rejection-revision loop from drifting
off-corpus on large inputs:

1. ``build_context_manifest`` — distils the original target into a structural
   manifest (file list + scope/constraints) that can be re-attached to every
   retry prompt. Without this, models fabricate filenames on revision
   iterations when the input corpus is large (15+ documents). This is
   Category C from specialist-agent testing.

2. ``build_retry_input`` — shapes the retry payload as a single ``user``-role
   message containing the Coach feedback, the context manifest, and the
   Player's previous output. Follows the
   ``ainvoke()``-never-takes-system-messages contract documented in
   TASK-REV-R2A1: ``create_agent()`` unconditionally prepends ``system_prompt``
   on every call, so any ``system`` role messages in the input produce dual
   system messages and vLLM returns ``HTTP 400``.

Both helpers were originally introduced inline in the weighted-evaluation
orchestrator scaffold (commit ``dfa8090d``). Promoting them here gives the
orchestrator template a vendorable single source of truth and avoids the
two-copies-drift-over-time problem.

Dependencies: stdlib only.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Context manifest
# ---------------------------------------------------------------------------

def build_context_manifest(target: dict[str, Any], context: str) -> str:
    """Distill ``target`` + ``context`` into a structural manifest for retries.

    The manifest is what the Player gets re-shown on every revision so it does
    not fabricate filenames or drift off-corpus. Prefer structured metadata
    from ``target`` first; fall back to a context-size summary only if the
    target carries no structural hints.

    Extraction order (first match wins):

    1. ``target['files']`` (list of str or dict with ``name``/``path``) —
       rendered as a bulleted "Document manifest" section.
    2. ``target['documents']`` — same handling as ``files``.
    3. ``target['scope']`` or ``target['constraints']`` — appended as a
       "Scope" section. Can appear alongside the document manifest.
    4. Fallback: a one-liner summarising the context size in lines. Only
       emitted when no structured metadata is present.

    Args:
        target: Original target specification. A free-form dict — we read
            only the optional keys listed above.
        context: Prefetched domain context string (the raw corpus the Player
            saw on the first attempt).

    Returns:
        Manifest string suitable for inclusion in :func:`build_retry_input`.
        Empty string if neither structured metadata nor context is available.
    """
    parts: list[str] = []

    files = target.get("files", target.get("documents", []))
    if files:
        parts.append("### Document manifest\n")
        for f in files:
            if isinstance(f, str):
                name = f
            else:
                name = f.get("name", f.get("path", str(f)))
            parts.append(f"- {name}")
        parts.append("")

    scope = target.get("scope", target.get("constraints", ""))
    if scope:
        parts.append(f"### Scope\n{scope}\n")

    if not parts and context:
        ctx_lines = context.strip().splitlines()
        parts.append(
            f"Context: {len(ctx_lines)} lines of domain context "
            "provided in original input."
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Retry input builder
# ---------------------------------------------------------------------------

def build_retry_input(
    player_content: str,
    issues: list[str],
    *,
    context_manifest: str | None = None,
) -> dict:
    """Build the Player ``ainvoke()`` input for a revision attempt.

    Emits a single ``user`` role message containing:

    1. A framed header announcing Coach rejection.
    2. The Coach feedback (joined with ``"; "``).
    3. The context manifest (when provided).
    4. A guidance line nudging the Player to focus on the lowest-scoring
       criteria without discarding prior work.
    5. The Player's previous output.

    The single-``user``-message shape is required by TASK-REV-R2A1: the
    framework's ``create_agent()`` factory prepends ``system_prompt`` on
    every ``ainvoke()`` call, so the input must never contain ``system``
    messages.

    Args:
        player_content: The Player's previous output (the one the Coach
            rejected).
        issues: Coach feedback issues or extraction error messages. Joined
            with ``"; "`` into a single feedback string.
        context_manifest: Optional structural context produced by
            :func:`build_context_manifest`. Should be supplied for every
            retry when the original corpus is large — without it, models
            fabricate filenames on revision iterations.

    Returns:
        Dict matching the ``ainvoke()`` input contract:
        ``{"messages": [{"role": "user", "content": ...}]}``.
    """
    feedback = "; ".join(issues)

    parts = [
        "IMPORTANT: Your previous output was rejected by the Coach.\n",
        f"Feedback: {feedback}\n\n",
    ]

    if context_manifest:
        parts.append(
            "## Available Context (from original input)\n\n"
            f"{context_manifest}\n\n"
        )

    parts.append(
        "Apply targeted revisions focusing on the lowest-scoring "
        "criteria. Do NOT discard existing work.\n\n"
        f"Previous output:\n{player_content}"
    )

    return {
        "messages": [
            {
                "role": "user",
                "content": "".join(parts),
            },
        ],
    }
