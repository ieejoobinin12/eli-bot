import os
import random
import urllib.request
import base64
import json
import time
import asyncio
from io import BytesIO
from PIL import Image
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="e", intents=intents)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = "ieejoobinin12/eli-bot"

claim_cooldowns = {}
active_trade_channels = set()
active_trade_views = {}

async def get_economy_data():
    api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/economy.txt"
    try:
        req = urllib.request.Request(api_url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            sha = data['sha']
            content = base64.b64decode(data['content']).decode('utf-8')
            return sha, content
    except Exception:
        return None, ""

async def save_economy_data(new_content, sha, commit_message):
    api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/economy.txt"
    payload_data = {
        "message": commit_message,
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    }
    if sha:
        payload_data["sha"] = sha

    payload = json.dumps(payload_data).encode('utf-8')
    update_req = urllib.request.Request(api_url, data=payload, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }, method="PUT")

    with urllib.request.urlopen(update_req):
        pass

async def get_user_cards(user_id):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        lines = urllib.request.urlopen(req).read().decode('utf-8').splitlines()
        user_cards = []
        for line in lines:
            if "|" in line:
                owner, card = line.split("|", 1)
                if owner.strip() == str(user_id):
                    user_cards.append(card.strip())
        return user_cards
    except Exception:
        return []

async def get_card_print_number(card_name: str):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        lines = urllib.request.urlopen(req).read().decode('utf-8').splitlines()
        
        count = 0
        for line in lines:
            if "|" in line:
                owner, card = line.split("|", 1)
                # Strip out any existing print suffix from stored inventory lines for accurate counting
                base_card = card.split("#")[0].strip()
                if base_card.lower() == card_name.strip().lower():
                    count += 1
        return count + 1
    except Exception:
        return 1

class VoteView(discord.ui.View):
    def __init__(self, vote_url: str):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="Open vote page", url=vote_url, style=discord.ButtonStyle.link))

