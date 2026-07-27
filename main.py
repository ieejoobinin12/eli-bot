import random
import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # Required to read commands

bot = commands.Bot(command_prefix="!", intents=intents)

# A list of your cards (you can add names, image links, or descriptions)
cards_list = [
    "Common Card: ano & eli ",
    "Common Card: ano ",
    "Common Card: eli",
    "Common Card: tung tung tung sahurhttps ://cdn.discordapp.com/attachments/1450544431496429571/1531254222429884506/506410c5e062a21589fef3fd0bd6a575.webp.jpg?ex=6a688b1f&is=6a67399f&hm=9ace7896bb9e202778bf40fbf840249b60d202c3c16cd00b3bf60ed8a77b0f00&"
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

