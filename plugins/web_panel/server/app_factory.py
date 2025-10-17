from flask import Flask

from .config import DATABASE_URI, SECRET_KEY
from .database import init_app_db
from .plugin_discovery import discover_plugins
from .routes_auth import auth_bp
from .routes_core import core_bp
from .routes_items import items_bp
from .routes_lists import lists_bp
from .routes_main import main_pages_bp


def create_app(password_verifier=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['PASSWORD_VERIFIER'] = password_verifier

    init_app_db(app)

    discovered_plugins = discover_plugins()
    plugins_frontend_info = []
    gadgets_catalog = []

    for plugin in discovered_plugins:
        plugin_name = plugin['name']
        manifest = plugin['manifest']
        blueprint = plugin['blueprint']
        gadgets_provider = plugin.get('gadgets_provider')

        url_prefix = f'/plugins/{plugin_name}'
        app.register_blueprint(blueprint, url_prefix=url_prefix)

        plugins_frontend_info.append(
            {
                'name': plugin_name,
                'display_name': manifest.get('display_name', plugin_name),
                'icon': manifest.get('icon', 'fa-question-circle'),
                'base_path': url_prefix,
            }
        )

        if callable(gadgets_provider):
            try:
                provided_gadgets = gadgets_provider(url_prefix)
            except Exception as gadget_error:
                app.logger.error(
                    "Gadget provider for plugin '%s' raised an exception: %s",
                    plugin_name,
                    gadget_error,
                )
                provided_gadgets = []

            if isinstance(provided_gadgets, list):
                for index, gadget in enumerate(provided_gadgets):
                    if not isinstance(gadget, dict):
                        continue

                    title = gadget.get('title')
                    content_html = gadget.get('content_html')

                    if not title or not content_html:
                        continue

                    normalized = {
                        'id': gadget.get('id') or f'{plugin_name}-gadget-{index}',
                        'plugin': plugin_name,
                        'title': title,
                        'description': gadget.get('description', ''),
                        'content_html': content_html,
                        'download': gadget.get('download'),
                        'order': gadget.get('order', index),
                    }
                    gadgets_catalog.append(normalized)

    app.config['DISCOVERED_PLUGINS_INFO'] = plugins_frontend_info
    app.config['GADGETS_CATALOG'] = sorted(
        gadgets_catalog,
        key=lambda item: (item.get('order', 0), item.get('title', '')),
    )

    app.register_blueprint(main_pages_bp)
    app.register_blueprint(core_bp, url_prefix='/api/core')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(lists_bp, url_prefix='/api/lists')
    app.register_blueprint(items_bp, url_prefix='/api/items')

    return app
