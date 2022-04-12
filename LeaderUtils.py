from cgitb import text
from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord
import ErrorHandler

class LeaderUtils(commands.Cog):
    """Miscellaneous utilities for leaders/admins."""

    def __init__(self, bot):
        self.bot = bot

    """
    Command: !export {false_logic_only} {include_card_levels}

    Export database information to spreadsheet.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def export(self, ctx, false_logic_only: bool=True, include_card_levels: bool=False):
        """Export database to Excel spreadsheet."""
        path = db_utils.export(false_logic_only, include_card_levels)
        await ctx.send(file=discord.File(path))


    """
    Command: !update_all_members

    Update all members of the server and apply any necessary Discord role changes.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def update_all_members(self, ctx: commands.Context):
        """Update all members in the server and apply any necessary Discord role updates."""
        await bot_utils.update_all_members(ctx.guild)
        embed = discord.Embed(title="Update complete", color=discord.Color.green())
        await ctx.send(embed=embed)


    """
    Command: !force_rules_check

    Force all players back to rules channel until they acknowledge new rules.
    """
    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def force_rules_check(self, ctx):
        """Strip roles from all non-leaders until they acknowledge new rules. Clash bot will send message to react to in rules channel."""
        # Get a list of members in guild without any special roles (New, Check Rules, or Admin) and that aren't bots.
        members = [member for member in ctx.guild.members if ((len(set(bot_utils.SPECIAL_ROLES.values()).intersection(set(member.roles))) == 0) and (not member.bot))]
        roles_to_remove = list(bot_utils.NORMAL_ROLES.values())
        starting_embed = discord.Embed(title="Beginning to update roles. This will take a few minutes.", color=0xFFFF00)
        await ctx.send(embed=starting_embed)

        for member in members:
            # Get a list of normal roles (Visitor, Member, Elder, or Leader) that a member current has. These will be restored after reacting to rules message.
            roles_to_commit = [ role.name for role in list(set(bot_utils.NORMAL_ROLES.values()).intersection(set(member.roles))) ]
            db_utils.commit_roles(member.id, roles_to_commit)
            await member.remove_roles(*roles_to_remove)
            await member.add_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])

        await bot_utils.send_rules_message(ctx, self.bot.user)
        admin_role = bot_utils.SPECIAL_ROLES[ADMIN_ROLE_NAME]
        leader_role = bot_utils.NORMAL_ROLES[LEADER_ROLE_NAME]
        completed_embed = discord.Embed(color=discord.Color.green())
        completed_embed.add_field(name="Force rules check complete",
                                  value="Don't forget to react to the new rules too if you are an Admin or Leader.")
        await ctx.send(content=f"{admin_role.mention} {leader_role.mention}", embed=completed_embed)


    """
    Command: !mention_users {members} {channel} {message}

    Have a bot tag specific users and send a message in a specified channel.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def mention_users(self, ctx, members: commands.Greedy[discord.Member], channel: discord.TextChannel, message: str):
        """Send message to channel mentioning specified users. Message must be enclosed in quotes."""
        message_string = ""

        for member in members:
            message_string += member.mention + " "
        
        message_string += "\n" + message

        await channel.send(message_string)

    @mention_users.error
    async def mention_users_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            err_msg = f"ClashBot does not have permission to send messages in the specified channel."
            embed = ErrorHandler.ErrorHandler.invoke_error_embed(err_msg)
            await ctx.send(embed=embed)
            return


    """
    Command: !send_reminder {message}

    Manually send automated reminder message. Optionally modify message.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def send_reminder(self, ctx, *message):
        """Send message to reminders channel tagging users who still have battles to complete. Excludes members currently on vacation. Optionally specify the message you want sent with the reminder."""
        reminder_message = ' '.join(message)
        if len(reminder_message) == 0:
            reminder_message = DEFAULT_REMINDER_MESSAGE
        await bot_utils.deck_usage_reminder(self.bot, message=reminder_message, automated=False)


    """
    Command: !top_medals

    Send a list of the members with the top medals to the fame channel.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def top_medals(self, ctx):
        """Send a list of top users by medals in the fame channel."""
        top_members = clash_utils.get_top_medal_users()
        fame_channel = discord.utils.get(ctx.guild.channels, name=FAME_CHANNEL)
        table = PrettyTable()
        table.field_names = ["Member", "Medals"]
        embed = discord.Embed()

        for player_name, fame in top_members:
            table.add_row([player_name, fame])

        embed.add_field(name="Top members by medals", value="```\n" + table.get_string() + "```")

        try:
            await fame_channel.send(embed=embed)
        except:
            await fame_channel.send("Top members by medals\n" + "```\n" + table.get_string() + "```")


    """
    Command: !medals_check {threshold}

    Mention users below the threshold in the fame channel.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def medals_check(self, ctx, threshold: int):
        """Mention users below the specified fame threshold. Ignores users on vacation."""
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        users_on_vacation = db_utils.get_users_on_vacation()
        fame_channel = discord.utils.get(ctx.guild.channels, name=REMINDER_CHANNEL)

        member_string = ""
        non_member_string = ""

        for player_name, player_tag, fame in hall_of_shame:
            if player_tag in users_on_vacation:
                continue

            member = None
            discord_id = db_utils.get_member_id(player_tag)

            if discord_id is not None:
                member = discord.utils.get(fame_channel.members, id=discord_id)

            if member is None:
                non_member_string += f"{player_name} - Fame: {fame}" + "\n"
            else:
                member_string += f"{member.mention} - Fame: {fame}" + "\n"

        if (len(member_string) == 0) and (len(non_member_string) == 0):
            await ctx.send("There are currently no members below the threshold you specified.")
            return

        fame_string = f"The following members are below {threshold} medals:" + "\n" + member_string + non_member_string
        await fame_channel.send(fame_string)


    """
    Command: !kick {player_name}

    Add a kick entry to the database with the current time for specified user.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check({COMMANDS_CHANNEL, KICKS_CHANNEL})
    async def kick(self, ctx, member: discord.Member):
        """Log that the specified user was kicked from the clan."""
        player_tag = db_utils.get_player_tag(member.id)
        embed = bot_utils.kick(member.display_name, player_tag)
        await ctx.send(embed=embed)

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)
            if player_tag is not None:
                embed = bot_utils.kick(error.argument, player_tag)
                await ctx.send(embed=embed)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)


    async def undo_kick_helper(self, ctx, player_name: str, player_tag: str):
        """
        Undo the latest kick of the specified user and send an embed with details about the kick.

        Args:
            player_name(str): Name of player to undo kick for.
            player_tag(str): Tag of player to undo kick for.
        """
        removed_kick = db_utils.undo_kick(player_tag)
        embed = discord.Embed(title="Kick Undone")

        if removed_kick is None:
            embed.add_field(name=player_name, value="This user has no kicks to undo.")
        else:
            embed.add_field(name=player_name, value=f"```Undid kick from: {removed_kick}```")

        await ctx.send(embed=embed)

    """
    Command: !undo_kick {player_name}

    Undo the latest kick for specified user.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check({COMMANDS_CHANNEL, KICKS_CHANNEL})
    async def undo_kick(self, ctx, member: discord.Member):
        """Undo the latest kick of the specified user."""
        player_tag = db_utils.get_player_tag(member.id)
        await self.undo_kick_helper(ctx, member.display_name, player_tag)

    @undo_kick.error
    async def undo_kick_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)
            if player_tag is not None:
                await self.undo_kick_helper(ctx, error.argument, player_tag)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)
