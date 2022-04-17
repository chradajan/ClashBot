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

class ChannelNames(Enum):
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
    """Stores channels relevant to bot."""

    def __init__(self):
        """Create channels dictionary."""
        self.channels = {
            ChannelNames.COMMANDS: None,
            ChannelNames.FAME: None,
            ChannelNames.KICKS: None,
            ChannelNames.LEADER_INFO: None,
            ChannelNames.WELCOME: None,
            ChannelNames.REMINDER: None,
            ChannelNames.RULES: None,
            ChannelNames.STRIKES: None,
            ChannelNames.TIME_OFF: None
        }

    def initialize(self, guild: discord.Guild):
        """Save relevant channels to dictionary based on configured channel names.

        Args:
            guild: Discord server to get channels from.
        """
        self.channels[ChannelNames.COMMANDS] = discord.utils.get(guild.channels, name=ChannelNames.COMMANDS.value)
        self.channels[ChannelNames.FAME] = discord.utils.get(guild.channels, name=ChannelNames.FAME.value)
        self.channels[ChannelNames.KICKS] = discord.utils.get(guild.channels, name=ChannelNames.KICKS.value)
        self.channels[ChannelNames.LEADER_INFO] = discord.utils.get(guild.channels, name=ChannelNames.LEADER_INFO.value)
        self.channels[ChannelNames.WELCOME] = discord.utils.get(guild.channels, name=ChannelNames.WELCOME.value)
        self.channels[ChannelNames.REMINDER] = discord.utils.get(guild.channels, name=ChannelNames.REMINDER.value)
        self.channels[ChannelNames.RULES] = discord.utils.get(guild.channels, name=ChannelNames.RULES.value)
        self.channels[ChannelNames.STRIKES] = discord.utils.get(guild.channels, name=ChannelNames.STRIKES.value)
        self.channels[ChannelNames.TIME_OFF] = discord.utils.get(guild.channels, name=ChannelNames.TIME_OFF.value)

    def commands(self) -> discord.TextChannel:
        """Get commands channel.

        Returns:
            Commands channel.
        """
        return self.channels[ChannelNames.COMMANDS]

    def fame(self) -> discord.TextChannel:
        """Get fame channel.

        Returns:
            Fame channel.
        """
        return self.channels[ChannelNames.FAME]

    def kicks(self) -> discord.TextChannel:
        """Get kicks channel.

        Returns:
            Kicks channel.
        """
        return self.channels[ChannelNames.KICKS]

    def leader_info(self) -> discord.TextChannel:
        """Get leader info channel.

        Returns:
            Leader info channel.
        """
        return self.channels[ChannelNames.LEADER_INFO]

    def welcome(self) -> discord.TextChannel:
        """Get welcome channel.

        Returns:
            Welcome channel.
        """
        return self.channels[ChannelNames.WELCOME]

    def reminder(self) -> discord.TextChannel:
        """Get reminder channel.

        Returns:
            Reminder channel.
        """
        return self.channels[ChannelNames.REMINDER]

    def rules(self) -> discord.TextChannel:
        """Get rules channel.

        Returns:
            Rules channel.
        """
        return self.channels[ChannelNames.RULES]

    def strikes(self) -> discord.TextChannel:
        """Get strikes channel.

        Returns:
            Strikes channel.
        """
        return self.channels[ChannelNames.STRIKES]

    def time_off(self) -> discord.TextChannel:
        """Get time off channel.

        Returns:
            Time off channel.
        """
        return self.channels[ChannelNames.TIME_OFF]


CHANNEL = Channels()


def prepare_channels(guild: discord.Guild):
    """Initialize CHANNEL object.

    Args:
        Guild to get channels of.
    """
    global CHANNEL
    CHANNEL.initialize(guild)
