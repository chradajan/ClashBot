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
        db_utils.remove_user(member.display_name)


    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor welcome channel for users posting player tags."""
        if message.author.bot:
            return

        if message.channel.name == NEW_CHANNEL:
            discord_name = message.author.name + "#" + message.author.discriminator
            clash_data = clash_utils.get_clash_user_data(message.content, discord_name)
            if clash_data != None:
                if db_utils.add_new_user(clash_data):
                    if not await bot_utils.is_admin(message.author):
                        await message.author.edit(nick=clash_data["player_name"])
                    await message.author.add_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])
                    await message.author.remove_roles(bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME])
            await message.delete()

        #await self.bot.process_commands(message)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Monitor rules channel for people reacting to rules message."""
        guild = self.bot.get_guild(payload.guild_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = guild.get_member(payload.user_id)

        if (channel.name != RULES_CHANNEL) or (bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME] not in member.roles) or (member.bot):
            return

        await member.remove_roles(bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME])

        if await bot_utils.is_admin(member):
            roles_to_add = list(bot_utils.NORMAL_ROLES.values())
            await member.add_roles(*roles_to_add)
            await member.remove_roles(bot_utils.NORMAL_ROLES[VISITOR_ROLE_NAME])
            return

        db_roles = db_utils.get_roles(member.display_name)
        saved_roles = []
        for role in db_roles:
            saved_roles.append(bot_utils.NORMAL_ROLES[role])
        await member.add_roles(*saved_roles)