import discord
from discord.ext import commands, tasks
import requests
import os
import json

# Import bot token from config
from config import TOKEN

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="Fortnite Item Shop"))



# Global variables
shop_channel_id = None  # Will be set by admin command
last_shop_data = None

# Fortnite API URL - using a more reliable endpoint
FORTNITE_API_URL = 'https://fortnite-api.com/v2/shop'

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print('Bot is now watching the Fortnite Item Shop! 🛒')
    check_shop_update.start()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="shop", description="Show the current Fortnite item shop")
async def shop(interaction: discord.Interaction):
    """Show the current Fortnite item shop."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if shop_data:
        embeds = format_shop_embed(shop_data)
        
        # Send first embed
        await interaction.followup.send(embed=embeds[0])
        
        # Send additional embeds if there are more
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send('Could not fetch the item shop.')

@bot.tree.command(name="item", description="Show detailed information about a specific item")
async def item(interaction: discord.Interaction, item_name: str):
    """Show detailed information about a specific item."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    if item.get('name', '').lower() == item_name.lower():
                        embed = create_item_detail_embed(item, entry)
                        await interaction.followup.send(embed=embed)
                        return
            
            await interaction.followup.send(f'Item "{item_name}" not found in the current shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in item command: {e}')
        await interaction.followup.send('Error fetching item details.')

def create_item_detail_embed(item, entry):
    """Create a detailed embed for a specific item."""
    name = item.get('name', 'Unknown Item')
    description = item.get('description', 'No description available.')
    price = entry.get('finalPrice', 0)
    rarity = item.get('rarity', {}).get('displayValue', 'Common')
    item_type = item.get('type', {}).get('displayValue', 'Item')
    set_info = item.get('set', {}).get('text', '')
    
    # Get images
    images = item.get('images', {})
    icon_url = images.get('icon', '')
    featured_url = images.get('featured', '')
    
    # Create embed
    embed = discord.Embed(
        title=f'🎮 {name}',
        description=description,
        color=get_rarity_color(rarity)
    )
    
    # Add fields
    embed.add_field(name="💰 Price", value=f"{price} V-Bucks", inline=True)
    embed.add_field(name="⭐ Rarity", value=rarity, inline=True)
    embed.add_field(name="📦 Type", value=item_type, inline=True)
    
    if set_info:
        embed.add_field(name="🎯 Set", value=set_info, inline=False)
    
    # Set images
    if featured_url:
        embed.set_image(url=featured_url)
    elif icon_url:
        embed.set_thumbnail(url=icon_url)
    
    # Add bundle info if available
    if entry.get('bundle'):
        embed.add_field(name="📦 Bundle", value=entry['bundle']['name'], inline=False)
    
    return embed

def get_rarity_color(rarity):
    """Get color based on item rarity."""
    colors = {
        'Common': 0x8A8A8A,    # Gray
        'Uncommon': 0x2D8E47,  # Green
        'Rare': 0x4A90E2,      # Blue
        'Epic': 0x9B4F96,      # Purple
        'Legendary': 0xE6B800, # Gold
        'Mythic': 0xFF6B35     # Orange
    }
    return colors.get(rarity, 0x00ff00)

@bot.tree.command(name="setshopchannel", description="Set the channel for automatic item shop updates (Admin only)")
async def setshopchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel for automatic item shop updates."""
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return
    
    global shop_channel_id
    shop_channel_id = channel.id
    await interaction.response.send_message(f'Item shop updates will be sent to {channel.mention}')

@bot.tree.command(name="search", description="Search for items in the current shop")
async def search(interaction: discord.Interaction, query: str):
    """Search for items in the current shop."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            found_items = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    name = item.get('name', '').lower()
                    description = item.get('description', '').lower()
                    
                    if query.lower() in name or query.lower() in description:
                        found_items.append((item, entry))
            
            if found_items:
                embed = discord.Embed(
                    title=f'🔍 Search Results for "{query}"',
                    color=0x4A90E2
                )
                
                for i, (item, entry) in enumerate(found_items[:5]):  # Show up to 5 results
                    name = item.get('name', 'Unknown Item')
                    price = entry.get('finalPrice', 0)
                    rarity = item.get('rarity', {}).get('displayValue', 'Common')
                    
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"💰 {price} V-Bucks | ⭐ {rarity}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f'No items found matching "{query}".')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in search command: {e}')
        await interaction.followup.send('Error searching for items.')