class MultiClaimView(discord.ui.View):
    def __init__(self, card1_name: str, card2_name: str):
        super().__init__(timeout=60)
        self.card1_name = card1_name
        self.card2_name = card2_name

    async def claim_card(self, interaction: discord.Interaction, card_name: str, button: discord.ui.Button):
        user_id = interaction.user.id
        current_time = time.time()
        
        if user_id in claim_cooldowns:
            time_passed = current_time - claim_cooldowns[user_id]
            if time_passed < 600:
                left = int(600 - time_passed)
                mins = left // 60
                secs = left % 60
                await interaction.response.send_message(f"⏳ You are on claim cooldown! Please wait **{mins}m {secs}s** before claiming again.", ephemeral=True)
                return

        user_id_str = str(interaction.user.id)
        print_num = await get_card_print_number(card_name)
        entry = f"{user_id_str} | {card_name} #{print_num}"

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
                "message": f"Claim card {card_name} #{print_num} by {interaction.user}",
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

            claim_cooldowns[user_id] = time.time()

            button.disabled = True
            button.label = f"Claimed by {interaction.user.display_name}"
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(f"🎉 {interaction.user.mention}, you successfully claimed **{card_name}** `[Print #{print_num}]`!")
        except Exception as e:
            await interaction.response.send_message(f"Failed to claim card: {e}", ephemeral=True)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def claim_first(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.claim_card(interaction, self.card1_name, button)

    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def claim_second(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.claim_card(interaction, self.card2_name, button)

class TradeSessionView(discord.ui.View):
    def __init__(self, author: discord.Member, target: discord.Member):
        super().__init__(timeout=None)
        self.author = author
        self.target = target
        
        self.author_cards = []
        self.target_cards = []
        self.author_hearties = 0
        self.target_hearties = 0
        self.author_coins = 0
        self.target_coins = 0
        
        self.author_locked = False
        self.target_locked = False
        self.author_confirmed = False
        self.target_confirmed = False
        
        self.state = "active"
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.state == "active":
            lock_btn = discord.ui.Button(label="Lock", style=discord.ButtonStyle.primary, custom_id="lock")
            decline_btn = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger, custom_id="decline")
            lock_btn.callback = self.lock_callback
            decline_btn.callback = self.decline_callback
            self.add_item(lock_btn)
            self.add_item(decline_btn)
        elif self.state == "locked":
            confirm_btn = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
            decline_btn = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger, custom_id="decline")
            confirm_btn.callback = self.confirm_callback
            decline_btn.callback = self.decline_callback
            self.add_item(confirm_btn)
            self.add_item(decline_btn)

    def build_embed(self):
        embed = discord.Embed(title="🤝 Trade Session", color=discord.Color.gold())
        
        author_offer = []
        if self.author_cards:
            author_offer.append(f"Cards: {', '.join(self.author_cards)}")
        if self.author_hearties:
            author_offer.append(f"<:hearty:1531623071067410504> {self.author_hearties} Hearts")
        if self.author_coins:
            author_offer.append(f"<:coiny:1531623010727891065> {self.author_coins} Coins")
        if not author_offer:
            author_offer.append("Nothing offered yet")
        
        target_offer = []
        if self.target_cards:
            target_offer.append(f"Cards: {', '.join(self.target_cards)}")
        if self.target_hearties:
            target_offer.append(f"<:hearty:1531623071067410504> {self.target_hearties} Hearts")
        if self.target_coins:
            target_offer.append(f"<:coiny:1531623010727891065> {self.target_coins} Coins")
        if not target_offer:
            target_offer.append("Nothing offered yet")

        lock_status_1 = "🔒 Locked" if self.author_locked else "🔓 Unlocked"
        confirm_status_1 = "✅ Confirmed" if self.author_confirmed else "⏳ Pending"
        
        lock_status_2 = "🔒 Locked" if self.target_locked else "🔓 Unlocked"
        confirm_status_2 = "✅ Confirmed" if self.target_confirmed else "⏳ Pending"

        embed.add_field(
            name=f"{self.author.display_name}'s Offer ({lock_status_1} | {confirm_status_1})",
            value="\n".join(author_offer),
            inline=False
        )
        embed.add_field(
            name=f"{self.target.display_name}'s Offer ({lock_status_2} | {confirm_status_2})",
            value="\n".join(target_offer),
            inline=False
        )
        
        if self.state == "active":
            embed.set_footer(text="Use 'eadd [number]' for cards or 'eadd [amount] hearty/coiny' to add to your offer!")
        elif self.state == "locked":
            embed.set_footer(text="Both parties locked! Click Confirm to finalize.")
        return embed

    async def lock_callback(self, interaction: discord.Interaction):
        if interaction.user not in (self.author, self.target):
            await interaction.response.send_message("You are not part of this trade!", ephemeral=True)
            return

        if interaction.user == self.author:
            self.author_locked = True
        else:
            self.target_locked = True

        if self.author_locked and self.target_locked:
            self.state = "locked"
            self.update_buttons()

        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user not in (self.author, self.target):
            await interaction.response.send_message("You are not part of this trade!", ephemeral=True)
            return

        if interaction.user == self.author:
            self.author_confirmed = True
        else:
            self.target_confirmed = True

        if self.author_confirmed and self.target_confirmed:
            success = await execute_trade(self.author, self.target, self.author_cards, self.target_cards, self.author_hearties, self.target_hearties, self.author_coins, self.target_coins)
            active_trade_channels.discard(interaction.channel_id)
            active_trade_views.pop(interaction.channel_id, None)
            if success:
                self.stop()
                embed = discord.Embed(title="🤝 Trade Successful!", description=f"Trade between {self.author.mention} and {self.target.mention} completed successfully!", color=discord.Color.green())
                await interaction.response.edit_message(embed=embed, view=None)
                return
            else:
                await interaction.response.send_message("❌ Trade failed due to inventory/economy updates. Please try again.", ephemeral=True)
                return

        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def decline_callback(self, interaction: discord.Interaction):
        if interaction.user not in (self.author, self.target):
            await interaction.response.send_message("You are not part of this trade!", ephemeral=True)
            return
        active_trade_channels.discard(interaction.channel_id)
        active_trade_views.pop(interaction.channel_id, None)
        self.stop()
        embed = discord.Embed(title="❌ Trade Cancelled", description=f"Trade was cancelled by {interaction.user.mention}.", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=None)

