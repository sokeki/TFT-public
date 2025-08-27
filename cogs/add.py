# add.py
import discord
from discord import option
from discord.ext import commands
import pandas as pd
from pymongo_get_database import get_database

dbname = get_database()
pd.set_option("display.float_format", "{:.0f}".format)


class Add(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="add", description="Add an account to be tracked")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part after the #", required=True)
    @option("region", description="Region", required=True, choices=["euw1", "na1"])
    async def add(
        self, ctx: discord.ApplicationContext, name: str, tag: str, region: str
    ):
        collection = dbname["users"]
        users = pd.DataFrame(collection.find())

        try:
            summoner = await self.bot.riot.get_summoner(region, name)
            riot_id = summoner["puuid"]
        except Exception:
            await ctx.respond(
                "Error fetching account details. Check the name and region."
            )
            return

        if riot_id in users["_id"].values:
            await ctx.respond("Account already tracked.")
            return

        # Get LP
        try:
            stats = await self.bot.riot.get_league_entries(region, riot_id)
        except Exception:
            stats = []

        lp = 0
        tier_lp = {
            "BRONZE": 400,
            "SILVER": 800,
            "GOLD": 1200,
            "PLATINUM": 1600,
            "EMERALD": 2000,
            "DIAMOND": 2400,
        }
        rank_lp = {"III": 100, "II": 200, "I": 300}

        for stat in stats:
            if stat["queueType"] == "RANKED_TFT":
                lp += tier_lp.get(stat["tier"], 0)
                lp += rank_lp.get(stat["rank"], 0)
                lp += stat["leaguePoints"]

        collection.insert_one(
            {
                "_id": riot_id,
                "name": name,
                "tag": tag,
                "lp": lp,
                "region": region,
                "last_message": "",
            }
        )

        await ctx.respond(f"Added {name}#{tag} with {lp} LP.")


def setup(bot):
    bot.add_cog(Add(bot))
