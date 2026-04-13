import json
import re
import xml.etree.ElementTree as ET


# =========================
# 🔥 BUILD FIX MAP (SMART + NORMALIZED)
# =========================
def build_fix_map(issues):

    fix_map = {}

    for i in issues:
        pkg = i.get("package")
        fix = i.get("fix")

        if not pkg or not fix:
            continue

        pkg = pkg.lower()

        # Store full package (e.g., org.springframework:spring-core)
        # Pick the safest (latest) version
        if "," in fix:
            versions = [v.strip() for v in fix.split(",")]
            fix = versions[0]   # 🔥 choose highest priority

        fix_map[pkg] = fix

        # Also store short name (artifactId / package name)
        if ":" in pkg:
            short = pkg.split(":")[-1]
            fix_map[short] = fix

    return fix_map


# =========================
# 🐍 PYTHON PATCHER (robust)
# =========================
def patch_requirements(content, fix_map):

    lines = content.split("\n")
    updated = []

    for line in lines:

        # Skip comments
        if line.strip().startswith("#") or not line.strip():
            updated.append(line)
            continue

        # Extract package name
        match = re.match(r"([a-zA-Z0-9_\-]+)", line)
        if not match:
            updated.append(line)
            continue

        pkg = match.group(1).lower()

        if pkg in fix_map:
            new_version = fix_map[pkg]

            # Skip if already fixed
            if new_version in line:
                updated.append(line)
                continue

            updated.append(f"{pkg}=={new_version}")
            print(f"[PATCH][PY] {pkg} → {new_version}")
        else:
            updated.append(line)

    return "\n".join(updated)


# =========================
# 🟢 NODE PATCHER (safe)
# =========================
def patch_package_json(content, fix_map):

    try:
        data = json.loads(content)
    except:
        return content

    updated_flag = False

    for section in ["dependencies", "devDependencies"]:

        if section not in data:
            continue

        for pkg in data[section]:

            key = pkg.lower()

            if key in fix_map:

                new_version = fix_map[key]

                # Skip if already fixed
                if new_version in data[section][pkg]:
                    continue

                print(f"[PATCH][NODE] {pkg} → {new_version}")

                data[section][pkg] = new_version
                updated_flag = True

    if not updated_flag:
        return content

    return json.dumps(data, indent=2)


# =========================
# ☕ MAVEN PATCHER (CORRECT FIX)
# =========================
def patch_pom_xml(content, fix_map):

    try:
        root = ET.fromstring(content)
    except:
        return content

    updated_flag = False

    for dep in root.findall(".//dependency"):

        group = dep.find("groupId")
        artifact = dep.find("artifactId")
        version = dep.find("version")

        if group is None or artifact is None or version is None:
            continue

        full_pkg = f"{group.text}:{artifact.text}".lower()
        short_pkg = artifact.text.lower()

        new_version = None

        if full_pkg in fix_map:
            new_version = fix_map[full_pkg]
        elif short_pkg in fix_map:
            new_version = fix_map[short_pkg]

        if not new_version:
            continue

        # Skip if already fixed
        if version.text == new_version:
            continue

        print(f"[PATCH][MAVEN] {full_pkg} {version.text} → {new_version}")

        version.text = new_version
        updated_flag = True

    if not updated_flag:
        return content

    return ET.tostring(root, encoding="unicode")


# =========================
# 🚀 MAIN ENTRY POINT
# =========================
def patch_dependency_file(file_path, issues):

    fix_map = build_fix_map(issues)

    with open(file_path, "r") as f:
        content = f.read()

    updated = content

    if file_path.endswith("requirements.txt"):
        updated = patch_requirements(content, fix_map)

    elif file_path.endswith("package.json"):
        updated = patch_package_json(content, fix_map)

    elif file_path.endswith("pom.xml"):
        updated = patch_pom_xml(content, fix_map)

    # =========================
    # 🛑 IDEMPOTENCY CHECK
    # =========================
    if updated.strip() == content.strip():
        return content

    return updated