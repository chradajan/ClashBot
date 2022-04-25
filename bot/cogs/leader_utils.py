"""Leader utils cog. Various leadership only commands."""

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Cogs
from cogs.error_handler import ErrorHandler

# Config
from config.config import DEFAULT_REMINDER_MESSAGE

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.channel_utils import CHANNEL
from utils.logging_utils import LOG, log_message
from utils.role_utils import ROLE


class LeaderUtils(commands.Cog):
    """Miscellaneous utilities for leaders/admins."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def export(self, ctx: commands.Context, false_logic_only: bool=True, include_card_levels: bool=False):
        """Export database to Excel spreadsheet."""
        LOG.command_start(ctx, false_logic_only=false_logic_only, include_card_levels=include_card_levels)
        path = db_utils.export(false_logic_only, include_card_levels)
        await ctx.send(file=discord.File(path))
        LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def update_all_users(self, ctx: commands.Context):
        """Update all members in the server and apply any necessary Discord role updates."""
        LOG.command_start(ctx)
        await bot_utils.update_all_members(ctx.guild)
        embed = discord.Embed(title="Update complete", color=discord.Color.green())
        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_admin_command_check()
    @bot_utils.commands_channel_check()
    async def force_rules_check(self, ctx: commands.Context):
        """Force all non-admins to acknowledge the rules. After reacting to the bot's message, they will get back their roles."""
        LOG.command_start(ctx)
        # Get a list of members in guild without any special roles (New, Check Rules, or Admin) and that aren't bots.
        members = [member for member in ctx.guild.members
                   if (not set(ROLE.special_roles()).intersection(set(member.roles))) and not member.bot]
        roles_to_remove = ROLE.normal_roles()
        starting_embed = discord.Embed(title="Beginning to update roles. This will take a few minutes.", color=0xFFFF00)
        await ctx.send(embed=starting_embed)

        for member in members:
            # Get a list of normal roles (Visitor, Member, Elder, or Leader) that a member current has.
            # These will be restored after reacting to rules message.
            roles_to_commit = [role.name for role in list(set(ROLE.normal_roles()).intersection(set(member.roles)))]
            LOG.debug(log_message(msg="Committing roles", member=member, roles=roles_to_commit))
            db_utils.commit_roles(member.id, roles_to_commit)
            await member.remove_roles(*roles_to_remove)
            await member.add_roles(ROLE.check_rules())

        await bot_utils.send_rules_message(self.bot.user)
        completed_embed = discord.Embed(color=discord.Color.green())
        completed_embed.add_field(name="Force rules check complete",
                                  value="Don't forget to react to the new rules too if you are an Admin or Leader.")
        await ctx.send(content=f"{ROLE.admin().mention} {ROLE.leader().mention}", embed=completed_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def mention_users(self,
                            ctx: commands.Context,
                            members: commands.Greedy[discord.Member],
                            channel: discord.TextChannel,
                            message: str):
        """Send message to specified channel mentioning specified users. Message must be enclosed in quotes."""
        LOG.command_start(ctx,
                          members=[f"{member.name}#{member.discriminator}" for member in members],
                          target_channel=channel,
                          message=message)
        message_string = ""

        for member in members:
            message_string += member.mention + " "

        message_string += "\n" + message
        await channel.send(message_string)

        confirmation_embed = discord.Embed(title=f"Message successfully sent to #{channel.name}.",
                                           color=discord.Color.green())
        await ctx.send(embed=confirmation_embed)
        LOG.command_end()

    @mention_users.error
    async def mention_users_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!mention_users error handler."""
        if isinstance(error, commands.errors.CommandInvokeError):
            embed = ErrorHandler.invoke_error_embed("ClashBot does not have permission to send messages in the specified channel.")
            await ctx.send(embed=embed)
            LOG.exception(error)
            return

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def send_reminder(self, ctx: commands.Context, *message):
        """Send reminder message to users with remaining decks. Optionally send a custom message with reminder."""
        reminder_message = ' '.join(message)

        if not reminder_message:
            reminder_message = DEFAULT_REMINDER_MESSAGE

        LOG.command_start(ctx, reminder_message=reminder_message)

        await bot_utils.deck_usage_reminder(message=reminder_message, automated=False)

        confirmation_embed = discord.Embed(title=f"Reminder message sent to #{CHANNEL.reminder().name}.",
                                           color=discord.Color.green())
        await ctx.send(embed=confirmation_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def top_medals(self, ctx: commands.Context):
        """Send a list of top users by medals to the fame channel."""
        LOG.command_start(ctx)
        top_members = clash_utils.get_top_medal_users()
        table = PrettyTable()
        table.field_names = ["Member", "Medals"]
        embed = discord.Embed()

        for player_name, fame in top_members:
            table.add_row([player_name, fame])

        embed.add_field(name="Top members by medals", value="```\n" + table.get_string() + "```")

        try:
            await CHANNEL.fame().send(embed=embed)
        except:
            await CHANNEL.fame().send("Top members by medals\n" + "```\n" + table.get_string() + "```")

        confirmation_embed = discord.Embed(title=f"Message successfully sent to #{CHANNEL.fame().name}.",
                                           color=discord.Color.green())
        await ctx.send(embed=confirmation_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def medals_check(self, ctx: commands.Context, threshold: int):
        """Mention users below the specified medals threshold."""
        LOG.command_start(ctx, threshold=threshold)
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        users_on_vacation = db_utils.get_users_on_vacation()

        member_string = ""
        non_member_string = ""

        for player_name, player_tag, fame in hall_of_shame:
            if player_tag in users_on_vacation:
                continue

            member = None
            discord_id = db_utils.get_member_id(player_tag)

            if discord_id is not None:
                member = discord.utils.get(CHANNEL.fame().members, id=discord_id)

            if member is None:
                non_member_string += f"{player_name} - Fame: {fame}" + "\n"
            else:
                member_string += f"{member.mention} - Fame: {fame}" + "\n"

        if not member_string and not non_member_string:
            embed = discord.Embed(title="There are currently no members below the threshold you specified.",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
            LOG.command_end("No members below threshold")
            return

        fame_string = f"The following members are below {threshold} medals:" + "\n" + member_string + non_member_string
        await CHANNEL.fame().send(fame_string)

        embed = discord.Embed(title=f"Message successfully sent to #{CHANNEL.fame().name}.", color=discord.Color.green())
        await ctx.send(embed=embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.kicks_channel_check()
    async def kick(self, ctx: commands.Context, member: discord.Member):
        """Log that the specified user was kicked from the clan."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return
        else:
            _, player_tag, _ = player_info[0]

        embed = await bot_utils.kick(player_tag, member.display_name)
        await ctx.send(embed=embed)
        LOG.command_end()

    @kick.error
    async def kick_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!kick error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, kick_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                embed = await bot_utils.kick(player_tag, player_name)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "kick")

            await ctx.send(embed=embed)
            LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.kicks_channel_check()
    async def undo_kick(self, ctx: commands.Context, member: discord.Member):
        """Undo the latest kick of the specified user."""
        LOG.command_start(ctx, member=member)
        player_info = db_utils.find_user_in_db(member.id)

        if not player_info:
            embed = ErrorHandler.missing_db_info(member.display_name)
            await ctx.send(embed=embed)
            LOG.command_end("Attempted to get data of Discord member not in database")
            return
        else:
            _, player_tag, _ = player_info[0]

        embed = bot_utils.undo_kick(member.display_name, player_tag)
        await ctx.send(embed=embed)
        LOG.command_end()

    @undo_kick.error
    async def undo_kick_error(self, ctx: commands.Context, error: discord.DiscordException):
        """!undo_kick error handler."""
        if isinstance(error, commands.errors.MemberNotFound):
            player_info = db_utils.find_user_in_db(error.argument)
            LOG.command_start(ctx, undo_kick_error_argument=error.argument, player_info=player_info)

            if not player_info:
                embed = ErrorHandler.member_not_found_embed(False)
            elif len(player_info) == 1:
                player_name, player_tag, _ = player_info[0]
                embed = bot_utils.undo_kick(player_name, player_tag)
            else:
                embed = bot_utils.duplicate_names_embed(player_info, "undo_kick")

            await ctx.send(embed=embed)
            LOG.command_end()
