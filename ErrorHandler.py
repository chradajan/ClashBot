from config import *
from difflib import SequenceMatcher
from discord.ext import commands
import bot_utils
import discord

special_member_not_found_handling_commands = {"kick", "undo_kick", "player_report", "stats_report", "give_strike", "remove_strike"}

class ErrorHandler(commands.Cog):
    """Error handling cog."""

    def __init__(self, bot):
        self.bot = bot
        self.prefix = '!'

    def command_usage(self, command: commands.Command, msg: str="Command should be formatted as:\n") -> str:
        """
        Get a string showing how to properly format the specified command.

        Args:
            command(commands.Command): Command to get usage of.
            msg(str): Custom message to say in front of proper command usage.

        Returns:
            str: How to use the command.
        """
        args_str = " ".join(f"<{arg}>" for arg in command.clean_params.keys())
        usage = msg + f"{self.prefix}{command.name}"

        if len(args_str) > 0:
                usage += f" {args_str}"

        return usage

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: discord.DiscordException):
        """
        Error handler for failed commands.
        """
        if isinstance(error, commands.errors.CommandNotFound):
            if ctx.channel.name == NEW_CHANNEL:
                return

            embed = await self.command_not_found_embed(ctx.invoked_with, ctx)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.MissingRequiredArgument):
            embed = self.missing_args_embed(ctx.command)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.CheckFailure):
            is_admin_only = False
            is_leader_or_admin_only = False
            is_channel_check = False
            is_welcome_or_rules_check = False

            for check in ctx.command.checks:
                check_str = repr(check)
                check_outcome = await check(ctx)
                if bot_utils.is_admin_command_check.__name__ in check_str and not check_outcome:
                    is_admin_only = True
                elif bot_utils.is_leader_command_check.__name__ in check_str and not check_outcome:
                    is_leader_or_admin_only = True
                elif bot_utils.channel_check.__name__ in check_str and not check_outcome:
                    is_channel_check = True
                elif bot_utils.not_welcome_or_rules_check.__name__ in check_str and not check_outcome:
                    is_welcome_or_rules_check = True

            if is_welcome_or_rules_check:
                return

            embed = self.check_failure_embed(is_admin_only, is_leader_or_admin_only, is_channel_check)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.ChannelNotFound):
            embed = self.bad_channel_embed(error.argument)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.MemberNotFound):
            if ctx.command.name in special_member_not_found_handling_commands:
                return
            embed = self.member_not_found_embed(True)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.BadArgument):
            embed = self.bad_argument_embed(ctx.command, error)
            await ctx.send(embed=embed)

        elif isinstance(error, commands.errors.CommandInvokeError):
            if ctx.command.has_error_handler():
                return
            embed = self.invoke_error_embed("This may be the result of a bug.")
            embed.set_footer(text="More information about this error has been logged.")
            await ctx.send(embed=embed)
            raise error

        else:
            embed = self.unknown_error_embed(ctx.command)
            await ctx.send(embed=embed)
            raise error


    async def command_not_found_embed(self, not_found_cmd: str, ctx: commands.Context) -> discord.Embed:
        """
        Creates an embed with the most similar command to a sent command that does not exist.

        Args:
            not_found_cmd(str): Sent command that does not exist.
            ctx(commands.Context): Context of failed command.

        Returns:
            discord.Embed: Embed with information about most similar command.
        """
        highest_similarity = 0
        closest_command = None

        for cog in self.bot.cogs.values():
            for command in cog.get_commands():

                if not await command.can_run(ctx):
                    continue

                similarity = SequenceMatcher(None, command.name, not_found_cmd).ratio()
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    closest_command = command

        embed = discord.Embed(color=discord.Color.red())

        if closest_command is None:
            embed.add_field(name=f"{self.prefix}{not_found_cmd} is not a valid command",
                            value=f"Use `{self.prefix}help` to see a list of commands.")
        else:
            embed.add_field(name=f"{self.prefix}{not_found_cmd} is not a valid command",
                            value=self.command_usage(closest_command, "Did you mean ") + "?")

        return embed


    def missing_args_embed(self, command: commands.Command) -> discord.Embed:
        """
        Creates an embed for commands send with missing arguments.

        Args:
            command(commands.Command): Incorrectly used command.

        Returns:
            discord.Embed: Embedded message with information about how to use command.
        """
        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="Missing required argument(s)",
                        value=self.command_usage(command))
        return embed

    def bad_channel_embed(self, invalid_channel: str) -> discord.Embed:
        """
        Creates an embed for commands that fail to find a specified channel.

        Args:
            invalid_channel(str): The name of a channel that could not be found.

        Returns:
            discord.Embed: Embedded message with information about failure.
        """
        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="Invalid channel",
                        value=f"The channel {invalid_channel} could not be found.")
        return embed

    def bad_argument_embed(self, command: commands.Command, error: discord.DiscordException) -> discord.Embed:
        """
        Creates and embed for when a converter fails.

        Args:
            command(commands.Command): Command that resulted in a converter failure.
            error(discord.DiscordException): Error raised by converter failure.

        Returns:
            discord.Embed: Embedded message with information about the invalid parameter.
        """
        embed = discord.Embed(color=discord.Color.red())

        if isinstance(error, commands.errors.BadBoolArgument):
            embed.add_field(name="Invalid Boolean parameter",
                            value="Valid Boolean parameters are `true` and `false`.")
        else:
            embed.add_field(name="Invalid parameter type",
                            value=self.command_usage(command))
        return embed


    def check_failure_embed(self, is_admin_only: bool, is_leader_or_admin_only: bool, is_channel_check: bool) -> discord.Embed:
        """
        Creates an embed for when a command cannot be issued due to a check failure.

        Args:
            is_admin_only(bool): If command failed because a non-admin issued it.
            is_leader_or_admin_only(bool): If command failed because a non-leader/non-admin issued it.
            is_channel_check(bool): If command failed because it was sent in an illegal channel.

        Returns:
            discord.Embed: Embedded message with information about why the command could not be issued.
        """
        embed = discord.Embed(color=discord.Color.red())

        fail_reason = ""

        if is_leader_or_admin_only:
            fail_reason += "\t•You must be a leader/admin to issue this command\n"
        if is_admin_only:
            fail_reason += "\t•You must be an admin to issue this command\n"
        if is_channel_check:
            fail_reason += "\t•That command cannot be issue in this channel"

        embed.add_field(name="Permissions error", value=fail_reason)
        return embed


    @staticmethod
    def member_not_found_embed(requires_discord_member: bool) -> discord.Embed:
        """
        Creates an embed for when a command cannot find a specified member.

        Args:
            requires_discord_member(bool): Whether the failing command requires the member to be on Discord.

        Returns:
            discord.Embed: Embedded message with information about why the member was not found.
        """
        embed = discord.Embed(color=discord.Color.red())

        if requires_discord_member:
            embed.add_field(name="Member not found",
                            value="Make sure the specified member is on Discord. If their name includes spaces, place quotes around their name.")
        else:
            embed.add_field(name="Member not found",
                            value="The specified member either doesn't exist or there are multiple people with the same player name. If their name includes spaces, place quotes around their name.")
        return embed

    @staticmethod
    def invoke_error_embed(msg: str) -> discord.Embed:
        """
        Creates an embed for commands that could not be invoked.

        Args:
            msg(str): Message to print with error.

        Returns:
            discord.Embed: Embedded message with information about error.
        """
        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="Command invoke error", value=msg)
        return embed


    def unknown_error_embed(self, command: commands.Command) -> discord.Embed:
        """
        Creates an embed for when an unhandled error has occurred.

        Args:
            command(commands.Command): Command that triggered unhandled error.

        Returns:
            discord.Embed: Embedded message with information about how to use command.
        """
        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="An unknown error has occurred",
                        value=self.command_usage(command))
        embed.set_footer(text="More information about this error has been logged.")
        return embed
