# مسیر: plugins/secure_editor/editor_modules/autosave.py

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
        # تایمر را به حالت "یک‌بار اجرا" (single shot) تغییر می‌دهیم.
        # این یعنی فقط یک بار پس از اتمام زمان اجرا می‌شود.
        self.timer.setSingleShot(True) 
        self.timer.timeout.connect(self._trigger_save)
        
    def on_activity(self):
        """
        این متد باید هر زمان که فعالیتی از کاربر (مانند تایپ) رخ می‌دهد، فراخوانی شود.
        این کار تایمر را ریست کرده و شمارش معکوس را از نو شروع می‌کند.
        """
        # تایمر را با تاخیر مشخص شده در کانفیگ، (دوباره) راه‌اندازی کن.
        # اگر تایمر در حال اجرا باشد، متد start() آن را ریست می‌کند.
        self.timer.start(config.IDLE_AUTOSAVE_DELAY_MS)
            
    def stop(self):
        """تایمر را به طور کامل متوقف می‌کند."""
        if self.timer.isActive():
            self.timer.stop()
            print("[AutoSaver] Stopped.")

    def _trigger_save(self):
        """
        این متد خصوصی فقط زمانی اجرا می‌شود که تایمر به پایان برسد
        (یعنی کاربر برای مدتی غیرفعال بوده است).
        """
        print(f"[AutoSaver] Idle time of {config.IDLE_AUTOSAVE_DELAY_MS}ms detected. Requesting autosave.")
        self.request_autosave.emit()