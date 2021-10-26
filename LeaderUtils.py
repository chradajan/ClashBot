from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord

class LeaderUtils(commands.Cog):
    """Miscellaneous utilities for leaders/admins."""

    def __init__(self, bot):
        self.bot = bot

    """
    Command: !export {update_before_export} {false_logic_only}

    Export database information to csv.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def export(self, ctx, update_before_export: bool=True, false_logic_only: bool=True, include_deck_usage_history: bool=True, include_match_performance_history: bool=True):
        """Export database to csv file."""
        if update_before_export:
            await ctx.send("Starting export and updating all player information. This might take a minute.")
            for member in ctx.guild.members:
                await bot_utils.update_member(member)

        path = db_utils.output_to_csv(false_logic_only, include_deck_usage_history, include_match_performance_history)
        await ctx.send(file=discord.File(path))

    @export.error
    async def export_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!export command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.send(f"Invalid argument. Valid arguments: yes or no")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !export <update_before_export (optional)> <false_logic_only (optional)> <include_deck_usage_history (optional)> <include_match_performance_history (optional)>")
            raise error


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
        await ctx.send("Starting to update user roles. This might take a minute...")

        for member in members:
            # Get a list of normal roles (Visitor, Member, Elder, or Leader) that a member current has. These will be restored after reacting to rules message.
            roles_to_commit = [ role.name for role in list(set(bot_utils.NORMAL_ROLES.values()).intersection(set(member.roles))) ]
            db_utils.commit_roles(member.id, roles_to_commit)
            await member.remove_roles(*roles_to_remove)
            await member.add_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])

        await bot_utils.send_rules_message(ctx, self.bot.user)
        admin_role = bot_utils.SPECIAL_ROLES[ADMIN_ROLE_NAME]
        leader_role = bot_utils.NORMAL_ROLES[LEADER_ROLE_NAME]
        await ctx.send(f"Force rules check complete. If you are a {admin_role.mention} or {leader_role.mention}, don't forget to acknowledge the rules too.")

    @force_rules_check.error
    async def force_rules_check_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!force_rules_check command can only be sent in {channel.mention} by Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !force_rules_check")
            raise error


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
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send("Clash bot needs permission to send messages to the specified channel.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !mention_users <members> <channel> <message>")
            raise error


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
        await bot_utils.deck_usage_reminder(self.bot, None, reminder_message, False)

    @send_reminder.error
    async def send_reminder_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !send_reminder <message (optional)>")
            raise error


    """
    Command: !top_fame

    Send a list of the members with the top fame to the fame channel.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def top_fame(self, ctx):
        """Send a list of top users by fame in the fame channel."""
        top_members = clash_utils.get_top_fame_users()
        fame_channel = discord.utils.get(ctx.guild.channels, name=FAME_CHANNEL)
        table = PrettyTable()
        table.field_names = ["Member", "Fame"]
        embed = discord.Embed()

        for player_name, fame in top_members:
            table.add_row([player_name, fame])

        embed.add_field(name="Top members by fame", value="```\n" + table.get_string() + "```")

        try:
            await fame_channel.send(embed=embed)
        except:
            await fame_channel.send("Top members by fame\n" + "```\n" + table.get_string() + "```")

    @top_fame.error
    async def top_fame_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!top_fame command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !top_fame")
            raise error


    """
    Command: !fame_check {threshold}

    Mention users below the threshold in the fame channel.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def fame_check(self, ctx, threshold: int):
        """Mention users below the specified fame threshold. Ignores users on vacation."""
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        vacation_list = db_utils.get_vacation_list()
        fame_channel = discord.utils.get(ctx.guild.channels, name=REMINDER_CHANNEL)

        member_string = ""
        non_member_string = ""

        for player_name, fame in hall_of_shame:
            if player_name in vacation_list:
                continue

            member = discord.utils.get(fame_channel.members, display_name=player_name)

            if member == None:
                non_member_string += f"{player_name} - Fame: {fame}" + "\n"
            else:
                member_string += f"{member.mention} - Fame: {fame}" + "\n"

        if (len(member_string) == 0) and (len(non_member_string) == 0):
            await ctx.send("There are currently no members below the threshold you specified.")
            return

        fame_string = f"The following members are below {threshold} fame:" + "\n" + member_string + non_member_string
        await fame_channel.send(fame_string)

    @fame_check.error
    async def fame_check_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!fame_check command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.send("Invalid fame threshold. Fame must be an integer value.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !fame_check <threshold>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !fame_check <threshold>")
            raise error