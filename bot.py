import os
import discord
from discord.ext import tasks
import asyncpraw
import random
from datetime import datetime
import asyncio

# Environment variables'dan al
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '1219326585912561715'))
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'python:xbox.media.bot:v1.0')

# Discord bot ayarları
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Reddit API bağlantısı (asenkron)
async def init_reddit():
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

async def get_xbox_media():
    try:
        reddit = await init_reddit()
        subreddit = await reddit.subreddit('realgirls')
        media_posts = []

        async for post in subreddit.hot(limit=50):
            if hasattr(post, 'url'):
                url = post.url.lower()
                # Video kontrolü ekleyelim
                if hasattr(post, 'is_video') and post.is_video:
                    if hasattr(post, 'media') and 'reddit_video' in post.media:
                        media_posts.append({
                            'url': post.media['reddit_video']['fallback_url'],
                            'type': 'video'
                        })
                # Normal medya kontrolü
                elif any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.gifv', '.mp4']):
                    media_posts.append({
                        'url': post.url,
                        'type': 'image'
                    })

        await reddit.close()
        
        if media_posts:
            return random.choice(media_posts)
        return None
    except Exception as e:
        print(f"Reddit'ten medya alınırken hata oluştu: {e}")
        return None

async def send_media_message(channel):
    media_posts = []
    # 10 farklı medya al
    for _ in range(10):
        media_post = await get_xbox_media()
        if media_post and media_post['url'] not in [p['url'] for p in media_posts]:
            media_posts.append(media_post)
    
    # Tüm medyaları gönder
    if media_posts:
        try:
            for post in media_posts:
                await channel.send(post['url'])
                await asyncio.sleep(1)  # Her gönderi arasında 1 saniye bekle
        except Exception as e:
            print(f"Medya gönderilirken hata oluştu: {e}")
    else:
        print("Medya bulunamadı")

@client.event
async def on_ready():
    print(f'{client.user} olarak giriş yapıldı!')
    # İlk paylaşımı yap
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await send_media_message(channel)
    # 30 dakikalık döngüyü başlat
    send_xbox_media.start()

@tasks.loop(minutes=30)
async def send_xbox_media():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await send_media_message(channel)

client.run(TOKEN) 