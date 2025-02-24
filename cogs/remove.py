import discord
import pandas as pd
from discord import option
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands

load_dotenv()
api_key = str(os.getenv('RIOT'))
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)
pd.set_option('display.float_format', '{:.0f}'.format)

class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="remove", description="Remove a tracked account")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part that comes after the #", required=True)
    @option("region", description="Summoner region", required=True, choices=["EUW1", "NA1"])
    async def stats(self, ctx: discord.ApplicationContext, name: str, tag: str, region: str):
        data = pd.read_csv('./tft_data.csv')
        riot_region = "EUROPE" if region == "EUW1" else "AMERICAS"
        
        try:
            account = riot_watcher.account.by_riot_id(riot_region, name, tag)
            riot_id = account['puuid']
        except Exception as e:
            await ctx.respond("Error fetching account details. Please check the provided information.")
            return
        
        if riot_id in data['riot_id'].values:
            data = data[data['riot_id'] != riot_id]
            data.to_csv("./tft_data.csv", index=False, float_format='%.0f')
            
            print(f'Removed {name}')
            await ctx.respond(f'Removed user {name}#{tag}')
        else:
            await ctx.respond("User is not currently tracked")


def setup(bot):
    bot.add_cog(Remove(bot))