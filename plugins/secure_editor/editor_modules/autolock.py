from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from . import config

class AutoLocker(QObject):
    request_lock = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.request_lock.emit)

    def start(self):
        self.timer.start(config.AUTOLOCK_INTERVAL_S * 1000)

    def reset(self):
        if self.timer.isActive():
            self.timer.start() # Reset the timer