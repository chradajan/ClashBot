from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord

class MemberUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    """
    Command: !river_race_status

    Show a list of clans in the current river race and how many decks they have remaining today.
    """
    @commands.command()
    async def river_race_status(self, ctx):
        """Send a list of clans in the current river race and their number of decks remaining today."""
        clans = clash_utils.get_clan_decks_remaining()
        embed = discord.Embed(title="Current River Race Status")

        table = PrettyTable()
        table.field_names = ["Clan", "Decks"]

        for clan_name, decks_remaining in clans:
            table.add_row([clan_name, decks_remaining])

        embed.add_field(name="Remaining decks for each clan", value="```\n" + table.get_string() + "```")

        await ctx.send(embed=embed)

    @river_race_status.error
    async def river_race_status_error(self, ctx, error):
        await ctx.send("Something went wrong. Command should be formatted as:  !river_race_status")
        raise error


    """
    Command: !set_reminder_time {reminder_time}

    Allow individual users to set their reminder time to US or EU.
    """
    @commands.command()
    async def set_reminder_time(self, ctx, reminder_time: str):
        """Set reminder time to either US or EU. US reminders go out at 01:00 UTC. EU reminders go out at 17:00 UTC."""
        time_zone = None
        if reminder_time == "US":
            time_zone = True
        elif reminder_time == "EU":
            time_zone = False
        else:
            await ctx.send("Invalid time zone. Valid reminder times are US or EU")
            return

        db_utils.update_time_zone(ctx.author.display_name, time_zone)
        await ctx.send("Your reminder time preference has been updated.")

    @set_reminder_time.error
    async def set_reminder_time_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You need to specify a reminder time. Valid reminder times are US or EU")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_reminder_time <reminder_time>")
            raise error