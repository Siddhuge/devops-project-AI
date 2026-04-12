import json
import xml.etree.ElementTree as ET


def build_fix_map(issues):
    fix_map = {}
    for i in issues:
        pkg = i.get("package")
        fix = i.get("fix")
        if pkg and fix:
            fix_map[pkg.lower()] = fix
    return fix_map


def patch_requirements(content, fix_map):
    lines = content.split("\n")
    updated = []

    for line in lines:
        pkg = line.split("==")[0].strip().lower()

        if pkg in fix_map:
            updated.append(f"{pkg}=={fix_map[pkg]}")
        else:
            updated.append(line)

    return "\n".join(updated)


def patch_package_json(content, fix_map):
    try:
        data = json.loads(content)
    except:
        return content

    for sec in ["dependencies", "devDependencies"]:
        if sec in data:
            for pkg in data[sec]:
                if pkg.lower() in fix_map:
                    data[sec][pkg] = fix_map[pkg.lower()]

    return json.dumps(data, indent=2)


def patch_pom_xml(content, fix_map):
    try:
        root = ET.fromstring(content)
    except:
        return content

    for dep in root.findall(".//dependency"):
        artifact = dep.find("artifactId")
        version = dep.find("version")

        if artifact is not None and version is not None:
            pkg = artifact.text.lower()
            if pkg in fix_map:
                version.text = fix_map[pkg]

    return ET.tostring(root, encoding="unicode")


def patch_dependency_file(file_path, issues):
    fix_map = build_fix_map(issues)

    with open(file_path) as f:
        content = f.read()

    if file_path.endswith("requirements.txt"):
        return patch_requirements(content, fix_map)

    elif file_path.endswith("package.json"):
        return patch_package_json(content, fix_map)

    elif file_path.endswith("pom.xml"):
        return patch_pom_xml(content, fix_map)

    return content