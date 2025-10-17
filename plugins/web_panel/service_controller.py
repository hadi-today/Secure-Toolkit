"""Helpers that launch and supervise the background web panel service.

The plugin keeps the server in a separate Python process so the Qt event loop
remains responsive.  This module abstracts the bookkeeping required to start
that worker, stream its logs back into the UI, and terminate it cleanly.
"""

import json
import os
import subprocess
import sys
from urllib.parse import quote_plus

from PyQt6.QtCore import QThread, pyqtSignal

from auth import CONFIG_FILE, ITERATIONS, KEY_LENGTH


class ServiceStartError(Exception):
    """Raised when the service cannot be launched due to configuration issues."""


class LogReader(QThread):
    """Background thread that streams server stdout to the Qt text widget."""

    new_log = pyqtSignal(str)

    def __init__(self, process_stdout):
        super().__init__()
        # ``process_stdout`` is a file-like object obtained from Popen.  We keep
        # it around so ``run`` can iterate over the bytes as they arrive and
        # forward them to any connected slots.
        self.stdout = process_stdout

    def run(self):
        """Continuously forward stdout lines until the process terminates."""

        for line in iter(self.stdout.readline, ''):
            if not line:
                break
            self.new_log.emit(line.strip())
        self.stdout.close()


class WebPanelServiceController:
    """Facade that manages the lifecycle of the web panel worker process."""

    def __init__(self, main_window, service_name='web_panel_server'):
        # ``main_window`` exposes the ``background_services`` registry that all
        # plugins share.  It allows the controller to coordinate process state
        # with the rest of the application.
        self.main_window = main_window
        self.service_name = service_name
        self.log_reader = None

    def is_running(self):
        """Return ``True`` when the worker process exists and is alive."""

        service = self.main_window.background_services.get(self.service_name)
        return bool(service and service['process'].poll() is None)

    def current_endpoint(self):
        """Return the ``(host, port)`` pair when a server process is active."""

        if not self.is_running():
            return None, None
        process = self.main_window.background_services[self.service_name]['process']
        return process.args[2], process.args[3]

    def start(self, host, port, log_callback):
        """Launch the worker process and attach a log streaming callback."""

        password_hash_b64, salt_b64 = self._load_auth_config()
        process = self._spawn_process(host, port, password_hash_b64, salt_b64)

        self.main_window.background_services[self.service_name] = {'process': process}

        self.log_reader = LogReader(process.stdout)
        self.log_reader.new_log.connect(log_callback)
        self.log_reader.start()

        return host, port

    def stop(self):
        """Terminate the worker process and clean up the log reader thread."""

        if not self.is_running():
            return

        process = self.main_window.background_services[self.service_name]['process']
        process.terminate()
        process.wait()
        self.main_window.background_services.pop(self.service_name, None)

        if self.log_reader:
            self.log_reader.wait()
            self.log_reader = None

    def _load_auth_config(self):
        """Fetch hashed credential data that the web server expects."""

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
            return config['password_hash'], config['salt']
        except (IOError, KeyError, json.JSONDecodeError) as error:
            raise ServiceStartError(f'Could not read auth data: {error}') from error

    def _spawn_process(self, host, port, password_hash_b64, salt_b64):
        """Create the ``subprocess.Popen`` instance that runs the Flask app."""

        runner_script = os.path.join(os.path.dirname(__file__), 'server_runner.py')
        safe_hash = quote_plus(password_hash_b64)
        safe_salt = quote_plus(salt_b64)

        command = [
            sys.executable,
            runner_script,
            host,
            port,
            safe_hash,
            safe_salt,
            str(ITERATIONS),
            str(KEY_LENGTH),
        ]

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,  # capture stdout so it can be displayed
            stderr=subprocess.STDOUT,  # merge stderr into stdout for simplicity
            text=True,
            creationflags=creation_flags,
        )
