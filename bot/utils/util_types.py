"""Custom types used by bot."""

from enum import Enum


class ReminderTime(Enum):
    """Reminder time options."""
    US = "US"
    EU = "EU"
    ALL = "ALL"
