# remove.py
import discord
from discord import option
from discord.ext import commands
import pandas as pd
from pymongo_get_database import get_database

dbname = get_database()


class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="remove", description="Remove a tracked account")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="Tag", required=True)
    @option("region", description="Region", required=True, choices=["euw1", "na1"])
    async def remove(
        self, ctx: discord.ApplicationContext, name: str, tag: str, region: str
    ):
        collection = dbname["users"]
        users = pd.DataFrame(collection.find())

        try:
            region2 = "europe" if region == "euw1" else "americas"
            summoner = await self.bot.riot.get_summoner(region2, tag, name)
            riot_id = summoner["puuid"]
        except Exception:
            await ctx.respond("Could not fetch summoner. Check the name and region.")
            return

        if riot_id not in users["_id"].values:
            await ctx.respond("User is not currently tracked.")
            return

        # Remove from main users collection
        collection.delete_one({"_id": riot_id})

        # Drop match collection
        dbname[riot_id].drop()

        await ctx.respond(f"Removed {name} from tracking.")


def setup(bot):
    bot.add_cog(Remove(bot))
