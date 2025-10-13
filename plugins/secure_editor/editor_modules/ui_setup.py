#  plugins/secure_editor/editor_modules/ui_setup.py

from PyQt6.QtWidgets import (QTextEdit, QToolBar, QStatusBar, QWidget, QLabel, 
                             QPushButton, QHBoxLayout, QFontComboBox, QComboBox, 
                             QStackedWidget, QPlainTextEdit, QVBoxLayout)
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtCore import QSize, Qt, pyqtSignal, QUrl

class ClickableTextEdit(QTextEdit):
    linkClicked = pyqtSignal(QUrl)

    def __init__(self, parent=None):
        super().__init__(parent)
    
    def mouseReleaseEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor:
            self.linkClicked.emit(QUrl(anchor))
        else:
            super().mouseReleaseEvent(event)

class MainWindowUI:
    def setup_ui(self, main_widget: QWidget):
        main_widget.setWindowTitle("Secure HTML Editor")
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(20, 20))
        layout.addWidget(self.toolbar)

        self.save_action = QAction(QIcon.fromTheme("document-save"), "Save", main_widget)
        self.load_action = QAction(QIcon.fromTheme("document-open"), "Load", main_widget)
        self.manage_action = QAction(QIcon.fromTheme("document-properties"), "Manage Notes", main_widget)
        self.search_action = QAction(QIcon.fromTheme("edit-find"), "Search", main_widget)
        
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.load_action)
        self.toolbar.addAction(self.manage_action)
        self.toolbar.addAction(self.search_action)
        self.toolbar.addSeparator()

        self.toggle_view_button = QPushButton("Show Code")
        self.toggle_view_button.setCheckable(True)
        self.toolbar.addWidget(self.toggle_view_button)

        self.format_toolbar = QToolBar("Format Toolbar")
        self.format_toolbar.setIconSize(QSize(18, 18))
        layout.addWidget(self.format_toolbar)
        self.font_combo = QFontComboBox()
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems([str(s) for s in [8, 9, 10, 12, 14, 18, 24, 32, 48]])
        self.format_toolbar.addWidget(self.font_combo); self.format_toolbar.addWidget(self.font_size_combo)
        self.format_toolbar.addSeparator()
        self.bold_action = QAction(QIcon.fromTheme("format-text-bold"), "Bold", main_widget); self.bold_action.setCheckable(True)
        self.italic_action = QAction(QIcon.fromTheme("format-text-italic"), "Italic", main_widget); self.italic_action.setCheckable(True)
        self.underline_action = QAction(QIcon.fromTheme("format-text-underline"), "Underline", main_widget); self.underline_action.setCheckable(True)
        self.format_toolbar.addAction(self.bold_action); self.format_toolbar.addAction(self.italic_action); self.format_toolbar.addAction(self.underline_action)
        self.format_toolbar.addSeparator()
        self.align_left_action = QAction(QIcon.fromTheme("format-justify-left"), "Align Left", main_widget)
        self.align_center_action = QAction(QIcon.fromTheme("format-justify-center"), "Align Center", main_widget)
        self.align_right_action = QAction(QIcon.fromTheme("format-justify-right"), "Align Right", main_widget)
        self.format_toolbar.addAction(self.align_left_action); self.format_toolbar.addAction(self.align_center_action); self.format_toolbar.addAction(self.align_right_action)
        self.format_toolbar.addSeparator()
        self.ltr_action = QAction(QIcon.fromTheme("format-text-direction-ltr"), "Left to Right", main_widget)
        self.rtl_action = QAction(QIcon.fromTheme("format-text-direction-rtl"), "Right to Left", main_widget)
        self.format_toolbar.addAction(self.ltr_action); self.format_toolbar.addAction(self.rtl_action)
        self.format_toolbar.addSeparator()
        self.bullet_list_action = QAction(QIcon.fromTheme("format-list-bulleted"), "Bulleted List", main_widget)
        self.numbered_list_action = QAction(QIcon.fromTheme("format-list-numbered"), "Numbered List", main_widget)
        self.format_toolbar.addAction(self.bullet_list_action); self.format_toolbar.addAction(self.numbered_list_action)
        self.format_toolbar.addSeparator()
        self.link_action = QAction(QIcon.fromTheme("insert-link"), "Insert Link", main_widget)
        self.image_action = QAction(QIcon.fromTheme("insert-image"), "Insert Image", main_widget)
        self.file_action = QAction(QIcon.fromTheme("document-attach"), "Attach File", main_widget)
        self.format_toolbar.addAction(self.link_action); self.format_toolbar.addAction(self.image_action); self.format_toolbar.addAction(self.file_action)
        self.editor_stack = QStackedWidget()
        layout.addWidget(self.editor_stack)
        self.text_edit = ClickableTextEdit()
        self.text_edit.setAcceptRichText(True)      
        self.code_edit = QPlainTextEdit()
        code_font = QFont("Courier", 11)
        self.code_edit.setFont(code_font)
        self.editor_stack.addWidget(self.text_edit)
        self.editor_stack.addWidget(self.code_edit)
        bottom_bar_widget = QWidget()
        bottom_bar_layout = QHBoxLayout(bottom_bar_widget)
        bottom_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.export_pdf_button = QPushButton("Export PDF")
        self.export_word_button = QPushButton("Export Word")
        self.theme_button = QPushButton("Toggle Theme")
        bottom_bar_layout.addWidget(self.export_pdf_button); bottom_bar_layout.addWidget(self.export_word_button); bottom_bar_layout.addWidget(self.theme_button)
        bottom_bar_layout.addStretch()
        self.word_count_label = QLabel("Words: 0")
        bottom_bar_layout.addWidget(self.word_count_label)
        layout.addWidget(bottom_bar_widget)
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        main_widget.setLayout(layout)