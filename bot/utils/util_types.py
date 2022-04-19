"""Custom types used by bot."""

from enum import auto, Enum
from typing import Dict, TypedDict, Union


class AutoName(Enum):
    """Inherit this to create an enum where auto() sets value = name."""
    def _generate_next_value_(name, _start, _count, _last_values):
        return name

class ReminderTime(AutoName):
    """Reminder time options."""
    US = auto()
    EU = auto()
    ALL = auto()


class Status(AutoName):
    """Enum of status states used in database."""
    ACTIVE = auto()
    INACTIVE = auto()
    UNREGISTERED = auto()
    DEPARTED = auto()


class ClashData(TypedDict):
    """Dictionary containing data about user from Clash Royale API."""
    player_tag: str
    player_name: str
    role: str
    exp_level: int
    trophies: int
    best_trophies: int
    cards: Dict[int, int]
    found_cards: int
    total_cards: int
    clan_name: str
    clan_tag: str


class DiscordData(TypedDict):
    """Dictionary containing Discord data about user."""
    discord_name: str
    discord_id: Union[int, None]
    status: Status


class CombinedData(ClashData, DiscordData):
    """Dictionary containing Clash Royale and Discord data."""


class Participant(TypedDict):
    """Dictionary containing data about a participant in a river race."""
    player_tag: str
    player_name: str
    fame: int
    repair_points: int
    boat_attacks: int
    decks_used: int
    decks_used_today: int
