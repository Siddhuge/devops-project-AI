def deduplicate(issues):
    seen = {}
    unique = []

    print(f"[DEDUP] Incoming issues: {len(issues)}")

    for issue in issues:

        # =========================
        # 🔥 NORMALIZE FIELDS
        # =========================
        cve = (issue.get("id") or issue.get("vulnerability_id") or "unknown").upper().strip()
        pkg = (issue.get("package") or "unknown").lower().strip()
        severity = (issue.get("severity") or "UNKNOWN").upper().strip()

        # 🔥 Version handling (important)
        installed = (
            issue.get("installed_version")
            or issue.get("version")
            or ""
        ).strip()

        # 🔥 Normalize fixed versions
        fixed_versions = issue.get("fixed_versions") or issue.get("fix") or []

        if isinstance(fixed_versions, str):
            fixed_versions = [v.strip() for v in fixed_versions.split(",") if v.strip()]

        fixed_versions = tuple(sorted(fixed_versions))

        # =========================
        # 🔥 IMPROVED UNIQUE KEY (LESS NOISE)
        # =========================
        key = (
            cve,
            pkg,
            installed
        )

        # =========================
        # 🔥 KEEP BEST ISSUE (SMART MERGE)
        # =========================
        if key in seen:
            existing = seen[key]

            severity_rank = {
                "CRITICAL": 4,
                "HIGH": 3,
                "MEDIUM": 2,
                "LOW": 1
            }

            existing_rank = severity_rank.get(existing.get("severity"), 0)
            current_rank = severity_rank.get(severity, 0)

            # Prefer higher severity
            if current_rank > existing_rank:
                seen[key] = issue

            # Prefer higher confidence
            elif issue.get("confidence", 0) > existing.get("confidence", 0):
                seen[key] = issue

            # Prefer more fix info (NEW IMPROVEMENT)
            elif len(fixed_versions) > len(existing.get("fixed_versions") or []):
                seen[key] = issue

            continue

        seen[key] = issue

    unique = list(seen.values())

    print(f"[DEDUP] After dedup: {len(unique)}")

    return unique