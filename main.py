import random
import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # Required to read commands

bot = commands.Bot(command_prefix="elidrop", intents=intents)

# A list of your cards (you can add names, image links, or descriptions)
cards_list = [
    "Common Card: ano & eli",
    "Common Card: ano ",
    "Common Card: eli",
    "Common Card: tung tung tung sahur"
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.command()
async def drop(ctx):
    # Picks a random card from the list
    chosen_card = random.choice(cards_list)
    await ctx.send(f"🃏 A card has dropped! **{chosen_card}**")

# Runs the bot using the token from Railway variables
bot.run(os.getenv('DISCORD_TOKEN'))

