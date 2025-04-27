import discord
import pandas as pd
from discord import option
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands
from pymongo_get_database import get_database

dbname = get_database()

load_dotenv()
api_key = os.getenv("RIOT")

tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)

pd.set_option("display.float_format", "{:.0f}".format)


class Add(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="add", description="Add an account to be tracked")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part that comes after the #", required=True)
    @option(
        "region", description="Summoner region", required=True, choices=["euw1", "na1"]
    )
    async def stats(
        self, ctx: discord.ApplicationContext, name: str, tag: str, region: str
    ):
        collection_name = dbname["users"]
        data_raw = collection_name.find()
        data = pd.DataFrame(data_raw)
        riot_region = "EUROPE" if region == "euw1" else "AMERICAS"

        account = riot_watcher.account.by_riot_id(riot_region, name, tag)
        riot_id = account["puuid"]

        if riot_id in data["_id"].values:
            await ctx.respond("Account has already been added.")
            return

        me = tft_watcher.summoner.by_puuid(region, riot_id)
        stats = tft_watcher.league.by_summoner(region, me["id"])

        lp = sum(
            self.calculate_lp(stat)
            for stat in stats
            if stat["queueType"] == "RANKED_TFT"
        )

        info = {
            "_id": riot_id,
            "summ_id": me["id"],
            "name": name,
            "tag": tag,
            "lp": lp,
            "region": region,
            "last_message": "",
        }
        collection_name.insert_one(info)

        await ctx.respond(f"Successfully added {name}#{tag} with {lp} LP.")

    def calculate_lp(self, stat):
        tier_to_lp = {
            "BRONZE": 400,
            "SILVER": 800,
            "GOLD": 1200,
            "PLATINUM": 1600,
            "EMERALD": 2000,
            "DIAMOND": 2400,
        }
        rank_to_lp = {"III": 100, "II": 200, "I": 300}

        tier_lp = tier_to_lp.get(stat["tier"], 0)
        rank_lp = rank_to_lp.get(stat["rank"], 0)

        return tier_lp + rank_lp + stat["leaguePoints"]


def setup(bot):
    bot.add_cog(Add(bot))
