def deduplicate(issues):
    seen = {}

    print(f"[DEDUP] Incoming issues: {len(issues)}")

    severity_rank = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    for issue in issues:

        # =========================
        # 🔥 NORMALIZE FIELDS
        # =========================
        cve = (issue.get("id") or issue.get("vulnerability_id") or "unknown").upper().strip()
        pkg = (issue.get("package") or "unknown").lower().strip()
        severity = (issue.get("severity") or "UNKNOWN").upper().strip()

        target = (issue.get("target") or "unknown").lower().strip()

        installed = (
            issue.get("installed_version")
            or issue.get("version")
            or ""
        ).strip()

        stage = issue.get("stage", "builder")
        priority = issue.get("priority", 0)
        confidence = issue.get("confidence", 0)

        fixed_versions = issue.get("fixed_versions") or issue.get("fix") or []

        if isinstance(fixed_versions, str):
            fixed_versions = [v.strip() for v in fixed_versions.split(",") if v.strip()]

        fixed_versions = set(fixed_versions)

        # =========================
        # 🔥 IMPROVED KEY (LESS NOISE)
        # =========================
        key = (cve, pkg)

        # =========================
        # 🔥 MERGE LOGIC (ENTERPRISE)
        # =========================
        if key in seen:
            existing = seen[key]

            # 🔥 Merge fix versions
            existing_versions = set(existing.get("fixed_versions") or [])
            merged_versions = existing_versions.union(fixed_versions)

            # 🔥 Prefer runtime issues
            if stage == "runtime" and existing.get("stage") != "runtime":
                seen[key] = issue
                issue["fixed_versions"] = sorted(merged_versions)
                continue

            # 🔥 Prefer higher priority
            if priority > existing.get("priority", 0):
                seen[key] = issue
                issue["fixed_versions"] = sorted(merged_versions)
                continue

            # 🔥 Prefer higher severity (fallback)
            existing_rank = severity_rank.get(existing.get("severity"), 0)
            current_rank = severity_rank.get(severity, 0)

            if current_rank > existing_rank:
                existing["severity"] = severity

            # 🔥 Prefer better confidence
            if confidence > existing.get("confidence", 0):
                existing["confidence"] = confidence

            # 🔥 Merge fix versions
            existing["fixed_versions"] = sorted(merged_versions)

            continue

        # =========================
        # 🔥 FIRST ENTRY
        # =========================
        issue["fixed_versions"] = sorted(fixed_versions)
        seen[key] = issue

    deduped = list(seen.values())

    print(f"[DEDUP] After dedup: {len(deduped)}")

    return deduped