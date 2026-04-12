from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

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
last_pr_number = None


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
# 🚀 SCAN
# =========================
@app.post("/scan")
async def scan_repo(payload: dict):
    repo = payload.get("repo")

    if not repo:
        return {"error": "repo required"}

    try:
        print(f"\n[SCAN] Starting scan for repo: {repo}")

        # 🔥 CACHE: avoid re-cloning every time
        if repo in repo_data and os.path.exists(repo_data[repo]["path"]):
            repo_path = repo_data[repo]["path"]
            print("[CACHE] Using existing repo")
        else:
            repo_path = clone_repo(repo)

        language = detect_language(repo_path)

        plugins = load_plugins()

        results = await execute_plugins(plugins, repo_path)

        deduped = deduplicate(results)

        # 🔥 FILTER NOISE (IMPORTANT)
        deduped = [
            i for i in deduped
            if i.get("severity") in ["HIGH", "CRITICAL"]
        ]

        for i in deduped:
            i["confidence"] = calculate_confidence(i, language)

        snapshot = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "CRITICAL": len([i for i in deduped if i["severity"] == "CRITICAL"]),
            "HIGH": len([i for i in deduped if i["severity"] == "HIGH"]),
            "MEDIUM": len([i for i in deduped if i["severity"] == "MEDIUM"]),
            "LOW": len([i for i in deduped if i["severity"] == "LOW"]),
        }

        repo_data[repo] = {
            "issues": deduped,              # 🔹 filtered (UI)
            "all_issues": results,          # 🔥 FULL issues (IMPORTANT FIX)
            "history": repo_data.get(repo, {}).get("history", []) + [snapshot],
            "path": repo_path
        }
        print(f"[SCAN COMPLETE] {len(deduped)} issues")

        return {"issues": deduped, "total_issues": len(results), "language": language}

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
# 🔍 Preview Fix
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

    for root, _, files in os.walk(repo_path):
        for f in files:

            path = os.path.join(root, f)

            try:
                with open(path, "r") as file:
                    original = file.read()
            except:
                continue

            updated = original

            # 🔥 Dependency patching
            if f in ["requirements.txt", "package.json", "pom.xml"]:
                updated = patch_dependency_file(path, issues)

            # 🔥 Dockerfile patching (minimal)
            elif f.lower() == "dockerfile":
                updated = semantic_patch_dockerfile(original, issues)

            # Skip unchanged
            if original.strip() == updated.strip():
                continue

            diff = generate_diff(original, updated)

            # 🔥 PREVENT UI CRASH
            if not diff or not isinstance(diff, str):
                continue

            diffs.append({
                "file": path,
                "diff": diff,
                "updated": updated
            })

    if not diffs:
        return {"message": "No fixes needed", "diffs": []}

    preview_cache["files"] = diffs

    return {
        "diffs": diffs,
        "summary": {
            "files_changed": len(diffs),
            "total_fixes": len(issues)
        }
    }


# =========================
# 🚀 Create PR
# =========================
@app.post("/create-pr")
async def create_pr_api():
    global last_pr_number

    if "files" not in preview_cache:
        return {"error": "Run preview first"}

    pr_links = []

    for file_data in preview_cache["files"]:
        file_path = file_data["file"].split("repos/")[-1]
        updated = file_data["updated"]

        pr = create_pr(file_path, updated)

        last_pr_number = pr.get("number")
        pr_links.append(pr.get("url"))

    return {"urls": pr_links}


# =========================
# PR Status
# =========================
@app.get("/pr-status")
def pr_status():
    if not last_pr_number:
        return {"status": "no_pr"}

    return get_pr_status(last_pr_number)