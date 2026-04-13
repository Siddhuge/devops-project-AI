import json
import re
import xml.etree.ElementTree as ET

# 🔥 NEW IMPORTS (INTEGRATION)
from core.risk_engine import calculate_risk, calculate_confidence


# =========================
# 🔥 VERSION PARSER (SAFE)
# =========================
def normalize_version(v):
    return re.sub(r"[^\d\.]", "", v or "")


def version_tuple(v):
    try:
        return tuple(int(x) for x in normalize_version(v).split(".") if x)
    except:
        return (0,)


def get_major(v):
    try:
        return version_tuple(v)[0]
    except:
        return None


# =========================
# 🔥 SMART VERSION PICKER (CVE-AWARE)
# =========================
def pick_safe_version(current, fixes):

    if not fixes:
        return None

    if isinstance(fixes, str):
        fixes = [f.strip() for f in fixes.split(",")]

    fixes = [f for f in fixes if f]

    if not fixes:
        return None

    current_major = get_major(current)

    safe_versions = []
    risky_versions = []

    for f in fixes:
        f_major = get_major(f)

        if current_major is not None and f_major == current_major:
            safe_versions.append(f)
        else:
            risky_versions.append(f)

    if safe_versions:
        return sorted(safe_versions, key=version_tuple)[-1]

    if risky_versions:
        return sorted(risky_versions, key=version_tuple)[-1]

    return None


# =========================
# 🔥 BUILD FIX MAP (IMPROVED)
# =========================
def build_fix_map(issues):

    fix_map = {}

    for i in issues:
        pkg = i.get("package")
        fixes = i.get("fixed_versions") or i.get("fix")

        if not pkg or not fixes:
            continue

        pkg = pkg.lower()

        if isinstance(fixes, str):
            fixes = [f.strip() for f in fixes.split(",")]

        if pkg not in fix_map:
            fix_map[pkg] = []

        fix_map[pkg].extend(fixes)

        if ":" in pkg:
            short = pkg.split(":")[-1]
            fix_map.setdefault(short, []).extend(fixes)

    return fix_map


# =========================
# 🔥 AI REASONING (UPDATED WITH RISK ENGINE)
# =========================
def generate_reason(pkg, old, new, issue=None):

    if not old or not new:
        return ""

    risk = calculate_risk(old, new)

    confidence = 0
    if issue:
        confidence = calculate_confidence(issue)

    return f"{pkg}: {old} → {new} | Risk: {risk} | Confidence: {confidence} | CVE Fix Applied"


# =========================
# 🐍 PYTHON PATCHER
# =========================
def patch_requirements(content, fix_map, issues, patch_log):

    lines = content.split("\n")
    updated = []

    for line in lines:

        if line.strip().startswith("#") or not line.strip():
            updated.append(line)
            continue

        match = re.match(r"([a-zA-Z0-9_\-]+)(==([\w\.\-]+))?", line)
        if not match:
            updated.append(line)
            continue

        pkg = match.group(1).lower()
        current_version = match.group(3)

        if pkg in fix_map:
            new_version = pick_safe_version(current_version, fix_map[pkg])

            if not new_version or new_version == current_version:
                updated.append(line)
                continue

            print(f"[PATCH][PY] {pkg} {current_version} → {new_version}")

            issue = next((i for i in issues if i.get("package", "").lower() == pkg), None)

            patch_log.append(generate_reason(pkg, current_version, new_version, issue))

            updated.append(f"{pkg}=={new_version}")
        else:
            updated.append(line)

    return "\n".join(updated)


# =========================
# 🟢 NODE PATCHER
# =========================
def patch_package_json(content, fix_map, issues, patch_log):

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
            current_version = data[section][pkg]

            if key in fix_map:

                new_version = pick_safe_version(current_version, fix_map[key])

                if not new_version or new_version in current_version:
                    continue

                print(f"[PATCH][NODE] {pkg} → {new_version}")

                issue = next((i for i in issues if i.get("package", "").lower() == key), None)

                patch_log.append(generate_reason(pkg, current_version, new_version, issue))

                data[section][pkg] = new_version
                updated_flag = True

    if not updated_flag:
        return content

    return json.dumps(data, indent=2)


# =========================
# ☕ MAVEN PATCHER
# =========================
def patch_pom_xml(content, fix_map, issues, patch_log):

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
        current_version = version.text

        fixes = fix_map.get(full_pkg) or fix_map.get(short_pkg)

        if not fixes:
            continue

        new_version = pick_safe_version(current_version, fixes)

        if not new_version or new_version == current_version:
            continue

        print(f"[PATCH][MAVEN] {full_pkg} {current_version} → {new_version}")

        issue = next((i for i in issues if i.get("package", "").lower() in [full_pkg, short_pkg]), None)

        patch_log.append(generate_reason(full_pkg, current_version, new_version, issue))

        version.text = new_version
        updated_flag = True

    if not updated_flag:
        return content

    return ET.tostring(root, encoding="unicode")


# =========================
# 🚀 MAIN ENTRY (UPDATED)
# =========================
def patch_dependency_file(file_path, issues):

    fix_map = build_fix_map(issues)

    with open(file_path, "r") as f:
        content = f.read()

    updated = content
    patch_log = []

    if file_path.endswith("requirements.txt"):
        updated = patch_requirements(content, fix_map, issues, patch_log)

    elif file_path.endswith("package.json"):
        updated = patch_package_json(content, fix_map, issues, patch_log)

    elif file_path.endswith("pom.xml"):
        updated = patch_pom_xml(content, fix_map, issues, patch_log)

    # =========================
    # 🛑 IDEMPOTENCY CHECK
    # =========================
    if updated.strip() == content.strip():
        return content

    return updated