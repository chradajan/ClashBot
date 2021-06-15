from checks import is_admin, is_leader_command_check, is_admin_command_check, channel_check
from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import db_utils
import discord
import roles

class UserUpdates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def reset_user_helper(member: discord.Member):
        if member.bot:
            return

        roles_to_remove = list(roles.NORMAL_ROLES.values())
        roles_to_remove.append(roles.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(roles.SPECIAL_ROLES[NEW_ROLE_NAME])

        db_utils.remove_user(member.display_name)


    """
    Command: !update

    Update a user in the database.
    """
    @commands.command()
    async def update(self, ctx):
        """Update your player name, clan role/affiliation, Discord server role, and Discord nickname."""
        if not await bot_utils.update_member(ctx.author):
            await ctx.send("Something went wrong. Your information has not been updated.")
            return

        if await is_admin(ctx.author):
            await ctx.send("Your information has been updated. As an Admin, you must manually update your Discord nickname if it no longer matches your in-game player name.")
        else:
            await ctx.send("Your information has been updated.")

    @update.error
    async def update_error(self, ctx, error):
        await ctx.send("Something went wrong. You should have gone through the new user and check rules channels before using this command. Command should be formatted as:  !update")
        raise error


    """
    Command: !update_user {member} {player_tag}

    Update a specified user in the database.
    """
    @commands.command()
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def update_user(self, ctx, member: discord.Member, player_tag: str=None):
        """Update a member. Specify a player_tag if they need a new one, or leave it blank to update with their current player tag. Updates player name, clan role/affiliation, Discord server role, and Discord nickname."""
        if not await bot_utils.update_member(member, player_tag):
            await ctx.send(f"Something went wrong. {member.display_name}'s information has not been updated.")
            return

        if await is_admin(member):
            await ctx.send(f"{member.display_name}'s information has been updated. As an Admin, they must manually update their Discord nickname if it no longer matches their in-game player name.")
        else:
            await ctx.send(f"{member.display_name}'s information has been updated.")

    @update_user.error
    async def update_user_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("Member not found.")
        elif isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!update_user command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !update_user <member> <player_tag>")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Something went wrong. Make sure the player tag you entered doesn't belong to another user in this server. Command should be formatted as:  !update <player_tag>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !update_user <member> <player_tag>")
            raise error


    """
    Command: !reset_user {member}

    Reset specified user .
    """
    @commands.command()
    @is_admin_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def reset_user(self, ctx, member: discord.Member):
        """Admin only. Delete selected user from database. Set their role to New."""
        await self.reset_user_helper(member)
        await ctx.send(f"{member.display_name} has been reset.")

    @reset_user.error
    async def reset_user_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("Member not found.")
        elif isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!reset_user command can only be sent in {channel.mention} by Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !reset_user <member>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !reset_user <member>")
            raise error


    """
    Command: !reset_all_users

    Reset all users and delete them from DB.
    """
    @commands.command()
    @is_admin_command_check()
    @channel_check(COMMANDS_CHANNEL)
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

        await LeaderUtils.send_rules_message(ctx, self.bot.user)

        admin_role = roles.SPECIAL_ROLES[ADMIN_ROLE_NAME]
        await ctx.send(f"All users have been reset. If you are a {admin_role.mention}, please send your player tag in the welcome channel to be re-added to the database. Then, react to the rules message to automatically get all roles back. Finally, update your Discord nickname to match your in-game username.")

    @reset_all_users.error
    async def reset_all_users_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!reset_all_users command can only be sent in {channel.mention} by Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing confirmation. Command should be formatted as:  !reset_all_users <confirmation>. Make sure to enclose the confirmation message in quotes.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !reset_all_users <confirmation>. Make sure to enclose the confirmation message in quotes.")
            raise error