@bot.tree.command(name="price", description="Check the price of a specific item")
async def price(interaction: discord.Interaction, item_name: str):
    """Check the price of a specific item."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    if item.get('name', '').lower() == item_name.lower():
                        name = item.get('name', 'Unknown Item')
                        price = entry.get('finalPrice', 0)
                        original_price = entry.get('regularPrice', price)
                        rarity = item.get('rarity', {}).get('displayValue', 'Common')
                        
                        embed = discord.Embed(
                            title=f'💰 {name}',
                            color=get_rarity_color(rarity)
                        )
                        
                        embed.add_field(name="Current Price", value=f"{price} V-Bucks", inline=True)
                        if original_price != price:
                            embed.add_field(name="Original Price", value=f"{original_price} V-Bucks", inline=True)
                            discount = original_price - price
                            embed.add_field(name="Discount", value=f"Save {discount} V-Bucks! 🎉", inline=True)
                        
                        embed.add_field(name="Rarity", value=rarity, inline=True)
                        embed.add_field(name="Type", value=item.get('type', {}).get('displayValue', 'Item'), inline=True)
                        
                        # Add item icon if available
                        if item.get('images') and item['images'].get('icon'):
                            embed.set_thumbnail(url=item['images']['icon'])
                        
                        await interaction.followup.send(embed=embed)
                        return
            
            await interaction.followup.send(f'Item "{item_name}" not found in the current shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in price command: {e}')
        await interaction.followup.send('Error checking item price.')

@bot.tree.command(name="deals", description="Show items that are on sale/discount")
async def deals(interaction: discord.Interaction):
    """Show items that are on sale/discount."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            deals = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    original_price = entry.get('regularPrice', 0)
                    final_price = entry.get('finalPrice', 0)
                    
                    if final_price < original_price:
                        item = entry['brItems'][0]
                        name = item.get('name', 'Unknown Item')
                        discount = original_price - final_price
                        discount_percent = int((discount / original_price) * 100)
                        
                        deals.append({
                            'name': name,
                            'original': original_price,
                            'final': final_price,
                            'discount': discount,
                            'percent': discount_percent,
                            'item': item,
                            'entry': entry
                        })
            
            if deals:
                # Sort by discount percentage (highest first)
                deals.sort(key=lambda x: x['percent'], reverse=True)
                
                embed = discord.Embed(
                    title='🔥 Hot Deals!',
                    description='Items currently on sale:',
                    color=0xFF6B35
                )
                
                for i, deal in enumerate(deals[:8]):  # Show up to 8 deals
                    embed.add_field(
                        name=f"🎉 {deal['name']}",
                        value=f"~~{deal['original']}~~ **{deal['final']}** V-Bucks\n"
                              f"💸 Save {deal['discount']} V-Bucks ({deal['percent']}% off!)",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send('No items are currently on sale.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in deals command: {e}')
        await interaction.followup.send('Error fetching deals.')

@bot.tree.command(name="stats", description="Show shop statistics")
async def stats(interaction: discord.Interaction):
    """Show shop statistics."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            
            total_items = len(entries)
            total_value = sum(entry.get('finalPrice', 0) for entry in entries)
            
            # Count by rarity
            rarity_counts = {}
            type_counts = {}
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    rarity = item.get('rarity', {}).get('displayValue', 'Unknown')
                    item_type = item.get('type', {}).get('displayValue', 'Unknown')
                    
                    rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                    type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            embed = discord.Embed(
                title='📊 Shop Statistics',
                color=0x4A90E2
            )
            
            embed.add_field(name="Total Items", value=total_items, inline=True)
            embed.add_field(name="Total Value", value=f"{total_value:,} V-Bucks", inline=True)
            
            # Add rarity breakdown
            rarity_text = "\n".join([f"{rarity}: {count}" for rarity, count in rarity_counts.items()])
            if rarity_text:
                embed.add_field(name="Rarity Breakdown", value=rarity_text, inline=True)
            
            # Add type breakdown
            type_text = "\n".join([f"{item_type}: {count}" for item_type, count in type_counts.items()])
            if type_text:
                embed.add_field(name="Type Breakdown", value=type_text, inline=True)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in stats command: {e}')
        await interaction.followup.send('Error fetching shop statistics.')

@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show all available commands."""
    embed = discord.Embed(
        title='🛒 Fortnite Shop Bot Commands',
        description='Here are all the available commands:',
        color=0x00ff00
    )
    
    commands_info = [
        ("`/shop`", "Show the current Fortnite item shop with icons and details"),
        ("`/item <name>`", "Show detailed information about a specific item"),
        ("`/search <query>`", "Search for items in the current shop"),
        ("`/price <item>`", "Check the price of a specific item"),
        ("`/deals`", "Show items that are currently on sale/discount"),
        ("`/stats`", "Show shop statistics and breakdown"),
        ("`/rarity <type>`", "Show items filtered by rarity (Common, Rare, Epic, etc.)"),
        ("`/type <type>`", "Show items filtered by type (Outfit, Backpack, Pickaxe, etc.)"),
        ("`/expensive`", "Show the most expensive items in the shop"),
        ("`/cheap`", "Show the cheapest items in the shop"),
        ("`/bundles`", "Show all bundle items in the shop"),
        ("`/info`", "Show bot information and status"),
        ("`/setshopchannel <channel>`", "Set up automatic shop updates (Admin only)"),
        ("`/help`", "Show this help message")
    ]
    
    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="Bot automatically checks for shop updates every 24 hours!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rarity", description="Show items by rarity")
