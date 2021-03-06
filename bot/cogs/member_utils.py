"""Member Utils cog. Various commands available to all users."""

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.logging_utils import LOG
from utils.util_types import ReminderTime


class MemberUtils(commands.Cog):
    """Miscellaneous utilities for everyone."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def river_race_status(self, ctx: commands.Context, show_predictions: bool=False):
        """Send a list of clans in the current river race and how many battles they can still do today."""
        LOG.command_start(ctx, show_predictions=show_predictions)
        clans = clash_utils.get_clan_decks_remaining()
        table = PrettyTable()
        table.field_names = ["Clan", "Decks"]

        for clan, decks_remaining in clans:
            _, clan_name = clan
            table.add_row([clan_name, decks_remaining])

        embed = discord.Embed(title="Remaining decks for each clan",
                              description="```\n" + table.get_string() + "```",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

        if show_predictions and db_utils.is_war_time():
            predicted_outcomes, completed_clans, _ = bot_utils.predict_race_outcome(True, False)
            embed, _, _ = bot_utils.create_prediction_embeds(predicted_outcomes, completed_clans, {})
            await ctx.send(embed=embed)

        LOG.command_end()

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def predict(self, ctx: commands.Context, use_historical_win_rates: bool, use_historical_deck_usage: bool):
        """
Predict today's river race outcome. If use_historical_win_rates is true, predicted scores will be based on each clan's \
average win rate in this river race, otherwise it will use a win rate of 50% for each clan. If use_historical_deck_usage is \
true, predicted scores will be based on each clan's historical deck usage per day, otherwise it will assume each clan uses \
all possible remaining decks."""
        LOG.command_start(ctx,
                          use_historical_win_rates=use_historical_win_rates,
                          use_historical_deck_usage=use_historical_deck_usage)

        if not db_utils.is_war_time():
            embed = discord.Embed(title="Predictions can only be made on battle days.", color=discord.Color.red())
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to make prediction during non-war time")
            return

        predicted_outcomes, completed_clans, catch_up_info = bot_utils.predict_race_outcome(use_historical_win_rates,
                                                                                            use_historical_deck_usage)

        predicted_embed, completed_embed, catch_up_embed = bot_utils.create_prediction_embeds(predicted_outcomes,
                                                                                              completed_clans,
                                                                                              catch_up_info)

        await ctx.send(embed=predicted_embed)

        if completed_embed is not None:
            await ctx.send(embed=completed_embed)

        if catch_up_embed is not None:
            await ctx.send(embed=catch_up_embed)

        LOG.command_end()

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def set_reminder_time(self, ctx: commands.Context, reminder_time: str):
        """Set reminder time to either US or EU. US reminders go out at 02:00 UTC. EU reminders go out at 19:00 UTC."""
        LOG.command_start(ctx, reminder_time=reminder_time)
        time_zone: ReminderTime
        invalid_embed = discord.Embed(color=discord.Color.red())
        invalid_embed.add_field(name="Invalid time zone", value="Valid reminder times are `US` or `EU`")

        try:
            time_zone = ReminderTime(reminder_time.upper())
        except ValueError:
            await ctx.send(embed=invalid_embed)
            LOG.command_end("Invalid time zone")
            return

        if time_zone == ReminderTime.ALL:
            await ctx.send(embed=invalid_embed)
            LOG.command_end("Invalid time zone")
            return

        db_utils.update_time_zone(ctx.author.id, time_zone)
        success_embed = discord.Embed(color=discord.Color.green())
        success_embed.add_field(name="Your reminder time has updated", value=f"You will now receive {reminder_time} reminders")
        await ctx.send(embed=success_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.time_off_channel_check()
    async def vacation(self, ctx: commands.Context):
        """Toggle your vacation status."""
        LOG.command_start(ctx)
        vacation_status = db_utils.update_vacation_for_user(ctx.author.id)

        if vacation_status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())

        embed.add_field(name="Vacation status updated",
                        value=f"You are now {'NOT ' if not vacation_status else ''} ON VACATION")

        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def update(self, ctx: commands.Context):
        """Update your player name, clan role/affiliation, Discord server role, and Discord nickname."""
        LOG.command_start(ctx)
        if not await bot_utils.update_member(ctx.author):
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value="This is likely due to the Clash Royale API being down. Your information has not been updated.")
        elif bot_utils.is_admin(ctx.author):
            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name="Your information has been updated",
                            value=("ClashBot does not have permission to modify Admin nicknames. "
                                   "You must do this yourself if your player name has changed."))
        else:
            embed = discord.Embed(title="Your information has been updated",
                                  color=discord.Color.green())

        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def strikes(self, ctx: commands.Context):
        """Check how many strikes you have."""
        LOG.command_start(ctx)
        strikes = db_utils.get_strikes(ctx.author.id)

        if strikes is None:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=("Your Discord ID is not in the database. This should not happen. "
                                   "Contact a leader if you see this error."))
            LOG.error("Discord member not found in database")
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
        LOG.command_end()

    @commands.command()
    @bot_utils.not_welcome_or_rules_check()
    async def stats(self, ctx: commands.Context):
        """Check your river race statistics."""
        LOG.command_start(ctx)
        player_info = db_utils.find_user_in_db(ctx.author.id)

        if not player_info:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=("Your Discord ID is not in the database. This should not happen. "
                                   "Contact a leader if you see this error."))
            LOG.error("Discord member not found in database")
        else:
            _, player_tag, _ = player_info[0]
            embed = bot_utils.create_match_performance_embed(ctx.author.display_name, player_tag)

        await ctx.send(embed=embed)
        LOG.command_end()
