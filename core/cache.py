import json
import os
import time

FILE = "cache.json"

def load():
    if not os.path.exists(FILE):
        return {}

    try:
        with open(FILE) as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception:
        return {}   # fallback if corrupted


def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f)


def get_cache(key):
    data = load()
    entry = data.get(key)

    if not entry:
        return None

    if time.time() > entry["expiry"]:
        del data[key]
        save(data)
        return None

    return entry["value"]


def set_cache(key, value, ttl):
    data = load()
    data[key] = {
        "value": value,
        "expiry": time.time() + ttl
    }
    save(data)