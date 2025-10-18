"""Top-level dialog for the Secure Editor plugin."""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from .editor_modules.autosave import AutoSaver
from .editor_modules.database_manager import DatabaseManager
from .editor_modules.editor_logic import EditorLogic
from .editor_modules.ui_setup import MainWindowUI


class SecureEditorWidget(QDialog):
    """Modal dialog that hosts the secure editor and an overview panel."""

    def __init__(self, keyring_data, save_callback, parent=None):
        # Honour the optional parent provided by the launcher so the dialog
        # stacks with the main window without inheriting its layout.
        super().__init__(parent)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Retain injected dependencies for later use.
        self.keyring_data = keyring_data
        self.save_callback = save_callback

        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        self.db_manager = DatabaseManager()
        self.logic = EditorLogic(self, self.ui, self.db_manager, keyring_data)
        self.autosave_manager = AutoSaver(self)

        self._connect_signals()
        self.refresh_overview_panel()

        self.ui.status_bar.showMessage("Ready. Load or create a new note to begin.")

    def _connect_signals(self):
        """Wire UI controls to their respective handlers."""

        # === Primary toolbar ===
        self.ui.save_action.triggered.connect(self.logic.save_note)
        self.ui.load_action.triggered.connect(self.logic.load_note)
        self.ui.manage_action.triggered.connect(self.logic.manage_notes)
        self.ui.search_action.triggered.connect(self.logic.search_notes)
        self.ui.toggle_view_button.clicked.connect(self.logic.toggle_editor_view)

        # === Editors ===
        self.ui.text_edit.textChanged.connect(self.logic.on_text_changed)
        self.ui.text_edit.textChanged.connect(self.autosave_manager.on_activity)
        self.ui.text_edit.cursorPositionChanged.connect(self.logic._update_format_toolbar)
        self.ui.text_edit.linkClicked.connect(self.logic.handle_link_clicked)

        self.ui.code_edit.textChanged.connect(self.logic.on_code_changed)

        # === Formatting toolbar ===
        self.ui.font_combo.currentFontChanged.connect(self.ui.text_edit.setCurrentFont)
        self.ui.font_size_combo.currentTextChanged.connect(
            lambda size: self.ui.text_edit.setFontPointSize(float(size))
        )
        self.ui.bold_action.triggered.connect(
            lambda checked: self.ui.text_edit.setFontWeight(
                QFont.Weight.Bold if checked else QFont.Weight.Normal
            )
        )
        self.ui.italic_action.triggered.connect(self.ui.text_edit.setFontItalic)
        self.ui.underline_action.triggered.connect(self.ui.text_edit.setFontUnderline)
        self.ui.align_left_action.triggered.connect(
            lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        )
        self.ui.align_center_action.triggered.connect(
            lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        )
        self.ui.align_right_action.triggered.connect(
            lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        )
        self.ui.ltr_action.triggered.connect(
            lambda: self.logic.set_text_direction(Qt.LayoutDirection.LeftToRight)
        )
        self.ui.rtl_action.triggered.connect(
            lambda: self.logic.set_text_direction(Qt.LayoutDirection.RightToLeft)
        )
        self.ui.bullet_list_action.triggered.connect(lambda: self.logic.create_list("bullet"))
        self.ui.numbered_list_action.triggered.connect(
            lambda: self.logic.create_list("numbered")
        )
        self.ui.link_action.triggered.connect(self.logic.insert_link)
        self.ui.image_action.triggered.connect(self.logic.insert_image)
        self.ui.file_action.triggered.connect(self.logic.insert_file)

        # === Bottom bar ===
        self.ui.export_pdf_button.clicked.connect(self.logic.export_to_pdf)
        self.ui.export_word_button.clicked.connect(self.logic.export_to_word)
        self.ui.theme_button.clicked.connect(self.logic.toggle_theme)

        # === Notes overview panel ===
        self.ui.notes_list.itemSelectionChanged.connect(self._on_note_selection_changed)
        self.ui.versions_list.itemSelectionChanged.connect(
            self._on_version_selection_changed
        )
        self.ui.versions_list.itemDoubleClicked.connect(self._on_version_activated)
        self.ui.view_version_button.clicked.connect(self._view_selected_version)

        # === Background services ===
        self.autosave_manager.request_autosave.connect(
            lambda: self.logic.save_note(is_autosave=True)
        )

    def refresh_overview_panel(self, selected_note_id=None, selected_version_id=None):
        """Populate the overview panel with the current notes and versions."""

        notes = self.db_manager.get_all_notes()
        self.ui.note_count_label.setText(f"Notes: {len(notes)}")

        self.ui.notes_list.blockSignals(True)
        self.ui.notes_list.clear()
        target_note_item = None

        for note in notes:
            item = QListWidgetItem(note["name"])
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.ui.notes_list.addItem(item)
            if note["id"] == selected_note_id:
                target_note_item = item

        self.ui.notes_list.blockSignals(False)

        if target_note_item is None and self.ui.notes_list.count() > 0:
            target_note_item = self.ui.notes_list.item(0)

        if target_note_item is not None:
            self.ui.notes_list.setCurrentItem(target_note_item)
            self._populate_versions_for_note(target_note_item, selected_version_id)
        else:
            self._clear_versions_list()

    def _populate_versions_for_note(self, note_item, preselect_version_id=None):
        """Fill the versions list for the selected note."""

        if note_item is None:
            self._clear_versions_list()
            return

        note_id = note_item.data(Qt.ItemDataRole.UserRole)
        note_name = note_item.text()
        versions = self.db_manager.get_note_versions(note_id)

        self.ui.versions_list.blockSignals(True)
        self.ui.versions_list.clear()

        selected_item = None
        for version in versions:
            timestamp = datetime.fromisoformat(version["timestamp"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            item = QListWidgetItem(timestamp)
            item.setData(
                Qt.ItemDataRole.UserRole,
                {
                    "note_id": note_id,
                    "note_name": note_name,
                    "version_id": version["id"],
                    "timestamp": timestamp,
                },
            )
            self.ui.versions_list.addItem(item)
            if preselect_version_id and version["id"] == preselect_version_id:
                selected_item = item

        self.ui.versions_list.blockSignals(False)

        if selected_item is None and self.ui.versions_list.count() > 0:
            selected_item = self.ui.versions_list.item(0)

        if selected_item is not None:
            self.ui.versions_list.setCurrentItem(selected_item)

        self.ui.version_count_label.setText(
            f"Versions: {self.ui.versions_list.count()}"
        )
        self.ui.view_version_button.setEnabled(self.ui.versions_list.count() > 0)

    def _clear_versions_list(self):
        """Reset the versions list when no note is selected."""

        self.ui.versions_list.blockSignals(True)
        self.ui.versions_list.clear()
        self.ui.versions_list.blockSignals(False)
        self.ui.version_count_label.setText("Versions: 0")
        self.ui.view_version_button.setEnabled(False)

    def _on_note_selection_changed(self):
        """Handle switching between notes in the overview."""

        note_item = self.ui.notes_list.currentItem()
        self._populate_versions_for_note(note_item)

    def _on_version_selection_changed(self):
        """Update the view button when a version is highlighted."""

        has_selection = self.ui.versions_list.currentItem() is not None
        self.ui.view_version_button.setEnabled(has_selection)

    def _on_version_activated(self, item):
        """Open the requested note version on double click."""

        if item is not None:
            self._load_version_from_item(item)

    def _view_selected_version(self):
        """Open the version highlighted in the overview list."""

        item = self.ui.versions_list.currentItem()
        if item is not None:
            self._load_version_from_item(item)

    def _load_version_from_item(self, item):
        """Delegate loading a version to the editor logic."""

        data = item.data(Qt.ItemDataRole.UserRole) or {}
        note_id = data.get("note_id")
        version_id = data.get("version_id")
        note_name = data.get("note_name")
        timestamp = data.get("timestamp")

        if None in (note_id, version_id):
            return

        if self.logic.load_note_version(note_id, version_id, note_name, timestamp):
            self.refresh_overview_panel(note_id, version_id)

    def highlight_version(self, note_id, version_id):
        """Ensure the requested note/version pair is highlighted."""

        self.refresh_overview_panel(note_id, version_id)

    def closeEvent(self, event):
        """Stop background tasks and close database connections."""

        self.autosave_manager.stop()
        self.db_manager.close()
        super().closeEvent(event)
