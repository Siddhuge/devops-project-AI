import os

def detect_language(repo_path):

    files = os.listdir(repo_path)

    if "package.json" in files:
        return "node"

    if "requirements.txt" in files or "pyproject.toml" in files:
        return "python"

    if "pom.xml" in files:
        return "java"

    return "unknown"