class TradeRequestView(discord.ui.View):
    def __init__(self, author: discord.Member, target: discord.Member):
        super().__init__(timeout=60)
        self.author = author
        self.target = target
        self.accepted = False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("This trade request is not for you!", ephemeral=True)
            return
        self.accepted = True
        self.stop()
        
        active_trade_channels.add(interaction.channel_id)
        trade_view = TradeSessionView(self.author, self.target)
        active_trade_views[interaction.channel_id] = trade_view
        
        embed = trade_view.build_embed()
        await interaction.response.edit_message(content=f"🤝 Trade started between {self.author.mention} and {self.target.mention}!", embed=embed, view=trade_view)
        trade_view.message = interaction.message

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("This trade request is not for you!", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content=f"❌ {self.target.mention} declined the trade request.", embed=None, view=None)

async def execute_trade(author, target, author_cards, target_cards, author_hearties, target_hearties, author_coins, target_coins):
    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/inventory.txt"
        req = urllib.request.Request(api_url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        })
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode('utf-8'))
        sha = data['sha']
        inv_content = base64.b64decode(data['content']).decode('utf-8')

        lines = inv_content.splitlines()
        new_lines = []

        author_remaining_cards_to_give = list(author_cards)
        target_remaining_cards_to_give = list(target_cards)

        for line in lines:
            if "|" in line:
                owner, card = line.split("|", 1)
                owner = owner.strip()
                card = card.strip()
                
                if owner == str(author.id) and card in author_remaining_cards_to_give:
                    author_remaining_cards_to_give.remove(card)
                    new_lines.append(f"{target.id} | {card}")
                elif owner == str(target.id) and card in target_remaining_cards_to_give:
                    target_remaining_cards_to_give.remove(card)
                    new_lines.append(f"{author.id} | {card}")
                else:
                    new_lines.append(line)
            else:
                if line.strip():
                    new_lines.append(line)

        updated_inv = "\n".join(new_lines) + "\n"
        
        payload_data = {
            "message": f"Execute trade between {author} and {target}",
            "content": base64.b64encode(updated_inv.encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        
        update_req = urllib.request.Request(api_url, data=json.dumps(payload_data).encode('utf-8'), headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }, method="PUT")
        with urllib.request.urlopen(update_req):
            pass

        if author_hearties > 0 or target_hearties > 0 or author_coins > 0 or target_coins > 0:
            eco_sha, eco_content = await get_economy_data()
            eco_lines = eco_content.splitlines()
            eco_dict = {}
            for line in eco_lines:
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        eco_dict[parts[0]] = [int(float(parts[1])), int(float(parts[2])), parts[3] if len(parts) > 3 else "0"]
                    elif len(parts) == 2:
                        eco_dict[parts[0]] = [int(float(parts[1])), 0, "0"]

            if str(author.id) not in eco_dict:
                eco_dict[str(author.id)] = [0, 0, "0"]
            if str(target.id) not in eco_dict:
                eco_dict[str(target.id)] = [0, 0, "0"]

            eco_dict[str(author.id)][0] = eco_dict[str(author.id)][0] - author_hearties + target_hearties
            eco_dict[str(author.id)][1] = eco_dict[str(author.id)][1] - author_coins + target_coins

            eco_dict[str(target.id)][0] = eco_dict[str(target.id)][0] - target_hearties + author_hearties
            eco_dict[str(target.id)][1] = eco_dict[str(target.id)][1] - target_coins + author_coins

            new_eco_lines = [f"{uid} | {val[0]} | {val[1]} | {val[2]}" for uid, val in eco_dict.items()]
            await save_economy_data("\n".join(new_eco_lines) + "\n", eco_sha, f"Economy update from trade between {author} and {target}")

        return True
    except Exception as e:
        print(f"Trade error: {e}")
        return False

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user}!")

