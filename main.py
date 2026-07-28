import os, random, urllib.request, base64, json, time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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

async def _req(url, data=None, method="GET"):
    headers = {"User-Agent": "Mozilla/5.0"}
    if GITHUB_TOKEN:
        headers.update({"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"})
    payload = json.dumps(data).encode('utf-8') if data else None
    if payload: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(req) as res:
        return res.read().decode('utf-8')

async def get_economy_data():
    try:
        res = json.loads(await _req(f"https://api.github.com/repos/{REPO_NAME}/contents/economy.txt"))
        return res['sha'], base64.b64decode(res['content']).decode('utf-8')
    except Exception:
        return None, ""

async def save_economy_data(content, sha, msg):
    await _req(f"https://api.github.com/repos/{REPO_NAME}/contents/economy.txt", {
        "message": msg, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha
    }, method="PUT")

async def get_user_cards(user_id):
    try:
        lines = (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt")).splitlines()
        return [card.strip() for line in lines if "|" in line for owner, card in [line.split("|", 1)] if owner.strip() == str(user_id)]
    except Exception:
        return []

async def get_card_print_number(card_name: str):
    try:
        lines = (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt")).splitlines()
        return sum(1 for line in lines if "|" in line for owner, card in [line.split("|", 1)] if card.split("#")[0].strip().lower() == card_name.strip().lower()) + 1
    except Exception:
        return 1

class VoteView(discord.ui.View):
    def __init__(self, vote_url):
        super().__init__(timeout=180)
        self.add_item(discord.ui.Button(label="Open vote page", url=vote_url, style=discord.ButtonStyle.link))

class MultiClaimView(discord.ui.View):
    def __init__(self, c1, c2):
        super().__init__(timeout=60)
        self.c1, self.c2 = c1, c2

    async def claim_card(self, interaction, card_name, button):
        user_id = interaction.user.id
        if user_id in claim_cooldowns and time.time() - claim_cooldowns[user_id] < 600:
            left = int(600 - (time.time() - claim_cooldowns[user_id]))
            return await interaction.response.send_message(f"⏳ Cooldown! Wait **{left//60}m {left%60}s**.", ephemeral=True)
        if not GITHUB_TOKEN:
            return await interaction.response.send_message("Error: Missing GITHUB_TOKEN!", ephemeral=True)

        try:
            print_num = await get_card_print_number(card_name)
            api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/inventory.txt"
            try:
                res = json.loads(await _req(api_url))
                sha, content = res['sha'], base64.b64decode(res['content']).decode('utf-8')
            except Exception:
                sha, content = None, ""

            new_content = f"{content.strip()}\n{interaction.user.id} | {card_name} #{print_num}\n"
            await _req(api_url, {
                "message": f"Claim {card_name} #{print_num}",
                "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
                **({"sha": sha} if sha else {})
            }, method="PUT")

            claim_cooldowns[user_id] = time.time()
            button.disabled = True
            button.label = f"Claimed by {interaction.user.display_name}"
            await interaction.message.edit(view=self)
            await interaction.response.send_message(f"🎉 {interaction.user.mention}, claimed **{card_name}** `[Print #{print_num}]`!")
        except Exception as e:
            await interaction.response.send_message(f"Failed: {e}", ephemeral=True)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def c1_btn(self, interaction, button): await self.claim_card(interaction, self.c1, button)

    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def c2_btn(self, interaction, button): await self.claim_card(interaction, self.c2, button)

class TradeSessionView(discord.ui.View):
    def __init__(self, author, target):
        super().__init__(timeout=None)
        self.author, self.target = author, target
        self.author_cards, self.target_cards = [], []
        self.author_hearties = self.target_hearties = self.author_coins = self.target_coins = 0
        self.author_locked = self.target_locked = self.author_confirmed = self.target_confirmed = False
        self.state = "active"
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        is_locked = self.state == "locked"
        btn1 = discord.ui.Button(label="Confirm" if is_locked else "Lock", style=discord.ButtonStyle.success if is_locked else discord.ButtonStyle.primary)
        btn1.callback = self.confirm_callback if is_locked else self.lock_callback
        btn2 = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger, callback=self.decline_callback)
        self.add_item(btn1)
        self.add_item(btn2)

    def build_embed(self):
        embed = discord.Embed(title="🤝 Trade Session", color=discord.Color.gold())
        for user, cards, h, c, l, conf in [
            (self.author, self.author_cards, self.author_hearties, self.author_coins, self.author_locked, self.author_confirmed),
            (self.target, self.target_cards, self.target_hearties, self.target_coins, self.target_locked, self.target_confirmed)
        ]:
            offer = [f"Cards: {', '.join(cards)}" if cards else "Nothing offered"]
            if h: offer.append(f"<:hearty:1531623071067410504> {h} Hearts")
            if c: offer.append(f"<:coiny:1531623010727891065> {c} Coins")
            embed.add_field(name=f"{user.display_name} ({'🔒 Locked' if l else '🔓 Unlocked'} | {'✅ Confirmed' if conf else '⏳'})", value="\n".join(offer), inline=False)
        return embed

    async def lock_callback(self, interaction):
        if interaction.user not in (self.author, self.target): return
        if interaction.user == self.author: self.author_locked = True
        else: self.target_locked = True
        if self.author_locked and self.target_locked: self.state = "locked"
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def confirm_callback(self, interaction):
        if interaction.user not in (self.author, self.target): return
        if interaction.user == self.author: self.author_confirmed = True
        else: self.target_confirmed = True
        
        if self.author_confirmed and self.target_confirmed:
            success = await execute_trade(self.author, self.target, self.author_cards, self.target_cards, self.author_hearties, self.target_hearties, self.author_coins, self.target_coins)
            active_trade_channels.discard(interaction.channel_id)
            active_trade_views.pop(interaction.channel_id, None)
            if success:
                self.stop()
                return await interaction.response.edit_message(embed=discord.Embed(title="🤝 Trade Successful!", color=discord.Color.green()), view=None)
            return await interaction.response.send_message("❌ Trade failed.", ephemeral=True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def decline_callback(self, interaction):
        if interaction.user not in (self.author, self.target): return
        active_trade_channels.discard(interaction.channel_id)
        active_trade_views.pop(interaction.channel_id, None)
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="❌ Trade Cancelled", color=discord.Color.red()), view=None)

