import os, json
from core.plugin_base import BasePlugin

class ZapPlugin(BasePlugin):

    def name(self): return "zap"

    def run(self):
        os.system("zap-baseline.py -t https://example.com -J reports/zap.json")

    def parse(self):
        data = json.load(open("reports/zap.json"))

        vulns = []
        for a in data.get("site", [{}])[0].get("alerts", []):
            vulns.append({
                "id": a["alert"],
                "severity": a["riskdesc"],
                "component": a["url"],
                "fix": a["solution"],
                "source": "zap"
            })
        return vulns