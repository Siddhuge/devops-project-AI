def calculate_confidence(issue, language):

    score = 50

    if issue.get("severity") == "CRITICAL":
        score += 20

    if language in ["node", "python", "java"]:
        score += 15

    if issue.get("fix"):
        score += 15

    return min(score, 100)