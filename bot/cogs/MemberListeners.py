"""
Listener functions. Handles members joining/leaving, sending welcome messages, and reacting to specific messages.
"""

from discord.ext import commands
import discord

# Config
from config.config import (
    ADMIN_ROLE_NAME,
    LEADER_ROLE_NAME,
    VISITOR_ROLE_NAME,
    CHECK_RULES_ROLE_NAME,
    NEW_ROLE_NAME,
    RULES_CHANNEL,
    NEW_CHANNEL,
    KICKS_CHANNEL,
    LEADER_INFO_CHANNEL,
    PRIMARY_CLAN_TAG,
    PRIMARY_CLAN_NAME
)

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils


class MemberListeners(commands.Cog):
    """Various listener functions."""
    def __init__(self, bot):
        self.bot = bot
        self.kick_messages = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Give new members New role upon joining server."""
        if member.bot:
            return

        await member.add_roles(bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME])


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove user from database when they leave server."""
        db_utils.remove_user(member.id)


    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor welcome channel for users posting player tags and kicks channel for people posting images of kick screenshots."""
        if message.author.bot:
            return

        if message.channel.name == NEW_CHANNEL:
            if not message.content.startswith("#"):
                await message.channel.send(content="You forgot to include the # symbol at the start of your player tag. Try again with that included.", delete_after=10)
            elif message.content == PRIMARY_CLAN_TAG:
                await message.channel.send(content=f"You sent {PRIMARY_CLAN_NAME}'s clan tag. Please send your player tag instead.", delete_after=10)
            else:
                discord_name = bot_utils.full_name(message.author)
                clash_data = clash_utils.get_clash_user_data(message.content, discord_name, message.author.id)
                if clash_data is not None:
                    if db_utils.add_new_user(clash_data):
                        if not await bot_utils.is_admin(message.author):
                            await message.author.edit(nick=clash_data["player_name"])
                        await message.author.add_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])
                        await message.author.remove_roles(bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME])
                        info_channel = discord.utils.get(message.guild.channels, name=LEADER_INFO_CHANNEL)
                        await bot_utils.send_new_member_info(info_channel, clash_data)
                    else:
                        await message.channel.send(content="A player affiliated with that player tag already exists on the server. Please enter an unused player tag.", delete_after=10)
                else:
                    await message.channel.send(content="Something went wrong getting your Clash Royale information. Please try again with your player tag. If this issue persists, message a leader for help.", delete_after=5)

            await message.delete()
        elif message.channel.name == KICKS_CHANNEL and len(message.attachments) > 0:
            for attachment in message.attachments:
                if attachment.content_type in {'image/png', 'image/jpeg'}:
                    player_tag, player_name = await bot_utils.get_player_info_from_image(attachment)

                    if player_tag is None:
                        embed = discord.Embed()
                        embed.add_field(name="Unable to parse player info.", value="You can still log this kick manually with !kick.")
                        await message.channel.send(embed=embed)
                        return

                    embed = discord.Embed(title=f"Did you just kick {player_name}?")
                    embed.add_field(name="React to log this kick if everything looks correct.", value=f"```Name: {player_name}\nTag: {player_tag}```")
                    kick_message = await message.channel.send(embed=embed)
                    await kick_message.add_reaction('✅')
                    await kick_message.add_reaction('❌')
                    self.kick_messages[kick_message.id] = (player_tag, player_name)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Monitor reacts to kick and strike messages."""
        kick_info = self.kick_messages.get(reaction.message.id)
        strike_info = bot_utils.strike_messages.get(reaction.message.id)

        if (kick_info is None and strike_info is None) or user.bot:
            return

        if kick_info is not None:
            player_tag, player_name = kick_info
            self.kick_messages.pop(reaction.message.id, None)

            if reaction.emoji == '✅':
                edited_embed = bot_utils.kick(player_name, player_tag)
                await reaction.message.edit(embed=edited_embed)
                await reaction.message.clear_reaction('✅')
                await reaction.message.clear_reaction('❌')
            elif reaction.emoji == '❌':
                edited_embed = discord.Embed(title=f"A kick was not logged for {player_name}.")
                await reaction.message.edit(embed=edited_embed)
                await reaction.message.clear_reaction('✅')
                await reaction.message.clear_reaction('❌')

        elif strike_info is not None:
            if (bot_utils.NORMAL_ROLES[LEADER_ROLE_NAME] not in user.roles) or (bot_utils.SPECIAL_ROLES[ADMIN_ROLE_NAME] not in user.roles):
                return

            player_tag, player_name, decks_used, decks_required, tracked_since, channel = strike_info
            bot_utils.strike_messages.pop(reaction.message.id, None)

            if reaction.emoji == '✅':
                _, strikes, _, _ = db_utils.give_strike(player_tag, 1)
                embed = discord.Embed()
                embed.add_field(name=player_name,
                                value=f"```Decks: {decks_used}/{decks_required}\nStrikes: {strikes}\nDate: {tracked_since}```")

                discord_id = db_utils.get_member_id(player_tag)
                member = None

                if discord_id is not None:
                    member = discord.utils.get(channel.members, id=discord_id)

                if member is not None:
                    await channel.send(content=f"{member.mention}", embed=embed)
                else:
                    await channel.send(embed=embed)

                edited_embed = discord.Embed(title=f"{player_name} received a strike.")
                await reaction.message.edit(embed=edited_embed)
                await reaction.message.clear_reaction('✅')
                await reaction.message.clear_reaction('❌')
            elif reaction.emoji == '❌':
                edited_embed = discord.Embed(title=f"{player_name} did not receive a strike.")
                await reaction.message.edit(embed=edited_embed)
                await reaction.message.clear_reaction('✅')
                await reaction.message.clear_reaction('❌')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Monitor rules channel for people reacting to rules message."""
        guild = self.bot.get_guild(payload.guild_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = None

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return

        member = guild.get_member(payload.user_id)

        if (channel.name != RULES_CHANNEL) or (bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME] not in member.roles) or (member.bot):
            return

        await member.remove_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])

        if await bot_utils.is_admin(member):
            roles_to_add = list(bot_utils.NORMAL_ROLES.values())
            await member.add_roles(*roles_to_add)
            await member.remove_roles(bot_utils.NORMAL_ROLES[VISITOR_ROLE_NAME])
            return

        db_roles = db_utils.get_roles(member.id)
        saved_roles = []
        for role in db_roles:
            saved_roles.append(bot_utils.NORMAL_ROLES[role])
        await member.add_roles(*saved_roles)