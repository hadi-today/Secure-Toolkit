# plugins/secure_editor/editor_modules/editor_logic.py

import os
import shutil
import base64
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QApplication
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QTextListFormat, QTextBlockFormat, QDesktopServices
from . import config
# --- ایمپورت‌های مطلق و نهایی ---
from plugins.secure_editor.editor_modules.crypto_manager import encrypt_content, decrypt_content
from plugins.secure_editor.editor_modules.dialogs import SelectKeyDialog, get_passphrase

from PyQt6.QtGui import QFont, QTextListFormat, QTextBlockFormat

try:
    import docx
except ImportError:
    docx = None

class EditorLogic:
    def __init__(self, main_widget, ui, db_manager, keyring_data):
        self.main_widget = main_widget
        self.ui = ui
        self.db = db_manager
        self.keyring_data = keyring_data
        self.current_note_id = None
        self.current_version_id = None
        self.current_key_name = None
        self.current_note_name = ""
        self.content_changed = False
        self.is_dark_theme = False
        self.is_code_view = False
        self.attachments_dir = os.path.join(config.PLUGIN_DIR, "attachments")
        Path(self.attachments_dir).mkdir(parents=True, exist_ok=True)

    def on_text_changed(self):
        self.content_changed = True
        plain_text = self.ui.text_edit.toPlainText()
        word_count = len(plain_text.split()) if plain_text else 0
        self.ui.word_count_label.setText(f"Words: {word_count}")
    def on_code_changed(self):
        self.content_changed = True

    def get_key_from_keyring(self, key_name, key_type='private'):
        for pair in self.keyring_data.get('my_key_pairs', []):
            if pair['name'] == key_name:
                return pair.get(f'{key_type}_key')
        return None

    def save_note(self, is_autosave=False):
        if self.is_code_view:
            self.ui.text_edit.setHtml(self.ui.code_edit.toPlainText())
        if not self.content_changed and is_autosave:
            return
        note_name = self.current_note_name
        if not is_autosave:
            text, ok = QInputDialog.getText(self.main_widget, "Save Note", "Enter name:", text=note_name)
            if not ok or not text.strip(): return
            note_name = text.strip()
            self.current_note_name = note_name
            if self.current_key_name is None:
                keys = [k['name'] for k in self.keyring_data.get('my_key_pairs', [])]
                if not keys:
                    QMessageBox.critical(self.main_widget, "Error", "No key pairs found.")
                    return
                dialog = SelectKeyDialog(keys, self.main_widget)
                key = dialog.get_selected_key()
                if not key: return
                self.current_key_name = key
        
        if not self.current_key_name: return
        pub_key = self.get_key_from_keyring(self.current_key_name, 'public')
        bundle = encrypt_content(self.ui.text_edit.toHtml().encode('utf-8'), pub_key)
        self.db.add_note_version(note_name, "", datetime.now().isoformat(), self.current_key_name, bundle)
        self.content_changed = False
        msg = f"Autosaved." if is_autosave else f"Saved."
        self.ui.status_bar.showMessage(f"Note '{note_name}' {msg}", 4000)
        if not is_autosave:
            self.current_note_id = self.db.get_note_id_by_name(note_name)

    def load_note(self):
        print("--- DEBUG: 1. Starting load_note process... ---")
        notes = self.db.get_all_notes()
        if not notes:
            QMessageBox.information(self.main_widget, "No Notes", "No notes to load.")
            print("--- DEBUG: No notes found. Exiting. ---")
            return
        
        print(f"--- DEBUG: 2. Found {len(notes)} notes in the database. ---")
        note_name, ok = QInputDialog.getItem(self.main_widget, "Select Note", "Choose note:", [n['name'] for n in notes], 0, False)
        if not ok:
            print("--- DEBUG: User canceled note selection. Exiting. ---")
            return
        
        print(f"--- DEBUG: 3. User selected note: '{note_name}' ---")
        note_id = self.db.get_note_id_by_name(note_name)
        if not note_id:
            print(f"--- DEBUG: ERROR! Could not find ID for note '{note_name}'. Exiting. ---")
            QMessageBox.critical(self.main_widget, "Error", f"Could not find a valid ID for note '{note_name}'.")
            return
            
        versions = self.db.get_note_versions(note_id)
        if not versions:
            print(f"--- DEBUG: No versions found for note '{note_name}'. Exiting. ---")
            QMessageBox.warning(self.main_widget, "No Versions", f"No saved versions found for '{note_name}'.")
            return
            
        print(f"--- DEBUG: 4. Found {len(versions)} versions. Showing version selection dialog. ---")
        timestamps = [datetime.fromisoformat(v['timestamp']).strftime('%Y-%m-%d %H:%M:%S') for v in versions]
        ts, ok = QInputDialog.getItem(self.main_widget, "Select Version", f"Choose version for '{note_name}':", timestamps, 0, False)
        if not ok:
            print("--- DEBUG: User canceled version selection. Exiting. ---")
            return
        
        print(f"--- DEBUG: 5. User selected version: {ts} ---")
        v_id = versions[timestamps.index(ts)]['id']
        bundle = self.db.get_version_bundle(v_id)
        key_name = bundle['encrypting_key_name']
        priv_key = self.get_key_from_keyring(key_name, 'private')
        
        pw = None
        if "ENCRYPTED" in priv_key:
            pw = get_passphrase(self.main_widget)
            if pw is None:
                print("--- DEBUG: Private key is encrypted but user canceled passphrase input. Exiting. ---")
                return

        try:
            print("--- DEBUG: 6. Attempting to decrypt content... ---")
            content = decrypt_content(bundle, priv_key, pw)
            self.ui.text_edit.setHtml(content.decode('utf-8'))
            print("--- DEBUG: 7. Decryption successful. Content set in text_edit. ---")
            
            if self.is_code_view:
                print("--- DEBUG: Currently in code view, switching to preview... ---")
                self.toggle_editor_view()
            
            self.current_note_id, self.current_version_id, self.current_key_name, self.current_note_name = note_id, v_id, key_name, note_name
            self.content_changed = False
            self.ui.status_bar.showMessage(f"Loaded '{note_name}' - {ts}", 5000)
            print("--- DEBUG: 8. Load process finished successfully! ---")
        except Exception as e:
            print(f"--- DEBUG: CRITICAL ERROR during decryption: {e} ---")
            QMessageBox.critical(self.main_widget, "Decryption Failed", f"Error: {e}")

    def export_to_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self.main_widget, "Export to PDF", self.current_note_name, "*.pdf")
        if path:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self.ui.text_edit.document().print(printer)
            self.ui.status_bar.showMessage(f"Exported to {path}", 4000)

    def export_to_word(self):
        if not docx:
            QMessageBox.warning(self.main_widget, "Missing Library", "'python-docx' is required.")
            return
        path, _ = QFileDialog.getSaveFileName(self.main_widget, "Export to Word", self.current_note_name, "*.docx")
        if path:
            doc = docx.Document()
            doc.add_paragraph(self.ui.text_edit.toPlainText())
            doc.save(path)
            self.ui.status_bar.showMessage(f"Exported to {path}", 4000)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        style = "QWidget{background-color:#2b2b2b;color:#f0f0f0}QTextEdit{background-color:#3c3c3c}"
        QApplication.instance().setStyleSheet(style if self.is_dark_theme else "")

    def manage_notes(self):
        QMessageBox.information(self.main_widget, "WIP", "Note management is work in progress.")

    def search_notes(self):
        QMessageBox.information(self.main_widget, "WIP", "Search is work in progress.")
        
    def create_list(self, style):
        cursor = self.ui.text_edit.textCursor()
        list_format = QTextListFormat()
        if style == 'bullet':
            list_format.setStyle(QTextListFormat.Style.ListDisc)
        else: # numbered
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
        
        cursor.createList(list_format)

    def _update_format_toolbar(self):
        font = self.ui.text_edit.currentFont()
        self.ui.font_combo.setCurrentFont(font)
        self.ui.font_size_combo.setCurrentText(str(int(font.pointSize())))

        self.ui.bold_action.setChecked(font.bold())
        self.ui.italic_action.setChecked(font.italic())
        self.ui.underline_action.setChecked(font.underline())
    def set_text_direction(self, direction):
        cursor = self.ui.text_edit.textCursor()
        block_format = QTextBlockFormat()
        block_format.setLayoutDirection(direction)
        cursor.mergeBlockFormat(block_format)
        self.ui.text_edit.setTextCursor(cursor)
    def insert_link(self):
        cursor = self.ui.text_edit.textCursor()
        selected_text = cursor.selectedText()
        
        link_text = selected_text
        if not link_text:
            text, ok = QInputDialog.getText(self.main_widget, "Insert Link", "Link Text:")
            if not ok or not text:
                return
            link_text = text

        url, ok = QInputDialog.getText(self.main_widget, "Insert Link", "URL:", text="https://")
        if ok and url:
            html = f'<a href="{url}">{link_text}</a>'
            cursor.insertHtml(html)

    def insert_image(self):
        cursor = self.ui.text_edit.textCursor()

        path, _ = QFileDialog.getOpenFileName(self.main_widget, "Insert Image", "", 
                                              "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if path:
            try:
                with open(path, "rb") as f:
                    image_data = f.read()
                
                b64_data = base64.b64encode(image_data).decode('utf-8')
                ext = os.path.splitext(path)[1][1:].lower()
                mime_type = f"image/{ext}"

                html = f'<img src="data:{mime_type};base64,{b64_data}" width="300" />'
                cursor.insertHtml(html)
                self.ui.status_bar.showMessage("Image inserted.", 3000)
            except Exception as e:
                QMessageBox.critical(self.main_widget, "Error", f"Could not insert image: {e}")

    def insert_file(self):
        cursor = self.ui.text_edit.textCursor()

        source_path, _ = QFileDialog.getOpenFileName(self.main_widget, "Attach File", "")
        if not source_path:
            return

        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.attachments_dir, filename)

        try:
            shutil.copy(source_path, dest_path)
            
            file_url = Path(dest_path).as_uri()
            html = f'📎 <a href="{file_url}">{filename}</a>'
            cursor.insertHtml(html)
            self.ui.status_bar.showMessage(f"File '{filename}' attached.", 3000)
        except Exception as e:
            QMessageBox.critical(self.main_widget, "Error", f"Could not attach file: {e}")
    def toggle_editor_view(self):
        if not self.is_code_view:
            html_content = self.ui.text_edit.toHtml()
            self.ui.code_edit.setPlainText(html_content)
            
            self.ui.editor_stack.setCurrentIndex(1)
            self.ui.toggle_view_button.setText("Show Preview")
            
            self.ui.format_toolbar.setEnabled(False)
            self.is_code_view = True
        else:
            code_content = self.ui.code_edit.toPlainText()
            self.ui.text_edit.setHtml(code_content)

            self.ui.editor_stack.setCurrentIndex(0)
            self.ui.toggle_view_button.setText("Show Code")

            self.ui.format_toolbar.setEnabled(True)
            self.is_code_view = False
    def handle_link_clicked(self, url: QUrl):
        scheme = url.scheme()
        
        if scheme == 'attachment':
            filename = url.path()
            file_path = os.path.join(self.attachments_dir, filename)
            
            if os.path.exists(file_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                QMessageBox.warning(self.main_widget, "File Not Found", 
                                    f"The attached file '{filename}' could not be found.")
        
        elif scheme in ['http', 'https']:
            QDesktopServices.openUrl(url)