from upstash_redis import Redis
from config import REDIS_URL, REDIS_TOKEN

# Initialize Redis Instance
db = Redis(url=REDIS_URL, token=REDIS_TOKEN)

# --- CONFIGURATION ENGINE ---
def get_config(key: str, default: str = "on") -> str:
    val = db.get(f"config:{key}")
    return val if val else default

def set_config(key: str, value: str):
    db.set(f"config:{key}", value)

# --- WARNING TRACKER ENGINE ---
def get_warns(user_id: int) -> int:
    val = db.get(f"warn:{user_id}")
    return int(val) if val else 0

def add_warn(user_id: int) -> int:
    warns = get_warns(user_id) + 1
    db.set(f"warn:{user_id}", warns)
    return warns

def reset_warns(user_id: int):
    db.set(f"warn:{user_id}", 0)
