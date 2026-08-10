import os

# Telegram Settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "8859396816:AAFwRlqP9A-YDDumy6QIL9enWMtxW5o-Juo")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7517891518"))

# Database Settings
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Whitelisted Whitelists
ALLOWED_DOMAINS = ["animethic.xyz", "animethic.in"]
ALLOWED_CHANNEL = "@animethic2"
