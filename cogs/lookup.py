# lookup.py
import discord
from discord.ext import commands, tasks
import pandas as pd
from pymongo_get_database import get_database
import urllib.request
import asyncio
import json
import aiohttp

dbname = get_database()
pd.set_option("display.float_format", "{:.0f}".format)

USER_CHANNEL_ID = 1284900822773141514
COMPANIONS_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/companions.json"


async def url_exists(url: str) -> bool:
    """Check if a URL exists by making a HEAD request."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as resp:
                # Some servers don't handle HEAD well — fallback to GET if necessary
                if resp.status == 405:
                    async with session.get(url, allow_redirects=True) as resp_get:
                        return resp_get.status == 200
                return resp.status == 200
    except Exception:
        return False


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
        print("Updating MongoDB...")
        collection = dbname["users"]
        users = pd.DataFrame(collection.find())

        for i, user in users.iterrows():
            riot_id = user["_id"]
            region = "europe" if user["region"] == "euw1" else "americas"

            try:
                summoner = await self.bot.riot.get_summoner(
                    region, user["tag"], user["name"]
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
        print("Updating ranks...")
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
                "IRON": 0,
                "BRONZE": 400,
                "SILVER": 800,
                "GOLD": 1200,
                "PLATINUM": 1600,
                "EMERALD": 2000,
                "DIAMOND": 2400,
                "MASTER": 2800,
                "GRANDMASTER": 3200,
                "CHALLENGER": 3600,
            }
            rank_mapping = {"III": 100, "II": 200, "I": 300}

            for stat in stats:
                if stat["queueType"] == "RANKED_TFT":
                    lp += tier_mapping.get(stat["tier"], 0)
                    lp += rank_mapping.get(stat["rank"], 0)
                    lp += stat["leaguePoints"]
                    str_rank = f"{stat['tier'].capitalize()} {stat['rank']} {stat['leaguePoints']}LP"

            if user["lp"] != lp:
                print("lp change detected!")
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

                print("Printing lp message...")

                embed = discord.Embed(title=title, description=desc, color=color)
                embed.add_field(name="Placement", value="Pending...", inline=True)
                msg = await channel.send(embed=embed)
                collection.update_one(
                    {"_id": riot_id}, {"$set": {"last_message": str(msg.id)}}
                )
                print("Sent rank update.")

    # --------------------------
    # Update matches and edit embeds
    # --------------------------
    async def update_matches(self):
        print("Updating matches...")
        collection_users = dbname["users"]
        users = pd.DataFrame(collection_users.find())
        channel = self.bot.get_channel(USER_CHANNEL_ID)
        companions_df = await fetch_companions()

        for i, user in users.iterrows():
            riot_id = user["_id"]
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
                    if match_data["info"]["queue_id"] != 1100:
                        continue
                except Exception:
                    continue

                print("New match data found...")
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
                    )
                    url = url.lower()
                else:
                    url = "https://upload.wikimedia.org/wikipedia/commons/a/a3/Image-not-found.png"

                # If a last message exists -> edit it
                if last_msg_id:
                    try:
                        message = await channel.fetch_message(int(last_msg_id))
                        embed = message.embeds[0].to_dict()
                        embed_fields = embed.get("fields", [])
                        print("Updating message...")

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
                                "name": "\u200b",
                                "value": "\u200b",
                                "inline": True,
                            },
                            {
                                "name": "Damage dealt",
                                "value": str(damage),
                                "inline": True,
                            },
                            {"name": "End level", "value": str(level), "inline": True},
                            {
                                "name": "\u200b",
                                "value": "\u200b",
                                "inline": True,
                            },
                        ]
                        embed["fields"] = embed_fields

                        if await url_exists(url):
                            embed["thumbnail"] = {"url": url}
                        else:
                            fallback = "https://upload.wikimedia.org/wikipedia/commons/a/a3/Image-not-found.png"
                            embed["thumbnail"] = {"url": fallback}
                            print(f"Skipped invalid thumbnail URL: {url}")

                        await message.edit(embed=discord.Embed.from_dict(embed))
                        print("Edited message.")

                        collection_users.update_one(
                            {"_id": riot_id}, {"$set": {"last_message": ""}}
                        )
                    except Exception:
                        continue

                # ELSE: send a brand new message
                else:
                    print("Printing new message...")
                    color = (
                        discord.Colour.green()
                        if placement < 5
                        else discord.Colour.red()
                    )
                    title = f"{user['name']} has just {'won' if placement < 5 else 'lost'} a game"
                    lp = 0
                    str_rank = "Unranked"
                    tier_mapping = {
                        "IRON": 0,
                        "BRONZE": 400,
                        "SILVER": 800,
                        "GOLD": 1200,
                        "PLATINUM": 1600,
                        "EMERALD": 2000,
                        "DIAMOND": 2400,
                        "MASTER": 2800,
                        "GRANDMASTER": 3200,
                        "CHALLENGER": 3600,
                    }
                    rank_mapping = {"III": 100, "II": 200, "I": 300}

                    stats = await self.bot.riot.get_league_entries(
                        user["region"], riot_id
                    )

                    for stat in stats:
                        if stat["queueType"] == "RANKED_TFT":
                            lp += tier_mapping.get(stat["tier"], 0)
                            lp += rank_mapping.get(stat["rank"], 0)
                            lp += stat["leaguePoints"]
                            str_rank = f"{stat['tier'].capitalize()} {stat['rank']} {stat['leaguePoints']}LP"

                    lp_diff = lp - user["lp"]
                    collection_users.update_one({"_id": riot_id}, {"$set": {"lp": lp}})

                    desc = f"Currently {str_rank}, gained {lp_diff}LP"

                    embed = discord.Embed(title=title, description=desc, color=color)
                    embed.add_field(name="Placement", value=str(placement), inline=True)
                    embed.add_field(
                        name="Players killed", value=str(eliminations), inline=True
                    )
                    embed.add_field(name="\u200b", value="\u200b", inline=True),
                    embed.add_field(name="Damage dealt", value=str(damage), inline=True)
                    embed.add_field(name="End level", value=str(level), inline=True)
                    embed.add_field(name="\u200b", value="\u200b", inline=True),
                    if await url_exists(url):
                        embed.set_thumbnail(url=url)
                    else:
                        fallback = "https://upload.wikimedia.org/wikipedia/commons/a/a3/Image-not-found.png"
                        embed.set_thumbnail(url=fallback)
                        print(f"Skipped invalid thumbnail URL: {url}")

                    collection_users.update_one(
                        {"_id": riot_id}, {"$set": {"last_message": ""}}
                    )
                    msg = await channel.send(embed=embed)
                    print("Printed message.")


def setup(bot):
    bot.add_cog(Lookup(bot))
