import os
import discord
import praw
import asyncio
from discord.ext import tasks, commands
from asyncpraw import Reddit  # Daha hızlı async desteği için
from flask import Flask
import threading

# Environment variables
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')

SUBREDDITS = [
    "legalteens",
    "collegesluts",
    "gonewild18",
    "realgirls",
    "homemadexxx",
    "nsfw_amateurs",
    "normalnudes",
    "irlgirls",
    "camsluts",
    "cosplaybutts"
]

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Render'ın sağladığı PORT değişkenini kullan
    app.run(host='0.0.0.0', port=port)

# Async Reddit client
reddit = Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="discord-bot/2.0"
)

class RedditMediaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())
        
    async def setup_hook(self):
        self.post_media.start()

    @tasks.loop(minutes=15)
    async def post_media(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            return

        async def process_subreddit(subreddit_name):
            try:
                subreddit = await reddit.subreddit(subreddit_name)
                async for submission in subreddit.new(limit=15):
                    if self.is_valid_media(submission):
                        return submission.url
                return None
            except Exception as e:
                print(f"Error in {subreddit_name}: {str(e)}")
                return None

        # Tüm subreddit'leri paralel işle
        tasks = [process_subreddit(sub) for sub in SUBREDDITS]
        results = await asyncio.gather(*tasks)

        # Bulunan URL'leri gönder
        for url in filter(None, results):
            await channel.send(url)
            await asyncio.sleep(1)  # Rate limit koruması

    def is_valid_media(self, submission):
        media_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.gifv', '.mp4', '.webm')
        return (
            not submission.over_18 and  # NSFW kontrolü kaldırıldı
            (submission.url.lower().endswith(media_extensions) or
             'redgifs' in submission.url or
             'imgur' in submission.url or
             getattr(submission, 'is_video', False))
        )

    @post_media.before_loop
    async def before_start(self):
        await self.wait_until_ready()

if __name__ == "__main__":
    # Flask sunucusunu ayrı bir thread'de çalıştır
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Discord botunu çalıştır
    bot = RedditMediaBot()
    bot.run(DISCORD_TOKEN)
