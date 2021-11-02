from config import *
from discord.ext import commands
import bot_utils
import clash_utils
import db_utils
import discord

class MemberListeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        """Monitor welcome channel for users posting player tags."""
        if message.author.bot:
            return

        if message.channel.name == NEW_CHANNEL:
            if not message.content.startswith("#"):
                await message.channel.send(content="You forgot to include the # symbol at the start of your player tag. Try again with that included.", delete_after=10)
            elif message.content == PRIMARY_CLAN_TAG:
                await message.channel.send(content="You sent False Logic's clan tag. Please send your player tag instead.", delete_after=10)
            else:
                discord_name = bot_utils.full_name(message.author)
                clash_data = clash_utils.get_clash_user_data(message.content, discord_name, message.author.id)
                if clash_data != None:
                    if db_utils.add_new_user(clash_data):
                        if not await bot_utils.is_admin(message.author):
                            await message.author.edit(nick=clash_data["player_name"])
                        await message.author.add_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])
                        await message.author.remove_roles(bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME])
                    else:
                        await message.channel.send(content="A player affiliated with that player tag already exists on the server. Please enter an unused player tag.", delete_after=10)
                else:
                    await message.channel.send(content="Something went wrong getting your Clash Royale information. Please try again with your player tag. If this issue persists, message a leader for help.", delete_after=5)

            await message.delete()

        #await self.bot.process_commands(message)


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