async def rarity(interaction: discord.Interaction, rarity_type: str):
    """Show items filtered by rarity."""
    await interaction.response.defer()
    
    # Valid rarity types
    valid_rarities = ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic']
    rarity_type = rarity_type.lower()
    
    if rarity_type not in valid_rarities:
        await interaction.followup.send(f'Invalid rarity. Please choose from: {", ".join(valid_rarities).title()}')
        return
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            rarity_items = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    item_rarity = item.get('rarity', {}).get('value', '').lower()
                    
                    if item_rarity == rarity_type:
                        name = item.get('name', 'Unknown Item')
                        price = entry.get('finalPrice', 0)
                        item_type = item.get('type', {}).get('displayValue', 'Item')
                        rarity_items.append((name, price, item_type, item, entry))
            
            if rarity_items:
                embed = discord.Embed(
                    title=f'⭐ {rarity_type.title()} Items',
                    description=f'All {rarity_type.title()} items currently in the shop:',
                    color=get_rarity_color(rarity_type.title())
                )
                
                for i, (name, price, item_type, item, entry) in enumerate(rarity_items[:10]):
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"💰 {price} V-Bucks | 📦 {item_type}",
                        inline=False
                    )
                
                if len(rarity_items) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(rarity_items)} {rarity_type.title()} items")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f'No {rarity_type.title()} items found in the current shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in rarity command: {e}')
        await interaction.followup.send('Error fetching rarity items.')

@bot.tree.command(name="type", description="Show items by type")
async def type_filter(interaction: discord.Interaction, item_type: str):
    """Show items filtered by type."""
    await interaction.response.defer()
    
    # Valid item types
    valid_types = ['outfit', 'backpack', 'pickaxe', 'glider', 'emote', 'wrap', 'music', 'banner']
    item_type = item_type.lower()
    
    if item_type not in valid_types:
        await interaction.followup.send(f'Invalid type. Please choose from: {", ".join(valid_types).title()}')
        return
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            type_items = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    item_type_value = item.get('type', {}).get('value', '').lower()
                    
                    if item_type_value == item_type:
                        name = item.get('name', 'Unknown Item')
                        price = entry.get('finalPrice', 0)
                        rarity = item.get('rarity', {}).get('displayValue', 'Common')
                        type_items.append((name, price, rarity, item, entry))
            
            if type_items:
                embed = discord.Embed(
                    title=f'📦 {item_type.title()} Items',
                    description=f'All {item_type.title()} items currently in the shop:',
                    color=0x4A90E2
                )
                
                for i, (name, price, rarity, item, entry) in enumerate(type_items[:10]):
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"💰 {price} V-Bucks | ⭐ {rarity}",
                        inline=False
                    )
                
                if len(type_items) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(type_items)} {item_type.title()} items")
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f'No {item_type.title()} items found in the current shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in type command: {e}')
        await interaction.followup.send('Error fetching type items.')

