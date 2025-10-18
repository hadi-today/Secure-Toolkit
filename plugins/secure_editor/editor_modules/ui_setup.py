"""UI composition for the Secure Editor plugin."""

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QFontComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QStatusBar,
    QStackedWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class ClickableTextEdit(QTextEdit):
    """Text edit that exposes link-click events."""

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
    """Builds the editor surface and companion overview panel."""

    def setup_ui(self, main_widget: QWidget):
        main_widget.setWindowTitle("Secure HTML Editor")
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Primary toolbar ---
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(20, 20))
        layout.addWidget(self.toolbar)

        self.save_action = QAction(QIcon.fromTheme("document-save"), "Save", main_widget)
        self.load_action = QAction(QIcon.fromTheme("document-open"), "Load", main_widget)
        self.manage_action = QAction(
            QIcon.fromTheme("document-properties"), "Manage Notes", main_widget
        )
        self.search_action = QAction(QIcon.fromTheme("edit-find"), "Search", main_widget)

        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.load_action)
        self.toolbar.addAction(self.manage_action)
        self.toolbar.addAction(self.search_action)
        self.toolbar.addSeparator()

        self.toggle_view_button = QPushButton("Show Code")
        self.toggle_view_button.setCheckable(True)
        self.toolbar.addWidget(self.toggle_view_button)

        # --- Formatting toolbar ---
        self.format_toolbar = QToolBar("Format Toolbar")
        self.format_toolbar.setIconSize(QSize(18, 18))
        layout.addWidget(self.format_toolbar)

        self.font_combo = QFontComboBox()
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems([str(s) for s in [8, 9, 10, 12, 14, 18, 24, 32, 48]])
        self.format_toolbar.addWidget(self.font_combo)
        self.format_toolbar.addWidget(self.font_size_combo)
        self.format_toolbar.addSeparator()

        self.bold_action = QAction(QIcon.fromTheme("format-text-bold"), "Bold", main_widget)
        self.bold_action.setCheckable(True)
        self.italic_action = QAction(
            QIcon.fromTheme("format-text-italic"), "Italic", main_widget
        )
        self.italic_action.setCheckable(True)
        self.underline_action = QAction(
            QIcon.fromTheme("format-text-underline"), "Underline", main_widget
        )
        self.underline_action.setCheckable(True)
        self.format_toolbar.addAction(self.bold_action)
        self.format_toolbar.addAction(self.italic_action)
        self.format_toolbar.addAction(self.underline_action)
        self.format_toolbar.addSeparator()

        self.align_left_action = QAction(
            QIcon.fromTheme("format-justify-left"), "Align Left", main_widget
        )
        self.align_center_action = QAction(
            QIcon.fromTheme("format-justify-center"), "Align Center", main_widget
        )
        self.align_right_action = QAction(
            QIcon.fromTheme("format-justify-right"), "Align Right", main_widget
        )
        self.format_toolbar.addAction(self.align_left_action)
        self.format_toolbar.addAction(self.align_center_action)
        self.format_toolbar.addAction(self.align_right_action)
        self.format_toolbar.addSeparator()

        self.ltr_action = QAction(
            QIcon.fromTheme("format-text-direction-ltr"), "Left to Right", main_widget
        )
        self.rtl_action = QAction(
            QIcon.fromTheme("format-text-direction-rtl"), "Right to Left", main_widget
        )
        self.format_toolbar.addAction(self.ltr_action)
        self.format_toolbar.addAction(self.rtl_action)
        self.format_toolbar.addSeparator()

        self.bullet_list_action = QAction(
            QIcon.fromTheme("format-list-bulleted"), "Bulleted List", main_widget
        )
        self.numbered_list_action = QAction(
            QIcon.fromTheme("format-list-numbered"), "Numbered List", main_widget
        )
        self.format_toolbar.addAction(self.bullet_list_action)
        self.format_toolbar.addAction(self.numbered_list_action)
        self.format_toolbar.addSeparator()

        self.link_action = QAction(QIcon.fromTheme("insert-link"), "Insert Link", main_widget)
        self.image_action = QAction(QIcon.fromTheme("insert-image"), "Insert Image", main_widget)
        self.file_action = QAction(
            QIcon.fromTheme("document-attach"), "Attach File", main_widget
        )
        self.format_toolbar.addAction(self.link_action)
        self.format_toolbar.addAction(self.image_action)
        self.format_toolbar.addAction(self.file_action)

        # --- Main editor surface ---
        self.editor_stack = QStackedWidget()
        self.text_edit = ClickableTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.code_edit = QPlainTextEdit()
        code_font = QFont("Courier", 11)
        self.code_edit.setFont(code_font)
        self.editor_stack.addWidget(self.text_edit)
        self.editor_stack.addWidget(self.code_edit)

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(4)
        editor_layout.addWidget(self.editor_stack)

        bottom_bar_widget = QWidget()
        bottom_bar_layout = QHBoxLayout(bottom_bar_widget)
        bottom_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.export_pdf_button = QPushButton("Export PDF")
        self.export_word_button = QPushButton("Export Word")
        self.theme_button = QPushButton("Toggle Theme")
        bottom_bar_layout.addWidget(self.export_pdf_button)
        bottom_bar_layout.addWidget(self.export_word_button)
        bottom_bar_layout.addWidget(self.theme_button)
        bottom_bar_layout.addStretch()
        self.word_count_label = QLabel("Words: 0")
        bottom_bar_layout.addWidget(self.word_count_label)
        editor_layout.addWidget(bottom_bar_widget)

        overview_group = QGroupBox("Notes Overview")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(8, 8, 8, 8)
        overview_layout.setSpacing(6)

        self.note_count_label = QLabel("Notes: 0")
        self.version_count_label = QLabel("Versions: 0")
        overview_layout.addWidget(self.note_count_label)
        overview_layout.addWidget(self.version_count_label)

        self.notes_list = QListWidget()
        self.notes_list.setMinimumWidth(180)
        overview_layout.addWidget(self.notes_list, 1)

        self.versions_list = QListWidget()
        overview_layout.addWidget(self.versions_list, 1)

        self.view_version_button = QPushButton("Open Selected Version")
        self.view_version_button.setEnabled(False)
        overview_layout.addWidget(self.view_version_button)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(8, 4, 8, 4)
        content_layout.setSpacing(8)
        content_layout.addWidget(editor_container, 3)
        content_layout.addWidget(overview_group, 1)
        layout.addLayout(content_layout)

        # --- Status bar ---
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        main_widget.setLayout(layout)
