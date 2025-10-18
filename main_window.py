import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QMenuBar,
    QApplication,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from about_dialog import AboutDialog
from plugin_loader import discover_manifests, load_plugin_class, run_status_check
from plugin_ui import add_plugin_entry, set_status_indicator

PLUGINS_DIR = 'plugins'


class MainWindow(QWidget):
    def __init__(self, keyring_data, save_keyring_callback):
        super().__init__()
        self.keyring_data = keyring_data
        self.save_keyring_callback = save_keyring_callback
        self.background_services = {}
        self.active_plugins = []
        self.status_plugins = {}
        self.setWindowTitle('Security Toolkit')
        self.setGeometry(150, 150, 1180, 760)
        self.setMinimumSize(1080, 680)
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        print(f"[*] Attempting to load icon from path: {icon_path}")
        print(f"[*] Does the icon file exist at this path? {os.path.exists(icon_path)}")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(18)
        self._create_menu_bar()
        self.content_widget = QWidget()
        self.content_widget.setObjectName('ContentCard')
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(18)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setContentsMargins(32, 24, 32, 24)
        self.content_layout.setSpacing(20)
        title = QLabel('Available Tools:')
        title.setStyleSheet(
            'font-size: 24px; font-weight: 600; margin-bottom: 8px; letter-spacing: 0.3px;'
        )
        self.content_layout.addWidget(title)

        subtitle = QLabel('Choose a plugin card below to launch the desired toolkit feature.')
        subtitle.setStyleSheet('font-size: 14px; color: #9ca3af; margin-bottom: 16px;')
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)
        self.main_layout.addWidget(self.content_widget)
        self.plugin_grid_widget = QWidget(self.content_widget)
        self.plugin_grid_layout = QGridLayout(self.plugin_grid_widget)
        self.plugin_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.plugin_grid_layout.setHorizontalSpacing(18)
        self.plugin_grid_layout.setVerticalSpacing(18)
        self.plugin_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.addWidget(self.plugin_grid_widget)
        self.plugin_grid_columns = 3
        for column in range(self.plugin_grid_columns):
            self.plugin_grid_layout.setColumnStretch(column, 1)
        self._load_plugins()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_all_statuses)
        self.status_timer.start(5000)

    def _create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.main_layout.addWidget(menu_bar)
        file_menu = menu_bar.addMenu('&File')
        quit_action = QAction('&Quit', self)
        quit_action.triggered.connect(self._quit_application)
        file_menu.addAction(quit_action)
        help_menu = menu_bar.addMenu('&Help')
        about_action = QAction('&About...', self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _quit_application(self):
        app = QApplication.instance()
        if app:
            app.quit()

    def _show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def _load_plugins(self):
        for index, (plugin_folder_name, manifest) in enumerate(
            discover_manifests(PLUGINS_DIR)
        ):
            add_plugin_entry(
                self.plugin_grid_layout,
                self.status_plugins,
                manifest,
                plugin_folder_name,
                self.launch_plugin,
                index,
                self.plugin_grid_columns,
            )

    def update_all_statuses(self):
        for name, data in self.status_plugins.items():
            try:
                manifest = data['manifest']
                indicator = data['indicator']
                is_ok = run_status_check(PLUGINS_DIR, name, manifest)
                set_status_indicator(indicator, is_ok)
            except Exception as error:
                print(f"Failed to update status for '{name}': {error}")
                indicator = data['indicator']
                indicator.setStyleSheet('background-color: grey; border-radius: 7px;')

    def closeEvent(self, event):
        print('Main window closing. Stopping all background services...')
        for service_name, service_data in self.background_services.items():
            worker = service_data.get('worker')
            thread = service_data.get('thread')
            if worker and hasattr(worker, 'stop'):
                print(f"Stopping service: {service_name}...")
                worker.stop()
                if thread:
                    thread.quit()
                    thread.wait()
                print(f"Service {service_name} stopped.")
        super().closeEvent(event)

    def launch_plugin(self, manifest, plugin_folder_name):
        try:
            plugin_class = load_plugin_class(PLUGINS_DIR, plugin_folder_name, manifest)
            plugin_instance = self._create_plugin_instance(plugin_class)
            self.active_plugins.append(plugin_instance)
            plugin_instance.show()
        except Exception as error:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self,
                'Plugin Launch Error',
                f"Failed to launch plugin '{manifest.get('name')}'.\n\nError: {error}",
            )

    def _create_plugin_instance(self, plugin_class):
        """Instantiate a plugin, gracefully handling older constructor signatures."""

        try:
            return plugin_class(self.keyring_data, self.save_keyring_callback, self)
        except TypeError as error:
            message = str(error)
            if 'positional argument' not in message and 'unexpected keyword' not in message:
                raise

        try:
            return plugin_class(self.keyring_data, self.save_keyring_callback)
        except TypeError as error:
            message = str(error)
            if 'positional argument' not in message and 'unexpected keyword' not in message:
                raise

        return plugin_class(self.keyring_data)
