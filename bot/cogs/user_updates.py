"""User updates cog. Various commands for leadership to update Discord members."""

import discord
from discord.ext import commands

# Cogs
from cogs.error_handler import ErrorHandler

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils
from utils.logging_utils import LOG
from utils.role_utils import ROLE


class UserUpdates(commands.Cog):
    """Commands for updating/resetting users."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @staticmethod
    async def reset_user_helper(member: discord.Member):
        """Move a user back to the welcome channel.

        Args:
            member: Member to reset.
        """
        if member.bot:
            return

        roles_to_remove = ROLE.normal_roles()
        roles_to_remove.append(ROLE.check_rules())
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(ROLE.new())
        db_utils.remove_user(member.id)

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def update_user(self, ctx: commands.Context, member: discord.Member, player_tag: str=None):
        """Update a member. Optionally specify a player tag to associate the member with that instead of their current one."""
        LOG.command_start(ctx, member=member, player_tag=player_tag)

        if not await bot_utils.update_member(member, player_tag):
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=("This is likely due to the Clash Royale API being down. "
                                   f"{member.display_name}'s information has not been updated."))
        elif bot_utils.is_admin(member):
            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name=f"{member.display_name}'s information has been updated",
                            value=("ClashBot does not have permission to modify Admin nicknames. "
                                   f"{member.display_name} must do this themself if their player name has changed."))
        else:
            embed = discord.Embed(title=f"{member.display_name}'s information has been updated", color=discord.Color.green())

        await ctx.send(embed=embed)
        LOG.command_end()

    @update_user.error
    async def update_user_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!update_user error handler."""
        if isinstance(error, commands.errors.CommandInvokeError):
            embed = ErrorHandler.invoke_error_embed(("Another player on this server is already associated "
                                                     "with the player tag you entered."))
            await ctx.send(embed=embed)
            LOG.exception(error)

    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.commands_channel_check()
    async def reset_user(self, ctx: commands.Context, member: discord.Member):
        """Reset a user back to the welcome channel."""
        LOG.command_start(ctx, member=member)
        await self.reset_user_helper(member)
        embed = discord.Embed(title=f"{member.display_name} has been reset", color=discord.Color.green())
        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.disallowed_command_check()
    @bot_utils.commands_channel_check()
    async def reset_all_users(self, ctx: commands.Context, confirmation: str):
        """Deletes all users from database and resets everyone back to the welcome channel."""
        LOG.command_start(ctx, confirmation=confirmation)
        confirmation_message = "Yes, I really want to drop all players from the database and reset roles."

        if confirmation != confirmation_message:
            await ctx.send(("Users NOT reset. Must type the following confirmation message exactly, "
                            "in quotes, along with reset_all_users command:\n"
                            f"{confirmation_message}"))
            LOG.command_end("Bad confirmation")
            return

        await ctx.send("Deleting all users from database... This might take a couple minutes.")
        db_utils.remove_all_users()

        for member in ctx.guild.members:
            await self.reset_user_helper(member)

        await bot_utils.send_rules_message(self.bot.user)
        await ctx.send((f"All users have been reset. If you are a {ROLE.admin().mention}, please send your player tag in the "
                        "welcome channel to be re-added to the database. Then, react to the rules message to automatically get all "
                        "roles back. Finally, update your Discord nickname to match your in-game username."))
        LOG.command_end()
