"""Helpers that launch and supervise the background web panel service.

The plugin keeps the server in a separate Python process so the Qt event loop
remains responsive.  This module abstracts the bookkeeping required to start
that worker, stream its logs back into the UI, and terminate it cleanly.
"""

import json
import os
import signal
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

    def force_kill_port(self, port):
        """Attempt to terminate any process currently bound to ``port``.

        Returns a tuple ``(terminated_pids, errors)`` so the caller can provide
        feedback to the user.  The helper first checks whether the bundled web
        panel service is occupying the port, then falls back to platform
        specific utilities for any remaining listeners.
        """

        terminated = []
        errors = []

        # Stop the managed worker first so we do not orphan the process entry.
        if self.is_running():
            process = self.main_window.background_services[self.service_name]['process']
            running_port = process.args[3]
            if str(running_port) == str(port):
                terminated.append(process.pid)
                self.stop()

        # Nothing else to do when the platform specific utilities are missing.
        try:
            extra_pids, extra_errors = self._terminate_external_processes(port)
            terminated.extend(extra_pids)
            errors.extend(extra_errors)
        except FileNotFoundError as error:
            errors.append(str(error))

        # Remove duplicates while preserving order for readability.
        seen = set()
        ordered = []
        for pid in terminated:
            if pid not in seen:
                seen.add(pid)
                ordered.append(pid)

        return ordered, errors

    def _terminate_external_processes(self, port):
        """Use OS tooling to kill any non-managed process on ``port``."""

        terminated = []
        errors = []

        if os.name == 'nt':
            result = subprocess.run(
                ['netstat', '-ano'], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                errors.append(result.stderr.strip() or 'netstat command failed')
                return terminated, errors

            seen = set()
            for line in result.stdout.splitlines():
                if f':{port} ' not in line:
                    continue
                parts = line.split()
                if not parts:
                    continue
                pid = parts[-1]
                if not pid.isdigit():
                    continue
                pid_int = int(pid)
                if pid_int in seen:
                    continue
                seen.add(pid_int)
                kill_result = subprocess.run(
                    ['taskkill', '/PID', pid, '/F', '/T'],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if kill_result.returncode == 0:
                    terminated.append(pid_int)
                else:
                    errors.append(
                        kill_result.stderr.strip()
                        or kill_result.stdout.strip()
                        or f'Failed to terminate PID {pid}'
                    )
            return terminated, errors

        # POSIX style systems – try lsof first for detailed PID listings.
        lsof_missing = False
        try:
            result = subprocess.run(
                ['lsof', '-t', f'-i:{port}'], capture_output=True, text=True, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                for pid_text in set(result.stdout.split()):
                    try:
                        pid = int(pid_text)
                    except ValueError:
                        continue
                    try:
                        os.kill(pid, signal.SIGTERM)
                        terminated.append(pid)
                    except PermissionError as error:
                        errors.append(f'Permission denied terminating PID {pid}: {error}')
                    except ProcessLookupError:
                        continue
            elif result.returncode == 127:
                lsof_missing = True
        except FileNotFoundError:
            lsof_missing = True

        # ``fuser`` is a good fallback on many Linux distributions and can also
        # take care of any stubborn processes that ignored SIGTERM.
        try:
            kill_result = subprocess.run(
                ['fuser', '-k', f'{port}/tcp'], capture_output=True, text=True, check=False
            )
            if kill_result.returncode == 0:
                for token in kill_result.stdout.split():
                    if token.isdigit():
                        terminated.append(int(token))
            elif kill_result.returncode == 127:
                if lsof_missing:
                    raise FileNotFoundError('Neither lsof nor fuser utilities are available.')
            elif kill_result.returncode not in (0, 1):
                errors.append(
                    kill_result.stderr.strip()
                    or kill_result.stdout.strip()
                    or 'fuser command failed'
                )
        except FileNotFoundError as error:
            if lsof_missing:
                raise
            errors.append(str(error))

        return terminated, errors


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

