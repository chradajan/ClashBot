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


    """
    Command: !set_reminder_time {reminder_time}

    Allow individual users to set their reminder time to US or EU.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def set_reminder_time(self, ctx, reminder_time: str):
        """Set reminder time to either US or EU. US reminders go out at 01:00 UTC. EU reminders go out at 17:00 UTC."""

        time_zone: bot_utils.ReminderTime
        invalid_embed = discord.Embed(color=discord.Color.red())
        invalid_embed.add_field(name="Invalid time zone", value="Valid reminder times are `US` or `EU`")

        try:
            time_zone = bot_utils.ReminderTime(reminder_time.upper())
        except ValueError:
            await ctx.send(embed=invalid_embed)
            return

        if time_zone == bot_utils.ReminderTime.ALL:
            await ctx.send(embed=invalid_embed)
            return

        db_utils.update_time_zone(ctx.author.id, time_zone)
        success_embed = discord.Embed(color=discord.Color.green())
        success_embed.add_field(name="Your reminder time has updated", value=f"You will now receive {reminder_time} reminders")
        await ctx.send(embed=success_embed)


    """
    Command: !vacation

    Toggle the vacation status of the user who issued the command.
    """
    @commands.command()
    @bot_utils.channel_check(TIME_OFF_CHANNEL)
    async def vacation(self, ctx):
        """Toggles vacation status."""
        vacation_status = db_utils.update_vacation_for_user(ctx.author.id)

        if vacation_status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())
        
        embed.add_field(name="Vacation status updated",
                        value=f"You are now {'NOT ' if not vacation_status else ''} ON VACATION")

        await ctx.send(embed=embed)


    """
    Command: !update

    Update a user in the database.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def update(self, ctx):
        """Update your player name, clan role/affiliation, Discord server role, and Discord nickname."""
        if not await bot_utils.update_member(ctx.author):
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value="This is likely due to the Clash Royale API being down. Your information has not been updated.")
        elif await bot_utils.is_admin(ctx.author):
            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name="Your information has been updated",
                            value="ClashBot does not have permission to modify Admin nicknames. You must do this yourself if your player name has changed.")
        else:
            embed = discord.Embed(title="Your information has been updated",
                                  color=discord.Color.green())

        await ctx.send(embed=embed)


    """
    Command: !strikes

    Show a user how many strikes they currently have.
    """
    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def strikes(self, ctx):
        """Get your current strike count."""
        strikes = db_utils.get_strikes(ctx.author.id)

        if strikes is None:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value="You were not found in the database.")
        else:
            if strikes == 0:
                color = discord.Color.green()
            elif strikes == 1:
                color = 0xFFFF00
            else:
                color = discord.Color.red()

            embed = discord.Embed(title=f"You have {strikes} strikes",
                                  color=color)

        await ctx.send(embed=embed)


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
