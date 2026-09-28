import os

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()

publisher_url = os.getenv("REDIS_PUBLISHER_URL", "")

client = Redis.from_url(publisher_url)