@bot.command(name="drop")
@commands.cooldown(1, 900, commands.BucketType.user)
async def drop(ctx):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt"
        req_cards = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req_cards)
        lines = response.read().decode('utf-8').splitlines()
        
        valid_cards = [line for line in lines if line.count("|") >= 2]
        
        if len(valid_cards) < 2:
            await ctx.send("You need at least 2 properly formatted cards in `cards.txt`! Use `eaddcard [Name] | [Series] | [URL]`")
            return
            
        chosen_cards = random.sample(valid_cards, 2)
        
        parts1 = chosen_cards[0].split("|", 2)
        parts2 = chosen_cards[1].split("|", 2)
        
        c1_name, c1_series, img1_url = parts1[0].strip(), parts1[1].strip(), parts1[2].strip()
        c2_name, c2_series, img2_url = parts2[0].strip(), parts2[1].strip(), parts2[2].strip()
        
        c1_print = await get_card_print_number(c1_name)
        c2_print = await get_card_print_number(c2_name)
        
        req_img1 = urllib.request.Request(img1_url, headers={'User-Agent': 'Mozilla/5.0'})
        req_img2 = urllib.request.Request(img2_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        img1_res = urllib.request.urlopen(req_img1)
        img2_res = urllib.request.urlopen(req_img2)
        
        im1 = Image.open(BytesIO(img1_res.read())).convert("RGBA")
        im2 = Image.open(BytesIO(img2_res.read())).convert("RGBA")
        
        target_height = 600
        im1 = im1.resize((int(im1.width * (target_height / im1.height)), target_height))
        im2 = im2.resize((int(im2.width * (target_height / im2.height)), target_height))
        
        gap = 20
        combined_width = im1.width + im2.width + gap
        combined_image = Image.new("RGBA", (combined_width, target_height), (0, 0, 0, 0))
        
        combined_image.paste(im1, (0, 0))
        combined_image.paste(im2, (im1.width + gap, 0))
        
        buffer = BytesIO()
        combined_image.save(buffer, format="PNG")
        buffer.seek(0)
        
        file = discord.File(buffer, filename="drop.png")
        view = MultiClaimView(c1_name, c2_name)
        
        description = f"1️⃣ **{c1_name}** `[Print #{c1_print}]` (*{c1_series}*)\n2️⃣ **{c2_name}** `[Print #{c2_print}]` (*{c2_series}*)"
        embed = discord.Embed(
            title=f"✨ {ctx.author.display_name} eli ig is dropping 2 cards!",
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://drop.png")
        
        await ctx.send(embed=embed, file=file, view=view)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the cards right now: {e}")

@drop.error
async def drop_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        await ctx.send(f"⏳ {ctx.author.mention}, please wait **{minutes}m {seconds}s** before dropping cards again!")

@bot.command(name="daily")
async def daily(ctx):
    user_id = str(ctx.author.id)
    current_time = time.time()
    daily_cooldown = 86400  # 24 hours

    try:
        sha, content = await get_economy_data()
        lines = content.splitlines()
        
        user_found = False
        user_hearties = 0
        user_coins = 0
        last_vote_time = 0.0
        last_daily_time = 0.0
        new_lines = []

        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if parts[0] == user_id:
                    user_found = True
                    
                    try:
                        user_hearties = int(float(parts[1])) if len(parts) > 1 and parts[1] != "" else 0
                    except ValueError:
                        user_hearties = 0
                        
                    try:
                        user_coins = int(float(parts[2])) if len(parts) > 2 and parts[2] != "" else 0
                    except ValueError:
                        user_coins = 0
                    
                    try:
                        last_vote_time = float(parts[3]) if len(parts) > 3 and parts[3] != "" else 0.0
                    except ValueError:
                        last_vote_time = 0.0
                        
                    try:
                        last_daily_time = float(parts[4]) if len(parts) > 4 and parts[4] != "" else 0.0
                    except ValueError:
                        last_daily_time = 0.0
                    
                    if current_time - last_daily_time < daily_cooldown:
                        left = int(daily_cooldown - (current_time - last_daily_time))
                        hours = left // 3600
                        mins = (left % 3600) // 60
                        await ctx.send(f"⏳ {ctx.author.mention}, you already claimed your daily coins! Please wait **{hours}h {mins}m**.")
                        return
                    else:
                        earned_coins = random.randint(12, 88)
                        user_coins += earned_coins
                        last_daily_time = current_time
                        new_lines.append(f"{user_id} | {user_hearties} | {user_coins} | {last_vote_time} | {last_daily_time}")
                        
                        embed = discord.Embed(
                            title="Daily Coiny",
                            description=f"🎉 {ctx.author.mention}, you claimed your daily reward and received **{earned_coins}** <:coiny:1531623010727891065> coins!",
                            color=discord.Color.green()
                        )
                        await ctx.send(embed=embed)
                else:
                    new_lines.append(line)
            else:
                if line.strip():
                    new_lines.append(line)

        if not user_found:
            earned_coins = random.randint(12, 88)
            user_coins = earned_coins
            last_daily_time = current_time
            new_lines.append(f"{user_id} | 0 | {user_coins} | 0.0 | {last_daily_time}")
            
            embed = discord.Embed(
                title="Daily Coiny",
                description=f"🎉 {ctx.author.mention}, you claimed your daily reward and received **{earned_coins}** <:coiny:1531623010727891065> coins!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

        updated_content = "\n".join(new_lines) + "\n"
        await save_economy_data(updated_content, sha, f"Daily coins reward for {ctx.author}")

    except Exception as e:
        await ctx.send(f"Failed to process daily: {e}")

@bot.command(name="hearty", aliases=["balance", "bal", "inv", "einv", "einventory", "inventory"])
async def hearty(ctx):
    try:
        sha, content = await get_economy_data()
        user_id = str(ctx.author.id)
        user_hearties = 0
        user_coins = 0

        for line in content.splitlines():
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if parts[0] == user_id:
                    user_hearties = int(float(parts[1])) if len(parts) > 1 and parts[1] != "" else 0
                    user_coins = int(float(parts[2])) if len(parts) > 2 and parts[2] != "" else 0
                    break

        embed = discord.Embed(
            title="Inventory",
            description=f"Items carried by {ctx.author.mention}",
            color=discord.Color.dark_theme()
        )
        embed.add_field(
            name="Wallet",
            value=f"<:coiny:1531623010727891065> **{user_coins}** · Coins\n<:hearty:1531623071067410504> **{user_hearties}** · Hearts",
            inline=False
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Could not load inventory: {e}")

@bot.command(name="vote")
async def vote(ctx):
    vote_url = "https://top.gg/bot/1531222383980056648/vote"
    user_id = str(ctx.author.id)
    current_time = time.time()
    vote_cooldown = 43200

    try:
        sha, content = await get_economy_data()
        lines = content.splitlines()
        
        user_found = False
        user_hearties = 0
        user_coins = 0
        last_vote_time = 0.0
        last_daily_time = 0.0
        new_lines = []

        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if parts[0] == user_id:
                    user_found = True
                    user_hearties = int(float(parts[1])) if len(parts) > 1 and parts[1] != "" else 0
                    user_coins = int(float(parts[2])) if len(parts) > 2 and parts[2] != "" else 0
                    
                    try:
                        last_vote_time = float(parts[3]) if len(parts) > 3 and parts[3] != "" else 0.0
                    except ValueError:
                        last_vote_time = 0.0
                        
                    try:
                        last_daily_time = float(parts[4]) if len(parts) > 4 and parts[4] != "" else 0.0
                    except ValueError:
                        last_daily_time = 0.0
                    
                    if current_time - last_vote_time < vote_cooldown:
                        left = int(vote_cooldown - (current_time - last_vote_time))
                        hours = left // 3600
                        mins = (left % 3600) // 60
                        await ctx.send(f"⏳ {ctx.author.mention}, you must wait **{hours}h {mins}m** before voting again!")
                        return
                    else:
                        user_hearties += 1
                        last_vote_time = current_time
                        new_lines.append(f"{user_id} | {user_hearties} | {user_coins} | {last_vote_time} | {last_daily_time}")
                else:
                    new_lines.append(line)
            else:
                if line.strip():
                    new_lines.append(line)

        if not user_found:
            user_hearties = 1
            last_vote_time = current_time
            new_lines.append(f"{user_id} | {user_hearties} | 0 | {last_vote_time} | 0.0")

        updated_content = "\n".join(new_lines) + "\n"
        await save_economy_data(updated_content, sha, f"Vote reward for {ctx.author}")

        embed = discord.Embed(
            title="Vote",
            description=f"Use this link to vote for me\n{vote_url}",
            color=discord.Color.purple()
        )
        view = VoteView(vote_url)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(f"Failed to process vote: {e}")

@bot.command(name="cooldown")
async def ecooldown(ctx):
    user_id = ctx.author.id
    current_time = time.time()
    
    drop_command = bot.get_command("drop")
    drop_text = "You can spawn a card now!"
    
    if drop_command:
        bucket = drop_command._buckets.get_bucket(ctx.message)
        if bucket:
            retry_seconds = bucket.get_retry_after()
            if retry_seconds:
                dmins = int(retry_seconds // 60)
                dsecs = int(retry_seconds % 60)
                drop_text = f"**{dmins}m {dsecs}s** left to spawn a card again."

    claim_text = "You can claim a card again now!"
    if user_id in claim_cooldowns:
        passed = current_time - claim_cooldowns[user_id]
        if passed < 600:
            left = int(600 - passed)
            cmins = left // 60
            csecs = left % 60
            claim_text = f"**{cmins}m {csecs}s** left to claim a card again."

    daily_text = "You can claim your daily coins now!"
    vote_text = "You can vote for the bot now!"
    try:
        _, content = await get_economy_data()
        for line in content.splitlines():
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if parts[0] == str(user_id):
                    try:
                        v_time = float(parts[3]) if len(parts) > 3 and parts[3] != "" else 0.0
                    except ValueError:
                        v_time = 0.0
                        
                    try:
                        d_time = float(parts[4]) if len(parts) > 4 and parts[4] != "" else 0.0
                    except ValueError:
                        d_time = 0.0

                    if v_time > 0:
                        v_passed = current_time - v_time
                        if v_passed < 43200:
                            v_left = int(43200 - v_passed)
                            vote_text = f"**{v_left // 3600}h {(v_left % 3600) // 60}m** left to vote for the bot again."
                    if d_time > 0:
                        d_passed = current_time - d_time
                        if d_passed < 86400:
                            d_left = int(86400 - d_passed)
                            daily_text = f"**{d_left // 3600}h {(d_left % 3600) // 60}m** left to claim daily coins again."
                    break
    except:
        pass

    embed = discord.Embed(
        title="Cooldowns",
        description=f"Cooldown for {ctx.author.mention}\n\n"
                    f"{drop_text}\n"
                    f"{claim_text}\n"
                    f"{daily_text}\n"
                    f"{vote_text}\n"
                    f"30 drops left for pity",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command(name="collection", aliases=["ecollection", "ec"])
async def collection(ctx):
    try:
        url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt"
        req_inv = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req_inv)
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
            
        total_cards = len(user_cards)
        formatted_lines = []
        
        for index, card in enumerate(user_cards, start=1):
            formatted_lines.append(f"`{index}` · {card}")
            
        card_list = "\n".join(formatted_lines)
        
        embed = discord.Embed(
            title=f"🃏 {ctx.author.display_name}'s Card Collection",
            description=card_list,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"1-{total_cards} of {total_cards} | Total Cards Owned: {total_cards}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Could not load your collection: {e}")

@bot.command(name="view", aliases=["ev"])
async def view(ctx, card_index: int):
    try:
        inv_url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt"
        req_inv = urllib.request.Request(inv_url, headers={'User-Agent': 'Mozilla/5.0'})
        inv_lines = urllib.request.urlopen(req_inv).read().decode('utf-8').splitlines()
        
        user_id = str(ctx.author.id)
        user_cards = []
        
        for line in inv_lines:
            if "|" in line:
                owner_id, card_name = line.split("|", 1)
                if owner_id.strip() == user_id:
                    user_cards.append(card_name.strip())
                    
        if card_index < 1 or card_index > len(user_cards):
            await ctx.send(f"❌ {ctx.author.mention}, invalid card number! Please pick a number between **1** and **{len(user_cards)}**.")
            return
            
        stored_card_entry = user_cards[card_index - 1]
        target_card_name = stored_card_entry.split("#")[0].strip()
        
        cards_url = "https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt"
        req_cards = urllib.request.Request(cards_url, headers={'User-Agent': 'Mozilla/5.0'})
        card_lines = urllib.request.urlopen(req_cards).read().decode('utf-8').splitlines()
        
        card_image_url = None
        card_series = "Unknown Series"
        
        for c_line in card_lines:
            if c_line.count("|") >= 2:
                parts = [p.strip() for p in c_line.split("|", 2)]
                if parts[0].lower() == target_card_name.lower():
                    card_series = parts[1]
                    card_image_url = parts[2]
                    break
                    
        if not card_image_url:
            await ctx.send(f"⚠️ Found **{stored_card_entry}** in your inventory, but its image data couldn't be located in `cards.txt`.")
            return
            
        embed = discord.Embed(
            title=f"#{card_index} · {stored_card_entry}",
            description=f"Series: *{card_series}*\nOwned by {ctx.author.mention}",
            color=discord.Color.purple()
        )
        embed.set_image(url=card_image_url)
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Could not view the card: {e}")

@bot.command(name="trade", aliases=["et"])
async def trade(ctx, member: discord.Member = None):
    if not member and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    if not member or member == ctx.author:
        await ctx.send("❌ Please mention a user or reply to someone to start a trade!")
        return

    view = TradeRequestView(ctx.author, member)
    embed = discord.Embed(
        title="🤝 Trade Request",
        description=f"{ctx.author.mention} has requested a trade with {member.mention}!\nClick **Accept** below to open the trade session.",
        color=discord.Color.blurple()
    )
    await ctx.send(content=member.mention, embed=embed, view=view)

@bot.command(name="add", aliases=["ea"])
async def eadd(ctx, *, arg: str):
    if ctx.channel.id not in active_trade_channels:
        await ctx.send("❌ There is no active trade session in this channel!", delete_after=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return

    view = active_trade_views.get(ctx.channel.id)
    if not view or view.state != "active" or ctx.author not in (view.author, view.target):
        try:
            await ctx.message.delete()
        except:
            pass
        return

    try:
        await ctx.message.delete()
    except:
        pass

    user = ctx.author
    user_cards = await get_user_cards(user.id)
    arg = arg.strip().lower()

    if arg.isdigit():
        card_idx = int(arg)
        if 1 <= card_idx <= len(user_cards):
            card_name = user_cards[card_idx - 1]
            if user == view.author:
                if card_name not in view.author_cards:
                    view.author_cards.append(card_name)
            else:
                if card_name not in view.target_cards:
                    view.target_cards.append(card_name)
    else:
        parts = arg.split()
        if len(parts) >= 2:
            try:
                amount = int(parts[0])
                currency_type = parts[1]
                if "heart" in currency_type:
                    if user == view.author:
                        view.author_hearties += amount
                    else:
                        view.target_hearties += amount
                elif "coin" in currency_type:
                    if user == view.author:
                        view.author_coins += amount
                    else:
                        view.target_coins += amount
            except:
                pass
        elif len(parts) == 1:
            currency_type = parts[0]
            if "heart" in currency_type:
                if user == view.author:
                    view.author_hearties += 1
                else:
                    view.target_hearties += 1
            elif "coin" in currency_type:
                if user == view.author:
                    view.author_coins += 100
                else:
                    view.target_coins += 100

    try:
        if hasattr(view, 'message') and view.message:
            await view.message.edit(embed=view.build_embed(), view=view)
    except Exception as e:
        print(f"Error updating trade embed: {e}")

@bot.command(name="addcard")
async def addcard(ctx, *, data_input: str):
    if not GITHUB_TOKEN:
        await ctx.send("Error: GITHUB_TOKEN environment variable is missing on Railway!")
        return

    parts = [p.strip() for p in data_input.split("|")]
    if len(parts) < 3:
        await ctx.send("❌ Incorrect format! Please use:\n`eaddcard Name | Series | ImageURL`")
        return

    name, series, image_url = parts[0], parts[1], parts[2]

    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/cards.txt"
        
        try:
            req = urllib.request.Request(api_url, headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Mozilla/5.0"
            })
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                sha = data['sha']
                current_content = base64.b64decode(data['content']).decode('utf-8')
        except Exception:
            sha = None
            current_content = ""

        new_content = current_content.strip() + "\n" + f"{name} | {series} | {image_url}" + "\n"
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
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }, method="PUT")

        with urllib.request.urlopen(update_req):
            pass

        await ctx.send(f"✅ Successfully added new card: **{name}** from **{series}**!")
    except Exception as e:
        await ctx.send(f"Failed to add card: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
