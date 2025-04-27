import discord
import pandas as pd
from discord import option
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands
from pathlib import Path
from pymongo_get_database import get_database

dbname = get_database()

load_dotenv()
api_key = str(os.getenv("RIOT"))
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)
pd.set_option("display.float_format", "{:.0f}".format)


class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="remove", description="Remove a tracked account")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part that comes after the #", required=True)
    @option(
        "region", description="Summoner region", required=True, choices=["EUW1", "NA1"]
    )
    async def stats(
        self, ctx: discord.ApplicationContext, name: str, tag: str, region: str
    ):
        collection_name = dbname["users"]
        data_raw = collection_name.find()
        data = pd.DataFrame(data_raw)
        riot_region = "EUROPE" if region == "EUW1" else "AMERICAS"

        try:
            account = riot_watcher.account.by_riot_id(riot_region, name, tag)
            riot_id = account["puuid"]
        except Exception as e:
            await ctx.respond(
                "Error fetching account details. Please check the provided information."
            )
            return

        if riot_id in data["_id"].values:
            query = {"_id": riot_id}
            collection_name.delete_one(query)

            collection_name = dbname[riot_id]
            collection_name.drop()

            print(f"Removed {name}")
            await ctx.respond(f"Removed user {name}#{tag}")
        else:
            await ctx.respond("User is not currently tracked")


def setup(bot):
    bot.add_cog(Remove(bot))
