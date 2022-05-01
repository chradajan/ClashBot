"""Custom types used by bot."""

from datetime import datetime
from enum import auto, Enum
from typing import Dict, List, Tuple, TypedDict, Union


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


class RiverRaceClan(TypedDict):
    """Dictionary containing data about a clan's stats in a river race."""
    clan_tag: str
    clan_name: str
    fame: int
    total_decks_used: int
    decks_used_today: int
    completed: bool


class DatabaseClan(TypedDict):
    """Dictionary containing data about a clan saved in the river_race_clans table."""
    clan_tag: str
    clan_name: str
    fame: int
    total_fame: int
    total_decks_used: int
    war_decks_used: int
    num_days: int


class RaceStats(TypedDict):
    """Dictionary containing data about a user's stats in a river race."""
    player_tag: str
    battle_wins: int
    battle_losses: int
    special_battle_wins: int
    special_battle_losses: int
    boat_attack_wins: int
    boat_attack_losses: int
    duel_match_wins: int
    duel_match_losses: int
    duel_series_wins: int
    duel_series_losses: int


class MatchTypeStats(TypedDict):
    """Dictionary containing a user's stats for a single game mode (e.g. regular matches or boat attacks)."""
    wins: int
    losses: int
    total: int
    win_rate: str


class AllMatchTypeStats(TypedDict):
    """Dictionary containing a user's stats for all game modes."""
    regular: MatchTypeStats
    special: MatchTypeStats
    duel_matches: MatchTypeStats
    duel_series: MatchTypeStats
    combined_pvp: MatchTypeStats
    boat_attacks: MatchTypeStats


class RecentStats(AllMatchTypeStats):
    """Dictionary containing a user's stats in most recent river race."""
    fame: int
    tracked_since: datetime


class RiverRaceStats(TypedDict):
    """Dictionary containing a user's all time, season, and most recent river race stats."""
    recent: RecentStats
    season: RecentStats
    all: AllMatchTypeStats


class DatabaseData(TypedDict):
    """Dictionary containing a user's basic data saved in the database."""
    player_tag: str
    player_name: str
    discord_name: str
    discord_id: int
    role: str


class DatabaseDataExtended(DatabaseData):
    """Dictionary containing a user's extended data in the database."""
    clan_tag: str
    clan_name: str
    vacation: bool
    strikes: int
    permanent_strikes: int
    usage_history: int
    status: Status


class ResetTimes(TypedDict):
    """Dictionary containing reset times of each day of a river race."""
    thursday: datetime
    friday: datetime
    saturday: datetime
    sunday: datetime


class DecksReport(TypedDict):
    """Dictionary containing a report of deck usage today."""
    remaining_decks: int
    participants: int
    active_members_with_no_decks_used: int
    active_members_with_remaining_decks: List[Tuple[str, int]]
    active_members_without_remaining_decks: List[Tuple[str, int]]
    inactive_members_with_decks_used: List[Tuple[str, int]]
    locked_out_active_members: List[Tuple[str, int]]
