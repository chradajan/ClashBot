"""User updates cog. Various commands for leadership to update Discord members."""

from discord.ext import commands
import discord

# Cogs
from cogs.ErrorHandler import ErrorHandler

# Config
from config.config import (
    ADMIN_ROLE_NAME,
    CHECK_RULES_ROLE_NAME,
    NEW_ROLE_NAME,
    COMMANDS_CHANNEL
)

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils

class UserUpdates(commands.Cog):
    """Commands for updating/resetting users."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def reset_user_helper(member: discord.Member):
        if member.bot:
            return

        roles_to_remove = list(bot_utils.NORMAL_ROLES.values())
        roles_to_remove.append(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME])

        db_utils.remove_user(member.id)


    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def update_user(self, ctx, member: discord.Member, player_tag: str=None):
        """Update a member. Specify a player_tag if they need a new one, or leave it blank to update with their current player tag. Updates player name, clan role/affiliation, Discord server role, and Discord nickname."""
        if not await bot_utils.update_member(member, player_tag):
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=f"This is likely due to the Clash Royale API being down. {member.display_name}'s information has not been updated.")
        elif await bot_utils.is_admin(member):
            embed = discord.Embed(color=discord.Color.green())
            embed.add_field(name=f"{member.display_name}'s information has been updated",
                            value=f"ClashBot does not have permission to modify Admin nicknames. {member.display_name} must do this themself if their player name has changed.")
        else:
            embed = discord.Embed(title=f"{member.display_name}'s information has been updated",
                                  color=discord.Color.green())

        await ctx.send(embed=embed)

    @update_user.error
    async def update_user_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            embed = ErrorHandler.invoke_error_embed("Another player on this server is already associated with the player tag you entered.")
            await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_user(self, ctx, member: discord.Member):
        """Admin only. Delete selected user from database. Set their role to New."""
        await self.reset_user_helper(member)
        embed = discord.Embed(title=f"{member.display_name} has been reset", color=discord.Color.green())
        await ctx.send(embed=embed)


    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.disallowed_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_all_users(self, ctx, confirmation: str):
        """Deletes all users from database, removes roles, and assigns New role. Leaders retain Leader role. Leaders must still resend player tag in welcome channel and react to rules message."""
        confirmation_message = "Yes, I really want to drop all players from the database and reset roles."

        if (confirmation != confirmation_message):
            await ctx.send("Users NOT reset. Must type the following confirmation message exactly, in quotes, along with reset_all_users command:\n" + confirmation_message)
            return

        await ctx.send("Deleting all users from database... This might take a couple minutes.")

        db_utils.remove_all_users()

        for member in ctx.guild.members:
            await self.reset_user_helper(member)

        await bot_utils.send_rules_message(ctx, self.bot.user)

        admin_role = bot_utils.SPECIAL_ROLES[ADMIN_ROLE_NAME]
        await ctx.send(f"All users have been reset. If you are a {admin_role.mention}, please send your player tag in the welcome channel to be re-added to the database. Then, react to the rules message to automatically get all roles back. Finally, update your Discord nickname to match your in-game username.")
