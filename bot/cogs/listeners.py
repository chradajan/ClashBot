"""Listener functions. Handles members joining/leaving, sending welcome messages, and reacting to specific messages."""

import discord
from discord.ext import commands

# Config
from config.config import (
    PRIMARY_CLAN_TAG,
    PRIMARY_CLAN_NAME,
    CONFIRM_EMOJI,
    DECLINE_EMOJI
)

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.callback_utils import CallbackType, CALLBACK_MANAGER
from utils.channel_utils import CHANNEL
from utils.logging_utils import LOG, log_message
from utils.role_utils import ROLE


class Listeners(commands.Cog):
    """Various listener functions."""

    def __init__(self, bot: commands.Bot):
        """Store bot and kick messages."""
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Give new members New role upon joining server."""
        LOG.info(f"{member} joined the server")
        if member.bot:
            return

        await member.add_roles(ROLE.new())

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove user from database when they leave server."""
        LOG.info(f"{member.display_name} - {member} left the server")
        db_utils.remove_user(member.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor welcome channel for users posting player tags and kicks channel for people posting images of kick screenshots."""
        if message.author.bot:
            return

        if message.channel == CHANNEL.welcome():
            if not message.content.startswith("#"):
                LOG.warning(log_message("Received improperly formatted welcome message",
                                        Sender=message.author,
                                        Message=message.content))
                await message.channel.send(content=("You forgot to include the # symbol at the start of your player tag. "
                                                    "Try again with that included."),
                                           delete_after=10)
            elif message.content == PRIMARY_CLAN_TAG:
                LOG.warning(log_message("Received primary clan tag as welcome message",
                                        Sender=message.author,
                                        Message=message.content))
                await message.channel.send(content=(f"You sent {PRIMARY_CLAN_NAME}'s clan tag. "
                                                    "Please send your player tag instead."),
                                           delete_after=10)
            else:
                user_data = bot_utils.get_combined_data(message.content, message.author)
                if user_data is not None:
                    if db_utils.add_new_user(user_data):
                        LOG.info(log_message("Added new user to database", User=message.author, user_data=user_data))
                        await message.channel.send(f"Player tag entered successfully! Please move on to {CHANNEL.rules().mention}.",
                                                   delete_after=15)

                        if not bot_utils.is_admin(message.author):
                            await message.author.edit(nick=user_data["player_name"])

                        await message.author.add_roles(ROLE.check_rules())
                        await message.author.remove_roles(ROLE.new())
                        await bot_utils.send_new_member_info(user_data)
                    else:
                        LOG.warning(log_message("Received player tag of existing user in welcome message",
                                                User=message.author,
                                                user_data=user_data))
                        await message.channel.send(content=("A player affiliated with that player tag is already on the server. "
                                                            "Please enter an unused player tag."),
                                                   delete_after=10)
                else:
                    LOG.warning(log_message("Could not get user data from properly formatted player tag in welcome message",
                                            Sender=message.author,
                                            Message=message.content))
                    await message.channel.send(content=("Something went wrong getting your Clash Royale information. "
                                                        "Please try again with your player tag. "
                                                        "If this issue persists, message a leader for help."),
                                               delete_after=10)

            await message.delete()
        elif (message.channel == CHANNEL.kicks()) and (len(message.attachments) > 0):
            for attachment in message.attachments:
                if attachment.content_type in {'image/png', 'image/jpeg'}:
                    player_tag, player_name = await bot_utils.get_player_info_from_image(attachment)
                    LOG.info(log_message("Parsed data from image in kicks channel", player_name=player_name, player_tag=player_tag))

                    if player_tag is None:
                        embed = discord.Embed(title="Unable to parse player info.",
                                              description="You can still log this kick manually with `!kick <member>`.")
                        await message.channel.send(embed=embed)
                        return

                    embed = discord.Embed(title=f"Did you just kick {player_name}?")
                    embed.add_field(name="React to log this kick if everything looks correct.",
                                    value=f"```Name: {player_name}\nTag: {player_tag}```")
                    kick_message = await message.channel.send(embed=embed)
                    await kick_message.add_reaction(CONFIRM_EMOJI)
                    await kick_message.add_reaction(DECLINE_EMOJI)
                    decline_embed = discord.Embed(title=f"A kick was not logged for {player_name}.")
                    CALLBACK_MANAGER.save_callback(kick_message.id,
                                                   CallbackType.KICK,
                                                   bot_utils.kick,
                                                   decline_embed,
                                                   player_tag, player_name)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reactions to rules message and callback messages."""
        if payload.member.bot:
            return

        channel = self.bot.get_channel(payload.channel_id)

        if channel is None:
            return

        if channel == CHANNEL.rules() and ROLE.check_rules() in payload.member.roles:
            await payload.member.remove_roles(ROLE.check_rules())

            if bot_utils.is_admin(payload.member):
                LOG.info(f"{payload.member} (admin) reacted to the rules message. Assigning all normal roles besides visitor role.")
                await payload.member.add_roles(*ROLE.normal_roles())
                await payload.member.remove_roles(ROLE.visitor())
                return

            db_roles = db_utils.get_roles(payload.member.id)
            saved_roles = []
            LOG.info(log_message(f"{payload.member} reacted to the rules message", db_roles=db_roles))

            for role in db_roles:
                saved_roles.append(ROLE.get_role_from_name(role))

            await payload.member.add_roles(*saved_roles)
        else:
            try:
                message = await channel.fetch_message(payload.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as error:
                LOG.exception(error)
                return

            await CALLBACK_MANAGER.handle_callback(message, payload.emoji, payload.member)
