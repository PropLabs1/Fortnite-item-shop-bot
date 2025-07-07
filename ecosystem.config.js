module.exports = {
  apps: [{
    name: 'fortnite-shop-bot',
    script: 'python3',
    args: 'bot.py',
    cwd: '/Users/conor/Documents/Discord Bot Fn item shop',
    watch: false,
    instances: 1,
    autorestart: true,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    }
  }]
} 