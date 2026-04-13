import re


# =========================
# 🔧 VERSION PARSER
# =========================
def parse_version(v):
    try:
        return [int(x) for x in re.findall(r"\d+", v)]
    except:
        return [0]


def get_major(v):
    parts = parse_version(v)
    return parts[0] if parts else 0


def get_minor(v):
    parts = parse_version(v)
    return parts[1] if len(parts) > 1 else 0


# =========================
# 🚦 RISK CALCULATOR
# =========================
def calculate_risk(installed, fixed):

    if not installed or not fixed:
        return "UNKNOWN"

    try:
        old_major = get_major(installed)
        new_major = get_major(fixed)

        old_minor = get_minor(installed)
        new_minor = get_minor(fixed)

        # =========================
        # 🔥 HIGH RISK
        # =========================
        if new_major > old_major:
            return "HIGH"

        # =========================
        # ⚠️ MEDIUM RISK
        # =========================
        if new_minor > old_minor:
            return "MEDIUM"

        # =========================
        # ✅ LOW RISK
        # =========================
        return "LOW"

    except:
        return "UNKNOWN"


# =========================
# 📊 CONFIDENCE BOOSTER
# =========================
def calculate_confidence(issue):

    base = issue.get("confidence", 50)

    if issue.get("fixed_versions"):
        base += 20

    if issue.get("severity") in ["HIGH", "CRITICAL"]:
        base += 10

    return min(base, 100)


# =========================
# 📦 PACKAGE RISK SUMMARY
# =========================
def summarize_risk(patch_log):

    high = 0
    medium = 0
    low = 0

    for p in patch_log:
        if "HIGH" in p:
            high += 1
        elif "MEDIUM" in p:
            medium += 1
        elif "LOW" in p:
            low += 1

    if high > 0:
        return "HIGH"
    if medium > 0:
        return "MEDIUM"

    return "LOW"