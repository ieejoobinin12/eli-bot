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
            description=f"A wild card appeared: **{name.strip()}**",
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url.strip())
        embed.set_footer(text="✨ Type !addcard to add more cards!")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Oops! Couldn't load the card right now: {e}")
