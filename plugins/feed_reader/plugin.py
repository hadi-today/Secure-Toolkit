# File: plugin.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QTabWidget, QMessageBox,
                             QInputDialog, QMenu, QSplitter, QLabel)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices

from .constants import *
from .database_manager import DatabaseManager
from .feed_fetcher import FetchFeedThread
from .ui_dialogs import AddFeedDialog
from .utils import humanize_time

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    from PyQt6.QtWidgets import QTextBrowser

class FeedReaderWidget(QWidget):
    def __init__(self, keyring_data, save_callback, main_window):
        super().__init__()
        self.setWindowTitle("Feed Reader"); self.db = DatabaseManager()
        self.threads = []; self._init_ui(); self._load_initial_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()
        add_feed_btn = QPushButton("Add Feed"); add_feed_btn.clicked.connect(self._add_feed)
        refresh_all_btn = QPushButton("Refresh All Feeds"); refresh_all_btn.clicked.connect(self._refresh_all_feeds)
        top_bar_layout.addWidget(add_feed_btn); top_bar_layout.addWidget(refresh_all_btn); top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel_widget = QWidget(); left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(0,0,0,0); left_layout.addWidget(QLabel("Feeds"))
        self.feed_list_widget = QListWidget()
        self.feed_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.feed_list_widget.customContextMenuRequested.connect(self._show_feed_context_menu)
        left_layout.addWidget(self.feed_list_widget)
        
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        self.unread_list = self._create_article_list()
        self.read_list = self._create_article_list()
        self.used_archived_list = self._create_article_list()
        self.tabs.addTab(self.unread_list, "Unread")
        self.tabs.addTab(self.read_list, "Read")
        self.tabs.addTab(self.used_archived_list, "Used & Archived")
        
        if WEB_ENGINE_AVAILABLE: self.article_view = QWebEngineView()
        else: self.article_view = QTextBrowser(); self.article_view.setOpenExternalLinks(True)
        right_splitter.addWidget(self.tabs); right_splitter.addWidget(self.article_view)
        right_splitter.setSizes([300, 600]); main_splitter.addWidget(left_panel_widget)
        main_splitter.addWidget(right_splitter); main_splitter.setSizes([200, 900])
        main_layout.addWidget(main_splitter); self.setLayout(main_layout)

    def _create_article_list(self):
        list_widget = QListWidget(); list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(self._show_article_context_menu)
        list_widget.itemClicked.connect(self._on_article_clicked)
        return list_widget

    def _load_initial_data(self):
        self._populate_feed_list()
        self._populate_list(self.unread_list, self.db.get_articles_by_status(STATUS_UNREAD))
        self._populate_list(self.read_list, self.db.get_articles_by_status(STATUS_READ))
        self._populate_list(self.used_archived_list, self.db.get_articles_by_status(STATUS_USED_ARCHIVED))

    def _populate_feed_list(self):
        self.feed_list_widget.clear()
        for feed in self.db.get_all_feeds():
            item = QListWidgetItem(feed[1]); item.setData(Qt.ItemDataRole.UserRole, feed)
            self.feed_list_widget.addItem(item)
            
    def _populate_list(self, list_widget, articles):
        list_widget.clear()
        for article in articles:
            time_str = humanize_time(article[3]); item_text = f"{time_str} - {article[1]}\n[{article[5]}]"
            item = QListWidgetItem(item_text); item.setData(Qt.ItemDataRole.UserRole, article)
            list_widget.addItem(item)
            
    def _add_feed(self):
        dialog = AddFeedDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not (data["name"] and data["url"]): return
            new_feed_id = self.db.add_feed(data["name"], data["url"], data["timezone"], data["fetch_days"])
            if new_feed_id: self._populate_feed_list(); self._fetch_single_feed(new_feed_id, data["url"], data["timezone"], data["fetch_days"])
            else: QMessageBox.warning(self, "Error", "This feed URL already exists.")

    def _refresh_all_feeds(self):
        if self.threads: return
        feeds = self.db.get_all_feeds()
        if not feeds: return
        for feed_id, name, url, timezone, fetch_days in feeds:
            self._fetch_single_feed(feed_id, url, timezone, fetch_days)

    def _fetch_single_feed(self, feed_id, feed_url, feed_timezone, fetch_days):
        thread = FetchFeedThread(feed_id, feed_url, feed_timezone, fetch_days)
        thread.result_ready.connect(self._on_fetch_result)
        thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Fetch Error", msg))
        thread.status_updated.connect(lambda msg: print(msg))
        thread.finished.connect(self._check_if_all_fetches_done)
        self.threads.append(thread); thread.start()

    def _on_fetch_result(self, feed_id, articles):
        if articles: self.db.save_articles_if_new(feed_id, articles)

    def _check_if_all_fetches_done(self):
        sender_thread = self.sender()
        if sender_thread in self.threads: self.threads.remove(sender_thread)
        if not self.threads: self._load_initial_data(); QMessageBox.information(self, "Refresh Complete", "All feeds processed.")
            
    def _on_article_clicked(self, item):
        list_widget = self.sender(); article_data = item.data(Qt.ItemDataRole.UserRole)
        article_id, _, link, _, _, _, _ = article_data
        if list_widget == self.unread_list:
            self.db.update_article_status(article_id, STATUS_READ)
            taken_item = self.unread_list.takeItem(self.unread_list.row(item))
            self.read_list.insertItem(0, taken_item)
        if WEB_ENGINE_AVAILABLE: self.article_view.setUrl(QUrl(link))
        else: self.article_view.setHtml(f"<h2><a href='{link}'>{article_data[1]}</a></h2>")

    def _show_article_context_menu(self, pos):
        list_widget = self.sender(); item = list_widget.itemAt(pos)
        if not item: return
        article_data = item.data(Qt.ItemDataRole.UserRole); menu = QMenu()
        current_status = article_data[6]
        if current_status in [STATUS_UNREAD, STATUS_READ]:
            use_action = menu.addAction("Use & Start Archiving")
            use_action.triggered.connect(lambda: self._use_and_archive(item))
        elif current_status == STATUS_USED_ARCHIVED:
            edit_archive_action = menu.addAction("Add/Edit Archive Link")
            edit_archive_action.triggered.connect(lambda: self._edit_archive_link(item))
            return_action = menu.addAction("Return to Unread")
            return_action.triggered.connect(lambda: self._mark_as_unread(item))
            view_archived = menu.addAction("View Archived Version")
            view_archived.setEnabled(bool(article_data[4]))
            view_archived.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(article_data[4])))
        menu.addSeparator()
        open_original = menu.addAction("Open Original in Browser")
        open_original.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(article_data[2])))
        menu.exec(list_widget.mapToGlobal(pos))
        
    def _show_feed_context_menu(self, pos):
        item = self.feed_list_widget.itemAt(pos);
        if not item: return
        feed_data = item.data(Qt.ItemDataRole.UserRole); menu = QMenu()
        edit_action = menu.addAction("Edit Feed")
        edit_action.triggered.connect(lambda: self._edit_feed(feed_data))
        refresh_action = menu.addAction("Refresh This Feed")
        # <<< FIX: Pass the missing fetch_days (feed_data[4]) to the function call >>>
        refresh_action.triggered.connect(lambda: self._fetch_single_feed(feed_data[0], feed_data[2], feed_data[3], feed_data[4]))
        delete_action = menu.addAction("Delete Feed")
        delete_action.triggered.connect(lambda: self._delete_feed(feed_data[0], feed_data[1]))
        menu.exec(self.feed_list_widget.mapToGlobal(pos))
        
    def _edit_feed(self, feed_data):
        feed_id, name, url, timezone, fetch_days = feed_data
        dialog_data = {'name': name, 'url': url, 'timezone': timezone, 'fetch_days': fetch_days}
        dialog = AddFeedDialog(self, feed_data=dialog_data)
        if dialog.exec():
            new_data = dialog.get_data()
            if not (new_data["name"] and new_data["url"]): return
            self.db.update_feed(feed_id, new_data["name"], new_data["url"], new_data["timezone"], new_data["fetch_days"])
            self._populate_feed_list()
            
    def _delete_feed(self, feed_id, feed_name):
        reply = QMessageBox.question(self, "Confirm Deletion", f"Delete '{feed_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.db.delete_feed(feed_id); self._load_initial_data()
        
    def _use_and_archive(self, item):
        list_widget = self.sender(); article_data = item.data(Qt.ItemDataRole.UserRole)
        article_id, _, link, _, _, _, _ = article_data
        self.db.update_article_status(article_id, STATUS_USED_ARCHIVED)
        QDesktopServices.openUrl(QUrl(f"https://archive.is/?url={link}"))
        self._load_initial_data()
        
    def _edit_archive_link(self, item):
        article_data = item.data(Qt.ItemDataRole.UserRole); article_id = article_data[0]
        current_link = article_data[4] or ""
        archive_link, ok = QInputDialog.getText(self, "Add/Edit Archive Link", "Paste the final archive.is URL here:", text=current_link)
        if ok and archive_link.strip().startswith("https://archive.is/"):
            self.db.update_archive_link(article_id, archive_link.strip())
            self._load_initial_data()
        elif ok: QMessageBox.warning(self, "Invalid URL", "Please provide a valid URL from archive.is.")
            
    def _mark_as_unread(self, item):
        article_data = item.data(Qt.ItemDataRole.UserRole); article_id = article_data[0]
        self.db.update_article_status(article_id, STATUS_UNREAD); self._load_initial_data()