@bot.tree.command(name="expensive", description="Show the most expensive items in the shop")
async def expensive(interaction: discord.Interaction):
    """Show the most expensive items in the shop."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            price_items = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    name = item.get('name', 'Unknown Item')
                    price = entry.get('finalPrice', 0)
                    rarity = item.get('rarity', {}).get('displayValue', 'Common')
                    item_type = item.get('type', {}).get('displayValue', 'Item')
                    price_items.append((name, price, rarity, item_type, item, entry))
            
            if price_items:
                # Sort by price (highest first)
                price_items.sort(key=lambda x: x[1], reverse=True)
                
                embed = discord.Embed(
                    title='💰 Most Expensive Items',
                    description='Top 10 most expensive items in the shop:',
                    color=0xFFD700
                )
                
                for i, (name, price, rarity, item_type, item, entry) in enumerate(price_items[:10]):
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"💰 **{price:,}** V-Bucks | ⭐ {rarity} | 📦 {item_type}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send('No items found in the shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in expensive command: {e}')
        await interaction.followup.send('Error fetching expensive items.')

@bot.tree.command(name="cheap", description="Show the cheapest items in the shop")
async def cheap(interaction: discord.Interaction):
    """Show the cheapest items in the shop."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            price_items = []
            
            for entry in entries:
                if entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    name = item.get('name', 'Unknown Item')
                    price = entry.get('finalPrice', 0)
                    rarity = item.get('rarity', {}).get('displayValue', 'Common')
                    item_type = item.get('type', {}).get('displayValue', 'Item')
                    price_items.append((name, price, rarity, item_type, item, entry))
            
            if price_items:
                # Sort by price (lowest first)
                price_items.sort(key=lambda x: x[1])
                
                embed = discord.Embed(
                    title='💸 Cheapest Items',
                    description='Top 10 cheapest items in the shop:',
                    color=0x2D8E47
                )
                
                for i, (name, price, rarity, item_type, item, entry) in enumerate(price_items[:10]):
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"💰 **{price:,}** V-Bucks | ⭐ {rarity} | 📦 {item_type}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send('No items found in the shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in cheap command: {e}')
        await interaction.followup.send('Error fetching cheap items.')

