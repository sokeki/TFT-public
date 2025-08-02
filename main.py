import discord
import os
from dotenv import load_dotenv

load_dotenv()
bot = discord.Bot()

cogs_list = ["add", "list", "lookup", "remove", "stats"]

for cog in cogs_list:
    bot.load_extension(f"cogs.{cog}")


@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="your LP"),
    )

    id_cog = bot.get_cog("Ids")
    if id_cog and not id_cog.ids.is_running():
        id_cog.ids.start()
        print("Id check loop started")

    lookup_cog = bot.get_cog("Lookup")
    if lookup_cog and not lookup_cog.lookup.is_running():
        lookup_cog.lookup.start()
        print("Lookup loop started")


bot.run(os.getenv("TOKEN"))
