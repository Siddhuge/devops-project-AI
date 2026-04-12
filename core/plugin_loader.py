import os
import importlib


def load_plugins():
    plugins = []

    plugin_dir = "plugins"

    print(f"[PLUGIN LOADER] Scanning folder: {plugin_dir}")

    for file in os.listdir(plugin_dir):

        # Only load python files
        if file.endswith(".py") and not file.startswith("__"):

            module_name = file[:-3]

            try:
                module = importlib.import_module(f"{plugin_dir}.{module_name}")

                if hasattr(module, "run"):
                    plugins.append(module)
                    print(f"[PLUGIN LOADED] {module_name}")

                else:
                    print(f"[SKIPPED] {module_name} has no run()")

            except Exception as e:
                print(f"[ERROR] Failed to load {module_name}: {e}")

    print(f"[PLUGIN LOADER] Total plugins: {len(plugins)}")

    return plugins