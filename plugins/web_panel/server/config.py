import os


PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_NAME = 'web_panel.db'
DATABASE_URI = f'sqlite:///{os.path.join(PLUGIN_DIR, DB_NAME)}'
SECRET_KEY = 'this-is-a-super-secret-key-for-jwt-!@#$%^&*()'
