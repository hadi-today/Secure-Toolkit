import os

# --- Main Paths ---
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, "archive.db")
ARCHIVE_DIR = os.path.join(PLUGIN_DIR, "archive")
THUMBNAIL_DIR = os.path.join(PLUGIN_DIR, "thumbnails")

# --- UI Settings ---
THUMBNAIL_SIZE = (150, 150)
WINDOW_TITLE = "Image Manager"

# --- Search Logic ---
TAG_MATCH_SCORE = 3
DESC_MATCH_SCORE = 1

# --- Database Schema ---
TABLE_NAME = "archive_items"


# --- User Settings ---
SETTINGS_PATH = os.path.join(PLUGIN_DIR, "user_settings.json")