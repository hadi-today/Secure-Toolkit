import os
import shutil
import uuid
import logging
import json
import sys
import subprocess
import re
from PyQt6.QtWidgets import (QWidget, QListWidgetItem, QMessageBox, QFileDialog)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize, QStringListModel, Qt

from . import config, ui_setup
from .database_manager import DatabaseManager
from .image_utils import create_thumbnail, process_and_save_image
from .search_logic import extract_keywords, rank_results

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageManagerWidget(QWidget):
    def __init__(self, keyring_data, save_callback):
        super().__init__()
        
        self.db_manager = DatabaseManager()
        self.current_item_id = None
        self.current_preview_path = None
        self.all_items = []
        self.settings = {}

        self.setWindowTitle(config.WINDOW_TITLE)
        self.setMinimumSize(1200, 800)

        self.THUMBNAIL_SIZE = QSize(*config.THUMBNAIL_SIZE)
        self.ARCHIVE_DIR = config.ARCHIVE_DIR
        self.THUMBNAIL_DIR = config.THUMBNAIL_DIR

        self.setup_directories()
        self.load_settings()
        self.db_manager.connect()
        self.db_manager.create_tables()

        ui_setup.setup_ui(self)
        self.connect_signals()
        self.load_all_items_into_gallery()
        self.update_tag_pool()
        self.settings_editor_input.setText(self.settings.get("external_editor", ""))

    def setup_directories(self):
        os.makedirs(self.ARCHIVE_DIR, exist_ok=True)
        os.makedirs(self.THUMBNAIL_DIR, exist_ok=True)

    def load_settings(self):
        try:
            with open(config.SETTINGS_PATH, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {}

    def save_settings(self):
        self.settings['external_editor'] = self.settings_editor_input.text()
        try:
            with open(config.SETTINGS_PATH, 'w') as f:
                json.dump(self.settings, f, indent=4)
            QMessageBox.information(self, "Success", "Settings saved.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save settings: {e}")

    def connect_signals(self):
        self.drag_drop_area.filesDropped.connect(self.handle_files_dropped)
        self.gallery_list.currentItemChanged.connect(self.handle_gallery_selection_changed)
        self.gallery_list.selectionModel().selectionChanged.connect(self.handle_gallery_multi_selection)
        self.save_button.clicked.connect(self.save_current_item_details)
        self.tag_pool_list.itemClicked.connect(self.add_tag_from_pool)
        self.search_bar.textChanged.connect(self.filter_gallery)
        
        self.add_framed_button.clicked.connect(self.add_framed_version)
        self.view_original_button.clicked.connect(lambda: self.update_preview(framed=False))
        self.view_framed_button.clicked.connect(lambda: self.update_preview(framed=True))

        self.bulk_apply_button.clicked.connect(self.apply_bulk_edit)
        self.settings_save_button.clicked.connect(self.save_settings)
        self.export_button.clicked.connect(self.export_current_image)
        self.open_editor_button.clicked.connect(self.open_with_external_editor)
        self.delete_button.clicked.connect(self.delete_single_item)
        self.bulk_delete_button.clicked.connect(self.delete_bulk_items)

    def load_all_items_into_gallery(self):
        self.all_items = self.db_manager.get_all_items()
        self.display_items_in_gallery(self.all_items)

    def display_items_in_gallery(self, items):
        self.gallery_list.clear()
        for item in items:
            thumb_path = os.path.join(self.THUMBNAIL_DIR, item['thumbnail_filename'])
            if os.path.exists(thumb_path):
                list_item = QListWidgetItem(QIcon(thumb_path), "")
                list_item.setData(Qt.ItemDataRole.UserRole, item['id'])
                self.gallery_list.addItem(list_item)

    def handle_files_dropped(self, file_paths):
        processed_count = 0
        for path in file_paths:
            try:
                new_filename, dest_path = process_and_save_image(path)
                if not new_filename or not dest_path:
                    raise Exception("Image processing failed.")
                thumb_filename = create_thumbnail(dest_path)
                if not thumb_filename:
                    raise Exception("Thumbnail creation failed.")
                self.db_manager.add_item(new_filename, thumb_filename)
                processed_count += 1
            except Exception as e:
                logging.error(f"Failed to add file {path}: {e}")
                QMessageBox.warning(self, "Error", f"Could not process file: {os.path.basename(path)}")
        if processed_count > 0:
            self.load_all_items_into_gallery()

    def handle_gallery_selection_changed(self, current, previous):
        if not current:
            self.current_item_id = None
            self.current_preview_path = None
            self.details_panel.setVisible(False)
            return
        self.current_item_id = current.data(Qt.ItemDataRole.UserRole)
        self.populate_details_panel(self.current_item_id)
        
    def handle_gallery_multi_selection(self):
        selected_count = len(self.gallery_list.selectedItems())
        if selected_count > 1:
            self.details_panel.setVisible(False)
            self.bulk_edit_panel.setVisible(True)
        else:
            self.bulk_edit_panel.setVisible(False)
            if self.gallery_list.currentItem():
                self.details_panel.setVisible(True)
                self.populate_details_panel(self.gallery_list.currentItem().data(Qt.ItemDataRole.UserRole))
            else:
                 self.details_panel.setVisible(False)

    def populate_details_panel(self, item_id):
        item_data = self.db_manager.get_item_by_id(item_id)
        if not item_data: return
        self.desc_input.setText(item_data['description'])
        self.tags_input.setText(item_data['tags'])
        self.source_text_input.setText(item_data['source_text'])
        self.source_link_input.setText(item_data['source_link'])
        self.update_preview(framed=False)
        self.view_framed_button.setEnabled(bool(item_data['framed_filename']))
        self.details_panel.setVisible(True)

    def update_preview(self, framed=False):
        if not self.current_item_id: return
        item_data = self.db_manager.get_item_by_id(self.current_item_id)
        filename_to_show = item_data['filename']
        if framed and item_data['framed_filename']:
            filename_to_show = item_data['framed_filename']
        self.current_preview_path = os.path.join(self.ARCHIVE_DIR, filename_to_show)
        if os.path.exists(self.current_preview_path):
            pixmap = QPixmap(self.current_preview_path)
            self.image_preview.setPixmap(pixmap.scaled(self.image_preview.size(), 
                                           Qt.AspectRatioMode.KeepAspectRatio, 
                                           Qt.TransformationMode.SmoothTransformation))
        else:
            self.image_preview.setText(f"Image not found:\n{filename_to_show}")
            self.current_preview_path = None

    def save_current_item_details(self):
        if not self.current_item_id: return

        # Standardize tags before saving
        raw_tags = self.tags_input.text()
        # Split by comma, hash, or space, and filter out empty strings
        tags_list = [tag.strip() for tag in re.split(r'[,#\s]+', raw_tags) if tag.strip()]
        clean_tags_str = ', '.join(sorted(list(set(tags_list)))) # Unique, sorted, comma-separated

        data = {
            'description': self.desc_input.toPlainText(),
            'tags': clean_tags_str, # Use the cleaned string
            'source_text': self.source_text_input.text(),
            'source_link': self.source_link_input.text()
        }
        self.db_manager.update_item(self.current_item_id, data)
        self.tags_input.setText(clean_tags_str) # Update the UI with the cleaned tags
        self.update_tag_pool()
        QMessageBox.information(self, "Success", "Changes have been saved.")

    def add_framed_version(self):
        if not self.current_item_id: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Framed Image", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path: return
        item_data = self.db_manager.get_item_by_id(self.current_item_id)
        base, ext = os.path.splitext(item_data['filename'])
        framed_filename = f"{base}-framed{ext}"
        dest_path = os.path.join(self.ARCHIVE_DIR, framed_filename)
        try:
            shutil.copy(file_path, dest_path)
            self.db_manager.update_item(self.current_item_id, {'framed_filename': framed_filename})
            self.view_framed_button.setEnabled(True)
            self.update_preview(framed=True)
            QMessageBox.information(self, "Success", "Framed version added.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not add framed version: {e}")
            
    def update_tag_pool(self):
        tags = self.db_manager.get_all_unique_tags()
        self.tag_pool_list.clear()
        self.tag_pool_list.addItems(tags)
        model = QStringListModel(tags)
        self.tag_completer.setModel(model)

    def add_tag_from_pool(self, item):
        tag_to_add = item.text()
        current_tags = set(t.strip() for t in self.tags_input.text().split(',') if t.strip())
        if tag_to_add not in current_tags:
            current_tags.add(tag_to_add)
            self.tags_input.setText(', '.join(sorted(list(current_tags))))

    def filter_gallery(self, text):
        if not text:
            self.display_items_in_gallery(self.all_items)
            return
        keywords = extract_keywords(text)
        if not keywords:
            self.display_items_in_gallery(self.all_items)
            return
        ranked_results = rank_results(self.all_items, keywords)
        items_to_display = [res['item'] for res in ranked_results]
        self.display_items_in_gallery(items_to_display)

    def apply_bulk_edit(self):
            selected_items = self.gallery_list.selectedItems()
            if not selected_items: return
            item_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
            
            # Split by comma, hash, or space for robust input
            tags_to_add_str = self.bulk_add_tags_input.text()
            tags_to_add = [t.strip() for t in re.split(r'[,#\s]+', tags_to_add_str) if t.strip()]
            if tags_to_add: self.db_manager.bulk_add_tags(item_ids, tags_to_add)

            tags_to_remove_str = self.bulk_remove_tags_input.text()
            tags_to_remove = [t.strip() for t in re.split(r'[,#\s]+', tags_to_remove_str) if t.strip()]
            if tags_to_remove: self.db_manager.bulk_remove_tags(item_ids, tags_to_remove)
            
            source_text = self.bulk_source_input.text()
            if source_text: self.db_manager.bulk_update_source(item_ids, source_text)
            source_link = self.bulk_source_link_input.text()
            if source_link:
                self.db_manager.bulk_update_source_link(item_ids, source_link)
            description = self.bulk_description_input.toPlainText()
            if description:
              self.db_manager.bulk_update_description(item_ids, description)
            self.load_all_items_into_gallery()
            self.update_tag_pool()
            self.bulk_add_tags_input.clear(); self.bulk_remove_tags_input.clear(); self.bulk_source_input.clear(); self.bulk_description_input.clear(); self.bulk_source_link_input.clear()
            QMessageBox.information(self, "Success", f"Changes applied to {len(item_ids)} items.")

    def export_current_image(self):
        if not self.current_preview_path:
            QMessageBox.warning(self, "No Image", "Please select an image to export.")
            return
        
        suggested_filename = os.path.basename(self.current_preview_path)
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Image As...", suggested_filename, "Images (*.png *.jpg *.jpeg)")

        if save_path:
            try:
                shutil.copy(self.current_preview_path, save_path)
                QMessageBox.information(self, "Success", f"Image successfully exported to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export image: {e}")

    def open_with_external_editor(self):
        editor_command = self.settings.get("external_editor")
        if not editor_command:
            QMessageBox.warning(self, "Editor Not Set", "Please set the external editor command in the Settings panel first.")
            return
        if not self.current_preview_path:
            QMessageBox.warning(self, "No Image", "Please select an image to open.")
            return

        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", "-a", editor_command, self.current_preview_path], check=True)
            elif sys.platform == "win32":  # Windows
                # os.startfile is an option for default apps, but for a specific one, subprocess is better.
                subprocess.run([editor_command, self.current_preview_path], check=True, shell=True)
            else:  # Linux and other UNIX-like
                subprocess.run([editor_command, self.current_preview_path], check=True)
        except FileNotFoundError:
            QMessageBox.critical(self, "Command Not Found", f"The command '{editor_command}' was not found. Please check your settings and system's PATH.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open image with '{editor_command}':\n{e}")

    def closeEvent(self, event):
        self.db_manager.close()
        event.accept()
    def delete_single_item(self):
        """Handles deleting the currently selected single item."""
        if not self.current_item_id:
            return
        self.delete_items([self.current_item_id])

    def delete_bulk_items(self):
        """Handles deleting all currently selected items in the gallery."""
        selected_items = self.gallery_list.selectedItems()
        if not selected_items:
            return
        
        item_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        self.delete_items(item_ids)

    def delete_items(self, item_ids):
        """Core deletion logic for a list of item IDs."""
        if not item_ids:
            return

        count = len(item_ids)
        item_text = "item" if count == 1 else "items"
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete {count} {item_text}?\n"
            "This will also delete the associated image files from the disk and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            items_to_delete = []
            for item_id in item_ids:
                item_data = self.db_manager.get_item_by_id(item_id)
                if item_data:
                    items_to_delete.append(item_data)
            
            # Step 1: Delete files from disk
            for item_data in items_to_delete:
                self._delete_associated_files(item_data)

            # Step 2: Delete records from database
            self.db_manager.delete_items_by_ids(item_ids)

            # Step 3: Refresh UI
            self.load_all_items_into_gallery()
            self.details_panel.setVisible(False)
            self.bulk_edit_panel.setVisible(False)
            self.update_tag_pool()
            
            QMessageBox.information(self, "Success", f"{count} {item_text} have been deleted.")

    def _delete_associated_files(self, item_data_row):
        """Safely deletes all files associated with a single database row."""
        filenames_to_delete = [
            item_data_row['filename'],
            item_data_row['framed_filename'],
            item_data_row['thumbnail_filename']
        ]
        
        dir_map = {
            item_data_row['filename']: self.ARCHIVE_DIR,
            item_data_row['framed_filename']: self.ARCHIVE_DIR,
            item_data_row['thumbnail_filename']: self.THUMBNAIL_DIR
        }

        for filename in filenames_to_delete:
            if filename:  # Check if filename is not None or empty
                try:
                    dir_path = dir_map.get(filename)
                    if dir_path:
                        file_path = os.path.join(dir_path, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logging.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logging.error(f"Failed to delete file {filename}: {e}")