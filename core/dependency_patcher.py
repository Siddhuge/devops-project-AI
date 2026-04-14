import json
import re
import xml.etree.ElementTree as ET

from core.risk_engine import calculate_risk, calculate_confidence
from core.ai_fix_engine import suggest_fix  # 🔥 NEW


# =========================
# VERSION HELPERS
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


def is_already_fixed(current, new):
    try:
        return version_tuple(current) >= version_tuple(new)
    except:
        return False


# =========================
# SAFE FALLBACK LOGIC (UNCHANGED)
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
# BUILD FIX MAP
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

        fix_map.setdefault(pkg, []).extend(fixes)

        if ":" in pkg:
            short = pkg.split(":")[-1]
            fix_map.setdefault(short, []).extend(fixes)

    return fix_map


# =========================
# 🔥 AI + FALLBACK VERSION PICKER
# =========================
def get_ai_version(pkg, current, fixes, issue):

    try:
        ai_result = suggest_fix(issue)

        if not ai_result:
            return None, None

        new_version = ai_result.get("recommended_version")

        # 🔥 SAFETY CHECK
        if not new_version:
            return None, None

        if is_already_fixed(current, new_version):
            return None, None

        return new_version, ai_result

    except Exception as e:
        print("[AI ERROR]", e)
        return None, None


# =========================
# REASON GENERATOR
# =========================
def generate_reason(pkg, old, new, issue=None, ai_result=None):

    if ai_result:
        return (
            f"{pkg}: {old} → {new} | "
            f"Risk: {ai_result.get('risk')} | "
            f"Confidence: {ai_result.get('confidence')} | "
            f"{ai_result.get('reason')}"
        )

    risk = calculate_risk(old, new)
    confidence = calculate_confidence(issue) if issue else 0

    return f"{pkg}: {old} → {new} | Risk: {risk} | Confidence: {confidence} | CVE Fix Applied"


# =========================
# PYTHON PATCHER
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

            issue = next((i for i in issues if i.get("package", "").lower() == pkg), None)

            # 🔥 TRY AI FIRST
            new_version, ai_result = get_ai_version(pkg, current_version, fix_map[pkg], issue)

            # 🔥 FALLBACK
            if not new_version:
                new_version = pick_safe_version(current_version, fix_map[pkg])
                ai_result = None

            if not new_version or is_already_fixed(current_version, new_version):
                updated.append(line)
                continue

            print(f"[PATCH][PY] {pkg} {current_version} → {new_version}")

            patch_log.append(generate_reason(pkg, current_version, new_version, issue, ai_result))

            updated.append(f"{pkg}=={new_version}")
        else:
            updated.append(line)

    return "\n".join(updated)


# =========================
# NODE PATCHER
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

                issue = next((i for i in issues if i.get("package", "").lower() == key), None)

                new_version, ai_result = get_ai_version(key, current_version, fix_map[key], issue)

                if not new_version:
                    new_version = pick_safe_version(current_version, fix_map[key])
                    ai_result = None

                if not new_version or is_already_fixed(current_version, new_version):
                    continue

                print(f"[PATCH][NODE] {pkg} → {new_version}")

                patch_log.append(generate_reason(pkg, current_version, new_version, issue, ai_result))

                data[section][pkg] = new_version
                updated_flag = True

    if not updated_flag:
        return content

    return json.dumps(data, indent=2)


# =========================
# MAVEN PATCHER
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

        issue = next((i for i in issues if i.get("package", "").lower() in [full_pkg, short_pkg]), None)

        new_version, ai_result = get_ai_version(full_pkg, current_version, fixes, issue)

        if not new_version:
            new_version = pick_safe_version(current_version, fixes)
            ai_result = None

        if not new_version or is_already_fixed(current_version, new_version):
            continue

        print(f"[PATCH][MAVEN] {full_pkg} {current_version} → {new_version}")

        patch_log.append(generate_reason(full_pkg, current_version, new_version, issue, ai_result))

        version.text = new_version
        updated_flag = True

    if not updated_flag:
        return content

    return ET.tostring(root, encoding="unicode")


# =========================
# MAIN ENTRY
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

    if updated.strip() == content.strip():
        return content

    return updated