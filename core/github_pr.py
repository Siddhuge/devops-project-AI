import os
from github import Github
from datetime import datetime


# =========================
# 🔐 Get Repo (Dynamic)
# =========================
def get_github_repo(repo_full_name=None):

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise Exception("GITHUB_TOKEN not set")

    g = Github(token)

    if repo_full_name:
        return g.get_repo(repo_full_name)

    repo_name = os.getenv("GITHUB_REPO")

    if not repo_name:
        raise Exception("GITHUB_REPO not set")

    return g.get_repo(repo_name)


# =========================
# 🧠 BUILD PR BODY (AI ENHANCED)
# =========================
def build_pr_body(files, patch_log=None, issues=None):

    body = "🚀 AI DevSecOps Security Fix\n\n"

    body += f"📦 Files Updated: {len(files)}\n"

    if issues:
        body += f"🐞 Total Vulnerabilities: {len(issues)}\n"

    body += "\n---\n"

    # =========================
    # 🔐 PATCH DETAILS
    # =========================
    if patch_log:
        body += "### 🔧 Applied Fixes:\n\n"

        for p in patch_log:
            body += f"- {p}\n"

        body += "\n---\n"

    # =========================
    # ⚠️ RISK SUMMARY
    # =========================
    risk = "LOW"

    if patch_log:
        if any("HIGH" in p for p in patch_log):
            risk = "HIGH"
        elif any("MEDIUM" in p for p in patch_log):
            risk = "MEDIUM"

    body += f"### ⚠️ Risk Level: {risk}\n\n"

    # =========================
    # 📌 NOTES
    # =========================
    body += "### 📌 Notes:\n"
    body += "- CVE-aware version selection applied\n"
    body += "- Safe upgrades preferred (same major version)\n"
    body += "- Dockerfile hardened (non-root user, optimized installs)\n"

    return body


# =========================
# 🚀 Create PR (MULTI-FILE SUPPORT)
# =========================
def create_pr(files, repo_full_name, patch_log=None, issues=None):

    repo = get_github_repo(repo_full_name)

    base_branch = "main"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"ai-fix-{timestamp}"

    base = repo.get_branch(base_branch)

    # =========================
    # 🔥 Create Branch (Safe)
    # =========================
    try:
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base.commit.sha
        )
        print(f"[PR] Created branch: {branch_name}")
    except Exception:
        print(f"[PR] Branch already exists, reusing: {branch_name}")

    # =========================
    # 🔥 Commit ALL FILES
    # =========================
    for file in files:

        path = file["path"]
        content = file["content"]

        print(f"[PR] Processing file: {path}")

        try:
            existing = repo.get_contents(path, ref=base_branch)

            repo.update_file(
                path=path,
                message=f"fix(security): update {path}",
                content=content,
                sha=existing.sha,
                branch=branch_name
            )

            print(f"[PR] Updated: {path}")

        except Exception:
            try:
                repo.create_file(
                    path=path,
                    message=f"fix(security): add {path}",
                    content=content,
                    branch=branch_name
                )

                print(f"[PR] Created: {path}")

            except Exception as e:
                print(f"[PR ERROR] Failed for {path}: {str(e)}")
                raise e

    # =========================
    # 🔥 Build PR Body
    # =========================
    pr_body = build_pr_body(files, patch_log, issues)

    # =========================
    # 🔥 Create PR
    # =========================
    try:
        pr = repo.create_pull(
            title=f"🔐 AI DevSecOps Fix ({len(files)} files)",
            body=pr_body,
            head=branch_name,
            base=base_branch
        )

        print(f"[PR] Created PR: {pr.html_url}")

        return {
            "url": pr.html_url,
            "number": pr.number
        }

    except Exception as e:
        print("[PR ERROR] PR creation failed:", str(e))
        raise e


# =========================
# 🔁 PR Status
# =========================
def get_pr_status(pr_number):

    repo = get_github_repo()

    pr = repo.get_pull(pr_number)

    return {
        "state": pr.state,
        "merged": pr.is_merged()
    }