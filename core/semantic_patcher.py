import re
from core.ai_fix_engine import suggest_docker_fix


def semantic_patch_dockerfile(content, issues=None, patch_log=None, dockerfile_path=None):

    lines = content.split("\n")
    updated = []

    has_user = any("USER" in l for l in lines)
    workdir = None

    for l in lines:
        if l.strip().startswith("WORKDIR"):
            parts = l.strip().split()
            if len(parts) > 1:
                workdir = parts[1]

    # =========================
    # 🔥 FILTER ISSUES PER DOCKERFILE (CRITICAL FIX)
    # =========================
    def filter_issues_for_image(all_issues, dockerfile_path):
        try:
            return [
                i for i in all_issues or []
                if dockerfile_path and dockerfile_path in str(i.get("target", ""))
            ]
        except:
            return []

    # =========================
    # 🔥 ENTERPRISE CVE MATCHING
    # =========================
    def has_relevant_critical_cve(image_issues, image_name):
        try:
            if not image_issues:
                return False

            image_name = image_name.lower()

            # 🔥 OS-level packages
            os_packages = [
                "openssl", "glibc", "musl", "libssl", "busybox",
                "bash", "zlib", "curl", "wget", "tar"
            ]

            # 🔥 Language ecosystems
            ecosystem_map = {
                "node": ["node", "npm", "lodash", "express"],
                "python": ["python", "pip", "django", "flask"],
                "openjdk": ["java", "jdk", "log4j"],
                "ubuntu": os_packages,
                "debian": os_packages,
                "alpine": ["musl", "busybox"] + os_packages
            }

            relevant_keywords = []

            for key, values in ecosystem_map.items():
                if key in image_name:
                    relevant_keywords.extend(values)

            for issue in image_issues:
                severity = issue.get("severity", "").upper()
                pkg = (issue.get("package") or "").lower()

                if severity != "CRITICAL":
                    continue

                # 🔥 Strong match
                if any(k in pkg for k in relevant_keywords):
                    print(f"[CVE MATCH] {pkg} is relevant to {image_name}")
                    return True

            return False

        except Exception as e:
            print("[CVE MATCH ERROR]", e)
            return False

    # =========================
    # VERSION HELPERS
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

    stage_has_patch = False

    # 🔥 FILTERED ISSUES (IMPORTANT)
    image_issues = filter_issues_for_image(issues, dockerfile_path)

    for line in lines:

        stripped = line.strip()

        if stripped.upper().startswith("FROM"):

            stage_has_patch = False

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
            # AI LOGIC
            # =========================
            try:
                ai_result = suggest_docker_fix(image, image_issues)

                if ai_result:
                    confidence = ai_result.get("confidence", 0)

                    if confidence < 70:
                        print(f"[AI SKIPPED] Low confidence ({confidence}%) for {image}")
                    else:
                        recommended = ai_result.get("recommended_image")

                        if recommended and ":" in recommended and recommended != image:

                            _, new_tag = recommended.split(":", 1)

                            if is_major_upgrade(tag, new_tag):

                                # 🔥 FIXED LOGIC
                                if has_relevant_critical_cve(image_issues, name):
                                    print(f"[AI OVERRIDE] Critical CVE matched → allowing upgrade: {image} → {recommended}")
                                    new_image = recommended
                                    changed = True
                                else:
                                    print(f"[AI BLOCKED] Major upgrade skipped: {image} → {recommended}")

                            else:
                                new_image = recommended
                                changed = True

            except Exception as e:
                print("[AI ERROR]", e)

            # =========================
            # FALLBACK
            # =========================
            if not changed:
                if "slim" not in tag and "alpine" not in tag:
                    new_image = f"{name}:{tag}-slim"

            if new_image.strip() != image.strip():
                print(f"[PATCH][DOCKER] {image} → {new_image}")

                if patch_log is not None and ai_result:
                    patch_log.append(
                        f"Docker: {image} → {new_image} | "
                        f"Risk: {ai_result.get('risk')} | "
                        f"Confidence: {ai_result.get('confidence')}%"
                    )

            if alias:
                updated.append(f"FROM {new_image} AS {alias}")
            else:
                updated.append(f"FROM {new_image}")

            # =========================
            # OS PATCH
            # =========================
            if not stage_has_patch:
                print("[PATCH][DOCKER] Adding OS security patch (per stage)")

                if "alpine" in new_image:
                    updated.append("RUN apk update && apk upgrade")
                else:
                    updated.append(
                        "RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*"
                    )

                stage_has_patch = True

            continue

        # =========================
        # NON ROOT
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

        updated.append(line)

    return "\n".join(updated)