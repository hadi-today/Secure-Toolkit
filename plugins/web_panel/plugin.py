# plugins/web_panel/plugin.py

import sys
import os
import subprocess
import json
import base64
from urllib.parse import quote_plus
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QMessageBox, QComboBox, 
                             QLineEdit, QPushButton, QLabel, QTextEdit)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from auth import CONFIG_FILE, ITERATIONS


from auth import CONFIG_FILE

from .ui_builder import (create_settings_group, create_control_group, 
                         create_log_group, populate_ip_addresses)

class LogReader(QThread):
    new_log = pyqtSignal(str)
    def __init__(self, process_stdout):
        super().__init__()
        self.stdout = process_stdout
    def run(self):
        for line in iter(self.stdout.readline, ''):
            self.new_log.emit(line.strip())
        self.stdout.close()

class WebPanelWidget(QWidget):
    def __init__(self, keyring_data, save_callback, main_window):
        super().__init__()
        self.main_window = main_window
        self.service_name = "web_panel_server"
        self.log_reader_thread = None
        self.ip_combo = QComboBox()
        self.port_input = QLineEdit("8080")
        self.start_stop_button = QPushButton("Start Server")
        self.status_label = QLabel("Status: Stopped")
        self.log_output = QTextEdit()
        self.setWindowTitle("Web Panel Management")
        self.init_ui()
        self.sync_ui_with_service_state()

    def init_ui(self):
        layout = QVBoxLayout(self)
        populate_ip_addresses(self.ip_combo)
        self.log_output.setReadOnly(True)
        self.status_label.setStyleSheet("color: red;")
        settings_group = create_settings_group(self.ip_combo, self.port_input)
        control_group = create_control_group(self.start_stop_button, self.status_label)
        log_group = create_log_group(self.log_output)
        layout.addWidget(settings_group)
        layout.addWidget(control_group)
        layout.addWidget(log_group)
        self.start_stop_button.clicked.connect(self.toggle_server)

    def is_service_running(self):
        service = self.main_window.background_services.get(self.service_name)
        return service and service['process'].poll() is None

    def sync_ui_with_service_state(self):
        if self.is_service_running():
            process = self.main_window.background_services[self.service_name]['process']
            host, port = process.args[2], process.args[3]
            self.update_ui_for_server_start(host, port)
        else:
            self.update_ui_for_server_stop()

    def toggle_server(self):
        if self.is_service_running():
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        host = self.ip_combo.currentText().split(' ')[0]
        port = self.port_input.text()
        
        try:
            with open(CONFIG_FILE, 'r') as f: config = json.load(f)
            password_hash_b64 = config['password_hash']
            salt_b64 = config['salt']
            print("\n--- DEBUG: Data Sent from plugin.py ---")
            print(f"HASH: {password_hash_b64}")
            print(f"SALT: {salt_b64}")
            print("--------------------------------------\n")
        except (IOError, KeyError) as e:
            QMessageBox.critical(self, "Config Error", f"Could not read auth data: {e}")
            return
        safe_hash = quote_plus(password_hash_b64)
        safe_salt = quote_plus(salt_b64)
        KEY_LENGTH = 32
        runner_script = os.path.join(os.path.dirname(__file__), "server_runner.py")

        command = [
            sys.executable, 
            runner_script, 
            host, 
            port, 
            safe_hash, 
            safe_salt,
            str(ITERATIONS), 
            str(KEY_LENGTH)  
        ]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        self.main_window.background_services[self.service_name] = {'process': process}
        
        self.log_reader_thread = LogReader(process.stdout)
        self.log_reader_thread.new_log.connect(self.log_output.append)
        self.log_reader_thread.start()
        
        self.update_ui_for_server_start(host, port)

    def stop_server(self):
        if self.is_service_running():
            self.log_output.append("Terminating server process...")
            process = self.main_window.background_services[self.service_name]['process']
            process.terminate()
            process.wait()
            self.main_window.background_services.pop(self.service_name, None)
            if self.log_reader_thread: self.log_reader_thread.wait()
            self.update_ui_for_server_stop()
    
    def update_ui_for_server_start(self, host, port):
        self.start_stop_button.setText("Stop Server")
        self.status_label.setText(f"Status: Running on {host}:{port}")
        self.status_label.setStyleSheet("color: green;")
        index = self.ip_combo.findText(host, Qt.MatchFlag.MatchContains)
        if index >= 0: self.ip_combo.setCurrentIndex(index)
        self.port_input.setText(str(port))
        self.ip_combo.setEnabled(False)
        self.port_input.setEnabled(False)
        
    def update_ui_for_server_stop(self):
        self.start_stop_button.setText("Start Server")
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("color: red;")
        self.ip_combo.setEnabled(True)
        self.port_input.setEnabled(True)