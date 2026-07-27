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
            
        # Format the list of cards
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
