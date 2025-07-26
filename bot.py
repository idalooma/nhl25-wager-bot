import discord
from discord.ext import commands
import random
import string
from db import db

# Intents allow us to access member info
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or('/'), intents=intents)

@bot.event
async def on_ready():
    db.init_db()
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

import asyncio

async def main():
    from config import DISCORD_BOT_TOKEN
    # Load cogs so their commands are available
    try:
        await bot.load_extension("cogs.stats")
        print("Loaded cogs.stats successfully.")
    except Exception as e:
        print(f"Failed to load cogs.stats: {e}")
    try:
        await bot.load_extension("cogs.lobby")
        print("Loaded cogs.lobby successfully.")
    except Exception as e:
        print(f"Failed to load cogs.lobby: {e}")
    try:
        await bot.load_extension("cogs.money")
        print("Loaded cogs.money successfully.")
    except Exception as e:
        print(f"Failed to load cogs.money: {e}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
@bot.event
async def on_ready():
    db.init_db()
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

import asyncio

async def main():
    from config import DISCORD_BOT_TOKEN
    # Load cogs so their commands are available
    try:
        await bot.load_extension("cogs.stats")
        print("Loaded cogs.stats successfully.")
    except Exception as e:
        print(f"Failed to load cogs.stats: {e}")
    try:
        await bot.load_extension("cogs.lobby")
        print("Loaded cogs.lobby successfully.")
    except Exception as e:
        print(f"Failed to load cogs.lobby: {e}")
    try:
        await bot.load_extension("cogs.money")
        print("Loaded cogs.money successfully.")
    except Exception as e:
        print(f"Failed to load cogs.money: {e}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

@bot.event
async def on_ready():
    db.init_db()
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")


import asyncio

async def main():
    from config import DISCORD_BOT_TOKEN
    # Load cogs so their commands are available
    try:
        await bot.load_extension("cogs.stats")
        print("Loaded cogs.stats successfully.")
    except Exception as e:
        print(f"Failed to load cogs.stats: {e}")
    try:
        await bot.load_extension("cogs.lobby")
        print("Loaded cogs.lobby successfully.")
    except Exception as e:
        print(f"Failed to load cogs.lobby: {e}")
    try:
        await bot.load_extension("cogs.money")
        print("Loaded cogs.money successfully.")
    except Exception as e:
        print(f"Failed to load cogs.money: {e}")
    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())