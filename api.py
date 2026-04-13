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
patch_logs = {}  # 🔥 NEW
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

        if repo in repo_data and os.path.exists(repo_data[repo]["path"]):
            repo_path = repo_data[repo]["path"]
            print("[CACHE] Using existing repo")
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
# 🔍 Preview Fix (UPDATED)
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
    patch_log = []  # 🔥 NEW

    for root, _, files in os.walk(repo_path):
        for f in files:

            path = os.path.join(root, f)

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    original = file.read()
            except:
                continue

            updated = original

            # 🔥 Dependency patching (WITH LOG)
            if f in ["requirements.txt", "package.json", "pom.xml"]:
                updated = patch_dependency_file(path, issues)

            elif f.lower() == "dockerfile":
                updated = semantic_patch_dockerfile(original, issues)

            if original.strip() == updated.strip():
                continue

            diff = generate_diff(original, updated)

            if not diff or not isinstance(diff, str):
                continue

            diffs.append({
                "file": path,
                "diff": diff,
                "updated": updated
            })

    if not diffs:
        return {"message": "No fixes needed", "diffs": []}

    preview_cache[repo] = diffs
    patch_logs[repo] = patch_log  # 🔥 STORE

    return {
        "diffs": diffs,
        "summary": {
            "files_changed": len(diffs),
            "total_fixes": len(issues)
        }
    }


# =========================
# 🚀 Create PR (UPDATED)
# =========================
@app.post("/create-pr")
async def create_pr_api(payload: dict):
    global last_pr_number

    import traceback

    repo = None

    if isinstance(payload, dict):
        repo = payload.get("repo")

    if not repo and repo_data:
        repo = list(repo_data.keys())[-1]

    if not repo:
        return {"error": "repo required"}

    if repo not in preview_cache:
        return {"error": "Run preview first"}

    try:
        repo_name = repo.split("/")[-1]

        def normalize_git_path(file_path):
            prefix = f"repos/{repo_name}/"
            if file_path.startswith(prefix):
                return file_path[len(prefix):]
            return file_path

        files_to_commit = []
        seen = set()

        for file_data in preview_cache[repo]:
            raw_path = file_data["file"]
            updated = file_data["updated"]

            normalized_path = normalize_git_path(raw_path)

            if normalized_path in seen:
                continue
            seen.add(normalized_path)

            files_to_commit.append({
                "path": normalized_path,
                "content": updated
            })

        if not files_to_commit:
            return {"error": "No files to commit"}

        # 🔥 PASS PATCH LOG + ISSUES
        pr = create_pr(
            files_to_commit,
            repo,
            patch_logs.get(repo, []),
            repo_data[repo]["all_issues"]
        )

        if not pr:
            return {"error": "PR creation failed"}

        last_pr_number = pr.get("number")

        return {
            "url": pr.get("url"),
            "files": len(files_to_commit),
            "message": "PR created successfully"
        }

    except Exception as e:
        print("[PR ERROR]", traceback.format_exc())
        return {"error": f"PR creation failed: {str(e)}"}


# =========================
# PR Status
# =========================
@app.get("/pr-status")
def pr_status():
    if not last_pr_number:
        return {"status": "no_pr"}

    return get_pr_status(last_pr_number)