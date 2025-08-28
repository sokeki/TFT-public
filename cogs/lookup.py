# lookup.py
import discord
from discord.ext import commands, tasks
import pandas as pd
from pymongo_get_database import get_database
import urllib.request
import asyncio
import json

dbname = get_database()
pd.set_option("display.float_format", "{:.0f}".format)

USER_CHANNEL_ID = 1284900822773141514
COMPANIONS_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/companions.json"


# --------------------------
# Helper: fetch companion data
# --------------------------
async def fetch_companions():
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, urllib.request.urlopen, COMPANIONS_URL)
    return pd.read_json(data)


class Lookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lookup_loop.start()

    def cog_unload(self):
        self.lookup_loop.cancel()

    @tasks.loop(minutes=1)
    async def lookup_loop(self):
        await self.update_names_and_tags()
        await self.update_ranks()
        await self.update_matches()

    # --------------------------
    # Update summoner names/tags
    # --------------------------
    async def update_names_and_tags(self):
        print("Updating Data")
        collection = dbname["users"]
        users = pd.DataFrame(collection.find())

        for i, user in users.iterrows():
            riot_id = user["_id"]
            region = "europe" if user["region"] == "euw1" else "americas"

            try:
                summoner = await self.bot.riot.get_summoner(
                    user["region"], user["name"]
                )
                new_name = summoner["name"]
                new_tag = summoner.get("tagLine", "")
            except Exception:
                continue

            if new_name != user["name"] or new_tag != user["tag"]:
                collection.update_one(
                    {"_id": riot_id}, {"$set": {"name": new_name, "tag": new_tag}}
                )
                print(f"Updated {user['name']} -> {new_name}#{new_tag}")

    # --------------------------
    # Update LP and ranks
    # --------------------------
    async def update_ranks(self):
        print("Updating Ranks")
        collection = dbname["users"]
        users = pd.DataFrame(collection.find())
        channel = self.bot.get_channel(USER_CHANNEL_ID)

        for i, user in users.iterrows():
            riot_id = user["_id"]
            region = user["region"]

            try:
                stats = await self.bot.riot.get_league_entries(region, riot_id)
            except Exception:
                continue

            lp = 0
            str_rank = "Unranked"
            tier_mapping = {
                "BRONZE": 400,
                "SILVER": 800,
                "GOLD": 1200,
                "PLATINUM": 1600,
                "EMERALD": 2000,
                "DIAMOND": 2400,
            }
            rank_mapping = {"III": 100, "II": 200, "I": 300}

            for stat in stats:
                if stat["queueType"] == "RANKED_TFT":
                    lp += tier_mapping.get(stat["tier"], 0)
                    lp += rank_mapping.get(stat["rank"], 0)
                    lp += stat["leaguePoints"]
                    str_rank = f"{stat['tier'].capitalize()} {stat['rank']} {stat['leaguePoints']}LP"

            if user["lp"] != lp:
                lp_diff = lp - user["lp"]
                collection.update_one({"_id": riot_id}, {"$set": {"lp": lp}})

                if lp_diff > 0:
                    color = discord.Colour.green()
                    title = f"{user['name']} has just won a game"
                    desc = f"Currently {str_rank}, +{lp_diff}LP"
                else:
                    color = discord.Colour.red()
                    title = f"{user['name']} has just lost a game"
                    desc = f"Currently {str_rank}, {lp_diff}LP"

                embed = discord.Embed(title=title, description=desc, color=color)
                embed.add_field(name="Placement", value="Pending...", inline=True)
                msg = await channel.send(embed=embed)
                collection.update_one(
                    {"_id": riot_id}, {"$set": {"last_message": str(msg.id)}}
                )

    # --------------------------
    # Update matches and edit embeds
    # --------------------------
    async def update_matches(self):
        print("Updating Matches")
        collection_users = dbname["users"]
        users = pd.DataFrame(collection_users.find())
        channel = self.bot.get_channel(USER_CHANNEL_ID)
        companions_df = await fetch_companions()

        for i, user in users.iterrows():
            riot_id = user["_id"]
            print(riot_id)
            region = "europe" if user["region"] == "euw1" else "americas"
            try:
                match_ids = await self.bot.riot.get_match_ids(region, riot_id, count=5)
            except Exception:
                continue

            user_coll = dbname[riot_id]

            for match_id in match_ids:
                if user_coll.find_one({"match_id": match_id}):
                    continue

                try:
                    match_data = await self.bot.riot.get_match(region, match_id)
                    if match_data["info"]["tft_game_type"] != "standard":
                        continue
                except Exception:
                    continue

                participants = match_data["info"]["participants"]
                player = next((p for p in participants if p["puuid"] == riot_id), None)
                if not player:
                    continue

                placement = player["placement"]
                eliminations = player["players_eliminated"]
                damage = player["total_damage_to_players"]
                level = player["level"]
                tactician_id = player["companion"]["item_ID"]
                last_msg_id = user.get("last_message", "")

                user_coll.insert_one(
                    {
                        "match_id": match_id,
                        "placement": placement,
                        "eliminations": eliminations,
                        "damage_dealt": damage,
                        "level": level,
                        "tactician_id": tactician_id,
                        "message_id": last_msg_id,
                    }
                )

                tactician = companions_df[companions_df["itemId"] == tactician_id]
                if not tactician.empty:
                    url = tactician.iloc[0]["loadoutsIcon"]
                    url = url.replace(
                        "/lol-game-data/assets/ASSETS/Loadouts/Companions/",
                        "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/assets/loadouts/companions/",
                    ).lower()
                else:
                    url = "https://upload.wikimedia.org/wikipedia/commons/a/a3/Image-not-found.png"

                # If a last message exists -> edit it
                if last_msg_id:
                    try:
                        message = await channel.fetch_message(int(last_msg_id))
                        embed = message.embeds[0].to_dict()
                        embed_fields = embed.get("fields", [])

                        # Update placement
                        for field in embed_fields:
                            if field["name"] == "Placement":
                                field["value"] = str(placement)

                        # Add eliminations, damage, level
                        embed_fields += [
                            {
                                "name": "Players killed",
                                "value": str(eliminations),
                                "inline": True,
                            },
                            {
                                "name": "Damage dealt",
                                "value": str(damage),
                                "inline": True,
                            },
                            {"name": "End level", "value": str(level), "inline": True},
                        ]
                        embed["fields"] = embed_fields
                        embed["thumbnail"] = {"url": url}

                        await message.edit(embed=discord.Embed.from_dict(embed))

                        collection_users.update_one(
                            {"_id": riot_id}, {"$set": {"last_message": ""}}
                        )
                    except Exception:
                        continue

                # ELSE: send a brand new message
                else:
                    color = (
                        discord.Colour.green()
                        if placement < 5
                        else discord.Colour.red()
                    )
                    title = f"{user['name']} has just {'won' if placement < 5 else 'lost'} a game"
                    desc = f"Placement: {placement}"

                    embed = discord.Embed(title=title, description=desc, color=color)
                    embed.add_field(
                        name="Players killed", value=str(eliminations), inline=True
                    )
                    embed.add_field(name="Damage dealt", value=str(damage), inline=True)
                    embed.add_field(name="End level", value=str(level), inline=True)
                    embed.set_thumbnail(url=url)

                    msg = await channel.send(embed=embed)
                    collection_users.update_one(
                        {"_id": riot_id}, {"$set": {"last_message": str(msg.id)}}
                    )


def setup(bot):
    bot.add_cog(Lookup(bot))
