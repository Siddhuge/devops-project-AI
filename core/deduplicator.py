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
        # 🔥 NORMALIZATION (CRITICAL)
        # =========================
        cve = (issue.get("id") or issue.get("vulnerability_id") or "unknown").upper().strip()

        raw_pkg = (issue.get("package") or "unknown").lower().strip()
        pkg = raw_pkg.split(":")[-1]          # remove groupId
        pkg = pkg.split("/")[-1]              # remove path noise

        source_raw = issue.get("source", "")
        source = source_raw.split(":")[0]     # normalize source (fs / image)

        severity = (issue.get("severity") or "UNKNOWN").upper().strip()
        stage = issue.get("stage", "builder")
        priority = issue.get("priority", 0)
        confidence = issue.get("confidence", 0)

        # Normalize fix versions
        fixed_versions = issue.get("fixed_versions") or issue.get("fix") or []
        if isinstance(fixed_versions, str):
            fixed_versions = [v.strip() for v in fixed_versions.split(",") if v.strip()]
        fixed_versions = set(fixed_versions)

        # 🔥 FORCE normalized values back
        issue["package"] = pkg
        issue["source"] = source
        issue["fixed_versions"] = list(fixed_versions)

        # =========================
        # 🔥 FINAL KEY
        # =========================
        key = (cve, pkg)

        # =========================
        # 🔥 MERGE LOGIC (ENTERPRISE)
        # =========================
        if key in seen:
            existing = seen[key]

            existing_versions = set(existing.get("fixed_versions") or [])
            merged_versions = existing_versions.union(fixed_versions)

            # 1️⃣ Prefer runtime
            if stage == "runtime" and existing.get("stage") != "runtime":
                issue["fixed_versions"] = sorted(merged_versions)
                seen[key] = issue
                continue

            # 2️⃣ Prefer higher priority
            if priority > existing.get("priority", 0):
                issue["fixed_versions"] = sorted(merged_versions)
                seen[key] = issue
                continue

            # 3️⃣ Prefer higher severity
            existing_rank = severity_rank.get(existing.get("severity"), 0)
            current_rank = severity_rank.get(severity, 0)

            if current_rank > existing_rank:
                existing["severity"] = severity

            # 4️⃣ Prefer better confidence
            if confidence > existing.get("confidence", 0):
                existing["confidence"] = confidence

            # 5️⃣ Merge fix versions
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