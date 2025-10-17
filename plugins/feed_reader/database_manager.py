# File: database_manager.py

import sqlite3
import os
from .constants import DB_FILE

class DatabaseManager:
    def __init__(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(plugin_dir, DB_FILE)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            timezone TEXT,
            fetch_days INTEGER DEFAULT 30
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            published_date DATETIME,
            status INTEGER DEFAULT 0,
            archive_link TEXT,
            FOREIGN KEY (feed_id) REFERENCES feeds (id) ON DELETE CASCADE
        )""")
        self.conn.commit()

    def add_feed(self, name, url, timezone, fetch_days):
        try:
            self.cursor.execute("INSERT INTO feeds (name, url, timezone, fetch_days) VALUES (?, ?, ?, ?)", (name, url, timezone, fetch_days))
            self.conn.commit(); return self.cursor.lastrowid
        except sqlite3.IntegrityError: return None

    def get_all_feeds(self):
        self.cursor.execute("SELECT id, name, url, timezone, fetch_days FROM feeds ORDER BY name")
        return self.cursor.fetchall()
        
    def delete_feed(self, feed_id):
        self.cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,)); self.conn.commit()

    def save_articles_if_new(self, feed_id, articles):
        new_articles = []
        for article in articles:
            self.cursor.execute("SELECT id FROM articles WHERE link = ?", (article['link'],))
            if self.cursor.fetchone() is None:
                new_articles.append((feed_id, article['title'], article['link'], article['published_parsed']))
        if new_articles:
            self.cursor.executemany("INSERT INTO articles (feed_id, title, link, published_date, status) VALUES (?, ?, ?, ?, 0)", new_articles)
            self.conn.commit()

    def get_articles_by_status(self, status):
        query = """
            SELECT a.id, a.title, a.link, a.published_date, a.archive_link, f.name, a.status 
            FROM articles a JOIN feeds f ON a.feed_id = f.id
            WHERE a.status = ? ORDER BY a.published_date DESC """
        self.cursor.execute(query, (status,)); return self.cursor.fetchall()

    def update_article_status(self, article_id, new_status):
        self.cursor.execute("UPDATE articles SET status = ? WHERE id = ?", (new_status, article_id)); self.conn.commit()

    def update_archive_link(self, article_id, archive_link):
        self.cursor.execute("UPDATE articles SET archive_link = ? WHERE id = ?", (archive_link, article_id)); self.conn.commit()
        
    def update_feed(self, feed_id, name, url, timezone, fetch_days):
        try:
            self.cursor.execute("UPDATE feeds SET name = ?, url = ?, timezone = ?, fetch_days = ? WHERE id = ?", (name, url, timezone, fetch_days, feed_id))
            self.conn.commit(); return True
        except Exception as e:
            print(f"Error updating feed: {e}"); return False
            
    def close(self): self.conn.close()