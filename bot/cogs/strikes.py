"""Strikes cog. Various commands to update strike counts."""

from typing import Tuple

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Cogs
from cogs.error_handler import ErrorHandler

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.channel_utils import CHANNEL
from utils.logging_utils import LOG


class Strikes(commands.Cog):
    """Commands for updating strike counts."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @staticmethod
    async def strike_helper(ctx: commands.Context, player_name: str, player_tag: str, delta: int, member: discord.Member=None):
        """Give or remove a strike from a user and send confirmation messages back to leader commands and strikes channels.

        Args:
            player_name: User's in game name.
            player_tag: User to update strikes for.
            delta: Number of strikes to give or remove.
            member (optional): Member object of user if they are on Discord.
        """
        old_strikes, new_strikes, old_permanent_strikes, new_permanent_strikes = db_utils.update_strikes(player_tag, delta)

        if old_strikes is None:
            embed = discord.Embed(title=f"Something went wrong while updating {player_name}'s strikes. This should not happen.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        message = "has received a strike" if delta > 0 else "has had a strike removed"
        embed = discord.Embed(title="Strikes Updated", color=discord.Color.green())
        embed.add_field(name=player_name,
                        value=(f"```Strikes: {old_strikes} -> {new_strikes}\n"
                               f"Permanent Strikes: {old_permanent_strikes} -> {new_permanent_strikes}```"))
        await ctx.send(embed=embed)

        if member is None:
            await CHANNEL.strikes().send(f"{player_name} {message}.  {old_strikes} -> {new_strikes}")
        else:
            await CHANNEL.strikes().send(f"{member.mention} {message}.  {old_strikes} -> {new_strikes}")

    @staticmethod
    async def multiple_strikes_helper(ctx: commands.Context, delta: int, users: Tuple[str]):
        """Give or remove a strike to multiple users. Send a confirmation back to ctx channel and strikes channel.

        Args:
            ctx: Context used to send confirmation message back to.
            delta: Number of strikes to give or remove.
            users: Names of users to give or remove strikes to.
        """
        if not users:
            confirmation_embed = discord.Embed(title="You did not specify any users.", color=discord.Color.red())
        else:
            confirmation_embed = discord.Embed(title="Strike results", color=discord.Color.green())

        strikes_message = ""
        message = "has received a strike" if delta > 0 else "has had a strike removed"

        for user in users:
            converter = commands.MemberConverter()

            try:
                member = await converter.convert(ctx, user)
                player_info = db_utils.find_user_in_db(member.id)
            except commands.errors.MemberNotFound:
                player_info = db_utils.find_user_in_db(user)

            if not player_info:
                confirmation_embed.add_field(name=user, value="```Could not be found in database```", inline=False)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                old_strikes, new_strikes, old_permanent_strikes, new_permanent_strikes = db_utils.update_strikes(player_tag, delta)
                confirmation_embed.add_field(name=f"{player_name} updated",
                                             value=(f"```Strikes: {old_strikes} -> {new_strikes}\n"
                                                    f"Permanent Strikes: {old_permanent_strikes} -> {new_permanent_strikes}```"),
                                             inline=False)
                discord_id = db_utils.get_member_id(player_tag)
                member = None

                if discord_id is not None:
                    member = ctx.guild.get_member(discord_id)

                if member is None:
                    strikes_message += f"{player_name} {message}. {old_strikes} -> {new_strikes}\n"
                else:
                    strikes_message += f"{member.mention} {message}. {old_strikes} -> {new_strikes}\n"
            else:
                duplicates_str = ""

                for player_name, player_tag, clan_name in player_info:
                    duplicates_str += f"Name: {player_name}  Tag: {player_tag}  Clan: {clan_name}\n"

                confirmation_embed.add_field(name="Duplicate names detected. Try using their player tag instead of name.",
                                             value=f"```{duplicates_str}```",
                                             inline=False)

        if strikes_message:
            await CHANNEL.strikes().send(strikes_message)

        await ctx.send(embed=confirmation_embed)



    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def give_strike(self, ctx: commands.Context, member: discord.Member):
        """Increment specified user's strikes by 1."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return

        _, player_tag, _ = player_info[0]
        await self.strike_helper(ctx, member.display_name, player_tag, 1, member)
        LOG.command_end()

    @give_strike.error
    async def give_strike_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!give_strike error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, give_strike_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                discord_id = db_utils.get_member_id(player_tag)
                member = ctx.guild.get_member(discord_id)
                await self.strike_helper(ctx, player_name, player_tag, 1, member)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "give_strike")
                await ctx.send(embed=embed)

            LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def give_strikes(self, ctx: commands.Context, *members):
        """Increment strikes by 1 for all specified users."""
        await self.multiple_strikes_helper(ctx, 1, members)

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def remove_strike(self, ctx: commands.Context, member: discord.Member):
        """Decrement specified user's strikes by 1."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return
        else:
            _, player_tag, _ = player_info[0]

        await self.strike_helper(ctx, member.display_name, player_tag, -1, member)
        LOG.command_end()

    @remove_strike.error
    async def remove_strike_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!remove_strike error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, remove_strike_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                discord_id = db_utils.get_member_id(player_tag)
                member = ctx.guild.get_member(discord_id)
                await self.strike_helper(ctx, player_name, player_tag, -1, member)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "remove_strike")
                await ctx.send(embed=embed)

            LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def remove_strikes(self, ctx: commands.Context, *members):
        """Decrement strikes by 1 for all specified users."""
        await self.multiple_strikes_helper(ctx, -1, members)

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def reset_all_strikes(self, ctx: commands.Context):
        """Reset everyone's strikes to 0. Permanent strikes are not affected."""
        LOG.command_start(ctx)
        db_utils.reset_strikes()

        strikes_channel_embed = discord.Embed(color=discord.Color.green())
        strikes_channel_embed.add_field(name="Strikes Reset", value="All users have been reset to 0 strikes")
        await CHANNEL.strikes().send(embed=strikes_channel_embed)

        confirmation_embed = discord.Embed(title="Strikes successfully reset to 0.", color=discord.Color.green())
        await ctx.send(embed=confirmation_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def strikes_report(self, ctx: commands.Context):
        """Get a report of players with strikes."""
        LOG.command_start(ctx)
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
                active_name = active_members[player_tag]['player_name']
                active_table.add_row([active_name, strikes])
            else:
                non_active_members_have_strikes = True
                non_active_table.add_row([player_name, strikes])

        if active_members_have_strikes:
            active_embed = discord.Embed(title="Active members with strikes",
                                         description="```\n" + active_table.get_string() + "```")

            try:
                await ctx.send(embed=active_embed)
            except:
                await ctx.send("Active members with strikes\n" + "```\n" + active_table.get_string() + "```")

        if non_active_members_have_strikes:
            non_active_embed = discord.Embed(title="Users not in clan with strikes",
                                             description="```\n" + non_active_table.get_string() + "```")

            try:
                await ctx.send(embed=non_active_embed)
            except:
                await ctx.send("Users not in clan with strikes\n" + "```\n" + non_active_table.get_string() + "```")

        if (not active_members_have_strikes) and (not non_active_members_have_strikes):
            embed = discord.Embed(title="Strikes Report", description="No users currently have strikes")
            await ctx.send(embed=embed)

        LOG.command_end()


    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def upcoming_strikes(self, ctx: commands.Context):
        """Get a list of users who will receive strikes for lack of participation in the current river race."""
        LOG.command_start(ctx)
        upcoming_strikes_list = bot_utils.upcoming_strikes(True)
        embed_one = discord.Embed(title="Upcoming Strikes", color=discord.Color.green())
        embed_two = discord.Embed(title="Upcoming Strikes", color=discord.Color.green())
        send_second_embed = False
        field_count = 0
        strikes_enabled = db_utils.get_strike_status()

        if not strikes_enabled:
            embed_one.set_footer(text="Automated strikes are currently disabled.")
            embed_two.set_footer(text="Automated strikes are currently disabled.")

        if not upcoming_strikes_list:
            embed = discord.Embed(title="No players are currently set to receive strikes.", color=discord.Color.green())

            if not strikes_enabled:
                embed.set_footer(text="Automated strikes are currently disabled.")

            await ctx.send(embed=embed)
            LOG.command_end()
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

        LOG.command_end()
