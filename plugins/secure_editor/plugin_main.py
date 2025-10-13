# plugins/secure_editor/plugin_main.py

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt      
from PyQt6.QtGui import QFont    

from .editor_modules.database_manager import DatabaseManager
from .editor_modules.editor_logic import EditorLogic
from .editor_modules.ui_setup import MainWindowUI
from .editor_modules.autosave import AutoSaver

class SecureEditorWidget(QWidget):
    def __init__(self, keyring_data, save_callback):
        super().__init__()
        
        self.ui = MainWindowUI()
        self.ui.setup_ui(self)
        
        self.db_manager = DatabaseManager()
        self.logic = EditorLogic(self, self.ui, self.db_manager, keyring_data)
        self.autosave_manager = AutoSaver(self)

        self._connect_signals()
        
        self.ui.status_bar.showMessage("Ready. Load or create a new note to begin.")


    def _connect_signals(self):
        self.ui.save_action.triggered.connect(self.logic.save_note)
        self.ui.load_action.triggered.connect(self.logic.load_note) 
        self.ui.manage_action.triggered.connect(self.logic.manage_notes)
        self.ui.search_action.triggered.connect(self.logic.search_notes)
        self.ui.toggle_view_button.clicked.connect(self.logic.toggle_editor_view)
        

        self.ui.text_edit.textChanged.connect(self.logic.on_text_changed)
        self.ui.text_edit.textChanged.connect(self.autosave_manager.on_activity)
        self.ui.text_edit.cursorPositionChanged.connect(self.logic._update_format_toolbar)
        self.ui.text_edit.linkClicked.connect(self.logic.handle_link_clicked)
        
        self.ui.code_edit.textChanged.connect(self.logic.on_code_changed)

        self.ui.font_combo.currentFontChanged.connect(self.ui.text_edit.setCurrentFont)
        self.ui.font_size_combo.currentTextChanged.connect(lambda size: self.ui.text_edit.setFontPointSize(float(size)))
        self.ui.bold_action.triggered.connect(lambda checked: self.ui.text_edit.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal))
        self.ui.italic_action.triggered.connect(self.ui.text_edit.setFontItalic)
        self.ui.underline_action.triggered.connect(self.ui.text_edit.setFontUnderline)
        self.ui.align_left_action.triggered.connect(lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.ui.align_center_action.triggered.connect(lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.ui.align_right_action.triggered.connect(lambda: self.ui.text_edit.setAlignment(Qt.AlignmentFlag.AlignRight))
        self.ui.ltr_action.triggered.connect(lambda: self.logic.set_text_direction(Qt.LayoutDirection.LeftToRight))
        self.ui.rtl_action.triggered.connect(lambda: self.logic.set_text_direction(Qt.LayoutDirection.RightToLeft))
        self.ui.bullet_list_action.triggered.connect(lambda: self.logic.create_list('bullet'))
        self.ui.numbered_list_action.triggered.connect(lambda: self.logic.create_list('numbered'))
        self.ui.link_action.triggered.connect(self.logic.insert_link)
        self.ui.image_action.triggered.connect(self.logic.insert_image)
        self.ui.file_action.triggered.connect(self.logic.insert_file)
        
        self.ui.export_pdf_button.clicked.connect(self.logic.export_to_pdf)
        self.ui.export_word_button.clicked.connect(self.logic.export_to_word)
        self.ui.theme_button.clicked.connect(self.logic.toggle_theme)

        self.autosave_manager.request_autosave.connect(
            lambda: self.logic.save_note(is_autosave=True)
        )
    def closeEvent(self, event):
        print("[Main] Stopping tasks and closing connections.")
        self.autosave_manager.stop()
        self.db_manager.close()
        super().closeEvent(event)