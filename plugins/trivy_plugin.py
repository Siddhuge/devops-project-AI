import subprocess
import json
import os


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
                line = line.strip()
                if line.upper().startswith("FROM"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed reading Dockerfile: {e}")
    return None


# =========================
# 🔥 Validate Docker Image (IMPROVED)
# =========================
def validate_image(image):
    try:
        result = subprocess.run(
            ["docker", "manifest", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15
        )
        return result.returncode == 0
    except:
        return False


# =========================
# 🔥 Dynamic Image Resolver (FIXED)
# =========================
def get_valid_image(base_image):

    if not base_image:
        return None

    if ":" in base_image:
        name, tag = base_image.split(":", 1)
    else:
        name, tag = base_image, "latest"

    candidates = [
        base_image,
        f"{name}:{tag}-slim",
        f"{name}:{tag}-alpine",
        f"{name}:{tag}-jdk",
        f"{name}:{tag}-jre",
        f"{name}:latest",
        name
    ]

    # remove duplicates safely
    candidates = list(dict.fromkeys(candidates))

    print(f"[DEBUG] Image candidates: {candidates}")

    for img in candidates:
        print(f"[TRY] {img}")
        if validate_image(img):
            print(f"[IMAGE] Using: {img}")
            return img

    print(f"[INFO] Using fallback/AI resolution for base: {base_image}")
    return None


# =========================
# 🔥 Deduplicate issues (FIXED STRONGER)
# =========================
def deduplicate_issues(issues):

    seen = set()
    unique = []

    for i in issues:
        key = (
            i.get("id"),
            i.get("package"),
            i.get("target"),
            i.get("source")   # 🔥 FIX: avoid collapsing FS + image issues
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(i)

    return unique


# =========================
# 🔥 Normalize Fix Versions (NEW)
# =========================
def normalize_fix_versions(fix):
    if not fix:
        return []

    if isinstance(fix, list):
        return fix

    return [v.strip() for v in str(fix).split(",") if v.strip()]


# =========================
# 🔥 Add priority + confidence
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

    # 🔥 Normalize fix versions (IMPORTANT for patcher)
    issue["fixed_versions"] = normalize_fix_versions(issue.get("fix"))

    # 🔥 Confidence logic improved
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
    # 🔥 FILESYSTEM SCAN
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
        print("[ERROR] Failed parsing FS scan output")
        data = {}

    for r in data.get("Results", []):
        for v in r.get("Vulnerabilities", []):
            issue = {
                "id": v.get("VulnerabilityID"),
                "severity": v.get("Severity"),
                "package": v.get("PkgName"),
                "fix": v.get("FixedVersion"),
                "installed_version": v.get("InstalledVersion"),
                "target": r.get("Target"),
                "source": "fs"
            }

            issues.append(enrich_issue(issue))

    print(f"[DEBUG] FS findings: {len(issues)}")

    # =========================
    # 🐳 DOCKER IMAGE SCAN
    # =========================
    dockerfiles = find_dockerfiles(repo_path)

    print(f"[SCAN] Found {len(dockerfiles)} Dockerfiles")

    for dockerfile in dockerfiles:

        print(f"[SCAN] Processing Dockerfile: {dockerfile}")

        base_image = extract_base_image(dockerfile)

        if not base_image:
            print("[WARN] No base image found")
            continue

        print(f"[SCAN] Base image: {base_image}")

        valid_image = get_valid_image(base_image)

        if not valid_image:
            issues.append(enrich_issue({
                "id": "IMAGE_NOT_FOUND",
                "severity": "LOW",
                "package": base_image,
                "fix": "Use supported base image",
                "target": dockerfile,
                "source": "docker"
            }))
            continue

        img = subprocess.run(
            [
                "trivy",
                "image",
                "--scanners", "vuln",
                "--format", "json",
                valid_image
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

                issue = {
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "package": v.get("PkgName"),
                    "fix": v.get("FixedVersion"),
                    "installed_version": v.get("InstalledVersion"),
                    "target": dockerfile,
                    "source": f"image:{valid_image}"
                }

                issues.append(enrich_issue(issue))

    # =========================
    # 🔥 FINAL CLEANUP
    # =========================
    issues = deduplicate_issues(issues)

    # 🔥 Sort by priority
    issues.sort(key=lambda x: x.get("priority", 0), reverse=True)

    print(f"[FINAL] Total findings: {len(issues)}")

    return issues