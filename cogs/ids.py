import discord
import pandas as pd
from discord.ext import tasks
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
import urllib
from discord.ext import commands
from pymongo_get_database import get_database

dbname = get_database()

user_agent = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"
headers = {
    "User-Agent": user_agent,
}
url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/companions.json"
request = urllib.request.Request(url, None, headers)
companions = urllib.request.urlopen(request)

load_dotenv()
bot = discord.Bot()
api_key = str(os.getenv("RIOT"))
print(api_key)
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)
pd.set_option("display.float_format", "{:.0f}".format)


class Ids(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(hours=12)
    async def ids(self):
        print("checking ranks...")
        collection_name = dbname["users"]
        data_raw = collection_name.find()
        data = pd.DataFrame(data_raw)
        for i in range(len(data)):
            riot_id = data.iloc[i]["_id"]
            region = data.iloc[i]["region"]
            name = data.iloc[i]["name"]
            tag = data.iloc[i]["tag"]
            account = riot_watcher.account.by_riot_id(region, name, tag)
            new_id = account["puuid"]
            if riot_id != id:
                query = {"$and": [{"region": region, "name": name, "tag": tag}]}
                new_values = {"$set": {"_id": new_id}}
                collection_name.update(query, new_values)
                print("Updated ID")
            new_name = account["gameName"]
            new_tag = account["tagLine"]
            if new_name != name or new_tag != tag:
                query = {"_id": riot_id}
                new_values = {"$set": {"name": new_name}}
                collection_name.update(query, new_values)
                new_values = {"$set": {"tag": new_tag}}
                collection_name.update(query, new_values)
                print("Updated name and tag")


def setup(bot):
    bot.add_cog(Ids(bot))
