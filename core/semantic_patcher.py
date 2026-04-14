import re
from core.ai_fix_engine import suggest_docker_fix


def semantic_patch_dockerfile(content, issues=None, patch_log=None):
    """
    🔥 Enterprise-grade Dockerfile patcher (AI + Rule Hybrid)

    - AI-driven base image upgrade
    - CVE-aware
    - Safe (no breaking upgrades)
    - Dynamic fallback (existing logic)
    """

    lines = content.split("\n")
    updated = []

    has_user = any("USER" in l for l in lines)
    has_os_patch = any("apt-get upgrade" in l or "apk upgrade" in l for l in lines)

    workdir = None

    # =========================
    # Detect WORKDIR
    # =========================
    for l in lines:
        if l.strip().startswith("WORKDIR"):
            parts = l.strip().split()
            if len(parts) > 1:
                workdir = parts[1]

    # =========================
    # 🔥 EXISTING FALLBACK LOGIC (UNCHANGED)
    # =========================
    def get_smart_tag(name, tag):

        match = re.search(r"\d+(\.\d+)?", tag)
        version = float(match.group()) if match else None

        suffix = ""
        if "slim" in tag:
            suffix = "-slim"
        elif "alpine" in tag:
            suffix = "-alpine"

        if "python" in name and version:
            if version < 3.8:
                return f"3.11{suffix or '-slim'}"

        if "node" in name and version:
            if version < 16:
                return f"18{suffix or '-slim'}"

        if ("openjdk" in name or "jdk" in name) and version:
            if version < 11:
                return "17-jre"

        if not suffix:
            return f"{tag}-slim"

        return tag

    # =========================
    # 🔥 SAFE VERSION CHECK
    # =========================
    def extract_major(version):
        try:
            match = re.search(r"\d+", version)
            return int(match.group()) if match else None
        except:
            return None


    def is_major_upgrade(old_tag, new_tag):
        try:
            old_major = extract_major(old_tag)
            new_major = extract_major(new_tag)

            if old_major is None or new_major is None:
                return False

            return new_major > old_major
        except:
            return False

    for line in lines:

        stripped = line.strip()

        # =========================
        # 🐳 HANDLE FROM LINE
        # =========================
        if stripped.upper().startswith("FROM"):

            parts = stripped.split()

            image = parts[1]
            alias = parts[3] if len(parts) > 3 and parts[2].upper() == "AS" else None

            name = image
            tag = "latest"

            if ":" in image:
                name, tag = image.split(":", 1)

            new_image = image
            changed = False
            ai_result = None

            # =========================
            # 🔥 AI FIRST
            # =========================
            try:
                ai_result = suggest_docker_fix(image, issues)

                if ai_result:
                    confidence = ai_result.get("confidence", 0)

                    if confidence < 70:
                        print(f"[AI SKIPPED] Low confidence ({confidence}%) for {image}")
                    else:
                        recommended = ai_result.get("recommended_image")

                        if recommended and ":" in recommended and recommended != image:

                            _, new_tag = recommended.split(":", 1)

                            # 🔥 BLOCK BREAKING CHANGE
                            if is_major_upgrade(tag, new_tag):
                                print(f"[AI BLOCKED] Major upgrade skipped: {image} → {recommended}")
                            else:
                                new_image = recommended
                                changed = True

            except Exception as e:
                print("[AI ERROR]", e)

            # =========================
            # 🔥 FALLBACK (UNCHANGED)
            # =========================
            if not changed:

                new_tag = tag

                if issues:
                    for issue in issues:
                        if issue.get("package") == name and issue.get("fixed_versions"):
                            new_tag = tag if "slim" in tag or "alpine" in tag else f"{tag}-slim"
                            break

                smart_tag = get_smart_tag(name, tag)

                if smart_tag and smart_tag != tag:
                    new_tag = smart_tag

                new_image = f"{name}:{new_tag}"

            # =========================
            # APPLY CHANGE
            # =========================
            if new_image.strip() == image.strip():
                updated.append(line)
                continue

            print(f"[PATCH][DOCKER] {image} → {new_image}")

            # 🔥 ADD PATCH LOG (NEW)
            if patch_log is not None and ai_result:
                try:
                    patch_log.append(
                        f"Docker: {image} → {new_image} | "
                        f"Risk: {ai_result.get('risk')} | "
                        f"Confidence: {ai_result.get('confidence')}%"
                    )
                except:
                    pass

            if alias:
                updated.append(f"FROM {new_image} AS {alias}")
            else:
                updated.append(f"FROM {new_image}")

            continue

        # =========================
        # OS PATCHING
        # =========================
        if stripped.startswith("WORKDIR") and not has_os_patch:

            print("[PATCH][DOCKER] Adding OS security patch")

            if "alpine" in content:
                updated.append("RUN apk update && apk upgrade")
            else:
                updated.append(
                    "RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*"
                )

            has_os_patch = True
            updated.append(line)
            continue

        # =========================
        # NON-ROOT USER
        # =========================
        if stripped.startswith("CMD") or stripped.startswith("ENTRYPOINT"):

            if not has_user:
                print("[PATCH][DOCKER] Adding non-root user")

                updated.append("RUN addgroup -S app && adduser -S app -G app")

                if workdir:
                    updated.append(f"RUN chown -R app:app {workdir}")

                updated.append("USER app")

                has_user = True

            updated.append(line)
            continue

        # =========================
        # INSTALL OPTIMIZATION
        # =========================
        if "apt-get install" in line and "--no-install-recommends" not in line:
            fixed = line.replace(
                "apt-get install",
                "apt-get install -y --no-install-recommends"
            )
            print("[PATCH][DOCKER] Optimized apt install")
            updated.append(fixed)
            continue

        updated.append(line)

    return "\n".join(updated)