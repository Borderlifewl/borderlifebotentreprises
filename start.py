import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive
import os
import asyncio

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    await bot.load_extension("cogs.tickets_lspd_command")
    await bot.load_extension("cogs.tickets_lspd_executive")
    await bot.load_extension("cogs.tickets_lspd_supervisor")
    await bot.load_extension("cogs.tickets_lspd")
    await bot.load_extension("cogs.tickets_lsmc")
    await bot.load_extension("cogs.tickets_pdm")
    await bot.load_extension("cogs.tickets_pdm_contact")
    await bot.load_extension("cogs.tickets_wl")
    await bot.load_extension("cogs.tickets_unicorn")
    await bot.load_extension("cogs.tickets_vigneron")

keep_alive()

@bot.event
async def on_ready():
    print(f"{bot.user} à belle et bien démarré !")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(token)

asyncio.run(main())