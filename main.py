        import io
from PIL import Image
import requests

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
        
        # 1. Download character image
        char_res = requests.get(image_url.strip())
        char_img = Image.open(io.BytesIO(char_res.content)).convert("RGBA")
        
        # 2. Create a card base / frame (e.g., standard trading card size 400x600)
        card_width, card_height = 400, 600
        card = Image.new("RGBA", (card_width, card_height), (30, 30, 30, 255)) # Dark background frame
        
        # Resize character image to fit inside the frame nicely
        char_img = char_img.resize((360, 500))
        
        # Paste character onto the card frame (centered)
        card.paste(char_img, (20, 20), char_img)
        
        # Save to temporary buffer to send to Discord
        buffer = io.BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        
        file = discord.File(buffer, filename="card.png")
        
        embed = discord.Embed(
            title="🃏 A framed card has dropped!",
            description=f"You found: **{name.strip()}**",
            color=discord.Color.gold()
        )
        embed.set_image(url="attachment://card.png")
        
        await ctx.send(file=file, embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the framed card right now: {e}")
