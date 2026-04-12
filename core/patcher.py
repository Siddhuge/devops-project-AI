import re


# =========================
# 🔍 Safe package update (APT)
# =========================
def update_apt_packages(line, issues):
    if "apt-get install" not in line:
        return line

    for issue in issues:
        pkg = issue.get("package")
        fix = issue.get("fix")

        if not pkg or not fix:
            continue

        if pkg in line:

            # Already fixed
            if f"{pkg}={fix}" in line:
                continue

            # Replace pkg version safely
            pattern = rf"{pkg}(=\S+)?"
            line = re.sub(pattern, f"{pkg}={fix}", line)

    return line


# =========================
# 🔍 Safe base image upgrade
# =========================
def update_base_image(line):
    if not line.strip().startswith("FROM"):
        return line

    image = line.split()[1]

    # DO NOT blindly modify
    if any(x in image for x in ["slim", "alpine", "bookworm", "buster"]):
        return line

    # Only upgrade very old images
    if any(x in image for x in ["node:10", "node:12", "python:3.6", "openjdk:8"]):
        return line.replace(image, image + "-slim")

    return line


# =========================
# 🚀 MAIN PATCHER
# =========================
def apply_fixes(file_path, issues):

    # Filter usable fixes
    issues = [
        i for i in issues
        if i.get("fix") and i.get("package")
    ]

    with open(file_path, "r") as f:
        lines = f.readlines()

    updated_lines = []

    for line in lines:

        original = line

        # Base image fix
        line = update_base_image(line)

        # Package fix (APT only)
        line = update_apt_packages(line, issues)

        updated_lines.append(line)

    updated_content = "".join(updated_lines)

    # Idempotency check
    if updated_content.strip() == "".join(lines).strip():
        return "".join(lines)

    return updated_content