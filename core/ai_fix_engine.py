import os
import json
from openai import AzureOpenAI


client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)


def suggest_fix(issue, context=None):
    """
    AI decides best dependency fix version with reasoning
    """

    try:
        package = issue.get("package")
        current = issue.get("version")
        fixes = issue.get("fixed_versions", [])
        severity = issue.get("severity")

        prompt = f"""
You are a senior DevSecOps engineer.

Vulnerability:
- Package: {package}
- Current Version: {current}
- Available Fix Versions: {fixes}
- Severity: {severity}

Rules:
- Prefer non-breaking upgrades
- Stay within same major version if possible
- Avoid risky upgrades unless severity is CRITICAL
- Ensure compatibility with existing systems

Return STRICT JSON ONLY:
{{
  "recommended_version": "...",
  "reason": "...",
  "risk": "LOW|MEDIUM|HIGH",
  "confidence": 0-100
}}
"""

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        return json.loads(content)

    except Exception as e:
        print("[AI DEP ERROR]", e)
        return None



def suggest_docker_fix(base_image, issues=None):
    """
    AI suggests secure Docker base image upgrade
    """

    try:
        prompt = f"""
You are a senior DevSecOps engineer specializing in container security.

Docker Base Image:
{base_image}

Context:
- The image may be outdated or vulnerable
- Suggest a secure, modern, production-ready replacement
- Prefer LTS versions
- Prefer slim/alpine variants when safe
- Avoid breaking runtime compatibility

Rules:
- Do NOT drastically change runtime (e.g., python → node)
- Keep same ecosystem (python, node, java, etc.)
- Upgrade to supported versions only

Return STRICT JSON ONLY:
{{
  "recommended_image": "...",
  "reason": "...",
  "risk": "LOW|MEDIUM|HIGH",
  "confidence": 0-100
}}
"""

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        result = json.loads(content)

        # 🔥 SAFETY CHECK
        recommended = result.get("recommended_image")

        if not recommended or ":" not in recommended:
            return None

        return result

    except Exception as e:
        print("[AI DOCKER ERROR]", e)
        return None