import asyncio
from core.plugin_loader import load_plugins
from core.executor import execute_plugins
from core.deduplicator import deduplicate
from core.prioritizer import prioritize
from core.fixer import generate_fix

async def main():
    plugins = load_plugins()
    results = await execute_plugins(plugins)

    dedup = deduplicate(results)
    prioritized = prioritize(dedup)

    for v in prioritized[:5]:
        print(v["id"], v["severity"])
        print(generate_fix(v))

if __name__ == "__main__":
    asyncio.run(main())