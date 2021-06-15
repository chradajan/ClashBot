from config import *
from discord.ext import commands
import discord
import roles

async def is_admin(member: discord.Member) -> bool:
    return (roles.SPECIAL_ROLES[ADMIN_ROLE_NAME] in member.roles) or member.guild_permissions.administrator

def is_leader_command_check():
    async def predicate(ctx):
        return (roles.NORMAL_ROLES[LEADER_ROLE_NAME] in ctx.author.roles) or (roles.SPECIAL_ROLES[ADMIN_ROLE_NAME] in ctx.author.roles)
    return commands.check(predicate)

def is_admin_command_check():
    async def predicate(ctx):
        return await is_admin(ctx.author)
    return commands.check(predicate)

def channel_check(CHANNEL_NAME):
    async def predicate(ctx):
        return ctx.message.channel.name == CHANNEL_NAME
    return commands.check(predicate)