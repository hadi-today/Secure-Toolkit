# مسیر: plugins/secure_editor/editor_modules/config.py

import os

# --- Paths ---
PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE_PATH = os.path.join(PLUGIN_DIR, "notes.db")

# --- Timers (in milliseconds) ---
AUTOSAVE_INTERVAL_MS = 60 * 1000  # 60 seconds
IDLE_AUTOSAVE_DELAY_MS = 2500     # <<< این خط باید اضافه شود: 2.5 ثانیه تاخیر
AUTOLOCK_INTERVAL_S = 5 * 60      # 5 minutes

# --- Cryptography ---
AES_KEY_SIZE = 32  # 256-bit
AES_NONCE_SIZE = 12 # GCM standard nonce size