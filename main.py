        
       import os
import random
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

# Class for the interactive Claim Button
class ClaimButtonView(discord.ui.View):
    def __init__(self, card_name: str):
        super().__init__(timeout=60)  # Button expires after 60 seconds
        self.card_name = card_name

    @discord.ui.button(label="Claim Card! 🎁", style=discord.ButtonStyle.green)
    async def claim_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        entry = f"{user_id} | {self.card_name}"

        if not GITHUB_TOKEN:
            await interaction.response.send_message("Error: GITHUB_TOKEN environment variable is missing on Railway!", ephemeral=True)
            return

        try:
            api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/inventory.txt"
            
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
                "message": f"Claim card {self.card_name} by {interaction.user}",
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

            # Disable button after it's claimed so no one else can spam it
            for child in self.children:
                child.disabled = True
            
            button.label = f"Claimed by {interaction.user.display_name}"
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(f"🎉 {interaction.user.mention}, you successfully claimed **{self.card_name}**!")
        except Exception as e:
            await interaction.response.send_message(f"Failed to claim card: {e}", ephemeral=True)

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
        card_name = name.strip()
        
        embed = discord.Embed(
            title="🃏 Card Drop!",
            description=f"A wild card appeared: **{card_name}**\nClick the button below to claim it!",
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url.strip())
        
        # Attach the button view to the message
        view = ClaimButtonView(card_name)
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the card right now: {e}")

@bot.command()
async def collection(ctx):
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
        await ctx.send(f"Could not load your collection: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
 
