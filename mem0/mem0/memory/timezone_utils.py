"""
Unified timezone utilities for autonomous AI memory storage.
This module provides consistent timezone handling across all memory components.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


class TimezoneConfig:
    """
    Configuration for timezone handling in the memory system.
    """

    def __init__(
        self, default_timezone: str = "US/Pacific", use_system_timezone: bool = False
    ):
        """
        Initialize timezone configuration.

        Args:
            default_timezone: Default timezone for memory timestamps
            use_system_timezone: Whether to use system timezone as fallback
        """
        self.default_timezone = default_timezone
        self.use_system_timezone = use_system_timezone
        self._default_tz = pytz.timezone(default_timezone)

    def get_default_timezone(self):
        """Get the configured default timezone."""
        return self._default_tz

    def get_timezone_for_timestamp(self, reference_time: Optional[datetime] = None):
        """
        Get appropriate timezone for timestamp creation.

        Args:
            reference_time: Optional reference datetime to match timezone

        Returns:
            Timezone to use for timestamp creation
        """
        if reference_time and reference_time.tzinfo:
            return reference_time.tzinfo
        return self._default_tz


# Global timezone configuration instance
_timezone_config = TimezoneConfig()


def configure_timezone(
    default_timezone: str = "US/Pacific", use_system_timezone: bool = False
):
    """
    Configure global timezone settings for the memory system.

    Args:
        default_timezone: Default timezone for memory timestamps
        use_system_timezone: Whether to use system timezone as fallback
    """
    global _timezone_config
    _timezone_config = TimezoneConfig(default_timezone, use_system_timezone)
    logger.info(
        f"Timezone configured: default={default_timezone}, use_system={use_system_timezone}"
    )


def safe_datetime_now(reference_time: Optional[datetime] = None) -> datetime:
    """
    Safely get current datetime with proper timezone handling.

    Args:
        reference_time: Optional reference datetime to match timezone

    Returns:
        Current datetime with proper timezone handling
    """
    if reference_time is None:
        # Use configured default timezone
        return datetime.now(_timezone_config.get_default_timezone())

    try:
        # Handle timezone-aware reference time
        if reference_time.tzinfo is not None:
            # Safe: get the timezone object first, then use it
            target_tz = reference_time.tzinfo
            return datetime.now(target_tz)

        # Handle timezone-naive reference time - use default timezone
        return datetime.now(_timezone_config.get_default_timezone())
    except Exception as e:
        logger.warning(f"Timezone handling error in safe_datetime_now: {e}")
        return datetime.now(_timezone_config.get_default_timezone())


def safe_datetime_diff(dt1: datetime, dt2: datetime) -> timedelta:
    """
    Safely calculate difference between two datetimes, handling timezone mismatches.

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        Time difference as timedelta
    """
    try:
        # If both are naive or both are aware, calculate normally
        if (dt1.tzinfo is None) == (dt2.tzinfo is None):
            return dt1 - dt2

        # If one is aware and other is naive, convert naive to default timezone
        default_tz = _timezone_config.get_default_timezone()

        if dt1.tzinfo is None:
            # Create timezone-aware version using localize
            dt1 = default_tz.localize(dt1)
        if dt2.tzinfo is None:
            # Create timezone-aware version using localize
            dt2 = default_tz.localize(dt2)

        return dt1 - dt2
    except Exception as e:
        logger.warning(f"Timezone handling error in safe_datetime_diff: {e}")
        # Fallback: create naive versions for comparison by reconstructing datetimes
        dt1_naive = datetime(
            dt1.year,
            dt1.month,
            dt1.day,
            dt1.hour,
            dt1.minute,
            dt1.second,
            dt1.microsecond,
        )
        dt2_naive = datetime(
            dt2.year,
            dt2.month,
            dt2.day,
            dt2.hour,
            dt2.minute,
            dt2.second,
            dt2.microsecond,
        )
        return dt1_naive - dt2_naive


def create_memory_timestamp(reference_time: Optional[datetime] = None) -> str:
    """
    Create a properly formatted timestamp for memory storage.

    Args:
        reference_time: Optional reference datetime to match timezone

    Returns:
        ISO formatted timestamp string
    """
    return safe_datetime_now(reference_time).isoformat()


def get_memory_age_hours(
    created_at: str, reference_time: Optional[datetime] = None
) -> float:
    """
    Calculate age of memory in hours from timestamp string.

    Args:
        created_at: ISO formatted timestamp string
        reference_time: Optional reference time for calculation

    Returns:
        Age in hours, or 0.0 if calculation fails
    """
    try:
        created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        current_time = safe_datetime_now(reference_time)
        age_diff = safe_datetime_diff(current_time, created_time)
        return age_diff.total_seconds() / 3600
    except Exception as e:
        logger.warning(f"Error calculating memory age: {e}")
        return 0.0


def get_memory_age_days(
    created_at: str, reference_time: Optional[datetime] = None
) -> int:
    """
    Calculate age of memory in days from timestamp string.

    Args:
        created_at: ISO formatted timestamp string
        reference_time: Optional reference time for calculation

    Returns:
        Age in days, or 0 if calculation fails
    """
    try:
        created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        current_time = safe_datetime_now(reference_time)
        age_diff = safe_datetime_diff(current_time, created_time)
        return age_diff.days
    except Exception as e:
        logger.warning(f"Error calculating memory age: {e}")
        return 0
