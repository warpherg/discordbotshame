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
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '1219326585912561715'))
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'python:multireddit.bot:v1.0')
SUBREDDITS = os.getenv('SUBREDDITS', 'legalteens+collegesluts+gonewild18+realgirls+homemadexxx+nsfw_amateurs+normalnudes+irlgirls+camsluts+cosplaybutts').split('+')

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Configurations
POST_CACHE = set()
MAX_POSTS = 150  # Toplam çekilecek post sayısı
MEDIA_LIMIT = 15  # Gönderilecek içerik sayısı
CACHE_SIZE = 300  # Maksimum önbellek boyutu

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_reddit():
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

async def get_reddit_media():
    try:
        reddit = await init_reddit()
        subreddit = await reddit.subreddit('+'.join(SUBREDDITS))
        media_posts = []
        
        async for post in subreddit.hot(limit=MAX_POSTS):
            if len(media_posts) >= MEDIA_LIMIT * 2:  # Yeterli çeşitlilik için
                break
                
            if post.id in POST_CACHE:
                continue

            url = getattr(post, 'url', '')
            if not url:
                continue

            # Video kontrolü
            if getattr(post, 'is_video', False) and post.media:
                media_url = None
                if 'reddit_video' in post.media:
                    media_url = post.media['reddit_video']['fallback_url']
                elif 'dash_url' in post.media:
                    media_url = post.media['dash_url']
                
                if media_url:
                    media_posts.append({'url': media_url, 'source': post.subreddit})
                    POST_CACHE.add(post.id)

            # Resim/GIF kontrolü
            elif hasattr(post, 'post_hint') and post.post_hint in ['image', 'rich:video']:
                media_posts.append({'url': url, 'source': post.subreddit})
                POST_CACHE.add(post.id)

            # Önbellek temizleme
            if len(POST_CACHE) > CACHE_SIZE:
                POST_CACHE.pop()

        await reddit.close()
        return media_posts
    except Exception as e:
        logger.error(f"Reddit error: {str(e)}")
        return []

async def send_media_message(channel):
    try:
        media_posts = await get_reddit_media()
        if not media_posts:
            logger.warning("No media found")
            return

        # Benzersiz subreddit dağılımı
        selected = []
        subreddit_groups = {}
        
        for post in media_posts:
            sub = post['source'].display_name.lower()
            if sub not in subreddit_groups:
                subreddit_groups[sub] = []
            subreddit_groups[sub].append(post)

        # Her subreddit'ten en fazla 2 içerik
        for sub in subreddit_groups.values():
            selected += random.sample(sub, min(2, len(sub)))

        # Rastgele karıştır ve limit uygula
        random.shuffle(selected)
        final_selection = selected[:MEDIA_LIMIT]

        # Gönderim işlemi
        for post in final_selection:
            try:
                parsed = urlparse(post['url'])
                if parsed.netloc in ['v.redd.it', 'i.redd.it', 'i.imgur.com', 'gfycat.com']:
                    await channel.send(f"**r/{post['source']}**\n{post['url']}")
                    await asyncio.sleep(3)  # Rate limit önleme
            except Exception as e:
                logger.error(f"Gönderim hatası: {str(e)}")

    except Exception as e:
        logger.error(f"Genel hata: {str(e)}")

@client.event
async def on_ready():
    logger.info(f'{client.user} başarıyla giriş yaptı!')
    
    try:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            raise ValueError("Kanal bulunamadı")
            
        await send_media_message(channel)
        send_media.start()
    except Exception as e:
        logger.error(f"Başlangıç hatası: {str(e)}")

@tasks.loop(minutes=45)
async def send_media():
    try:
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await send_media_message(channel)
    except Exception as e:
        logger.error(f"Görev hatası: {str(e)}")

@send_media.before_loop
async def before_task():
    await client.wait_until_ready()

if __name__ == "__main__":
    client.run(TOKEN)
