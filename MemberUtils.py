from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord

class MemberUtils(commands.Cog):
    """Miscellaneous utilities for everyone."""

    def __init__(self, bot):
        self.bot = bot


    """
    Command: !river_race_status

    Show a list of clans in the current river race and how many decks they have remaining today.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def river_race_status(self, ctx, show_predictions: bool=False):
        """Send a list of clans in the current river race and their number of decks remaining today."""
        clans = clash_utils.get_clan_decks_remaining()
        embed = discord.Embed()

        table = PrettyTable()
        table.field_names = ["Clan", "Decks"]

        for clan, decks_remaining in clans:
            _, clan_name = clan
            table.add_row([clan_name, decks_remaining])

        embed.add_field(name="Remaining decks for each clan", value="```\n" + table.get_string() + "```")

        await ctx.send(embed=embed)

        if show_predictions and db_utils.is_war_time():
            predicted_outcomes = bot_utils.get_predicted_race_outcome(clans)
            embed = discord.Embed()
            table = PrettyTable()
            table.field_names = ["Clan", "Score"]

            for clan_name, fame in predicted_outcomes:
                table.add_row([clan_name, fame])

            embed.add_field(name="Predicted outcome for today", value="```\n" + table.get_string() + "```")
            embed.set_footer(text="Assuming each clan uses all remaining decks at a 50% winrate")

            await ctx.send(embed=embed)

    @river_race_status.error
    async def river_race_status_error(self, ctx, error):
        if not isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Something went wrong. Command should be formatted as:  !river_race_status")
            raise error


    """
    Command: !set_reminder_time {reminder_time}

    Allow individual users to set their reminder time to US or EU.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def set_reminder_time(self, ctx, reminder_time: str):
        """Set reminder time to either US or EU. US reminders go out at 01:00 UTC. EU reminders go out at 17:00 UTC."""
        time_zone = None
        if reminder_time == "US":
            time_zone = True
        elif reminder_time == "EU":
            time_zone = False
        else:
            await ctx.send("Invalid time zone. Valid reminder times are US or EU")
            return

        db_utils.update_time_zone(ctx.author.id, time_zone)
        await ctx.send("Your reminder time preference has been updated.")

    @set_reminder_time.error
    async def set_reminder_time_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You need to specify a reminder time. Valid reminder times are US or EU")
        elif isinstance(error, commands.errors.CheckFailure):
            return
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_reminder_time <reminder_time>")
            raise error

    
    """
    Command: !vacation

    Toggle the vacation status of the user who issued the command.
    """
    @commands.command()
    @bot_utils.channel_check(TIME_OFF_CHANNEL)
    async def vacation(self, ctx):
        """Toggles vacation status."""
        vacation_status = db_utils.update_vacation_for_user(ctx.author.id)
        vacation_status_string = ("NOT " if not vacation_status else "") + "ON VACATION"
        await ctx.send(f"New vacation status for {ctx.author.mention}: {vacation_status_string}.")

    @vacation.error
    async def vacation_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=TIME_OFF_CHANNEL)
            await ctx.send(f"!vacation command can only be sent in {channel.mention}.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !vacation")
            raise error


    """
    Command: !update

    Update a user in the database.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def update(self, ctx):
        """Update your player name, clan role/affiliation, Discord server role, and Discord nickname."""
        if not await bot_utils.update_member(ctx.author):
            await ctx.send("Something went wrong. Your information has not been updated.")
            return

        if await bot_utils.is_admin(ctx.author):
            await ctx.send("Your information has been updated. As an Admin, you must manually update your Discord nickname if it no longer matches your in-game player name.")
        else:
            await ctx.send("Your information has been updated.")

    @update.error
    async def update_error(self, ctx, error):
        if not isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Something went wrong. You should have gone through the new user and check rules channels before using this command. Command should be formatted as:  !update")
            raise error

    
    """
    Command: !strikes

    Show a user how many strikes they currently have.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def strikes(self, ctx):
        """Get your current strike count."""
        strikes = db_utils.get_strikes(ctx.author.id)
        message = ""

        if strikes == None:
            message = "Error, you were not found in the database."
        else:
            message = f"You currently have {strikes} strikes."

        await ctx.send(message)

    @strikes.error
    async def strikes_error(self, ctx, error):
        if not isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Something went wrong. Command should be formatted as:  !strikes")
            raise error

    
    """
    Command: !stats

    Show a user their river race stats.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def stats(self, ctx):
        """Get your river race performance stats."""
        player_tag = db_utils.get_player_tag(ctx.author.id)
        embed = bot_utils.create_match_performance_embed(ctx.author.display_name, player_tag)
        await ctx.send(embed=embed)

    @stats.error
    async def stats_error(self, ctx, error):
        if not isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Something went wrong. Command should be formatted as:  !stats")
            raise error
