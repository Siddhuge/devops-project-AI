import yaml

def load_config():
    with open("config/config.yaml") as f:
        return yaml.safe_load(f)