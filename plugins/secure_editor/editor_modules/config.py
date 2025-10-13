# plugins/secure_editor/editor_modules/config.py

import os


PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE_PATH = os.path.join(PLUGIN_DIR, "notes.db")


AUTOSAVE_INTERVAL_MS = 60 * 1000  
IDLE_AUTOSAVE_DELAY_MS = 2500     
AUTOLOCK_INTERVAL_S = 5 * 60     


AES_KEY_SIZE = 32 
AES_NONCE_SIZE = 12 