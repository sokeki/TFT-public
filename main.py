# main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pymongo_get_database import get_database
from riot_api import RiotAPI
import asyncio

load_dotenv()

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize MongoDB
DB = get_database()

# List of cogs to load
COGS = ["add", "remove", "list", "stats", "lookup"]

# Load cogs
for cog in COGS:
    try:
        bot.load_extension(f"cogs.{cog}")
        print(f"Loaded cog: {cog}")
    except Exception as e:
        print(f"Failed to load cog {cog}: {e}")


# RiotAPI client will be initialized on_ready to ensure event loop is running
@bot.event
async def on_ready():
    if not hasattr(bot, "riot"):
        RIOT_KEY = os.getenv("RIOT")
        bot.riot = RiotAPI(api_key=RIOT_KEY)  # Session created here in running loop
        print("RiotAPI client initialized")

    print(f"{bot.user} is ready!")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="your LP"),
    )


# Close RiotAPI session gracefully on shutdown
async def shutdown():
    if hasattr(bot, "riot"):
        await bot.riot.close()
    await bot.close()


# Signal handler for shutdown (optional)
def main():
    try:
        TOKEN = os.getenv("TOKEN")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("Shutting down...")
        asyncio.run(shutdown())


if __name__ == "__main__":
    main()