class TradeRequestView(discord.ui.View):
    def __init__(self, author, target):
        super().__init__(timeout=60)
        self.author, self.target = author, target

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        if interaction.user != self.target: return await interaction.response.send_message("Not for you!", ephemeral=True)
        self.stop()
        active_trade_channels.add(interaction.channel_id)
        trade_view = TradeSessionView(self.author, self.target)
        active_trade_views[interaction.channel_id] = trade_view
        trade_view.message = interaction.message
        await interaction.response.edit_message(content=f"🤝 Trade started!", embed=trade_view.build_embed(), view=trade_view)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction, button):
        if interaction.user != self.target: return
        self.stop()
        await interaction.response.edit_message(content="❌ Trade declined.", embed=None, view=None)

async def execute_trade(author, target, ac, tc, ah, th, aco, tco):
    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/inventory.txt"
        res = json.loads(await _req(api_url))
        sha, lines = res['sha'], base64.b64decode(res['content']).decode('utf-8').splitlines()
        
        new_lines, ar, tr = [], list(ac), list(tc)
        for line in lines:
            if "|" in line:
                owner, card = map(str.strip, line.split("|", 1))
                if owner == str(author.id) and card in ar:
                    ar.remove(card); new_lines.append(f"{target.id} | {card}")
                elif owner == str(target.id) and card in tr:
                    tr.remove(card); new_lines.append(f"{author.id} | {card}")
                else: new_lines.append(line)
            elif line.strip(): new_lines.append(line)

        await _req(api_url, {
            "message": f"Trade {author} & {target}",
            "content": base64.b64encode(("\n".join(new_lines) + "\n").encode('utf-8')).decode('utf-8'),
            "sha": sha
        }, method="PUT")

        if ah or th or aco or tco:
            eco_sha, eco_content = await get_economy_data()
            eco = {}
            for line in eco_content.splitlines():
                if "|" in line:
                    p = [x.strip() for x in line.split("|")]
                    eco[p[0]] = [int(float(p[1])), int(float(p[2])), p[3] if len(p) > 3 else "0"]
            
            for uid in (str(author.id), str(target.id)):
                if uid not in eco: eco[uid] = [0, 0, "0"]

            eco[str(author.id)][0] += th - ah
            eco[str(author.id)][1] += tco - aco
            eco[str(target.id)][0] += ah - th
            eco[str(target.id)][1] += aco - tco

            await save_economy_data("\n".join([f"{k} | {v[0]} | {v[1]} | {v[2]}" for k, v in eco.items()]) + "\n", eco_sha, "Trade eco update")
        return True
    except Exception as e:
        print(e)
        return False

