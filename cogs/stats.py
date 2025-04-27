import discord
import pandas as pd
from discord import option
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands

load_dotenv()
api_key = str(os.getenv("RIOT"))
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)
pd.set_option("display.float_format", "{:.0f}".format)


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="stats", description="Pull player stats")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part that comes after the #", required=True)
    @option(
        "region", description="Summoner region", required=True, choices=["EUW1", "NA1"]
    )
    async def stats(
        self, ctx: discord.ApplicationContext, name: str, tag: str, region: str
    ):
        riot_region = "EUROPE" if region == "EUW1" else "AMERICAS"
        account = riot_watcher.account.by_riot_id(riot_region, name, tag)
        me = tft_watcher.summoner.by_puuid(region, account["puuid"])
        stats = tft_watcher.league.by_summoner(region, me["id"])

        embed = discord.Embed(color=discord.Colour.green())
        user = f"{name}#{tag}"
        embed.set_author(name=f"{user} Competitive Stats")

        for stat in stats:
            queue_type = (
                stat["queueType"].replace("_", " ").title().replace("Tft", "TFT")
            )
            tier = stat["tier"].capitalize()
            rank = stat["rank"]
            lp = stat["leaguePoints"]
            wins = stat["wins"]
            losses = stat["losses"]
            winrate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

            str_rank = (
                f"{tier} {rank} {lp}LP // {wins}W {losses}L: {winrate:.2f}% winrate"
            )
            embed.add_field(name=queue_type, value=str_rank, inline=False)

        print(f"Output stats for {name}")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
