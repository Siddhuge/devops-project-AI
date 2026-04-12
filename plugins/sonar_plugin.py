import requests
from core.plugin_base import BasePlugin

class SonarPlugin(BasePlugin):

    def name(self): return "sonar"

    def run(self): pass

    def parse(self):
        res = requests.get("http://localhost:9000/api/issues/search", auth=("admin","admin"))
        data = res.json()

        return [{
            "id": i["key"],
            "severity": i["severity"],
            "component": i["component"],
            "fix": i["message"],
            "source": "sonar"
        } for i in data.get("issues", [])]