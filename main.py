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
        "name": "eli & ano", 
        "image": "https://cdn.discordapp.com/attachments/1531251680266686466/1531257522802004068/Sans_titre_203_20260411231744-1.jpg?ex=6a688e32&is=6a673cb2&hm=796fd2af083030a2efcd7f50cd2d2b9f7c414e41570aa5adabb0bbd28edeb03d&"
    },
    {
        "name": "eli", 
        "image": "https://cdn.discordapp.com/attachments/1531251680266686466/1531257569098596392/Sans_titre_224_20260711201844-1.png?ex=6a688e3d&is=6a673cbd&hm=a5f71918bd5872f78a10abb7783500bd454111b5139cd0cfab25294627baff96&"
    },
    {
        "name": "tung tung tung sahur", 
        "image": "https://cdn.discordapp.com/attachments/1531251680266686466/1531257590477095103/506410c5e062a21589fef3fd0bd6a575.webp.jpg?ex=6a688e42&is=6a673cc2&hm=74508743aaaa03ed35297306ef11d6f41362caa8ca0bf20cb711dbd06b94f5a7& "
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


