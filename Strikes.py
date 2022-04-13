from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord
import ErrorHandler

class Strikes(commands.Cog):
    """Commands for updating strike counts."""

    def __init__(self, bot):
        self.bot = bot


    async def strike_helper(self, ctx, player_name: str, player_tag: str, delta: int, member: discord.Member=None):
        """
        Give or remove a strike from a user and send confirmation messages back to leader commands and strikes channels.

        Args:
            player_name(str): User's in game name.
            player_tag(str): User to update strikes for.
            delta(int): Number of strikes to give or remove.
            member(discord.Member): Member object of user if they are on Discord.
        """
        old_strike_count, new_strike_count, old_permanent_strikes, new_permanent_strikes = db_utils.give_strike(player_tag, delta)

        if old_strike_count is None:
            await ctx.send(f"Something went wrong while updating {player_name}'s strikes. This should not happen.")
            return

        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        message = "has received a strike" if delta > 0 else "has had a strike removed"

        embed = discord.Embed(title="Strikes Updated", color=discord.Color.green())
        embed.add_field(name=player_name, value=f"```Strikes: {old_strike_count} -> {new_strike_count}\nPermanent Strikes: {old_permanent_strikes} -> {new_permanent_strikes}```")
        await ctx.send(embed=embed)

        if member is None:
            await channel.send(f"{player_name} {message}.  {old_strike_count} -> {new_strike_count}")
        else:
            await channel.send(f"{member.mention} {message}.  {old_strike_count} -> {new_strike_count}")


    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def give_strike(self, ctx, member: discord.Member):
        """Increment specified user's strikes by 1."""
        player_info = db_utils.find_user_in_db(member.id)

        if len(player_info) == 0:
            embed = ErrorHandler.ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            return
        else:
            _, player_tag, _ = player_info[0]

        await self.strike_helper(ctx, member.display_name, player_tag, 1, member)

    @give_strike.error
    async def give_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)

            if len(player_info) == 0:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                await self.strike_helper(ctx, player_name, player_tag, 1)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "give_strike")
                await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def remove_strike(self, ctx, member: discord.Member):
        """Decrement specified user's strikes by 1."""
        player_info = db_utils.find_user_in_db(member.id)

        if len(player_info) == 0:
            embed = ErrorHandler.ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            return
        else:
            _, player_tag, _ = player_info[0]

        await self.strike_helper(ctx, member.display_name, player_tag, -1, member)

    @remove_strike.error
    async def remove_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)

            if len(player_info) == 0:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                await self.strike_helper(ctx, player_name, player_tag, -1)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "remove_strike")
                await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_all_strikes(self, ctx):
        """Reset everyone's strikes to 0. Permanent strikes are not affected."""
        db_utils.reset_strikes()

        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        strikes_channel_embed = discord.Embed(color=discord.Color.green())
        strikes_channel_embed.add_field(name="Strikes Reset", value="All users have been reset to 0 strikes")
        await channel.send(embed=strikes_channel_embed)

        commands_channel_embed = discord.Embed(title="Strikes successfully reset to 0.", color=discord.Color.green())
        await ctx.send(embed=commands_channel_embed)


    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def strikes_report(self, ctx):
        """Get a report of players with strikes."""
        strikes = db_utils.get_users_with_strikes()
        active_members = clash_utils.get_active_members_in_clan()

        active_table = PrettyTable()
        active_table.field_names = ["Member", "Strikes"]
        active_members_have_strikes = False

        non_active_table = PrettyTable()
        non_active_table.field_names = ["Member", "Strikes"]
        non_active_members_have_strikes = False

        for player_tag, player_name, strikes in strikes:
            if player_tag in active_members:
                active_members_have_strikes = True
                active_name = active_members[player_tag]["name"]
                active_table.add_row([active_name, strikes])
            else:
                non_active_members_have_strikes = True
                non_active_table.add_row([player_name, strikes])

        if active_members_have_strikes:
            active_embed = discord.Embed()
            active_embed.add_field(name="Active members with strikes", value="```\n" + active_table.get_string() + "```")

            try:
                await ctx.send(embed=active_embed)
            except:
                await ctx.send("Active members with strikes\n" + "```\n" + active_table.get_string() + "```")

        if non_active_members_have_strikes:
            non_active_embed = discord.Embed()
            non_active_embed.add_field(name="Users not in clan with strikes", value="```\n" + non_active_table.get_string() + "```")

            try:
                await ctx.send(embed=non_active_embed)
            except:
                await ctx.send("Active members with strikes\n" + "```\n" + non_active_table.get_string() + "```")

        if (not active_members_have_strikes) and (not non_active_members_have_strikes):
            embed = discord.Embed()
            embed.add_field(name="Strikes Report", value="No users currently have strikes")
            await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def upcoming_strikes(self, ctx):
        """Get a list of users who will receive strikes for lack of participation in the current river race."""
        upcoming_strikes_list = bot_utils.upcoming_strikes(True)
        embed_one = discord.Embed(title="Upcoming Strikes", color=discord.Color.green())
        embed_two = discord.Embed(title="Upcoming Strikes", color=discord.Color.green())
        send_second_embed = False
        field_count = 0
        strikes_enabled = db_utils.get_strike_status()

        if not strikes_enabled:
            embed_one.set_footer(text="Automated strikes are currently disabled.")
            embed_two.set_footer(text="Automated strikes are currently disabled.")

        if len(upcoming_strikes_list) == 0:
            embed = discord.Embed(title="No players are currently set to receive strikes.", color=discord.Color.green())

            if not strikes_enabled:
                embed.set_footer(text="Automated strikes are currently disabled.")

            await ctx.send(embed=embed)
            return

        for player_name, _, decks_used, decks_required, strikes in upcoming_strikes_list:
            if field_count < 25:
                embed_one.add_field(name=player_name,
                                    value=f"```Decks: {decks_used}/{decks_required}\nStrikes: {strikes} -> {strikes+1}```",
                                    inline=False)
                field_count += 1
            else:
                embed_two.add_field(name=player_name,
                                    value=f"```Decks: {decks_used}/{decks_required}\nStrikes: {strikes} -> {strikes+1}```",
                                    inline=False)
                send_second_embed = True

        await ctx.send(embed=embed_one)

        if send_second_embed:
            await ctx.send(embed=embed_two)
