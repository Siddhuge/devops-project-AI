import re


def semantic_patch_dockerfile(content, issues=None):
    """
    🔥 Enterprise-grade Dockerfile patcher

    - Works without CVEs
    - Dynamic base image upgrades
    - Multi-stage safe
    - Idempotent
    """

    lines = content.split("\n")
    updated = []

    for line in lines:

        stripped = line.strip()

        # =========================
        # 🐳 HANDLE FROM LINE
        # =========================
        if stripped.startswith("FROM"):

            parts = stripped.split()

            # Handle multi-stage: FROM image AS builder
            image = parts[1]
            alias = parts[3] if len(parts) > 3 and parts[2].upper() == "AS" else None

            # -------------------------
            # Normalize image
            # -------------------------
            name = image
            tag = "latest"

            if ":" in image:
                name, tag = image.split(":", 1)

            new_tag = tag

            # =========================
            # 🔥 DYNAMIC UPGRADE STRATEGY
            # =========================

            # Case 1: numeric tag (node:14, python:3.9, openjdk:8)
            if re.match(r"^\d+(\.\d+)?$", tag):
                new_tag = f"{tag}-slim"

            # Case 2: already slim/alpine → keep
            elif any(x in tag for x in ["slim", "alpine"]):
                new_tag = tag

            # Case 3: generic tag → harden
            else:
                new_tag = f"{tag}-slim"

            fixed_image = f"{name}:{new_tag}"

            # =========================
            # 🛑 IDEMPOTENT CHECK
            # =========================
            if fixed_image == image:
                updated.append(line)
                continue

            print(f"[PATCH][DOCKER] {image} → {fixed_image}")

            # Rebuild line
            if alias:
                updated.append(f"FROM {fixed_image} AS {alias}")
            else:
                updated.append(f"FROM {fixed_image}")

            continue

        # =========================
        # 🔐 ADD SECURITY BEST PRACTICES
        # =========================

        # Add non-root user if not present
        if stripped.startswith("CMD") or stripped.startswith("ENTRYPOINT"):

            # Ensure USER is added before CMD
            if not any("USER" in l for l in updated):
                print("[PATCH][DOCKER] Adding non-root user")
                updated.append("RUN addgroup -S app && adduser -S app -G app")
                updated.append("USER app")

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