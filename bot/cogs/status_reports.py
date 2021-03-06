"""Status Report cog. Various report commands available to leadership."""

import datetime
from typing import Dict, Union

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Cogs
from cogs.error_handler import ErrorHandler

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.logging_utils import LOG
from utils.util_types import DatabaseDataExtended


class StatusReports(commands.Cog):
    """Commands to get different status reports."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def decks_report(self, ctx: commands.Context):
        """Get a report of players with remaining battles today."""
        LOG.command_start(ctx)
        usage_info = clash_utils.get_remaining_decks_today_dicts()
        users_on_vacation = db_utils.get_users_on_vacation()

        if not usage_info:
            embed = discord.Embed(title="Something went wrong. There might be issues accessing the Clash Royale API right now.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            LOG.command_end("Could not get usage_info")
            return

        embed = discord.Embed(title="Deck Usage Report",
                              description=(f"{usage_info['participants']} players have participated in war today.\n"
                                           f"They have used a total of {200 - usage_info['remaining_decks']} decks."))

        remaining_participants = 50 - usage_info['participants']
        non_warring_active_members = usage_info['active_members_with_no_decks_used']
        if non_warring_active_members > remaining_participants:
            embed.add_field(name="`WARNING`",
                            value=(f"Only {remaining_participants} players can still participate in war today, "
                                   f"but there are currently {non_warring_active_members} active members of the clan that have not "
                                   "used any decks. Some players could be locked out."))

        await ctx.send(embed=embed)

        if len(usage_info['active_members_with_remaining_decks']) > 0:
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info['active_members_with_remaining_decks']:
                table.add_row([player_name, decks_remaining])

            embed = discord.Embed(title="Active members with remaining decks", description="```\n" + table.get_string() + "```")
            await ctx.send(embed=embed)

        if len(usage_info['inactive_members_with_decks_used']) > 0:
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info['inactive_members_with_decks_used']:
                table.add_row([player_name, decks_remaining])

            embed = discord.Embed(title="Former members with remaining decks", description="```\n" + table.get_string() + "```")
            await ctx.send(embed=embed)

        if len(usage_info['locked_out_active_members']) > 0:
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info['locked_out_active_members']:
                table.add_row([player_name, decks_remaining])

            embed=discord.Embed(title="Active members locked out today", description="```\n" + table.get_string() + "```")
            await ctx.send(embed=embed)

        if len(users_on_vacation) > 0:
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_tag, player_name in users_on_vacation.items():
                decks_remaining = 4 - clash_utils.get_user_decks_used_today(player_tag)
                table.add_row([player_name, decks_remaining])

            embed = discord.Embed(title="Members currently on vacation", description="```\n" + table.get_string() + "```")
            await ctx.send(embed=embed)

        LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def medals_report(self, ctx: commands.Context, threshold: int):
        """Get a report of players below the specified medal count."""
        LOG.command_start(ctx, threshold=threshold)
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        users_on_vacation = db_utils.get_users_on_vacation()
        table = PrettyTable()
        table.field_names = ["Member", "Medals"]
        embed = discord.Embed(title="Medals Report")

        for player_name, player_tag, fame in hall_of_shame:
            if player_tag in users_on_vacation:
                continue

            table.add_row([player_name, fame])

        embed.add_field(name="Players below medals threshold", value = "```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Players below medals threshold\n" + "```\n" + table.get_string() + "```")

        LOG.command_end()

    @staticmethod
    async def player_report_helper(ctx: commands.Context, user_data: DatabaseDataExtended):
        """Build player report table and send to channel where command was invoked.

        Args:
            ctx: Context of command being invoked.
            user_data: Data of user to send report about.
        """
        general_info_table = PrettyTable()
        kicks = db_utils.get_kicks(user_data['player_tag'])
        total_kicks = len(kicks)
        last_kicked = "Never"
        if total_kicks > 0:
            last_kicked = kicks[-1]

        general_info_table.add_row(["Player Name", user_data['player_name']])
        general_info_table.add_row(["Player Tag", user_data['player_tag']])
        general_info_table.add_row(["Strikes", user_data['strikes']])
        general_info_table.add_row(["Permanent Strikes", user_data['permanent_strikes']])
        general_info_table.add_row(["Kicks", total_kicks])
        general_info_table.add_row(["Last Kicked", last_kicked])
        general_info_table.add_row(["Discord Name", user_data['discord_name']])
        general_info_table.add_row(["Clan Name", user_data['clan_name']])
        general_info_table.add_row(["Clan Tag", user_data['clan_tag']])
        general_info_table.add_row(["Clan Role", user_data['role'].capitalize()])
        general_info_table.add_row(["On Vacation", "Yes" if user_data['vacation'] else "No"])
        general_info_table.add_row(["Status", user_data['status'].value])

        general_info_embed = discord.Embed(title="Player Report", url=bot_utils.royale_api_url(user_data['player_tag']))
        general_info_embed.add_field(name=f"{user_data['player_name']}'s general info",
                        value = "```\n" + general_info_table.get_string(header=False) + "```")

        await ctx.send(embed=general_info_embed)

        clan_deck_usage = clash_utils.get_deck_usage_today()

        if user_data['player_tag'] not in clan_deck_usage:
            decks_used_today = 0
        else:
            decks_used_today = clan_deck_usage[user_data['player_tag']]

        usage_history_list = bot_utils.break_down_usage_history(user_data['usage_history'],
                                                                datetime.datetime.now(datetime.timezone.utc))

        deck_usage_history_table = PrettyTable()
        deck_usage_history_table.field_names = ["Day", "Decks Used"]
        deck_usage_history_table.add_row(["Today", decks_used_today])

        for decks_used, date in usage_history_list:
            deck_usage_history_table.add_row([date, decks_used])

        deck_usage_embed = discord.Embed(title=f"{user_data['player_name']}'s deck usage history",
                                         description="```\n" + deck_usage_history_table.get_string() + "```")

        await ctx.send(embed=deck_usage_embed)

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def player_report(self, ctx: commands.Context, member: discord.Member):
        """Get information about a member."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return

        _, player_tag, _ = player_info[0]
        user_data = db_utils.get_user_data(player_tag)

        if user_data is None:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return

        await self.player_report_helper(ctx, user_data)
        LOG.command_end()

    @player_report.error
    async def player_report_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!player_report error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, player_report_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                user_data = db_utils.get_user_data(player_tag)

                if user_data is None:
                    embed = ErrorHandler.missing_db_info(player_name)
                    await ctx.send(embed=embed)
                    LOG.command_end("Attempted to get data of Discord member not in database")
                    return

                await self.player_report_helper(ctx, user_data)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "player_report")
                await ctx.send(embed=embed)
            
            LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def stats_report(self, ctx: commands.Context, member: discord.Member):
        """Get specified user's river race statistics."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            return

        _, player_tag, _ = player_info[0]

        embed = bot_utils.create_match_performance_embed(member.display_name, player_tag)
        await ctx.send(embed=embed)
        LOG.command_end()

    @stats_report.error
    async def stats_report_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!stats_report error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, stats_report_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                embed = bot_utils.create_match_performance_embed(player_name, player_tag)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "stats_report")

            await ctx.send(embed=embed)
            LOG.command_end()
