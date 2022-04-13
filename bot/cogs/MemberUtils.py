"""Member Utils cog. Various commands available to all users."""

from discord.ext import commands
from prettytable import PrettyTable
import discord

# Config
from config.config import TIME_OFF_CHANNEL

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils


class MemberUtils(commands.Cog):
    """Miscellaneous utilities for everyone."""

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def river_race_status(self, ctx, show_predictions: bool=False):
        """Send a list of clans in the current river race and how battles they can still do today."""
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
            predicted_outcomes, completed_clans, _ = bot_utils.predict_race_outcome(False, False)
            embed, _, _ = bot_utils.create_prediction_embeds(predicted_outcomes, completed_clans, {}, True)
            await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def predict(self, ctx, use_historical_win_rates: bool, use_historical_deck_usage: bool):
        """
Predict today's river race outcome. If use_historical_win_rates is true, predicted scores will be based on each clan's \
average win rate in this river race, otherwise it will use a win rate of 50% for each clan. If use_historical_deck_usage is \
true, predicted scores will be based on each clan's historical deck usage per day, otherwise it will assume each clan uses \
all possible remaining decks."""
        if not db_utils.is_war_time():
            embed = discord.Embed(title="Predictions can only be made on battle days.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        predicted_outcomes, completed_clans, catch_up_info = bot_utils.predict_race_outcome(use_historical_win_rates,
                                                                                            use_historical_deck_usage)

        predicted_embed, completed_embed, catch_up_embed = bot_utils.create_prediction_embeds(predicted_outcomes,
                                                                                              completed_clans,
                                                                                              catch_up_info,
                                                                                              False)

        await ctx.send(embed=predicted_embed)

        if completed_embed is not None:
            await ctx.send(embed=completed_embed)

        if catch_up_embed is not None:
            await ctx.send(embed=catch_up_embed)


    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def set_reminder_time(self, ctx, reminder_time: str):
        """Set reminder time to either US or EU. US reminders go out at 02:00 UTC. EU reminders go out at 19:00 UTC."""

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


    @commands.command()
    @bot_utils.channel_check(TIME_OFF_CHANNEL)
    async def vacation(self, ctx):
        """Toggle your vacation status."""
        vacation_status = db_utils.update_vacation_for_user(ctx.author.id)

        if vacation_status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())
        
        embed.add_field(name="Vacation status updated",
                        value=f"You are now {'NOT ' if not vacation_status else ''} ON VACATION")

        await ctx.send(embed=embed)


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


    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def strikes(self, ctx):
        """Check how many strikes you have."""
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


    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def stats(self, ctx):
        """Check your river race statistics."""
        player_info = db_utils.find_user_in_db(ctx.author.id)

        if len(player_info) == 0:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value="Your Discord ID is not in the database. This should not happen. Contact a leader if you see this error.")
            await ctx.send(embed=embed)
            return
        else:
            _, player_tag, _ = player_info[0]

        embed = bot_utils.create_match_performance_embed(ctx.author.display_name, player_tag)
        await ctx.send(embed=embed)
