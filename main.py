import io
from PIL import Image, ImageOps

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
        
        # Download and open the card image
        char_res = requests.get(image_url.strip())
        card_img = Image.open(io.BytesIO(char_res.content)).convert("RGBA")
        
        # Add a sleek border frame around the image (e.g., 15 pixels of gold/dark frame)
        framed_img = ImageOps.expand(card_img, border=15, fill="#d4af37") # Gold border
        
        # Save to buffer
        buffer = io.BytesIO()
        framed_img.save(buffer, format="PNG")
        buffer.seek(0)
        
        file = discord.File(buffer, filename="framed_card.png")
        
        embed = discord.Embed(
            title="🃏 Card Drop!",
            description=f"A wild framed card appeared: **{name.strip()}**",
            color=discord.Color.gold()
        )
        embed.set_image(url="attachment://framed_card.png")
        embed.set_footer(text="✨ Type !addcard to add more cards!")
        
        await ctx.send(file=file, embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the framed card right now: {e}")