@bot.event
async def on_ready(): print(f"Logged in as {bot.user}!")

@bot.command(name="drop")
@commands.cooldown(1, 900, commands.BucketType.user)
async def drop(ctx):
    try:
        valid_cards = [line for line in (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt")).splitlines() if line.count("|") >= 2]
        if len(valid_cards) < 2: return await ctx.send("Need at least 2 cards in `cards.txt`!")
        
        c1, c2 = random.sample(valid_cards, 2)
        n1, s1, i1 = map(str.strip, c1.split("|", 2))
        n2, s2, i2 = map(str.strip, c2.split("|", 2))
        
        p1, p2 = await get_card_print_number(n1), await get_card_print_number(n2)
        
        def load_img(url, p):
            im = Image.open(BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read())).convert("RGBA")
            im = im.resize((int(im.width * (600 / im.height)), 600))
            draw = ImageDraw.Draw(im)
            
            # Scalable font logic
            font_size = 28
            font = None
            font_paths = ["arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
            
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except OSError:
                    continue
            
            if font is None:
                try:
                    font = ImageFont.load_default(size=font_size)
                except TypeError:
                    font = ImageFont.load_default()

            # Original badge container size
            bw, bh = 98, 56
            bx = im.width - bw - int(im.width * 0.04)
            by = int(im.height * 0.04)
            
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=(255, 255, 255, 230), outline=(200, 200, 205), width=2)
            
            text_str = str(p)
            bbox = draw.textbbox((0, 0), text_str, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((bx + (bw - tw) // 2, by + (bh - th) // 2 - 4), text_str, fill=(0, 0, 0), font=font)
            return im

        im1, im2 = load_img(i1, p1), load_img(i2, p2)
        combined = Image.new("RGBA", (im1.width + im2.width + 20, 600), (0, 0, 0, 0))
        combined.paste(im1, (0, 0))
        combined.paste(im2, (im1.width + 20, 0))
        
        buffer = BytesIO()
        combined.save(buffer, format="PNG")
        buffer.seek(0)
        
        embed = discord.Embed(title=f"✨ {ctx.author.display_name} dropped 2 cards!", description=f"1️⃣ **{n1}** `[Print #{p1}]` (*{s1}*)\n2️⃣ **{n2}** `[Print #{p2}]` (*{s2}*)", color=discord.Color.blurple())
        embed.set_image(url="attachment://drop.png")
        await ctx.send(embed=embed, file=discord.File(buffer, filename="drop.png"), view=MultiClaimView(n1, n2))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@drop.error
async def drop_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Wait **{int(error.retry_after//60)}m {int(error.retry_after%60)}s**.")

@bot.command(name="daily")
async def daily(ctx):
    try:
        sha, content = await get_economy_data()
        user_id, t = str(ctx.author.id), time.time()
        lines, user_found, coins = content.splitlines(), False, 0
        new_lines = []

        for line in lines:
            if "|" in line:
                p = [x.strip() for x in line.split("|")]
                if p[0] == user_id:
                    user_found = True
                    h, coins = int(float(p[1])), int(float(p[2]))
                    v_time, d_time = float(p[3]) if len(p) > 3 and p[3] else 0.0, float(p[4]) if len(p) > 4 and p[4] else 0.0
                    if t - d_time < 86400:
                        left = int(86400 - (t - d_time))
                        return await ctx.send(f"⏳ Wait **{left//3600}h {(left%3600)//60}m** for daily.")
                    coins += random.randint(12, 88)
                    new_lines.append(f"{user_id} | {h} | {coins} | {v_time} | {t}")
                else: new_lines.append(line)
            elif line.strip(): new_lines.append(line)

        if not user_found:
            coins = random.randint(12, 88)
            new_lines.append(f"{user_id} | 0 | {coins} | 0.0 | {t}")

        await save_economy_data("\n".join(new_lines) + "\n", sha, f"Daily for {ctx.author}")
        await ctx.send(embed=discord.Embed(title="Daily Coiny", description=f"🎉 Claimed **{coins}** <:coiny:1531623010727891065> coins!", color=discord.Color.green()))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="hearty", aliases=["balance", "bal", "inv", "einv", "einventory", "inventory"])
async def hearty(ctx):
    try:
        _, content = await get_economy_data()
        h, c = 0, 0
        for line in content.splitlines():
            if "|" in line:
                p = [x.strip() for x in line.split("|")]
                if p[0] == str(ctx.author.id):
                    h, c = int(float(p[1])) if len(p) > 1 and p[1] else 0, int(float(p[2])) if len(p) > 2 and p[2] else 0
                    break
        embed = discord.Embed(title="Inventory", description=f"Items carried by {ctx.author.mention}", color=discord.Color.dark_theme())
        embed.add_field(name="Wallet", value=f"<:coiny:1531623010727891065> **{c}** · Coins\n<:hearty:1531623071067410504> **{h}** · Hearts", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="vote")
async def vote(ctx):
    try:
        sha, content = await get_economy_data()
        user_id, t = str(ctx.author.id), time.time()
        lines, user_found, new_lines = content.splitlines(), False, []

        for line in lines:
            if "|" in line:
                p = [x.strip() for x in line.split("|")]
                if p[0] == user_id:
                    user_found = True
                    h, coins = int(float(p[1])), int(float(p[2]))
                    v_time, d_time = float(p[3]) if len(p) > 3 and p[3] else 0.0, float(p[4]) if len(p) > 4 and p[4] else 0.0
                    if t - v_time < 43200:
                        left = int(43200 - (t - v_time))
                        return await ctx.send(f"⏳ Wait **{left//3600}h {(left%3600)//60}m** to vote.")
                    h += 1
                    new_lines.append(f"{user_id} | {h} | {coins} | {t} | {d_time}")
                else: new_lines.append(line)
            elif line.strip(): new_lines.append(line)

        if not user_found: new_lines.append(f"{user_id} | 1 | 0 | {t} | 0.0")
        await save_economy_data("\n".join(new_lines) + "\n", sha, f"Vote for {ctx.author}")
        
        url = "https://top.gg/bot/1531222383980056648/vote"
        await ctx.send(embed=discord.Embed(title="Vote", description=f"Vote here:\n{url}", color=discord.Color.purple()), view=VoteView(url))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="cooldown")
async def ecooldown(ctx):
    t = time.time()
    drop_txt = f"**{int((drop_cmd:=bot.get_command('drop'))._buckets.get_bucket(ctx.message).get_retry_after()//60)}m**" if drop_cmd and (r:=drop_cmd._buckets.get_bucket(ctx.message).get_retry_after()) else "Ready!"
    claim_txt = f"**{int((600 - (t - claim_cooldowns[ctx.author.id]))//60)}m**" if ctx.author.id in claim_cooldowns and t - claim_cooldowns[ctx.author.id] < 600 else "Ready!"
    
    v_txt, d_txt = "Ready!", "Ready!"
    try:
        _, content = await get_economy_data()
        for line in content.splitlines():
            if "|" in line:
                p = [x.strip() for x in line.split("|")]
                if p[0] == str(ctx.author.id):
                    if len(p) > 3 and p[3] and (vt:=float(p[3])) and t - vt < 43200:
                        v_txt = f"**{int(43200 - (t-vt))//3600}h**"
                    if len(p) > 4 and p[4] and (dt:=float(p[4])) and t - dt < 86400:
                        d_txt = f"**{int(86400 - (t-dt))//3600}h**"
                    break
    except: pass

    await ctx.send(embed=discord.Embed(title="Cooldowns", description=f"Drop: {drop_txt}\nClaim: {claim_txt}\nDaily: {d_txt}\nVote: {v_txt}", color=discord.Color.purple()))

@bot.command(name="collection", aliases=["ecollection", "ec"])
async def collection(ctx):
    try:
        cards = [card.strip() for line in (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt")).splitlines() if "|" in line for owner, card in [line.split("|", 1)] if owner.strip() == str(ctx.author.id)]
        if not cards: return await ctx.send("📦 Collection empty.")
        await ctx.send(embed=discord.Embed(title=f"🃏 {ctx.author.display_name}'s Collection", description="\n".join([f"`{i}` · {c}" for i, c in enumerate(cards, 1)]), color=discord.Color.blue()))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="view", aliases=["ev"])
async def view(ctx, idx: int):
    try:
        cards = [card.strip() for line in (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/inventory.txt")).splitlines() if "|" in line for owner, card in [line.split("|", 1)] if owner.strip() == str(ctx.author.id)]
        if not 1 <= idx <= len(cards): return await ctx.send("❌ Invalid index.")
        
        target, series, img = cards[idx - 1].split("#")[0].strip().lower(), "Unknown", None
        for line in (await _req("https://raw.githubusercontent.com/ieejoobinin12/eli-bot/main/cards.txt")).splitlines():
            if line.count("|") >= 2:
                p = [x.strip() for x in line.split("|", 2)]
                if p[0].lower() == target: series, img = p[1], p[2]; break
        
        if not img: return await ctx.send("⚠️ Image not found.")
        await ctx.send(embed=discord.Embed(title=f"#{idx} · {cards[idx-1]}", description=f"Series: *{series}*", color=discord.Color.purple()).set_image(url=img))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="trade", aliases=["et"])
async def trade(ctx, member: discord.Member = None):
    if not member and ctx.message.reference: member = (await ctx.channel.fetch_message(ctx.message.reference.message_id)).author
    if not member or member == ctx.author: return await ctx.send("❌ Mention someone to trade!")
    await ctx.send(content=member.mention, embed=discord.Embed(title="🤝 Trade Request", description=f"{ctx.author.mention} wants to trade with {member.mention}!", color=discord.Color.blurple()), view=TradeRequestView(ctx.author, member))

@bot.command(name="add", aliases=["ea"])
async def eadd(ctx, *, arg: str):
    if ctx.channel.id not in active_trade_channels or (view := active_trade_views.get(ctx.channel.id)).state != "active" or ctx.author not in (view.author, view.target):
        try: await ctx.message.delete()
        except: pass
        return

    try: await ctx.message.delete()
    except: pass

    user, arg = ctx.author, arg.strip().lower()
    user_cards = await get_user_cards(user.id)

    if arg.isdigit() and 1 <= (idx := int(arg)) <= len(user_cards):
        card = user_cards[idx - 1]
        target_list = view.author_cards if user == view.author else view.target_cards
        if card not in target_list: target_list.append(card)
    else:
        parts = arg.split()
        amt = int(parts[0]) if parts and parts[0].isdigit() else 1
        curr = parts[1] if len(parts) >= 2 else (parts[0] if parts else "")
        
        if "heart" in curr:
            if user == view.author: view.author_hearties += amt if parts[0].isdigit() else 1
            else: view.target_hearties += amt if parts[0].isdigit() else 1
        elif "coin" in curr:
            val = amt if parts[0].isdigit() else 100
            if user == view.author: view.author_coins += val
            else: view.target_coins += val

    if hasattr(view, 'message') and view.message:
        await view.message.edit(embed=view.build_embed(), view=view)

@bot.command(name="addcard")
async def addcard(ctx, *, data: str):
    if not GITHUB_TOKEN: return await ctx.send("Error: Missing GITHUB_TOKEN!")
    parts = [p.strip() for p in data.split("|")]
    if len(parts) < 3: return await ctx.send("❌ Format: `eaddcard Name | Series | URL`")
    name, series, url = parts[0], parts[1], parts[2]

    try:
        api_url = f"https://api.github.com/repos/{REPO_NAME}/contents/cards.txt"
        try:
            res = json.loads(await _req(api_url))
            sha, content = res['sha'], base64.b64decode(res['content']).decode('utf-8')
        except Exception:
            sha, content = None, ""

        await _req(api_url, {
            "message": f"Add {name}",
            "content": base64.b64encode((content.strip() + f"\n{name} | {series} | {url}\n").encode('utf-8')).decode('utf-8'),
            **({"sha": sha} if sha else {})
        }, method="PUT")
        await ctx.send(f"✅ Added card: **{name}**!")
    except Exception as e:
        await ctx.send(f"Error: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
