SCORES = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

def prioritize(vulns):
    return sorted(vulns, key=lambda x: SCORES.get(x["severity"], 0), reverse=True)