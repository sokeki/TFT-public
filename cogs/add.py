import discord
import pandas as pd
from discord import option
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from discord.ext import commands

load_dotenv()
api_key = os.getenv('RIOT')

tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)

pd.set_option('display.float_format', '{:.0f}'.format)

class Add(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @discord.slash_command(name="add", description="Add an account to be tracked")
    @option("name", description="Summoner name", required=True)
    @option("tag", description="The part that comes after the #", required=True)
    @option("region", description="Summoner region", required=True, choices=["euw1", "na1"])
    async def stats(self, ctx: discord.ApplicationContext, name: str, tag: str, region: str):
        data = pd.read_csv('./tft_data.csv')
        riot_region = "EUROPE" if region == "euw1" else "AMERICAS"
        
        account = riot_watcher.account.by_riot_id(riot_region, name, tag)
        riot_id = account['puuid']
        
        if riot_id in data['riot_id'].values:
            await ctx.respond("Account has already been added.")
            return
        
        me = tft_watcher.summoner.by_puuid(region, riot_id)
        stats = tft_watcher.league.by_summoner(region, me['id'])
        
        lp = sum(self.calculate_lp(stat) for stat in stats if stat['queueType'] == "RANKED_TFT")
        
        info = {'riot_id': [riot_id], 'summ_id': [me['id']], 'name': [name], 'lp': [lp], 'region': [region]}
        data = pd.concat([data, pd.DataFrame(info)], ignore_index=True)
        data.to_csv("./tft_data.csv", index=False, float_format='%.0f')
        
        await ctx.respond(f'Successfully added {name}#{tag} with {lp} LP.')
        
    def calculate_lp(self, stat):
        tier_to_lp = {"BRONZE": 400, "SILVER": 800, "GOLD": 1200, "PLATINUM": 1600, "EMERALD": 2000, "DIAMOND": 2400}
        rank_to_lp = {"III": 100, "II": 200, "I": 300}
        
        tier_lp = tier_to_lp.get(stat['tier'], 0)
        rank_lp = rank_to_lp.get(stat['rank'], 0)
        
        return tier_lp + rank_lp + stat['leaguePoints']
        

def setup(bot):
    bot.add_cog(Add(bot))
