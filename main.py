import sys
import os
import json
import importlib
import base64
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QMessageBox, QMenuBar, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
from auth import (LoginWindow, SetupWindow, CONFIG_FILE, derive_keyring_key, 
                  load_and_decrypt_keyring, encrypt_and_save_keyring, KEYRING_FILE)

PLUGINS_DIR = "plugins"
APP_DIR = os.path.dirname(os.path.abspath(__file__)) 

# ---"About" ---
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Secure Toolkit")
        self.setFixedSize(350, 220)
        layout = QVBoxLayout(self)       
        title_label = QLabel("Secure Toolkit")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label = QLabel("Version 1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label = QLabel("A modular toolkit for cryptographic operations.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        link_label = QLabel()
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setOpenExternalLinks(True)
        link_label.setText('<a href="https://hadi.ge">hadi.ge</a>')      
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addStretch()
        layout.addWidget(desc_label)
        layout.addWidget(link_label)
        layout.addStretch()
        layout.addWidget(close_button)

class MainWindow(QWidget):
    def __init__(self, keyring_data, save_keyring_callback):
        super().__init__()
        self.keyring_data = keyring_data
        self.save_keyring_callback = save_keyring_callback
        self.setWindowTitle("Security Toolkit")
        self.setGeometry(300, 300, 400, 350)
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        print(f"[*] Attempting to load icon from path: {icon_path}")
        print(f"[*] Does the icon file exist at this path? {os.path.exists(icon_path)}")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.active_plugins = []
        self.status_plugins = {} 
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self._create_menu_bar()
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop) 
        title = QLabel("Available Tools:")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        content_layout.addWidget(title)
        self.main_layout.addWidget(content_widget)
        self.content_layout = content_layout
        self.discover_and_load_plugins()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_all_statuses)
        self.status_timer.start(5000)
    def _create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.main_layout.addWidget(menu_bar)
        file_menu = menu_bar.addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About...", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
    def _show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()
    def discover_and_load_plugins(self):
        if not os.path.isdir(PLUGINS_DIR): return
        for plugin_folder_name in os.listdir(PLUGINS_DIR):
            plugin_path = os.path.join(PLUGINS_DIR, plugin_folder_name)
            manifest_path = os.path.join(plugin_path, "manifest.json")
            if os.path.isdir(plugin_path) and os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    self.create_plugin_entry(manifest, plugin_folder_name)
                except Exception as e:
                    print(f"Could not load plugin '{plugin_folder_name}': {e}")   
    def create_plugin_entry(self, manifest, plugin_folder_name):
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        status_check_info = manifest.get("status_check")
        if status_check_info and status_check_info.get("enabled"):
            status_indicator = QLabel()
            status_indicator.setFixedSize(16, 16)
            status_indicator.setStyleSheet("background-color: grey; border-radius: 8px;")
            h_layout.addWidget(status_indicator)
            self.status_plugins[plugin_folder_name] = {"indicator": status_indicator, "manifest": manifest}       
        button = QPushButton(manifest.get("button_text", "Unnamed Plugin"))
        button.setToolTip(manifest.get("description", ""))
        button.setStyleSheet("""QPushButton { font-size: 14px; padding-top: 5px; padding-bottom: 5px; padding-left: 10px; padding-right: 10px; text-align: left; }""")
        button.clicked.connect(lambda ch, name=plugin_folder_name: self.launch_plugin(manifest, name))
        h_layout.addWidget(button)
        self.content_layout.addWidget(container)
    def update_all_statuses(self):
        for name, data in self.status_plugins.items():
            try:
                manifest = data["manifest"]; indicator = data["indicator"]
                module_path = f"{PLUGINS_DIR}.{name}.{manifest['module']}"
                plugin_module = importlib.import_module(module_path)
                status_func_name = manifest["status_check"]["function_name"]
                status_function = getattr(plugin_module, status_func_name)
                is_ok = status_function()
                color = "green" if is_ok else "red"
                indicator.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
            except Exception as e:
                print(f"Failed to update status for '{name}': {e}")
                data["indicator"].setStyleSheet("background-color: grey; border-radius: 8px;")


    def launch_plugin(self, manifest, plugin_folder_name):
        try:
            module_name = f"{PLUGINS_DIR}.{plugin_folder_name}.{manifest['module']}"
            class_name = manifest['entry_point']
            plugin_module = importlib.import_module(module_name)
            PluginWidget = getattr(plugin_module, class_name)
            
            plugin_instance = PluginWidget(self.keyring_data, self.save_keyring_callback)
            
            self.active_plugins.append(plugin_instance)
            plugin_instance.show()
        except Exception as e:
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "Plugin Launch Error", f"Failed to launch plugin '{manifest.get('name')}'.\n\nError: {e}")
class ApplicationController:
    def __init__(self):
        self.main_window = None; self.auth_window = None
        self.keyring_data = None; self.keyring_encryption_key = None

    def start(self):
        if os.path.exists(CONFIG_FILE):
            self.auth_window = LoginWindow()
            self.auth_window.login_successful.connect(self._handle_successful_login)
        else:
            self.auth_window = SetupWindow()
            self.auth_window.setup_successful.connect(self._handle_successful_login)
        self.auth_window.show()

    def _handle_successful_login(self, password):
        try:
            with open(CONFIG_FILE, 'r') as f: config = json.load(f)
            if 'keyring_salt' not in config:
                QMessageBox.critical(None, "Config Error", "Configuration file is outdated. Please delete 'config.json' and restart.")
                sys.exit(1)
            keyring_salt = base64.b64decode(config['keyring_salt'])
            self.keyring_encryption_key = derive_keyring_key(password, keyring_salt)
            keyring_needs_initialization = not os.path.exists(KEYRING_FILE)
            self.keyring_data = load_and_decrypt_keyring(self.keyring_encryption_key)
            if keyring_needs_initialization:
                print("First run: Initializing secure keyring file.")
                self.save_keyring_data(self.keyring_data)
            if self.auth_window: self.auth_window.close()
            self.show_main_window()
        except Exception as e:
            import traceback; traceback.print_exc()
            QMessageBox.critical(None, "Fatal Error", f"Could not load secure data: {e}\n\nThe application will now exit.")
            sys.exit(1)

    def save_keyring_data(self, new_data):
        self.keyring_data = new_data
        try:
            encrypt_and_save_keyring(self.keyring_encryption_key, self.keyring_data)
            print("Keyring securely saved to disk.")
        except Exception as e:
            QMessageBox.critical(None, "Save Error", f"Could not save keyring data securely: {e}")

    def show_main_window(self):
        if self.main_window is None:
            self.main_window = MainWindow(self.keyring_data, self.save_keyring_data)
        self.main_window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if sys.platform == "darwin": # "darwin" نام داخلی macOS است
        try:
            from AppKit import NSImage, NSApplication
            icon_path = os.path.join(APP_DIR, 'icon.png')
            if os.path.exists(icon_path):
                image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                NSApplication.sharedApplication().setApplicationIconImage_(image)
        except ImportError:
            print("[!] Warning: PyObjC is not installed. Dock icon cannot be set on macOS.")
        except Exception as e:
            print(f"[!] Error setting Dock icon on macOS: {e}")    
    controller = ApplicationController()
    controller.start()
    sys.exit(app.exec())