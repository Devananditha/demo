"""Canonical Time Representation & Discrete Tick Conversion Utilities.

Conventions:
- 1 tick = 5 minutes
- Horizon H = 288 discrete ticks (24-hour day)
- Standard operating day starts at tick 96 (08:00)
- Standard operating day ends at tick 204 (17:00)
- All timestamps must be timezone-aware (UTC default).
"""

from datetime import date, datetime, time, timezone
from typing import Optional

TICK_DURATION_MINUTES: int = 5
TICKS_PER_HOUR: int = 60 // TICK_DURATION_MINUTES  # 12 ticks/hr
HORIZON_TICKS: int = 288  # 24 hours * 12 ticks/hr
OPERATING_DAY_START_TICK: int = 96  # 08:00 (8 * 12)
OPERATING_DAY_END_TICK: int = 204  # 17:00 (17 * 12)
OVERTIME_CUTOFF_TICK: int = 228  # 19:00 (19 * 12)


def tick_to_minutes(tick: int) -> int:
    """Convert discrete tick index to cumulative minutes from midnight."""
    if not (0 <= tick <= HORIZON_TICKS):
        raise ValueError(f"Tick {tick} is outside valid horizon [0, {HORIZON_TICKS}]")
    return tick * TICK_DURATION_MINUTES


def minutes_to_ticks(minutes: int) -> int:
    """Convert cumulative minutes from midnight to discrete tick index."""
    if not (0 <= minutes <= 1440):
        raise ValueError(f"Minutes {minutes} is outside valid 24-hour range [0, 1440]")
    return minutes // TICK_DURATION_MINUTES


def time_str_to_tick(time_str: str) -> int:
    """Convert 'HH:MM' string (24-hour) to discrete tick index.
    
    Example: '08:00' -> 96, '13:15' -> 159, '17:00' -> 204
    """
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            raise ValueError()
        hours, mins = int(parts[0]), int(parts[1])
        if not (0 <= hours <= 23 and 0 <= mins <= 59):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid time format '{time_str}'. Expected 'HH:MM' in 24-hour format.")
    
    total_minutes = hours * 60 + mins
    return total_minutes // TICK_DURATION_MINUTES


def tick_to_time_str(tick: int) -> str:
    """Convert discrete tick index to 'HH:MM' string (24-hour format).
    
    Example: 96 -> '08:00', 159 -> '13:15', 204 -> '17:00'
    """
    total_minutes = tick_to_minutes(tick)
    hours = (total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"


def datetime_to_tick(dt: datetime, base_date: Optional[date] = None) -> int:
    """Convert timezone-aware datetime to discrete tick on base_date.
    
    If base_date is omitted, uses the calendar date of the provided dt.
    """
    if dt.tzinfo is None:
        raise ValueError(f"Datetime {dt} must be timezone-aware.")
    
    # Calculate minutes from start of day in the datetime's own calendar date
    total_minutes = dt.hour * 60 + dt.minute
    return total_minutes // TICK_DURATION_MINUTES


def tick_to_datetime(
    tick: int,
    base_date: date,
    tz: timezone = timezone.utc
) -> datetime:
    """Convert discrete tick index on a base_date into a timezone-aware datetime."""
    total_minutes = tick_to_minutes(tick)
    hours = total_minutes // 60
    mins = total_minutes % 60
    t = time(hour=hours % 24, minute=mins)
    return datetime.combine(base_date, t, tzinfo=tz)
