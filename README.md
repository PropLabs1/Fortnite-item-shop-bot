# Fortnite Item Shop Discord Bot

A Discord bot that shows the current Fortnite item shop and automatically posts updates when the shop changes.

## Features

- `/shop` - Shows current Fortnite item shop with icons and details
- `/item <item_name>` - Shows detailed information about a specific item
- `/setshopchannel <channel>` - Sets up automatic shop updates (Admin only)
- Automatic shop updates every 24 hours
- Color-coded rarity levels
- High-quality item images

## Railway Deployment

### Prerequisites
- Discord Bot Token
- Railway Account

### Steps

1. **Fork/Clone this repository** to your GitHub account

2. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

3. **Deploy to Railway**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect Python and deploy

4. **Set Environment Variables**
   - Go to your project settings in Railway
   - Add environment variable:
     - `DISCORD_BOT_TOKEN` = Your Discord bot token

5. **Deploy**
   - Railway will automatically deploy your bot
   - Check the logs to ensure it's running

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   - Create `.env` file with your bot token
   - Or set `DISCORD_BOT_TOKEN` environment variable

3. **Run bot:**
   ```bash
   python3 bot.py
   ```

## Commands

- `/shop` - Display current item shop
- `/item <name>` - Show detailed item info
- `/setshopchannel <channel>` - Set auto-update channel (Admin)

## Security Note

Never commit your bot token to version control. Use environment variables instead. 