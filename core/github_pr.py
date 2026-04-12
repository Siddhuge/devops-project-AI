import os
from github import Github
from datetime import datetime


def get_github_repo():
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")

    if not token or not repo_name:
        raise Exception("GITHUB_TOKEN or GITHUB_REPO not set")

    g = Github(token)
    return g.get_repo(repo_name)


# =========================
# 🚀 Create PR
# =========================
def create_pr(file_path, updated_content):

    repo = get_github_repo()

    base_branch = "main"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"ai-fix-{timestamp}"

    base = repo.get_branch(base_branch)

    # 🔥 Create new branch
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=base.commit.sha
    )

    # 🔥 Get file from main
    file = repo.get_contents(file_path, ref=base_branch)

    # 🔥 Update file in new branch
    repo.update_file(
        path=file_path,
        message="AI Security Fix",
        content=updated_content,
        sha=file.sha,
        branch=branch_name
    )

    # 🔥 Create PR
    pr = repo.create_pull(
        title="AI Security Fix",
        body="Auto-generated vulnerability fixes",
        head=branch_name,
        base=base_branch
    )

    return {
        "url": pr.html_url,
        "number": pr.number
    }


# =========================
# 🔁 PR Status
# =========================
def get_pr_status(pr_number):

    repo = get_github_repo()

    pr = repo.get_pull(pr_number)

    return {
        "state": pr.state,         # open / closed
        "merged": pr.is_merged()   # True / False
    }