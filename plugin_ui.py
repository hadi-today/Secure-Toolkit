from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel


def add_plugin_entry(content_layout, status_plugins, manifest, plugin_folder_name, launch_callback):
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    status_check_info = manifest.get('status_check')
    if status_check_info and status_check_info.get('enabled'):
        status_indicator = QLabel()
        status_indicator.setFixedSize(16, 16)
        status_indicator.setStyleSheet('background-color: grey; border-radius: 8px;')
        layout.addWidget(status_indicator)
        status_plugins[plugin_folder_name] = {
            'indicator': status_indicator,
            'manifest': manifest,
        }
    button = QPushButton(manifest.get('button_text', 'Unnamed Plugin'))
    button.setToolTip(manifest.get('description', ''))
    button.setStyleSheet(
        'QPushButton { font-size: 14px; padding-top: 5px; padding-bottom: 5px; padding-left: 10px; padding-right: 10px; text-align: left; }'
    )
    button.clicked.connect(lambda _, name=plugin_folder_name: launch_callback(manifest, name))
    layout.addWidget(button)
    content_layout.addWidget(container)


def set_status_indicator(indicator, is_ok):
    color = 'green' if is_ok else 'red'
    indicator.setStyleSheet(f'background-color: {color}; border-radius: 8px;')