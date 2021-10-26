from config import *
from discord.ext import commands
import bot_utils
import db_utils
import discord

class Strikes(commands.Cog):
    """Commands for updating strike counts."""

    def __init__(self, bot):
        self.bot = bot


    """
    Command: !set_strike_count {member} {strikes}

    Set a user's strike count to a specified value.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def set_strike_count(self, ctx, member: discord.Member, strikes: int):
        """Set user's strike count to specified value."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag == None:
            await ctx.send("Player not found in database. No changes have been made.")
            return

        prev_strike_count = db_utils.set_strikes(player_tag, strikes)

        if prev_strike_count == None:
            await ctx.send("Player not found in database. No changes have been made.")
            return

        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        await channel.send(f"Strikes updated for {member.mention}.  {prev_strike_count} -> {strikes}")

    @set_strike_count.error
    async def set_strike_count_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("Member not found. Member names are case sensitive. If member name includes spaces, place quotes around name when issuing command.")
        elif isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!set_strike_count command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error,commands.errors.BadArgument):
            await ctx.send("Invalid strikes value. Strikes must be an integer value.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !set_strike_count <member> <strikes>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_strike_count <member> <strikes>")
            raise error


    """
    Command: !give_strike {members}

    Give a list of members 1 strike.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def give_strike(self, ctx, members: commands.Greedy[discord.Member]):
        """Specify a list of members and increment each user's strike count by 1."""
        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        strike_message = "The following members have each received a strike:\n"
        members_message = ""

        for member in members:
            new_strike_count = db_utils.give_strike(db_utils.get_player_tag(member.id))
            if new_strike_count == 0:
                continue

            members_message += f"{member.mention}: {new_strike_count - 1} -> {new_strike_count}" + "\n"

        if len(members_message) == 0:
            await ctx.send("You either didn't specify any members, or none of the members you specified exist in the database. No strikes have been assigned.")
            return

        strike_message += members_message
        await channel.send(strike_message)

    @give_strike.error
    async def give_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !give_strike <members>")
            raise error


    """
    Command: !reset_all_strikes

    Set all members to 0 strikes.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_all_strikes(self, ctx):
        """Reset each member's strikes to 0."""
        db_utils.reset_strikes()
        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        await channel.send("Strikes for all members have been reset to 0.")

    @reset_all_strikes.error
    async def reset_all_strikes_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !reset_all_strikes")
            raise error