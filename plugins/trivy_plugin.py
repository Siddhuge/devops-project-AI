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
# 🔍 Extract base image (multi-stage safe)
# =========================
def extract_base_image(dockerfile):
    try:
        with open(dockerfile) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("FROM"):
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    return parts[1].strip()
    except:
        pass

    return None


# =========================
# 🔥 Validate Docker Image (SAFE)
# =========================
def validate_image(image):

    try:
        result = subprocess.run(
            ["docker", "pull", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
            text=True
        )

        if result.returncode == 0:
            return True

        return False

    except Exception as e:
        return False


# =========================
# 🔥 Dynamic Image Resolver (IMPROVED)
# =========================
def get_valid_image(base_image):

    candidates = []

    # Normalize
    if ":" in base_image:
        name, tag = base_image.split(":", 1)
    else:
        name, tag = base_image, "latest"

    # 🔥 Smart candidate generation
    candidates = [
        base_image,
        f"{name}:{tag}-slim",
        f"{name}:{tag}-alpine",
        f"{name}:latest",
        name
    ]

    # Remove duplicates
    candidates = list(dict.fromkeys(candidates))

    print(f"[DEBUG] Image candidates: {candidates}")

    for img in candidates:
        print(f"[TRY] {img}")

        if validate_image(img):
            print(f"[IMAGE] Using: {img}")
            return img

    print(f"[WARN] No valid image found for base: {base_image}")
    return None


# =========================
# 🔥 Deduplicate issues (PLUGIN LEVEL)
# =========================
def deduplicate_issues(issues):

    seen = set()
    unique = []

    for i in issues:
        key = (i["id"], i["package"], i["target"])

        if key in seen:
            continue

        seen.add(key)
        unique.append(i)

    return unique


# =========================
# 🚀 MAIN SCAN
# =========================
async def run(repo_path):

    issues = []

    print(f"[SCAN] Starting scan for: {repo_path}")

    # =========================
    # 🔥 FILESYSTEM SCAN (OPTIMIZED)
    # =========================
    fs = subprocess.run(
        [
            "trivy",
            "fs",
            "--scanners", "vuln",   # 🔥 faster
            "--format", "json",
            repo_path
        ],
        capture_output=True,
        text=True
    )

    try:
        data = json.loads(fs.stdout or "{}")
    except:
        data = {}

    for r in data.get("Results", []):
        for v in r.get("Vulnerabilities", []):
            issues.append({
                "id": v.get("VulnerabilityID"),
                "severity": v.get("Severity"),
                "package": v.get("PkgName"),
                "fix": v.get("FixedVersion"),
                "target": r.get("Target"),
                "source": "fs"
            })

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

        # 🔥 If no valid image → fallback info
        if not valid_image:
            issues.append({
                "id": "IMAGE_NOT_FOUND",
                "severity": "LOW",
                "package": base_image,
                "fix": "Use a valid/supported base image",
                "target": dockerfile,
                "source": "docker"
            })
            continue

        # =========================
        # 🔍 Image Scan
        # =========================
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
            img_data = {}

        for r in img_data.get("Results", []):
            for v in r.get("Vulnerabilities", []):
                issues.append({
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "package": v.get("PkgName"),
                    "fix": v.get("FixedVersion"),
                    "target": dockerfile,
                    "source": f"image:{valid_image}"
                })

    # =========================
    # 🔥 FINAL CLEANUP
    # =========================
    issues = deduplicate_issues(issues)

    print(f"[FINAL] Total findings: {len(issues)}")

    return issues