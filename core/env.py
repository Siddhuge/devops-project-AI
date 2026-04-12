import os

def get_env(name, default=None, required=True):
    val = os.getenv(name, default)
    if required and not val:
        raise ValueError(f"Missing env variable: {name}")
    return val