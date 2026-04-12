def semantic_patch_dockerfile(content, issues):

    # Only apply if OS-level issues exist
    has_os_vuln = any(i["source"].startswith("image") for i in issues)

    if not has_os_vuln:
        return content

    lines = content.split("\n")
    updated = []

    for line in lines:

        if line.strip().startswith("FROM"):

            image = line.split()[1]

            # Skip already optimized
            if any(x in image for x in ["slim", "alpine"]):
                updated.append(line)
                continue

            # Safe improvement
            updated.append(f"FROM {image}-slim")
            continue

        updated.append(line)

    return "\n".join(updated)