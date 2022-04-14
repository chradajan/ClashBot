"""Channels used on Discord server."""

from enum import Enum
import discord

from config.config import (
    COMMANDS_CHANNEL_NAME,
    FAME_CHANNEL_NAME,
    KICKS_CHANNEL_NAME,
    LEADER_INFO_CHANNEL_NAME,
    WELCOME_CHANNEL_NAME,
    REMINDER_CHANNEL_NAME,
    RULES_CHANNEL_NAME,
    STRIKES_CHANNEL_NAME,
    TIME_OFF_CHANNEL_NAME
)

class CHANNEL_NAMES(Enum):
    """Enum of relevant channel names."""
    COMMANDS = COMMANDS_CHANNEL_NAME
    FAME = FAME_CHANNEL_NAME
    KICKS = KICKS_CHANNEL_NAME
    LEADER_INFO = LEADER_INFO_CHANNEL_NAME
    WELCOME = WELCOME_CHANNEL_NAME
    REMINDER = REMINDER_CHANNEL_NAME
    RULES = RULES_CHANNEL_NAME
    STRIKES = STRIKES_CHANNEL_NAME
    TIME_OFF = TIME_OFF_CHANNEL_NAME


class Channels:
    def __init__(self):
        """Create channels dictionary."""
        self.channels = {
            CHANNEL_NAMES.COMMANDS: None,
            CHANNEL_NAMES.FAME: None,
            CHANNEL_NAMES.KICKS: None,
            CHANNEL_NAMES.LEADER_INFO: None,
            CHANNEL_NAMES.WELCOME: None,
            CHANNEL_NAMES.REMINDER: None,
            CHANNEL_NAMES.RULES: None,
            CHANNEL_NAMES.STRIKES: None,
            CHANNEL_NAMES.TIME_OFF: None
        }

    def initialize(self, guild: discord.Guild):
        """
        Save relevant channels to dictionary based on configured channel names.

        Args:
            guild (discord.Guild): Discord server to get channels from.
        """
        self.channels[CHANNEL_NAMES.COMMANDS] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.COMMANDS.value)
        self.channels[CHANNEL_NAMES.FAME] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.FAME.value)
        self.channels[CHANNEL_NAMES.KICKS] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.KICKS.value)
        self.channels[CHANNEL_NAMES.LEADER_INFO] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.LEADER_INFO.value)
        self.channels[CHANNEL_NAMES.WELCOME] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.WELCOME.value)
        self.channels[CHANNEL_NAMES.REMINDER] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.REMINDER.value)
        self.channels[CHANNEL_NAMES.RULES] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.RULES.value)
        self.channels[CHANNEL_NAMES.STRIKES] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.STRIKES.value)
        self.channels[CHANNEL_NAMES.TIME_OFF] = discord.utils.get(guild.channels, name=CHANNEL_NAMES.TIME_OFF.value)

    def commands(self) -> discord.TextChannel:
        """
        Get commands channel.

        Returns:
            discord.TextChannel: Commands channel.
        """
        return self.channels[CHANNEL_NAMES.COMMANDS]

    def fame(self) -> discord.TextChannel:
        """
        Get fame channel.

        Returns:
            discord.TextChannel: Fame channel.
        """
        return self.channels[CHANNEL_NAMES.FAME]

    def kicks(self) -> discord.TextChannel:
        """
        Get kicks channel.

        Returns:
            discord.TextChannel: Kicks channel.
        """
        return self.channels[CHANNEL_NAMES.KICKS]

    def leader_info(self) -> discord.TextChannel:
        """
        Get leader info channel.

        Returns:
            discord.TextChannel: Leader info channel.
        """
        return self.channels[CHANNEL_NAMES.LEADER_INFO]

    def welcome(self) -> discord.TextChannel:
        """
        Get welcome channel.

        Returns:
            discord.TextChannel: Welcome channel.
        """
        return self.channels[CHANNEL_NAMES.WELCOME]

    def reminder(self) -> discord.TextChannel:
        """
        Get reminder channel.

        Returns:
            discord.TextChannel: Reminder channel.
        """
        return self.channels[CHANNEL_NAMES.REMINDER]

    def rules(self) -> discord.TextChannel:
        """
        Get rules channel.

        Returns:
            discord.TextChannel: Rules channel.
        """
        return self.channels[CHANNEL_NAMES.RULES]

    def strikes(self) -> discord.TextChannel:
        """
        Get strikes channel.

        Returns:
            discord.TextChannel: Strikes channel.
        """
        return self.channels[CHANNEL_NAMES.STRIKES]

    def time_off(self) -> discord.TextChannel:
        """
        Get time off channel.

        Returns:
            discord.TextChannel: Time off channel.
        """
        return self.channels[CHANNEL_NAMES.TIME_OFF]


CHANNEL = Channels()


def prepare_channels(guild: discord.Guild):
    """
    Find roles in guild and save to dictionary.

    Args:
        guild(discord.Guild): Guild to find roles within.
    """
    global CHANNEL
    CHANNEL.initialize(guild)
