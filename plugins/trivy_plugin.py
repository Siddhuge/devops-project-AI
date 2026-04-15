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
# 🔍 Extract ALL base images
# =========================
def extract_base_images(dockerfile):
    images = []
    try:
        with open(dockerfile) as f:
            for line in f:
                line = line.strip()
                if line.upper().startswith("FROM"):
                    parts = line.split()
                    if len(parts) >= 2:
                        images.append(parts[1].strip())
    except Exception as e:
        print(f"[ERROR] Failed reading Dockerfile: {e}")
    return images


# =========================
# 🧠 Detect runtime vs builder
# =========================
def get_stage_type(base_images, current):
    if not base_images:
        return "runtime"
    return "runtime" if current == base_images[-1] else "builder"


# =========================
# 🔥 Detect image type
# =========================
def detect_image_type(image):
    image = image.lower()

    if any(x in image for x in ["ubuntu", "debian", "alpine", "centos"]):
        return "os"

    if any(x in image for x in ["node", "python", "openjdk", "golang", "ruby"]):
        return "os,library"

    if "distroless" in image:
        return "library"

    if image == "scratch":
        return "skip"

    return "os,library"


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
# 🔥 Enrich Issue (WITH STAGE)
# =========================
def enrich_issue(issue, stage="builder"):
    severity = issue.get("severity", "LOW")

    priority_map = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    base_priority = priority_map.get(severity, 0)
    stage_weight = 2 if stage == "runtime" else 1

    issue["priority"] = base_priority * stage_weight
    issue["stage"] = stage
    issue["stage_weight"] = stage_weight

    fix_versions = normalize_fix_versions(issue.get("fix"))
    issue["fixed_versions"] = fix_versions

    if fix_versions:
        issue["confidence"] = 95
    elif issue.get("fix"):
        issue["confidence"] = 80
    else:
        issue["confidence"] = 50

    return issue


# =========================
# 🔥 Enterprise Dedup (IMPROVED)
# =========================
def deduplicate_issues(issues):
    best = {}

    for i in issues:
        key = (i.get("id"), i.get("package"))

        if key not in best:
            best[key] = i
            continue

        existing = best[key]

        # Prefer runtime issues
        if i.get("stage") == "runtime" and existing.get("stage") != "runtime":
            best[key] = i
            continue

        # Prefer higher priority
        if i.get("priority", 0) > existing.get("priority", 0):
            best[key] = i
            continue

        # Prefer fix availability
        if i.get("fixed_versions") and not existing.get("fixed_versions"):
            best[key] = i

    return list(best.values())


# =========================
# 🚀 MAIN SCAN
# =========================
async def run(repo_path):

    issues = []

    print(f"[SCAN] Starting scan for: {repo_path}")

    # =========================
    # 🔍 FILESYSTEM SCAN
    # =========================
    fs = subprocess.run(
        ["trivy", "fs", "--scanners", "vuln", "--format", "json", repo_path],
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
    # 🐳 DOCKER SCAN
    # =========================
    dockerfiles = find_dockerfiles(repo_path)
    print(f"[SCAN] Found {len(dockerfiles)} Dockerfiles")

    for dockerfile in dockerfiles:

        print(f"[SCAN] Processing Dockerfile: {dockerfile}")

        base_images = extract_base_images(dockerfile)
        print(f"[SCAN] Base images: {base_images}")

        image_tag = f"scan-temp:{abs(hash(dockerfile))}"

        print(f"[DOCKER] Building image: {image_tag}")

        build = subprocess.run(
            ["docker", "build", "-t", image_tag, "-f", dockerfile, repo_path],
            capture_output=True,
            text=True
        )

        build_failed = build.returncode != 0

        if build_failed:
            print("[ERROR] Docker build failed")
            print(build.stderr)

        # 🔥 Scan ONCE if build success
        built_image_scanned = False

        for base_image in base_images:

            stage = get_stage_type(base_images, base_image)
            print(f"[STAGE] {base_image} → {stage}")

            image_type = detect_image_type(base_image)

            if image_type == "skip":
                continue

            if not build_failed:
                # scan built image only once
                if built_image_scanned:
                    continue
                image_to_scan = image_tag
                built_image_scanned = True
            else:
                image_to_scan = base_image
                print(f"[FALLBACK] Scanning base image: {base_image}")

            img = subprocess.run(
                [
                    "trivy",
                    "image",
                    "--scanners", "vuln",
                    "--vuln-type", image_type,
                    "--severity", "CRITICAL,HIGH",
                    "--ignore-unfixed",
                    "--format", "json",
                    image_to_scan
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
                        "source": f"image:{image_to_scan}"
                    }, stage=stage))

    issues = deduplicate_issues(issues)

    # 🔥 Runtime-first sorting
    issues.sort(key=lambda x: (
        x.get("stage") != "runtime",
        -x.get("priority", 0)
    ))

    print(f"[FINAL] Total findings: {len(issues)}")

    return issues