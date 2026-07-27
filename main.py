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

class MultiClaimView(discord.ui.View):
    def __init__(self, card1_name: str, card2_name: str):
        super().__init__(timeout=60)
        self.card1_name = card1_name
        self.card2_name = card2_name

    async def claim_card(self, interaction: discord.Interaction, card_name: str, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        entry = f"{user_id} | {card_name}"

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
                "message": f"Claim card {card_name} by {interaction.user}",
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

            button.disabled = True
            button.label = f"Claimed by {interaction.user.display_name}"
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(f"🎉 {interaction.user.mention}, you successfully claimed **{card_name}**!")
        except Exception as e:
            await interaction.response.send_message(f"Failed to claim card: {e}", ephemeral=True)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def claim_first(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.claim_card(interaction, self.card1_name, button)

    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def claim_second(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.claim_card(interaction, self.card2_name, button)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.command()
async def drop(ctx):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt"
        response = urllib.request.urlopen(url)
        lines = response.read().decode('utf-8').splitlines()
        
        valid_cards = [line for line in lines if "|" in line]
        
        if len(valid_cards) < 2:
            await ctx.send("You need at least 2 cards in `cards.txt` to do a 2-card drop! Use `eaddcard` to add more.")
            return
            
        chosen_cards = random.sample(valid_cards, 2)
        
        name1, img1 = chosen_cards[0].split("|", 1)
        name2, img2 = chosen_cards[1].split("|", 1)
        
        c1_name = name1.strip()
        c2_name = name2.strip()
        
        embeds = []
        
        embed1 = discord.Embed(title=f"1️⃣ {c1_name}", color=discord.Color.blurple())
        embed1.set_image(url=img1.strip())
        embeds.append(embed1)
        
        embed2 = discord.Embed(title=f"2️⃣ {c2_name}", color=discord.Color.blurple())
        embed2.set_image(url=img2.strip())
        embeds.append(embed2)
        
        view = MultiClaimView(c1_name, c2_name)
        await ctx.send(content=f"✨ {ctx.author.mention} eli ig is dropping 2 cards!", embeds=embeds, view=view)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the cards right now: {e}")

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

@bot.command()
async def addcard(ctx, name: str, image_url: str):
    if not GITHUB_TOKEN:
        await ctx.send("Error: GITHUB_TOKEN environment variable is missing on Railway!")
        return

    entry = f"{name} | {image_url}"

    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/cards.txt"
        
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
            "message": f"Add card {name} via Discord",
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

        await ctx.send(f"✅ Successfully added new card: **{name}**!")
    except Exception as e:
        await ctx.send(f"Failed to add card: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))

        
                    
        
