# plugins/web_panel/worker.py

import select
from PyQt6.QtCore import QObject, pyqtSignal
from server import main as server_main

class ServerWorker(QObject):
    finished = pyqtSignal()
    log_message = pyqtSignal(str)
    server_stopped = pyqtSignal()
    
    def __init__(self, host, port, password_verifier):
        super().__init__()
        self.host = host
        self.port = port
        self.password_verifier = password_verifier
        self.server = None
        self._is_running = True 

    def run(self):
        try:
            self.log_message.emit(f"Setting up server...")
            self.server = server_main.setup_server(
                self.host, self.port, self.password_verifier
            )
            self.log_message.emit(f"Server event loop is now running.")
            
            while self._is_running:
                r, _, _ = select.select([self.server.socket], [], [], 0.5)
                
                if r:
                    self.server.handle_request()
            
            self.log_message.emit("Server event loop has been gracefully exited.")

        except Exception as e:
            self.log_message.emit(f"Server thread exited with an error: {e}")
        finally:
            if self.server:
                self.server.server_close()
            self.server_stopped.emit()
            self.finished.emit()
            
    def stop(self):
        self.log_message.emit("Shutdown signal received. Requesting event loop to stop...")
        self._is_running = False