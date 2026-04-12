import asyncio

async def execute_plugins(plugins, repo_path):

    tasks = [plugin.run(repo_path) for plugin in plugins]

    results = await asyncio.gather(*tasks)

    combined = []
    for r in results:
        combined.extend(r)

    return combined