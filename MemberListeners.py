from config import *
from discord.ext import commands
import checks
import clash_utils
import db_utils
import discord
import roles

class MemberListeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Give new members New role upon joining server."""
        if member.bot:
            return

        await member.add_roles(roles.SPECIAL_ROLES["New"])


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
                    if not is_admin(message.author):
                        await message.author.edit(nick=clash_data["player_name"])
                    await message.author.add_roles(roles.SPECIAL_ROLES["Check Rules"])
                    await message.author.remove_roles(roles.SPECIAL_ROLES["New"])
            await message.delete()

        await self.bot.process_commands(message)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Monitor rules channel for people reacting to rules message."""
        guild = self.bot.get_guild(payload.guild_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = guild.get_member(payload.user_id)

        if (channel.name != RULES_CHANNEL) or (roles.SPECIAL_ROLES["Check Rules"] not in member.roles) or (member.bot):
            return

        await member.remove_roles(roles.SPECIAL_ROLES["Check Rules"])

        if is_admin(member):
            roles_to_add = list(roles.NORMAL_ROLES.values())
            await member.add_roles(*roles_to_add)
            await member.remove_roles(roles.NORMAL_ROLES["Visitor"])
            return

        db_roles = db_utils.get_roles(member.display_name)
        saved_roles = []
        for role in db_roles:
            saved_roles.append(roles.NORMAL_ROLES[role])
        await member.add_roles(*saved_roles)