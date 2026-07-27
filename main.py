import random
import os
import urllib.request
import base64
import json
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = "ieejoobinin12/eli-bot"

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.command()
async def drop(ctx):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt"
        response = urllib.request.urlopen(url)
        lines = response.read().decode('utf-8').splitlines()
        
        if not lines:
            await ctx.send("No cards found in the database yet!")
            return
            
        chosen_line = random.choice(lines)
        name, image_url = chosen_line.split("|")
        
        embed = discord.Embed(
            title="🃏 Card Drop!",
            description=f"A wild card appeared: **{name.strip()}**",
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url.strip())
        embed.set_footer(text="Type !addcard to add more cards!")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the card right now.")

@bot.command()
async def addcard(dtx, *, content: str = None):
    if not content or "|" not in content:
        await dtx.send("Usage: `!addcard Card Name | Image_URL`")
        return

    if not GITHUB_TOKEN:
        await dtx.send("Error: GITHUB_TOKEN environment variable is missing on Railway!")
        return

    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/cards.txt"
        req = urllib.request.Request(api_url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        })
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            sha = data['sha']
            current_content = base64.b64decode(data['content']).decode('utf-8')

        new_content = current_content.strip() + "\n" + content.strip() + "\n"
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

        payload = json.dumps({
            "message": f"Add new card via Discord by {dtx.author}",
            "content": encoded_content,
            "sha": sha
        }).encode('utf-8')

        update_req = urllib.request.Request(api_url, data=payload, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }, method="PUT")

        with urllib.request.urlopen(update_req):
            pass

        await dtx.send(f"✅ Successfully added new card: **{content.split('|')[0].strip()}**!")
    except Exception as e:
        await dtx.send(f"Failed to add card: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
