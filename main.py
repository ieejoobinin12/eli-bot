import random
import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# List of cards with a title and an image link
cards_list = [
    {
        "name": "Fire Dragon 🔥", 
        "image": "https://i.imgur.com/example1.png"
    },
    {
        "name": "Shadow Knight ⚔️", 
        "image": "https://i.imgur.com/example2.png"
    },
    {
        "name": "Cosmic Angel ✨", 
        "image": "https://i.imgur.com/example3.png"
    }
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.command()
async def drop(ctx):
    # Pick a random card dictionary
    card = random.choice(cards_list)
    
    # Create a nice Discord embed for the card
    embed = discord.Embed(
        title="🃏 A card has dropped!",
        description=f"You found: **{card['name']}**",
        color=discord.Color.blue()
    )
    embed.set_image(url=card['image'])
    
    await ctx.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))


