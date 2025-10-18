from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
)


def add_plugin_entry(
    grid_layout,
    status_plugins,
    manifest,
    plugin_folder_name,
    launch_callback,
    index,
    columns,
):
    card = QWidget()
    card.setObjectName('pluginCard')
    card.setMinimumWidth(240)
    card.setMaximumWidth(320)
    card.setStyleSheet(
        (
            "#pluginCard {"
            "    background-color: #111827;"
            "    border: 1px solid #1f2937;"
            "    border-radius: 12px;"
            "}"
        )
    )

    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(18, 18, 18, 18)
    card_layout.setSpacing(12)

    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(12)

    status_indicator = None
    status_check_info = manifest.get('status_check')
    if status_check_info and status_check_info.get('enabled'):
        status_indicator = QLabel()
        status_indicator.setFixedSize(14, 14)
        status_indicator.setStyleSheet('background-color: grey; border-radius: 7px;')
        header_layout.addWidget(status_indicator, alignment=Qt.AlignmentFlag.AlignTop)
        status_plugins[plugin_folder_name] = {
            'indicator': status_indicator,
            'manifest': manifest,
        }

    name_label = QLabel(manifest.get('name', 'Unnamed Plugin'))
    name_label.setStyleSheet('font-size: 16px; font-weight: 600; color: #e5e7eb;')
    header_layout.addWidget(name_label)
    header_layout.addStretch()
    card_layout.addLayout(header_layout)

    description = manifest.get('description', '')
    if description:
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet('color: #9ca3af; font-size: 12px; line-height: 1.4;')
        card_layout.addWidget(description_label)

    button = QPushButton(manifest.get('button_text', 'Launch'))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(30)
    button.setStyleSheet(
        (
            "QPushButton {"
            "    background-color: #2563eb;"
            "    color: white;"
            "    border-radius: 8px;"
            "    font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
    )
    button.clicked.connect(
        lambda _, name=plugin_folder_name: launch_callback(manifest, name)
    )
    card_layout.addStretch()
    card_layout.addWidget(button)

    row = index // max(columns, 1)
    column = index % max(columns, 1)
    grid_layout.addWidget(card, row, column)


def set_status_indicator(indicator, is_ok):
    color = 'green' if is_ok else 'red'
    indicator.setStyleSheet(f'background-color: {color}; border-radius: 7px;')