@bot.tree.command(name="bundles", description="Show all bundle items in the shop")
async def bundles(interaction: discord.Interaction):
    """Show all bundle items in the shop."""
    await interaction.response.defer()
    
    shop_data = fetch_shop()
    if not shop_data:
        await interaction.followup.send('Could not fetch the item shop.')
        return
    
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            bundle_items = []
            
            for entry in entries:
                if entry.get('bundle') and entry.get('brItems') and entry['brItems']:
                    item = entry['brItems'][0]
                    name = item.get('name', 'Unknown Item')
                    price = entry.get('finalPrice', 0)
                    bundle_name = entry['bundle'].get('name', 'Unknown Bundle')
                    rarity = item.get('rarity', {}).get('displayValue', 'Common')
                    bundle_items.append((name, price, bundle_name, rarity, item, entry))
            
            if bundle_items:
                embed = discord.Embed(
                    title='📦 Bundle Items',
                    description='All bundle items currently in the shop:',
                    color=0x9B4F96
                )
                
                for i, (name, price, bundle_name, rarity, item, entry) in enumerate(bundle_items):
                    embed.add_field(
                        name=f"{i+1}. {name}",
                        value=f"📦 **{bundle_name}**\n💰 {price:,} V-Bucks | ⭐ {rarity}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send('No bundle items found in the current shop.')
        else:
            await interaction.followup.send('No shop data available.')
            
    except Exception as e:
        print(f'Error in bundles command: {e}')
        await interaction.followup.send('Error fetching bundle items.')

@bot.tree.command(name="info", description="Show bot information and status")
async def info(interaction: discord.Interaction):
    """Show bot information and status."""
    # Check if user is the bot owner
    if interaction.user.id != 1264677032357527607:  # Your Discord user ID
        await interaction.response.send_message("❌ This command is restricted to the bot owner only.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title='🤖 Fortnite Shop Bot Info',
        description='Information about this bot:',
        color=0x00ff00
    )
    
    # Bot stats
    embed.add_field(
        name="📊 Bot Status",
        value=f"✅ Online\n🕐 Uptime: Running\n🔄 Auto-updates: {'Enabled' if shop_channel_id else 'Disabled'}",
        inline=False
    )
    
    # Features
    embed.add_field(
        name="🎮 Features",
        value="• Complete shop display\n• Item search & filtering\n• Price checking\n• Sale detection\n• Statistics\n• Automatic updates",
        inline=False
    )
    
    # Commands count
    embed.add_field(
        name="📋 Commands",
        value="14 total commands available",
        inline=True
    )
    
    # API Status
    embed.add_field(
        name="🌐 API Status",
        value="✅ Fortnite API Connected",
        inline=True
    )
    
    embed.set_footer(text="Made with ❤️ for Fortnite players")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

def fetch_shop():
    """Fetch the current Fortnite item shop data."""
    try:
        response = requests.get(FORTNITE_API_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'API request failed with status code: {response.status_code}')
    except requests.RequestException as e:
        print(f'Error fetching shop: {e}')
    except json.JSONDecodeError as e:
        print(f'Error parsing JSON response: {e}')
    return None

def format_shop_embed(shop_data):
    """Format the shop data into a Discord embed."""
    try:
        if 'data' in shop_data and shop_data['data']:
            entries = shop_data['data'].get('entries', [])
            
            if entries:
                # Create multiple embeds to show all items
                embeds = []
                current_embed = discord.Embed(
                    title='🛒 Fortnite Item Shop - All Items', 
                    color=0x00ff00,
                    description='📋 **Complete list of all items currently in the shop:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                )
                
                item_count = 0
                items_per_embed = 8  # Reduced for better readability
                
                for i, entry in enumerate(entries):
                    if entry.get('brItems') and entry['brItems']:
                        item = entry['brItems'][0]
                        name = item.get('name', 'Unknown Item')
                        price = entry.get('finalPrice', 0)
                        rarity = item.get('rarity', {}).get('displayValue', 'Common')
                        item_type = item.get('type', {}).get('displayValue', 'Item')
                        
                        # Add bundle info if available
                        bundle_info = ""
                        if entry.get('bundle'):
                            bundle_info = f" (Bundle: {entry['bundle']['name']})"
                        
                        # Check if item is on sale
                        original_price = entry.get('regularPrice', price)
                        sale_info = ""
                        if original_price != price:
                            discount = original_price - price
                            sale_info = f"💰 ~~{original_price}~~ **{price}** V-Bucks 💸 **SAVE {discount}!**"
                        else:
                            sale_info = f"💰 **{price}** V-Bucks"
                        
                        # Create item field with better formatting
                        item_text = f"{sale_info}\n"
                        item_text += f"⭐ *{rarity} {item_type}*{bundle_info}"
                        
                        # Add to current embed with better spacing
                        current_embed.add_field(
                            name=f"{i+1}. {name}",
                            value=item_text,
                            inline=False  # Changed to False for better readability
                        )
                        
                        item_count += 1
                        
                        # Create new embed if we've reached the limit
                        if item_count >= items_per_embed:
                            current_embed.set_footer(text=f"Page {len(embeds) + 1} • Shop updates every 24 hours")
                            embeds.append(current_embed)
                            
                            # Start new embed
                            current_embed = discord.Embed(
                                title='🛒 Fortnite Item Shop - All Items (Continued)', 
                                color=0x00ff00,
                                description='📋 **More items from the shop:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                            )
                            item_count = 0
                
                # Add the last embed if it has items
                if item_count > 0:
                    current_embed.set_footer(text=f"Page {len(embeds) + 1} • Shop updates every 24 hours")
                    embeds.append(current_embed)
                
                # Set thumbnail to first item's icon if available
                if entries and entries[0].get('brItems') and entries[0]['brItems']:
                    first_item = entries[0]['brItems'][0]
                    if first_item.get('images') and first_item['images'].get('icon'):
                        embeds[0].set_thumbnail(url=first_item['images']['icon'])
                
                return embeds if embeds else [discord.Embed(title="No items found in the shop.", color=0xff0000)]
            else:
                return [discord.Embed(title="No items found in the shop.", color=0xff0000)]
        else:
            return [discord.Embed(title="No shop data available.", color=0xff0000)]
            
    except Exception as e:
        print(f'Error formatting shop embed: {e}')
        return [discord.Embed(title="Error loading shop data.", color=0xff0000)]

@tasks.loop(minutes=10)
async def check_shop_update():
    global last_shop_data
    if shop_channel_id is None:
        return
    shop_data = fetch_shop()
    if shop_data and shop_data != last_shop_data:
        last_shop_data = shop_data
        channel = bot.get_channel(shop_channel_id)
        if channel:
            embeds = format_shop_embed(shop_data)
            
            # Send update notification with first embed
            await channel.send('🆕 **The Fortnite Item Shop has updated!**', embed=embeds[0])
            
            # Send additional embeds if there are more
            for embed in embeds[1:]:
                await channel.send(embed=embed)

if __name__ == '__main__':
    bot.run(TOKEN) 