import discord
import pandas as pd
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands
from pymongo_get_database import get_database

dbname = get_database()

load_dotenv()
api_key = str(os.getenv("RIOT"))
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)

pd.set_option("display.float_format", "{:.0f}".format)


class List(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="list", description="Show account leaderboard")
    async def show_leaderboard(self, ctx: discord.ApplicationContext):
        collection_name = dbname["users"]
        data_raw = collection_name.find()
        data = pd.DataFrame(data_raw)
        data = data.sort_values("lp", ascending=False).reset_index(drop=True)

        embed = discord.Embed(color=discord.Colour.green())
        embed.set_author(name="Current TFT Rankings")

        for i, row in data.iterrows():
            user = row["name"]
            lp_total = row["lp"]
            str_rank = self.calculate_rank(lp_total)

            user_rank = f"{i + 1}. {user}"
            embed.add_field(name=user_rank, value=str_rank, inline=False)

        print("Output current leaderboard")
        await ctx.respond(embed=embed)

    def calculate_rank(self, lp_total):
        if lp_total == 0:
            return "Unranked"

        lp = lp_total % 100
        tier_points = lp_total - lp
        rank_num = tier_points % 400

        rank_mapping = {0: "IV", 100: "III", 200: "II", 300: "I"}
        rank = rank_mapping.get(rank_num, "")

        tier_mapping = {
            1: "Bronze",
            2: "Silver",
            3: "Gold",
            4: "Platinum",
            5: "Emerald",
            6: "Diamond",
        }
        tier_num = tier_points // 400
        tier = tier_mapping.get(tier_num, "Iron")

        return f"{tier} {rank} {lp}LP"


def setup(bot):
    bot.add_cog(List(bot))
