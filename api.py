from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import subprocess  # 🔥 NEW

from core.plugin_loader import load_plugins
from core.executor import execute_plugins
from core.deduplicator import deduplicate
from core.repo_manager import clone_repo
from core.language_detector import detect_language
from core.confidence import calculate_confidence
from core.semantic_patcher import semantic_patch_dockerfile
from core.dependency_patcher import patch_dependency_file
from core.diff_generator import generate_diff
from core.github_pr import create_pr, get_pr_status

from core.explainer import generate_summary

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Storage
# =========================
repo_data = {}
onboarded_repos = []
preview_cache = {}
patch_logs = {}
last_pr_number = None

# 🔥 NEW
pr_repo_map = {}


# =========================
# 🔥 Repo Sync Function
# =========================
def update_repo(repo_path):
    try:
        print("[GIT] Fetching latest...")
        subprocess.run(["git", "-C", repo_path, "fetch"], check=True)

        print("[GIT] Resetting to origin/main...")
        subprocess.run(
            ["git", "-C", repo_path, "reset", "--hard", "origin/main"],
            check=True
        )

        print("[GIT] Repo updated successfully")

    except Exception as e:
        print("[GIT ERROR]", e)


# =========================
# Repo onboarding
# =========================
@app.post("/onboard")
async def onboard_repo(payload: dict):
    repo = payload.get("repo")

    if repo and repo not in onboarded_repos:
        onboarded_repos.append(repo)

    return {"repos": onboarded_repos}


@app.get("/onboarded")
def get_onboarded():
    return {"repos": onboarded_repos}


# =========================
# 🚀 SCAN (UPDATED)
# =========================
@app.post("/scan")
async def scan_repo(payload: dict):
    repo = payload.get("repo")

    if not repo:
        return {"error": "repo required"}

    try:
        print(f"\n[SCAN] Starting scan for repo: {repo}")

        if repo in repo_data and os.path.exists(repo_data[repo]["path"]):
            repo_path = repo_data[repo]["path"]

            # 🔥 FIX: ALWAYS SYNC
            print("[CACHE] Updating repo before scan")
            update_repo(repo_path)

        else:
            repo_path = clone_repo(repo)

        language = detect_language(repo_path)

        plugins = load_plugins()
        results = await execute_plugins(plugins, repo_path)

        all_issues = deduplicate(results)

        filtered_issues = [
            i for i in all_issues
            if i.get("severity") in ["HIGH", "CRITICAL"]
        ][:50]

        for i in filtered_issues:
            i["confidence"] = calculate_confidence(i, language)

        snapshot = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "CRITICAL": len([i for i in filtered_issues if i["severity"] == "CRITICAL"]),
            "HIGH": len([i for i in filtered_issues if i["severity"] == "HIGH"]),
            "MEDIUM": len([i for i in filtered_issues if i["severity"] == "MEDIUM"]),
            "LOW": len([i for i in filtered_issues if i["severity"] == "LOW"]),
        }

        repo_data[repo] = {
            "issues": filtered_issues,
            "all_issues": all_issues,
            "history": repo_data.get(repo, {}).get("history", []) + [snapshot],
            "path": repo_path
        }

        print(f"[SCAN COMPLETE] {len(filtered_issues)} issues | {len(all_issues)} total")

        return {
            "issues": filtered_issues,
            "total_issues": len(all_issues),
            "language": language
        }

    except Exception as e:
        print("[ERROR]", e)
        return {"error": str(e)}


# =========================
# History
# =========================
@app.get("/history")
def get_history(repo: str):
    return {"history": repo_data.get(repo, {}).get("history", [])}


# =========================
# 🔍 Preview Fix (UNCHANGED)
# =========================
@app.post("/preview-fix")
async def preview_fix(payload: dict):
    repo = payload.get("repo")

    repo_info = repo_data.get(repo)
    if not repo_info:
        return {"error": "Run scan first"}

    repo_path = repo_info["path"]
    issues = repo_info.get("all_issues", repo_info["issues"])

    print(f"[PREVIEW] Using issues: {len(issues)}")

    diffs = []
    patch_log = []

    for root, _, files in os.walk(repo_path):
        for f in files:
            path = os.path.join(root, f)

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    original = file.read()
            except:
                continue

            updated = original

            if f in ["requirements.txt", "package.json", "pom.xml"]:
                result = patch_dependency_file(path, issues)

                if isinstance(result, tuple):
                    updated, log = result
                    patch_log.extend(log)
                else:
                    updated = result

            elif f.lower() == "dockerfile":
                updated = semantic_patch_dockerfile(original, issues)

            if original.strip() == updated.strip():
                continue

            diff = generate_diff(original, updated)

            if not diff:
                continue

            diffs.append({
                "file": path,
                "diff": diff,
                "updated": updated
            })

    if not diffs:
        return {"message": "No fixes needed", "diffs": []}

    preview_cache[repo] = diffs
    patch_logs[repo] = patch_log

    security_summary = generate_summary(issues)

    return {
        "diffs": diffs,
        "summary": {
            "files_changed": len(diffs),
            "total_fixes": len(issues),
            "security_summary": security_summary
        }
    }


# =========================
# 🚀 Create PR (UPDATED)
# =========================
@app.post("/create-pr")
async def create_pr_api(payload: dict):
    global last_pr_number

    import traceback

    repo = payload.get("repo")

    if not repo:
        return {"error": "repo required"}

    if repo not in preview_cache:
        return {"error": "Run preview first"}

    try:
        repo_name = repo.split("/")[-1]

        def normalize_git_path(file_path):
            prefix = f"repos/{repo_name}/"
            return file_path.replace(prefix, "")

        files_to_commit = []
        seen = set()

        for file_data in preview_cache[repo]:
            path = normalize_git_path(file_data["file"])

            if path in seen:
                continue
            seen.add(path)

            files_to_commit.append({
                "path": path,
                "content": file_data["updated"]
            })

        pr = create_pr(
            files_to_commit,
            repo,
            patch_logs.get(repo, []),
            repo_data[repo]["all_issues"]
        )

        if not pr:
            return {"error": "PR creation failed"}

        pr_number = pr.get("number")

        # 🔥 NEW
        pr_repo_map[pr_number] = repo

        last_pr_number = pr_number

        return {
            "url": pr.get("url"),
            "number": pr_number,
            "files": len(files_to_commit),
            "message": "PR created successfully"
        }

    except Exception as e:
        print("[PR ERROR]", traceback.format_exc())
        return {"error": str(e)}


# =========================
# 🔍 Check PR merged
# =========================
@app.get("/check-pr-merged")
def check_pr_merged(pr_number: int):
    status = get_pr_status(pr_number)
    return {"merged": status.get("merged", False)}


# =========================
# 🔁 AUTO REVALIDATE
# =========================
@app.post("/auto-revalidate")
async def auto_revalidate(payload: dict):
    pr_number = payload.get("pr_number")

    if pr_number not in pr_repo_map:
        return {"error": "Unknown PR"}

    repo = pr_repo_map[pr_number]

    print(f"[AUTO] Revalidating repo: {repo}")

    # 🔥 Clear cache
    repo_data.pop(repo, None)
    preview_cache.pop(repo, None)

    # 🔥 Re-scan
    result = await scan_repo({"repo": repo})

    return {
        "message": "Revalidation complete",
        "scan": result
    }


# =========================
# PR Status
# =========================
@app.get("/pr-status")
def pr_status():
    if not last_pr_number:
        return {"status": "no_pr"}

    return get_pr_status(last_pr_number)