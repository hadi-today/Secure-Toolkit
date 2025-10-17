import sys
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QListWidget, QLabel, 
    QTextEdit, QPushButton, QSplitter, QFrame, QAbstractItemView, QCompleter,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from .custom_widgets import DragDropArea

def setup_ui(main_window):
    # --- Main Layout ---
    main_window.main_layout = QHBoxLayout(main_window)
    main_window.splitter = QSplitter(Qt.Orientation.Horizontal)
    main_window.main_layout.addWidget(main_window.splitter)

    # --- Left Pane ---
    main_window.left_pane = QWidget()
    main_window.left_layout = QVBoxLayout(main_window.left_pane)
    main_window.splitter.addWidget(main_window.left_pane)

    # Search and Gallery Group
    gallery_group = QGroupBox("Archive")
    gallery_layout = QVBoxLayout(gallery_group)
    main_window.search_bar = QLineEdit()
    main_window.search_bar.setPlaceholderText("Search (e.g., #usa meeting white house)")
    gallery_layout.addWidget(main_window.search_bar)
    main_window.drag_drop_area = DragDropArea()
    gallery_layout.addWidget(main_window.drag_drop_area)
    main_window.gallery_list = QListWidget()
    main_window.gallery_list.setIconSize(main_window.THUMBNAIL_SIZE)
    main_window.gallery_list.setFlow(QListWidget.Flow.LeftToRight)
    main_window.gallery_list.setWrapping(True)
    main_window.gallery_list.setResizeMode(QListWidget.ResizeMode.Adjust)
    main_window.gallery_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    gallery_layout.addWidget(main_window.gallery_list)
    main_window.left_layout.addWidget(gallery_group)

    # Tag Pool Group
    tag_pool_group = QGroupBox("Tag Pool")
    tag_pool_layout = QVBoxLayout(tag_pool_group)
    main_window.tag_pool_list = QListWidget()
    main_window.tag_pool_list.setFlow(QListWidget.Flow.LeftToRight)
    main_window.tag_pool_list.setWrapping(True)
    tag_pool_layout.addWidget(main_window.tag_pool_list)
    main_window.left_layout.addWidget(tag_pool_group)

    # Settings Group
    settings_group = QGroupBox("Settings")
    settings_layout = QVBoxLayout(settings_group)
    
    # Platform-specific label for the editor command
    label_text = "External Editor Command:"
    if sys.platform == "darwin":  # macOS
        label_text += " (e.g., Adobe Photoshop 2024)"
    elif sys.platform == "win32":  # Windows
        label_text += " (e.g., photoshop.exe)"
    else:  # Linux
        label_text += " (e.g., gimp)"

    settings_layout.addWidget(QLabel(label_text))
    main_window.settings_editor_input = QLineEdit()
    settings_layout.addWidget(main_window.settings_editor_input)
    main_window.settings_save_button = QPushButton("Save Settings")
    settings_layout.addWidget(main_window.settings_save_button)
    main_window.left_layout.addWidget(settings_group)
    
    main_window.left_layout.setStretch(0, 3) # Gallery group takes more space
    main_window.left_layout.setStretch(1, 1) # Tag pool
    main_window.left_layout.setStretch(2, 0) # Settings group has fixed size


    # --- Right Pane (Details) ---
    main_window.right_pane = QWidget()
    main_window.right_layout = QVBoxLayout(main_window.right_pane)
    main_window.splitter.addWidget(main_window.right_pane)

    # Bulk Edit Panel
    main_window.bulk_edit_panel = QGroupBox("Bulk Edit Panel")
    main_window.bulk_edit_layout = QVBoxLayout(main_window.bulk_edit_panel)
    main_window.bulk_add_tags_input = QLineEdit()
    main_window.bulk_add_tags_input.setPlaceholderText("Add tags (comma-separated)...")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_add_tags_input)
    main_window.bulk_remove_tags_input = QLineEdit()
    main_window.bulk_remove_tags_input.setPlaceholderText("Remove tags (comma-separated)...")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_remove_tags_input)
    main_window.bulk_source_input = QLineEdit()
    main_window.bulk_source_input.setPlaceholderText("Set source text for all...")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_source_input)
    main_window.bulk_source_link_input = QLineEdit()
    main_window.bulk_source_link_input.setPlaceholderText("Set source link for all...")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_source_link_input)
    main_window.bulk_edit_layout.addWidget(QLabel("Set Description for all:"))
    main_window.bulk_description_input = QTextEdit()
    main_window.bulk_description_input.setMaximumHeight(100) # Prevent it from taking too much space
    main_window.bulk_edit_layout.addWidget(main_window.bulk_description_input)
    main_window.bulk_apply_button = QPushButton("Apply to Selected")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_apply_button)
    main_window.bulk_delete_button = QPushButton("Delete Selected Items")
    main_window.bulk_delete_button.setStyleSheet("background-color: #ff4757; color: white;")
    main_window.bulk_edit_layout.addWidget(main_window.bulk_delete_button)
    main_window.right_layout.addWidget(main_window.bulk_edit_panel)
    main_window.bulk_edit_panel.setVisible(False)

    # Single Item Details Panel
    main_window.details_panel = QGroupBox("Details")
    main_window.details_layout = QVBoxLayout(main_window.details_panel)
    main_window.image_preview = QLabel("Select an image to see details")
    main_window.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.image_preview.setMinimumSize(400, 300)
    main_window.image_preview.setFrameShape(QFrame.Shape.StyledPanel)
    main_window.details_layout.addWidget(main_window.image_preview)
    view_button_layout = QHBoxLayout()
    main_window.view_original_button = QPushButton("View Original")
    main_window.view_framed_button = QPushButton("View Framed")
    main_window.add_framed_button = QPushButton("Add/Change Framed Version")
    view_button_layout.addWidget(main_window.view_original_button)
    view_button_layout.addWidget(main_window.view_framed_button)
    view_button_layout.addWidget(main_window.add_framed_button)
    main_window.details_layout.addLayout(view_button_layout)
    main_window.details_layout.addWidget(QLabel("Description:"))
    main_window.desc_input = QTextEdit()
    main_window.details_layout.addWidget(main_window.desc_input)
    main_window.details_layout.addWidget(QLabel("Tags (comma-separated):"))
    main_window.tags_input = QLineEdit()
    main_window.tag_completer = QCompleter([])
    main_window.tag_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    main_window.tags_input.setCompleter(main_window.tag_completer)
    main_window.details_layout.addWidget(main_window.tags_input)
    main_window.details_layout.addWidget(QLabel("Source Text:"))
    main_window.source_text_input = QLineEdit()
    main_window.details_layout.addWidget(main_window.source_text_input)
    main_window.details_layout.addWidget(QLabel("Source Link:"))
    main_window.source_link_input = QLineEdit()
    main_window.details_layout.addWidget(main_window.source_link_input)
    
    # Action buttons
    actions_layout = QHBoxLayout()
    main_window.export_button = QPushButton("Export...")
    main_window.open_editor_button = QPushButton("Open with External Editor...")
    main_window.delete_button = QPushButton("Delete")
    main_window.delete_button.setStyleSheet("background-color: #ff4757; color: white;") # Make it stand out
    main_window.save_button = QPushButton("Save Changes")
    actions_layout.addWidget(main_window.export_button)
    actions_layout.addWidget(main_window.open_editor_button)
    actions_layout.addStretch()
    actions_layout.addWidget(main_window.delete_button)
    actions_layout.addWidget(main_window.save_button)
    main_window.details_layout.addLayout(actions_layout)

    main_window.right_layout.addWidget(main_window.details_panel)
    main_window.details_panel.setVisible(False)

    main_window.splitter.setSizes([700, 500])