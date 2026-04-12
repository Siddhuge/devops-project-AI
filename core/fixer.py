import hashlib, json
from openai import AzureOpenAI
from core.config import load_config
from core.env import get_env
from core.cache import get_cache, set_cache

config = load_config()

client = AzureOpenAI(
    api_key=get_env("AZURE_OPENAI_KEY"),
    api_version=config["ai"]["azure"]["api_version"],
    azure_endpoint=get_env("AZURE_OPENAI_ENDPOINT")
)

DEPLOYMENT = config["ai"]["azure"]["deployment_name"]
CHEAP = get_env("AZURE_OPENAI_CHEAP_DEPLOYMENT", DEPLOYMENT, False)

def key(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()

def generate_fix(v):
    k = key(v)

    if config["cache"]["enabled"]:
        cached = get_cache(k)
        if cached:
            return cached

    model = DEPLOYMENT if v["severity"] in ["CRITICAL","HIGH"] else CHEAP

    res = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":str(v)}],
        temperature=0.2
    )

    out = res.choices[0].message.content

    if config["cache"]["enabled"]:
        set_cache(k, out, config["cache"]["ttl_seconds"])

    return out