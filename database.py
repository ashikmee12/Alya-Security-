import os
import logging

logger = logging.getLogger(__name__)

# Environment Variable থেকে URL ও Token নেওয়া এবং .strip() দিয়ে ক্লিন করা
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

db = None

try:
    if UPSTASH_URL and UPSTASH_TOKEN:
        from upstash_redis import Redis
        db = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)
    else:
        logger.warning("Upstash Redis credentials are missing in Environment Variables.")
except Exception as e:
    logger.error(f"Failed to initialize Upstash Redis: {e}")

def get_config(key, default="off"):
    if not db:
        return default
    try:
        val = db.get(f"config:{key}")
        if val is None:
            return default
        # Boolean বা String হ্যান্ডলিং
        if isinstance(val, bytes):
            val = val.decode('utf-8')
        return str(val)
    except Exception as e:
        logger.error(f"Redis get_config error for key '{key}': {e}")
        return default

def set_config(key, value):
    if not db:
        return False
    try:
        db.set(f"config:{key}", str(value))
        return True
    except Exception as e:
        logger.error(f"Redis set_config error for key '{key}': {e}")
        return False
