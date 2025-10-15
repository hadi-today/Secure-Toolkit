# plugins/web_panel/server/plugin_discovery.py

import os
import json
import importlib
import logging

PLUGINS_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def discover_plugins():

    discovered = []
    logging.info(f"Scanning for plugins in: {PLUGINS_ROOT_DIR}")

    for plugin_name in os.listdir(PLUGINS_ROOT_DIR):
        plugin_path = os.path.join(PLUGINS_ROOT_DIR, plugin_name)
        panel_manifest_path = os.path.join(plugin_path, 'panel', 'manifest.json')

        if not os.path.isdir(plugin_path) or not os.path.exists(panel_manifest_path):
            continue

        try:
            with open(panel_manifest_path, 'r') as f:
                manifest = json.load(f)

            module_path = f"plugins.{plugin_name}.{manifest['blueprint_module']}"
            module = importlib.import_module(module_path)
            blueprint = getattr(module, manifest['blueprint_name'])

            gadgets_provider = None
            gadgets_module_name = manifest.get('gadgets_module')
            gadgets_factory_name = manifest.get('gadgets_factory')

            if gadgets_module_name and gadgets_factory_name:
                try:
                    gadgets_module_path = f"plugins.{plugin_name}.{gadgets_module_name}"
                    gadgets_module = importlib.import_module(gadgets_module_path)
                    gadgets_provider = getattr(gadgets_module, gadgets_factory_name)
                    logging.info(
                        "Discovered gadget provider '%s.%s' for plugin '%s'",
                        gadgets_module_name,
                        gadgets_factory_name,
                        plugin_name,
                    )
                except (ImportError, AttributeError) as gadget_error:
                    logging.error(
                        "Failed to load gadgets for plugin '%s': %s",
                        plugin_name,
                        gadget_error,
                    )

            discovered.append({
                "name": plugin_name,
                "manifest": manifest,
                "blueprint": blueprint,
                "gadgets_provider": gadgets_provider,
            })
            logging.info(f"Successfully discovered web plugin: {plugin_name}")

        except (json.JSONDecodeError, KeyError, ImportError, AttributeError) as e:
            logging.error(f"Failed to load web plugin '{plugin_name}': {e}")
            
    return discovered