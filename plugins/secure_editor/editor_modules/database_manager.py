import sqlite3
from . import config

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(config.DB_FILE_PATH)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                tags TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY,
                note_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                content_ciphertext BLOB NOT NULL,
                wrapped_cek BLOB NOT NULL,
                encrypting_key_name TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def add_note_version(self, name, tags, timestamp, key_name, crypto_bundle):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM notes WHERE name = ?", (name,))
        note = cursor.fetchone()
        
        if not note:
            cursor.execute("INSERT INTO notes (name, tags) VALUES (?, ?)", (name, tags))
            note_id = cursor.lastrowid
        else:
            note_id = note['id']
            if tags is not None:
                 cursor.execute("UPDATE notes SET tags = ? WHERE id = ?", (tags, note_id))

        cursor.execute("""
            INSERT INTO versions (note_id, timestamp, content_ciphertext, wrapped_cek, encrypting_key_name)
            VALUES (?, ?, ?, ?, ?)
        """, (note_id, timestamp, crypto_bundle['content_ciphertext'], crypto_bundle['wrapped_cek'], key_name))
        
        self.conn.commit()

    def get_all_notes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM notes ORDER BY name")
        return cursor.fetchall()

    def get_note_versions(self, note_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, timestamp FROM versions WHERE note_id = ? ORDER BY timestamp DESC", (note_id,))
        return cursor.fetchall()
        
    def get_version_bundle(self, version_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT content_ciphertext, wrapped_cek, encrypting_key_name FROM versions WHERE id = ?", (version_id,))
        return cursor.fetchone()
    def get_note_id_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM notes WHERE name = ?", (name,))
        note = cursor.fetchone()
        return note['id'] if note else None

    def close(self):
        self.conn.close()