# list.py
import discord
from discord.ext import commands
import pandas as pd
from pymongo_get_database import get_database

dbname = get_database()
pd.set_option("display.float_format", "{:.0f}".format)


class List(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="list", description="Show account leaderboard")
    async def show_leaderboard(self, ctx: discord.ApplicationContext):
        collection = dbname["users"]
        users = (
            pd.DataFrame(collection.find())
            .sort_values("lp", ascending=False)
            .reset_index(drop=True)
        )

        embed = discord.Embed(color=discord.Colour.green())
        embed.set_author(name="Current TFT Rankings")

        for i, row in users.iterrows():
            user = row["name"]
            lp = row["lp"]
            str_rank = self.calculate_rank(lp)
            embed.add_field(name=f"{i+1}. {user}", value=str_rank, inline=False)

        await ctx.respond(embed=embed)

    def calculate_rank(self, lp_total):
        if lp_total == 0:
            return "Unranked"
        tier_points = lp_total - (lp_total % 100)
        rank_num = tier_points % 400
        tier_mapping = {
            0: "Iron",
            1: "Bronze",
            2: "Silver",
            3: "Gold",
            4: "Plat",
            5: "Emerald",
        }
        tier = tier_mapping.get(tier_points // 400, "Iron")
        rank_mapping = {0: "IV", 100: "III", 200: "II", 300: "I"}
        rank = rank_mapping.get(rank_num, "")
        lp = lp_total % 100
        return f"{tier} {rank} {lp}LP"


def setup(bot):
    bot.add_cog(List(bot))
