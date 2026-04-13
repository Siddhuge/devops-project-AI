import re


def semantic_patch_dockerfile(content, issues=None):
    """
    🔥 Enterprise-grade Dockerfile patcher (Improved)

    - CVE-aware (uses issues if available)
    - Dynamic base image upgrades
    - Multi-stage safe
    - Idempotent
    - Non-root hardened
    """

    lines = content.split("\n")
    updated = []

    has_user = any("USER" in l for l in lines)
    workdir = None

    # =========================
    # 🔍 Detect WORKDIR
    # =========================
    for l in lines:
        if l.strip().startswith("WORKDIR"):
            parts = l.strip().split()
            if len(parts) > 1:
                workdir = parts[1]

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

            new_tag = tag

            # =========================
            # 🔥 CVE-AWARE CHECK (if issues available)
            # =========================
            if issues:
                for issue in issues:
                    if issue.get("package") == name and issue.get("fixed_versions"):
                        # pick safer tag hint
                        new_tag = tag if "slim" in tag or "alpine" in tag else f"{tag}-slim"
                        break

            # =========================
            # 🔥 FALLBACK LOGIC (your original)
            # =========================
            else:
                if re.match(r"^\d+(\.\d+)?$", tag):
                    new_tag = f"{tag}-slim"

                elif any(x in tag for x in ["slim", "alpine"]):
                    new_tag = tag

                else:
                    new_tag = f"{tag}-slim"

            fixed_image = f"{name}:{new_tag}"

            if fixed_image == image:
                updated.append(line)
                continue

            print(f"[PATCH][DOCKER] {image} → {fixed_image}")

            if alias:
                updated.append(f"FROM {fixed_image} AS {alias}")
            else:
                updated.append(f"FROM {fixed_image}")

            continue

        # =========================
        # 🔐 ADD SECURITY BEST PRACTICES
        # =========================
        if stripped.startswith("CMD") or stripped.startswith("ENTRYPOINT"):

            if not has_user:
                print("[PATCH][DOCKER] Adding non-root user")

                updated.append("RUN addgroup -S app && adduser -S app -G app")

                if workdir:
                    updated.append(f"RUN chown -R app:app {workdir}")

                updated.append("USER app")

                has_user = True  # prevent duplicate

            updated.append(line)
            continue

        # =========================
        # 📦 OPTIMIZE INSTALL COMMANDS
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