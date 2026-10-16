"""Derived field calculations for user summaries."""

from __future__ import annotations

from datetime import UTC, date, datetime


def calculate_days_since_created(created_at: datetime) -> int:
    """Calculate the number of days between a creation date and today.

    Handles both timezone-aware and timezone-naive datetimes correctly.
    Timezone-aware datetimes are converted to UTC before extracting the date.

    Args:
        created_at: The creation datetime (timezone-aware or naive).

    Returns:
        The number of days since creation as a non-negative integer.
    """
    if created_at.tzinfo is not None:
        utc_date = created_at.astimezone(UTC).date()
    else:
        utc_date = created_at.date()

    today = date.today()
    delta = (today - utc_date).days
    return max(delta, 0)
