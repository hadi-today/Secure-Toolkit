import json
import os
import subprocess
import sys
import importlib


def discover_manifests(plugins_dir):
    if not os.path.isdir(plugins_dir):
        return
    for plugin_folder_name in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, plugin_folder_name)
        manifest_path = os.path.join(plugin_path, 'manifest.json')
        if not (os.path.isdir(plugin_path) and os.path.exists(manifest_path)):
            continue
        requirements_path = os.path.join(plugin_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            print(f"Found requirements for plugin '{plugin_folder_name}'. Installing...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
                print(f"Successfully installed dependencies for '{plugin_folder_name}'.")
            except subprocess.CalledProcessError as error:
                print(f"ERROR: Failed to install dependencies for '{plugin_folder_name}'.")
                print(f"The plugin will be skipped. Error: {error}")
                continue
        try:
            with open(manifest_path, 'r') as file:
                manifest = json.load(file)
            yield plugin_folder_name, manifest
        except Exception as error:
            print(f"Could not load plugin '{plugin_folder_name}': {error}")


def load_plugin_class(plugins_dir, plugin_folder_name, manifest):
    module_name = f"{plugins_dir}.{plugin_folder_name}.{manifest['module']}"
    plugin_module = importlib.import_module(module_name)
    class_name = manifest['entry_point']
    return getattr(plugin_module, class_name)


def run_status_check(plugins_dir, plugin_folder_name, manifest):
    module_name = f"{plugins_dir}.{plugin_folder_name}.{manifest['module']}"
    plugin_module = importlib.import_module(module_name)
    status_function = getattr(plugin_module, manifest['status_check']['function_name'])
    return status_function()