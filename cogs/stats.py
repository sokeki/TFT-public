# stats.py
import discord
from discord import option
from discord.ext import commands


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="stats", description="Pull player stats")
    @option("name", description="Summoner name", required=True)
    @option("region", description="Region", required=True, choices=["euw1", "na1"])
    async def stats(self, ctx: discord.ApplicationContext, name: str, region: str):
        try:
            summoner = await self.bot.riot.get_summoner(region, name)
            riot_id = summoner["puuid"]
            stats = await self.bot.riot.get_league_entries(region, riot_id)
        except Exception:
            await ctx.respond("Error fetching stats. Check the name and region.")
            return

        embed = discord.Embed(color=discord.Colour.green())
        embed.set_author(name=f"{name} Competitive Stats")

        for stat in stats:
            queue_type = (
                stat["queueType"].replace("_", " ").title().replace("Tft", "TFT")
            )
            tier = stat["tier"].capitalize()
            rank = stat["rank"]
            lp = stat["leaguePoints"]
            wins = stat["wins"]
            losses = stat["losses"]
            winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            embed.add_field(
                name=queue_type,
                value=f"{tier} {rank} {lp}LP // {wins}W {losses}L: {winrate:.2f}% winrate",
                inline=False,
            )

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
