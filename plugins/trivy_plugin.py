import subprocess
import json
import os
import re


# =========================
# 🔍 Find Dockerfiles
# =========================
def find_dockerfiles(repo_path):
    dockerfiles = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.lower() == "dockerfile":
                dockerfiles.append(os.path.join(root, f))
    return dockerfiles


# =========================
# 🔍 Extract base image
# =========================
def extract_base_image(dockerfile):
    try:
        with open(dockerfile) as f:
            for line in f:
                if line.strip().upper().startswith("FROM"):
                    return line.split()[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed reading Dockerfile: {e}")
    return None


# =========================
# 🔥 Deduplicate issues
# =========================
def deduplicate_issues(issues):
    seen = set()
    unique = []

    for i in issues:
        key = (
            i.get("id"),
            i.get("package"),
            i.get("target"),
            i.get("source")
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(i)

    return unique


# =========================
# 🔥 Normalize Fix Versions
# =========================
def normalize_fix_versions(fix):
    if not fix:
        return []
    if isinstance(fix, list):
        return fix
    return [v.strip() for v in str(fix).split(",") if v.strip()]


# =========================
# 🔥 Enrich Issue
# =========================
def enrich_issue(issue):
    severity = issue.get("severity", "LOW")

    priority_map = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    issue["priority"] = priority_map.get(severity, 0)
    issue["fixed_versions"] = normalize_fix_versions(issue.get("fix"))

    if issue["fixed_versions"]:
        issue["confidence"] = 95
    elif issue.get("fix"):
        issue["confidence"] = 80
    else:
        issue["confidence"] = 50

    return issue


# =========================
# 🚀 MAIN SCAN
# =========================
async def run(repo_path):

    issues = []

    print(f"[SCAN] Starting scan for: {repo_path}")

    # =========================
    # 🔥 FIXED: FILESYSTEM SCAN
    # =========================
    fs = subprocess.run(
        [
            "trivy",
            "fs",
            "--scanners", "vuln",
            "--format", "json",
            repo_path
        ],
        capture_output=True,
        text=True
    )

    try:
        data = json.loads(fs.stdout or "{}")
    except:
        print("[ERROR] Failed parsing FS scan")
        data = {}

    for r in data.get("Results", []):
        for v in r.get("Vulnerabilities", []):
            issues.append(enrich_issue({
                "id": v.get("VulnerabilityID"),
                "severity": v.get("Severity"),
                "package": v.get("PkgName"),
                "fix": v.get("FixedVersion"),
                "installed_version": v.get("InstalledVersion"),
                "target": r.get("Target"),
                "source": "fs"
            }))

    print(f"[DEBUG] FS findings: {len(issues)}")

    # =========================
    # 🐳 DOCKER BUILD + SCAN
    # =========================
    dockerfiles = find_dockerfiles(repo_path)

    print(f"[SCAN] Found {len(dockerfiles)} Dockerfiles")

    for dockerfile in dockerfiles:

        print(f"[SCAN] Processing Dockerfile: {dockerfile}")

        base_image = extract_base_image(dockerfile)
        print(f"[SCAN] Base image: {base_image}")

        # 🔥 BUILD IMAGE
        image_tag = f"scan-temp:{abs(hash(dockerfile))}"

        print(f"[DOCKER] Building image: {image_tag}")

        build = subprocess.run(
            ["docker", "build", "-t", image_tag, "-f", dockerfile, repo_path],
            capture_output=True,
            text=True
        )

        if build.returncode != 0:
            print("[ERROR] Docker build failed")
            print(build.stderr)
            continue

        # 🔥 SCAN BUILT IMAGE
        img = subprocess.run(
            [
                "trivy",
                "image",
                "--scanners", "vuln",
                "--vuln-type", "os,library",
                "--severity", "CRITICAL,HIGH",
                 "--ignore-unfixed",
                "--format", "json",
                image_tag
            ],
            capture_output=True,
            text=True
        )

        try:
            img_data = json.loads(img.stdout or "{}")
        except:
            print("[ERROR] Failed parsing image scan")
            img_data = {}

        for r in img_data.get("Results", []):
            for v in r.get("Vulnerabilities", []):
                issues.append(enrich_issue({
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "package": v.get("PkgName"),
                    "fix": v.get("FixedVersion"),
                    "installed_version": v.get("InstalledVersion"),
                    "target": dockerfile,
                    "source": f"image:{image_tag}"
                }))

    issues = deduplicate_issues(issues)
    issues.sort(key=lambda x: x.get("priority", 0), reverse=True)

    print(f"[FINAL] Total findings: {len(issues)}")

    return issues