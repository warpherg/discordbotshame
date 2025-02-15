import os
import discord
from discord.ext import tasks
import asyncpraw
import random
import asyncio
import logging
from urllib.parse import urlparse

# Environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'python:multireddit.bot:v2.0')
SUBREDDITS = os.getenv('SUBREDDITS', 'legalteens+collegesluts+gonewild18+realgirls+homemadexxx+nsfw_amateurs+normalnudes+irlgirls+camsluts+cosplaybutts').split('+')

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Configurations
POST_CACHE = set()
MAX_POSTS = 200
TARGET_POSTS = 15
CACHE_SIZE = 500
SUBREDDIT_LIMIT = 2  # Her subreddit'ten max içerik

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_reddit():
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

async def fetch_content():
    try:
        reddit = await init_reddit()
        content_pool = []
        
        for subreddit_name in SUBREDDITS:
            subreddit = await reddit.subreddit(subreddit_name)
            try:
                async for post in subreddit.hot(limit=30):
                    if len(content_pool) >= MAX_POSTS:
                        break
                        
                    if post.id in POST_CACHE:
                        continue
                        
                    # Medya URL kontrolü
                    if hasattr(post, 'is_video') and post.is_video:
                        url = getattr(post.media, 'fallback_url', '')
                    else:
                        url = getattr(post, 'url', '')
                        
                    if not url or 'reddit.com/gallery' in url:
                        continue
                        
                    content_pool.append({
                        'url': url,
                        'subreddit': subreddit.display_name,
                        'nsfw': post.over_18
                    })
                    POST_CACHE.add(post.id)
                    
            except Exception as sub_error:
                logger.error(f"{subreddit_name} error: {str(sub_error)}")
                
            await asyncio.sleep(1)  # Rate limit önleme

        await reddit.close()
        return content_pool
        
    except Exception as e:
        logger.error(f"Reddit connection error: {str(e)}")
        return []

async def send_content(channel):
    try:
        all_content = await fetch_content()
        if not all_content:
            logger.warning("No content found")
            return

        # NSFW filtreleme ve karıştırma
        safe_content = [c for c in all_content if not c['nsfw']]
        random.shuffle(safe_content)
        
        # Subreddit dağılımı
        selected = []
        subreddit_counts = {sub: 0 for sub in SUBREDDITS}
        
        for content in safe_content:
            sub = content['subreddit'].lower()
            if subreddit_counts.get(sub, 0) < SUBREDDIT_LIMIT:
                selected.append(content)
                subreddit_counts[sub] += 1
                
            if len(selected) >= TARGET_POSTS:
                break

        # Gönderim işlemi
        for item in selected[:TARGET_POSTS]:
            try:
                parsed_url = urlparse(item['url'])
                if parsed_url.scheme and parsed_url.netloc:
                    await channel.send(f"**r/{item['subreddit']}**\n{item['url']}")
                    await asyncio.sleep(4)  # Rate limit koruması
            except Exception as send_error:
                logger.error(f"Send error: {str(send_error)}")

    except Exception as e:
        logger.error(f"Content processing error: {str(e)}")

@client.event
async def on_ready():
    logger.info(f'Bot aktif: {client.user}')
    try:
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await send_content(channel)
            content_loop.start()
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")

@tasks.loop(minutes=60)
async def content_loop():
    try:
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await send_content(channel)
    except Exception as e:
        logger.error(f"Loop error: {str(e)}")

@content_loop.before_loop
async def before_loop():
    await client.wait_until_ready()

if __name__ == "__main__":
    client.run(TOKEN)
