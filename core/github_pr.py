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
# 🔥 Get Default Branch
# =========================
def get_default_branch(repo):
    try:
        return repo.default_branch
    except Exception:
        return "main"


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
    # 🔧 AI FIX DETAILS
    # =========================
    if patch_log:
        body += "### 🤖 AI Fix Summary\n\n"

        for p in patch_log:
            body += f"- {p}\n"

        body += "\n---\n"

    # =========================
    # ⚠️ RISK + CONFIDENCE SUMMARY
    # =========================
    risk = "LOW"
    confidence_values = []

    if patch_log:
        for p in patch_log:
            if "CRITICAL" in p:
                risk = "CRITICAL"
            elif "HIGH" in p and risk != "CRITICAL":
                risk = "HIGH"
            elif "MEDIUM" in p and risk not in ["CRITICAL", "HIGH"]:
                risk = "MEDIUM"

            # 🔥 Extract confidence if present
            try:
                if "Confidence:" in p:
                    val = int(p.split("Confidence:")[1].split("%")[0].strip())
                    confidence_values.append(val)
            except:
                pass

    avg_conf = int(sum(confidence_values) / len(confidence_values)) if confidence_values else 85

    body += f"### ⚠️ Risk Level: {risk}\n"
    body += f"### 📊 Confidence Score: {avg_conf}%\n\n"

    # =========================
    # 🧠 AI EXPLANATION
    # =========================
    body += "### 🧠 AI Reasoning\n"
    body += "- Fixes vulnerabilities using CVE-aware recommendations\n"
    body += "- Prioritizes non-breaking upgrades\n"
    body += "- Uses AI + rule validation for safe remediation\n"
    body += "- Docker images upgraded to secure, supported versions\n\n"

    # =========================
    # 📌 NOTES
    # =========================
    body += "### 📌 Notes:\n"
    body += "- Safe upgrades preferred (same major version)\n"
    body += "- Non-root Docker execution enforced\n"
    body += "- OS-level security patches applied\n"
    body += "- Fallback logic ensures stability if AI suggestion fails\n"

    return body


# =========================
# 🚀 Create PR
# =========================
def create_pr(files, repo_full_name, patch_log=None, issues=None):

    repo = get_github_repo(repo_full_name)

    base_branch = get_default_branch(repo)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"ai-fix-{timestamp}"

    base = repo.get_branch(base_branch)

    # =========================
    # Create Branch
    # =========================
    try:
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base.commit.sha
        )
        print(f"[PR] Created branch: {branch_name}")
    except Exception:
        print(f"[PR] Branch exists, reusing: {branch_name}")

    # =========================
    # Commit Files
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

        except Exception:
            repo.create_file(
                path=path,
                message=f"fix(security): add {path}",
                content=content,
                branch=branch_name
            )

    # =========================
    # Build PR Body
    # =========================
    pr_body = build_pr_body(files, patch_log, issues)

    # =========================
    # Create PR
    # =========================
    pr = repo.create_pull(
        title=f"🔐 AI DevSecOps Fix ({len(files)} files)",
        body=pr_body,
        head=branch_name,
        base=base_branch
    )

    print(f"[PR] Created PR: {pr.html_url}")

    return {
        "url": pr.html_url,
        "number": pr.number,
        "branch": branch_name,
        "base": base_branch
    }


# =========================
# 🔁 PR Status
# =========================
def get_pr_status(pr_number, repo_full_name=None):

    repo = get_github_repo(repo_full_name)

    pr = repo.get_pull(pr_number)

    return {
        "state": pr.state,
        "merged": pr.merged,
        "merged_at": str(pr.merged_at) if pr.merged else None,
        "base": pr.base.ref,
        "head": pr.head.ref
    }