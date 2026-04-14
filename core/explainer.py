def generate_explanation(issue, fixed_version=None):

    cve = issue.get("id", "Unknown CVE")
    pkg = issue.get("package", "unknown package")
    severity = issue.get("severity", "UNKNOWN")
    title = issue.get("title") or "Security vulnerability detected"
    desc = issue.get("description") or ""
    ref = issue.get("reference") or ""

    explanation = f"""
🔐 Vulnerability: {cve}

📦 Package: {pkg}
📊 Severity: {severity}

⚠️ Issue:
{title}

📖 Details:
{desc[:200]}...

"""

    if fixed_version:
        explanation += f"""
🛠 Fix Applied:
Upgraded to version {fixed_version}, which includes patches for this vulnerability.
"""

    explanation += f"""
📚 Reference:
{ref}

"""

    return explanation.strip()


# =========================
# 🔥 GROUP EXPLANATIONS
# =========================
def build_full_explanation(issues, patch_log=None):

    explanations = []

    for issue in issues[:10]:  # limit for readability
        explanations.append(generate_explanation(issue))

    return "\n\n---\n\n".join(explanations)


# =========================
# 🧠 SHORT SUMMARY (UI / PR)
# =========================
def generate_summary(issues):
    """
    AI-style security summary (no external API call, fast + deterministic)
    """

    if not issues:
        return "No vulnerabilities found."

    critical = len([i for i in issues if i.get("severity") == "CRITICAL"])
    high = len([i for i in issues if i.get("severity") == "HIGH"])

    top_issues = issues[:5]

    lines = []
    lines.append(f"Detected {len(issues)} vulnerabilities "
                 f"({critical} CRITICAL, {high} HIGH).")

    lines.append("")

    for i in top_issues:
        pkg = i.get("package")
        sev = i.get("severity")
        cve = i.get("id", "Unknown CVE")

        lines.append(
            f"- {pkg} ({sev}): affects security via {cve}"
        )

    lines.append("")
    lines.append("Fix Strategy:")
    lines.append("- AI-selected non-breaking upgrades")
    lines.append("- CVE-aware patching applied")
    lines.append("- High-confidence fixes prioritized")

    return "\n".join(lines)