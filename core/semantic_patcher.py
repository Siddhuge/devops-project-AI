import re
import os
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
    # 🔥 FILTER ISSUES (STRONG)
    # =========================
    def filter_issues_for_image(all_issues, dockerfile_path):
        try:
            if not all_issues:
                return []

            filtered = []
            for i in all_issues:
                target = str(i.get("target", "")).lower()

                if dockerfile_path and dockerfile_path.lower() in target:
                    filtered.append(i)

            print(f"[DEBUG] Matched {len(filtered)} issues for {dockerfile_path}")
            return filtered

        except Exception as e:
            print("[FILTER ERROR]", e)
            return []

    # =========================
    # 🔥 STAGE DETECTION
    # =========================
    def get_stage_type(all_lines, current_index):
        from_indices = [i for i, l in enumerate(all_lines) if l.strip().upper().startswith("FROM")]
        return "runtime" if current_index == from_indices[-1] else "builder"

    # =========================
    # 🔥 SMART RELEVANCE FILTER
    # =========================
    def is_relevant_package(image, package):
        image = image.lower()
        package = package.lower()

        # Node
        if "node" in image:
            return any(x in package for x in ["node", "npm", "lodash", "express"])

        # Python
        if "python" in image:
            return any(x in package for x in ["python", "pip", "django", "flask"])

        # Java
        if any(x in image for x in ["openjdk", "temurin"]):
            return any(x in package for x in ["spring", "log4j", "jackson", "netty"])

        # Tomcat
        if "tomcat" in image:
            return any(x in package for x in ["tomcat", "servlet", "jsp"])

        # OS
        if any(x in image for x in ["ubuntu", "debian", "alpine"]):
            return any(x in package for x in ["glibc", "openssl", "bash", "apt"])

        return False

    # =========================
    # 🔥 CVE MATCHING (FINAL)
    # =========================
    def has_relevant_critical_cve(image_issues, image_name, all_issues=None):
        try:
            if not image_issues:
                print(f"[FALLBACK] No direct CVEs for {image_name}, checking global issues")
                image_issues = all_issues or []

            print(f"[DEBUG] Checking CVEs for {image_name}")

            for issue in image_issues:
                severity = issue.get("severity", "").upper()
                pkg = (issue.get("package") or "").lower()

                print(" →", severity, pkg)

                if severity != "CRITICAL":
                    continue

                if is_relevant_package(image_name, pkg):
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

    # =========================
    # 🔥 FILTER ISSUES
    # =========================
    image_issues = filter_issues_for_image(issues, dockerfile_path)

    stage_has_patch = False

    for idx, line in enumerate(lines):

        stripped = line.strip()

        # =========================
        # 🔥 HANDLE FROM
        # =========================
        if stripped.upper().startswith("FROM"):

            stage_has_patch = False

            stage = get_stage_type(lines, idx)

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

                                # 🔥 CRITICAL FIX: runtime only
                                if stage != "runtime":
                                    print(f"[AI BLOCKED] {image} is builder stage")
                                elif has_relevant_critical_cve(image_issues, name, issues):
                                    print(f"[AI OVERRIDE] Runtime critical CVE → allowing upgrade: {image} → {recommended}")
                                    new_image = recommended
                                    changed = True
                                else:
                                    print(f"[AI BLOCKED] Upgrade not safe for: {image}")

                            else:
                                new_image = recommended
                                changed = True

            except Exception as e:
                print("[AI ERROR]", e)

            # fallback slim
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

            # OS patch
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
        # 🔥 USER FIX
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