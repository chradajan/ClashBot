import discord
import checks
import clash_utils
import db_utils
from config import *

async def send_rules_message(ctx, user_to_purge: discord.ClientUser):
    rules_channel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rules_channel.purge(limit=10, check=lambda message: message.author == bot.user)
    new_react_message = await rules_channel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await new_react_message.add_reaction(u"\u2705")


async def deck_usage_reminder(bot, US_time: bool=None, message: str=DEFAULT_REMINDER_MESSAGE, automated: bool=True):
    reminder_list = clash_utils.get_deck_usage_today()
    vacation_list = db_utils.get_vacation_list()
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    if len(reminder_list) == 0:
        return

    member_string = ""
    non_member_string = ""

    check_time_zones = (US_time != None)
    time_zone_list = []

    if check_time_zones:
        time_zone_list = db_utils.get_members_in_time_zone(US_time)
        if time_zone_list == None:
            check_time_zones = False

    for player_name, decks_remaining in reminder_list:
        if player_name in vacation_list:
            continue

        if check_time_zones and (player_name not in time_zone_list):
            continue

        member = discord.utils.get(channel.members, display_name=player_name)

        if member == None:
            non_member_string += f"{player_name} - Decks left: {decks_remaining}" + "\n"
        else:
            member_string += f"{member.mention} - Decks left: {decks_remaining}" + "\n"

    if (len(member_string) == 0) and (len(non_member_string) == 0):
        if check_time_zones:
            zone = "US" if US_time else "EU"
            no_reminder_string = f"Everyone that receives {zone} reminders has already used all their decks today. Good job!"
            await channel.send(no_reminder_string)
        else:
            await channel.send("Everyone has already used all their decks today. Good job!")
        return

    reminder_string = message + "\n" + member_string + non_member_string

    if automated:
        automated_message = ''
        if US_time:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the night for you, consider switching your reminder time to 7PM GMT with command "!set_reminder_time EU"'
        else:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the day for you, consider switching your reminder time to 6PM PDT with command "!set_reminder_time US"'
        reminder_string += "\n\n" + automated_message

    await channel.send(reminder_string)


async def update_member(member: discord.Member, player_tag: str = None) -> bool:
    if member.bot:
        return False

    if player_tag == None:
        player_tag = db_utils.get_player_tag(member.display_name)

    if player_tag == None:
        return False

    discord_name = member.name + "#" + member.discriminator
    clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)

    if clash_data == None:
        return False

    member_status = db_utils.update_user(clash_data, member.display_name)

    if not is_admin(member):
        if clash_data["player_name"] != member.display_name
            await member.edit(nick = clash_data["player_name"])

        roles_to_remove = [roles.NORMAL_ROLES["Member"], roles.NORMAL_ROLES["Visitor"], roles.NORMAL_ROLES["Elder"]]
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(roles.NORMAL_ROLES[member_status])

        if clash_data["clan_role"] == "elder":
            await member.add_roles(roles.NORMAL_ROLES["Elder"])

    return True