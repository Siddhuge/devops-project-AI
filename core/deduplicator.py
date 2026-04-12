def deduplicate(issues):
    seen = set()
    unique = []

    print(f"[DEDUP] Incoming issues: {len(issues)}")

    for issue in issues:
        cve = issue.get("id", "unknown")
        pkg = issue.get("package", "unknown")
        severity = issue.get("severity", "UNKNOWN")
        target = issue.get("target", "global")
        source = issue.get("source", "unknown")

        # =========================
        # 🔥 STRONG UNIQUE KEY
        # =========================
        key = f"{cve}:{pkg}:{severity}:{target}:{source}"

        if key not in seen:
            seen.add(key)
            unique.append(issue)

    print(f"[DEDUP] After dedup: {len(unique)}")

    return unique