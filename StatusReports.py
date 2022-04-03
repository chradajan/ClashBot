from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import datetime
import db_utils
import discord
import ErrorHandler

class StatusReports(commands.Cog):
    """Commands to get different status reports."""

    def __init__(self, bot):
        self.bot = bot


        """
    Command: !decks_report

    Get a list of users and their number of decks remaining today.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def decks_report(self, ctx):
        """Get a report of players with decks remaining today."""
        usage_info = clash_utils.get_remaining_decks_today_dicts()
        users_on_vacation = db_utils.get_users_on_vacation()

        if len(usage_info) == 0:
            await ctx.send("Something went wrong. There might be issues accessing the Clash Royale API right now.")

        embed = discord.Embed(title="Deck Usage Report",
                              description=f"{usage_info['participants']} players have participated in war today.\nThey have used a total of {200 - usage_info['remaining_decks']} decks.")

        remaining_participants = 50 - usage_info["participants"]
        non_warring_active_members = usage_info["active_members_with_no_decks_used"]
        if non_warring_active_members > remaining_participants:
            embed.add_field(name="`WARNING`", value=f"Only {remaining_participants} players can still participate in war today, but there are currently {non_warring_active_members} active members of the clan that have not used any decks. Some players could be locked out.")

        await ctx.send(embed=embed)

        if len(usage_info["active_members_with_remaining_decks"]) > 0:
            embed = discord.Embed()
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info["active_members_with_remaining_decks"]:
                table.add_row([player_name, decks_remaining])

            embed.add_field(name="Active members with remaining decks", value = "```\n" + table.get_string() + "```")

            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send("Active members with remaining decks\n" + "```\n" + table.get_string() + "```")

        if len(usage_info["inactive_members_with_decks_used"]) > 0:
            embed = discord.Embed()
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info["inactive_members_with_decks_used"]:
                table.add_row([player_name, decks_remaining])

            embed.add_field(name="Former members with remaining decks", value = "```\n" + table.get_string() + "```")

            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send("Former members with remaining decks\n" + "```\n" + table.get_string() + "```")

        if len(usage_info["locked_out_active_members"]) > 0:
            embed = discord.Embed()
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_name, decks_remaining in usage_info["locked_out_active_members"]:
                table.add_row([player_name, decks_remaining])

            embed.add_field(name="Active members locked out today", value = "```\n" + table.get_string() + "```")

            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send("Active members locked out today\n" + "```\n" + table.get_string() + "```")

        if len(users_on_vacation) > 0:
            embed = discord.Embed()
            table = PrettyTable()
            table.field_names = ["Member", "Decks"]

            for player_tag, player_name in users_on_vacation.items():
                decks_remaining = 4 - clash_utils.get_user_decks_used_today(player_tag)
                table.add_row([player_name, decks_remaining])

            embed.add_field(name="Members currently on vacation", value = "```\n" + table.get_string() + "```")

            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send("Members currently on vacation\n" + "```\n" + table.get_string() + "```")


    """
    Command: !medals_report {threshold}

    Get a list of users below a specified fame threshold.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def medals_report(self, ctx, threshold: int):
        """Get a report of players below the specified medal count. Ignores users on vacation."""
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


    async def player_report_helper(self, ctx, user_data: dict):
        general_info_table = PrettyTable()
        kicks = db_utils.get_kicks(user_data["player_tag"])
        total_kicks = len(kicks)
        last_kicked = "Never"
        if total_kicks > 0:
            last_kicked = kicks[-1]

        general_info_table.add_row(["Player Name", user_data["player_name"]])
        general_info_table.add_row(["Player Tag", user_data["player_tag"]])
        general_info_table.add_row(["Strikes", user_data["strikes"]])
        general_info_table.add_row(["Permanent Strikes", user_data["permanent_strikes"]])
        general_info_table.add_row(["Kicks", total_kicks])
        general_info_table.add_row(["Last Kicked", last_kicked])
        general_info_table.add_row(["Discord Name", user_data["discord_name"]])
        general_info_table.add_row(["Clan Name", user_data["clan_name"]])
        general_info_table.add_row(["Clan Tag", user_data["clan_tag"]])
        general_info_table.add_row(["Clan Role", user_data["clan_role"].capitalize()])
        general_info_table.add_row(["On Vacation", "Yes" if user_data["vacation"] else "No"])
        general_info_table.add_row(["Status", user_data["status"]])

        url = f"https://royaleapi.com/player/{user_data['player_tag'][1:]}"
        embed = discord.Embed(title="Player Report", url=url)
        embed.add_field(name=f"{user_data['player_name']}'s general info", value = "```\n" + general_info_table.get_string(header=False) + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send(f"{user_data['player_name']}'s general info" + "\n" + "```\n" + general_info_table.get_string(header=False) + "```")

        decks_used_today = clash_utils.get_user_decks_used_today(user_data["player_tag"])
        if decks_used_today == None:
            decks_used_today = 0

        usage_history_list = bot_utils.break_down_usage_history(user_data["usage_history"], datetime.datetime.now(datetime.timezone.utc))

        deck_usage_history_table = PrettyTable()
        deck_usage_history_table.field_names = ["Day", "Decks Used"]

        for decks_used, date in usage_history_list:
            deck_usage_history_table.add_row([date, decks_used])

        embed = discord.Embed()
        embed.set_footer(text=f"{user_data['player_name']} has used {decks_used_today} decks today.")
        embed.add_field(name=f"{user_data['player_name']}'s deck usage history", value = "```\n" + deck_usage_history_table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send(f"{user_data['player_name']} has used {decks_used_today} decks today." + "\n\n" +\
                            f"{user_data['player_name']}'s deck usage history" + "\n" + "```\n" + deck_usage_history_table.get_string() + "```")


    """
    Command: !player_report {member}

    Get information about a member in the server.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def player_report(self, ctx, member: discord.Member):
        """Get information about a member."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag == None:
            await ctx.send(f"{member.display_name} was found on Discord but not in the database. Make sure they've entered their player tag in the welcome channel.")
            return

        user_data = db_utils.get_user_data(player_tag)

        if user_data == None:
            await ctx.send(f"{member.display_name} was found on Discord but not in the database. Make sure they've entered their player tag in the welcome channel.")
            return
        
        await self.player_report_helper(ctx, user_data)

    @player_report.error
    async def player_report_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            user_data = db_utils.get_user_data(error.argument)
            if user_data is not None:
                await self.player_report_helper(ctx, user_data)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)


    """
    Command: !stats_report {member}

    Get war stats of specified user.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def stats_report(self, ctx, member: discord.Member):
        """Get war stats of specified user."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag is None:
            await ctx.send(f"{member.display_name} was found on Discord but not in the database. Make sure they've entered their player tag in the welcome channel.")
            return

        embed = bot_utils.create_match_performance_embed(member.display_name, player_tag)
        await ctx.send(embed=embed)

    @stats_report.error
    async def stats_report_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)
            if player_tag is not None:
                embed = bot_utils.create_match_performance_embed(error.argument, player_tag)
                await ctx.send(embed=embed)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
