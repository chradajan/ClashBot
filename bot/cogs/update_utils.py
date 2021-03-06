"""Update members cog. Various commands for leadership to update Discord members."""

import discord
from discord.ext import commands

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils
from utils.logging_utils import LOG
from utils.role_utils import ROLE


class UpdateUtils(commands.Cog):
    """Commands for updating/resetting Discord members."""

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
    async def update_member(self, ctx: commands.Context, member: discord.Member):
        """Update a member of the Discord server."""
        LOG.command_start(ctx, member=member)

        if not await bot_utils.update_member(member):
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

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def update_all_members(self, ctx: commands.Context):
        """Update all members in the server and apply any necessary Discord role updates."""
        LOG.command_start(ctx)
        await bot_utils.update_all_members(ctx.guild)
        embed = discord.Embed(title="Update complete", color=discord.Color.green())
        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.commands_channel_check()
    async def reset_member(self, ctx: commands.Context, member: discord.Member):
        """Reset a member back to the welcome channel."""
        LOG.command_start(ctx, member=member)
        await self.reset_user_helper(member)
        embed = discord.Embed(title=f"{member.display_name} has been reset", color=discord.Color.green())
        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.commands_channel_check()
    async def reset_all_members(self, ctx: commands.Context, confirmation: str):
        """Deletes all users from database and resets everyone back to the welcome channel."""
        LOG.command_start(ctx, confirmation=confirmation)
        confirmation_message = "RESET THE BOT"

        if confirmation != confirmation_message:
            embed = discord.Embed(title="Users were NOT reset.", color=discord.Color.red())
            embed.add_field(name="You must send the command with the following confirmation message in quotes:",
                            value=confirmation_message)
            await ctx.send(embed)
            LOG.command_end("Bad confirmation")
            return

        embed = discord.Embed(title="Reseting all users. This will take a few minutes.", color=0xFFFF00)
        await ctx.send(embed=embed)
        db_utils.remove_all_users()

        for member in ctx.guild.members:
            await self.reset_user_helper(member)

        await bot_utils.send_rules_message(self.bot.user)
        embed = discord.Embed(title="All users have been reset.", color= discord.Color.green())
        embed.add_field(name=f"All users have been assigned the {ROLE.new().name} role.",
                        value=(f"If you are a {ROLE.admin().name}, you too need to enter your player tag and react to the rules "
                               "message to get your roles. Don't forget to manually adjust your server nickname too if needed."))
        await ctx.send(embed=embed)
        LOG.command_end()
