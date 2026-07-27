
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
        
        # Framed text layout using markdown quotes and borders
        card_text = (
            "╔══════════════════════════╗\n"
            f" 🌟 **{name.strip()}** 🌟\n"
            "╚══════════════════════════╝"
        )
        
        embed = discord.Embed(
            description=card_text,
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url.strip())
        embed.set_footer(text="✨ Rarity: Common | Type !addcard to add more")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the card right now.")
