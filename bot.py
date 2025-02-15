import os
import discord
import praw
import asyncio
import time
from discord.ext import tasks, commands

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

# Reddit API setup
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="discord-bot/1.0"
)

class RedditMediaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
        
    async def setup_hook(self):
        self.post_media.start()

    @tasks.loop(minutes=15)
    async def post_media(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            return

        # Time-based subreddit selection
        epoch_time = int(time.time())
        interval = (epoch_time // 60) % len(SUBREDDITS)  # 900 saniye = 15 dakika
        target_subreddit = SUBREDDITS[interval]

        # Find valid media post
        submission = self.find_media_post(target_subreddit)
        if submission:
            await channel.send(submission.url)

    def find_media_post(self, subreddit_name):
        for submission in reddit.subreddit(subreddit_name).new(limit=15):
            if self.is_valid_media(submission):
                return submission
        return None

    def is_valid_media(self, submission):
        media_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.gifv', '.mp4', '.webm')
        return (
            not submission.is_self and
            (submission.url.lower().endswith(media_extensions) or
             'redgifs' in submission.url or
             'imgur' in submission.url or
             submission.is_video)
        )

    @post_media.before_loop
    async def before_start(self):
        await self.wait_until_ready()

if __name__ == "__main__":
    bot = RedditMediaBot()
    bot.run(DISCORD_TOKEN)
