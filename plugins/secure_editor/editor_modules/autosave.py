# plugins/secure_editor/editor_modules/autosave.py

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from . import config

class AutoSaver(QObject):
    """
    Manages autosaving after a period of user inactivity.
    """
    request_autosave = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True) 
        self.timer.timeout.connect(self._trigger_save)
        
    def on_activity(self):
        self.timer.start(config.IDLE_AUTOSAVE_DELAY_MS)
            
    def stop(self):
        if self.timer.isActive():
            self.timer.stop()
            print("[AutoSaver] Stopped.")

    def _trigger_save(self):
        print(f"[AutoSaver] Idle time of {config.IDLE_AUTOSAVE_DELAY_MS}ms detected. Requesting autosave.")
        self.request_autosave.emit()