import discord
import pandas as pd
from discord.ext import tasks
import os
from dotenv import load_dotenv
from riotwatcher import TftWatcher, RiotWatcher
from pathlib import Path
import numpy as np
import urllib
from discord.ext import commands

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
headers={'User-Agent':user_agent,}
url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/companions.json"
request=urllib.request.Request(url,None,headers)
companions = urllib.request.urlopen(request)

load_dotenv()
bot = discord.Bot()
api_key = str(os.getenv('RIOT'))
print(api_key)
tft_watcher = TftWatcher(api_key)
riot_watcher = RiotWatcher(api_key)
pd.set_option('display.float_format', '{:.0f}'.format)

class Lookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(minutes=1)
    async def lookup(self):
        print("checking ranks...")
        data = pd.read_csv('./tft_data.csv')
        channel = self.bot.get_channel(1284900822773141514)
        for i in range(len(data)):
            lp=0
            riot_id = data.iloc[i]['riot_id']
            region = data.iloc[i]['region']
            me = tft_watcher.summoner.by_puuid(region, riot_id)
            stats = tft_watcher.league.by_summoner(region, me['id'])
            str_rank=""
            for j in range(len(stats)):
                queueType = stats[j]['queueType']
                if queueType == "RANKED_TFT":
                    match stats[j]['tier']:
                        case "BRONZE":
                            lp += 400
                        case "SILVER":
                            lp += 800
                        case "GOLD":
                            lp += 1200
                        case "PLATINUM":
                            lp += 1600
                        case "EMERALD":
                            lp += 2000
                        case "DIAMOND":
                            lp += 2400
                    match stats[j]['rank']:
                        case "III":
                            lp += 100
                        case "II":
                            lp += 200
                        case "I":
                            lp += 300
                    lp += stats[j]['leaguePoints']
                    tier = stats[j]['tier']
                    tier = tier.lower()
                    tier = tier.capitalize()
                    str_rank = tier + " " + stats[j]['rank'] + " " + str(stats[j]['leaguePoints']) + "LP"
            if data.iloc[i]['lp'] < lp:
                lp_diff = lp - data.iloc[i]['lp']
                data.loc[i, 'lp'] = lp
                data.to_csv("./tft_data.csv", index=False)
                embed = discord.Embed(
                    title = data.iloc[i]['name'] + " has just won a game",
                    description = f'Currently {str_rank}, +{lp_diff}LP', 
                    color=discord.Colour.green(),
                )
                embed.add_field(name="", value="", inline=False)
                embed.add_field(name="Placement", value="Placement pending...", inline=True)
                message = await channel.send(embed=embed)
                data.loc[i, 'newest_message'] = "'" + str(message.id)
                data.to_csv("./tft_data.csv", index=False, float_format='%.0f')
                
            elif data.iloc[i]['lp'] > lp:
                lp_diff = data.iloc[i]['lp'] - lp
                data.loc[i, 'lp'] = lp
                data.to_csv("./tft_data.csv", index=False)
                embed = discord.Embed(
                    title = data.iloc[i]['name'] + " has just lost a game",
                    description = f'Currently {str_rank}, -{lp_diff}LP', 
                    color=discord.Colour.red(),
                )
                embed.add_field(name="", value="", inline=False)
                embed.add_field(name="Placement", value="Placement pending...", inline=True)
                message = await channel.send(embed=embed)
                data.loc[i, 'newest_message'] = "'" + str(message.id)
                data.to_csv("./tft_data.csv", index=False, float_format='%.0f')
                
        print("checking matches...")
        users = data
        for i in range(len(users)):
            riot_id = users.iloc[i]['riot_id']
            region = users.iloc[i]['region']
            new_match_list = tft_watcher.match.by_puuid(region, riot_id)
            file = Path("./" + riot_id + ".csv")
            if file.exists():
                df = pd.read_csv(file)
                for match_id in new_match_list:
                    if match_id not in df['match_id'].values:
                        match = tft_watcher.match.by_id(region, match_id)
                        if match['info']['tft_game_type'] == 'standard':
                            print("match found!")
                            match_df = pd.json_normalize(match['info']['participants'])
                            player_stats = match_df.loc[match_df['puuid'] == riot_id]
                            placement = player_stats.iloc[0]['placement']
                            eliminations = player_stats.iloc[0]['players_eliminated']
                            player_damage = player_stats.iloc[0]['total_damage_to_players']
                            level = player_stats.iloc[0]['level']
                            tactician_id = player_stats.iloc[0]['companion.item_ID']
                            user_info = users.loc[users['riot_id'] == riot_id]
                            message_id = user_info.iloc[0]['newest_message']
                            info = {'match_id':[match_id], 'placement':[placement], 'eliminations':[eliminations], 'damage_dealt':[player_damage], 'level':[level], 'tactician_id':[tactician_id], 'message_id':[message_id]}
                            message_id = message_id.replace("'", "")
                            df = pd.concat([df, pd.DataFrame(info)], ignore_index=True)
                            df.to_csv(file, index=False, float_format='%.0f')
                            print("added to match list...")
                            if message_id != np.nan:
                                message = await channel.fetch_message(message_id)
                                embed=message.embeds[0]
                                embed_dict = embed.to_dict()
                                create_new = 0
                                for field in embed_dict["fields"]:
                                    if field["name"] == "Players killed":
                                        create_new = 1            
                                if create_new == 0:
                                    for field in embed_dict["fields"]:
                                        if field["name"] == "Placement":
                                            field["value"] = str(placement)
                                    embed = discord.Embed.from_dict(embed_dict)
                                    embed.add_field(name="Players killed", value=str(eliminations), inline=True)
                                    embed.add_field(name="", value="", inline=False)
                                    embed.add_field(name="Damage dealt", value=str(player_damage), inline=True)
                                    embed.add_field(name="End level", value=str(level), inline=True)
                                    request=urllib.request.Request(url,None,headers)
                                    companions = urllib.request.urlopen(request)
                                    tactician_df = pd.read_json(companions)
                                    tactician = tactician_df.loc[tactician_df['itemId'] == tactician_id]
                                    tactician_url = tactician.iloc[0]['loadoutsIcon']
                                    tactician_url = tactician_url.replace("/lol-game-data/assets/ASSETS/Loadouts/Companions/", "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/assets/loadouts/companions/")
                                    tactician_url = tactician_url.lower()
                                    embed.set_thumbnail(url=tactician_url)
                                    await message.edit(embed=embed)  
                                    print("edited message")
                                else:
                                    me = tft_watcher.summoner.by_puuid(region, riot_id)
                                    stats = tft_watcher.league.by_summoner(region, me['id'])
                                    tier = stats[j]['tier']
                                    tier = tier.lower()
                                    tier = tier.capitalize()
                                    str_rank = tier + " " + stats[j]['rank'] + " " + str(stats[j]['leaguePoints']) + "LP"
                                    embed = discord.Embed(
                                    title = data.iloc[i]['name'] + " has just lost a game",
                                    description = f'Currently {str_rank}, -0LP', 
                                    color=discord.Colour.red(),
                                    )
                                    embed.add_field(name="", value="", inline=False)
                                    embed.add_field(name="Placement", value=str(placement), inline=True)
                                    embed.add_field(name="Players killed", value=str(eliminations), inline=True)
                                    embed.add_field(name="", value="", inline=False)
                                    embed.add_field(name="Damage dealt", value=str(player_damage), inline=True)
                                    embed.add_field(name="End level", value=str(level), inline=True)
                                    request=urllib.request.Request(url,None,headers)
                                    companions = urllib.request.urlopen(request)
                                    tactician_df = pd.read_json(companions)
                                    tactician = tactician_df.loc[tactician_df['itemId'] == tactician_id]
                                    tactician_url = tactician.iloc[0]['loadoutsIcon']
                                    tactician_url = tactician_url.replace("/lol-game-data/assets/ASSETS/Loadouts/Companions/", "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/assets/loadouts/companions/")
                                    tactician_url = tactician_url.lower()
                                    embed.set_thumbnail(url=tactician_url)
                                    message = await channel.send(embed=embed)
                                    data.loc[i, 'newest_message'] = "'" + str(message.id)
                                    data.to_csv("./tft_data.csv", index=False, float_format='%.0f')
                                    print("sent message")                   
                        
            else:
                print('fetching match data...')
                data = pd.DataFrame(columns=['match_id', 'placement', 'eliminations', 'damage_dealt', 'level', 'tactician_id', 'message_id'])
                for match_id in new_match_list:
                    match = tft_watcher.match.by_id(region, match_id)
                    if match['info']['tft_game_type'] == 'standard':
                        match_df = pd.json_normalize(match['info']['participants'])
                        player_stats = match_df.loc[match_df['puuid'] == riot_id]
                        placement = player_stats.iloc[0]['placement']
                        eliminations = player_stats.iloc[0]['players_eliminated']
                        player_damage = player_stats.iloc[0]['total_damage_to_players']
                        level = player_stats.iloc[0]['level']
                        tactician_id = player_stats.iloc[0]['companion.item_ID']
                        info = {'match_id':[match_id], 'placement':[placement], 'eliminations':[eliminations], 'damage_dealt':[player_damage], 'level':[level], 'tactician_id':[tactician_id], 'message_id':[np.nan]}
                        data = pd.concat([data, pd.DataFrame(info)], ignore_index=True)
                data.to_csv(file, index=False, float_format='%.0f')
                print('written to file')

def setup(bot):
    bot.add_cog(Lookup(bot))