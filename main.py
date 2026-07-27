import os
import random
import urllib.request
import base64
import json
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="e", intents=intents)

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
        if "|" not in chosen_line:
            return
            
        name, image_url = chosen_line.split("|", 1)
        
        embed = discord.Embed(
            title="🃏 Card Drop!",
            description=f"A wild card appeared: **{name.strip()}**\nType `!claim {name.strip()}` to add it to your collection!",
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url.strip())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the card right now: {e}")

@bot.command()
async def claim(ctx, *, card_name: str = None):
    if not card_name:
        await ctx.send("Please specify the name of the card you want to claim!")
        return

    if not GITHUB_TOKEN:
        await ctx.send("Error: GITHUB_TOKEN environment variable is missing on Railway!")
        return

    user_id = str(ctx.author.id)
    entry = f"{user_id} | {card_name.strip()}"

    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/inventory.txt"
        
        # Try fetching inventory.txt, or create it if it doesn't exist yet
        try:
            req = urllib.request.Request(api_url, headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            })
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                sha = data['sha']
                current_content = base64.b64decode(data['content']).decode('utf-8')
        except Exception:
            sha = None
            current_content = ""

        new_content = current_content.strip() + "\n" + entry + "\n"
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

        payload_data = {
            "message": f"Claim card {card_name} by {ctx.author}",
            "content": encoded_content
        }
        if sha:
            payload_data["sha"] = sha

        payload = json.dumps(payload_data).encode('utf-8')

        update_req = urllib.request.Request(api_url, data=payload, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }, method="PUT")

        with urllib.request.urlopen(update_req):
            pass

        await ctx.send(f"🎉 {ctx.author.mention}, you successfully claimed **{card_name.strip()}**!")
    except Exception as e:
        await ctx.send(f"Failed to claim card: {e}")

@bot.command()
async def collection(ctx):
    print("DEBUG: collection command triggered!")
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt"
        response = urllib.request.urlopen(url)
        lines = response.read().decode('utf-8').splitlines()
        
        user_id = str(ctx.author.id)
        user_cards = []
        
        for line in lines:
            if "|" in line:
                owner_id, card_name = line.split("|", 1)
                if owner_id.strip() == user_id:
                    user_cards.append(card_name.strip())
                    
        if not user_cards:
            await ctx.send(f"📦 {ctx.author.mention}, your collection is empty! Claim cards when they drop.")
            return
            
        card_list = "\n".join([f"• {card}" for card in user_cards])
        
        embed = discord.Embed(
            title=f"🃏 {ctx.author.display_name}'s Card Collection",
            description=card_list,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total Cards Owned: {len(user_cards)}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"ERROR in collection: {e}")
        await ctx.send(f"Could not load your collection: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
