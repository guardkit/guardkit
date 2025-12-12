"""
Size validation for guidance files.

Ensures guidance files meet size targets (<3KB ideal, <5KB maximum).
"""


def validate_guidance_size(content: str, name: str) -> list[str]:
    """
    Validate guidance file meets size target.

    Args:
        content: Guidance file content
        name: Agent name for warning messages

    Returns:
        List of warning messages (empty if valid)
    """
    size_kb = len(content.encode('utf-8')) / 1024
    warnings = []

    if size_kb > 5:
        warnings.append(f"Guidance '{name}' exceeds 5KB ({size_kb:.1f}KB)")
    elif size_kb > 3:
        warnings.append(f"Guidance '{name}' exceeds target 3KB ({size_kb:.1f}KB)")

    return warnings
