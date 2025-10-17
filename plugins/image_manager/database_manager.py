import sqlite3
import logging
from . import config

class DatabaseManager:
    def __init__(self, db_path=config.DB_PATH):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logging.info("Database connection successful.")
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")

    def execute_query(self, query, params=(), fetch=None):
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            if fetch == "one":
                return cursor.fetchone()
            if fetch == "all":
                return cursor.fetchall()
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Query failed: {query} - {e}")
            self.conn.rollback()
            return None

    def create_tables(self):
        query = f"""
        CREATE TABLE IF NOT EXISTS {config.TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            description TEXT,
            source_text TEXT,
            source_link TEXT,
            tags TEXT,
            framed_filename TEXT,
            date_added TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            thumbnail_filename TEXT UNIQUE
        );
        """
        self.execute_query(query)
        logging.info(f"Table '{config.TABLE_NAME}' created or already exists.")
        
    def add_item(self, filename, thumbnail_filename):
        query = f"INSERT INTO {config.TABLE_NAME} (filename, thumbnail_filename) VALUES (?, ?)"
        cursor = self.conn.cursor()
        cursor.execute(query, (filename, thumbnail_filename))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_items(self):
        query = f"SELECT * FROM {config.TABLE_NAME} ORDER BY date_added DESC"
        return self.execute_query(query, fetch="all")

    def get_item_by_id(self, item_id):
        query = f"SELECT * FROM {config.TABLE_NAME} WHERE id = ?"
        return self.execute_query(query, (item_id,), fetch="one")

    def update_item(self, item_id, data):
        fields = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {config.TABLE_NAME} SET {fields} WHERE id = ?"
        params = list(data.values()) + [item_id]
        self.execute_query(query, tuple(params))

    def get_all_unique_tags(self):
        query = f"SELECT tags FROM {config.TABLE_NAME}"
        rows = self.execute_query(query, fetch="all")
        if not rows:
            return []
        
        all_tags = set()
        for row in rows:
            if row['tags']:
                tags = [tag.strip() for tag in row['tags'].split(',')]
                all_tags.update(tags)
        return sorted(list(all_tags))

    def bulk_add_tags(self, item_ids, tags_to_add):
        placeholders = ','.join('?' for _ in item_ids)
        query = f"SELECT id, tags FROM {config.TABLE_NAME} WHERE id IN ({placeholders})"
        rows = self.execute_query(query, tuple(item_ids), fetch="all")
        
        for row in rows:
            current_tags_str = row['tags'] or ''  # Handle None case
            current_tags = set(tag.strip() for tag in current_tags_str.split(',') if tag.strip())
            current_tags.update(tags_to_add)
            new_tags_str = ','.join(sorted(list(current_tags)))
            self.update_item(row['id'], {'tags': new_tags_str})
        logging.info(f"Added tags '{tags_to_add}' to {len(item_ids)} items.")

    def bulk_remove_tags(self, item_ids, tags_to_remove):
        placeholders = ','.join('?' for _ in item_ids)
        query = f"SELECT id, tags FROM {config.TABLE_NAME} WHERE id IN ({placeholders})"
        rows = self.execute_query(query, tuple(item_ids), fetch="all")
        
        for row in rows:
            current_tags_str = row['tags'] or ''  # Handle None case
            current_tags = set(tag.strip() for tag in current_tags_str.split(',') if tag.strip())
            current_tags.difference_update(tags_to_remove)
            new_tags_str = ','.join(sorted(list(current_tags)))
            self.update_item(row['id'], {'tags': new_tags_str})
        logging.info(f"Removed tags '{tags_to_remove}' from {len(item_ids)} items.")

    def bulk_update_source(self, item_ids, source_text):
        placeholders = ','.join('?' for _ in item_ids)
        query = f"UPDATE {config.TABLE_NAME} SET source_text = ? WHERE id IN ({placeholders})"
        params = [source_text] + item_ids
        self.execute_query(query, tuple(params))
        logging.info(f"Updated source text for {len(item_ids)} items.")
    def bulk_update_source_link(self, item_ids, source_link):
        placeholders = ','.join('?' for _ in item_ids)
        query = f"UPDATE {config.TABLE_NAME} SET source_link = ? WHERE id IN ({placeholders})"
        params = [source_link] + item_ids
        self.execute_query(query, tuple(params))
        logging.info(f"Updated source link for {len(item_ids)} items.")
    def bulk_update_description(self, item_ids, description):
        placeholders = ','.join('?' for _ in item_ids)
        query = f"UPDATE {config.TABLE_NAME} SET description = ? WHERE id IN ({placeholders})"
        params = [description] + item_ids
        self.execute_query(query, tuple(params))
        logging.info(f"Updated description for {len(item_ids)} items.")
    def delete_items_by_ids(self, item_ids):
        """Deletes one or more items from the database based on their IDs."""
        if not item_ids:
            return
        
        placeholders = ','.join('?' for _ in item_ids)
        query = f"DELETE FROM {config.TABLE_NAME} WHERE id IN ({placeholders})"
        self.execute_query(query, tuple(item_ids))
        logging.info(f"Deleted {len(item_ids)} items from the database.")