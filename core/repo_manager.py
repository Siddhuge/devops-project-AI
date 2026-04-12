import os
import subprocess

BASE_DIR = "repos"


def clone_repo(repo_url: str) -> str:
    os.makedirs(BASE_DIR, exist_ok=True)

    repo_name = repo_url.split("/")[-1]
    repo_path = os.path.join(BASE_DIR, repo_name)

    # =========================
    # ✅ CACHE: If exists → pull instead of clone
    # =========================
    if os.path.exists(repo_path):

        try:
            subprocess.run(
                ["git", "-C", repo_path, "pull"],
                check=True
            )
        except:
            pass

        return repo_path

    # =========================
    # FIRST TIME CLONE
    # =========================
    clone_url = f"https://github.com/{repo_url}.git"

    subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, repo_path],
        check=True
    )

    return repo_path