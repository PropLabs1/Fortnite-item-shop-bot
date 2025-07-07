#!/bin/bash

# Install PM2 if not already installed
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    npm install -g pm2
fi

# Start the bot with PM2
echo "Starting Fortnite Shop Bot..."
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Set PM2 to start on system boot
pm2 startup

echo "Bot is now running with PM2!"
echo "Commands:"
echo "  pm2 status    - Check bot status"
echo "  pm2 logs      - View bot logs"
echo "  pm2 restart   - Restart bot"
echo "  pm2 stop      - Stop bot" 